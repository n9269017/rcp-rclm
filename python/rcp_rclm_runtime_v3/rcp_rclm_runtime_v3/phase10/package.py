from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer, strict_object

from rcp_rclm_runtime_v3.contract.common import SELECTED_MODEL_FAMILY, require_hash, require_schema
from rcp_rclm_runtime_v3.contract.state import ModelIdentity
from rcp_rclm_runtime_v3.phase10.adapters import (
    LoRAAdapterManifest,
    create_zero_output_lora_manifest,
    empty_adapter_manifest,
)
from rcp_rclm_runtime_v3.phase10.architecture import CompactTransformerArchitecture
from rcp_rclm_runtime_v3.phase10.constants import (
    BASE_PARAMETER_COUNT,
    EXTENDED_PARAMETER_COUNT,
    PACKAGE_MANIFEST_SCHEMA_ID,
    PHASE10_CONTRACT_VERSION,
    require_exact_string,
)
from rcp_rclm_runtime_v3.phase10.tensors import (
    TensorManifest,
    create_zero_base_tensor_manifest,
)
from rcp_rclm_runtime_v3.phase10.tokenizer import (
    ByteTokenizerManifest,
    tokenizer_bytes,
    vocabulary_json,
)

ARCHITECTURE_PATH = "model/architecture.json"
TOKENIZER_BYTES_PATH = "model/tokenizer/tokenizer.bin"
VOCABULARY_PATH = "model/tokenizer/vocabulary.json"
TOKENIZER_MANIFEST_PATH = "model/tokenizer/manifest.json"
TENSOR_MANIFEST_PATH = "model/tensors/manifest.json"
ADAPTER_MANIFEST_PATH = "model/adapters/manifest.json"
PACKAGE_MANIFEST_PATH = "package_manifest.json"

SUPPORT_ARTIFACTS: Mapping[str, Mapping[str, object]] = {
    "training/training_policy.json": {
        "schema_id": "runtime.v3.phase10.training_policy.v1",
        "backend_authority": "untrusted_external_only",
        "gpu_training_permitted": True,
        "authoritative_evaluation_permitted": False,
        "status": "reference_substrate_no_training",
    },
    "training/optimizer_state.json": {
        "schema_id": "runtime.v3.phase10.optimizer_state.v1",
        "optimizer": "none",
        "step": 0,
        "status": "reference_substrate",
    },
    "training/data_curriculum.json": {
        "schema_id": "runtime.v3.phase10.data_curriculum.v1",
        "task_class": "lean_theorem_completion_v1",
        "training_examples": 0,
        "heldout_examples_visible": False,
        "status": "reference_substrate",
    },
    "policies/generator_policy.json": {
        "schema_id": "runtime.v3.phase10.generator_policy.v1",
        "policy": "external_reference_only",
        "learned_proposal_authority": False,
    },
    "policies/planner_policy.json": {
        "schema_id": "runtime.v3.phase10.planner_policy.v1",
        "policy": "external_reference_only",
        "open_ended_planning": False,
    },
    "policies/tool_policy.json": {
        "schema_id": "runtime.v3.phase10.tool_policy.v1",
        "allowed_tools": [],
        "dynamic_code_loading": False,
    },
    "policies/verification_policy.json": {
        "schema_id": "runtime.v3.phase10.verification_policy.v1",
        "task_verifier": "pinned_lean_theorem_verifier_v1",
        "candidate_self_report_authoritative": False,
    },
    "policies/resource_policy.json": {
        "schema_id": "runtime.v3.phase10.resource_policy.v1",
        "maximum_parameter_count": 50_000_000,
        "authoritative_cpu_evaluation": True,
        "training_backend_untrusted": True,
    },
    "retrieval/index_manifest.json": {
        "schema_id": "runtime.v3.phase10.retrieval_index.v1",
        "entry_count": 0,
        "status": "empty",
    },
    "memory/memory_manifest.json": {
        "schema_id": "runtime.v3.phase10.memory_manifest.v1",
        "entry_count": 0,
        "status": "empty",
    },
    "self_model/manifest.json": {
        "schema_id": "runtime.v3.phase10.self_model.v1",
        "declared_model_family": SELECTED_MODEL_FAMILY,
        "phase": 10,
        "claim": "substrate_only",
    },
    "runtime/rng_state.json": {
        "schema_id": "runtime.v3.phase10.rng_state.v1",
        "algorithm": "sha256_counter_v1",
        "seed_hex": sha256_hex(b"RCLM-PHASE10-REFERENCE-SEED"),
        "counter": 0,
    },
    "runtime/environment.json": {
        "schema_id": "runtime.v3.phase10.environment.v1",
        "authoritative_evaluation": "deterministic_cpu_only",
        "network_required": False,
        "gpu_required": False,
        "native_float_acceptance": False,
    },
    "runtime/resource_measurement.json": {
        "schema_id": "runtime.v3.phase10.resource_measurement.v1",
        "base_parameter_count": BASE_PARAMETER_COUNT,
        "training_invocations": 0,
        "generator_invocations": 0,
        "replay_invocations": 0,
    },
}

