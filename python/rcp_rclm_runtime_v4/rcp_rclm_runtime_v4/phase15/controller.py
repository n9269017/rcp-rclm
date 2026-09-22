from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.promotion._record_common import Phase7ReasonCode
from rcp_rclm_runtime.promotion.policy import phase7_run_id
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_policy import Phase7ControllerBudgetRecord
from rcp_rclm_runtime.promotion.record_stage import Phase7StageResult
from rcp_rclm_runtime.promotion.store_transactions import (
    append_phase7_nonpromotion,
    promote_phase7_candidate,
    publish_phase7_attempt_directory,
)
from rcp_rclm_runtime.promotion.store_verifier import (
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_closure import phase12b_phase7_policy
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v4.gatee.records import (
    AttemptRecord,
    AutonomousSearchReport,
    FrontierSnapshot,
    RouteHintPolicy,
)
from rcp_rclm_runtime_v4.gatee.validation import validate_report

from rcp_rclm_runtime_v4.phase15.candidate import build_phase15_candidate
from rcp_rclm_runtime_v4.phase15.challenges import (
    answer_store_json,
    challenge_manifest_json,
    challenge_suite_after_freeze,
)
from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH,
    PHASE15_EXPECTED_PHASE14_TRAJECTORY_HASH,
    PHASE15_OBJECTIVE_ID,
    PHASE15_TRAJECTORY_ID,
    PHASE15_UPDATE_KIND_BY_TARGET,
)
from rcp_rclm_runtime_v4.phase15.evaluation import (
    build_initial_m8_state,
    evaluate_phase15_candidate,
)
from rcp_rclm_runtime_v4.phase15.outer import directory_tree_hash, verify_outer_envelope
from rcp_rclm_runtime_v4.phase15.realization import phase15_phase6_budget, realize_candidate
from rcp_rclm_runtime_v4.phase15.records import Phase15AttemptSummary
from rcp_rclm_runtime_v4.phase15.trajectory import Phase15TrajectoryReport


def _write_json(path: Path, value: object) -> str:
    content = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return sha256_hex(content)


def _active_semantic_root(snapshot) -> Path:
    root = snapshot.package_root / "predecessor/payload" / EMBEDDED_PHASE12_ROOT
    manifest = load_package_manifest(root)
    if not manifest.package_hash:
        raise ValueError("active semantic package manifest is unavailable")
    return root


def phase15_budget() -> Phase7ControllerBudgetRecord:
    return Phase7ControllerBudgetRecord(
        max_attempts=2,
        max_attempt_units=2,
        attempt_unit_cost=1,
        max_promotions=1,
        phase6_budget=phase15_phase6_budget(),
    )


def _stage(
    name: str,
    status: str,
    evidence: object,
    reasons: Sequence[Phase7ReasonCode] = (),
) -> Phase7StageResult:
    return Phase7StageResult.build(name, status, reasons, evidence)  # type: ignore[arg-type]


def _stages(
    *,
    accepted: bool,
    candidate_hash: str,
    selection_hash: str,
    phase6_report_hash: str,
    evaluation_hash: str,
    gate_e_hash: str,
    outer_hash: str | None,
    rollback_hash: str,
    reason_codes: Sequence[str],
) -> tuple[Phase7StageResult, ...]:
    common = (
        _stage("generator", "pass", {"candidate_hash": candidate_hash, "package_generated": True}),
        _stage("proposal_validation", "pass", {"route_hints_absent": True, "challenge_generated_after_freeze": True}),
        _stage("selection", "pass", {"selection_hash": selection_hash, "host_selected_successful_route": False}),
        _stage("realization", "pass", {"phase6_report_hash": phase6_report_hash}),
    )
    if accepted:
        return common + (
            _stage("objective_evaluation", "pass", {"semantic_evaluation_hash": evaluation_hash}),
            _stage("certificate_construction", "pass", {"gate_e_report_hash": gate_e_hash}),
            _stage("lean_bridge", "pass", {"outer_verification_hash": outer_hash}),
            _stage("hardened_checker", "pass", {"outer_verification_hash": outer_hash}),
            _stage("fallback_rollback", "pass", {"rollback_hash": rollback_hash, "verified": True}),
        )
    return common + (
        _stage(
            "objective_evaluation",
            "fail",
            {"semantic_evaluation_hash": evaluation_hash, "reason_codes": list(reason_codes)},
            (Phase7ReasonCode.EVALUATION_FAILED,),
        ),
        _stage("certificate_construction", "not_evaluated", {"not_evaluated": True}),
        _stage("lean_bridge", "not_evaluated", {"not_evaluated": True}),
        _stage("hardened_checker", "not_evaluated", {"not_evaluated": True}),
        _stage("fallback_rollback", "pass", {"rollback_hash": rollback_hash, "verified": True}),
    )


