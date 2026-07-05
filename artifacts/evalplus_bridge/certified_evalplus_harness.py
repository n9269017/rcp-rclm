#!/usr/bin/env python3
"""Phase 4B-alt: Docker-free EvalPlus/HumanEval+ certificate-preserving sidecar.

This revision avoids the hanging EvalPlus CLI subprocess path on Windows by
using a direct, deterministic micro-evaluator over EvalPlus public task data.
It is intended for Docker-free micro-subset validation and certificate-sidecar
integration, not for claiming an official EvalPlus leaderboard score.

Diagnostic oracle mode uses canonical solutions and is pipeline validation only.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

THIS = Path(__file__).resolve()
THIS_DIR = THIS.parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from evalplus_sidecar_schema import ClaimBoundary, validate_sidecar
from evalplus_micro_dataset import (
    make_baseline_samples,
    make_oracle_successor_samples,
    make_override_dataset,
    load_evalplus_problems,
)
from score_delta import compute_delta, dump_json, load_json, sha256_file


def repo_root_from_script() -> Path:
    return THIS.parents[2]


def ensure_learned_entry(repo: Path, mode: str, N: int, seed: int) -> Path:
    summary = repo / "artifacts" / "learned_entry" / "results" / f"{mode}_N{N}_seed{seed}" / "learned_entry_audit_summary.json"
    if summary.exists():
        return summary
    script = repo / "artifacts" / "learned_entry" / "learned_entry_audit.py"
    if not script.exists():
        raise FileNotFoundError(f"learned_entry_audit.py not found: {script}")
    cmd = [sys.executable, str(script), "--mode", mode, "--N", str(N), "--seed", str(seed)]
    proc = subprocess.run(cmd, cwd=str(repo), text=True, encoding="utf-8", errors="replace", capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"learned-entry audit failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    if not summary.exists():
        raise FileNotFoundError(f"learned-entry audit finished but summary not found: {summary}")
    return summary


def certificate_bundle(repo: Path, mode: str, N: int, seed: int) -> Dict[str, Any]:
    summary_path = ensure_learned_entry(repo, mode, N, seed)
    summary = load_json(summary_path)
    lecert = summary.get("LECert", {})
    certificate_preserved = (
        summary.get("audit_status") == "FullPass"
        and bool(summary.get("checker_passed"))
        and bool(summary.get("closed_loop_ok"))
        and all(bool(v) for v in lecert.values())
    )
    return {
        "learned_entry_summary_path": str(summary_path.relative_to(repo)).replace("\\", "/"),
        "learned_entry_summary_hash": sha256_file(summary_path),
        "LECert": lecert,
        "LECert_status": summary.get("audit_status"),
        "checker_passed": bool(summary.get("checker_passed")),
        "closed_loop_ok": bool(summary.get("closed_loop_ok")),
        "certificate_preserved": bool(certificate_preserved),
        "component_summary": summary.get("component_summary", {}),
        "claim_boundary": summary.get("claim_boundary", {}),
    }


def copy_if_external(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    return dst


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


RUNNER = """
import json, math, pickle, sys, traceback


def call(fn, inp):
    if isinstance(inp, dict):
        return fn(**inp)
    if isinstance(inp, (list, tuple)):
        return fn(*inp)
    return fn(inp)


def safe_repr(x):
    try:
        return repr(x)
    except ValueError as e:
        if isinstance(x, int):
            return f"<int bit_length={x.bit_length()}>"
        return f"<repr failed: {type(e).__name__}>"

