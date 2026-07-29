from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal, cast

from rcp_rclm_runtime.errors import SchemaValidationError

PHASE14_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v4-phase-14-v1"
PHASE14_TRAJECTORY_ID: Final[str] = "phase14-schedule-free-m4-successor-closure-v1"
PHASE14_OBJECTIVE_ID: Final[str] = "expand_certified_frontier_schedule_free"
PHASE14_MIN_PROMOTIONS: Final[int] = 4
PHASE14_MIN_UPDATE_FAMILIES: Final[int] = 3
PHASE14_MIN_REJECTIONS: Final[int] = 2
PHASE14_MAX_ATTEMPTS_PER_CHALLENGE: Final[int] = 4
PHASE14_SEARCH_COST_PER_ATTEMPT: Final[int] = 1
PHASE14_SLOT_START: Final[int] = 180
PHASE14_SLOT_COUNT: Final[int] = 64
PHASE14_ROUTE_MARKER: Final[int] = ord("W")
PHASE14_COMPLETION: Final[str] = "q"
PHASE14_PROBE_BIT_START: Final[int] = 8
PHASE14_PROBE_BIT_END: Final[int] = 16
PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH: Final[str] = (
    "e153216d08df0ce74e43864f9398e49930fbbf1d24220142e03ff6084b9126a1"
)
PHASE13_EXIT_REPORT_HASH: Final[str] = (
    "1967dad3254e7c62c33971929d6937b4e62722260719a2360162b27deaefb49f"
)
PHASE13_BUNDLE_MANIFEST_HASH: Final[str] = (
    "8fb457b08aaf587dd408b686ff66b0df7ea4079f74257c7fbc283bbf01e56da8"
)

UpdateFamily = Literal[
    "model_weights",
    "memory_retrieval",
    "generator_planner",
    "adapter_optimizer",
]

ProgramVariant = Literal["probe", "recover", "direct"]

UPDATE_FAMILIES: Final[Sequence[UpdateFamily]] = (
    "model_weights",
    "memory_retrieval",
    "generator_planner",
    "adapter_optimizer",
)

UPDATE_KINDS_BY_FAMILY: Final[dict[UpdateFamily, Sequence[str]]] = {
    "model_weights": ("weight_update",),
    "memory_retrieval": ("memory_update", "retrieval_update"),
    "generator_planner": ("generator_update", "planner_update"),
    "adapter_optimizer": (
        "adapter_update",
        "optimizer_policy_update",
    ),
}

CHANGED_COMPONENTS_BY_FAMILY: Final[dict[UpdateFamily, Sequence[str]]] = {
    "model_weights": ("model_weights",),
    "memory_retrieval": ("memory_state", "retrieval_policy"),
    "generator_planner": ("generator_policy", "planner_policy"),
    "adapter_optimizer": ("adapter_manifest", "optimizer_policy"),
}

PHASE6_COMPONENT_KINDS_BY_FAMILY: Final[dict[UpdateFamily, Sequence[str]]] = {
    "model_weights": ("model_weights",),
    "memory_retrieval": ("memory_policy", "retrieval_policy"),
    "generator_planner": ("code_generation_policy", "planning_policy"),
    "adapter_optimizer": ("architecture_code", "training_policy"),
}

FORBIDDEN_ROUTE_HINT_FIELDS: Final[Sequence[str]] = (
    "next_successful_transition_index",
    "required_successful_component_set",
    "accepted_program_bytes",
    "expected_candidate_hash",
    "expected_new_capability",
    "expected_final_model_identity",
    "host_selected_objective",
)


def cast_update_family(value: str, path: str = "phase14.update_family") -> UpdateFamily:
    if value not in UPDATE_FAMILIES:
        raise SchemaValidationError(path, f"unsupported update family: {value}")
    return cast(UpdateFamily, value)


def cast_program_variant(
    value: str,
    path: str = "phase14.program_variant",
) -> ProgramVariant:
    if value not in {"probe", "recover", "direct"}:
        raise SchemaValidationError(path, f"unsupported program variant: {value}")
    return cast(ProgramVariant, value)


def commitment_requires_probe(commitment_hash: str) -> bool:
    if len(commitment_hash) != 64 or any(
        character not in "0123456789abcdef"
        for character in commitment_hash
    ):
        raise SchemaValidationError(
            "phase14.challenge_commitment_hash",
            "expected lowercase SHA-256",
        )
    probe_word = commitment_hash[
        PHASE14_PROBE_BIT_START:PHASE14_PROBE_BIT_END
    ]
    return int(probe_word, 16) % 2 == 0


__all__ = [
    "CHANGED_COMPONENTS_BY_FAMILY",
    "FORBIDDEN_ROUTE_HINT_FIELDS",
    "PHASE13_BUNDLE_MANIFEST_HASH",
    "PHASE13_EXIT_REPORT_HASH",
    "PHASE14_COMPLETION",
    "PHASE14_CONTRACT_VERSION",
    "PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH",
    "PHASE14_MAX_ATTEMPTS_PER_CHALLENGE",
    "PHASE14_MIN_PROMOTIONS",
    "PHASE14_MIN_REJECTIONS",
    "PHASE14_MIN_UPDATE_FAMILIES",
    "PHASE14_OBJECTIVE_ID",
    "PHASE14_PROBE_BIT_END",
    "PHASE14_PROBE_BIT_START",
    "PHASE14_ROUTE_MARKER",
    "PHASE14_SEARCH_COST_PER_ATTEMPT",
    "PHASE14_SLOT_COUNT",
    "PHASE14_SLOT_START",
    "PHASE14_TRAJECTORY_ID",
    "PHASE6_COMPONENT_KINDS_BY_FAMILY",
    "UPDATE_FAMILIES",
    "UPDATE_KINDS_BY_FAMILY",
    "ProgramVariant",
    "UpdateFamily",
    "cast_program_variant",
    "cast_update_family",
    "commitment_requires_probe",
]
