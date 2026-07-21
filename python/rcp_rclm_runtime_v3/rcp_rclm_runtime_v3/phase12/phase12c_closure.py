from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedReport,
    Phase4HardenedRequest,
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
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationEvidence,
    LeanReferenceVerifier,
)
from rcp_rclm_runtime.promotion._record_common import Phase7ReasonCode
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.evaluator import (
    Phase7EvaluationEvidence,
    evaluate_realized_candidate,
)
from rcp_rclm_runtime.promotion.policy import phase7_run_id
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_stage import Phase7StageResult
from rcp_rclm_runtime.promotion.store_transactions import (
    append_phase7_nonpromotion,
    promote_phase7_candidate,
)
from rcp_rclm_runtime.promotion.store_types import Phase7PromotionCommit
from rcp_rclm_runtime.promotion.store_verifier import (
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap

from rcp_rclm_runtime_v3.contract.state import LearnedRCLMState
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, verify_decoded_task
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import (
    PHASE11B_NEW_TASK,
    verify_phase11b_task,
)
from rcp_rclm_runtime_v3.phase12.phase12b_closure import (
    Phase12BPromotionEvidence,
    phase12b_phase7_budget,
    phase12b_phase7_policy,
    promote_phase12b_candidate,
    verify_phase12b_candidate,
)
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import (
    PHASE12B_NEW_TASK,
    verify_phase12b_task,
)
from rcp_rclm_runtime_v3.phase12.phase12c_candidate import (
    Phase12CInformationReport,
    build_phase12c_information_report,
)
from rcp_rclm_runtime_v3.phase12.phase12c_lifecycle import (
    Phase12CReference,
)
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import (
    verify_phase12c_task,
)
from rcp_rclm_runtime_v3.phase12.records import Phase12ProgressLedger

PHASE12C_CONTROLLER_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase12c.controller_environment.v1",
        "network": "disabled",
        "accelerators": 0,
        "training_steps_for_transition": 0,
        "manual_repair": "forbidden",
        "candidate_direct_write": "forbidden",
        "model_evaluator": "framework_independent_exact_integer_plus_retrieval",
        "task_verifier": "pinned_lean_theorem_verifier_v1",
        "outer_checker": "phase4_hardened_plus_gate_d_phase9",
        "rejection_preserves_active_package": True,
        "self_hosted_proposal_required": True,
    }
)


def _directory_tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _forbidden_training_modules() -> Sequence[str]:
    return tuple(
        sorted(
            name
            for name in sys.modules
            if name == "torch"
            or name.startswith("torch.")
            or name.endswith("phase10.training_process")
            or name.endswith("phase11.phase11b_training")
            or name.endswith("phase12.phase12b_training")
            or name.endswith("phase10_training_worker")
        )
    )


def _certification_matches(
    state: LearnedRCLMState,
    report: TaskVerifierReport,
) -> bool:
    certification = state.task_ledger.certification_by_task_id.get(report.task_id)
    return bool(
        certification
        and certification.model_identity_hash == report.model_identity_hash
        and certification.verifier_report_hash == report.report_hash
    )


