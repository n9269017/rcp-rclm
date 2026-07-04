#!/usr/bin/env python3
"""Validate EvalPlus sample JSONL coverage before running evaluations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List


def load_problems(dataset: str) -> Dict[str, Dict[str, Any]]:
    if dataset == "humaneval":
        from evalplus.data import get_human_eval_plus
        return dict(get_human_eval_plus())
    if dataset == "mbpp":
        from evalplus.data import get_mbpp_plus
        return dict(get_mbpp_plus())
    raise ValueError(f"unsupported dataset: {dataset}")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"invalid JSONL line {i}: {e}") from e
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Validate EvalPlus sample coverage")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--samples", type=Path, required=True)
    p.add_argument("--task-list", type=Path, default=None)
    p.add_argument("--full", action="store_true")
    p.add_argument("--allow-todo", action="store_true")
    args = p.parse_args()

    problems = load_problems(args.dataset)
    if args.full:
        expected = list(problems.keys())
    elif args.task_list:
        expected = [x.strip() for x in args.task_list.read_text(encoding="utf-8").splitlines() if x.strip()]
    else:
        expected = list(problems.keys())

    rows = read_jsonl(args.samples)
    seen: Dict[str, Dict[str, Any]] = {}
    duplicates = []
    malformed = []
    todo_like = []
    for row in rows:
        tid = row.get("task_id")
        if not tid:
            malformed.append({"row": row, "reason": "missing task_id"})
            continue
        if tid in seen:
            duplicates.append(tid)
        seen[tid] = row
        body = str(row.get("solution", row.get("completion", "")))
        if not body.strip():
            malformed.append({"task_id": tid, "reason": "empty solution/completion"})
        if ("TODO" in body or "replace" in body.lower()) and not args.allow_todo:
            todo_like.append(tid)

    missing = [tid for tid in expected if tid not in seen]
    extra = [tid for tid in seen if tid not in set(expected)]
    ok = not missing and not duplicates and not malformed and not todo_like
    result = {
        "ok": ok,
        "dataset": args.dataset,
        "samples": str(args.samples),
        "expected_tasks": len(expected),
        "provided_tasks": len(seen),
        "missing": missing,
        "duplicates": duplicates,
        "malformed": malformed,
        "todo_like": todo_like,
        "extra": extra,
        "full_dataset": bool(args.full),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
