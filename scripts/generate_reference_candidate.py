from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.generator.process import run_reference_generator_process
from rcp_rclm_runtime.generator.protocol import ReferenceGeneratorInputRecord


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Phase 5A bounded reference generator in a separate isolated "
            "stdin/stdout process."
        )
    )
    parser.add_argument("request", type=Path)
    parser.add_argument("--proposal-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = args.request.read_bytes()
        value = load_json_strict(data, require_canonical=True)
        request = ReferenceGeneratorInputRecord.from_json(value)
    except (OSError, RuntimeValidationError, TypeError, ValueError) as exc:
        print(f"invalid reference-generator request: {exc}", file=sys.stderr)
        return 2
    evidence = run_reference_generator_process(request)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_bytes(canonical_json_bytes(evidence.report.to_json()) + b"\n")
    if evidence.proposal is None:
        return 1
    args.proposal_out.parent.mkdir(parents=True, exist_ok=True)
    args.proposal_out.write_bytes(evidence.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
