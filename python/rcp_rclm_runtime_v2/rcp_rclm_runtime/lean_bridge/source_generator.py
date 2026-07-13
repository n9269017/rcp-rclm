from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_text
from rcp_rclm_runtime.lean_bridge.packet import (
    LeanReferencePacket,
    interpret_reference_packet,
)

LEAN_VERDICT_MARKER_PREFIX: Final[str] = "RCP_RCLM_LEAN_VERDICT_V2:"
LEAN_VERDICT_SCHEMA_ID: Final[str] = "runtime.lean_reference_verdict.v2"
SOURCE_GENERATOR_VERSION: Final[str] = "rcp-rclm-lean-source-generator-v2.0.0"

_CLASSICAL_THEOREM_SURFACE: Final[Sequence[str]] = (
    "RcpRclmFormalCoreV2.RCP.ClassicalFinite.binaryCheck_eq_true_iff",
    "RcpRclmFormalCoreV2.RCP.ClassicalFinite.binary_checker_refines_kernel",
    "RcpRclmFormalCoreV2.RCP.ClassicalFinite.initial_improvement_obligations",
    "RcpRclmFormalCoreV2.RCP.ClassicalFinite.target_stability_obligations",
    "RcpRclmFormalCoreV2.RCLM.ClassicalBinary.check_eq_true_iff",
    "RcpRclmFormalCoreV2.RCLM.ClassicalBinary.accepted_architecture_successor",
    "RcpRclmFormalCoreV2.RCLM.ClassicalBinary.improvement_refines_gate_b",
)

_QUANTUM_THEOREM_SURFACE: Final[Sequence[str]] = (
    "RcpRclmFormalCoreV2.RCP.QuantumFinite.quantumCheck_eq_true_iff",
    "RcpRclmFormalCoreV2.RCP.QuantumFinite.quantum_checker_refines_kernel",
    "RcpRclmFormalCoreV2.RCP.QuantumFinite.source_improvement_obligations",
    "RcpRclmFormalCoreV2.RCP.QuantumFinite.target_stability_obligations",
    "RcpRclmFormalCoreV2.RCLM.QuantumBinary.check_eq_true_iff",
    "RcpRclmFormalCoreV2.RCLM.QuantumBinary.accepted_quantum_architecture_successor",
)


@dataclass(frozen=True, slots=True)
class GeneratedLeanSource:
    packet: LeanReferencePacket
    source_text: str
    source_hash: str
    theorem_surface: Sequence[str]
    theorem_surface_hash: str
    expected_acceptance: bool
    virtual_path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "theorem_surface", tuple(self.theorem_surface))

    @property
    def source_bytes(self) -> bytes:
        return self.source_text.encode("utf-8")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.generated_lean_reference_source.v2",
            "source_generator_version": SOURCE_GENERATOR_VERSION,
            "packet_hash": self.packet.packet_hash,
            "case_id": self.packet.case_id,
            "scope": self.packet.scope,
            "virtual_path": self.virtual_path,
            "source_hash": self.source_hash,
            "theorem_surface": list(self.theorem_surface),
            "theorem_surface_hash": self.theorem_surface_hash,
            "expected_acceptance": self.expected_acceptance,
        }


def generate_reference_source(packet: LeanReferencePacket) -> GeneratedLeanSource:
    expected = interpret_reference_packet(packet)
    theorem_surface = (
        _CLASSICAL_THEOREM_SURFACE
        if packet.scope == "gate_b_classical"
        else _QUANTUM_THEOREM_SURFACE
    )
    theorem_surface_hash = canonical_json_hash(list(theorem_surface))
    marker = canonical_json_text(
        {
            "schema_id": LEAN_VERDICT_SCHEMA_ID,
            "case_id": packet.case_id,
            "scope": packet.scope,
            "rcp_accepted": expected,
            "rclm_accepted": expected,
            "packet_hash": packet.packet_hash,
            "theorem_surface_hash": theorem_surface_hash,
            "source_generator_version": SOURCE_GENERATOR_VERSION,
        }
    )
    marker_line = LEAN_VERDICT_MARKER_PREFIX + marker
    if packet.scope == "gate_b_classical":
        source_text = _classical_source(packet, expected, marker_line, theorem_surface)
    else:
        source_text = _quantum_source(packet, expected, marker_line, theorem_surface)
    source_bytes = source_text.encode("utf-8")
    virtual_path = f"generated/{packet.case_id}.lean"
    return GeneratedLeanSource(
        packet=packet,
        source_text=source_text,
        source_hash=sha256_hex(source_bytes),
        theorem_surface=theorem_surface,
        theorem_surface_hash=theorem_surface_hash,
        expected_acceptance=expected,
        virtual_path=virtual_path,
    )


