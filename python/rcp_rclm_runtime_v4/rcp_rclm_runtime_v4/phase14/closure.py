from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase14.attacks import Phase14AttackSuiteReport
from rcp_rclm_runtime_v4.phase14.bundle import Phase14BundleManifest
from rcp_rclm_runtime_v4.phase14.replay import Phase14ReplayReport
from rcp_rclm_runtime_v4.phase14.trajectory import Phase14TrajectoryReport

_REQUIRED_PLATFORMS = ("macos", "ubuntu", "windows")


@dataclass(frozen=True, slots=True)
class Phase14ClosureReport:
    source_head: str
    source_tree: str
    bundle_manifest_hash: str
    trajectory_report_hash: str
    attack_report_hash: str
    final_store_package_hash: str
    final_semantic_package_hash: str
    replay_reports: Sequence[Phase14ReplayReport]
    accepted_promotions: int
    rejected_attempts: int
    substantive_update_families: Sequence[str]
    initial_frontier_cardinality: int
    final_frontier_cardinality: int

    schema_id: ClassVar[str] = "runtime.v4.phase14.closure_report.v1"

    def __post_init__(self) -> None:
        reports = tuple(
            sorted(self.replay_reports, key=lambda item: item.platform_id.encode("utf-8"))
        )
        if len({item.platform_id for item in reports}) != len(reports):
            raise SchemaValidationError(
                "phase14.closure.replay_reports",
                "duplicate replay platform",
            )
        object.__setattr__(self, "replay_reports", reports)
        families = tuple(
            sorted(set(self.substantive_update_families), key=lambda item: item.encode("utf-8"))
        )
        object.__setattr__(self, "substantive_update_families", families)

    @property
    def platforms(self) -> tuple[str, ...]:
        return tuple(item.platform_id for item in self.replay_reports)

    @property
    def replay_report_hashes(self) -> tuple[str, ...]:
        return tuple(item.report_hash for item in self.replay_reports)

    @property
    def all_replays_accepted(self) -> bool:
        return bool(self.replay_reports) and all(item.accepted for item in self.replay_reports)

    @property
    def all_replays_pinned(self) -> bool:
        return bool(self.replay_reports) and all(item.pinned_lean for item in self.replay_reports)

    @property
    def all_source_bindings_agree(self) -> bool:
        return all(
            item.source_head == self.source_head
            and item.source_tree == self.source_tree
            for item in self.replay_reports
        )

    @property
    def all_semantic_bindings_agree(self) -> bool:
        return all(
            item.bundle_manifest_hash == self.bundle_manifest_hash
            and item.trajectory_report_hash == self.trajectory_report_hash
            and item.final_store_package_hash == self.final_store_package_hash
            and item.final_semantic_package_hash
            == self.final_semantic_package_hash
            and item.accepted_promotions == self.accepted_promotions
            and item.rejected_attempts == self.rejected_attempts
            and tuple(item.distinct_update_families)
            == tuple(self.substantive_update_families)
            for item in self.replay_reports
        )

    @property
    def phase14_exit_closed(self) -> bool:
        return (
            self.platforms == _REQUIRED_PLATFORMS
            and self.all_replays_accepted
            and self.all_replays_pinned
            and self.all_source_bindings_agree
            and self.all_semantic_bindings_agree
            and self.accepted_promotions >= 4
            and self.rejected_attempts >= 2
            and len(self.substantive_update_families) >= 3
            and self.final_frontier_cardinality
            >= self.initial_frontier_cardinality + self.accepted_promotions
        )

    @property
    def accepted(self) -> bool:
        return self.phase14_exit_closed

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "trajectory_report_hash": self.trajectory_report_hash,
            "attack_report_hash": self.attack_report_hash,
            "final_store_package_hash": self.final_store_package_hash,
            "final_semantic_package_hash": self.final_semantic_package_hash,
            "platforms": list(self.platforms),
            "replay_report_hashes": list(self.replay_report_hashes),
            "replay_reports": [
                report.to_json() for report in self.replay_reports
            ],
            "accepted_promotions": self.accepted_promotions,
            "rejected_attempts": self.rejected_attempts,
            "substantive_update_families": list(self.substantive_update_families),
            "initial_frontier_cardinality": self.initial_frontier_cardinality,
            "final_frontier_cardinality": self.final_frontier_cardinality,
            "all_replays_accepted": self.all_replays_accepted,
            "all_replays_pinned": self.all_replays_pinned,
            "all_source_bindings_agree": self.all_source_bindings_agree,
            "all_semantic_bindings_agree": self.all_semantic_bindings_agree,
            "manual_repairs": 0,
            "host_provided_successful_route": False,
            "heldout_material_visible_before_freeze": False,
            "proposal_worker_invocations_during_replay": 0,
            "training_invocations_during_replay": 0,
            "generator_invocations_during_replay": 0,
            "planner_invocations_during_replay": 0,
            "accepted": self.accepted,
            "phase14_exit_closed": self.phase14_exit_closed,
            "gate_e_closed": False,
            "next_phase": 15 if self.phase14_exit_closed else 14,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> "Phase14ClosureReport":
        if not isinstance(value, dict):
            raise SchemaValidationError("phase14.closure", "expected object")
        raw_reports = value.get("replay_reports")
        raw_families = value.get("substantive_update_families")
        if not isinstance(raw_reports, list) or not isinstance(raw_families, list):
            raise SchemaValidationError(
                "phase14.closure",
                "expected replay_reports and substantive_update_families arrays",
            )
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            bundle_manifest_hash=str(value["bundle_manifest_hash"]),
            trajectory_report_hash=str(value["trajectory_report_hash"]),
            attack_report_hash=str(value["attack_report_hash"]),
            final_store_package_hash=str(value["final_store_package_hash"]),
            final_semantic_package_hash=str(
                value["final_semantic_package_hash"]
            ),
            replay_reports=tuple(
                Phase14ReplayReport.from_json(item)
                for item in raw_reports
            ),
            accepted_promotions=int(value["accepted_promotions"]),
            rejected_attempts=int(value["rejected_attempts"]),
            substantive_update_families=tuple(
                str(item) for item in raw_families
            ),
            initial_frontier_cardinality=int(
                value["initial_frontier_cardinality"]
            ),
            final_frontier_cardinality=int(
                value["final_frontier_cardinality"]
            ),
        )
        expected = result.to_json()
        if value != expected:
            raise SchemaValidationError(
                "phase14.closure",
                "derived closure content or report hash mismatch",
            )
        return result


