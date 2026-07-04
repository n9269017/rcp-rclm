#!/usr/bin/env python3
"""Phase 4C: EvalPlus/HumanEval+ subset/full-suite leaderboard-prep sidecar.

This script scales the existing Phase 4B-alt micro sidecar from one task to a
chosen subset or full EvalPlus dataset.  It is still careful about claims:
  * direct backend results are Docker-free public-data sidecars, not leaderboard.
  * leaderboard claims require official EvalPlus evaluation/submission artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

THIS = Path(__file__).resolve()
REPO = THIS.parents[2]
BRIDGE = REPO / "artifacts" / "evalplus_bridge"
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

from certified_evalplus_harness import direct_eval_samples, certificate_bundle
from evalplus_micro_dataset import make_baseline_samples, load_evalplus_problems
from score_delta import compute_delta, dump_json, sha256_file
from leaderboard_sidecar_schema import EvalPlusClaimBoundary, validate_sidecar


def read_task_list(path: Path) -> List[str]:
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def choose_task_ids(dataset: str, *, full: bool, task_ids: Optional[List[str]], task_list: Optional[Path], limit: int) -> List[str]:
    problems = load_evalplus_problems(dataset)
    if full:
        ids = list(problems.keys())
    elif task_list:
        ids = read_task_list(task_list)
    elif task_ids:
        ids = task_ids
    else:
        ids = ["HumanEval/0"] if dataset == "humaneval" else list(problems.keys())[:1]
    if limit and limit > 0:
        ids = ids[:limit]
    missing = [tid for tid in ids if tid not in problems]
    if missing:
        raise KeyError(f"Task IDs not found in EvalPlus {dataset}: {missing}")
    return ids


def rel(repo: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo.resolve())).replace("\\", "/")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="RCP/RCLM certified EvalPlus suite sidecar")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--mode", choices=["rcp", "rclm"], default="rclm")
    p.add_argument("--N", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--task-ids", nargs="+", default=None)
    p.add_argument("--task-list", type=Path, default=None)
    p.add_argument("--full", action="store_true", help="Run all tasks in the selected EvalPlus dataset")
    p.add_argument("--limit", type=int, default=0, help="Optional first-N task limit")
    p.add_argument("--successor-samples", type=Path, required=True)
    p.add_argument("--baseline-samples", type=Path, default=None)
    p.add_argument("--mini", action="store_true", help="Bound plus tests for quicker non-leaderboard pilots")
    p.add_argument("--base-only", action="store_true")
    p.add_argument("--per-test-timeout", type=float, default=2.0)
    p.add_argument("--max-plus-tests", type=int, default=50)
    p.add_argument("--diagnostic-oracle", action="store_true")
    p.add_argument("--outdir", type=Path, default=None)
    args = p.parse_args(argv)

    repo = REPO
    task_ids = choose_task_ids(args.dataset, full=args.full, task_ids=args.task_ids, task_list=args.task_list, limit=args.limit)
    task_count = len(task_ids)
    scope = "full" if args.full and args.limit == 0 else f"{task_count}tasks"
    case_name = f"{args.mode}_N{args.N}_seed{args.seed}_{args.dataset}_{scope}"
    out_root = args.outdir or (repo / "artifacts" / "evalplus_leaderboard" / "results")
    case_dir = out_root / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    task_list_path = case_dir / "task_ids.txt"
    task_list_path.write_text("\n".join(task_ids) + "\n", encoding="utf-8")

    baseline_samples = args.baseline_samples or (case_dir / "baseline_samples.jsonl")
    if args.baseline_samples:
        shutil.copy2(args.baseline_samples, baseline_samples)
    else:
        make_baseline_samples(task_ids, baseline_samples)

    successor_samples = case_dir / "successor_samples.jsonl"
    shutil.copy2(args.successor_samples, successor_samples)

    baseline_results_path = case_dir / "baseline_direct_eval_results.json"
    successor_results_path = case_dir / "successor_direct_eval_results.json"

    baseline = direct_eval_samples(
        dataset=args.dataset,
        samples_path=baseline_samples,
        task_ids=task_ids,
        out_path=baseline_results_path,
        mini=args.mini,
        base_only=args.base_only,
        per_test_timeout=args.per_test_timeout,
        max_plus_tests=args.max_plus_tests,
    )
    successor = direct_eval_samples(
        dataset=args.dataset,
        samples_path=successor_samples,
        task_ids=task_ids,
        out_path=successor_results_path,
        mini=args.mini,
        base_only=args.base_only,
        per_test_timeout=args.per_test_timeout,
        max_plus_tests=args.max_plus_tests,
    )
    delta_info = compute_delta(float(baseline["score"]), float(successor["score"]))
    cert = certificate_bundle(repo, args.mode, args.N, args.seed)
    cert_preserved = bool(cert.get("certificate_preserved"))
    full_he = args.dataset == "humaneval" and task_count == len(load_evalplus_problems("humaneval")) and args.full
    full_mbpp = args.dataset == "mbpp" and task_count == len(load_evalplus_problems("mbpp")) and args.full
    claimable = (not args.diagnostic_oracle) and cert_preserved and bool(delta_info["improved"])

    boundary = EvalPlusClaimBoundary(
        evalplus_public_code_benchmark=True,
        docker_free_local_evalplus=True,
        official_evalplus_cli_result=False,
        evalplus_leaderboard_result=False,
        full_humaneval_plus_suite=bool(full_he),
        full_mbpp_plus_suite=bool(full_mbpp),
        diagnostic_oracle=bool(args.diagnostic_oracle),
        claimable_non_oracle_improvement=bool(claimable),
        certificate_preserved=cert_preserved,
    ).to_dict()

    artifacts = [baseline_samples, successor_samples, task_list_path, baseline_results_path, successor_results_path]
    sidecar = {
        "benchmark": f"EvalPlus-{args.dataset}-suite-prep",
        "benchmark_version": "EvalPlus public task data; direct Docker-free suite evaluator; not leaderboard official",
        "benchmark_kind": "docker_free_evalplus_suite_sidecar",
        "official_public_benchmark": False,
        "public_benchmark_dataset": True,
        "dataset": args.dataset,
        "dataset_scope": scope,
        "task_count": task_count,
        "task_ids_path": rel(repo, task_list_path),
        "mode": args.mode,
        "N": args.N,
        "seed": args.seed,
        "baseline_score": delta_info["baseline_score"],
        "successor_score": delta_info["successor_score"],
        "delta": delta_info["delta"],
        "improved": delta_info["improved"],
        "certificate_preserved": cert_preserved,
        "accepted_updates": args.N,
        "all_pcs_checked": cert_preserved,
        "LECert_status": cert.get("LECert_status"),
        "checker_passed": bool(cert.get("checker_passed")),
        "closed_loop_ok": bool(cert.get("closed_loop_ok")),
        "score_artifact_paths": [rel(repo, p) for p in artifacts] + [cert.get("learned_entry_summary_path")],
        "score_artifact_hashes": {rel(repo, p): sha256_file(p) for p in artifacts if p.exists()},
        "runlog_hash": sha256_file(successor_results_path),
        "certificate_hash": cert.get("learned_entry_summary_hash"),
        "diagnostic_oracle": bool(args.diagnostic_oracle),
        "claimable_non_oracle_improvement": bool(claimable),
        "claim_boundary": boundary,
        "evaluation_backend": "direct_evalplus_suite",
        "mini": bool(args.mini),
        "base_only": bool(args.base_only),
        "max_plus_tests": args.max_plus_tests if args.mini else "all",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ok": True,
    }
    schema_errors = validate_sidecar(sidecar)
    sidecar["schema_errors"] = schema_errors
    sidecar["schema_valid"] = not schema_errors
    sidecar["ok"] = not schema_errors

    sidecar_path = case_dir / "leaderboard_prep_sidecar.json"
    scores_path = case_dir / "leaderboard_prep_scores.json"
    dump_json(sidecar_path, sidecar)
    dump_json(scores_path, {"baseline": baseline, "successor": successor, "delta": delta_info})

    summary = {
        "suite_name": "Phase 4C: EvalPlus leaderboard-prep suite sidecar",
        "suite_scope": "Scales certificate-preserving EvalPlus sidecars beyond one micro task. Direct backend is not an official leaderboard score.",
        "ok": bool(sidecar["ok"]),
        "case_dir": rel(repo, case_dir),
        "task_count": task_count,
        "baseline_score": sidecar["baseline_score"],
        "successor_score": sidecar["successor_score"],
        "delta": sidecar["delta"],
        "improved": sidecar["improved"],
        "certificate_preserved": sidecar["certificate_preserved"],
        "claimable_non_oracle_improvement": sidecar["claimable_non_oracle_improvement"],
        "official_leaderboard_result": False,
    }
    dump_json(out_root / "evalplus_leaderboard_prep_summary.json", summary)

    csv_path = out_root / "evalplus_leaderboard_prep_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary.keys()))
        w.writeheader()
        w.writerow(summary)

    print(json.dumps({"ok": sidecar["ok"], "summary": summary, "sidecar": str(sidecar_path)}, indent=2))
    return 0 if sidecar["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
