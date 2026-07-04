#!/usr/bin/env python3
"""Merge Phase 4C-D2 HumanEval chunk files into a full 164-task sample file.

By default this refuses to write the final file if any TODO/placeholder remains.
Use --allow-todo only to regenerate a draft file, never for a benchmark claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "artifacts" / "evalplus_leaderboard"
DEFAULT_WORKSPACE = ROOT / "full_164_workspace"
DEFAULT_OUT = ROOT / "successor_samples_non_oracle_HumanEval_full.jsonl"
TODO_NEEDLES = ["TODO", "REPLACE_WITH", "placeholder", "non-oracle generated complete solution"]
EXPECTED_IDS = [f"HumanEval/{i}" for i in range(164)]


def read_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid JSON in {path} line {line_no}: {e}") from e
    return rows


def is_todo(sol: str) -> bool:
    low = sol.lower()
    return any(n.lower() in low for n in TODO_NEEDLES)


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge HumanEval full-suite chunk samples")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--allow-todo", action="store_true", help="Allow TODO placeholders; for draft only")
    args = ap.parse_args()

    chunks_dir = args.workspace / "chunks"
    if not chunks_dir.exists():
        raise SystemExit(f"Missing chunks directory: {chunks_dir}")
    chunk_files = sorted(chunks_dir.glob("humaneval_*.jsonl"))
    if not chunk_files:
        raise SystemExit(f"No chunk files found in {chunks_dir}")

    by_id: Dict[str, dict] = {}
    duplicates: List[str] = []
    todo: List[str] = []
    malformed: List[str] = []
    for path in chunk_files:
        for row in read_jsonl(path):
            tid = row.get("task_id")
            sol = row.get("solution", row.get("completion"))
            if not isinstance(tid, str) or not isinstance(sol, str) or not sol.strip():
                malformed.append(f"{path}:{row}")
                continue
            if tid in by_id:
                duplicates.append(tid)
            by_id[tid] = {"task_id": tid, "solution": sol}
            if is_todo(sol):
                todo.append(tid)

    missing = [tid for tid in EXPECTED_IDS if tid not in by_id]
    extra = sorted(set(by_id) - set(EXPECTED_IDS))
    errors = {
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "malformed_count": len(malformed),
        "todo_count": len(todo),
        "todo_first_20": todo[:20],
    }
    if missing or extra or duplicates or malformed:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    if todo and not args.allow_todo:
        print(json.dumps({
            "ok": False,
            "reason": "TODO placeholders remain; refusing to create claimable full sample file",
            "errors": errors,
            "hint": "Edit the chunk files, remove TODOs, then rerun without --allow-todo.",
        }, indent=2))
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    ordered = [by_id[tid] for tid in EXPECTED_IDS]
    args.out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in ordered) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "out": str(args.out.relative_to(REPO)).replace("\\", "/"),
        "task_count": len(ordered),
        "todo_count": len(todo),
        "claimable_candidate": not bool(todo),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
