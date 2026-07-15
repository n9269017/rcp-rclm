from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_structural_integer, strict_object
from rcp_rclm_runtime.successor._record_common import PHASE6_RESOURCE_USAGE_SCHEMA_ID, require_nonnegative, required_bool
from rcp_rclm_runtime.successor.record_budget import Phase6ResourceBudgetRecord

@dataclass(frozen=True, slots=True)
class Phase6ResourceUsageRecord:
    budget: Phase6ResourceBudgetRecord
    predecessor_file_count: int
    candidate_file_count: int
    predecessor_bytes: int
    candidate_bytes: int
    bytes_read: int
    bytes_written: int
    changed_files: int
    commands: int
    snapshot_bytes: int

    schema_id: ClassVar[str] = PHASE6_RESOURCE_USAGE_SCHEMA_ID

    def __post_init__(self) -> None:
        for name, value in (
            ("predecessor_file_count", self.predecessor_file_count),
            ("candidate_file_count", self.candidate_file_count),
            ("predecessor_bytes", self.predecessor_bytes),
            ("candidate_bytes", self.candidate_bytes),
            ("bytes_read", self.bytes_read),
            ("bytes_written", self.bytes_written),
            ("changed_files", self.changed_files),
            ("commands", self.commands),
            ("snapshot_bytes", self.snapshot_bytes),
        ):
            require_nonnegative(value, f"phase6_resource_usage.{name}")

    @property
    def within_budget(self) -> bool:
        return (
            self.predecessor_file_count <= self.budget.max_file_count
            and self.candidate_file_count <= self.budget.max_file_count
            and self.predecessor_bytes <= self.budget.max_total_bytes
            and self.candidate_bytes <= self.budget.max_total_bytes
            and self.bytes_written <= self.budget.max_written_bytes
            and self.changed_files <= self.budget.max_changed_files
            and self.commands <= self.budget.max_commands
            and self.snapshot_bytes <= self.budget.max_snapshot_bytes
        )

    @property
    def usage_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_resource_usage",
    ) -> Phase6ResourceUsageRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "budget",
                "predecessor_file_count",
                "candidate_file_count",
                "predecessor_bytes",
                "candidate_bytes",
                "bytes_read",
                "bytes_written",
                "changed_files",
                "commands",
                "snapshot_bytes",
                "within_budget",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        record = cls(
            budget=Phase6ResourceBudgetRecord.from_json(
                obj["budget"], f"{path}.budget"
            ),
            predecessor_file_count=require_structural_integer(
                obj["predecessor_file_count"],
                f"{path}.predecessor_file_count",
                minimum=0,
            ),
            candidate_file_count=require_structural_integer(
                obj["candidate_file_count"],
                f"{path}.candidate_file_count",
                minimum=0,
            ),
            predecessor_bytes=require_structural_integer(
                obj["predecessor_bytes"], f"{path}.predecessor_bytes", minimum=0
            ),
            candidate_bytes=require_structural_integer(
                obj["candidate_bytes"], f"{path}.candidate_bytes", minimum=0
            ),
            bytes_read=require_structural_integer(
                obj["bytes_read"], f"{path}.bytes_read", minimum=0
            ),
            bytes_written=require_structural_integer(
                obj["bytes_written"], f"{path}.bytes_written", minimum=0
            ),
            changed_files=require_structural_integer(
                obj["changed_files"], f"{path}.changed_files", minimum=0
            ),
            commands=require_structural_integer(
                obj["commands"], f"{path}.commands", minimum=0
            ),
            snapshot_bytes=require_structural_integer(
                obj["snapshot_bytes"], f"{path}.snapshot_bytes", minimum=0
            ),
        )
        declared_within = required_bool(
            obj["within_budget"], f"{path}.within_budget"
        )
        if declared_within != record.within_budget:
            raise SchemaValidationError(
                f"{path}.within_budget",
                "declared budget result does not match computed result",
            )
        return record

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "budget": self.budget.to_json(),
            "predecessor_file_count": self.predecessor_file_count,
            "candidate_file_count": self.candidate_file_count,
            "predecessor_bytes": self.predecessor_bytes,
            "candidate_bytes": self.candidate_bytes,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
            "changed_files": self.changed_files,
            "commands": self.commands,
            "snapshot_bytes": self.snapshot_bytes,
            "within_budget": self.within_budget,
        }
