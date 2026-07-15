from __future__ import annotations

from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.promotion.records import (
    Phase7ControllerBudgetRecord,
    Phase7ControllerPolicyRecord,
)
from rcp_rclm_runtime.successor.reference import reference_phase6_budget

PHASE7_CONTROLLER_POLICY_ID: Final[str] = (
    "rcp-rclm-phase7-finite-reference-promotion-controller-v1"
)
PHASE7_CONTROLLER_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.phase7_controller_environment_policy.v2",
        "policy_id": PHASE7_CONTROLLER_POLICY_ID,
        "network": "disabled",
        "model": "absent",
        "manual_repair": "forbidden",
        "candidate_mutation": "forbidden",
        "active_pointer_update": "atomic_replace",
        "generator_process": "phase5a_isolated_stdio",
        "promotion_limit_per_run": 1,
    }
)


def reference_phase7_policy() -> Phase7ControllerPolicyRecord:
    return Phase7ControllerPolicyRecord(
        policy_id=PHASE7_CONTROLLER_POLICY_ID,
        scope="gate_b_classical_reference",
        generator_backend="phase5a_reference_process",
        selector_backend="phase6_reference_selector",
        realizer_backend="phase6_isolated_realizer",
        evaluator_backend="phase3_reference_evaluator",
        checker_backend="phase4_hardened_checker",
        require_two_run_generator_replay=True,
        require_public_package_verification=True,
        require_lean_acceptance=True,
        require_checker_acceptance=True,
        allow_manual_repair=False,
        allow_candidate_mutation=False,
    )


def reference_phase7_budget() -> Phase7ControllerBudgetRecord:
    return Phase7ControllerBudgetRecord(
        max_attempts=2,
        max_attempt_units=2,
        attempt_unit_cost=1,
        max_promotions=1,
        phase6_budget=reference_phase6_budget(),
    )


def phase7_run_id(
    *,
    run_label: str,
    active_pointer_hash: str,
    policy_hash: str,
    budget_hash: str,
) -> str:
    digest = canonical_json_hash(
        {
            "schema_id": "runtime.phase7_run_identity.v2",
            "run_label": run_label,
            "active_pointer_hash": active_pointer_hash,
            "policy_hash": policy_hash,
            "budget_hash": budget_hash,
        }
    )
    return f"phase7.{digest[:40]}"
