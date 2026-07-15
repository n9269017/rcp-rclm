from __future__ import annotations

from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.promotion.record_policy import (
    Phase7ControllerBudgetRecord,
    Phase7ControllerPolicyRecord,
)
from rcp_rclm_runtime.successor.record_budget import Phase6ResourceBudgetRecord

PYTORCH_PILOT_CONTROLLER_POLICY_ID: Final[str] = (
    "rcp-rclm-pytorch-pilot-controller-v1"
)
PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.pytorch_pilot_controller_environment.v1",
        "policy_id": PYTORCH_PILOT_CONTROLLER_POLICY_ID,
        "network": "disabled",
        "gpu": "disabled",
        "manual_repair": "forbidden",
        "candidate_mutation": "forbidden",
        "training_process": "isolated_cpu_subprocess",
        "model_evaluator": "framework_independent_exact_integer",
        "lean": "pinned_reference_stability",
        "checker": "phase4_hardened_checker",
    }
)


def pytorch_pilot_phase7_policy() -> Phase7ControllerPolicyRecord:
    return Phase7ControllerPolicyRecord(
        policy_id=PYTORCH_PILOT_CONTROLLER_POLICY_ID,
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


def pytorch_pilot_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=128,
        max_total_bytes=2_097_152,
        max_changed_files=16,
        max_written_bytes=8_388_608,
        max_commands=32,
        max_snapshot_bytes=4_194_304,
    )


def pytorch_pilot_phase7_budget() -> Phase7ControllerBudgetRecord:
    return Phase7ControllerBudgetRecord(
        max_attempts=1,
        max_attempt_units=1,
        attempt_unit_cost=1,
        max_promotions=1,
        phase6_budget=pytorch_pilot_phase6_budget(),
    )


__all__ = [
    "PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH",
    "PYTORCH_PILOT_CONTROLLER_POLICY_ID",
    "pytorch_pilot_phase6_budget",
    "pytorch_pilot_phase7_budget",
    "pytorch_pilot_phase7_policy",
]
