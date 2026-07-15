from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex, validate_hash256
from rcp_rclm_runtime.canonical.paths import validate_file_mode, validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.successor._record_common import FileOperationKind, PHASE6_OPERATION_SCHEMA_ID, SUBSTANTIVE_COMPONENT_KINDS, SubstantiveComponentKind, component_path_matches, literal, optional_hash, optional_mode, optional_string, require_exact_set

@dataclass(frozen=True, slots=True)
class SelectedFileOperationRecord:
    path: str
    operation: FileOperationKind
    component_kind: SubstantiveComponentKind | None
    expected_before_hash: str | None
    expected_before_mode: str | None
    after_mode: str | None
    content_base64: str | None
    after_hash: str | None

    schema_id: ClassVar[str] = PHASE6_OPERATION_SCHEMA_ID

    def __post_init__(self) -> None:
        validate_semantic_path(self.path)
        if self.path == "manifest.json" or self.path.startswith("evidence/") or self.path.startswith(
            "rollback/"
        ):
            raise SchemaValidationError(
                "phase6_operation.path",
                "control-plane package paths cannot be modified by a proposal",
            )
        require_exact_set(
            self.operation,
            {"write", "delete"},
            "phase6_operation.operation",
        )
        if self.component_kind is not None:
            require_exact_set(
                self.component_kind,
                set(SUBSTANTIVE_COMPONENT_KINDS),
                "phase6_operation.component_kind",
            )
            if not component_path_matches(self.component_kind, self.path):
                raise SchemaValidationError(
                    "phase6_operation.component_kind",
                    "component kind is not permitted for the selected path",
                )
        if self.expected_before_hash is not None:
            validate_hash256(
                self.expected_before_hash,
                "phase6_operation.expected_before_hash",
            )
        if self.expected_before_mode is not None:
            validate_file_mode(self.expected_before_mode)
        if self.operation == "write":
            if self.after_mode is None or self.content_base64 is None or self.after_hash is None:
                raise SchemaValidationError(
                    "phase6_operation",
                    "write operation requires mode, content, and after hash",
                )
            validate_file_mode(self.after_mode)
            validate_hash256(self.after_hash, "phase6_operation.after_hash")
            content = self.decoded_content()
            if sha256_hex(content) != self.after_hash:
                raise SchemaValidationError(
                    "phase6_operation.after_hash",
                    "after hash does not match decoded content",
                )
        else:
            if self.expected_before_hash is None or self.expected_before_mode is None:
                raise SchemaValidationError(
                    "phase6_operation",
                    "delete operation requires expected before hash and mode",
                )
            if self.after_mode is not None or self.content_base64 is not None or self.after_hash is not None:
                raise SchemaValidationError(
                    "phase6_operation",
                    "delete operation cannot contain after content",
                )

    @classmethod
    def write(
        cls,
        *,
        path: str,
        component_kind: SubstantiveComponentKind | None,
        expected_before_hash: str | None,
        expected_before_mode: str | None,
        after_mode: str,
        content: bytes,
    ) -> SelectedFileOperationRecord:
        return cls(
            path=path,
            operation="write",
            component_kind=component_kind,
            expected_before_hash=expected_before_hash,
            expected_before_mode=expected_before_mode,
            after_mode=after_mode,
            content_base64=base64.b64encode(content).decode("ascii"),
            after_hash=sha256_hex(content),
        )

    def decoded_content(self) -> bytes:
        if self.content_base64 is None:
            return b""
        try:
            return base64.b64decode(self.content_base64.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error) as exc:
            raise SchemaValidationError(
                "phase6_operation.content_base64",
                "expected canonical base64 content",
            ) from exc

    @property
    def operation_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_operation",
    ) -> SelectedFileOperationRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "path",
                "operation",
                "component_kind",
                "expected_before_hash",
                "expected_before_mode",
                "after_mode",
                "content_base64",
                "after_hash",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        component_raw = obj["component_kind"]
        component = (
            None
            if component_raw is None
            else literal(
                component_raw,
                f"{path}.component_kind",
                set(SUBSTANTIVE_COMPONENT_KINDS),
            )
        )
        return cls(
            path=validate_semantic_path(
                require_string(obj["path"], f"{path}.path")
            ),
            operation=literal(
                obj["operation"], f"{path}.operation", {"write", "delete"}
            ),
            component_kind=component,
            expected_before_hash=optional_hash(
                obj["expected_before_hash"], f"{path}.expected_before_hash"
            ),
            expected_before_mode=optional_mode(
                obj["expected_before_mode"], f"{path}.expected_before_mode"
            ),
            after_mode=optional_mode(obj["after_mode"], f"{path}.after_mode"),
            content_base64=optional_string(
                obj["content_base64"], f"{path}.content_base64"
            ),
            after_hash=optional_hash(obj["after_hash"], f"{path}.after_hash"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "path": self.path,
            "operation": self.operation,
            "component_kind": self.component_kind,
            "expected_before_hash": self.expected_before_hash,
            "expected_before_mode": self.expected_before_mode,
            "after_mode": self.after_mode,
            "content_base64": self.content_base64,
            "after_hash": self.after_hash,
        }
