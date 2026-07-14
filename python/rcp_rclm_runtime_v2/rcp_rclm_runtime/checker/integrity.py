from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    canonical_json_hash,
    file_record_from_bytes,
    semantic_tree_hash,
    validate_hash256,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.mathematics.rational import parse_canonical_nonnegative_integer
from rcp_rclm_runtime.schema._common import (
    require_schema_id,
    require_string,
    strict_object,
)
from rcp_rclm_runtime.schema.package import PackageManifestRecord
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.policy import (
    CHECKER_POLICY_HASH,
    CLAIM_BOUNDARY_HASH,
    LEAN_VERIFIER_POLICY_HASH,
)
from rcp_rclm_runtime.checker.records import ComponentResultRecord, Phase3CheckerRequest

PACKAGE_INTEGRITY_SCHEMA_ID: Final[str] = "runtime.phase4_package_integrity.v2"
PHASE_3_MANIFEST_HASH: Final[str] = (
    "cbe7956c0a7d227fd39d6e24970adbf8801d4b2c2d9b319aebcb574cf2e03365"
)


@dataclass(frozen=True, slots=True)
class PackageIntegrityRecord:
    predecessor_manifest: PackageManifestRecord
    candidate_manifest: PackageManifestRecord
    predecessor_files: Sequence[SemanticFileRecord]
    candidate_files: Sequence[SemanticFileRecord]
    checker_manifest_hash: str
    transition_binding_hash: str

    schema_id: ClassVar[str] = PACKAGE_INTEGRITY_SCHEMA_ID

    def __post_init__(self) -> None:
        predecessor_files = tuple(self.predecessor_files)
        candidate_files = tuple(self.candidate_files)
        _require_sorted_unique_paths(predecessor_files, "package_integrity.predecessor_files")
        _require_sorted_unique_paths(candidate_files, "package_integrity.candidate_files")
        object.__setattr__(self, "predecessor_files", predecessor_files)
        object.__setattr__(self, "candidate_files", candidate_files)
        validate_hash256(
            self.checker_manifest_hash,
            "package_integrity.checker_manifest_hash",
        )
        validate_hash256(
            self.transition_binding_hash,
            "package_integrity.transition_binding_hash",
        )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "package_integrity",
    ) -> PackageIntegrityRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "predecessor_manifest",
                "candidate_manifest",
                "predecessor_files",
                "candidate_files",
                "checker_manifest_hash",
                "transition_binding_hash",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        predecessor_files = _parse_file_array(
            obj["predecessor_files"],
            f"{path}.predecessor_files",
        )
        candidate_files = _parse_file_array(
            obj["candidate_files"],
            f"{path}.candidate_files",
        )
        checker_manifest_hash = require_string(
            obj["checker_manifest_hash"],
            f"{path}.checker_manifest_hash",
        )
        transition_binding_hash = require_string(
            obj["transition_binding_hash"],
            f"{path}.transition_binding_hash",
        )
        validate_hash256(checker_manifest_hash, f"{path}.checker_manifest_hash")
        validate_hash256(transition_binding_hash, f"{path}.transition_binding_hash")
        return cls(
            predecessor_manifest=PackageManifestRecord.from_json(
                obj["predecessor_manifest"],
                f"{path}.predecessor_manifest",
            ),
            candidate_manifest=PackageManifestRecord.from_json(
                obj["candidate_manifest"],
                f"{path}.candidate_manifest",
            ),
            predecessor_files=predecessor_files,
            candidate_files=candidate_files,
            checker_manifest_hash=checker_manifest_hash,
            transition_binding_hash=transition_binding_hash,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "predecessor_manifest": self.predecessor_manifest.to_json(),
            "candidate_manifest": self.candidate_manifest.to_json(),
            "predecessor_files": [item.to_json() for item in self.predecessor_files],
            "candidate_files": [item.to_json() for item in self.candidate_files],
            "checker_manifest_hash": self.checker_manifest_hash,
            "transition_binding_hash": self.transition_binding_hash,
        }


def transition_binding_hash(
    request: Phase3CheckerRequest,
    predecessor_manifest_hash: str,
) -> str:
    validate_hash256(predecessor_manifest_hash, "predecessor_manifest_hash")
    return canonical_json_hash(
        {
            "schema_id": "runtime.phase4_transition_binding.v2",
            "transition_id": request.transition_id,
            "predecessor_manifest_hash": predecessor_manifest_hash,
            "predecessor_state_hash": canonical_json_hash(request.predecessor.to_json()),
            "candidate_hash": canonical_json_hash(request.candidate.to_json()),
            "certificate_hash": canonical_json_hash(request.certificate.to_json()),
            "evaluation_evidence_hash": canonical_json_hash(
                request.evaluation_evidence.to_json()
            ),
            "lean_bridge_report_hash": request.lean_bridge_report.report_hash,
        }
    )


