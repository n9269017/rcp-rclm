from __future__ import annotations
from pathlib import Path
from rcp_rclm_runtime.generator.protocol import ReferenceGeneratorInputRecord, ReferenceProposalRecord
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationEvidence
from rcp_rclm_runtime.successor.package_builder import Phase6PackageBuildEvidence
from rcp_rclm_runtime.successor.records import Phase6SelectionRecord
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.evaluator import Phase7EvaluationEvidence
from rcp_rclm_runtime.promotion.records import Phase7AttemptReport, Phase7ControllerPolicyRecord, Phase7ReasonCode, Phase7StageResult
from rcp_rclm_runtime.promotion.store import Phase7StoreSnapshot
from rcp_rclm_runtime.promotion.controller_types import Phase7AttemptExecution, _AttemptArtifacts, _ATTEMPT_STAGE_ORDER
from rcp_rclm_runtime.promotion.controller_support import _active_pointer_observation, _write_json_artifact

def _finish_attempt(*, snapshot: Phase7StoreSnapshot, run_id: str, attempt_index: int, units_consumed: int, generator_input: ReferenceGeneratorInputRecord, stages: list[Phase7StageResult], artifacts: _AttemptArtifacts, staging_root: Path, evidence_root: Path, proposal: ReferenceProposalRecord | None, selection: Phase6SelectionRecord | None, phase6: Phase6PackageBuildEvidence | None, evaluation: Phase7EvaluationEvidence | None, certificate: Phase7CertificateEvidence | None, lean_evidence: LeanBridgeVerificationEvidence | None, checker_report_hash: str | None, candidate_tree_hash: str | None, policy: Phase7ControllerPolicyRecord) -> Phase7AttemptExecution:
    while len(stages) < len(_ATTEMPT_STAGE_ORDER) - 1:
        stages.append(Phase7StageResult.build(_ATTEMPT_STAGE_ORDER[len(stages)], 'not_evaluated', (), {}))
    active_after_hash, active_unchanged = _active_pointer_observation(snapshot, policy)
    if phase6 is None or phase6.report.realization is None:
        candidate_fallback = True
        rollback_hash = None
    else:
        candidate_fallback = phase6.report.realization.rollback.verified
        rollback_hash = phase6.report.realization.rollback.rollback_hash
    fallback_ok = active_unchanged and candidate_fallback
    stages.append(Phase7StageResult.build('fallback_rollback', 'pass' if fallback_ok else 'fail', () if fallback_ok else (Phase7ReasonCode.ROLLBACK_FAILED,), {'active_pointer_hash_before': snapshot.pointer.pointer_hash, 'active_pointer_hash_after': active_after_hash, 'active_pointer_unchanged': active_unchanged, 'candidate_rollback_verified': candidate_fallback, 'candidate_rollback_record_hash': rollback_hash, 'manual_repair_count': 0}))
    failed = any((stage.status == 'fail' for stage in stages))
    indeterminate = any((stage.status == 'indeterminate' for stage in stages))
    if failed:
        verdict = 'reject'
    elif indeterminate:
        verdict = 'indeterminate'
    else:
        verdict = 'accept'
    reason_codes = tuple(dict.fromkeys((reason for stage in stages for reason in stage.reason_codes)))
    if verdict != 'accept' and (not reason_codes):
        reason_codes = (Phase7ReasonCode.INTERNAL_ERROR,)
    if phase6 is not None:
        phase6_report_hash = phase6.report.report_hash
    else:
        phase6_report_hash = None
    attempt = Phase7AttemptReport(run_id=run_id, attempt_index=attempt_index, transition_id=generator_input.transition_id, verdict=verdict, reason_codes=reason_codes, controller_units_consumed=units_consumed, active_pointer_hash_before=snapshot.pointer.pointer_hash, active_pointer_hash_after=active_after_hash, generator_input_hash=generator_input.input_hash, proposal_hash=None if proposal is None else proposal.proposal_hash, selection_hash=None if selection is None else selection.selection_hash, phase6_report_hash=phase6_report_hash, candidate_package_tree_hash=candidate_tree_hash, evaluation_hash=None if evaluation is None else evaluation.evaluation_hash, certificate_hash=None if certificate is None else certificate.certificate_hash, lean_report_hash=None if lean_evidence is None else lean_evidence.report.report_hash, checker_report_hash=checker_report_hash, fallback_rollback_verified=fallback_ok, manual_repair_count=0, stages=tuple(stages), artifact_hashes=artifacts.frozen())
    _write_json_artifact(evidence_root, 'attempt_report.json', attempt.to_json(), None)
    return Phase7AttemptExecution(report=attempt, staging_root=staging_root, evidence_root=evidence_root, candidate_root=staging_root / 'candidate' if (staging_root / 'candidate').exists() else None)
