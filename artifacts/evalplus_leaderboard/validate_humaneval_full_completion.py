#!/usr/bin/env python3
"""Validate a candidate full 164-task HumanEval+ successor samples JSONL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "artifacts" / "evalplus_leaderboard"
DEFAULT_SAMPLES = ROOT / "successor_samples_non_oracle_HumanEval_full.jsonl"
EXPECTED_IDS = [f"HumanEval/{i}" for i in range(164)]
TODO_NEEDLES = ["TODO", "REPLACE_WITH", "placeholder", "non-oracle generated complete solution"]


def read_jsonl(path: Path) -> List[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            rows.append({"__malformed__": f"line {line_no}: {e}"})
    return rows


def is_todo(sol: str) -> bool:
    low = sol.lower()
    return any(n.lower() in low for n in TODO_NEEDLES)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate full HumanEval sample file")
    ap.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    ap.add_argument("--allow-todo", action="store_true")
    args = ap.parse_args()

    if not args.samples.exists():
        print(json.dumps({"ok": False, "missing_file": str(args.samples)}, indent=2))
        return 1
    rows = read_jsonl(args.samples)
    by_id: Dict[str, str] = {}
    malformed = []
    duplicates = []
    todo = []
    empty = []
    for row in rows:
        if "__malformed__" in row:
            malformed.append(row["__malformed__"])
            continue
        tid = row.get("task_id")
        sol = row.get("solution", row.get("completion"))
        if not isinstance(tid, str) or not isinstance(sol, str):
            malformed.append(str(row)[:300])
            continue
        if tid in by_id:
            duplicates.append(tid)
        by_id[tid] = sol
        if not sol.strip():
            empty.append(tid)
        if is_todo(sol):
            todo.append(tid)
    missing = [tid for tid in EXPECTED_IDS if tid not in by_id]
    extra = sorted(set(by_id) - set(EXPECTED_IDS))
    ok = not (malformed or duplicates or missing or extra or empty or (todo and not args.allow_todo))
    out = {
        "ok": ok,
        "samples": str(args.samples).replace("\\", "/"),
        "expected_tasks": 164,
        "provided_tasks": len(by_id),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "malformed_count": len(malformed),
        "empty": empty,
        "todo_count": len(todo),
        "todo_first_20": todo[:20],
        "claimable_candidate": ok and not todo,
    }
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