def humaneval32_semantic_check(got, inp):
    # HumanEval/32 asks for any root x such that poly(xs, x) = 0.
    # Exact equality against the canonical solution's floating output is too
    # strict for this task, because many valid numerical solvers return a
    # different approximation to the same root.  Use the public semantic root
    # predicate: finite real x and |poly(xs, x)| < 1e-4.
    if not isinstance(got, (int, float)) or not math.isfinite(float(got)):
        return {
            'ok': False,
            'semantic_predicate': 'HumanEval/32 root residual < 1e-4',
            'reason': 'returned value is not a finite real number',
            'got_repr': safe_repr(got),
        }

    if isinstance(inp, (list, tuple)) and len(inp) == 1 and isinstance(inp[0], (list, tuple)):
        xs = list(inp[0])
    elif isinstance(inp, (list, tuple)):
        xs = list(inp)
    else:
        return {
            'ok': False,
            'semantic_predicate': 'HumanEval/32 root residual < 1e-4',
            'reason': 'input is not a coefficient list or singleton coefficient-list argument',
            'input_repr': repr(inp)[:500],
            'got_repr': safe_repr(got),
        }

    residual = abs(sum(coeff * math.pow(float(got), i) for i, coeff in enumerate(xs)))
    ok = residual < 1e-4
    return {
        'ok': ok,
        'semantic_predicate': 'HumanEval/32 root residual < 1e-4',
        'got_repr': safe_repr(got),
        'residual': residual,
        'residual_bound': 1e-4,
    }


payload = pickle.loads(sys.stdin.buffer.read())
solution = payload['solution']
canonical = payload['canonical']
entry_point = payload['entry_point']
inp = payload['input']
task_id = payload.get('task_id')
try:
    ns_s = {}
    exec(solution, ns_s)
    got = call(ns_s[entry_point], inp)

    if task_id == 'HumanEval/32' and entry_point == 'find_zero':
        result = humaneval32_semantic_check(got, inp)
        print(json.dumps(result))
    else:
        ns_c = {}
        exec(canonical, ns_c)
        expected = call(ns_c[entry_point], inp)
        ok = (got == expected)
        def safe_repr(x):
            try:
                return repr(x)
            except ValueError as e:
                if isinstance(x, int):
                    return f"<int bit_length={x.bit_length()}>"
                return f"<repr failed: {type(e).__name__}>"
        
        print(json.dumps({'ok': ok, 'got_repr': safe_repr(got), 'expected_repr': safe_repr(expected)}))
except BaseException as e:
    print(json.dumps({'ok': False, 'error': repr(e), 'traceback': traceback.format_exc()[-2000:]}))
    sys.exit(0)
