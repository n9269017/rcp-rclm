from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object

PACKAGE_MANIFEST_SCHEMA_ID: Final[str] = "runtime.package_manifest.v2"


@dataclass(frozen=True, slots=True)
class PackageManifestRecord:
    package_id: str
    parent_package_id: str | None
    parent_manifest_hash: str | None
    semantic_tree_hash: str
    candidate_hash: str
    certificate_packet_hash: str
    checker_policy_hash: str
    lean_verifier_policy_hash: str
    trust_anchor_hash: str
    resource_record_hash: str
    claim_boundary_hash: str
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PACKAGE_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.package_id, "package_manifest.package_id")
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "package_manifest.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        parent_id_present = self.parent_package_id is not None
        parent_hash_present = self.parent_manifest_hash is not None
        if parent_id_present != parent_hash_present:
            raise SchemaValidationError(
                "package_manifest.parent",
                "parent package ID and parent manifest hash must both be null or both be present",
            )
        if self.parent_package_id is not None:
            require_string(self.parent_package_id, "package_manifest.parent_package_id")
        if self.parent_manifest_hash is not None:
            validate_hash256(
                self.parent_manifest_hash,
                "package_manifest.parent_manifest_hash",
            )
        for field_name in (
            "semantic_tree_hash",
            "candidate_hash",
            "certificate_packet_hash",
            "checker_policy_hash",
            "lean_verifier_policy_hash",
            "trust_anchor_hash",
            "resource_record_hash",
            "claim_boundary_hash",
        ):
            validate_hash256(getattr(self, field_name), f"package_manifest.{field_name}")

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "package_manifest",
    ) -> PackageManifestRecord:
        fields = {
            "schema_id",
            "contract_version",
            "package_id",
            "parent_package_id",
            "parent_manifest_hash",
            "semantic_tree_hash",
            "candidate_hash",
            "certificate_packet_hash",
            "checker_policy_hash",
            "lean_verifier_policy_hash",
            "trust_anchor_hash",
            "resource_record_hash",
            "claim_boundary_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        contract_version = require_string(obj["contract_version"], f"{path}.contract_version")
        package_id = require_string(obj["package_id"], f"{path}.package_id")
        parent_package_id_raw = obj["parent_package_id"]
        if parent_package_id_raw is not None and not isinstance(parent_package_id_raw, str):
            raise SchemaValidationError(f"{path}.parent_package_id", "expected string or null")
        parent_manifest_hash_raw = obj["parent_manifest_hash"]
        if parent_manifest_hash_raw is not None and not isinstance(parent_manifest_hash_raw, str):
            raise SchemaValidationError(f"{path}.parent_manifest_hash", "expected string or null")

        hash_values: dict[str, str] = {}
        for field_name in (
            "semantic_tree_hash",
            "candidate_hash",
            "certificate_packet_hash",
            "checker_policy_hash",
            "lean_verifier_policy_hash",
            "trust_anchor_hash",
            "resource_record_hash",
            "claim_boundary_hash",
        ):
            hash_value = require_string(obj[field_name], f"{path}.{field_name}")
            validate_hash256(hash_value, f"{path}.{field_name}")
            hash_values[field_name] = hash_value

        return cls(
            package_id=package_id,
            parent_package_id=parent_package_id_raw,
            parent_manifest_hash=parent_manifest_hash_raw,
            semantic_tree_hash=hash_values["semantic_tree_hash"],
            candidate_hash=hash_values["candidate_hash"],
            certificate_packet_hash=hash_values["certificate_packet_hash"],
            checker_policy_hash=hash_values["checker_policy_hash"],
            lean_verifier_policy_hash=hash_values["lean_verifier_policy_hash"],
            trust_anchor_hash=hash_values["trust_anchor_hash"],
            resource_record_hash=hash_values["resource_record_hash"],
            claim_boundary_hash=hash_values["claim_boundary_hash"],
            contract_version=contract_version,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "package_id": self.package_id,
            "parent_package_id": self.parent_package_id,
            "parent_manifest_hash": self.parent_manifest_hash,
            "semantic_tree_hash": self.semantic_tree_hash,
            "candidate_hash": self.candidate_hash,
            "certificate_packet_hash": self.certificate_packet_hash,
            "checker_policy_hash": self.checker_policy_hash,
            "lean_verifier_policy_hash": self.lean_verifier_policy_hash,
            "trust_anchor_hash": self.trust_anchor_hash,
            "resource_record_hash": self.resource_record_hash,
            "claim_boundary_hash": self.claim_boundary_hash,
        }

    def content_hash(self) -> str:
        return canonical_json_hash(self.to_json())
