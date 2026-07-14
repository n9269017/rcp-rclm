from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime._version import FORMAL_SOURCE_COMMIT, LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError, UnsupportedScopeError
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.mathematics.classical import BIASED_BINARY, binary_state_distribution
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    TARGET_DENSITY,
    quantum_state_density,
)
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema._common import TypedArtifactRecord, strict_object, thaw_json
from rcp_rclm_runtime.schema.certificate import (
    CLASSICAL_CERTIFICATE_ARTIFACT_SCHEMA_ID,
    QUANTUM_CERTIFICATE_ARTIFACT_SCHEMA_ID,
    RclmCertificatePacketRecord,
    classical_core_certificate,
    quantum_core_certificate,
)
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
    RclmStateRecord,
    RcpStateRecord,
)
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    QuantumUpdateRecord,
    RclmUpdateRecord,
    RcpUpdateRecord,
)
from rcp_rclm_runtime.checker.policy import (
    CHECKER_POLICY_HASH,
    CLAIM_BOUNDARY_HASH,
    EVALUATOR_POLICY_HASH,
    FORMAL_MANIFEST_BLOB,
    GATE_C_AUDIT_SHA256,
    LEAN_VERIFIER_POLICY_HASH,
    RESOURCE_METER_POLICY_HASH,
    CheckerScope,
    required_protected_distinctions,
)
from rcp_rclm_runtime.checker.records import (
    EvaluationEvidenceRecord,
    ProtectedDistinctionRecord,
    ResourceRecord,
    TrustAnchorRecord,
)

LANGUAGE_REGISTER_SCHEMA_ID: Final[str] = "rclm.language_register.v2"
WORLD_REFERENCE_REGISTER_SCHEMA_ID: Final[str] = "rclm.world_reference_register.v2"
HUMAN_REFERENCE_REGISTER_SCHEMA_ID: Final[str] = "rclm.human_reference_register.v2"
DEFINITIVENESS_REGISTER_SCHEMA_ID: Final[str] = "rclm.definitiveness_register.v2"
AMBIGUITY_REGISTER_SCHEMA_ID: Final[str] = "rclm.ambiguity_register.v2"
MEMORY_REGISTER_SCHEMA_ID: Final[str] = "rclm.memory_register.v2"
VERIFIER_REGISTER_SCHEMA_ID: Final[str] = "rclm.verifier_register.v2"
RESOURCE_REGISTER_SCHEMA_ID: Final[str] = "rclm.resource_register.v2"
SELF_MODEL_REGISTER_SCHEMA_ID: Final[str] = "rclm.self_model_register.v2"

PARAMETER_UPDATE_SCHEMA_ID: Final[str] = "rclm.parameter_update_register.v2"
ARCHITECTURE_UPDATE_SCHEMA_ID: Final[str] = "rclm.architecture_update_register.v2"
MEMORY_UPDATE_SCHEMA_ID: Final[str] = "rclm.memory_update_register.v2"
VERIFIER_UPDATE_SCHEMA_ID: Final[str] = "rclm.verifier_update_register.v2"
SEMANTIC_UPDATE_SCHEMA_ID: Final[str] = "rclm.semantic_update_register.v2"
TOOL_UPDATE_SCHEMA_ID: Final[str] = "rclm.tool_update_register.v2"
RESOURCE_UPDATE_SCHEMA_ID: Final[str] = "rclm.resource_update_register.v2"

SEMANTIC_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.semantic_evidence.v2"
TYPE_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.type_evidence.v2"
LEDGER_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.ledger_evidence.v2"
GOAL_TRANSPORT_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.goal_transport_evidence.v2"
TRUST_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.trust_evidence.v2"
RESOURCE_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.resource_evidence.v2"
REALITY_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.reality_evidence.v2"
RECOVERY_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.recovery_evidence.v2"
PROGRESS_EVIDENCE_SCHEMA_ID: Final[str] = "rclm.progress_evidence.v2"

