from __future__ import annotations

from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

PHASE11_SLICE_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-11a"
PHASE11_PROGRAM_VERSION: Final[str] = "V1"
PHASE11_GENERATOR_PROFILE: Final[str] = "position_addressed_typed_mutation_v1"
PHASE11_OBJECTIVE: Final[str] = "expand_certified_frontier"
PHASE11_DATA_SELECTION: Final[str] = "training_partition_alpha"
PHASE11_ARCHITECTURE_MUTATION: Final[str] = "none"
PHASE11_ROLLBACK_MODE: Final[str] = "exact_predecessor_restore"
PHASE11_BOOTSTRAP_PACKAGE_ID: Final[str] = "phase11-bootstrap-active-predecessor"

REJECTED_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=V;D=A;A=N;R=1,0,2,96,1,1;E=V;B=X;G=1;P=1"
)
ACCEPTED_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=WGP;D=A;A=N;R=1,0,1,96,1,1;E=WGP;B=X;G=2;P=2"
)
REJECTED_PROGRAM_BYTES: Final[bytes] = REJECTED_PROGRAM_TEXT.encode("ascii")
ACCEPTED_PROGRAM_BYTES: Final[bytes] = ACCEPTED_PROGRAM_TEXT.encode("ascii")

REJECTED_BANK_START: Final[int] = 0
REJECTED_BANK_CAPACITY: Final[int] = 64
ACCEPTED_BANK_START: Final[int] = 128
ACCEPTED_BANK_CAPACITY: Final[int] = 128

PROPOSAL_PROTOCOL: Final[dict[str, object]] = {
    "schema_id": "runtime.v3.phase11.proposal_protocol.v1",
    "program_version": PHASE11_PROGRAM_VERSION,
    "generator_profile": PHASE11_GENERATOR_PROFILE,
    "field_order": ["O", "U", "D", "A", "R", "E", "B", "G", "P"],
    "state_schedule": "bank_start_plus_output_position",
    "termination": "eos_token",
    "candidate_direct_write": False,
    "heldout_material_permitted": False,
}
PROPOSAL_PROTOCOL_HASH: Final[str] = canonical_json_hash(PROPOSAL_PROTOCOL)

FROZEN_AUTHORITIES: Final[tuple[str, ...]] = (
    "active_ledger_history",
    "canonical_serializer",
    "hardened_checker",
    "heldout_answer_store",
    "package_hashing",
    "pinned_lean_project",
    "promotion_authority",
    "root_trust_anchor",
)

ALLOWED_UPDATE_CLASSES: Final[tuple[str, ...]] = (
    "architecture_extension",
    "data_curriculum_update",
    "generator_update",
    "memory_update",
    "optimizer_policy_update",
    "planner_update",
    "resource_policy_update",
    "retrieval_update",
    "self_model_update",
    "tool_policy_update",
    "training_policy_update",
    "weight_update",
)

FORBIDDEN_UPDATE_CLASSES: Final[tuple[str, ...]] = (
    "tokenizer_update",
    "verification_policy_update",
)

UPDATE_CODE_TO_CLASS: Final[dict[str, str]] = {
    "G": "generator_update",
    "P": "planner_update",
    "V": "verification_policy_update",
    "W": "weight_update",
}
UPDATE_CLASS_TO_COMPONENT: Final[dict[str, str]] = {
    "generator_update": "generator_policy",
    "planner_update": "planner_policy",
    "verification_policy_update": "verification_policy",
    "weight_update": "model_weights",
}
COMPONENT_CODE_TO_COMPONENT: Final[dict[str, str]] = {
    "G": "generator_policy",
    "P": "planner_policy",
    "V": "verification_policy",
    "W": "model_weights",
}

ACTIVE_GENERATOR_GENERATION: Final[int] = 1
ACTIVE_PLANNER_GENERATION: Final[int] = 1
