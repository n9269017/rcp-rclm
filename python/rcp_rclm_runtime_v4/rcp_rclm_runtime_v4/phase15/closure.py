from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.phase15.attacks import Phase15AttackSuiteReport
from rcp_rclm_runtime_v4.phase15.replay import Phase15ReplayReport
from rcp_rclm_runtime_v4.phase15.trajectory import Phase15TrajectoryReport


@dataclass(frozen=True, slots=True)
class Phase15ClosureReport:
    source_head: str
    source_tree: str
    trajectory_report_hash: str
    bundle_manifest_hash: str
    attack_report_hash: str
    final_store_package_hash: str
    final_m9_semantic_package_hash: str
    replay_reports: Sequence[Phase15ReplayReport]

    schema_id: ClassVar[str] = "runtime.v4.phase15.closure_report.v1"

    @property
    def accepted(self) -> bool:
        platforms = tuple(sorted(item.platform_id for item in self.replay_reports))
        return (
            platforms == ("macos", "ubuntu", "windows")
            and all(item.accepted for item in self.replay_reports)
            and all(item.source_head == self.source_head for item in self.replay_reports)
            and all(item.source_tree == self.source_tree for item in self.replay_reports)
            and all(item.trajectory_report_hash == self.trajectory_report_hash for item in self.replay_reports)
            and all(item.bundle_manifest_hash == self.bundle_manifest_hash for item in self.replay_reports)
            and all(item.final_store_package_hash == self.final_store_package_hash for item in self.replay_reports)
            and all(item.final_m9_semantic_package_hash == self.final_m9_semantic_package_hash for item in self.replay_reports)
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "trajectory_report_hash": self.trajectory_report_hash,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "attack_report_hash": self.attack_report_hash,
            "final_store_package_hash": self.final_store_package_hash,
            "final_m9_semantic_package_hash": self.final_m9_semantic_package_hash,
            "replay_reports": [item.to_json() for item in sorted(self.replay_reports, key=lambda item: item.platform_id)],
            "platforms": sorted(item.platform_id for item in self.replay_reports),
            "all_replays_pinned": all(item.pinned_lean for item in self.replay_reports),
            "training_invocations_during_replay": 0,
            "candidate_builder_invocations_during_replay": 0,
            "proposal_worker_invocations_during_replay": 0,
            "manual_repairs": 0,
            "accepted": self.accepted,
            "phase15_exit_closed": self.accepted,
            "gate_e_closed": False,
            "next_phase": 16 if self.accepted else 15,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> "Phase15ClosureReport":
        if not isinstance(value, dict) or not isinstance(value.get("replay_reports"), list):
            raise SchemaValidationError("phase15.closure", "expected object with replay reports")
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            trajectory_report_hash=str(value["trajectory_report_hash"]),
            bundle_manifest_hash=str(value["bundle_manifest_hash"]),
            attack_report_hash=str(value["attack_report_hash"]),
            final_store_package_hash=str(value["final_store_package_hash"]),
            final_m9_semantic_package_hash=str(value["final_m9_semantic_package_hash"]),
            replay_reports=tuple(Phase15ReplayReport.from_json(item) for item in value["replay_reports"]),
        )
        if value.get("report_hash") != result.report_hash:
            raise SchemaValidationError("phase15.closure.report_hash", "hash mismatch")
        if value.get("accepted") is not result.accepted:
            raise SchemaValidationError("phase15.closure.accepted", "derived flag mismatch")
        return result


def close_phase15(
    *,
    trajectory: Phase15TrajectoryReport,
    bundle_manifest_hash: str,
    attacks: Phase15AttackSuiteReport,
    replays: Sequence[Phase15ReplayReport],
) -> Phase15ClosureReport:
    if not trajectory.accepted:
        raise SchemaValidationError("phase15.closure.trajectory", "trajectory did not close campaign")
    if not attacks.accepted or attacks.bundle_manifest_hash != bundle_manifest_hash:
        raise SchemaValidationError("phase15.closure.attacks", "attack suite binding failed")
    report = Phase15ClosureReport(
        source_head=trajectory.source_head,
        source_tree=trajectory.source_tree,
        trajectory_report_hash=trajectory.report_hash,
        bundle_manifest_hash=bundle_manifest_hash,
        attack_report_hash=attacks.report_hash,
        final_store_package_hash=trajectory.final_store_package_hash,
        final_m9_semantic_package_hash=trajectory.final_m9_semantic_package_hash,
        replay_reports=tuple(replays),
    )
    if not report.accepted:
        raise SchemaValidationError("phase15.closure", "three-platform closure predicates failed")
    return report


__all__ = ["Phase15ClosureReport", "close_phase15"]
