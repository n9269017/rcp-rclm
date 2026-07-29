from __future__ import annotations

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
from rcp_rclm_runtime_v3.phase12.phase12b_closure import phase12b_phase7_policy
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v4.gatee.records import AttemptRecord

from rcp_rclm_runtime_v4.phase14.candidate import build_semantic_candidate
from rcp_rclm_runtime_v4.phase14.challenges import (
    HiddenChallenge,
    answer_store_json,
    challenge_manifest_json,
    development_challenge_suite,
)
from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE13_BUNDLE_MANIFEST_HASH,
    PHASE13_EXIT_REPORT_HASH,
    PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH,
    PHASE14_MAX_ATTEMPTS_PER_CHALLENGE,
    PHASE14_MIN_PROMOTIONS,
    PHASE14_MIN_REJECTIONS,
    PHASE14_MIN_UPDATE_FAMILIES,
    PHASE14_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v4.phase14.evaluation import (
    build_gate_e_challenge_report,
    build_initial_m4_state,
    evaluate_semantic_candidate,
    initial_recursive_frontier,
)
from rcp_rclm_runtime_v4.phase14.outer import directory_tree_hash, verify_outer_envelope
from rcp_rclm_runtime_v4.phase14.proposal import run_proposal_worker_twice
from rcp_rclm_runtime_v4.phase14.realization import (
    phase14_phase6_budget,
    realize_candidate,
)
from rcp_rclm_runtime_v4.phase14.trajectory import Phase14TrajectoryReport
from rcp_rclm_runtime_v4.phase14.records import (
    Phase14AttemptSummary,
    Phase14SearchHistory,
    Phase14SearchHistoryEntry,
)


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


def phase14_budget() -> Phase7ControllerBudgetRecord:
    return Phase7ControllerBudgetRecord(
        max_attempts=PHASE14_MAX_ATTEMPTS_PER_CHALLENGE,
        max_attempt_units=PHASE14_MAX_ATTEMPTS_PER_CHALLENGE,
        attempt_unit_cost=1,
        max_promotions=1,
        phase6_budget=phase14_phase6_budget(),
    )


def _stage(
    name: str,
    status: str,
    evidence: object,
    reasons: Sequence[Phase7ReasonCode] = (),
) -> Phase7StageResult:
    return Phase7StageResult.build(
        name,
        status,  # type: ignore[arg-type]
        reasons,
        evidence,
    )


def _stages(
    *,
    accepted: bool,
    proposal_hash: str,
    selection_hash: str,
    phase6_report_hash: str,
    semantic_evaluation_hash: str,
    gate_e_hash: str,
    outer_hash: str | None,
    rollback_hash: str,
    reason_codes: Sequence[str],
) -> tuple[Phase7StageResult, ...]:
    if accepted:
        return (
            _stage("generator", "pass", {"proposal_enumeration_hash": proposal_hash, "package_generated": True}),
            _stage("proposal_validation", "pass", {"route_hints_absent": True}),
            _stage("selection", "pass", {"selection_hash": selection_hash, "host_selected_family": False}),
            _stage("realization", "pass", {"phase6_report_hash": phase6_report_hash}),
            _stage("objective_evaluation", "pass", {"semantic_evaluation_hash": semantic_evaluation_hash}),
            _stage("certificate_construction", "pass", {"gate_e_report_hash": gate_e_hash}),
            _stage("lean_bridge", "pass", {"outer_verification_hash": outer_hash}),
            _stage("hardened_checker", "pass", {"outer_verification_hash": outer_hash}),
            _stage("fallback_rollback", "pass", {"rollback_hash": rollback_hash, "verified": True}),
        )
    return (
        _stage("generator", "pass", {"proposal_enumeration_hash": proposal_hash, "package_generated": True}),
        _stage("proposal_validation", "pass", {"route_hints_absent": True}),
        _stage("selection", "pass", {"selection_hash": selection_hash, "host_selected_family": False}),
        _stage("realization", "pass", {"phase6_report_hash": phase6_report_hash}),
        _stage(
            "objective_evaluation",
            "fail",
            {"semantic_evaluation_hash": semantic_evaluation_hash, "reason_codes": list(reason_codes)},
            (Phase7ReasonCode.EVALUATION_FAILED,),
        ),
        _stage("certificate_construction", "not_evaluated", {"not_evaluated": True}),
        _stage("lean_bridge", "not_evaluated", {"not_evaluated": True}),
        _stage("hardened_checker", "not_evaluated", {"not_evaluated": True}),
        _stage("fallback_rollback", "pass", {"rollback_hash": rollback_hash, "verified": True}),
    )




