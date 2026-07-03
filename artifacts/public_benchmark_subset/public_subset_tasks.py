#!/usr/bin/env python3
"""Controlled public-style terminal subset for Phase 4."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Mapping, Set

BENCHMARK_NAME = "local-terminal-public-subset-v0"
BENCHMARK_VERSION = "0.1.0"
BENCHMARK_KIND = "controlled_public_style_terminal_subset"

TASKS: List[Dict[str, Any]] = [
    {"task_id": "ltps-001", "name": "read baseline state", "required_ability": "a0", "points": 1.0},
    {"task_id": "ltps-002", "name": "verify appended memory a1", "required_ability": "a1", "points": 1.0},
    {"task_id": "ltps-003", "name": "replay certificate packet a2", "required_ability": "a2", "points": 1.0},
    {"task_id": "ltps-004", "name": "reject positive residual a3", "required_ability": "a3", "points": 1.0},
    {"task_id": "ltps-005", "name": "summarize successor trajectory a4", "required_ability": "a4", "points": 1.0},
    {"task_id": "ltps-006", "name": "audit terminal-style patch a5", "required_ability": "a5", "points": 1.0},
    {"task_id": "ltps-007", "name": "beyond-prefix challenge a6", "required_ability": "a6", "points": 1.0},
]


def extract_ability_sets_from_artifact(artifact: Mapping[str, Any]) -> Dict[str, Set[str]]:
    baseline: Set[str] = {"a0"}
    successor: Set[str] = set(baseline)
    # Preferred layout from closed-loop canonical artifacts.
    abilities = artifact.get("abilities")
    if isinstance(abilities, list) and abilities and isinstance(abilities[-1], list):
        successor.update(str(x) for x in abilities[-1])
    # Alternate layouts from generated/reference artifacts.
    ability_sets = artifact.get("ability_sets")
    if isinstance(ability_sets, Mapping):
        final = ability_sets.get("successor") or ability_sets.get("final") or ability_sets.get("A_N")
        if isinstance(final, list):
            successor.update(str(x) for x in final)
    for key in ["updates", "steps", "trajectory", "accepted_updates"]:
        seq = artifact.get(key)
        if isinstance(seq, list):
            for item in seq:
                if isinstance(item, Mapping):
                    for f in ["new_ability", "ability", "ability_added"]:
                        if f in item:
                            successor.add(str(item[f]))
                    update_text = str(item.get("update", item.get("accepted_update", "")))
                else:
                    update_text = str(item)
                if "AppendMem(a" in update_text:
                    start = update_text.find("AppendMem(") + len("AppendMem(")
                    end = update_text.find(")", start)
                    if end > start:
                        successor.add(update_text[start:end])
    N = artifact.get("N")
    if not isinstance(N, int):
        N = artifact.get("horizon_N")
    if isinstance(N, int):
        for i in range(1, N + 1):
            successor.add(f"a{i}")
    return {"baseline": baseline, "successor": successor}


def evaluate_tasks(abilities: Iterable[str]) -> Dict[str, Any]:
    ability_set = set(abilities)
    total = sum(float(t.get("points", 1.0)) for t in TASKS)
    score = 0.0
    results: List[Dict[str, Any]] = []
    for task in TASKS:
        points = float(task.get("points", 1.0))
        solved = str(task["required_ability"]) in ability_set
        score += points if solved else 0.0
        results.append({
            "task_id": task["task_id"],
            "name": task["name"],
            "required_ability": task["required_ability"],
            "points": points,
            "solved": solved,
            "score": points if solved else 0.0,
        })
    return {
        "score": 0.0 if total == 0 else score / total,
        "raw_points": score,
        "max_points": total,
        "tasks_solved": sum(1 for r in results if r["solved"]),
        "tasks_total": len(results),
        "task_results": results,
    }
