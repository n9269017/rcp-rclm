from __future__ import annotations

import copy
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
from rcp_rclm_runtime.successor.records import Phase6PackageReport, Phase6SelectionRecord
from rcp_rclm_runtime.successor.workspace import load_predecessor_package
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_closure import phase12b_phase7_policy
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v4.gatee.records import AttemptRecord, AutonomousSearchReport, FrontierSnapshot, RouteHintPolicy
from rcp_rclm_runtime_v4.gatee.validation import validate_report

from rcp_rclm_runtime_v4.phase15.bundle import verify_phase15_bundle
from rcp_rclm_runtime_v4.phase15.candidate import load_phase15_candidate
from rcp_rclm_runtime_v4.phase15.challenges import (
    answer_store_json,
    challenge_manifest_json,
    challenges_from_answer_store,
)
from rcp_rclm_runtime_v4.phase15.constants import PHASE15_OBJECTIVE_ID, PHASE15_UPDATE_KIND_BY_TARGET
from rcp_rclm_runtime_v4.phase15.evaluation import build_initial_m8_state, evaluate_phase15_candidate
from rcp_rclm_runtime_v4.phase15.outer import directory_tree_hash, verify_outer_envelope
from rcp_rclm_runtime_v4.phase15.realization import Phase15RealizedCandidate
from rcp_rclm_runtime_v4.phase15.trajectory import Phase15TrajectoryReport


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical object")
    return value


def _semantic_root(store_root: Path, package_hash: str) -> Path:
    root = store_root / "packages" / package_hash / "predecessor/payload" / EMBEDDED_PHASE12_ROOT
    load_package_manifest(root)
    return root


def _forbidden_worker_modules() -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in sys.modules
            if name.endswith(".phase15.training_worker")
            or name == "torch"
            or name.startswith("torch.")
        )
    )



def _evaluation_semantic_projection(
    value: dict[str, object],
) -> dict[str, object]:
    """Remove only the explicit Lean-pin execution bit."""
    normalized = copy.deepcopy(value)
    for field in (
        "predecessor_dynamic_reports",
        "candidate_dynamic_reports",
    ):
        reports = normalized.get(field)
        if not isinstance(reports, list):
            raise SchemaValidationError(
                f"phase15.replay.{field}",
                "expected dynamic-report array",
            )
        for report in reports:
            if not isinstance(report, dict):
                raise SchemaValidationError(
                    f"phase15.replay.{field}",
                    "expected dynamic-report object",
                )
            if "pinned_lean" not in report:
                raise SchemaValidationError(
                    f"phase15.replay.{field}",
                    "pinned-Lean field absent",
                )
            report.pop("pinned_lean")
    return normalized


def _outer_semantic_projection(
    value: dict[str, object],
) -> dict[str, object]:
    """Remove only pin-dependent compiler/checker evidence."""
    normalized = copy.deepcopy(value)
    for field in (
        "lean_report_hash",
        "checker_report_hash",
        "lean_invoked",
        "checker_invoked",
    ):
        if field not in normalized:
            raise SchemaValidationError(
                "phase15.replay.outer_verification",
                f"required pin-dependent field absent: {field}",
            )
        normalized.pop(field)
    return normalized

def _verify_store(store_root: Path, final_hash: str) -> int:
    policy = phase12b_phase7_policy()
    snapshot = load_active_phase7_store(store_root, policy)
    if snapshot.pointer.active_package_hash != final_hash:
        raise SchemaValidationError("phase15.replay.store", "final active package mismatch")
    count = 0
    for package_root in sorted((store_root / "packages").iterdir(), key=lambda item: item.name.encode("utf-8")):
        verify_immutable_phase7_package(package_root, policy)
        count += 1
    return count


