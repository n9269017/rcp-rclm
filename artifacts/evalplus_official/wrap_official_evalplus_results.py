#!/usr/bin/env python3
"""Wrap official EvalPlus CLI artifacts with an RCP/RCLM certificate sidecar."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

THIS = Path(__file__).resolve()
REPO = THIS.parents[2]
THIS_DIR = THIS.parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from parse_evalplus_outputs import parse_runlog, existing_artifacts_from_runlog, sha256_file
from official_evalplus_sidecar_schema import validate_official_sidecar


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def score_from_runlog(path: Optional[Path], score_kind: str) -> Optional[float]:
    if not path:
        return None
    obj = parse_runlog(path)
    scores = obj.get("parsed_scores", {})
    if score_kind == "base":
        val = scores.get("base_pass_at_1")
    elif score_kind == "plus":
        val = scores.get("plus_pass_at_1")
    else:
        val = scores.get("plus_pass_at_1")
        if val is None:
            val = scores.get("base_pass_at_1")
    return None if val is None else float(val)


def certificate_from_direct_sidecar(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {
            "certificate_preserved": False,
            "source": None,
            "reason": "no direct sidecar supplied",
        }
    obj = load_json(path)
    preserved = bool(obj.get("certificate_preserved")) and bool(obj.get("checker_passed")) and bool(obj.get("closed_loop_ok"))
    return {
        "certificate_preserved": preserved,
        "source": rel(path),
        "source_hash": sha256_file(path),
        "LECert_status": obj.get("LECert_status"),
        "checker_passed": bool(obj.get("checker_passed")),
        "closed_loop_ok": bool(obj.get("closed_loop_ok")),
        "accepted_updates": obj.get("accepted_updates"),
        "all_pcs_checked": obj.get("all_pcs_checked"),
        "direct_sidecar_claim_boundary": obj.get("claim_boundary", {}),
    }


def add_artifact(paths: list[Path], p: Optional[Path]) -> None:
    if p and p.exists():
        paths.append(p)


def main() -> int:
    p = argparse.ArgumentParser(description="Wrap official EvalPlus CLI artifacts with RCP/RCLM certificate sidecar")
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--mode", choices=["rcp", "rclm"], default="rclm")
    p.add_argument("--N", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--label", required=True)
    p.add_argument("--score-kind", choices=["base", "plus", "auto"], default="auto")
    p.add_argument("--baseline-run", type=Path, default=None)
    p.add_argument("--successor-run", type=Path, default=None)
    p.add_argument("--baseline-score", type=float, default=None)
    p.add_argument("--successor-score", type=float, default=None)
    p.add_argument("--direct-sidecar", type=Path, default=None)
    p.add_argument("--task-count", type=int, default=164)
    p.add_argument("--full-suite", action="store_true")
    p.add_argument("--mini", action="store_true", help="Mark wrapped official CLI artifact as using --mini")
    p.add_argument("--leaderboard-eligible-candidate", action="store_true", help="Marks local artifact as leaderboard-style candidate, not external listing")
    p.add_argument("--outdir", type=Path, default=REPO / "artifacts" / "evalplus_official" / "results")
    args = p.parse_args()

    baseline_score = args.baseline_score
    successor_score = args.successor_score

    if baseline_score is None:
        baseline_score = score_from_runlog(args.baseline_run, args.score_kind)
    if successor_score is None:
        successor_score = score_from_runlog(args.successor_run, args.score_kind)

    if baseline_score is None or successor_score is None:
        raise SystemExit(
            "Could not parse baseline/successor scores from runlogs. "
            "Pass --baseline-score and --successor-score after inspecting official EvalPlus output."
        )

    delta = float(successor_score) - float(baseline_score)
    improved = delta > 0
    cert = certificate_from_direct_sidecar(args.direct_sidecar)

    artifact_paths: list[Path] = []
    for rp in [args.baseline_run, args.successor_run, args.direct_sidecar]:
        add_artifact(artifact_paths, rp)

    for rp in [args.baseline_run, args.successor_run]:
        if rp and rp.exists():
            runlog = load_json(rp)
            for ap in existing_artifacts_from_runlog(runlog):
                add_artifact(artifact_paths, Path(ap))

    # de-duplicate
    seen: set[str] = set()
    artifacts: list[Path] = []
    for pth in artifact_paths:
        key = str(pth.resolve()) if pth.exists() else str(pth)
        if key not in seen and pth.exists():
            seen.add(key)
            artifacts.append(pth)

    artifact_hashes = {rel(pth): sha256_file(pth) for pth in artifacts}

    # Leaderboard listing is an external social/process fact, so this wrapper never sets it true.
    leaderboard_result = False
    leaderboard_style_candidate = bool(
        args.leaderboard_eligible_candidate and args.full_suite and not args.mini and args.score_kind in {"plus", "auto"}
    )

    sidecar: Dict[str, Any] = {
        "benchmark": f"EvalPlus-{args.dataset}-official-cli",
        "benchmark_version": "EvalPlus official CLI artifact; see official_evalplus_runlog command and stdout",
        "benchmark_kind": "official_evalplus_cli_artifact_sidecar",
        "official_public_benchmark": True,
        "official_evalplus_cli_result": True,
        "evalplus_leaderboard_result": leaderboard_result,
        "leaderboard_style_candidate": leaderboard_style_candidate,
        "public_benchmark_dataset": True,
        "dataset": args.dataset,
        "task_count": int(args.task_count),
        "full_suite": bool(args.full_suite),
        "mini": bool(args.mini),
        "score_kind": args.score_kind,
        "mode": args.mode,
        "N": args.N,
        "seed": args.seed,
        "baseline_score": float(baseline_score),
        "successor_score": float(successor_score),
        "delta": delta,
        "improved": improved,
        "certificate_preserved": bool(cert.get("certificate_preserved")),
        "certificate_bundle": cert,
        "official_artifact_paths": [rel(pth) for pth in artifacts],
        "official_artifact_hashes": artifact_hashes,
        "baseline_runlog": rel(args.baseline_run) if args.baseline_run else None,
        "successor_runlog": rel(args.successor_run) if args.successor_run else None,
        "direct_sidecar": rel(args.direct_sidecar) if args.direct_sidecar else None,
        "claimable_official_cli_improvement": bool(improved and cert.get("certificate_preserved")),
        "claim_boundary": {
            "evalplus_public_code_benchmark": True,
            "official_evalplus_cli_result": True,
            "evalplus_leaderboard_result": leaderboard_result,
            "leaderboard_style_candidate": leaderboard_style_candidate,
            "full_humaneval_plus_suite": bool(args.dataset == "humaneval" and args.full_suite and args.score_kind in {"plus", "auto"} and not args.mini),
            "canonical_base_humaneval": bool(args.dataset == "humaneval" and args.score_kind == "base"),
            "diagnostic_oracle": False,
            "claimable_non_oracle_improvement": bool(improved and cert.get("certificate_preserved")),
            "certificate_preserved": bool(cert.get("certificate_preserved")),
            "swe_bench_result": False,
            "terminal_bench_result": False,
            "re_bench_result": False,
            "mle_bench_result": False,
            "webarena_result": False,
            "arbitrary_trained_system_entry": False,
            "full_autonomous_rsi": False,
        },
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }

    errors = validate_official_sidecar(sidecar)
    sidecar["schema_errors"] = errors
    sidecar["schema_valid"] = not errors
    sidecar["ok"] = not errors

    case = args.outdir / args.label
    case.mkdir(parents=True, exist_ok=True)
    out = case / "official_evalplus_certificate_sidecar.json"
    out.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_path = args.outdir / "official_evalplus_summary.json"
    existing = []
    if summary_path.exists():
        try:
            existing = json.loads(summary_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    row = {
        "label": args.label,
        "dataset": args.dataset,
        "task_count": args.task_count,
        "score_kind": args.score_kind,
        "baseline_score": baseline_score,
        "successor_score": successor_score,
        "delta": delta,
        "improved": improved,
        "certificate_preserved": bool(cert.get("certificate_preserved")),
        "official_evalplus_cli_result": True,
        "evalplus_leaderboard_result": False,
        "leaderboard_style_candidate": leaderboard_style_candidate,
        "ok": sidecar["ok"],
        "sidecar": rel(out),
    }
    existing = [r for r in existing if r.get("label") != args.label]
    existing.append(row)
    summary_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "ok": sidecar["ok"],
        "sidecar": str(out),
        "baseline_score": baseline_score,
        "successor_score": successor_score,
        "delta": delta,
        "certificate_preserved": cert.get("certificate_preserved"),
        "claimable_official_cli_improvement": sidecar["claimable_official_cli_improvement"],
        "leaderboard_style_candidate": leaderboard_style_candidate,
        "evalplus_leaderboard_result": False,
        "schema_errors": errors,
    }, indent=2, ensure_ascii=False))
    return 0 if sidecar["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
