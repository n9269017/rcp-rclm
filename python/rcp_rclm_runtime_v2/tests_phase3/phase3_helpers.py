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
from rcp_rclm_runtime.checker.policy import PHASE_2_PROJECT_PIN_HASH
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


def lean_report_for(
    predecessor: object,
    candidate: RclmCandidateRecord,
    certificate: object,
    *,
    indeterminate: bool = False,
) -> LeanBridgeVerificationReport:
    packet = build_lean_reference_packet(predecessor, candidate, certificate)
    expected = interpret_reference_packet(packet)
    compiler = LeanVerifierReportRecord(
        verdict="reject" if indeterminate else "accept",
        source_hash="1" * 64,
        exit_code=125 if indeterminate else 0,
        stdout_hash="2" * 64,
        stderr_hash="3" * 64,
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
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


def classical_request(
    *,
    stability: bool = False,
    successor: str | None = None,
    certificate_name: str | None = None,
) -> Phase3CheckerRequest:
    predecessor_core = ClassicalBinaryStateRecord("target" if stability else "initial")
    update_core = ClassicalBinaryUpdateRecord("stay" if stability else "improve")
    successor_core = ClassicalBinaryStateRecord(successor or "target")
    resolved_certificate = certificate_name or (
        "stability" if stability else "improvement"
    )
    predecessor = canonical_rclm_state(predecessor_core)
    candidate = RclmCandidateRecord(
        update=canonical_rclm_update(update_core),
        next=canonical_rclm_state(successor_core),
    )
    certificate = canonical_rclm_certificate(
        "gate_b_classical",
        resolved_certificate,
    )
    return Phase3CheckerRequest(
        transition_id="phase3.classical.reference",
        predecessor=predecessor,
        candidate=candidate,
        certificate=certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(),
        protected_distinctions=reference_protected_distinctions(
            "gate_b_classical"
        ),
        evaluation_evidence=reference_evaluation_evidence(
            predecessor,
            candidate,
        ),
        lean_bridge_report=lean_report_for(
            predecessor,
            candidate,
            certificate,
        ),
    )


def quantum_request(
    *,
    stability: bool = False,
    successor: str | None = None,
    certificate_name: str | None = None,
) -> Phase3CheckerRequest:
    predecessor_core = QuantumStateRecord.canonical(
        "target" if stability else "source"
    )
    update_core = QuantumUpdateRecord.canonical(
        "stay" if stability else "swap"
    )
    successor_core = QuantumStateRecord.canonical(successor or "target")
    resolved_certificate = certificate_name or (
        "stability" if stability else "improvement"
    )
    predecessor = canonical_rclm_state(predecessor_core)
    candidate = RclmCandidateRecord(
        update=canonical_rclm_update(update_core),
        next=canonical_rclm_state(successor_core),
    )
    certificate = canonical_rclm_certificate(
        "gate_c_diagonal_quantum",
        resolved_certificate,
    )
    return Phase3CheckerRequest(
        transition_id="phase3.quantum.reference",
        predecessor=predecessor,
        candidate=candidate,
        certificate=certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(),
        protected_distinctions=reference_protected_distinctions(
            "gate_c_diagonal_quantum"
        ),
        evaluation_evidence=reference_evaluation_evidence(
            predecessor,
            candidate,
        ),
        lean_bridge_report=lean_report_for(
            predecessor,
            candidate,
            certificate,
        ),
    )


def with_refreshed_lean(request: Phase3CheckerRequest) -> Phase3CheckerRequest:
    return replace(
        request,
        lean_bridge_report=lean_report_for(
            request.predecessor,
            request.candidate,
            request.certificate,
        ),
        evaluation_evidence=reference_evaluation_evidence(
            request.predecessor,
            request.candidate,
        ),
    )
