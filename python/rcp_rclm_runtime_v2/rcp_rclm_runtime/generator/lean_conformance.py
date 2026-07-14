from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompilationResult, LeanCompiler
from rcp_rclm_runtime.lean_bridge.source_guard import (
    SourceGuardReport,
    scan_source_bytes,
)

REFERENCE_GRAMMAR_CONFORMANCE_SCHEMA_ID: Final[str] = (
    "runtime.phase5_reference_grammar_lean_conformance.v2"
)
REFERENCE_GRAMMAR_SOURCE_PATH: Final[str] = (
    "generated/Phase5AReferenceGrammarConformance.lean"
)


@dataclass(frozen=True, slots=True)
class ReferenceGrammarLeanConformanceReport:
    source_hash: str
    source_path: str
    source_guard: SourceGuardReport
    compilation: LeanCompilationResult | None

    schema_id: ClassVar[str] = REFERENCE_GRAMMAR_CONFORMANCE_SCHEMA_ID

    @property
    def accepted(self) -> bool:
        return (
            self.source_guard.clean
            and self.compilation is not None
            and self.compilation.succeeded
            and self.compilation.source_hash == self.source_hash
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_hash": self.source_hash,
            "source_path": self.source_path,
            "accepted": self.accepted,
            "source_guard": self.source_guard.to_json(),
            "compilation": (
                None if self.compilation is None else self.compilation.to_json()
            ),
        }


def reference_grammar_lean_source() -> bytes:
    source = """import RcpRclmFormalCoreV2.RCLM.ClassicalBinarySeedLibrary

namespace RcpRclmRuntimePhase5AReferenceGrammar

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV2.RCLM
open RcpRclmFormalCoreV2.RCLM.ClassicalBinary

example : initialBoundedSeedPacket.word = BoundedPacketWord.improve := rfl
example : targetBoundedSeedPacket.word = BoundedPacketWord.stabilize := rfl

example : boundedWordDepth BoundedPacketWord.improve = 1 := rfl
example : boundedWordDepth BoundedPacketWord.stabilize = 1 := rfl
example : boundedProofLength BoundedPacketWord.improve = 1 := rfl
example : boundedProofLength BoundedPacketWord.stabilize = 1 := rfl

example :
    boundedWitnessOf BoundedPacketWord.improve =
      EngineWitness.strictImprovement := rfl
example :
    boundedWitnessOf BoundedPacketWord.stabilize =
      EngineWitness.stableContinuation := rfl
example :
    boundedProposalOf BoundedPacketWord.improve =
      EngineProposal.improve := rfl
example :
    boundedProposalOf BoundedPacketWord.stabilize =
      EngineProposal.stabilize := rfl

example :
    boundedCertificateOf BoundedPacketWord.improve =
      improvementCertificate := rfl
example :
    boundedCertificateOf BoundedPacketWord.stabilize =
      stabilityCertificate := rfl

example :
    boundedCandidateOf initialState BoundedPacketWord.improve =
      improvementCandidate := rfl
example :
    boundedCandidateOf targetState BoundedPacketWord.stabilize =
      stabilityCandidate := rfl

example :
    BoundedPacketWord.improve ∈ boundedPacketGrammar initialState := by
  simp [boundedPacketGrammar]
example :
    BoundedPacketWord.stabilize ∈ boundedPacketGrammar targetState := by
  simp [boundedPacketGrammar, targetState_ne_initialState]
example :
    BoundedPacketWord.rejected ∉ boundedPacketGrammar initialState := by
  simp [boundedPacketGrammar]
example :
    BoundedPacketWord.rejected ∉ boundedPacketGrammar targetState := by
  simp [boundedPacketGrammar, targetState_ne_initialState]

end RcpRclmRuntimePhase5AReferenceGrammar
"""
    return source.encode("utf-8")


def verify_reference_grammar_with_lean(
    compiler: LeanCompiler,
) -> ReferenceGrammarLeanConformanceReport:
    source = reference_grammar_lean_source()
    source_hash = sha256_hex(source)
    guard = scan_source_bytes(
        source,
        source_path=REFERENCE_GRAMMAR_SOURCE_PATH,
    )
    compilation = (
        compiler.compile_source(
            source,
            source_name=REFERENCE_GRAMMAR_SOURCE_PATH,
        )
        if guard.clean
        else None
    )
    return ReferenceGrammarLeanConformanceReport(
        source_hash=source_hash,
        source_path=REFERENCE_GRAMMAR_SOURCE_PATH,
        source_guard=guard,
        compilation=compilation,
    )
