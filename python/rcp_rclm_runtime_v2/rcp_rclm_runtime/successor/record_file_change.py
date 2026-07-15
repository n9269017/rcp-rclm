from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import SemanticFileRecord, canonical_json_hash, validate_hash256
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.successor._record_common import FileChangeKind, PHASE6_FILE_CHANGE_SCHEMA_ID, SUBSTANTIVE_COMPONENT_KINDS, SubstantiveComponentKind, literal, optional_hash, optional_semantic_file, required_bool, require_exact_set

@dataclass(frozen=True, slots=True)
class Phase6FileChangeRecord:
    path: str
    change_kind: FileChangeKind
    component_kind: SubstantiveComponentKind | None
    before: SemanticFileRecord | None
    after: SemanticFileRecord | None
    semantic_before_hash: str | None
    semantic_after_hash: str | None
    substantive: bool

    schema_id: ClassVar[str] = PHASE6_FILE_CHANGE_SCHEMA_ID

    def __post_init__(self) -> None:
        validate_semantic_path(self.path)
        require_exact_set(
            self.change_kind,
            {"added", "modified", "deleted"},
            "phase6_file_change.change_kind",
        )
        if self.component_kind is not None:
            require_exact_set(
                self.component_kind,
                set(SUBSTANTIVE_COMPONENT_KINDS),
                "phase6_file_change.component_kind",
            )
        if self.before is not None and self.before.path != self.path:
            raise SchemaValidationError(
                "phase6_file_change.before.path",
                "before file path mismatch",
            )
        if self.after is not None and self.after.path != self.path:
            raise SchemaValidationError(
                "phase6_file_change.after.path",
                "after file path mismatch",
            )
        if self.change_kind == "added" and (self.before is not None or self.after is None):
            raise SchemaValidationError(
                "phase6_file_change",
                "added change requires only an after file",
            )
        if self.change_kind == "deleted" and (self.before is None or self.after is not None):
            raise SchemaValidationError(
                "phase6_file_change",
                "deleted change requires only a before file",
            )
        if self.change_kind == "modified" and (self.before is None or self.after is None):
            raise SchemaValidationError(
                "phase6_file_change",
                "modified change requires before and after files",
            )
        for name, value in (
            ("semantic_before_hash", self.semantic_before_hash),
            ("semantic_after_hash", self.semantic_after_hash),
        ):
            if value is not None:
                validate_hash256(value, f"phase6_file_change.{name}")
        if not isinstance(self.substantive, bool):
            raise SchemaValidationError(
                "phase6_file_change.substantive",
                "expected a Boolean",
            )
        if self.substantive and self.component_kind is None:
            raise SchemaValidationError(
                "phase6_file_change.component_kind",
                "substantive change requires a component kind",
            )
        if self.substantive and self.semantic_before_hash == self.semantic_after_hash:
            raise SchemaValidationError(
                "phase6_file_change.substantive",
                "substantive change requires distinct semantic hashes",
            )

    @property
    def change_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_file_change",
    ) -> Phase6FileChangeRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "path",
                "change_kind",
                "component_kind",
                "before",
                "after",
                "semantic_before_hash",
                "semantic_after_hash",
                "substantive",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        component_raw = obj["component_kind"]
        return cls(
            path=validate_semantic_path(
                require_string(obj["path"], f"{path}.path")
            ),
            change_kind=literal(
                obj["change_kind"],
                f"{path}.change_kind",
                {"added", "modified", "deleted"},
            ),
            component_kind=(
                None
                if component_raw is None
                else literal(
                    component_raw,
                    f"{path}.component_kind",
                    set(SUBSTANTIVE_COMPONENT_KINDS),
                )
            ),
            before=optional_semantic_file(obj["before"], f"{path}.before"),
            after=optional_semantic_file(obj["after"], f"{path}.after"),
            semantic_before_hash=optional_hash(
                obj["semantic_before_hash"],
                f"{path}.semantic_before_hash",
            ),
            semantic_after_hash=optional_hash(
                obj["semantic_after_hash"],
                f"{path}.semantic_after_hash",
            ),
            substantive=required_bool(
                obj["substantive"], f"{path}.substantive"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "path": self.path,
            "change_kind": self.change_kind,
            "component_kind": self.component_kind,
            "before": None if self.before is None else self.before.to_json(),
            "after": None if self.after is None else self.after.to_json(),
            "semantic_before_hash": self.semantic_before_hash,
            "semantic_after_hash": self.semantic_after_hash,
            "substantive": self.substantive,
        }
