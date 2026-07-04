#!/usr/bin/env python3
"""Wrap official EvalPlus CLI/cache results with an RCP/RCLM certificate sidecar.

Use this only after running EvalPlus' own evaluator, e.g.
  evalplus.evaluate --dataset humaneval --samples samples.jsonl
and obtaining the corresponding *_eval_results.jsonl/json cache file.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

THIS = Path(__file__).resolve()
REPO = THIS.parents[2]
BRIDGE = REPO / "artifacts" / "evalplus_bridge"
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

from certified_evalplus_harness import certificate_bundle
from score_delta import parse_evalplus_result_file, compute_delta, dump_json, sha256_file
from leaderboard_sidecar_schema import EvalPlusClaimBoundary, validate_sidecar


def rel(repo: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo.resolve())).replace("\\", "/") if path.resolve().is_relative_to(repo.resolve()) else str(path.resolve()).replace("\\", "/")


def pick_score(path: Path) -> float:
    parsed = parse_evalplus_result_file(path)
    if parsed.get("plus_pass_at_1") is not None:
        return float(parsed["plus_pass_at_1"])
    if parsed.get("base_pass_at_1") is not None:
        return float(parsed["base_pass_at_1"])
    raise ValueError(f"Could not parse pass@1 score from {path}")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Wrap official EvalPlus result files with certificate sidecar")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--mode", choices=["rcp", "rclm"], default="rclm")
    p.add_argument("--N", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--baseline-result", type=Path, required=True)
    p.add_argument("--successor-result", type=Path, required=True)
    p.add_argument("--samples", type=Path, required=True)
    p.add_argument("--task-count", type=int, required=True)
    p.add_argument("--full-suite", action="store_true")
    p.add_argument("--leaderboard-submitted", action="store_true", help="Set only after an actual leaderboard submission/accepted report exists")
    p.add_argument("--outdir", type=Path, default=None)
    args = p.parse_args(argv)

    outdir = args.outdir or (REPO / "artifacts" / "evalplus_leaderboard" / "official_results")
    outdir.mkdir(parents=True, exist_ok=True)
    baseline_score = pick_score(args.baseline_result)
    successor_score = pick_score(args.successor_result)
    delta = compute_delta(baseline_score, successor_score)
    cert = certificate_bundle(REPO, args.mode, args.N, args.seed)
    cert_preserved = bool(cert.get("certificate_preserved"))
    claimable = cert_preserved and bool(delta["improved"])

    full_he = args.dataset == "humaneval" and args.full_suite
    full_mbpp = args.dataset == "mbpp" and args.full_suite
    boundary = EvalPlusClaimBoundary(
        evalplus_public_code_benchmark=True,
        docker_free_local_evalplus=False,
        official_evalplus_cli_result=True,
        evalplus_leaderboard_result=bool(args.leaderboard_submitted),
        full_humaneval_plus_suite=bool(full_he),
        full_mbpp_plus_suite=bool(full_mbpp),
        diagnostic_oracle=False,
        claimable_non_oracle_improvement=bool(claimable),
        certificate_preserved=cert_preserved,
    ).to_dict()

    sidecar = {
        "benchmark": f"EvalPlus-{args.dataset}-official-wrap",
        "benchmark_version": "EvalPlus official evaluator/cache artifact",
        "benchmark_kind": "official_evalplus_result_sidecar",
        "official_public_benchmark": True,
        "public_benchmark_dataset": True,
        "dataset": args.dataset,
        "dataset_scope": "full" if args.full_suite else f"{args.task_count}tasks",
        "task_count": args.task_count,
        "mode": args.mode,
        "N": args.N,
        "seed": args.seed,
        "baseline_score": delta["baseline_score"],
        "successor_score": delta["successor_score"],
        "delta": delta["delta"],
        "improved": delta["improved"],
        "certificate_preserved": cert_preserved,
        "accepted_updates": args.N,
        "all_pcs_checked": cert_preserved,
        "LECert_status": cert.get("LECert_status"),
        "checker_passed": bool(cert.get("checker_passed")),
        "closed_loop_ok": bool(cert.get("closed_loop_ok")),
        "score_artifact_paths": [rel(REPO, args.baseline_result), rel(REPO, args.successor_result), rel(REPO, args.samples), cert.get("learned_entry_summary_path")],
        "score_artifact_hashes": {
            rel(REPO, args.baseline_result): sha256_file(args.baseline_result),
            rel(REPO, args.successor_result): sha256_file(args.successor_result),
            rel(REPO, args.samples): sha256_file(args.samples),
        },
        "runlog_hash": sha256_file(args.successor_result),
        "certificate_hash": cert.get("learned_entry_summary_hash"),
        "diagnostic_oracle": False,
        "claimable_non_oracle_improvement": bool(claimable),
        "claim_boundary": boundary,
        "evaluation_backend": "official_evalplus_cli_cache_wrap",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ok": True,
    }
    errors = validate_sidecar(sidecar)
    sidecar["schema_errors"] = errors
    sidecar["schema_valid"] = not errors
    sidecar["ok"] = not errors
    out = outdir / f"{args.dataset}_official_evalplus_sidecar.json"
    dump_json(out, sidecar)
    print(json.dumps({"ok": sidecar["ok"], "sidecar": str(out), "delta": delta, "claim_boundary": boundary}, indent=2))
    return 0 if sidecar["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
