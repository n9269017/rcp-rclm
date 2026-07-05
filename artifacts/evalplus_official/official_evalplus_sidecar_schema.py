#!/usr/bin/env python3
"""Schema checks for Phase 4C-E official EvalPlus sidecars."""

from __future__ import annotations

from typing import Any, Dict, List


REQUIRED_TOP = [
    "benchmark",
    "benchmark_kind",
    "official_evalplus_cli_result",
    "dataset",
    "mode",
    "N",
    "seed",
    "task_count",
    "score_kind",
    "baseline_score",
    "successor_score",
    "delta",
    "improved",
    "certificate_preserved",
    "claim_boundary",
    "official_artifact_paths",
    "official_artifact_hashes",
]


def validate_official_sidecar(obj: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for k in REQUIRED_TOP:
        if k not in obj:
            errors.append(f"missing:{k}")

    if obj.get("benchmark_kind") != "official_evalplus_cli_artifact_sidecar":
        errors.append("benchmark_kind must be official_evalplus_cli_artifact_sidecar")

    if obj.get("official_evalplus_cli_result") is not True:
        errors.append("official_evalplus_cli_result must be true for this Phase 4C-E wrapper")

    if not isinstance(obj.get("baseline_score"), (int, float)):
        errors.append("baseline_score must be numeric")
    if not isinstance(obj.get("successor_score"), (int, float)):
        errors.append("successor_score must be numeric")
    if not isinstance(obj.get("delta"), (int, float)):
        errors.append("delta must be numeric")

    cb = obj.get("claim_boundary", {})
    if not isinstance(cb, dict):
        errors.append("claim_boundary must be an object")
    else:
        if cb.get("swe_bench_result") is not False:
            errors.append("claim_boundary.swe_bench_result must be false")
        if cb.get("full_autonomous_rsi") is not False:
            errors.append("claim_boundary.full_autonomous_rsi must be false")
        if cb.get("certificate_preserved") != obj.get("certificate_preserved"):
            errors.append("claim_boundary.certificate_preserved must match certificate_preserved")

    if obj.get("evalplus_leaderboard_result") is True:
        errors.append("This wrapper must not set evalplus_leaderboard_result=true; external listing is separate.")

    return errors