def close_phase14(
    *,
    trajectory: Phase14TrajectoryReport,
    bundle: Phase14BundleManifest,
    attacks: Phase14AttackSuiteReport,
    replay_reports: Sequence[Phase14ReplayReport],
) -> Phase14ClosureReport:
    if not trajectory.campaign_closed or not trajectory.accepted:
        raise SchemaValidationError(
            "phase14.closure.trajectory",
            "schedule-free campaign is not accepted",
        )
    if trajectory.to_json().get("phase14_exit_closed") is not False:
        raise SchemaValidationError(
            "phase14.closure.trajectory",
            "intermediate trajectory improperly closes Phase 14",
        )
    if bundle.source_head != trajectory.source_head or bundle.source_tree != trajectory.source_tree:
        raise SchemaValidationError(
            "phase14.closure.bundle",
            "bundle source binding differs from trajectory",
        )
    if bundle.trajectory_report_hash != trajectory.report_hash:
        raise SchemaValidationError(
            "phase14.closure.bundle",
            "bundle trajectory binding differs",
        )
    if not attacks.accepted:
        raise SchemaValidationError(
            "phase14.closure.attacks",
            "adversarial suite is not accepted",
        )
    result = Phase14ClosureReport(
        source_head=trajectory.source_head,
        source_tree=trajectory.source_tree,
        bundle_manifest_hash=bundle.manifest_hash,
        trajectory_report_hash=trajectory.report_hash,
        attack_report_hash=attacks.report_hash,
        final_store_package_hash=trajectory.final_store_package_hash,
        final_semantic_package_hash=trajectory.final_semantic_package_hash,
        replay_reports=tuple(replay_reports),
        accepted_promotions=trajectory.accepted_promotions,
        rejected_attempts=trajectory.rejected_attempts,
        substantive_update_families=trajectory.substantive_update_families,
        initial_frontier_cardinality=len(trajectory.initial_capability_frontier),
        final_frontier_cardinality=len(trajectory.final_capability_frontier),
    )
    if not result.phase14_exit_closed:
        raise SchemaValidationError(
            "phase14.closure",
            "final aggregation predicates failed",
        )
    return result


__all__ = ["Phase14ClosureReport", "close_phase14"]
