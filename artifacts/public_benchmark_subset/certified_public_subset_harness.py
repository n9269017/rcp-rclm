#!/usr/bin/env python3
"""B9-Bridge Phase 4: certificate-preserving public benchmark subset adapter.

Default mode runs a controlled public-style local terminal subset and wraps the
run with the same sidecar needed for future public benchmark subset results.
It does not claim official public benchmark performance unless an external
score manifest is supplied.
"""
from __future__ import annotations
import argparse, csv, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path: sys.path.insert(0, str(THIS_DIR))

from public_subset_schema import classify_sidecar, phase4_claim_boundary, validate_public_subset_sidecar
from public_subset_tasks import BENCHMARK_KIND, BENCHMARK_NAME, BENCHMARK_VERSION, evaluate_tasks, extract_ability_sets_from_artifact
from phase4_utils import load_json, score_delta, sha256_file, sha256_obj, summarize, write_json


def find_repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "artifacts" / "learned_entry" / "learned_entry_audit.py").exists():
            return path
    raise FileNotFoundError("Could not find repository root containing artifacts/learned_entry/learned_entry_audit.py")


def run_command(cmd: Sequence[str], cwd: Path) -> Tuple[int, str, str]:
    p = subprocess.run(list(cmd), cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout, p.stderr


def extract_json_from_stdout(stdout: str) -> Dict[str, Any]:
    txt = stdout.strip()
    if not txt: return {}
    try: return json.loads(txt)
    except json.JSONDecodeError:
        s, e = txt.find("{"), txt.rfind("}")
        if s >= 0 and e > s: return json.loads(txt[s:e+1])
        raise


def safe_rel(path: Path, repo: Path) -> str:
    try: return str(path.resolve().relative_to(repo.resolve())).replace("\\", "/")
    except Exception: return str(path)


def ensure_learned_entry(repo: Path, mode: str, N: int, seed: int, rerun: bool) -> Dict[str, Any]:
    case = repo / "artifacts" / "learned_entry" / "results" / f"{mode}_N{N}_seed{seed}"
    summary = case / "learned_entry_audit_summary.json"
    if rerun or not summary.exists():
        script = repo / "artifacts" / "learned_entry" / "learned_entry_audit.py"
        code, out, err = run_command([sys.executable, str(script), "--mode", mode, "--N", str(N), "--seed", str(seed)], repo)
        if code != 0:
            raise RuntimeError(f"learned_entry_audit failed for {mode}_N{N}_seed{seed}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
        if not summary.exists():
            return extract_json_from_stdout(out)
    return load_json(summary)


def run_checker(repo: Path, mode: str, artifact: Path) -> Dict[str, Any]:
    checker = repo / "artifacts" / mode / "checker.py"
    code, out, err = run_command([sys.executable, str(checker), str(artifact)], repo)
    parsed: Dict[str, Any] = {}
    if out.strip():
        try: parsed = extract_json_from_stdout(out)
        except Exception: parsed = {"raw_stdout": out}
    parsed["checker_exit_code_phase4"] = code
    parsed["checker_stderr_phase4"] = err
    return parsed


def read_bundle(repo: Path, audit: Mapping[str, Any]) -> Dict[str, Any]:
    paths = audit.get("paths", {})
    case_dir = repo / str(paths.get("case_dir", ""))
    items = {
        "artifact_path": repo / str(paths.get("generated_artifact", "")),
        "accepted_path": repo / str(paths.get("accepted_trajectory", "")),
        "rejected_path": repo / str(paths.get("rejected_candidates", "")),
        "runlog_path": repo / str(paths.get("closed_loop_runlog", "")),
        "hashes_path": repo / str(paths.get("hashes", "")),
        "lecert_path": case_dir / "lecert.json",
    }
    missing = [str(p) for p in items.values() if isinstance(p, Path) and not p.exists()]
    if missing: raise FileNotFoundError("missing learned-entry bundle paths: " + "; ".join(missing))
    return {**items,
        "artifact": load_json(items["artifact_path"]),
        "accepted": load_json(items["accepted_path"]),
        "runlog": load_json(items["runlog_path"]),
        "lecert": load_json(items["lecert_path"]),
    }


def local_sidecar(repo: Path, mode: str, N: int, seed: int, rerun_audit: bool, outdir: Path) -> Dict[str, Any]:
    audit = ensure_learned_entry(repo, mode, N, seed, rerun_audit)
    try:
        bundle = read_bundle(repo, audit)
    except FileNotFoundError:
        audit = ensure_learned_entry(repo, mode, N, seed, True)
        bundle = read_bundle(repo, audit)
    checker = run_checker(repo, mode, bundle["artifact_path"])
    ability_sets = extract_ability_sets_from_artifact(bundle["artifact"])
    baseline = evaluate_tasks(ability_sets["baseline"])
    successor = evaluate_tasks(ability_sets["successor"])
    delta = score_delta(baseline["score"], successor["score"])
    lecert = bundle["lecert"]
    runlog = bundle["runlog"]
    all_pcs_checked = bool(audit.get("checker_passed") is True and audit.get("closed_loop_ok") is True and lecert.get("PCS") is True and lecert.get("Q_SV_A_nonpositive") is True and runlog.get("all_accepted_steps_checked") is True)
    certificate_preserved = bool(audit.get("audit_status") == "FullPass" and audit.get("ok") is True and checker.get("ok") is True and all_pcs_checked and lecert.get("GoalId") is True and lecert.get("TrustRef") is True and lecert.get("RealCont") is True and lecert.get("SVTract") is True)
    sidecar: Dict[str, Any] = {
        "schema": "RCP/RCLM-B9-Bridge-Phase4-public-benchmark-subset-sidecar-v0.1",
        "phase": "B9-Bridge Phase 4: public benchmark subset adapter",
        "benchmark": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_kind": BENCHMARK_KIND,
        "official_public_benchmark": False,
        "mode": mode,
        "N": N,
        "seed": seed,
        **delta,
        "certificate_preserved": certificate_preserved,
        "accepted_updates": int(runlog.get("accepted_candidates", len(bundle["accepted"]))),
        "generated_candidates": int(runlog.get("generated_candidates", 0)),
        "rejected_candidates": int(runlog.get("rejected_candidates", 0)),
        "all_pcs_checked": all_pcs_checked,
        "checker_passed": checker.get("ok") is True,
        "LECert_status": audit.get("audit_status", "Fail"),
        "learned_entry_fullpass": audit.get("audit_status") == "FullPass",
        "runlog_hash": sha256_file(bundle["runlog_path"]),
        "certificate_hash": str(lecert.get("certificate_hash") or sha256_obj(lecert)),
        "artifact_hash": sha256_file(bundle["artifact_path"]),
        "sidecar_created_utc": datetime.now(timezone.utc).isoformat(),
        "score_trace": {"M_0": baseline["score"], f"M_{N}": successor["score"]},
        "task_summary": {"baseline": {k:v for k,v in baseline.items() if k != "task_results"}, "successor": {k:v for k,v in successor.items() if k != "task_results"}},
        "claim_boundary": phase4_claim_boundary(official_public_benchmark=False, controlled_subset=True),
        "paths": {"lecert": safe_rel(bundle["lecert_path"], repo), "generated_artifact": safe_rel(bundle["artifact_path"], repo), "accepted_trajectory": safe_rel(bundle["accepted_path"], repo), "closed_loop_runlog": safe_rel(bundle["runlog_path"], repo), "hashes": safe_rel(bundle["hashes_path"], repo)},
        "checker_summary": checker,
        "public_benchmark_notes": ["Controlled public-style subset only; not an official SWE-bench/Terminal-Bench/RE-Bench/MLE-bench/WebArena run.", "Use external-manifest mode to wrap official subset scores after running official harnesses."],
    }
    sidecar["ok"] = bool(certificate_preserved and delta["delta_positive"])
    schema_ok, schema_errors = validate_public_subset_sidecar(sidecar)
    sidecar["schema_valid"] = schema_ok
    sidecar["schema_errors"] = schema_errors
    sidecar["ok"] = bool(schema_ok and sidecar["ok"])
    sidecar["benchmark_status"] = classify_sidecar(sidecar)
    case = outdir / f"{mode}_N{N}_seed{seed}_{BENCHMARK_NAME}"
    case.mkdir(parents=True, exist_ok=True)
    write_json(case / "benchmark_sidecar.json", sidecar)
    write_json(case / "benchmark_scores.json", {"baseline": baseline, "successor": successor, "delta": delta})
    write_json(case / "public_subset_task_results.json", {"baseline": baseline["task_results"], "successor": successor["task_results"]})
    write_json(case / "certificate_bundle.json", {"audit_summary": audit, "LECert": lecert, "checker_summary": checker})
    write_json(case / "benchmark_runlog.json", {"phase": sidecar["phase"], "benchmark": BENCHMARK_NAME, "mode": mode, "N": N, "seed": seed, "ok": sidecar["ok"]})
    write_json(case / "hashes.json", {p.name: sha256_file(p) for p in case.iterdir() if p.is_file() and p.name != "hashes.json"})
    return sidecar


def external_manifest_sidecar(repo: Path, manifest_path: Path, outdir: Path) -> Dict[str, Any]:
    m = load_json(manifest_path)
    required = ["benchmark", "benchmark_version", "benchmark_kind", "mode", "N", "seed", "baseline_score", "successor_score", "certificate_bundle_path"]
    missing = [k for k in required if k not in m]
    if missing: raise ValueError("external manifest missing: " + ", ".join(missing))
    cert_path = repo / m["certificate_bundle_path"]
    cert = load_json(cert_path)
    lecert = cert.get("LECert", {})
    audit = cert.get("audit_summary", {})
    checker = cert.get("checker_summary", {})
    delta = score_delta(m["baseline_score"], m["successor_score"])
    all_pcs_checked = bool(lecert.get("PCS") is True and lecert.get("Q_SV_A_nonpositive") is True and audit.get("checker_passed") is True)
    certificate_preserved = bool(audit.get("audit_status") == "FullPass" and checker.get("ok") is True and all_pcs_checked)
    sidecar = {"schema": "RCP/RCLM-B9-Bridge-Phase4-public-benchmark-subset-sidecar-v0.1", "phase": "B9-Bridge Phase 4: external public-subset score sidecar", "benchmark": m["benchmark"], "benchmark_version": m["benchmark_version"], "benchmark_kind": m["benchmark_kind"], "official_public_benchmark": bool(m.get("official_public_benchmark", False)), "mode": m["mode"], "N": int(m["N"]), "seed": int(m["seed"]), **delta, "certificate_preserved": certificate_preserved, "accepted_updates": int(m.get("accepted_updates", 0)), "all_pcs_checked": all_pcs_checked, "checker_passed": checker.get("ok") is True, "LECert_status": audit.get("audit_status", "Fail"), "runlog_hash": str(m.get("runlog_hash", "")), "certificate_hash": sha256_file(cert_path), "claim_boundary": phase4_claim_boundary(official_public_benchmark=bool(m.get("official_public_benchmark", False)), controlled_subset=False), "score_artifact_paths": m.get("score_artifact_paths", []), "task_ids": m.get("task_ids", []), "sidecar_created_utc": datetime.now(timezone.utc).isoformat(), "ok": False}
    sidecar["ok"] = bool(sidecar["certificate_preserved"] and sidecar["delta_positive"])
    schema_ok, schema_errors = validate_public_subset_sidecar(sidecar)
    sidecar["schema_valid"] = schema_ok; sidecar["schema_errors"] = schema_errors; sidecar["ok"] = bool(schema_ok and sidecar["ok"]); sidecar["benchmark_status"] = classify_sidecar(sidecar)
    case = outdir / f"external_{sidecar['benchmark']}_{sidecar['mode']}_N{sidecar['N']}_seed{sidecar['seed']}"; case.mkdir(parents=True, exist_ok=True)
    write_json(case / "benchmark_sidecar.json", sidecar); write_json(case / "external_manifest_used.json", m); write_json(case / "hashes.json", {p.name: sha256_file(p) for p in case.iterdir() if p.is_file() and p.name != "hashes.json"})
    return sidecar


def parse_ints(text: str) -> List[int]: return [int(x.strip()) for x in str(text).split(",") if x.strip()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=["rcp", "rclm"], choices=["rcp", "rclm"])
    ap.add_argument("--N", default="5")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--benchmark", default="local-terminal-public-subset-v0", choices=["local-terminal-public-subset-v0", "external-manifest"])
    ap.add_argument("--external-manifest")
    ap.add_argument("--rerun-audit", action="store_true")
    ap.add_argument("--outdir", default="artifacts/public_benchmark_subset/results")
    args = ap.parse_args(argv)
    repo = find_repo_root(); outdir = (repo / args.outdir).resolve(); outdir.mkdir(parents=True, exist_ok=True)
    sidecars: List[Dict[str, Any]] = []
    if args.benchmark == "external-manifest":
        if not args.external_manifest: raise SystemExit("--external-manifest is required")
        sidecars.append(external_manifest_sidecar(repo, Path(args.external_manifest), outdir))
    else:
        for mode in args.modes:
            for N in parse_ints(args.N):
                for seed in parse_ints(args.seeds):
                    print(f"[public-subset] running {mode}_N{N}_seed{seed}_local-terminal-public-subset-v0", flush=True)
                    sidecars.append(local_sidecar(repo, mode, N, seed, args.rerun_audit, outdir))
    summary = summarize(sidecars)
    write_json(outdir / "public_subset_benchmark_summary.json", summary)
    write_json(outdir / "public_subset_benchmark_detailed.json", sidecars)
    with (outdir / "public_subset_benchmark_results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["benchmark", "benchmark_version", "benchmark_kind", "mode", "N", "seed", "baseline_score", "successor_score", "delta", "delta_positive", "certificate_preserved", "LECert_status", "checker_passed", "ok", "benchmark_status"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for s in sidecars: w.writerow({k: s.get(k) for k in fields})
    print(json.dumps({"ok": bool(summary.get("all_cases_ok")), "outdir": str(outdir), "summary": summary}, indent=2, sort_keys=True))
    return 0 if summary.get("all_cases_ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