CertificateName = str


def _register(schema_id: str, register: str) -> TypedArtifactRecord:
    return TypedArtifactRecord.from_value(schema_id, {"register": register})


def _evidence(schema_id: str, evidence: str) -> TypedArtifactRecord:
    return TypedArtifactRecord.from_value(schema_id, {"evidence": evidence})


def scope_from_core_state(state: RcpStateRecord) -> CheckerScope:
    if isinstance(state, ClassicalBinaryStateRecord):
        return "gate_b_classical"
    if isinstance(state, QuantumStateRecord):
        return "gate_c_diagonal_quantum"
    raise UnsupportedScopeError("state", f"unsupported core state type: {type(state).__name__}")


def canonical_rclm_state(core: RcpStateRecord) -> RclmStateRecord:
    if isinstance(core, ClassicalBinaryStateRecord):
        state = core.state
        if state == "outside":
            registers = (
                "invalid",
                "absent",
                "absent",
                "invalid",
                "uncontrolled",
                "outside",
                "untrusted",
                2,
                1,
                "outside",
            )
        elif state == "initial":
            registers = (
                "symbolicBinary",
                "biasedTarget",
                "declaredBinaryTask",
                "provisional",
                "bounded",
                "initial",
                "trustedBinaryChecker",
                0,
                1,
                "initial",
            )
        else:
            registers = (
                "symbolicBinary",
                "biasedTarget",
                "declaredBinaryTask",
                "certified",
                "resolved",
                "target",
                "trustedBinaryChecker",
                1,
                1,
                "target",
            )
    elif isinstance(core, QuantumStateRecord):
        state = core.state
        if state == "outside":
            registers = (
                "invalid",
                "absent",
                "absent",
                "invalid",
                "uncontrolled",
                "outside",
                "untrusted",
                2,
                1,
                "outside",
            )
        elif state == "source":
            registers = (
                "symbolicBinary",
                "biasedTarget",
                "declaredBinaryTask",
                "provisional",
                "bounded",
                "initial",
                "trustedBinaryChecker",
                0,
                1,
                "initial",
            )
        else:
            registers = (
                "symbolicBinary",
                "biasedTarget",
                "declaredBinaryTask",
                "certified",
                "resolved",
                "target",
                "trustedBinaryChecker",
                1,
                1,
                "target",
            )
    else:
        raise UnsupportedScopeError(
            "state",
            f"unsupported core state type: {type(core).__name__}",
        )
    (
        language,
        world_reference,
        human_reference,
        definitiveness,
        ambiguity,
        memory,
        verifier,
        resource_used,
        resource_limit,
        self_model,
    ) = registers
    return RclmStateRecord(
        core=core,
        language=_register(LANGUAGE_REGISTER_SCHEMA_ID, language),
        world_reference=_register(WORLD_REFERENCE_REGISTER_SCHEMA_ID, world_reference),
        human_reference=_register(HUMAN_REFERENCE_REGISTER_SCHEMA_ID, human_reference),
        definitiveness=_register(DEFINITIVENESS_REGISTER_SCHEMA_ID, definitiveness),
        ambiguity=_register(AMBIGUITY_REGISTER_SCHEMA_ID, ambiguity),
        memory=_register(MEMORY_REGISTER_SCHEMA_ID, memory),
        verifier=_register(VERIFIER_REGISTER_SCHEMA_ID, verifier),
        resources=TypedArtifactRecord.from_value(
            RESOURCE_REGISTER_SCHEMA_ID,
            {"used": resource_used, "limit": resource_limit},
        ),
        self_model=_register(SELF_MODEL_REGISTER_SCHEMA_ID, self_model),
    )


