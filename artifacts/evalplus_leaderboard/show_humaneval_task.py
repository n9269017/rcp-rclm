#!/usr/bin/env python3
"""Print public prompt material for a HumanEval task exported by Phase 4C."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASKS = REPO / "artifacts" / "evalplus_leaderboard" / "tasks" / "humaneval" / "humaneval_public_tasks.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description="Show exported public HumanEval prompt")
    ap.add_argument("task_id")
    args = ap.parse_args()
    if not TASKS.exists():
        raise SystemExit(f"Missing {TASKS}. Run export_evalplus_tasks.py --dataset humaneval first.")
    for line in TASKS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("task_id") == args.task_id:
            print("task_id:", row.get("task_id"))
            print("entry_point:", row.get("entry_point"))
            print("\nprompt:\n")
            print(row.get("prompt", ""))
            return 0
    raise SystemExit(f"Task not found: {args.task_id}")


if __name__ == "__main__":
    raise SystemExit(main())