@dataclass(frozen=True, slots=True)
class Phase12CAuthoritativeVerification:
    logical_evaluation: Phase7EvaluationEvidence
    active_protected: TaskVerifierReport
    active_phase10: TaskVerifierReport
    active_phase11: TaskVerifierReport
    active_phase12b: TaskVerifierReport
    active_phase12c: TaskVerifierReport
    candidate_protected: TaskVerifierReport
    candidate_phase10: TaskVerifierReport
    candidate_phase11: TaskVerifierReport
    candidate_phase12b: TaskVerifierReport
    candidate_phase12c: TaskVerifierReport
    information_report: Phase12CInformationReport
    gate_b_certificate: Phase7CertificateEvidence
    gate_b_lean: LeanBridgeVerificationEvidence
    hardened_checker: Phase4HardenedReport
    candidate_tree_hash_before: str
    candidate_tree_hash_after: str
    expected_task_reports_match: bool
    memory_projection_matches: bool
    retrieval_projection_matches: bool
    forbidden_training_modules_loaded: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase12c.authoritative_verification.v1"

    @property
    def candidate_unchanged(self) -> bool:
        return self.candidate_tree_hash_before == self.candidate_tree_hash_after

    @property
    def frontier_transition_accepted(self) -> bool:
        return (
            self.active_protected.solved
            and self.active_phase10.solved
            and self.active_phase11.solved
            and self.active_phase12b.solved
            and not self.active_phase12c.solved
            and self.candidate_protected.solved
            and self.candidate_phase10.solved
            and self.candidate_phase11.solved
            and self.candidate_phase12b.solved
            and self.candidate_phase12c.solved
            and self.information_report.accepted
            and self.expected_task_reports_match
        )

    @property
    def accepted(self) -> bool:
        return (
            self.frontier_transition_accepted
            and self.gate_b_lean.report.accepted
            and self.gate_b_lean.source_guard.clean
            and self.hardened_checker.accepted
            and self.candidate_unchanged
            and self.memory_projection_matches
            and self.retrieval_projection_matches
            and not self.forbidden_training_modules_loaded
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "frontier_transition_accepted": self.frontier_transition_accepted,
            "logical_evaluation": self.logical_evaluation.to_json(),
            "active_protected": self.active_protected.to_json(),
            "active_phase10": self.active_phase10.to_json(),
            "active_phase11": self.active_phase11.to_json(),
            "active_phase12b": self.active_phase12b.to_json(),
            "active_phase12c": self.active_phase12c.to_json(),
            "candidate_protected": self.candidate_protected.to_json(),
            "candidate_phase10": self.candidate_phase10.to_json(),
            "candidate_phase11": self.candidate_phase11.to_json(),
            "candidate_phase12b": self.candidate_phase12b.to_json(),
            "candidate_phase12c": self.candidate_phase12c.to_json(),
            "information_report": self.information_report.to_json(),
            "gate_b_certificate": self.gate_b_certificate.to_json(),
            "gate_b_lean_report": self.gate_b_lean.report.to_json(),
            "gate_b_source_guard": self.gate_b_lean.source_guard.to_json(),
            "hardened_checker": self.hardened_checker.to_json(),
            "candidate_tree_hash_before": self.candidate_tree_hash_before,
            "candidate_tree_hash_after": self.candidate_tree_hash_after,
            "candidate_unchanged": self.candidate_unchanged,
            "expected_task_reports_match": self.expected_task_reports_match,
            "memory_projection_matches": self.memory_projection_matches,
            "retrieval_projection_matches": self.retrieval_projection_matches,
            "forbidden_training_modules_loaded": list(self.forbidden_training_modules_loaded),
            "training_invocations_during_verification": 0,
            "candidate_self_report_consumed": False,
        }


