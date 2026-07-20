from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

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
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.policy import phase7_run_id
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_stage import Phase7StageResult
from rcp_rclm_runtime.promotion.store_transactions import promote_phase7_candidate
from rcp_rclm_runtime.promotion.store_verifier import (
    bootstrap_phase7_store,
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.promotion.store_types import Phase7PromotionCommit
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.promotion.evaluator import (
    Phase7EvaluationEvidence,
    evaluate_realized_candidate,
)
from rcp_rclm_runtime.torch_backend.pilot_policy import (
    PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
    pytorch_pilot_phase7_budget,
    pytorch_pilot_phase7_policy,
)
from rcp_rclm_runtime_v3.phase10.information import (
    Phase10InformationReport,
    build_information_report,
)
from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    PROTECTED_TASK,
)
from rcp_rclm_runtime_v3.phase10.lifecycle import (
    EMBEDDED_PHASE10_ROOT,
    Phase10Phase6Fixture,
)
from rcp_rclm_runtime_v3.phase10.tasks import (
    TaskVerifierReport,
    verify_decoded_task,
)

PHASE10_PROMOTION_SCHEMA_ID: Final[str] = "runtime.v3.phase10.promotion.v1"
PHASE10_VERIFICATION_SCHEMA_ID: Final[str] = "runtime.v3.phase10.verification.v1"
PHASE10_PROMOTION_POLICY_NOTE: Final[str] = (
    "immutable_runtime_v2_pytorch_policy_reused_as_transport_only"
)


def _write_json(path: Path, value: object) -> str:
    content = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return sha256_hex(content)


def _directory_tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _forbidden_training_modules() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or name.endswith("phase10.training_process")
        or name.endswith("phase10_training_worker")
    )


@dataclass(frozen=True, slots=True)
class Phase10VerificationEvidence:
    logical_evaluation: Phase7EvaluationEvidence
    predecessor_protected: TaskVerifierReport
    predecessor_heldout: TaskVerifierReport
    candidate_protected: TaskVerifierReport
    candidate_heldout: TaskVerifierReport
    information_report: Phase10InformationReport
    gate_b_certificate: Phase7CertificateEvidence
    gate_b_lean: LeanBridgeVerificationEvidence
    hardened_checker: Phase4HardenedReport
    candidate_tree_hash_before: str
    candidate_tree_hash_after: str
    expected_task_reports_match: bool
    forbidden_training_modules_loaded: Sequence[str]

    @property
    def candidate_unchanged(self) -> bool:
        return self.candidate_tree_hash_before == self.candidate_tree_hash_after

    @property
    def accepted(self) -> bool:
        return (
            self.predecessor_protected.solved
            and not self.predecessor_heldout.solved
            and self.candidate_protected.solved
            and self.candidate_heldout.solved
            and self.information_report.accepted
            and self.expected_task_reports_match
            and self.gate_b_lean.report.accepted
            and self.gate_b_lean.source_guard.clean
            and self.hardened_checker.accepted
            and self.candidate_unchanged
            and not self.forbidden_training_modules_loaded
        )

    @property
    def semantic_report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": PHASE10_VERIFICATION_SCHEMA_ID,
            "accepted": self.accepted,
            "logical_evaluation": self.logical_evaluation.to_json(),
            "predecessor_protected": self.predecessor_protected.to_json(),
            "predecessor_heldout": self.predecessor_heldout.to_json(),
            "candidate_protected": self.candidate_protected.to_json(),
            "candidate_heldout": self.candidate_heldout.to_json(),
            "information_report": self.information_report.to_json(),
            "gate_b_certificate": self.gate_b_certificate.to_json(),
            "gate_b_lean_report": self.gate_b_lean.report.to_json(),
            "gate_b_source_guard": self.gate_b_lean.source_guard.to_json(),
            "hardened_checker": self.hardened_checker.to_json(),
            "candidate_tree_hash_before": self.candidate_tree_hash_before,
            "candidate_tree_hash_after": self.candidate_tree_hash_after,
            "candidate_unchanged": self.candidate_unchanged,
            "expected_task_reports_match": self.expected_task_reports_match,
            "forbidden_training_modules_loaded": list(
                self.forbidden_training_modules_loaded
            ),
            "training_invocations": 0,
            "candidate_self_report_consumed": False,
        }


