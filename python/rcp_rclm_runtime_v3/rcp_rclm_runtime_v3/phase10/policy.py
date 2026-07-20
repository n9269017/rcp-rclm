from __future__ import annotations

from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.promotion.record_policy import (
    Phase7ControllerBudgetRecord,
    Phase7ControllerPolicyRecord,
)
from rcp_rclm_runtime_v3.phase10.lifecycle import phase10_phase6_budget

PHASE10_CONTROLLER_POLICY_ID: Final[str] = (
    "rcp-rclm-v3-phase10-learned-controller-v1"
)
PHASE10_CONTROLLER_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase10.controller_environment.v1",
        "policy_id": PHASE10_CONTROLLER_POLICY_ID,
        "network": "disabled",
        "gpu_training_authority": False,
        "manual_repair": "forbidden",
        "candidate_mutation": "forbidden",
        "training_process": "isolated_untrusted_subprocess",
        "model_evaluator": "framework_independent_exact_integer",
        "task_verifier": "pinned_lean_theorem_verifier_v1",
        "lean_bridge": "pinned_gate_b_reference_stability",
        "checker": "phase4_hardened_plus_gate_d_phase9",
    }
)


def phase10_phase7_policy() -> Phase7ControllerPolicyRecord:
    return Phase7ControllerPolicyRecord(
        policy_id=PHASE10_CONTROLLER_POLICY_ID,
        scope="phase10_learned_gate_d_frontier_expansion",
        generator_backend="phase10_isolated_untrusted_training_process",
        selector_backend="phase10_host_model_weight_selector",
        realizer_backend="phase6_isolated_realizer",
        evaluator_backend="phase10_exact_integer_lean_qre_evaluator",
        checker_backend="phase4_hardened_plus_gate_d_phase9",
        require_two_run_generator_replay=True,
        require_public_package_verification=True,
        require_lean_acceptance=True,
        require_checker_acceptance=True,
        allow_manual_repair=False,
        allow_candidate_mutation=False,
    )


def phase10_phase7_budget() -> Phase7ControllerBudgetRecord:
    return Phase7ControllerBudgetRecord(
        max_attempts=1,
        max_attempt_units=1,
        attempt_unit_cost=1,
        max_promotions=1,
        phase6_budget=phase10_phase6_budget(),
    )


__all__ = [
    "PHASE10_CONTROLLER_ENVIRONMENT_HASH",
    "PHASE10_CONTROLLER_POLICY_ID",
    "phase10_phase7_budget",
    "phase10_phase7_policy",
]
