#!/usr/bin/env python3
"""B9-Bridge Phase 3: certificate-preserving local benchmark sidecar.

This harness wraps a controlled local benchmark with the M3-Min learned-entry
certificate boundary and the closed-loop generator artifacts.

It implements the executable sidecar shape:

    BenchmarkRun_B(M_0,...,M_N) ⇓ (Score_{B,0},...,Score_{B,N})
    while learned-entry FullPass, PCS checking, checker pass, and replay hashes
    are recorded in the sidecar.

Scope:
    - local controlled mini benchmark only;
    - certificate-preserving score delta for a finite controlled run;
    - not SWE-bench / RE-Bench / MLE-bench / Terminal-Bench / WebArena;
    - not arbitrary trained-system entry;
    - not full autonomous RSI.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from benchmark_sidecar_schema import classify_benchmark_sidecar, sidecar_claim_boundary, validate_sidecar
from local_mini_tasks import BENCHMARK_NAME, BENCHMARK_VERSION, evaluate_tasks, extract_ability_sets_from_artifact
from score_delta import load_json, score_delta, sha256_file, sha256_obj, summarize_sidecars, write_json


def find_repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "artifacts" / "learned_entry" / "learned_entry_audit.py").exists() and (path / "artifacts" / "common" / "closed_loop_reference_engine.py").exists():
            return path
    raise FileNotFoundError("Could not find repo root containing artifacts/learned_entry and artifacts/common closed-loop engine")


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
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def safe_rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def ensure_learned_entry_result(repo: Path, mode: str, N: int, seed: int, *, rerun: bool) -> Dict[str, Any]:
    case_dir = repo / "artifacts" / "learned_entry" / "results" / f"{mode}_N{N}_seed{seed}"
    summary_path = case_dir / "learned_entry_audit_summary.json"
    if rerun or not summary_path.exists():
        script = repo / "artifacts" / "learned_entry" / "learned_entry_audit.py"
        code, stdout, stderr = run_command([sys.executable, str(script), "--mode", mode, "--N", str(N), "--seed", str(seed)], repo)
        if code != 0:
            raise RuntimeError(f"learned_entry_audit failed for {mode}_N{N}_seed{seed}:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
        # The script writes the summary.  We parse stdout only as fallback.
        if not summary_path.exists():
            return extract_json_from_stdout(stdout)
    return load_json(summary_path)


def run_checker(repo: Path, mode: str, artifact_path: Path) -> Dict[str, Any]:
    checker = repo / "artifacts" / mode / "checker.py"
    code, stdout, stderr = run_command([sys.executable, str(checker), str(artifact_path)], repo)
    parsed: Dict[str, Any] = {}
    if stdout.strip():
        try:
            parsed = extract_json_from_stdout(stdout)
        except Exception:
            parsed = {"raw_stdout": stdout}
    parsed.update({"checker_exit_code_phase3": code, "checker_stderr_phase3": stderr})
    return parsed


def read_phase2_bundle(repo: Path, audit_summary: Mapping[str, Any]) -> Dict[str, Any]:
    paths = audit_summary.get("paths", {})
    generated_artifact = repo / paths.get("generated_artifact", "")
    accepted_trajectory = repo / paths.get("accepted_trajectory", "")
    rejected_candidates = repo / paths.get("rejected_candidates", "")
    closed_loop_runlog = repo / paths.get("closed_loop_runlog", "")
    hashes = repo / paths.get("hashes", "")
    case_dir = repo / paths.get("case_dir", "")
    lecert_path = case_dir / "lecert.json"
    learned_system_path = case_dir / "learned_system.json"

    required = [generated_artifact, accepted_trajectory, rejected_candidates, closed_loop_runlog, hashes, lecert_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing learned-entry/closed-loop paths: " + "; ".join(missing))

    return {
        "artifact_path": generated_artifact,
        "accepted_path": accepted_trajectory,
        "rejected_path": rejected_candidates,
        "closed_loop_runlog_path": closed_loop_runlog,
        "hashes_path": hashes,
        "lecert_path": lecert_path,
        "learned_system_path": learned_system_path,
        "artifact": load_json(generated_artifact),
        "accepted": load_json(accepted_trajectory),
        "rejected": load_json(rejected_candidates),
        "runlog": load_json(closed_loop_runlog),
        "hashes": load_json(hashes),
        "lecert": load_json(lecert_path),
        "learned_system": load_json(learned_system_path) if learned_system_path.exists() else {},
    }


def build_sidecar(repo: Path, mode: str, N: int, seed: int, benchmark: str, rerun_audit: bool, outdir: Path) -> Dict[str, Any]:
    if benchmark != BENCHMARK_NAME:
        raise ValueError(f"Only {BENCHMARK_NAME} is implemented in Phase 3A")

    audit_summary = ensure_learned_entry_result(repo, mode, N, seed, rerun=rerun_audit)
    try:
        bundle = read_phase2_bundle(repo, audit_summary)
    except FileNotFoundError:
        # A repository may contain an older Phase-2 summary without the full
        # closed-loop subdirectory.  In that case rerun the learned-entry audit
        # to regenerate the executable evidence bundle before building the
        # benchmark sidecar.
        audit_summary = ensure_learned_entry_result(repo, mode, N, seed, rerun=True)
        bundle = read_phase2_bundle(repo, audit_summary)
    checker_summary = run_checker(repo, mode, bundle["artifact_path"])

    ability_sets = extract_ability_sets_from_artifact(bundle["artifact"])
    baseline_eval = evaluate_tasks(ability_sets["baseline"])
    successor_eval = evaluate_tasks(ability_sets["successor"])
    delta_obj = score_delta(baseline_eval["score"], successor_eval["score"])

    lecert = bundle["lecert"]
    runlog = bundle["runlog"]
    accepted = bundle["accepted"]
    hashes = bundle["hashes"]

    all_pcs_checked = bool(
        audit_summary.get("checker_passed") is True
        and audit_summary.get("closed_loop_ok") is True
        and lecert.get("PCS") is True
        and lecert.get("Q_SV_A_nonpositive") is True
        and runlog.get("all_accepted_steps_checked") is True
    )
    certificate_preserved = bool(
        audit_summary.get("audit_status") == "FullPass"
        and audit_summary.get("ok") is True
        and checker_summary.get("ok") is True
        and all_pcs_checked
        and lecert.get("GoalId") is True
        and lecert.get("TrustRef") is True
        and lecert.get("RealCont") is True
        and lecert.get("SVTract") is True
    )

    sidecar: Dict[str, Any] = {
        "schema": "RCP/RCLM-B9-Bridge-Phase3-certificate-preserving-benchmark-sidecar-v0.1",
        "benchmark": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_scope": "controlled-local-mini-benchmark; not a public external AI-agent benchmark",
        "mode": mode,
        "N": N,
        "seed": seed,
        **delta_obj,
        "certificate_preserved": certificate_preserved,
        "accepted_updates": int(runlog.get("accepted_candidates", len(accepted))),
        "generated_candidates": int(runlog.get("generated_candidates", 0)),
        "rejected_candidates": int(runlog.get("rejected_candidates", 0)),
        "all_pcs_checked": all_pcs_checked,
        "checker_passed": checker_summary.get("ok") is True,
        "LECert_status": audit_summary.get("audit_status", "Fail"),
        "learned_entry_fullpass": audit_summary.get("audit_status") == "FullPass",
        "runlog_hash": sha256_file(bundle["closed_loop_runlog_path"]),
        "certificate_hash": str(lecert.get("certificate_hash") or sha256_obj(lecert)),
        "artifact_hash": sha256_file(bundle["artifact_path"]),
        "sidecar_created_utc": datetime.now(timezone.utc).isoformat(),
        "score_trace": {
            "M_0": baseline_eval["score"],
            f"M_{N}": successor_eval["score"],
        },
        "task_summary": {
            "baseline": {k: v for k, v in baseline_eval.items() if k != "task_results"},
            "successor": {k: v for k, v in successor_eval.items() if k != "task_results"},
        },
        "claim_boundary": sidecar_claim_boundary(local_benchmark=True),
        "paths": {
            "learned_entry_summary": safe_rel(repo / audit_summary.get("paths", {}).get("case_dir", "") / "learned_entry_audit_summary.json", repo),
            "lecert": safe_rel(bundle["lecert_path"], repo),
            "generated_artifact": safe_rel(bundle["artifact_path"], repo),
            "accepted_trajectory": safe_rel(bundle["accepted_path"], repo),
            "rejected_candidates": safe_rel(bundle["rejected_path"], repo),
            "closed_loop_runlog": safe_rel(bundle["closed_loop_runlog_path"], repo),
            "hashes": safe_rel(bundle["hashes_path"], repo),
        },
        "checker_summary": checker_summary,
    }
    # Set a preliminary finite-run success flag before schema validation because
    # the schema explicitly requires an ``ok`` boolean field.  Then refine it
    # after validation succeeds.
    sidecar["ok"] = bool(certificate_preserved and delta_obj["delta_positive"])
    schema_ok, schema_errors = validate_sidecar(sidecar)
    sidecar["schema_valid"] = schema_ok
    sidecar["schema_errors"] = schema_errors
    sidecar["ok"] = bool(schema_ok and certificate_preserved and delta_obj["delta_positive"])
    sidecar["benchmark_status"] = classify_benchmark_sidecar(sidecar)

    case_dir = outdir / f"{mode}_N{N}_seed{seed}_{BENCHMARK_NAME}"
    case_dir.mkdir(parents=True, exist_ok=True)
    write_json(case_dir / "benchmark_sidecar.json", sidecar)
    write_json(case_dir / "benchmark_scores.json", {"baseline": baseline_eval, "successor": successor_eval, "delta": delta_obj})
    write_json(case_dir / "local_task_results.json", {"baseline": baseline_eval["task_results"], "successor": successor_eval["task_results"]})
    write_json(case_dir / "certificate_bundle.json", {"audit_summary": audit_summary, "LECert": lecert, "checker_summary": checker_summary})
    write_json(case_dir / "benchmark_runlog.json", {
        "benchmark": BENCHMARK_NAME,
        "mode": mode,
        "N": N,
        "seed": seed,
        "sidecar_hash": sha256_obj(sidecar),
        "scores_hash": sha256_obj({"baseline": baseline_eval, "successor": successor_eval, "delta": delta_obj}),
        "certificate_preserved": certificate_preserved,
        "ok": sidecar["ok"],
    })
    write_json(case_dir / "hashes.json", {
        "benchmark_sidecar_sha256": sha256_file(case_dir / "benchmark_sidecar.json"),
        "benchmark_scores_sha256": sha256_file(case_dir / "benchmark_scores.json"),
        "local_task_results_sha256": sha256_file(case_dir / "local_task_results.json"),
        "certificate_bundle_sha256": sha256_file(case_dir / "certificate_bundle.json"),
        "benchmark_runlog_sha256": sha256_file(case_dir / "benchmark_runlog.json"),
    })
    return {"case_dir": case_dir, "sidecar": sidecar}


def write_csv(path: Path, sidecars: List[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "benchmark", "benchmark_version", "mode", "N", "seed", "baseline_score", "successor_score", "delta",
        "certificate_preserved", "accepted_updates", "generated_candidates", "rejected_candidates", "all_pcs_checked",
        "checker_passed", "LECert_status", "benchmark_status", "ok",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in sidecars:
            writer.writerow({field: row.get(field) for field in fields})


def parse_int_list(items: Optional[List[str]], default: List[int]) -> List[int]:
    if not items:
        return default
    out: List[int] = []
    for item in items:
        for part in str(item).replace(",", " ").split():
            out.append(int(part))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B9-Bridge Phase 3 certificate-preserving local benchmark sidecar.")
    parser.add_argument("--modes", nargs="+", default=["rclm"], choices=["rcp", "rclm"], help="Modes to benchmark")
    parser.add_argument("--N", nargs="+", default=None, help="Horizons; default 5")
    parser.add_argument("--seeds", nargs="+", default=None, help="Seeds; default 0")
    parser.add_argument("--benchmark", default=BENCHMARK_NAME, choices=[BENCHMARK_NAME])
    parser.add_argument("--outdir", default="artifacts/benchmark_bridge/results")
    parser.add_argument("--rerun-audit", action="store_true", help="Rerun learned-entry audit even if results exist")
    args = parser.parse_args()

    repo = find_repo_root()
    outdir = repo / args.outdir
    Ns = parse_int_list(args.N, [5])
    seeds = parse_int_list(args.seeds, [0])

    cases: List[Dict[str, Any]] = []
    for mode in args.modes:
        for N in Ns:
            for seed in seeds:
                print(f"[benchmark-bridge] running {mode}_N{N}_seed{seed}_{args.benchmark}", file=sys.stderr)
                result = build_sidecar(repo, mode, int(N), int(seed), args.benchmark, args.rerun_audit, outdir)
                cases.append(result["sidecar"])

    summary = summarize_sidecars(cases)
    summary.update({
        "suite_name": "B9-Bridge Phase 3: certificate-preserving local benchmark bridge",
        "benchmark": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "suite_scope": "Controlled local benchmark sidecar for certificate-preserving score deltas; not a public external benchmark.",
    })
    write_json(outdir / "certificate_preserving_benchmark_summary.json", summary)
    write_json(outdir / "certificate_preserving_benchmark_detailed.json", cases)
    write_csv(outdir / "certificate_preserving_benchmark_results.csv", cases)

    print(json.dumps({"ok": summary["all_cases_ok"], "outdir": str(outdir), "summary": summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
