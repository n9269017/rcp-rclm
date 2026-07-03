#!/usr/bin/env python3
"""Schema utilities for B9-Bridge Phase 4 public-benchmark subset sidecars.

Default Phase-4 runs use a controlled public-style subset.  Official public
benchmark status is permitted only when an external manifest supplies benchmark
identity/version, task IDs, scoring-harness metadata, score artifacts, and a
valid certificate bundle.
"""
from __future__ import annotations
from typing import Any, Dict, List, Mapping, Tuple

REQUIRED_FIELDS = [
    "schema", "phase", "benchmark", "benchmark_version", "benchmark_kind",
    "mode", "N", "seed", "baseline_score", "successor_score", "delta",
    "delta_positive", "certificate_preserved", "accepted_updates",
    "all_pcs_checked", "checker_passed", "LECert_status", "runlog_hash",
    "certificate_hash", "claim_boundary", "ok"
]


def phase4_claim_boundary(*, official_public_benchmark: bool, controlled_subset: bool) -> Dict[str, bool]:
    return {
        "phase4_public_subset_adapter": True,
        "controlled_public_style_subset": controlled_subset,
        "official_public_benchmark_claim": official_public_benchmark,
        "certificate_preserving_score_delta": True,
        "b10_external_public_benchmark_full_pass": False,
        "swe_bench_verified_full_run": False,
        "terminal_bench_full_run": False,
        "re_bench_full_run": False,
        "mle_bench_full_run": False,
        "webarena_full_run": False,
        "arbitrary_trained_system_entry": False,
        "frontier_scale_validation": False,
        "full_autonomous_rsi": False,
    }


def validate_public_subset_sidecar(sidecar: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key in REQUIRED_FIELDS:
        if key not in sidecar:
            errors.append(f"missing required field: {key}")
    for key in ["certificate_preserved", "all_pcs_checked", "checker_passed", "delta_positive", "ok"]:
        if key in sidecar and not isinstance(sidecar[key], bool):
            errors.append(f"{key} must be boolean")
    for key in ["baseline_score", "successor_score", "delta"]:
        if key in sidecar and not isinstance(sidecar[key], (int, float)):
            errors.append(f"{key} must be numeric")
    if sidecar.get("delta_positive") is True and float(sidecar.get("delta", 0)) <= 0:
        errors.append("delta_positive is true but delta <= 0")
    if sidecar.get("certificate_preserved") is True:
        if sidecar.get("LECert_status") != "FullPass":
            errors.append("certificate_preserved requires LECert_status == FullPass")
        if sidecar.get("all_pcs_checked") is not True:
            errors.append("certificate_preserved requires all_pcs_checked")
        if sidecar.get("checker_passed") is not True:
            errors.append("certificate_preserved requires checker_passed")
    if sidecar.get("ok") is True:
        if sidecar.get("certificate_preserved") is not True:
            errors.append("ok requires certificate_preserved")
        if sidecar.get("delta_positive") is not True:
            errors.append("ok requires delta_positive")
    return len(errors) == 0, errors


def classify_sidecar(sidecar: Mapping[str, Any]) -> str:
    if sidecar.get("ok") and sidecar.get("certificate_preserved") and sidecar.get("delta_positive"):
        if sidecar.get("claim_boundary", {}).get("official_public_benchmark_claim"):
            return "OfficialPublicSubsetCertificatePreservingImprovement"
        return "ControlledPublicStyleSubsetCertificatePreservingImprovement"
    if sidecar.get("certificate_preserved") and not sidecar.get("delta_positive"):
        return "CertificatePreservedNoImprovement"
    if sidecar.get("delta_positive") and not sidecar.get("certificate_preserved"):
        return "ImprovementWithoutCertificatePreservation"
    return "NoCertifiedImprovement"
