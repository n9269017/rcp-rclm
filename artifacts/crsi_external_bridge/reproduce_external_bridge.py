#!/usr/bin/env python3
"""Offline reproduction checker for CRSI-RE/METR bridge sidecars."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from external_bridge_schema import (
    BRIDGE_INVARIANT_KEYS,
    SCHEMA_VERSION,
    SUITE_NAME,
    load_json,
    safe_rel,
    sha256_file,
    sha256_obj,
    validate_bridge_sidecar,
    write_json,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "artifacts" / "crsi_external_bridge" / "external_bridge_schema.py").exists():
            return path
    raise FileNotFoundError("Could not find repo root containing artifacts/crsi_external_bridge/external_bridge_schema.py")


def rpath(repo: Path, value: Optional[str]) -> Optional[Path]:
    if value is None:
        return None
    p = Path(value)
    return p if p.is_absolute() else repo / p


def check_file_hash(repo: Path, sidecar: Mapping[str, Any], path_key: str, hash_key: str) -> List[str]:
    errors: List[str] = []
    path_value = sidecar.get(path_key)
    expected = sidecar.get(hash_key)
    if path_value is None:
        if expected is not None:
            errors.append(f"{hash_key}_present_without_{path_key}")
        return errors
    path = rpath(repo, str(path_value))
    if path is None or not path.exists():
        errors.append(f"missing_file:{path_value}")
        return errors
    actual = sha256_file(path)
    if actual != expected:
        errors.append(f"hash_mismatch:{path_value}:{actual}!={expected}")
    return errors


def verify(sidecar_path: Path, repo: Path) -> Dict[str, Any]:
    sidecar = load_json(sidecar_path)
    errors = validate_bridge_sidecar(sidecar)
    for path_key, hash_key in [
        ("crsi_chain_summary_path", "crsi_chain_summary_hash"),
        ("task_manifest_path", "task_manifest_hash"),
        ("external_score_ledger_path", "external_score_ledger_hash"),
        ("scorer_artifact_path", "scorer_artifact_hash"),
    ]:
        errors.extend(check_file_hash(repo, sidecar, path_key, hash_key))
    invariants = sidecar.get("bridge_invariants", {})
    if isinstance(invariants, Mapping):
        for key in BRIDGE_INVARIANT_KEYS:
            if invariants.get(key) is not True:
                errors.append(f"bridge_invariant_false:{key}")
    else:
        errors.append("bridge_invariants_not_object")
    if sidecar.get("sidecar_hash") != sha256_obj({k: v for k, v in sidecar.items() if k != "sidecar_hash"}):
        errors.append("sidecar_hash_mismatch")
    report = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "sidecar_path": safe_rel(sidecar_path, repo),
        "benchmark_id": sidecar.get("benchmark_id"),
        "benchmark_kind": sidecar.get("benchmark_kind"),
        "ok": not errors,
        "errors": errors,
        "verified_at_utc": now(),
    }
    report["report_hash"] = sha256_obj(report)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Reproduce/check a CRSI external bridge sidecar without rerunning the benchmark.")
    p.add_argument("sidecar", type=Path)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--allow-failures", action="store_true")
    args = p.parse_args(argv)
    repo = find_repo_root(args.repo_root)
    sidecar_path = args.sidecar if args.sidecar.is_absolute() else repo / args.sidecar
    report = verify(sidecar_path, repo)
    out = args.out if args.out else sidecar_path.with_name("crsi_external_bridge_reproduction_report.json")
    out = out if out.is_absolute() else repo / out
    write_json(out, report)
    print(json.dumps({"ok": report["ok"], "report": safe_rel(out, repo), "errors": report["errors"]}, indent=2, sort_keys=True))
    return 0 if report["ok"] or args.allow_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
