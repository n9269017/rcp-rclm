#!/usr/bin/env python3
"""Offline reproduction checker for CRSI-RE-Bench v1 result directories."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    load_json,
    progression_analysis,
    self_hash,
    sha256_file,
    utc_now,
    validate_agent_entrypoint_manifest,
    validate_core_chain,
    validate_hash_map,
    validate_no_leakage_manifest,
    write_json,
)
from re_bench_score_adapter import find_environment, find_scorer, load_raw_score_entries
from crsi_re_bench_schema import select_best_score


def repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "artifacts" / "crsi_core" / "reproduce_crsi_core.py").exists():
            return candidate
    raise FileNotFoundError("Could not locate repository root")


def run_core_reproduction(repo: Path, chain_path: Path, out_path: Path) -> Dict[str, Any]:
    checker = repo / "artifacts" / "crsi_core" / "reproduce_crsi_core.py"
    proc = subprocess.run(
        [sys.executable, str(checker), str(chain_path), "--out", str(out_path)],
        cwd=str(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    parsed: Dict[str, Any] = {}
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pass
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "parsed": parsed}


def resolve(path: Path, repo: Path) -> Path:
    return path if path.is_absolute() else repo / path


def verify(args: argparse.Namespace, repo: Path) -> Dict[str, Any]:
    result_dir = args.result_dir.resolve()
    chain_path = args.crsi_chain_summary.resolve()
    pin_path = args.official_environment_hashes.resolve()
    scorer_path = args.pinned_scorer_manifest.resolve()
    agent_path = args.agent_entrypoint_manifest.resolve()
    leakage_path = args.no_leakage_manifest.resolve()
    budget_path = args.compute_budget_manifest.resolve()

    chain = load_json(chain_path)
    pin = load_json(pin_path)
    scorer = load_json(scorer_path)
    agent = load_json(agent_path)
    leakage = load_json(leakage_path)
    budgets = load_json(budget_path)
    plan = load_json(result_dir / "run_plan.json")
    execution = load_json(result_dir / "execution_report.json")
    ledger = load_json(result_dir / "crsi_re_bench_score_ledger.json")
    sidecar = load_json(result_dir / "certificate_bridge_sidecar.json")
    errors: List[str] = []

    errors.extend(validate_core_chain(chain))
    errors.extend(validate_agent_entrypoint_manifest(agent, chain, full_mode=ledger.get("run_mode") != "pilot"))
    errors.extend(validate_no_leakage_manifest(leakage))
    if pin.get("manifest_hash") != self_hash(pin, "manifest_hash") or pin.get("ok") is not True:
        errors.append("official_environment_pin_invalid")
    if scorer.get("manifest_hash") != self_hash(scorer, "manifest_hash") or scorer.get("ok") is not True:
        errors.append("scorer_manifest_invalid")
    if plan.get("plan_hash") != self_hash(plan, "plan_hash") or plan.get("ok") is not True:
        errors.append("run_plan_invalid")
    if execution.get("execution_report_hash") != self_hash(execution, "execution_report_hash") or execution.get("ok") is not True:
        errors.append("execution_report_invalid")
    if ledger.get("ledger_hash") != self_hash(ledger, "ledger_hash"):
        errors.append("score_ledger_hash_mismatch")
    if sidecar.get("sidecar_hash") != self_hash(sidecar, "sidecar_hash"):
        errors.append("certificate_bridge_sidecar_hash_mismatch")

    input_paths = {
        "chain": chain_path,
        "pin": pin_path,
        "scorer": scorer_path,
        "agent": agent_path,
        "no_leakage": leakage_path,
        "budgets": budget_path,
    }
    for key, path in input_paths.items():
        expected = sidecar.get("input_hashes", {}).get(key)
        if expected != sha256_file(path):
            errors.append(f"sidecar_input_hash_mismatch:{key}")
    if sidecar.get("run_plan_hash") != plan.get("plan_hash"):
        errors.append("sidecar_plan_hash_mismatch")
    if sidecar.get("execution_report_hash") != execution.get("execution_report_hash"):
        errors.append("sidecar_execution_hash_mismatch")
    if sidecar.get("score_ledger_hash") != ledger.get("ledger_hash"):
        errors.append("sidecar_ledger_hash_mismatch")

    policy_by_index = {int(record["package_index"]): record for record in agent.get("resolved_profiles", [])}
    stored_artifacts: List[Mapping[str, Any]] = []
    by_package: Dict[int, Dict[str, Any]] = {}
    for run in plan.get("runs", []):
        run_dir = result_dir / str(run["result_relative_dir"])
        hash_manifest_path = run_dir / "artifact_hashes.json"
        if not hash_manifest_path.is_file():
            errors.append(f"run_{run['run_index']}:artifact_hash_manifest_missing")
            continue
        hash_manifest = load_json(hash_manifest_path)
        errors.extend(f"run_{run['run_index']}:{err}" for err in validate_hash_map(run_dir, hash_manifest.get("hashes", {})))
        score_path = run_dir / "normalized_score_artifact.json"
        if not score_path.is_file():
            errors.append(f"run_{run['run_index']}:normalized_score_artifact_missing")
            continue
        artifact = load_json(score_path)
        stored_artifacts.append(artifact)
        if artifact.get("score_artifact_hash") != self_hash(artifact, "score_artifact_hash"):
            errors.append(f"run_{run['run_index']}:score_artifact_hash_mismatch")
        environment = find_environment(pin, str(run["environment_id"]))
        scorer_row = find_scorer(scorer, str(run["environment_id"]))
        entries = load_raw_score_entries(run_dir / "raw_score_log.json")
        selection = select_best_score(entries, environment)
        if abs(float(artifact.get("raw_score", float("nan"))) - float(selection["raw_score"])) > 1e-12:
            errors.append(f"run_{run['run_index']}:raw_score_recompute_mismatch")
        if abs(float(artifact.get("normalized_score", float("nan"))) - float(selection["normalized_score"])) > 1e-12:
            errors.append(f"run_{run['run_index']}:normalized_score_recompute_mismatch")
        if artifact.get("scorer_hash") != scorer_row.get("official_scorer_sha256"):
            errors.append(f"run_{run['run_index']}:scorer_hash_mismatch")
        policy = policy_by_index.get(int(run["package_index"]), {})
        for key in ["core_successor_id", "benchmark_successor_id", "policy_hash"]:
            if artifact.get(key) != policy.get(key):
                errors.append(f"run_{run['run_index']}:{key}_mismatch")
        provenance = load_json(run_dir / "raw_score_provenance.json")
        if provenance.get("raw_score_log_sha256") != sha256_file(run_dir / "raw_score_log.json"):
            errors.append(f"run_{run['run_index']}:raw_score_provenance_hash_mismatch")
        if provenance.get("manual_or_declared_score") is not False:
            errors.append(f"run_{run['run_index']}:manual_score_flag_not_false")

        package_index = int(artifact["package_index"])
        package = by_package.setdefault(package_index, {
            "package_index": package_index,
            "core_successor_id": artifact["core_successor_id"],
            "benchmark_successor_id": artifact["benchmark_successor_id"],
            "policy_hash": artifact["policy_hash"],
            "environment_scores": {},
            "score_artifact_hashes": {},
        })
        package["environment_scores"][artifact["environment_id"]] = artifact["normalized_score"]
        package["score_artifact_hashes"][artifact["environment_id"]] = artifact["score_artifact_hash"]

    environment_ids = list(ledger.get("environment_ids", []))
    package_rows: List[Dict[str, Any]] = []
    for index in sorted(by_package):
        row = by_package[index]
        scores = [float(row["environment_scores"].get(env, 0.0)) for env in environment_ids]
        row["re_score"] = sum(scores) / len(scores) if scores else 0.0
        package_rows.append(row)
    if package_rows != ledger.get("packages"):
        errors.append("score_ledger_package_rows_recompute_mismatch")

    profile_map = {"pilot": "pilot_rust_60m", "full60": "full_suite_60m", "full480": "full_suite_480m"}
    budget_profile = budgets["profiles"][profile_map[str(ledger.get("run_mode"))]]
    progression = progression_analysis(package_rows, environment_ids, float(budget_profile.get("per_environment_regression_epsilon", 0.05)))
    if progression != ledger.get("progression"):
        errors.append("score_progression_recompute_mismatch")
    if ledger.get("manual_or_declared_scores_accepted") is not False:
        errors.append("ledger_accepts_manual_scores")
    if ledger.get("ok") is not True:
        errors.append("score_ledger_not_accepted")
    if sidecar.get("ok") is not True:
        errors.append("certificate_bridge_sidecar_not_accepted")
    for key, value in sidecar.get("bridge_invariants", {}).items():
        if value is not True:
            errors.append(f"bridge_invariant_false:{key}")

    core_report_path = args.core_reproduction_out or result_dir / "crsi_core_reproduction_report.json"
    core_result = run_core_reproduction(repo, chain_path, core_report_path.resolve())
    if core_result["returncode"] != 0 or core_result.get("parsed", {}).get("ok") is not True:
        errors.append("core_chain_reproduction_failed")

    report = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "result_dir": str(result_dir),
        "run_mode": ledger.get("run_mode"),
        "seed": ledger.get("seed"),
        "score_artifact_count": len(stored_artifacts),
        "core_reproduction_report": str(core_report_path.resolve()),
        "created_utc": utc_now(),
        "errors": errors,
        "ok": not errors,
    }
    report["reproduction_report_hash"] = self_hash(report, "reproduction_report_hash")
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reproduce a CRSI-RE-Bench v1 result directory offline.")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--crsi-chain-summary", type=Path, required=True)
    parser.add_argument("--official-environment-hashes", type=Path, required=True)
    parser.add_argument("--pinned-scorer-manifest", type=Path, required=True)
    parser.add_argument("--agent-entrypoint-manifest", type=Path, required=True)
    parser.add_argument("--no-leakage-manifest", type=Path, required=True)
    parser.add_argument("--compute-budget-manifest", type=Path, default=Path(__file__).resolve().parent / "compute_budget_manifest.json")
    parser.add_argument("--core-reproduction-out", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo = repo_root(args.repo_root)
    for field in [
        "result_dir", "crsi_chain_summary", "official_environment_hashes", "pinned_scorer_manifest",
        "agent_entrypoint_manifest", "no_leakage_manifest", "compute_budget_manifest",
    ]:
        setattr(args, field, resolve(getattr(args, field), repo).resolve())
    if args.core_reproduction_out is not None:
        args.core_reproduction_out = resolve(args.core_reproduction_out, repo)
    report = verify(args, repo)
    out = args.out.resolve() if args.out else args.result_dir / "reproduction_report.json"
    write_json(out, report)
    print(json.dumps({"ok": report["ok"], "report": str(out), "errors": report["errors"]}, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
