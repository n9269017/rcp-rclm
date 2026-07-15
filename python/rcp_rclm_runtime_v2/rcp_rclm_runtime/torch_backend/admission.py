from __future__ import annotations

import importlib
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedRequest,
    Phase4HardenedReport,
    check_hardened_transition,
)
from rcp_rclm_runtime.checker.integrity import build_reference_package_integrity
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    canonical_rclm_certificate,
    reference_protected_distinctions,
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationEvidence
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.controller_support import (
    _controller_report,
    _directory_tree_hash,
    _write_bytes_artifact,
    _write_json_artifact,
    _write_lean_evidence,
)
from rcp_rclm_runtime.promotion.evaluator import (
    Phase7EvaluationEvidence,
    evaluate_realized_candidate,
)
from rcp_rclm_runtime.promotion.policy import phase7_run_id
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_report import Phase7ControllerReport
from rcp_rclm_runtime.promotion.record_stage import Phase7StageResult
from rcp_rclm_runtime.promotion.records import Phase7ReasonCode
from rcp_rclm_runtime.promotion.store import (
    Phase7StoreLock,
    Phase7StoreSnapshot,
    append_phase7_nonpromotion,
    bootstrap_phase7_store,
    load_active_phase7_store,
    promote_phase7_candidate,
    publish_phase7_attempt_directory,
    write_phase7_run_report,
)
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.package_builder import (
    Phase6PackageBuildEvidence,
    build_candidate_package,
    verify_candidate_package,
)
from rcp_rclm_runtime.torch_backend.adapter import (
    PilotHostSelectionEvidence,
    PilotProposalValidationEvidence,
    build_host_phase6_selection,
    validate_pytorch_proposal_output,
)
from rcp_rclm_runtime.torch_backend.exact_evaluator import (
    ExactEvaluationRecord,
    evaluate_quantized_transition,
)
from rcp_rclm_runtime.torch_backend.pilot_data import (
    pilot_heldout_evaluation_data,
)
from rcp_rclm_runtime.torch_backend.pilot_policy import (
    PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
    pytorch_pilot_phase7_budget,
    pytorch_pilot_phase7_policy,
)
from rcp_rclm_runtime.torch_backend.pilot_reference import (
    build_pytorch_pilot_predecessor,
    request_for_pytorch_pilot_predecessor,
)
if TYPE_CHECKING:
    from rcp_rclm_runtime.torch_backend.process import PilotProcessEvidence
from rcp_rclm_runtime.torch_backend.protocol import PilotRequestBinding

LeanVerifierCallable = Callable[[LeanReferencePacket], LeanBridgeVerificationEvidence]
PilotControllerVerdict = Literal["promoted", "rejected", "indeterminate"]
PILOT_STAGE_ORDER: Final[Sequence[str]] = (
    "generator",
    "proposal_validation",
    "selection",
    "realization",
    "objective_evaluation",
    "certificate_construction",
    "lean_bridge",
    "hardened_checker",
    "fallback_rollback",
)


@dataclass(frozen=True, slots=True)
class PilotAdmissionEvidence:
    controller_report: Phase7ControllerReport
    attempt_report: Phase7AttemptReport
    store_root: Path
    promoted_package_root: Path | None
    verdict: PilotControllerVerdict

    @property
    def report_hash(self) -> str:
        return self.controller_report.report_hash


@dataclass(frozen=True, slots=True)
class _ArtifactLedger:
    values: dict[str, str]

    @classmethod
    def empty(cls) -> _ArtifactLedger:
        return cls(values={})

    def add(self, key: str, digest: str) -> None:
        self.values[key] = digest

    def frozen(self) -> FrozenHashMap:
        return FrozenHashMap.from_mapping(
            self.values,
            "pytorch_pilot.attempt.artifact_hashes",
        )


def bootstrap_pytorch_pilot_store(store_root: Path) -> None:
    resolved = store_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"pilot store already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-pytorch-bootstrap-",
        dir=resolved.parent,
    ) as temporary_directory:
        predecessor = build_pytorch_pilot_predecessor(
            Path(temporary_directory) / "predecessor"
        )
        bootstrap_phase7_store(
            resolved,
            predecessor_root := predecessor.payload_root.parent,
            pytorch_pilot_phase7_policy(),
            bootstrap_id="pytorch-pilot-bootstrap-v1",
        )
        if predecessor_root.exists():
            shutil.rmtree(predecessor_root)


