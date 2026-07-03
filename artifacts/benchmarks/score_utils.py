#!/usr/bin/env python3
"""Utility functions for the RCP/RCLM internal RSI benchmark harness.

These utilities intentionally score only internal closed-loop certification
properties. They are not public SWE/RE/MLE/Terminal/WebArena benchmark scores.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

CORE_BOOLEAN_FIELDS = [
    "closed_loop_ok",
    "checker_passed",
    "all_accepted_steps_checked",
    "all_residuals_nonpositive",
    "strict_ability_expansion_each_step",
    "non_loss_recovery_preserved_each_step",
    "zero_goal_identity_drift",
    "singleton_reality_containment",
    "has_rejection_evidence",
]


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else num / den


def compute_case_score(case: Mapping[str, Any]) -> float:
    """Return a 0..1 internal certification score for one case.

    The score is deliberately conservative: it is the fraction of core Boolean
    certification fields that passed. It is not an external task-performance
    score and should not be reported as such.
    """
    passed = 0
    total = len(CORE_BOOLEAN_FIELDS)
    for key in CORE_BOOLEAN_FIELDS:
        if bool(case.get(key, False)):
            passed += 1
    return safe_div(passed, total)


def summarize_cases(cases: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total = len(cases)
    passed_cases = [c for c in cases if c.get("ok") is True]
    failed_cases = [c for c in cases if c.get("ok") is not True]
    generated_total = sum(int(c.get("generated_candidates", 0)) for c in cases)
    accepted_total = sum(int(c.get("accepted_candidates", 0)) for c in cases)
    rejected_total = sum(int(c.get("rejected_candidates", 0)) for c in cases)
    scores = [float(c.get("internal_certification_score", 0.0)) for c in cases]

    by_mode: Dict[str, Dict[str, Any]] = {}
    for case in cases:
        mode = str(case.get("mode", "unknown"))
        bucket = by_mode.setdefault(mode, {"cases": 0, "passed": 0, "scores": [], "generated": 0, "accepted": 0, "rejected": 0})
        bucket["cases"] += 1
        bucket["passed"] += 1 if case.get("ok") is True else 0
        bucket["scores"].append(float(case.get("internal_certification_score", 0.0)))
        bucket["generated"] += int(case.get("generated_candidates", 0))
        bucket["accepted"] += int(case.get("accepted_candidates", 0))
        bucket["rejected"] += int(case.get("rejected_candidates", 0))

    for bucket in by_mode.values():
        bucket["pass_rate"] = safe_div(bucket["passed"], bucket["cases"])
        bucket["mean_internal_certification_score"] = safe_div(sum(bucket["scores"]), len(bucket["scores"]))
        bucket["acceptance_rate"] = safe_div(bucket["accepted"], bucket["generated"])
        del bucket["scores"]

    return {
        "suite_name": "B9-Bridge Phase 1: internal closed-loop RSI benchmark suite",
        "suite_scope": "Internal RCP/RCLM closed-loop certification benchmark, not an external public AI-agent benchmark.",
        "total_cases": total,
        "passed_cases": len(passed_cases),
        "failed_cases": len(failed_cases),
        "pass_rate": safe_div(len(passed_cases), total),
        "mean_internal_certification_score": safe_div(sum(scores), len(scores)),
        "generated_candidates": generated_total,
        "accepted_candidates": accepted_total,
        "rejected_candidates": rejected_total,
        "acceptance_rate": safe_div(accepted_total, generated_total),
        "by_mode": by_mode,
        "all_cases_ok": len(failed_cases) == 0,
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    preferred = [
        "case_id", "mode", "N", "seed", "ok", "internal_certification_score",
        "generated_candidates", "accepted_candidates", "rejected_candidates", "acceptance_rate",
        "checker_passed", "all_accepted_steps_checked", "all_residuals_nonpositive",
        "strict_ability_expansion_each_step", "non_loss_recovery_preserved_each_step",
        "zero_goal_identity_drift", "singleton_reality_containment", "has_rejection_evidence",
        "final_dimension", "artifact_hash", "trajectory_hash", "run_dir",
    ]
    fieldnames = [f for f in preferred if any(f in r for r in rows)]
    extras = sorted(set().union(*(r.keys() for r in rows)) - set(fieldnames))
    fieldnames += [f for f in extras if isinstance(rows[0].get(f, ""), (str, int, float, bool, type(None)))]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
