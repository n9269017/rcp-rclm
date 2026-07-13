from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Literal, TypeAlias

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    TypedArtifactRecord,
    require_schema_id,
    strict_object,
)

ClassicalBinaryCertificateName: TypeAlias = Literal["improvement", "stability", "malformed"]
QuantumCertificateName: TypeAlias = Literal["improvement", "stability", "malformed"]

RCLM_CERTIFICATE_PACKET_SCHEMA_ID: Final[str] = "rclm.certificate_packet.v2"
CLASSICAL_CERTIFICATE_ARTIFACT_SCHEMA_ID: Final[str] = "gate_b.binary_certificate.v2"
QUANTUM_CERTIFICATE_ARTIFACT_SCHEMA_ID: Final[str] = "gate_c.quantum_certificate.v2"


@dataclass(frozen=True, slots=True)
class RclmCertificatePacketRecord:
    core: TypedArtifactRecord
    semantics: TypedArtifactRecord
    typing: TypedArtifactRecord
    ledger: TypedArtifactRecord
    goal_transport: TypedArtifactRecord
    trust: TypedArtifactRecord
    resources: TypedArtifactRecord
    reality: TypedArtifactRecord
    recovery: TypedArtifactRecord
    progress: TypedArtifactRecord

    schema_id: ClassVar[str] = RCLM_CERTIFICATE_PACKET_SCHEMA_ID

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "rclm_certificate_packet",
    ) -> RclmCertificatePacketRecord:
        fields = {
            "schema_id",
            "core",
            "semantics",
            "typing",
            "ledger",
            "goal_transport",
            "trust",
            "resources",
            "reality",
            "recovery",
            "progress",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            core=TypedArtifactRecord.from_json(obj["core"], f"{path}.core"),
            semantics=TypedArtifactRecord.from_json(obj["semantics"], f"{path}.semantics"),
            typing=TypedArtifactRecord.from_json(obj["typing"], f"{path}.typing"),
            ledger=TypedArtifactRecord.from_json(obj["ledger"], f"{path}.ledger"),
            goal_transport=TypedArtifactRecord.from_json(
                obj["goal_transport"], f"{path}.goal_transport"
            ),
            trust=TypedArtifactRecord.from_json(obj["trust"], f"{path}.trust"),
            resources=TypedArtifactRecord.from_json(obj["resources"], f"{path}.resources"),
            reality=TypedArtifactRecord.from_json(obj["reality"], f"{path}.reality"),
            recovery=TypedArtifactRecord.from_json(obj["recovery"], f"{path}.recovery"),
            progress=TypedArtifactRecord.from_json(obj["progress"], f"{path}.progress"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "core": self.core.to_json(),
            "semantics": self.semantics.to_json(),
            "typing": self.typing.to_json(),
            "ledger": self.ledger.to_json(),
            "goal_transport": self.goal_transport.to_json(),
            "trust": self.trust.to_json(),
            "resources": self.resources.to_json(),
            "reality": self.reality.to_json(),
            "recovery": self.recovery.to_json(),
            "progress": self.progress.to_json(),
        }


def classical_core_certificate(
    certificate: ClassicalBinaryCertificateName,
) -> TypedArtifactRecord:
    if certificate not in {"improvement", "stability", "malformed"}:
        raise SchemaValidationError("certificate", f"unknown classical certificate: {certificate}")
    return TypedArtifactRecord.from_value(
        CLASSICAL_CERTIFICATE_ARTIFACT_SCHEMA_ID,
        {"certificate": certificate},
    )


def quantum_core_certificate(
    certificate: QuantumCertificateName,
) -> TypedArtifactRecord:
    if certificate not in {"improvement", "stability", "malformed"}:
        raise SchemaValidationError("certificate", f"unknown quantum certificate: {certificate}")
    return TypedArtifactRecord.from_value(
        QUANTUM_CERTIFICATE_ARTIFACT_SCHEMA_ID,
        {"certificate": certificate},
    )