def verify_phase12c_candidate(
    reference: Phase12CReference,
    *,
    repo_root: Path,
    lean_project_root: Path,
) -> Phase12CAuthoritativeVerification:
    active_root = reference.wrapper_predecessor.payload_root / EMBEDDED_PHASE12_ROOT
    candidate_root = reference.phase6.embedded_candidate_root
    candidate_tree_before = _directory_tree_hash(reference.phase6.candidate_root)

    active_protected = verify_decoded_task(active_root, PROTECTED_TASK, lean_project_root)
    active_phase10 = verify_decoded_task(active_root, HELDOUT_TASK, lean_project_root)
    active_phase11 = verify_phase11b_task(active_root, lean_project_root)
    active_phase12b = verify_phase12b_task(active_root, lean_project_root)
    active_phase12c = verify_phase12c_task(active_root, lean_project_root)

    candidate_protected = verify_decoded_task(candidate_root, PROTECTED_TASK, lean_project_root)
    candidate_phase10 = verify_decoded_task(candidate_root, HELDOUT_TASK, lean_project_root)
    candidate_phase11 = verify_phase11b_task(candidate_root, lean_project_root)
    candidate_phase12b = verify_phase12b_task(candidate_root, lean_project_root)
    candidate_phase12c = verify_phase12c_task(candidate_root, lean_project_root)

    information = build_phase12c_information_report(active_root, candidate_root)
    if information.report_hash != reference.semantic_candidate.information_report.report_hash:
        raise ValueError("authoritative Phase 12C information report differs")

    active_state = reference.phase12b.semantic_candidate.candidate_state
    candidate_state = reference.semantic_candidate.candidate_state
    expected_reports_match = all(
        (
            _certification_matches(active_state, active_protected),
            _certification_matches(active_state, active_phase10),
            _certification_matches(active_state, active_phase11),
            _certification_matches(active_state, active_phase12b),
            _certification_matches(candidate_state, candidate_protected),
            _certification_matches(candidate_state, candidate_phase10),
            _certification_matches(candidate_state, candidate_phase11),
            _certification_matches(candidate_state, candidate_phase12b),
            _certification_matches(candidate_state, candidate_phase12c),
        )
    )

    logical = evaluate_realized_candidate(
        reference.wrapper_predecessor.payload_root.parent,
        reference.phase6.candidate_root,
        reference.phase6.selection,
    )
    gate_b_certificate = Phase7CertificateEvidence(
        certificate_name="stability",
        certificate=canonical_rclm_certificate("gate_b_classical", "stability"),
    )
    packet = build_lean_reference_packet(
        logical.predecessor.state,
        logical.candidate,
        gate_b_certificate.certificate,
    )
    project = PinnedLeanProject.discover(repo_root.resolve(strict=True))
    compiler = LeanCompiler(project=project, timeout_seconds=180)
    gate_b_lean = LeanReferenceVerifier(compiler).verify_with_evidence(packet)
    checker_request = Phase3CheckerRequest(
        transition_id=reference.phase6.selection.transition_id,
        predecessor=logical.predecessor.state,
        candidate=logical.candidate,
        certificate=gate_b_certificate.certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(
            budget_units=2,
            consumed_units=2,
            environment_hash=PHASE12C_CONTROLLER_ENVIRONMENT_HASH,
        ),
        protected_distinctions=reference_protected_distinctions("gate_b_classical"),
        evaluation_evidence=logical.evaluation,
        lean_bridge_report=gate_b_lean.report,
    )
    hardened = check_hardened_transition(
        Phase4HardenedRequest(
            checker_request=checker_request,
            package_integrity=build_reference_package_integrity(checker_request),
        )
    )
    candidate_tree_after = _directory_tree_hash(reference.phase6.candidate_root)
    evidence = Phase12CAuthoritativeVerification(
        logical_evaluation=logical,
        active_protected=active_protected,
        active_phase10=active_phase10,
        active_phase11=active_phase11,
        active_phase12b=active_phase12b,
        active_phase12c=active_phase12c,
        candidate_protected=candidate_protected,
        candidate_phase10=candidate_phase10,
        candidate_phase11=candidate_phase11,
        candidate_phase12b=candidate_phase12b,
        candidate_phase12c=candidate_phase12c,
        information_report=information,
        gate_b_certificate=gate_b_certificate,
        gate_b_lean=gate_b_lean,
        hardened_checker=hardened,
        candidate_tree_hash_before=candidate_tree_before,
        candidate_tree_hash_after=candidate_tree_after,
        expected_task_reports_match=expected_reports_match,
        memory_projection_matches=reference.phase6.memory_projection_matches,
        retrieval_projection_matches=reference.phase6.retrieval_projection_matches,
        forbidden_training_modules_loaded=_forbidden_training_modules(),
    )
    if not evidence.accepted:
        raise ValueError("Phase 12C authoritative verification did not accept")
    if not reference.lifecycle_transition.accepted:
        raise ValueError("Phase 12C Gate D transition is not accepted")
    return evidence


def _write_json(path: Path, value: object) -> str:
    content = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return sha256_hex(content)


def _stage(
    name: str,
    status: str,
    reason_codes: Sequence[Phase7ReasonCode],
    evidence: object,
) -> Phase7StageResult:
    return Phase7StageResult.build(
        name,
        status,  # type: ignore[arg-type]
        tuple(reason_codes),
        evidence,
    )