def _classical_source(
    packet: LeanReferencePacket,
    expected: bool,
    marker_line: str,
    theorem_surface: Sequence[str],
) -> str:
    check_lines = "\n".join(f"#check {name}" for name in theorem_surface)
    expected_text = "true" if expected else "false"
    lean_marker = json.dumps(marker_line, ensure_ascii=False)
    obligation = _classical_obligation_example(packet) if expected else ""
    return (
        "import RcpRclmFormalCoreV2.RCP.ClassicalBinary\n"
        "import RcpRclmFormalCoreV2.RCLM.ClassicalBinary\n\n"
        "namespace RcpRclmRuntimeV2Bridge\n\n"
        "open RcpRclmFormalCoreV2\n"
        "open RcpRclmFormalCoreV2.RCP\n\n"
        "namespace RCPReference\n\n"
        "open RcpRclmFormalCoreV2.RCP.ClassicalFinite\n\n"
        "def bridgeCandidate : Candidate BinaryState BinaryUpdate where\n"
        f"  update := BinaryUpdate.{packet.update}\n"
        f"  next := BinaryState.{packet.successor}\n\n"
        "example :\n"
        f"    binaryCheck BinaryState.{packet.predecessor}\n"
        "      bridgeCandidate\n"
        f"      BinaryCertificate.{packet.certificate} = {expected_text} := by\n"
        "  rfl\n\n"
        f"{obligation}"
        "end RCPReference\n\n"
        "namespace RCLMReference\n\n"
        "def bridgeCandidate :\n"
        "    Candidate\n"
        "      RcpRclmFormalCoreV2.RCLM.ClassicalBinary.ClassicalState\n"
        "      RcpRclmFormalCoreV2.RCLM.ClassicalBinary.ClassicalUpdate where\n"
        "  update := RcpRclmFormalCoreV2.RCLM.ClassicalBinary.canonicalUpdate\n"
        f"    RcpRclmFormalCoreV2.RCP.ClassicalFinite.BinaryUpdate.{packet.update}\n"
        "  next := RcpRclmFormalCoreV2.RCLM.ClassicalBinary.canonicalState\n"
        f"    RcpRclmFormalCoreV2.RCP.ClassicalFinite.BinaryState.{packet.successor}\n\n"
        "example :\n"
        "    RcpRclmFormalCoreV2.RCLM.ClassicalBinary.check\n"
        "      (RcpRclmFormalCoreV2.RCLM.ClassicalBinary.canonicalState\n"
        f"        RcpRclmFormalCoreV2.RCP.ClassicalFinite.BinaryState.{packet.predecessor})\n"
        "      bridgeCandidate\n"
        "      (RcpRclmFormalCoreV2.RCLM.ClassicalBinary.canonicalCertificate\n"
        f"        RcpRclmFormalCoreV2.RCP.ClassicalFinite.BinaryCertificate.{packet.certificate}) =\n"
        f"      {expected_text} := by\n"
        "  rfl\n\n"
        "end RCLMReference\n\n"
        f"{check_lines}\n\n"
        f"#eval IO.println {lean_marker}\n\n"
        "end RcpRclmRuntimeV2Bridge\n"
    )


