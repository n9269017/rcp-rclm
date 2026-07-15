from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
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
from rcp_rclm_runtime.promotion.store import load_active_phase7_store
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord
from rcp_rclm_runtime.torch_backend.admission import (
    bootstrap_pytorch_pilot_store,
    run_pytorch_pilot_controller,
    verify_pytorch_pilot_promotion,
)
from rcp_rclm_runtime.torch_backend.pilot_data import pilot_heldout_evaluation_data
from rcp_rclm_runtime.torch_backend.pilot_policy import pytorch_pilot_phase7_policy
from rcp_rclm_runtime.torch_backend.replay import replay_pytorch_pilot_store


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--case", choices=("accepted", "rejected"), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outdir = args.outdir.resolve(strict=False)
    if outdir.exists():
        raise FileExistsError(f"fixture output already exists: {outdir}")
    outdir.mkdir(parents=True, exist_ok=False)
    store = outdir / "store"
    bootstrap_pytorch_pilot_store(store)
    before = load_active_phase7_store(store, pytorch_pilot_phase7_policy())
    evaluation_data = pilot_heldout_evaluation_data()
    expected = "promoted"
    if args.case == "rejected":
        evaluation_data["labels"] = [0, 0, 0, 0]
        expected = "rejected"
    evidence = run_pytorch_pilot_controller(
        store,
        fixture_lean_evidence,
        run_label=f"pytorch-pilot-fixture-{args.case}",
        evaluation_data=evaluation_data,
    )
    after = verify_pytorch_pilot_promotion(evidence)
    replay_json: object = None
    replay_accepted = False
    replay_generator_invocations = 0
    if args.case == "accepted":
        replay = replay_pytorch_pilot_store(
            store,
            outdir / "replay",
            fixture_lean_evidence,
        )
        replay_json = replay.report.to_json()
        replay_accepted = replay.report.accepted
        replay_generator_invocations = replay.report.generator_invocations
    summary = {
        "schema_id": "runtime.pytorch_pilot_fixture_summary.v1",
        "case": args.case,
        "expected_verdict": expected,
        "observed_verdict": evidence.verdict,
        "expectation_met": evidence.verdict == expected,
        "controller_report_hash": evidence.controller_report.report_hash,
        "attempt_report_hash": evidence.attempt_report.report_hash,
        "active_package_hash_before": before.pointer.active_package_hash,
        "active_package_hash_after": after.pointer.active_package_hash,
        "active_package_changed": (
            before.pointer.active_package_hash != after.pointer.active_package_hash
        ),
        "fallback_rollback_verified": (
            evidence.attempt_report.fallback_rollback_verified
        ),
        "manual_repair_count": evidence.attempt_report.manual_repair_count,
        "host_torch_loaded": "torch" in sys.modules,
        "host_proposal_backend_loaded": (
            "rcp_rclm_runtime.torch_backend.proposal_backend" in sys.modules
        ),
        "replay_accepted": replay_accepted,
        "replay_generator_invocations": replay_generator_invocations,
        "replay_report": replay_json,
    }
    if args.case == "accepted":
        summary["expectation_met"] = bool(
            summary["expectation_met"]
            and summary["active_package_changed"]
            and replay_accepted
            and replay_generator_invocations == 0
        )
    else:
        summary["expectation_met"] = bool(
            summary["expectation_met"]
            and not summary["active_package_changed"]
            and summary["fallback_rollback_verified"]
        )
    encoded = canonical_json_bytes(summary)
    (outdir / "summary.json").write_bytes(encoded)
    print(encoded.decode("utf-8"))
    return 0 if summary["expectation_met"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