def verify_phase10_candidate(
    fixture: Phase10Phase6Fixture,
    *,
    repo_root: Path,
    lean_project_root: Path,
    candidate_root: Path | None = None,
) -> Phase10VerificationEvidence:
    resolved_candidate = (
        fixture.candidate_root
        if candidate_root is None
        else candidate_root.resolve(strict=True)
    )
    embedded_predecessor = fixture.embedded_predecessor_root
    embedded_candidate = resolved_candidate / "payload" / EMBEDDED_PHASE10_ROOT
    candidate_tree_before = _directory_tree_hash(resolved_candidate)

    predecessor_protected = verify_decoded_task(
        embedded_predecessor,
        PROTECTED_TASK,
        lean_project_root,
    )
    predecessor_heldout = verify_decoded_task(
        embedded_predecessor,
        HELDOUT_TASK,
        lean_project_root,
    )
    candidate_protected = verify_decoded_task(
        embedded_candidate,
        PROTECTED_TASK,
        lean_project_root,
    )
    candidate_heldout = verify_decoded_task(
        embedded_candidate,
        HELDOUT_TASK,
        lean_project_root,
    )
    expected_reports_match = (
        predecessor_protected.to_json()
        == fixture.reference.predecessor_protected.to_json()
        and candidate_protected.to_json()
        == fixture.reference.candidate_protected.to_json()
        and candidate_heldout.to_json()
        == fixture.reference.candidate_heldout.to_json()
    )
    information = build_information_report(
        embedded_predecessor,
        embedded_candidate,
        PROTECTED_TASK,
        HELDOUT_TASK,
    )
    if information.report_hash != fixture.reference.information_report.report_hash:
        raise ValueError("authoritative information report differs from the frozen reference")

    logical = evaluate_realized_candidate(
        fixture.wrapper_predecessor.payload_root.parent,
        resolved_candidate,
        fixture.selection,
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
        transition_id=fixture.selection.transition_id,
        predecessor=logical.predecessor.state,
        candidate=logical.candidate,
        certificate=gate_b_certificate.certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=reference_resource_record(
            budget_units=1,
            consumed_units=1,
            environment_hash=PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
        ),
        protected_distinctions=reference_protected_distinctions(
            "gate_b_classical"
        ),
        evaluation_evidence=logical.evaluation,
        lean_bridge_report=gate_b_lean.report,
    )
    package_integrity = build_reference_package_integrity(checker_request)
    hardened = check_hardened_transition(
        Phase4HardenedRequest(
            checker_request=checker_request,
            package_integrity=package_integrity,
        )
    )
    candidate_tree_after = _directory_tree_hash(resolved_candidate)
    evidence = Phase10VerificationEvidence(
        logical_evaluation=logical,
        predecessor_protected=predecessor_protected,
        predecessor_heldout=predecessor_heldout,
        candidate_protected=candidate_protected,
        candidate_heldout=candidate_heldout,
        information_report=information,
        gate_b_certificate=gate_b_certificate,
        gate_b_lean=gate_b_lean,
        hardened_checker=hardened,
        candidate_tree_hash_before=candidate_tree_before,
        candidate_tree_hash_after=candidate_tree_after,
        expected_task_reports_match=expected_reports_match,
        forbidden_training_modules_loaded=tuple(_forbidden_training_modules()),
    )
    if not evidence.accepted:
        raise ValueError("Phase 10 authoritative verification did not accept")
    if not fixture.reference.transition_report.accepted:
        raise ValueError("Phase 9/Gate D transition is not accepted")
    return evidence


def _stage(
    name: str,
    evidence: Mapping[str, object],
) -> Phase7StageResult:
    return Phase7StageResult.build(name, "pass", (), evidence)


def _attempt_stages(
    fixture: Phase10Phase6Fixture,
    verification: Phase10VerificationEvidence,
) -> Sequence[Phase7StageResult]:
    realization = fixture.phase6.report.realization
    if realization is None:
        raise ValueError("Phase 6 realization is unavailable")
    return (
        _stage(
            "generator",
            {
                "proposal_source": "isolated_untrusted_training_worker",
                "successor_request_hash": fixture.reference.successor_request.request_hash,
                "heldout_material_consumed": False,
                "learned_proposal_authority": False,
            },
        ),
        _stage(
            "proposal_validation",
            {
                "proposal_hash": fixture.selection.proposal_hash,
                "candidate_model_identity_hash": (
                    fixture.reference.candidate_manifest.model_identity_hash
                ),
                "host_recomputed_training_output": True,
                "candidate_self_report_consumed": False,
            },
        ),
        _stage(
            "selection",
            {
                "selection_hash": fixture.selection.selection_hash,
                "selection_policy_id": fixture.selection.selection_policy_id,
                "selection_constructed_outside_training_worker": True,
                "substantive_component_kinds": ["model_weights"],
            },
        ),
        _stage(
            "realization",
            {
                "phase6_report_hash": fixture.phase6.report.report_hash,
                "rollback_verified": realization.rollback.verified,
                "rollback_hash": realization.rollback.rollback_hash,
                "changed_file_count": len(realization.changes),
            },
        ),
        _stage(
            "objective_evaluation",
            {
                "verification_hash": verification.semantic_report_hash,
                "protected_task_retained": verification.candidate_protected.solved,
                "new_heldout_task_solved": verification.candidate_heldout.solved,
                "information_nonregression": (
                    verification.information_report.protected_nonregression
                ),
                "strict_information_witness": (
                    verification.information_report.strict_information_witness
                ),
            },
        ),
        _stage(
            "certificate_construction",
            {
                "gate_b_certificate_hash": (
                    verification.gate_b_certificate.certificate_hash
                ),
                "gate_d_certificate_hash": (
                    fixture.reference.certificate.certificate_hash
                ),
                "constructed_outside_candidate": True,
            },
        ),
        _stage(
            "lean_bridge",
            {
                "gate_b_lean_report_hash": verification.gate_b_lean.report.report_hash,
                "predecessor_task_report_hash": (
                    verification.predecessor_protected.report_hash
                ),
                "candidate_protected_report_hash": (
                    verification.candidate_protected.report_hash
                ),
                "candidate_heldout_report_hash": (
                    verification.candidate_heldout.report_hash
                ),
                "source_guard_clean": verification.gate_b_lean.source_guard.clean,
            },
        ),
        _stage(
            "hardened_checker",
            {
                "hardened_report_hash": verification.hardened_checker.report_hash,
                "checker_accepted": verification.hardened_checker.accepted,
                "phase9_transition_report_hash": (
                    fixture.reference.transition_report.semantic_report_hash
                ),
                "candidate_unchanged": verification.candidate_unchanged,
            },
        ),
        _stage(
            "fallback_rollback",
            {
                "rollback_verified": realization.rollback.verified,
                "archive_hash": realization.rollback.archive_hash,
                "restored_tree_hash": realization.rollback.restored_tree_hash,
            },
        ),
    )


@dataclass(frozen=True, slots=True)
class Phase10PromotionEvidence:
    fixture: Phase10Phase6Fixture
    verification: Phase10VerificationEvidence
    attempt: Phase7AttemptReport
    promotion: Phase7PromotionCommit
    initial_active_package_hash: str

    @property
    def accepted(self) -> bool:
        snapshot = self.promotion.snapshot
        return (
            self.fixture.accepted
            and self.verification.accepted
            and self.attempt.verdict == "accept"
            and snapshot.pointer.active_package_hash
            == self.promotion.package_manifest.package_hash
            and self.promotion.package_manifest.parent_package_hash
            == self.initial_active_package_hash
            and snapshot.pointer.ledger_sequence_number == 1
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": PHASE10_PROMOTION_SCHEMA_ID,
            "accepted": self.accepted,
            "fixture_hash": self.fixture.to_json()["fixture_hash"],
            "verification_hash": self.verification.semantic_report_hash,
            "attempt_report_hash": self.attempt.report_hash,
            "initial_active_package_hash": self.initial_active_package_hash,
            "promoted_package_hash": self.promotion.package_manifest.package_hash,
            "promoted_package_id": self.promotion.package_manifest.package_id,
            "parent_package_hash": self.promotion.package_manifest.parent_package_hash,
            "ledger_entry_hash": self.promotion.ledger_entry.entry_hash,
            "ledger_sequence_number": (
                self.promotion.snapshot.pointer.ledger_sequence_number
            ),
            "controller_policy_hash": (
                self.promotion.package_manifest.controller_policy_hash
            ),
            "controller_policy_note": PHASE10_PROMOTION_POLICY_NOTE,
            "candidate_model_identity_hash": (
                self.fixture.reference.candidate_manifest.model_identity_hash
            ),
            "phase9_transition_report_hash": (
                self.fixture.reference.transition_report.semantic_report_hash
            ),
            "rollback_verified": bool(
                self.fixture.phase6.report.realization
                and self.fixture.phase6.report.realization.rollback.verified
            ),
            "training_invocations_during_promotion": 0,
        }


def promote_phase10_candidate(
    fixture: Phase10Phase6Fixture,
    verification: Phase10VerificationEvidence,
    *,
    store_root: Path,
    evidence_root: Path,
) -> Phase10PromotionEvidence:
    if not fixture.accepted or not verification.accepted:
        raise ValueError("Phase 10 candidate is not eligible for promotion")
    policy = pytorch_pilot_phase7_policy()
    budget = pytorch_pilot_phase7_budget()
    snapshot = bootstrap_phase7_store(
        store_root,
        fixture.wrapper_predecessor.payload_root.parent,
        policy,
        bootstrap_id="phase10-learned-bootstrap-v1",
    )
    initial_hash = snapshot.pointer.active_package_hash
    run_id = phase7_run_id(
        run_label="phase10-learned-promotion-v1",
        active_pointer_hash=snapshot.pointer.pointer_hash,
        policy_hash=policy.policy_hash,
        budget_hash=budget.budget_hash,
    )
    evidence_path = evidence_root.resolve(strict=False)
    if evidence_path.exists():
        raise FileExistsError(f"promotion evidence already exists: {evidence_path}")
    evidence_path.mkdir(parents=True, exist_ok=False)
    payloads: dict[str, object] = {
        "policy.json": policy.to_json(),
        "phase6_report.json": fixture.phase6.report.to_json(),
        "selection.json": fixture.selection.to_json(),
        "verification.json": verification.to_json(),
        "phase9_transition.json": fixture.reference.transition_report.to_json(),
        "gate_d_certificate.json": fixture.reference.certificate.to_json(),
        "information.json": verification.information_report.to_json(),
        "gate_b_lean_report.json": verification.gate_b_lean.report.to_json(),
        "hardened_checker.json": verification.hardened_checker.to_json(),
        "task_predecessor_protected.json": verification.predecessor_protected.to_json(),
        "task_predecessor_heldout.json": verification.predecessor_heldout.to_json(),
        "task_candidate_protected.json": verification.candidate_protected.to_json(),
        "task_candidate_heldout.json": verification.candidate_heldout.to_json(),
    }
    artifact_hashes: dict[str, str] = {}
    for name in sorted(payloads, key=lambda item: item.encode("utf-8")):
        artifact_hashes[name] = _write_json(evidence_path / name, payloads[name])

    combined_certificate_hash = canonical_json_hash(
        {
            "gate_b": verification.gate_b_certificate.to_json(),
            "gate_d": fixture.reference.certificate.to_json(),
        }
    )
    combined_lean_hash = canonical_json_hash(
        {
            "gate_b": verification.gate_b_lean.report.to_json(),
            "predecessor_protected": verification.predecessor_protected.to_json(),
            "predecessor_heldout": verification.predecessor_heldout.to_json(),
            "candidate_protected": verification.candidate_protected.to_json(),
            "candidate_heldout": verification.candidate_heldout.to_json(),
        }
    )
    combined_checker_hash = canonical_json_hash(
        {
            "hardened": verification.hardened_checker.to_json(),
            "gate_d": fixture.reference.transition_report.to_json(),
        }
    )
    attempt = Phase7AttemptReport(
        run_id=run_id,
        attempt_index=0,
        transition_id=fixture.selection.transition_id,
        verdict="accept",
        reason_codes=(),
        controller_units_consumed=1,
        active_pointer_hash_before=snapshot.pointer.pointer_hash,
        active_pointer_hash_after=snapshot.pointer.pointer_hash,
        generator_input_hash=fixture.reference.successor_request.request_hash,
        proposal_hash=fixture.selection.proposal_hash,
        selection_hash=fixture.selection.selection_hash,
        phase6_report_hash=fixture.phase6.report.report_hash,
        candidate_package_tree_hash=verification.candidate_tree_hash_before,
        evaluation_hash=verification.semantic_report_hash,
        certificate_hash=combined_certificate_hash,
        lean_report_hash=combined_lean_hash,
        checker_report_hash=combined_checker_hash,
        fallback_rollback_verified=True,
        manual_repair_count=0,
        stages=_attempt_stages(fixture, verification),
        artifact_hashes=FrozenHashMap.from_mapping(
            artifact_hashes,
            "phase10.promotion.artifact_hashes",
        ),
    )
    _write_json(evidence_path / "attempt_report.json", attempt.to_json())
    promotion = promote_phase7_candidate(
        snapshot,
        fixture.candidate_root,
        evidence_path,
        attempt,
        policy,
    )
    verified_snapshot = load_active_phase7_store(store_root, policy)
    if verified_snapshot.pointer != promotion.snapshot.pointer:
        raise ValueError("reopened Phase 7 pointer differs from promotion result")
    verify_immutable_phase7_package(
        verified_snapshot.package_root,
        policy,
    )
    result = Phase10PromotionEvidence(
        fixture=fixture,
        verification=verification,
        attempt=attempt,
        promotion=promotion,
        initial_active_package_hash=initial_hash,
    )
    if not result.accepted:
        raise ValueError("Phase 10 atomic promotion did not close")
    _write_json(evidence_path.parent / "phase10_promotion_report.json", result.to_json())
    return result


__all__ = [
    "Phase10PromotionEvidence",
    "Phase10VerificationEvidence",
    "promote_phase10_candidate",
    "verify_phase10_candidate",
]
