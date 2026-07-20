from __future__ import annotations

import hashlib
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer, strict_object

from rcp_rclm_runtime_v3.contract.common import require_hash, require_schema
from rcp_rclm_runtime_v3.phase10.architecture import CompactTransformerArchitecture
from rcp_rclm_runtime_v3.phase10.constants import (
    ADAPTER_MANIFEST_SCHEMA_ID,
    LORA_ALPHA,
    LORA_PARAMETER_COUNT,
    LORA_RANK,
    LORA_TARGET_MODULES,
    PHASE10_CONTRACT_VERSION,
    AdapterStatus,
    cast_adapter_status,
    require_exact_integer,
    require_exact_string,
    require_string_sequence,
)
from rcp_rclm_runtime_v3.phase10.tensors import TensorRecord, TensorSpec, file_is_all_zero


def _adapter_tensor_path(name: str) -> str:
    return validate_semantic_path(f"model/adapters/tensors/{name}.i16le.bin")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_zero_file(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"adapter tensor path already exists: {path}")
    block = b"\x00" * min(size_bytes, 1024 * 1024)
    remaining = size_bytes
    with path.open("xb") as destination:
        while remaining > 0:
            count = min(remaining, len(block))
            destination.write(block[:count])
            remaining -= count


def _write_deterministic_a(path: Path, spec: TensorSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"adapter tensor path already exists: {path}")
    name_seed = sum(spec.name.encode("utf-8"))
    remaining = spec.element_count
    offset = 0
    with path.open("xb") as destination:
        while remaining > 0:
            count = min(remaining, 4096)
            values: list[int] = []
            for local_index in range(count):
                value = ((name_seed + 17 * (offset + local_index)) % 7) - 3
                if value == 0:
                    value = 1
                values.append(value)
            destination.write(struct.pack("<" + "h" * count, *values))
            offset += count
            remaining -= count


def _file_has_nonzero(path: Path) -> bool:
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                return False
            if any(chunk):
                return True


def expected_lora_tensor_specs(
    architecture: CompactTransformerArchitecture,
) -> Sequence[TensorSpec]:
    blueprint_by_name = {
        blueprint.name: blueprint
        for blueprint in architecture.base_tensor_blueprints()
    }
    result: list[TensorSpec] = []
    for layer_index in range(architecture.layer_count):
        prefix = f"model.layers.{layer_index:02d}"
        for module_name in LORA_TARGET_MODULES:
            base_name = f"{prefix}.{module_name}.weight"
            if base_name not in blueprint_by_name:
                raise SchemaValidationError(
                    "phase10.adapter.targets",
                    f"selected LoRA target does not exist: {base_name}",
                )
            out_features, in_features = blueprint_by_name[base_name].shape
            adapter_prefix = f"adapter.layers.{layer_index:02d}.{module_name}"
            result.extend(
                (
                    TensorSpec(
                        name=f"{adapter_prefix}.A",
                        path=_adapter_tensor_path(f"{adapter_prefix}.A"),
                        shape=(LORA_RANK, in_features),
                        role="adapter_a",
                    ),
                    TensorSpec(
                        name=f"{adapter_prefix}.B",
                        path=_adapter_tensor_path(f"{adapter_prefix}.B"),
                        shape=(out_features, LORA_RANK),
                        role="adapter_b",
                    ),
                )
            )
    ordered = tuple(sorted(result, key=lambda item: item.name.encode("utf-8")))
    observed = sum(item.element_count for item in ordered)
    if observed != LORA_PARAMETER_COUNT:
        raise SchemaValidationError(
            "phase10.adapter.parameter_count",
            f"selected LoRA graph contains {observed} parameters",
        )
    return ordered


def expected_lora_base_targets(
    architecture: CompactTransformerArchitecture,
) -> Sequence[str]:
    result = []
    for layer_index in range(architecture.layer_count):
        prefix = f"model.layers.{layer_index:02d}"
        for module_name in LORA_TARGET_MODULES:
            result.append(f"{prefix}.{module_name}.weight")
    return tuple(sorted(result, key=lambda item: item.encode("utf-8")))


