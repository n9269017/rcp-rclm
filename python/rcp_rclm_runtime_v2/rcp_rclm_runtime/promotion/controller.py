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


from rcp_rclm_runtime.promotion.controller_types import GeneratorCallable, LeanVerifierCallable, Phase7AttemptExecution
from rcp_rclm_runtime.promotion.attempt import _run_phase7_attempt
from rcp_rclm_runtime.promotion.controller_support import _controller_report, _reference_generator_callable

def run_phase7_promotion_controller(store_root: Path, verify_lean: LeanVerifierCallable, *, run_label: str, policy: Phase7ControllerPolicyRecord | None=None, budget: Phase7ControllerBudgetRecord | None=None, generator: GeneratorCallable | None=None) -> Phase7ControllerReport:
    resolved_policy = policy or reference_phase7_policy()
    resolved_budget = budget or reference_phase7_budget()
    generator_callable = generator or _reference_generator_callable
    initial_snapshot = load_active_phase7_store(store_root, resolved_policy)
    run_id = phase7_run_id(run_label=run_label, active_pointer_hash=initial_snapshot.pointer.pointer_hash, policy_hash=resolved_policy.policy_hash, budget_hash=resolved_budget.budget_hash)
    attempts: list[Phase7AttemptReport] = []
    ledger_hashes: list[str] = []
    units_consumed = 0
    snapshot = initial_snapshot
    with Phase7StoreLock(snapshot.store_root, run_id):
        for attempt_index in range(resolved_budget.max_attempts):
            if units_consumed + resolved_budget.attempt_unit_cost > resolved_budget.max_attempt_units:
                break
            execution = _run_phase7_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_before=units_consumed, policy=resolved_policy, budget=resolved_budget, generator=generator_callable, verify_lean=verify_lean)
            attempt_root = publish_phase7_attempt_directory(snapshot.store_root, run_id, attempt_index, execution.staging_root)
            report = execution.report
            attempts.append(report)
            units_consumed += report.controller_units_consumed
            if report.verdict == 'accept':
                candidate_root = attempt_root / 'candidate'
                evidence_root = attempt_root / 'evidence'
                try:
                    commit = promote_phase7_candidate(snapshot, candidate_root, evidence_root, report, resolved_policy)
                except Phase7StoreError as exc:
                    final_snapshot = load_active_phase7_store(snapshot.store_root, resolved_policy)
                    controller_report = _controller_report(run_id=run_id, verdict='indeterminate', reason_codes=(Phase7ReasonCode.PROMOTION_FAILED, exc.reason_code), policy=resolved_policy, budget=resolved_budget, initial_snapshot=initial_snapshot, final_snapshot=final_snapshot, attempts=attempts, units_consumed=units_consumed, promoted_package_hash=None, ledger_hashes=ledger_hashes)
                    write_phase7_run_report(snapshot.store_root, run_id, controller_report.to_json())
                    return controller_report
                snapshot = commit.snapshot
                ledger_hashes.append(commit.ledger_entry.entry_hash)
                controller_report = _controller_report(run_id=run_id, verdict='promoted', reason_codes=(), policy=resolved_policy, budget=resolved_budget, initial_snapshot=initial_snapshot, final_snapshot=snapshot, attempts=attempts, units_consumed=units_consumed, promoted_package_hash=commit.package_manifest.package_hash, ledger_hashes=ledger_hashes)
                write_phase7_run_report(snapshot.store_root, run_id, controller_report.to_json())
                return controller_report
            event = 'indeterminate' if report.verdict == 'indeterminate' else 'rejection'
            snapshot, entry = append_phase7_nonpromotion(snapshot, report, resolved_policy, event=event)
            ledger_hashes.append(entry.entry_hash)
            if report.verdict == 'indeterminate':
                controller_report = _controller_report(run_id=run_id, verdict='indeterminate', reason_codes=report.reason_codes, policy=resolved_policy, budget=resolved_budget, initial_snapshot=initial_snapshot, final_snapshot=snapshot, attempts=attempts, units_consumed=units_consumed, promoted_package_hash=None, ledger_hashes=ledger_hashes)
                write_phase7_run_report(snapshot.store_root, run_id, controller_report.to_json())
                return controller_report
        final_snapshot = load_active_phase7_store(snapshot.store_root, resolved_policy)
        controller_report = _controller_report(run_id=run_id, verdict='exhausted', reason_codes=(Phase7ReasonCode.BUDGET_EXHAUSTED,), policy=resolved_policy, budget=resolved_budget, initial_snapshot=initial_snapshot, final_snapshot=final_snapshot, attempts=attempts, units_consumed=units_consumed, promoted_package_hash=None, ledger_hashes=ledger_hashes)
        write_phase7_run_report(snapshot.store_root, run_id, controller_report.to_json())
        return controller_report

__all__ = [
    "GeneratorCallable",
    "LeanVerifierCallable",
    "Phase7AttemptExecution",
    "run_phase7_promotion_controller",
]
