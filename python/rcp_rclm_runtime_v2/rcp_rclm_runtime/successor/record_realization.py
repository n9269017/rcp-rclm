from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.successor._record_common import PHASE6_REALIZATION_SCHEMA_ID, SUBSTANTIVE_COMPONENT_KINDS, SubstantiveComponentKind, literal, required_hash
from rcp_rclm_runtime.successor.record_command import Phase6CommandRecord
from rcp_rclm_runtime.successor.record_environment import Phase6EnvironmentRecord
from rcp_rclm_runtime.successor.record_file_change import Phase6FileChangeRecord
from rcp_rclm_runtime.successor.record_resource import Phase6ResourceUsageRecord
from rcp_rclm_runtime.successor.record_rollback import Phase6RollbackSnapshotRecord

@dataclass(frozen=True, slots=True)
class Phase6RealizationRecord:
    transition_id: str
    predecessor_manifest_hash: str
    selection_hash: str
    workspace_copy_tree_hash: str
    candidate_payload_tree_hash: str
    changes: Sequence[Phase6FileChangeRecord]
    commands: Sequence[Phase6CommandRecord]
    environment: Phase6EnvironmentRecord
    resources: Phase6ResourceUsageRecord
    rollback: Phase6RollbackSnapshotRecord

    schema_id: ClassVar[str] = PHASE6_REALIZATION_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase6_realization.transition_id")
        for name, value in (
            ("predecessor_manifest_hash", self.predecessor_manifest_hash),
            ("selection_hash", self.selection_hash),
            ("workspace_copy_tree_hash", self.workspace_copy_tree_hash),
            ("candidate_payload_tree_hash", self.candidate_payload_tree_hash),
        ):
            validate_hash256(value, f"phase6_realization.{name}")
        changes = tuple(self.changes)
        commands = tuple(self.commands)
        object.__setattr__(self, "changes", changes)
        object.__setattr__(self, "commands", commands)
        change_paths = [change.path for change in changes]
        if change_paths != sorted(change_paths, key=lambda item: item.encode("utf-8")):
            raise SchemaValidationError(
                "phase6_realization.changes",
                "changes must be sorted by UTF-8 path bytes",
            )
        command_numbers = [command.sequence_number for command in commands]
        if command_numbers != list(range(len(commands))):
            raise SchemaValidationError(
                "phase6_realization.commands",
                "command sequence numbers must be contiguous from zero",
            )
        if not changes:
            raise SchemaValidationError(
                "phase6_realization.changes",
                "realization must modify at least one file",
            )
        if not any(change.substantive for change in changes):
            raise SchemaValidationError(
                "phase6_realization.changes",
                "realization requires at least one substantive change",
            )
        if self.workspace_copy_tree_hash != self.rollback.predecessor_tree_hash:
            raise SchemaValidationError(
                "phase6_realization.workspace_copy_tree_hash",
                "workspace copy must equal rollback predecessor tree",
            )
        if not self.rollback.verified:
            raise SchemaValidationError(
                "phase6_realization.rollback",
                "rollback snapshot must be verified",
            )
        if not self.resources.within_budget:
            raise SchemaValidationError(
                "phase6_realization.resources",
                "realization exceeds declared resource budget",
            )
        if self.resources.changed_files != len(changes):
            raise SchemaValidationError(
                "phase6_realization.resources.changed_files",
                "changed-file count does not match ledger",
            )
        if self.resources.commands != len(commands):
            raise SchemaValidationError(
                "phase6_realization.resources.commands",
                "command count does not match command ledger",
            )

    @property
    def substantive_component_kinds(self) -> Sequence[SubstantiveComponentKind]:
        return tuple(
            sorted(
                {
                    change.component_kind
                    for change in self.changes
                    if change.substantive and change.component_kind is not None
                }
            )
        )

    @property
    def change_ledger_hash(self) -> str:
        return canonical_json_hash(
            [change.to_json() for change in self.changes]
        )

    @property
    def command_log_hash(self) -> str:
        return canonical_json_hash(
            [command.to_json() for command in self.commands]
        )

    @property
    def realization_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_realization",
    ) -> Phase6RealizationRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "transition_id",
                "predecessor_manifest_hash",
                "selection_hash",
                "workspace_copy_tree_hash",
                "candidate_payload_tree_hash",
                "changes",
                "commands",
                "environment",
                "resources",
                "rollback",
                "substantive_component_kinds",
                "change_ledger_hash",
                "command_log_hash",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        changes_raw = obj["changes"]
        commands_raw = obj["commands"]
        if not isinstance(changes_raw, list):
            raise SchemaValidationError(f"{path}.changes", "expected an array")
        if not isinstance(commands_raw, list):
            raise SchemaValidationError(f"{path}.commands", "expected an array")
        record = cls(
            transition_id=require_string(
                obj["transition_id"], f"{path}.transition_id"
            ),
            predecessor_manifest_hash=required_hash(
                obj["predecessor_manifest_hash"],
                f"{path}.predecessor_manifest_hash",
            ),
            selection_hash=required_hash(
                obj["selection_hash"], f"{path}.selection_hash"
            ),
            workspace_copy_tree_hash=required_hash(
                obj["workspace_copy_tree_hash"],
                f"{path}.workspace_copy_tree_hash",
            ),
            candidate_payload_tree_hash=required_hash(
                obj["candidate_payload_tree_hash"],
                f"{path}.candidate_payload_tree_hash",
            ),
            changes=tuple(
                Phase6FileChangeRecord.from_json(
                    item, f"{path}.changes[{index}]"
                )
                for index, item in enumerate(changes_raw)
            ),
            commands=tuple(
                Phase6CommandRecord.from_json(
                    item, f"{path}.commands[{index}]"
                )
                for index, item in enumerate(commands_raw)
            ),
            environment=Phase6EnvironmentRecord.from_json(
                obj["environment"], f"{path}.environment"
            ),
            resources=Phase6ResourceUsageRecord.from_json(
                obj["resources"], f"{path}.resources"
            ),
            rollback=Phase6RollbackSnapshotRecord.from_json(
                obj["rollback"], f"{path}.rollback"
            ),
        )
        components_raw = obj["substantive_component_kinds"]
        if not isinstance(components_raw, list):
            raise SchemaValidationError(
                f"{path}.substantive_component_kinds",
                "expected an array",
            )
        declared_components = tuple(
            literal(
                item,
                f"{path}.substantive_component_kinds[{index}]",
                set(SUBSTANTIVE_COMPONENT_KINDS),
            )
            for index, item in enumerate(components_raw)
        )
        if declared_components != record.substantive_component_kinds:
            raise SchemaValidationError(
                f"{path}.substantive_component_kinds",
                "declared components do not match change ledger",
            )
        if required_hash(
            obj["change_ledger_hash"], f"{path}.change_ledger_hash"
        ) != record.change_ledger_hash:
            raise SchemaValidationError(
                f"{path}.change_ledger_hash",
                "change ledger hash mismatch",
            )
        if required_hash(
            obj["command_log_hash"], f"{path}.command_log_hash"
        ) != record.command_log_hash:
            raise SchemaValidationError(
                f"{path}.command_log_hash",
                "command log hash mismatch",
            )
        return record

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "transition_id": self.transition_id,
            "predecessor_manifest_hash": self.predecessor_manifest_hash,
            "selection_hash": self.selection_hash,
            "workspace_copy_tree_hash": self.workspace_copy_tree_hash,
            "candidate_payload_tree_hash": self.candidate_payload_tree_hash,
            "changes": [change.to_json() for change in self.changes],
            "commands": [command.to_json() for command in self.commands],
            "environment": self.environment.to_json(),
            "resources": self.resources.to_json(),
            "rollback": self.rollback.to_json(),
            "substantive_component_kinds": list(
                self.substantive_component_kinds
            ),
            "change_ledger_hash": self.change_ledger_hash,
            "command_log_hash": self.command_log_hash,
        }
