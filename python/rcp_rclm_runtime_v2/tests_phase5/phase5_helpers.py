from __future__ import annotations

from rcp_rclm_runtime._version import LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.lean_bridge.packet import (
    LeanReferencePacket,
    interpret_reference_packet,
)
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationReport
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord
from rcp_rclm_runtime.checker.policy import PHASE_2_PROJECT_PIN_HASH


def fixture_lean_report(packet: LeanReferencePacket) -> LeanBridgeVerificationReport:
    expected = interpret_reference_packet(packet)
    compiler = LeanVerifierReportRecord(
        verdict="accept",
        source_hash="1" * 64,
        exit_code=0,
        stdout_hash="2" * 64,
        stderr_hash=sha256_hex(b""),
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
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
        generated_source_hash="3" * 64,
        theorem_surface_hash="4" * 64,
        project_pin_hash=PHASE_2_PROJECT_PIN_HASH,
        toolchain_runtime_hash="5" * 64,
        source_guard_hash="6" * 64,
        error_detail_hash=sha256_hex(b""),
        compiler_report=compiler,
        compiler_duration_ms=1,
        timed_out=False,
    )
