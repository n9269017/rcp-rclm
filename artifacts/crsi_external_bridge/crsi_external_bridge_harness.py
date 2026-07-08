#!/usr/bin/env python3
"""CRSI-RE/METR Bridge harness.

This adapter binds an external AI-R&D benchmark score ledger to a recorded
CRSI-Core chain. It verifies that the external ledger preserves the chain's
RCP/RCLM certificates, protected non-loss invariants, hash chain, and no-leakage
conditions. A built-in smoke fixture is available for adapter validation only;
it is explicitly not an official RE-Bench/METR result.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from external_bridge_schema import (
    BRIDGE_INVARIANT_KEYS,
    SCHEMA_VERSION,
    SUITE_NAME,
    chain_successor_ids,
    core_certificates_preserved,
    core_hash_chain_valid,
    core_invariants_preserved,
    load_json,
    make_claim_boundary,
    no_leakage,
    normalize_score_entries,
    safe_rel,
    score_ids_match_chain,
    score_monotonicity,
    sha256_file,
    sha256_obj,
    validate_bridge_sidecar,
    validate_score_ledger,
    validate_task_manifest,
    write_json,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "artifacts" / "crsi_core" / "reproduce_crsi_core.py").exists():
            return path
    raise FileNotFoundError("Could not find repo root containing artifacts/crsi_core/reproduce_crsi_core.py")


def run_command(cmd: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(list(cmd), cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def extract_json(stdout: str) -> Dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def run_crsi_reproduction(repo: Path, chain_summary: Path, outdir: Path) -> Dict[str, Any]:
    checker = repo / "artifacts" / "crsi_core" / "reproduce_crsi_core.py"
    report_path = outdir / "crsi_chain_reproduction_report.json"
    cmd = [sys.executable, str(checker), str(chain_summary), "--out", str(report_path)]
    code, stdout, stderr = run_command(cmd, repo)
    obj = extract_json(stdout) if stdout.strip() else {}
    return {"exit_code": code, "stdout": stdout, "stderr": stderr, "summary": obj, "report_path": report_path}


def make_smoke_fixture(chain: Mapping[str, Any], outdir: Path, benchmark_id: str) -> tuple[Path, Path]:
    packages = chain.get("packages", []) if isinstance(chain.get("packages"), list) else []
    tasks = [
        {"task_id": "bridge-smoke/research-engineering-0", "description": "Synthetic adapter smoke task; not an external benchmark."},
        {"task_id": "bridge-smoke/research-engineering-1", "description": "Synthetic adapter smoke task; not an external benchmark."},
    ]
    task_manifest = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": benchmark_id,
        "benchmark_kind": "synthetic_bridge_smoke_fixture",
        "task_count": len(tasks),
        "tasks": tasks,
        "benchmark_answers_in_prompt": False,
        "hidden_tests_exposed": False,
        "private_solution_material_used": False,
        "diagnostic_oracle": False,
        "manual_repair_inside_chain": False,
        "human_patch_inside_chain": False,
        "created_utc": now(),
    }
    scores = []
    for package in packages:
        score = float(package.get("core_score", {}).get("certified_ability_count", len(scores)))
        scores.append({
            "package_index": int(package.get("package_index", len(scores))),
            "successor_id": package.get("successor_id"),
            "score": score,
            "score_units": "synthetic_smoke_score",
            "note": "Adapter smoke score derived from recorded CRSI package metadata; not an external benchmark score.",
        })
    score_ledger = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": benchmark_id,
        "benchmark_kind": "synthetic_bridge_smoke_fixture",
        "scores": scores,
        "benchmark_answers_in_prompt": False,
        "hidden_tests_exposed": False,
        "private_solution_material_used": False,
        "diagnostic_oracle": False,
        "manual_repair_inside_chain": False,
        "human_patch_inside_chain": False,
        "created_utc": now(),
    }
    task_path = outdir / "smoke_task_manifest.json"
    score_path = outdir / "smoke_external_score_ledger.json"
    write_json(task_path, task_manifest)
    write_json(score_path, score_ledger)
    return task_path, score_path


def build_bridge(
    *,
    repo: Path,
    chain_summary_path: Path,
    task_manifest_path: Optional[Path],
    score_ledger_path: Optional[Path],
    outdir: Path,
    benchmark_id: str,
    benchmark_kind: str,
    official_re_bench: bool,
    official_metr: bool,
    public_benchmark: bool,
    adapter_smoke: bool,
    allow_nonregression: bool,
    scorer_artifact: Optional[Path],
) -> Dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    chain = load_json(chain_summary_path)
    if adapter_smoke:
        task_manifest_path, score_ledger_path = make_smoke_fixture(chain, outdir, benchmark_id)
    if task_manifest_path is None or score_ledger_path is None:
        raise ValueError("Provide --task-manifest and --score-ledger, or use --make-smoke-fixture.")

    task_manifest = load_json(task_manifest_path)
    score_ledger = load_json(score_ledger_path)
    task_errors = validate_task_manifest(task_manifest)
    score_errors = validate_score_ledger(score_ledger)
    reproduction = run_crsi_reproduction(repo, chain_summary_path, outdir)

    successor_ids = chain_successor_ids(chain)
    entries = normalize_score_entries(score_ledger)
    monotonicity = score_monotonicity(entries)
    improved_ok = bool(monotonicity.get("strictly_improved")) or (allow_nonregression and bool(monotonicity.get("monotone_non_decreasing")))
    scorer_hash = sha256_file(scorer_artifact) if scorer_artifact and scorer_artifact.exists() else None

    invariants = {
        "crsi_chain_ok": chain.get("ok") is True,
        "crsi_chain_schema_valid": chain.get("schema_valid") is True,
        "core_certificates_preserved": core_certificates_preserved(chain),
        "core_non_loss_invariants_preserved": core_invariants_preserved(chain),
        "core_hash_chain_valid": core_hash_chain_valid(chain),
        "task_manifest_hash_logged": bool(sha256_file(task_manifest_path)),
        "external_score_ledger_hash_logged": bool(sha256_file(score_ledger_path)),
        "scorer_artifact_hash_logged_or_declared_absent": scorer_hash is not None or scorer_artifact is None,
        "no_benchmark_leakage": no_leakage(task_manifest, score_ledger),
        "no_oracle_access": no_leakage(task_manifest, score_ledger),
        "no_manual_repair": no_leakage(task_manifest, score_ledger),
        "successor_ids_match_chain": score_ids_match_chain(entries, successor_ids),
        "external_scores_monotone_non_decreasing": bool(monotonicity.get("monotone_non_decreasing")),
        "external_score_improved_or_policy_allows_nonregression": improved_ok,
    }
    claim_boundary = make_claim_boundary(
        official_re_bench=official_re_bench,
        official_metr=official_metr,
        public_benchmark=public_benchmark,
        adapter_smoke=adapter_smoke,
    )

    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "benchmark_id": benchmark_id,
        "benchmark_kind": benchmark_kind if not adapter_smoke else "synthetic_bridge_smoke_fixture",
        "crsi_chain_id": chain.get("chain_id"),
        "crsi_chain_summary_path": safe_rel(chain_summary_path, repo),
        "crsi_chain_summary_hash": sha256_file(chain_summary_path),
        "crsi_chain_reproduction": {
            "ok": reproduction["exit_code"] == 0 and reproduction.get("summary", {}).get("ok") is True,
            "exit_code": reproduction["exit_code"],
            "report_path": safe_rel(reproduction["report_path"], repo),
        },
        "task_manifest_path": safe_rel(task_manifest_path, repo),
        "task_manifest_hash": sha256_file(task_manifest_path),
        "external_score_ledger_path": safe_rel(score_ledger_path, repo),
        "external_score_ledger_hash": sha256_file(score_ledger_path),
        "scorer_artifact_path": safe_rel(scorer_artifact, repo) if scorer_artifact else None,
        "scorer_artifact_hash": scorer_hash,
        "external_score_summary": monotonicity,
        "external_score_entries": entries,
        "bridge_invariants": invariants,
        "task_manifest_schema_errors": task_errors,
        "score_ledger_schema_errors": score_errors,
        "claim_boundary": claim_boundary,
        "created_utc": now(),
    }
    sidecar["ok"] = (
        not task_errors
        and not score_errors
        and reproduction["exit_code"] == 0
        and reproduction.get("summary", {}).get("ok") is True
        and all(invariants.get(key) is True for key in BRIDGE_INVARIANT_KEYS)
    )
    sidecar["schema_errors"] = validate_bridge_sidecar(sidecar)
    sidecar["schema_valid"] = not sidecar["schema_errors"]
    sidecar["ok"] = bool(sidecar["ok"] and sidecar["schema_valid"])
    sidecar["sidecar_hash"] = sha256_obj({k: v for k, v in sidecar.items() if k != "sidecar_hash"})

    sidecar_path = outdir / "crsi_external_bridge_sidecar.json"
    summary_path = outdir / "crsi_external_bridge_summary.json"
    write_json(sidecar_path, sidecar)
    write_json(summary_path, {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "ok": sidecar["ok"],
        "benchmark_id": benchmark_id,
        "benchmark_kind": sidecar["benchmark_kind"],
        "adapter_smoke_test_only": claim_boundary["adapter_smoke_test_only"],
        "official_re_bench_result": claim_boundary["official_re_bench_result"],
        "external_public_benchmark_result": claim_boundary["external_public_benchmark_result"],
        "crsi_chain_id": chain.get("chain_id"),
        "external_score_summary": monotonicity,
        "sidecar_path": safe_rel(sidecar_path, repo),
        "sidecar_hash": sidecar["sidecar_hash"],
        "created_utc": now(),
    })
    return sidecar


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Attach an external AI-R&D score ledger to a certificate-preserving CRSI-Core chain.")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--crsi-chain-summary", type=Path, required=True)
    p.add_argument("--task-manifest", type=Path, default=None)
    p.add_argument("--score-ledger", type=Path, default=None)
    p.add_argument("--outdir", type=Path, default=Path("artifacts") / "crsi_external_bridge" / "results" / "smoke")
    p.add_argument("--benchmark-id", default="re_metr_bridge_smoke")
    p.add_argument("--benchmark-kind", default="re_metr_external_ai_rd_adapter")
    p.add_argument("--official-re-bench", action="store_true")
    p.add_argument("--official-metr", action="store_true")
    p.add_argument("--public-benchmark", action="store_true")
    p.add_argument("--make-smoke-fixture", action="store_true", help="Generate a synthetic adapter smoke task/score ledger; not an external benchmark result.")
    p.add_argument("--allow-nonregression", action="store_true", help="Accept non-regression instead of requiring at least one strict score improvement.")
    p.add_argument("--scorer-artifact", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo = find_repo_root(args.repo_root)
    chain_summary = args.crsi_chain_summary if args.crsi_chain_summary.is_absolute() else repo / args.crsi_chain_summary
    outdir = args.outdir if args.outdir.is_absolute() else repo / args.outdir
    task_manifest = args.task_manifest if args.task_manifest is None or args.task_manifest.is_absolute() else repo / args.task_manifest
    score_ledger = args.score_ledger if args.score_ledger is None or args.score_ledger.is_absolute() else repo / args.score_ledger
    scorer_artifact = args.scorer_artifact if args.scorer_artifact is None or args.scorer_artifact.is_absolute() else repo / args.scorer_artifact
    sidecar = build_bridge(
        repo=repo,
        chain_summary_path=chain_summary,
        task_manifest_path=task_manifest,
        score_ledger_path=score_ledger,
        outdir=outdir,
        benchmark_id=args.benchmark_id,
        benchmark_kind=args.benchmark_kind,
        official_re_bench=args.official_re_bench,
        official_metr=args.official_metr,
        public_benchmark=args.public_benchmark,
        adapter_smoke=args.make_smoke_fixture,
        allow_nonregression=args.allow_nonregression,
        scorer_artifact=scorer_artifact,
    )
    print(json.dumps({
        "ok": sidecar["ok"],
        "sidecar": str(outdir / "crsi_external_bridge_sidecar.json"),
        "benchmark_id": sidecar["benchmark_id"],
        "benchmark_kind": sidecar["benchmark_kind"],
        "external_score_summary": sidecar["external_score_summary"],
        "schema_errors": sidecar.get("schema_errors", []),
        "claim_boundary": sidecar["claim_boundary"],
    }, indent=2, sort_keys=True))
    return 0 if sidecar["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
