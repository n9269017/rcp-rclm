from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH,
    PHASE14_MIN_PROMOTIONS,
    PHASE14_MIN_REJECTIONS,
    PHASE14_MIN_UPDATE_FAMILIES,
    PHASE14_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v4.phase14.records import Phase14AttemptSummary

@dataclass(frozen=True, slots=True)
class Phase14TrajectoryReport:
    source_head: str
    source_tree: str
    phase13_exit_report_hash: str
    phase13_bundle_manifest_hash: str
    initial_store_package_hash: str
    initial_m4_semantic_package_hash: str
    final_store_package_hash: str
    final_semantic_package_hash: str
    initial_capability_frontier: Sequence[str]
    final_capability_frontier: Sequence[str]
    initial_recursive_productivity_frontier: Sequence[str]
    final_recursive_productivity_frontier: Sequence[str]
    attempts: Sequence[Phase14AttemptSummary]
    challenge_manifest_hash: str
    answer_store_hash: str
    challenge_count: int
    challenge_gate_e_report_hashes: Sequence[str]
    challenge_gate_e_validation_hashes: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v4.phase14.trajectory_report.v1"

    @classmethod
    def from_json(cls, value: object) -> Phase14TrajectoryReport:
        if not isinstance(value, dict):
            raise ValueError("Phase 14 trajectory report must be an object")
        raw_attempts = value.get("attempts")
        if not isinstance(raw_attempts, list):
            raise ValueError("Phase 14 trajectory attempts must be an array")
        sequence_fields = (
            "initial_capability_frontier",
            "final_capability_frontier",
            "initial_recursive_productivity_frontier",
            "final_recursive_productivity_frontier",
            "challenge_gate_e_report_hashes",
            "challenge_gate_e_validation_hashes",
        )
        for field in sequence_fields:
            if not isinstance(value.get(field), list):
                raise ValueError(f"Phase 14 trajectory {field} must be an array")
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            phase13_exit_report_hash=str(value["phase13_exit_report_hash"]),
            phase13_bundle_manifest_hash=str(value["phase13_bundle_manifest_hash"]),
            initial_store_package_hash=str(value["initial_store_package_hash"]),
            initial_m4_semantic_package_hash=str(value["initial_m4_semantic_package_hash"]),
            final_store_package_hash=str(value["final_store_package_hash"]),
            final_semantic_package_hash=str(value["final_semantic_package_hash"]),
            initial_capability_frontier=tuple(
                str(item) for item in value["initial_capability_frontier"]
            ),
            final_capability_frontier=tuple(
                str(item) for item in value["final_capability_frontier"]
            ),
            initial_recursive_productivity_frontier=tuple(
                str(item)
                for item in value["initial_recursive_productivity_frontier"]
            ),
            final_recursive_productivity_frontier=tuple(
                str(item)
                for item in value["final_recursive_productivity_frontier"]
            ),
            attempts=tuple(
                Phase14AttemptSummary.from_json(item) for item in raw_attempts
            ),
            challenge_manifest_hash=str(value["challenge_manifest_hash"]),
            answer_store_hash=str(value["answer_store_hash"]),
            challenge_count=int(value["challenge_count"]),
            challenge_gate_e_report_hashes=tuple(
                str(item) for item in value["challenge_gate_e_report_hashes"]
            ),
            challenge_gate_e_validation_hashes=tuple(
                str(item)
                for item in value["challenge_gate_e_validation_hashes"]
            ),
        )
        if value.get("report_hash") != result.report_hash:
            raise ValueError("Phase 14 trajectory report hash mismatch")
        if value.get("accepted") is not result.accepted:
            raise ValueError("Phase 14 trajectory accepted flag mismatch")
        if value.get("phase14_campaign_closed") is not result.campaign_closed:
            raise ValueError("Phase 14 campaign-closure flag mismatch")
        if value.get("phase14_exit_closed") is not False:
            raise ValueError("Only the Phase 14 aggregator may close the exit")
        if value.get("next_phase") != 14:
            raise ValueError("intermediate Phase 14 reports must retain next_phase=14")
        return result

    @property
    def accepted_promotions(self) -> int:
        return sum(attempt.verdict == "accept" for attempt in self.attempts)

    @property
    def rejected_attempts(self) -> int:
        return sum(attempt.verdict == "reject" for attempt in self.attempts)

    @property
    def substantive_update_families(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {attempt.update_family for attempt in self.attempts if attempt.verdict == "accept"},
                key=lambda item: item.encode("utf-8"),
            )
        )

    @property
    def rejection_conditioned_recovery(self) -> bool:
        return any(
            attempt.verdict == "accept" and attempt.rejection_conditioned
            for attempt in self.attempts
        )

    @property
    def campaign_closed(self) -> bool:
        return (
            self.initial_m4_semantic_package_hash
            == PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH
            and self.accepted_promotions >= PHASE14_MIN_PROMOTIONS
            and len(self.substantive_update_families) >= PHASE14_MIN_UPDATE_FAMILIES
            and self.rejected_attempts >= PHASE14_MIN_REJECTIONS
            and self.rejection_conditioned_recovery
            and len(self.final_capability_frontier)
            >= len(self.initial_capability_frontier) + PHASE14_MIN_PROMOTIONS
            and set(self.initial_capability_frontier).issubset(self.final_capability_frontier)
            and set(self.initial_recursive_productivity_frontier).issubset(
                self.final_recursive_productivity_frontier
            )
            and self.challenge_count >= PHASE14_MIN_PROMOTIONS
            and len(self.challenge_gate_e_report_hashes) == self.challenge_count
            and len(self.challenge_gate_e_validation_hashes) == self.challenge_count
        )

    @property
    def accepted(self) -> bool:
        return self.campaign_closed

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json(include_hash=False))

    def to_json(self, *, include_hash: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_id": self.schema_id,
            "trajectory_id": PHASE14_TRAJECTORY_ID,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "phase13_exit_report_hash": self.phase13_exit_report_hash,
            "phase13_bundle_manifest_hash": self.phase13_bundle_manifest_hash,
            "initial_store_package_hash": self.initial_store_package_hash,
            "initial_m4_semantic_package_hash": self.initial_m4_semantic_package_hash,
            "final_store_package_hash": self.final_store_package_hash,
            "final_semantic_package_hash": self.final_semantic_package_hash,
            "initial_capability_frontier": list(self.initial_capability_frontier),
            "final_capability_frontier": list(self.final_capability_frontier),
            "initial_recursive_productivity_frontier": list(
                self.initial_recursive_productivity_frontier
            ),
            "final_recursive_productivity_frontier": list(
                self.final_recursive_productivity_frontier
            ),
            "attempts": [attempt.to_json() for attempt in self.attempts],
            "challenge_manifest_hash": self.challenge_manifest_hash,
            "answer_store_hash": self.answer_store_hash,
            "challenge_count": self.challenge_count,
            "challenge_gate_e_report_hashes": list(self.challenge_gate_e_report_hashes),
            "challenge_gate_e_validation_hashes": list(
                self.challenge_gate_e_validation_hashes
            ),
            "accepted_promotions": self.accepted_promotions,
            "rejected_attempts": self.rejected_attempts,
            "substantive_update_families": list(self.substantive_update_families),
            "rejection_conditioned_recovery": self.rejection_conditioned_recovery,
            "manual_repairs": 0,
            "host_provided_successful_route": False,
            "heldout_material_visible_before_freeze": False,
            "expected_candidate_hash_present": False,
            "expected_accepted_program_bytes_present": False,
            "expected_new_capability_present": False,
            "expected_final_model_identity_present": False,
            "four_promotion_threshold_encoded_in_package_policy": False,
            "external_validation_challenge_count": self.challenge_count,
            "gate_e_closed": False,
            "phase14_campaign_closed": self.campaign_closed,
            "phase14_exit_closed": False,
            "accepted": self.accepted,
            "next_phase": 14,
        }
        if include_hash:
            value["report_hash"] = self.report_hash
        return value


__all__ = ["Phase14TrajectoryReport"]