def run_pytorch_pilot_controller(
    store_root: Path,
    verify_lean: LeanVerifierCallable,
    *,
    run_label: str,
    evaluation_data: object | None = None,
) -> PilotAdmissionEvidence:
    policy = pytorch_pilot_phase7_policy()
    budget = pytorch_pilot_phase7_budget()
    snapshot = load_active_phase7_store(store_root, policy)
    initial_snapshot = snapshot
    run_id = phase7_run_id(
        run_label=run_label,
        active_pointer_hash=snapshot.pointer.pointer_hash,
        policy_hash=policy.policy_hash,
        budget_hash=budget.budget_hash,
    )
    resolved_evaluation_data = (
        pilot_heldout_evaluation_data()
        if evaluation_data is None
        else evaluation_data
    )
    with Phase7StoreLock(snapshot.store_root, run_id):
        staging_root = Path(
            tempfile.mkdtemp(
                prefix=f".{run_id}-attempt-0000-",
                dir=snapshot.store_root / "runs",
            )
        )
        evidence_root = staging_root / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=False)
        candidate_root = staging_root / "candidate"
        attempt = _execute_pytorch_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=0,
            candidate_root=candidate_root,
            evidence_root=evidence_root,
            verify_lean=verify_lean,
            evaluation_data=resolved_evaluation_data,
        )
        published_attempt = publish_phase7_attempt_directory(
            snapshot.store_root,
            run_id,
            0,
            staging_root,
        )
        if attempt.verdict == "accept":
            commit = promote_phase7_candidate(
                snapshot,
                published_attempt / "candidate",
                published_attempt / "evidence",
                attempt,
                policy,
            )
            final_snapshot = commit.snapshot
            report = _controller_report(
                run_id=run_id,
                verdict="promoted",
                reason_codes=(),
                policy=policy,
                budget=budget,
                initial_snapshot=initial_snapshot,
                final_snapshot=final_snapshot,
                attempts=(attempt,),
                units_consumed=1,
                promoted_package_hash=commit.package_manifest.package_hash,
                ledger_hashes=(commit.ledger_entry.entry_hash,),
            )
            write_phase7_run_report(snapshot.store_root, run_id, report.to_json())
            return PilotAdmissionEvidence(
                controller_report=report,
                attempt_report=attempt,
                store_root=snapshot.store_root,
                promoted_package_root=final_snapshot.package_root,
                verdict="promoted",
            )
        event = "indeterminate" if attempt.verdict == "indeterminate" else "rejection"
        final_snapshot, entry = append_phase7_nonpromotion(
            snapshot,
            attempt,
            policy,
            event=event,
        )
        controller_verdict = "indeterminate" if event == "indeterminate" else "exhausted"
        reasons = attempt.reason_codes or (Phase7ReasonCode.BUDGET_EXHAUSTED,)
        report = _controller_report(
            run_id=run_id,
            verdict=controller_verdict,
            reason_codes=reasons,
            policy=policy,
            budget=budget,
            initial_snapshot=initial_snapshot,
            final_snapshot=final_snapshot,
            attempts=(attempt,),
            units_consumed=1,
            promoted_package_hash=None,
            ledger_hashes=(entry.entry_hash,),
        )
        write_phase7_run_report(snapshot.store_root, run_id, report.to_json())
        return PilotAdmissionEvidence(
            controller_report=report,
            attempt_report=attempt,
            store_root=snapshot.store_root,
            promoted_package_root=None,
            verdict="indeterminate" if event == "indeterminate" else "rejected",
        )