def _gate_e_report(
    *,
    source_state_hash: str,
    challenge_manifest_hash: str,
    capability_frontier: Sequence[str],
    recursive_frontier: Sequence[str],
    attempts: Sequence[AttemptRecord],
) -> tuple[AutonomousSearchReport, dict[str, object]]:
    selected = next((item for item in attempts if item.evaluator_accepted), None)
    if selected is None:
        raise ValueError("Phase 15 Gate E report requires one accepted attempt")
    report = AutonomousSearchReport(
        source_package_hash=source_state_hash,
        history_hash=canonical_json_hash([item.attempt_hash for item in attempts]),
        challenge_commitment_hash=challenge_manifest_hash,
        route_hints=RouteHintPolicy(),
        predecessor_frontier=FrontierSnapshot(
            capability_tasks=tuple(capability_frontier),
            recursive_productivity_tasks=tuple(recursive_frontier),
        ),
        attempts=tuple(attempts),
        search_budget=2,
        manual_repairs=0,
        heldout_material_visible_before_freeze=False,
        result_kind="promoted",
        selected_attempt_index=selected.attempt_index,
        exhaustion=None,
    )
    return report, validate_report(report)


def _phase14_bindings(bundle_root: Path) -> tuple[str, str]:
    manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))
    trajectory = json.loads((bundle_root / "campaign/phase14_trajectory.json").read_text(encoding="utf-8"))
    manifest_hash = str(manifest.get("manifest_hash"))
    trajectory_hash = str(trajectory.get("report_hash"))
    if manifest_hash != PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH:
        raise ValueError("Phase 15 source bundle is not the certified Phase 14 bundle")
    if trajectory_hash != PHASE15_EXPECTED_PHASE14_TRAJECTORY_HASH:
        raise ValueError("Phase 15 source trajectory is not the certified Phase 14 trajectory")
    return manifest_hash, trajectory_hash


