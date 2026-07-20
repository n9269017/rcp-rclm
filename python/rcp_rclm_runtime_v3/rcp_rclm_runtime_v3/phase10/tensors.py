from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer, strict_object

from rcp_rclm_runtime_v3.contract.common import require_hash, require_schema
from rcp_rclm_runtime_v3.phase10.architecture import CompactTransformerArchitecture
from rcp_rclm_runtime_v3.phase10.constants import (
    PHASE10_CONTRACT_VERSION,
    QUANTIZATION_SCALE_DENOMINATOR,
    QUANTIZATION_SCALE_NUMERATOR,
    TENSOR_BYTE_ORDER,
    TENSOR_DTYPE,
    TENSOR_MANIFEST_SCHEMA_ID,
    TENSOR_RECORD_SCHEMA_ID,
    TENSOR_SPEC_SCHEMA_ID,
    TensorRole,
    cast_tensor_role,
    require_exact_integer,
    require_exact_string,
    require_integer_sequence,
)

_BYTES_PER_ELEMENT = 2
_ZERO_CHUNK = b"\x00" * (1024 * 1024)


def _element_count(shape: Sequence[int]) -> int:
    result = 1
    for dimension in shape:
        result *= dimension
    return result


def _base_tensor_path(name: str) -> str:
    return validate_semantic_path(f"model/tensors/{name}.i16le.bin")


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
        raise FileExistsError(f"tensor path already exists: {path}")
    remaining = size_bytes
    with path.open("xb") as destination:
        while remaining > 0:
            chunk_size = min(remaining, len(_ZERO_CHUNK))
            destination.write(_ZERO_CHUNK[:chunk_size])
            remaining -= chunk_size


def file_is_all_zero(path: Path) -> bool:
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                return True
            if any(chunk):
                return False