def run_phase14_trajectory(
    *,
    source_store_root: Path,
    work_root: Path,
    repo_root: Path,
    lean_project_root: Path | None,
    source_head: str,
    source_tree: str,
    challenges: Sequence[HiddenChallenge] | None = None,
) -> Phase14TrajectoryReport:
    challenge_values = tuple(
        development_challenge_suite() if challenges is None else challenges
    )
    if len(challenge_values) < PHASE14_MIN_PROMOTIONS:
        raise ValueError("Phase 14 requires at least four hidden challenges")
    if len({item.commitment_hash for item in challenge_values}) != len(
        challenge_values
    ):
        raise ValueError("Phase 14 hidden challenge commitments must be unique")
    challenge_manifest = challenge_manifest_json(challenge_values)
    private_answer_store = answer_store_json(challenge_values)
    work = work_root.resolve(strict=False)
    if work.exists():
        raise FileExistsError(f"Phase 14 work root already exists: {work}")
    work.mkdir(parents=True, exist_ok=False)
    store_root = work / "store"
    shutil.copytree(source_store_root.resolve(strict=True), store_root, symlinks=False)
    # Ordinary ZIP transport omits empty directories.  Phase 13 declares the
    # Phase 7 ``runs`` directory as the only transport-sensitive empty path,
    # so rematerialize it before reopening the immutable store.
    runs_root = store_root / "runs"
    if not runs_root.exists():
        runs_root.mkdir(parents=False, exist_ok=False)
    evidence_root = work / "evidence"
    policy = phase12b_phase7_policy()
    budget = phase14_budget()
    snapshot = load_active_phase7_store(store_root, policy)
    verify_immutable_phase7_package(snapshot.package_root, policy)
    initial_store_hash = snapshot.pointer.active_package_hash
    active_semantic_root = _active_semantic_root(snapshot)
    initial_manifest = load_package_manifest(active_semantic_root)
    if initial_manifest.package_hash != PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH:
        raise ValueError("Phase 14 did not begin from the certified M4 semantic package")
    active_state, _ = build_initial_m4_state(
        active_semantic_root,
        lean_project_root=lean_project_root,
    )
    initial_frontier = tuple(active_state.capability_frontier.task_ids)
    recursive_frontier = initial_recursive_frontier()
    initial_recursive = recursive_frontier
    history = Phase14SearchHistory(entries=())
    accepted_challenges: list[HiddenChallenge] = []
    attempt_summaries: list[Phase14AttemptSummary] = []
    gate_e_hashes: list[str] = []
    gate_e_validation_hashes: list[str] = []
    global_attempt = 0
    for challenge_index, challenge in enumerate(challenge_values):
        gate_e_attempts: list[AttemptRecord] = []
        challenge_active_state = active_state
        challenge_recursive_frontier = recursive_frontier
        for local_attempt in range(PHASE14_MAX_ATTEMPTS_PER_CHALLENGE):
            snapshot = load_active_phase7_store(store_root, policy)
            active_store_hash_before = snapshot.pointer.active_package_hash
            active_semantic_root = _active_semantic_root(snapshot)
            attempt_root = evidence_root / f"challenge-{challenge_index:02d}" / f"attempt-{local_attempt:02d}"
            proposal, first_bytes, second_bytes = run_proposal_worker_twice(
                active_semantic_root,
                challenge.commitment_hash,
                history,
                attempt_root / "proposal_worker",
            )
            if first_bytes != second_bytes:
                raise ValueError("Phase 14 proposal replay differs")
            program = proposal.programs[0]
            semantic = build_semantic_candidate(
                active_semantic_root,
                program,
                attempt_root / "semantic_candidate",
            )
            realized = realize_candidate(
                active_semantic_root,
                semantic,
                attempt_root / "realization",
            )
            evaluation = evaluate_semantic_candidate(
                active_semantic_root,
                semantic,
                active_state,
                tuple(accepted_challenges),
                challenge,
                proposal,
                history,
                recursive_frontier,
                lean_project_root=lean_project_root,
                generation=5 + challenge_index,
                hidden_challenges=challenge_values,
            )
            recursive_after = evaluation.recursive_productivity_report.candidate_frontier
            capability_after = (
                active_state.capability_frontier.task_ids
                if evaluation.candidate_state is None
                else evaluation.candidate_state.capability_frontier.task_ids
            )
            gate_e_attempt = AttemptRecord(
                attempt_index=local_attempt,
                objective_id=program.objective_id,
                update_kinds=program.update_kinds,
                program_hash=program.program_hash,
                candidate_hash=semantic.manifest.package_hash,
                gate_d_certificate_hash=evaluation.gate_d_evidence_hash,
                package_generated=True,
                evaluator_accepted=evaluation.accepted,
                reason_codes=evaluation.reason_codes,
                capability_frontier_after=capability_after,
                recursive_productivity_frontier_after=recursive_after,
                search_cost=program.search_cost,
            )
            gate_e_attempts.append(gate_e_attempt)
            gate_e_report_hash = canonical_json_hash(
                {
                    "pending_attempt_hashes": [item.attempt_hash for item in gate_e_attempts],
                    "challenge_commitment_hash": challenge.commitment_hash,
                    "accepted": evaluation.accepted,
                }
            )
            gate_e_validation_hash = gate_e_report_hash
            outer = None
            if evaluation.accepted:
                gate_e_report, gate_e_validation = build_gate_e_challenge_report(
                    challenge_active_state,
                    challenge_recursive_frontier,
                    challenge.commitment_hash,
                    tuple(gate_e_attempts),
                )
                gate_e_report_hash = gate_e_report.report_hash
                gate_e_validation_hash = str(gate_e_validation["validation_hash"])
                outer = verify_outer_envelope(
                    realized,
                    repo_root=repo_root,
                    lean_project_root=lean_project_root,
                )
            artifact_payloads: dict[str, object] = {
                # The existing immutable Phase 7 store verifier requires these
                # canonical filenames in every promoted package's evidence.
                "policy.json": policy.to_json(),
                "phase6_report.json": realized.phase6.report.to_json(),
                "challenge_commitment.json": challenge.commitment_json(),
                "proposal_enumeration.json": proposal.to_json(),
                "program.json": program.to_json(),
                "semantic_candidate.json": semantic.to_json(),
                "realization.json": realized.to_json(),
                "semantic_evaluation.json": evaluation.to_json(),
                "gate_e_attempt.json": gate_e_attempt.to_json(),
                "gate_e_binding.json": {
                    "report_hash": gate_e_report_hash,
                    "validation_hash": gate_e_validation_hash,
                },
            }
            if outer is not None:
                artifact_payloads["outer_verification.json"] = outer.to_json()
            artifact_hashes = {
                name: _write_json(attempt_root / "retained" / name, payload)
                for name, payload in sorted(
                    artifact_payloads.items(),
                    key=lambda item: item[0].encode("utf-8"),
                )
            }
            realization_record = realized.phase6.report.realization
            if realization_record is None:
                raise ValueError("Phase 14 realization record is absent")
            run_id = phase7_run_id(
                run_label=(
                    f"phase14-challenge-{challenge_index}-attempt-{local_attempt}"
                ),
                active_pointer_hash=snapshot.pointer.pointer_hash,
                policy_hash=policy.policy_hash,
                budget_hash=budget.budget_hash,
            )
            accepted = bool(evaluation.accepted and outer is not None and outer.accepted)
            phase7_attempt = Phase7AttemptReport(
                run_id=run_id,
                attempt_index=local_attempt,
                transition_id=realized.selection.transition_id,
                verdict="accept" if accepted else "reject",
                reason_codes=() if accepted else (Phase7ReasonCode.EVALUATION_FAILED,),
                controller_units_consumed=1,
                active_pointer_hash_before=snapshot.pointer.pointer_hash,
                active_pointer_hash_after=snapshot.pointer.pointer_hash,
                generator_input_hash=proposal.enumeration_hash,
                proposal_hash=program.program_hash,
                selection_hash=realized.selection.selection_hash,
                phase6_report_hash=realized.phase6.report.report_hash,
                candidate_package_tree_hash=directory_tree_hash(realized.candidate_root),
                evaluation_hash=evaluation.report_hash,
                certificate_hash=evaluation.gate_d_evidence_hash,
                lean_report_hash=None if outer is None else outer.lean_report_hash,
                checker_report_hash=None if outer is None else outer.checker_report_hash,
                fallback_rollback_verified=realization_record.rollback.verified,
                manual_repair_count=0,
                stages=_stages(
                    accepted=accepted,
                    proposal_hash=proposal.enumeration_hash,
                    selection_hash=realized.selection.selection_hash,
                    phase6_report_hash=realized.phase6.report.report_hash,
                    semantic_evaluation_hash=evaluation.report_hash,
                    gate_e_hash=gate_e_report_hash,
                    outer_hash=None if outer is None else outer.report_hash,
                    rollback_hash=realization_record.rollback.rollback_hash,
                    reason_codes=evaluation.reason_codes,
                ),
                artifact_hashes=FrozenHashMap.from_mapping(
                    artifact_hashes,
                    "phase14.attempt_artifact_hashes",
                ),
            )
            _write_json(attempt_root / "retained" / "attempt_report.json", phase7_attempt.to_json())
            if accepted:
                promotion = promote_phase7_candidate(
                    snapshot,
                    realized.candidate_root,
                    attempt_root / "retained",
                    phase7_attempt,
                    policy,
                )
                reopened = load_active_phase7_store(store_root, policy)
                if reopened.pointer != promotion.snapshot.pointer:
                    raise ValueError("Phase 14 promoted store pointer differs after reopen")
                active_store_hash_after = reopened.pointer.active_package_hash
                installed_semantic = _active_semantic_root(reopened)
                installed_manifest = load_package_manifest(installed_semantic)
                if installed_manifest.package_hash != semantic.manifest.package_hash:
                    raise ValueError("Phase 14 installed semantic package differs")
                ledger_hash = promotion.ledger_entry.entry_hash
                if evaluation.candidate_state is None:
                    raise ValueError("accepted Phase 14 attempt lacks candidate state")
                active_state = evaluation.candidate_state
                recursive_frontier = tuple(recursive_after)
                accepted_challenges.append(challenge)
                gate_e_hashes.append(gate_e_report_hash)
                gate_e_validation_hashes.append(gate_e_validation_hash)
                rejection_evidence_hash = None
            else:
                reopened, entry = append_phase7_nonpromotion(
                    snapshot,
                    phase7_attempt,
                    policy,
                    event="rejection",
                )
                active_store_hash_after = reopened.pointer.active_package_hash
                if active_store_hash_after != active_store_hash_before:
                    raise ValueError("Phase 14 rejection changed the active package")
                ledger_hash = entry.entry_hash
                rejection_evidence_hash = evaluation.report_hash
            store_attempt_staging = attempt_root / "store_attempt_staging"
            shutil.copytree(
                attempt_root / "retained",
                store_attempt_staging,
                symlinks=False,
            )
            publish_phase7_attempt_directory(
                store_root,
                run_id,
                local_attempt,
                store_attempt_staging,
            )
            history_entry = Phase14SearchHistoryEntry(
                sequence_number=len(history.entries),
                challenge_commitment_hash=challenge.commitment_hash,
                attempt_index=local_attempt,
                update_family=program.update_family,
                program_variant=program.variant,
                program_hash=program.program_hash,
                candidate_semantic_package_hash=semantic.manifest.package_hash,
                verdict="accept" if accepted else "reject",
                reason_codes=() if accepted else evaluation.reason_codes,
                active_package_hash_before=active_store_hash_before,
                active_package_hash_after=active_store_hash_after,
                rejection_evidence_hash=rejection_evidence_hash,
            )
            history = Phase14SearchHistory(entries=(*history.entries, history_entry))
            summary = Phase14AttemptSummary(
                global_attempt_index=global_attempt,
                challenge_index=challenge_index,
                challenge_commitment_hash=challenge.commitment_hash,
                local_attempt_index=local_attempt,
                update_family=program.update_family,
                program_variant=program.variant,
                program_hash=program.program_hash,
                proposal_enumeration_hash=proposal.enumeration_hash,
                candidate_semantic_package_hash=semantic.manifest.package_hash,
                candidate_phase6_tree_hash=directory_tree_hash(realized.candidate_root),
                verdict="accept" if accepted else "reject",
                reason_codes=() if accepted else evaluation.reason_codes,
                hidden_task_report_hash=evaluation.hidden_task_report.report_hash,
                gate_d_report_hash=evaluation.gate_d_evidence_hash,
                gate_e_report_hash=gate_e_report_hash,
                recursive_productivity_report_hash=(
                    evaluation.recursive_productivity_report.report_hash
                ),
                active_store_package_hash_before=active_store_hash_before,
                active_store_package_hash_after=active_store_hash_after,
                phase7_ledger_entry_hash=ledger_hash,
                rejection_conditioned=bool(local_attempt),
            )
            attempt_summaries.append(summary)
            _write_json(attempt_root / "attempt_summary.json", summary.to_json())
            global_attempt += 1
            if accepted:
                break
        else:
            raise ValueError(
                f"Phase 14 bounded search exhausted without promotion for {challenge.challenge_id}"
            )
    final_snapshot = load_active_phase7_store(store_root, policy)
    final_semantic_root = _active_semantic_root(final_snapshot)
    final_manifest = load_package_manifest(final_semantic_root)
    report = Phase14TrajectoryReport(
        source_head=source_head,
        source_tree=source_tree,
        phase13_exit_report_hash=PHASE13_EXIT_REPORT_HASH,
        phase13_bundle_manifest_hash=PHASE13_BUNDLE_MANIFEST_HASH,
        initial_store_package_hash=initial_store_hash,
        initial_m4_semantic_package_hash=initial_manifest.package_hash,
        final_store_package_hash=final_snapshot.pointer.active_package_hash,
        final_semantic_package_hash=final_manifest.package_hash,
        initial_capability_frontier=initial_frontier,
        final_capability_frontier=active_state.capability_frontier.task_ids,
        initial_recursive_productivity_frontier=initial_recursive,
        final_recursive_productivity_frontier=recursive_frontier,
        attempts=tuple(attempt_summaries),
        challenge_manifest_hash=str(challenge_manifest["manifest_hash"]),
        answer_store_hash=str(private_answer_store["answer_store_hash"]),
        challenge_count=len(challenge_values),
        challenge_gate_e_report_hashes=tuple(gate_e_hashes),
        challenge_gate_e_validation_hashes=tuple(gate_e_validation_hashes),
    )
    _write_json(work / "phase14_trajectory.json", report.to_json())
    _write_json(work / "search_history.json", history.to_json())
    _write_json(work / "challenge_manifest.json", challenge_manifest)
    _write_json(work / "answer_store_private.json", private_answer_store)
    if not report.campaign_closed:
        raise ValueError("Phase 14 trajectory did not satisfy the closure floor")
    return report


__all__ = [
    "Phase14TrajectoryReport",
    "phase14_budget",
    "run_phase14_trajectory",
]
