#!/usr/bin/env python3
"""Run the official EvalPlus CLI and capture artifacts.

This script is a thin subprocess wrapper around `evalplus.evaluate`. It records
stdout, stderr, command, sample hashes, parsed pass@1 scores, and cache paths.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
REPO = THIS.parents[2]
THIS_DIR = THIS.parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from parse_evalplus_outputs import parse_evalplus_scores_from_text, possible_eval_cache_paths, sha256_file


def main() -> int:
    p = argparse.ArgumentParser(description="Run official EvalPlus CLI")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--samples", type=Path, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--outdir", type=Path, default=REPO / "artifacts" / "evalplus_official" / "results")
    p.add_argument("--base-only", action="store_true")
    p.add_argument("--mini", action="store_true")
    p.add_argument("--parallel", type=int, default=None)
    p.add_argument("--i-just-wanna-run", action="store_true")
    p.add_argument("--command", default=None, help="Override EvalPlus executable, default finds evalplus.evaluate")
    p.add_argument("--extra-arg", action="append", default=[], help="Extra argument appended to EvalPlus command")
    args = p.parse_args()

    samples = args.samples.resolve()
    if not samples.exists():
        raise SystemExit(f"samples not found: {samples}")

    case = args.outdir / args.label
    case.mkdir(parents=True, exist_ok=True)

    exe = args.command or shutil.which("evalplus.evaluate")
    if exe:
        cmd = [exe]
    else:
        # Some installations expose only the module path.
        cmd = [sys.executable, "-m", "evalplus.evaluate"]

    cmd += ["--dataset", args.dataset, "--samples", str(samples)]
    if args.base_only:
        cmd.append("--base-only")
    if args.mini:
        cmd.append("--mini")
    if args.parallel:
        cmd += ["--parallel", str(args.parallel)]
    if args.i_just_wanna_run:
        cmd.append("--i-just-wanna-run")
    cmd += list(args.extra_arg or [])

    env = os.environ.copy()
    proc = subprocess.run(cmd, cwd=str(REPO), text=True, encoding="utf-8", errors="replace", capture_output=True)

    stdout_path = case / "evalplus_stdout.txt"
    stderr_path = case / "evalplus_stderr.txt"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    parsed = parse_evalplus_scores_from_text(proc.stdout + "\n" + proc.stderr)
    caches = [str(p) for p in possible_eval_cache_paths(samples) if p.exists()]

    runlog = {
        "ok": proc.returncode == 0,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "label": args.label,
        "samples_path": str(samples),
        "samples_hash": sha256_file(samples),
        "base_only": bool(args.base_only),
        "mini": bool(args.mini),
        "command": cmd,
        "returncode": proc.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed_scores": parsed,
        "eval_cache_paths": caches,
        "runlog_path": str(case / "official_evalplus_runlog.json"),
    }

    runlog_path = case / "official_evalplus_runlog.json"
    runlog_path.write_text(json.dumps(runlog, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "ok": runlog["ok"],
        "label": args.label,
        "runlog": str(runlog_path),
        "returncode": proc.returncode,
        "parsed_scores": parsed,
        "eval_cache_paths": caches,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }, indent=2, ensure_ascii=False))

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
