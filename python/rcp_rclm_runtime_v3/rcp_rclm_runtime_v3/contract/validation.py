from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.contract.records import (
    ALL_COMPONENT_TARGETS,
    HeldoutAccessPolicy,
    LearnedCertificatePacket,
    LearnedRCLMState,
    LearnedRCLMUpdate,
    SELECTED_MODEL_FAMILY,
    SELECTED_TASK_CLASS,
)

ReasonCode = Literal[
    "PHASE9_ACCEPT",
    "PHASE9_STATE_BINDING_FAILED",
    "PHASE9_PARENT_BINDING_FAILED",
    "PHASE9_UPDATE_BINDING_FAILED",
    "PHASE9_COMPONENT_CHANGE_MISMATCH",
    "PHASE9_FRONTIER_RETENTION_FAILED",
    "PHASE9_FRONTIER_EXPANSION_FAILED",
    "PHASE9_PROTECTED_FRONTIER_FAILED",
    "PHASE9_CERTIFICATION_FAILED",
    "PHASE9_HELDOUT_POLICY_FAILED",
    "PHASE9_HELDOUT_ISOLATION_FAILED",
    "PHASE9_SELF_HOSTING_BINDING_FAILED",
    "PHASE9_CERTIFICATE_BINDING_FAILED",
    "PHASE9_TASK_CLASS_MISMATCH",
    "PHASE9_MODEL_FAMILY_MISMATCH",
]

REPORT_SCHEMA_ID: Final[str] = "runtime.v3.phase9.transition_report.v1"


@dataclass(frozen=True, slots=True)
class Phase9TransitionReport:
    accepted: bool
    reason_codes: Sequence[ReasonCode]
    predecessor_state_hash: str
    candidate_state_hash: str
    update_hash: str
    certificate_hash: str
    heldout_access_policy_hash: str
    retained_task_ids: Sequence[str]
    new_task_ids: Sequence[str]
    changed_components: Sequence[str]
    semantic_report_hash: str

    schema_id: ClassVar[str] = REPORT_SCHEMA_ID

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "predecessor_state_hash": self.predecessor_state_hash,
            "candidate_state_hash": self.candidate_state_hash,
            "update_hash": self.update_hash,
            "certificate_hash": self.certificate_hash,
            "heldout_access_policy_hash": self.heldout_access_policy_hash,
            "retained_task_ids": list(self.retained_task_ids),
            "new_task_ids": list(self.new_task_ids),
            "changed_components": list(self.changed_components),
        }

    def to_json(self) -> dict[str, object]:
        result = self.content_json()
        result["semantic_report_hash"] = self.semantic_report_hash
        return result


def _ordered(values: set[str]) -> Sequence[str]:
    return tuple(sorted(values, key=lambda item: item.encode("utf-8")))