def canonical_rclm_update(core: RcpUpdateRecord) -> RclmUpdateRecord:
    if isinstance(core, ClassicalBinaryUpdateRecord):
        improving = core.update == "improve"
    elif isinstance(core, QuantumUpdateRecord):
        improving = core.update == "swap"
    else:
        raise UnsupportedScopeError(
            "update",
            f"unsupported core update type: {type(core).__name__}",
        )
    return RclmUpdateRecord(
        core=core,
        parameters=_register(
            PARAMETER_UPDATE_SCHEMA_ID,
            "targetAligned" if improving else "unchanged",
        ),
        architecture=_register(ARCHITECTURE_UPDATE_SCHEMA_ID, "preserved"),
        memory=_register(
            MEMORY_UPDATE_SCHEMA_ID,
            "advanced" if improving else "retained",
        ),
        verifier=_register(VERIFIER_UPDATE_SCHEMA_ID, "retained"),
        semantics=_register(
            SEMANTIC_UPDATE_SCHEMA_ID,
            "targetAligned" if improving else "preserved",
        ),
        tools=_register(TOOL_UPDATE_SCHEMA_ID, "none"),
        resources=_register(RESOURCE_UPDATE_SCHEMA_ID, "bounded"),
    )


def canonical_rclm_certificate(
    scope: CheckerScope,
    certificate_name: CertificateName,
) -> RclmCertificatePacketRecord:
    if certificate_name not in {"improvement", "stability", "malformed"}:
        raise SchemaValidationError(
            "certificate",
            f"unknown certificate: {certificate_name}",
        )
    if scope == "gate_b_classical":
        core = classical_core_certificate(certificate_name)
    elif scope == "gate_c_diagonal_quantum":
        core = quantum_core_certificate(certificate_name)
    else:
        raise UnsupportedScopeError("scope", f"unsupported scope: {scope}")

    rejected = certificate_name == "malformed"
    return RclmCertificatePacketRecord(
        core=core,
        semantics=_evidence(
            SEMANTIC_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "coherent",
        ),
        typing=_evidence(
            TYPE_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "typed",
        ),
        ledger=_evidence(
            LEDGER_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "withinBudget",
        ),
        goal_transport=_evidence(
            GOAL_TRANSPORT_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "targetFixed",
        ),
        trust=_evidence(
            TRUST_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "predecessorVerified",
        ),
        resources=_evidence(
            RESOURCE_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "bounded",
        ),
        reality=_evidence(
            REALITY_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "contained",
        ),
        recovery=_evidence(
            RECOVERY_EVIDENCE_SCHEMA_ID,
            "rejected" if rejected else "exact",
        ),
        progress=_evidence(
            PROGRESS_EVIDENCE_SCHEMA_ID,
            (
                "rejected"
                if rejected
                else ("strict" if certificate_name == "improvement" else "stable")
            ),
        ),
    )


def core_certificate_name(
    certificate: RclmCertificatePacketRecord,
) -> tuple[CheckerScope, CertificateName]:
    if certificate.core.schema_id == CLASSICAL_CERTIFICATE_ARTIFACT_SCHEMA_ID:
        scope: CheckerScope = "gate_b_classical"
    elif certificate.core.schema_id == QUANTUM_CERTIFICATE_ARTIFACT_SCHEMA_ID:
        scope = "gate_c_diagonal_quantum"
    else:
        raise UnsupportedScopeError(
            "certificate.core.schema_id",
            f"unsupported core certificate schema: {certificate.core.schema_id}",
        )
    value = thaw_json(certificate.core.value)
    obj = strict_object(value, "certificate.core.value", {"certificate"})
    certificate_name = obj["certificate"]
    if not isinstance(certificate_name, str):
        raise SchemaValidationError(
            "certificate.core.value.certificate",
            "expected a string",
        )
    if certificate_name not in {"improvement", "stability", "malformed"}:
        raise SchemaValidationError(
            "certificate.core.value.certificate",
            f"unknown certificate: {certificate_name}",
        )
    return scope, certificate_name


