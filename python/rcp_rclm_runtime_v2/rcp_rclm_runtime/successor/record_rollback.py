from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, require_structural_integer, strict_object
from rcp_rclm_runtime.successor._record_common import PHASE6_ROLLBACK_SCHEMA_ID, require_nonnegative, required_bool, required_hash

@dataclass(frozen=True, slots=True)
class Phase6RollbackSnapshotRecord:
    archive_relative_path: str
    archive_hash: str
    archive_bytes: int
    predecessor_tree_hash: str
    restored_tree_hash: str
    verified: bool

    schema_id: ClassVar[str] = PHASE6_ROLLBACK_SCHEMA_ID

    def __post_init__(self) -> None:
        validate_semantic_path(self.archive_relative_path)
        if not self.archive_relative_path.startswith("rollback/"):
            raise SchemaValidationError(
                "phase6_rollback.archive_relative_path",
                "rollback snapshot must be stored under rollback/",
            )
        for name, value in (
            ("archive_hash", self.archive_hash),
            ("predecessor_tree_hash", self.predecessor_tree_hash),
            ("restored_tree_hash", self.restored_tree_hash),
        ):
            validate_hash256(value, f"phase6_rollback.{name}")
        require_nonnegative(self.archive_bytes, "phase6_rollback.archive_bytes")
        if not isinstance(self.verified, bool):
            raise SchemaValidationError(
                "phase6_rollback.verified",
                "expected a Boolean",
            )
        computed = self.predecessor_tree_hash == self.restored_tree_hash
        if self.verified != computed:
            raise SchemaValidationError(
                "phase6_rollback.verified",
                "verified flag does not match restored-tree comparison",
            )

    @property
    def rollback_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_rollback",
    ) -> Phase6RollbackSnapshotRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "archive_relative_path",
                "archive_hash",
                "archive_bytes",
                "predecessor_tree_hash",
                "restored_tree_hash",
                "verified",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            archive_relative_path=validate_semantic_path(
                require_string(
                    obj["archive_relative_path"],
                    f"{path}.archive_relative_path",
                )
            ),
            archive_hash=required_hash(
                obj["archive_hash"], f"{path}.archive_hash"
            ),
            archive_bytes=require_structural_integer(
                obj["archive_bytes"], f"{path}.archive_bytes", minimum=0
            ),
            predecessor_tree_hash=required_hash(
                obj["predecessor_tree_hash"],
                f"{path}.predecessor_tree_hash",
            ),
            restored_tree_hash=required_hash(
                obj["restored_tree_hash"], f"{path}.restored_tree_hash"
            ),
            verified=required_bool(obj["verified"], f"{path}.verified"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "archive_relative_path": self.archive_relative_path,
            "archive_hash": self.archive_hash,
            "archive_bytes": self.archive_bytes,
            "predecessor_tree_hash": self.predecessor_tree_hash,
            "restored_tree_hash": self.restored_tree_hash,
            "verified": self.verified,
        }
