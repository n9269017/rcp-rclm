#!/usr/bin/env python3
"""Convert exported official RE-Bench scorer logs into hash-bound CRSI score artifacts.

The adapter exposes no numeric-score argument. It accepts only preserved scorer
exports accompanied by execution-time provenance, actual usage, the pinned
scorer manifest, and the package-specific agent manifest.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    elapsed_at_entry,
    hash_file_or_tree,
    load_json,
    normalize_re_bench_score,
    parse_score_log,
    safe_rel,
    select_best_score,
    select_official_score,
    sha256_file,
    sha256_obj,
    utc_now,
    validate_usage_record,
    verify_document_self_hash,
    write_json,
)


def environment_row(manifest: Mapping[str, Any], environment_id: str) -> Mapping[str, Any]:
    for row in manifest.get("environments", []):
        if isinstance(row, Mapping) and row.get("environment_id") == environment_id:
            return row
    raise KeyError(f"environment missing from scorer manifest: {environment_id}")


def profile_row(agent_manifest: Mapping[str, Any], package_index: int) -> Mapping[str, Any]:
    for row in agent_manifest.get("profiles", []):
        if isinstance(row, Mapping) and int(row.get("package_index", -1)) == package_index:
            return row
    raise KeyError(f"package profile missing from agent manifest: {package_index}")


def adapt_score(
    *,
    repo_root: Path,
    environment_id: str,
    package_index: int,
    seed: int,
    raw_score_log: Path,
    raw_score_provenance_path: Path,
    usage_path: Path,
    task_runlog_path: Path,
    trajectory_path: Path,
    submission_path: Path,
    scorer_manifest_path: Path,
    agent_manifest_path: Path,
) -> Dict[str, Any]:
    errors = []
    scorer_manifest = load_json(scorer_manifest_path)
    agent_manifest = load_json(agent_manifest_path)
    task_runlog = load_json(task_runlog_path)
    provenance = load_json(raw_score_provenance_path)
    usage = load_json(usage_path)
    scorer = environment_row(scorer_manifest, environment_id)
    profile = profile_row(agent_manifest, package_index)

    if scorer_manifest.get("ok") is not True or not verify_document_self_hash(scorer_manifest, "manifest_hash"):
        errors.append("pinned_scorer_manifest_not_ok_or_self_hash_invalid")
    if agent_manifest.get("ok") is not True or not verify_document_self_hash(agent_manifest, "manifest_hash"):
        errors.append("agent_entrypoint_manifest_not_ok_or_self_hash_invalid")
    if task_runlog.get("official_scorer_executed") is not True:
        errors.append("task_runlog_does_not_attest_official_scorer_execution")
    if task_runlog.get("environment_id") != environment_id:
        errors.append("task_runlog_environment_id_mismatch")
    if int(task_runlog.get("package_index", -1)) != package_index:
        errors.append("task_runlog_package_index_mismatch")
    if int(task_runlog.get("seed", -1)) != seed:
        errors.append("task_runlog_seed_mismatch")
    if task_runlog.get("scorer_sha256") != scorer.get("scorer_sha256"):
        errors.append("task_runlog_scorer_sha256_mismatch")
    if task_runlog.get("benchmark_successor_id") != profile.get("benchmark_successor_id"):
        errors.append("task_runlog_benchmark_successor_id_mismatch")

    if provenance.get("source_kind") != "official_scorer_export":
        errors.append("raw_score_provenance_source_invalid")
    if provenance.get("manual_or_declared_score") is not False:
        errors.append("raw_score_provenance_allows_manual_score")
    if provenance.get("vivaria_run_id") != task_runlog.get("vivaria_run_id"):
        errors.append("raw_score_provenance_run_id_mismatch")
    if provenance.get("raw_score_log_sha256") != (sha256_file(raw_score_log) if raw_score_log.is_file() else None):
        errors.append("raw_score_provenance_log_hash_mismatch")
    if provenance.get("scorer_manifest_hash") != scorer_manifest.get("manifest_hash"):
        errors.append("raw_score_provenance_scorer_manifest_mismatch")
    if provenance.get("official_scorer_sha256") != scorer.get("scorer_sha256"):
        errors.append("raw_score_provenance_scorer_hash_mismatch")
    if provenance.get("provenance_hash") and not verify_document_self_hash(provenance, "provenance_hash"):
        errors.append("raw_score_provenance_self_hash_invalid")

    for path, label in [
        (raw_score_log, "raw_score_log"),
        (raw_score_provenance_path, "raw_score_provenance"),
        (usage_path, "usage"),
        (task_runlog_path, "task_runlog"),
        (trajectory_path, "agent_trajectory"),
        (submission_path, "final_submission"),
    ]:
        if not path.exists():
            errors.append(f"missing_input:{label}:{path}")

    errors.extend(validate_usage_record(usage, expected_run_id=task_runlog.get("vivaria_run_id")))
    entries = []
    if raw_score_log.is_file():
        try:
            entries = parse_score_log(raw_score_log)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"raw_score_log_invalid:{exc}")
    official_raw_score, official_index = select_official_score(entries, str(scorer["aggregation"])) if entries else (math.nan, -1)
    best_score, best_index = select_best_score(entries, str(scorer["raw_score_direction"])) if entries else (math.nan, -1)
    normalized = normalize_re_bench_score(
        official_raw_score,
        float(scorer["starting_score"]),
        float(scorer["reference_score"]),
    ) if entries else math.nan

    artifact: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "kind": "official_re_bench_score_artifact",
        "source_kind": "official_re_bench_scorer_export",
        "environment_id": environment_id,
        "task_id": scorer.get("task_id"),
        "package_index": package_index,
        "seed": seed,
        "core_successor_id": profile.get("core_successor_id"),
        "benchmark_successor_id": profile.get("benchmark_successor_id"),
        "policy_hash": profile.get("profile_sha256"),
        "policy_provenance_mode": profile.get("policy_provenance_mode"),
        "raw_score": official_raw_score,
        "normalized_score": normalized,
        "best_score": best_score,
        "official_aggregation": scorer.get("aggregation"),
        "raw_score_direction": scorer.get("raw_score_direction"),
        "starting_score": scorer.get("starting_score"),
        "reference_score": scorer.get("reference_score"),
        "official_selected_entry_index": official_index,
        "best_entry_index": best_index,
        "time_to_best_seconds": elapsed_at_entry(entries, best_index) if best_index >= 0 else None,
        "score_entry_count": len(entries),
        "compute_used": usage,
        "usage_limits": task_runlog.get("usage_limits", {}),
        "declared_resources": task_runlog.get("declared_resources", {}),
        "model_access_policy_id": task_runlog.get("model_access_policy_id"),
        "vivaria_run_id": task_runlog.get("vivaria_run_id"),
        "raw_score_log_path": safe_rel(raw_score_log, repo_root),
        "raw_score_log_sha256": sha256_file(raw_score_log) if raw_score_log.is_file() else None,
        "raw_score_provenance_path": safe_rel(raw_score_provenance_path, repo_root),
        "raw_score_provenance_sha256": sha256_file(raw_score_provenance_path) if raw_score_provenance_path.is_file() else None,
        "usage_path": safe_rel(usage_path, repo_root),
        "usage_sha256": sha256_file(usage_path) if usage_path.is_file() else None,
        "task_runlog_path": safe_rel(task_runlog_path, repo_root),
        "task_runlog_sha256": sha256_file(task_runlog_path) if task_runlog_path.is_file() else None,
        "agent_trajectory_path": safe_rel(trajectory_path, repo_root),
        "agent_trajectory_sha256": hash_file_or_tree(trajectory_path) if trajectory_path.exists() else None,
        "final_submission_path": safe_rel(submission_path, repo_root),
        "submission_hash": hash_file_or_tree(submission_path) if submission_path.exists() else None,
        "scorer_manifest_path": safe_rel(scorer_manifest_path, repo_root),
        "scorer_manifest_sha256": sha256_file(scorer_manifest_path),
        "scorer_path": scorer.get("scorer_path"),
        "scorer_hash": scorer.get("scorer_sha256"),
        "scorer_bundle_sha256": scorer.get("scorer_bundle_sha256"),
        "score_source": "exported_official_scorer_log",
        "manually_declared_score": False,
        "raw_entries": entries,
        "errors": errors,
        "created_utc": utc_now(),
    }
    artifact["ok"] = not errors and bool(entries) and math.isfinite(official_raw_score) and math.isfinite(normalized)
    artifact["score_artifact_hash"] = sha256_obj({k: v for k, v in artifact.items() if k != "score_artifact_hash"})
    return artifact


def self_test() -> Dict[str, Any]:
    cases = [
        (5.6, 5.6, 4.54, 0.0),
        (4.54, 5.6, 4.54, 1.0),
        (6.0, 5.6, 4.54, 0.0),
        (4.0, 5.6, 4.54, (4.0 - 5.6) / (4.54 - 5.6)),
        (0.0, 0.0, 0.13, 0.0),
        (0.13, 0.0, 0.13, 1.0),
        (-0.1, 0.0, 0.13, 0.0),
        (0.2, 0.0, 0.13, 0.2 / 0.13),
    ]
    errors = []
    for raw, start, reference, expected in cases:
        actual = normalize_re_bench_score(raw, start, reference)
        if abs(actual - expected) > 1e-12:
            errors.append({"raw": raw, "start": start, "reference": reference, "expected": expected, "actual": actual})
    entries = [{"score": 0.9}, {"score": 0.4}]
    if select_official_score(entries, "last") != (0.4, 1):
        errors.append("last_aggregation_self_test_failed")
    return {"ok": not errors, "case_count": len(cases) + 1, "errors": errors}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Adapt an exported official RE-Bench scorer log into a CRSI score artifact.")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--environment-id")
    p.add_argument("--package-index", type=int)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--raw-score-log", type=Path)
    p.add_argument("--raw-score-provenance", type=Path)
    p.add_argument("--usage", type=Path)
    p.add_argument("--task-runlog", type=Path)
    p.add_argument("--trajectory", type=Path)
    p.add_argument("--submission", type=Path)
    p.add_argument("--scorer-manifest", type=Path)
    p.add_argument("--agent-entrypoint-manifest", type=Path)
    p.add_argument("--out", type=Path)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    required = {
        "environment_id": args.environment_id,
        "package_index": args.package_index,
        "raw_score_log": args.raw_score_log,
        "raw_score_provenance": args.raw_score_provenance,
        "usage": args.usage,
        "task_runlog": args.task_runlog,
        "trajectory": args.trajectory,
        "submission": args.submission,
        "scorer_manifest": args.scorer_manifest,
        "agent_entrypoint_manifest": args.agent_entrypoint_manifest,
        "out": args.out,
    }
    missing = [key for key, value in required.items() if value is None]
    if missing:
        print(json.dumps({"ok": False, "errors": [f"missing_arguments:{','.join(missing)}"]}, indent=2))
        return 1
    repo_root = args.repo_root.resolve()
    artifact = adapt_score(
        repo_root=repo_root,
        environment_id=args.environment_id,
        package_index=args.package_index,
        seed=args.seed,
        raw_score_log=args.raw_score_log.resolve(),
        raw_score_provenance_path=args.raw_score_provenance.resolve(),
        usage_path=args.usage.resolve(),
        task_runlog_path=args.task_runlog.resolve(),
        trajectory_path=args.trajectory.resolve(),
        submission_path=args.submission.resolve(),
        scorer_manifest_path=args.scorer_manifest.resolve(),
        agent_manifest_path=args.agent_entrypoint_manifest.resolve(),
    )
    write_json(args.out, artifact)
    print(json.dumps({
        "ok": artifact["ok"],
        "environment_id": artifact["environment_id"],
        "package_index": artifact["package_index"],
        "raw_score": artifact["raw_score"],
        "normalized_score": artifact["normalized_score"],
        "score_artifact": str(args.out),
        "errors": artifact["errors"],
    }, indent=2, sort_keys=True))
    return 0 if artifact["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
