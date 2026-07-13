from __future__ import annotations

from rcp_rclm_runtime.schema._common import TypedArtifactRecord
from rcp_rclm_runtime.schema.certificate import (
    RclmCertificatePacketRecord,
    classical_core_certificate,
)
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord, RclmStateRecord
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord, RclmUpdateRecord


def artifact(name: str, value: object) -> TypedArtifactRecord:
    return TypedArtifactRecord.from_value(f"test.{name}.v2", value)


def sample_rclm_state() -> RclmStateRecord:
    return RclmStateRecord(
        core=ClassicalBinaryStateRecord("initial"),
        language=artifact("language", {"register": "language"}),
        world_reference=artifact("world", {"register": "world"}),
        human_reference=artifact("human", {"register": "human"}),
        definitiveness=artifact("definitiveness", {"value": "declared"}),
        ambiguity=artifact("ambiguity", {"value": "bounded"}),
        memory=artifact("memory", {"entries": []}),
        verifier=artifact("verifier", {"policy": "pinned"}),
        resources=artifact("resources", {"budget": "fixed"}),
        self_model=artifact("self_model", {"version": "v2"}),
    )


def sample_rclm_update() -> RclmUpdateRecord:
    return RclmUpdateRecord(
        core=ClassicalBinaryUpdateRecord("improve"),
        parameters=artifact("parameters_update", {"kind": "unchanged"}),
        architecture=artifact("architecture_update", {"kind": "reference"}),
        memory=artifact("memory_update", {"kind": "append"}),
        verifier=artifact("verifier_update", {"kind": "preserve"}),
        semantics=artifact("semantics_update", {"kind": "transport"}),
        tools=artifact("tools_update", {"kind": "unchanged"}),
        resources=artifact("resource_update", {"cost": "1"}),
    )


def sample_certificate() -> RclmCertificatePacketRecord:
    return RclmCertificatePacketRecord(
        core=classical_core_certificate("improvement"),
        semantics=artifact("semantics_evidence", {"ok": True}),
        typing=artifact("typing_evidence", {"ok": True}),
        ledger=artifact("ledger_evidence", {"ok": True}),
        goal_transport=artifact("goal_transport_evidence", {"ok": True}),
        trust=artifact("trust_evidence", {"ok": True}),
        resources=artifact("resource_evidence", {"ok": True}),
        reality=artifact("reality_evidence", {"ok": True}),
        recovery=artifact("recovery_evidence", {"ok": True}),
        progress=artifact("progress_evidence", {"strict": True}),
    )
