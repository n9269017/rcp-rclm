#!/usr/bin/env python3
"""Build the final 164-task HumanEval sample file from the passed 144-task file
plus the HumanEval/144--163 final expansion block.

This script performs strict coverage checks:
- exactly HumanEval/0--HumanEval/163,
- no duplicate task IDs,
- no missing task IDs,
- no extra task IDs,
- no TODO-like placeholder solutions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parent
TASKS = ROOT / "tasks" / "humaneval"
SOURCE_0_143 = ROOT / "successor_samples_non_oracle_HumanEval_144.jsonl"
SOURCE_144_163 = ROOT / "successor_samples_non_oracle_HumanEval_144_163.jsonl"
OUT = ROOT / "successor_samples_non_oracle_HumanEval_164.jsonl"
TASK_IDS = TASKS / "humaneval_task_ids_164.txt"

TODO_MARKERS = [
    "TODO",
    "REPLACE_WITH",
    "replace with a non-oracle",
    "placeholder",
]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception as e:
                raise SystemExit(f"Malformed JSON at {path}:{lineno}: {e}") from e
            if "task_id" not in row or not ("solution" in row or "completion" in row):
                raise SystemExit(f"Missing task_id/solution-or-completion at {path}:{lineno}")
            rows.append(row)
    return rows


def task_id_num(task_id: str) -> int:
    prefix = "HumanEval/"
    if not task_id.startswith(prefix):
        raise ValueError(task_id)
    return int(task_id[len(prefix):])


def todo_like(row: Dict[str, Any]) -> bool:
    text = str(row.get("solution", row.get("completion", "")))
    upper = text.upper()
    return any(marker.upper() in upper for marker in TODO_MARKERS)


def update_workspace_chunks(rows: List[Dict[str, Any]]) -> List[str]:
    workspace = ROOT / "full_164_workspace"
    if not workspace.exists():
        return []

    by_id = {row["task_id"]: row for row in rows}
    updated: List[str] = []
    for chunk in workspace.glob("chunks/*.jsonl"):
        original = read_jsonl(chunk)
        changed = False
        new_rows = []
        for row in original:
            tid = row["task_id"]
            if tid in by_id:
                new_rows.append(by_id[tid])
                changed = True
            else:
                new_rows.append(row)
        if changed:
            chunk.write_text("\n".join(json.dumps(r) for r in new_rows) + "\n", encoding="utf-8")
            updated.append(str(chunk))
    return updated


def main() -> int:
    if not SOURCE_0_143.exists():
        raise SystemExit(f"Missing required 0--143 source: {SOURCE_0_143}")
    if not SOURCE_144_163.exists():
        raise SystemExit(f"Missing required 144--163 source: {SOURCE_144_163}")

    rows = read_jsonl(SOURCE_0_143) + read_jsonl(SOURCE_144_163)
    expected = [f"HumanEval/{i}" for i in range(164)]
    ids = [r["task_id"] for r in rows]

    missing = [tid for tid in expected if tid not in ids]
    extra = [tid for tid in ids if tid not in expected]
    duplicates = sorted({tid for tid in ids if ids.count(tid) > 1})
    todos = [r["task_id"] for r in rows if todo_like(r)]

    ok = not (missing or extra or duplicates or todos) and len(rows) == 164

    if not ok:
        print(json.dumps({
            "ok": False,
            "source_0_143": str(SOURCE_0_143),
            "source_144_163": str(SOURCE_144_163),
            "provided_rows": len(rows),
            "missing": missing,
            "extra": extra,
            "duplicates": duplicates,
            "todo_like": todos,
        }, indent=2))
        raise SystemExit(1)

    rows = sorted(rows, key=lambda r: task_id_num(r["task_id"]))
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    TASK_IDS.write_text("\n".join(expected) + "\n", encoding="utf-8")

    updated = update_workspace_chunks(rows)

    print(json.dumps({
        "ok": True,
        "wrote": str(OUT),
        "task_ids": str(TASK_IDS),
        "task_count": len(rows),
        "source_0_143": str(SOURCE_0_143),
        "source_144_163": str(SOURCE_144_163),
        "workspace_chunks_updated": updated,
        "claimable_result": False,
        "next_required_step": "Run validate_evalplus_samples.py, then run base-only canonical HumanEval and direct EvalPlus-mini 164-task sidecars.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
