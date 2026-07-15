from __future__ import annotations
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from rcp_rclm_runtime.canonical.hashing import build_tree_records, canonical_json_hash, semantic_tree_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.checker.hardened import Phase4HardenedRequest, check_hardened_transition
from rcp_rclm_runtime.checker.integrity import build_reference_package_integrity
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import build_lean_reference_packet, reference_protected_distinctions, reference_resource_record, reference_trust_anchor
from rcp_rclm_runtime.generator.grammar import validate_untrusted_proposal
from rcp_rclm_runtime.generator.process import GeneratorProcessEvidence, run_reference_generator_process
from rcp_rclm_runtime.generator.protocol import GeneratorPredecessorViewRecord, ReferenceGeneratorInputRecord, ReferenceProposalRecord
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationEvidence
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.package_builder import Phase6PackageBuildEvidence, build_candidate_package, verify_candidate_package
from rcp_rclm_runtime.successor.records import Phase6SelectionRecord
from rcp_rclm_runtime.successor.selector import Phase6SelectionError, select_reference_successor
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence, construct_reference_certificate
from rcp_rclm_runtime.promotion.evaluator import Phase7EvaluationError, Phase7EvaluationEvidence, evaluate_realized_candidate
from rcp_rclm_runtime.promotion.policy import PHASE7_CONTROLLER_ENVIRONMENT_HASH, phase7_run_id, reference_phase7_budget, reference_phase7_policy
from rcp_rclm_runtime.promotion.records import Phase7AttemptReport, Phase7ControllerBudgetRecord, Phase7ControllerPolicyRecord, Phase7ControllerReport, Phase7ReasonCode, Phase7StageResult
from rcp_rclm_runtime.promotion.store import RUNS_DIRECTORY_NAME, Phase7StoreError, Phase7StoreLock, Phase7StoreSnapshot, append_phase7_nonpromotion, load_active_phase7_store, promote_phase7_candidate, publish_phase7_attempt_directory, write_phase7_run_report
GeneratorCallable = Callable[[ReferenceGeneratorInputRecord, int, int], GeneratorProcessEvidence]
LeanVerifierCallable = Callable[[LeanReferencePacket], LeanBridgeVerificationEvidence]
_ATTEMPT_STAGE_ORDER: Final[Sequence[str]] = ('generator', 'proposal_validation', 'selection', 'realization', 'objective_evaluation', 'certificate_construction', 'lean_bridge', 'hardened_checker', 'fallback_rollback')


@dataclass(frozen=True, slots=True)
class Phase7AttemptExecution:
    report: Phase7AttemptReport
    staging_root: Path
    evidence_root: Path
    candidate_root: Path | None

@dataclass(frozen=True, slots=True)
class _AttemptArtifacts:
    values: dict[str, str]

    @classmethod
    def empty(cls) -> _AttemptArtifacts:
        return cls(values={})

    def add_hash(self, key: str, value: str) -> None:
        self.values[key] = value

    def frozen(self) -> FrozenHashMap:
        return FrozenHashMap.from_mapping(self.values, 'phase7_attempt.artifact_hashes')
