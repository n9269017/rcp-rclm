#!/usr/bin/env python3
"""Independently reproduce a recorded CRSI-RE-Bench result from scorer logs and hashes."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    elapsed_at_entry,
    ensure_required_run_artifacts,
    evaluate_score_progression,
    hash_file_or_tree,
    load_json,
    normalize_re_bench_score,
    parse_score_log,
    select_best_score,
    select_official_score,
    sha256_file,
    sha256_obj,
    utc_now,
    validate_budget_equivalence,
    validate_crsi_chain,
    validate_no_leakage_manifest,
    validate_usage_record,
    verify_document_self_hash,
    write_json,
)
from crsi_re_bench_runner import (
    budget_profile,
    find_repo_root,
    run_crsi_reproduction,
    validate_agent_manifest,
    verify_live_official_checkout,
)


def resolve(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def close_number(a: Any, b: Any, tolerance: float = 1e-12) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance)
    except (TypeError, ValueError):
        return a == b


def scorer_row(manifest: Mapping[str, Any], environment_id: str) -> Mapping[str, Any]:
    for row in manifest.get("environments", []):
        if isinstance(row, Mapping) and row.get("environment_id") == environment_id:
            return row
    raise KeyError(environment_id)


def profile_row(manifest: Mapping[str, Any], package_index: int) -> Mapping[str, Any]:
    for row in manifest.get("profiles", []):
        if isinstance(row, Mapping) and int(row.get("package_index", -1)) == package_index:
            return row
    raise KeyError(package_index)


def verify_result(
    *,
    repo_root: Path,
    result_dir: Path,
    official_root: Path,
    chain_path: Path,
    environment_manifest_path: Path,
    scorer_manifest_path: Path,
    agent_manifest_path: Path,
    no_leakage_path: Path,
    compute_manifest_path: Path,
) -> Dict[str, Any]:
    errors: List[str] = []
    ledger_path = result_dir / "crsi_re_bench_score_ledger.json"
    sidecar_path = result_dir / "certificate_bridge_sidecar.json"
    plan_path = result_dir / "run_plan.json"
    execution_path = result_dir / "execution_report.json"
    artifact_hashes_path = result_dir / "artifact_hashes.json"
    ingestion_path = result_dir / "ingestion_report.json"
    for path in (ledger_path, sidecar_path, plan_path, execution_path, artifact_hashes_path, ingestion_path):
        if not path.is_file():
            errors.append(f"missing_result_file:{path.name}")
    if errors:
        return {"ok": False, "errors": errors, "created_utc": utc_now()}

    chain = load_json(chain_path)
    env_manifest = load_json(environment_manifest_path)
    scorer_manifest = load_json(scorer_manifest_path)
    agent_manifest = load_json(agent_manifest_path)
    no_leakage = load_json(no_leakage_path)
    compute_manifest = load_json(compute_manifest_path)
    ledger = load_json(ledger_path)
    sidecar = load_json(sidecar_path)
    plan = load_json(plan_path)
    execution = load_json(execution_path)
    ingestion = load_json(ingestion_path)
    artifact_hashes = load_json(artifact_hashes_path)

    errors.extend(validate_crsi_chain(chain))
    errors.extend(validate_no_leakage_manifest(no_leakage))
    errors.extend(validate_agent_manifest(agent_manifest, str(ledger.get("run_mode"))))
    errors.extend(verify_live_official_checkout(official_root, env_manifest, scorer_manifest))
    if not verify_document_self_hash(env_manifest, "manifest_hash"):
        errors.append("official_environment_manifest_self_hash_invalid")
    if not verify_document_self_hash(scorer_manifest, "manifest_hash"):
        errors.append("scorer_manifest_self_hash_invalid")
    if not verify_document_self_hash(agent_manifest, "manifest_hash"):
        errors.append("agent_manifest_self_hash_invalid")
    for document, field, label in [
        (plan, "plan_hash", "run_plan"),
        (execution, "report_hash", "execution_report"),
        (ledger, "ledger_hash", "score_ledger"),
        (sidecar, "sidecar_hash", "certificate_sidecar"),
        (ingestion, "report_hash", "ingestion_report"),
    ]:
        if not verify_document_self_hash(document, field):
            errors.append(f"{label}_self_hash_invalid")

    expected_inputs = {
        "crsi_chain_summary_sha256": sha256_file(chain_path),
        "official_environment_manifest_sha256": sha256_file(environment_manifest_path),
        "pinned_scorer_manifest_sha256": sha256_file(scorer_manifest_path),
        "agent_entrypoint_manifest_sha256": sha256_file(agent_manifest_path),
        "no_leakage_manifest_sha256": sha256_file(no_leakage_path),
        "run_plan_sha256": sha256_file(plan_path),
        "execution_report_sha256": sha256_file(execution_path),
    }
    for key, expected in expected_inputs.items():
        if ledger.get("input_hashes", {}).get(key) != expected:
            errors.append(f"ledger_input_hash_mismatch:{key}")

    crsi_reproduction = run_crsi_reproduction(repo_root, chain_path, result_dir)
    if not crsi_reproduction["ok"]:
        errors.append("crsi_core_reproduction_failed")

    recomputed_rows: List[Dict[str, Any]] = []
    task_runlogs: List[Dict[str, Any]] = []
    stored_by_key = {
        (int(row["package_index"]), str(row["environment_id"]), int(row["seed"])): row
        for row in ledger.get("score_artifacts", [])
        if isinstance(row, Mapping)
    }

    for plan_row in plan.get("runs", []):
        package_index = int(plan_row["package_index"])
        environment_id = str(plan_row["environment_id"])
        seed = int(plan_row["seed"])
        environment_dir = result_dir / str(plan_row["run_key"])
        errors.extend(f"{plan_row['run_key']}:{err}" for err in ensure_required_run_artifacts(environment_dir))
        required = [environment_dir / "normalized_score_artifact.json", environment_dir / "artifact_hashes.json"]
        for path in required:
            if not path.is_file():
                errors.append(f"{plan_row['run_key']}:missing:{path.name}")
        if any(not path.exists() for path in required) or ensure_required_run_artifacts(environment_dir):
            continue

        task_runlog = load_json(environment_dir / "task_runlog.json")
        task_runlogs.append(task_runlog)
        provenance = load_json(environment_dir / "raw_score_provenance.json")
        usage = load_json(environment_dir / "usage.json")
        errors.extend(f"{plan_row['run_key']}:usage:{err}" for err in validate_usage_record(usage, expected_run_id=task_runlog.get("vivaria_run_id")))
        if provenance.get("source_kind") != "official_scorer_export":
            errors.append(f"{plan_row['run_key']}:invalid_raw_score_provenance_source")
        if provenance.get("manual_or_declared_score") is not False:
            errors.append(f"{plan_row['run_key']}:raw_score_provenance_allows_manual_score")
        if provenance.get("vivaria_run_id") != task_runlog.get("vivaria_run_id"):
            errors.append(f"{plan_row['run_key']}:raw_score_provenance_run_id_mismatch")
        if provenance.get("raw_score_log_sha256") != sha256_file(environment_dir / "raw_score_log.json"):
            errors.append(f"{plan_row['run_key']}:raw_score_provenance_log_hash_mismatch")
        if provenance.get("scorer_manifest_hash") != scorer_manifest.get("manifest_hash"):
            errors.append(f"{plan_row['run_key']}:raw_score_provenance_scorer_manifest_mismatch")
        if provenance.get("provenance_hash") and not verify_document_self_hash(provenance, "provenance_hash"):
            errors.append(f"{plan_row['run_key']}:raw_score_provenance_self_hash_invalid")
        if task_runlog.get("compute_used") != usage:
            errors.append(f"{plan_row['run_key']}:task_runlog_usage_mismatch")
        stored = load_json(environment_dir / "normalized_score_artifact.json")
        if not verify_document_self_hash(stored, "score_artifact_hash"):
            errors.append(f"{plan_row['run_key']}:score_artifact_self_hash_invalid")
        scorer = scorer_row(scorer_manifest, environment_id)
        profile = profile_row(agent_manifest, package_index)
        try:
            entries = parse_score_log(environment_dir / "raw_score_log.json")
            raw, official_index = select_official_score(entries, str(scorer["aggregation"]))
            best, best_index = select_best_score(entries, str(scorer["raw_score_direction"]))
            normalized = normalize_re_bench_score(raw, float(scorer["starting_score"]), float(scorer["reference_score"]))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{plan_row['run_key']}:raw_score_reproduction_failed:{exc}")
            continue
        checks = {
            "raw_score": raw,
            "normalized_score": normalized,
            "best_score": best,
            "official_selected_entry_index": official_index,
            "best_entry_index": best_index,
            "time_to_best_seconds": elapsed_at_entry(entries, best_index),
            "raw_score_log_sha256": sha256_file(environment_dir / "raw_score_log.json"),
            "raw_score_provenance_sha256": sha256_file(environment_dir / "raw_score_provenance.json"),
            "usage_sha256": sha256_file(environment_dir / "usage.json"),
            "compute_used": usage,
            "task_runlog_sha256": sha256_file(environment_dir / "task_runlog.json"),
            "agent_trajectory_sha256": hash_file_or_tree(environment_dir / "agent_trajectory.json"),
            "submission_hash": hash_file_or_tree(environment_dir / "final_submission"),
            "scorer_hash": scorer["scorer_sha256"],
            "policy_hash": profile["profile_sha256"],
            "core_successor_id": profile["core_successor_id"],
            "benchmark_successor_id": profile["benchmark_successor_id"],
        }
        for key, expected in checks.items():
            actual = stored.get(key)
            if isinstance(expected, float) or isinstance(actual, float):
                if expected is None and actual is None:
                    continue
                if not close_number(actual, expected):
                    errors.append(f"{plan_row['run_key']}:score_artifact_mismatch:{key}")
            elif actual != expected:
                errors.append(f"{plan_row['run_key']}:score_artifact_mismatch:{key}")
        if stored.get("score_source") != "exported_official_scorer_log" or stored.get("manually_declared_score") is not False:
            errors.append(f"{plan_row['run_key']}:invalid_score_source")
        key = (package_index, environment_id, seed)
        ledger_row = stored_by_key.get(key)
        if ledger_row is None or ledger_row.get("score_artifact_hash") != stored.get("score_artifact_hash"):
            errors.append(f"{plan_row['run_key']}:ledger_score_artifact_mismatch")
        recomputed_rows.append(stored)

        local_hashes = load_json(environment_dir / "artifact_hashes.json")
        for path_value, expected_hash in local_hashes.items():
            path = resolve(repo_root, path_value)
            if not path.exists() or hash_file_or_tree(path) != expected_hash:
                errors.append(f"{plan_row['run_key']}:local_artifact_hash_mismatch:{path_value}")

    budget_errors = validate_budget_equivalence(task_runlogs)
    errors.extend(budget_errors)
    budget = budget_profile(compute_manifest, str(ledger.get("run_mode")))
    progression = evaluate_score_progression(
        recomputed_rows,
        epsilon=float(budget["per_environment_regression_epsilon"]),
    ) if recomputed_rows else {"ok": False}
    if progression != ledger.get("progression"):
        errors.append("score_progression_mismatch")
    if not progression.get("ok"):
        errors.append("recomputed_score_progression_not_accepted")

    if sidecar.get("score_ledger_sha256") != sha256_file(ledger_path):
        errors.append("sidecar_score_ledger_sha256_mismatch")
    if sidecar.get("score_ledger_hash") != ledger.get("ledger_hash"):
        errors.append("sidecar_score_ledger_hash_mismatch")
    if sidecar.get("ok") is not True or ledger.get("ok") is not True or ingestion.get("ok") is not True:
        errors.append("recorded_result_not_ok")
    if not all(value is True for value in sidecar.get("bridge_invariants", {}).values()):
        errors.append("bridge_invariant_false")

    for path_value, expected_hash in artifact_hashes.items():
        path = resolve(repo_root, path_value)
        if not path.exists():
            errors.append(f"missing_global_artifact:{path_value}")
        elif hash_file_or_tree(path) != expected_hash:
            errors.append(f"global_artifact_hash_mismatch:{path_value}")

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "kind": "crsi_re_bench_reproduction_report",
        "result_dir": str(result_dir.resolve()),
        "run_mode": ledger.get("run_mode"),
        "seed": ledger.get("seed"),
        "score_artifact_count": len(recomputed_rows),
        "crsi_core_reproduction": crsi_reproduction,
        "recomputed_progression": progression,
        "errors": sorted(set(errors)),
        "created_utc": utc_now(),
    }
    report["ok"] = not report["errors"]
    report["report_hash"] = sha256_obj({k: v for k, v in report.items() if k != "report_hash"})
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproduce every input hash, score, aggregate, and acceptance condition for CRSI-RE-Bench v1.")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--result-dir", type=Path, required=True)
    p.add_argument("--official-release-root", type=Path, required=True)
    p.add_argument("--crsi-chain-summary", type=Path, required=True)
    p.add_argument("--official-environment-hashes", type=Path, required=True)
    p.add_argument("--pinned-scorer-manifest", type=Path, required=True)
    p.add_argument("--agent-entrypoint-manifest", type=Path, required=True)
    p.add_argument("--no-leakage-manifest", type=Path, required=True)
    p.add_argument("--compute-budget-manifest", type=Path, default=THIS / "compute_budget_manifest.json")
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root(args.repo_root)

    def pth(value: Path) -> Path:
        return value if value.is_absolute() else repo_root / value

    report = verify_result(
        repo_root=repo_root,
        result_dir=pth(args.result_dir),
        official_root=pth(args.official_release_root),
        chain_path=pth(args.crsi_chain_summary),
        environment_manifest_path=pth(args.official_environment_hashes),
        scorer_manifest_path=pth(args.pinned_scorer_manifest),
        agent_manifest_path=pth(args.agent_entrypoint_manifest),
        no_leakage_path=pth(args.no_leakage_manifest),
        compute_manifest_path=pth(args.compute_budget_manifest),
    )
    out = pth(args.out) if args.out else pth(args.result_dir) / "reproduction_report.json"
    write_json(out, report)
    print(json.dumps({"ok": report["ok"], "report": str(out), "errors": report["errors"]}, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
