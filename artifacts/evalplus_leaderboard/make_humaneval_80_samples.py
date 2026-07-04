#!/usr/bin/env python3
"""Phase 4C-D2b helper: build the HumanEval+ 80-task sample file.

This script is intentionally conservative. It does not synthesize new answers.
It merges the already-passed 0--39 sample file with the supplied 40--79 sample
file, validates exact task coverage, rejects TODO placeholders, and writes the
80-task JSONL plus task-id list. If the full_164_workspace exists, it also
updates the corresponding 040--059 and 060--079 chunk files so later full-suite
merging remains synchronized.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
LEADER = ROOT / "artifacts" / "evalplus_leaderboard"
FIRST40 = LEADER / "successor_samples_non_oracle_HumanEval_40.jsonl"
NEXT40 = LEADER / "successor_samples_non_oracle_HumanEval_40_79.jsonl"
OUT80 = LEADER / "successor_samples_non_oracle_HumanEval_80.jsonl"
TASK80 = LEADER / "tasks" / "humaneval" / "humaneval_task_ids_80.txt"
WORKSPACE = LEADER / "full_164_workspace"

TODO_MARKERS = ("TODO", "REPLACE_WITH", "placeholder", "Public prompt excerpt")

def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as e:
            raise ValueError(f"Malformed JSON at {path}:{line_no}: {e}") from e
        if "task_id" not in row or not ("solution" in row or "completion" in row):
            raise ValueError(f"Malformed sample at {path}:{line_no}: expected task_id and solution/completion")
        rows.append(row)
    return rows

def assert_exact(rows: List[dict], start: int, end_exclusive: int, label: str) -> None:
    expected = [f"HumanEval/{i}" for i in range(start, end_exclusive)]
    seen = [r.get("task_id") for r in rows]
    missing = [x for x in expected if x not in seen]
    extra = [x for x in seen if x not in expected]
    dupes = sorted({x for x in seen if seen.count(x) > 1})
    todo = []
    for r in rows:
        text = str(r.get("solution", r.get("completion", "")))
        if any(marker.lower() in text.lower() for marker in TODO_MARKERS):
            todo.append(r.get("task_id"))
    errors = {"missing": missing, "extra": extra, "duplicates": dupes, "todo_like": todo}
    if any(errors.values()):
        raise ValueError(f"{label} failed coverage validation: {json.dumps(errors, indent=2)}")

def write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def main() -> int:
    first40 = read_jsonl(FIRST40)
    next40 = read_jsonl(NEXT40)
    assert_exact(first40, 0, 40, "existing 0--39 sample")
    assert_exact(next40, 40, 80, "new 40--79 sample")
    combined = first40 + next40
    assert_exact(combined, 0, 80, "combined 0--79 sample")

    write_jsonl(OUT80, combined)
    TASK80.parent.mkdir(parents=True, exist_ok=True)
    TASK80.write_text("\n".join(f"HumanEval/{i}" for i in range(80)) + "\n", encoding="utf-8")

    updated_chunks = []
    if WORKSPACE.exists():
        chunks = WORKSPACE / "chunks"
        task_lists = WORKSPACE / "task_lists"
        task_lists.mkdir(parents=True, exist_ok=True)
        rows_by_id: Dict[str, dict] = {r["task_id"]: r for r in next40}
        for start in (40, 60):
            end = start + 20
            chunk_rows = [rows_by_id[f"HumanEval/{i}"] for i in range(start, end)]
            chunk_path = chunks / f"humaneval_{start:03d}_{end-1:03d}.jsonl"
            list_path = task_lists / f"humaneval_task_ids_{start}_{end-1}.txt"
            write_jsonl(chunk_path, chunk_rows)
            list_path.write_text("\n".join(f"HumanEval/{i}" for i in range(start, end)) + "\n", encoding="utf-8")
            updated_chunks.append(str(chunk_path))

    summary = {
        "ok": True,
        "wrote": str(OUT80).replace("\\", "/"),
        "task_ids": str(TASK80).replace("\\", "/"),
        "task_count": len(combined),
        "source_0_39": str(FIRST40).replace("\\", "/"),
        "source_40_79": str(NEXT40).replace("\\", "/"),
        "workspace_chunks_updated": updated_chunks,
        "claimable_result": False,
        "next_required_step": "Run validate_evalplus_samples.py and certified_evalplus_suite_harness.py for the 80-task sidecar."
    }
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
