#!/usr/bin/env python3
"""Score and parsing utilities for EvalPlus sidecars.

The EvalPlus CLI has changed output formatting across versions.  Some
versions print pass@1 to stdout, some mix progress/table output into stderr,
and all recent versions write a cached ``*_eval_results.jsonl`` file next to
the samples.  These helpers therefore parse both the console text and the
cache file instead of relying on one brittle stdout regex.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Matches the documented EvalPlus output, but is intentionally permissive about
# whitespace, ANSI/progress text, and quote style.
PASS_RE = re.compile(
    r"(Base(?:\s*\+\s*Extra)?)\s*.{0,800}?['\"]pass@1['\"]\s*:\s*([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE | re.DOTALL,
)
ANY_PASS_RE = re.compile(r"['\"]pass@1['\"]\s*:\s*([0-9]+(?:\.[0-9]+)?)")


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_evalplus_stdout(text: str) -> Dict[str, Optional[float]]:
    """Parse EvalPlus console text for Base and Base+Extra pass@1 scores."""
    scores: Dict[str, Optional[float]] = {
        "base_pass_at_1": None,
        "plus_pass_at_1": None,
    }
    if not text:
        return scores

    # Strip ANSI escape codes and normalize line endings.
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text).replace("\r\n", "\n")

    for label, value in PASS_RE.findall(text):
        norm = re.sub(r"\s+", " ", label.strip()).lower()
        if norm == "base":
            scores["base_pass_at_1"] = float(value)
        elif norm == "base + extra":
            scores["plus_pass_at_1"] = float(value)

    # If EvalPlus prints only one pass@1 dictionary, use it as base.  This is a
    # fallback for base-only runs and some condensed outputs.
    if scores["base_pass_at_1"] is None and scores["plus_pass_at_1"] is None:
        vals = ANY_PASS_RE.findall(text)
        if vals:
            scores["base_pass_at_1"] = float(vals[-1])
    return scores


def _status_is_pass(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        y = x.strip().lower()
        if y in {"pass", "passed", "ok", "success", "true", "1"}:
            return True
        if y in {"fail", "failed", "error", "timeout", "false", "0"}:
            return False
    return None


def _collect_status_rows(obj: Any, rows: List[Tuple[Optional[bool], Optional[bool]]]) -> None:
    """Collect (base_pass, plus_pass) pairs from known EvalPlus result shapes."""
    if isinstance(obj, list):
        for item in obj:
            _collect_status_rows(item, rows)
        return
    if not isinstance(obj, dict):
        return

    # Current/known EvalPlus cached row shape.
    base = None
    plus = None
    for key in ["base_status", "base", "base_pass", "base_passed"]:
        if key in obj:
            val = obj[key]
            if isinstance(val, dict):
                val = val.get("status", val.get("passed", val.get("pass")))
            base = _status_is_pass(val)
            break
    for key in ["plus_status", "extra_status", "base_plus_extra_status", "plus", "plus_pass", "plus_passed"]:
        if key in obj:
            val = obj[key]
            if isinstance(val, dict):
                val = val.get("status", val.get("passed", val.get("pass")))
            plus = _status_is_pass(val)
            break

    if base is not None or plus is not None:
        rows.append((base, plus))

    # Some report shapes nest results under eval/results/task IDs.
    for key in ["eval", "results", "detail", "details"]:
        if key in obj:
            _collect_status_rows(obj[key], rows)


def parse_evalplus_result_file(path: Path) -> Dict[str, Optional[float]]:
    """Parse EvalPlus cached eval-results JSON/JSONL for pass@1 scores.

    Returns base/plus pass rates over rows with available status fields.
    """
    rows: List[Tuple[Optional[bool], Optional[bool]]] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    # Try JSON first, then JSONL.
    try:
        _collect_status_rows(json.loads(text), rows)
    except Exception:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                _collect_status_rows(json.loads(line), rows)
            except Exception:
                continue

    base_vals = [b for b, _ in rows if b is not None]
    plus_vals = [p for _, p in rows if p is not None]
    return {
        "base_pass_at_1": (sum(base_vals) / len(base_vals)) if base_vals else None,
        "plus_pass_at_1": (sum(plus_vals) / len(plus_vals)) if plus_vals else None,
    }


def find_evalplus_result_files(samples_path: Path) -> List[Path]:
    parent = samples_path.parent
    stem = samples_path.stem
    candidates: List[Path] = []
    names = [
        parent / f"{stem}_eval_results.jsonl",
        parent / f"{stem}_eval_results.json",
        parent / f"{stem}.eval_results.jsonl",
        parent / f"{stem}.eval_results.json",
    ]
    for p in names:
        if p.exists():
            candidates.append(p)
    candidates.extend(sorted(parent.glob(f"{stem}*eval*result*.jsonl")))
    candidates.extend(sorted(parent.glob(f"{stem}*eval*result*.json")))
    # Deduplicate preserving order.
    out: List[Path] = []
    seen = set()
    for p in candidates:
        rp = p.resolve()
        if rp not in seen and p.exists():
            out.append(p)
            seen.add(rp)
    return out


def score_from_evalplus_outputs(stdout: str, stderr: str = "", samples_path: Optional[Path] = None) -> float:
    """Return preferred EvalPlus pass@1 score from console text or cache file.

    Preference is HumanEval+/MBPP+ score (Base + Extra) when present, otherwise
    base score.  Raises with useful diagnostics if nothing parseable exists.
    """
    combined = f"{stdout or ''}\n{stderr or ''}"
    parsed = parse_evalplus_stdout(combined)
    if parsed["plus_pass_at_1"] is not None:
        return float(parsed["plus_pass_at_1"])
    if parsed["base_pass_at_1"] is not None:
        return float(parsed["base_pass_at_1"])

    checked: List[str] = []
    if samples_path is not None:
        for p in find_evalplus_result_files(samples_path):
            checked.append(str(p))
            parsed_file = parse_evalplus_result_file(p)
            if parsed_file["plus_pass_at_1"] is not None:
                return float(parsed_file["plus_pass_at_1"])
            if parsed_file["base_pass_at_1"] is not None:
                return float(parsed_file["base_pass_at_1"])

    snippet = combined[-3000:]
    raise ValueError(
        "Could not parse EvalPlus pass@1 score from stdout/stderr or cache file.\n"
        f"Checked result files: {checked}\n"
        f"Console tail:\n{snippet}"
    )


# Backward-compatible names used by older harness code.
def score_from_evalplus_stdout(stdout: str) -> float:
    return score_from_evalplus_outputs(stdout)


def compute_delta(baseline_score: float, successor_score: float) -> Dict[str, Any]:
    delta = float(successor_score) - float(baseline_score)
    return {
        "baseline_score": float(baseline_score),
        "successor_score": float(successor_score),
        "delta": delta,
        "improved": delta > 0,
    }
