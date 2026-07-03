#!/usr/bin/env python3
"""Open-loop arbitrary-horizon canonical RCP/RCLM reference artifact generator.

This script is the Tier-1 generator upgrade for the RCP/RCLM executable
instantiation package. It is intentionally not a closed-loop RSI engine: it does
not search over competing successors, reject invalid candidates, or improve its
own generator. Instead it constructs the canonical appended-module reference
trajectory for any finite horizon N >= 2, writes the corresponding proof-carrying
artifact JSON, and writes a reproducible generation run log.

Generated artifacts are compatible with the existing RCP/RCLM replay checkers:

    python artifacts/common/generate_reference_artifact.py --mode rcp --N 5 \
      --out artifacts/rcp/generated_artifact_N5.json \
      --runlog artifacts/rcp/generated_runlog_N5.json
    python artifacts/rcp/checker.py artifacts/rcp/generated_artifact_N5.json

    python artifacts/common/generate_reference_artifact.py --mode rclm --N 5 \
      --out artifacts/rclm/generated_artifact_N5.json \
      --runlog artifacts/rclm/generated_runlog_N5.json
    python artifacts/rclm/checker.py artifacts/rclm/generated_artifact_N5.json

Scope boundary:
    - Proves/generates arbitrary finite prefixes of the canonical append-only
      reference construction.
    - Does not prove broad learned-agent entry.
    - Does not implement closed-loop candidate generation/accept-reject search.
    - Does not replace the Lean certificate; it produces replayable JSON inputs
      for the existing executable checkers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

RESIDUAL_KEYS = [
    "seed", "cand", "ver", "trans", "goal", "unc", "trust", "budget",
    "persist", "world", "proof", "sound",
]

RHO0 = [2 / 3, 1 / 3]
SIGMA0 = [1 / 3, 2 / 3]


def canonical_json(obj: Any) -> bytes:
    """Stable JSON encoding used for reproducible hashes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def rel_entropy_base2(p: List[float], q: List[float]) -> float:
    total = 0.0
    for pi, qi in zip(p, q):
        if pi == 0:
            continue
        if qi == 0:
            raise ValueError("relative entropy infinite: q has zero where p is positive")
        total += pi * math.log(pi / qi, 2)
    return total


def append_alpha_1(probs: List[float]) -> List[float]:
    """Canonical append of deterministic |1><1| in diagonal coordinates."""
    out: List[float] = []
    for p in probs:
        out.extend([0.0, p])
    return out


def ability_sets(N: int) -> List[List[str]]:
    return [[f"a{i}" for i in range(t + 1)] for t in range(N + 1)]


def state_trajectory(N: int) -> Tuple[List[List[float]], List[List[float]]]:
    rho = [RHO0]
    sigma = [SIGMA0]
    for _ in range(N):
        rho.append(append_alpha_1(rho[-1]))
        sigma.append(append_alpha_1(sigma[-1]))
    return rho, sigma


def zero_residuals(value: float = 0.0) -> Dict[str, float]:
    return {key: value for key in RESIDUAL_KEYS}


def common_external_mechanization(scope: str) -> Dict[str, Any]:
    return {
        "certificate_supplied": False,
        "status": "not_proof_assistant_mechanized_in_this_artifact",
        "scope_if_supplied": scope,
    }


