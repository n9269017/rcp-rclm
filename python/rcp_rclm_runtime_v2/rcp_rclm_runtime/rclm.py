from __future__ import annotations

from collections.abc import Mapping

from rcp_rclm_runtime.refinement.mapping import (
    KernelRefinementRecord,
    RclmCandidateRecord,
    RefinementMappingEvidence,
    compute_refinement_mapping_evidence,
    forget_rclm_candidate,
    forget_rclm_certificate,
    forget_rclm_state,
    forget_rclm_update,
)
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.schema.update import RclmUpdateRecord


def validate_rclm_state(value: RclmStateRecord | Mapping[str, object]) -> RclmStateRecord:
    if isinstance(value, RclmStateRecord):
        return value
    return RclmStateRecord.from_json(value)


def validate_rclm_update(value: RclmUpdateRecord | Mapping[str, object]) -> RclmUpdateRecord:
    if isinstance(value, RclmUpdateRecord):
        return value
    return RclmUpdateRecord.from_json(value)


def validate_certificate_packet(
    value: RclmCertificatePacketRecord | Mapping[str, object],
) -> RclmCertificatePacketRecord:
    if isinstance(value, RclmCertificatePacketRecord):
        return value
    return RclmCertificatePacketRecord.from_json(value)


def verify_kernel_refinement(
    state: RclmStateRecord,
    update: RclmUpdateRecord,
    certificate: RclmCertificatePacketRecord,
) -> RefinementMappingEvidence:
    return compute_refinement_mapping_evidence(state, update, certificate)


__all__ = [
    "KernelRefinementRecord",
    "RclmCandidateRecord",
    "RclmCertificatePacketRecord",
    "RclmStateRecord",
    "RclmUpdateRecord",
    "RefinementMappingEvidence",
    "compute_refinement_mapping_evidence",
    "forget_rclm_candidate",
    "forget_rclm_certificate",
    "forget_rclm_state",
    "forget_rclm_update",
    "validate_certificate_packet",
    "validate_rclm_state",
    "validate_rclm_update",
    "verify_kernel_refinement",
]
