#!/usr/bin/env python3
"""Local controlled mini benchmark tasks for B9-Bridge Phase 3.

This is a small deterministic benchmark used to test the certificate-preserving
benchmark sidecar protocol.  It is deliberately local and controlled; it is not
SWE-bench, RE-Bench, MLE-bench, Terminal-Bench, WebArena, or any other public
external benchmark.

Task semantics:
    - baseline M_0 has only ability a0;
    - successor M_N has the final ability set recorded in the generated artifact;
    - a task is solved exactly when its required ability is present.

This makes the benchmark auditable and fully reproducible while still showing a
before/after score delta tied to the accepted closed-loop updates.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set

BENCHMARK_NAME = "local-mini-terminal-v0"
BENCHMARK_VERSION = "0.1.0"


def task_suite() -> List[Dict[str, Any]]:
    """Return the fixed local mini task suite.

    Four tasks require the predecessor/base ability a0 and are solved by both
    M_0 and M_N.  Ten tasks require successive appended abilities a1..a10.  For
    N=5, the successor solves a1..a5 but not a6..a10.  For N=10, it solves the
    full task suite.
    """
    base_tasks = [
        ("base-000", "a0", "Load the canonical diagonal state and report its protected-pair role."),
        ("base-001", "a0", "Replay the predecessor verifier identity check."),
        ("base-002", "a0", "Read the baseline ability ledger and report a0."),
        ("base-003", "a0", "Confirm the no-hidden-update baseline condition."),
    ]
    successor_tasks = [
        ("succ-001", "a1", "Use AppendMem(a1) to satisfy a memory-extension query."),
        ("succ-002", "a2", "Use AppendMem(a2) to retrieve the second extension witness."),
        ("succ-003", "a3", "Use AppendMem(a3) to reconstruct a recovery-ledger step."),
        ("succ-004", "a4", "Use AppendMem(a4) to emit a certificate-sidecar hash."),
        ("succ-005", "a5", "Use AppendMem(a5) to summarize a closed-loop runlog."),
        ("succ-006", "a6", "Use AppendMem(a6) to summarize an additional successor packet."),
        ("succ-007", "a7", "Use AppendMem(a7) to enumerate an added witness-library item."),
        ("succ-008", "a8", "Use AppendMem(a8) to report an added rejection-test class."),
        ("succ-009", "a9", "Use AppendMem(a9) to report an added tractability row."),
        ("succ-010", "a10", "Use AppendMem(a10) to solve the final local successor task."),
    ]
    rows: List[Dict[str, Any]] = []
    for task_id, required, description in [*base_tasks, *successor_tasks]:
        rows.append({
            "task_id": task_id,
            "required_ability": required,
            "weight": 1.0,
            "description": description,
            "scope": "controlled-local-certificate-preserving-mini-task",
        })
    return rows


def evaluate_tasks(abilities: Sequence[str]) -> Dict[str, Any]:
    ability_set: Set[str] = set(abilities)
    task_results: List[Dict[str, Any]] = []
    for task in task_suite():
        solved = task["required_ability"] in ability_set
        row = dict(task)
        row.update({
            "solved": solved,
            "available_abilities_contains_required": solved,
        })
        task_results.append(row)

    total_weight = sum(float(row["weight"]) for row in task_results)
    solved_weight = sum(float(row["weight"]) for row in task_results if row["solved"])
    score = solved_weight / total_weight if total_weight else 0.0
    return {
        "benchmark": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "abilities": sorted(ability_set),
        "score": score,
        "solved_count": sum(1 for row in task_results if row["solved"]),
        "tasks": len(task_results),
        "solved_weight": solved_weight,
        "total_weight": total_weight,
        "task_results": task_results,
    }


def extract_ability_sets_from_artifact(artifact: Mapping[str, Any]) -> Dict[str, List[str]]:
    abilities = artifact.get("abilities")
    if not isinstance(abilities, list) or not abilities:
        raise ValueError("artifact does not contain a nonempty abilities trajectory")
    baseline = abilities[0]
    successor = abilities[-1]
    if not isinstance(baseline, list) or not isinstance(successor, list):
        raise ValueError("artifact abilities trajectory entries must be lists")
    return {"baseline": list(baseline), "successor": list(successor)}
