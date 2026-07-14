from __future__ import annotations

from rcp_rclm_runtime.errors import SchemaValidationError, UnsupportedScopeError
from rcp_rclm_runtime.mathematics.diagonal_quantum import apply_quantum_update
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema.candidate import CandidateRecord, apply_candidate
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
    RclmStateRecord,
)
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    QuantumUpdateRecord,
)
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.records import ComponentResultRecord
from rcp_rclm_runtime.checker.reference import scope_from_core_state


def core_packet_accepted(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
    certificate_name: str,
) -> bool:
    core = predecessor.core
    update = candidate.update.core
    successor = candidate.next.core
    if isinstance(core, ClassicalBinaryStateRecord):
        if not isinstance(update, ClassicalBinaryUpdateRecord):
            return False
        improvement = (
            core.state == "initial"
            and update.update == "improve"
            and isinstance(successor, ClassicalBinaryStateRecord)
            and successor.state == "target"
            and certificate_name == "improvement"
        )
        stability = (
            core.state == "target"
            and update.update == "stay"
            and isinstance(successor, ClassicalBinaryStateRecord)
            and successor.state == "target"
            and certificate_name == "stability"
        )
        return improvement or stability
    if isinstance(core, QuantumStateRecord):
        if not isinstance(update, QuantumUpdateRecord):
            return False
        improvement = (
            core.state == "source"
            and update.update == "swap"
            and isinstance(successor, QuantumStateRecord)
            and successor.state == "target"
            and certificate_name == "improvement"
        )
        stability = (
            core.state == "target"
            and update.update == "stay"
            and isinstance(successor, QuantumStateRecord)
            and successor.state == "target"
            and certificate_name == "stability"
        )
        return improvement or stability
    return False


def _typed_successor(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
) -> tuple[ComponentResultRecord, bool]:
    computed = apply_candidate(
        predecessor.core,
        CandidateRecord(
            update=candidate.update.core,
            next=candidate.next.core,
        ),
    )
    typed_ok = computed == candidate.next.core
    result = ComponentResultRecord.from_evidence(
        "pass" if typed_ok else "fail",
        () if typed_ok else (ReasonCode.TYPED_SUCCESSOR_FAILED,),
        {
            "computed_successor": computed.to_json(),
            "declared_successor": candidate.next.core.to_json(),
            "equal": typed_ok,
        },
    )
    return result, typed_ok


def _recovery_result(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
) -> ComponentResultRecord:
    if isinstance(predecessor.core, ClassicalBinaryStateRecord):
        recovered = predecessor.core
    elif isinstance(predecessor.core, QuantumStateRecord):
        if not isinstance(candidate.next.core, QuantumStateRecord):
            raise SchemaValidationError("candidate.next.core", "expected quantum state")
        if not isinstance(candidate.update.core, QuantumUpdateRecord):
            raise SchemaValidationError("candidate.update.core", "expected quantum update")
        recovered_name = apply_quantum_update(
            candidate.next.core.state,
            candidate.update.core.update,
        )
        recovered = QuantumStateRecord.canonical(recovered_name)
    else:
        raise UnsupportedScopeError(
            "predecessor.core",
            f"unsupported state type: {type(predecessor.core).__name__}",
        )
    exact = recovered == predecessor.core
    error = Rational.zero() if exact else Rational.one()
    return ComponentResultRecord.from_evidence(
        "pass" if exact else "fail",
        () if exact else (ReasonCode.RECOVERY_FAILED,),
        {
            "recovered_state": recovered.to_json(),
            "predecessor_state": predecessor.core.to_json(),
            "recovery_error": error.to_json(),
            "recovery_budget": Rational.zero().to_json(),
            "within_budget": exact,
        },
    )


def _invariant_result(
    candidate: RclmCandidateRecord,
) -> ComponentResultRecord:
    core_admissible = candidate.next.core.state != "outside"
    return ComponentResultRecord.from_evidence(
        "pass" if core_admissible else "fail",
        () if core_admissible else (ReasonCode.INVARIANT_FAILED,),
        {
            "successor_core_not_outside": core_admissible,
            "candidate_assertions_consumed": [],
        },
    )


def _containment_result(
    typed_successor: bool,
    candidate: RclmCandidateRecord,
) -> ComponentResultRecord:
    successor_not_outside = candidate.next.core.state != "outside"
    ok = successor_not_outside and typed_successor
    return ComponentResultRecord.from_evidence(
        "pass" if ok else "fail",
        () if ok else (ReasonCode.CONTAINMENT_FAILED,),
        {
            "successor_not_outside": successor_not_outside,
            "successor_equals_recomputed_apply": typed_successor,
            "candidate_reality_declaration_consumed": False,
        },
    )


def _domain_result(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
) -> ComponentResultRecord:
    predecessor_admissible = predecessor.core.state != "outside"
    successor_admissible = candidate.next.core.state != "outside"
    same_scope = scope_from_core_state(predecessor.core) == scope_from_core_state(
        candidate.next.core
    )
    ok = predecessor_admissible and successor_admissible and same_scope
    return ComponentResultRecord.from_evidence(
        "pass" if ok else "fail",
        () if ok else (ReasonCode.SUCCESSOR_DOMAIN_FAILED,),
        {
            "predecessor_admissible": predecessor_admissible,
            "successor_admissible": successor_admissible,
            "same_scope": same_scope,
        },
    )
