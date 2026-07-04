#!/usr/bin/env python3
"""Schema helpers for Phase 4B-alt EvalPlus certificate-preserving sidecars."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


REQUIRED_SIDECAR_FIELDS = [
    "benchmark",
    "benchmark_version",
    "benchmark_kind",
    "official_public_benchmark",
    "dataset",
    "dataset_scope",
    "task_ids",
    "mode",
    "N",
    "seed",
    "baseline_score",
    "successor_score",
    "delta",
    "improved",
    "certificate_preserved",
    "accepted_updates",
    "all_pcs_checked",
    "LECert_status",
    "checker_passed",
    "closed_loop_ok",
    "score_artifact_paths",
    "score_artifact_hashes",
    "runlog_hash",
    "certificate_hash",
    "diagnostic_oracle",
    "claimable_non_oracle_improvement",
    "claim_boundary",
    "created_utc",
    "ok",
]


def validate_sidecar(sidecar: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in REQUIRED_SIDECAR_FIELDS:
        if field not in sidecar:
            errors.append(f"missing required field: {field}")

    if errors:
        return errors

    if not isinstance(sidecar["task_ids"], list) or not sidecar["task_ids"]:
        errors.append("task_ids must be a nonempty list")

    for field in ["baseline_score", "successor_score", "delta"]:
        if not isinstance(sidecar[field], (int, float)):
            errors.append(f"{field} must be numeric")

    expected_delta = float(sidecar["successor_score"]) - float(sidecar["baseline_score"])
    if abs(float(sidecar["delta"]) - expected_delta) > 1e-9:
        errors.append("delta must equal successor_score - baseline_score")

    expected_improved = float(sidecar["delta"]) > 0
    if bool(sidecar["improved"]) != expected_improved:
        errors.append("improved must equal delta > 0")

    expected_claimable = (
        expected_improved
        and bool(sidecar["certificate_preserved"])
        and not bool(sidecar["diagnostic_oracle"])
    )
    if bool(sidecar["claimable_non_oracle_improvement"]) != expected_claimable:
        errors.append(
            "claimable_non_oracle_improvement must be improved and certificate_preserved and not diagnostic_oracle"
        )

    if not isinstance(sidecar["claim_boundary"], dict):
        errors.append("claim_boundary must be an object")

    return errors


@dataclass
class ClaimBoundary:
    evalplus_public_code_benchmark: bool
    docker_free_local_evalplus: bool
    diagnostic_oracle: bool
    claimable_non_oracle_improvement: bool
    certificate_preserved: bool
    swe_bench_result: bool = False
    terminal_bench_result: bool = False
    re_bench_result: bool = False
    mle_bench_result: bool = False
    webarena_result: bool = False
    arbitrary_trained_system_entry: bool = False
    full_autonomous_rsi: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
