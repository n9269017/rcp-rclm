from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Literal, TypeAlias, TypeVar, cast

from rcp_rclm_runtime.canonical.hashing import SemanticFileRecord, validate_hash256
from rcp_rclm_runtime.canonical.paths import validate_file_mode, validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, strict_object
from rcp_rclm_runtime.schema.verdict import FrozenHashMap

PHASE6_BUDGET_SCHEMA_ID = "runtime.phase6_resource_budget.v2"
PHASE6_PREDECESSOR_MANIFEST_SCHEMA_ID = "runtime.phase6_predecessor_manifest.v2"
PHASE6_OPERATION_SCHEMA_ID = "runtime.phase6_selected_file_operation.v2"
PHASE6_SELECTION_SCHEMA_ID = "runtime.phase6_selection.v2"
PHASE6_FILE_CHANGE_SCHEMA_ID = "runtime.phase6_file_change.v2"
PHASE6_COMMAND_SCHEMA_ID = "runtime.phase6_command_record.v2"
PHASE6_ENVIRONMENT_SCHEMA_ID = "runtime.phase6_environment_record.v2"
PHASE6_RESOURCE_USAGE_SCHEMA_ID = "runtime.phase6_resource_usage.v2"
PHASE6_ROLLBACK_SCHEMA_ID = "runtime.phase6_rollback_snapshot.v2"
PHASE6_REALIZATION_SCHEMA_ID = "runtime.phase6_realization.v2"
PHASE6_CANDIDATE_MANIFEST_SCHEMA_ID = "runtime.phase6_candidate_manifest.v2"
PHASE6_PACKAGE_REPORT_SCHEMA_ID = "runtime.phase6_package_report.v2"

SuccessorVerdict: TypeAlias = Literal["success", "reject", "indeterminate"]
FileOperationKind: TypeAlias = Literal["write", "delete"]
FileChangeKind: TypeAlias = Literal["added", "modified", "deleted"]
CandidateStatus: TypeAlias = Literal["realized_unverified"]
CommandKind: TypeAlias = Literal[
    "copy_payload",
    "write_file",
    "delete_file",
    "build_rollback",
    "verify_rollback",
    "build_package",
]
WorkingDirectoryPolicy: TypeAlias = Literal[
    "isolated_workspace",
    "candidate_package_staging",
]
SubstantiveComponentKind: TypeAlias = Literal[
    "model_weights",
    "training_policy",
    "planning_policy",
    "tool_policy",
    "memory_policy",
    "retrieval_policy",
    "verification_policy",
    "code_generation_policy",
    "architecture_code",
]
LiteralText = TypeVar("LiteralText", bound=str)

SUBSTANTIVE_COMPONENT_KINDS: frozenset[str] = frozenset(
    {
        "model_weights",
        "training_policy",
        "planning_policy",
        "tool_policy",
        "memory_policy",
        "retrieval_policy",
        "verification_policy",
        "code_generation_policy",
        "architecture_code",
    }
)

_SUBSTANTIVE_COMPONENT_PATH_RULES: Mapping[str, Sequence[str]] = {
    "model_weights": ("model/weights/",),
    "training_policy": ("policies/training_policy.json",),
    "planning_policy": ("policies/planning_policy.json",),
    "tool_policy": ("policies/tool_policy.json",),
    "memory_policy": ("policies/memory_policy.json",),
    "retrieval_policy": ("policies/retrieval_policy.json",),
    "verification_policy": ("policies/verification_policy.json",),
    "code_generation_policy": ("policies/code_generation_policy.json",),
    "architecture_code": ("architecture/",),
}


