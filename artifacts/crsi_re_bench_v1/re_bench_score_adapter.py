#!/usr/bin/env python3
"""Adapt scorer-produced RE-Bench logs into normalized CRSI score artifacts.

No score is accepted from a hand-authored score table. A raw score log must be
accompanied by execution-time provenance identifying the external score exporter,
the Vivaria run, and the pinned scorer manifest.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    load_json,
    path_hash,
    safe_rel,
    select_best_score,
    self_hash,
    sha256_file,
    utc_now,
    validate_usage,
    write_json,
)


def load_raw_score_entries(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("raw score log is empty")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        entries: List[Dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, Mapping):
                raise ValueError(f"JSONL score entry {line_number} is not an object")
            entries.append(dict(obj))
        return entries
    if isinstance(parsed, list):
        return [dict(item) for item in parsed if isinstance(item, Mapping)]
    if isinstance(parsed, Mapping):
        for key in ["scores", "entries", "score_log", "results"]:
            value = parsed.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, Mapping)]
        if "score" in parsed:
            return [dict(parsed)]
    raise ValueError("raw score log must be an object with score, a list, or JSONL")


def find_environment(pin: Mapping[str, Any], environment_id: str) -> Mapping[str, Any]:
    for environment in pin.get("environments", []):
        if isinstance(environment, Mapping) and environment.get("environment_id") == environment_id:
            return environment
    raise KeyError(f"environment not found in official pin: {environment_id}")


def find_scorer(scorer_manifest: Mapping[str, Any], environment_id: str) -> Mapping[str, Any]:
    for scorer in scorer_manifest.get("scorers", []):
        if isinstance(scorer, Mapping) and scorer.get("environment_id") == environment_id:
            return scorer
    raise KeyError(f"scorer not found in scorer manifest: {environment_id}")


def build_score_artifact(
    *,
    repo_root: Path,
    environment_id: str,
    raw_score_log: Path,
    raw_score_provenance: Path,
    usage_path: Path,
    task_runlog: Path,
    submission_path: Path,
    trajectory_path: Path,
    official_pin: Mapping[str, Any],
    scorer_manifest: Mapping[str, Any],
    policy_record: Mapping[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    environment = find_environment(official_pin, environment_id)
    scorer = find_scorer(scorer_manifest, environment_id)
    provenance = load_json(raw_score_provenance)
    usage = load_json(usage_path)
    runlog = load_json(task_runlog)
    entries = load_raw_score_entries(raw_score_log)

    if provenance.get("source_kind") != "official_scorer_export":
        errors.append("raw_score_provenance_not_official_scorer_export")
    if provenance.get("producer") != "external_score_export_command":
        errors.append("raw_score_producer_mismatch")
    if provenance.get("manual_or_declared_score") is not False:
        errors.append("manual_or_declared_score_not_explicitly_false")
    if provenance.get("vivaria_run_id") != runlog.get("vivaria_run_id"):
        errors.append("provenance_run_id_mismatch")
    if provenance.get("scorer_manifest_hash") != scorer_manifest.get("manifest_hash"):
        errors.append("provenance_scorer_manifest_hash_mismatch")
    if provenance.get("official_scorer_sha256") != scorer.get("official_scorer_sha256"):
        errors.append("provenance_scorer_sha256_mismatch")
    if provenance.get("raw_score_log_sha256") != sha256_file(raw_score_log):
        errors.append("provenance_raw_score_log_hash_mismatch")
    errors.extend(validate_usage(usage))
    if not submission_path.exists():
        errors.append("final_submission_missing")
    if not trajectory_path.exists() or not trajectory_path.is_file():
        errors.append("agent_trajectory_missing")

    selection = select_best_score(entries, environment)
    best_entry = selection["entries"][selection["best_entry_index"]]
    compute_used = best_entry.get("compute_used") if isinstance(best_entry.get("compute_used"), Mapping) else usage
    errors.extend(f"compute_used:{error}" for error in validate_usage(compute_used))
    if compute_used.get("vivaria_run_id") != runlog.get("vivaria_run_id"):
        errors.append("compute_used_run_id_mismatch")
    if selection.get("time_to_best_seconds") is None:
        errors.append("time_to_best_seconds_missing")
    usage_limits = runlog.get("usage_limits", {})
    for key in ["tokens", "actions", "total_seconds", "cost"]:
        if key not in usage_limits:
            errors.append(f"usage_limit_missing:{key}")
    expected_resources = environment.get("resources", {})
    recorded_resources = runlog.get("resource_requirements", {})
    if recorded_resources != expected_resources:
        errors.append("resource_requirements_do_not_match_official_environment")
    if expected_resources.get("cpus") is not None and int(usage.get("cpu_count", -1)) != int(expected_resources["cpus"]):
        errors.append("actual_cpu_count_mismatch")
    if expected_resources.get("memory_gb") is not None and float(usage.get("memory_gb", -1)) != float(expected_resources["memory_gb"]):
        errors.append("actual_memory_gb_mismatch")
    gpu_count = int(usage.get("gpu_count", -1))
    gpu_min = int(expected_resources.get("gpu_count_min", 0))
    gpu_max = int(expected_resources.get("gpu_count_max", gpu_min))
    if not (gpu_min <= gpu_count <= gpu_max):
        errors.append("actual_gpu_count_outside_official_range")
    expected_gpu_model = expected_resources.get("gpu_model")
    if expected_gpu_model is not None and usage.get("gpu_model") != expected_gpu_model:
        errors.append("actual_gpu_model_mismatch")
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "source_kind": "official_re_bench_scorer_export",
        "environment_id": environment_id,
        "task_family": environment["task_family"],
        "task_id": environment["task_id"],
        "package_index": policy_record["package_index"],
        "core_successor_id": policy_record["core_successor_id"],
        "benchmark_successor_id": policy_record["benchmark_successor_id"],
        "policy_hash": policy_record["policy_hash"],
        "vivaria_run_id": runlog.get("vivaria_run_id"),
        "raw_score": selection["raw_score"],
        "normalized_score": selection["normalized_score"],
        "best_score": selection["best_score"],
        "best_entry_index": selection["best_entry_index"],
        "time_to_best_seconds": selection["time_to_best_seconds"],
        "raw_score_direction": environment["raw_score_direction"],
        "starting_score": environment["starting_score"],
        "reference_score": environment["reference_score"],
        "score_entry_count": len(entries),
        "compute_used": compute_used,
        "usage": usage,
        "usage_limits": usage_limits,
        "resource_requirements": recorded_resources,
        "model_access_policy_id": runlog.get("model_access_policy_id"),
        "network_policy": runlog.get("network_policy"),
        "submission_hash": path_hash(submission_path),
        "trajectory_sha256": sha256_file(trajectory_path),
        "raw_score_log_sha256": sha256_file(raw_score_log),
        "raw_score_provenance_sha256": sha256_file(raw_score_provenance),
        "task_runlog_sha256": sha256_file(task_runlog),
        "usage_sha256": sha256_file(usage_path),
        "scorer_hash": scorer["official_scorer_sha256"],
        "scorer_bundle_hash": scorer["scorer_bundle_sha256"],
        "official_environment_pin_hash": official_pin.get("manifest_hash"),
        "scorer_manifest_hash": scorer_manifest.get("manifest_hash"),
        "raw_entries": selection["entries"],
        "artifact_paths": {
            "raw_score_log": safe_rel(raw_score_log, repo_root),
            "raw_score_provenance": safe_rel(raw_score_provenance, repo_root),
            "task_runlog": safe_rel(task_runlog, repo_root),
            "usage": safe_rel(usage_path, repo_root),
            "trajectory": safe_rel(trajectory_path, repo_root),
            "submission": safe_rel(submission_path, repo_root),
        },
        "created_utc": utc_now(),
        "errors": errors,
        "ok": not errors,
    }
    artifact["score_artifact_hash"] = self_hash(artifact, "score_artifact_hash")
    return artifact


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize an official RE-Bench scorer export into a CRSI score artifact.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--raw-score-log", type=Path, required=True)
    parser.add_argument("--raw-score-provenance", type=Path, required=True)
    parser.add_argument("--usage", type=Path, required=True)
    parser.add_argument("--task-runlog", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--official-environment-hashes", type=Path, required=True)
    parser.add_argument("--scorer-manifest", type=Path, required=True)
    parser.add_argument("--agent-entrypoint-manifest", type=Path, required=True)
    parser.add_argument("--package-index", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    official_pin = load_json(args.official_environment_hashes.resolve())
    scorer_manifest = load_json(args.scorer_manifest.resolve())
    agent_manifest = load_json(args.agent_entrypoint_manifest.resolve())
    policy_records = agent_manifest.get("resolved_profiles", [])
    if args.package_index < 0 or args.package_index >= len(policy_records):
        raise SystemExit(f"package index out of range: {args.package_index}")
    artifact = build_score_artifact(
        repo_root=repo_root,
        environment_id=args.environment_id,
        raw_score_log=args.raw_score_log.resolve(),
        raw_score_provenance=args.raw_score_provenance.resolve(),
        usage_path=args.usage.resolve(),
        task_runlog=args.task_runlog.resolve(),
        submission_path=args.submission.resolve(),
        trajectory_path=args.trajectory.resolve(),
        official_pin=official_pin,
        scorer_manifest=scorer_manifest,
        policy_record=policy_records[args.package_index],
    )
    write_json(args.out.resolve(), artifact)
    print(json.dumps({
        "ok": artifact["ok"],
        "raw_score": artifact["raw_score"],
        "normalized_score": artifact["normalized_score"],
        "out": str(args.out.resolve()),
        "errors": artifact["errors"],
    }, indent=2, sort_keys=True))
    return 0 if artifact["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