"""


def run_one_test(solution: str, canonical: str, entry_point: str, inp: Any, timeout: float, task_id: Optional[str] = None) -> Dict[str, Any]:
    payload = pickle.dumps({"solution": solution, "canonical": canonical, "entry_point": entry_point, "input": inp, "task_id": task_id})
    try:
        proc = subprocess.run([sys.executable, "-c", RUNNER], input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "timeout": True, "input_repr": repr(inp)[:500]}
    out = proc.stdout.decode("utf-8", errors="replace").strip().splitlines()
    if not out:
        return {"ok": False, "empty_output": True, "stderr": proc.stderr.decode("utf-8", errors="replace")[-1000:]}
    try:
        result = json.loads(out[-1])
    except Exception:
        return {"ok": False, "parse_error": True, "stdout": "\n".join(out)[-1000:]}
    result["input_repr"] = repr(inp)[:500]
    return result


def sample_solution_for_task(samples: List[Dict[str, Any]], task_id: str, prompt: str) -> Optional[str]:
    for row in samples:
        if row.get("task_id") != task_id:
            continue
        if "solution" in row and row["solution"] is not None:
            return str(row["solution"])
        if "completion" in row and row["completion"] is not None:
            return prompt + str(row["completion"])
    return None


def direct_eval_samples(*, dataset: str, samples_path: Path, task_ids: List[str], out_path: Path, mini: bool, base_only: bool, per_test_timeout: float, max_plus_tests: int) -> Dict[str, Any]:
    problems = load_evalplus_problems(dataset)
    samples = read_jsonl(samples_path)
    task_results = []
    passed = 0
    total = 0
    for task_id in task_ids:
        if task_id not in problems:
            raise KeyError(f"Task {task_id!r} not found in EvalPlus dataset {dataset!r}")
        problem = problems[task_id]
        prompt = problem.get("prompt", "")
        entry_point = problem.get("entry_point")
        canonical = prompt + problem.get("canonical_solution", "")
        solution = sample_solution_for_task(samples, task_id, prompt)
        if solution is None:
            task_results.append({"task_id": task_id, "passed": False, "reason": "missing sample"})
            total += 1
            continue
        base_inputs = list(problem.get("base_input", []) or [])
        plus_inputs = [] if base_only else list(problem.get("plus_input", []) or [])
        if mini and max_plus_tests > 0:
            plus_inputs = plus_inputs[:max_plus_tests]
        all_inputs = [("base", x) for x in base_inputs] + [("plus", x) for x in plus_inputs]
        task_ok = True
        test_details = []
        for kind, inp in all_inputs:
            r = run_one_test(solution, canonical, entry_point, inp, per_test_timeout, task_id=task_id)
            r["kind"] = kind
            test_details.append(r)
            if not r.get("ok"):
                task_ok = False
                break
        passed += int(task_ok)
        total += 1
        task_results.append({
            "task_id": task_id,
            "entry_point": entry_point,
            "passed": task_ok,
            "num_base_inputs": len(base_inputs),
            "num_plus_inputs_used": len(plus_inputs),
            "tests_run_until_first_failure": len(test_details),
            "first_failure": next((d for d in test_details if not d.get("ok")), None),
        })
    score = passed / total if total else 0.0
    obj = {
        "benchmark_backend": "direct_evalplus_micro",
        "dataset": dataset,
        "task_ids": task_ids,
        "samples_path": str(samples_path),
        "mini": mini,
        "base_only": base_only,
        "per_test_timeout": per_test_timeout,
        "max_plus_tests": max_plus_tests,
        "passed_tasks": passed,
        "total_tasks": total,
        "score": score,
        "task_results": task_results,
    }
    dump_json(out_path, obj)
    return obj


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="RCP/RCLM EvalPlus certificate-preserving benchmark sidecar")
    p.add_argument("--mode", choices=["rcp", "rclm"], default="rclm")
    p.add_argument("--N", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    p.add_argument("--task-ids", nargs="+", default=["HumanEval/0"])
    p.add_argument("--mini", action="store_true", help="Use a bounded micro subset of plus tests")
    p.add_argument("--base-only", action="store_true", help="Run only base tests")
    p.add_argument("--diagnostic-oracle", action="store_true", help="Use canonical solutions for successor diagnostic; not claimable")
    p.add_argument("--baseline-samples", type=Path, default=None)
    p.add_argument("--successor-samples", type=Path, default=None)
    p.add_argument("--outdir", type=Path, default=None)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--no-run", action="store_true", help="Prepare samples/dataset only; do not evaluate")
    p.add_argument("--per-test-timeout", type=float, default=2.0)
    p.add_argument("--max-plus-tests", type=int, default=50)
    args = p.parse_args(argv)

    repo = args.repo_root.resolve() if args.repo_root else repo_root_from_script()
    out_root = args.outdir.resolve() if args.outdir else repo / "artifacts" / "evalplus_bridge" / "results"
    dataset_label = "HumanEval+" if args.dataset == "humaneval" else "MBPP+"
    scope = "micro"
    task_slug = "_".join(t.replace("/", "_") for t in args.task_ids)
    case = out_root / f"{args.mode}_N{args.N}_seed{args.seed}_{args.dataset}_{scope}_{task_slug}"
    case.mkdir(parents=True, exist_ok=True)

    override_name = "HumanEvalPlus_micro.jsonl.gz" if args.dataset == "humaneval" else "MbppPlus_micro.jsonl.gz"
    override_path = case / override_name
    make_override_dataset(args.dataset, args.task_ids, override_path)

    baseline_samples = case / "baseline_samples.jsonl"
    if args.baseline_samples:
        copy_if_external(args.baseline_samples, baseline_samples)
    else:
        make_baseline_samples(args.task_ids, baseline_samples)

    successor_samples = case / "successor_samples.jsonl"
    if args.successor_samples:
        copy_if_external(args.successor_samples, successor_samples)
        diagnostic_oracle = False
    elif args.diagnostic_oracle:
        make_oracle_successor_samples(args.dataset, args.task_ids, successor_samples)
        diagnostic_oracle = True
    else:
        raise SystemExit("Provide --successor-samples for a real non-oracle run, or use --diagnostic-oracle for pipeline validation.")

    baseline_run: Dict[str, Any] = {"returncode": None, "backend": "direct_evalplus_micro"}
    successor_run: Dict[str, Any] = {"returncode": None, "backend": "direct_evalplus_micro"}
    if args.no_run:
        baseline_score = 0.0
        successor_score = 0.0
    else:
        bres = direct_eval_samples(dataset=args.dataset, samples_path=baseline_samples, task_ids=args.task_ids, out_path=case / "baseline_direct_eval_results.json", mini=args.mini, base_only=args.base_only, per_test_timeout=args.per_test_timeout, max_plus_tests=args.max_plus_tests)
        sres = direct_eval_samples(dataset=args.dataset, samples_path=successor_samples, task_ids=args.task_ids, out_path=case / "successor_direct_eval_results.json", mini=args.mini, base_only=args.base_only, per_test_timeout=args.per_test_timeout, max_plus_tests=args.max_plus_tests)
        baseline_score = float(bres["score"])
        successor_score = float(sres["score"])
        baseline_run.update({"returncode": 0, "result_file": str(case / "baseline_direct_eval_results.json"), "score": baseline_score})
        successor_run.update({"returncode": 0, "result_file": str(case / "successor_direct_eval_results.json"), "score": successor_score})

    delta_obj = compute_delta(baseline_score, successor_score)
    cert = certificate_bundle(repo, args.mode, args.N, args.seed)
    score_artifacts = [baseline_samples, successor_samples, override_path]
    if not args.no_run:
        score_artifacts += [case / "baseline_direct_eval_results.json", case / "successor_direct_eval_results.json"]
    hashes: Dict[str, str] = {}
    for path in score_artifacts:
        if path.exists():
            key = str(path.relative_to(repo)).replace("\\", "/") if path.resolve().is_relative_to(repo.resolve()) else str(path)
            hashes[key] = sha256_file(path)
    cert_bundle_path = case / "certificate_bundle.json"
    dump_json(cert_bundle_path, cert)
    hashes[str(cert_bundle_path.relative_to(repo)).replace("\\", "/")] = sha256_file(cert_bundle_path)
    runlog = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "suite_name": "Phase 4B-alt: Docker-free EvalPlus/HumanEval+ certificate-preserving benchmark sidecar",
        "mode": args.mode,
        "N": args.N,
        "seed": args.seed,
        "dataset": args.dataset,
        "task_ids": args.task_ids,
        "mini": args.mini,
        "base_only": args.base_only,
        "diagnostic_oracle": diagnostic_oracle,
        "no_run": args.no_run,
        "evaluation_backend": "direct_evalplus_micro",
        "per_test_timeout": args.per_test_timeout,
        "max_plus_tests": args.max_plus_tests,
        "baseline_run": baseline_run,
        "successor_run": successor_run,
    }
    runlog_path = case / "evalplus_runlog.json"
    dump_json(runlog_path, runlog)
    hashes[str(runlog_path.relative_to(repo)).replace("\\", "/")] = sha256_file(runlog_path)
    claimable = bool(delta_obj["improved"] and cert["certificate_preserved"] and not diagnostic_oracle and not args.no_run)
    claim_boundary = ClaimBoundary(evalplus_public_code_benchmark=True, docker_free_local_evalplus=True, diagnostic_oracle=diagnostic_oracle, claimable_non_oracle_improvement=claimable, certificate_preserved=bool(cert["certificate_preserved"])).to_dict()
    sidecar = {
        "benchmark": f"EvalPlus-{dataset_label}-{scope}",
        "benchmark_version": "EvalPlus public task data; direct Docker-free micro-evaluator; not leaderboard official",
        "benchmark_kind": "docker_free_public_code_benchmark_sidecar",
        "official_public_benchmark": False,
        "public_benchmark_dataset": True,
        "dataset": args.dataset,
        "dataset_scope": scope,
        "task_ids": args.task_ids,
        "mode": args.mode,
        "N": args.N,
        "seed": args.seed,
        **delta_obj,
        "certificate_preserved": bool(cert["certificate_preserved"]),
        "accepted_updates": args.N,
        "all_pcs_checked": bool(cert["certificate_preserved"]),
        "LECert_status": cert.get("LECert_status"),
        "checker_passed": bool(cert.get("checker_passed")),
        "closed_loop_ok": bool(cert.get("closed_loop_ok")),
        "score_artifact_paths": list(hashes.keys()),
        "score_artifact_hashes": hashes,
        "runlog_hash": sha256_file(runlog_path),
        "certificate_hash": sha256_file(cert_bundle_path),
        "diagnostic_oracle": diagnostic_oracle,
        "claimable_non_oracle_improvement": claimable,
        "claim_boundary": claim_boundary,
        "evaluation_backend": "direct_evalplus_micro",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ok": (not args.no_run) and bool(cert["certificate_preserved"]) and baseline_run.get("returncode") == 0 and successor_run.get("returncode") == 0,
    }
    errors = validate_sidecar(sidecar)
    sidecar["schema_errors"] = errors
    sidecar["schema_valid"] = not errors
    sidecar["ok"] = bool(sidecar["ok"] and sidecar["schema_valid"])
    dump_json(case / "benchmark_scores.json", {"baseline": {"samples": str(baseline_samples), "score": baseline_score}, "successor": {"samples": str(successor_samples), "score": successor_score}, "delta": delta_obj})
    dump_json(case / "hashes.json", hashes)
    dump_json(case / "benchmark_sidecar.json", sidecar)
    summary_path = out_root / "evalplus_benchmark_summary.json"
    detailed_path = out_root / "evalplus_benchmark_detailed.json"
    existing: List[Dict[str, Any]] = []
    if detailed_path.exists():
        try:
            existing = json.loads(detailed_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    case_key = str(case.relative_to(repo)).replace("\\", "/")
    existing = [x for x in existing if x.get("case_dir") != case_key]
    row = {"case_dir": case_key, "benchmark": sidecar["benchmark"], "dataset": args.dataset, "task_ids": args.task_ids, "mode": args.mode, "N": args.N, "seed": args.seed, "baseline_score": baseline_score, "successor_score": successor_score, "delta": delta_obj["delta"], "improved": delta_obj["improved"], "certificate_preserved": sidecar["certificate_preserved"], "diagnostic_oracle": diagnostic_oracle, "claimable_non_oracle_improvement": claimable, "evaluation_backend": "direct_evalplus_micro", "ok": sidecar["ok"]}
    existing.append(row)
    total = len(existing)
    ok_cases = sum(1 for x in existing if x["ok"])
    summary = {"suite_name": "Phase 4B-alt: Docker-free EvalPlus/HumanEval+ certificate-preserving benchmark sidecar", "suite_scope": "Public HumanEval+/EvalPlus-data micro sidecar. Direct backend is Docker-free and local; not an official leaderboard score.", "total_cases": total, "ok_cases": ok_cases, "pass_rate": ok_cases / total if total else 0.0, "improved_cases": sum(1 for x in existing if x["improved"]), "certificate_preserved_cases": sum(1 for x in existing if x["certificate_preserved"]), "claimable_non_oracle_improvement_cases": sum(1 for x in existing if x["claimable_non_oracle_improvement"]), "diagnostic_oracle_cases": sum(1 for x in existing if x["diagnostic_oracle"]), "mean_delta": sum(float(x["delta"]) for x in existing) / total if total else 0.0, "all_cases_ok": total > 0 and ok_cases == total}
    dump_json(summary_path, summary)
    dump_json(detailed_path, existing)
    print(json.dumps({"ok": sidecar["ok"], "case_dir": str(case), "sidecar": str(case / "benchmark_sidecar.json"), "summary": summary, "claim_boundary": claim_boundary}, indent=2, ensure_ascii=False))
    return 0 if sidecar["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
