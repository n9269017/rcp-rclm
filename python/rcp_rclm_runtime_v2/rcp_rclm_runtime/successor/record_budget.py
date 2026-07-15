from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.schema._common import require_schema_id, require_structural_integer, strict_object
from rcp_rclm_runtime.successor._record_common import PHASE6_BUDGET_SCHEMA_ID, require_positive

@dataclass(frozen=True, slots=True)
class Phase6ResourceBudgetRecord:
    max_file_count: int
    max_total_bytes: int
    max_changed_files: int
    max_written_bytes: int
    max_commands: int
    max_snapshot_bytes: int

    schema_id: ClassVar[str] = PHASE6_BUDGET_SCHEMA_ID

    def __post_init__(self) -> None:
        for name, value in (
            ("max_file_count", self.max_file_count),
            ("max_total_bytes", self.max_total_bytes),
            ("max_changed_files", self.max_changed_files),
            ("max_written_bytes", self.max_written_bytes),
            ("max_commands", self.max_commands),
            ("max_snapshot_bytes", self.max_snapshot_bytes),
        ):
            require_positive(value, f"phase6_budget.{name}")

    @property
    def budget_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_budget",
    ) -> Phase6ResourceBudgetRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "max_file_count",
                "max_total_bytes",
                "max_changed_files",
                "max_written_bytes",
                "max_commands",
                "max_snapshot_bytes",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            max_file_count=require_structural_integer(
                obj["max_file_count"], f"{path}.max_file_count", minimum=1
            ),
            max_total_bytes=require_structural_integer(
                obj["max_total_bytes"], f"{path}.max_total_bytes", minimum=1
            ),
            max_changed_files=require_structural_integer(
                obj["max_changed_files"], f"{path}.max_changed_files", minimum=1
            ),
            max_written_bytes=require_structural_integer(
                obj["max_written_bytes"], f"{path}.max_written_bytes", minimum=1
            ),
            max_commands=require_structural_integer(
                obj["max_commands"], f"{path}.max_commands", minimum=1
            ),
            max_snapshot_bytes=require_structural_integer(
                obj["max_snapshot_bytes"], f"{path}.max_snapshot_bytes", minimum=1
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "max_file_count": self.max_file_count,
            "max_total_bytes": self.max_total_bytes,
            "max_changed_files": self.max_changed_files,
            "max_written_bytes": self.max_written_bytes,
            "max_commands": self.max_commands,
            "max_snapshot_bytes": self.max_snapshot_bytes,
        }
