from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    BETA_BANK_START,
    BETA_PROGRAM_BYTES,
)

PHASE12A_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-12a"
PHASE12_TRAJECTORY_ID: Final[str] = "phase12-self-hosted-four-promotion-trajectory-v1"
PHASE12_ACTIVE_GENERATOR_GENERATION: Final[int] = 2
PHASE12_ACTIVE_PLANNER_GENERATION: Final[int] = 2
PHASE12_REQUIRED_ACCEPTED_PROMOTIONS: Final[int] = 4
PHASE12_REQUIRED_REJECTED_ATTEMPTS: Final[int] = 2
PHASE12_INITIAL_FRONTIER_CARDINALITY: Final[int] = 3
PHASE12_TARGET_FRONTIER_CARDINALITY: Final[int] = 7
PHASE11_MERGE_COMMIT: Final[str] = "5af6f68bc43c32ae5477d303c443b7159698eeed"

PHASE12_RECURSIVE_BANK_START: Final[int] = BETA_BANK_START
PHASE12_RECURSIVE_BANK_CAPACITY: Final[int] = 64
PHASE12_EXPECTED_FIRST_PROGRAM_BYTES: Final[bytes] = BETA_PROGRAM_BYTES

PHASE12_COMPONENT_SCHEDULE: Final[Sequence[dict[str, object]]] = (
    {
        "transition_index": 0,
        "required_components": ["model_weights"],
        "description": "genuine model-weight update",
    },
    {
        "transition_index": 1,
        "required_components": ["memory_state", "retrieval_policy"],
        "description": "memory and retrieval policy update",
    },
    {
        "transition_index": 2,
        "required_components": ["generator_policy", "planner_policy"],
        "description": "generator and planner self-modification",
    },
    {
        "transition_index": 3,
        "required_components": [
            "adapter_manifest",
            "architecture_manifest",
            "optimizer_policy",
        ],
        "description": "typed architecture or adapter and optimizer modification",
    },
)

PHASE12_TOTAL_BUDGET: Final[dict[str, int]] = {
    "max_wall_clock_seconds": 24,
    "max_accelerator_count": 0,
    "max_training_steps": 4,
    "max_output_bytes": 576,
    "max_generator_invocations": 6,
    "max_candidate_realizations": 4,
    "max_candidate_evaluations": 4,
    "max_promotions": 4,
    "max_rejected_attempts": 2,
    "max_manual_repairs": 0,
}
PHASE12_TOTAL_BUDGET_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase12.trajectory_budget.v1",
        **PHASE12_TOTAL_BUDGET,
    }
)

PHASE12_PROPOSAL_PROTOCOL: Final[dict[str, object]] = {
    "schema_id": "runtime.v3.phase12.recursive_proposal_protocol.v1",
    "trajectory_id": PHASE12_TRAJECTORY_ID,
    "typed_program_version": "V1",
    "authoritative_source": "active_package_generator_and_planner",
    "initial_active_generator_generation": PHASE12_ACTIVE_GENERATOR_GENERATION,
    "initial_active_planner_generation": PHASE12_ACTIVE_PLANNER_GENERATION,
    "candidate_direct_write": False,
    "heldout_material_permitted": False,
    "manual_repair_permitted": False,
    "required_accepted_promotions": PHASE12_REQUIRED_ACCEPTED_PROMOTIONS,
    "required_rejected_attempts": PHASE12_REQUIRED_REJECTED_ATTEMPTS,
    "component_schedule": list(PHASE12_COMPONENT_SCHEDULE),
    "total_budget_hash": PHASE12_TOTAL_BUDGET_HASH,
}
PHASE12_PROPOSAL_PROTOCOL_HASH: Final[str] = canonical_json_hash(
    PHASE12_PROPOSAL_PROTOCOL
)

__all__ = [name for name in globals() if name.isupper()]