def build_lean_reference_packet(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
    certificate: RclmCertificatePacketRecord,
) -> LeanReferencePacket:
    scope = scope_from_core_state(predecessor.core)
    certificate_scope, certificate_name = core_certificate_name(certificate)
    if certificate_scope != scope:
        raise SchemaValidationError(
            "certificate.core",
            "certificate scope differs from predecessor scope",
        )
    transition_hash = canonical_json_hash(
        {
            "predecessor": predecessor.to_json(),
            "candidate": candidate.to_json(),
            "certificate": certificate.to_json(),
        }
    )
    predecessor_name = predecessor.core.state
    update_name = candidate.update.core.update
    successor_name = candidate.next.core.state
    return LeanReferencePacket(
        case_id=f"phase3.{scope}.{transition_hash[:40]}",
        scope=scope,
        predecessor=predecessor_name,
        update=update_name,
        successor=successor_name,
        certificate=certificate_name,
    )


def reference_trust_anchor() -> TrustAnchorRecord:
    return TrustAnchorRecord(
        formal_source_commit=FORMAL_SOURCE_COMMIT,
        lean_toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
        formal_manifest_blob=FORMAL_MANIFEST_BLOB,
        gate_c_audit_sha256=GATE_C_AUDIT_SHA256,
        checker_policy_hash=CHECKER_POLICY_HASH,
        lean_verifier_policy_hash=LEAN_VERIFIER_POLICY_HASH,
        claim_boundary_hash=CLAIM_BOUNDARY_HASH,
    )


def reference_resource_record(
    *,
    precision_bits: int = 256,
    budget_units: int = 1,
    consumed_units: int = 1,
    environment_hash: str | None = None,
) -> ResourceRecord:
    resolved_environment_hash = environment_hash or canonical_json_hash(
        {
            "environment": "phase3-reference",
            "network": "disabled",
            "model": "absent",
        }
    )
    return ResourceRecord(
        budget_units=budget_units,
        consumed_units=consumed_units,
        precision_bits=precision_bits,
        model_invocations=0,
        network_requests=0,
        predecessor_write_attempts=0,
        candidate_write_attempts=0,
        checker_source_write_attempts=0,
        manual_repair_count=0,
        hidden_oracle_reads=0,
        environment_hash=resolved_environment_hash,
        meter_policy_hash=RESOURCE_METER_POLICY_HASH,
    )


def reference_protected_distinctions(
    scope: CheckerScope,
) -> Sequence[ProtectedDistinctionRecord]:
    return tuple(
        ProtectedDistinctionRecord(
            distinction_id=distinction,
            loss_budget=Rational.zero(),
        )
        for distinction in sorted(required_protected_distinctions(scope))
    )


def reference_evaluation_evidence(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
) -> EvaluationEvidenceRecord:
    scope = scope_from_core_state(predecessor.core)
    if scope == "gate_b_classical":
        if not isinstance(predecessor.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("predecessor.core", "expected classical state")
        if not isinstance(candidate.next.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("candidate.next.core", "expected classical state")
        return EvaluationEvidenceRecord(
            scope=scope,
            predecessor_observation=binary_state_distribution(predecessor.core.state),
            successor_observation=binary_state_distribution(candidate.next.core.state),
            target_observation=BIASED_BINARY,
            evaluator_policy_hash=EVALUATOR_POLICY_HASH,
        )
    if not isinstance(predecessor.core, QuantumStateRecord):
        raise SchemaValidationError("predecessor.core", "expected quantum state")
    if not isinstance(candidate.next.core, QuantumStateRecord):
        raise SchemaValidationError("candidate.next.core", "expected quantum state")
    return EvaluationEvidenceRecord(
        scope=scope,
        predecessor_observation=quantum_state_density(predecessor.core.state),
        successor_observation=quantum_state_density(candidate.next.core.state),
        target_observation=TARGET_DENSITY,
        evaluator_policy_hash=EVALUATOR_POLICY_HASH,
    )
