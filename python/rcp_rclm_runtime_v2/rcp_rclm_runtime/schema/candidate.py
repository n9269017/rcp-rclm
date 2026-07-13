from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.classical import apply_binary_update
from rcp_rclm_runtime.mathematics.diagonal_quantum import apply_quantum_update
from rcp_rclm_runtime.schema._common import require_schema_id, strict_object
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
    RcpStateRecord,
    parse_rcp_state,
)
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    QuantumUpdateRecord,
    RcpUpdateRecord,
    parse_rcp_update,
)

CANDIDATE_SCHEMA_ID: Final[str] = "rcp.candidate.v2"


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    update: RcpUpdateRecord
    next: RcpStateRecord

    schema_id: ClassVar[str] = CANDIDATE_SCHEMA_ID

    def __post_init__(self) -> None:
        if isinstance(self.update, ClassicalBinaryUpdateRecord):
            if not isinstance(self.next, ClassicalBinaryStateRecord):
                raise SchemaValidationError(
                    "candidate.next", "classical update requires a classical successor state"
                )
        elif isinstance(self.update, QuantumUpdateRecord):
            if not isinstance(self.next, QuantumStateRecord):
                raise SchemaValidationError(
                    "candidate.next", "quantum update requires a selected quantum successor state"
                )
        else:
            raise SchemaValidationError("candidate.update", "unsupported update record type")

    @classmethod
    def from_json(cls, value: object, path: str = "candidate") -> CandidateRecord:
        obj = strict_object(value, path, {"schema_id", "update", "next"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            update=parse_rcp_update(obj["update"], f"{path}.update"),
            next=parse_rcp_state(obj["next"], f"{path}.next"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "update": self.update.to_json(),
            "next": self.next.to_json(),
        }


def apply_candidate(
    predecessor: RcpStateRecord,
    candidate: CandidateRecord,
) -> RcpStateRecord:
    if isinstance(predecessor, ClassicalBinaryStateRecord):
        if not isinstance(candidate.update, ClassicalBinaryUpdateRecord):
            raise SchemaValidationError(
                "candidate.update", "predecessor and candidate update scopes differ"
            )
        computed = apply_binary_update(predecessor.state, candidate.update.update)
        return ClassicalBinaryStateRecord(state=computed)
    if isinstance(predecessor, QuantumStateRecord):
        if not isinstance(candidate.update, QuantumUpdateRecord):
            raise SchemaValidationError(
                "candidate.update", "predecessor and candidate update scopes differ"
            )
        computed = apply_quantum_update(predecessor.state, candidate.update.update)
        return QuantumStateRecord.canonical(computed)
    raise SchemaValidationError("predecessor", "unsupported predecessor state type")
