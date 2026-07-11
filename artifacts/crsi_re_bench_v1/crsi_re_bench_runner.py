#!/usr/bin/env python3
"""Plan, gate, execute, and ingest CRSI runs on official RE-Bench v1 tasks.

Phases:
  preflight - verify immutable inputs and certificate/no-leakage conditions
  plan      - construct equal-budget concrete Vivaria commands
  execute   - launch only behind OFFICIAL_RE_BENCH_V1 and export all evidence
  ingest    - normalize scorer-produced logs and construct the certificate bridge

The runner never substitutes manually declared benchmark scores for official
scorer exports.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from crsi_re_bench_schema import (
    EXECUTION_CONFIRMATION,
    SCHEMA_VERSION,
    SUITE_NAME,
    collect_artifact_hashes,
    core_certificate_summary,
    deterministic_tree_sha256,
    equal_usage_limits,
    load_json,
    progression_analysis,
    safe_rel,
    self_hash,
    sha256_file,
    sha256_obj,
    utc_now,
    validate_agent_entrypoint_manifest,
    validate_core_chain,
    validate_no_leakage_manifest,
    verify_clean_git_checkout,
    write_json,
)
from re_bench_score_adapter import build_score_artifact

THIS = Path(__file__).resolve().parent
DEFAULT_BUDGETS = THIS / "compute_budget_manifest.json"
RUN_MODE_TO_PROFILE = {
    "pilot": "pilot_rust_60m",
    "full60": "full_suite_60m",
    "full480": "full_suite_480m",
}


def repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "artifacts" / "crsi_core" / "reproduce_crsi_core.py").exists():
            return candidate
    raise FileNotFoundError("Could not locate repository root")


def run_process(cmd: Sequence[str], cwd: Path) -> Dict[str, Any]:
    proc = subprocess.run(list(cmd), cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return {"command": list(cmd), "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def run_shell(command: str, cwd: Path) -> Dict[str, Any]:
    proc = subprocess.run(command, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def parse_run_id(stdout: str) -> Optional[int]:
    for line in stdout.splitlines():
        if re.fullmatch(r"\s*\d+\s*", line):
            return int(line.strip())
    match = re.search(r"/run/(?:#)?(\d+)", stdout)
    if match:
        return int(match.group(1))
    return None


def find_environment(pin: Mapping[str, Any], environment_id: str) -> Mapping[str, Any]:
    for env in pin.get("environments", []):
        if isinstance(env, Mapping) and env.get("environment_id") == environment_id:
            return env
    raise KeyError(environment_id)


def find_scorer(scorer_manifest: Mapping[str, Any], environment_id: str) -> Mapping[str, Any]:
    for scorer in scorer_manifest.get("scorers", []):
        if isinstance(scorer, Mapping) and scorer.get("environment_id") == environment_id:
            return scorer
    raise KeyError(environment_id)


def verify_live_official_pin(official_root: Path, pin: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    checkout = verify_clean_git_checkout(official_root, str(pin.get("repository_commit", "")))
    errors.extend(checkout.get("errors", []))
    for env in pin.get("environments", []):
        if not isinstance(env, Mapping):
            errors.append("official_pin_environment_not_object")
            continue
        for path_field, hash_field in [
            ("manifest_path", "manifest_sha256"),
            ("task_family_implementation_path", "task_family_implementation_sha256"),
            ("official_scorer_path", "official_scorer_sha256"),
        ]:
            relative = env.get(path_field)
            expected = env.get(hash_field)
            if not relative or not expected:
                errors.append(f"{env.get('environment_id')}:missing_pin_field:{path_field}/{hash_field}")
                continue
            path = official_root / str(relative)
            if not path.is_file():
                errors.append(f"{env.get('environment_id')}:missing_live_file:{relative}")
            elif sha256_file(path) != expected:
                errors.append(f"{env.get('environment_id')}:live_hash_mismatch:{relative}")
        family_root = official_root / str(env.get("task_family", ""))
        if family_root.is_dir() and env.get("task_family_tree_sha256"):
            if deterministic_tree_sha256(family_root) != env["task_family_tree_sha256"]:
                errors.append(f"{env.get('environment_id')}:task_family_tree_hash_mismatch")
    return errors


def run_core_reproduction(repo: Path, chain_path: Path, outdir: Path) -> Dict[str, Any]:
    checker = repo / "artifacts" / "crsi_core" / "reproduce_crsi_core.py"
    report_path = outdir / "crsi_core_reproduction_report.json"
    result = run_process([sys.executable, str(checker), str(chain_path), "--out", str(report_path)], repo)
    parsed: Dict[str, Any] = {}
    try:
        parsed = json.loads(result["stdout"])
    except json.JSONDecodeError:
        pass
    return {**result, "parsed": parsed, "report_path": report_path}


def load_inputs(args: argparse.Namespace, repo: Path) -> Dict[str, Any]:
    paths = {
        "chain": args.crsi_chain_summary.resolve(),
        "pin": args.official_environment_hashes.resolve(),
        "scorer": args.pinned_scorer_manifest.resolve(),
        "agent": args.agent_entrypoint_manifest.resolve(),
        "no_leakage": args.no_leakage_manifest.resolve(),
        "budgets": args.compute_budget_manifest.resolve(),
    }
    return {"paths": paths, **{key: load_json(path) for key, path in paths.items()}}


def preflight(args: argparse.Namespace, repo: Path, outdir: Path) -> Dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(args, repo)
    chain, pin, scorer, agent, no_leakage = (inputs[key] for key in ["chain", "pin", "scorer", "agent", "no_leakage"])
    errors: List[str] = []
    errors.extend(validate_core_chain(chain))
    errors.extend(validate_agent_entrypoint_manifest(agent, chain, full_mode=args.run_mode != "pilot"))
    errors.extend(validate_no_leakage_manifest(no_leakage))
    if pin.get("ok") is not True or pin.get("resolved") is not True:
        errors.append("official_environment_pin_not_ok")
    if scorer.get("ok") is not True or scorer.get("resolved") is not True:
        errors.append("pinned_scorer_manifest_not_ok")
    if scorer.get("manual_or_declared_scores_accepted") is not False:
        errors.append("scorer_manifest_allows_manual_scores")
    if pin.get("manifest_hash") != scorer.get("official_environment_pin_hash"):
        errors.append("scorer_manifest_official_pin_hash_mismatch")
    if len(pin.get("environments", [])) != 7 or len(scorer.get("scorers", [])) != 7:
        errors.append("official_environment_or_scorer_count_not_seven")
    errors.extend(verify_live_official_pin(args.official_release_root.resolve(), pin))

    reproduction = run_core_reproduction(repo, inputs["paths"]["chain"], outdir)
    if reproduction["returncode"] != 0 or reproduction.get("parsed", {}).get("ok") is not True:
        errors.append("crsi_core_reproduction_failed")

    profile_name = RUN_MODE_TO_PROFILE[args.run_mode]
    budgets = inputs["budgets"]
    profile = budgets.get("profiles", {}).get(profile_name)
    if not isinstance(profile, Mapping):
        errors.append(f"compute_budget_profile_missing:{profile_name}")
    if args.run_mode != "pilot" and agent.get("policy_provenance_mode") != "predecessor_generated":
        errors.append("full_mode_requires_predecessor_generated_policies")

    report = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "phase": "preflight",
        "run_mode": args.run_mode,
        "budget_profile_id": profile_name,
        "input_paths": {key: safe_rel(path, repo) for key, path in inputs["paths"].items()},
        "input_hashes": {key: sha256_file(path) for key, path in inputs["paths"].items()},
        "official_release_root": str(args.official_release_root.resolve()),
        "crsi_core_reproduction_report": safe_rel(reproduction["report_path"], repo),
        "core_certificate_summary": core_certificate_summary(chain),
        "created_utc": utc_now(),
        "errors": errors,
        "ok": not errors,
    }
    report["report_hash"] = self_hash(report, "report_hash")
    write_json(outdir / "preflight_report.json", report)
    return report


def build_plan(args: argparse.Namespace, repo: Path, outdir: Path) -> Dict[str, Any]:
    preflight_report = preflight(args, repo, outdir)
    inputs = load_inputs(args, repo)
    chain, pin, agent, budgets = (inputs[key] for key in ["chain", "pin", "agent", "budgets"])
    profile_name = RUN_MODE_TO_PROFILE[args.run_mode]
    budget = budgets["profiles"][profile_name]
    errors = list(preflight_report["errors"])
    if args.seed not in budget.get("seeds", []):
        errors.append(f"seed_not_allowed_by_budget_profile:{args.seed}")
    selected_environment_ids = list(budget.get("environments", []))
    selected_environments = [find_environment(pin, environment_id) for environment_id in selected_environment_ids]
    profiles = agent.get("resolved_profiles", [])
    runs: List[Dict[str, Any]] = []
    secrets_env = args.secrets_env.resolve()
    if not secrets_env.is_file():
        errors.append(f"secrets_env_missing:{secrets_env}")
    agent_root = Path(agent.get("agent_repository", {}).get("agent_root", ""))
    if not agent_root.is_dir():
        errors.append(f"agent_root_missing:{agent_root}")

    for policy in profiles:
        package_index = int(policy["package_index"])
        source_profile_path = repo / str(policy["source_profile_path"])
        for environment in selected_environments:
            suite_index = int(environment.get("suite_index", selected_environment_ids.index(environment["environment_id"])))
            result_relative = Path(f"package_RCLM_{package_index}") / f"environment_{suite_index}_{environment['environment_id']}"
            name = f"crsi-rebench-{args.run_mode}-s{args.seed}-p{package_index}-{environment['environment_id']}"
            command = [
                args.viv_executable,
                "run",
                str(environment["task_id"]),
                "--yes",
                "--agent-path",
                str(agent_root),
                "--task-family-path",
                str(args.official_release_root.resolve() / str(environment["task_family"])),
                "--env-file-path",
                str(secrets_env),
                "--agent-settings-override",
                safe_rel(source_profile_path, repo),
                "--max-tokens",
                str(budget["max_tokens_per_run"]),
                "--max-actions",
                str(budget["max_actions_per_run"]),
                "--max-total-seconds",
                str(budget["wall_time_seconds_per_run"]),
                "--max-cost",
                str(budget["max_model_api_cost_per_run"]),
                "--priority",
                str(budget.get("priority", "low")),
                "--batch-concurrency-limit",
                str(budget.get("batch_concurrency_limit", 1)),
                "--name",
                name,
            ]
            runs.append({
                "run_index": len(runs),
                "seed": args.seed,
                "package_index": package_index,
                "core_successor_id": policy["core_successor_id"],
                "benchmark_successor_id": policy["benchmark_successor_id"],
                "policy_hash": policy["policy_hash"],
                "policy_profile_path": safe_rel(source_profile_path, repo),
                "environment_id": environment["environment_id"],
                "suite_index": suite_index,
                "task_family": environment["task_family"],
                "task_id": environment["task_id"],
                "official_scorer_sha256": find_scorer(inputs["scorer"], environment["environment_id"])["official_scorer_sha256"],
                "scorer_bundle_sha256": find_scorer(inputs["scorer"], environment["environment_id"])["scorer_bundle_sha256"],
                "usage_limits": {
                    "tokens": budget["max_tokens_per_run"],
                    "actions": budget["max_actions_per_run"],
                    "total_seconds": budget["wall_time_seconds_per_run"],
                    "cost": budget["max_model_api_cost_per_run"],
                },
                "resource_requirements": environment["resources"],
                "model_access_policy_id": budget["model_access_policy_id"],
                "network_policy": budget["network_policy"],
                "result_relative_dir": str(result_relative).replace("\\", "/"),
                "command": command,
            })

    plan = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "phase": "plan",
        "run_mode": args.run_mode,
        "budget_profile_id": profile_name,
        "seed": args.seed,
        "package_count": len(profiles),
        "environment_count": len(selected_environments),
        "run_count": len(runs),
        "official_environment_pin_hash": inputs["pin"].get("manifest_hash"),
        "scorer_manifest_hash": inputs["scorer"].get("manifest_hash"),
        "agent_entrypoint_manifest_hash": inputs["agent"].get("manifest_hash"),
        "no_leakage_attestation_hash": inputs["no_leakage"].get("attestation_hash"),
        "compute_budget_manifest_sha256": sha256_file(inputs["paths"]["budgets"]),
        "crsi_chain_summary_sha256": sha256_file(inputs["paths"]["chain"]),
        "preflight_report_hash": preflight_report["report_hash"],
        "runs": runs,
        "created_utc": utc_now(),
        "errors": errors,
        "ok": preflight_report["ok"] and not errors and len(runs) == len(profiles) * len(selected_environments),
    }
    plan["plan_hash"] = self_hash(plan, "plan_hash")
    write_json(outdir / "run_plan.json", plan)
    return plan


def format_export(template: str, *, run_id: int, out: Path, run: Mapping[str, Any]) -> str:
    return template.format(
        run_id=run_id,
        out=str(out.resolve()),
        package_index=run["package_index"],
        family=run["task_family"],
        environment_id=run["environment_id"],
        seed=run["seed"],
    )


def execute_plan(args: argparse.Namespace, repo: Path, outdir: Path) -> Dict[str, Any]:
    if args.confirm_execute != EXECUTION_CONFIRMATION:
        raise ValueError(f"Execution requires --confirm-execute {EXECUTION_CONFIRMATION}")
    required_templates = {
        "score": args.score_export_command_template,
        "trajectory": args.trajectory_export_command_template,
        "submission": args.submission_export_command_template,
        "usage": args.usage_export_command_template,
    }
    missing = [key for key, value in required_templates.items() if not value]
    if missing:
        raise ValueError(f"missing required export command templates: {missing}")

    plan = load_json(args.plan.resolve())
    if plan.get("ok") is not True or plan.get("plan_hash") != self_hash(plan, "plan_hash"):
        raise ValueError("run plan is not valid/hash-consistent")
    no_leakage = load_json(args.no_leakage_manifest.resolve())
    leakage_errors = validate_no_leakage_manifest(no_leakage)
    if leakage_errors:
        raise ValueError(f"no-leakage manifest invalid: {leakage_errors}")

    run_reports: List[Dict[str, Any]] = []
    overall_errors: List[str] = []
    for run in plan.get("runs", []):
        result_dir = outdir / str(run["result_relative_dir"])
        result_dir.mkdir(parents=True, exist_ok=True)
        start = utc_now()
        viv_result = run_process(run["command"], repo)
        (result_dir / "viv_stdout.txt").write_text(viv_result["stdout"], encoding="utf-8")
        (result_dir / "viv_stderr.txt").write_text(viv_result["stderr"], encoding="utf-8")
        run_id = parse_run_id(viv_result["stdout"])
        run_errors: List[str] = []
        if viv_result["returncode"] != 0:
            run_errors.append(f"viv_run_failed:{viv_result['returncode']}")
        if run_id is None:
            run_errors.append("vivaria_run_id_not_found")

        completion_result = None
        if run_id is not None and args.completion_command_template:
            command = format_export(args.completion_command_template, run_id=run_id, out=result_dir, run=run)
            completion_result = run_shell(command, repo)
            (result_dir / "completion_stdout.txt").write_text(completion_result["stdout"], encoding="utf-8")
            (result_dir / "completion_stderr.txt").write_text(completion_result["stderr"], encoding="utf-8")
            if completion_result["returncode"] != 0:
                run_errors.append("completion_command_failed")

        export_results: Dict[str, Any] = {}
        targets = {
            "score": result_dir / "raw_score_log.json",
            "trajectory": result_dir / "agent_trajectory.json",
            "submission": result_dir / "final_submission",
            "usage": result_dir / "usage.json",
        }
        if run_id is not None and not run_errors:
            for kind, template in required_templates.items():
                target = targets[kind]
                if kind == "submission":
                    target.mkdir(parents=True, exist_ok=True)
                command = format_export(template, run_id=run_id, out=target, run=run)
                result = run_shell(command, repo)
                export_results[kind] = result
                if kind == "score":
                    (result_dir / "scorer_stdout.txt").write_text(result["stdout"], encoding="utf-8")
                    (result_dir / "scorer_stderr.txt").write_text(result["stderr"], encoding="utf-8")
                else:
                    (result_dir / f"{kind}_export_stdout.txt").write_text(result["stdout"], encoding="utf-8")
                    (result_dir / f"{kind}_export_stderr.txt").write_text(result["stderr"], encoding="utf-8")
                if result["returncode"] != 0:
                    run_errors.append(f"{kind}_export_failed")
            for kind, target in targets.items():
                if kind == "submission":
                    if not target.is_dir() or not any(path.is_file() for path in target.rglob("*")):
                        run_errors.append("final_submission_empty_or_missing")
                elif not target.is_file() or target.stat().st_size == 0:
                    run_errors.append(f"{kind}_artifact_missing_or_empty")

        task_runlog = {
            "schema_version": SCHEMA_VERSION,
            "suite_name": SUITE_NAME,
            "source_kind": "vivaria_official_environment_execution",
            "run_index": run["run_index"],
            "seed": run["seed"],
            "package_index": run["package_index"],
            "core_successor_id": run["core_successor_id"],
            "benchmark_successor_id": run["benchmark_successor_id"],
            "policy_hash": run["policy_hash"],
            "environment_id": run["environment_id"],
            "task_family": run["task_family"],
            "task_id": run["task_id"],
            "vivaria_run_id": run_id,
            "usage_limits": run["usage_limits"],
            "resource_requirements": run["resource_requirements"],
            "model_access_policy_id": run["model_access_policy_id"],
            "network_policy": run["network_policy"],
            "viv_command": run["command"],
            "viv_returncode": viv_result["returncode"],
            "completion_wait_delegated_to_exporters": args.completion_command_template is None,
            "completion_command": completion_result["command"] if completion_result else None,
            "export_commands": {key: value.get("command") for key, value in export_results.items()},
            "started_utc": start,
            "completed_utc": utc_now(),
            "errors": run_errors,
            "ok": not run_errors,
        }
        task_runlog["runlog_hash"] = self_hash(task_runlog, "runlog_hash")
        write_json(result_dir / "task_runlog.json", task_runlog)

        if (result_dir / "raw_score_log.json").is_file() and run_id is not None:
            provenance = {
                "schema_version": SCHEMA_VERSION,
                "source_kind": "official_scorer_export",
                "producer": "external_score_export_command",
                "manual_or_declared_score": False,
                "vivaria_run_id": run_id,
                "score_export_command": export_results.get("score", {}).get("command"),
                "score_export_command_hash": sha256_obj(export_results.get("score", {}).get("command")),
                "raw_score_log_sha256": sha256_file(result_dir / "raw_score_log.json"),
                "scorer_manifest_hash": plan["scorer_manifest_hash"],
                "official_scorer_sha256": run["official_scorer_sha256"],
                "scorer_bundle_sha256": run["scorer_bundle_sha256"],
                "created_utc": utc_now(),
            }
            provenance["provenance_hash"] = self_hash(provenance, "provenance_hash")
            write_json(result_dir / "raw_score_provenance.json", provenance)

        hashes = collect_artifact_hashes(result_dir, exclude_names=["artifact_hashes.json"])
        write_json(result_dir / "artifact_hashes.json", {
            "schema_version": SCHEMA_VERSION,
            "root": safe_rel(result_dir, repo),
            "hashes": hashes,
            "created_utc": utc_now(),
        })
        run_reports.append({
            "run_index": run["run_index"],
            "result_relative_dir": run["result_relative_dir"],
            "vivaria_run_id": run_id,
            "errors": run_errors,
            "ok": not run_errors,
        })
        overall_errors.extend(f"run_{run['run_index']}:{error}" for error in run_errors)

    report = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "phase": "execute",
        "plan_path": safe_rel(args.plan.resolve(), repo),
        "plan_hash": plan["plan_hash"],
        "confirmation_token": args.confirm_execute,
        "run_count": len(run_reports),
        "runs": run_reports,
        "created_utc": utc_now(),
        "errors": overall_errors,
        "ok": not overall_errors and len(run_reports) == plan.get("run_count"),
    }
    report["execution_report_hash"] = self_hash(report, "execution_report_hash")
    write_json(outdir / "execution_report.json", report)
    return report


def ingest(args: argparse.Namespace, repo: Path, outdir: Path) -> Dict[str, Any]:
    inputs = load_inputs(args, repo)
    chain, pin, scorer, agent, no_leakage, budgets = (inputs[key] for key in ["chain", "pin", "scorer", "agent", "no_leakage", "budgets"])
    plan_path = args.plan.resolve() if args.plan else outdir / "run_plan.json"
    execution_path = args.execution_report.resolve() if args.execution_report else outdir / "execution_report.json"
    plan = load_json(plan_path)
    execution = load_json(execution_path)
    errors: List[str] = []
    errors.extend(validate_core_chain(chain))
    errors.extend(validate_agent_entrypoint_manifest(agent, chain, full_mode=args.run_mode != "pilot"))
    errors.extend(validate_no_leakage_manifest(no_leakage))
    if plan.get("ok") is not True or plan.get("plan_hash") != self_hash(plan, "plan_hash"):
        errors.append("run_plan_invalid")
    if execution.get("ok") is not True or execution.get("execution_report_hash") != self_hash(execution, "execution_report_hash"):
        errors.append("execution_report_invalid")

    score_artifacts: List[Dict[str, Any]] = []
    by_package: Dict[int, Dict[str, Any]] = {}
    by_environment: Dict[str, List[Dict[str, Any]]] = {}
    profiles_by_index = {int(row["package_index"]): row for row in agent.get("resolved_profiles", [])}
    for run in plan.get("runs", []):
        result_dir = outdir / str(run["result_relative_dir"])
        policy = profiles_by_index[int(run["package_index"])]
        artifact = build_score_artifact(
            repo_root=repo,
            environment_id=str(run["environment_id"]),
            raw_score_log=result_dir / "raw_score_log.json",
            raw_score_provenance=result_dir / "raw_score_provenance.json",
            usage_path=result_dir / "usage.json",
            task_runlog=result_dir / "task_runlog.json",
            submission_path=result_dir / "final_submission",
            trajectory_path=result_dir / "agent_trajectory.json",
            official_pin=pin,
            scorer_manifest=scorer,
            policy_record=policy,
        )
        write_json(result_dir / "normalized_score_artifact.json", artifact)
        hashes = collect_artifact_hashes(result_dir, exclude_names=["artifact_hashes.json"])
        write_json(result_dir / "artifact_hashes.json", {
            "schema_version": SCHEMA_VERSION,
            "root": safe_rel(result_dir, repo),
            "hashes": hashes,
            "created_utc": utc_now(),
        })
        if artifact.get("ok") is not True:
            errors.extend(f"run_{run['run_index']}:{item}" for item in artifact.get("errors", []))
        score_artifacts.append(artifact)
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
        by_environment.setdefault(artifact["environment_id"], []).append(artifact)

    package_rows = []
    selected_env_ids = [str(value) for value in budgets["profiles"][RUN_MODE_TO_PROFILE[args.run_mode]]["environments"]]
    for package_index in sorted(by_package):
        row = by_package[package_index]
        missing_envs = [env for env in selected_env_ids if env not in row["environment_scores"]]
        if missing_envs:
            errors.append(f"package_{package_index}:missing_environment_scores:{missing_envs}")
        values = [float(row["environment_scores"].get(env, 0.0)) for env in selected_env_ids]
        row["re_score"] = sum(values) / len(values) if values else 0.0
        package_rows.append(row)
    expected_package_count = len(chain.get("packages", [])) if isinstance(chain.get("packages"), list) else 0
    if len(package_rows) != expected_package_count:
        errors.append(f"not_all_crsi_packages_evaluated:{len(package_rows)}!={expected_package_count}")

    budget_equivalence: Dict[str, Any] = {}
    all_budget_equal = True
    for env_id, records in by_environment.items():
        ordered = sorted(records, key=lambda item: int(item["package_index"]))
        equal_limits = equal_usage_limits(ordered)
        resource_rows = [record.get("resource_requirements", {}) for record in ordered]
        model_policy_rows = [record.get("model_access_policy_id") for record in ordered]
        network_rows = [record.get("network_policy") for record in ordered]
        equal_resources = all(row == resource_rows[0] for row in resource_rows[1:]) if resource_rows else False
        equal_model_policy = len(set(model_policy_rows)) == 1 if model_policy_rows else False
        equal_network_policy = len(set(network_rows)) == 1 if network_rows else False
        equal = equal_limits and equal_resources and equal_model_policy and equal_network_policy
        budget_equivalence[env_id] = {
            "equal_declared_usage_limits": equal_limits,
            "equal_official_resource_requirements": equal_resources,
            "equal_model_access_policy": equal_model_policy,
            "equal_network_policy": equal_network_policy,
            "usage_limits": [record.get("usage_limits", {}) for record in ordered],
            "resource_requirements": resource_rows,
            "model_access_policy_ids": model_policy_rows,
            "network_policies": network_rows,
            "ok": equal,
        }
        all_budget_equal = all_budget_equal and equal
    if not all_budget_equal:
        errors.append("declared_usage_limits_not_equal_across_packages")

    epsilon = float(budgets["profiles"][RUN_MODE_TO_PROFILE[args.run_mode]].get("per_environment_regression_epsilon", 0.05))
    progression = progression_analysis(package_rows, selected_env_ids, epsilon)
    if not progression["ok"]:
        errors.append("external_score_progression_rule_failed")

    ledger = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "source_kind": "official_re_bench_scorer_exports",
        "run_mode": args.run_mode,
        "seed": args.seed,
        "environment_ids": selected_env_ids,
        "package_count": len(package_rows),
        "packages": package_rows,
        "budget_equivalence": budget_equivalence,
        "progression": progression,
        "raw_score_logs_required": True,
        "manual_or_declared_scores_accepted": False,
        "created_utc": utc_now(),
        "errors": errors,
        "ok": not errors and all(artifact.get("ok") for artifact in score_artifacts),
    }
    ledger["ledger_hash"] = self_hash(ledger, "ledger_hash")
    write_json(outdir / "crsi_re_bench_score_ledger.json", ledger)

    cert_summary = core_certificate_summary(chain)
    invariants = {
        "core_chain_valid": not validate_core_chain(chain),
        "rcp_rclm_certificates_preserved": cert_summary["all_preserved"],
        "official_environment_hashes_pinned": pin.get("ok") is True,
        "official_scorer_hashes_pinned": scorer.get("ok") is True,
        "no_leakage_no_oracle_no_manual_repair": not validate_no_leakage_manifest(no_leakage),
        "all_runs_executed_and_exported": execution.get("ok") is True,
        "all_scores_from_official_scorer_exports": all(artifact.get("source_kind") == "official_re_bench_scorer_export" and artifact.get("ok") for artifact in score_artifacts),
        "resource_budget_equivalent": all_budget_equal,
        "aggregate_score_nonregression": progression["aggregate_monotone_non_decreasing"],
        "strict_aggregate_improvement": progression["strict_aggregate_improvement"],
        "no_catastrophic_per_environment_regression": progression["no_catastrophic_per_environment_regression"],
        "successor_and_policy_ids_bound": all(row.get("core_successor_id") and row.get("benchmark_successor_id") and row.get("policy_hash") for row in package_rows),
    }
    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "run_mode": args.run_mode,
        "seed": args.seed,
        "input_paths": {key: safe_rel(path, repo) for key, path in inputs["paths"].items()},
        "input_hashes": {key: sha256_file(path) for key, path in inputs["paths"].items()},
        "run_plan_path": safe_rel(plan_path, repo),
        "run_plan_hash": plan["plan_hash"],
        "execution_report_path": safe_rel(execution_path, repo),
        "execution_report_hash": execution["execution_report_hash"],
        "score_ledger_path": safe_rel(outdir / "crsi_re_bench_score_ledger.json", repo),
        "score_ledger_hash": ledger["ledger_hash"],
        "core_certificate_summary": cert_summary,
        "bridge_invariants": invariants,
        "claim_boundary": {
            "independent_official_environment_run": ledger["ok"],
            "pilot_only": args.run_mode == "pilot",
            "full_seven_environment_single_seed_result": args.run_mode == "full480" and ledger["ok"],
            "full_seven_environment_multi_seed_result": False,
            "human_comparable_eight_hour_budget": args.run_mode == "full480" and ledger["ok"],
            "three_seed_requirement_satisfied": False,
            "official_metr_validated_result": False,
            "full_autonomous_rsi": False,
            "unbounded_horizon_empirical_proof": False,
        },
        "created_utc": utc_now(),
        "errors": errors,
        "ok": not errors and all(invariants.values()) and ledger["ok"],
    }
    sidecar["sidecar_hash"] = self_hash(sidecar, "sidecar_hash")
    write_json(outdir / "certificate_bridge_sidecar.json", sidecar)

    report = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "phase": "ingest",
        "score_artifact_count": len(score_artifacts),
        "ledger_path": safe_rel(outdir / "crsi_re_bench_score_ledger.json", repo),
        "sidecar_path": safe_rel(outdir / "certificate_bridge_sidecar.json", repo),
        "created_utc": utc_now(),
        "errors": errors,
        "ok": sidecar["ok"],
    }
    report["ingestion_report_hash"] = self_hash(report, "ingestion_report_hash")
    write_json(outdir / "ingestion_report.json", report)
    return report


def add_common_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--crsi-chain-summary", type=Path, default=None)
    parser.add_argument("--official-environment-hashes", type=Path, default=None)
    parser.add_argument("--pinned-scorer-manifest", type=Path, default=None)
    parser.add_argument("--agent-entrypoint-manifest", type=Path, default=None)
    parser.add_argument("--no-leakage-manifest", type=Path, default=None)
    parser.add_argument("--compute-budget-manifest", type=Path, default=DEFAULT_BUDGETS)
    parser.add_argument("--run-mode", choices=list(RUN_MODE_TO_PROFILE), default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--outdir", type=Path, required=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CRSI-RE-Bench v1 official-environment integration runner.")
    parser.add_argument("--phase", choices=["preflight", "plan", "execute", "ingest"], required=True)
    add_common_inputs(parser)
    parser.add_argument("--official-release-root", type=Path, default=None)
    parser.add_argument("--secrets-env", type=Path, default=None)
    parser.add_argument("--viv-executable", default="viv")
    parser.add_argument("--plan", type=Path, default=None)
    parser.add_argument("--execution-report", type=Path, default=None)
    parser.add_argument("--confirm-execute", default=None)
    parser.add_argument("--completion-command-template", default=None)
    parser.add_argument("--score-export-command-template", default=None)
    parser.add_argument("--trajectory-export-command-template", default=None)
    parser.add_argument("--submission-export-command-template", default=None)
    parser.add_argument("--usage-export-command-template", default=None)
    return parser.parse_args(argv)


def resolve_path(path: Path, repo: Path) -> Path:
    return path if path.is_absolute() else repo / path


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo = repo_root(args.repo_root)
    for field in [
        "crsi_chain_summary", "official_environment_hashes", "pinned_scorer_manifest",
        "agent_entrypoint_manifest", "no_leakage_manifest", "compute_budget_manifest", "outdir",
    ]:
        value = getattr(args, field)
        if value is not None:
            setattr(args, field, resolve_path(value, repo))
    if args.official_release_root is not None:
        args.official_release_root = resolve_path(args.official_release_root, repo)
    if args.secrets_env is not None:
        args.secrets_env = resolve_path(args.secrets_env, repo)
    if args.plan is not None:
        args.plan = resolve_path(args.plan, repo)
    if args.execution_report is not None:
        args.execution_report = resolve_path(args.execution_report, repo)
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    input_fields = [
        "crsi_chain_summary", "official_environment_hashes", "pinned_scorer_manifest",
        "agent_entrypoint_manifest", "no_leakage_manifest", "run_mode",
    ]
    if args.phase in {"preflight", "plan", "ingest"}:
        missing = [field for field in input_fields if getattr(args, field) is None]
        if missing:
            raise SystemExit(f"missing required arguments for {args.phase}: {missing}")
    if args.phase in {"preflight", "plan"} and args.official_release_root is None:
        raise SystemExit("--official-release-root is required for preflight/plan")
    if args.phase == "plan" and args.secrets_env is None:
        raise SystemExit("--secrets-env is required for plan")
    if args.phase == "execute":
        if args.no_leakage_manifest is None:
            raise SystemExit("--no-leakage-manifest is required for execute")
        if args.plan is None:
            args.plan = outdir / "run_plan.json"

    if args.phase == "preflight":
        result = preflight(args, repo, outdir)
    elif args.phase == "plan":
        result = build_plan(args, repo, outdir)
    elif args.phase == "execute":
        result = execute_plan(args, repo, outdir)
    else:
        result = ingest(args, repo, outdir)

    print(json.dumps({
        "phase": args.phase,
        "ok": result.get("ok") is True,
        "outdir": safe_rel(outdir, repo),
        "errors": result.get("errors", []),
    }, indent=2, sort_keys=True))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
