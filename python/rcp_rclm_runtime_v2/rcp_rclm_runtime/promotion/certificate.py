from __future__ import annotations

from dataclasses import dataclass

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.checker.reference import canonical_rclm_certificate
from rcp_rclm_runtime.generator.grammar import certificate_name_for_word
from rcp_rclm_runtime.generator.protocol import ReferenceProposalRecord
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord


@dataclass(frozen=True, slots=True)
class Phase7CertificateEvidence:
    certificate_name: str
    certificate: RclmCertificatePacketRecord

    @property
    def certificate_hash(self) -> str:
        return canonical_json_hash(self.certificate.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.phase7_certificate_evidence.v2",
            "certificate_name": self.certificate_name,
            "certificate": self.certificate.to_json(),
            "certificate_hash": self.certificate_hash,
            "generator_certificate_field_consumed": False,
            "manual_repair_consumed": False,
        }


def construct_reference_certificate(
    proposal: ReferenceProposalRecord,
) -> Phase7CertificateEvidence:
    certificate_name = certificate_name_for_word(proposal.word)
    certificate = canonical_rclm_certificate(
        "gate_b_classical",
        certificate_name,
    )
    return Phase7CertificateEvidence(
        certificate_name=certificate_name,
        certificate=certificate,
    )
