#!/usr/bin/env python3
"""Export EvalPlus public task prompts and blank sample templates.

This script does not export canonical solutions.  It is for producing the
non-oracle prompt/task material needed to generate model/agent samples.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_problems(dataset: str) -> Dict[str, Dict[str, Any]]:
    if dataset == "humaneval":
        from evalplus.data import get_human_eval_plus
        return dict(get_human_eval_plus())
    if dataset == "mbpp":
        from evalplus.data import get_mbpp_plus
        return dict(get_mbpp_plus())
    raise ValueError(f"unsupported dataset: {dataset}")


def main() -> int:
    p = argparse.ArgumentParser(description="Export public EvalPlus prompts and sample templates")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--outdir", type=Path, default=None)
    p.add_argument("--limit", type=int, default=0, help="Optional first-N limit for small pilots")
    args = p.parse_args()

    repo = repo_root_from_script()
    outdir = args.outdir or (repo / "artifacts" / "evalplus_leaderboard" / "tasks" / args.dataset)
    outdir.mkdir(parents=True, exist_ok=True)

    problems = load_problems(args.dataset)
    task_ids = list(problems.keys())
    if args.limit and args.limit > 0:
        task_ids = task_ids[: args.limit]

    public_rows = []
    template_rows = []
    for tid in task_ids:
        problem = problems[tid]
        public_rows.append({
            "task_id": tid,
            "prompt": problem.get("prompt", ""),
            "entry_point": problem.get("entry_point", ""),
            "contract": problem.get("contract", ""),
            "metadata": problem.get("metadata", {}),
        })
        template_rows.append({
            "task_id": tid,
            "solution": "# TODO: replace with a non-oracle generated complete solution for this task\n"
        })

    tasks_jsonl = outdir / f"{args.dataset}_public_tasks.jsonl"
    ids_txt = outdir / f"{args.dataset}_task_ids.txt"
    template_jsonl = outdir / f"{args.dataset}_successor_samples_template.jsonl"

    with tasks_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for row in public_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    ids_txt.write_text("\n".join(task_ids) + "\n", encoding="utf-8")
    with template_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for row in template_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({
        "ok": True,
        "dataset": args.dataset,
        "task_count": len(task_ids),
        "tasks_jsonl": str(tasks_jsonl),
        "task_ids": str(ids_txt),
        "successor_template": str(template_jsonl),
        "oracle_solutions_exported": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