@dataclass(frozen=True, slots=True)
class LoRAAdapterManifest:
    architecture_hash: str
    base_weights_tree_hash: str
    status: AdapterStatus
    rank: int
    alpha: int
    zero_output_factor: str
    target_base_tensors: Sequence[str]
    records: Sequence[TensorRecord]
    parameter_count: int
    contract_version: str = PHASE10_CONTRACT_VERSION

    schema_id: ClassVar[str] = ADAPTER_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_hash(self.architecture_hash, "phase10.adapter.architecture_hash")
        require_hash(self.base_weights_tree_hash, "phase10.adapter.base_weights_tree_hash")
        cast_adapter_status(self.status)
        targets = tuple(self.target_base_tensors)
        records = tuple(self.records)
        if len(set(targets)) != len(targets):
            raise SchemaValidationError("phase10.adapter.target_base_tensors", "duplicate target")
        if targets != tuple(sorted(targets, key=lambda item: item.encode("utf-8"))):
            raise SchemaValidationError(
                "phase10.adapter.target_base_tensors",
                "targets must be sorted by UTF-8 bytes",
            )
        names = tuple(record.spec.name for record in records)
        if len(set(names)) != len(names):
            raise SchemaValidationError("phase10.adapter.records", "duplicate tensor name")
        if records != tuple(sorted(records, key=lambda item: item.spec.name.encode("utf-8"))):
            raise SchemaValidationError(
                "phase10.adapter.records",
                "records must be sorted by tensor name",
            )
        if self.status == "absent":
            if self.rank != 0 or self.alpha != 0 or self.parameter_count != 0:
                raise SchemaValidationError(
                    "phase10.adapter",
                    "absent adapter must have zero rank, alpha, and parameter count",
                )
            if self.zero_output_factor != "none" or targets or records:
                raise SchemaValidationError(
                    "phase10.adapter",
                    "absent adapter must have no target or tensor records",
                )
        else:
            if self.rank != LORA_RANK:
                raise SchemaValidationError("phase10.adapter.rank", f"expected {LORA_RANK}")
            if self.alpha != LORA_ALPHA:
                raise SchemaValidationError("phase10.adapter.alpha", f"expected {LORA_ALPHA}")
            if self.parameter_count != LORA_PARAMETER_COUNT:
                raise SchemaValidationError(
                    "phase10.adapter.parameter_count",
                    f"expected {LORA_PARAMETER_COUNT}",
                )
            if self.zero_output_factor != "B":
                raise SchemaValidationError(
                    "phase10.adapter.zero_output_factor",
                    "selected LoRA extension uses factor B as the zero output factor",
                )
            if any(record.spec.role not in {"adapter_a", "adapter_b"} for record in records):
                raise SchemaValidationError(
                    "phase10.adapter.records",
                    "adapter manifest may contain only adapter tensors",
                )
            observed = sum(record.spec.element_count for record in records)
            if observed != self.parameter_count:
                raise SchemaValidationError(
                    "phase10.adapter.parameter_count",
                    f"declared {self.parameter_count}, observed {observed}",
                )
        if self.contract_version != PHASE10_CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase10.adapter.contract_version",
                f"expected {PHASE10_CONTRACT_VERSION}",
            )
        object.__setattr__(self, "target_base_tensors", targets)
        object.__setattr__(self, "records", records)

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "architecture_hash": self.architecture_hash,
            "base_weights_tree_hash": self.base_weights_tree_hash,
            "status": self.status,
            "rank": self.rank,
            "alpha": self.alpha,
            "zero_output_factor": self.zero_output_factor,
            "target_base_tensors": list(self.target_base_tensors),
            "parameter_count": self.parameter_count,
            "records": [record.to_json() for record in self.records],
        }

    def serialized_json(self) -> dict[str, object]:
        result = self.to_json()
        result["manifest_hash"] = self.manifest_hash
        return result

    @classmethod
    def from_json(cls, value: object) -> "LoRAAdapterManifest":
        obj = strict_object(
            value,
            "phase10.adapter",
            {
                "schema_id",
                "contract_version",
                "architecture_hash",
                "base_weights_tree_hash",
                "status",
                "rank",
                "alpha",
                "zero_output_factor",
                "target_base_tensors",
                "parameter_count",
                "records",
                "manifest_hash",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.adapter.schema_id")
        status_text = require_string(obj["status"], "phase10.adapter.status")
        raw_records = obj["records"]
        if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes, bytearray)):
            raise SchemaValidationError("phase10.adapter.records", "expected an array")
        result = cls(
            architecture_hash=require_hash(
                obj["architecture_hash"], "phase10.adapter.architecture_hash"
            ),
            base_weights_tree_hash=require_hash(
                obj["base_weights_tree_hash"], "phase10.adapter.base_weights_tree_hash"
            ),
            status=cast_adapter_status(status_text),
            rank=require_structural_integer(obj["rank"], "phase10.adapter.rank", minimum=0),
            alpha=require_structural_integer(obj["alpha"], "phase10.adapter.alpha", minimum=0),
            zero_output_factor=require_string(
                obj["zero_output_factor"], "phase10.adapter.zero_output_factor"
            ),
            target_base_tensors=require_string_sequence(
                obj["target_base_tensors"], "phase10.adapter.target_base_tensors"
            ),
            records=tuple(TensorRecord.from_json(item) for item in raw_records),
            parameter_count=require_structural_integer(
                obj["parameter_count"], "phase10.adapter.parameter_count", minimum=0
            ),
            contract_version=require_exact_string(
                obj["contract_version"], PHASE10_CONTRACT_VERSION, "phase10.adapter.contract_version"
            ),
        )
        if require_hash(obj["manifest_hash"], "phase10.adapter.manifest_hash") != result.manifest_hash:
            raise SchemaValidationError("phase10.adapter.manifest_hash", "content hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ZeroAdapterVerification:
    all_b_tensors_zero: bool
    at_least_one_a_tensor_nonzero: bool
    expected_tensor_graph: bool

    @property
    def accepted(self) -> bool:
        return self.all_b_tensors_zero and self.at_least_one_a_tensor_nonzero and self.expected_tensor_graph


def empty_adapter_manifest(
    architecture: CompactTransformerArchitecture,
    base_weights_tree_hash: str,
) -> LoRAAdapterManifest:
    return LoRAAdapterManifest(
        architecture_hash=architecture.architecture_hash,
        base_weights_tree_hash=base_weights_tree_hash,
        status="absent",
        rank=0,
        alpha=0,
        zero_output_factor="none",
        target_base_tensors=(),
        records=(),
        parameter_count=0,
    )


def create_zero_output_lora_manifest(
    package_root: Path,
    architecture: CompactTransformerArchitecture,
    base_weights_tree_hash: str,
) -> LoRAAdapterManifest:
    root = package_root.resolve(strict=False)
    records: list[TensorRecord] = []
    for spec in expected_lora_tensor_specs(architecture):
        file_path = root / spec.path
        if spec.role == "adapter_a":
            _write_deterministic_a(file_path, spec)
        else:
            _write_zero_file(file_path, spec.size_bytes)
        records.append(TensorRecord(spec=spec, sha256=_file_sha256(file_path)))
    return LoRAAdapterManifest(
        architecture_hash=architecture.architecture_hash,
        base_weights_tree_hash=base_weights_tree_hash,
        status="zero_output_extension",
        rank=LORA_RANK,
        alpha=LORA_ALPHA,
        zero_output_factor="B",
        target_base_tensors=expected_lora_base_targets(architecture),
        records=tuple(records),
        parameter_count=LORA_PARAMETER_COUNT,
    )


def verify_adapter_manifest(
    package_root: Path,
    architecture: CompactTransformerArchitecture,
    base_weights_tree_hash: str,
    manifest: LoRAAdapterManifest,
) -> ZeroAdapterVerification:
    if manifest.architecture_hash != architecture.architecture_hash:
        raise SchemaValidationError(
            "phase10.adapter.architecture_hash",
            "adapter is not bound to the selected architecture",
        )
    if manifest.base_weights_tree_hash != base_weights_tree_hash:
        raise SchemaValidationError(
            "phase10.adapter.base_weights_tree_hash",
            "adapter is not bound to the selected base weights",
        )
    if manifest.status == "absent":
        return ZeroAdapterVerification(
            all_b_tensors_zero=True,
            at_least_one_a_tensor_nonzero=True,
            expected_tensor_graph=True,
        )
    expected_specs = expected_lora_tensor_specs(architecture)
    expected_targets = expected_lora_base_targets(architecture)
    graph_matches = (
        tuple(record.spec for record in manifest.records) == expected_specs
        and manifest.target_base_tensors == expected_targets
    )
    root = package_root.resolve(strict=True)
    all_b_zero = True
    any_a_nonzero = False
    for record in manifest.records:
        file_path = root / record.spec.path
        if not file_path.is_file():
            raise SchemaValidationError(
                "phase10.adapter.records",
                f"missing adapter tensor file {record.spec.path}",
            )
        if file_path.stat().st_size != record.spec.size_bytes:
            raise SchemaValidationError(
                "phase10.adapter.records",
                f"adapter tensor size mismatch for {record.spec.name}",
            )
        if _file_sha256(file_path) != record.sha256:
            raise SchemaValidationError(
                "phase10.adapter.records",
                f"adapter tensor hash mismatch for {record.spec.name}",
            )
        if record.spec.role == "adapter_b":
            all_b_zero = all_b_zero and file_is_all_zero(file_path)
        else:
            any_a_nonzero = any_a_nonzero or _file_has_nonzero(file_path)
    return ZeroAdapterVerification(
        all_b_tensors_zero=all_b_zero,
        at_least_one_a_tensor_nonzero=any_a_nonzero,
        expected_tensor_graph=graph_matches,
    )


__all__ = [
    "LoRAAdapterManifest",
    "ZeroAdapterVerification",
    "create_zero_output_lora_manifest",
    "empty_adapter_manifest",
    "expected_lora_base_targets",
    "expected_lora_tensor_specs",
    "verify_adapter_manifest",
]
