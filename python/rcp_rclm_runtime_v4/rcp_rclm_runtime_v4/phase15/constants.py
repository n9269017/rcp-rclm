from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, Literal, cast

from rcp_rclm_runtime.errors import SchemaValidationError

PHASE15_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v4-phase-15-v1"
PHASE15_TRAJECTORY_ID: Final[str] = "phase15-dynamic-hidden-m8-m9-v1"
PHASE15_OBJECTIVE_ID: Final[str] = "expand_dynamic_multidomain_frontier"
PHASE15_EXPECTED_M8_SEMANTIC_PACKAGE_HASH: Final[str] = (
    "8b47fc42da83fc75abfd74f755c3f2b609b023bae229f5f947ab499267d34310"
)
PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH: Final[str] = (
    "401568424e0b9cae8e7b6c0806c201ec484eb66d718d4894f1e51fbf66f4f5dc"
)
PHASE15_EXPECTED_PHASE14_TRAJECTORY_HASH: Final[str] = (
    "04f3e842cd89283a07bc93dc5f34978731b18541fce2d29ef48f3b3a6160b02c"
)
PHASE15_EXPECTED_PHASE14_FINAL_STORE_HASH: Final[str] = (
    "8c7977e7450e2efc946ed59b5c1efad6be4671a1bbf7e60314e517d36804f72f"
)

PHASE15_DECODER_VOCAB_SIZE: Final[int] = 32
PHASE15_DECODER_FEATURE_DIMENSION: Final[int] = 1024
PHASE15_DECODER_PARAMETER_COUNT: Final[int] = (
    PHASE15_DECODER_VOCAB_SIZE * PHASE15_DECODER_FEATURE_DIMENSION
)
PHASE15_MAX_PLAN_TOKENS: Final[int] = 16
PHASE15_TRAINING_EPOCHS: Final[int] = 24
PHASE15_MAX_ABS_PARAMETER: Final[int] = 8
PHASE15_EXHAUSTIVE_MIN_X: Final[int] = -16
PHASE15_EXHAUSTIVE_MAX_X: Final[int] = 16
PHASE15_EXTERNAL_CHALLENGE_SEED: Final[str] = (
    "RCP-RCLM-PHASE15-DYNAMIC-HIDDEN-CHALLENGE-SEED-v1"
)

TaskDomain = Literal["lean_multistep", "integer_program"]
CandidateVariant = Literal["lean_only", "multidomain"]

TASK_DOMAINS: Final[Sequence[TaskDomain]] = (
    "integer_program",
    "lean_multistep",
)
CANDIDATE_VARIANTS: Final[Sequence[CandidateVariant]] = (
    "lean_only",
    "multidomain",
)

TOKEN_BY_NAME: Final[Mapping[str, int]] = {
    "BOS": 0,
    "EOS": 1,
    "LEAN_BEGIN": 2,
    "LEAN_HAVE": 3,
    "LEAN_OMEGA": 4,
    "LEAN_EXACT": 5,
    "PROGRAM_BEGIN": 6,
    "PROGRAM_MUL": 7,
    "PROGRAM_ADD": 8,
    "PROGRAM_RETURN": 9,
    "SEPARATOR": 10,
    "RESERVED_11": 11,
    "INT_NEG8": 12,
    "INT_NEG7": 13,
    "INT_NEG6": 14,
    "INT_NEG5": 15,
    "INT_NEG4": 16,
    "INT_NEG3": 17,
    "INT_NEG2": 18,
    "INT_NEG1": 19,
    "INT_0": 20,
    "INT_1": 21,
    "INT_2": 22,
    "INT_3": 23,
    "INT_4": 24,
    "INT_5": 25,
    "INT_6": 26,
    "INT_7": 27,
    "INT_8": 28,
    "RESERVED_29": 29,
    "RESERVED_30": 30,
    "ERROR": 31,
}
NAME_BY_TOKEN: Final[Mapping[int, str]] = {
    token: name for name, token in TOKEN_BY_NAME.items()
}

PHASE15_COMPONENT_PATHS: Final[Mapping[str, str]] = {
    "training_policy": "training/training_policy.json",
    "optimizer_policy": "training/optimizer_state.json",
    "data_curriculum": "training/data_curriculum.json",
    "generator_policy": "policies/generator_policy.json",
    "planner_policy": "policies/planner_policy.json",
    "tool_policy": "policies/tool_policy.json",
    "verification_policy": "policies/verification_policy.json",
    "self_model": "self_model/manifest.json",
}