def _quantum_source(
    packet: LeanReferencePacket,
    expected: bool,
    marker_line: str,
    theorem_surface: Sequence[str],
) -> str:
    check_lines = "\n".join(f"#check {name}" for name in theorem_surface)
    expected_text = "true" if expected else "false"
    lean_marker = json.dumps(marker_line, ensure_ascii=False)
    obligation = _quantum_obligation_example(packet) if expected else ""
    return (
        "import RcpRclmFormalCoreV2.RCP.QuantumFinite\n"
        "import RcpRclmFormalCoreV2.RCLM.QuantumBinary\n\n"
        "namespace RcpRclmRuntimeV2Bridge\n\n"
        "open RcpRclmFormalCoreV2\n"
        "open RcpRclmFormalCoreV2.RCP\n\n"
        "namespace RCPReference\n\n"
        "open RcpRclmFormalCoreV2.RCP.QuantumFinite\n\n"
        "def bridgeCandidate : Candidate QuantumState QuantumUpdate where\n"
        f"  update := QuantumUpdate.{packet.update}\n"
        f"  next := QuantumState.{packet.successor}\n\n"
        "example :\n"
        f"    quantumCheck QuantumState.{packet.predecessor}\n"
        "      bridgeCandidate\n"
        f"      QuantumCertificate.{packet.certificate} = {expected_text} := by\n"
        "  rfl\n\n"
        f"{obligation}"
        "end RCPReference\n\n"
        "namespace RCLMReference\n\n"
        "def bridgeCandidate :\n"
        "    Candidate\n"
        "      RcpRclmFormalCoreV2.RCLM.QuantumBinary.ArchitectureState\n"
        "      RcpRclmFormalCoreV2.RCLM.QuantumBinary.ArchitectureUpdate where\n"
        "  update := RcpRclmFormalCoreV2.RCLM.QuantumBinary.canonicalUpdate\n"
        f"    RcpRclmFormalCoreV2.RCP.QuantumFinite.QuantumUpdate.{packet.update}\n"
        "  next := RcpRclmFormalCoreV2.RCLM.QuantumBinary.canonicalState\n"
        f"    RcpRclmFormalCoreV2.RCP.QuantumFinite.QuantumState.{packet.successor}\n\n"
        "example :\n"
        "    RcpRclmFormalCoreV2.RCLM.QuantumBinary.check\n"
        "      (RcpRclmFormalCoreV2.RCLM.QuantumBinary.canonicalState\n"
        f"        RcpRclmFormalCoreV2.RCP.QuantumFinite.QuantumState.{packet.predecessor})\n"
        "      bridgeCandidate\n"
        "      (RcpRclmFormalCoreV2.RCLM.QuantumBinary.canonicalCertificate\n"
        f"        RcpRclmFormalCoreV2.RCP.QuantumFinite.QuantumCertificate.{packet.certificate}) =\n"
        f"      {expected_text} := by\n"
        "  rfl\n\n"
        "end RCLMReference\n\n"
        f"{check_lines}\n\n"
        f"#eval IO.println {lean_marker}\n\n"
        "end RcpRclmRuntimeV2Bridge\n"
    )


def _classical_obligation_example(packet: LeanReferencePacket) -> str:
    if packet.predecessor == "initial":
        theorem = "initial_improvement_obligations"
        candidate_definition = "improvementCandidate"
    else:
        theorem = "target_stability_obligations"
        candidate_definition = "stabilityCandidate"
    return (
        "example :\n"
        "    RcpRclmFormalCoreV2.RCP.StepObligations\n"
        "      RcpRclmFormalCoreV2.RCP.ClassicalFinite.binaryKernel\n"
        f"      RcpRclmFormalCoreV2.RCP.ClassicalFinite.BinaryState.{packet.predecessor}\n"
        "      bridgeCandidate\n"
        f"      RcpRclmFormalCoreV2.RCP.ClassicalFinite.BinaryCertificate.{packet.certificate} := by\n"
        f"  simpa [bridgeCandidate, RcpRclmFormalCoreV2.RCP.ClassicalFinite.{candidate_definition}] using\n"
        f"    RcpRclmFormalCoreV2.RCP.ClassicalFinite.{theorem}\n\n"
    )


def _quantum_obligation_example(packet: LeanReferencePacket) -> str:
    if packet.predecessor == "source":
        theorem = "source_improvement_obligations"
        candidate_definition = "improvementCandidate"
    else:
        theorem = "target_stability_obligations"
        candidate_definition = "stabilityCandidate"
    return (
        "example :\n"
        "    RcpRclmFormalCoreV2.RCP.StepObligations\n"
        "      RcpRclmFormalCoreV2.RCP.QuantumFinite.quantumKernel\n"
        f"      RcpRclmFormalCoreV2.RCP.QuantumFinite.QuantumState.{packet.predecessor}\n"
        "      bridgeCandidate\n"
        f"      RcpRclmFormalCoreV2.RCP.QuantumFinite.QuantumCertificate.{packet.certificate} := by\n"
        f"  simpa [bridgeCandidate, RcpRclmFormalCoreV2.RCP.QuantumFinite.{candidate_definition}] using\n"
        f"    RcpRclmFormalCoreV2.RCP.QuantumFinite.{theorem}\n\n"
    )
