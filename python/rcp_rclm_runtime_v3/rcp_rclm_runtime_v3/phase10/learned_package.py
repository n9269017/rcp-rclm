from __future__ import annotations

import copy
import hashlib
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.adapters import empty_adapter_manifest
from rcp_rclm_runtime_v3.phase10.learned_data import PROTECTED_CHAIN
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    ARCHITECTURE_PATH,
    PACKAGE_MANIFEST_PATH,
    SUPPORT_ARTIFACTS,
    SUPPORT_HASH_FIELD_BY_PATH,
    TENSOR_MANIFEST_PATH,
    TOKENIZER_MANIFEST_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    build_reference_predecessor_package,
    load_package_components,
    load_package_manifest,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import (
    ATTN_OUTPUT_TENSOR,
    apply_sparse_profile,
    transition_tensor_path,
    validate_sparse_profile,
)
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord

LEARNED_SUPPORT_PROFILE: Final[str] = "phase10_sparse_language_model_v1"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _overwrite_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _learned_support_artifacts(
    *,
    optimizer_step: int,
    training_report_hash: str,
    training_examples: int,
) -> dict[str, dict[str, object]]:
    values = {path: copy.deepcopy(dict(value)) for path, value in SUPPORT_ARTIFACTS.items()}
    values["training/training_policy.json"] = {
        "schema_id": "runtime.v3.phase10.training_policy.v1",
        "backend_authority": "untrusted_external_only",
        "gpu_training_permitted": True,
        "authoritative_evaluation_permitted": False,
        "objective": "sparse_transition_squared_logit_v1",
        "status": "trained_sparse_transition_reference",
    }
    values["training/optimizer_state.json"] = {
        "schema_id": "runtime.v3.phase10.optimizer_state.v1",
        "optimizer": "sgd",
        "learning_rate_numerator": 1,
        "learning_rate_denominator": 1,
        "momentum_numerator": 0,
        "momentum_denominator": 1,
        "step": optimizer_step,
        "training_report_hash": training_report_hash,
        "status": "untrusted_worker_output_validated",
    }
    values["training/data_curriculum.json"] = {
        "schema_id": "runtime.v3.phase10.data_curriculum.v1",
        "task_class": "lean_theorem_completion_v1",
        "training_examples": training_examples,
        "heldout_task_ids_visible": False,
        "heldout_prompts_visible": False,
        "heldout_reference_answers_visible": False,
        "status": "frozen_training_partition",
    }
    values["policies/verification_policy.json"] = {
        "schema_id": "runtime.v3.phase10.verification_policy.v1",
        "task_verifier": "pinned_lean_theorem_verifier_v1",
        "candidate_self_report_authoritative": False,
        "authoritative_inference_profile": "sparse_last_token_transition_v1",
        "distribution_normalization": "exact_dyadic_logit_v1",
        "greedy_tie_break": "lowest_token_id",
    }
    values["self_model/manifest.json"] = {
        "schema_id": "runtime.v3.phase10.self_model.v1",
        "declared_model_family": "compact_decoder_only_transformer_v1",
        "phase": 10,
        "claim": "selected_sparse_language_model",
        "full_native_float_transformer_equivalence_claimed": False,
    }
    values["runtime/resource_measurement.json"] = {
        "schema_id": "runtime.v3.phase10.resource_measurement.v1",
        "base_parameter_count": 13_195_840,
        "training_invocations": 1,
        "generator_invocations": 0,
        "replay_invocations": 0,
    }
    return values


def _support_hashes(values: Mapping[str, Mapping[str, object]]) -> dict[str, str]:
    return {
        SUPPORT_HASH_FIELD_BY_PATH[path]: canonical_json_hash(value)
        for path, value in values.items()
    }


def _rewrite_support(root: Path, values: Mapping[str, Mapping[str, object]]) -> None:
    if set(values) != set(SUPPORT_HASH_FIELD_BY_PATH):
        raise SchemaValidationError("phase10.learned_support", "support file set mismatch")
    for path, value in values.items():
        _overwrite_json(root / path, value)


def _rebuild_tensor_manifest(root: Path, old: TensorManifest) -> TensorManifest:
    records = tuple(
        TensorRecord(spec=record.spec, sha256=_file_sha256(root / record.spec.path))
        for record in old.records
    )
    result = TensorManifest(
        architecture_hash=old.architecture_hash,
        records=records,
        parameter_count=old.parameter_count,
    )
    _overwrite_json(root / TENSOR_MANIFEST_PATH, result.serialized_json())
    return result


def _finalize_learned_package(
    root: Path,
    *,
    package_id: str,
    parent_package_id: str | None,
    optimizer_step: int,
    training_report_hash: str,
    training_examples: int,
) -> ModelPackageManifest:
    old_manifest, architecture, tokenizer, old_tensors, _ = load_package_components(root)
    del old_manifest
    tensors = _rebuild_tensor_manifest(root, old_tensors)
    adapter = empty_adapter_manifest(architecture, tensors.weights_tree_hash)
    _overwrite_json(root / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
    support = _learned_support_artifacts(
        optimizer_step=optimizer_step,
        training_report_hash=training_report_hash,
        training_examples=training_examples,
    )
    _rewrite_support(root, support)
    if (root / PACKAGE_MANIFEST_PATH).exists():
        (root / PACKAGE_MANIFEST_PATH).unlink()
    payload_hash = _payload_tree_hash(root)
    manifest = _manifest_from_components(
        package_id=package_id,
        parent_package_id=parent_package_id,
        architecture=architecture,
        tokenizer=tokenizer,
        tensors=tensors,
        adapter=adapter,
        support_hashes=_support_hashes(support),
        payload_tree_hash=payload_hash,
    )
    _overwrite_json(root / PACKAGE_MANIFEST_PATH, manifest.to_json())
    return manifest


def build_sparse_predecessor_package(
    output_root: Path,
    *,
    training_report_hash: str,
) -> ModelPackageManifest:
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"learned predecessor already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-learned-base-", dir=resolved.parent) as temporary:
        staging = Path(temporary) / "package"
        build_reference_predecessor_package(staging)
        apply_sparse_profile(staging, PROTECTED_CHAIN)
        manifest = _finalize_learned_package(
            staging,
            package_id="phase10-learned-predecessor",
            parent_package_id=None,
            optimizer_step=1,
            training_report_hash=training_report_hash,
            training_examples=1,
        )
        os.replace(staging, resolved)
    return manifest


