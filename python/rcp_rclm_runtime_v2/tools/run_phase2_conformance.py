from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.conformance import DifferentialConformanceSuiteReport
from rcp_rclm_runtime.lean_bridge.packet import reference_packets
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the pinned Lean/Python Phase 2 differential conformance suite."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--lake-command", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser.parse_args()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def main() -> int:
    args = _arguments()
    repo_root = args.repo_root.resolve(strict=True)
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    project = PinnedLeanProject.discover(repo_root)
    compiler = LeanCompiler(
        project=project,
        lake_command=args.lake_command,
        timeout_seconds=args.timeout_seconds,
    )
    verifier = LeanReferenceVerifier(compiler)

    _write_json(outdir / "project_pin.json", project.to_json())
    reports = []
    for packet in reference_packets():
        evidence = verifier.verify_with_evidence(packet)
        case_dir = outdir / "cases" / packet.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        _write_json(case_dir / "packet.json", packet.to_json())
        _write_json(case_dir / "generated_source.json", evidence.generated.to_json())
        (case_dir / "generated_certificate.lean").write_text(
            evidence.generated.source_text,
            encoding="utf-8",
            newline="\n",
        )
        _write_json(case_dir / "source_guard.json", evidence.source_guard.to_json())
        _write_json(case_dir / "bridge_report.json", evidence.report.to_json())
        if evidence.parsed_verdict is not None:
            _write_json(case_dir / "lean_verdict.json", evidence.parsed_verdict.to_json())
        if evidence.compilation is not None:
            _write_json(case_dir / "compilation.json", evidence.compilation.to_json())
            (case_dir / "lean_stdout.txt").write_bytes(evidence.compilation.stdout)
            (case_dir / "lean_stderr.txt").write_bytes(evidence.compilation.stderr)
            _write_json(
                case_dir / "toolchain_identity.json",
                evidence.compilation.toolchain_identity.to_json(),
            )
        reports.append(evidence.report)

    suite = DifferentialConformanceSuiteReport(reports=tuple(reports))
    _write_json(outdir / "phase_2_conformance_report.json", suite.to_json())
    summary = {
        "schema_id": "runtime.phase_2_conformance_summary.v2",
        "case_count": suite.case_count,
        "accepting_case_count": suite.accepting_case_count,
        "rejecting_case_count": suite.rejecting_case_count,
        "all_bridge_reports_accepted": suite.all_bridge_reports_accepted,
        "all_differential_matches": suite.all_differential_matches,
        "report_hash": suite.report_hash,
        "ok": suite.ok,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if suite.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
