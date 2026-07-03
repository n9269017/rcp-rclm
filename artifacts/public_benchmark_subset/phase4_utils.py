#!/usr/bin/env python3
"""Hashing, JSON, and score helpers for Phase 4."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def score_delta(baseline: float, successor: float) -> Dict[str, Any]:
    baseline = float(baseline)
    successor = float(successor)
    delta = successor - baseline
    return {
        "baseline_score": baseline,
        "successor_score": successor,
        "delta": delta,
        "relative_delta": None if baseline == 0 else delta / baseline,
        "delta_positive": delta > 0,
    }


def summarize(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    xs = list(rows)
    total = len(xs)
    ok = [x for x in xs if x.get("ok")]
    preserved = [x for x in xs if x.get("certificate_preserved")]
    improved = [x for x in xs if x.get("delta_positive")]
    deltas = [float(x.get("delta", 0.0)) for x in xs]
    return {
        "suite_name": "B9-Bridge Phase 4: public benchmark subset adapter",
        "suite_scope": "Certificate-preserving public-subset-compatible sidecars; default local-terminal-public-subset-v0 is controlled, not official public benchmark.",
        "total_cases": total,
        "ok_cases": len(ok),
        "pass_rate": 0.0 if total == 0 else len(ok) / total,
        "certificate_preserved_cases": len(preserved),
        "certificate_preservation_rate": 0.0 if total == 0 else len(preserved) / total,
        "improved_cases": len(improved),
        "improvement_rate": 0.0 if total == 0 else len(improved) / total,
        "mean_delta": 0.0 if not deltas else sum(deltas) / len(deltas),
        "min_delta": None if not deltas else min(deltas),
        "max_delta": None if not deltas else max(deltas),
        "official_public_benchmark_cases": sum(1 for x in xs if x.get("claim_boundary", {}).get("official_public_benchmark_claim")),
        "all_cases_ok": total > 0 and len(ok) == total,
    }
