from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_text
from rcp_rclm_runtime.generator.grammar import validate_untrusted_proposal
from rcp_rclm_runtime.generator.process import run_reference_generator_process
from rcp_rclm_runtime.generator.reference import reference_generator_input


def run_suite(output_path: Path) -> int:
    cases: list[dict[str, object]] = []
    ok = True
    for state in ("initial", "target"):
        request = reference_generator_input(state)
        first = run_reference_generator_process(request)
        second = run_reference_generator_process(request)
        replay = (
            first.report.verdict == "success"
            and second.report.verdict == "success"
            and first.stdout == second.stdout
            and first.stderr == second.stderr
            and first.proposal == second.proposal
            and first.report.to_json() == second.report.to_json()
        )
        validation = (
            None
            if first.proposal is None
            else validate_untrusted_proposal(request, first.proposal)
        )
        case_ok = replay and validation is not None and validation.status == "pass"
        ok = ok and case_ok
        cases.append(
            {
                "state": state,
                "request_hash": request.input_hash,
                "first_process": first.report.to_json(),
                "second_process": second.report.to_json(),
                "proposal": None if first.proposal is None else first.proposal.to_json(),
                "proposal_validation": (
                    None if validation is None else validation.to_json()
                ),
                "deterministic_replay": replay,
                "ok": case_ok,
            }
        )
    report = {
        "schema_id": "runtime.phase5a_process_suite.v2",
        "case_count": len(cases),
        "cases": cases,
        "all_passed": ok,
    }
    report["report_hash"] = canonical_json_hash(report)
    text = canonical_json_text(report) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the two-case Phase 5A separate-process generator suite."
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_suite(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
