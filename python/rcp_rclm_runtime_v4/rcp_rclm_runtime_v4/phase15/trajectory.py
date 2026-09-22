from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_EXPECTED_M8_SEMANTIC_PACKAGE_HASH,
    PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH,
    PHASE15_EXPECTED_PHASE14_FINAL_STORE_HASH,
    PHASE15_EXPECTED_PHASE14_TRAJECTORY_HASH,
    PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS,
    PHASE15_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v4.phase15.records import Phase15AttemptSummary


@dataclass(frozen=True, slots=True)
class Phase15TrajectoryReport:
    source_head: str
    source_tree: str
    phase14_bundle_manifest_hash: str
    phase14_trajectory_report_hash: str
    initial_store_package_hash: str
    initial_m8_semantic_package_hash: str
    final_store_package_hash: str
    final_m9_semantic_package_hash: str
    initial_capability_frontier: Sequence[str]
    final_capability_frontier: Sequence[str]
    initial_recursive_productivity_frontier: Sequence[str]
    final_recursive_productivity_frontier: Sequence[str]
    candidate_freeze_hashes: Sequence[str]
    challenge_manifest_hash: str
    answer_store_hash: str
    dynamic_task_ids: Sequence[str]
    attempts: Sequence[Phase15AttemptSummary]
    gate_e_report_hash: str
    gate_e_validation_hash: str

    schema_id: ClassVar[str] = "runtime.v4.phase15.trajectory_report.v1"

    @property
    def accepted_promotions(self) -> int:
        return sum(item.verdict == "accept" for item in self.attempts)

    @property
    def rejected_attempts(self) -> int:
        return sum(item.verdict == "reject" for item in self.attempts)

    @property
    def candidate_variants(self) -> tuple[str, ...]:
        return tuple(item.variant for item in self.attempts)

    @property
    def campaign_closed(self) -> bool:
        return (
            self.phase14_bundle_manifest_hash == PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH
            and self.phase14_trajectory_report_hash == PHASE15_EXPECTED_PHASE14_TRAJECTORY_HASH
            and self.initial_store_package_hash == PHASE15_EXPECTED_PHASE14_FINAL_STORE_HASH
            and self.initial_m8_semantic_package_hash == PHASE15_EXPECTED_M8_SEMANTIC_PACKAGE_HASH
            and len(self.attempts) == 2
            and self.candidate_variants == ("lean_only", "multidomain")
            and self.rejected_attempts == 1
            and self.accepted_promotions == 1
            and len(set(self.candidate_freeze_hashes)) == 2
            and len(self.dynamic_task_ids) == 2
            and set(self.initial_capability_frontier).issubset(self.final_capability_frontier)
            and len(self.final_capability_frontier) == len(self.initial_capability_frontier) + 2
            and set(self.initial_recursive_productivity_frontier).issubset(self.final_recursive_productivity_frontier)
            and set(PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS).issubset(self.final_recursive_productivity_frontier)
            and self.attempts[0].active_store_package_hash_before == self.attempts[0].active_store_package_hash_after
            and self.attempts[1].active_store_package_hash_before == self.attempts[0].active_store_package_hash_after
            and self.attempts[1].active_store_package_hash_after == self.final_store_package_hash
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
            "trajectory_id": PHASE15_TRAJECTORY_ID,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "phase14_bundle_manifest_hash": self.phase14_bundle_manifest_hash,
            "phase14_trajectory_report_hash": self.phase14_trajectory_report_hash,
            "initial_store_package_hash": self.initial_store_package_hash,
            "initial_m8_semantic_package_hash": self.initial_m8_semantic_package_hash,
            "final_store_package_hash": self.final_store_package_hash,
            "final_m9_semantic_package_hash": self.final_m9_semantic_package_hash,
            "initial_capability_frontier": list(self.initial_capability_frontier),
            "final_capability_frontier": list(self.final_capability_frontier),
            "initial_recursive_productivity_frontier": list(self.initial_recursive_productivity_frontier),
            "final_recursive_productivity_frontier": list(self.final_recursive_productivity_frontier),
            "candidate_freeze_hashes": list(self.candidate_freeze_hashes),
            "challenge_manifest_hash": self.challenge_manifest_hash,
            "answer_store_hash": self.answer_store_hash,
            "dynamic_task_ids": list(self.dynamic_task_ids),
            "attempts": [item.to_json() for item in self.attempts],
            "gate_e_report_hash": self.gate_e_report_hash,
            "gate_e_validation_hash": self.gate_e_validation_hash,
            "accepted_promotions": self.accepted_promotions,
            "rejected_attempts": self.rejected_attempts,
            "dynamic_domains": ["integer_program", "lean_multistep"],
            "bounded_autoregressive_execution": True,
            "multi_token_reasoning": True,
            "canonical_quantized_model_package": True,
            "untrusted_training_with_deterministic_export": True,
            "independent_cross_domain_evaluation": True,
            "dynamic_challenges_generated_after_candidate_freeze": True,
            "predecessor_failed_all_dynamic_tasks": True,
            "candidate_passed_all_dynamic_tasks": True,
            "manual_repairs": 0,
            "heldout_material_visible_before_freeze": False,
            "host_provided_successful_route": False,
            "phase15_campaign_closed": self.campaign_closed,
            "phase15_exit_closed": False,
            "gate_e_closed": False,
            "accepted": self.accepted,
            "next_phase": 15,
        }
        if include_hash:
            value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> "Phase15TrajectoryReport":
        if not isinstance(value, dict):
            raise ValueError("Phase 15 trajectory report must be an object")
        attempts = value.get("attempts")
        if not isinstance(attempts, list):
            raise ValueError("Phase 15 attempts must be an array")
        sequence_fields = (
            "initial_capability_frontier",
            "final_capability_frontier",
            "initial_recursive_productivity_frontier",
            "final_recursive_productivity_frontier",
            "candidate_freeze_hashes",
            "dynamic_task_ids",
        )
        for field in sequence_fields:
            if not isinstance(value.get(field), list):
                raise ValueError(f"Phase 15 {field} must be an array")
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            phase14_bundle_manifest_hash=str(value["phase14_bundle_manifest_hash"]),
            phase14_trajectory_report_hash=str(value["phase14_trajectory_report_hash"]),
            initial_store_package_hash=str(value["initial_store_package_hash"]),
            initial_m8_semantic_package_hash=str(value["initial_m8_semantic_package_hash"]),
            final_store_package_hash=str(value["final_store_package_hash"]),
            final_m9_semantic_package_hash=str(value["final_m9_semantic_package_hash"]),
            initial_capability_frontier=tuple(str(item) for item in value["initial_capability_frontier"]),
            final_capability_frontier=tuple(str(item) for item in value["final_capability_frontier"]),
            initial_recursive_productivity_frontier=tuple(str(item) for item in value["initial_recursive_productivity_frontier"]),
            final_recursive_productivity_frontier=tuple(str(item) for item in value["final_recursive_productivity_frontier"]),
            candidate_freeze_hashes=tuple(str(item) for item in value["candidate_freeze_hashes"]),
            challenge_manifest_hash=str(value["challenge_manifest_hash"]),
            answer_store_hash=str(value["answer_store_hash"]),
            dynamic_task_ids=tuple(str(item) for item in value["dynamic_task_ids"]),
            attempts=tuple(Phase15AttemptSummary.from_json(item) for item in attempts),
            gate_e_report_hash=str(value["gate_e_report_hash"]),
            gate_e_validation_hash=str(value["gate_e_validation_hash"]),
        )
        if value.get("report_hash") != result.report_hash:
            raise ValueError("Phase 15 trajectory report hash mismatch")
        if value.get("accepted") is not result.accepted:
            raise ValueError("Phase 15 accepted flag mismatch")
        if value.get("phase15_exit_closed") is not False or value.get("next_phase") != 15:
            raise ValueError("intermediate Phase 15 report has invalid closure authority")
        return result


__all__ = ["Phase15TrajectoryReport"]
