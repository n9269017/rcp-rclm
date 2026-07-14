from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.schema.verdict import FrozenHashMap, ReasonCode
from rcp_rclm_runtime.checker.policy import CHECKER_POLICY_HASH, CLAIM_BOUNDARY_HASH
from rcp_rclm_runtime.checker.records import (
    ComponentResultRecord,
    Phase3CheckerReport,
    Phase3CheckerRequest,
)


def _basic_artifact_hashes(request: Phase3CheckerRequest) -> FrozenHashMap:
    return FrozenHashMap.from_mapping(
        {
            "candidate": canonical_json_hash(request.candidate.to_json()),
            "certificate": canonical_json_hash(request.certificate.to_json()),
            "checker_policy": CHECKER_POLICY_HASH,
            "evaluation_evidence": canonical_json_hash(
                request.evaluation_evidence.to_json()
            ),
            "lean_bridge_report": request.lean_bridge_report.report_hash,
            "predecessor": canonical_json_hash(request.predecessor.to_json()),
            "protected_distinctions": canonical_json_hash(
                [item.to_json() for item in request.protected_distinctions]
            ),
            "request": canonical_json_hash(request.to_json()),
            "resource_record": canonical_json_hash(request.resource_record.to_json()),
            "trust_anchor": canonical_json_hash(request.trust_anchor.to_json()),
        },
        "artifact_hashes",
    )


def _complete_artifact_hashes(
    request: Phase3CheckerRequest,
    *,
    mapping_evidence: object,
    lean_packet: object,
) -> FrozenHashMap:
    values = _basic_artifact_hashes(request).to_json()
    values.update(
        {
            "claim_boundary": CLAIM_BOUNDARY_HASH,
            "lean_packet": canonical_json_hash(lean_packet),
            "refinement_mapping": canonical_json_hash(
                getattr(mapping_evidence, "to_json")()
            ),
        }
    )
    return FrozenHashMap.from_mapping(values, "artifact_hashes")


def _early_report(
    *,
    request: Phase3CheckerRequest,
    structural_result: ComponentResultRecord,
    artifact_hashes: FrozenHashMap,
) -> Phase3CheckerReport:
    blank = _blank_component()
    reasons = _ordered_reason_codes((structural_result,))
    verdict = "reject" if structural_result.status == "fail" else "indeterminate"
    return Phase3CheckerReport(
        transition_id=request.transition_id,
        verdict=verdict,
        reason_codes=reasons,
        structural_result=structural_result,
        typed_successor_result=blank,
        computed_residuals=(),
        residual_result=blank,
        metric_bounds=None,
        evaluation_result=blank,
        protected_nonloss_result=blank,
        recovery_result=blank,
        invariant_result=blank,
        containment_result=blank,
        progress_result=blank,
        strict_witness_result=blank,
        trust_result=blank,
        resource_result=blank,
        domain_result=blank,
        refinement_result=blank,
        monitor_result=blank,
        lean_bridge_result=blank,
        artifact_hashes=artifact_hashes,
        checker_policy_hash=CHECKER_POLICY_HASH,
    )


def _exception_report(
    *,
    transition_id: str,
    reason: ReasonCode,
    detail: Exception,
    artifact_hashes: Mapping[str, str],
) -> Phase3CheckerReport:
    error_component = ComponentResultRecord.from_evidence(
        "fail",
        (reason,),
        {
            "error_type": type(detail).__name__,
            "error_hash": sha256_hex(str(detail).encode("utf-8")),
        },
    )
    blank = _blank_component()
    return Phase3CheckerReport(
        transition_id=transition_id,
        verdict="reject",
        reason_codes=(reason,),
        structural_result=error_component,
        typed_successor_result=blank,
        computed_residuals=(),
        residual_result=blank,
        metric_bounds=None,
        evaluation_result=blank,
        protected_nonloss_result=blank,
        recovery_result=blank,
        invariant_result=blank,
        containment_result=blank,
        progress_result=blank,
        strict_witness_result=blank,
        trust_result=blank,
        resource_result=blank,
        domain_result=blank,
        refinement_result=blank,
        monitor_result=blank,
        lean_bridge_result=blank,
        artifact_hashes=FrozenHashMap.from_mapping(
            artifact_hashes,
            "artifact_hashes",
        ),
        checker_policy_hash=CHECKER_POLICY_HASH,
    )


def _blank_component() -> ComponentResultRecord:
    return ComponentResultRecord.from_evidence(
        "not_evaluated",
        (),
        {"evaluated": False},
    )


def _derive_verdict(components: Iterable[ComponentResultRecord]) -> str:
    statuses = tuple(component.status for component in components)
    if "fail" in statuses:
        return "reject"
    if "indeterminate" in statuses or "not_evaluated" in statuses:
        return "indeterminate"
    return "accept"


def _ordered_reason_codes(
    components: Iterable[ComponentResultRecord],
) -> Sequence[ReasonCode]:
    ordered: list[ReasonCode] = []
    for component in components:
        for reason in component.reason_codes:
            if reason not in ordered:
                ordered.append(reason)
    return tuple(ordered)


def _transition_id_from_untrusted(value: object) -> str:
    if isinstance(value, Mapping):
        transition_id = value.get("transition_id")
        if isinstance(transition_id, str) and transition_id:
            return transition_id
    return "unparsed"
