from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def run_test_suite(package_root: Path, output_path: Path) -> int:
    resolved_root = package_root.resolve(strict=True)
    tests_root = resolved_root / "tests_phase4"
    if not tests_root.is_dir():
        raise FileNotFoundError(f"Phase 4 tests directory is missing: {tests_root}")
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(tests_root),
        "-p",
        "test_*.py",
        "-v",
    ]
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(completed.stdout, encoding="utf-8", newline="\n")
    print(completed.stdout, end="")
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Phase 4 adversarial checker unit suite."
    )
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_test_suite(args.package_root, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
