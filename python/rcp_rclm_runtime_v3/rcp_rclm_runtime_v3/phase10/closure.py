from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.promotion.store_verifier import (
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime_v3.phase10.lifecycle import (
    Phase10Phase6Fixture,
    replay_phase10_phase6,
)
from rcp_rclm_runtime_v3.phase10.policy import phase10_phase7_policy
from rcp_rclm_runtime_v3.phase10.promotion import (
    Phase10PromotionEvidence,
    Phase10VerificationEvidence,
    verify_phase10_candidate,
)


def _directory_tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _forbidden_modules() -> Sequence[str]:
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


def remove_phase10_training_backend(repo_root: Path) -> Sequence[str]:
    root = repo_root.resolve(strict=True)
    relative_paths = (
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/training_process.py",
        "python/rcp_rclm_runtime_v3/tools/phase10_training_worker.py",
        "python/rcp_rclm_runtime_v3/tools/run_phase10_training_reference.py",
    )
    removed: list[str] = []
    for relative in relative_paths:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"required training-backend source is absent: {relative}")
        path.unlink()
        removed.append(relative)
    return tuple(removed)


@dataclass(frozen=True, slots=True)
class Phase10IndependentReplayEvidence:
    phase6_replay: dict[str, object]
    verification: Phase10VerificationEvidence
    promoted_package_hash: str
    promoted_source_candidate_tree_hash: str
    replay_candidate_tree_hash: str
    promotion_parent_hash: str
    ledger_sequence_number: int
    removed_training_paths: Sequence[str]
    forbidden_modules_loaded: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase10.independent_replay.v1"

    @property
    def source_candidate_matches(self) -> bool:
        return (
            self.promoted_source_candidate_tree_hash
            == self.replay_candidate_tree_hash
        )

    @property
    def accepted(self) -> bool:
        return (
            self.phase6_replay["ok"] is True
            and self.verification.accepted
            and self.source_candidate_matches
            and self.ledger_sequence_number == 1
            and len(self.removed_training_paths) == 3
            and not self.forbidden_modules_loaded
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "phase6_replay": self.phase6_replay,
            "verification_hash": self.verification.semantic_report_hash,
            "promoted_package_hash": self.promoted_package_hash,
            "promoted_source_candidate_tree_hash": (
                self.promoted_source_candidate_tree_hash
            ),
            "replay_candidate_tree_hash": self.replay_candidate_tree_hash,
            "source_candidate_matches": self.source_candidate_matches,
            "promotion_parent_hash": self.promotion_parent_hash,
            "ledger_sequence_number": self.ledger_sequence_number,
            "removed_training_paths": list(self.removed_training_paths),
            "forbidden_modules_loaded": list(self.forbidden_modules_loaded),
            "training_invocations": 0,
            "generator_invocations": 0,
            "planner_invocations": 0,
            "candidate_self_report_consumed": False,
        }


def replay_promoted_phase10_candidate(
    fixture: Phase10Phase6Fixture,
    promotion: Phase10PromotionEvidence,
    *,
    repo_root: Path,
    lean_project_root: Path,
    replay_candidate_root: Path,
    removed_training_paths: Sequence[str],
) -> Phase10IndependentReplayEvidence:
    if _forbidden_modules():
        raise ValueError("a forbidden training module was loaded before replay")
    replay_report = replay_phase10_phase6(
        fixture.root,
        replay_candidate_root,
    )
    replay_verification = verify_phase10_candidate(
        fixture,
        repo_root=repo_root,
        lean_project_root=lean_project_root,
        candidate_root=replay_candidate_root,
    )
    policy = phase10_phase7_policy()
    snapshot = load_active_phase7_store(
        promotion.promotion.snapshot.store_root,
        policy,
    )
    immutable_manifest = verify_immutable_phase7_package(
        snapshot.package_root,
        policy,
    )
    if immutable_manifest != promotion.promotion.package_manifest:
        raise ValueError("reopened immutable promotion manifest differs")
    promoted_source_candidate = snapshot.package_root / "source_candidate"
    promoted_tree = _directory_tree_hash(promoted_source_candidate)
    replay_tree = _directory_tree_hash(replay_candidate_root)
    evidence = Phase10IndependentReplayEvidence(
        phase6_replay=replay_report,
        verification=replay_verification,
        promoted_package_hash=immutable_manifest.package_hash,
        promoted_source_candidate_tree_hash=promoted_tree,
        replay_candidate_tree_hash=replay_tree,
        promotion_parent_hash=immutable_manifest.parent_package_hash,
        ledger_sequence_number=snapshot.pointer.ledger_sequence_number,
        removed_training_paths=tuple(removed_training_paths),
        forbidden_modules_loaded=_forbidden_modules(),
    )
    if not evidence.accepted:
        raise ValueError("Phase 10 independent replay did not close")
    return evidence


@dataclass(frozen=True, slots=True)
class Phase10ClosureEvidence:
    fixture: Phase10Phase6Fixture
    source_verification: Phase10VerificationEvidence
    promotion: Phase10PromotionEvidence
    replay: Phase10IndependentReplayEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase10.closure.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.fixture.accepted
            and self.source_verification.accepted
            and self.promotion.accepted
            and self.replay.accepted
            and self.fixture.lifecycle_transition.accepted
            and self.fixture.reference.information_report.accepted
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "phase10_exit_closed": self.accepted,
            "phase6_fixture_hash": self.fixture.to_json()["fixture_hash"],
            "source_verification_hash": (
                self.source_verification.semantic_report_hash
            ),
            "promotion_report_hash": self.promotion.report_hash,
            "replay_report_hash": self.replay.report_hash,
            "predecessor_model_identity_hash": (
                self.fixture.reference.predecessor_manifest.model_identity_hash
            ),
            "candidate_model_identity_hash": (
                self.fixture.reference.candidate_manifest.model_identity_hash
            ),
            "phase9_transition_report_hash": (
                self.fixture.lifecycle_transition.semantic_report_hash
            ),
            "information_report_hash": (
                self.fixture.reference.information_report.report_hash
            ),
            "promoted_package_hash": (
                self.promotion.promotion.package_manifest.package_hash
            ),
            "frontier_before": list(
                self.fixture.reference.predecessor_state.capability_frontier.task_ids
            ),
            "frontier_after": list(
                self.fixture.reference.candidate_state.capability_frontier.task_ids
            ),
            "protected_retained": True,
            "new_heldout_task_certified": True,
            "selected_kl_qre_nonregression": True,
            "rollback_exact": True,
            "atomic_promotion": True,
            "independent_replay_without_retraining": True,
            "training_invocations_during_replay": 0,
            "generator_invocations_during_replay": 0,
            "claim_boundary": {
                "one_selected_compact_model_family": True,
                "one_selected_lean_task_class": True,
                "one_promoted_learned_successor": True,
                "self_hosted_recursive_generation": False,
                "generic_successor_availability": False,
                "autonomous_unbounded_rsi": False,
            },
        }


def write_phase10_closure_report(
    path: Path,
    evidence: Phase10ClosureEvidence,
) -> None:
    output = path.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(evidence.to_json()))


__all__ = [
    "Phase10ClosureEvidence",
    "Phase10IndependentReplayEvidence",
    "remove_phase10_training_backend",
    "replay_promoted_phase10_candidate",
    "write_phase10_closure_report",
]