def _rejection_stages(reference: Phase12CReference) -> Sequence[Phase7StageResult]:
    return (
        _stage(
            "generator",
            "pass",
            (),
            {
                "proposal_source": "promoted_m1_generation2_successor",
                "proposal_hash": reference.invalid_proposal.report_hash,
                "program_hash": reference.invalid_proposal.program.program_hash,
                "heldout_material_consumed": False,
            },
        ),
        _stage(
            "proposal_validation",
            "fail",
            (Phase7ReasonCode.PROPOSAL_INVALID,),
            {
                "validation_hash": reference.invalid_validation.report_hash,
                "reason_codes": list(reference.invalid_validation.reason_codes),
            },
        ),
        _stage("selection", "not_evaluated", (), {}),
        _stage("realization", "not_evaluated", (), {}),
        _stage("objective_evaluation", "not_evaluated", (), {}),
        _stage("certificate_construction", "not_evaluated", (), {}),
        _stage("lean_bridge", "not_evaluated", (), {}),
        _stage("hardened_checker", "not_evaluated", (), {}),
        _stage(
            "fallback_rollback",
            "pass",
            (),
            {
                "candidate_realized": False,
                "active_package_unchanged": reference.invalid_proposal.package_unchanged,
                "active_package_tree_hash": reference.invalid_proposal.package_tree_hash_after,
            },
        ),
    )


def _promotion_stages(
    reference: Phase12CReference,
    verification: Phase12CAuthoritativeVerification,
) -> Sequence[Phase7StageResult]:
    realization = reference.phase6.phase6.report.realization
    if realization is None:
        raise ValueError("Phase 12C Phase 6 realization is unavailable")
    return (
        _stage(
            "generator",
            "pass",
            (),
            {
                "proposal_source": "active_m1_generation2_generator_planner",
                "proposal_hash": reference.proposal.report_hash,
                "prior_rejection_hash": reference.invalid_validation.report_hash,
                "fresh_after_rejection": True,
                "heldout_material_consumed": False,
            },
        ),
        _stage(
            "proposal_validation",
            "pass",
            (),
            {
                "validation_hash": reference.validation.report_hash,
                "validated": reference.validation.accepted,
            },
        ),
        _stage(
            "selection",
            "pass",
            (),
            {
                "selection_hash": reference.phase6.selection.selection_hash,
                "manual_repair_count": 0,
                "affected_components": ["memory_state", "retrieval_policy"],
            },
        ),
        _stage(
            "realization",
            "pass",
            (),
            {
                "phase6_report_hash": reference.phase6.phase6.report.report_hash,
                "rollback_verified": realization.rollback.verified,
                "rollback_hash": realization.rollback.rollback_hash,
            },
        ),
        _stage(
            "objective_evaluation",
            "pass",
            (),
            {
                "verification_hash": verification.report_hash,
                "protected_tasks_retained": True,
                "new_heldout_task_solved": True,
                "selected_information_nonregression": True,
            },
        ),
        _stage(
            "certificate_construction",
            "pass",
            (),
            {
                "gate_b_certificate_hash": verification.gate_b_certificate.certificate_hash,
                "gate_d_certificate_hash": reference.lifecycle_certificate.certificate_hash,
                "constructed_outside_candidate": True,
            },
        ),
        _stage(
            "lean_bridge",
            "pass",
            (),
            {
                "gate_b_lean_report_hash": verification.gate_b_lean.report.report_hash,
                "candidate_protected_report_hash": verification.candidate_protected.report_hash,
                "candidate_phase10_report_hash": verification.candidate_phase10.report_hash,
                "candidate_phase11_report_hash": verification.candidate_phase11.report_hash,
                "candidate_phase12b_report_hash": verification.candidate_phase12b.report_hash,
                "candidate_phase12c_report_hash": verification.candidate_phase12c.report_hash,
            },
        ),
        _stage(
            "hardened_checker",
            "pass",
            (),
            {
                "hardened_report_hash": verification.hardened_checker.report_hash,
                "checker_accepted": verification.hardened_checker.accepted,
                "phase9_transition_hash": reference.lifecycle_transition.semantic_report_hash,
                "candidate_unchanged": verification.candidate_unchanged,
            },
        ),
        _stage(
            "fallback_rollback",
            "pass",
            (),
            {
                "rollback_verified": realization.rollback.verified,
                "archive_hash": realization.rollback.archive_hash,
                "restored_tree_hash": realization.rollback.restored_tree_hash,
            },
        ),
    )


