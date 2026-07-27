from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.gatee.constants import (
    ATTEMPT_SCHEMA_ID,
    CONTRACT_VERSION,
    EXHAUSTION_SCHEMA_ID,
    FRONTIER_SCHEMA_ID,
    REPORT_SCHEMA_ID,
    RESULT_KINDS,
    ROUTE_HINT_SCHEMA_ID,
)


def _nonempty_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(path, "expected nonempty string")
    return value


def _nonnegative_int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaValidationError(path, "expected nonnegative integer")
    return value


def _sorted_unique(values: tuple[str, ...], path: str, *, nonempty: bool = False) -> tuple[str, ...]:
    normalized = tuple(_nonempty_text(value, f"{path}[{index}]") for index, value in enumerate(values))
    if nonempty and not normalized:
        raise SchemaValidationError(path, "at least one entry is required")
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError(path, "duplicate entry")
    expected = tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))
    if normalized != expected:
        raise SchemaValidationError(path, "entries must be sorted by UTF-8 bytes")
    return normalized


@dataclass(frozen=True, slots=True)
class RouteHintPolicy:
    next_successful_transition_index_present: bool = False
    required_successful_component_set_present: bool = False
    accepted_program_bytes_present: bool = False
    expected_candidate_hash_present: bool = False
    expected_new_capability_present: bool = False
    expected_final_model_identity_present: bool = False
    host_selected_objective_present: bool = False

    schema_id: Final[str] = ROUTE_HINT_SCHEMA_ID

    def __post_init__(self) -> None:
        for field_name, value in self.to_json().items():
            if field_name == "schema_id":
                continue
            if not isinstance(value, bool):
                raise SchemaValidationError(f"route_hints.{field_name}", "expected Boolean")
            if value:
                raise SchemaValidationError(f"route_hints.{field_name}", "forbidden host route hint")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted_program_bytes_present": self.accepted_program_bytes_present,
            "expected_candidate_hash_present": self.expected_candidate_hash_present,
            "expected_final_model_identity_present": self.expected_final_model_identity_present,
            "expected_new_capability_present": self.expected_new_capability_present,
            "host_selected_objective_present": self.host_selected_objective_present,
            "next_successful_transition_index_present": self.next_successful_transition_index_present,
            "required_successful_component_set_present": self.required_successful_component_set_present,
        }


@dataclass(frozen=True, slots=True)
class FrontierSnapshot:
    capability_tasks: tuple[str, ...]
    recursive_productivity_tasks: tuple[str, ...]

    schema_id: Final[str] = FRONTIER_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_tasks",
            _sorted_unique(self.capability_tasks, "frontier.capability_tasks"),
        )
        object.__setattr__(
            self,
            "recursive_productivity_tasks",
            _sorted_unique(
                self.recursive_productivity_tasks,
                "frontier.recursive_productivity_tasks",
            ),
        )

    @property
    def frontier_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "capability_tasks": list(self.capability_tasks),
            "recursive_productivity_tasks": list(self.recursive_productivity_tasks),
        }


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    attempt_index: int
    objective_id: str
    update_kinds: tuple[str, ...]
    program_hash: str
    candidate_hash: str
    gate_d_certificate_hash: str
    package_generated: bool
    evaluator_accepted: bool
    reason_codes: tuple[str, ...]
    capability_frontier_after: tuple[str, ...]
    recursive_productivity_frontier_after: tuple[str, ...]
    search_cost: int

    schema_id: Final[str] = ATTEMPT_SCHEMA_ID

    def __post_init__(self) -> None:
        _nonnegative_int(self.attempt_index, "attempt.attempt_index")
        _nonempty_text(self.objective_id, "attempt.objective_id")
        object.__setattr__(
            self,
            "update_kinds",
            _sorted_unique(self.update_kinds, "attempt.update_kinds", nonempty=True),
        )
        validate_hash256(self.program_hash, "attempt.program_hash")
        validate_hash256(self.candidate_hash, "attempt.candidate_hash")
        validate_hash256(self.gate_d_certificate_hash, "attempt.gate_d_certificate_hash")
        if not isinstance(self.package_generated, bool) or not self.package_generated:
            raise SchemaValidationError("attempt.package_generated", "active package generation is required")
        if not isinstance(self.evaluator_accepted, bool):
            raise SchemaValidationError("attempt.evaluator_accepted", "expected Boolean")
        object.__setattr__(
            self,
            "reason_codes",
            _sorted_unique(self.reason_codes, "attempt.reason_codes"),
        )
        if self.evaluator_accepted and self.reason_codes:
            raise SchemaValidationError("attempt.reason_codes", "accepted attempt must have no rejection reasons")
        if not self.evaluator_accepted and not self.reason_codes:
            raise SchemaValidationError("attempt.reason_codes", "rejected attempt requires a reason")
        object.__setattr__(
            self,
            "capability_frontier_after",
            _sorted_unique(
                self.capability_frontier_after,
                "attempt.capability_frontier_after",
            ),
        )
        object.__setattr__(
            self,
            "recursive_productivity_frontier_after",
            _sorted_unique(
                self.recursive_productivity_frontier_after,
                "attempt.recursive_productivity_frontier_after",
            ),
        )
        _nonnegative_int(self.search_cost, "attempt.search_cost")

    @property
    def attempt_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attempt_index": self.attempt_index,
            "objective_id": self.objective_id,
            "update_kinds": list(self.update_kinds),
            "program_hash": self.program_hash,
            "candidate_hash": self.candidate_hash,
            "gate_d_certificate_hash": self.gate_d_certificate_hash,
            "package_generated": self.package_generated,
            "evaluator_accepted": self.evaluator_accepted,
            "reason_codes": list(self.reason_codes),
            "capability_frontier_after": list(self.capability_frontier_after),
            "recursive_productivity_frontier_after": list(
                self.recursive_productivity_frontier_after
            ),
            "search_cost": self.search_cost,
            "attempt_hash": self.attempt_hash_without_self(),
        }

    def attempt_hash_without_self(self) -> str:
        value = {
            "schema_id": self.schema_id,
            "attempt_index": self.attempt_index,
            "objective_id": self.objective_id,
            "update_kinds": list(self.update_kinds),
            "program_hash": self.program_hash,
            "candidate_hash": self.candidate_hash,
            "gate_d_certificate_hash": self.gate_d_certificate_hash,
            "package_generated": self.package_generated,
            "evaluator_accepted": self.evaluator_accepted,
            "reason_codes": list(self.reason_codes),
            "capability_frontier_after": list(self.capability_frontier_after),
            "recursive_productivity_frontier_after": list(
                self.recursive_productivity_frontier_after
            ),
            "search_cost": self.search_cost,
        }
        return canonical_json_hash(value)


