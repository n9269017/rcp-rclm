from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.bootstrap import Phase16BootstrapReport
from rcp_rclm_runtime_v4.phase16.capture import run_phase16_capture
from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_FIXED_VERIFIER_HASH,
    PHASE16_PLATFORMS,
    PHASE16_REPLAY_SCHEMA_ID,
)


@dataclass(frozen=True, slots=True)
class Phase16ReplayReport:
    platform_id: str
    source_head: str
    source_tree: str
    bootstrap_report_hash: str
    capture_report_hash: str
    reconstructed_capture_hash: str
    campaign_count: int
    accepted_promotions: int
    rejected_attempts: int
    stretch_target_executed: bool

    schema_id: ClassVar[str] = PHASE16_REPLAY_SCHEMA_ID

    @property
    def accepted(self) -> bool:
        return (
            self.platform_id in PHASE16_PLATFORMS
            and self.capture_report_hash == self.reconstructed_capture_hash
            and self.campaign_count == 16
            and self.accepted_promotions >= 480
            and self.rejected_attempts >= self.accepted_promotions
        )

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "platform_id": self.platform_id,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "bootstrap_report_hash": self.bootstrap_report_hash,
            "capture_report_hash": self.capture_report_hash,
            "reconstructed_capture_hash": self.reconstructed_capture_hash,
            "campaign_count": self.campaign_count,
            "accepted_promotions": self.accepted_promotions,
            "rejected_attempts": self.rejected_attempts,
            "stretch_target_executed": self.stretch_target_executed,
            "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
            "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
            "proposal_worker_invocations": 0,
            "generator_worker_invocations": 0,
            "training_worker_invocations": 0,
            "planner_worker_invocations": 0,
            "model_serving_invocations": 0,
            "manual_repairs": 0,
            "worker_free_replay": True,
            "accepted": self.accepted,
            "phase16_exit_closed": False,
            "gate_e_closed": False,
            "next_phase": 16,
        }

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase16ReplayReport:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("phase16.replay", "expected object")
        report = cls(
            platform_id=str(value.get("platform_id")),
            source_head=str(value.get("source_head")),
            source_tree=str(value.get("source_tree")),
            bootstrap_report_hash=str(value.get("bootstrap_report_hash")),
            capture_report_hash=str(value.get("capture_report_hash")),
            reconstructed_capture_hash=str(
                value.get("reconstructed_capture_hash")
            ),
            campaign_count=int(value.get("campaign_count", -1)),
            accepted_promotions=int(value.get("accepted_promotions", -1)),
            rejected_attempts=int(value.get("rejected_attempts", -1)),
            stretch_target_executed=value.get("stretch_target_executed") is True,
        )
        if value.get("report_hash") != report.report_hash:
            raise SchemaValidationError("phase16.replay.report_hash", "hash mismatch")
        if value.get("accepted") is not report.accepted or not report.accepted:
            raise SchemaValidationError("phase16.replay.accepted", "replay failed")
        return report


def replay_phase16_capture(
    *,
    capture: Mapping[str, object],
    bootstrap: Phase16BootstrapReport,
    platform_id: str,
) -> Phase16ReplayReport:
    if platform_id not in PHASE16_PLATFORMS:
        raise SchemaValidationError("phase16.replay.platform_id", "unsupported platform")
    observed = capture.get("report_hash")
    if not isinstance(observed, str):
        raise SchemaValidationError("phase16.replay.capture", "capture hash missing")
    payload = dict(capture)
    del payload["report_hash"]
    if observed != canonical_json_hash(payload):
        raise SchemaValidationError("phase16.replay.capture", "capture hash mismatch")
    if capture.get("bootstrap_report_hash") != bootstrap.report_hash:
        raise SchemaValidationError("phase16.replay.capture", "bootstrap mismatch")
    reconstructed = run_phase16_capture(
        bootstrap=bootstrap,
        source_head=str(capture.get("source_head")),
        source_tree=str(capture.get("source_tree")),
        include_stretch=capture.get("stretch_target_executed") is True,
    )
    if capture != reconstructed:
        raise SchemaValidationError(
            "phase16.replay.capture",
            "worker-free deterministic reconstruction mismatch",
        )
    report = Phase16ReplayReport(
        platform_id=platform_id,
        source_head=str(capture["source_head"]),
        source_tree=str(capture["source_tree"]),
        bootstrap_report_hash=bootstrap.report_hash,
        capture_report_hash=observed,
        reconstructed_capture_hash=str(reconstructed["report_hash"]),
        campaign_count=int(capture["campaign_count"]),
        accepted_promotions=int(capture["total_accepted_promotions"]),
        rejected_attempts=int(capture["total_rejected_attempts"]),
        stretch_target_executed=capture.get("stretch_target_executed") is True,
    )
    if not report.accepted:
        raise SchemaValidationError("phase16.replay", "replay predicates failed")
    return report


__all__ = ["Phase16ReplayReport", "replay_phase16_capture"]