def build_reference_package_integrity(
    request: Phase3CheckerRequest,
) -> PackageIntegrityRecord:
    predecessor_files, candidate_files = _reference_file_records(request)
    trust_anchor_hash = canonical_json_hash(request.trust_anchor.to_json())
    resource_record_hash = canonical_json_hash(request.resource_record.to_json())
    predecessor_manifest = PackageManifestRecord(
        package_id=f"{request.transition_id}.predecessor",
        parent_package_id=None,
        parent_manifest_hash=None,
        semantic_tree_hash=semantic_tree_hash(predecessor_files),
        candidate_hash=canonical_json_hash(request.predecessor.to_json()),
        certificate_packet_hash=_root_certificate_hash(request.transition_id),
        checker_policy_hash=CHECKER_POLICY_HASH,
        lean_verifier_policy_hash=LEAN_VERIFIER_POLICY_HASH,
        trust_anchor_hash=trust_anchor_hash,
        resource_record_hash=resource_record_hash,
        claim_boundary_hash=CLAIM_BOUNDARY_HASH,
    )
    predecessor_manifest_hash = predecessor_manifest.content_hash()
    candidate_manifest = PackageManifestRecord(
        package_id=f"{request.transition_id}.candidate",
        parent_package_id=predecessor_manifest.package_id,
        parent_manifest_hash=predecessor_manifest_hash,
        semantic_tree_hash=semantic_tree_hash(candidate_files),
        candidate_hash=canonical_json_hash(request.candidate.to_json()),
        certificate_packet_hash=canonical_json_hash(request.certificate.to_json()),
        checker_policy_hash=CHECKER_POLICY_HASH,
        lean_verifier_policy_hash=LEAN_VERIFIER_POLICY_HASH,
        trust_anchor_hash=trust_anchor_hash,
        resource_record_hash=resource_record_hash,
        claim_boundary_hash=CLAIM_BOUNDARY_HASH,
    )
    return PackageIntegrityRecord(
        predecessor_manifest=predecessor_manifest,
        candidate_manifest=candidate_manifest,
        predecessor_files=predecessor_files,
        candidate_files=candidate_files,
        checker_manifest_hash=PHASE_3_MANIFEST_HASH,
        transition_binding_hash=transition_binding_hash(
            request,
            predecessor_manifest_hash,
        ),
    )