def build_rcp_artifact(N: int) -> Dict[str, Any]:
    rho, sigma = state_trajectory(N)
    abilities = ability_sets(N)
    pcs: List[Dict[str, Any]] = []
    for t in range(N):
        pcs.append(
            {
                "t": t,
                "update": f"AppendMem(a{t + 1})",
                "phi": "append_alpha_1",
                "recovery": "trace_last_qubit",
                "checker_result": 1,
                "residuals": zero_residuals(0),
                "goal_identity_drift": 0,
                "reality_containment": {
                    "contained": True,
                    "envelope": "singleton_true_law",
                    "beta_env": 0,
                    "epsilon_env": 0,
                },
                "cost": {
                    "checker_steps": 18,
                    "residual_checks": len(RESIDUAL_KEYS),
                },
            }
        )
    final_dim = len(rho[-1])
    artifact: Dict[str, Any] = {
        "artifact_type": "RCP-Batch13R-B-controlled-canonical-reference-artifact",
        "generator": "open_loop_arbitrary_horizon_generator_v1",
        "description": (
            "Generated canonical appended-module RCP reference artifact. "
            "This is an open-loop arbitrary finite-prefix construction, not a closed-loop RSI engine."
        ),
        "horizon_N": N,
        "states": {"rho": rho, "sigma": sigma},
        "abilities": abilities,
        "updates": [f"AppendMem(a{t + 1})" for t in range(N)],
        "pcs": pcs,
        "goal_object": "constant U_can with identity transport",
        "trust_anchor": "frozen checker node C_star, not modified by updates",
        "true_environment": "deterministic finite append_alpha_1 transition law",
        "tractability": {
            "dense_cost_bound": N * (final_dim ** 3),
            "diagonal_table_cost_bound": N * final_dim,
            "final_dimension": final_dim,
        },
        "external_mechanization": {
            "certificate_supplied": False,
            "required_for_machine_checked_claim": "MechCert_{0:N}^{RCP,can}",
            "status": "not_proof_assistant_mechanized_in_this_artifact",
            "scope_if_supplied": "canonical finite RCP non-loss/recovery/ability/residual/checker core only",
        },
    }
    artifact["hash_manifest"] = {
        "states_sha256": sha256_obj(artifact["states"]),
        "abilities_sha256": sha256_obj(artifact["abilities"]),
        "pcs_sha256": sha256_obj(artifact["pcs"]),
        "artifact_without_hash_manifest_sha256": sha256_obj({k: v for k, v in artifact.items() if k != "hash_manifest"}),
    }
    return artifact


def build_rclm_artifact(N: int) -> Dict[str, Any]:
    rho, sigma = state_trajectory(N)
    abilities = ability_sets(N)
    D0 = rel_entropy_base2(rho[0], sigma[0])
    pcs: List[Dict[str, Any]] = []
    for t in range(N):
        rho_before = rho[t]
        rho_after = rho[t + 1]
        sigma_before = sigma[t]
        sigma_after = sigma[t + 1]
        n_after = len(rho_after)
        pcs.append(
            {
                "t": t,
                "candidate": f"AppendMem(a{t + 1})",
                "transition": "X -> X tensor alpha_t where alpha_t is deterministic |1><1|",
                "transition_kind": "canonical_append_only_non_noop",
                "proof_carrying_packet_kind": "RCLM-Batch13R-B-controlled-PCS",
                "checker_result": 1,
                "explicit_rclm_sv_residuals": zero_residuals(-1.0),
                "goal_identity_drift": 0.0,
                "reality_containment": {
                    "contained": True,
                    "kind": "singleton_simulated_world",
                    "beta_env": 0.0,
                    "epsilon_env": 0.0,
                },
                "trust": "immutable_predecessor_checker_anchor_not_modified",
                "recovery": "partial_trace_last_appended_register",
                "old_abilities": abilities[t],
                "new_abilities": abilities[t + 1],
                "new_ability": f"a{t + 1}",
                "relative_entropy_before": rel_entropy_base2(rho_before, sigma_before),
                "relative_entropy_after": rel_entropy_base2(rho_after, sigma_after),
                "rho_before": rho_before,
                "rho_after": rho_after,
                "sigma_before": sigma_before,
                "sigma_after": sigma_after,
                "cost_record": {
                    "dense_matrix_bound_units": n_after ** 3,
                    "diagonal_table_bound_units": n_after,
                },
            }
        )
    final_dim = len(rho[-1])
    artifact: Dict[str, Any] = {
        "artifact_type": "RCLM-Batch13R-B-controlled-executable-reference-system",
        "generator": "open_loop_arbitrary_horizon_generator_v1",
        "description": (
            "Generated canonical appended-module RCLM reference artifact. "
            "This is an open-loop arbitrary finite-prefix construction, not a closed-loop RSI engine."
        ),
        "horizon_N": N,
        "states": {"rho": rho, "sigma": sigma},
        "abilities": abilities,
        "pcs": pcs,
        "controlled_executable_conditions": {
            "N_ge_2": N >= 2,
            "all_updates_non_noop": True,
            "strict_ability_expansion_each_step": True,
            "explicit_residuals_present": True,
            "zero_goal_drift": True,
            "singleton_reality_containment": True,
        },
        "tractability": {
            "dense_cost_bound": N * (final_dim ** 3),
            "diagonal_table_cost_bound": N * final_dim,
            "final_dimension": final_dim,
        },
        "external_mechanization": {
            "certificate_supplied": False,
            "required_certificate": "MechCert_0_N_RCLM_can",
            "status": "not_proof_assistant_mechanized_in_this_artifact",
            "scope_if_supplied": (
                "canonical finite RCLM non-loss/recovery/ability/residual/checker/replay/refinement core only"
            ),
        },
        "open_loop_generation_status": {
            "successor_steps_are_generated_from_N": True,
            "successor_steps_are_predeclared_by_static_json": False,
            "closed_loop_candidate_search": False,
            "accept_reject_search": False,
            "relative_entropy_base2_initial": D0,
        },
    }
    artifact["hash_manifest"] = {
        "states_sha256": sha256_obj(artifact["states"]),
        "abilities_sha256": sha256_obj(artifact["abilities"]),
        "pcs_sha256": sha256_obj(artifact["pcs"]),
        "artifact_without_hash_manifest_sha256": sha256_obj({k: v for k, v in artifact.items() if k != "hash_manifest"}),
    }
    return artifact


