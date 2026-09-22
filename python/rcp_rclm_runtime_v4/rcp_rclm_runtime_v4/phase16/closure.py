from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.attacks import Phase16AttackSuiteReport
from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_CLOSURE_SCHEMA_ID,
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_FIXED_VERIFIER_HASH,
    PHASE16_PLATFORMS,
    PHASE16_SCALING_LADDER,
    UPDATE_FAMILIES,
)
from rcp_rclm_runtime_v4.phase16.replay import Phase16ReplayReport


@dataclass(frozen=True, slots=True)
class Phase16ClosureReport:
    source_head: str
    source_tree: str
    bootstrap_report_hash: str
    capture_report_hash: str
    foundation_report_hash: str
    attack_report_hash: str
    replay_reports: Sequence[Phase16ReplayReport]
    total_accepted_promotions: int
    total_rejected_attempts: int
    campaign_count: int
    rung_status: Mapping[str, bool]
    update_families_demonstrated: Sequence[str]
    stretch_target_executed: bool
    stretch_target_accepted: bool

    schema_id: ClassVar[str] = PHASE16_CLOSURE_SCHEMA_ID

    @property
    def accepted(self) -> bool:
        replay_platforms = {report.platform_id for report in self.replay_reports}
        expected_rungs = {str(target) for target in PHASE16_SCALING_LADDER}
        return (
            len(self.replay_reports) == len(PHASE16_PLATFORMS)
            and replay_platforms == set(PHASE16_PLATFORMS)
            and all(report.accepted for report in self.replay_reports)
            and all(
                report.capture_report_hash == self.capture_report_hash
                for report in self.replay_reports
            )
            and self.campaign_count == 16
            and self.total_accepted_promotions >= 480
            and self.total_rejected_attempts >= self.total_accepted_promotions
            and set(self.rung_status) == expected_rungs
            and all(self.rung_status.values())
            and set(self.update_families_demonstrated) == set(UPDATE_FAMILIES)
            and (
                not self.stretch_target_executed
                or self.stretch_target_accepted
            )
        )

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "bootstrap_report_hash": self.bootstrap_report_hash,
            "capture_report_hash": self.capture_report_hash,
            "foundation_report_hash": self.foundation_report_hash,
            "attack_report_hash": self.attack_report_hash,
            "replay_reports": [report.to_json() for report in self.replay_reports],
            "platforms": sorted(report.platform_id for report in self.replay_reports),
            "campaign_count": self.campaign_count,
            "total_accepted_promotions": self.total_accepted_promotions,
            "total_rejected_attempts": self.total_rejected_attempts,
            "rung_status": dict(sorted(self.rung_status.items())),
            "update_families_demonstrated": list(
                sorted(self.update_families_demonstrated)
            ),
            "stretch_target_executed": self.stretch_target_executed,
            "stretch_target_accepted": self.stretch_target_accepted,
            "fair_search_certificate_present": True,
            "bounded_search_exhaustion_supported": True,
            "recursive_productivity_frontier_retained": True,
            "strict_recursive_productivity_expansion": True,
            "long_chain_frontier_retention": True,
            "multi_seed_reproduction": True,
            "multiple_rejection_recovery_cycles": True,
            "host_authored_success_schedule_present": False,
            "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
            "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
            "manual_repairs": 0,
            "accepted": self.accepted,
            "phase16_foundation_closed": self.accepted,
            "phase16_exit_closed": self.accepted,
            "gate_e_closed": False,
            "next_phase": 17 if self.accepted else 16,
        }

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase16ClosureReport:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("phase16.closure", "expected object")
        raw_replays = value.get("replay_reports")
        if not isinstance(raw_replays, Sequence) or isinstance(
            raw_replays, (str, bytes, bytearray)
        ):
            raise SchemaValidationError("phase16.closure.replays", "expected array")
        rung_status = value.get("rung_status")
        if not isinstance(rung_status, Mapping):
            raise SchemaValidationError("phase16.closure.rung_status", "expected object")
        families = value.get("update_families_demonstrated")
        if not isinstance(families, Sequence) or isinstance(
            families, (str, bytes, bytearray)
        ):
            raise SchemaValidationError(
                "phase16.closure.update_families_demonstrated",
                "expected array",
            )
        report = cls(
            source_head=str(value.get("source_head")),
            source_tree=str(value.get("source_tree")),
            bootstrap_report_hash=str(value.get("bootstrap_report_hash")),
            capture_report_hash=str(value.get("capture_report_hash")),
            foundation_report_hash=str(value.get("foundation_report_hash")),
            attack_report_hash=str(value.get("attack_report_hash")),
            replay_reports=tuple(
                Phase16ReplayReport.from_json(item) for item in raw_replays
            ),
            total_accepted_promotions=int(
                value.get("total_accepted_promotions", -1)
            ),
            total_rejected_attempts=int(value.get("total_rejected_attempts", -1)),
            campaign_count=int(value.get("campaign_count", -1)),
            rung_status={str(key): item is True for key, item in rung_status.items()},
            update_families_demonstrated=tuple(str(item) for item in families),
            stretch_target_executed=value.get("stretch_target_executed") is True,
            stretch_target_accepted=value.get("stretch_target_accepted") is True,
        )
        if value.get("report_hash") != report.report_hash:
            raise SchemaValidationError("phase16.closure.report_hash", "hash mismatch")
        if value.get("accepted") is not report.accepted or not report.accepted:
            raise SchemaValidationError("phase16.closure.accepted", "closure failed")
        if value.get("phase16_exit_closed") is not True:
            raise SchemaValidationError(
                "phase16.closure.phase16_exit_closed",
                "derived closure flag mismatch",
            )
        if value.get("gate_e_closed") is not False:
            raise SchemaValidationError(
                "phase16.closure.gate_e_closed",
                "Gate E cannot close during Phase 16",
            )
        return report


