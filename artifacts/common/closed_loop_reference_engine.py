#!/usr/bin/env python3
"""Closed-loop certified successor synthesis reference engine for RCP/RCLM.

This is the Tier-2/3/4 executable-artifact upgrade:

    current certified state rho_t
        -> generate candidate successor set C_t
        -> build proof-carrying packets for each candidate
        -> verify candidate obligations
        -> reject invalid candidates with explicit reasons
        -> accept a passing candidate
        -> append accepted successor to the trajectory
        -> repeat for a finite horizon N

Scope boundary:
    - This is a finite closed-loop certified successor-generation reference
      system inside the canonical diagonal append-only RCP/RCLM class.
    - It is not a broad autonomous RSI/ASI system.
    - It does not prove arbitrary trained-system entry.
    - It does not replace the Lean certificate; it creates replayable artifacts
      and logs that can be checked by the existing executable checkers.

The accepted path remains the canonical AppendMem path, but it is selected by
verification from a candidate set containing invalid/adversarial candidates.
The generated final artifact is compatible with the existing RCP/RCLM checkers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

RESIDUAL_KEYS = [
    "seed", "cand", "ver", "trans", "goal", "unc", "trust", "budget",
    "persist", "world", "proof", "sound",
]

RHO0 = [2 / 3, 1 / 3]
SIGMA0 = [1 / 3, 2 / 3]


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def rel_entropy_base2(p: List[float], q: List[float]) -> float:
    if len(p) != len(q):
        raise AssertionError("relative entropy inputs have different dimensions")
    total = 0.0
    for pi, qi in zip(p, q):
        if pi == 0:
            continue
        if qi == 0:
            raise AssertionError("relative entropy infinite: q has zero where p is positive")
        total += pi * math.log(pi / qi, 2)
    return total


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(a - b) <= tol


def append_alpha_1(probs: List[float]) -> List[float]:
    """Canonical append of deterministic |1><1| in diagonal coordinates."""
    out: List[float] = []
    for p in probs:
        out.extend([0.0, p])
    return out


def append_alpha_0(probs: List[float]) -> List[float]:
    """Wrong-but-recoverable append used for invalid-candidate tests."""
    out: List[float] = []
    for p in probs:
        out.extend([p, 0.0])
    return out


def recover_last_qubit(probs: List[float]) -> List[float]:
    if len(probs) % 2 != 0:
        raise AssertionError("state length not divisible by 2")
    return [probs[i] + probs[i + 1] for i in range(0, len(probs), 2)]


def zero_residuals(value: float = 0.0) -> Dict[str, float]:
    return {key: value for key in RESIDUAL_KEYS}


def ability_set(t: int) -> List[str]:
    return [f"a{i}" for i in range(t + 1)]


def diagonal_cost_record(n_after: int, residual_value_count: int = len(RESIDUAL_KEYS)) -> Dict[str, int]:
    return {
        "dense_matrix_bound_units": n_after ** 3,
        "diagonal_table_bound_units": n_after,
        "residual_checks": residual_value_count,
        "checker_steps": 18,
    }


@dataclass
class Candidate:
    t: int
    kind: str
    update: str
    rho_after: List[float]
    sigma_after: List[float]
    old_abilities: List[str]
    new_abilities: List[str]
    residuals: Dict[str, float]
    goal_identity_drift: float
    reality_containment: Dict[str, Any]
    trust_anchor_valid: bool
    cost_record: Dict[str, int]
    proof_trace: Dict[str, Any]


def candidate_to_log_dict(candidate: Candidate, accepted: bool, reasons: List[str]) -> Dict[str, Any]:
    d = asdict(candidate)
    d["accepted"] = accepted
    d["rejection_reasons"] = reasons
    d["candidate_hash"] = sha256_obj(asdict(candidate))
    return d


def build_candidate(
    *,
    mode: str,
    t: int,
    kind: str,
    rho_t: List[float],
    sigma_t: List[float],
    ab_t: List[str],
) -> Candidate:
    """Build one candidate proof-carrying packet candidate.

    The candidate grammar intentionally includes invalid moves to demonstrate
    non-vacuous rejection:
        - wrong_dimension_append
        - noop_no_ability_expansion
        - residual_positive
        - recovery_breaking
        - bad_goal_transport
        - bad_trust_anchor
        - bad_cost_bound
        - valid_append_mem
    """
    new_ability = f"a{t + 1}"

    if kind == "valid_append_mem":
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0 if mode == "rcp" else -1.0)
        goal_drift = 0.0
        contained = True
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = f"AppendMem(a{t + 1})"
    elif kind == "wrong_dimension_append":
        rho_after = append_alpha_1(rho_t) + [0.0]
        sigma_after = append_alpha_1(sigma_t) + [0.0]
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        goal_drift = 0.0
        contained = True
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = f"BadAppendWrongDim(a{t + 1})"
    elif kind == "noop_no_ability_expansion":
        rho_after = list(rho_t)
        sigma_after = list(sigma_t)
        ab_next = list(ab_t)
        residuals = zero_residuals(0.0)
        goal_drift = 0.0
        contained = True
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = "NoOp"
    elif kind == "residual_positive":
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        residuals["budget"] = 1.0
        goal_drift = 0.0
        contained = True
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = f"AppendMemPositiveResidual(a{t + 1})"
    elif kind == "recovery_breaking":
        # Same dimension, but recovery/marginal is intentionally wrong.
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        if rho_after:
            rho_after[-1] = max(0.0, rho_after[-1] - 0.125)
            rho_after[0] += 0.125
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        goal_drift = 0.0
        contained = True
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = f"AppendMemRecoveryBreaking(a{t + 1})"
    elif kind == "bad_goal_transport":
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        goal_drift = 0.1
        contained = True
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = f"AppendMemBadGoal(a{t + 1})"
    elif kind == "bad_trust_anchor":
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        goal_drift = 0.0
        contained = True
        trust_valid = False
        cost = diagonal_cost_record(len(rho_after))
        update = f"AppendMemBadTrust(a{t + 1})"
    elif kind == "bad_cost_bound":
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        goal_drift = 0.0
        contained = True
        trust_valid = True
        cost = {"dense_matrix_bound_units": 0, "diagonal_table_bound_units": 0, "residual_checks": len(RESIDUAL_KEYS)}
        update = f"AppendMemBadCost(a{t + 1})"
    elif kind == "bad_reality_containment":
        rho_after = append_alpha_1(rho_t)
        sigma_after = append_alpha_1(sigma_t)
        ab_next = ab_t + [new_ability]
        residuals = zero_residuals(0.0)
        goal_drift = 0.0
        contained = False
        trust_valid = True
        cost = diagonal_cost_record(len(rho_after))
        update = f"AppendMemBadReality(a{t + 1})"
    else:
        raise ValueError(f"unknown candidate kind: {kind}")

    return Candidate(
        t=t,
        kind=kind,
        update=update,
        rho_after=rho_after,
        sigma_after=sigma_after,
        old_abilities=list(ab_t),
        new_abilities=ab_next,
        residuals=residuals,
        goal_identity_drift=goal_drift,
        reality_containment={
            "contained": contained,
            "envelope": "singleton_true_law" if mode == "rcp" else "singleton_simulated_world",
            "beta_env": 0.0,
            "epsilon_env": 0.0,
        },
        trust_anchor_valid=trust_valid,
        cost_record=cost,
        proof_trace={
            "transition_rule": "candidate_generated_from_current_state_not_static_json",
            "candidate_grammar_kind": kind,
            "new_ability": new_ability,
            "closed_loop_step": t,
            "mode": mode,
        },
    )


def verify_candidate(
    *,
    mode: str,
    candidate: Candidate,
    rho_t: List[float],
    sigma_t: List[float],
    abilities_t: List[str],
    base_relative_entropy: float,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    t = candidate.t
    rho_next = candidate.rho_after
    sigma_next = candidate.sigma_after

    if len(rho_next) != 2 * len(rho_t):
        reasons.append("wrong_dimension: rho successor dimension is not 2 * predecessor dimension")
    if len(sigma_next) != 2 * len(sigma_t):
        reasons.append("wrong_dimension: sigma successor dimension is not 2 * predecessor dimension")

    if candidate.update == "NoOp":
        reasons.append("no_op: candidate does not perform a non-noop successor construction")

    if abs(sum(rho_next) - 1.0) > 1e-12 or any(x < -1e-12 for x in rho_next):
        reasons.append("rho_not_probability_vector")
    if abs(sum(sigma_next) - 1.0) > 1e-12 or any(x < -1e-12 for x in sigma_next):
        reasons.append("sigma_not_probability_vector")

    if len(rho_next) % 2 == 0:
        try:
            if recover_last_qubit(rho_next) != rho_t:
                reasons.append("recovery_failure: recovered rho does not equal predecessor")
        except AssertionError as exc:
            reasons.append(f"recovery_failure: {exc}")
    if len(sigma_next) % 2 == 0:
        try:
            if recover_last_qubit(sigma_next) != sigma_t:
                reasons.append("recovery_failure: recovered sigma does not equal predecessor")
        except AssertionError as exc:
            reasons.append(f"recovery_failure: {exc}")

    try:
        d_after = rel_entropy_base2(rho_next, sigma_next)
        if not close(d_after, base_relative_entropy):
            reasons.append("non_loss_failure: protected relative entropy is not preserved")
    except Exception as exc:
        reasons.append(f"non_loss_failure: {exc}")

    old = set(abilities_t)
    new = set(candidate.new_abilities)
    expected_new_ability = f"a{t + 1}"
    if not old.issubset(new):
        reasons.append("ability_preservation_failure: predecessor abilities not included")
    if expected_new_ability not in new - old:
        reasons.append("strict_ability_expansion_failure: expected new ability absent")

    for key in RESIDUAL_KEYS:
        if key not in candidate.residuals:
            reasons.append(f"missing_residual:{key}")
        elif candidate.residuals[key] > 0:
            reasons.append(f"positive_residual:{key}={candidate.residuals[key]}")

    if candidate.goal_identity_drift != 0:
        reasons.append("goal_identity_failure: nonzero goal drift")

    if candidate.reality_containment.get("contained") is not True:
        reasons.append("reality_containment_failure: true environment not contained")
    if candidate.reality_containment.get("beta_env", 0) != 0:
        reasons.append("reality_containment_failure: beta_env nonzero")
    if candidate.reality_containment.get("epsilon_env", 0) != 0:
        reasons.append("reality_containment_failure: epsilon_env nonzero")

    if not candidate.trust_anchor_valid:
        reasons.append("trust_failure: checker/trust anchor modified or invalid")

    n_after = len(rho_next)
    if candidate.cost_record.get("dense_matrix_bound_units", -1) < n_after ** 3:
        reasons.append("cost_failure: dense bound underestimates declared cost")
    if candidate.cost_record.get("diagonal_table_bound_units", -1) < n_after:
        reasons.append("cost_failure: diagonal bound underestimates declared cost")

    return (len(reasons) == 0, reasons)


def pcs_from_accepted(mode: str, candidate: Candidate) -> Dict[str, Any]:
    """Convert accepted internal candidate into final artifact PCS schema."""
    if mode == "rcp":
        return {
            "t": candidate.t,
            "update": candidate.update,
            "phi": "append_alpha_1",
            "recovery": "trace_last_qubit",
            "checker_result": 1,
            "residuals": candidate.residuals,
            "goal_identity_drift": candidate.goal_identity_drift,
            "reality_containment": candidate.reality_containment,
            "cost": {
                "checker_steps": candidate.cost_record.get("checker_steps", 18),
                "residual_checks": len(RESIDUAL_KEYS),
            },
            "closed_loop_trace": {
                "selected_by_closed_loop_verification": True,
                "candidate_kind": candidate.kind,
                "candidate_hash": sha256_obj(asdict(candidate)),
                "trust_anchor_valid": candidate.trust_anchor_valid,
                "proof_trace": candidate.proof_trace,
            },
        }
    return {
        "t": candidate.t,
        "candidate": candidate.update,
        "transition": "X -> X tensor alpha_t where alpha_t is deterministic |1><1|",
        "transition_kind": "canonical_append_only_non_noop",
        "proof_carrying_packet_kind": "RCLM-closed-loop-certified-PCS",
        "checker_result": 1,
        "explicit_rclm_sv_residuals": candidate.residuals,
        "goal_identity_drift": candidate.goal_identity_drift,
        "reality_containment": {
            "contained": candidate.reality_containment["contained"],
            "kind": candidate.reality_containment["envelope"],
            "beta_env": candidate.reality_containment["beta_env"],
            "epsilon_env": candidate.reality_containment["epsilon_env"],
        },
        "trust": "immutable_predecessor_checker_anchor_not_modified",
        "recovery": "partial_trace_last_appended_register",
        "old_abilities": candidate.old_abilities,
        "new_abilities": candidate.new_abilities,
        "new_ability": f"a{candidate.t + 1}",
        "relative_entropy_before": rel_entropy_base2(candidate.rho_after if False else recover_last_qubit(candidate.rho_after), recover_last_qubit(candidate.sigma_after)),
        "relative_entropy_after": rel_entropy_base2(candidate.rho_after, candidate.sigma_after),
        "rho_before": recover_last_qubit(candidate.rho_after),
        "rho_after": candidate.rho_after,
        "sigma_before": recover_last_qubit(candidate.sigma_after),
        "sigma_after": candidate.sigma_after,
        "cost_record": {
            "dense_matrix_bound_units": candidate.cost_record["dense_matrix_bound_units"],
            "diagonal_table_bound_units": candidate.cost_record["diagonal_table_bound_units"],
        },
        "closed_loop_trace": {
            "selected_by_closed_loop_verification": True,
            "candidate_kind": candidate.kind,
            "candidate_hash": sha256_obj(asdict(candidate)),
            "trust_anchor_valid": candidate.trust_anchor_valid,
            "proof_trace": candidate.proof_trace,
        },
    }


def candidate_grammar(include_extra_invalid: bool = True) -> List[str]:
    base = [
        "wrong_dimension_append",
        "noop_no_ability_expansion",
        "residual_positive",
        "recovery_breaking",
        "bad_goal_transport",
        "bad_trust_anchor",
        "bad_cost_bound",
        "bad_reality_containment",
        "valid_append_mem",
    ]
    if include_extra_invalid:
        return base
    return ["noop_no_ability_expansion", "residual_positive", "valid_append_mem"]


def run_closed_loop(mode: str, N: int, seed: int = 0) -> Dict[str, Any]:
    if mode not in {"rcp", "rclm"}:
        raise ValueError("mode must be 'rcp' or 'rclm'")
    if N < 2:
        raise ValueError("closed-loop controlled reference run requires N >= 2")

    rng = random.Random(seed)
    rho_states: List[List[float]] = [RHO0]
    sigma_states: List[List[float]] = [SIGMA0]
    abilities: List[List[str]] = [ability_set(0)]
    pcs: List[Dict[str, Any]] = []
    accepted_log: List[Dict[str, Any]] = []
    rejected_log: List[Dict[str, Any]] = []
    step_summaries: List[Dict[str, Any]] = []
    D0 = rel_entropy_base2(RHO0, SIGMA0)

    for t in range(N):
        rho_t = rho_states[-1]
        sigma_t = sigma_states[-1]
        ab_t = abilities[-1]
        kinds = candidate_grammar(include_extra_invalid=True)
        # Deterministic but seed-aware order: invalids are shuffled, valid candidate remains present.
        invalid = [k for k in kinds if k != "valid_append_mem"]
        rng.shuffle(invalid)
        ordered_kinds = invalid + ["valid_append_mem"]

        step_candidates: List[Dict[str, Any]] = []
        accepted_candidate: Optional[Candidate] = None

        for kind in ordered_kinds:
            cand = build_candidate(mode=mode, t=t, kind=kind, rho_t=rho_t, sigma_t=sigma_t, ab_t=ab_t)
            ok, reasons = verify_candidate(
                mode=mode,
                candidate=cand,
                rho_t=rho_t,
                sigma_t=sigma_t,
                abilities_t=ab_t,
                base_relative_entropy=D0,
            )
            log_entry = candidate_to_log_dict(cand, accepted=ok, reasons=[] if ok else reasons)
            step_candidates.append(log_entry)
            if ok and accepted_candidate is None:
                accepted_candidate = cand
                # Continue evaluating all candidates for rejection evidence, but select the first passing candidate.

        if accepted_candidate is None:
            raise RuntimeError(f"closed loop failed: no accepted candidate at t={t}")

        rho_states.append(accepted_candidate.rho_after)
        sigma_states.append(accepted_candidate.sigma_after)
        abilities.append(accepted_candidate.new_abilities)
        pcs.append(pcs_from_accepted(mode, accepted_candidate))

        for entry in step_candidates:
            if entry["accepted"]:
                # Only the selected first passing candidate is accepted. Any later passing candidate would be recorded as non-selected.
                if entry["candidate_hash"] == sha256_obj(asdict(accepted_candidate)):
                    accepted_log.append(entry)
                else:
                    entry = dict(entry)
                    entry["accepted"] = False
                    entry["rejection_reasons"] = ["not_selected: a prior valid candidate was accepted"]
                    rejected_log.append(entry)
            else:
                rejected_log.append(entry)

        step_summaries.append(
            {
                "t": t,
                "candidates_generated": len(step_candidates),
                "accepted_update": accepted_candidate.update,
                "accepted_candidate_hash": sha256_obj(asdict(accepted_candidate)),
                "rejected_count": len([x for x in step_candidates if not x["accepted"]]),
                "successor_dimension": len(accepted_candidate.rho_after),
                "new_ability": f"a{t + 1}",
            }
        )

    final_dim = len(rho_states[-1])
    common_status = {
        "mode": mode,
        "N": N,
        "seed": seed,
        "loop_type": "closed_loop_certified_successor_generation",
        "generated_candidates": len(accepted_log) + len(rejected_log),
        "accepted_candidates": len(accepted_log),
        "rejected_candidates": len(rejected_log),
        "all_accepted_steps_checked": len(accepted_log) == N,
        "all_residuals_nonpositive": True,
        "strict_ability_expansion_each_step": True,
        "non_loss_recovery_preserved_each_step": True,
        "goal_identity_drift": 0.0,
        "singleton_reality_containment": True,
        "final_dimension": final_dim,
        "closed_loop_candidate_search": True,
        "static_predeclared_json_path": False,
    }

    if mode == "rcp":
        artifact: Dict[str, Any] = {
            "artifact_type": "RCP-Batch13R-B-controlled-canonical-reference-artifact",
            "generator": "closed_loop_certified_successor_generator_v1",
            "description": (
                "Closed-loop canonical RCP reference artifact. Successors are selected by a finite "
                "candidate-generation/check/accept-reject loop, not prewritten as a static JSON trajectory."
            ),
            "horizon_N": N,
            "states": {"rho": rho_states, "sigma": sigma_states},
            "abilities": abilities,
            "updates": [entry["update"] for entry in accepted_log],
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
            "closed_loop_generation_status": common_status,
        }
    else:
        artifact = {
            "artifact_type": "RCLM-Batch13R-B-controlled-executable-reference-system",
            "generator": "closed_loop_certified_successor_generator_v1",
            "description": (
                "Closed-loop canonical RCLM reference artifact. Successors are selected by a finite "
                "candidate-generation/check/accept-reject loop, not prewritten as a static JSON trajectory."
            ),
            "horizon_N": N,
            "states": {"rho": rho_states, "sigma": sigma_states},
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
            "closed_loop_generation_status": common_status,
        }

    # Keep the legacy artifact hash_manifest exactly compatible with the existing
    # RCP/RCLM checker.py scripts. Closed-loop-specific hashes are written to
    # hashes.json rather than added here, because the RCLM checker asserts the
    # exact expected manifest shape.
    artifact["hash_manifest"] = {
        "states_sha256": sha256_obj(artifact["states"]),
        "abilities_sha256": sha256_obj(artifact["abilities"]),
        "pcs_sha256": sha256_obj(artifact["pcs"]),
        "artifact_without_hash_manifest_sha256": sha256_obj({k: v for k, v in artifact.items() if k != "hash_manifest"}),
    }

    runlog = {
        **common_status,
        "ok": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "trajectory_hash": sha256_obj({"rho": rho_states, "sigma": sigma_states, "abilities": abilities, "pcs": pcs}),
        "artifact_hash": sha256_obj(artifact),
        "step_summaries": step_summaries,
        "claim_boundary": {
            "finite_closed_loop_certified_reference_instance": True,
            "full_autonomous_rsi": False,
            "broad_learned_agent_entry": False,
            "empirical_deployment_validation": False,
        },
    }

    hashes = {
        "artifact_sha256": sha256_obj(artifact),
        "accepted_trajectory_sha256": sha256_obj(accepted_log),
        "rejected_candidates_sha256": sha256_obj(rejected_log),
        "runlog_sha256": sha256_obj(runlog),
        "states_sha256": sha256_obj(artifact["states"]),
        "pcs_sha256": sha256_obj(artifact["pcs"]),
    }

    return {
        "artifact": artifact,
        "accepted_trajectory": accepted_log,
        "rejected_candidates": rejected_log,
        "runlog": runlog,
        "hashes": hashes,
    }


def write_run_bundle(result: Dict[str, Any], run_dir: Path) -> Dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "generated_artifact": run_dir / "generated_artifact.json",
        "accepted_trajectory": run_dir / "accepted_trajectory.json",
        "rejected_candidates": run_dir / "rejected_candidates.json",
        "closed_loop_runlog": run_dir / "closed_loop_runlog.json",
        "hashes": run_dir / "hashes.json",
    }
    write_json(paths["generated_artifact"], result["artifact"])
    write_json(paths["accepted_trajectory"], result["accepted_trajectory"])
    write_json(paths["rejected_candidates"], result["rejected_candidates"])
    write_json(paths["closed_loop_runlog"], result["runlog"])
    write_json(paths["hashes"], result["hashes"])
    return {key: str(value) for key, value in paths.items()}


def default_run_dir(mode: str, N: int, seed: int) -> Path:
    return Path("artifacts") / "closed_loop_runs" / f"{mode}_N{N}_seed{seed}"


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Closed-loop certified successor synthesis reference engine.")
    parser.add_argument("--mode", choices=["rcp", "rclm"], required=True)
    parser.add_argument("--N", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    run_dir = args.run_dir if args.run_dir is not None else default_run_dir(args.mode, args.N, args.seed)
    result = run_closed_loop(args.mode, args.N, args.seed)
    paths = write_run_bundle(result, run_dir)
    summary = {
        **result["runlog"],
        "paths": paths,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
