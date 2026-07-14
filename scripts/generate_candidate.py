from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.generator.process import run_reference_generator_replay
from rcp_rclm_runtime.generator.records import ReferenceGeneratorInputRecord


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the deterministic Phase 5A bounded reference generator in a "
            "separate process and emit its replay report."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the canonical generator replay report to this path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = args.input.read_bytes()
        parsed = load_json_strict(raw, require_canonical=True)
        generator_input = ReferenceGeneratorInputRecord.from_json(parsed)
    except OSError as exc:
        print(f"could not read generator input: {exc}", file=sys.stderr)
        return 2
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        print(f"invalid generator input: {exc}", file=sys.stderr)
        return 2
    report = run_reference_generator_replay(generator_input)
    output = canonical_json_bytes(report.to_json()) + b"\n"
    if args.out is None:
        sys.stdout.buffer.write(output)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(output)
    return 0 if report.status == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
