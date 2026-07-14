from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime._version import FORMAL_SOURCE_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.schema._common import (
    TypedArtifactRecord,
    require_schema_id,
    strict_object,
)
from rcp_rclm_runtime.schema.candidate import CandidateRecord
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord
from rcp_rclm_runtime.schema.state import RclmStateRecord, RcpStateRecord
from rcp_rclm_runtime.schema.update import RclmUpdateRecord, RcpUpdateRecord

REFINEMENT_MAPPING_ID: Final[str] = "rclm-to-rcp-selected-gate-b-c-v2"
RCLM_CANDIDATE_SCHEMA_ID: Final[str] = "rclm.candidate.v2"
PRESERVED_KERNEL_FIELDS: Final[Sequence[str]] = (
    "apply",
    "admissible",
    "protected_invariant",
    "protected_value",
    "transport_protected",
    "loss_budget",
    "state_distance",
    "recover",
    "recovery_budget",
    "progress",
    "strict_witness",
    "residual",
    "trust_valid",
    "resource_valid",
    "reality_contained",
)


@dataclass(frozen=True, slots=True)
class RclmCandidateRecord:
    update: RclmUpdateRecord
    next: RclmStateRecord

    schema_id: ClassVar[str] = RCLM_CANDIDATE_SCHEMA_ID

    def __post_init__(self) -> None:
        CandidateRecord(update=self.update.core, next=self.next.core)

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "rclm_candidate",
    ) -> RclmCandidateRecord:
        obj = strict_object(value, path, {"schema_id", "update", "next"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            update=RclmUpdateRecord.from_json(obj["update"], f"{path}.update"),
            next=RclmStateRecord.from_json(obj["next"], f"{path}.next"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "update": self.update.to_json(),
            "next": self.next.to_json(),
        }


@dataclass(frozen=True, slots=True)
class KernelRefinementRecord:
    mapping_id: str = REFINEMENT_MAPPING_ID
    formal_source_commit: str = FORMAL_SOURCE_COMMIT
    preserved_fields: Sequence[str] = PRESERVED_KERNEL_FIELDS

    def __post_init__(self) -> None:
        object.__setattr__(self, "preserved_fields", tuple(self.preserved_fields))
        if self.mapping_id != REFINEMENT_MAPPING_ID:
            raise ValueError(f"unexpected refinement mapping ID: {self.mapping_id}")
        if self.formal_source_commit != FORMAL_SOURCE_COMMIT:
            raise ValueError("refinement record is not pinned to the frozen formal source")
        if self.preserved_fields != PRESERVED_KERNEL_FIELDS:
            raise ValueError("refinement preserved-field surface differs from the frozen contract")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "rclm.kernel_refinement.v2",
            "mapping_id": self.mapping_id,
            "formal_source_commit": self.formal_source_commit,
            "preserved_fields": list(self.preserved_fields),
        }


@dataclass(frozen=True, slots=True)
class RefinementMappingEvidence:
    mapping_id: str
    rclm_state_hash: str
    core_state_hash: str
    rclm_update_hash: str
    core_update_hash: str
    rclm_certificate_hash: str
    core_certificate_hash: str

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "rclm.kernel_refinement_evidence.v2",
            "mapping_id": self.mapping_id,
            "rclm_state_hash": self.rclm_state_hash,
            "core_state_hash": self.core_state_hash,
            "rclm_update_hash": self.rclm_update_hash,
            "core_update_hash": self.core_update_hash,
            "rclm_certificate_hash": self.rclm_certificate_hash,
            "core_certificate_hash": self.core_certificate_hash,
        }


def forget_rclm_state(state: RclmStateRecord) -> RcpStateRecord:
    return state.core


def forget_rclm_update(update: RclmUpdateRecord) -> RcpUpdateRecord:
    return update.core


def forget_rclm_certificate(
    certificate: RclmCertificatePacketRecord,
) -> TypedArtifactRecord:
    return certificate.core


def forget_rclm_candidate(candidate: RclmCandidateRecord) -> CandidateRecord:
    return CandidateRecord(
        update=forget_rclm_update(candidate.update),
        next=forget_rclm_state(candidate.next),
    )


def compute_refinement_mapping_evidence(
    state: RclmStateRecord,
    update: RclmUpdateRecord,
    certificate: RclmCertificatePacketRecord,
) -> RefinementMappingEvidence:
    core_state = forget_rclm_state(state)
    core_update = forget_rclm_update(update)
    core_certificate = forget_rclm_certificate(certificate)
    return RefinementMappingEvidence(
        mapping_id=REFINEMENT_MAPPING_ID,
        rclm_state_hash=canonical_json_hash(state.to_json()),
        core_state_hash=canonical_json_hash(core_state.to_json()),
        rclm_update_hash=canonical_json_hash(update.to_json()),
        core_update_hash=canonical_json_hash(core_update.to_json()),
        rclm_certificate_hash=canonical_json_hash(certificate.to_json()),
        core_certificate_hash=canonical_json_hash(core_certificate.to_json()),
    )
