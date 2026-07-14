from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.checker.aggregate import check_transition_bytes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the deterministic, model-free, network-free Phase 3 checker "
            "against one canonical request."
        )
    )
    parser.add_argument("request", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the canonical checker report to this path",
    )
    parser.add_argument(
        "--allow-noncanonical-input",
        action="store_true",
        help="parse noncanonical JSON but never use this mode for promotion",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request_bytes = args.request.read_bytes()
    except OSError as exc:
        print(f"could not read checker request: {exc}", file=sys.stderr)
        return 2
    report = check_transition_bytes(
        request_bytes,
        require_canonical=not args.allow_noncanonical_input,
    )
    output = canonical_json_bytes(report.to_json()) + b"\n"
    if args.out is None:
        sys.stdout.buffer.write(output)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(output)
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
