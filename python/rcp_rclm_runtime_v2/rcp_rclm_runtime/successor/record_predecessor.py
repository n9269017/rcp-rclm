from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, require_structural_integer, strict_object
from rcp_rclm_runtime.successor._record_common import PHASE6_PREDECESSOR_MANIFEST_SCHEMA_ID, require_nonnegative, required_hash

@dataclass(frozen=True, slots=True)
class Phase6PredecessorManifestRecord:
    package_id: str
    phase5_manifest_hash: str
    payload_tree_hash: str
    state_path: str
    state_hash: str
    file_count: int
    total_bytes: int
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE6_PREDECESSOR_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.package_id, "phase6_predecessor_manifest.package_id")
        validate_hash256(
            self.phase5_manifest_hash,
            "phase6_predecessor_manifest.phase5_manifest_hash",
        )
        validate_hash256(
            self.payload_tree_hash,
            "phase6_predecessor_manifest.payload_tree_hash",
        )
        validate_semantic_path(self.state_path)
        validate_hash256(self.state_hash, "phase6_predecessor_manifest.state_hash")
        require_nonnegative(
            self.file_count,
            "phase6_predecessor_manifest.file_count",
        )
        require_nonnegative(
            self.total_bytes,
            "phase6_predecessor_manifest.total_bytes",
        )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase6_predecessor_manifest.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_predecessor_manifest",
    ) -> Phase6PredecessorManifestRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "contract_version",
                "package_id",
                "phase5_manifest_hash",
                "payload_tree_hash",
                "state_path",
                "state_hash",
                "file_count",
                "total_bytes",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            package_id=require_string(obj["package_id"], f"{path}.package_id"),
            phase5_manifest_hash=required_hash(
                obj["phase5_manifest_hash"], f"{path}.phase5_manifest_hash"
            ),
            payload_tree_hash=required_hash(
                obj["payload_tree_hash"], f"{path}.payload_tree_hash"
            ),
            state_path=validate_semantic_path(
                require_string(obj["state_path"], f"{path}.state_path")
            ),
            state_hash=required_hash(obj["state_hash"], f"{path}.state_hash"),
            file_count=require_structural_integer(
                obj["file_count"], f"{path}.file_count", minimum=0
            ),
            total_bytes=require_structural_integer(
                obj["total_bytes"], f"{path}.total_bytes", minimum=0
            ),
            contract_version=require_string(
                obj["contract_version"], f"{path}.contract_version"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "package_id": self.package_id,
            "phase5_manifest_hash": self.phase5_manifest_hash,
            "payload_tree_hash": self.payload_tree_hash,
            "state_path": self.state_path,
            "state_hash": self.state_hash,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
        }
