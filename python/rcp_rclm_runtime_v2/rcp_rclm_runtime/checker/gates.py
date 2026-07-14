from __future__ import annotations

from rcp_rclm_runtime._version import FORMAL_SOURCE_COMMIT, LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.intervals import PRECISION_SCHEDULE
from rcp_rclm_runtime.refinement.mapping import compute_refinement_mapping_evidence
from rcp_rclm_runtime.schema._common import strict_object, thaw_json
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord, QuantumUpdateRecord
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.policy import (
    CHECKER_POLICY_HASH,
    CLAIM_BOUNDARY_HASH,
    EVALUATOR_POLICY_HASH,
    FORMAL_MANIFEST_BLOB,
    GATE_C_AUDIT_SHA256,
    LEAN_VERIFIER_POLICY_HASH,
    PHASE_2_PROJECT_PIN_HASH,
    RESOURCE_METER_POLICY_HASH,
)
from rcp_rclm_runtime.checker.records import ComponentResultRecord, Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    canonical_rclm_certificate,
    canonical_rclm_state,
    canonical_rclm_update,
    scope_from_core_state,
)


def _structural_result(
    request: Phase3CheckerRequest,
    *,
    scope: str,
    certificate_scope: str,
) -> ComponentResultRecord:
    next_scope = scope_from_core_state(request.candidate.next.core)
    update_scope = _scope_from_update(request.candidate.update.core)
    scope_checks = {
        "predecessor_scope": scope,
        "successor_scope": next_scope,
        "update_scope": update_scope,
        "certificate_scope": certificate_scope,
        "evaluation_scope": request.evaluation_evidence.scope,
    }
    scope_consistent = len(set(scope_checks.values())) == 1
    evaluator_policy_valid = (
        request.evaluation_evidence.evaluator_policy_hash == EVALUATOR_POLICY_HASH
    )
    contract_valid = (
        request.contract_version == request.lean_bridge_report.contract_version
    )
    if not scope_consistent:
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.TYPE_MISMATCH,),
            {
                **scope_checks,
                "scope_consistent": False,
                "evaluator_policy_valid": evaluator_policy_valid,
                "contract_consistent": contract_valid,
            },
        )
    if not evaluator_policy_valid or not contract_valid:
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.PROVENANCE_FAILED,),
            {
                **scope_checks,
                "scope_consistent": True,
                "evaluator_policy_valid": evaluator_policy_valid,
                "contract_consistent": contract_valid,
            },
        )
    return ComponentResultRecord.from_evidence(
        "pass",
        (),
        {
            **scope_checks,
            "scope_consistent": True,
            "evaluator_policy_valid": True,
            "contract_consistent": True,
            "candidate_assertion_fields_consumed": [],
            "model_dependency": False,
            "network_dependency": False,
        },
    )


def _trust_result(
    request: Phase3CheckerRequest,
    *,
    certificate_name: str,
) -> ComponentResultRecord:
    anchor = request.trust_anchor
    checks = {
        "formal_source_commit": anchor.formal_source_commit == FORMAL_SOURCE_COMMIT,
        "lean_toolchain": anchor.lean_toolchain == LEAN_TOOLCHAIN,
        "mathlib_commit": anchor.mathlib_commit == MATHLIB_COMMIT,
        "formal_manifest_blob": anchor.formal_manifest_blob == FORMAL_MANIFEST_BLOB,
        "gate_c_audit_sha256": anchor.gate_c_audit_sha256 == GATE_C_AUDIT_SHA256,
        "checker_policy_hash": anchor.checker_policy_hash == CHECKER_POLICY_HASH,
        "lean_verifier_policy_hash": (
            anchor.lean_verifier_policy_hash == LEAN_VERIFIER_POLICY_HASH
        ),
        "claim_boundary_hash": anchor.claim_boundary_hash == CLAIM_BOUNDARY_HASH,
        "predecessor_not_outside": request.predecessor.core.state != "outside",
        "certificate_not_malformed": certificate_name != "malformed",
    }
    root_keys = (
        "formal_source_commit",
        "lean_toolchain",
        "mathlib_commit",
        "formal_manifest_blob",
        "gate_c_audit_sha256",
        "checker_policy_hash",
        "lean_verifier_policy_hash",
        "claim_boundary_hash",
    )
    roots_ok = all(checks[key] for key in root_keys)
    semantic_ok = checks["predecessor_not_outside"] and checks["certificate_not_malformed"]
    if not roots_ok:
        reasons = (ReasonCode.TRUST_ANCHOR_CHANGED, ReasonCode.TRUST_INVALID)
    elif not semantic_ok:
        reasons = (ReasonCode.TRUST_INVALID,)
    else:
        reasons = ()
    return ComponentResultRecord.from_evidence(
        "pass" if not reasons else "fail",
        reasons,
        checks,
    )