SUPPORT_HASH_FIELD_BY_PATH: Mapping[str, str] = {
    "training/training_policy.json": "training_policy_hash",
    "training/optimizer_state.json": "optimizer_state_hash",
    "training/data_curriculum.json": "data_curriculum_hash",
    "policies/generator_policy.json": "generator_policy_hash",
    "policies/planner_policy.json": "planner_policy_hash",
    "policies/tool_policy.json": "tool_policy_hash",
    "policies/verification_policy.json": "verification_policy_hash",
    "policies/resource_policy.json": "resource_policy_hash",
    "retrieval/index_manifest.json": "retrieval_index_hash",
    "memory/memory_manifest.json": "memory_manifest_hash",
    "self_model/manifest.json": "self_model_hash",
    "runtime/rng_state.json": "rng_state_hash",
    "runtime/environment.json": "environment_hash",
    "runtime/resource_measurement.json": "resource_measurement_hash",
}


def _write_new_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"output path already exists: {path}")
    path.write_bytes(content)


def _write_new_json(path: Path, value: object) -> None:
    _write_new_bytes(path, canonical_json_bytes(value))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _payload_tree_hash(root: Path) -> str:
    records: list[SemanticFileRecord] = []
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_root)
        for directory_name in directory_names:
            directory_path = current / directory_name
            if directory_path.is_symlink():
                raise SchemaValidationError("phase10.package", "symlink directory is forbidden")
        for file_name in file_names:
            file_path = current / file_name
            relative = file_path.relative_to(root).as_posix()
            if relative == PACKAGE_MANIFEST_PATH:
                continue
            validate_semantic_path(relative)
            status = file_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise SchemaValidationError(
                    "phase10.package",
                    f"only regular files are permitted: {relative}",
                )
            records.append(
                SemanticFileRecord(
                    path=relative,
                    mode="0755" if status.st_mode & 0o111 else "0644",
                    size=status.st_size,
                    sha256=_file_sha256(file_path),
                )
            )
    return semantic_tree_hash(records)


def support_artifact_hashes() -> dict[str, str]:
    return {
        SUPPORT_HASH_FIELD_BY_PATH[path]: canonical_json_hash(value)
        for path, value in SUPPORT_ARTIFACTS.items()
    }


def _write_support_artifacts(root: Path) -> dict[str, str]:
    for path, value in SUPPORT_ARTIFACTS.items():
        _write_new_json(root / path, value)
    return support_artifact_hashes()


def _verify_support_artifacts(root: Path, manifest_values: Mapping[str, str]) -> None:
    for path, expected_value in SUPPORT_ARTIFACTS.items():
        file_path = root / path
        if not file_path.is_file():
            raise SchemaValidationError("phase10.package", f"missing support artifact {path}")
        observed = load_json_strict(file_path.read_bytes(), require_canonical=True)
        if observed != expected_value:
            raise SchemaValidationError("phase10.package", f"support artifact mismatch: {path}")
        field_name = SUPPORT_HASH_FIELD_BY_PATH[path]
        if manifest_values[field_name] != canonical_json_hash(expected_value):
            raise SchemaValidationError("phase10.package", f"support hash mismatch: {field_name}")


