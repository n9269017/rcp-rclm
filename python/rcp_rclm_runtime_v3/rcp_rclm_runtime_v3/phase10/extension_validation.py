from __future__ import annotations

from pathlib import Path

from rcp_rclm_runtime.errors import RuntimeValidationError

from rcp_rclm_runtime_v3.contract.state import ModelIdentity
from rcp_rclm_runtime_v3.phase10.adapters import ZeroAdapterVerification, verify_adapter_manifest
from rcp_rclm_runtime_v3.phase10.constants import BASE_PARAMETER_COUNT, EXTENDED_PARAMETER_COUNT
from rcp_rclm_runtime_v3.phase10.package import ModelPackageManifest, load_package_components
from rcp_rclm_runtime_v3.phase10.package_validation import validate_model_package
from rcp_rclm_runtime_v3.phase10.reports import (
    ConservativeExtensionReport,
    ExtensionReasonCode,
    extension_report,
    ordered_reason_codes,
)


def validate_conservative_extension(
    predecessor_root: Path, successor_root: Path
) -> ConservativeExtensionReport:
    reasons: list[ExtensionReasonCode] = []
    predecessor_report = validate_model_package(predecessor_root)
    successor_report = validate_model_package(successor_root)
    if not predecessor_report.accepted:
        reasons.append("PHASE10_PREDECESSOR_INVALID")
    if not successor_report.accepted:
        reasons.append("PHASE10_SUCCESSOR_INVALID")
    try:
        predecessor, _, predecessor_tok, predecessor_tensors, predecessor_adapter = (
            load_package_components(predecessor_root)
        )
        successor, successor_arch, successor_tok, successor_tensors, successor_adapter = (
            load_package_components(successor_root)
        )
    except (OSError, RuntimeValidationError, ValueError):
        zero = "0" * 64
        false_verification = ZeroAdapterVerification(False, False, False)
        return extension_report(
            reasons=ordered_reason_codes(reasons),
            predecessor_package_hash=zero,
            successor_package_hash=zero,
            predecessor_model_identity_hash=zero,
            successor_model_identity_hash=zero,
            architecture_unchanged=False,
            base_weights_unchanged=False,
            tokenizer_unchanged=False,
            support_policies_unchanged=False,
            zero_verification=false_verification,
            model_hash_changed=False,
            recovery_exact=False,
            parameter_count_extended=False,
        )

    if successor.parent_package_id != predecessor.package_id:
        reasons.append("PHASE10_PARENT_BINDING_FAILED")
    architecture_unchanged = predecessor.architecture_hash == successor.architecture_hash
    base_weights_unchanged = (
        predecessor.weights_tree_hash == successor.weights_tree_hash
        and predecessor.tensor_manifest_hash == successor.tensor_manifest_hash
        and predecessor_tensors == successor_tensors
    )
    if not architecture_unchanged or not base_weights_unchanged:
        reasons.append("PHASE10_BASE_MODEL_CHANGED")
    tokenizer_unchanged = (
        predecessor.tokenizer_hash == successor.tokenizer_hash
        and predecessor.vocabulary_hash == successor.vocabulary_hash
        and predecessor.tokenizer_manifest_hash == successor.tokenizer_manifest_hash
        and predecessor_tok == successor_tok
    )
    if not tokenizer_unchanged:
        reasons.append("PHASE10_TOKENIZER_CHANGED")
    excluded = {
        "architecture_hash",
        "tokenizer_manifest_hash",
        "tokenizer_hash",
        "vocabulary_hash",
        "tensor_manifest_hash",
        "weights_tree_hash",
        "adapter_manifest_hash",
        "model_identity_hash",
        "payload_tree_hash",
    }
    support_unchanged = all(
        getattr(predecessor, field) == getattr(successor, field)
        for field in ModelPackageManifest.hash_field_names()
        if field not in excluded
    )
    if not support_unchanged:
        reasons.append("PHASE10_SUPPORT_POLICY_CHANGED")
    try:
        zero_verification = verify_adapter_manifest(
            successor_root, successor_arch, successor_tensors.weights_tree_hash, successor_adapter
        )
    except (OSError, RuntimeValidationError):
        zero_verification = ZeroAdapterVerification(False, False, False)
    if not (
        predecessor_adapter.status == "absent"
        and successor_adapter.status == "zero_output_extension"
        and zero_verification.accepted
    ):
        reasons.append("PHASE10_ADAPTER_NOT_CONSERVATIVE")
    model_hash_changed = predecessor.model_identity_hash != successor.model_identity_hash
    if not model_hash_changed:
        reasons.append("PHASE10_MODEL_HASH_UNCHANGED")
    recovered = ModelIdentity(
        model_family=predecessor.model_identity().model_family,
        architecture_hash=successor.architecture_hash,
        weights_tree_hash=successor.weights_tree_hash,
        adapter_manifest_hash=predecessor.adapter_manifest_hash,
        tensor_manifest_hash=successor.tensor_manifest_hash,
        tokenizer_hash=successor.tokenizer_hash,
        vocabulary_hash=successor.vocabulary_hash,
        parameter_count=BASE_PARAMETER_COUNT,
    )
    recovery_exact = recovered.model_identity_hash == predecessor.model_identity_hash
    if not recovery_exact:
        reasons.append("PHASE10_RECOVERY_FAILED")
    parameter_count_extended = (
        predecessor.parameter_count == BASE_PARAMETER_COUNT
        and successor.parameter_count == EXTENDED_PARAMETER_COUNT
    )
    if not parameter_count_extended:
        reasons.append("PHASE10_PARAMETER_COUNT_FAILED")
    return extension_report(
        reasons=ordered_reason_codes(reasons),
        predecessor_package_hash=predecessor.package_hash,
        successor_package_hash=successor.package_hash,
        predecessor_model_identity_hash=predecessor.model_identity_hash,
        successor_model_identity_hash=successor.model_identity_hash,
        architecture_unchanged=architecture_unchanged,
        base_weights_unchanged=base_weights_unchanged,
        tokenizer_unchanged=tokenizer_unchanged,
        support_policies_unchanged=support_unchanged,
        zero_verification=zero_verification,
        model_hash_changed=model_hash_changed,
        recovery_exact=recovery_exact,
        parameter_count_extended=parameter_count_extended,
    )


__all__ = ["validate_conservative_extension"]