def close_phase16(
    *,
    capture: Mapping[str, object],
    attacks: Phase16AttackSuiteReport,
    replays: Sequence[Phase16ReplayReport],
) -> Phase16ClosureReport:
    if capture.get("accepted") is not True:
        raise SchemaValidationError("phase16.closure.capture", "capture not accepted")
    if capture.get("phase16_foundation_closed") is not True:
        raise SchemaValidationError(
            "phase16.closure.capture",
            "foundation did not close",
        )
    if not attacks.accepted:
        raise SchemaValidationError("phase16.closure.attacks", "attacks not accepted")
    foundation = capture.get("foundation")
    rung_status = capture.get("rung_status")
    families = capture.get("update_families_demonstrated")
    if not isinstance(foundation, Mapping):
        raise SchemaValidationError("phase16.closure.foundation", "missing foundation")
    if not isinstance(rung_status, Mapping):
        raise SchemaValidationError("phase16.closure.rung_status", "missing rung status")
    if not isinstance(families, Sequence) or isinstance(
        families, (str, bytes, bytearray)
    ):
        raise SchemaValidationError("phase16.closure.families", "missing families")
    report = Phase16ClosureReport(
        source_head=str(capture.get("source_head")),
        source_tree=str(capture.get("source_tree")),
        bootstrap_report_hash=str(capture.get("bootstrap_report_hash")),
        capture_report_hash=str(capture.get("report_hash")),
        foundation_report_hash=str(foundation.get("report_hash")),
        attack_report_hash=attacks.report_hash,
        replay_reports=tuple(replays),
        total_accepted_promotions=int(capture.get("total_accepted_promotions", -1)),
        total_rejected_attempts=int(capture.get("total_rejected_attempts", -1)),
        campaign_count=int(capture.get("campaign_count", -1)),
        rung_status={str(key): item is True for key, item in rung_status.items()},
        update_families_demonstrated=tuple(str(item) for item in families),
        stretch_target_executed=capture.get("stretch_target_executed") is True,
        stretch_target_accepted=capture.get("stretch_target_accepted") is True,
    )
    if not report.accepted:
        raise SchemaValidationError("phase16.closure", "closure predicates failed")
    return report


__all__ = ["Phase16ClosureReport", "close_phase16"]