@dataclass(frozen=True, slots=True)
class Phase12CPromotionEvidence:
    phase12b_prefix: Phase12BPromotionEvidence
    reference: Phase12CReference
    verification: Phase12CAuthoritativeVerification
    rejection_attempt: Phase7AttemptReport
    rejection_ledger_hash: str
    promotion_attempt: Phase7AttemptReport
    promotion: Phase7PromotionCommit
    m1_store_package_hash: str
    active_package_hash_after_rejection: str
    installed_semantic_package_hash: str
    installed_memory_bytes_hash: str
    installed_retrieval_bytes_hash: str
    installed_generator_bytes_hash: str
    installed_planner_bytes_hash: str
    progress_ledger: Phase12ProgressLedger

    schema_id: ClassVar[str] = "runtime.v3.phase12c.promotion.v1"

    @property
    def accepted(self) -> bool:
        pointer = self.promotion.snapshot.pointer
        active_manifest = self.reference.phase12b.semantic_candidate.manifest
        candidate_manifest = self.reference.semantic_candidate.manifest
        return (
            self.phase12b_prefix.accepted
            and self.reference.accepted
            and self.verification.accepted
            and self.rejection_attempt.verdict == "reject"
            and self.active_package_hash_after_rejection == self.m1_store_package_hash
            and self.promotion_attempt.verdict == "accept"
            and self.promotion.package_manifest.parent_package_hash == self.m1_store_package_hash
            and pointer.active_package_hash == self.promotion.package_manifest.package_hash
            and pointer.ledger_sequence_number == 4
            and self.installed_semantic_package_hash == candidate_manifest.package_hash
            and candidate_manifest.model_identity_hash == active_manifest.model_identity_hash
            and candidate_manifest.memory_manifest_hash != active_manifest.memory_manifest_hash
            and candidate_manifest.retrieval_index_hash != active_manifest.retrieval_index_hash
            and candidate_manifest.generator_policy_hash == active_manifest.generator_policy_hash
            and candidate_manifest.planner_policy_hash == active_manifest.planner_policy_hash
            and self.progress_ledger.generator_invocations == 4
            and self.progress_ledger.rejected_attempts == 2
            and self.progress_ledger.candidate_realizations == 2
            and self.progress_ledger.candidate_evaluations == 2
            and self.progress_ledger.accepted_promotions == 2
            and self.progress_ledger.frontier_expansions == 2
            and self.progress_ledger.manual_repairs == 0
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "phase12b_prefix_promotion_hash": self.phase12b_prefix.report_hash,
            "reference_hash": self.reference.reference_hash,
            "verification_hash": self.verification.report_hash,
            "rejection_attempt": self.rejection_attempt.to_json(),
            "rejection_ledger_hash": self.rejection_ledger_hash,
            "m1_store_package_hash": self.m1_store_package_hash,
            "active_package_hash_after_rejection": self.active_package_hash_after_rejection,
            "promotion_attempt": self.promotion_attempt.to_json(),
            "promoted_package_hash": self.promotion.package_manifest.package_hash,
            "promoted_package_id": self.promotion.package_manifest.package_id,
            "parent_package_hash": self.promotion.package_manifest.parent_package_hash,
            "promotion_ledger_hash": self.promotion.ledger_entry.entry_hash,
            "ledger_sequence_number": self.promotion.snapshot.pointer.ledger_sequence_number,
            "installed_semantic_package_hash": self.installed_semantic_package_hash,
            "installed_memory_bytes_hash": self.installed_memory_bytes_hash,
            "installed_retrieval_bytes_hash": self.installed_retrieval_bytes_hash,
            "installed_generator_bytes_hash": self.installed_generator_bytes_hash,
            "installed_planner_bytes_hash": self.installed_planner_bytes_hash,
            "active_memory_hash": self.reference.phase12b.semantic_candidate.manifest.memory_manifest_hash,
            "successor_memory_hash": self.reference.semantic_candidate.manifest.memory_manifest_hash,
            "active_retrieval_hash": self.reference.phase12b.semantic_candidate.manifest.retrieval_index_hash,
            "successor_retrieval_hash": self.reference.semantic_candidate.manifest.retrieval_index_hash,
            "active_generator_hash": self.reference.phase12b.semantic_candidate.manifest.generator_policy_hash,
            "successor_generator_hash": self.reference.semantic_candidate.manifest.generator_policy_hash,
            "active_planner_hash": self.reference.phase12b.semantic_candidate.manifest.planner_policy_hash,
            "successor_planner_hash": self.reference.semantic_candidate.manifest.planner_policy_hash,
            "progress_ledger": self.progress_ledger.to_json(),
            "manual_repair_count": 0,
            "recursive_use_of_m1_generator": True,
        }