def _realized(attempt_root: Path, semantic) -> Phase15RealizedCandidate:
    realization_root = attempt_root / "realization"
    candidate_root = realization_root / "candidate_package"
    wrapper = load_predecessor_package(realization_root / "wrapper_predecessor")
    selection = Phase6SelectionRecord.from_json(
        _object(candidate_root / "evidence/selection.json", "phase15.replay.selection")
    )
    phase6_report = Phase6PackageReport.from_json(
        _object(attempt_root / "retained/phase6_report.json", "phase15.replay.phase6_report")
    )
    result = Phase15RealizedCandidate(
        semantic_candidate=semantic,
        wrapper_predecessor=wrapper,
        selection=selection,
        phase6=Phase6PackageBuildEvidence(report=phase6_report, output_root=candidate_root),
    )
    if not result.accepted:
        raise SchemaValidationError("phase15.replay.realization", "retained realization did not reopen")
    if result.to_json() != _object(attempt_root / "retained/realization.json", "phase15.replay.realization_record"):
        raise SchemaValidationError("phase15.replay.realization", "retained realization differs")
    return result


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
        raise SchemaValidationError("phase15.replay.gate_e", "accepted attempt absent")
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


@dataclass(frozen=True, slots=True)
class Phase15ReplayReport:
    source_head: str
    source_tree: str
    platform_id: str
    bundle_manifest_hash: str
    trajectory_report_hash: str
    final_store_package_hash: str
    final_m9_semantic_package_hash: str
    immutable_packages_verified: int
    protected_task_replays: int
    dynamic_task_replays: int
    gate_d_replays: int
    gate_e_replays: int
    outer_replays: int
    accepted_promotions: int
    rejected_attempts: int
    pinned_lean: bool
    forbidden_worker_modules: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v4.phase15.replay_report.v1"

    @property
    def semantic_replay_accepted(self) -> bool:
        return (
            self.immutable_packages_verified >= 10
            and self.protected_task_replays == 22
            and self.dynamic_task_replays == 4
            and self.gate_d_replays == 1
            and self.gate_e_replays == 1
            and self.outer_replays == 1
            and self.accepted_promotions == 1
            and self.rejected_attempts == 1
            and not self.forbidden_worker_modules
        )

    @property
    def accepted(self) -> bool:
        return self.semantic_replay_accepted and self.pinned_lean

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
            "final_m9_semantic_package_hash": self.final_m9_semantic_package_hash,
            "immutable_packages_verified": self.immutable_packages_verified,
            "protected_task_replays": self.protected_task_replays,
            "dynamic_task_replays": self.dynamic_task_replays,
            "gate_d_replays": self.gate_d_replays,
            "gate_e_replays": self.gate_e_replays,
            "outer_replays": self.outer_replays,
            "accepted_promotions": self.accepted_promotions,
            "rejected_attempts": self.rejected_attempts,
            "pinned_lean": self.pinned_lean,
            "training_invocations": 0,
            "candidate_builder_invocations": 0,
            "proposal_worker_invocations": 0,
            "generator_invocations": 0,
            "planner_invocations": 0,
            "manual_repairs": 0,
            "forbidden_worker_modules": list(self.forbidden_worker_modules),
            "semantic_replay_accepted": self.semantic_replay_accepted,
            "accepted": self.accepted,
            "phase15_exit_closed": False,
            "gate_e_closed": False,
        }

    def to_json(self) -> dict[str, object]:
        result = self.content_json()
        result["report_hash"] = self.report_hash
        return result

    @classmethod
    def from_json(cls, value: object) -> "Phase15ReplayReport":
        if not isinstance(value, dict):
            raise SchemaValidationError("phase15.replay", "expected object")
        forbidden = value.get("forbidden_worker_modules")
        if not isinstance(forbidden, list):
            raise SchemaValidationError("phase15.replay.forbidden_worker_modules", "expected array")
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            platform_id=str(value["platform_id"]),
            bundle_manifest_hash=str(value["bundle_manifest_hash"]),
            trajectory_report_hash=str(value["trajectory_report_hash"]),
            final_store_package_hash=str(value["final_store_package_hash"]),
            final_m9_semantic_package_hash=str(value["final_m9_semantic_package_hash"]),
            immutable_packages_verified=int(value["immutable_packages_verified"]),
            protected_task_replays=int(value["protected_task_replays"]),
            dynamic_task_replays=int(value["dynamic_task_replays"]),
            gate_d_replays=int(value["gate_d_replays"]),
            gate_e_replays=int(value["gate_e_replays"]),
            outer_replays=int(value["outer_replays"]),
            accepted_promotions=int(value["accepted_promotions"]),
            rejected_attempts=int(value["rejected_attempts"]),
            pinned_lean=bool(value["pinned_lean"]),
            forbidden_worker_modules=tuple(str(item) for item in forbidden),
        )
        if value.get("report_hash") != result.report_hash:
            raise SchemaValidationError("phase15.replay.report_hash", "hash mismatch")
        if value.get("accepted") is not result.accepted:
            raise SchemaValidationError("phase15.replay.accepted", "derived flag mismatch")
        return result


