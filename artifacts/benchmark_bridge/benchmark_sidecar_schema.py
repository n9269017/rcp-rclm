#!/usr/bin/env python3
"""Schema validation for certificate-preserving benchmark sidecars."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

FULL_PASS = "FullPass"
PARTIAL_PASS = "PartialPass"
FAIL = "Fail"

REQUIRED_SIDECAR_FIELDS = [
    "benchmark",
    "benchmark_version",
    "mode",
    "N",
    "seed",
    "baseline_score",
    "successor_score",
    "delta",
    "certificate_preserved",
    "accepted_updates",
    "all_pcs_checked",
    "runlog_hash",
    "certificate_hash",
    "LECert_status",
    "checker_passed",
    "ok",
]


def validate_sidecar(sidecar: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for field in REQUIRED_SIDECAR_FIELDS:
        if field not in sidecar:
            errors.append(f"missing required field: {field}")

    if sidecar.get("mode") not in {"rcp", "rclm"}:
        errors.append("mode must be 'rcp' or 'rclm'")

    try:
        N = int(sidecar.get("N"))
        if N < 1:
            errors.append("N must be >= 1")
    except Exception:
        errors.append("N must be an integer")

    for score_field in ["baseline_score", "successor_score", "delta"]:
        try:
            float(sidecar.get(score_field))
        except Exception:
            errors.append(f"{score_field} must be numeric")

    for bool_field in ["certificate_preserved", "all_pcs_checked", "checker_passed", "ok"]:
        if not isinstance(sidecar.get(bool_field), bool):
            errors.append(f"{bool_field} must be boolean")

    if sidecar.get("LECert_status") not in {FULL_PASS, PARTIAL_PASS, FAIL}:
        errors.append("LECert_status must be FullPass, PartialPass, or Fail")

    if sidecar.get("benchmark") == "local-mini-terminal-v0" and sidecar.get("public_external_benchmark") is True:
        errors.append("local-mini-terminal-v0 must not be marked as a public external benchmark")

    return (len(errors) == 0), errors


def sidecar_claim_boundary(*, local_benchmark: bool = True) -> Dict[str, bool]:
    return {
        "certificate_preserving_local_benchmark": bool(local_benchmark),
        "b9_learned_entry_fullpass_required": True,
        "b10_public_external_benchmark": False,
        "public_benchmark_sota_claim": False,
        "arbitrary_trained_system_entry": False,
        "frontier_scale_validation": False,
        "full_autonomous_rsi": False,
    }


def classify_benchmark_sidecar(sidecar: Mapping[str, Any]) -> str:
    if not sidecar.get("ok"):
        return FAIL
    if sidecar.get("certificate_preserved") is True and float(sidecar.get("delta", 0.0)) > 0:
        return FULL_PASS
    if sidecar.get("certificate_preserved") is True:
        return PARTIAL_PASS
    return FAIL