def validate_phase9_transition(
    predecessor: LearnedRCLMState,
    update: LearnedRCLMUpdate,
    candidate: LearnedRCLMState,
    certificate: LearnedCertificatePacket,
    heldout_policy: HeldoutAccessPolicy,
) -> Phase9TransitionReport:
    reasons: list[ReasonCode] = []

    predecessor_hash = predecessor.state_hash
    candidate_hash = candidate.state_hash
    update_hash = update.update_hash
    certificate_hash = certificate.certificate_hash
    policy_hash = heldout_policy.policy_hash

    if (
        predecessor.selected_task_class != SELECTED_TASK_CLASS
        or candidate.selected_task_class != SELECTED_TASK_CLASS
    ):
        reasons.append("PHASE9_TASK_CLASS_MISMATCH")
    if (
        predecessor.model.model_family != SELECTED_MODEL_FAMILY
        or candidate.model.model_family != SELECTED_MODEL_FAMILY
    ):
        reasons.append("PHASE9_MODEL_FAMILY_MISMATCH")

    if (
        update.predecessor_state_hash != predecessor_hash
        or update.candidate_state_hash != candidate_hash
    ):
        reasons.append("PHASE9_STATE_BINDING_FAILED")
    if candidate.parent_package_id != predecessor.package_id:
        reasons.append("PHASE9_PARENT_BINDING_FAILED")

    operation_targets = {operation.target for operation in update.operations}
    actual_changed_targets = {
        target
        for target in ALL_COMPONENT_TARGETS
        if predecessor.component_hash(target) != candidate.component_hash(target)
    }
    if operation_targets != actual_changed_targets:
        reasons.append("PHASE9_COMPONENT_CHANGE_MISMATCH")
    else:
        for operation in update.operations:
            if (
                operation.before_hash != predecessor.component_hash(operation.target)
                or operation.after_hash != candidate.component_hash(operation.target)
            ):
                reasons.append("PHASE9_UPDATE_BINDING_FAILED")
                break

    before_frontier = set(predecessor.capability_frontier.task_ids)
    after_frontier = set(candidate.capability_frontier.task_ids)
    retained = before_frontier & after_frontier
    new_tasks = after_frontier - before_frontier

    if not before_frontier.issubset(after_frontier):
        reasons.append("PHASE9_FRONTIER_RETENTION_FAILED")
    if not new_tasks or len(after_frontier) <= len(before_frontier):
        reasons.append("PHASE9_FRONTIER_EXPANSION_FAILED")

    protected = set(certificate.protected_task_ids)
    if protected != before_frontier or not protected.issubset(after_frontier):
        reasons.append("PHASE9_PROTECTED_FRONTIER_FAILED")
    if set(certificate.new_task_ids) != new_tasks:
        reasons.append("PHASE9_CERTIFICATE_BINDING_FAILED")

    candidate_tasks = candidate.task_ledger.task_by_id
    candidate_certifications = candidate.task_ledger.certification_by_task_id
    if any(task_id not in candidate_certifications for task_id in after_frontier):
        reasons.append("PHASE9_CERTIFICATION_FAILED")
    if any(
        candidate_certifications[task_id].model_identity_hash
        != candidate.model.model_identity_hash
        for task_id in after_frontier
        if task_id in candidate_certifications
    ):
        reasons.append("PHASE9_CERTIFICATION_FAILED")

    if heldout_policy.selected_task_class != SELECTED_TASK_CLASS:
        reasons.append("PHASE9_HELDOUT_POLICY_FAILED")
    if any(
        task_id not in candidate_tasks or candidate_tasks[task_id].partition != "heldout"
        for task_id in new_tasks
    ):
        reasons.append("PHASE9_HELDOUT_ISOLATION_FAILED")

    certificate_bindings = (
        certificate.transition_id == update.transition_id,
        certificate.predecessor_state_hash == predecessor_hash,
        certificate.candidate_state_hash == candidate_hash,
        certificate.update_hash == update_hash,
        certificate.capability_frontier_before_hash
        == predecessor.capability_frontier.frontier_hash,
        certificate.capability_frontier_after_hash
        == candidate.capability_frontier.frontier_hash,
        certificate.heldout_access_policy_hash == policy_hash,
    )
    if not all(certificate_bindings):
        reasons.append("PHASE9_CERTIFICATE_BINDING_FAILED")

    self_hosting_bindings = (
        certificate.active_generator_hash
        == predecessor.policies.generator_policy_hash,
        certificate.active_planner_hash == predecessor.policies.planner_policy_hash,
        certificate.proposal_protocol_hash
        == predecessor.self_hosting.proposal_protocol_hash,
        predecessor.self_hosting.generator_component_hash
        == predecessor.policies.generator_policy_hash,
        predecessor.self_hosting.planner_component_hash
        == predecessor.policies.planner_policy_hash,
        candidate.self_hosting.generator_component_hash
        == candidate.policies.generator_policy_hash,
        candidate.self_hosting.planner_component_hash
        == candidate.policies.planner_policy_hash,
    )
    if not all(self_hosting_bindings):
        reasons.append("PHASE9_SELF_HOSTING_BINDING_FAILED")

    if (
        "generator_policy" in actual_changed_targets
        and predecessor.self_hosting.generator_component_hash
        == candidate.self_hosting.generator_component_hash
    ):
        reasons.append("PHASE9_SELF_HOSTING_BINDING_FAILED")
    if (
        "planner_policy" in actual_changed_targets
        and predecessor.self_hosting.planner_component_hash
        == candidate.self_hosting.planner_component_hash
    ):
        reasons.append("PHASE9_SELF_HOSTING_BINDING_FAILED")

    unique_reasons = tuple(dict.fromkeys(reasons))
    accepted = not unique_reasons
    semantic_reasons: Sequence[ReasonCode] = (
        ("PHASE9_ACCEPT",) if accepted else unique_reasons
    )
    content = {
        "schema_id": REPORT_SCHEMA_ID,
        "accepted": accepted,
        "reason_codes": list(semantic_reasons),
        "predecessor_state_hash": predecessor_hash,
        "candidate_state_hash": candidate_hash,
        "update_hash": update_hash,
        "certificate_hash": certificate_hash,
        "heldout_access_policy_hash": policy_hash,
        "retained_task_ids": list(_ordered(retained)),
        "new_task_ids": list(_ordered(new_tasks)),
        "changed_components": list(_ordered(actual_changed_targets)),
    }
    return Phase9TransitionReport(
        accepted=accepted,
        reason_codes=semantic_reasons,
        predecessor_state_hash=predecessor_hash,
        candidate_state_hash=candidate_hash,
        update_hash=update_hash,
        certificate_hash=certificate_hash,
        heldout_access_policy_hash=policy_hash,
        retained_task_ids=_ordered(retained),
        new_task_ids=_ordered(new_tasks),
        changed_components=_ordered(actual_changed_targets),
        semantic_report_hash=canonical_json_hash(content),
    )


__all__ = [
    "Phase9TransitionReport",
    "REPORT_SCHEMA_ID",
    "ReasonCode",
    "validate_phase9_transition",
]