def _execute_pytorch_attempt(
    *,
    snapshot,
    run_id: str,
    attempt_index: int,
    candidate_root: Path,
    evidence_root: Path,
    verify_lean: LeanVerifierCallable,
    evaluation_data: object,
) -> Phase7AttemptReport:
    stages: list[Phase7StageResult] = []
    artifacts = _ArtifactLedger.empty()
    request = request_for_pytorch_pilot_predecessor(
        snapshot.predecessor,
        transition_id=f"{run_id}.attempt-{attempt_index:04d}",
    )
    _write_json(evidence_root, "policy.json", pytorch_pilot_phase7_policy().to_json(), artifacts)
    _write_json(evidence_root, "request.json", request.to_json(), artifacts)

    first_root = evidence_root / "first_proposal_output"
    second_root = evidence_root / "second_proposal_output"
    first = _run_proposal_process_ephemeral(
        request, snapshot.predecessor.payload_root, first_root
    )
    second = _run_proposal_process_ephemeral(
        request, snapshot.predecessor.payload_root, second_root
    )
    _write_process_evidence(evidence_root, "first", first, artifacts)
    _write_process_evidence(evidence_root, "second", second, artifacts)
    process_success = (
        first.report.verdict == "success"
        and second.report.verdict == "success"
        and first.output_root is not None
        and second.output_root is not None
        and first.source_guard.clean
        and second.source_guard.clean
    )
    deterministic = (
        first.stdout == second.stdout
        and first.stderr == second.stderr
        and first.report.output_tree_hash == second.report.output_tree_hash
        and first.report.proposal_hash == second.report.proposal_hash
        and first.source_guard.to_json() == second.source_guard.to_json()
    )
    if first.report.timed_out or second.report.timed_out:
        stages.append(
            Phase7StageResult.build(
                "generator",
                "indeterminate",
                (Phase7ReasonCode.GENERATOR_FAILED,),
                _generator_evidence(first, second, process_success, deterministic),
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
        )
    if not process_success or not deterministic:
        reason = (
            Phase7ReasonCode.GENERATOR_REPLAY_MISMATCH
            if process_success and not deterministic
            else Phase7ReasonCode.GENERATOR_FAILED
        )
        stages.append(
            Phase7StageResult.build(
                "generator",
                "fail",
                (reason,),
                _generator_evidence(first, second, process_success, deterministic),
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
        )
    stages.append(
        Phase7StageResult.build(
            "generator",
            "pass",
            (),
            _generator_evidence(first, second, process_success, deterministic),
        )
    )

    try:
        first_validation = validate_pytorch_proposal_output(
            request.to_json(), first_root, snapshot.predecessor
        )
        second_validation = validate_pytorch_proposal_output(
            request.to_json(), second_root, snapshot.predecessor
        )
        if first_validation.to_json() != second_validation.to_json():
            raise SchemaValidationError(
                "pytorch_pilot.replay", "validated proposal outputs differ"
            )
    except (OSError, SchemaValidationError, ValueError) as exc:
        stages.append(
            Phase7StageResult.build(
                "proposal_validation",
                "fail",
                (Phase7ReasonCode.PROPOSAL_INVALID,),
                {
                    "error_type": type(exc).__name__,
                    "detail_hash": sha256_hex(str(exc).encode("utf-8")),
                },
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
        )
    _write_json(
        evidence_root,
        "proposal_validation.json",
        first_validation.to_json(),
        artifacts,
    )
    stages.append(
        Phase7StageResult.build(
            "proposal_validation",
            "pass",
            (),
            {
                "validation_hash": first_validation.validation_hash,
                "proposal_hash": first_validation.proposal.proposal_hash,
                "candidate_reported_selection_consumed": False,
                "heldout_labels_consumed": False,
                "candidate_acceptance_consumed": False,
            },
        )
    )

    try:
        host_selection = build_host_phase6_selection(
            first_validation,
            first_root,
            snapshot.predecessor,
        )
    except (OSError, SchemaValidationError, ValueError) as exc:
        stages.append(
            Phase7StageResult.build(
                "selection",
                "fail",
                (Phase7ReasonCode.SELECTION_FAILED,),
                {
                    "error_type": type(exc).__name__,
                    "detail_hash": sha256_hex(str(exc).encode("utf-8")),
                },
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
            proposal_validation=first_validation,
        )
    _write_json(
        evidence_root,
        "host_selection.json",
        host_selection.to_json(),
        artifacts,
    )
    stages.append(
        Phase7StageResult.build(
            "selection",
            "pass",
            (),
            {
                "selection_hash": host_selection.selection.selection_hash,
                "selection_constructed_outside_pytorch": True,
                "candidate_reported_selection_consumed": False,
                "substantive_component_kinds": ["model_weights"],
            },
        )
    )

    phase6 = build_candidate_package(
        snapshot.predecessor_root,
        host_selection.selection,
        pytorch_pilot_phase7_budget().phase6_budget,
        candidate_root,
    )
    _write_json(evidence_root, "phase6_report.json", phase6.report.to_json(), artifacts)
    if not phase6.report.built or phase6.output_root is None:
        stages.append(
            Phase7StageResult.build(
                "realization",
                "fail",
                (Phase7ReasonCode.REALIZATION_FAILED,),
                {
                    "phase6_report_hash": phase6.report.report_hash,
                    "reason_codes": [item.value for item in phase6.report.reason_codes],
                },
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
            proposal_validation=first_validation,
            host_selection=host_selection,
            phase6=phase6,
        )
    public_manifest = verify_candidate_package(candidate_root)
    candidate_tree_hash = _directory_tree_hash(candidate_root)
    artifacts.add("candidate_package_tree", candidate_tree_hash)
    stages.append(
        Phase7StageResult.build(
            "realization",
            "pass",
            (),
            {
                "phase6_report_hash": phase6.report.report_hash,
                "candidate_manifest_hash": public_manifest.manifest_hash,
                "candidate_payload_tree_hash": public_manifest.payload_tree_hash,
                "candidate_package_tree_hash": candidate_tree_hash,
                "rollback_verified": bool(
                    phase6.report.realization
                    and phase6.report.realization.rollback.verified
                ),
            },
        )
    )

    _write_json(evidence_root, "evaluation_data.json", evaluation_data, artifacts)
    exact_evaluation = evaluate_quantized_transition(
        snapshot.predecessor.payload_root,
        candidate_root / "payload",
        evaluation_data,
    )
    logical_evaluation = evaluate_realized_candidate(
        snapshot.predecessor_root,
        candidate_root,
        host_selection.selection,
    )
    combined_evaluation = {
        "schema_id": "runtime.pytorch_pilot_combined_evaluation.v1",
        "exact_model_evaluation": exact_evaluation.to_json(),
        "logical_reference_evaluation": logical_evaluation.to_json(),
        "model_objective_authoritative_source": "framework_independent_exact_integer",
        "formal_checker_model_objective_claimed": False,
        "candidate_package_tree_hash": candidate_tree_hash,
    }
    combined_evaluation_hash = canonical_json_hash(combined_evaluation)
    _write_json(evidence_root, "evaluation.json", combined_evaluation, artifacts)
    if not exact_evaluation.evaluation_conditions_met:
        stages.append(
            Phase7StageResult.build(
                "objective_evaluation",
                "fail",
                (Phase7ReasonCode.EVALUATION_FAILED,),
                {
                    "combined_evaluation_hash": combined_evaluation_hash,
                    "exact_evaluation_hash": exact_evaluation.evaluation_hash,
                    "objective_improved": exact_evaluation.objective_improved,
                    "protected_nonregression": exact_evaluation.protected_nonregression,
                    "torch_used_for_evaluation": False,
                },
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
            proposal_validation=first_validation,
            host_selection=host_selection,
            phase6=phase6,
            candidate_tree_hash=candidate_tree_hash,
            combined_evaluation_hash=combined_evaluation_hash,
        )
    stages.append(
        Phase7StageResult.build(
            "objective_evaluation",
            "pass",
            (),
            {
                "combined_evaluation_hash": combined_evaluation_hash,
                "exact_evaluation_hash": exact_evaluation.evaluation_hash,
                "logical_evaluation_hash": logical_evaluation.evaluation_hash,
                "objective_improved": True,
                "protected_nonregression": True,
                "torch_used_for_evaluation": False,
                "controller_mathematical_acceptance_calculated": False,
            },
        )
    )

    certificate = Phase7CertificateEvidence(
        certificate_name="stability",
        certificate=canonical_rclm_certificate("gate_b_classical", "stability"),
    )
    _write_json(evidence_root, "certificate.json", certificate.to_json(), artifacts)
    stages.append(
        Phase7StageResult.build(
            "certificate_construction",
            "pass",
            (),
            {
                "certificate_hash": certificate.certificate_hash,
                "certificate_name": "stability",
                "constructed_outside_pytorch": True,
                "candidate_certificate_consumed": False,
                "formal_claim_limited_to_gate_b_stability": True,
            },
        )
    )

    packet = build_lean_reference_packet(
        logical_evaluation.predecessor.state,
        logical_evaluation.candidate,
        certificate.certificate,
    )
    try:
        lean_evidence = verify_lean(packet)
    except Exception as exc:
        stages.append(
            Phase7StageResult.build(
                "lean_bridge",
                "indeterminate",
                (Phase7ReasonCode.LEAN_REJECTED,),
                {
                    "packet_hash": packet.packet_hash,
                    "error_type": type(exc).__name__,
                    "detail_hash": sha256_hex(str(exc).encode("utf-8")),
                },
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
            proposal_validation=first_validation,
            host_selection=host_selection,
            phase6=phase6,
            candidate_tree_hash=candidate_tree_hash,
            combined_evaluation_hash=combined_evaluation_hash,
            certificate=certificate,
        )
    _write_lean_evidence(evidence_root, lean_evidence, _ArtifactAdapter(artifacts))
    if lean_evidence.report.bridge_verdict != "accept":
        status = (
            "indeterminate"
            if lean_evidence.report.bridge_verdict == "indeterminate"
            else "fail"
        )
        stages.append(
            Phase7StageResult.build(
                "lean_bridge",
                status,
                (Phase7ReasonCode.LEAN_REJECTED,),
                {
                    "packet_hash": packet.packet_hash,
                    "lean_report_hash": lean_evidence.report.report_hash,
                    "bridge_verdict": lean_evidence.report.bridge_verdict,
                    "formal_claim_limited_to_gate_b_stability": True,
                },
            )
        )
        return _finish_pilot_attempt(
            snapshot=snapshot,
            run_id=run_id,
            attempt_index=attempt_index,
            request=request,
            stages=stages,
            artifacts=artifacts,
            evidence_root=evidence_root,
            proposal_validation=first_validation,
            host_selection=host_selection,
            phase6=phase6,
            candidate_tree_hash=candidate_tree_hash,
            combined_evaluation_hash=combined_evaluation_hash,
            certificate=certificate,
            lean_evidence=lean_evidence,
        )
    stages.append(
        Phase7StageResult.build(
            "lean_bridge",
            "pass",
            (),
            {
                "packet_hash": packet.packet_hash,
                "lean_report_hash": lean_evidence.report.report_hash,
                "bridge_verdict": "accept",
                "source_guard_clean": lean_evidence.source_guard.clean,
                "formal_claim_limited_to_gate_b_stability": True,
                "model_objective_proved_by_lean": False,
            },
        )
    )

    checker_request = Phase3CheckerRequest(
        transition_id=request.transition_id,
        predecessor=logical_evaluation.predecessor.state,
        candidate=logical_evaluation.candidate,
        certificate=certificate.certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(
            budget_units=1,
            consumed_units=1,
            environment_hash=PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
        ),
        protected_distinctions=reference_protected_distinctions("gate_b_classical"),
        evaluation_evidence=logical_evaluation.evaluation,
        lean_bridge_report=lean_evidence.report,
    )
    package_integrity = build_reference_package_integrity(checker_request)
    hardened_report = check_hardened_transition(
        Phase4HardenedRequest(
            checker_request=checker_request,
            package_integrity=package_integrity,
        )
    )
    _write_json(evidence_root, "checker_request.json", checker_request.to_json(), artifacts)
    _write_json(evidence_root, "package_integrity.json", package_integrity.to_json(), artifacts)
    _write_json(
        evidence_root,
        "hardened_checker_report.json",
        hardened_report.to_json(),
        artifacts,
    )
    candidate_tree_after = _directory_tree_hash(candidate_root)
    candidate_unchanged = candidate_tree_after == candidate_tree_hash
    if not candidate_unchanged:
        checker_status = "fail"
        checker_reasons: Sequence[Phase7ReasonCode] = (
            Phase7ReasonCode.CANDIDATE_MUTATED,
        )
    elif hardened_report.verdict == "accept":
        checker_status = "pass"
        checker_reasons = ()
    elif hardened_report.verdict == "indeterminate":
        checker_status = "indeterminate"
        checker_reasons = (Phase7ReasonCode.CHECKER_REJECTED,)
    else:
        checker_status = "fail"
        checker_reasons = (Phase7ReasonCode.CHECKER_REJECTED,)
    stages.append(
        Phase7StageResult.build(
            "hardened_checker",
            checker_status,
            checker_reasons,
            {
                "hardened_report_hash": hardened_report.report_hash,
                "checker_verdict": hardened_report.verdict,
                "checker_accepted": hardened_report.accepted,
                "candidate_tree_hash_before": candidate_tree_hash,
                "candidate_tree_hash_after": candidate_tree_after,
                "candidate_unchanged": candidate_unchanged,
                "model_invocations_inside_checker": 0,
                "torch_used_as_checker_authority": False,
                "model_objective_proved_by_checker": False,
                "exact_model_evaluation_required_separately": True,
            },
        )
    )
    return _finish_pilot_attempt(
        snapshot=snapshot,
        run_id=run_id,
        attempt_index=attempt_index,
        request=request,
        stages=stages,
        artifacts=artifacts,
        evidence_root=evidence_root,
        proposal_validation=first_validation,
        host_selection=host_selection,
        phase6=phase6,
        candidate_tree_hash=candidate_tree_after,
        combined_evaluation_hash=combined_evaluation_hash,
        certificate=certificate,
        lean_evidence=lean_evidence,
        hardened_report=hardened_report,
    )


def _finish_pilot_attempt(
    *,
    snapshot,
    run_id: str,
    attempt_index: int,
    request: PilotRequestBinding,
    stages: list[Phase7StageResult],
    artifacts: _ArtifactLedger,
    evidence_root: Path,
    proposal_validation: PilotProposalValidationEvidence | None = None,
    host_selection: PilotHostSelectionEvidence | None = None,
    phase6: Phase6PackageBuildEvidence | None = None,
    candidate_tree_hash: str | None = None,
    combined_evaluation_hash: str | None = None,
    certificate: Phase7CertificateEvidence | None = None,
    lean_evidence: LeanBridgeVerificationEvidence | None = None,
    hardened_report: Phase4HardenedReport | None = None,
) -> Phase7AttemptReport:
    while len(stages) < len(PILOT_STAGE_ORDER) - 1:
        stages.append(
            Phase7StageResult.build(
                PILOT_STAGE_ORDER[len(stages)],
                "not_evaluated",
                (),
                {},
            )
        )
    active_error: str | None = None
    try:
        active_after = load_active_phase7_store(
            snapshot.store_root,
            pytorch_pilot_phase7_policy(),
        ).pointer.pointer_hash
        active_unchanged = active_after == snapshot.pointer.pointer_hash
    except Exception as exc:
        active_error = f"{type(exc).__name__}: {exc}"
        active_after = sha256_hex(active_error.encode("utf-8"))
        active_unchanged = False
    rollback_verified = bool(
        phase6
        and phase6.report.realization
        and phase6.report.realization.rollback.verified
    )
    fallback_ok = active_unchanged and (rollback_verified or phase6 is None)
    stages.append(
        Phase7StageResult.build(
            "fallback_rollback",
            "pass" if fallback_ok else "fail",
            () if fallback_ok else (Phase7ReasonCode.ROLLBACK_FAILED,),
            {
                "active_pointer_hash_before": snapshot.pointer.pointer_hash,
                "active_pointer_hash_after": active_after,
                "active_pointer_unchanged": active_unchanged,
                "candidate_rollback_verified": rollback_verified if phase6 else True,
                "manual_repair_count": 0,
                "active_observation_error": active_error,
            },
        )
    )
    if any(stage.status == "fail" for stage in stages):
        verdict = "reject"
    elif any(stage.status == "indeterminate" for stage in stages):
        verdict = "indeterminate"
    else:
        verdict = "accept"
    reason_codes = tuple(
        dict.fromkeys(reason for stage in stages for reason in stage.reason_codes)
    )
    if verdict != "accept" and not reason_codes:
        reason_codes = (Phase7ReasonCode.INTERNAL_ERROR,)
    proposal_hash = (
        None
        if proposal_validation is None
        else proposal_validation.proposal.proposal_hash
    )
    selection_hash = (
        None if host_selection is None else host_selection.selection.selection_hash
    )
    attempt = Phase7AttemptReport(
        run_id=run_id,
        attempt_index=attempt_index,
        transition_id=request.transition_id,
        verdict=verdict,
        reason_codes=reason_codes,
        controller_units_consumed=1,
        active_pointer_hash_before=snapshot.pointer.pointer_hash,
        active_pointer_hash_after=active_after,
        generator_input_hash=request.request_hash,
        proposal_hash=proposal_hash,
        selection_hash=selection_hash,
        phase6_report_hash=None if phase6 is None else phase6.report.report_hash,
        candidate_package_tree_hash=candidate_tree_hash,
        evaluation_hash=combined_evaluation_hash,
        certificate_hash=None if certificate is None else certificate.certificate_hash,
        lean_report_hash=None if lean_evidence is None else lean_evidence.report.report_hash,
        checker_report_hash=None if hardened_report is None else hardened_report.report_hash,
        fallback_rollback_verified=fallback_ok,
        manual_repair_count=0,
        stages=tuple(stages),
        artifact_hashes=artifacts.frozen(),
    )
    _write_json_artifact(evidence_root, "attempt_report.json", attempt.to_json(), None)
    return attempt


def _run_proposal_process_ephemeral(
    request: PilotRequestBinding,
    predecessor_payload_root: Path,
    output_root: Path,
) -> PilotProcessEvidence:
    module_name = "rcp_rclm_runtime.torch_backend.process"
    package_name = "rcp_rclm_runtime.torch_backend"
    module = importlib.import_module(module_name)
    package = sys.modules.get(package_name)
    try:
        runner = getattr(module, "run_pytorch_proposal_process")
        evidence = runner(request, predecessor_payload_root, output_root)
    finally:
        sys.modules.pop(module_name, None)
        if package is not None and getattr(package, "process", None) is module:
            delattr(package, "process")
    return evidence


def _generator_evidence(
    first: PilotProcessEvidence,
    second: PilotProcessEvidence,
    process_success: bool,
    deterministic: bool,
) -> dict[str, object]:
    return {
        "first_process_report_hash": first.report.report_hash,
        "second_process_report_hash": second.report.report_hash,
        "first_source_guard_hash": first.source_guard.guard_hash,
        "second_source_guard_hash": second.source_guard.guard_hash,
        "process_success": process_success,
        "deterministic_replay": deterministic,
        "stdout_equal": first.stdout == second.stdout,
        "stderr_equal": first.stderr == second.stderr,
        "proposal_hash_equal": first.report.proposal_hash == second.report.proposal_hash,
        "output_tree_hash_equal": (
            first.report.output_tree_hash == second.report.output_tree_hash
        ),
        "write_handles_granted": [],
        "network_endpoints_granted": [],
        "checker_source_visible": False,
        "trust_anchor_visible": False,
        "promotion_ledger_visible": False,
    }


def _write_process_evidence(
    evidence_root: Path,
    prefix: str,
    evidence: PilotProcessEvidence,
    artifacts: _ArtifactLedger,
) -> None:
    _write_bytes(evidence_root, f"{prefix}_stdout.bin", evidence.stdout, artifacts)
    _write_bytes(evidence_root, f"{prefix}_stderr.bin", evidence.stderr, artifacts)
    _write_json(
        evidence_root,
        f"{prefix}_process_report.json",
        evidence.report.to_json(),
        artifacts,
    )
    _write_json(
        evidence_root,
        f"{prefix}_source_guard.json",
        evidence.source_guard.to_json(),
        artifacts,
    )


def _write_json(
    root: Path,
    name: str,
    value: object,
    artifacts: _ArtifactLedger,
) -> str:
    return _write_bytes(root, name, canonical_json_bytes(value), artifacts)


def _write_bytes(
    root: Path,
    name: str,
    content: bytes,
    artifacts: _ArtifactLedger,
) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"attempt artifact already exists: {name}")
    path.write_bytes(content)
    path.chmod(0o644)
    digest = sha256_hex(content)
    artifacts.add(f"evidence/{name}", digest)
    return digest


@dataclass(frozen=True, slots=True)
class _ArtifactAdapter:
    ledger: _ArtifactLedger

    def add_hash(self, key: str, value: str) -> None:
        self.ledger.add(key, value)


def verify_pytorch_pilot_promotion(
    evidence: PilotAdmissionEvidence,
) -> Phase7StoreSnapshot:
    policy = pytorch_pilot_phase7_policy()
    snapshot = load_active_phase7_store(evidence.store_root, policy)
    if evidence.verdict == "promoted":
        valid = (
            evidence.controller_report.promoted
            and evidence.promoted_package_root is not None
            and snapshot.package_root == evidence.promoted_package_root
            and snapshot.pointer.active_package_hash
            == evidence.controller_report.promoted_package_hash
            and evidence.attempt_report.verdict == "accept"
        )
    else:
        valid = (
            not evidence.controller_report.promoted
            and evidence.promoted_package_root is None
            and evidence.attempt_report.verdict in {"reject", "indeterminate"}
            and snapshot.pointer.active_package_hash
            == evidence.controller_report.final_pointer.active_package_hash
        )
    if not valid:
        raise ValueError("PyTorch pilot evidence does not match the verified Phase 7 store")
    return snapshot


__all__ = [
    "PilotAdmissionEvidence",
    "bootstrap_pytorch_pilot_store",
    "run_pytorch_pilot_controller",
    "verify_pytorch_pilot_promotion",
]