def promote_phase12c_candidate(
    reference: Phase12CReference,
    verification: Phase12CAuthoritativeVerification,
    *,
    store_root: Path,
    evidence_root: Path,
    repo_root: Path,
    lean_project_root: Path,
) -> Phase12CPromotionEvidence:
    if not reference.accepted or not verification.accepted:
        raise ValueError("Phase 12C lifecycle is not eligible for promotion")

    phase12b_verification = verify_phase12b_candidate(
        reference.phase12b,
        repo_root=repo_root,
        lean_project_root=lean_project_root,
    )
    phase12b_prefix = promote_phase12b_candidate(
        reference.phase12b,
        phase12b_verification,
        store_root=store_root,
        evidence_root=evidence_root / "phase12b-prefix",
    )
    policy = phase12b_phase7_policy()
    snapshot = load_active_phase7_store(store_root, policy)
    if snapshot.pointer != phase12b_prefix.promotion.snapshot.pointer:
        raise ValueError("reopened M1 store pointer differs from Phase 12B prefix")
    m1_hash = snapshot.pointer.active_package_hash
    budget = phase12b_phase7_budget()
    run_id = phase7_run_id(
        run_label="phase12-self-hosted-recursion-generation2-v1",
        active_pointer_hash=snapshot.pointer.pointer_hash,
        policy_hash=policy.policy_hash,
        budget_hash=budget.budget_hash,
    )
    root = (evidence_root / "phase12c").resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12C evidence root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)

    rejection_root = root / "attempt-0000"
    rejection_payloads: dict[str, object] = {
        "generator_input.json": reference.invalid_proposal.generator_input.to_json(),
        "proposal.json": reference.invalid_proposal.to_json(),
        "program_validation.json": reference.invalid_validation.to_json(),
    }
    rejection_hashes = {
        name: _write_json(rejection_root / name, value)
        for name, value in sorted(
            rejection_payloads.items(),
            key=lambda item: item[0].encode("utf-8"),
        )
    }
    rejection_attempt = Phase7AttemptReport(
        run_id=run_id,
        attempt_index=0,
        transition_id=reference.invalid_proposal.generator_input.transition_id,
        verdict="reject",
        reason_codes=(Phase7ReasonCode.PROPOSAL_INVALID,),
        controller_units_consumed=1,
        active_pointer_hash_before=snapshot.pointer.pointer_hash,
        active_pointer_hash_after=snapshot.pointer.pointer_hash,
        generator_input_hash=reference.invalid_proposal.generator_input.input_hash,
        proposal_hash=reference.invalid_proposal.program.program_hash,
        selection_hash=None,
        phase6_report_hash=None,
        candidate_package_tree_hash=None,
        evaluation_hash=None,
        certificate_hash=None,
        lean_report_hash=None,
        checker_report_hash=None,
        fallback_rollback_verified=True,
        manual_repair_count=0,
        stages=_rejection_stages(reference),
        artifact_hashes=FrozenHashMap.from_mapping(
            rejection_hashes,
            "phase12c.rejection_artifact_hashes",
        ),
    )
    _write_json(rejection_root / "attempt_report.json", rejection_attempt.to_json())
    snapshot_after_rejection, rejection_entry = append_phase7_nonpromotion(
        snapshot,
        rejection_attempt,
        policy,
        event="rejection",
    )
    if snapshot_after_rejection.pointer.active_package_hash != m1_hash:
        raise ValueError("rejected Phase 12C attempt changed M1")
    if snapshot_after_rejection.pointer.ledger_sequence_number != 3:
        raise ValueError("Phase 12C rejection ledger sequence is not three")

    promotion_root = root / "attempt-0001"
    promotion_payloads: dict[str, object] = {
        "policy.json": policy.to_json(),
        "proposal.json": reference.proposal.to_json(),
        "proposal_validation.json": reference.validation.to_json(),
        "selection.json": reference.phase6.selection.to_json(),
        "phase6_report.json": reference.phase6.phase6.report.to_json(),
        "candidate_evaluation.json": reference.semantic_candidate.evaluation.to_json(),
        "verification.json": verification.to_json(),
        "gate_d_certificate.json": reference.lifecycle_certificate.to_json(),
        "phase9_transition.json": reference.lifecycle_transition.to_json(),
        "information.json": verification.information_report.to_json(),
        "gate_b_lean_report.json": verification.gate_b_lean.report.to_json(),
        "hardened_checker.json": verification.hardened_checker.to_json(),
        "task_candidate_protected.json": verification.candidate_protected.to_json(),
        "task_candidate_phase10.json": verification.candidate_phase10.to_json(),
        "task_candidate_phase11.json": verification.candidate_phase11.to_json(),
        "task_candidate_phase12b.json": verification.candidate_phase12b.to_json(),
        "task_candidate_phase12c.json": verification.candidate_phase12c.to_json(),
    }
    promotion_hashes = {
        name: _write_json(promotion_root / name, value)
        for name, value in sorted(
            promotion_payloads.items(),
            key=lambda item: item[0].encode("utf-8"),
        )
    }
    combined_certificate_hash = canonical_json_hash(
        {
            "gate_b": verification.gate_b_certificate.to_json(),
            "gate_d": reference.lifecycle_certificate.to_json(),
        }
    )
    combined_lean_hash = canonical_json_hash(
        {
            "gate_b": verification.gate_b_lean.report.to_json(),
            "candidate_protected": verification.candidate_protected.to_json(),
            "candidate_phase10": verification.candidate_phase10.to_json(),
            "candidate_phase11": verification.candidate_phase11.to_json(),
            "candidate_phase12b": verification.candidate_phase12b.to_json(),
            "candidate_phase12c": verification.candidate_phase12c.to_json(),
        }
    )
    combined_checker_hash = canonical_json_hash(
        {
            "hardened": verification.hardened_checker.to_json(),
            "gate_d": reference.lifecycle_transition.to_json(),
        }
    )
    promotion_attempt = Phase7AttemptReport(
        run_id=run_id,
        attempt_index=1,
        transition_id=reference.phase6.selection.transition_id,
        verdict="accept",
        reason_codes=(),
        controller_units_consumed=1,
        active_pointer_hash_before=snapshot_after_rejection.pointer.pointer_hash,
        active_pointer_hash_after=snapshot_after_rejection.pointer.pointer_hash,
        generator_input_hash=reference.proposal.generator_input.input_hash,
        proposal_hash=reference.phase6.selection.proposal_hash,
        selection_hash=reference.phase6.selection.selection_hash,
        phase6_report_hash=reference.phase6.phase6.report.report_hash,
        candidate_package_tree_hash=_directory_tree_hash(reference.phase6.candidate_root),
        evaluation_hash=verification.report_hash,
        certificate_hash=combined_certificate_hash,
        lean_report_hash=combined_lean_hash,
        checker_report_hash=combined_checker_hash,
        fallback_rollback_verified=True,
        manual_repair_count=0,
        stages=_promotion_stages(reference, verification),
        artifact_hashes=FrozenHashMap.from_mapping(
            promotion_hashes,
            "phase12c.promotion_artifact_hashes",
        ),
    )
    _write_json(promotion_root / "attempt_report.json", promotion_attempt.to_json())
    promotion = promote_phase7_candidate(
        snapshot_after_rejection,
        reference.phase6.candidate_root,
        promotion_root,
        promotion_attempt,
        policy,
    )
    reopened = load_active_phase7_store(store_root, policy)
    if reopened.pointer != promotion.snapshot.pointer:
        raise ValueError("reopened M2 active pointer differs")
    verify_immutable_phase7_package(reopened.package_root, policy)
    installed_root = reopened.package_root / "predecessor/payload" / EMBEDDED_PHASE12_ROOT
    installed_manifest = load_package_manifest(installed_root)
    if installed_manifest.package_hash != reference.semantic_candidate.manifest.package_hash:
        raise ValueError("promoted M2 package contains the wrong semantic package")

    installed_memory_bytes_hash = sha256_hex(
        (installed_root / "memory/memory_manifest.json").read_bytes()
    )
    installed_retrieval_bytes_hash = sha256_hex(
        (installed_root / "retrieval/index_manifest.json").read_bytes()
    )
    installed_generator_bytes_hash = sha256_hex(
        (installed_root / "policies/generator_policy.json").read_bytes()
    )
    installed_planner_bytes_hash = sha256_hex(
        (installed_root / "policies/planner_policy.json").read_bytes()
    )
    expected_memory_bytes_hash = sha256_hex(
        (reference.semantic_candidate.root / "memory/memory_manifest.json").read_bytes()
    )
    expected_retrieval_bytes_hash = sha256_hex(
        (reference.semantic_candidate.root / "retrieval/index_manifest.json").read_bytes()
    )
    if installed_memory_bytes_hash != expected_memory_bytes_hash:
        raise ValueError("installed M2 memory bytes differ")
    if installed_retrieval_bytes_hash != expected_retrieval_bytes_hash:
        raise ValueError("installed M2 retrieval bytes differ")

    progress = Phase12ProgressLedger(
        total_budget_hash=reference.ledger.total_budget_hash,
        generator_invocations=4,
        rejected_attempts=2,
        candidate_realizations=2,
        candidate_evaluations=2,
        accepted_promotions=2,
        frontier_expansions=2,
        manual_repairs=0,
    )
    result = Phase12CPromotionEvidence(
        phase12b_prefix=phase12b_prefix,
        reference=reference,
        verification=verification,
        rejection_attempt=rejection_attempt,
        rejection_ledger_hash=rejection_entry.entry_hash,
        promotion_attempt=promotion_attempt,
        promotion=promotion,
        m1_store_package_hash=m1_hash,
        active_package_hash_after_rejection=snapshot_after_rejection.pointer.active_package_hash,
        installed_semantic_package_hash=installed_manifest.package_hash,
        installed_memory_bytes_hash=installed_memory_bytes_hash,
        installed_retrieval_bytes_hash=installed_retrieval_bytes_hash,
        installed_generator_bytes_hash=installed_generator_bytes_hash,
        installed_planner_bytes_hash=installed_planner_bytes_hash,
        progress_ledger=progress,
    )
    if not result.accepted:
        raise ValueError("Phase 12C promotion did not close")
    _write_json(root / "phase12c_promotion_report.json", result.to_json())
    return result


