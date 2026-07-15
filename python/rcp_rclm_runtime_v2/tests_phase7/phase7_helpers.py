from __future__ import annotations

from dataclasses import replace

from rcp_rclm_runtime._version import LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.lean_bridge.packet import (
    LeanReferencePacket,
    interpret_reference_packet,
)
from rcp_rclm_runtime.lean_bridge.source_generator import generate_reference_source
from rcp_rclm_runtime.lean_bridge.source_guard import scan_source_bytes
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationEvidence,
    LeanBridgeVerificationReport,
)
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord
from rcp_rclm_runtime.checker.policy import PHASE_2_PROJECT_PIN_HASH


def fixture_lean_evidence(
    packet: LeanReferencePacket,
) -> LeanBridgeVerificationEvidence:
    generated = generate_reference_source(packet)
    guard = scan_source_bytes(generated.source_bytes)
    expected = interpret_reference_packet(packet)
    compiler = LeanVerifierReportRecord(
        verdict="accept",
        source_hash=generated.source_hash,
        exit_code=0,
        stdout_hash="2" * 64,
        stderr_hash=sha256_hex(b""),
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
    )
    report = LeanBridgeVerificationReport(
        bridge_verdict="accept",
        reason_codes=(),
        case_id=packet.case_id,
        scope=packet.scope,
        packet_hash=packet.packet_hash,
        expected_acceptance=expected,
        lean_rcp_acceptance=expected,
        lean_rclm_acceptance=expected,
        differential_match=True,
        generated_source_path=generated.virtual_path,
        generated_source_hash=generated.source_hash,
        theorem_surface_hash=generated.theorem_surface_hash,
        project_pin_hash=PHASE_2_PROJECT_PIN_HASH,
        toolchain_runtime_hash="5" * 64,
        source_guard_hash=canonical_json_hash(guard.to_json()),
        error_detail_hash=sha256_hex(b""),
        compiler_report=compiler,
        compiler_duration_ms=1,
        timed_out=False,
    )
    return LeanBridgeVerificationEvidence(
        generated=generated,
        source_guard=guard,
        compilation=None,
        parsed_verdict=None,
        report=report,
    )


def fixture_rejected_lean_evidence(
    packet: LeanReferencePacket,
) -> LeanBridgeVerificationEvidence:
    evidence = fixture_lean_evidence(packet)
    report = replace(
        evidence.report,
        bridge_verdict="reject",
        reason_codes=("FIXTURE_REJECT",),
        differential_match=False,
    )
    return replace(evidence, report=report)


def fixture_indeterminate_lean_evidence(
    packet: LeanReferencePacket,
) -> LeanBridgeVerificationEvidence:
    evidence = fixture_lean_evidence(packet)
    report = replace(
        evidence.report,
        bridge_verdict="indeterminate",
        reason_codes=("FIXTURE_TIMEOUT",),
        differential_match=False,
        timed_out=True,
    )
    return replace(evidence, report=report)
