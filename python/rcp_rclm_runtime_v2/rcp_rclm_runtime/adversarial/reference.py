from __future__ import annotations

from dataclasses import replace

from rcp_rclm_runtime._version import LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.lean_bridge.packet import interpret_reference_packet
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationReport
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
)
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    QuantumUpdateRecord,
)
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord
from rcp_rclm_runtime.checker.hardened import Phase4HardenedRequest
from rcp_rclm_runtime.checker.integrity import build_reference_package_integrity
from rcp_rclm_runtime.checker.policy import PHASE_2_PROJECT_PIN_HASH, CheckerScope
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    canonical_rclm_certificate,
    canonical_rclm_state,
    canonical_rclm_update,
    reference_evaluation_evidence,
    reference_protected_distinctions,
    reference_resource_record,
    reference_trust_anchor,
)


def reference_lean_report_for(
    request: Phase3CheckerRequest,
    *,
    indeterminate: bool = False,
    source_guard_rejected: bool = False,
) -> LeanBridgeVerificationReport:
    packet = build_lean_reference_packet(
        request.predecessor,
        request.candidate,
        request.certificate,
    )
    expected = interpret_reference_packet(packet)
    compiler = LeanVerifierReportRecord(
        verdict=(
            "reject"
            if indeterminate or source_guard_rejected
            else "accept"
        ),
        source_hash="1" * 64,
        exit_code=(
            126
            if source_guard_rejected
            else (125 if indeterminate else 0)
        ),
        stdout_hash="2" * 64,
        stderr_hash="3" * 64,
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
    )
    if source_guard_rejected:
        return LeanBridgeVerificationReport(
            bridge_verdict="reject",
            reason_codes=("LEAN_SOURCE_GUARD_REJECTED",),
            case_id=packet.case_id,
            scope=packet.scope,
            packet_hash=packet.packet_hash,
            expected_acceptance=expected,
            lean_rcp_acceptance=None,
            lean_rclm_acceptance=None,
            differential_match=False,
            generated_source_path=f"generated/{packet.case_id}.lean",
            generated_source_hash="4" * 64,
            theorem_surface_hash="5" * 64,
            project_pin_hash=PHASE_2_PROJECT_PIN_HASH,
            toolchain_runtime_hash="6" * 64,
            source_guard_hash="7" * 64,
            error_detail_hash="8" * 64,
            compiler_report=compiler,
            compiler_duration_ms=0,
            timed_out=False,
        )
    if indeterminate:
        return LeanBridgeVerificationReport(
            bridge_verdict="indeterminate",
            reason_codes=("TEST_LEAN_UNAVAILABLE",),
            case_id=packet.case_id,
            scope=packet.scope,
            packet_hash=packet.packet_hash,
            expected_acceptance=expected,
            lean_rcp_acceptance=None,
            lean_rclm_acceptance=None,
            differential_match=False,
            generated_source_path=f"generated/{packet.case_id}.lean",
            generated_source_hash="4" * 64,
            theorem_surface_hash="5" * 64,
            project_pin_hash=PHASE_2_PROJECT_PIN_HASH,
            toolchain_runtime_hash="6" * 64,
            source_guard_hash="7" * 64,
            error_detail_hash="8" * 64,
            compiler_report=compiler,
            compiler_duration_ms=0,
            timed_out=True,
        )
    return LeanBridgeVerificationReport(
        bridge_verdict="accept",
        reason_codes=(),
        case_id=packet.case_id,
        scope=packet.scope,
        packet_hash=packet.packet_hash,
        expected_acceptance=expected,
        lean_rcp_acceptance=expected,
        lean_rclm_acceptance=expected,
        differential_match=True,
        generated_source_path=f"generated/{packet.case_id}.lean",
        generated_source_hash="4" * 64,
        theorem_surface_hash="5" * 64,
        project_pin_hash=PHASE_2_PROJECT_PIN_HASH,
        toolchain_runtime_hash="6" * 64,
        source_guard_hash="7" * 64,
        error_detail_hash=sha256_hex(b""),
        compiler_report=compiler,
        compiler_duration_ms=1,
        timed_out=False,
    )


def reference_phase3_request(
    scope: CheckerScope,
    *,
    stability: bool = False,
) -> Phase3CheckerRequest:
    if scope == "gate_b_classical":
        predecessor_core = ClassicalBinaryStateRecord(
            "target" if stability else "initial"
        )
        update_core = ClassicalBinaryUpdateRecord(
            "stay" if stability else "improve"
        )
        successor_core = ClassicalBinaryStateRecord("target")
    else:
        predecessor_core = QuantumStateRecord.canonical(
            "target" if stability else "source"
        )
        update_core = QuantumUpdateRecord.canonical(
            "stay" if stability else "swap"
        )
        successor_core = QuantumStateRecord.canonical("target")
    certificate_name = "stability" if stability else "improvement"
    predecessor = canonical_rclm_state(predecessor_core)
    candidate = RclmCandidateRecord(
        update=canonical_rclm_update(update_core),
        next=canonical_rclm_state(successor_core),
    )
    certificate = canonical_rclm_certificate(scope, certificate_name)
    initial = Phase3CheckerRequest(
        transition_id=f"phase4.{scope}.{'stability' if stability else 'improvement'}",
        predecessor=predecessor,
        candidate=candidate,
        certificate=certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(),
        protected_distinctions=reference_protected_distinctions(scope),
        evaluation_evidence=reference_evaluation_evidence(predecessor, candidate),
        lean_bridge_report=_placeholder_lean_report(scope),
    )
    return replace(initial, lean_bridge_report=reference_lean_report_for(initial))


def reference_hardened_request(
    scope: CheckerScope = "gate_b_classical",
    *,
    stability: bool = False,
) -> Phase4HardenedRequest:
    checker_request = reference_phase3_request(scope, stability=stability)
    return Phase4HardenedRequest(
        checker_request=checker_request,
        package_integrity=build_reference_package_integrity(checker_request),
    )


def refresh_hardened_request(
    request: Phase4HardenedRequest,
) -> Phase4HardenedRequest:
    phase3 = replace(
        request.checker_request,
        evaluation_evidence=reference_evaluation_evidence(
            request.checker_request.predecessor,
            request.checker_request.candidate,
        ),
    )
    phase3 = replace(phase3, lean_bridge_report=reference_lean_report_for(phase3))
    return Phase4HardenedRequest(
        checker_request=phase3,
        package_integrity=build_reference_package_integrity(phase3),
    )


def _placeholder_lean_report(scope: CheckerScope) -> LeanBridgeVerificationReport:
    compiler = LeanVerifierReportRecord(
        verdict="reject",
        source_hash="1" * 64,
        exit_code=125,
        stdout_hash="2" * 64,
        stderr_hash="3" * 64,
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
    )
    return LeanBridgeVerificationReport(
        bridge_verdict="indeterminate",
        reason_codes=("PLACEHOLDER_NOT_EVALUATED",),
        case_id="phase4.placeholder",
        scope=scope,
        packet_hash="4" * 64,
        expected_acceptance=False,
        lean_rcp_acceptance=None,
        lean_rclm_acceptance=None,
        differential_match=False,
        generated_source_path="generated/placeholder.lean",
        generated_source_hash="5" * 64,
        theorem_surface_hash="6" * 64,
        project_pin_hash=PHASE_2_PROJECT_PIN_HASH,
        toolchain_runtime_hash="7" * 64,
        source_guard_hash="8" * 64,
        error_detail_hash="9" * 64,
        compiler_report=compiler,
        compiler_duration_ms=0,
        timed_out=True,
    )
