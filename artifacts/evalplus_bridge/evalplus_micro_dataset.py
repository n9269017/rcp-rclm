#!/usr/bin/env python3
"""Micro-dataset/sample helpers for EvalPlus HumanEval+/MBPP+ adapter."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_jsonl_gz(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_evalplus_problems(dataset: str) -> Dict[str, dict]:
    if dataset == "humaneval":
        from evalplus.data import get_human_eval_plus
        return dict(get_human_eval_plus())
    if dataset == "mbpp":
        from evalplus.data import get_mbpp_plus
        return dict(get_mbpp_plus())
    raise ValueError(f"Unsupported dataset: {dataset}")


def select_tasks(dataset: str, task_ids: List[str]) -> Dict[str, dict]:
    problems = load_evalplus_problems(dataset)
    missing = [tid for tid in task_ids if tid not in problems]
    if missing:
        raise KeyError(f"Task IDs not found in EvalPlus {dataset}: {missing}")
    return {tid: problems[tid] for tid in task_ids}


def make_override_dataset(dataset: str, task_ids: List[str], out_path: Path) -> Dict[str, dict]:
    selected = select_tasks(dataset, task_ids)
    rows = []
    for task_id, problem in selected.items():
        row = dict(problem)
        row["task_id"] = task_id
        rows.append(row)
    write_jsonl_gz(out_path, rows)
    return selected


def make_baseline_samples(task_ids: List[str], out_path: Path) -> None:
    rows = []
    for task_id in task_ids:
        rows.append({
            "task_id": task_id,
            "completion": "\n    pass\n"
        })
    write_jsonl(out_path, rows)


def make_oracle_successor_samples(dataset: str, task_ids: List[str], out_path: Path) -> None:
    """Diagnostic only: uses canonical solutions. Not claimable as non-oracle."""
    selected = select_tasks(dataset, task_ids)
    rows = []
    for task_id, problem in selected.items():
        prompt = problem.get("prompt", "")
        canonical = problem.get("canonical_solution", "")
        if not canonical:
            raise ValueError(f"No canonical_solution found for {task_id}")
        rows.append({
            "task_id": task_id,
            "solution": prompt + canonical
        })
    write_jsonl(out_path, rows)
