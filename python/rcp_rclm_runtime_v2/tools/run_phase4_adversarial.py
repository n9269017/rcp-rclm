from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.adversarial.runner import run_phase4_adversarial_suite
from rcp_rclm_runtime.canonical.json import canonical_json_text


def run_suite(output_path: Path) -> int:
    report = run_phase4_adversarial_suite()
    text = canonical_json_text(report.to_json()) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if report.all_passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and record the Phase 4 deterministic adversarial rejection suite."
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_suite(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
