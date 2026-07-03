#!/usr/bin/env python3
"""Internal closed-loop RSI benchmark harness for the RCP/RCLM artifacts.

B9-Bridge / Phase 1 scope:
    - runs the closed-loop certified successor generator over several horizons,
      seeds, and modes;
    - verifies every generated artifact with the existing checker.py scripts;
    - records internal RSI certification metrics such as accepted/rejected
      candidates, residual nonpositivity, strict ability expansion, zero goal
      drift, singleton reality containment, and checker pass/fail.

Non-scope:
    - not a SWE-bench/RE-Bench/MLE-bench/Terminal-Bench/WebArena result;
    - not a learned-entry FullPass;
    - not empirical deployment validation;
    - not full autonomous RSI.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Allow running from repo root without installing this as a package.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from benchmark_schema import BenchmarkCase, BenchmarkConfig, DEFAULT_HORIZONS, DEFAULT_MODES, DEFAULT_SEEDS, validate_horizon, validate_mode
from score_utils import compute_case_score, load_json, safe_div, sha256_obj, summarize_cases, write_csv, write_json


def find_repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "artifacts" / "common" / "closed_loop_reference_engine.py").exists():
            return path
    raise FileNotFoundError("Could not find repo root containing artifacts/common/closed_loop_reference_engine.py")


def run_command(cmd: Sequence[str], cwd: Path) -> Tuple[int, str, str]:
    proc = subprocess.run(list(cmd), cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def extract_json_from_stdout(stdout: str) -> Dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some tools may print banner text before JSON. Parse from first { to last }.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def run_one_case(repo: Path, case: BenchmarkCase, outdir: Path, keep_run_dirs: bool = True) -> Dict[str, Any]:
    run_dir = outdir / "runs" / case.case_id
    engine = repo / "artifacts" / "common" / "closed_loop_reference_engine.py"
    checker = repo / "artifacts" / case.mode / "checker.py"

    validate_horizon(case.N)
    if not engine.exists():
        raise FileNotFoundError(engine)
    if not checker.exists():
        raise FileNotFoundError(checker)

    engine_cmd = [sys.executable, str(engine), "--mode", case.mode, "--N", str(case.N), "--seed", str(case.seed), "--run-dir", str(run_dir)]
    engine_code, engine_out, engine_err = run_command(engine_cmd, repo)
    engine_summary = extract_json_from_stdout(engine_out) if engine_out.strip() else {}

    artifact_path = run_dir / "generated_artifact.json"
    checker_cmd = [sys.executable, str(checker), str(artifact_path)]
    checker_code, checker_out, checker_err = run_command(checker_cmd, repo)
    checker_summary = extract_json_from_stdout(checker_out) if checker_out.strip() else {}

    runlog_path = run_dir / "closed_loop_runlog.json"
    runlog = load_json(runlog_path) if runlog_path.exists() else {}
    rejected_path = run_dir / "rejected_candidates.json"
    accepted_path = run_dir / "accepted_trajectory.json"
    rejected = load_json(rejected_path) if rejected_path.exists() else []
    accepted = load_json(accepted_path) if accepted_path.exists() else []

    generated_candidates = int(runlog.get("generated_candidates", 0))
    accepted_candidates = int(runlog.get("accepted_candidates", len(accepted)))
    rejected_candidates = int(runlog.get("rejected_candidates", len(rejected)))

    zero_goal = float(runlog.get("goal_identity_drift", 1.0)) == 0.0
    checker_passed = (checker_code == 0 and checker_summary.get("ok") is True)
    closed_loop_ok = (engine_code == 0 and runlog.get("ok", engine_summary.get("ok")) is True)
    has_rejection_evidence = rejected_candidates > 0 and len(rejected) > 0

    result: Dict[str, Any] = {
        **case.to_dict(),
        "run_dir": str(run_dir.relative_to(repo) if run_dir.is_relative_to(repo) else run_dir),
        "generated_artifact": str(artifact_path.relative_to(repo) if artifact_path.is_relative_to(repo) else artifact_path),
        "accepted_trajectory": str(accepted_path.relative_to(repo) if accepted_path.is_relative_to(repo) else accepted_path),
        "rejected_candidates_path": str(rejected_path.relative_to(repo) if rejected_path.is_relative_to(repo) else rejected_path),
        "closed_loop_runlog": str(runlog_path.relative_to(repo) if runlog_path.is_relative_to(repo) else runlog_path),
        "engine_exit_code": engine_code,
        "checker_exit_code": checker_code,
        "engine_stderr": engine_err.strip(),
        "checker_stderr": checker_err.strip(),
        "engine_stdout_sha256": sha256_obj(engine_out),
        "checker_stdout_sha256": sha256_obj(checker_out),
        "closed_loop_ok": closed_loop_ok,
        "checker_passed": checker_passed,
        "generated_candidates": generated_candidates,
        "accepted_candidates": accepted_candidates,
        "rejected_candidates": rejected_candidates,
        "acceptance_rate": safe_div(accepted_candidates, generated_candidates),
        "all_accepted_steps_checked": bool(runlog.get("all_accepted_steps_checked", False)),
        "all_residuals_nonpositive": bool(runlog.get("all_residuals_nonpositive", False)),
        "strict_ability_expansion_each_step": bool(runlog.get("strict_ability_expansion_each_step", False)),
        "non_loss_recovery_preserved_each_step": bool(runlog.get("non_loss_recovery_preserved_each_step", False)),
        "zero_goal_identity_drift": zero_goal,
        "goal_identity_drift": float(runlog.get("goal_identity_drift", 1.0)),
        "singleton_reality_containment": bool(runlog.get("singleton_reality_containment", False)),
        "has_rejection_evidence": has_rejection_evidence,
        "final_dimension": int(runlog.get("final_dimension", checker_summary.get("final_dimension", 0))),
        "artifact_hash": runlog.get("artifact_hash", checker_summary.get("artifact_hash")),
        "trajectory_hash": runlog.get("trajectory_hash"),
        "checker_summary": checker_summary,
        "engine_summary": engine_summary,
    }

    result["internal_certification_score"] = compute_case_score(result)
    result["ok"] = all([
        result["closed_loop_ok"],
        result["checker_passed"],
        result["all_accepted_steps_checked"],
        result["all_residuals_nonpositive"],
        result["strict_ability_expansion_each_step"],
        result["non_loss_recovery_preserved_each_step"],
        result["zero_goal_identity_drift"],
        result["singleton_reality_containment"],
        result["has_rejection_evidence"],
        generated_candidates == case.expected_generated_candidates,
        accepted_candidates == case.expected_accepted_candidates,
        rejected_candidates == case.expected_rejected_candidates,
    ])

    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the internal closed-loop RCP/RCLM RSI benchmark suite.")
    parser.add_argument("--modes", nargs="+", default=DEFAULT_MODES, help="Modes to run: rcp rclm")
    parser.add_argument("--N", dest="horizons", nargs="+", type=int, default=DEFAULT_HORIZONS, help="Horizons to run, default: 2 3 5 10")
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS, help="Seeds to run, default: 0 1 2")
    parser.add_argument("--outdir", type=Path, default=Path("artifacts") / "benchmarks" / "results")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--allow-failures", action="store_true", help="Return exit code 0 even if some cases fail.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    repo = find_repo_root(args.repo_root)
    modes = [validate_mode(m) for m in args.modes]
    for N in args.horizons:
        validate_horizon(N)
    config = BenchmarkConfig(
        modes=modes,
        horizons=list(args.horizons),
        seeds=list(args.seeds),
        outdir=str(args.outdir),
        allow_failures=bool(args.allow_failures),
    )
    outdir = (repo / args.outdir).resolve() if not args.outdir.is_absolute() else args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for case in config.cases():
        print(f"[benchmark] running {case.case_id}", file=sys.stderr)
        results.append(run_one_case(repo, case, outdir))

    summary = summarize_cases(results)
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "modes": modes,
            "horizons": list(args.horizons),
            "seeds": list(args.seeds),
            "outdir": str(args.outdir),
        },
        "claim_boundary": {
            "internal_closed_loop_rsi_benchmark": True,
            "b9_learned_entry_fullpass": False,
            "external_public_ai_agent_benchmark": False,
            "full_autonomous_rsi": False,
            "empirical_deployment_validation": False,
        },
        "summary": summary,
        "results": results,
    }
    report["report_sha256"] = sha256_obj({k: v for k, v in report.items() if k != "report_sha256"})

    write_json(outdir / "internal_closed_loop_benchmark_detailed.json", report)
    write_json(outdir / "internal_closed_loop_benchmark_summary.json", summary)
    write_csv(outdir / "internal_closed_loop_benchmark_results.csv", results)

    print(json.dumps({"ok": summary["all_cases_ok"], "summary": summary, "outdir": str(outdir)}, indent=2, sort_keys=True))
    if not summary["all_cases_ok"] and not args.allow_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
