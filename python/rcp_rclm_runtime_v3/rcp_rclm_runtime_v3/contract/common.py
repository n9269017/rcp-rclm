from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal, cast

from rcp_rclm_runtime.canonical.hashing import validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string

CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-9"
SELECTED_MODEL_FAMILY: Final[str] = "compact_decoder_only_transformer_v1"
SELECTED_TASK_CLASS: Final[str] = "lean_theorem_completion_v1"
SELECTED_VERIFIER_KIND: Final[str] = "pinned_lean_theorem_verifier_v1"
MAX_PARAMETER_COUNT: Final[int] = 50_000_000

STATE_SCHEMA_ID: Final[str] = "runtime.v3.phase9.learned_rclm_state.v1"
UPDATE_SCHEMA_ID: Final[str] = "runtime.v3.phase9.learned_rclm_update.v1"
CERTIFICATE_SCHEMA_ID: Final[str] = "runtime.v3.phase9.learned_certificate_packet.v1"
TASK_SCHEMA_ID: Final[str] = "runtime.v3.phase9.task_record.v1"
CERTIFICATION_SCHEMA_ID: Final[str] = "runtime.v3.phase9.certification_record.v1"
LEDGER_SCHEMA_ID: Final[str] = "runtime.v3.phase9.task_ledger.v1"
FRONTIER_SCHEMA_ID: Final[str] = "runtime.v3.phase9.capability_frontier.v1"
MODEL_SCHEMA_ID: Final[str] = "runtime.v3.phase9.model_identity.v1"
POLICY_SCHEMA_ID: Final[str] = "runtime.v3.phase9.policy_identity.v1"
SELF_HOSTING_SCHEMA_ID: Final[str] = "runtime.v3.phase9.self_hosting_binding.v1"
OPERATION_SCHEMA_ID: Final[str] = "runtime.v3.phase9.update_operation.v1"
HELDOUT_POLICY_SCHEMA_ID: Final[str] = "runtime.v3.phase9.heldout_access_policy.v1"

TaskPartition = Literal["training", "protected", "heldout"]
UpdateKind = Literal[
    "weight_update",
    "adapter_update",
    "optimizer_policy_update",
    "training_policy_update",
    "data_curriculum_update",
    "retrieval_update",
    "memory_update",
    "planner_update",
    "generator_update",
    "architecture_extension",
    "tokenizer_update",
    "tool_policy_update",
    "verification_policy_update",
    "resource_policy_update",
    "self_model_update",
]
ComponentTarget = Literal[
    "model_weights",
    "adapter_manifest",
    "optimizer_policy",
    "training_policy",
    "data_curriculum",
    "retrieval_policy",
    "memory_state",
    "planner_policy",
    "generator_policy",
    "model_architecture",
    "tokenizer",
    "tool_policy",
    "verification_policy",
    "resource_policy",
    "self_model",
]

ALLOWED_TASK_PARTITIONS: Final[frozenset[str]] = frozenset(
    {"training", "protected", "heldout"}
)
TARGET_BY_KIND: Final[dict[str, str]] = {
    "weight_update": "model_weights",
    "adapter_update": "adapter_manifest",
    "optimizer_policy_update": "optimizer_policy",
    "training_policy_update": "training_policy",
    "data_curriculum_update": "data_curriculum",
    "retrieval_update": "retrieval_policy",
    "memory_update": "memory_state",
    "planner_update": "planner_policy",
    "generator_update": "generator_policy",
    "architecture_extension": "model_architecture",
    "tokenizer_update": "tokenizer",
    "tool_policy_update": "tool_policy",
    "verification_policy_update": "verification_policy",
    "resource_policy_update": "resource_policy",
    "self_model_update": "self_model",
}
ALL_COMPONENT_TARGETS: Final[Sequence[str]] = tuple(
    sorted(set(TARGET_BY_KIND.values()), key=lambda item: item.encode("utf-8"))
)


def require_schema(value: object, expected: str, path: str) -> None:
    if value != expected:
        raise SchemaValidationError(path, f"expected {expected}")


def require_hash(value: object, path: str) -> str:
    text = require_string(value, path)
    validate_hash256(text, path)
    return text


def require_optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return require_string(value, path)


def require_boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, "expected Boolean")
    return value


def require_string_array(value: object, path: str) -> Sequence[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SchemaValidationError(path, "expected an array")
    return tuple(require_string(item, f"{path}[{index}]") for index, item in enumerate(value))


def normalize_sorted_unique_strings(values: Sequence[str], path: str) -> Sequence[str]:
    normalized = tuple(require_string(value, f"{path}[{index}]") for index, value in enumerate(values))
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError(path, "duplicate string entry")
    expected = tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))
    if normalized != expected:
        raise SchemaValidationError(path, "entries must be sorted by UTF-8 bytes")
    return normalized


def cast_task_partition(value: str) -> TaskPartition:
    return cast(TaskPartition, value)


def cast_update_kind(value: str) -> UpdateKind:
    return cast(UpdateKind, value)


def cast_component_target(value: str) -> ComponentTarget:
    return cast(ComponentTarget, value)
