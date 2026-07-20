from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError, SchemaValidationError

from rcp_rclm_runtime_v3.phase10.adapters import verify_adapter_manifest
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    ARCHITECTURE_PATH,
    PACKAGE_MANIFEST_PATH,
    SUPPORT_ARTIFACTS,
    TENSOR_MANIFEST_PATH,
    TOKENIZER_BYTES_PATH,
    TOKENIZER_MANIFEST_PATH,
    VOCABULARY_PATH,
    load_package_components,
    recompute_payload_tree_hash,
    verify_support_artifacts,
)
from rcp_rclm_runtime_v3.phase10.reports import (
    PackageReasonCode,
    Phase10PackageReport,
    empty_package_report,
    ordered_reason_codes,
    package_report,
)
from rcp_rclm_runtime_v3.phase10.tensors import verify_base_tensor_manifest
from rcp_rclm_runtime_v3.phase10.tokenizer import tokenizer_bytes, vocabulary_json


def package_files(root: Path) -> Sequence[str]:
    files: list[str] = []
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_root)
        if any((current / name).is_symlink() for name in directory_names):
            raise SchemaValidationError("phase10.package", "symlink directory is forbidden")
        for file_name in file_names:
            file_path = current / file_name
            if file_path.is_symlink():
                raise SchemaValidationError("phase10.package", "symlink file is forbidden")
            files.append(file_path.relative_to(root).as_posix())
    return tuple(sorted(files, key=lambda item: item.encode("utf-8")))


def expected_package_files(
    tensor_paths: Sequence[str], adapter_paths: Sequence[str]
) -> Sequence[str]:
    files = {
        ARCHITECTURE_PATH,
        TOKENIZER_BYTES_PATH,
        VOCABULARY_PATH,
        TOKENIZER_MANIFEST_PATH,
        TENSOR_MANIFEST_PATH,
        ADAPTER_MANIFEST_PATH,
        PACKAGE_MANIFEST_PATH,
        *SUPPORT_ARTIFACTS.keys(),
        *tensor_paths,
        *adapter_paths,
    }
    return tuple(sorted(files, key=lambda item: item.encode("utf-8")))


def validate_model_package(package_root: Path) -> Phase10PackageReport:
    reasons: list[PackageReasonCode] = []
    try:
        root = package_root.resolve(strict=True)
        manifest, architecture, tokenizer, tensors, adapter = load_package_components(root)
    except (OSError, RuntimeValidationError, ValueError):
        return empty_package_report("PHASE10_PACKAGE_PARSE_FAILED")

    if manifest.architecture_hash != architecture.architecture_hash:
        reasons.append("PHASE10_ARCHITECTURE_BINDING_FAILED")
    try:
        vocabulary = load_json_strict((root / VOCABULARY_PATH).read_bytes(), require_canonical=True)
        tokenizer_ok = (
            (root / TOKENIZER_BYTES_PATH).read_bytes() == tokenizer_bytes()
            and vocabulary == vocabulary_json()
            and manifest.tokenizer_manifest_hash == tokenizer.manifest_hash
            and manifest.tokenizer_hash == tokenizer.tokenizer_bytes_hash
            and manifest.vocabulary_hash == tokenizer.vocabulary_hash
        )
        if not tokenizer_ok:
            reasons.append("PHASE10_TOKENIZER_BINDING_FAILED")
    except (OSError, RuntimeValidationError):
        reasons.append("PHASE10_TOKENIZER_BINDING_FAILED")
    try:
        verify_base_tensor_manifest(root, architecture, tensors)
        if (
            manifest.tensor_manifest_hash != tensors.manifest_hash
            or manifest.weights_tree_hash != tensors.weights_tree_hash
        ):
            reasons.append("PHASE10_TENSOR_BINDING_FAILED")
    except (OSError, RuntimeValidationError):
        reasons.append("PHASE10_TENSOR_BINDING_FAILED")
    try:
        adapter_check = verify_adapter_manifest(root, architecture, tensors.weights_tree_hash, adapter)
        if (
            manifest.adapter_manifest_hash != adapter.manifest_hash
            or (adapter.status == "zero_output_extension" and not adapter_check.accepted)
        ):
            reasons.append("PHASE10_ADAPTER_BINDING_FAILED")
    except (OSError, RuntimeValidationError):
        reasons.append("PHASE10_ADAPTER_BINDING_FAILED")
    try:
        verify_support_artifacts(root, manifest)
    except (OSError, RuntimeValidationError):
        reasons.append("PHASE10_SUPPORT_BINDING_FAILED")
    if manifest.model_identity().model_identity_hash != manifest.model_identity_hash:
        reasons.append("PHASE10_MODEL_IDENTITY_FAILED")
    try:
        payload_hash = recompute_payload_tree_hash(root)
        if payload_hash != manifest.payload_tree_hash:
            reasons.append("PHASE10_PAYLOAD_TREE_FAILED")
    except (OSError, RuntimeValidationError):
        payload_hash = "0" * 64
        reasons.append("PHASE10_PAYLOAD_TREE_FAILED")
    try:
        files = package_files(root)
        expected = expected_package_files(
            tuple(record.spec.path for record in tensors.records),
            tuple(record.spec.path for record in adapter.records),
        )
        if files != expected:
            reasons.append("PHASE10_PACKAGE_FILE_SET_FAILED")
        total_size = sum((root / path).stat().st_size for path in files)
    except (OSError, RuntimeValidationError):
        files = ()
        total_size = 0
        reasons.append("PHASE10_PACKAGE_FILE_SET_FAILED")
    unique = ordered_reason_codes(reasons)
    return package_report(
        accepted=not unique,
        reasons=unique,
        package_id=manifest.package_id,
        package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        architecture_hash=manifest.architecture_hash,
        weights_tree_hash=manifest.weights_tree_hash,
        adapter_manifest_hash=manifest.adapter_manifest_hash,
        payload_tree_hash=payload_hash,
        parameter_count=manifest.parameter_count,
        file_count=len(files),
        total_size_bytes=total_size,
    )


__all__ = ["expected_package_files", "package_files", "validate_model_package"]
