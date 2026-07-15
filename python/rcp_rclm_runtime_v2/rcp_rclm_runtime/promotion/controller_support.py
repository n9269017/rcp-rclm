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


from rcp_rclm_runtime.promotion.controller_types import GeneratorCallable, LeanVerifierCallable, Phase7AttemptExecution, _AttemptArtifacts

def _generator_stage(first: GeneratorProcessEvidence, second: GeneratorProcessEvidence) -> tuple[Phase7StageResult, ReferenceProposalRecord | None]:
    process_success = first.report.verdict == 'success' and second.report.verdict == 'success' and (first.proposal is not None) and (second.proposal is not None) and first.source_guard.clean and second.source_guard.clean
    deterministic = first.input_bytes == second.input_bytes and first.stdout == second.stdout and (first.stderr == second.stderr) and (first.proposal == second.proposal) and (first.report.to_json() == second.report.to_json()) and (first.source_guard.to_json() == second.source_guard.to_json())
    timed_out = first.report.timed_out or second.report.timed_out
    if timed_out:
        status = 'indeterminate'
        reasons: Sequence[Phase7ReasonCode] = (Phase7ReasonCode.GENERATOR_FAILED,)
    elif not process_success:
        status = 'fail'
        reasons = (Phase7ReasonCode.GENERATOR_FAILED,)
    elif not deterministic:
        status = 'fail'
        reasons = (Phase7ReasonCode.GENERATOR_REPLAY_MISMATCH,)
    else:
        status = 'pass'
        reasons = ()
    proposal = first.proposal if status == 'pass' else None
    return (Phase7StageResult.build('generator', status, reasons, {'first_process_report_hash': canonical_json_hash(first.report.to_json()), 'second_process_report_hash': canonical_json_hash(second.report.to_json()), 'first_source_guard_hash': first.source_guard.report_hash, 'second_source_guard_hash': second.source_guard.report_hash, 'process_success': process_success, 'deterministic_replay': deterministic, 'timed_out': timed_out, 'write_handles_granted': [], 'network_endpoints_granted': [], 'checker_source_visible': False, 'trust_anchor_visible': False, 'promotion_ledger_visible': False}), proposal)

def _generator_input_from_snapshot(snapshot: Phase7StoreSnapshot) -> ReferenceGeneratorInputRecord:
    core = snapshot.predecessor.state.core
    if not hasattr(core, 'state') or core.state not in {'initial', 'target'}:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'active predecessor is outside the finite Gate B seed domain')
    template = reference_generator_input(core.state)
    predecessor = GeneratorPredecessorViewRecord(package_id=snapshot.predecessor.manifest.package_id, manifest_hash=snapshot.predecessor.manifest.phase5_manifest_hash, semantic_tree_hash=snapshot.predecessor.manifest.payload_tree_hash, state_hash=snapshot.predecessor.manifest.state_hash, state=snapshot.predecessor.state)
    if predecessor.package_id != template.predecessor.package_id:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'active predecessor package ID is not bound to the finite reference transition')
    if predecessor.manifest_hash != template.predecessor.manifest_hash:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'active predecessor logical manifest binding differs from the reference grammar')
    return ReferenceGeneratorInputRecord(transition_id=template.transition_id, predecessor=predecessor, policy=template.policy, objective=template.objective, budget=template.budget)

def _reference_generator_callable(request: ReferenceGeneratorInputRecord, attempt_index: int, replay_index: int) -> GeneratorProcessEvidence:
    if attempt_index < 0 or replay_index not in {0, 1}:
        raise ValueError('invalid deterministic generator invocation index')
    return run_reference_generator_process(request)

def _active_pointer_observation(snapshot: Phase7StoreSnapshot, policy: Phase7ControllerPolicyRecord) -> tuple[str, bool]:
    try:
        observed = load_active_phase7_store(snapshot.store_root, policy).pointer
        return (observed.pointer_hash, observed.pointer_hash == snapshot.pointer.pointer_hash)
    except Exception as exc:
        active_path = snapshot.store_root / 'active.json'
        if active_path.exists():
            observed_hash = sha256_hex(active_path.read_bytes())
        else:
            observed_hash = sha256_hex(str(exc).encode('utf-8'))
        return (observed_hash, False)

