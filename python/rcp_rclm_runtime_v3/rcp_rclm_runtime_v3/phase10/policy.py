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
PHASE10_TRANSPORT_PROFILE: Final[str] = (
    "runtime_v2_pytorch_profile_reused_as_immutable_transport_only"
)
PHASE10_CONTROLLER_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase10.controller_environment.v1",
        "policy_id": PHASE10_CONTROLLER_POLICY_ID,
        "transport_profile": PHASE10_TRANSPORT_PROFILE,
        "network": "disabled",
        "gpu_training_authority": False,
        "manual_repair": "forbidden",
        "candidate_mutation": "forbidden",
        "training_process": "isolated_untrusted_subprocess",
        "model_evaluator": "framework_independent_exact_integer",
        "task_verifier": "pinned_lean_theorem_verifier_v1",
        "lean_bridge": "pinned_gate_b_reference_stability",
        "outer_checker": "phase4_hardened_plus_gate_d_phase9",
        "transport_profile_authorizes_gate_d": False,
    }
)


def phase10_phase7_policy() -> Phase7ControllerPolicyRecord:
    """Return the unchanged reviewed Runtime v2 transport profile.

    The immutable Phase 7 store validates one of its two reviewed profiles. Phase 10
    therefore reuses the PyTorch learned-successor profile only for realization,
    content addressing, ledger construction, and pointer replacement. The Phase 10
    task-frontier, Lean, information, and Gate D authority remains in the separately
    hashed verification and attempt evidence consumed before this transport step.
    """

    return Phase7ControllerPolicyRecord(
        policy_id=PHASE10_CONTROLLER_POLICY_ID,
        scope="pytorch_pilot_gate_b_stable",
        generator_backend="pytorch_pilot_process",
        selector_backend="pytorch_pilot_host_selector",
        realizer_backend="phase6_isolated_realizer",
        evaluator_backend="pytorch_pilot_exact_integer_evaluator",
        checker_backend="phase4_hardened_checker",
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
    "PHASE10_TRANSPORT_PROFILE",
    "phase10_phase7_budget",
    "phase10_phase7_policy",
]