class Phase6ReasonCode(StrEnum):
    SCHEMA_MALFORMED = "PHASE6_SCHEMA_MALFORMED"
    PROPOSAL_INVALID = "PHASE6_PROPOSAL_INVALID"
    PREDECESSOR_MISMATCH = "PHASE6_PREDECESSOR_MISMATCH"
    UNSUPPORTED_SCOPE = "PHASE6_UNSUPPORTED_SCOPE"
    SELECTION_FAILED = "PHASE6_SELECTION_FAILED"
    WORKSPACE_INVALID = "PHASE6_WORKSPACE_INVALID"
    RESOURCE_EXCEEDED = "PHASE6_RESOURCE_EXCEEDED"
    COMMAND_FAILED = "PHASE6_COMMAND_FAILED"
    UNDECLARED_MODIFICATION = "PHASE6_UNDECLARED_MODIFICATION"
    SUBSTANTIVE_CHANGE_REQUIRED = "PHASE6_SUBSTANTIVE_CHANGE_REQUIRED"
    METADATA_ONLY_CHANGE = "PHASE6_METADATA_ONLY_CHANGE"
    ROLLBACK_SNAPSHOT_FAILED = "PHASE6_ROLLBACK_SNAPSHOT_FAILED"
    PACKAGE_BUILD_FAILED = "PHASE6_PACKAGE_BUILD_FAILED"
    INTERNAL_ERROR = "PHASE6_INTERNAL_ERROR"


def component_path_matches(component_kind: str, path: str) -> bool:
    rules = _SUBSTANTIVE_COMPONENT_PATH_RULES.get(component_kind, ())
    return any(
        path.startswith(rule) if rule.endswith("/") else path == rule
        for rule in rules
    )


def required_hash(value: object, path: str) -> str:
    return validate_hash256(require_string(value, path), path)


def optional_hash(value: object, path: str) -> str | None:
    if value is None:
        return None
    return required_hash(value, path)


def optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return require_string(value, path, nonempty=False)


def optional_mode(value: object, path: str) -> str | None:
    if value is None:
        return None
    return validate_file_mode(require_string(value, path))


def required_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, "expected a Boolean")
    return value


def required_integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError(path, "expected an integer")
    return value


def literal(value: object, path: str, allowed: set[str]) -> LiteralText:
    text = require_string(value, path)
    require_exact_set(text, allowed, path)
    return cast(LiteralText, text)


def require_exact(value: str, expected: str, path: str) -> None:
    if value != expected:
        raise SchemaValidationError(path, f"expected {expected}")


def require_exact_set(value: str, allowed: set[str], path: str) -> None:
    if value not in allowed:
        raise SchemaValidationError(path, f"unsupported value: {value}")


def require_positive(value: object, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SchemaValidationError(path, "expected a positive integer")


def require_nonnegative(value: object, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaValidationError(path, "expected a nonnegative integer")


def semantic_file_from_json(value: object, path: str) -> SemanticFileRecord:
    obj = strict_object(value, path, {"path", "mode", "size", "sha256"})
    size_raw = obj["size"]
    if not isinstance(size_raw, str) or not size_raw.isdigit():
        raise SchemaValidationError(
            f"{path}.size",
            "expected canonical nonnegative integer string",
        )
    if len(size_raw) > 1 and size_raw.startswith("0"):
        raise SchemaValidationError(f"{path}.size", "leading zeros are forbidden")
    return SemanticFileRecord(
        path=validate_semantic_path(require_string(obj["path"], f"{path}.path")),
        mode=validate_file_mode(require_string(obj["mode"], f"{path}.mode")),
        size=int(size_raw),
        sha256=required_hash(obj["sha256"], f"{path}.sha256"),
    )


def optional_semantic_file(
    value: object,
    path: str,
) -> SemanticFileRecord | None:
    if value is None:
        return None
    return semantic_file_from_json(value, path)


def frozen_hash_map(value: object, path: str) -> FrozenHashMap:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    mapping: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            raise SchemaValidationError(path, "hash-map keys must be strings")
        key = require_string(raw_key, f"{path}.key")
        mapping[key] = required_hash(raw_value, f"{path}.{key}")
    return FrozenHashMap.from_mapping(mapping, path)
