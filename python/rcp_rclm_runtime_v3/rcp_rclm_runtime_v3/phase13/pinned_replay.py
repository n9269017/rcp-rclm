from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.checker.hardened import (
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
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.evaluator import evaluate_realized_candidate
from rcp_rclm_runtime.successor.records import Phase6SelectionRecord

from rcp_rclm_runtime_v3.contract.state import LearnedRCLMState
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, verify_decoded_task
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import verify_phase11b_task
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import verify_phase12b_task
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import verify_phase12c_task
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import verify_phase12d_task
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import verify_phase12e_task
from rcp_rclm_runtime_v3.phase13.boundary import forbidden_modules_loaded
from rcp_rclm_runtime_v3.phase13.full_records import Phase13CheckRecord


_PHASE12B_POLICY_ID = "rcp-rclm-v3-phase12-first-self-hosted-promotion-v1"
_PHASES: Sequence[tuple[str, str, str, int]] = (
    (
        "M1",
        "phase12d/phase12c/phase12b",
        "phase12d-prefix/phase12c-prefix/phase12b-prefix/attempt-0001",
        2,
    ),
    (
        "M2",
        "phase12d/phase12c",
        "phase12d-prefix/phase12c-prefix/phase12c/attempt-0001",
        2,
    ),
    (
        "M3",
        "phase12d",
        "phase12d-prefix/phase12d/attempt-0000",
        1,
    ),
    (
        "M4",
        "",
        "phase12e/attempt-0000",
        1,
    ),
)


def _object(path: Path) -> dict[str, object]:
    value = load_json_strict(path.resolve(strict=True).read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError("phase13.pinned.json", f"expected object at {path}")
    return value


def _tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _phase_root(reference_root: Path, prefix: str) -> Path:
    root = reference_root.resolve(strict=True)
    return root / prefix if prefix else root


def _environment_hash(label: str) -> str:
    if label == "M1":
        value: dict[str, object] = {
            "schema_id": "runtime.v3.phase12b.controller_environment.v1",
            "policy_id": _PHASE12B_POLICY_ID,
            "network": "disabled",
            "accelerators": 0,
            "manual_repair": "forbidden",
            "candidate_direct_write": "forbidden",
            "model_evaluator": "framework_independent_exact_integer",
            "task_verifier": "pinned_lean_theorem_verifier_v1",
            "outer_checker": "phase4_hardened_plus_gate_d_phase9",
            "rejection_preserves_active_package": True,
            "self_hosted_proposal_required": True,
        }
    elif label == "M2":
        value = {
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
    elif label == "M3":
        value = {
            "schema_id": "runtime.v3.phase12d.controller_environment.v1",
            "network": "disabled",
            "accelerators": 0,
            "training_steps_for_transition": 0,
            "manual_repair": "forbidden",
            "candidate_direct_write": "forbidden",
            "model_evaluator": "framework_independent_integer_plus_planner_plus_retrieval",
            "task_verifier": "pinned_lean_theorem_verifier_v1",
            "outer_checker": "phase4_hardened_plus_gate_d_phase9",
            "self_hosted_proposal_required": True,
            "successor_generation": 3,
        }
    elif label == "M4":
        value = {
            "schema_id": "runtime.v3.phase12e.controller_environment.v1",
            "network": "disabled",
            "accelerators": 0,
            "training_steps_for_transition": 1,
            "manual_repair": "forbidden",
            "candidate_direct_write": "forbidden",
            "model_evaluator": "framework_independent_integer_plus_adapter_plus_planner_plus_retrieval",
            "task_verifier": "pinned_lean_theorem_verifier_v1",
            "outer_checker": "phase4_hardened_plus_gate_d_phase9",
            "self_hosted_proposal_required": True,
            "successor_generation": 3,
        }
    else:
        raise ValueError(f"unsupported Phase 13 transition label: {label}")
    return canonical_json_hash(value)


def _lean_semantic_fingerprint(value: Mapping[str, object]) -> str:
    normalized = dict(value)
    normalized.pop("compiler_duration_ms", None)
    normalized.pop("toolchain_runtime_hash", None)
    return canonical_json_hash(normalized)


def _checker_semantic_fingerprint(value: Mapping[str, object]) -> str:
    checker = value.get("checker_report")
    if not isinstance(checker, Mapping):
        return canonical_json_hash({"checker_report": None})
    normalized = dict(checker)
    normalized.pop("artifact_hashes", None)
    lean = normalized.get("lean_bridge_result")
    if isinstance(lean, Mapping):
        lean_copy = dict(lean)
        evidence = lean_copy.get("evidence")
        if isinstance(evidence, Mapping):
            evidence_copy = dict(evidence)
            evidence_copy.pop("report_hash", None)
            evidence_copy.pop("toolchain_runtime_hash", None)
            lean_copy["evidence"] = evidence_copy
        normalized["lean_bridge_result"] = lean_copy
    return canonical_json_hash(normalized)


def _final_state(reference_root: Path) -> LearnedRCLMState:
    retained = _object(reference_root.resolve(strict=True) / "retained/reference.json")
    semantic = retained.get("semantic_candidate")
    if not isinstance(semantic, Mapping):
        raise SchemaValidationError("phase13.pinned.semantic_candidate", "expected object")
    candidate_state = semantic.get("candidate_state")
    return LearnedRCLMState.from_json(candidate_state)


def _task_reports(package_root: Path, lean_project_root: Path) -> Sequence[tuple[str, TaskVerifierReport]]:
    return (
        ("protected", verify_decoded_task(package_root, PROTECTED_TASK, lean_project_root)),
        ("phase10", verify_decoded_task(package_root, HELDOUT_TASK, lean_project_root)),
        ("phase11", verify_phase11b_task(package_root, lean_project_root)),
        ("phase12b", verify_phase12b_task(package_root, lean_project_root)),
        ("phase12c", verify_phase12c_task(package_root, lean_project_root)),
        ("phase12d", verify_phase12d_task(package_root, lean_project_root)),
        ("phase12e", verify_phase12e_task(package_root, lean_project_root)),
    )


def replay_phase13_task_certifications(
    *,
    reference_root: Path,
    promotion_evidence_root: Path,
    lean_project_root: Path,
) -> Sequence[Phase13CheckRecord]:
    reference = reference_root.resolve(strict=True)
    evidence = promotion_evidence_root.resolve(strict=True)
    package_root = reference / "semantic_candidate"
    state = _final_state(reference)
    retained_root = evidence / "phase12e/attempt-0000"
    retained_names = {
        "protected": "task_candidate_protected.json",
        "phase10": "task_candidate_phase10.json",
        "phase11": "task_candidate_phase11.json",
        "phase12b": "task_candidate_phase12b.json",
        "phase12c": "task_candidate_phase12c.json",
        "phase12d": "task_candidate_phase12d.json",
        "phase12e": "task_candidate_phase12e.json",
    }
    records: list[Phase13CheckRecord] = []
    for label, report in _task_reports(package_root, lean_project_root.resolve(strict=True)):
        retained = _object(retained_root / retained_names[label])
        certification = state.task_ledger.certification_by_task_id.get(report.task_id)
        checks = {
            "candidate_self_report_not_consumed": retained.get("candidate_self_report_consumed")
            is False,
            "certification_model_identity_bound": certification is not None
            and certification.model_identity_hash == report.model_identity_hash,
            "certification_report_hash_bound": certification is not None
            and certification.verifier_report_hash == report.report_hash,
            "grammar_accepted": report.grammar_accepted,
            "lean_exit_zero": report.lean_exit_code == 0,
            "lean_invoked": report.lean_invoked,
            "retained_report_reproduced": report.to_json() == retained,
            "task_solved": report.solved,
        }
        records.append(
            Phase13CheckRecord(
                record_id=f"pinned.task.{label}",
                checks={key: checks[key] for key in sorted(checks)},
                evidence_hashes={
                    "completion_hash": report.completion_hash,
                    "model_identity_hash": report.model_identity_hash,
                    "source_hash": report.source_hash,
                    "task_report_hash": report.report_hash,
                },
            )
        )
    result = tuple(sorted(records, key=lambda item: item.record_id.encode("utf-8")))
    if not all(item.accepted for item in result):
        failed = [item.record_id for item in result if not item.accepted]
        raise ValueError(f"Phase 13 task recertification failed: {', '.join(failed)}")
    return result


def replay_phase13_hardened_transitions(
    *,
    repo_root: Path,
    reference_root: Path,
    promotion_evidence_root: Path,
) -> Sequence[Phase13CheckRecord]:
    repo = repo_root.resolve(strict=True)
    reference = reference_root.resolve(strict=True)
    evidence = promotion_evidence_root.resolve(strict=True)
    project = PinnedLeanProject.discover(repo)
    lean_verifier = LeanReferenceVerifier(LeanCompiler(project=project, timeout_seconds=180))
    records: list[Phase13CheckRecord] = []
    for label, prefix, evidence_relative, resource_units in _PHASES:
        phase_root = _phase_root(reference, prefix)
        candidate_root = phase_root / "phase6_candidate"
        wrapper_root = phase_root / "wrapper_predecessor"
        selection = Phase6SelectionRecord.from_json(
            _object(candidate_root / "evidence/selection.json")
        )
        candidate_tree_before = _tree_hash(candidate_root)
        logical = evaluate_realized_candidate(wrapper_root, candidate_root, selection)
        certificate = Phase7CertificateEvidence(
            certificate_name="stability",
            certificate=canonical_rclm_certificate("gate_b_classical", "stability"),
        )
        packet = build_lean_reference_packet(
            logical.predecessor.state,
            logical.candidate,
            certificate.certificate,
        )
        lean = lean_verifier.verify_with_evidence(packet)
        checker_request = Phase3CheckerRequest(
            transition_id=selection.transition_id,
            predecessor=logical.predecessor.state,
            candidate=logical.candidate,
            certificate=certificate.certificate,
            trust_anchor=reference_trust_anchor(),
            resource_record=reference_resource_record(
                budget_units=resource_units,
                consumed_units=resource_units,
                environment_hash=_environment_hash(label),
            ),
            protected_distinctions=reference_protected_distinctions("gate_b_classical"),
            evaluation_evidence=logical.evaluation,
            lean_bridge_report=lean.report,
        )
        hardened = check_hardened_transition(
            Phase4HardenedRequest(
                checker_request=checker_request,
                package_integrity=build_reference_package_integrity(checker_request),
            )
        )
        candidate_tree_after = _tree_hash(candidate_root)
        retained_root = evidence / evidence_relative
        verification = _object(retained_root / "verification.json")
        retained_lean = _object(retained_root / "gate_b_lean_report.json")
        retained_hardened = _object(retained_root / "hardened_checker.json")
        checks = {
            "candidate_tree_unchanged": candidate_tree_before == candidate_tree_after,
            "candidate_tree_matches_retained_before": candidate_tree_before
            == verification.get("candidate_tree_hash_before"),
            "candidate_tree_matches_retained_after": candidate_tree_after
            == verification.get("candidate_tree_hash_after"),
            "certificate_reproduced": certificate.to_json()
            == verification.get("gate_b_certificate"),
            "forbidden_runtime_modules_absent": not forbidden_modules_loaded(),
            "generated_lean_source_guard_clean": lean.source_guard.clean,
            "hardened_checker_accepts": hardened.accepted,
            "hardened_checker_semantics_reproduced": _checker_semantic_fingerprint(
                hardened.to_json()
            )
            == _checker_semantic_fingerprint(retained_hardened),
            "lean_bridge_accepts": lean.report.bridge_verdict == "accept",
            "lean_semantics_reproduced": _lean_semantic_fingerprint(lean.report.to_json())
            == _lean_semantic_fingerprint(retained_lean),
            "logical_evaluation_reproduced": logical.to_json()
            == verification.get("logical_evaluation"),
            "transition_id_bound": hardened.transition_id == selection.transition_id,
        }
        records.append(
            Phase13CheckRecord(
                record_id=f"pinned.hardened.{label}",
                checks={key: checks[key] for key in sorted(checks)},
                evidence_hashes={
                    "candidate_tree_hash": candidate_tree_after,
                    "checker_semantic_fingerprint": _checker_semantic_fingerprint(
                        hardened.to_json()
                    ),
                    "generated_source_hash": lean.report.generated_source_hash,
                    "lean_semantic_fingerprint": _lean_semantic_fingerprint(
                        lean.report.to_json()
                    ),
                    "logical_evaluation_hash": logical.evaluation_hash,
                },
            )
        )
    result = tuple(sorted(records, key=lambda item: item.record_id.encode("utf-8")))
    if not all(item.accepted for item in result):
        failed = [
            f"{item.record_id}: {', '.join(key for key, ok in item.checks.items() if not ok)}"
            for item in result
            if not item.accepted
        ]
        raise ValueError(f"Phase 13 hardened replay failed: {'; '.join(failed)}")
    return result


__all__ = [
    "replay_phase13_hardened_transitions",
    "replay_phase13_task_certifications",
]
