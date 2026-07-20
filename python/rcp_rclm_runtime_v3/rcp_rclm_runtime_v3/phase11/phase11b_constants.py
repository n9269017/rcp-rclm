from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase11.constants import (
    FROZEN_AUTHORITIES,
    PHASE11_ARCHITECTURE_MUTATION,
    PHASE11_OBJECTIVE,
    PHASE11_PROGRAM_VERSION,
    PHASE11_ROLLBACK_MODE,
)

PHASE11B_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-11b"
PHASE11B_GENERATOR_PROFILE: Final[str] = "position_addressed_typed_mutation_v2"
PHASE11B_ACTIVE_PACKAGE_ID: Final[str] = "phase11b-active-predecessor"
PHASE11B_REJECTED_CANDIDATE_ID: Final[str] = "phase11b-candidate-alpha-rejected"
PHASE11B_PROMOTED_CANDIDATE_ID: Final[str] = "phase11b-candidate-beta-promoted"
PHASE11B_DATA_SELECTION_ALPHA: Final[str] = "training_partition_alpha"
PHASE11B_DATA_SELECTION_BETA: Final[str] = "training_partition_beta"
PHASE11B_NEW_TASK_ID: Final[str] = "lean.phase11.heldout.add_zero_macro"
PHASE11B_NEW_MARKER: Final[int] = ord("S")
PHASE11B_NEW_COMPLETION: Final[bytes] = b"z"

INVALID_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=V;D=A;A=N;R=1,0,2,96,1,1;E=V;B=X;G=1;P=1"
)
ALPHA_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=WLGP;D=A;A=N;R=1,0,1,96,1,1;E=WLGP;B=X;G=2;P=2"
)
BETA_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=WLCGP;D=A;A=N;R=1,0,1,96,1,1;E=WLCGP;B=X;G=2;P=2"
)
INVALID_PROGRAM_BYTES: Final[bytes] = INVALID_PROGRAM_TEXT.encode("ascii")
ALPHA_PROGRAM_BYTES: Final[bytes] = ALPHA_PROGRAM_TEXT.encode("ascii")
BETA_PROGRAM_BYTES: Final[bytes] = BETA_PROGRAM_TEXT.encode("ascii")

INVALID_BANK_START: Final[int] = 0
ALPHA_BANK_START: Final[int] = 128
BETA_BANK_START: Final[int] = 192
BANK_CAPACITY: Final[int] = 64

PROGRAM_BY_INVOCATION: Final[Mapping[int, bytes]] = {
    0: INVALID_PROGRAM_BYTES,
    1: ALPHA_PROGRAM_BYTES,
    2: BETA_PROGRAM_BYTES,
}
BANK_START_BY_INVOCATION: Final[Mapping[int, int]] = {
    0: INVALID_BANK_START,
    1: ALPHA_BANK_START,
    2: BETA_BANK_START,
}

PHASE11B_PROPOSAL_PROTOCOL: Final[dict[str, object]] = {
    "schema_id": "runtime.v3.phase11b.proposal_protocol.v1",
    "program_version": PHASE11_PROGRAM_VERSION,
    "generator_profile": PHASE11B_GENERATOR_PROFILE,
    "field_order": ["O", "U", "D", "A", "R", "E", "B", "G", "P"],
    "state_schedule": "three_disjoint_position_addressed_banks",
    "termination": "eos_token",
    "candidate_direct_write": False,
    "heldout_material_permitted": False,
    "candidate_count": 2,
    "evaluation_call_count": 2,
    "invalid_proposal_precedes_candidates": True,
}
PHASE11B_PROPOSAL_PROTOCOL_HASH: Final[str] = canonical_json_hash(
    PHASE11B_PROPOSAL_PROTOCOL
)

UPDATE_CODE_TO_CLASS_V2: Final[Mapping[str, str]] = {
    "W": "weight_update",
    "L": "adapter_update",
    "C": "data_curriculum_update",
    "G": "generator_update",
    "P": "planner_update",
    "V": "verification_policy_update",
}
COMPONENT_CODE_TO_COMPONENT_V2: Final[Mapping[str, str]] = {
    "W": "model_weights",
    "L": "adapter_manifest",
    "C": "data_curriculum",
    "G": "generator_policy",
    "P": "planner_policy",
    "V": "verification_policy",
}
UPDATE_CLASS_TO_COMPONENT_V2: Final[Mapping[str, str]] = {
    value: COMPONENT_CODE_TO_COMPONENT_V2[key]
    for key, value in UPDATE_CODE_TO_CLASS_V2.items()
}
UPDATE_CODE_ORDER_V2: Final[Sequence[str]] = ("W", "L", "C", "G", "P", "V")
COMPONENT_CODE_ORDER_V2: Final[Sequence[str]] = ("W", "L", "C", "G", "P", "V")

ALLOWED_UPDATE_CLASSES_V2: Final[frozenset[str]] = frozenset(
    {
        "weight_update",
        "adapter_update",
        "data_curriculum_update",
        "generator_update",
        "planner_update",
    }
)
FORBIDDEN_UPDATE_CLASSES_V2: Final[frozenset[str]] = frozenset(
    {"tokenizer_update", "verification_policy_update"}
)

ACTIVE_GENERATOR_GENERATION: Final[int] = 1
ACTIVE_PLANNER_GENERATION: Final[int] = 1
SUCCESSOR_GENERATOR_GENERATION: Final[int] = 2
SUCCESSOR_PLANNER_GENERATION: Final[int] = 2

PHASE11B_FROZEN_AUTHORITIES: Final[Sequence[str]] = tuple(FROZEN_AUTHORITIES)
PHASE11B_ARCHITECTURE_MUTATION: Final[str] = PHASE11_ARCHITECTURE_MUTATION
PHASE11B_ROLLBACK_MODE: Final[str] = PHASE11_ROLLBACK_MODE
PHASE11B_OBJECTIVE: Final[str] = PHASE11_OBJECTIVE

__all__ = [name for name in globals() if name.isupper()]
