from __future__ import annotations
import tempfile
from collections.abc import Sequence
from pathlib import Path
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.checker.hardened import Phase4HardenedRequest, check_hardened_transition
from rcp_rclm_runtime.checker.integrity import build_reference_package_integrity
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import build_lean_reference_packet, reference_protected_distinctions, reference_resource_record, reference_trust_anchor
from rcp_rclm_runtime.generator.grammar import validate_untrusted_proposal
from rcp_rclm_runtime.generator.protocol import ReferenceGeneratorInputRecord, ReferenceProposalRecord
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationEvidence
from rcp_rclm_runtime.successor.package_builder import Phase6PackageBuildEvidence, build_candidate_package, verify_candidate_package
from rcp_rclm_runtime.successor.records import Phase6SelectionRecord
from rcp_rclm_runtime.successor.selector import Phase6SelectionError, select_reference_successor
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence, construct_reference_certificate
from rcp_rclm_runtime.promotion.evaluator import Phase7EvaluationError, Phase7EvaluationEvidence, evaluate_realized_candidate
from rcp_rclm_runtime.promotion.policy import PHASE7_CONTROLLER_ENVIRONMENT_HASH
from rcp_rclm_runtime.promotion.records import Phase7ControllerBudgetRecord, Phase7ControllerPolicyRecord, Phase7ReasonCode, Phase7StageResult
from rcp_rclm_runtime.promotion.store import RUNS_DIRECTORY_NAME, Phase7StoreSnapshot
from rcp_rclm_runtime.promotion.controller_types import GeneratorCallable, LeanVerifierCallable, Phase7AttemptExecution, _AttemptArtifacts, _ATTEMPT_STAGE_ORDER
from rcp_rclm_runtime.promotion.controller_support import _directory_tree_hash, _generator_input_from_snapshot, _generator_stage, _write_generator_evidence, _write_json_artifact, _write_lean_evidence
from rcp_rclm_runtime.promotion.attempt_finish import _finish_attempt