@dataclass(frozen=True, slots=True)
class ModelPackageManifest:
    package_id: str
    parent_package_id: str | None
    architecture_hash: str
    tokenizer_manifest_hash: str
    tokenizer_hash: str
    vocabulary_hash: str
    tensor_manifest_hash: str
    weights_tree_hash: str
    adapter_manifest_hash: str
    training_policy_hash: str
    optimizer_state_hash: str
    data_curriculum_hash: str
    generator_policy_hash: str
    planner_policy_hash: str
    tool_policy_hash: str
    verification_policy_hash: str
    resource_policy_hash: str
    retrieval_index_hash: str
    memory_manifest_hash: str
    self_model_hash: str
    rng_state_hash: str
    environment_hash: str
    resource_measurement_hash: str
    parameter_count: int
    model_identity_hash: str
    payload_tree_hash: str
    contract_version: str = PHASE10_CONTRACT_VERSION

    schema_id: ClassVar[str] = PACKAGE_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        if not self.package_id:
            raise SchemaValidationError("phase10.package.package_id", "package_id must be nonempty")
        if self.parent_package_id is not None and not self.parent_package_id:
            raise SchemaValidationError(
                "phase10.package.parent_package_id",
                "parent_package_id must be nonempty when present",
            )
        for name in self.hash_field_names():
            require_hash(getattr(self, name), f"phase10.package.{name}")
        if isinstance(self.parameter_count, bool) or not isinstance(self.parameter_count, int):
            raise SchemaValidationError("phase10.package.parameter_count", "expected an integer")
        if self.parameter_count not in {BASE_PARAMETER_COUNT, EXTENDED_PARAMETER_COUNT}:
            raise SchemaValidationError(
                "phase10.package.parameter_count",
                "selected substrate permits only the base or zero-LoRA-extended parameter count",
            )
        if self.contract_version != PHASE10_CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase10.package.contract_version",
                f"expected {PHASE10_CONTRACT_VERSION}",
            )

    @staticmethod
    def hash_field_names() -> Sequence[str]:
        return (
            "architecture_hash",
            "tokenizer_manifest_hash",
            "tokenizer_hash",
            "vocabulary_hash",
            "tensor_manifest_hash",
            "weights_tree_hash",
            "adapter_manifest_hash",
            "training_policy_hash",
            "optimizer_state_hash",
            "data_curriculum_hash",
            "generator_policy_hash",
            "planner_policy_hash",
            "tool_policy_hash",
            "verification_policy_hash",
            "resource_policy_hash",
            "retrieval_index_hash",
            "memory_manifest_hash",
            "self_model_hash",
            "rng_state_hash",
            "environment_hash",
            "resource_measurement_hash",
            "model_identity_hash",
            "payload_tree_hash",
        )

    @property
    def package_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def model_identity(self) -> ModelIdentity:
        return ModelIdentity(
            model_family=SELECTED_MODEL_FAMILY,
            architecture_hash=self.architecture_hash,
            weights_tree_hash=self.weights_tree_hash,
            adapter_manifest_hash=self.adapter_manifest_hash,
            tensor_manifest_hash=self.tensor_manifest_hash,
            tokenizer_hash=self.tokenizer_hash,
            vocabulary_hash=self.vocabulary_hash,
            parameter_count=self.parameter_count,
        )

    def content_json(self) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "package_id": self.package_id,
            "parent_package_id": self.parent_package_id,
            "parameter_count": self.parameter_count,
        }
        for name in self.hash_field_names():
            value[name] = getattr(self, name)
        return value

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["package_hash"] = self.package_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> "ModelPackageManifest":
        fields = {
            "schema_id",
            "contract_version",
            "package_id",
            "parent_package_id",
            "parameter_count",
            "package_hash",
            *cls.hash_field_names(),
        }
        obj = strict_object(value, "phase10.package", fields)
        require_schema(obj["schema_id"], cls.schema_id, "phase10.package.schema_id")
        parent = obj["parent_package_id"]
        if parent is not None:
            parent = require_string(parent, "phase10.package.parent_package_id")
        kwargs: dict[str, object] = {
            "package_id": require_string(obj["package_id"], "phase10.package.package_id"),
            "parent_package_id": parent,
            "parameter_count": require_structural_integer(
                obj["parameter_count"], "phase10.package.parameter_count", minimum=1
            ),
            "contract_version": require_exact_string(
                obj["contract_version"], PHASE10_CONTRACT_VERSION, "phase10.package.contract_version"
            ),
        }
        for name in cls.hash_field_names():
            kwargs[name] = require_hash(obj[name], f"phase10.package.{name}")
        result = cls(**kwargs)
        if require_hash(obj["package_hash"], "phase10.package.package_hash") != result.package_hash:
            raise SchemaValidationError("phase10.package.package_hash", "content hash mismatch")
        return result


