#!/usr/bin/env python3
"""Parse official EvalPlus CLI outputs and cache artifacts.

The official EvalPlus CLI normally prints blocks like:

Base
{'pass@1': 0.884...}
Base + Extra
{'pass@1': 0.768...}

This module parses those blocks from stdout/stderr and also records nearby
cache/result paths when available. It is intentionally conservative: if no
score can be parsed, the wrapper should ask for explicit inspected scores.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def _parse_dict_after_label(text: str, label: str) -> Optional[Dict[str, Any]]:
    pattern = re.compile(rf"{re.escape(label)}\s*\n\s*(\{{[^\n]*\}})", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    raw = matches[-1].group(1)
    try:
        obj = ast.literal_eval(raw)
    except Exception:
        try:
            obj = json.loads(raw.replace("'", '"'))
        except Exception:
            return None
    return obj if isinstance(obj, dict) else None


def parse_evalplus_scores_from_text(text: str) -> Dict[str, Any]:
    base = _parse_dict_after_label(text, "Base")
    plus = _parse_dict_after_label(text, "Base + Extra")
    scores: Dict[str, Any] = {
        "base": base,
        "plus": plus,
        "base_pass_at_1": None,
        "plus_pass_at_1": None,
    }
    if isinstance(base, dict):
        scores["base_pass_at_1"] = base.get("pass@1")
    if isinstance(plus, dict):
        scores["plus_pass_at_1"] = plus.get("pass@1")
    return scores


def parse_runlog(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    stdout = obj.get("stdout", "") or ""
    stderr = obj.get("stderr", "") or ""
    scores = parse_evalplus_scores_from_text(stdout + "\n" + stderr)
    obj["parsed_scores"] = scores
    return obj


def possible_eval_cache_paths(samples_path: Path) -> list[Path]:
    parent = samples_path.parent
    stem = samples_path.stem
    return [
        parent / f"{stem}_eval_results.jsonl",
        parent / f"{stem}_eval_results.json",
        parent / f"{samples_path.name}_eval_results.jsonl",
        parent / f"{samples_path.name}_eval_results.json",
    ]


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def existing_artifacts_from_runlog(runlog: Dict[str, Any]) -> list[str]:
    out: list[str] = []
    runlog_path = Path(runlog.get("runlog_path", "")) if runlog.get("runlog_path") else None
    if runlog_path and runlog_path.exists():
        out.append(str(runlog_path))
    samples = runlog.get("samples_path")
    if samples:
        sp = Path(samples)
        if sp.exists():
            out.append(str(sp))
        for p in possible_eval_cache_paths(sp):
            if p.exists():
                out.append(str(p))
    for key in ["stdout_path", "stderr_path"]:
        p = Path(runlog.get(key, "")) if runlog.get(key) else None
        if p and p.exists():
            out.append(str(p))
    # de-duplicate preserving order
    seen = set()
    dedup = []
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup
