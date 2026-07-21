from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
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
from rcp_rclm_runtime.promotion.record_policy import (
    Phase7ControllerBudgetRecord,
    Phase7ControllerPolicyRecord,
)
from rcp_rclm_runtime.promotion.record_stage import Phase7StageResult
from rcp_rclm_runtime.promotion.store_transactions import (
    append_phase7_nonpromotion,
    promote_phase7_candidate,
)
from rcp_rclm_runtime.promotion.store_types import Phase7PromotionCommit
from rcp_rclm_runtime.promotion.store_verifier import (
    bootstrap_phase7_store,
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap

from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.policy import phase10_phase7_policy
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, verify_decoded_task
from rcp_rclm_runtime_v3.phase11.phase11b_candidate import Phase11BInformationReport
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import (
    EMBEDDED_PHASE11_ROOT,
    Phase11BReference,
    phase11b_phase6_budget,
)
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import (
    PHASE11B_NEW_TASK,
    verify_phase11b_task,
)

PHASE11B_CONTROLLER_POLICY_ID: Final[str] = (
    "rcp-rclm-v3-phase11-model-generated-controller-v1"
)
PHASE11B_CONTROLLER_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase11b.controller_environment.v1",
        "policy_id": PHASE11B_CONTROLLER_POLICY_ID,
        "network": "disabled",
        "accelerators": 0,
        "manual_repair": "forbidden",
        "candidate_direct_write": "forbidden",
        "model_evaluator": "framework_independent_exact_integer",
        "task_verifier": "pinned_lean_theorem_verifier_v1",
        "outer_checker": "phase4_hardened_plus_gate_d_phase9",
        "rejection_preserves_active_package": True,
    }
)


def phase11b_phase7_policy() -> Phase7ControllerPolicyRecord:
    base = phase10_phase7_policy()
    return Phase7ControllerPolicyRecord(
        policy_id=PHASE11B_CONTROLLER_POLICY_ID,
        scope=base.scope,
        generator_backend=base.generator_backend,
        selector_backend=base.selector_backend,
        realizer_backend=base.realizer_backend,
        evaluator_backend=base.evaluator_backend,
        checker_backend=base.checker_backend,
        require_two_run_generator_replay=base.require_two_run_generator_replay,
        require_public_package_verification=base.require_public_package_verification,
        require_lean_acceptance=base.require_lean_acceptance,
        require_checker_acceptance=base.require_checker_acceptance,
        allow_manual_repair=False,
        allow_candidate_mutation=False,
    )


def phase11b_phase7_budget() -> Phase7ControllerBudgetRecord:
    return Phase7ControllerBudgetRecord(
        max_attempts=2,
        max_attempt_units=2,
        attempt_unit_cost=1,
        max_promotions=1,
        phase6_budget=phase11b_phase6_budget(),
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
            or name.endswith("phase10_training_worker")
        )
    )


def _certification_matches(
    reference: Phase11BReference,
    report: TaskVerifierReport,
) -> bool:
    state = reference.beta_candidate.candidate_state
    if state is None:
        return False
    certification = state.task_ledger.certification_by_task_id.get(report.task_id)
    return bool(certification and certification.verifier_report_hash == report.report_hash)


@dataclass(frozen=True, slots=True)
class Phase11BAuthoritativeVerification:
    logical_evaluation: Phase7EvaluationEvidence
    active_protected: TaskVerifierReport
    active_phase10_heldout: TaskVerifierReport
    active_phase11_heldout: TaskVerifierReport
    alpha_protected: TaskVerifierReport
    alpha_phase10_heldout: TaskVerifierReport
    alpha_phase11_heldout: TaskVerifierReport
    beta_protected: TaskVerifierReport
    beta_phase10_heldout: TaskVerifierReport
    beta_phase11_heldout: TaskVerifierReport
    information_report: Phase11BInformationReport
    gate_b_certificate: Phase7CertificateEvidence
    gate_b_lean: LeanBridgeVerificationEvidence
    hardened_checker: Phase4HardenedReport
    alpha_tree_hash_before: str
    alpha_tree_hash_after: str
    beta_tree_hash_before: str
    beta_tree_hash_after: str
    expected_task_reports_match: bool
    forbidden_training_modules_loaded: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase11b.authoritative_verification.v1"

    @property
    def alpha_unchanged(self) -> bool:
        return self.alpha_tree_hash_before == self.alpha_tree_hash_after

    @property
    def beta_unchanged(self) -> bool:
        return self.beta_tree_hash_before == self.beta_tree_hash_after

    @property
    def alpha_rejected(self) -> bool:
        return (
            not self.alpha_protected.solved
            and self.alpha_phase10_heldout.solved
            and self.alpha_phase11_heldout.solved
        )

    @property
    def beta_accepted(self) -> bool:
        return (
            self.active_protected.solved
            and self.active_phase10_heldout.solved
            and not self.active_phase11_heldout.solved
            and self.beta_protected.solved
            and self.beta_phase10_heldout.solved
            and self.beta_phase11_heldout.solved
            and self.information_report.accepted
            and self.expected_task_reports_match
            and self.gate_b_lean.report.accepted
            and self.gate_b_lean.source_guard.clean
            and self.hardened_checker.accepted
            and self.beta_unchanged
            and not self.forbidden_training_modules_loaded
        )

    @property
    def accepted(self) -> bool:
        return self.alpha_rejected and self.alpha_unchanged and self.beta_accepted

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "alpha_rejected": self.alpha_rejected,
            "beta_accepted": self.beta_accepted,
            "logical_evaluation": self.logical_evaluation.to_json(),
            "active_protected": self.active_protected.to_json(),
            "active_phase10_heldout": self.active_phase10_heldout.to_json(),
            "active_phase11_heldout": self.active_phase11_heldout.to_json(),
            "alpha_protected": self.alpha_protected.to_json(),
            "alpha_phase10_heldout": self.alpha_phase10_heldout.to_json(),
            "alpha_phase11_heldout": self.alpha_phase11_heldout.to_json(),
            "beta_protected": self.beta_protected.to_json(),
            "beta_phase10_heldout": self.beta_phase10_heldout.to_json(),
            "beta_phase11_heldout": self.beta_phase11_heldout.to_json(),
            "information_report": self.information_report.to_json(),
            "gate_b_certificate": self.gate_b_certificate.to_json(),
            "gate_b_lean_report": self.gate_b_lean.report.to_json(),
            "gate_b_source_guard": self.gate_b_lean.source_guard.to_json(),
            "hardened_checker": self.hardened_checker.to_json(),
            "alpha_tree_hash_before": self.alpha_tree_hash_before,
            "alpha_tree_hash_after": self.alpha_tree_hash_after,
            "alpha_unchanged": self.alpha_unchanged,
            "beta_tree_hash_before": self.beta_tree_hash_before,
            "beta_tree_hash_after": self.beta_tree_hash_after,
            "beta_unchanged": self.beta_unchanged,
            "expected_task_reports_match": self.expected_task_reports_match,
            "forbidden_training_modules_loaded": list(
                self.forbidden_training_modules_loaded
            ),
            "training_invocations_during_verification": 0,
            "candidate_self_report_consumed": False,
        }