PHASE15_UPDATE_KIND_BY_TARGET: Final[Mapping[str, str]] = {
    "training_policy": "training_policy_update",
    "optimizer_policy": "optimizer_policy_update",
    "data_curriculum": "data_curriculum_update",
    "generator_policy": "generator_update",
    "planner_policy": "planner_update",
    "tool_policy": "tool_policy_update",
    "verification_policy": "verification_policy_update",
    "self_model": "self_model_update",
}

PHASE15_PHASE6_PROJECTIONS: Final[Mapping[str, tuple[str, str]]] = {
    "policies/code_generation_policy.json": (
        "code_generation_policy",
        "policies/generator_policy.json",
    ),
    "policies/planning_policy.json": (
        "planning_policy",
        "policies/planner_policy.json",
    ),
    "policies/tool_policy.json": (
        "tool_policy",
        "policies/tool_policy.json",
    ),
    "policies/training_policy.json": (
        "training_policy",
        "training/training_policy.json",
    ),
    "policies/verification_policy.json": (
        "verification_policy",
        "policies/verification_policy.json",
    ),
}

PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS: Final[Sequence[str]] = (
    "recursive.bind_post_freeze_dynamic_challenge",
    "recursive.generate_multi_token_plan",
    "recursive.invoke_package_bound_tool",
)


def cast_task_domain(value: str, path: str = "phase15.task_domain") -> TaskDomain:
    if value not in TASK_DOMAINS:
        raise SchemaValidationError(path, f"unsupported task domain: {value}")
    return cast(TaskDomain, value)


def cast_candidate_variant(
    value: str,
    path: str = "phase15.candidate_variant",
) -> CandidateVariant:
    if value not in CANDIDATE_VARIANTS:
        raise SchemaValidationError(path, f"unsupported candidate variant: {value}")
    return cast(CandidateVariant, value)


def integer_token(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError("phase15.integer_token", "expected integer")
    if value < -PHASE15_MAX_ABS_PARAMETER or value > PHASE15_MAX_ABS_PARAMETER:
        raise SchemaValidationError(
            "phase15.integer_token",
            "integer is outside selected token range",
        )
    return TOKEN_BY_NAME[f"INT_{value}" if value >= 0 else f"INT_NEG{abs(value)}"]


def token_integer(token: int) -> int:
    if isinstance(token, bool) or not isinstance(token, int):
        raise SchemaValidationError("phase15.token_integer", "expected token integer")
    name = NAME_BY_TOKEN.get(token, "")
    if not name.startswith("INT_"):
        raise SchemaValidationError("phase15.token_integer", "token is not an integer token")
    suffix = name[4:]
    if suffix.startswith("NEG"):
        return -int(suffix[3:])
    return int(suffix)


__all__ = [
    "CANDIDATE_VARIANTS",
    "NAME_BY_TOKEN",
    "PHASE15_COMPONENT_PATHS",
    "PHASE15_CONTRACT_VERSION",
    "PHASE15_DECODER_FEATURE_DIMENSION",
    "PHASE15_DECODER_PARAMETER_COUNT",
    "PHASE15_DECODER_VOCAB_SIZE",
    "PHASE15_EXHAUSTIVE_MAX_X",
    "PHASE15_EXHAUSTIVE_MIN_X",
    "PHASE15_EXPECTED_M8_SEMANTIC_PACKAGE_HASH",
    "PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH",
    "PHASE15_EXPECTED_PHASE14_FINAL_STORE_HASH",
    "PHASE15_EXPECTED_PHASE14_TRAJECTORY_HASH",
    "PHASE15_EXTERNAL_CHALLENGE_SEED",
    "PHASE15_MAX_ABS_PARAMETER",
    "PHASE15_MAX_PLAN_TOKENS",
    "PHASE15_OBJECTIVE_ID",
    "PHASE15_PHASE6_PROJECTIONS",
    "PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS",
    "PHASE15_TRAINING_EPOCHS",
    "PHASE15_TRAJECTORY_ID",
    "PHASE15_UPDATE_KIND_BY_TARGET",
    "TASK_DOMAINS",
    "TOKEN_BY_NAME",
    "CandidateVariant",
    "TaskDomain",
    "cast_candidate_variant",
    "cast_task_domain",
    "integer_token",
    "token_integer",
]
