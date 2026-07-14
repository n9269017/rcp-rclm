from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationEvidence,
    LeanBridgeVerificationReport,
    LeanReferenceVerifier,
)
from rcp_rclm_runtime.generator.pipeline import run_phase5a_reference_loop
from rcp_rclm_runtime.generator.reference import reference_generator_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete Phase 5A bounded generator, construction, selection, "
            "logical realization, pinned Lean verification, and hardened checker loop."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument(
        "--state",
        choices=("initial", "target", "all"),
        default="all",
    )
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve(strict=True)
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    project = PinnedLeanProject.discover(repo_root)
    compiler = LeanCompiler(project, timeout_seconds=args.timeout_seconds)
    verifier = LeanReferenceVerifier(compiler)
    states = ("initial", "target") if args.state == "all" else (args.state,)
    cases: list[dict[str, object]] = []
    all_accepted = True

    for state in states:
        case_dir = outdir / state
        case_dir.mkdir(parents=True, exist_ok=True)
        captured: list[LeanBridgeVerificationEvidence] = []

        def verify(packet: LeanReferencePacket) -> LeanBridgeVerificationReport:
            evidence = verifier.verify_with_evidence(packet)
            captured.append(evidence)
            return evidence.report

        generator_input = reference_generator_input(state)
        evidence = run_phase5a_reference_loop(generator_input, verify)
        report = evidence.report
        all_accepted = all_accepted and report.accepted

        _write_json(case_dir / "generator_input.json", generator_input.to_json())
        (case_dir / "first_generator_stdout.json").write_bytes(
            evidence.first_process.stdout
        )
        (case_dir / "first_generator_stderr.bin").write_bytes(
            evidence.first_process.stderr
        )
        (case_dir / "second_generator_stdout.json").write_bytes(
            evidence.second_process.stdout
        )
        (case_dir / "second_generator_stderr.bin").write_bytes(
            evidence.second_process.stderr
        )
        _write_json(
            case_dir / "first_process_report.json",
            evidence.first_process.report.to_json(),
        )
        _write_json(
            case_dir / "second_process_report.json",
            evidence.second_process.report.to_json(),
        )
        _write_json(case_dir / "reference_loop_report.json", report.to_json())

        if captured:
            lean = captured[0]
            (case_dir / "generated_certificate.lean").write_bytes(
                lean.generated.source_bytes
            )
            _write_json(case_dir / "generated_source.json", lean.generated.to_json())
            _write_json(case_dir / "source_guard.json", lean.source_guard.to_json())
            _write_json(case_dir / "lean_bridge_report.json", lean.report.to_json())
            if lean.compilation is not None:
                _write_json(
                    case_dir / "compilation_report.json",
                    lean.compilation.to_json(),
                )
                (case_dir / "lean_stdout.bin").write_bytes(lean.compilation.stdout)
                (case_dir / "lean_stderr.bin").write_bytes(lean.compilation.stderr)
            if lean.parsed_verdict is not None:
                _write_json(
                    case_dir / "parsed_lean_verdict.json",
                    lean.parsed_verdict.to_json(),
                )

        cases.append(
            {
                "state": state,
                "transition_id": generator_input.transition_id,
                "accepted": report.accepted,
                "verdict": report.verdict,
                "report_hash": report.report_hash,
                "proposal_hash": (
                    None if report.proposal is None else report.proposal.proposal_hash
                ),
                "lean_report_hash": (
                    None
                    if report.lean_bridge_report is None
                    else report.lean_bridge_report.report_hash
                ),
                "hardened_report_hash": (
                    None
                    if report.hardened_checker_report is None
                    else report.hardened_checker_report.report_hash
                ),
            }
        )

    summary = {
        "schema_id": "runtime.phase5a_reference_loop_summary.v2",
        "case_count": len(cases),
        "cases": cases,
        "all_accepted": all_accepted,
        "project_pin_hash": project.pin_hash,
    }
    summary["summary_hash"] = canonical_json_hash(summary)
    _write_json(outdir / "summary.json", summary)
    return 0 if all_accepted else 1


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


if __name__ == "__main__":
    raise SystemExit(main())
