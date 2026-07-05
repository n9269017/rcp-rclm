#!/usr/bin/env python3
"""Build baseline and successor sample files for official EvalPlus CLI evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


REPO = Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_task_ids(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Build official EvalPlus baseline/successor samples")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--successor-source", type=Path, required=True)
    p.add_argument("--task-list", type=Path, required=True)
    p.add_argument("--outdir", type=Path, default=REPO / "artifacts" / "evalplus_official" / "samples")
    args = p.parse_args()

    task_ids = read_task_ids(args.task_list)
    src_rows = read_jsonl(args.successor_source)
    src_by_id = {r["task_id"]: r for r in src_rows}

    missing = [tid for tid in task_ids if tid not in src_by_id]
    if missing:
        raise SystemExit(f"successor source missing task IDs: {missing[:20]}")

    successor_rows = []
    for tid in task_ids:
        row = src_by_id[tid]
        out = {"task_id": tid}
        if "solution" in row:
            out["solution"] = row["solution"]
        elif "completion" in row:
            out["completion"] = row["completion"]
        else:
            raise SystemExit(f"task {tid} has neither solution nor completion")
        successor_rows.append(out)

    baseline_rows = [{"task_id": tid, "solution": ""} for tid in task_ids]
    count = len(task_ids)
    prefix = f"{args.dataset}_{count}"

    baseline_path = args.outdir / f"{prefix}_baseline_empty.jsonl"
    successor_path = args.outdir / f"{prefix}_successor.jsonl"
    write_jsonl(baseline_path, baseline_rows)
    write_jsonl(successor_path, successor_rows)

    print(json.dumps({
        "ok": True,
        "dataset": args.dataset,
        "task_count": count,
        "baseline_samples": str(baseline_path),
        "successor_samples": str(successor_path),
        "successor_source": str(args.successor_source),
        "task_list": str(args.task_list),
        "next": "Run run_evalplus_official.py on both sample files.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