@dataclass(frozen=True, slots=True)
class TensorSpec:
    name: str
    path: str
    shape: Sequence[int]
    role: TensorRole
    dtype: str = TENSOR_DTYPE
    byte_order: str = TENSOR_BYTE_ORDER
    quantization_scale_numerator: int = QUANTIZATION_SCALE_NUMERATOR
    quantization_scale_denominator: int = QUANTIZATION_SCALE_DENOMINATOR

    schema_id: ClassVar[str] = TENSOR_SPEC_SCHEMA_ID

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise SchemaValidationError("phase10.tensor_spec.name", "name must be nonempty")
        validate_semantic_path(self.path)
        shape = tuple(self.shape)
        if not shape or any(
            isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1
            for dimension in shape
        ):
            raise SchemaValidationError(
                "phase10.tensor_spec.shape",
                "shape must contain positive integers",
            )
        object.__setattr__(self, "shape", shape)
        cast_tensor_role(self.role)
        if self.dtype != TENSOR_DTYPE:
            raise SchemaValidationError("phase10.tensor_spec.dtype", f"expected {TENSOR_DTYPE}")
        if self.byte_order != TENSOR_BYTE_ORDER:
            raise SchemaValidationError(
                "phase10.tensor_spec.byte_order",
                f"expected {TENSOR_BYTE_ORDER}",
            )
        if self.quantization_scale_numerator != QUANTIZATION_SCALE_NUMERATOR:
            raise SchemaValidationError(
                "phase10.tensor_spec.quantization_scale_numerator",
                f"expected {QUANTIZATION_SCALE_NUMERATOR}",
            )
        if self.quantization_scale_denominator != QUANTIZATION_SCALE_DENOMINATOR:
            raise SchemaValidationError(
                "phase10.tensor_spec.quantization_scale_denominator",
                f"expected {QUANTIZATION_SCALE_DENOMINATOR}",
            )

    @property
    def element_count(self) -> int:
        return _element_count(self.shape)

    @property
    def size_bytes(self) -> int:
        return self.element_count * _BYTES_PER_ELEMENT

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "path": self.path,
            "shape": list(self.shape),
            "role": self.role,
            "dtype": self.dtype,
            "byte_order": self.byte_order,
            "quantization_scale_numerator": self.quantization_scale_numerator,
            "quantization_scale_denominator": self.quantization_scale_denominator,
            "element_count": self.element_count,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_json(cls, value: object) -> "TensorSpec":
        obj = strict_object(
            value,
            "phase10.tensor_spec",
            {
                "schema_id",
                "name",
                "path",
                "shape",
                "role",
                "dtype",
                "byte_order",
                "quantization_scale_numerator",
                "quantization_scale_denominator",
                "element_count",
                "size_bytes",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.tensor_spec.schema_id")
        role_text = require_string(obj["role"], "phase10.tensor_spec.role")
        result = cls(
            name=require_string(obj["name"], "phase10.tensor_spec.name"),
            path=validate_semantic_path(require_string(obj["path"], "phase10.tensor_spec.path")),
            shape=require_integer_sequence(obj["shape"], "phase10.tensor_spec.shape"),
            role=cast_tensor_role(role_text),
            dtype=require_exact_string(
                obj["dtype"], TENSOR_DTYPE, "phase10.tensor_spec.dtype"
            ),
            byte_order=require_exact_string(
                obj["byte_order"], TENSOR_BYTE_ORDER, "phase10.tensor_spec.byte_order"
            ),
            quantization_scale_numerator=require_exact_integer(
                obj["quantization_scale_numerator"],
                QUANTIZATION_SCALE_NUMERATOR,
                "phase10.tensor_spec.quantization_scale_numerator",
            ),
            quantization_scale_denominator=require_exact_integer(
                obj["quantization_scale_denominator"],
                QUANTIZATION_SCALE_DENOMINATOR,
                "phase10.tensor_spec.quantization_scale_denominator",
            ),
        )
        require_exact_integer(
            obj["element_count"], result.element_count, "phase10.tensor_spec.element_count"
        )
        require_exact_integer(
            obj["size_bytes"], result.size_bytes, "phase10.tensor_spec.size_bytes"
        )
        return result


@dataclass(frozen=True, slots=True)
class TensorRecord:
    spec: TensorSpec
    sha256: str

    schema_id: ClassVar[str] = TENSOR_RECORD_SCHEMA_ID

    def __post_init__(self) -> None:
        require_hash(self.sha256, "phase10.tensor_record.sha256")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "spec": self.spec.to_json(),
            "sha256": self.sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> "TensorRecord":
        obj = strict_object(
            value,
            "phase10.tensor_record",
            {"schema_id", "spec", "sha256"},
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.tensor_record.schema_id")
        return cls(
            spec=TensorSpec.from_json(obj["spec"]),
            sha256=require_hash(obj["sha256"], "phase10.tensor_record.sha256"),
        )


@dataclass(frozen=True, slots=True)
class TensorManifest:
    architecture_hash: str
    records: Sequence[TensorRecord]
    parameter_count: int
    contract_version: str = PHASE10_CONTRACT_VERSION

    schema_id: ClassVar[str] = TENSOR_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_hash(self.architecture_hash, "phase10.tensor_manifest.architecture_hash")
        records = tuple(self.records)
        if not records:
            raise SchemaValidationError("phase10.tensor_manifest.records", "at least one tensor is required")
        names = tuple(record.spec.name for record in records)
        paths = tuple(record.spec.path for record in records)
        if len(set(names)) != len(names):
            raise SchemaValidationError("phase10.tensor_manifest.records", "duplicate tensor name")
        if len(set(paths)) != len(paths):
            raise SchemaValidationError("phase10.tensor_manifest.records", "duplicate tensor path")
        ordered = tuple(sorted(records, key=lambda record: record.spec.name.encode("utf-8")))
        if records != ordered:
            raise SchemaValidationError(
                "phase10.tensor_manifest.records",
                "records must be sorted by tensor name",
            )
        if any(record.spec.role != "base_weight" for record in records):
            raise SchemaValidationError(
                "phase10.tensor_manifest.records",
                "base tensor manifest may contain only base_weight records",
            )
        observed = sum(record.spec.element_count for record in records)
        if self.parameter_count != observed:
            raise SchemaValidationError(
                "phase10.tensor_manifest.parameter_count",
                f"declared {self.parameter_count}, observed {observed}",
            )
        if self.contract_version != PHASE10_CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase10.tensor_manifest.contract_version",
                f"expected {PHASE10_CONTRACT_VERSION}",
            )
        object.__setattr__(self, "records", records)

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @property
    def weights_tree_hash(self) -> str:
        return semantic_tree_hash(
            SemanticFileRecord(
                path=record.spec.path,
                mode="0644",
                size=record.spec.size_bytes,
                sha256=record.sha256,
            )
            for record in self.records
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "architecture_hash": self.architecture_hash,
            "parameter_count": self.parameter_count,
            "records": [record.to_json() for record in self.records],
        }

    @classmethod
    def from_json(cls, value: object) -> "TensorManifest":
        obj = strict_object(
            value,
            "phase10.tensor_manifest",
            {
                "schema_id",
                "contract_version",
                "architecture_hash",
                "parameter_count",
                "records",
                "manifest_hash",
                "weights_tree_hash",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.tensor_manifest.schema_id")
        raw_records = obj["records"]
        if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes, bytearray)):
            raise SchemaValidationError("phase10.tensor_manifest.records", "expected an array")
        result = cls(
            architecture_hash=require_hash(
                obj["architecture_hash"], "phase10.tensor_manifest.architecture_hash"
            ),
            records=tuple(TensorRecord.from_json(item) for item in raw_records),
            parameter_count=require_structural_integer(
                obj["parameter_count"], "phase10.tensor_manifest.parameter_count", minimum=1
            ),
            contract_version=require_exact_string(
                obj["contract_version"],
                PHASE10_CONTRACT_VERSION,
                "phase10.tensor_manifest.contract_version",
            ),
        )
        if require_hash(obj["manifest_hash"], "phase10.tensor_manifest.manifest_hash") != result.manifest_hash:
            raise SchemaValidationError(
                "phase10.tensor_manifest.manifest_hash",
                "content hash mismatch",
            )
        if require_hash(
            obj["weights_tree_hash"], "phase10.tensor_manifest.weights_tree_hash"
        ) != result.weights_tree_hash:
            raise SchemaValidationError(
                "phase10.tensor_manifest.weights_tree_hash",
                "tree hash mismatch",
            )
        return result

    def serialized_json(self) -> dict[str, object]:
        value = self.to_json()
        value["manifest_hash"] = self.manifest_hash
        value["weights_tree_hash"] = self.weights_tree_hash
        return value


def expected_base_tensor_specs(
    architecture: CompactTransformerArchitecture,
) -> Sequence[TensorSpec]:
    return tuple(
        TensorSpec(
            name=blueprint.name,
            path=_base_tensor_path(blueprint.name),
            shape=blueprint.shape,
            role="base_weight",
        )
        for blueprint in architecture.base_tensor_blueprints()
    )


def create_zero_base_tensor_manifest(
    package_root: Path,
    architecture: CompactTransformerArchitecture,
) -> TensorManifest:
    root = package_root.resolve(strict=False)
    records: list[TensorRecord] = []
    for spec in expected_base_tensor_specs(architecture):
        file_path = root / spec.path
        _write_zero_file(file_path, spec.size_bytes)
        records.append(TensorRecord(spec=spec, sha256=_file_sha256(file_path)))
    return TensorManifest(
        architecture_hash=architecture.architecture_hash,
        records=tuple(records),
        parameter_count=architecture.base_parameter_count,
    )


def verify_base_tensor_manifest(
    package_root: Path,
    architecture: CompactTransformerArchitecture,
    manifest: TensorManifest,
) -> None:
    if manifest.architecture_hash != architecture.architecture_hash:
        raise SchemaValidationError(
            "phase10.tensor_manifest.architecture_hash",
            "manifest is not bound to the selected architecture",
        )
    expected = expected_base_tensor_specs(architecture)
    if tuple(record.spec for record in manifest.records) != expected:
        raise SchemaValidationError(
            "phase10.tensor_manifest.records",
            "tensor specifications do not equal the selected architecture graph",
        )
    root = package_root.resolve(strict=True)
    for record in manifest.records:
        file_path = root / record.spec.path
        if not file_path.is_file():
            raise SchemaValidationError(
                "phase10.tensor_manifest.records",
                f"missing tensor file {record.spec.path}",
            )
        observed_size = file_path.stat().st_size
        if observed_size != record.spec.size_bytes:
            raise SchemaValidationError(
                "phase10.tensor_manifest.records",
                f"tensor size mismatch for {record.spec.name}",
            )
        if _file_sha256(file_path) != record.sha256:
            raise SchemaValidationError(
                "phase10.tensor_manifest.records",
                f"tensor hash mismatch for {record.spec.name}",
            )


__all__ = [
    "TensorManifest",
    "TensorRecord",
    "TensorSpec",
    "create_zero_base_tensor_manifest",
    "expected_base_tensor_specs",
    "file_is_all_zero",
    "verify_base_tensor_manifest",
]
