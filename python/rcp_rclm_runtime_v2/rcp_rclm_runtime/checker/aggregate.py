from __future__ import annotations

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, RuntimeValidationError
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.gates import (
    _lean_bridge_result,
    _refinement_result,
    _resource_result,
    _structural_result,
    _trust_result,
)
from rcp_rclm_runtime.checker.mathematical import compute_mathematical_obligations
from rcp_rclm_runtime.checker.policy import CHECKER_POLICY_HASH
from rcp_rclm_runtime.checker.records import Phase3CheckerReport, Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import core_certificate_name, scope_from_core_state
from rcp_rclm_runtime.checker.report_builders import (
    _basic_artifact_hashes,
    _complete_artifact_hashes,
    _derive_verdict,
    _early_report,
    _exception_report,
    _ordered_reason_codes,
    _transition_id_from_untrusted,
)


def check_transition(request: Phase3CheckerRequest) -> Phase3CheckerReport:
    input_hash_before = canonical_json_hash(request.to_json())
    try:
        report = _check_transition(request)
    except Exception as exc:
        report = _exception_report(
            transition_id=request.transition_id,
            reason=ReasonCode.INTERNAL_ERROR,
            detail=exc,
            artifact_hashes={
                "request": input_hash_before,
                "checker_policy": CHECKER_POLICY_HASH,
            },
        )
    input_hash_after = canonical_json_hash(request.to_json())
    if input_hash_after != input_hash_before:
        return _exception_report(
            transition_id=request.transition_id,
            reason=ReasonCode.INTERNAL_ERROR,
            detail=RuntimeError("checker input mutation detected"),
            artifact_hashes={
                "request_before": input_hash_before,
                "request_after": input_hash_after,
                "checker_policy": CHECKER_POLICY_HASH,
            },
        )
    return report


def check_transition_bytes(
    data: bytes,
    *,
    require_canonical: bool = True,
) -> Phase3CheckerReport:
    raw_hash = sha256_hex(data)
    try:
        value = load_json_strict(data, require_canonical=require_canonical)
    except CanonicalizationError as exc:
        return _exception_report(
            transition_id="unparsed",
            reason=ReasonCode.CANONICALIZATION_FAILED,
            detail=exc,
            artifact_hashes={
                "raw_input": raw_hash,
                "checker_policy": CHECKER_POLICY_HASH,
            },
        )
    try:
        request = Phase3CheckerRequest.from_json(value)
    except RuntimeValidationError as exc:
        return _exception_report(
            transition_id=_transition_id_from_untrusted(value),
            reason=ReasonCode.SCHEMA_MALFORMED,
            detail=exc,
            artifact_hashes={
                "raw_input": raw_hash,
                "parsed_input": canonical_json_hash(value),
                "checker_policy": CHECKER_POLICY_HASH,
            },
        )
    return check_transition(request)


def _check_transition(request: Phase3CheckerRequest) -> Phase3CheckerReport:
    certificate_scope, certificate_name = core_certificate_name(request.certificate)
    scope = scope_from_core_state(request.predecessor.core)
    structural_result = _structural_result(
        request,
        scope=scope,
        certificate_scope=certificate_scope,
    )
    basic_hashes = _basic_artifact_hashes(request)
    if structural_result.status != "pass":
        return _early_report(
            request=request,
            structural_result=structural_result,
            artifact_hashes=basic_hashes,
        )

    mathematical = compute_mathematical_obligations(
        request.predecessor,
        request.candidate,
        certificate_name,
        request.protected_distinctions,
        request.evaluation_evidence,
        request.resource_record.precision_bits,
    )
    trust_result = _trust_result(request, certificate_name=certificate_name)
    resource_result = _resource_result(request, certificate_name=certificate_name)
    refinement_result, mapping_evidence = _refinement_result(
        request,
        scope=scope,
        certificate_name=certificate_name,
        evaluation_result=mathematical.evaluation_result,
    )
    lean_result, lean_packet = _lean_bridge_result(request)
    artifact_hashes = _complete_artifact_hashes(
        request,
        mapping_evidence=mapping_evidence,
        lean_packet=lean_packet.to_json(),
    )

    components = (
        structural_result,
        mathematical.typed_successor_result,
        mathematical.residual_result,
        mathematical.evaluation_result,
        mathematical.protected_nonloss_result,
        mathematical.recovery_result,
        mathematical.invariant_result,
        mathematical.containment_result,
        mathematical.domain_result,
        mathematical.progress_result,
        mathematical.strict_witness_result,
        trust_result,
        resource_result,
        refinement_result,
        mathematical.monitor_result,
        lean_result,
    )
    reasons = _ordered_reason_codes(components)
    verdict = _derive_verdict(components)
    return Phase3CheckerReport(
        transition_id=request.transition_id,
        verdict=verdict,
        reason_codes=reasons,
        structural_result=structural_result,
        typed_successor_result=mathematical.typed_successor_result,
        computed_residuals=mathematical.residuals,
        residual_result=mathematical.residual_result,
        metric_bounds=mathematical.metric_bounds,
        evaluation_result=mathematical.evaluation_result,
        protected_nonloss_result=mathematical.protected_nonloss_result,
        recovery_result=mathematical.recovery_result,
        invariant_result=mathematical.invariant_result,
        containment_result=mathematical.containment_result,
        progress_result=mathematical.progress_result,
        strict_witness_result=mathematical.strict_witness_result,
        trust_result=trust_result,
        resource_result=resource_result,
        domain_result=mathematical.domain_result,
        refinement_result=refinement_result,
        monitor_result=mathematical.monitor_result,
        lean_bridge_result=lean_result,
        artifact_hashes=artifact_hashes,
        checker_policy_hash=CHECKER_POLICY_HASH,
    )
