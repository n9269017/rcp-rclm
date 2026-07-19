from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, strict_object

from rcp_rclm_runtime_v3.contract.common import (
    ALL_COMPONENT_TARGETS,
    CONTRACT_VERSION,
    OPERATION_SCHEMA_ID,
    TARGET_BY_KIND,
    UPDATE_SCHEMA_ID,
    ComponentTarget,
    UpdateKind,
    cast_component_target,
    cast_update_kind,
    require_hash,
    require_schema,
)


@dataclass(frozen=True, slots=True)
class UpdateOperation:
    operation_id: str
    kind: UpdateKind
    target: ComponentTarget
    component_path: str
    before_hash: str
    after_hash: str

    schema_id: ClassVar[str] = OPERATION_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.operation_id, "phase9.operation.operation_id")
        if self.kind not in TARGET_BY_KIND:
            raise SchemaValidationError("phase9.operation.kind", "unsupported update kind")
        expected_target = TARGET_BY_KIND[self.kind]
        if self.target != expected_target:
            raise SchemaValidationError(
                "phase9.operation.target",
                f"update kind {self.kind} requires target {expected_target}",
            )
        validate_semantic_path(self.component_path)
        require_hash(self.before_hash, "phase9.operation.before_hash")
        require_hash(self.after_hash, "phase9.operation.after_hash")
        if self.before_hash == self.after_hash:
            raise SchemaValidationError(
                "phase9.operation.after_hash", "substantive operation must change the hash"
            )

    @classmethod
    def from_json(cls, value: object) -> UpdateOperation:
        obj = strict_object(
            value,
            "phase9.operation",
            {
                "schema_id",
                "operation_id",
                "kind",
                "target",
                "component_path",
                "before_hash",
                "after_hash",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.operation.schema_id")
        kind = require_string(obj["kind"], "phase9.operation.kind")
        target = require_string(obj["target"], "phase9.operation.target")
        if kind not in TARGET_BY_KIND:
            raise SchemaValidationError("phase9.operation.kind", "unsupported update kind")
        if target not in ALL_COMPONENT_TARGETS:
            raise SchemaValidationError("phase9.operation.target", "unsupported component target")
        return cls(
            operation_id=require_string(
                obj["operation_id"], "phase9.operation.operation_id"
            ),
            kind=cast_update_kind(kind),
            target=cast_component_target(target),
            component_path=require_string(
                obj["component_path"], "phase9.operation.component_path"
            ),
            before_hash=require_hash(obj["before_hash"], "phase9.operation.before_hash"),
            after_hash=require_hash(obj["after_hash"], "phase9.operation.after_hash"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "operation_id": self.operation_id,
            "kind": self.kind,
            "target": self.target,
            "component_path": self.component_path,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
        }


@dataclass(frozen=True, slots=True)
class LearnedRCLMUpdate:
    transition_id: str
    predecessor_state_hash: str
    candidate_state_hash: str
    base_update_hash: str
    operations: Sequence[UpdateOperation]
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = UPDATE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase9.update.transition_id")
        for name in ("predecessor_state_hash", "candidate_state_hash", "base_update_hash"):
            require_hash(getattr(self, name), f"phase9.update.{name}")
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase9.update.contract_version", f"expected {CONTRACT_VERSION}"
            )
        operations = tuple(self.operations)
        if not operations:
            raise SchemaValidationError("phase9.update.operations", "at least one operation is required")
        operation_ids = tuple(operation.operation_id for operation in operations)
        targets = tuple(operation.target for operation in operations)
        if len(set(operation_ids)) != len(operation_ids):
            raise SchemaValidationError("phase9.update.operations", "duplicate operation_id")
        if len(set(targets)) != len(targets):
            raise SchemaValidationError("phase9.update.operations", "duplicate component target")
        ordered = tuple(sorted(operations, key=lambda item: item.operation_id.encode("utf-8")))
        if operations != ordered:
            raise SchemaValidationError(
                "phase9.update.operations", "operations must be sorted by operation_id"
            )
        object.__setattr__(self, "operations", operations)

    @property
    def update_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "predecessor_state_hash": self.predecessor_state_hash,
            "candidate_state_hash": self.candidate_state_hash,
            "base_update_hash": self.base_update_hash,
            "operations": [operation.to_json() for operation in self.operations],
        }

    @classmethod
    def from_json(cls, value: object) -> LearnedRCLMUpdate:
        obj = strict_object(
            value,
            "phase9.update",
            {
                "schema_id",
                "contract_version",
                "transition_id",
                "predecessor_state_hash",
                "candidate_state_hash",
                "base_update_hash",
                "operations",
                "update_hash",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.update.schema_id")
        raw_operations = obj["operations"]
        if not isinstance(raw_operations, Sequence) or isinstance(
            raw_operations, (str, bytes, bytearray)
        ):
            raise SchemaValidationError("phase9.update.operations", "expected an array")
        result = cls(
            transition_id=require_string(
                obj["transition_id"], "phase9.update.transition_id"
            ),
            predecessor_state_hash=require_hash(
                obj["predecessor_state_hash"], "phase9.update.predecessor_state_hash"
            ),
            candidate_state_hash=require_hash(
                obj["candidate_state_hash"], "phase9.update.candidate_state_hash"
            ),
            base_update_hash=require_hash(
                obj["base_update_hash"], "phase9.update.base_update_hash"
            ),
            operations=tuple(UpdateOperation.from_json(item) for item in raw_operations),
            contract_version=require_string(
                obj["contract_version"], "phase9.update.contract_version"
            ),
        )
        declared = require_hash(obj["update_hash"], "phase9.update.update_hash")
        if declared != result.update_hash:
            raise SchemaValidationError("phase9.update.update_hash", "content hash mismatch")
        return result

    def to_json(self) -> dict[str, object]:
        result = self.content_json()
        result["update_hash"] = self.update_hash
        return result


__all__ = ["LearnedRCLMUpdate", "UpdateOperation"]