def build_artifact(mode: str, N: int) -> Dict[str, Any]:
    if N < 2:
        raise ValueError("N must be >= 2 for the controlled canonical reference artifact")
    if mode == "rcp":
        return build_rcp_artifact(N)
    if mode == "rclm":
        return build_rclm_artifact(N)
    raise ValueError(f"unknown mode: {mode}")


def build_runlog(mode: str, artifact: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
    N = int(artifact["horizon_N"])
    rho_final = artifact["states"]["rho"][-1]
    sigma0 = artifact["states"]["sigma"][0]
    rho0 = artifact["states"]["rho"][0]
    return {
        "ok": True,
        "mode": mode,
        "generator": "open_loop_arbitrary_horizon_generator_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "horizon_N": N,
        "output_artifact": str(output_path),
        "artifact_hash": sha256_obj(artifact),
        "final_dimension": len(rho_final),
        "relative_entropy_base2_initial": rel_entropy_base2(rho0, sigma0),
        "steps_generated": N,
        "updates_generated": [f"AppendMem(a{t + 1})" for t in range(N)],
        "strict_ability_expansion_each_step": True,
        "non_loss_recovery_preserved_by_construction": True,
        "explicit_residuals_generated": True,
        "singleton_reality_containment": True,
        "closed_loop_candidate_search": False,
        "result": "arbitrary_finite_prefix_reference_construction",
    }


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an open-loop arbitrary-N canonical RCP/RCLM reference artifact."
    )
    parser.add_argument("--mode", choices=["rcp", "rclm"], required=True, help="Artifact dialect to generate.")
    parser.add_argument("--N", type=int, default=3, help="Finite horizon N >= 2.")
    parser.add_argument("--out", type=Path, default=None, help="Output artifact JSON path.")
    parser.add_argument("--runlog", type=Path, default=None, help="Output generation runlog JSON path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = args.out or Path(f"generated_{args.mode}_artifact_N{args.N}.json")
    runlog_path = args.runlog or out.with_name(out.stem.replace("artifact", "runlog") + out.suffix)
    artifact = build_artifact(args.mode, args.N)
    write_json(out, artifact)
    runlog = build_runlog(args.mode, artifact, out)
    write_json(runlog_path, runlog)
    print(json.dumps({
        "ok": True,
        "mode": args.mode,
        "N": args.N,
        "artifact_path": str(out),
        "runlog_path": str(runlog_path),
        "artifact_hash": sha256_obj(artifact),
        "final_dimension": len(artifact["states"]["rho"][-1]),
        "closed_loop_candidate_search": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
