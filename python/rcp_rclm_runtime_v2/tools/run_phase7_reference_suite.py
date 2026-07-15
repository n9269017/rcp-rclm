from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime._version import LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.checker.policy import PHASE_2_PROJECT_PIN_HASH
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
from rcp_rclm_runtime.promotion.reference import run_reference_phase7_trajectory
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    store_root = outdir / "store"
    evidence = run_reference_phase7_trajectory(
        store_root,
        fixture_lean_evidence,
    )
    summary = evidence.to_json()
    summary["lean_mode"] = "deterministic_fixture_for_platform_testing"
    summary["trajectory_hash"] = evidence.trajectory_hash
    (outdir / "summary.json").write_bytes(canonical_json_bytes(summary))
    print(canonical_json_bytes(summary).decode("utf-8"))
    return 0 if evidence.all_expectations_met else 1


if __name__ == "__main__":
    raise SystemExit(main())
