#!/usr/bin/env python3
"""Phase 4C-D2d: build HumanEval+ 144-task sample file.

This script merges the already-passed 0--119 successor sample file with the
new 120--143 sample file, validates coverage, writes the 144-task aggregate,
and updates the optional full_164_workspace chunk files if present.

It deliberately does not run the evaluator and does not claim a result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parents[2]
LEADER = ROOT / "artifacts" / "evalplus_leaderboard"
SRC_0_119 = LEADER / "successor_samples_non_oracle_HumanEval_120.jsonl"
SRC_120_143 = LEADER / "successor_samples_non_oracle_HumanEval_120_143.jsonl"
OUT_144 = LEADER / "successor_samples_non_oracle_HumanEval_144.jsonl"
TASK_IDS_144 = LEADER / "tasks" / "humaneval" / "humaneval_task_ids_144.txt"


TODO_MARKERS = [
    "TODO",
    "REPLACE_WITH",
    "placeholder",
    "complete non-oracle generated solution",
]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Malformed JSON in {path} line {line_no}: {e}") from e
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def validate_rows(rows: List[Dict[str, Any]], expected: List[str]) -> Dict[str, Any]:
    seen: Dict[str, int] = {}
    malformed = []
    todo_like = []
    for idx, row in enumerate(rows, start=1):
        tid = row.get("task_id")
        sol = row.get("solution", row.get("completion"))
        if not isinstance(tid, str) or not isinstance(sol, str) or not sol.strip():
            malformed.append({"line": idx, "task_id": tid})
            continue
        seen[tid] = seen.get(tid, 0) + 1
        if any(marker.lower() in sol.lower() for marker in TODO_MARKERS):
            todo_like.append(tid)

    provided = set(seen)
    expected_set = set(expected)
    missing = [tid for tid in expected if tid not in provided]
    extra = sorted(provided - expected_set, key=lambda x: int(x.split("/")[-1]) if "/" in x else 999999)
    duplicates = sorted([tid for tid, count in seen.items() if count > 1], key=lambda x: int(x.split("/")[-1]) if "/" in x else 999999)

    ok = not (missing or extra or duplicates or malformed or todo_like) and len(rows) == len(expected)
    return {
        "ok": ok,
        "expected_tasks": len(expected),
        "provided_tasks": len(rows),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "malformed": malformed,
        "todo_like": todo_like,
    }


def update_workspace_chunks(rows_120_143: List[Dict[str, Any]]) -> List[str]:
    workspace = LEADER / "full_164_workspace"
    if not workspace.exists():
        return []

    by_id = {row["task_id"]: row for row in rows_120_143}
    updated = []

    # Replace 120--139 in the 120--139 chunk.
    chunk_120_139 = workspace / "chunks" / "humaneval_120_139.jsonl"
    if chunk_120_139.exists():
        rows = read_jsonl(chunk_120_139)
        out_rows = []
        for row in rows:
            out_rows.append(by_id.get(row.get("task_id"), row))
        write_jsonl(chunk_120_139, out_rows)
        updated.append(str(chunk_120_139))

    # Replace 140--143 inside the 140--159 chunk, leaving 144--159 TODOs intact.
    chunk_140_159 = workspace / "chunks" / "humaneval_140_159.jsonl"
    if chunk_140_159.exists():
        rows = read_jsonl(chunk_140_159)
        out_rows = []
        for row in rows:
            out_rows.append(by_id.get(row.get("task_id"), row))
        write_jsonl(chunk_140_159, out_rows)
        updated.append(str(chunk_140_159))

    return updated


def main() -> int:
    if not SRC_0_119.exists():
        raise SystemExit(f"Missing required 0--119 source file: {SRC_0_119}")
    if not SRC_120_143.exists():
        raise SystemExit(f"Missing required 120--143 source file: {SRC_120_143}")

    rows_0_119 = read_jsonl(SRC_0_119)
    rows_120_143 = read_jsonl(SRC_120_143)

    expected_120_143 = [f"HumanEval/{i}" for i in range(120, 144)]
    v_chunk = validate_rows(rows_120_143, expected_120_143)
    if not v_chunk["ok"]:
        print(json.dumps({"ok": False, "stage": "120_143_chunk", **v_chunk}, indent=2))
        return 1

    rows = rows_0_119 + rows_120_143
    expected_144 = [f"HumanEval/{i}" for i in range(144)]
    v_all = validate_rows(rows, expected_144)
    if not v_all["ok"]:
        print(json.dumps({"ok": False, "stage": "aggregate_144", **v_all}, indent=2))
        return 1

    write_jsonl(OUT_144, rows)
    TASK_IDS_144.parent.mkdir(parents=True, exist_ok=True)
    TASK_IDS_144.write_text("\n".join(expected_144) + "\n", encoding="utf-8")

    workspace_updates = update_workspace_chunks(rows_120_143)

    print(json.dumps({
        "ok": True,
        "wrote": str(OUT_144),
        "task_ids": str(TASK_IDS_144),
        "task_count": 144,
        "source_0_119": str(SRC_0_119),
        "source_120_143": str(SRC_120_143),
        "workspace_chunks_updated": workspace_updates,
        "claimable_result": False,
        "next_required_step": "Run validate_evalplus_samples.py and certified_evalplus_suite_harness.py for the 144-task sidecar."
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
