from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase10.adapters import ZeroAdapterVerification
from rcp_rclm_runtime_v3.phase10.constants import EXTENSION_REPORT_SCHEMA_ID

ExtensionReasonCode = Literal[
    "PHASE10_EXTENSION_ACCEPT",
    "PHASE10_PREDECESSOR_INVALID",
    "PHASE10_SUCCESSOR_INVALID",
    "PHASE10_PARENT_BINDING_FAILED",
    "PHASE10_BASE_MODEL_CHANGED",
    "PHASE10_TOKENIZER_CHANGED",
    "PHASE10_SUPPORT_POLICY_CHANGED",
    "PHASE10_ADAPTER_NOT_CONSERVATIVE",
    "PHASE10_MODEL_HASH_UNCHANGED",
    "PHASE10_RECOVERY_FAILED",
    "PHASE10_PARAMETER_COUNT_FAILED",
]


@dataclass(frozen=True, slots=True)
class ConservativeExtensionReport:
    accepted: bool
    reason_codes: Sequence[ExtensionReasonCode]
    predecessor_package_hash: str
    successor_package_hash: str
    predecessor_model_identity_hash: str
    successor_model_identity_hash: str
    architecture_unchanged: bool
    base_weights_unchanged: bool
    tokenizer_unchanged: bool
    support_policies_unchanged: bool
    all_adapter_b_tensors_zero: bool
    at_least_one_adapter_a_tensor_nonzero: bool
    adapter_graph_exact: bool
    model_hash_changed: bool
    recovery_exact: bool
    parameter_count_extended: bool
    lean_theorem: str
    semantic_report_hash: str

    schema_id: ClassVar[str] = EXTENSION_REPORT_SCHEMA_ID

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "predecessor_package_hash": self.predecessor_package_hash,
            "successor_package_hash": self.successor_package_hash,
            "predecessor_model_identity_hash": self.predecessor_model_identity_hash,
            "successor_model_identity_hash": self.successor_model_identity_hash,
            "architecture_unchanged": self.architecture_unchanged,
            "base_weights_unchanged": self.base_weights_unchanged,
            "tokenizer_unchanged": self.tokenizer_unchanged,
            "support_policies_unchanged": self.support_policies_unchanged,
            "all_adapter_b_tensors_zero": self.all_adapter_b_tensors_zero,
            "at_least_one_adapter_a_tensor_nonzero": self.at_least_one_adapter_a_tensor_nonzero,
            "adapter_graph_exact": self.adapter_graph_exact,
            "model_hash_changed": self.model_hash_changed,
            "recovery_exact": self.recovery_exact,
            "parameter_count_extended": self.parameter_count_extended,
            "lean_theorem": self.lean_theorem,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["semantic_report_hash"] = self.semantic_report_hash
        return value


def extension_report(
    *,
    reasons: Sequence[ExtensionReasonCode],
    predecessor_package_hash: str,
    successor_package_hash: str,
    predecessor_model_identity_hash: str,
    successor_model_identity_hash: str,
    architecture_unchanged: bool,
    base_weights_unchanged: bool,
    tokenizer_unchanged: bool,
    support_policies_unchanged: bool,
    zero_verification: ZeroAdapterVerification,
    model_hash_changed: bool,
    recovery_exact: bool,
    parameter_count_extended: bool,
) -> ConservativeExtensionReport:
    accepted = not reasons
    report_reasons: Sequence[ExtensionReasonCode] = (
        ("PHASE10_EXTENSION_ACCEPT",) if accepted else tuple(reasons)
    )
    lean_theorem = "RcpRclmFormalCoreV3.Learned.lora_zero_output_preserves"
    content = {
        "schema_id": ConservativeExtensionReport.schema_id,
        "accepted": accepted,
        "reason_codes": list(report_reasons),
        "predecessor_package_hash": predecessor_package_hash,
        "successor_package_hash": successor_package_hash,
        "predecessor_model_identity_hash": predecessor_model_identity_hash,
        "successor_model_identity_hash": successor_model_identity_hash,
        "architecture_unchanged": architecture_unchanged,
        "base_weights_unchanged": base_weights_unchanged,
        "tokenizer_unchanged": tokenizer_unchanged,
        "support_policies_unchanged": support_policies_unchanged,
        "all_adapter_b_tensors_zero": zero_verification.all_b_tensors_zero,
        "at_least_one_adapter_a_tensor_nonzero": zero_verification.at_least_one_a_tensor_nonzero,
        "adapter_graph_exact": zero_verification.expected_tensor_graph,
        "model_hash_changed": model_hash_changed,
        "recovery_exact": recovery_exact,
        "parameter_count_extended": parameter_count_extended,
        "lean_theorem": lean_theorem,
    }
    return ConservativeExtensionReport(
        accepted=accepted,
        reason_codes=report_reasons,
        predecessor_package_hash=predecessor_package_hash,
        successor_package_hash=successor_package_hash,
        predecessor_model_identity_hash=predecessor_model_identity_hash,
        successor_model_identity_hash=successor_model_identity_hash,
        architecture_unchanged=architecture_unchanged,
        base_weights_unchanged=base_weights_unchanged,
        tokenizer_unchanged=tokenizer_unchanged,
        support_policies_unchanged=support_policies_unchanged,
        all_adapter_b_tensors_zero=zero_verification.all_b_tensors_zero,
        at_least_one_adapter_a_tensor_nonzero=zero_verification.at_least_one_a_tensor_nonzero,
        adapter_graph_exact=zero_verification.expected_tensor_graph,
        model_hash_changed=model_hash_changed,
        recovery_exact=recovery_exact,
        parameter_count_extended=parameter_count_extended,
        lean_theorem=lean_theorem,
        semantic_report_hash=canonical_json_hash(content),
    )


__all__ = [
    "ConservativeExtensionReport",
    "ExtensionReasonCode",
    "extension_report",
]