@dataclass(frozen=True, slots=True)
class SearchExhaustionCertificate:
    enumeration_hash: str
    attempt_hashes: tuple[str, ...]
    complete_coverage: bool
    all_attempts_classified: bool
    no_accepted_attempt: bool

    schema_id: Final[str] = EXHAUSTION_SCHEMA_ID

    def __post_init__(self) -> None:
        validate_hash256(self.enumeration_hash, "exhaustion.enumeration_hash")
        if not self.attempt_hashes:
            raise SchemaValidationError("exhaustion.attempt_hashes", "at least one attempt is required")
        for index, value in enumerate(self.attempt_hashes):
            validate_hash256(value, f"exhaustion.attempt_hashes[{index}]")
        if len(set(self.attempt_hashes)) != len(self.attempt_hashes):
            raise SchemaValidationError("exhaustion.attempt_hashes", "duplicate attempt hash")
        if self.complete_coverage is not True:
            raise SchemaValidationError("exhaustion.complete_coverage", "complete coverage is required")
        if self.all_attempts_classified is not True:
            raise SchemaValidationError(
                "exhaustion.all_attempts_classified",
                "every attempt must be classified",
            )
        if self.no_accepted_attempt is not True:
            raise SchemaValidationError(
                "exhaustion.no_accepted_attempt",
                "exhaustion cannot contain an accepted attempt",
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "enumeration_hash": self.enumeration_hash,
            "attempt_hashes": list(self.attempt_hashes),
            "complete_coverage": self.complete_coverage,
            "all_attempts_classified": self.all_attempts_classified,
            "no_accepted_attempt": self.no_accepted_attempt,
        }


@dataclass(frozen=True, slots=True)
class AutonomousSearchReport:
    source_package_hash: str
    history_hash: str
    challenge_commitment_hash: str
    route_hints: RouteHintPolicy
    predecessor_frontier: FrontierSnapshot
    attempts: tuple[AttemptRecord, ...]
    search_budget: int
    manual_repairs: int
    heldout_material_visible_before_freeze: bool
    result_kind: str
    selected_attempt_index: int | None
    exhaustion: SearchExhaustionCertificate | None

    schema_id: Final[str] = REPORT_SCHEMA_ID
    contract_version: Final[str] = CONTRACT_VERSION

    def __post_init__(self) -> None:
        validate_hash256(self.source_package_hash, "report.source_package_hash")
        validate_hash256(self.history_hash, "report.history_hash")
        validate_hash256(self.challenge_commitment_hash, "report.challenge_commitment_hash")
        if not self.attempts:
            raise SchemaValidationError("report.attempts", "at least one attempt is required")
        _nonnegative_int(self.search_budget, "report.search_budget")
        _nonnegative_int(self.manual_repairs, "report.manual_repairs")
        if not isinstance(self.heldout_material_visible_before_freeze, bool):
            raise SchemaValidationError(
                "report.heldout_material_visible_before_freeze",
                "expected Boolean",
            )
        if self.result_kind not in RESULT_KINDS:
            raise SchemaValidationError("report.result_kind", "unsupported result kind")
        if self.selected_attempt_index is not None:
            _nonnegative_int(self.selected_attempt_index, "report.selected_attempt_index")

    @property
    def enumeration_hash(self) -> str:
        return canonical_json_hash([attempt.attempt_hash for attempt in self.attempts])

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json(include_hash=False))

    def to_json(self, *, include_hash: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "source_package_hash": self.source_package_hash,
            "history_hash": self.history_hash,
            "challenge_commitment_hash": self.challenge_commitment_hash,
            "route_hints": self.route_hints.to_json(),
            "predecessor_frontier": self.predecessor_frontier.to_json(),
            "attempts": [attempt.to_json() for attempt in self.attempts],
            "enumeration_hash": self.enumeration_hash,
            "search_budget": self.search_budget,
            "manual_repairs": self.manual_repairs,
            "heldout_material_visible_before_freeze": self.heldout_material_visible_before_freeze,
            "result_kind": self.result_kind,
            "selected_attempt_index": self.selected_attempt_index,
            "exhaustion": None if self.exhaustion is None else self.exhaustion.to_json(),
            "gate_e_closed": False,
            "phase14_exit_closed": False,
        }
        if include_hash:
            value["report_hash"] = self.report_hash
        return value
