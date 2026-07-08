#!/usr/bin/env python3
"""Offline reproduction checker for RCLM-CRSI-Core outputs.

Validates an existing rclm_crsi_core_chain_summary.json without rerunning the
closed-loop engine.  It checks schema validity, artifact hashes, parent/child
hash links, transition acceptance records, protected invariants, CoreScore
monotonicity, and the finite/non-external claim boundary.
"""
from __future__ import annotations

import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from crsi_core_schema import (CLAIM_BOUNDARY, PROTECTED_INVARIANT_KEYS, SCHEMA_VERSION, SUITE_NAME,
    load_json, safe_rel, score_improved, sha256_file, sha256_obj, validate_chain_summary, write_json)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "artifacts" / "common" / "closed_loop_reference_engine.py").exists():
            return p
    raise FileNotFoundError("Could not find repo root containing artifacts/common/closed_loop_reference_engine.py")


def rpath(repo: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else repo / p


def check_hashes(repo: Path, manifest: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    hashes = manifest.get("artifact_hashes", {})
    if not isinstance(hashes, Mapping):
        return ["artifact_hashes_not_object"]
    for rel_path, expected in hashes.items():
        path = rpath(repo, str(rel_path))
        if not path.exists():
            errors.append(f"missing_artifact:{rel_path}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            errors.append(f"hash_mismatch:{rel_path}:{actual}!={expected}")
    return errors


def check_manifest_file(repo: Path, manifest: Mapping[str, Any]) -> List[str]:
    path_value = manifest.get("manifest_path")
    if not path_value:
        return ["manifest_path_missing"]
    path = rpath(repo, str(path_value))
    if not path.exists():
        return [f"manifest_file_missing:{path_value}"]
    obj = load_json(path)
    if obj.get("manifest_without_hash_sha256") != manifest.get("manifest_without_hash_sha256"):
        return [f"manifest_hash_field_mismatch:{path_value}"]
    return []


def verify(summary: Mapping[str, Any], repo: Path) -> Dict[str, Any]:
    errors = validate_chain_summary(summary)
    packages = summary.get("packages", []) if isinstance(summary.get("packages"), list) else []
    transitions = summary.get("transitions", []) if isinstance(summary.get("transitions"), list) else []

    for i, manifest in enumerate(packages):
        if not isinstance(manifest, Mapping):
            errors.append(f"package_{i}:not_object")
            continue
        for err in check_hashes(repo, manifest):
            errors.append(f"package_{i}:{err}")
        for err in check_manifest_file(repo, manifest):
            errors.append(f"package_{i}:{err}")
        inv = manifest.get("protected_invariants", {})
        if isinstance(inv, Mapping):
            for key in PROTECTED_INVARIANT_KEYS:
                if inv.get(key) is not True:
                    errors.append(f"package_{i}:protected_invariant_false:{key}")

    for i in range(1, len(packages)):
        prev, curr = packages[i - 1], packages[i]
        if curr.get("parent_successor_id") != prev.get("successor_id"):
            errors.append(f"package_{i}:parent_successor_id_mismatch")
        if curr.get("parent_manifest_hash") != prev.get("manifest_without_hash_sha256"):
            errors.append(f"package_{i}:parent_manifest_hash_mismatch")
        if not score_improved(prev.get("core_score", {}), curr.get("core_score", {})):
            errors.append(f"package_{i}:score_not_improved")

    for i, transition in enumerate(transitions):
        if not isinstance(transition, Mapping) or transition.get("ok") is not True:
            errors.append(f"transition_{i}:not_ok")

    if summary.get("claim_boundary") != CLAIM_BOUNDARY:
        errors.append("claim_boundary_changed")

    report = {"schema_version": SCHEMA_VERSION, "suite_name": SUITE_NAME, "summary_chain_id": summary.get("chain_id"),
              "package_count": len(packages), "transition_count": len(transitions), "ok": not errors,
              "errors": errors, "verified_at_utc": now()}
    report["report_hash"] = sha256_obj(report)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Validate an existing RCLM-CRSI-Core chain summary offline.")
    p.add_argument("summary", type=Path, help="Path to rclm_crsi_core_chain_summary.json")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--allow-failures", action="store_true")
    args = p.parse_args(argv)

    repo = repo_root(args.repo_root)
    summary_path = args.summary if args.summary.is_absolute() else repo / args.summary
    report = verify(load_json(summary_path), repo)
    out = args.out if args.out else summary_path.with_name("rclm_crsi_core_reproduction_report.json")
    out = out if out.is_absolute() else repo / out
    write_json(out, report)
    print(json.dumps({"ok": report["ok"], "report": safe_rel(out, repo), "errors": report["errors"]}, indent=2, sort_keys=True))
    return 0 if report["ok"] or args.allow_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
