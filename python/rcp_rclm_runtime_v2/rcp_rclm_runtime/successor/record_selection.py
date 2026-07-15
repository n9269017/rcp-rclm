from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    FrozenJson,
    FrozenJsonArray,
    FrozenJsonObject,
    freeze_json,
    require_schema_id,
    require_string,
    strict_object,
    thaw_json,
)
from rcp_rclm_runtime.successor._record_common import (
    PHASE6_SELECTION_SCHEMA_ID,
    SUBSTANTIVE_COMPONENT_KINDS,
    SubstantiveComponentKind,
    literal,
    required_hash,
)
from rcp_rclm_runtime.successor.record_operation import SelectedFileOperationRecord


@dataclass(frozen=True, slots=True)
class Phase6SelectionRecord:
    transition_id: str
    proposal_hash: str
    generator_request_hash: str
    predecessor_package_id: str
    predecessor_manifest_hash: str
    phase5_predecessor_manifest_hash: str
    selection_policy_id: str
    selected_update: FrozenJson
    selected_update_hash: str
    operations: Sequence[SelectedFileOperationRecord]
    substantive_component_kinds: Sequence[SubstantiveComponentKind]

    schema_id: ClassVar[str] = PHASE6_SELECTION_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase6_selection.transition_id")
        require_string(
            self.predecessor_package_id,
            "phase6_selection.predecessor_package_id",
        )
        require_string(
            self.selection_policy_id,
            "phase6_selection.selection_policy_id",
        )
        for name, value in (
            ("proposal_hash", self.proposal_hash),
            ("generator_request_hash", self.generator_request_hash),
            ("predecessor_manifest_hash", self.predecessor_manifest_hash),
            (
                "phase5_predecessor_manifest_hash",
                self.phase5_predecessor_manifest_hash,
            ),
            ("selected_update_hash", self.selected_update_hash),
        ):
            validate_hash256(value, f"phase6_selection.{name}")
        selected_value = (
            thaw_json(self.selected_update)
            if isinstance(self.selected_update, (FrozenJsonArray, FrozenJsonObject))
            else self.selected_update
        )
        frozen_update = freeze_json(selected_value)
        object.__setattr__(self, "selected_update", frozen_update)
        if canonical_json_hash(thaw_json(frozen_update)) != self.selected_update_hash:
            raise SchemaValidationError(
                "phase6_selection.selected_update_hash",
                "selected update hash does not match selected update",
            )
        operations = tuple(self.operations)
        object.__setattr__(self, "operations", operations)
        if not operations:
            raise SchemaValidationError(
                "phase6_selection.operations",
                "selection must contain at least one file operation",
            )
        paths = [operation.path for operation in operations]
        if paths != sorted(paths, key=lambda item: item.encode("utf-8")):
            raise SchemaValidationError(
                "phase6_selection.operations",
                "operations must be sorted by UTF-8 path bytes",
            )
        if len(paths) != len(set(paths)):
            raise SchemaValidationError(
                "phase6_selection.operations",
                "duplicate operation path",
            )
        component_kinds = tuple(self.substantive_component_kinds)
        object.__setattr__(
            self,
            "substantive_component_kinds",
            component_kinds,
        )
        if component_kinds != tuple(sorted(set(component_kinds))):
            raise SchemaValidationError(
                "phase6_selection.substantive_component_kinds",
                "component kinds must be unique and sorted",
            )
        operation_components = tuple(
            sorted(
                {
                    operation.component_kind
                    for operation in operations
                    if operation.component_kind is not None
                }
            )
        )
        if component_kinds != operation_components:
            raise SchemaValidationError(
                "phase6_selection.substantive_component_kinds",
                "component list must equal operation component kinds",
            )
        if not component_kinds:
            raise SchemaValidationError(
                "phase6_selection.substantive_component_kinds",
                "selection requires a substantive component",
            )

    @property
    def selection_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_selection",
    ) -> Phase6SelectionRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "transition_id",
                "proposal_hash",
                "generator_request_hash",
                "predecessor_package_id",
                "predecessor_manifest_hash",
                "phase5_predecessor_manifest_hash",
                "selection_policy_id",
                "selected_update",
                "selected_update_hash",
                "operations",
                "substantive_component_kinds",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        operations_raw = obj["operations"]
        if not isinstance(operations_raw, list):
            raise SchemaValidationError(f"{path}.operations", "expected an array")
        components_raw = obj["substantive_component_kinds"]
        if not isinstance(components_raw, list):
            raise SchemaValidationError(
                f"{path}.substantive_component_kinds",
                "expected an array",
            )
        return cls(
            transition_id=require_string(
                obj["transition_id"], f"{path}.transition_id"
            ),
            proposal_hash=required_hash(
                obj["proposal_hash"], f"{path}.proposal_hash"
            ),
            generator_request_hash=required_hash(
                obj["generator_request_hash"],
                f"{path}.generator_request_hash",
            ),
            predecessor_package_id=require_string(
                obj["predecessor_package_id"],
                f"{path}.predecessor_package_id",
            ),
            predecessor_manifest_hash=required_hash(
                obj["predecessor_manifest_hash"],
                f"{path}.predecessor_manifest_hash",
            ),
            phase5_predecessor_manifest_hash=required_hash(
                obj["phase5_predecessor_manifest_hash"],
                f"{path}.phase5_predecessor_manifest_hash",
            ),
            selection_policy_id=require_string(
                obj["selection_policy_id"],
                f"{path}.selection_policy_id",
            ),
            selected_update=freeze_json(
                obj["selected_update"], f"{path}.selected_update"
            ),
            selected_update_hash=required_hash(
                obj["selected_update_hash"],
                f"{path}.selected_update_hash",
            ),
            operations=tuple(
                SelectedFileOperationRecord.from_json(
                    item,
                    f"{path}.operations[{index}]",
                )
                for index, item in enumerate(operations_raw)
            ),
            substantive_component_kinds=tuple(
                literal(
                    item,
                    f"{path}.substantive_component_kinds[{index}]",
                    set(SUBSTANTIVE_COMPONENT_KINDS),
                )
                for index, item in enumerate(components_raw)
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "transition_id": self.transition_id,
            "proposal_hash": self.proposal_hash,
            "generator_request_hash": self.generator_request_hash,
            "predecessor_package_id": self.predecessor_package_id,
            "predecessor_manifest_hash": self.predecessor_manifest_hash,
            "phase5_predecessor_manifest_hash": self.phase5_predecessor_manifest_hash,
            "selection_policy_id": self.selection_policy_id,
            "selected_update": thaw_json(self.selected_update),
            "selected_update_hash": self.selected_update_hash,
            "operations": [operation.to_json() for operation in self.operations],
            "substantive_component_kinds": list(self.substantive_component_kinds),
        }