def _write_generator_evidence(evidence_root: Path, prefix: str, evidence: GeneratorProcessEvidence, artifacts: _AttemptArtifacts) -> None:
    _write_bytes_artifact(evidence_root, f'{prefix}_generator_input.json', evidence.input_bytes, artifacts)
    _write_bytes_artifact(evidence_root, f'{prefix}_generator_stdout.bin', evidence.stdout, artifacts)
    _write_bytes_artifact(evidence_root, f'{prefix}_generator_stderr.bin', evidence.stderr, artifacts)
    _write_json_artifact(evidence_root, f'{prefix}_process_report.json', evidence.report.to_json(), artifacts)
    _write_json_artifact(evidence_root, f'{prefix}_source_guard.json', evidence.source_guard.to_json(), artifacts)

def _write_lean_evidence(evidence_root: Path, evidence: LeanBridgeVerificationEvidence, artifacts: _AttemptArtifacts) -> None:
    _write_bytes_artifact(evidence_root, 'generated_certificate.lean', evidence.generated.source_bytes, artifacts)
    _write_json_artifact(evidence_root, 'generated_source.json', evidence.generated.to_json(), artifacts)
    _write_json_artifact(evidence_root, 'lean_source_guard.json', evidence.source_guard.to_json(), artifacts)
    _write_json_artifact(evidence_root, 'lean_report.json', evidence.report.to_json(), artifacts)
    if evidence.compilation is not None:
        _write_json_artifact(evidence_root, 'lean_compilation.json', evidence.compilation.to_json(), artifacts)
        _write_bytes_artifact(evidence_root, 'lean_stdout.bin', evidence.compilation.stdout, artifacts)
        _write_bytes_artifact(evidence_root, 'lean_stderr.bin', evidence.compilation.stderr, artifacts)
    if evidence.parsed_verdict is not None:
        _write_json_artifact(evidence_root, 'parsed_lean_verdict.json', evidence.parsed_verdict.to_json(), artifacts)

def _write_json_artifact(root: Path, name: str, value: object, artifacts: _AttemptArtifacts | None) -> str:
    content = canonical_json_bytes(value)
    return _write_bytes_artifact(root, name, content, artifacts)

def _write_bytes_artifact(root: Path, name: str, content: bytes, artifacts: _AttemptArtifacts | None) -> str:
    output = root / name
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f'attempt artifact already exists: {name}')
    output.write_bytes(content)
    output.chmod(420)
    digest = sha256_hex(content)
    if artifacts is not None:
        artifacts.add_hash(f'evidence/{name}', digest)
    return digest

def _directory_tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root))

def _controller_report(*, run_id: str, verdict: str, reason_codes: Sequence[Phase7ReasonCode], policy: Phase7ControllerPolicyRecord, budget: Phase7ControllerBudgetRecord, initial_snapshot: Phase7StoreSnapshot, final_snapshot: Phase7StoreSnapshot, attempts: Sequence[Phase7AttemptReport], units_consumed: int, promoted_package_hash: str | None, ledger_hashes: Sequence[str]) -> Phase7ControllerReport:
    hashes = {'policy': policy.policy_hash, 'budget': budget.budget_hash, 'initial_pointer': initial_snapshot.pointer.pointer_hash, 'final_pointer': final_snapshot.pointer.pointer_hash, 'initial_active_package': initial_snapshot.pointer.active_package_hash, 'final_active_package': final_snapshot.pointer.active_package_hash}
    for index, attempt in enumerate(attempts):
        hashes[f'attempt_{index:04d}'] = attempt.report_hash
    for index, entry_hash in enumerate(ledger_hashes):
        hashes[f'ledger_{index:04d}'] = entry_hash
    if promoted_package_hash is not None:
        hashes['promoted_package'] = promoted_package_hash
    return Phase7ControllerReport(run_id=run_id, verdict=verdict, reason_codes=tuple(dict.fromkeys(reason_codes)), policy=policy, budget=budget, initial_pointer=initial_snapshot.pointer, final_pointer=final_snapshot.pointer, attempts=tuple(attempts), units_consumed=units_consumed, promoted_package_hash=promoted_package_hash, ledger_entry_hashes=tuple(ledger_hashes), artifact_hashes=FrozenHashMap.from_mapping(hashes, 'phase7_controller_report.artifact_hashes'))
