#!/usr/bin/env python3
"""RCLM wrapper for the shared closed-loop certified successor generator."""
from __future__ import annotations

import sys
from pathlib import Path

THIS = Path(__file__).resolve()
ROOT = THIS.parents[2]
COMMON = ROOT / "artifacts" / "common"
sys.path.insert(0, str(COMMON))

from closed_loop_reference_engine import main as common_main  # noqa: E402

if __name__ == "__main__":
    argv = ["--mode", "rclm"] + sys.argv[1:]
    common_main(argv)