def _resource_result(
    request: Phase3CheckerRequest,
    *,
    certificate_name: str,
) -> ComponentResultRecord:
    record = request.resource_record
    predecessor_used, predecessor_limit = _resource_register(request.predecessor.resources)
    successor_used, successor_limit = _resource_register(request.candidate.next.resources)
    update_name = request.candidate.update.core.update
    if isinstance(request.candidate.update.core, ClassicalBinaryUpdateRecord):
        certificate_update_pair = (
            (certificate_name == "improvement" and update_name == "improve")
            or (certificate_name == "stability" and update_name == "stay")
        )
    elif isinstance(request.candidate.update.core, QuantumUpdateRecord):
        certificate_update_pair = (
            (certificate_name == "improvement" and update_name == "swap")
            or (certificate_name == "stability" and update_name == "stay")
        )
    else:
        certificate_update_pair = False
    checks = {
        "meter_policy_hash": record.meter_policy_hash == RESOURCE_METER_POLICY_HASH,
        "precision_schedule": record.precision_bits in PRECISION_SCHEDULE,
        "budget": record.consumed_units <= record.budget_units,
        "model_free": record.model_invocations == 0,
        "network_free": record.network_requests == 0,
        "predecessor_unmodified": record.predecessor_write_attempts == 0,
        "candidate_unmodified": record.candidate_write_attempts == 0,
        "checker_source_unmodified": record.checker_source_write_attempts == 0,
        "manual_repair_absent": record.manual_repair_count == 0,
        "hidden_oracle_absent": record.hidden_oracle_reads == 0,
        "predecessor_resource_register": predecessor_used <= predecessor_limit,
        "successor_resource_register": successor_used <= successor_limit,
        "certificate_update_pair": certificate_update_pair,
        "certificate_not_malformed": certificate_name != "malformed",
    }
    reasons: list[ReasonCode] = []
    if not all(checks.values()):
        reasons.append(ReasonCode.RESOURCE_INVALID)
    if not checks["manual_repair_absent"]:
        reasons.append(ReasonCode.MANUAL_REPAIR_DETECTED)
    if not checks["hidden_oracle_absent"]:
        reasons.append(ReasonCode.PROVENANCE_FAILED)
    return ComponentResultRecord.from_evidence(
        "pass" if not reasons else "fail",
        tuple(dict.fromkeys(reasons)),
        {
            **checks,
            "budget_units": record.budget_units,
            "consumed_units": record.consumed_units,
            "precision_bits": record.precision_bits,
            "predecessor_used": predecessor_used,
            "predecessor_limit": predecessor_limit,
            "successor_used": successor_used,
            "successor_limit": successor_limit,
        },
    )