def build_sparse_candidate_package(
    predecessor_root: Path,
    output_root: Path,
    *,
    transition_tensor_bytes: bytes,
    training_report_hash: str,
    transition_pairs: Sequence[tuple[int, int]],
) -> ModelPackageManifest:
    predecessor = predecessor_root.resolve(strict=True)
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"learned candidate already exists: {resolved}")
    predecessor_manifest = load_package_manifest(predecessor)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-learned-candidate-", dir=resolved.parent) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(predecessor, staging, symlinks=False)
        tensor_path = transition_tensor_path(staging)
        if len(transition_tensor_bytes) != tensor_path.stat().st_size:
            raise SchemaValidationError(
                "phase10.learned_candidate.transition_tensor", "tensor byte length mismatch"
            )
        tensor_path.write_bytes(transition_tensor_bytes)
        manifest = _finalize_learned_package(
            staging,
            package_id="phase10-learned-candidate",
            parent_package_id=predecessor_manifest.package_id,
            optimizer_step=2,
            training_report_hash=training_report_hash,
            training_examples=3,
        )
        profile = validate_sparse_profile(staging, transition_pairs)
        if profile["accepted"] is not True:
            raise SchemaValidationError(
                "phase10.learned_candidate.sparse_profile", "candidate profile is invalid"
            )
        os.replace(staging, resolved)
    return manifest


def validate_learned_package(
    package_root: Path,
    transition_pairs: Sequence[tuple[int, int]],
) -> dict[str, object]:
    root = package_root.resolve(strict=True)
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(root)
    failures: list[str] = []
    if manifest.payload_tree_hash != _payload_tree_hash(root):
        failures.append("payload_tree_hash_mismatch")
    if manifest.architecture_hash != architecture.architecture_hash:
        failures.append("architecture_hash_mismatch")
    if manifest.tokenizer_manifest_hash != tokenizer.manifest_hash:
        failures.append("tokenizer_manifest_hash_mismatch")
    if manifest.tensor_manifest_hash != tensors.manifest_hash:
        failures.append("tensor_manifest_hash_mismatch")
    if manifest.weights_tree_hash != tensors.weights_tree_hash:
        failures.append("weights_tree_hash_mismatch")
    if manifest.adapter_manifest_hash != adapter.manifest_hash:
        failures.append("adapter_manifest_hash_mismatch")
    if manifest.model_identity_hash != manifest.model_identity().model_identity_hash:
        failures.append("model_identity_hash_mismatch")

    support_values: dict[str, object] = {}
    for path, field_name in SUPPORT_HASH_FIELD_BY_PATH.items():
        value = load_json_strict((root / path).read_bytes(), require_canonical=True)
        support_values[path] = value
        if getattr(manifest, field_name) != canonical_json_hash(value):
            failures.append(f"support_hash_mismatch:{path}")
    curriculum = support_values["training/data_curriculum.json"]
    if not isinstance(curriculum, dict) or any(
        curriculum.get(name) is not False
        for name in (
            "heldout_task_ids_visible",
            "heldout_prompts_visible",
            "heldout_reference_answers_visible",
        )
    ):
        failures.append("heldout_isolation_policy_failed")
    verification = support_values["policies/verification_policy.json"]
    if not isinstance(verification, dict) or verification.get("authoritative_inference_profile") != "sparse_last_token_transition_v1":
        failures.append("inference_policy_mismatch")

    profile = validate_sparse_profile(root, transition_pairs)
    if profile["accepted"] is not True:
        failures.extend(str(item) for item in profile["failures"])

    expected_files = {
        ARCHITECTURE_PATH,
        TOKENIZER_MANIFEST_PATH,
        TENSOR_MANIFEST_PATH,
        ADAPTER_MANIFEST_PATH,
        PACKAGE_MANIFEST_PATH,
        "model/tokenizer/tokenizer.bin",
        "model/tokenizer/vocabulary.json",
        *SUPPORT_HASH_FIELD_BY_PATH.keys(),
        *(record.spec.path for record in tensors.records),
        *(record.spec.path for record in adapter.records),
    }
    observed_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if observed_files != expected_files:
        failures.append("package_file_set_mismatch")

    content = {
        "schema_id": "runtime.v3.phase10.learned_package_report.v1",
        "package_hash": manifest.package_hash,
        "model_identity_hash": manifest.model_identity_hash,
        "sparse_profile_report_hash": profile["report_hash"],
        "failures": sorted(set(failures)),
        "accepted": not failures,
    }
    report = dict(content)
    report["report_hash"] = canonical_json_hash(content)
    return report


def transition_tensor_record(package_root: Path) -> TensorRecord:
    _, _, _, tensors, _ = load_package_components(package_root.resolve(strict=True))
    for record in tensors.records:
        if record.spec.name == ATTN_OUTPUT_TENSOR:
            return record
    raise SchemaValidationError("phase10.learned_package", "transition tensor is absent")


__all__ = [
    "build_sparse_candidate_package",
    "build_sparse_predecessor_package",
    "transition_tensor_record",
    "validate_learned_package",
]