def replay_phase15_bundle(
    *,
    bundle_root: Path,
    repo_root: Path,
    lean_project_root: Path | None,
    source_head: str,
    platform_id: str,
) -> Phase15ReplayReport:
    manifest = verify_phase15_bundle(bundle_root)
    if manifest.source_head != source_head:
        raise SchemaValidationError("phase15.replay.source_head", "requested source head differs")
    campaign = bundle_root.resolve(strict=True) / "campaign"
    trajectory = Phase15TrajectoryReport.from_json(
        _object(campaign / "phase15_trajectory.json", "phase15.replay.trajectory")
    )
    challenge_manifest = _object(
        campaign / "challenge_manifest.json",
        "phase15.replay.challenge_manifest",
    )
    answer_store = _object(
        campaign / "answer_store_private.json",
        "phase15.replay.answer_store",
    )
    challenges = challenges_from_answer_store(answer_store)
    raw_freezes = challenge_manifest.get("candidate_freeze_hashes")
    if not isinstance(raw_freezes, list):
        raise SchemaValidationError("phase15.replay.challenge_manifest", "freeze hashes must be an array")
    freeze_hashes = tuple(str(item) for item in raw_freezes)
    if challenge_manifest_json(challenges, candidate_freeze_hashes=freeze_hashes) != challenge_manifest:
        raise SchemaValidationError("phase15.replay.challenge_manifest", "challenge manifest differs")
    if answer_store_json(challenges) != answer_store:
        raise SchemaValidationError("phase15.replay.answer_store", "answer store differs")
    if trajectory.challenge_manifest_hash != challenge_manifest["manifest_hash"]:
        raise SchemaValidationError("phase15.replay.challenge_manifest", "trajectory binding mismatch")
    if trajectory.answer_store_hash != answer_store["answer_store_hash"]:
        raise SchemaValidationError("phase15.replay.answer_store", "trajectory binding mismatch")
    store_root = campaign / "store"
    immutable_count = _verify_store(store_root, trajectory.final_store_package_hash)
    initial_root = _semantic_root(store_root, trajectory.initial_store_package_hash)
    phase14_reference = campaign / "phase14_reference"
    predecessor_state, initial_reports = build_initial_m8_state(
        initial_root,
        phase14_reference,
        lean_project_root=lean_project_root,
    )
    phase14_trajectory = _object(
        phase14_reference / "campaign/phase14_trajectory.json",
        "phase15.replay.phase14_trajectory",
    )
    raw_recursive = phase14_trajectory.get("final_recursive_productivity_frontier")
    if not isinstance(raw_recursive, list):
        raise SchemaValidationError("phase15.replay.phase14_recursive_frontier", "expected array")
    recursive_frontier = tuple(str(item) for item in raw_recursive)
    gate_e_attempts: list[AttemptRecord] = []
    protected_replays = 0
    dynamic_replays = 0
    gate_d_replays = 0
    gate_e_replays = 0
    outer_replays = 0
    final_state = predecessor_state
    final_recursive = recursive_frontier
    final_root = initial_root
    update_kinds = tuple(
        sorted(set(PHASE15_UPDATE_KIND_BY_TARGET.values()), key=lambda item: item.encode("utf-8"))
    )
    for summary in trajectory.attempts:
        attempt_root = (
            campaign
            / "evidence"
            / f"attempt-{summary.attempt_index:02d}-{summary.variant}"
        ).resolve(strict=True)
        retained_candidate = _object(
            attempt_root / "retained/semantic_candidate.json",
            "phase15.replay.semantic_candidate",
        )
        frozen_root = campaign / "candidate_freeze" / summary.variant
        candidate = load_phase15_candidate(
            active_semantic_root=initial_root,
            candidate_root=frozen_root / "semantic_candidate",
            training_root=frozen_root / "training",
            retained_value=retained_candidate,
        )
        if candidate.freeze_hash != summary.candidate_freeze_hash:
            raise SchemaValidationError("phase15.replay.candidate_freeze", "freeze hash mismatch")
        if candidate.manifest.package_hash != summary.candidate_semantic_package_hash:
            raise SchemaValidationError("phase15.replay.candidate", "semantic package hash mismatch")
        realized = _realized(attempt_root, candidate)
        if directory_tree_hash(realized.candidate_root) != summary.candidate_phase6_tree_hash:
            raise SchemaValidationError("phase15.replay.realization", "candidate tree hash mismatch")
        evaluation = evaluate_phase15_candidate(
            initial_root,
            candidate,
            phase14_reference,
            challenges,
            predecessor_state,
            recursive_frontier,
            lean_project_root=lean_project_root,
            challenge_manifest_hash=trajectory.challenge_manifest_hash,
            answer_store_hash=trajectory.answer_store_hash,
        )
        retained_evaluation = _object(
            attempt_root / "retained/semantic_evaluation.json",
            "phase15.replay.semantic_evaluation",
        )
        evaluation_json = evaluation.to_json()
        if lean_project_root is None:
            if (
                _evaluation_semantic_projection(evaluation_json)
                != _evaluation_semantic_projection(retained_evaluation)
            ):
                raise SchemaValidationError(
                    "phase15.replay.semantic_evaluation",
                    "independent semantic evaluation differs",
                )
        elif evaluation_json != retained_evaluation:
            raise SchemaValidationError(
                "phase15.replay.semantic_evaluation",
                "independent pinned evaluation differs",
            )
        retained_evaluation_hash = canonical_json_hash(
            retained_evaluation
        )
        protected_replays += len(evaluation.protected_reports)
        dynamic_replays += len(evaluation.candidate_dynamic_reports)
        gate_d_evidence_hash = canonical_json_hash(
            {
                "evaluation_hash": retained_evaluation_hash,
                "certificate_hash": None if evaluation.certificate is None else evaluation.certificate.certificate_hash,
                "gate_d_report_hash": None if evaluation.gate_d_report is None else evaluation.gate_d_report.semantic_report_hash,
            }
        )
        if gate_d_evidence_hash != summary.gate_d_report_hash:
            raise SchemaValidationError("phase15.replay.gate_d", "Gate D evidence differs")
        gate_e_attempt = AttemptRecord(
            attempt_index=summary.attempt_index,
            objective_id=PHASE15_OBJECTIVE_ID,
            update_kinds=update_kinds,
            program_hash=candidate.training.result_hash,
            candidate_hash=candidate.manifest.package_hash,
            gate_d_certificate_hash=gate_d_evidence_hash,
            package_generated=True,
            evaluator_accepted=evaluation.accepted,
            reason_codes=evaluation.reason_codes,
            capability_frontier_after=(
                predecessor_state.capability_frontier.task_ids
                if evaluation.candidate_state is None
                else evaluation.candidate_state.capability_frontier.task_ids
            ),
            recursive_productivity_frontier_after=(
                evaluation.recursive_productivity_report.candidate_frontier
            ),
            search_cost=1,
        )
        gate_e_attempts.append(gate_e_attempt)
        retained_binding = _object(
            attempt_root / "retained/gate_e_binding.json",
            "phase15.replay.gate_e_binding",
        )
        if evaluation.accepted:
            if summary.verdict != "accept":
                raise SchemaValidationError("phase15.replay.verdict", "accepted evaluation recorded as rejection")
            gate_d_replays += 1
            gate_e, gate_e_validation = _gate_e_report(
                source_state_hash=predecessor_state.state_hash,
                challenge_manifest_hash=trajectory.challenge_manifest_hash,
                capability_frontier=predecessor_state.capability_frontier.task_ids,
                recursive_frontier=recursive_frontier,
                attempts=tuple(gate_e_attempts),
            )
            expected_binding = {
                "report_hash": gate_e.report_hash,
                "validation_hash": gate_e_validation["validation_hash"],
            }
            if retained_binding != expected_binding:
                raise SchemaValidationError("phase15.replay.gate_e", "Gate E binding differs")
            if gate_e.report_hash != trajectory.gate_e_report_hash:
                raise SchemaValidationError("phase15.replay.gate_e", "trajectory Gate E hash differs")
            gate_e_replays += 1
            outer = verify_outer_envelope(
                realized,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
            )
            retained_outer = _object(
                attempt_root / "retained/outer_verification.json",
                "phase15.replay.outer_verification",
            )
            outer_json = outer.to_json()
            if lean_project_root is None:
                if (
                    _outer_semantic_projection(outer_json)
                    != _outer_semantic_projection(retained_outer)
                ):
                    raise SchemaValidationError(
                        "phase15.replay.outer_verification",
                        "outer semantic evidence differs",
                    )
            elif outer_json != retained_outer:
                raise SchemaValidationError(
                    "phase15.replay.outer_verification",
                    "outer pinned evidence differs",
                )
            if (
                canonical_json_hash(retained_outer)
                != summary.outer_verification_hash
            ):
                raise SchemaValidationError(
                    "phase15.replay.outer_verification",
                    "retained outer hash differs",
                )
            outer_replays += 1
            if evaluation.candidate_state is None:
                raise SchemaValidationError("phase15.replay.candidate_state", "candidate state absent")
            final_state = evaluation.candidate_state
            final_recursive = tuple(evaluation.recursive_productivity_report.candidate_frontier)
            final_root = _semantic_root(store_root, summary.active_store_package_hash_after)
        else:
            if summary.verdict != "reject":
                raise SchemaValidationError("phase15.replay.verdict", "rejected evaluation recorded as acceptance")
            expected_pending = canonical_json_hash(
                {
                    "pending_attempt_hashes": [item.attempt_hash for item in gate_e_attempts],
                    "challenge_manifest_hash": trajectory.challenge_manifest_hash,
                    "accepted": False,
                }
            )
            if retained_binding != {"report_hash": expected_pending, "validation_hash": expected_pending}:
                raise SchemaValidationError("phase15.replay.gate_e", "pending Gate E binding differs")
            if summary.active_store_package_hash_before != summary.active_store_package_hash_after:
                raise SchemaValidationError("phase15.replay.rejection", "rejection changed active store")
        attempt_report = Phase7AttemptReport.from_json(
            _object(attempt_root / "retained/attempt_report.json", "phase15.replay.phase7_attempt")
        )
        if attempt_report.verdict != summary.verdict:
            raise SchemaValidationError("phase15.replay.phase7_attempt", "verdict mismatch")
        ledger = Phase7LedgerEntryRecord.from_json(
            _object(
                store_root / "ledger" / f"{summary.phase7_ledger_entry_hash}.json",
                "phase15.replay.ledger",
            )
        )
        if ledger.attempt_report_hash != attempt_report.report_hash:
            raise SchemaValidationError("phase15.replay.ledger", "attempt binding mismatch")
    if final_state.capability_frontier.task_ids != tuple(trajectory.final_capability_frontier):
        raise SchemaValidationError("phase15.replay.frontier", "final capability frontier differs")
    if tuple(final_recursive) != tuple(trajectory.final_recursive_productivity_frontier):
        raise SchemaValidationError("phase15.replay.recursive_frontier", "final recursive frontier differs")
    final_semantic_hash = load_package_manifest(final_root).package_hash
    if final_semantic_hash != trajectory.final_m9_semantic_package_hash:
        raise SchemaValidationError("phase15.replay.final_semantic_package", "final semantic package differs")
    report = Phase15ReplayReport(
        source_head=trajectory.source_head,
        source_tree=trajectory.source_tree,
        platform_id=platform_id,
        bundle_manifest_hash=manifest.manifest_hash,
        trajectory_report_hash=trajectory.report_hash,
        final_store_package_hash=trajectory.final_store_package_hash,
        final_m9_semantic_package_hash=final_semantic_hash,
        immutable_packages_verified=immutable_count,
        protected_task_replays=protected_replays,
        dynamic_task_replays=dynamic_replays,
        gate_d_replays=gate_d_replays,
        gate_e_replays=gate_e_replays,
        outer_replays=outer_replays,
        accepted_promotions=trajectory.accepted_promotions,
        rejected_attempts=trajectory.rejected_attempts,
        pinned_lean=lean_project_root is not None,
        forbidden_worker_modules=_forbidden_worker_modules(),
    )
    return report


__all__ = ["Phase15ReplayReport", "replay_phase15_bundle"]
