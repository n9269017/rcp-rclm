#!/usr/bin/env python3
"""Score utilities for the RCP/RCLM certificate-preserving benchmark bridge.

This module is intentionally dependency-free.  It computes finite controlled
benchmark scores, score deltas, and reproducible SHA-256 hashes for sidecar
objects.  It does not run or claim any public external benchmark.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple


def canonical_json_bytes(obj: Any) -> bytes:
    """Return deterministic JSON bytes for hashing."""
    return json.dumps(obj, sort_keys=True, indent=2, separators=(",", ": ")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def score_task_results(results: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = list(results)
    total_weight = sum(float(row.get("weight", 1.0)) for row in rows)
    solved_weight = sum(float(row.get("weight", 1.0)) for row in rows if row.get("solved") is True)
    score = solved_weight / total_weight if total_weight else 0.0
    return {
        "tasks": len(rows),
        "total_weight": total_weight,
        "solved_weight": solved_weight,
        "score": score,
        "solved_count": sum(1 for row in rows if row.get("solved") is True),
    }


def score_delta(baseline_score: float, successor_score: float) -> Dict[str, Any]:
    delta = float(successor_score) - float(baseline_score)
    return {
        "baseline_score": float(baseline_score),
        "successor_score": float(successor_score),
        "delta": delta,
        "delta_positive": delta > 0,
        "relative_improvement": (delta / baseline_score) if baseline_score > 0 else None,
    }


def summarize_sidecars(sidecars: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = list(sidecars)
    total = len(rows)
    preserved = sum(1 for row in rows if row.get("certificate_preserved") is True)
    improved = sum(1 for row in rows if float(row.get("delta", 0.0)) > 0)
    all_ok = sum(1 for row in rows if row.get("ok") is True)
    deltas = [float(row.get("delta", 0.0)) for row in rows]
    return {
        "total_cases": total,
        "ok_cases": all_ok,
        "certificate_preserved_cases": preserved,
        "improved_cases": improved,
        "pass_rate": all_ok / total if total else 0.0,
        "certificate_preservation_rate": preserved / total if total else 0.0,
        "improvement_rate": improved / total if total else 0.0,
        "mean_delta": sum(deltas) / total if total else 0.0,
        "min_delta": min(deltas) if deltas else 0.0,
        "max_delta": max(deltas) if deltas else 0.0,
        "all_cases_ok": all_ok == total and total > 0,
    }
