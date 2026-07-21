from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_structural_integer

from rcp_rclm_runtime_v3.phase12.constants import (
    PHASE12_REQUIRED_ACCEPTED_PROMOTIONS,
    PHASE12_REQUIRED_REJECTED_ATTEMPTS,
    PHASE12_TARGET_FRONTIER_CARDINALITY,
    PHASE12_TOTAL_BUDGET,
    PHASE12_TOTAL_BUDGET_HASH,
)


class Phase12StartReasonCode(StrEnum):
    BINDING_MISMATCH = "PHASE12_BINDING_MISMATCH"
    GENERATION_NOT_ADVANCED = "PHASE12_GENERATION_NOT_ADVANCED"
    HELDOUT_ACCESS_REQUESTED = "PHASE12_HELDOUT_ACCESS_REQUESTED"
    MANUAL_REPAIR_REQUESTED = "PHASE12_MANUAL_REPAIR_REQUESTED"
    OUTPUT_BUDGET_EXCEEDED = "PHASE12_OUTPUT_BUDGET_EXCEEDED"
    PROGRAM_MISMATCH = "PHASE12_PROGRAM_MISMATCH"


@dataclass(frozen=True, slots=True)
class Phase12TrajectoryBudget:
    max_wall_clock_seconds: int
    max_accelerator_count: int
    max_training_steps: int
    max_output_bytes: int
    max_generator_invocations: int
    max_candidate_realizations: int
    max_candidate_evaluations: int
    max_promotions: int
    max_rejected_attempts: int
    max_manual_repairs: int

    schema_id: ClassVar[str] = "runtime.v3.phase12.trajectory_budget.v1"

    def __post_init__(self) -> None:
        for name, minimum, maximum in (
            ("max_wall_clock_seconds", 1, 3_600),
            ("max_accelerator_count", 0, 8),
            ("max_training_steps", 0, 100_000),
            ("max_output_bytes", 1, 1_000_000),
            ("max_generator_invocations", 1, 10_000),
            ("max_candidate_realizations", 1, 10_000),
            ("max_candidate_evaluations", 1, 10_000),
            ("max_promotions", 1, 1_000),
            ("max_rejected_attempts", 1, 1_000),
            ("max_manual_repairs", 0, 0),
        ):
            require_structural_integer(
                getattr(self, name),
                f"phase12.budget.{name}",
                minimum=minimum,
                maximum=maximum,
            )
        if self.max_promotions != PHASE12_REQUIRED_ACCEPTED_PROMOTIONS:
            raise SchemaValidationError(
                "phase12.budget.max_promotions",
                f"expected {PHASE12_REQUIRED_ACCEPTED_PROMOTIONS}",
            )
        if self.max_rejected_attempts < PHASE12_REQUIRED_REJECTED_ATTEMPTS:
            raise SchemaValidationError(
                "phase12.budget.max_rejected_attempts",
                f"expected at least {PHASE12_REQUIRED_REJECTED_ATTEMPTS}",
            )

    @property
    def budget_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "max_wall_clock_seconds": self.max_wall_clock_seconds,
            "max_accelerator_count": self.max_accelerator_count,
            "max_training_steps": self.max_training_steps,
            "max_output_bytes": self.max_output_bytes,
            "max_generator_invocations": self.max_generator_invocations,
            "max_candidate_realizations": self.max_candidate_realizations,
            "max_candidate_evaluations": self.max_candidate_evaluations,
            "max_promotions": self.max_promotions,
            "max_rejected_attempts": self.max_rejected_attempts,
            "max_manual_repairs": self.max_manual_repairs,
        }


def default_phase12_trajectory_budget() -> Phase12TrajectoryBudget:
    result = Phase12TrajectoryBudget(**PHASE12_TOTAL_BUDGET)
    if result.budget_hash != PHASE12_TOTAL_BUDGET_HASH:
        raise ValueError("Phase 12 trajectory budget hash mismatch")
    return result


