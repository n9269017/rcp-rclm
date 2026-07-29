from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_package import Phase7LedgerEntryRecord
from rcp_rclm_runtime.promotion.store_verifier import (
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.successor.package_builder import Phase6PackageBuildEvidence
from rcp_rclm_runtime.successor.records import (
    Phase6PackageReport,
    Phase6SelectionRecord,
)
from rcp_rclm_runtime.successor.workspace import load_predecessor_package
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_closure import phase12b_phase7_policy
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v4.gatee.records import AttemptRecord

from rcp_rclm_runtime_v4.phase14.bundle import verify_phase14_bundle
from rcp_rclm_runtime_v4.phase14.candidate import (
    Phase14SemanticCandidate,
    validate_semantic_candidate,
)
from rcp_rclm_runtime_v4.phase14.challenges import (
    HiddenChallenge,
    answer_store_json,
    challenge_manifest_json,
    challenges_from_answer_store,
)
from rcp_rclm_runtime_v4.phase14.evaluation import (
    build_gate_e_challenge_report,
    build_initial_m4_state,
    evaluate_semantic_candidate,
    initial_recursive_frontier,
)
from rcp_rclm_runtime_v4.phase14.outer import (
    directory_tree_hash,
    verify_outer_envelope,
)
from rcp_rclm_runtime_v4.phase14.realization import Phase14RealizedCandidate
from rcp_rclm_runtime_v4.phase14.records import (
    Phase14ProposalEnumeration,
    Phase14SearchHistory,
)
from rcp_rclm_runtime_v4.phase14.trajectory import Phase14TrajectoryReport


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical object")
    return value


def _forbidden_worker_modules() -> tuple[str, ...]:
    suffixes = (
        ".phase14.proposal_worker",
        "phase10_training_worker",
        "phase12e_training_worker",
    )
    return tuple(
        sorted(
            name
            for name in sys.modules
            if name.endswith(suffixes)
            or name == "torch"
            or name.startswith("torch.")
        )
    )


def _semantic_root(store_root: Path, store_package_hash: str) -> Path:
    root = (
        store_root
        / "packages"
        / store_package_hash
        / "predecessor"
        / "payload"
        / EMBEDDED_PHASE12_ROOT
    )
    load_package_manifest(root)
    return root


def _semantic_candidate(
    *,
    root: Path,
    active_root: Path,
    proposal: Phase14ProposalEnumeration,
    value: dict[str, object],
) -> Phase14SemanticCandidate:
    programs = tuple(
        item for item in proposal.programs if item.program_hash == value.get("program_hash")
    )
    if len(programs) != 1:
        raise SchemaValidationError(
            "phase14.replay.semantic_candidate.program_hash",
            "program binding is missing or ambiguous",
        )
    changed = value.get("changed_paths")
    if not isinstance(changed, list):
        raise SchemaValidationError(
            "phase14.replay.semantic_candidate.changed_paths",
            "expected array",
        )
    manifest = load_package_manifest(root)
    result = Phase14SemanticCandidate(
        root=root,
        active_semantic_package_hash=str(value["active_semantic_package_hash"]),
        manifest=manifest,
        program=programs[0],
        changed_paths=tuple(str(item) for item in changed),
        family_evidence_hash=str(value["family_evidence_hash"]),
    )
    if result.to_json() != value:
        raise SchemaValidationError(
            "phase14.replay.semantic_candidate",
            "retained semantic candidate record differs",
        )
    validate_semantic_candidate(active_root, result)
    return result


def _realized_candidate(
    *,
    attempt_root: Path,
    semantic: Phase14SemanticCandidate,
) -> Phase14RealizedCandidate:
    realization_root = attempt_root / "realization"
    candidate_root = realization_root / "candidate_package"
    wrapper_root = realization_root / "wrapper_predecessor"
    wrapper = load_predecessor_package(wrapper_root)
    selection = Phase6SelectionRecord.from_json(
        _object(
            candidate_root / "evidence/selection.json",
            "phase14.replay.selection",
        )
    )
    phase6 = Phase6PackageReport.from_json(
        _object(
            attempt_root / "retained/phase6_report.json",
            "phase14.replay.phase6_report",
        )
    )
    result = Phase14RealizedCandidate(
        semantic_candidate=semantic,
        wrapper_predecessor=wrapper,
        selection=selection,
        phase6=Phase6PackageBuildEvidence(
            report=phase6,
            output_root=candidate_root,
        ),
    )
    if not result.accepted:
        raise SchemaValidationError(
            "phase14.replay.realized_candidate",
            "retained Phase 6 candidate did not reopen",
        )
    retained = _object(
        attempt_root / "retained/realization.json",
        "phase14.replay.realization",
    )
    if result.to_json() != retained:
        raise SchemaValidationError(
            "phase14.replay.realization",
            "realization record differs",
        )
    return result


def _attempt_root(campaign_root: Path, challenge_index: int, local_index: int) -> Path:
    return (
        campaign_root
        / "evidence"
        / f"challenge-{challenge_index:02d}"
        / f"attempt-{local_index:02d}"
    ).resolve(strict=True)


def _verify_store(store_root: Path, final_hash: str) -> int:
    policy = phase12b_phase7_policy()
    snapshot = load_active_phase7_store(store_root, policy)
    if snapshot.pointer.active_package_hash != final_hash:
        raise SchemaValidationError(
            "phase14.replay.store",
            "final active package mismatch",
        )
    count = 0
    for package_root in sorted(
        (store_root / "packages").iterdir(),
        key=lambda item: item.name.encode("utf-8"),
    ):
        verify_immutable_phase7_package(package_root, policy)
        count += 1
    return count


@dataclass(frozen=True, slots=True)
class Phase14ReplayReport:
    source_head: str
    source_tree: str
    platform_id: str
    bundle_manifest_hash: str
    trajectory_report_hash: str
    final_store_package_hash: str
    final_semantic_package_hash: str
    history_count: int
    accepted_promotions: int
    rejected_attempts: int
    distinct_update_families: Sequence[str]
    task_replays: int
    gate_d_replays: int
    gate_e_replays: int
    outer_replays: int
    immutable_packages_verified: int
    pinned_lean: bool
    forbidden_worker_modules: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v4.phase14.replay_report.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.accepted_promotions >= 4
            and self.rejected_attempts >= 2
            and len(set(self.distinct_update_families)) >= 3
            and self.gate_d_replays == self.accepted_promotions
            and self.gate_e_replays == self.accepted_promotions
            and self.outer_replays == self.accepted_promotions
            and self.task_replays >= self.history_count
            and self.immutable_packages_verified >= 9
            and not self.forbidden_worker_modules
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "platform_id": self.platform_id,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "trajectory_report_hash": self.trajectory_report_hash,
            "final_store_package_hash": self.final_store_package_hash,
            "final_semantic_package_hash": self.final_semantic_package_hash,
            "history_count": self.history_count,
            "accepted_promotions": self.accepted_promotions,
            "rejected_attempts": self.rejected_attempts,
            "distinct_update_families": list(self.distinct_update_families),
            "task_replays": self.task_replays,
            "gate_d_replays": self.gate_d_replays,
            "gate_e_replays": self.gate_e_replays,
            "outer_replays": self.outer_replays,
            "immutable_packages_verified": self.immutable_packages_verified,
            "pinned_lean": self.pinned_lean,
            "training_invocations": 0,
            "proposal_worker_invocations": 0,
            "generator_invocations": 0,
            "planner_invocations": 0,
            "manual_repairs": 0,
            "forbidden_worker_modules": list(self.forbidden_worker_modules),
            "accepted": self.accepted,
            "gate_e_closed": False,
            "phase14_exit_closed": False,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase14ReplayReport:
        if not isinstance(value, dict):
            raise SchemaValidationError("phase14.replay", "expected object")
        raw_families = value.get("distinct_update_families")
        raw_forbidden = value.get("forbidden_worker_modules")
        if not isinstance(raw_families, list) or not isinstance(raw_forbidden, list):
            raise SchemaValidationError("phase14.replay", "expected array fields")
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            platform_id=str(value["platform_id"]),
            bundle_manifest_hash=str(value["bundle_manifest_hash"]),
            trajectory_report_hash=str(value["trajectory_report_hash"]),
            final_store_package_hash=str(value["final_store_package_hash"]),
            final_semantic_package_hash=str(
                value["final_semantic_package_hash"]
            ),
            history_count=int(value["history_count"]),
            accepted_promotions=int(value["accepted_promotions"]),
            rejected_attempts=int(value["rejected_attempts"]),
            distinct_update_families=tuple(str(item) for item in raw_families),
            task_replays=int(value["task_replays"]),
            gate_d_replays=int(value["gate_d_replays"]),
            gate_e_replays=int(value["gate_e_replays"]),
            outer_replays=int(value["outer_replays"]),
            immutable_packages_verified=int(value["immutable_packages_verified"]),
            pinned_lean=bool(value["pinned_lean"]),
            forbidden_worker_modules=tuple(str(item) for item in raw_forbidden),
        )
        if value.get("report_hash") != result.report_hash:
            raise SchemaValidationError(
                "phase14.replay.report_hash",
                "content hash mismatch",
            )
        if value.get("accepted") is not result.accepted:
            raise SchemaValidationError(
                "phase14.replay.accepted",
                "derived flag mismatch",
            )
        if value.get("phase14_exit_closed") is not False:
            raise SchemaValidationError(
                "phase14.replay.phase14_exit_closed",
                "only the final aggregator may close Phase 14",
            )
        return result