def _manifest_from_components(
    *,
    package_id: str,
    parent_package_id: str | None,
    architecture: CompactTransformerArchitecture,
    tokenizer: ByteTokenizerManifest,
    tensors: TensorManifest,
    adapter: LoRAAdapterManifest,
    support_hashes: Mapping[str, str],
    payload_tree_hash: str,
) -> ModelPackageManifest:
    parameter_count = tensors.parameter_count + adapter.parameter_count
    identity = ModelIdentity(
        model_family=SELECTED_MODEL_FAMILY,
        architecture_hash=architecture.architecture_hash,
        weights_tree_hash=tensors.weights_tree_hash,
        adapter_manifest_hash=adapter.manifest_hash,
        tensor_manifest_hash=tensors.manifest_hash,
        tokenizer_hash=tokenizer.tokenizer_bytes_hash,
        vocabulary_hash=tokenizer.vocabulary_hash,
        parameter_count=parameter_count,
    )
    return ModelPackageManifest(
        package_id=package_id,
        parent_package_id=parent_package_id,
        architecture_hash=architecture.architecture_hash,
        tokenizer_manifest_hash=tokenizer.manifest_hash,
        tokenizer_hash=tokenizer.tokenizer_bytes_hash,
        vocabulary_hash=tokenizer.vocabulary_hash,
        tensor_manifest_hash=tensors.manifest_hash,
        weights_tree_hash=tensors.weights_tree_hash,
        adapter_manifest_hash=adapter.manifest_hash,
        parameter_count=parameter_count,
        model_identity_hash=identity.model_identity_hash,
        payload_tree_hash=payload_tree_hash,
        **support_hashes,
    )


def build_reference_predecessor_package(output_root: Path) -> ModelPackageManifest:
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"output package already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-base-", dir=resolved.parent) as temp_dir:
        staging = Path(temp_dir) / "package"
        staging.mkdir(parents=True, exist_ok=False)
        architecture = CompactTransformerArchitecture()
        tokenizer = ByteTokenizerManifest.frozen()
        _write_new_json(staging / ARCHITECTURE_PATH, architecture.to_json())
        _write_new_bytes(staging / TOKENIZER_BYTES_PATH, tokenizer_bytes())
        _write_new_json(staging / VOCABULARY_PATH, vocabulary_json())
        _write_new_json(staging / TOKENIZER_MANIFEST_PATH, tokenizer.to_json())
        tensors = create_zero_base_tensor_manifest(staging, architecture)
        _write_new_json(staging / TENSOR_MANIFEST_PATH, tensors.serialized_json())
        adapter = empty_adapter_manifest(architecture, tensors.weights_tree_hash)
        _write_new_json(staging / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
        support_hashes = _write_support_artifacts(staging)
        payload_hash = _payload_tree_hash(staging)
        manifest = _manifest_from_components(
            package_id="phase10-reference-root",
            parent_package_id=None,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=tensors,
            adapter=adapter,
            support_hashes=support_hashes,
            payload_tree_hash=payload_hash,
        )
        _write_new_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, resolved)
    return manifest


