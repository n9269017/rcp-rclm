from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.successor._record_common import CandidateStatus, PHASE6_CANDIDATE_MANIFEST_SCHEMA_ID, SUBSTANTIVE_COMPONENT_KINDS, SubstantiveComponentKind, literal, require_exact, required_hash

@dataclass(frozen=True, slots=True)
class Phase6CandidateManifestRecord:
    package_id: str
    parent_package_id: str
    parent_manifest_hash: str
    payload_tree_hash: str
    proposal_hash: str
    selection_hash: str
    change_ledger_hash: str
    command_log_hash: str
    environment_hash: str
    resource_usage_hash: str
    rollback_snapshot_hash: str
    substantive_component_kinds: Sequence[SubstantiveComponentKind]
    candidate_status: CandidateStatus = "realized_unverified"
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE6_CANDIDATE_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.package_id, "phase6_candidate_manifest.package_id")
        require_string(
            self.parent_package_id,
            "phase6_candidate_manifest.parent_package_id",
        )
        for name, value in (
            ("parent_manifest_hash", self.parent_manifest_hash),
            ("payload_tree_hash", self.payload_tree_hash),
            ("proposal_hash", self.proposal_hash),
            ("selection_hash", self.selection_hash),
            ("change_ledger_hash", self.change_ledger_hash),
            ("command_log_hash", self.command_log_hash),
            ("environment_hash", self.environment_hash),
            ("resource_usage_hash", self.resource_usage_hash),
            ("rollback_snapshot_hash", self.rollback_snapshot_hash),
        ):
            validate_hash256(value, f"phase6_candidate_manifest.{name}")
        components = tuple(self.substantive_component_kinds)
        object.__setattr__(self, "substantive_component_kinds", components)
        if components != tuple(sorted(set(components))):
            raise SchemaValidationError(
                "phase6_candidate_manifest.substantive_component_kinds",
                "component kinds must be unique and sorted",
            )
        if not components:
            raise SchemaValidationError(
                "phase6_candidate_manifest.substantive_component_kinds",
                "candidate requires a substantive component",
            )
        require_exact(
            self.candidate_status,
            "realized_unverified",
            "phase6_candidate_manifest.candidate_status",
        )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase6_candidate_manifest.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_candidate_manifest",
    ) -> Phase6CandidateManifestRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "contract_version",
                "package_id",
                "parent_package_id",
                "parent_manifest_hash",
                "payload_tree_hash",
                "proposal_hash",
                "selection_hash",
                "change_ledger_hash",
                "command_log_hash",
                "environment_hash",
                "resource_usage_hash",
                "rollback_snapshot_hash",
                "substantive_component_kinds",
                "candidate_status",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        components_raw = obj["substantive_component_kinds"]
        if not isinstance(components_raw, list):
            raise SchemaValidationError(
                f"{path}.substantive_component_kinds",
                "expected an array",
            )
        return cls(
            package_id=require_string(obj["package_id"], f"{path}.package_id"),
            parent_package_id=require_string(
                obj["parent_package_id"], f"{path}.parent_package_id"
            ),
            parent_manifest_hash=required_hash(
                obj["parent_manifest_hash"], f"{path}.parent_manifest_hash"
            ),
            payload_tree_hash=required_hash(
                obj["payload_tree_hash"], f"{path}.payload_tree_hash"
            ),
            proposal_hash=required_hash(
                obj["proposal_hash"], f"{path}.proposal_hash"
            ),
            selection_hash=required_hash(
                obj["selection_hash"], f"{path}.selection_hash"
            ),
            change_ledger_hash=required_hash(
                obj["change_ledger_hash"], f"{path}.change_ledger_hash"
            ),
            command_log_hash=required_hash(
                obj["command_log_hash"], f"{path}.command_log_hash"
            ),
            environment_hash=required_hash(
                obj["environment_hash"], f"{path}.environment_hash"
            ),
            resource_usage_hash=required_hash(
                obj["resource_usage_hash"], f"{path}.resource_usage_hash"
            ),
            rollback_snapshot_hash=required_hash(
                obj["rollback_snapshot_hash"],
                f"{path}.rollback_snapshot_hash",
            ),
            substantive_component_kinds=tuple(
                literal(
                    item,
                    f"{path}.substantive_component_kinds[{index}]",
                    set(SUBSTANTIVE_COMPONENT_KINDS),
                )
                for index, item in enumerate(components_raw)
            ),
            candidate_status=literal(
                obj["candidate_status"],
                f"{path}.candidate_status",
                {"realized_unverified"},
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
            "parent_package_id": self.parent_package_id,
            "parent_manifest_hash": self.parent_manifest_hash,
            "payload_tree_hash": self.payload_tree_hash,
            "proposal_hash": self.proposal_hash,
            "selection_hash": self.selection_hash,
            "change_ledger_hash": self.change_ledger_hash,
            "command_log_hash": self.command_log_hash,
            "environment_hash": self.environment_hash,
            "resource_usage_hash": self.resource_usage_hash,
            "rollback_snapshot_hash": self.rollback_snapshot_hash,
            "substantive_component_kinds": list(self.substantive_component_kinds),
            "candidate_status": self.candidate_status,
        }