def _refinement_result(
    request: Phase3CheckerRequest,
    *,
    scope: str,
    certificate_name: str,
    evaluation_result: ComponentResultRecord,
) -> tuple[ComponentResultRecord, object]:
    expected_predecessor = canonical_rclm_state(request.predecessor.core)
    expected_update = canonical_rclm_update(request.candidate.update.core)
    expected_successor = canonical_rclm_state(request.candidate.next.core)
    expected_certificate = canonical_rclm_certificate(scope, certificate_name)
    checks = {
        "predecessor_canonical": request.predecessor == expected_predecessor,
        "update_canonical": request.candidate.update == expected_update,
        "successor_canonical": request.candidate.next == expected_successor,
        "certificate_canonical": request.certificate == expected_certificate,
        "evaluation_refines_state": evaluation_result.status == "pass",
        "certificate_assertions_authoritative": False,
    }
    mapping_evidence = compute_refinement_mapping_evidence(
        request.predecessor,
        request.candidate.update,
        request.certificate,
    )
    ok = all(value for key, value in checks.items() if key != "certificate_assertions_authoritative")
    return (
        ComponentResultRecord.from_evidence(
            "pass" if ok else "fail",
            () if ok else (ReasonCode.REFINEMENT_MISMATCH,),
            {**checks, "mapping_evidence": mapping_evidence.to_json()},
        ),
        mapping_evidence,
    )


def _lean_bridge_result(
    request: Phase3CheckerRequest,
) -> tuple[ComponentResultRecord, object]:
    packet = build_lean_reference_packet(
        request.predecessor,
        request.candidate,
        request.certificate,
    )
    report = request.lean_bridge_report
    checks = {
        "case_id": report.case_id == packet.case_id,
        "scope": report.scope == packet.scope,
        "packet_hash": report.packet_hash == packet.packet_hash,
        "bridge_verdict": report.bridge_verdict == "accept",
        "expected_acceptance": report.expected_acceptance is True,
        "lean_rcp_acceptance": report.lean_rcp_acceptance is True,
        "lean_rclm_acceptance": report.lean_rclm_acceptance is True,
        "differential_match": report.differential_match,
        "not_timed_out": not report.timed_out,
        "compiler_verdict": report.compiler_report.verdict == "accept",
        "compiler_exit_code": report.compiler_report.exit_code == 0,
        "compiler_toolchain": report.compiler_report.toolchain == LEAN_TOOLCHAIN,
        "compiler_mathlib": report.compiler_report.mathlib_commit == MATHLIB_COMMIT,
        "project_pin_hash": report.project_pin_hash == PHASE_2_PROJECT_PIN_HASH,
    }
    if report.bridge_verdict == "indeterminate" or report.timed_out:
        status = "indeterminate"
        reasons = (ReasonCode.LEAN_VERIFIER_FAILED,)
    elif all(checks.values()):
        status = "pass"
        reasons = ()
    else:
        status = "fail"
        if any("SOURCE_GUARD" in reason for reason in report.reason_codes):
            reasons = (
                ReasonCode.LEAN_SOURCE_FORBIDDEN_TOKEN,
                ReasonCode.LEAN_VERIFIER_FAILED,
            )
        else:
            reasons = (ReasonCode.LEAN_VERIFIER_FAILED,)
    return (
        ComponentResultRecord.from_evidence(
            status,
            reasons,
            {
                **checks,
                "report_hash": report.report_hash,
                "report_reason_codes": list(report.reason_codes),
                "generated_source_hash": report.generated_source_hash,
                "theorem_surface_hash": report.theorem_surface_hash,
                "source_guard_hash": report.source_guard_hash,
                "toolchain_runtime_hash": report.toolchain_runtime_hash,
            },
        ),
        packet,
    )


def _scope_from_update(update: object) -> str:
    if isinstance(update, ClassicalBinaryUpdateRecord):
        return "gate_b_classical"
    if isinstance(update, QuantumUpdateRecord):
        return "gate_c_diagonal_quantum"
    return f"unsupported:{type(update).__name__}"


def _resource_register(artifact: object) -> tuple[int, int]:
    value = thaw_json(getattr(artifact, "value"))
    obj = strict_object(value, "resource_register", {"used", "limit"})
    used = obj["used"]
    limit = obj["limit"]
    if (
        isinstance(used, bool)
        or not isinstance(used, int)
        or used < 0
        or isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 0
    ):
        raise SchemaValidationError(
            "resource_register",
            "used and limit must be nonnegative integers",
        )
    return used, limit