def verify_phase11b_candidates(
    reference: Phase11BReference,
    *,
    repo_root: Path,
    lean_project_root: Path,
) -> Phase11BAuthoritativeVerification:
    active_root = reference.wrapper_predecessor.payload_root / EMBEDDED_PHASE11_ROOT
    alpha_root = reference.alpha_phase6.embedded_candidate_root
    beta_root = reference.beta_phase6.embedded_candidate_root
    alpha_tree_before = _directory_tree_hash(reference.alpha_phase6.candidate_root)
    beta_tree_before = _directory_tree_hash(reference.beta_phase6.candidate_root)
    active_protected = verify_decoded_task(active_root, PROTECTED_TASK, lean_project_root)
    active_phase10_heldout = verify_decoded_task(
        active_root,
        HELDOUT_TASK,
        lean_project_root,
    )
    active_phase11_heldout = verify_phase11b_task(active_root, lean_project_root)

    alpha_protected = verify_decoded_task(alpha_root, PROTECTED_TASK, lean_project_root)
    alpha_phase10_heldout = verify_decoded_task(
        alpha_root,
        HELDOUT_TASK,
        lean_project_root,
    )
    alpha_phase11_heldout = verify_phase11b_task(alpha_root, lean_project_root)

    beta_protected = verify_decoded_task(beta_root, PROTECTED_TASK, lean_project_root)
    beta_phase10_heldout = verify_decoded_task(
        beta_root,
        HELDOUT_TASK,
        lean_project_root,
    )
    beta_phase11_heldout = verify_phase11b_task(beta_root, lean_project_root)

    information = reference.beta_candidate.information_report
    if information is None:
        raise ValueError("Phase 11B information reference is unavailable")
    from rcp_rclm_runtime_v3.phase11.phase11b_candidate import (
        build_phase11b_information_report,
    )

    recomputed_information = build_phase11b_information_report(active_root, beta_root)
    if recomputed_information.report_hash != information.report_hash:
        raise ValueError("authoritative Phase 11B information report differs")

    expected_reports_match = all(
        (
            active_protected.to_json() == reference.active.protected_report.to_json(),
            active_phase10_heldout.to_json()
            == reference.active.phase10_heldout_report.to_json(),
            _certification_matches(reference, beta_protected),
            _certification_matches(reference, beta_phase10_heldout),
            _certification_matches(reference, beta_phase11_heldout),
        )
    )

    logical = evaluate_realized_candidate(
        reference.wrapper_predecessor.payload_root.parent,
        reference.beta_phase6.candidate_root,
        reference.beta_phase6.selection,
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
        transition_id=reference.beta_phase6.selection.transition_id,
        predecessor=logical.predecessor.state,
        candidate=logical.candidate,
        certificate=gate_b_certificate.certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(
            budget_units=2,
            consumed_units=2,
            environment_hash=PHASE11B_CONTROLLER_ENVIRONMENT_HASH,
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
    alpha_tree_after = _directory_tree_hash(reference.alpha_phase6.candidate_root)
    beta_tree_after = _directory_tree_hash(reference.beta_phase6.candidate_root)
    evidence = Phase11BAuthoritativeVerification(
        logical_evaluation=logical,
        active_protected=active_protected,
        active_phase10_heldout=active_phase10_heldout,
        active_phase11_heldout=active_phase11_heldout,
        alpha_protected=alpha_protected,
        alpha_phase10_heldout=alpha_phase10_heldout,
        alpha_phase11_heldout=alpha_phase11_heldout,
        beta_protected=beta_protected,
        beta_phase10_heldout=beta_phase10_heldout,
        beta_phase11_heldout=beta_phase11_heldout,
        information_report=recomputed_information,
        gate_b_certificate=gate_b_certificate,
        gate_b_lean=gate_b_lean,
        hardened_checker=hardened,
        alpha_tree_hash_before=alpha_tree_before,
        alpha_tree_hash_after=alpha_tree_after,
        beta_tree_hash_before=beta_tree_before,
        beta_tree_hash_after=beta_tree_after,
        expected_task_reports_match=expected_reports_match,
        forbidden_training_modules_loaded=_forbidden_training_modules(),
    )
    if not evidence.accepted:
        raise ValueError("Phase 11B authoritative verification did not accept")
    if not reference.lifecycle_transition.accepted:
        raise ValueError("Phase 11B Gate D transition is not accepted")
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


def _alpha_stages(
    reference: Phase11BReference,
    verification: Phase11BAuthoritativeVerification,
) -> Sequence[Phase7StageResult]:
    realization = reference.alpha_phase6.phase6.report.realization
    if realization is None:
        raise ValueError("alpha Phase 6 realization is unavailable")
    return (
        _stage(
            "generator",
            "pass",
            (),
            {
                "proposal_source": "active_predecessor_model",
                "invocation_hash": reference.alpha_invocation.report_hash,
                "program_hash": reference.alpha_invocation.program.program_hash,
                "heldout_material_consumed": False,
            },
        ),
        _stage(
            "proposal_validation",
            "pass",
            (),
            {
                "validation_hash": reference.alpha_validation.report_hash,
                "validated": reference.alpha_validation.accepted,
            },
        ),
        _stage(
            "selection",
            "pass",
            (),
            {
                "selection_hash": reference.alpha_phase6.selection.selection_hash,
                "manual_repair_count": 0,
            },
        ),
        _stage(
            "realization",
            "pass",
            (),
            {
                "phase6_report_hash": reference.alpha_phase6.phase6.report.report_hash,
                "rollback_verified": realization.rollback.verified,
                "rollback_hash": realization.rollback.rollback_hash,
            },
        ),
        _stage(
            "objective_evaluation",
            "fail",
            (Phase7ReasonCode.EVALUATION_FAILED,),
            {
                "evaluation_hash": reference.alpha_candidate.evaluation.report_hash,
                "protected_retained": verification.alpha_protected.solved,
                "new_task_solved": verification.alpha_phase11_heldout.solved,
                "rejection_reason": "protected_capability_regression",
            },
        ),
        _stage("certificate_construction", "not_evaluated", (), {}),
        _stage("lean_bridge", "not_evaluated", (), {}),
        _stage("hardened_checker", "not_evaluated", (), {}),
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


def _beta_stages(
    reference: Phase11BReference,
    verification: Phase11BAuthoritativeVerification,
) -> Sequence[Phase7StageResult]:
    realization = reference.beta_phase6.phase6.report.realization
    if realization is None:
        raise ValueError("beta Phase 6 realization is unavailable")
    return (
        _stage(
            "generator",
            "pass",
            (),
            {
                "proposal_source": "active_predecessor_model",
                "invocation_hash": reference.beta_invocation.report_hash,
                "program_hash": reference.beta_invocation.program.program_hash,
                "fresh_after_candidate_rejection": True,
                "heldout_material_consumed": False,
            },
        ),
        _stage(
            "proposal_validation",
            "pass",
            (),
            {
                "validation_hash": reference.beta_validation.report_hash,
                "validated": reference.beta_validation.accepted,
            },
        ),
        _stage(
            "selection",
            "pass",
            (),
            {
                "selection_hash": reference.beta_phase6.selection.selection_hash,
                "manual_repair_count": 0,
                "affected_components": list(
                    reference.beta_invocation.program.expected_affected_components
                ),
            },
        ),
        _stage(
            "realization",
            "pass",
            (),
            {
                "phase6_report_hash": reference.beta_phase6.phase6.report.report_hash,
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
                "beta_protected_report_hash": verification.beta_protected.report_hash,
                "beta_phase10_heldout_report_hash": (
                    verification.beta_phase10_heldout.report_hash
                ),
                "beta_phase11_heldout_report_hash": (
                    verification.beta_phase11_heldout.report_hash
                ),
            },
        ),
        _stage(
            "hardened_checker",
            "pass",
            (),
            {
                "hardened_report_hash": verification.hardened_checker.report_hash,
                "checker_accepted": verification.hardened_checker.accepted,
                "phase9_transition_hash": (
                    reference.lifecycle_transition.semantic_report_hash
                ),
                "candidate_unchanged": verification.beta_unchanged,
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
class Phase11BPromotionEvidence:
    reference: Phase11BReference
    verification: Phase11BAuthoritativeVerification
    rejection_attempt: Phase7AttemptReport
    rejection_ledger_hash: str
    promotion_attempt: Phase7AttemptReport
    promotion: Phase7PromotionCommit
    initial_active_package_hash: str
    active_package_hash_after_rejection: str
    installed_generator_bytes_hash: str
    installed_planner_bytes_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase11b.promotion.v1"

    @property
    def accepted(self) -> bool:
        pointer = self.promotion.snapshot.pointer
        return (
            self.reference.accepted
            and self.verification.accepted
            and self.rejection_attempt.verdict == "reject"
            and self.active_package_hash_after_rejection
            == self.initial_active_package_hash
            and self.promotion_attempt.verdict == "accept"
            and self.promotion.package_manifest.parent_package_hash
            == self.initial_active_package_hash
            and pointer.active_package_hash
            == self.promotion.package_manifest.package_hash
            and pointer.ledger_sequence_number == 2
            and self.installed_generator_bytes_hash
            == sha256_hex(
                (
                    self.reference.beta_candidate.root
                    / "policies/generator_policy.json"
                ).read_bytes()
            )
            and self.installed_planner_bytes_hash
            == sha256_hex(
                (
                    self.reference.beta_candidate.root
                    / "policies/planner_policy.json"
                ).read_bytes()
            )
            and self.reference.beta_candidate.manifest.generator_policy_hash
            != self.reference.active.active_manifest.generator_policy_hash
            and self.reference.beta_candidate.manifest.planner_policy_hash
            != self.reference.active.active_manifest.planner_policy_hash
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reference_hash": self.reference.reference_hash,
            "verification_hash": self.verification.report_hash,
            "rejection_attempt": self.rejection_attempt.to_json(),
            "rejection_ledger_hash": self.rejection_ledger_hash,
            "active_package_hash_before_rejection": self.initial_active_package_hash,
            "active_package_hash_after_rejection": (
                self.active_package_hash_after_rejection
            ),
            "promotion_attempt": self.promotion_attempt.to_json(),
            "promoted_package_hash": self.promotion.package_manifest.package_hash,
            "promoted_package_id": self.promotion.package_manifest.package_id,
            "parent_package_hash": self.promotion.package_manifest.parent_package_hash,
            "promotion_ledger_hash": self.promotion.ledger_entry.entry_hash,
            "ledger_sequence_number": (
                self.promotion.snapshot.pointer.ledger_sequence_number
            ),
            "installed_generator_bytes_hash": self.installed_generator_bytes_hash,
            "installed_planner_bytes_hash": self.installed_planner_bytes_hash,
            "active_generator_hash": (
                self.reference.active.active_manifest.generator_policy_hash
            ),
            "successor_generator_hash": (
                self.reference.beta_candidate.manifest.generator_policy_hash
            ),
            "active_planner_hash": self.reference.active.active_manifest.planner_policy_hash,
            "successor_planner_hash": (
                self.reference.beta_candidate.manifest.planner_policy_hash
            ),
            "manual_repair_count": 0,
            "recursive_use_of_successor_generator": False,
        }


def promote_phase11b_candidate(
    reference: Phase11BReference,
    verification: Phase11BAuthoritativeVerification,
    *,
    store_root: Path,
    evidence_root: Path,
) -> Phase11BPromotionEvidence:
    if not reference.accepted or not verification.accepted:
        raise ValueError("Phase 11B lifecycle is not eligible for promotion")
    policy = phase11b_phase7_policy()
    budget = phase11b_phase7_budget()
    snapshot = bootstrap_phase7_store(
        store_root,
        reference.wrapper_predecessor.payload_root.parent,
        policy,
        bootstrap_id="phase11b-active-model-bootstrap-v1",
    )
    initial_hash = snapshot.pointer.active_package_hash
    run_id = phase7_run_id(
        run_label="phase11b-autonomous-generator-v1",
        active_pointer_hash=snapshot.pointer.pointer_hash,
        policy_hash=policy.policy_hash,
        budget_hash=budget.budget_hash,
    )
    root = evidence_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 11B evidence root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)

    alpha_root = root / "attempt-0000"
    alpha_payloads: dict[str, object] = {
        "generator_input.json": reference.alpha_invocation.generator_input.to_json(),
        "invocation.json": reference.alpha_invocation.to_json(),
        "program_validation.json": reference.alpha_validation.to_json(),
        "selection.json": reference.alpha_phase6.selection.to_json(),
        "phase6_report.json": reference.alpha_phase6.phase6.report.to_json(),
        "candidate_evaluation.json": reference.alpha_candidate.evaluation.to_json(),
        "authoritative_alpha_protected.json": verification.alpha_protected.to_json(),
        "authoritative_alpha_new_task.json": (
            verification.alpha_phase11_heldout.to_json()
        ),
    }
    alpha_hashes = {
        name: _write_json(alpha_root / name, value)
        for name, value in sorted(
            alpha_payloads.items(), key=lambda item: item[0].encode("utf-8")
        )
    }
    alpha_attempt = Phase7AttemptReport(
        run_id=run_id,
        attempt_index=0,
        transition_id=reference.alpha_phase6.selection.transition_id,
        verdict="reject",
        reason_codes=(Phase7ReasonCode.EVALUATION_FAILED,),
        controller_units_consumed=1,
        active_pointer_hash_before=snapshot.pointer.pointer_hash,
        active_pointer_hash_after=snapshot.pointer.pointer_hash,
        generator_input_hash=(
            reference.alpha_invocation.generator_input.input_hash
        ),
        proposal_hash=reference.alpha_phase6.selection.proposal_hash,
        selection_hash=reference.alpha_phase6.selection.selection_hash,
        phase6_report_hash=reference.alpha_phase6.phase6.report.report_hash,
        candidate_package_tree_hash=_directory_tree_hash(
            reference.alpha_phase6.candidate_root
        ),
        evaluation_hash=reference.alpha_candidate.evaluation.report_hash,
        certificate_hash=None,
        lean_report_hash=None,
        checker_report_hash=None,
        fallback_rollback_verified=True,
        manual_repair_count=0,
        stages=_alpha_stages(reference, verification),
        artifact_hashes=FrozenHashMap.from_mapping(
            alpha_hashes,
            "phase11b.alpha_artifact_hashes",
        ),
    )
    _write_json(alpha_root / "attempt_report.json", alpha_attempt.to_json())
    snapshot_after_rejection, rejection_entry = append_phase7_nonpromotion(
        snapshot,
        alpha_attempt,
        policy,
        event="rejection",
    )
    if snapshot_after_rejection.pointer.active_package_hash != initial_hash:
        raise ValueError("rejected Phase 11B attempt changed the active package")

    beta_root = root / "attempt-0001"
    beta_payloads: dict[str, object] = {
        "policy.json": policy.to_json(),
        "generator_input.json": reference.beta_invocation.generator_input.to_json(),
        "invocation.json": reference.beta_invocation.to_json(),
        "program_validation.json": reference.beta_validation.to_json(),
        "selection.json": reference.beta_phase6.selection.to_json(),
        "phase6_report.json": reference.beta_phase6.phase6.report.to_json(),
        "candidate_evaluation.json": reference.beta_candidate.evaluation.to_json(),
        "verification.json": verification.to_json(),
        "gate_d_certificate.json": reference.lifecycle_certificate.to_json(),
        "phase9_transition.json": reference.lifecycle_transition.to_json(),
        "information.json": verification.information_report.to_json(),
        "gate_b_lean_report.json": verification.gate_b_lean.report.to_json(),
        "hardened_checker.json": verification.hardened_checker.to_json(),
        "task_beta_protected.json": verification.beta_protected.to_json(),
        "task_beta_phase10_heldout.json": (
            verification.beta_phase10_heldout.to_json()
        ),
        "task_beta_phase11_heldout.json": (
            verification.beta_phase11_heldout.to_json()
        ),
    }
    beta_hashes = {
        name: _write_json(beta_root / name, value)
        for name, value in sorted(
            beta_payloads.items(), key=lambda item: item[0].encode("utf-8")
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
            "active_protected": verification.active_protected.to_json(),
            "active_phase10_heldout": verification.active_phase10_heldout.to_json(),
            "active_phase11_heldout": verification.active_phase11_heldout.to_json(),
            "beta_protected": verification.beta_protected.to_json(),
            "beta_phase10_heldout": verification.beta_phase10_heldout.to_json(),
            "beta_phase11_heldout": verification.beta_phase11_heldout.to_json(),
        }
    )
    combined_checker_hash = canonical_json_hash(
        {
            "hardened": verification.hardened_checker.to_json(),
            "gate_d": reference.lifecycle_transition.to_json(),
        }
    )
    beta_attempt = Phase7AttemptReport(
        run_id=run_id,
        attempt_index=1,
        transition_id=reference.beta_phase6.selection.transition_id,
        verdict="accept",
        reason_codes=(),
        controller_units_consumed=1,
        active_pointer_hash_before=(
            snapshot_after_rejection.pointer.pointer_hash
        ),
        active_pointer_hash_after=(
            snapshot_after_rejection.pointer.pointer_hash
        ),
        generator_input_hash=reference.beta_invocation.generator_input.input_hash,
        proposal_hash=reference.beta_phase6.selection.proposal_hash,
        selection_hash=reference.beta_phase6.selection.selection_hash,
        phase6_report_hash=reference.beta_phase6.phase6.report.report_hash,
        candidate_package_tree_hash=_directory_tree_hash(
            reference.beta_phase6.candidate_root
        ),
        evaluation_hash=verification.report_hash,
        certificate_hash=combined_certificate_hash,
        lean_report_hash=combined_lean_hash,
        checker_report_hash=combined_checker_hash,
        fallback_rollback_verified=True,
        manual_repair_count=0,
        stages=_beta_stages(reference, verification),
        artifact_hashes=FrozenHashMap.from_mapping(
            beta_hashes,
            "phase11b.beta_artifact_hashes",
        ),
    )
    _write_json(beta_root / "attempt_report.json", beta_attempt.to_json())
    promotion = promote_phase7_candidate(
        snapshot_after_rejection,
        reference.beta_phase6.candidate_root,
        beta_root,
        beta_attempt,
        policy,
    )
    reopened = load_active_phase7_store(store_root, policy)
    if reopened.pointer != promotion.snapshot.pointer:
        raise ValueError("reopened Phase 11B active pointer differs")
    verify_immutable_phase7_package(reopened.package_root, policy)
    installed_root = (
        reopened.package_root
        / "predecessor/payload"
        / EMBEDDED_PHASE11_ROOT
    )
    installed_manifest = load_package_manifest(installed_root)
    if installed_manifest.package_hash != reference.beta_candidate.manifest.package_hash:
        raise ValueError("promoted Phase 11B package contains the wrong learned package")
    installed_generator_bytes_hash = sha256_hex(
        (installed_root / "policies/generator_policy.json").read_bytes()
    )
    installed_planner_bytes_hash = sha256_hex(
        (installed_root / "policies/planner_policy.json").read_bytes()
    )
    result = Phase11BPromotionEvidence(
        reference=reference,
        verification=verification,
        rejection_attempt=alpha_attempt,
        rejection_ledger_hash=rejection_entry.entry_hash,
        promotion_attempt=beta_attempt,
        promotion=promotion,
        initial_active_package_hash=initial_hash,
        active_package_hash_after_rejection=(
            snapshot_after_rejection.pointer.active_package_hash
        ),
        installed_generator_bytes_hash=installed_generator_bytes_hash,
        installed_planner_bytes_hash=installed_planner_bytes_hash,
    )
    if not result.accepted:
        raise ValueError("Phase 11B promotion did not close")
    _write_json(root / "phase11b_promotion_report.json", result.to_json())
    return result


@dataclass(frozen=True, slots=True)
class Phase11BClosureEvidence:
    reference: Phase11BReference
    verification: Phase11BAuthoritativeVerification
    promotion: Phase11BPromotionEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase11b.closure.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.reference.accepted
            and self.verification.accepted
            and self.promotion.accepted
        )

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
            "active_predecessor_model_generated_proposal": True,
            "heldout_material_consumed": False,
            "model_generated_candidate_rejected": True,
            "later_fresh_proposal_accepted": True,
            "manual_repairs": 0,
            "successor_generator_bytes_changed": True,
            "successor_planner_bytes_changed": True,
            "successor_generator_planner_installed": True,
            "recursive_use_of_modified_successor_generator": False,
            "phase11_exit_closed": self.accepted,
            "next_phase": 12,
        }


__all__ = [
    "PHASE11B_CONTROLLER_ENVIRONMENT_HASH",
    "PHASE11B_CONTROLLER_POLICY_ID",
    "Phase11BAuthoritativeVerification",
    "Phase11BClosureEvidence",
    "Phase11BPromotionEvidence",
    "phase11b_phase7_budget",
    "phase11b_phase7_policy",
    "promote_phase11b_candidate",
    "verify_phase11b_candidates",
]