def build_zero_lora_extension_package(
    predecessor_root: Path,
    output_root: Path,
) -> ModelPackageManifest:
    predecessor = predecessor_root.resolve(strict=True)
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"output package already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    predecessor_manifest = load_package_manifest(predecessor)
    architecture = CompactTransformerArchitecture.from_json(
        load_json_strict((predecessor / ARCHITECTURE_PATH).read_bytes(), require_canonical=True)
    )
    tokenizer = ByteTokenizerManifest.from_json(
        load_json_strict((predecessor / TOKENIZER_MANIFEST_PATH).read_bytes(), require_canonical=True)
    )
    tensors = TensorManifest.from_json(
        load_json_strict((predecessor / TENSOR_MANIFEST_PATH).read_bytes(), require_canonical=True)
    )
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-lora-", dir=resolved.parent) as temp_dir:
        staging = Path(temp_dir) / "package"
        shutil.copytree(predecessor, staging, symlinks=False)
        (staging / PACKAGE_MANIFEST_PATH).unlink()
        (staging / ADAPTER_MANIFEST_PATH).unlink()
        adapter = create_zero_output_lora_manifest(
            staging,
            architecture,
            tensors.weights_tree_hash,
        )
        _write_new_json(staging / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
        support_hashes = support_artifact_hashes()
        payload_hash = _payload_tree_hash(staging)
        manifest = _manifest_from_components(
            package_id="phase10-reference-zero-lora",
            parent_package_id=predecessor_manifest.package_id,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=tensors,
            adapter=adapter,
            support_hashes=support_hashes,
            payload_tree_hash=payload_hash,
        )
        _write_new_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, resolved)
    return manifest


def load_package_manifest(root: Path) -> ModelPackageManifest:
    resolved = root.resolve(strict=True)
    value = load_json_strict(
        (resolved / PACKAGE_MANIFEST_PATH).read_bytes(),
        require_canonical=True,
    )
    return ModelPackageManifest.from_json(value)


def load_package_components(
    root: Path,
) -> tuple[
    ModelPackageManifest,
    CompactTransformerArchitecture,
    ByteTokenizerManifest,
    TensorManifest,
    LoRAAdapterManifest,
]:
    resolved = root.resolve(strict=True)
    manifest = load_package_manifest(resolved)
    architecture = CompactTransformerArchitecture.from_json(
        load_json_strict((resolved / ARCHITECTURE_PATH).read_bytes(), require_canonical=True)
    )
    tokenizer = ByteTokenizerManifest.from_json(
        load_json_strict((resolved / TOKENIZER_MANIFEST_PATH).read_bytes(), require_canonical=True)
    )
    tensors = TensorManifest.from_json(
        load_json_strict((resolved / TENSOR_MANIFEST_PATH).read_bytes(), require_canonical=True)
    )
    adapter = LoRAAdapterManifest.from_json(
        load_json_strict((resolved / ADAPTER_MANIFEST_PATH).read_bytes(), require_canonical=True)
    )
    return manifest, architecture, tokenizer, tensors, adapter


def verify_support_artifacts(
    root: Path,
    manifest: ModelPackageManifest,
) -> None:
    values = {
        field_name: getattr(manifest, field_name)
        for field_name in SUPPORT_HASH_FIELD_BY_PATH.values()
    }
    _verify_support_artifacts(root.resolve(strict=True), values)


def recompute_payload_tree_hash(root: Path) -> str:
    return _payload_tree_hash(root.resolve(strict=True))


__all__ = [
    "ADAPTER_MANIFEST_PATH",
    "ARCHITECTURE_PATH",
    "ModelPackageManifest",
    "PACKAGE_MANIFEST_PATH",
    "TENSOR_MANIFEST_PATH",
    "TOKENIZER_BYTES_PATH",
    "TOKENIZER_MANIFEST_PATH",
    "VOCABULARY_PATH",
    "build_reference_predecessor_package",
    "build_zero_lora_extension_package",
    "load_package_components",
    "load_package_manifest",
    "recompute_payload_tree_hash",
    "support_artifact_hashes",
    "verify_support_artifacts",
]
