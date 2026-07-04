#!/usr/bin/env python3
"""Validate and run the full HumanEval+ direct sidecar.

This wrapper refuses TODO files and then invokes certified_evalplus_suite_harness.py
with --full.  It defaults to --mini for a fast full-coverage smoke run.  Use
--full-plus-tests for the heavier direct full-plus-test sidecar.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "artifacts" / "evalplus_leaderboard"
DEFAULT_SAMPLES = ROOT / "successor_samples_non_oracle_HumanEval_full.jsonl"


def run(cmd):
    print("[run]", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=REPO)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run full HumanEval+ certificate-preserving sidecar")
    ap.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    ap.add_argument("--mode", choices=["rcp", "rclm"], default="rclm")
    ap.add_argument("--N", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--full-plus-tests", action="store_true", help="Do not use --mini; run all direct plus tests")
    ap.add_argument("--per-test-timeout", type=float, default=2.0)
    ap.add_argument("--max-plus-tests", type=int, default=50)
    args = ap.parse_args()

    validate_cmd = [sys.executable, str(ROOT / "validate_humaneval_full_completion.py"), "--samples", str(args.samples)]
    rc = run(validate_cmd).returncode
    if rc != 0:
        print("Validation failed. Complete all 164 non-oracle solutions before running the full sidecar.")
        return rc

    harness = [
        sys.executable, str(ROOT / "certified_evalplus_suite_harness.py"),
        "--dataset", "humaneval",
        "--mode", args.mode,
        "--N", str(args.N),
        "--seed", str(args.seed),
        "--full",
        "--successor-samples", str(args.samples),
        "--per-test-timeout", str(args.per_test_timeout),
        "--max-plus-tests", str(args.max_plus_tests),
    ]
    if not args.full_plus_tests:
        harness.append("--mini")
    return run(harness).returncode


if __name__ == "__main__":
    raise SystemExit(main())
