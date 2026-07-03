#!/usr/bin/env python3
"""M3-Min learned-entry audit harness for RCP/RCLM artifacts.

B9-Bridge Phase 2 scope:
    - creates a controlled learned-system surrogate M_theta;
    - runs or consumes a closed-loop certified successor-generation trace;
    - checks the generated artifact with the existing RCP/RCLM checker;
    - constructs LECert_{0:N};
    - reports FullPass / PartialPass / Fail.

Non-scope:
    - not broad learned-agent entry;
    - not a public external AI-agent benchmark result;
    - not evidence that arbitrary trained systems enter the theorem domain.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from controlled_learned_system import make_controlled_learned_system, write_controlled_system
from lecert_schema import (
    CERTIFICATE_FIELDS,
    FAIL,
    FULL_PASS,
    PARTIAL_PASS,
    LearnedEntryCertificate,
    make_component,
    sha256_obj,
    summarize_components,
    validate_lecert_dict,
    write_json,
    load_json,
)


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


def residuals_nonpositive_for_accepted(accepted: List[Dict[str, Any]]) -> bool:
    for item in accepted:
        residuals = item.get("residuals", {})
        if not residuals:
            return False
        for value in residuals.values():
            try:
                if float(value) > 0:
                    return False
            except (TypeError, ValueError):
                return False
    return True


def all_trust_valid(accepted: List[Dict[str, Any]]) -> bool:
    return bool(accepted) and all(item.get("trust_anchor_valid") is True for item in accepted)


def all_goal_drift_zero(accepted: List[Dict[str, Any]], runlog: Dict[str, Any]) -> bool:
    if float(runlog.get("goal_identity_drift", 1.0)) != 0.0:
        return False
    return bool(accepted) and all(float(item.get("goal_identity_drift", 1.0)) == 0.0 for item in accepted)


def all_reality_contained(accepted: List[Dict[str, Any]], runlog: Dict[str, Any]) -> bool:
    if runlog.get("singleton_reality_containment") is not True:
        return False
    if not accepted:
        return False
    for item in accepted:
        reality = item.get("reality_containment", {})
        if reality.get("contained") is not True:
            return False
    return True


def state_count(artifact: Dict[str, Any]) -> int:
    states = artifact.get("states")
    if isinstance(states, dict) and isinstance(states.get("rho"), list):
        return len(states["rho"])
    if isinstance(states, list):
        return len(states)
    return 0


def tractability_certified(artifact: Dict[str, Any], runlog: Dict[str, Any], accepted: List[Dict[str, Any]], max_final_dimension: int) -> bool:
    final_dim = int(runlog.get("final_dimension", 0))
    if final_dim <= 0 or final_dim > max_final_dimension:
        return False
    if not accepted:
        return False
    for item in accepted:
        cost = item.get("cost_record", {})
        if int(cost.get("diagonal_table_bound_units", 0)) <= 0:
            return False
        if int(cost.get("residual_checks", 0)) <= 0:
            return False
    return True


def build_components(
    *,
    mode: str,
    N: int,
    system_obj: Dict[str, Any],
    artifact: Dict[str, Any],
    runlog: Dict[str, Any],
    accepted: List[Dict[str, Any]],
    rejected: List[Dict[str, Any]],
    hashes: Dict[str, Any],
    checker_summary: Dict[str, Any],
    engine_summary: Dict[str, Any],
    engine_code: int,
    checker_code: int,
    max_final_dimension: int,
) -> Dict[str, Any]:
    states = artifact.get("states", [])
    states_count = state_count(artifact)
    pcs = artifact.get("pcs", [])
    abilities = artifact.get("abilities", [])
    closed_loop_ok = engine_code == 0 and runlog.get("ok", engine_summary.get("ok")) is True
    checker_passed = checker_code == 0 and checker_summary.get("ok") is True

    components = {
        "TypeCert": make_component(
            "TypeCert",
            passed=(mode in {"rcp", "rclm"} and int(N) >= 1 and states_count == N + 1 and int(runlog.get("final_dimension", 0)) == 2 ** (N + 1)),
            evidence={"states": states_count, "expected_states": N + 1, "final_dimension": runlog.get("final_dimension")},
        ),
        "RegSemCert": make_component(
            "RegSemCert",
            passed=(artifact.get("description") is not None and artifact.get("generator") is not None and system_obj.get("architecture") is not None),
            evidence={"artifact_description_present": artifact.get("description") is not None, "system_architecture": system_obj.get("architecture")},
        ),
        "CoverageCert": make_component(
            "CoverageCert",
            passed=(int(runlog.get("generated_candidates", 0)) == 9 * N and int(runlog.get("rejected_candidates", 0)) >= 8 * N and len(rejected) >= 8 * N),
            evidence={"generated_candidates": runlog.get("generated_candidates"), "rejected_candidates": runlog.get("rejected_candidates"), "rejection_kinds_present": sorted({r.get("kind") for r in rejected})},
        ),
        "SVWitLib": make_component(
            "SVWitLib",
            passed=(len(accepted) == N and all(str(item.get("kind")) == "valid_append_mem" for item in accepted)),
            evidence={"accepted_candidates": len(accepted), "accepted_kinds": [item.get("kind") for item in accepted]},
        ),
        "SVBuilderTrace": make_component(
            "SVBuilderTrace",
            passed=(closed_loop_ok and runlog.get("closed_loop_candidate_search") is True and runlog.get("static_predeclared_json_path") is False),
            evidence={"closed_loop_ok": closed_loop_ok, "closed_loop_candidate_search": runlog.get("closed_loop_candidate_search"), "static_predeclared_json_path": runlog.get("static_predeclared_json_path")},
        ),
        "PCS": make_component(
            "PCS",
            passed=(len(pcs) == N and len(accepted) == N and bool(hashes.get("pcs_sha256"))),
            evidence={"pcs_count": len(pcs), "accepted_count": len(accepted), "pcs_sha256": hashes.get("pcs_sha256")},
        ),
        "Q_SV_A_nonpositive": make_component(
            "Q_SV_A_nonpositive",
            passed=(runlog.get("all_residuals_nonpositive") is True and residuals_nonpositive_for_accepted(accepted)),
            evidence={"runlog_all_residuals_nonpositive": runlog.get("all_residuals_nonpositive")},
        ),
        "GoalId": make_component(
            "GoalId",
            passed=all_goal_drift_zero(accepted, runlog),
            evidence={"goal_identity_drift": runlog.get("goal_identity_drift")},
        ),
        "TrustRef": make_component(
            "TrustRef",
            passed=all_trust_valid(accepted),
            evidence={"accepted_trust_anchor_valid": [item.get("trust_anchor_valid") for item in accepted]},
        ),
        "RealCont": make_component(
            "RealCont",
            passed=all_reality_contained(accepted, runlog),
            evidence={"singleton_reality_containment": runlog.get("singleton_reality_containment")},
        ),
        "SVTract": make_component(
            "SVTract",
            passed=tractability_certified(artifact, runlog, accepted, max_final_dimension),
            evidence={"final_dimension": runlog.get("final_dimension"), "max_final_dimension": max_final_dimension, "cost_records": [item.get("cost_record", {}) for item in accepted]},
        ),
        "ReplayTrace": make_component(
            "ReplayTrace",
            passed=(checker_passed and bool(hashes) and checker_summary.get("steps_checked") == N),
            evidence={"checker_passed": checker_passed, "steps_checked": checker_summary.get("steps_checked"), "hash_keys": sorted(hashes.keys())},
        ),
    }
    return components


def run_learned_entry_audit(
    *,
    repo: Path,
    mode: str,
    N: int,
    seed: int,
    outdir: Path,
    max_final_dimension: int,
    run_closed_loop: bool,
    existing_run_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    mode = mode.lower().strip()
    if mode not in {"rcp", "rclm"}:
        raise ValueError("mode must be 'rcp' or 'rclm'")
    if N < 1:
        raise ValueError("N must be positive")

    case_id = f"{mode}_N{N}_seed{seed}"
    case_dir = outdir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    closed_loop_run_dir = (existing_run_dir.resolve() if existing_run_dir else (case_dir / "closed_loop_run").resolve())

    system = make_controlled_learned_system(mode, N, seed)
    system_obj = write_controlled_system(case_dir / "learned_system.json", system)

    engine_code = 0
    engine_out = ""
    engine_err = ""
    engine_summary: Dict[str, Any] = {}
    if run_closed_loop or not (closed_loop_run_dir / "generated_artifact.json").exists():
        engine = repo / "artifacts" / "common" / "closed_loop_reference_engine.py"
        engine_cmd = [sys.executable, str(engine), "--mode", mode, "--N", str(N), "--seed", str(seed), "--run-dir", str(closed_loop_run_dir)]
        engine_code, engine_out, engine_err = run_command(engine_cmd, repo)
        engine_summary = extract_json_from_stdout(engine_out) if engine_out.strip() else {}
    else:
        runlog_path = closed_loop_run_dir / "closed_loop_runlog.json"
        engine_summary = load_json(runlog_path) if runlog_path.exists() else {}

    artifact_path = closed_loop_run_dir / "generated_artifact.json"
    checker = repo / "artifacts" / mode / "checker.py"
    checker_cmd = [sys.executable, str(checker), str(artifact_path)]
    checker_code, checker_out, checker_err = run_command(checker_cmd, repo)
    checker_summary = extract_json_from_stdout(checker_out) if checker_out.strip() else {}

    artifact = load_json(artifact_path) if artifact_path.exists() else {}
    runlog = load_json(closed_loop_run_dir / "closed_loop_runlog.json") if (closed_loop_run_dir / "closed_loop_runlog.json").exists() else {}
    accepted = load_json(closed_loop_run_dir / "accepted_trajectory.json") if (closed_loop_run_dir / "accepted_trajectory.json").exists() else []
    rejected = load_json(closed_loop_run_dir / "rejected_candidates.json") if (closed_loop_run_dir / "rejected_candidates.json").exists() else []
    hashes = load_json(closed_loop_run_dir / "hashes.json") if (closed_loop_run_dir / "hashes.json").exists() else {}

    components = build_components(
        mode=mode,
        N=N,
        system_obj=system_obj,
        artifact=artifact,
        runlog=runlog,
        accepted=accepted,
        rejected=rejected,
        hashes=hashes,
        checker_summary=checker_summary,
        engine_summary=engine_summary,
        engine_code=engine_code,
        checker_code=checker_code,
        max_final_dimension=max_final_dimension,
    )

    closed_loop_ok = engine_code == 0 and runlog.get("ok", engine_summary.get("ok")) is True
    checker_passed = checker_code == 0 and checker_summary.get("ok") is True

    lecert = LearnedEntryCertificate(
        mode=mode,
        N=N,
        seed=seed,
        learned_system_id=system_obj["system_id"],
        components=components,
        source_paths={
            "case_dir": safe_rel(case_dir, repo),
            "closed_loop_run_dir": safe_rel(closed_loop_run_dir, repo),
            "generated_artifact": safe_rel(artifact_path, repo),
            "closed_loop_runlog": safe_rel(closed_loop_run_dir / "closed_loop_runlog.json", repo),
            "accepted_trajectory": safe_rel(closed_loop_run_dir / "accepted_trajectory.json", repo),
            "rejected_candidates": safe_rel(closed_loop_run_dir / "rejected_candidates.json", repo),
            "hashes": safe_rel(closed_loop_run_dir / "hashes.json", repo),
            "checker": safe_rel(checker, repo),
        },
        claim_boundary={
            "m3_min_learned_entry_boundary": True,
            "b9_learned_entry_fullpass": all(component.passed for component in components.values()) and closed_loop_ok and checker_passed,
            "b10_external_public_benchmark": False,
            "arbitrary_trained_system_entry": False,
            "frontier_scale_validation": False,
            "full_autonomous_rsi": False,
        },
        notes=[
            "FullPass means every finite learned-entry certificate component is supplied for this controlled run.",
            "This does not prove arbitrary trained-system entry or any external public benchmark improvement.",
        ],
    )

    lecert_obj = lecert.to_dict(closed_loop_ok, checker_passed)
    ok_schema, schema_errors = validate_lecert_dict(lecert_obj)
    component_summary = summarize_components(components)
    audit_summary = {
        "ok": lecert_obj["audit_status"] == FULL_PASS and ok_schema,
        "suite_name": "B9-Bridge Phase 2: M3-Min learned-entry audit harness",
        "audit_status": lecert_obj["audit_status"],
        "mode": mode,
        "N": N,
        "seed": seed,
        "learned_system_id": system_obj["system_id"],
        "closed_loop_ok": closed_loop_ok,
        "checker_passed": checker_passed,
        "component_summary": component_summary,
        "LECert": {field: lecert_obj[field] for field in CERTIFICATE_FIELDS},
        "schema_valid": ok_schema,
        "schema_errors": schema_errors,
        "claim_boundary": lecert_obj["claim_boundary"],
        "paths": lecert_obj["source_paths"],
        "engine_exit_code": engine_code,
        "checker_exit_code": checker_code,
        "engine_stderr": engine_err.strip(),
        "checker_stderr": checker_err.strip(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }

    write_json(case_dir / "lecert.json", lecert_obj)
    write_json(case_dir / "learned_entry_audit_summary.json", audit_summary)
    write_json(case_dir / "audit_runlog.json", {
        "audit_summary": audit_summary,
        "engine_summary": engine_summary,
        "checker_summary": checker_summary,
        "system": system_obj,
    })
    return audit_summary


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M3-Min learned-entry audit for a controlled RCP/RCLM system.")
    parser.add_argument("--mode", choices=["rcp", "rclm"], default="rclm")
    parser.add_argument("--N", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--outdir", type=Path, default=Path("artifacts") / "learned_entry" / "results")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--max-final-dimension", type=int, default=2 ** 20)
    parser.add_argument("--existing-run-dir", type=Path, default=None, help="Use an existing closed-loop run directory instead of generating a fresh run.")
    parser.add_argument("--no-run-closed-loop", action="store_true", help="Do not run the closed-loop engine; require --existing-run-dir or existing default files.")
    parser.add_argument("--allow-partial", action="store_true", help="Return exit code 0 for PartialPass. Fail still returns nonzero.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    repo = find_repo_root(args.repo_root)
    outdir = (repo / args.outdir).resolve() if not args.outdir.is_absolute() else args.outdir.resolve()
    summary = run_learned_entry_audit(
        repo=repo,
        mode=args.mode,
        N=args.N,
        seed=args.seed,
        outdir=outdir,
        max_final_dimension=args.max_final_dimension,
        run_closed_loop=not args.no_run_closed_loop,
        existing_run_dir=args.existing_run_dir,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["audit_status"] == FULL_PASS:
        return
    if summary["audit_status"] == PARTIAL_PASS and args.allow_partial:
        return
    raise SystemExit(1)


if __name__ == "__main__":
    main()
