#!/usr/bin/env python3
"""Replay checker for the Batch-13R-B controlled canonical RCP artifact.

This is an executable replay checker, not a Lean/Coq/Isabelle/Agda proof.
It verifies the finite canonical appended-module reference object encoded in JSON.
"""
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
from typing import Any, Dict, List

RESIDUAL_KEYS = [
    "seed", "cand", "ver", "trans", "goal", "unc", "trust", "budget",
    "persist", "world", "proof", "sound"
]


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def rel_entropy_base2(p: List[float], q: List[float]) -> float:
    total = 0.0
    for pi, qi in zip(p, q):
        if pi == 0:
            continue
        if qi == 0:
            raise AssertionError("relative entropy infinite: q has zero where p positive")
        total += pi * math.log(pi / qi, 2)
    return total


def append_alpha_1(probs: List[float]) -> List[float]:
    out: List[float] = []
    for p in probs:
        out.extend([0.0, p])
    return out


def recover_last_qubit(probs: List[float]) -> List[float]:
    if len(probs) % 2 != 0:
        raise AssertionError("state length not divisible by 2")
    return [probs[i] + probs[i + 1] for i in range(0, len(probs), 2)]


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(a - b) <= tol


def check_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    assert artifact.get("artifact_type") == "RCP-Batch13R-B-controlled-canonical-reference-artifact"
    N = int(artifact["horizon_N"])
    assert N >= 2, "controlled artifact requires N >= 2"
    rho_states = artifact["states"]["rho"]
    sigma_states = artifact["states"]["sigma"]
    assert len(rho_states) == N + 1 and len(sigma_states) == N + 1
    rho0 = [2 / 3, 1 / 3]
    sigma0 = [1 / 3, 2 / 3]
    assert all(close(a, b) for a, b in zip(rho_states[0], rho0))
    assert all(close(a, b) for a, b in zip(sigma_states[0], sigma0))

    d0 = rel_entropy_base2(rho_states[0], sigma_states[0])
    steps_checked = 0
    for t in range(N):
        rho_t = rho_states[t]
        sigma_t = sigma_states[t]
        rho_next = rho_states[t + 1]
        sigma_next = sigma_states[t + 1]
        assert rho_next == append_alpha_1(rho_t), f"rho append mismatch at t={t}"
        assert sigma_next == append_alpha_1(sigma_t), f"sigma append mismatch at t={t}"
        assert recover_last_qubit(rho_next) == rho_t, f"rho recovery mismatch at t={t}"
        assert recover_last_qubit(sigma_next) == sigma_t, f"sigma recovery mismatch at t={t}"
        assert close(rel_entropy_base2(rho_next, sigma_next), d0), f"relative entropy mismatch at t={t}"
        ab_t = artifact["abilities"][t]
        ab_next = artifact["abilities"][t + 1]
        assert set(ab_t).issubset(set(ab_next)), f"ability preservation failed at t={t}"
        assert f"a{t+1}" in set(ab_next) - set(ab_t), f"strict ability expansion failed at t={t}"
        pcs = artifact["pcs"][t]
        assert pcs["update"] == f"AppendMem(a{t+1})"
        assert pcs["checker_result"] == 1
        residuals = pcs["residuals"]
        for key in RESIDUAL_KEYS:
            assert key in residuals, f"missing residual {key} at t={t}"
            assert residuals[key] <= 0, f"positive residual {key} at t={t}: {residuals[key]}"
        assert pcs["goal_identity_drift"] == 0
        assert pcs["reality_containment"]["contained"] is True
        assert pcs["reality_containment"]["beta_env"] == 0
        assert pcs["reality_containment"]["epsilon_env"] == 0
        steps_checked += 1

    nN = len(rho_states[-1])
    dense_bound = artifact["tractability"]["dense_cost_bound"]
    diagonal_bound = artifact["tractability"]["diagonal_table_cost_bound"]
    assert dense_bound >= N * (nN ** 3)
    assert diagonal_bound >= N * nN
    return {
        "ok": True,
        "artifact_hash": sha256_obj(artifact),
        "N": N,
        "final_dimension": nN,
        "relative_entropy_base2": d0,
        "steps_checked": steps_checked,
        "explicit_residuals_checked": True,
        "non_noop_updates": True,
        "strict_ability_expansion": True,
        "singleton_reality_containment": True,
        "external_mechanization_certificate_supplied": bool(artifact.get("external_mechanization", {}).get("certificate_supplied")),
        "mechanization_status": artifact.get("external_mechanization", {}).get("status", "not_provided")
    }


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("rcp_batch13rB_controlled_artifact.json")
    artifact = json.loads(path.read_text())
    result = check_artifact(artifact)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