def _run_phase7_attempt(*, snapshot: Phase7StoreSnapshot, run_id: str, attempt_index: int, units_before: int, policy: Phase7ControllerPolicyRecord, budget: Phase7ControllerBudgetRecord, generator: GeneratorCallable, verify_lean: LeanVerifierCallable) -> Phase7AttemptExecution:
    staging_root = Path(tempfile.mkdtemp(prefix=f'.{run_id}-attempt-{attempt_index:04d}-', dir=snapshot.store_root / RUNS_DIRECTORY_NAME))
    evidence_root = staging_root / 'evidence'
    evidence_root.mkdir(parents=True, exist_ok=False)
    candidate_root = staging_root / 'candidate'
    artifacts = _AttemptArtifacts.empty()
    stages: list[Phase7StageResult] = []
    proposal: ReferenceProposalRecord | None = None
    selection: Phase6SelectionRecord | None = None
    phase6: Phase6PackageBuildEvidence | None = None
    evaluation: Phase7EvaluationEvidence | None = None
    certificate: Phase7CertificateEvidence | None = None
    lean_evidence: LeanBridgeVerificationEvidence | None = None
    checker_report_hash: str | None = None
    candidate_tree_hash: str | None = None
    generator_input = _generator_input_from_snapshot(snapshot)
    _write_json_artifact(evidence_root, 'policy.json', policy.to_json(), artifacts)
    _write_json_artifact(evidence_root, 'budget.json', budget.to_json(), artifacts)
    _write_json_artifact(evidence_root, 'generator_input.json', generator_input.to_json(), artifacts)
    try:
        first = generator(generator_input, attempt_index, 0)
        second = generator(generator_input, attempt_index, 1)
        _write_generator_evidence(evidence_root, 'first', first, artifacts)
        _write_generator_evidence(evidence_root, 'second', second, artifacts)
        generator_stage, proposal = _generator_stage(first, second)
        stages.append(generator_stage)
        if generator_stage.status != 'pass' or proposal is None:
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        _write_json_artifact(evidence_root, 'proposal.json', proposal.to_json(), artifacts)
        proposal_validation = validate_untrusted_proposal(generator_input, proposal)
        proposal_ok = proposal_validation.status == 'pass'
        proposal_stage = Phase7StageResult.build('proposal_validation', 'pass' if proposal_ok else 'fail', () if proposal_ok else (Phase7ReasonCode.PROPOSAL_INVALID,), {'generator_result': proposal_validation.to_json(), 'proposal_hash': proposal.proposal_hash, 'candidate_successor_field_consumed': False, 'certificate_field_consumed': False, 'acceptance_field_consumed': False})
        stages.append(proposal_stage)
        if not proposal_ok:
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        try:
            selection = select_reference_successor(generator_input, proposal, snapshot.predecessor)
        except Phase6SelectionError as exc:
            stages.append(Phase7StageResult.build('selection', 'fail', (Phase7ReasonCode.SELECTION_FAILED,), {'phase6_reason_code': exc.reason_code.value, 'detail_hash': sha256_hex(exc.detail.encode('utf-8'))}))
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        _write_json_artifact(evidence_root, 'selection.json', selection.to_json(), artifacts)
        stages.append(Phase7StageResult.build('selection', 'pass', (), {'selection_hash': selection.selection_hash, 'proposal_hash': proposal.proposal_hash, 'substantive_component_kinds': list(selection.substantive_component_kinds), 'model_score_consumed': False, 'manual_repair_consumed': False}))
        phase6 = build_candidate_package(snapshot.predecessor_root, selection, budget.phase6_budget, candidate_root)
        _write_json_artifact(evidence_root, 'phase6_report.json', phase6.report.to_json(), artifacts)
        if not phase6.report.built or phase6.output_root is None:
            stages.append(Phase7StageResult.build('realization', 'fail', (Phase7ReasonCode.REALIZATION_FAILED,), {'phase6_verdict': phase6.report.verdict, 'phase6_reason_codes': [reason.value for reason in phase6.report.reason_codes], 'phase6_report_hash': phase6.report.report_hash}))
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        public_manifest = verify_candidate_package(candidate_root)
        candidate_tree_hash = _directory_tree_hash(candidate_root)
        artifacts.add_hash('candidate_package_tree', candidate_tree_hash)
        stages.append(Phase7StageResult.build('realization', 'pass', (), {'phase6_report_hash': phase6.report.report_hash, 'candidate_manifest_hash': public_manifest.manifest_hash, 'candidate_payload_tree_hash': public_manifest.payload_tree_hash, 'candidate_package_tree_hash': candidate_tree_hash, 'candidate_status': public_manifest.candidate_status, 'promotion_licensed_by_phase6': phase6.report.promotion_licensed}))
        try:
            evaluation = evaluate_realized_candidate(snapshot.predecessor_root, candidate_root, selection)
        except Phase7EvaluationError as exc:
            stages.append(Phase7StageResult.build('objective_evaluation', 'fail', (Phase7ReasonCode.EVALUATION_FAILED,), {'detail_hash': sha256_hex(exc.detail.encode('utf-8'))}))
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        _write_json_artifact(evidence_root, 'evaluation.json', evaluation.to_json(), artifacts)
        stages.append(Phase7StageResult.build('objective_evaluation', 'pass', (), {'evaluation_hash': evaluation.evaluation_hash, 'candidate_package_tree_hash': evaluation.candidate_package_tree_hash, 'evaluator_policy_hash': evaluation.evaluation.evaluator_policy_hash, 'controller_mathematical_acceptance_calculated': False}))
        try:
            certificate = construct_reference_certificate(proposal)
        except (TypeError, ValueError) as exc:
            stages.append(Phase7StageResult.build('certificate_construction', 'fail', (Phase7ReasonCode.CERTIFICATE_FAILED,), {'error_type': type(exc).__name__, 'detail_hash': sha256_hex(str(exc).encode('utf-8'))}))
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        _write_json_artifact(evidence_root, 'certificate.json', certificate.to_json(), artifacts)
        stages.append(Phase7StageResult.build('certificate_construction', 'pass', (), {'certificate_hash': certificate.certificate_hash, 'certificate_name': certificate.certificate_name, 'generator_certificate_field_consumed': False}))
        packet = build_lean_reference_packet(evaluation.predecessor.state, evaluation.candidate, certificate.certificate)
        try:
            lean_evidence = verify_lean(packet)
        except Exception as exc:
            stages.append(Phase7StageResult.build('lean_bridge', 'indeterminate', (Phase7ReasonCode.LEAN_REJECTED,), {'error_type': type(exc).__name__, 'detail_hash': sha256_hex(str(exc).encode('utf-8')), 'packet_hash': packet.packet_hash}))
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        _write_lean_evidence(evidence_root, lean_evidence, artifacts)
        if lean_evidence.report.bridge_verdict == 'accept':
            lean_status = 'pass'
            lean_reasons: Sequence[Phase7ReasonCode] = ()
        elif lean_evidence.report.bridge_verdict == 'indeterminate':
            lean_status = 'indeterminate'
            lean_reasons = (Phase7ReasonCode.LEAN_REJECTED,)
        else:
            lean_status = 'fail'
            lean_reasons = (Phase7ReasonCode.LEAN_REJECTED,)
        stages.append(Phase7StageResult.build('lean_bridge', lean_status, lean_reasons, {'packet_hash': packet.packet_hash, 'lean_report_hash': lean_evidence.report.report_hash, 'bridge_verdict': lean_evidence.report.bridge_verdict, 'source_guard_clean': lean_evidence.source_guard.clean, 'timed_out': lean_evidence.report.timed_out}))
        if lean_status != 'pass':
            return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
        resource_record = reference_resource_record(budget_units=budget.max_attempt_units, consumed_units=units_before + budget.attempt_unit_cost, environment_hash=PHASE7_CONTROLLER_ENVIRONMENT_HASH)
        checker_request = Phase3CheckerRequest(transition_id=generator_input.transition_id, predecessor=evaluation.predecessor.state, candidate=evaluation.candidate, certificate=certificate.certificate, trust_anchor=reference_trust_anchor(), resource_record=resource_record, protected_distinctions=reference_protected_distinctions('gate_b_classical'), evaluation_evidence=evaluation.evaluation, lean_bridge_report=lean_evidence.report)
        package_integrity = build_reference_package_integrity(checker_request)
        hardened_request = Phase4HardenedRequest(checker_request=checker_request, package_integrity=package_integrity)
        hardened_report = check_hardened_transition(hardened_request)
        checker_report_hash = hardened_report.report_hash
        _write_json_artifact(evidence_root, 'checker_request.json', checker_request.to_json(), artifacts)
        _write_json_artifact(evidence_root, 'package_integrity.json', package_integrity.to_json(), artifacts)
        _write_json_artifact(evidence_root, 'hardened_checker_report.json', hardened_report.to_json(), artifacts)
        candidate_tree_after = _directory_tree_hash(candidate_root)
        candidate_unchanged = candidate_tree_after == candidate_tree_hash
        if not candidate_unchanged:
            checker_status = 'fail'
            checker_reasons: Sequence[Phase7ReasonCode] = (Phase7ReasonCode.CANDIDATE_MUTATED,)
        elif hardened_report.verdict == 'accept':
            checker_status = 'pass'
            checker_reasons = ()
        elif hardened_report.verdict == 'indeterminate':
            checker_status = 'indeterminate'
            checker_reasons = (Phase7ReasonCode.CHECKER_REJECTED,)
        else:
            checker_status = 'fail'
            checker_reasons = (Phase7ReasonCode.CHECKER_REJECTED,)
        stages.append(Phase7StageResult.build('hardened_checker', checker_status, checker_reasons, {'hardened_report_hash': hardened_report.report_hash, 'checker_verdict': hardened_report.verdict, 'checker_accepted': hardened_report.accepted, 'candidate_tree_hash_before': candidate_tree_hash, 'candidate_tree_hash_after': candidate_tree_after, 'candidate_unchanged': candidate_unchanged, 'controller_authoritative_math_calculated': False}))
        candidate_tree_hash = candidate_tree_after
        return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
    except Exception as exc:
        next_stage = _ATTEMPT_STAGE_ORDER[min(len(stages), len(_ATTEMPT_STAGE_ORDER) - 2)]
        stages.append(Phase7StageResult.build(next_stage, 'fail', (Phase7ReasonCode.INTERNAL_ERROR,), {'error_type': type(exc).__name__, 'detail_hash': sha256_hex(str(exc).encode('utf-8'))}))
        return _finish_attempt(snapshot=snapshot, run_id=run_id, attempt_index=attempt_index, units_consumed=budget.attempt_unit_cost, generator_input=generator_input, stages=stages, artifacts=artifacts, staging_root=staging_root, evidence_root=evidence_root, proposal=proposal, selection=selection, phase6=phase6, evaluation=evaluation, certificate=certificate, lean_evidence=lean_evidence, checker_report_hash=checker_report_hash, candidate_tree_hash=candidate_tree_hash, policy=policy)