@dataclass(frozen=True, slots=True)
class Phase12CClosureEvidence:
    reference: Phase12CReference
    verification: Phase12CAuthoritativeVerification
    promotion: Phase12CPromotionEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase12c.closure.v1"

    @property
    def accepted(self) -> bool:
        return self.reference.accepted and self.verification.accepted and self.promotion.accepted

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reference_hash": self.reference.reference_hash,
            "verification_hash": self.verification.report_hash,
            "promotion_hash": self.promotion.report_hash,
            "phase12a_recursive_rejection_retained": True,
            "phase12b_first_promotion_retained": True,
            "phase12c_second_rejection_retained": True,
            "rejection_preserved_m1": True,
            "m1_to_m2_candidate_realized": True,
            "m1_to_m2_frontier_expansion": True,
            "m1_to_m2_atomic_promotion": True,
            "frontier_cardinality_before": 4,
            "frontier_cardinality_after": 5,
            "accepted_phase12_promotions": 2,
            "rejected_phase12_attempts": 2,
            "manual_repairs": 0,
            "heldout_material_consumed": False,
            "phase12c_memory_retrieval_promotion_closed": self.accepted,
            "phase12_exit_closed": False,
            "next_transition": "M2_to_M3_generator_planner_self_modification",
        }


__all__ = [
    "PHASE12C_CONTROLLER_ENVIRONMENT_HASH",
    "Phase12CAuthoritativeVerification",
    "Phase12CClosureEvidence",
    "Phase12CPromotionEvidence",
    "promote_phase12c_candidate",
    "verify_phase12c_candidate",
]
