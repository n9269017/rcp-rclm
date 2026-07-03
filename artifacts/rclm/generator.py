#!/usr/bin/env python3
"""RCLM convenience wrapper for the open-loop arbitrary-horizon generator."""
from __future__ import annotations
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMON = ROOT / "artifacts" / "common" / "generate_reference_artifact.py"

if "--mode" not in sys.argv:
    sys.argv.extend(["--mode", "rclm"])
if "--out" not in sys.argv:
    N = "3"
    if "--N" in sys.argv:
        idx = sys.argv.index("--N")
        if idx + 1 < len(sys.argv):
            N = sys.argv[idx + 1]
    sys.argv.extend(["--out", str(HERE / f"generated_artifact_N{N}.json")])
if "--runlog" not in sys.argv:
    N = "3"
    if "--N" in sys.argv:
        idx = sys.argv.index("--N")
        if idx + 1 < len(sys.argv):
            N = sys.argv[idx + 1]
    sys.argv.extend(["--runlog", str(HERE / f"generated_runlog_N{N}.json")])
runpy.run_path(str(COMMON), run_name="__main__")