def check_package_integrity(
    request: Phase3CheckerRequest,
    integrity: PackageIntegrityRecord,
) -> ComponentResultRecord:
    predecessor_manifest_hash = integrity.predecessor_manifest.content_hash()
    expected_binding_hash = transition_binding_hash(request, predecessor_manifest_hash)
    expected_trust_anchor_hash = canonical_json_hash(request.trust_anchor.to_json())
    expected_resource_record_hash = canonical_json_hash(request.resource_record.to_json())
    expected_predecessor_files, expected_candidate_files = _reference_file_records(request)
    predecessor = integrity.predecessor_manifest
    candidate = integrity.candidate_manifest
    checks = {
        "predecessor_file_records_match_request": (
            integrity.predecessor_files == expected_predecessor_files
        ),
        "candidate_file_records_match_request": (
            integrity.candidate_files == expected_candidate_files
        ),
        "predecessor_tree_hash": (
            semantic_tree_hash(integrity.predecessor_files)
            == predecessor.semantic_tree_hash
        ),
        "candidate_tree_hash": (
            semantic_tree_hash(integrity.candidate_files)
            == candidate.semantic_tree_hash
        ),
        "predecessor_package_id": (
            predecessor.package_id == f"{request.transition_id}.predecessor"
        ),
        "candidate_package_id": (
            candidate.package_id == f"{request.transition_id}.candidate"
        ),
        "parent_package_id": (
            candidate.parent_package_id == predecessor.package_id
        ),
        "parent_manifest_hash": (
            candidate.parent_manifest_hash == predecessor_manifest_hash
        ),
        "predecessor_state_hash": (
            predecessor.candidate_hash
            == canonical_json_hash(request.predecessor.to_json())
        ),
        "predecessor_root_certificate_hash": (
            predecessor.certificate_packet_hash
            == _root_certificate_hash(request.transition_id)
        ),
        "candidate_hash": (
            candidate.candidate_hash
            == canonical_json_hash(request.candidate.to_json())
        ),
        "certificate_packet_hash": (
            candidate.certificate_packet_hash
            == canonical_json_hash(request.certificate.to_json())
        ),
        "predecessor_checker_policy_hash": (
            predecessor.checker_policy_hash == CHECKER_POLICY_HASH
        ),
        "candidate_checker_policy_hash": (
            candidate.checker_policy_hash == CHECKER_POLICY_HASH
        ),
        "predecessor_lean_verifier_policy_hash": (
            predecessor.lean_verifier_policy_hash == LEAN_VERIFIER_POLICY_HASH
        ),
        "candidate_lean_verifier_policy_hash": (
            candidate.lean_verifier_policy_hash == LEAN_VERIFIER_POLICY_HASH
        ),
        "predecessor_trust_anchor_hash": (
            predecessor.trust_anchor_hash == expected_trust_anchor_hash
        ),
        "candidate_trust_anchor_hash": (
            candidate.trust_anchor_hash == expected_trust_anchor_hash
        ),
        "predecessor_resource_record_hash": (
            predecessor.resource_record_hash == expected_resource_record_hash
        ),
        "candidate_resource_record_hash": (
            candidate.resource_record_hash == expected_resource_record_hash
        ),
        "predecessor_claim_boundary_hash": (
            predecessor.claim_boundary_hash == CLAIM_BOUNDARY_HASH
        ),
        "candidate_claim_boundary_hash": (
            candidate.claim_boundary_hash == CLAIM_BOUNDARY_HASH
        ),
        "checker_manifest_hash": (
            integrity.checker_manifest_hash == PHASE_3_MANIFEST_HASH
        ),
        "transition_binding_hash": (
            integrity.transition_binding_hash == expected_binding_hash
        ),
    }
    reasons: list[ReasonCode] = []
    link_fields = (
        "predecessor_package_id",
        "candidate_package_id",
        "parent_package_id",
        "parent_manifest_hash",
    )
    if not all(checks[field] for field in link_fields):
        reasons.append(ReasonCode.PARENT_LINK_MISMATCH)
    hash_fields = tuple(
        field
        for field in checks
        if field not in {*link_fields, "transition_binding_hash"}
    )
    if not all(checks[field] for field in hash_fields):
        reasons.append(ReasonCode.HASH_MISMATCH)
    if not checks["checker_manifest_hash"] or not checks["transition_binding_hash"]:
        reasons.append(ReasonCode.PROVENANCE_FAILED)
    unique_reasons = tuple(dict.fromkeys(reasons))
    return ComponentResultRecord.from_evidence(
        "pass" if not unique_reasons else "fail",
        unique_reasons,
        {
            **checks,
            "predecessor_manifest_hash": predecessor_manifest_hash,
            "expected_transition_binding_hash": expected_binding_hash,
            "observed_transition_binding_hash": integrity.transition_binding_hash,
            "expected_checker_manifest_hash": PHASE_3_MANIFEST_HASH,
            "observed_checker_manifest_hash": integrity.checker_manifest_hash,
        },
    )


def _reference_file_records(
    request: Phase3CheckerRequest,
) -> tuple[tuple[SemanticFileRecord, ...], tuple[SemanticFileRecord, ...]]:
    predecessor_files = (
        file_record_from_bytes(
            "state/predecessor.json",
            "0644",
            canonical_json_bytes(request.predecessor.to_json()),
        ),
    )
    candidate_files = (
        file_record_from_bytes(
            "candidate/successor.json",
            "0644",
            canonical_json_bytes(request.candidate.next.to_json()),
        ),
        file_record_from_bytes(
            "candidate/update.json",
            "0644",
            canonical_json_bytes(request.candidate.update.to_json()),
        ),
    )
    return predecessor_files, candidate_files


def _root_certificate_hash(transition_id: str) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.phase4_root_certificate.v2",
            "transition_id": transition_id,
        }
    )


def _parse_file_array(value: object, path: str) -> Sequence[SemanticFileRecord]:
    if not isinstance(value, list):
        raise TypeError(f"{path} must be an array")
    return tuple(
        _semantic_file_record_from_json(item, f"{path}[{index}]")
        for index, item in enumerate(value)
    )


def _semantic_file_record_from_json(
    value: object,
    path: str,
) -> SemanticFileRecord:
    obj = strict_object(value, path, {"path", "mode", "size", "sha256"})
    size = parse_canonical_nonnegative_integer(obj["size"], f"{path}.size")
    sha256 = require_string(obj["sha256"], f"{path}.sha256")
    validate_hash256(sha256, f"{path}.sha256")
    return SemanticFileRecord(
        path=require_string(obj["path"], f"{path}.path"),
        mode=require_string(obj["mode"], f"{path}.mode"),
        size=size,
        sha256=sha256,
    )


def _require_sorted_unique_paths(
    records: Sequence[SemanticFileRecord],
    path: str,
) -> None:
    paths = [item.path for item in records]
    if paths != sorted(paths, key=lambda item: item.encode("utf-8")):
        raise ValueError(f"{path} must be sorted by UTF-8 path bytes")
    if len(paths) != len(set(paths)):
        raise ValueError(f"{path} contains duplicate paths")
