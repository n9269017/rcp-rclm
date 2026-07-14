from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.generator.lean_conformance import (
    reference_grammar_lean_source,
    verify_reference_grammar_with_lean,
)
from rcp_rclm_runtime.generator.pipeline import execute_reference_pipeline
from rcp_rclm_runtime.generator.reference import build_reference_generator_input
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the deterministic Phase 5A bounded reference generator through "
            "direct grammar conformance, certificate construction, selection, "
            "realization, pinned Lean, and the hardened checker."
        )
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

    grammar_dir = outdir / "grammar_conformance"
    grammar_evidence = verify_reference_grammar_with_lean(compiler)
    grammar_dir.mkdir(parents=True, exist_ok=True)
    (grammar_dir / "bounded_reference_grammar.lean").write_bytes(
        reference_grammar_lean_source()
    )
    _write_json(
        grammar_dir / "source_guard.json",
        grammar_evidence.source_guard.to_json(),
    )
    _write_json(
        grammar_dir / "grammar_conformance.json",
        grammar_evidence.to_json(),
    )
    if grammar_evidence.compilation is not None:
        _write_json(
            grammar_dir / "compilation.json",
            grammar_evidence.compilation.to_json(),
        )
        (grammar_dir / "lean_stdout.txt").write_bytes(
            grammar_evidence.compilation.stdout
        )
        (grammar_dir / "lean_stderr.txt").write_bytes(
            grammar_evidence.compilation.stderr
        )
        _write_json(
            grammar_dir / "toolchain_identity.json",
            grammar_evidence.compilation.toolchain_identity.to_json(),
        )

    case_summaries: list[dict[str, object]] = []
    all_accepted = grammar_evidence.accepted
    for predecessor_name in ("initial", "target"):
        generator_input = build_reference_generator_input(
            predecessor_name,
            task_id=f"phase5a.reference.{predecessor_name}",
            resource_units=1,
            timeout_seconds=min(args.timeout_seconds, 300),
        )
        execution = execute_reference_pipeline(generator_input, verifier)
        report = execution.report
        case_dir = outdir / "cases" / predecessor_name
        _write_json(case_dir / "generator_input.json", generator_input.to_json())
        _write_json(
            case_dir / "generator_replay.json",
            report.generator_replay.to_json(),
        )
        if report.generator_replay.proposal is not None:
            _write_json(
                case_dir / "untrusted_proposal.json",
                report.generator_replay.proposal.to_json(),
            )
        if report.certificate_construction is not None:
            _write_json(
                case_dir / "certificate_construction.json",
                report.certificate_construction.to_json(),
            )
        if report.selection is not None:
            _write_json(case_dir / "selection.json", report.selection.to_json())
        if report.realization is not None:
            _write_json(case_dir / "realization.json", report.realization.to_json())
        if report.lean_bridge_report is not None:
            _write_json(
                case_dir / "lean_bridge_report.json",
                report.lean_bridge_report.to_json(),
            )
        if report.hardened_checker_report is not None:
            _write_json(
                case_dir / "hardened_checker_report.json",
                report.hardened_checker_report.to_json(),
            )
        _write_json(case_dir / "pipeline_report.json", report.to_json())

        evidence = execution.lean_evidence
        if evidence is not None:
            _write_json(
                case_dir / "generated_source.json",
                evidence.generated.to_json(),
            )
            (case_dir / "generated_certificate.lean").write_text(
                evidence.generated.source_text,
                encoding="utf-8",
                newline="\n",
            )
            _write_json(
                case_dir / "source_guard.json",
                evidence.source_guard.to_json(),
            )
            if evidence.parsed_verdict is not None:
                _write_json(
                    case_dir / "lean_verdict.json",
                    evidence.parsed_verdict.to_json(),
                )
            if evidence.compilation is not None:
                _write_json(
                    case_dir / "compilation.json",
                    evidence.compilation.to_json(),
                )
                (case_dir / "lean_stdout.txt").write_bytes(
                    evidence.compilation.stdout
                )
                (case_dir / "lean_stderr.txt").write_bytes(
                    evidence.compilation.stderr
                )
                _write_json(
                    case_dir / "toolchain_identity.json",
                    evidence.compilation.toolchain_identity.to_json(),
                )

        case_summary = {
            "schema_id": "runtime.phase5_reference_pipeline_case_summary.v2",
            "predecessor": predecessor_name,
            "transition_id": report.transition_id,
            "generator_replay_deterministic": report.generator_replay.deterministic,
            "generator_status": report.generator_replay.status,
            "pipeline_verdict": report.verdict,
            "accepted": report.accepted,
            "pipeline_report_hash": report.report_hash,
        }
        _write_json(case_dir / "summary.json", case_summary)
        case_summaries.append(case_summary)
        all_accepted = all_accepted and report.accepted

    suite_payload = {
        "schema_id": "runtime.phase5_reference_pipeline_suite.v2",
        "grammar_conformance_accepted": grammar_evidence.accepted,
        "grammar_conformance_report_hash": grammar_evidence.report_hash,
        "case_count": len(case_summaries),
        "accepted_case_count": sum(
            1 for item in case_summaries if item["accepted"] is True
        ),
        "all_generator_replays_deterministic": all(
            item["generator_replay_deterministic"] is True
            for item in case_summaries
        ),
        "all_accepted": all_accepted,
        "cases": case_summaries,
    }
    suite = {
        **suite_payload,
        "suite_hash": canonical_json_hash(suite_payload),
    }
    _write_json(outdir / "phase_5_reference_pipeline_report.json", suite)
    print(json.dumps(suite, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if all_accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
