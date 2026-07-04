#!/usr/bin/env python3
"""Phase 4C-D2: create a full 164-task HumanEval+ coverage workspace.

This script does not claim a full-suite pass.  It creates a reproducible
workspace for moving from the already-passed 20-task sidecar to full 164-task
coverage without accidentally treating TODO placeholders as benchmark results.

Default inputs are the files produced by Phase 4C and Phase 4C-D1:
  artifacts/evalplus_leaderboard/tasks/humaneval/humaneval_task_ids.txt
  artifacts/evalplus_leaderboard/tasks/humaneval/humaneval_public_tasks.jsonl
  artifacts/evalplus_leaderboard/successor_samples_non_oracle_HumanEval_20.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "artifacts" / "evalplus_leaderboard"
TASK_DIR = ROOT / "tasks" / "humaneval"
DEFAULT_IDS = TASK_DIR / "humaneval_task_ids.txt"
DEFAULT_PUBLIC = TASK_DIR / "humaneval_public_tasks.jsonl"
DEFAULT_20 = ROOT / "successor_samples_non_oracle_HumanEval_20.jsonl"
DEFAULT_OUT = ROOT / "full_164_workspace"
TODO_MARKER = "TODO_D2_FULL_164_REPLACE_WITH_NON_ORACLE_SOLUTION"


@dataclass
class ChunkRecord:
    chunk: str
    first_index: int
    last_index: int
    task_count: int
    solved_from_seed: int
    todo_count: int
    path: str
    task_list_path: str


def read_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid JSONL in {path} line {line_no}: {e}") from e
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def read_task_ids(path: Path) -> List[str]:
    ids = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(ids) != 164:
        raise SystemExit(f"Expected 164 HumanEval task IDs in {path}, found {len(ids)}")
    expected = [f"HumanEval/{i}" for i in range(164)]
    if ids != expected:
        missing = sorted(set(expected) - set(ids))[:10]
        extra = sorted(set(ids) - set(expected))[:10]
        raise SystemExit(f"Unexpected HumanEval ID list. First missing={missing}, first extra={extra}")
    return ids


def load_public_tasks(path: Path) -> Dict[str, dict]:
    return {str(r.get("task_id")): r for r in read_jsonl(path) if r.get("task_id")}


def load_seed_solutions(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for row in read_jsonl(path):
        tid = row.get("task_id")
        sol = row.get("solution", row.get("completion"))
        if isinstance(tid, str) and isinstance(sol, str) and sol.strip():
            out[tid] = sol
    return out


def prompt_excerpt(public: Dict[str, dict], task_id: str, max_chars: int = 900) -> str:
    p = str(public.get(task_id, {}).get("prompt", ""))
    p = p.replace("\r\n", "\n").strip()
    if len(p) > max_chars:
        p = p[:max_chars] + "\n... [truncated; see humaneval_public_tasks.jsonl]"
    return p


def todo_solution(task_id: str, public: Dict[str, dict]) -> str:
    excerpt = prompt_excerpt(public, task_id)
    comment = "\n".join("# " + line for line in excerpt.splitlines()) if excerpt else "# Prompt not found in exported public tasks."
    return (
        f"# {TODO_MARKER}\n"
        f"# Task: {task_id}\n"
        f"# Replace this entire solution string with a complete non-oracle generated solution.\n"
        f"# Public prompt excerpt follows for convenience only; do not treat this as a solution.\n"
        f"{comment}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Create HumanEval+ full-164 coverage workspace")
    ap.add_argument("--task-ids", type=Path, default=DEFAULT_IDS)
    ap.add_argument("--public-tasks", type=Path, default=DEFAULT_PUBLIC)
    ap.add_argument("--seed-samples", type=Path, default=DEFAULT_20)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--chunk-size", type=int, default=20)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    if args.outdir.exists() and any(args.outdir.iterdir()) and not args.overwrite:
        raise SystemExit(f"Refusing to overwrite nonempty workspace {args.outdir}; rerun with --overwrite")

    ids = read_task_ids(args.task_ids)
    public = load_public_tasks(args.public_tasks)
    seeds = load_seed_solutions(args.seed_samples)

    args.outdir.mkdir(parents=True, exist_ok=True)
    chunks_dir = args.outdir / "chunks"
    lists_dir = args.outdir / "task_lists"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    lists_dir.mkdir(parents=True, exist_ok=True)

    full_rows: List[dict] = []
    records: List[ChunkRecord] = []
    for start in range(0, len(ids), args.chunk_size):
        part = ids[start:start + args.chunk_size]
        end = start + len(part) - 1
        rows: List[dict] = []
        solved = 0
        todo = 0
        for tid in part:
            if tid in seeds:
                rows.append({"task_id": tid, "solution": seeds[tid]})
                solved += 1
            else:
                rows.append({"task_id": tid, "solution": todo_solution(tid, public)})
                todo += 1
        name = f"humaneval_{start:03d}_{end:03d}.jsonl"
        list_name = f"humaneval_task_ids_{start:03d}_{end:03d}.txt"
        chunk_path = chunks_dir / name
        task_list_path = lists_dir / list_name
        write_jsonl(chunk_path, rows)
        task_list_path.write_text("\n".join(part) + "\n", encoding="utf-8")
        full_rows.extend(rows)
        records.append(ChunkRecord(
            chunk=f"{start:03d}_{end:03d}",
            first_index=start,
            last_index=end,
            task_count=len(part),
            solved_from_seed=solved,
            todo_count=todo,
            path=str(chunk_path.relative_to(REPO)).replace("\\", "/"),
            task_list_path=str(task_list_path.relative_to(REPO)).replace("\\", "/"),
        ))

    draft = args.outdir / "successor_samples_non_oracle_HumanEval_full.DRAFT_TODO.jsonl"
    write_jsonl(draft, full_rows)

    ids_full = TASK_DIR / "humaneval_task_ids_full.txt"
    ids_full.parent.mkdir(parents=True, exist_ok=True)
    ids_full.write_text("\n".join(ids) + "\n", encoding="utf-8")

    manifest = {
        "phase": "Phase 4C-D2: Full 164-task HumanEval+ coverage preparation",
        "status": "workspace_prepared_not_full_pass",
        "claim_boundary": {
            "full_164_successor_samples_complete": False,
            "direct_full_suite_sidecar_run": False,
            "official_evalplus_leaderboard_result": False,
            "claimable_full_suite_improvement": False,
            "todo_placeholders_present": True,
        },
        "task_count": len(ids),
        "seed_samples_path": str(args.seed_samples.relative_to(REPO)).replace("\\", "/") if args.seed_samples.exists() else str(args.seed_samples),
        "seed_solution_count": sum(1 for tid in ids if tid in seeds),
        "todo_count": sum(1 for tid in ids if tid not in seeds),
        "draft_todo_path": str(draft.relative_to(REPO)).replace("\\", "/"),
        "task_ids_full_path": str(ids_full.relative_to(REPO)).replace("\\", "/"),
        "chunk_size": args.chunk_size,
        "chunks": [asdict(r) for r in records],
        "next_required_action": "Replace all TODO solutions in chunk files, merge with merge_humaneval_full_samples.py, validate, then run certified_evalplus_suite_harness.py --full.",
    }
    (args.outdir / "full_workspace_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    csv_path = args.outdir / "chunk_status.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
        w.writeheader()
        for rec in records:
            w.writerow(asdict(rec))

    print(json.dumps({
        "ok": True,
        "workspace": str(args.outdir.relative_to(REPO)).replace("\\", "/"),
        "task_count": len(ids),
        "seed_solution_count": manifest["seed_solution_count"],
        "todo_count": manifest["todo_count"],
        "draft_todo_path": manifest["draft_todo_path"],
        "manifest": str((args.outdir / "full_workspace_manifest.json").relative_to(REPO)).replace("\\", "/"),
        "claimable_full_suite_improvement": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
