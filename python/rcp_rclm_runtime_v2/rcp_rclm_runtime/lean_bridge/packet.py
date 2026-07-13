from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final, Literal, TypeAlias

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object

BridgeScope: TypeAlias = Literal["gate_b_classical", "gate_c_diagonal_quantum"]
BridgeState: TypeAlias = Literal["outside", "initial", "target", "source"]
BridgeUpdate: TypeAlias = Literal["stay", "improve", "swap"]
BridgeCertificate: TypeAlias = Literal["improvement", "stability", "malformed"]

LEAN_REFERENCE_PACKET_SCHEMA_ID: Final[str] = "runtime.lean_reference_packet.v2"
_CASE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

_CLASSICAL_STATES: Final[frozenset[str]] = frozenset({"outside", "initial", "target"})
_CLASSICAL_UPDATES: Final[frozenset[str]] = frozenset({"stay", "improve"})
_QUANTUM_STATES: Final[frozenset[str]] = frozenset({"outside", "source", "target"})
_QUANTUM_UPDATES: Final[frozenset[str]] = frozenset({"stay", "swap"})
_CERTIFICATES: Final[frozenset[str]] = frozenset({"improvement", "stability", "malformed"})


@dataclass(frozen=True, slots=True)
class LeanReferencePacket:
    case_id: str
    scope: BridgeScope
    predecessor: BridgeState
    update: BridgeUpdate
    successor: BridgeState
    certificate: BridgeCertificate

    schema_id: ClassVar[str] = LEAN_REFERENCE_PACKET_SCHEMA_ID

    def __post_init__(self) -> None:
        if _CASE_ID_PATTERN.fullmatch(self.case_id) is None:
            raise SchemaValidationError(
                "lean_reference_packet.case_id",
                "case identifier must use lowercase ASCII letters, digits, dots, underscores, or hyphens",
            )
        if self.scope not in {"gate_b_classical", "gate_c_diagonal_quantum"}:
            raise SchemaValidationError(
                "lean_reference_packet.scope",
                f"unsupported bridge scope: {self.scope}",
            )
        if self.certificate not in _CERTIFICATES:
            raise SchemaValidationError(
                "lean_reference_packet.certificate",
                f"unknown certificate: {self.certificate}",
            )
        if self.scope == "gate_b_classical":
            if self.predecessor not in _CLASSICAL_STATES:
                raise SchemaValidationError(
                    "lean_reference_packet.predecessor",
                    f"invalid classical predecessor: {self.predecessor}",
                )
            if self.successor not in _CLASSICAL_STATES:
                raise SchemaValidationError(
                    "lean_reference_packet.successor",
                    f"invalid classical successor: {self.successor}",
                )
            if self.update not in _CLASSICAL_UPDATES:
                raise SchemaValidationError(
                    "lean_reference_packet.update",
                    f"invalid classical update: {self.update}",
                )
        else:
            if self.predecessor not in _QUANTUM_STATES:
                raise SchemaValidationError(
                    "lean_reference_packet.predecessor",
                    f"invalid quantum predecessor: {self.predecessor}",
                )
            if self.successor not in _QUANTUM_STATES:
                raise SchemaValidationError(
                    "lean_reference_packet.successor",
                    f"invalid quantum successor: {self.successor}",
                )
            if self.update not in _QUANTUM_UPDATES:
                raise SchemaValidationError(
                    "lean_reference_packet.update",
                    f"invalid quantum update: {self.update}",
                )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "lean_reference_packet",
    ) -> LeanReferencePacket:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "case_id",
                "scope",
                "predecessor",
                "update",
                "successor",
                "certificate",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        case_id = require_string(obj["case_id"], f"{path}.case_id")
        scope = require_string(obj["scope"], f"{path}.scope")
        predecessor = require_string(obj["predecessor"], f"{path}.predecessor")
        update = require_string(obj["update"], f"{path}.update")
        successor = require_string(obj["successor"], f"{path}.successor")
        certificate = require_string(obj["certificate"], f"{path}.certificate")
        if scope not in {"gate_b_classical", "gate_c_diagonal_quantum"}:
            raise SchemaValidationError(f"{path}.scope", f"unsupported bridge scope: {scope}")
        return cls(
            case_id=case_id,
            scope=scope,
            predecessor=predecessor,
            update=update,
            successor=successor,
            certificate=certificate,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "case_id": self.case_id,
            "scope": self.scope,
            "predecessor": self.predecessor,
            "update": self.update,
            "successor": self.successor,
            "certificate": self.certificate,
        }

    @property
    def packet_hash(self) -> str:
        return canonical_json_hash(self.to_json())


def interpret_reference_packet(packet: LeanReferencePacket) -> bool:
    if packet.scope == "gate_b_classical":
        improvement = (
            packet.predecessor == "initial"
            and packet.update == "improve"
            and packet.successor == "target"
            and packet.certificate == "improvement"
        )
        stability = (
            packet.predecessor == "target"
            and packet.update == "stay"
            and packet.successor == "target"
            and packet.certificate == "stability"
        )
        return improvement or stability
    improvement = (
        packet.predecessor == "source"
        and packet.update == "swap"
        and packet.successor == "target"
        and packet.certificate == "improvement"
    )
    stability = (
        packet.predecessor == "target"
        and packet.update == "stay"
        and packet.successor == "target"
        and packet.certificate == "stability"
    )
    return improvement or stability


def reference_packets() -> Sequence[LeanReferencePacket]:
    return (
        LeanReferencePacket(
            case_id="gate_b.accept.improvement",
            scope="gate_b_classical",
            predecessor="initial",
            update="improve",
            successor="target",
            certificate="improvement",
        ),
        LeanReferencePacket(
            case_id="gate_b.accept.stability",
            scope="gate_b_classical",
            predecessor="target",
            update="stay",
            successor="target",
            certificate="stability",
        ),
        LeanReferencePacket(
            case_id="gate_b.reject.wrong_successor",
            scope="gate_b_classical",
            predecessor="initial",
            update="improve",
            successor="initial",
            certificate="improvement",
        ),
        LeanReferencePacket(
            case_id="gate_b.reject.wrong_certificate",
            scope="gate_b_classical",
            predecessor="initial",
            update="improve",
            successor="target",
            certificate="stability",
        ),
        LeanReferencePacket(
            case_id="gate_b.reject.malformed_certificate",
            scope="gate_b_classical",
            predecessor="target",
            update="stay",
            successor="target",
            certificate="malformed",
        ),
        LeanReferencePacket(
            case_id="gate_c.accept.improvement",
            scope="gate_c_diagonal_quantum",
            predecessor="source",
            update="swap",
            successor="target",
            certificate="improvement",
        ),
        LeanReferencePacket(
            case_id="gate_c.accept.stability",
            scope="gate_c_diagonal_quantum",
            predecessor="target",
            update="stay",
            successor="target",
            certificate="stability",
        ),
        LeanReferencePacket(
            case_id="gate_c.reject.wrong_successor",
            scope="gate_c_diagonal_quantum",
            predecessor="source",
            update="swap",
            successor="source",
            certificate="improvement",
        ),
        LeanReferencePacket(
            case_id="gate_c.reject.wrong_certificate",
            scope="gate_c_diagonal_quantum",
            predecessor="source",
            update="swap",
            successor="target",
            certificate="stability",
        ),
        LeanReferencePacket(
            case_id="gate_c.reject.malformed_certificate",
            scope="gate_c_diagonal_quantum",
            predecessor="target",
            update="stay",
            successor="target",
            certificate="malformed",
        ),
    )
