#!/usr/bin/env python3
"""Schema utilities for Phase 4C EvalPlus leaderboard-prep sidecars.

These schemas intentionally separate:
  * public-data direct sidecar results,
  * official EvalPlus CLI artifacts,
  * actual leaderboard submission/recognition.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


REQUIRED_SIDECAR_FIELDS = [
    "benchmark",
    "benchmark_version",
    "benchmark_kind",
    "dataset",
    "task_count",
    "mode",
    "N",
    "seed",
    "baseline_score",
    "successor_score",
    "delta",
    "certificate_preserved",
    "LECert_status",
    "checker_passed",
    "closed_loop_ok",
    "diagnostic_oracle",
    "claimable_non_oracle_improvement",
    "claim_boundary",
    "ok",
]


@dataclass
class EvalPlusClaimBoundary:
    evalplus_public_code_benchmark: bool = True
    docker_free_local_evalplus: bool = True
    official_evalplus_cli_result: bool = False
    evalplus_leaderboard_result: bool = False
    full_humaneval_plus_suite: bool = False
    full_mbpp_plus_suite: bool = False
    diagnostic_oracle: bool = False
    claimable_non_oracle_improvement: bool = False
    certificate_preserved: bool = False
    swe_bench_result: bool = False
    terminal_bench_result: bool = False
    re_bench_result: bool = False
    mle_bench_result: bool = False
    webarena_result: bool = False
    arbitrary_trained_system_entry: bool = False
    full_autonomous_rsi: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)


def validate_sidecar(obj: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for f in REQUIRED_SIDECAR_FIELDS:
        if f not in obj:
            errors.append(f"missing required field: {f}")
    cb = obj.get("claim_boundary")
    if not isinstance(cb, dict):
        errors.append("claim_boundary must be an object")
    else:
        if bool(obj.get("claimable_non_oracle_improvement")) and bool(obj.get("diagnostic_oracle")):
            errors.append("claimable_non_oracle_improvement cannot be true in diagnostic_oracle mode")
        if bool(obj.get("claimable_non_oracle_improvement")) and not bool(obj.get("certificate_preserved")):
            errors.append("claimable_non_oracle_improvement requires certificate_preserved")
        if bool(cb.get("evalplus_leaderboard_result")) and not bool(cb.get("official_evalplus_cli_result")):
            errors.append("evalplus_leaderboard_result requires official_evalplus_cli_result")
    try:
        delta = float(obj.get("delta", 0.0))
        expected = float(obj.get("successor_score", 0.0)) - float(obj.get("baseline_score", 0.0))
        if abs(delta - expected) > 1e-9:
            errors.append(f"delta mismatch: {delta} != {expected}")
    except Exception as e:
        errors.append(f"could not validate numeric delta: {e}")
    return errors