def replay_phase14_bundle(
    *,
    bundle_root: Path,
    repo_root: Path,
    lean_project_root: Path | None,
    source_head: str,
    platform_id: str,
) -> Phase14ReplayReport:
    manifest = verify_phase14_bundle(bundle_root)
    if manifest.source_head != source_head:
        raise SchemaValidationError(
            "phase14.replay.source_head",
            "requested source head differs from bundle",
        )
    campaign = bundle_root.resolve(strict=True) / "campaign"
    trajectory = Phase14TrajectoryReport.from_json(
        _object(
            campaign / "phase14_trajectory.json",
            "phase14.replay.trajectory",
        )
    )
    history = Phase14SearchHistory.from_json(
        _object(campaign / "search_history.json", "phase14.replay.history")
    )
    answer_store = _object(
        campaign / "answer_store_private.json",
        "phase14.replay.answer_store",
    )
    challenges = challenges_from_answer_store(answer_store)
    if answer_store_json(challenges) != answer_store:
        raise SchemaValidationError(
            "phase14.replay.answer_store",
            "private answer store does not round trip",
        )
    challenge_manifest = _object(
        campaign / "challenge_manifest.json",
        "phase14.replay.challenge_manifest",
    )
    if challenge_manifest_json(challenges) != challenge_manifest:
        raise SchemaValidationError(
            "phase14.replay.challenge_manifest",
            "commitment manifest does not match retained private challenges",
        )
    if trajectory.answer_store_hash != answer_store["answer_store_hash"]:
        raise SchemaValidationError(
            "phase14.replay.answer_store_hash",
            "trajectory answer-store binding mismatch",
        )
    if trajectory.challenge_manifest_hash != challenge_manifest["manifest_hash"]:
        raise SchemaValidationError(
            "phase14.replay.challenge_manifest_hash",
            "trajectory challenge-manifest binding mismatch",
        )
    if len(history.entries) != len(trajectory.attempts):
        raise SchemaValidationError(
            "phase14.replay.history",
            "history and trajectory attempt counts differ",
        )
    store_root = campaign / "store"
    immutable_count = _verify_store(
        store_root,
        trajectory.final_store_package_hash,
    )
    active_root = _semantic_root(
        store_root,
        trajectory.initial_store_package_hash,
    )
    active_state, base_reports = build_initial_m4_state(
        active_root,
        lean_project_root=lean_project_root,
    )
    task_replays = len(base_reports)
    recursive_frontier = initial_recursive_frontier()
    accepted_challenges: list[HiddenChallenge] = []
    history_prefix = Phase14SearchHistory(entries=())
    challenge_attempts: dict[int, list[AttemptRecord]] = {}
    gate_d_replays = 0
    gate_e_replays = 0
    outer_replays = 0
    for summary, expected_history in zip(
        trajectory.attempts,
        history.entries,
        strict=True,
    ):
        if expected_history.sequence_number != summary.global_attempt_index:
            raise SchemaValidationError(
                "phase14.replay.history",
                "history order differs from attempt order",
            )
        challenge = challenges[summary.challenge_index]
        attempt_root = _attempt_root(
            campaign,
            summary.challenge_index,
            summary.local_attempt_index,
        )
        proposal = Phase14ProposalEnumeration.from_json(
            _object(
                attempt_root / "retained/proposal_enumeration.json",
                "phase14.replay.proposal",
            )
        )
        if proposal.enumeration_hash != summary.proposal_enumeration_hash:
            raise SchemaValidationError(
                "phase14.replay.proposal",
                "proposal enumeration hash mismatch",
            )
        program_value = _object(
            attempt_root / "retained/program.json",
            "phase14.replay.program",
        )
        program = next(
            (
                item
                for item in proposal.programs
                if item.program_hash == summary.program_hash
            ),
            None,
        )
        if program is None or program.to_json() != program_value:
            raise SchemaValidationError(
                "phase14.replay.program",
                "selected program differs",
            )
        semantic_root = attempt_root / "semantic_candidate"
        semantic = _semantic_candidate(
            root=semantic_root,
            active_root=active_root,
            proposal=proposal,
            value=_object(
                attempt_root / "retained/semantic_candidate.json",
                "phase14.replay.semantic_candidate",
            ),
        )
        if semantic.manifest.package_hash != summary.candidate_semantic_package_hash:
            raise SchemaValidationError(
                "phase14.replay.semantic_candidate",
                "candidate semantic package hash mismatch",
            )
        realized = _realized_candidate(
            attempt_root=attempt_root,
            semantic=semantic,
        )
        if directory_tree_hash(realized.candidate_root) != summary.candidate_phase6_tree_hash:
            raise SchemaValidationError(
                "phase14.replay.realized_candidate",
                "candidate package tree hash mismatch",
            )
        evaluation = evaluate_semantic_candidate(
            active_root,
            semantic,
            active_state,
            tuple(accepted_challenges),
            challenge,
            proposal,
            history_prefix,
            recursive_frontier,
            lean_project_root=lean_project_root,
            generation=5 + summary.challenge_index,
            hidden_challenges=challenges,
        )
        retained_evaluation = _object(
            attempt_root / "retained/semantic_evaluation.json",
            "phase14.replay.semantic_evaluation",
        )
        if evaluation.to_json() != retained_evaluation:
            raise SchemaValidationError(
                "phase14.replay.semantic_evaluation",
                "independent semantic evaluation differs",
            )
        task_replays += len(evaluation.protected_reports) + 1
        if evaluation.hidden_task_report.report_hash != summary.hidden_task_report_hash:
            raise SchemaValidationError(
                "phase14.replay.hidden_task",
                "hidden task report hash mismatch",
            )
        if evaluation.gate_d_evidence_hash != summary.gate_d_report_hash:
            raise SchemaValidationError(
                "phase14.replay.gate_d",
                "Gate D evidence hash mismatch",
            )
        gate_e_attempt = AttemptRecord(
            attempt_index=summary.local_attempt_index,
            objective_id=program.objective_id,
            update_kinds=program.update_kinds,
            program_hash=program.program_hash,
            candidate_hash=semantic.manifest.package_hash,
            gate_d_certificate_hash=evaluation.gate_d_evidence_hash,
            package_generated=True,
            evaluator_accepted=evaluation.accepted,
            reason_codes=evaluation.reason_codes,
            capability_frontier_after=(
                active_state.capability_frontier.task_ids
                if evaluation.candidate_state is None
                else evaluation.candidate_state.capability_frontier.task_ids
            ),
            recursive_productivity_frontier_after=(
                evaluation.recursive_productivity_report.candidate_frontier
            ),
            search_cost=program.search_cost,
        )
        challenge_attempts.setdefault(summary.challenge_index, []).append(
            gate_e_attempt
        )
        if evaluation.accepted:
            if summary.verdict != "accept":
                raise SchemaValidationError(
                    "phase14.replay.verdict",
                    "accepted evaluation was recorded as rejection",
                )
            gate_d_replays += 1
            gate_e_report, gate_e_validation = build_gate_e_challenge_report(
                active_state,
                recursive_frontier,
                challenge.commitment_hash,
                tuple(challenge_attempts[summary.challenge_index]),
            )
            retained_binding = _object(
                attempt_root / "retained/gate_e_binding.json",
                "phase14.replay.gate_e_binding",
            )
            if retained_binding != {
                "report_hash": gate_e_report.report_hash,
                "validation_hash": gate_e_validation["validation_hash"],
            }:
                raise SchemaValidationError(
                    "phase14.replay.gate_e",
                    "Gate E report binding differs",
                )
            if gate_e_report.report_hash != summary.gate_e_report_hash:
                raise SchemaValidationError(
                    "phase14.replay.gate_e",
                    "Gate E report hash mismatch",
                )
            gate_e_replays += 1
            outer = verify_outer_envelope(
                realized,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
            )
            retained_outer = _object(
                attempt_root / "retained/outer_verification.json",
                "phase14.replay.outer_verification",
            )
            if outer.to_json() != retained_outer:
                raise SchemaValidationError(
                    "phase14.replay.outer_verification",
                    "outer verification differs",
                )
            outer_replays += 1
            if evaluation.candidate_state is None:
                raise SchemaValidationError(
                    "phase14.replay.candidate_state",
                    "accepted evaluation lacks candidate state",
                )
            active_state = evaluation.candidate_state
            recursive_frontier = tuple(
                evaluation.recursive_productivity_report.candidate_frontier
            )
            accepted_challenges.append(challenge)
            active_root = _semantic_root(
                store_root,
                summary.active_store_package_hash_after,
            )
        else:
            if summary.verdict != "reject":
                raise SchemaValidationError(
                    "phase14.replay.verdict",
                    "rejected evaluation was recorded as acceptance",
                )
            if summary.active_store_package_hash_before != summary.active_store_package_hash_after:
                raise SchemaValidationError(
                    "phase14.replay.rejection",
                    "rejection changed the active package",
                )
        attempt_report = Phase7AttemptReport.from_json(
            _object(
                attempt_root / "retained/attempt_report.json",
                "phase14.replay.phase7_attempt",
            )
        )
        if attempt_report.verdict != summary.verdict:
            raise SchemaValidationError(
                "phase14.replay.phase7_attempt",
                "Phase 7 attempt verdict mismatch",
            )
        ledger = Phase7LedgerEntryRecord.from_json(
            _object(
                store_root
                / "ledger"
                / f"{summary.phase7_ledger_entry_hash}.json",
                "phase14.replay.ledger",
            )
        )
        if ledger.attempt_report_hash != attempt_report.report_hash:
            raise SchemaValidationError(
                "phase14.replay.ledger",
                "ledger attempt binding mismatch",
            )
        if expected_history.program_hash != program.program_hash:
            raise SchemaValidationError(
                "phase14.replay.history",
                "history program binding mismatch",
            )
        history_prefix = Phase14SearchHistory(
            entries=(*history_prefix.entries, expected_history)
        )
    if history_prefix.to_json() != history.to_json():
        raise SchemaValidationError(
            "phase14.replay.history",
            "reconstructed search history differs",
        )
    if active_state.capability_frontier.task_ids != tuple(trajectory.final_capability_frontier):
        raise SchemaValidationError(
            "phase14.replay.frontier",
            "final capability frontier differs",
        )
    if tuple(recursive_frontier) != tuple(trajectory.final_recursive_productivity_frontier):
        raise SchemaValidationError(
            "phase14.replay.recursive_frontier",
            "final recursive-productivity frontier differs",
        )
    final_semantic_hash = load_package_manifest(active_root).package_hash
    if final_semantic_hash != trajectory.final_semantic_package_hash:
        raise SchemaValidationError(
            "phase14.replay.final_semantic_package_hash",
            "final semantic package differs",
        )
    forbidden = _forbidden_worker_modules()
    report = Phase14ReplayReport(
        source_head=trajectory.source_head,
        source_tree=trajectory.source_tree,
        platform_id=platform_id,
        bundle_manifest_hash=manifest.manifest_hash,
        trajectory_report_hash=trajectory.report_hash,
        final_store_package_hash=trajectory.final_store_package_hash,
        final_semantic_package_hash=final_semantic_hash,
        history_count=len(history.entries),
        accepted_promotions=trajectory.accepted_promotions,
        rejected_attempts=trajectory.rejected_attempts,
        distinct_update_families=trajectory.substantive_update_families,
        task_replays=task_replays,
        gate_d_replays=gate_d_replays,
        gate_e_replays=gate_e_replays,
        outer_replays=outer_replays,
        immutable_packages_verified=immutable_count,
        pinned_lean=lean_project_root is not None,
        forbidden_worker_modules=forbidden,
    )
    if not report.accepted:
        raise SchemaValidationError(
            "phase14.replay",
            "worker-free replay predicates failed",
        )
    return report


__all__ = ["Phase14ReplayReport", "replay_phase14_bundle"]