def run_phase15_trajectory(
    *,
    phase14_bundle_root: Path,
    work_root: Path,
    repo_root: Path,
    lean_project_root: Path | None,
    source_head: str,
    source_tree: str,
) -> Phase15TrajectoryReport:
    bundle = phase14_bundle_root.resolve(strict=True)
    phase14_manifest_hash, phase14_trajectory_hash = _phase14_bindings(bundle)
    work = work_root.resolve(strict=False)
    if work.exists():
        raise FileExistsError(f"Phase 15 work root already exists: {work}")
    work.mkdir(parents=True, exist_ok=False)
    phase14_reference = work / "phase14_reference"
    (phase14_reference / "campaign").mkdir(parents=True, exist_ok=False)
    for relative in (
        "manifest.json",
        "campaign/phase14_trajectory.json",
        "campaign/challenge_manifest.json",
        "campaign/answer_store_private.json",
    ):
        source = bundle / relative
        destination = phase14_reference / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    store_root = work / "store"
    shutil.copytree(bundle / "campaign/store", store_root, symlinks=False)
    runs_root = store_root / "runs"
    if not runs_root.exists():
        runs_root.mkdir(parents=False, exist_ok=False)
    evidence_root = work / "evidence"
    policy = phase12b_phase7_policy()
    budget = phase15_budget()
    snapshot = load_active_phase7_store(store_root, policy)
    verify_immutable_phase7_package(snapshot.package_root, policy)
    initial_store_hash = snapshot.pointer.active_package_hash
    active_semantic_root = _active_semantic_root(snapshot)
    initial_manifest = load_package_manifest(active_semantic_root)
    predecessor_state, _ = build_initial_m8_state(
        active_semantic_root,
        bundle,
        lean_project_root=lean_project_root,
    )
    phase14_trajectory = json.loads((bundle / "campaign/phase14_trajectory.json").read_text(encoding="utf-8"))
    recursive_frontier = tuple(str(item) for item in phase14_trajectory["final_recursive_productivity_frontier"])
    initial_capability = tuple(predecessor_state.capability_frontier.task_ids)
    initial_recursive = recursive_frontier

    # Both candidates are fully trained, built, and frozen before any hidden
    # challenge parameter or answer exists.
    candidates = tuple(
        build_phase15_candidate(
            active_semantic_root,
            variant=variant,
            output_root=work / "candidate_freeze" / variant / "semantic_candidate",
            training_work_root=work / "candidate_freeze" / variant / "training",
            runtime_package_root=repo_root / "python/rcp_rclm_runtime_v4",
        )
        for variant in ("lean_only", "multidomain")
    )
    freeze_hashes = tuple(item.freeze_hash for item in candidates)
    challenges = challenge_suite_after_freeze(
        source_head=source_head,
        candidate_freeze_hashes=freeze_hashes,
        phase14_bundle_manifest_hash=phase14_manifest_hash,
    )
    challenge_manifest = challenge_manifest_json(challenges, candidate_freeze_hashes=freeze_hashes)
    answer_store = answer_store_json(challenges)
    challenge_manifest_hash = str(challenge_manifest["manifest_hash"])
    answer_store_hash = str(answer_store["answer_store_hash"])
    _write_json(work / "challenge_manifest.json", challenge_manifest)
    _write_json(work / "answer_store_private.json", answer_store)
    _write_json(
        work / "candidate_freeze_manifest.json",
        {
            "schema_id": "runtime.v4.phase15.candidate_freeze_manifest.v1",
            "candidate_freeze_hashes": list(freeze_hashes),
            "candidate_semantic_package_hashes": [item.manifest.package_hash for item in candidates],
            "challenge_generated_after_all_candidate_freezes": True,
            "challenge_manifest_hash": challenge_manifest_hash,
        },
    )

    gate_e_attempts: list[AttemptRecord] = []
    summaries: list[Phase15AttemptSummary] = []
    final_gate_e_report: AutonomousSearchReport | None = None
    final_gate_e_validation: dict[str, object] | None = None
    final_state = predecessor_state
    final_recursive = recursive_frontier

    for attempt_index, candidate in enumerate(candidates):
        snapshot = load_active_phase7_store(store_root, policy)
        active_store_before = snapshot.pointer.active_package_hash
        active_semantic_root = _active_semantic_root(snapshot)
        attempt_root = evidence_root / f"attempt-{attempt_index:02d}-{candidate.variant}"
        realized = realize_candidate(active_semantic_root, candidate, attempt_root / "realization")
        evaluation = evaluate_phase15_candidate(
            active_semantic_root,
            candidate,
            bundle,
            challenges,
            predecessor_state,
            recursive_frontier,
            lean_project_root=lean_project_root,
            challenge_manifest_hash=challenge_manifest_hash,
            answer_store_hash=answer_store_hash,
        )
        capability_after = (
            predecessor_state.capability_frontier.task_ids
            if evaluation.candidate_state is None
            else evaluation.candidate_state.capability_frontier.task_ids
        )
        recursive_after = evaluation.recursive_productivity_report.candidate_frontier
        update_kinds = tuple(
            sorted(
                set(PHASE15_UPDATE_KIND_BY_TARGET.values()),
                key=lambda item: item.encode("utf-8"),
            )
        )
        gate_d_evidence_hash = canonical_json_hash(
            {
                "evaluation_hash": evaluation.report_hash,
                "certificate_hash": None if evaluation.certificate is None else evaluation.certificate.certificate_hash,
                "gate_d_report_hash": None if evaluation.gate_d_report is None else evaluation.gate_d_report.semantic_report_hash,
            }
        )
        gate_e_attempt = AttemptRecord(
            attempt_index=attempt_index,
            objective_id=PHASE15_OBJECTIVE_ID,
            update_kinds=update_kinds,
            program_hash=candidate.training.result_hash,
            candidate_hash=candidate.manifest.package_hash,
            gate_d_certificate_hash=gate_d_evidence_hash,
            package_generated=True,
            evaluator_accepted=evaluation.accepted,
            reason_codes=evaluation.reason_codes,
            capability_frontier_after=capability_after,
            recursive_productivity_frontier_after=recursive_after,
            search_cost=1,
        )
        gate_e_attempts.append(gate_e_attempt)
        gate_e_hash = canonical_json_hash(
            {
                "pending_attempt_hashes": [item.attempt_hash for item in gate_e_attempts],
                "challenge_manifest_hash": challenge_manifest_hash,
                "accepted": evaluation.accepted,
            }
        )
        gate_e_validation_hash = gate_e_hash
        outer = None
        if evaluation.accepted:
            final_gate_e_report, final_gate_e_validation = _gate_e_report(
                source_state_hash=predecessor_state.state_hash,
                challenge_manifest_hash=challenge_manifest_hash,
                capability_frontier=predecessor_state.capability_frontier.task_ids,
                recursive_frontier=recursive_frontier,
                attempts=tuple(gate_e_attempts),
            )
            gate_e_hash = final_gate_e_report.report_hash
            gate_e_validation_hash = str(final_gate_e_validation["validation_hash"])
            outer = verify_outer_envelope(
                realized,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
            )
        retained_payloads: dict[str, object] = {
            "policy.json": policy.to_json(),
            "phase6_report.json": realized.phase6.report.to_json(),
            "semantic_candidate.json": candidate.to_json(),
            "realization.json": realized.to_json(),
            "semantic_evaluation.json": evaluation.to_json(),
            "gate_e_attempt.json": gate_e_attempt.to_json(),
            "gate_e_binding.json": {
                "report_hash": gate_e_hash,
                "validation_hash": gate_e_validation_hash,
            },
            "challenge_manifest.json": challenge_manifest,
            "candidate_freeze.json": {
                "freeze_hash": candidate.freeze_hash,
                "challenge_created_before_freeze": False,
            },
        }
        if outer is not None:
            retained_payloads["outer_verification.json"] = outer.to_json()
        artifact_hashes = {
            name: _write_json(attempt_root / "retained" / name, payload)
            for name, payload in sorted(retained_payloads.items(), key=lambda item: item[0].encode("utf-8"))
        }
        realization_record = realized.phase6.report.realization
        if realization_record is None:
            raise ValueError("Phase 15 realization record is absent")
        accepted = bool(evaluation.accepted and outer is not None and outer.accepted)
        run_id = phase7_run_id(
            run_label=f"phase15-attempt-{attempt_index}-{candidate.variant}",
            active_pointer_hash=snapshot.pointer.pointer_hash,
            policy_hash=policy.policy_hash,
            budget_hash=budget.budget_hash,
        )
        phase7_attempt = Phase7AttemptReport(
            run_id=run_id,
            attempt_index=attempt_index,
            transition_id=realized.selection.transition_id,
            verdict="accept" if accepted else "reject",
            reason_codes=() if accepted else (Phase7ReasonCode.EVALUATION_FAILED,),
            controller_units_consumed=1,
            active_pointer_hash_before=snapshot.pointer.pointer_hash,
            active_pointer_hash_after=snapshot.pointer.pointer_hash,
            generator_input_hash=candidate.training.curriculum_manifest["manifest_hash"],
            proposal_hash=candidate.training.result_hash,
            selection_hash=realized.selection.selection_hash,
            phase6_report_hash=realized.phase6.report.report_hash,
            candidate_package_tree_hash=directory_tree_hash(realized.candidate_root),
            evaluation_hash=evaluation.report_hash,
            certificate_hash=gate_d_evidence_hash,
            lean_report_hash=None if outer is None else outer.lean_report_hash,
            checker_report_hash=None if outer is None else outer.checker_report_hash,
            fallback_rollback_verified=realization_record.rollback.verified,
            manual_repair_count=0,
            stages=_stages(
                accepted=accepted,
                candidate_hash=candidate.candidate_hash,
                selection_hash=realized.selection.selection_hash,
                phase6_report_hash=realized.phase6.report.report_hash,
                evaluation_hash=evaluation.report_hash,
                gate_e_hash=gate_e_hash,
                outer_hash=None if outer is None else outer.report_hash,
                rollback_hash=realization_record.rollback.rollback_hash,
                reason_codes=evaluation.reason_codes,
            ),
            artifact_hashes=FrozenHashMap.from_mapping(artifact_hashes, "phase15.attempt_artifact_hashes"),
        )
        _write_json(attempt_root / "retained/attempt_report.json", phase7_attempt.to_json())
        if accepted:
            promotion = promote_phase7_candidate(
                snapshot,
                realized.candidate_root,
                attempt_root / "retained",
                phase7_attempt,
                policy,
            )
            reopened = load_active_phase7_store(store_root, policy)
            active_store_after = reopened.pointer.active_package_hash
            if reopened.pointer != promotion.snapshot.pointer:
                raise ValueError("Phase 15 promoted store pointer differs after reopen")
            installed = load_package_manifest(_active_semantic_root(reopened))
            if installed.package_hash != candidate.manifest.package_hash:
                raise ValueError("Phase 15 installed semantic package differs")
            ledger_hash = promotion.ledger_entry.entry_hash
            rejection_evidence_hash = None
            if evaluation.candidate_state is None:
                raise ValueError("accepted Phase 15 attempt lacks candidate state")
            final_state = evaluation.candidate_state
            final_recursive = tuple(recursive_after)
        else:
            reopened, entry = append_phase7_nonpromotion(snapshot, phase7_attempt, policy, event="rejection")
            active_store_after = reopened.pointer.active_package_hash
            if active_store_after != active_store_before:
                raise ValueError("Phase 15 rejection changed active store")
            ledger_hash = entry.entry_hash
            rejection_evidence_hash = evaluation.report_hash
        staging = attempt_root / "store_attempt_staging"
        shutil.copytree(attempt_root / "retained", staging, symlinks=False)
        publish_phase7_attempt_directory(store_root, run_id, attempt_index, staging)
        summary = Phase15AttemptSummary(
            attempt_index=attempt_index,
            variant=candidate.variant,
            candidate_semantic_package_hash=candidate.manifest.package_hash,
            candidate_freeze_hash=candidate.freeze_hash,
            decoder_manifest_hash=candidate.decoder_manifest.manifest_hash,
            training_result_hash=candidate.training.result_hash,
            candidate_phase6_tree_hash=directory_tree_hash(realized.candidate_root),
            verdict="accept" if accepted else "reject",
            reason_codes=() if accepted else evaluation.reason_codes,
            protected_report_hashes=tuple(sorted((item.report_hash for item in evaluation.protected_reports))),
            predecessor_dynamic_report_hashes=tuple(sorted((item.report_hash for item in evaluation.predecessor_dynamic_reports))),
            candidate_dynamic_report_hashes=tuple(sorted((item.report_hash for item in evaluation.candidate_dynamic_reports))),
            information_report_hash=evaluation.information_report.report_hash,
            recursive_productivity_report_hash=evaluation.recursive_productivity_report.report_hash,
            gate_d_report_hash=gate_d_evidence_hash,
            gate_e_report_hash=gate_e_hash,
            gate_e_validation_hash=gate_e_validation_hash,
            outer_verification_hash=None if outer is None else outer.report_hash,
            active_store_package_hash_before=active_store_before,
            active_store_package_hash_after=active_store_after,
            phase7_ledger_entry_hash=ledger_hash,
            rejection_evidence_hash=rejection_evidence_hash,
        )
        summaries.append(summary)
        _write_json(attempt_root / "attempt_summary.json", summary.to_json())
        if accepted:
            break
    if final_gate_e_report is None or final_gate_e_validation is None:
        raise ValueError("Phase 15 bounded search failed to promote the multidomain candidate")
    final_snapshot = load_active_phase7_store(store_root, policy)
    final_manifest = load_package_manifest(_active_semantic_root(final_snapshot))
    report = Phase15TrajectoryReport(
        source_head=source_head,
        source_tree=source_tree,
        phase14_bundle_manifest_hash=phase14_manifest_hash,
        phase14_trajectory_report_hash=phase14_trajectory_hash,
        initial_store_package_hash=initial_store_hash,
        initial_m8_semantic_package_hash=initial_manifest.package_hash,
        final_store_package_hash=final_snapshot.pointer.active_package_hash,
        final_m9_semantic_package_hash=final_manifest.package_hash,
        initial_capability_frontier=initial_capability,
        final_capability_frontier=final_state.capability_frontier.task_ids,
        initial_recursive_productivity_frontier=initial_recursive,
        final_recursive_productivity_frontier=final_recursive,
        candidate_freeze_hashes=freeze_hashes,
        challenge_manifest_hash=challenge_manifest_hash,
        answer_store_hash=answer_store_hash,
        dynamic_task_ids=tuple(sorted((item.task_id for item in challenges), key=lambda item: item.encode("utf-8"))),
        attempts=tuple(summaries),
        gate_e_report_hash=final_gate_e_report.report_hash,
        gate_e_validation_hash=str(final_gate_e_validation["validation_hash"]),
    )
    _write_json(work / "phase15_trajectory.json", report.to_json())
    _write_json(work / "gate_e_report.json", final_gate_e_report.to_json())
    _write_json(work / "gate_e_validation.json", final_gate_e_validation)
    if not report.campaign_closed:
        raise ValueError("Phase 15 trajectory did not satisfy the campaign floor")
    return report


__all__ = ["phase15_budget", "run_phase15_trajectory"]