@dataclass(frozen=True, slots=True)
class Phase12StartValidationReport:
    invocation_hash: str
    program_hash: str
    active_generator_generation: int
    active_planner_generation: int
    requested_generator_generation: int
    requested_planner_generation: int
    binding_checks: dict[str, bool]
    reason_codes: tuple[Phase12StartReasonCode, ...]

    schema_id: ClassVar[str] = "runtime.v3.phase12.start_validation.v1"

    def __post_init__(self) -> None:
        validate_hash256(self.invocation_hash, "phase12.validation.invocation_hash")
        validate_hash256(self.program_hash, "phase12.validation.program_hash")
        for name in (
            "active_generator_generation",
            "active_planner_generation",
            "requested_generator_generation",
            "requested_planner_generation",
        ):
            require_structural_integer(
                getattr(self, name),
                f"phase12.validation.{name}",
                minimum=1,
                maximum=1_000_000,
            )
        if any(not isinstance(value, bool) for value in self.binding_checks.values()):
            raise SchemaValidationError(
                "phase12.validation.binding_checks",
                "checks must be Boolean",
            )
        normalized = tuple(
            sorted(set(self.reason_codes), key=lambda item: item.value.encode("utf-8"))
        )
        object.__setattr__(self, "reason_codes", normalized)

    @property
    def accepted(self) -> bool:
        return not self.reason_codes and all(self.binding_checks.values())

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "invocation_hash": self.invocation_hash,
            "program_hash": self.program_hash,
            "active_generator_generation": self.active_generator_generation,
            "active_planner_generation": self.active_planner_generation,
            "requested_generator_generation": self.requested_generator_generation,
            "requested_planner_generation": self.requested_planner_generation,
            "binding_checks": {
                key: self.binding_checks[key]
                for key in sorted(self.binding_checks, key=lambda item: item.encode("utf-8"))
            },
            "reason_codes": [item.value for item in self.reason_codes],
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class Phase12ProgressLedger:
    total_budget_hash: str
    generator_invocations: int
    rejected_attempts: int
    candidate_realizations: int
    candidate_evaluations: int
    accepted_promotions: int
    frontier_expansions: int
    manual_repairs: int

    schema_id: ClassVar[str] = "runtime.v3.phase12.progress_ledger.v1"

    def __post_init__(self) -> None:
        validate_hash256(self.total_budget_hash, "phase12.ledger.total_budget_hash")
        for name in (
            "generator_invocations",
            "rejected_attempts",
            "candidate_realizations",
            "candidate_evaluations",
            "accepted_promotions",
            "frontier_expansions",
            "manual_repairs",
        ):
            require_structural_integer(
                getattr(self, name),
                f"phase12.ledger.{name}",
                minimum=0,
                maximum=1_000_000,
            )
        if self.manual_repairs != 0:
            raise SchemaValidationError(
                "phase12.ledger.manual_repairs",
                "manual repair is forbidden",
            )
        if self.accepted_promotions > PHASE12_REQUIRED_ACCEPTED_PROMOTIONS:
            raise SchemaValidationError(
                "phase12.ledger.accepted_promotions",
                "accepted promotions exceed the precommitted target",
            )
        if self.frontier_expansions != self.accepted_promotions:
            raise SchemaValidationError(
                "phase12.ledger.frontier_expansions",
                "every accepted promotion must contribute exactly one frontier expansion",
            )

    @property
    def target_frontier_cardinality(self) -> int:
        return PHASE12_TARGET_FRONTIER_CARDINALITY

    @property
    def ledger_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "total_budget_hash": self.total_budget_hash,
            "generator_invocations": self.generator_invocations,
            "rejected_attempts": self.rejected_attempts,
            "candidate_realizations": self.candidate_realizations,
            "candidate_evaluations": self.candidate_evaluations,
            "accepted_promotions": self.accepted_promotions,
            "frontier_expansions": self.frontier_expansions,
            "manual_repairs": self.manual_repairs,
            "target_frontier_cardinality": self.target_frontier_cardinality,
        }


__all__ = [
    "Phase12ProgressLedger",
    "Phase12StartReasonCode",
    "Phase12StartValidationReport",
    "Phase12TrajectoryBudget",
    "default_phase12_trajectory_budget",
]
