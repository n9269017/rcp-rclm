from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.codec import ordered_unique
from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_FIXED_VERIFIER_HASH,
    UpdateFamily,
    UPDATE_FAMILIES,
    cast_update_family,
)


def _nonnegative(value: int, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaValidationError(path, "expected nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class MutationProgram:
    promotion_index: int
    family: UpdateFamily
    variant: int
    generation: int
    operation_id: str
    parameter_a: int
    parameter_b: int
    public_nonce_hash: str

    schema_id: ClassVar[str] = "runtime.v4.phase16.mutation_program.v1"

    def __post_init__(self) -> None:
        _nonnegative(self.promotion_index, "phase16.program.promotion_index")
        cast_update_family(self.family)
        if self.variant not in range(4):
            raise SchemaValidationError("phase16.program.variant", "expected integer in [0, 3]")
        if self.generation <= 0:
            raise SchemaValidationError("phase16.program.generation", "expected positive integer")
        if not self.operation_id:
            raise SchemaValidationError("phase16.program.operation_id", "expected nonempty string")
        if isinstance(self.parameter_a, bool) or not isinstance(self.parameter_a, int):
            raise SchemaValidationError("phase16.program.parameter_a", "expected integer")
        if isinstance(self.parameter_b, bool) or not isinstance(self.parameter_b, int):
            raise SchemaValidationError("phase16.program.parameter_b", "expected integer")
        validate_hash256(self.public_nonce_hash, "phase16.program.public_nonce_hash")

    @property
    def program_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "promotion_index": self.promotion_index,
            "family": self.family,
            "variant": self.variant,
            "generation": self.generation,
            "operation_id": self.operation_id,
            "parameter_a": self.parameter_a,
            "parameter_b": self.parameter_b,
            "public_nonce_hash": self.public_nonce_hash,
        }


@dataclass(frozen=True, slots=True)
class ModelState:
    model_index: int
    active_package_hash: str
    component_generations: Mapping[str, int]
    installed_program_hashes: Sequence[str]
    capability_frontier: Sequence[str]
    recursive_productivity_frontier: Sequence[str]
    archive_root_hash: str
    fixed_verifier_hash: str = PHASE16_FIXED_VERIFIER_HASH
    semantics_id: str = PHASE16_DIAGONAL_SEMANTICS_ID

    schema_id: ClassVar[str] = "runtime.v4.phase16.model_state.v1"

    def __post_init__(self) -> None:
        if self.model_index < 9:
            raise SchemaValidationError("phase16.state.model_index", "model index precedes M9")
        validate_hash256(self.active_package_hash, "phase16.state.active_package_hash")
        validate_hash256(self.archive_root_hash, "phase16.state.archive_root_hash")
        validate_hash256(self.fixed_verifier_hash, "phase16.state.fixed_verifier_hash")
        if self.fixed_verifier_hash != PHASE16_FIXED_VERIFIER_HASH:
            raise SchemaValidationError("phase16.state.fixed_verifier_hash", "fixed verifier changed")
        if self.semantics_id != PHASE16_DIAGONAL_SEMANTICS_ID:
            raise SchemaValidationError("phase16.state.semantics_id", "semantic regime changed")
        generations = dict(self.component_generations)
        if set(generations) != set(UPDATE_FAMILIES):
            raise SchemaValidationError(
                "phase16.state.component_generations",
                "exact Phase 16 update-family generation map required",
            )
        for family, generation in generations.items():
            cast_update_family(family)
            _nonnegative(generation, f"phase16.state.component_generations.{family}")
        object.__setattr__(self, "component_generations", generations)
        programs = tuple(self.installed_program_hashes)
        for index, value in enumerate(programs):
            validate_hash256(value, f"phase16.state.installed_program_hashes[{index}]")
        object.__setattr__(
            self,
            "installed_program_hashes",
            ordered_unique(programs, "phase16.state.installed_program_hashes"),
        )
        object.__setattr__(
            self,
            "capability_frontier",
            ordered_unique(tuple(self.capability_frontier), "phase16.state.capability_frontier"),
        )
        object.__setattr__(
            self,
            "recursive_productivity_frontier",
            ordered_unique(
                tuple(self.recursive_productivity_frontier),
                "phase16.state.recursive_productivity_frontier",
            ),
        )

    @property
    def state_record_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "model_index": self.model_index,
            "active_package_hash": self.active_package_hash,
            "component_generations": dict(
                sorted(self.component_generations.items(), key=lambda item: item[0].encode("utf-8"))
            ),
            "installed_program_hashes": list(self.installed_program_hashes),
            "capability_frontier": list(self.capability_frontier),
            "recursive_productivity_frontier": list(self.recursive_productivity_frontier),
            "archive_root_hash": self.archive_root_hash,
            "fixed_verifier_hash": self.fixed_verifier_hash,
            "semantics_id": self.semantics_id,
        }


@dataclass(frozen=True, slots=True)
class FairSearchCertificate:
    promotion_index: int
    enumerator_id: str
    legal_program_hashes: Sequence[str]
    fair_order_hashes: Sequence[str]
    considered_program_hashes: Sequence[str]
    accepted_program_hash: str | None
    accepted_considered_index: int | None
    exhausted: bool
    resource_envelope_limits: Sequence[int]
    learned_prefix_count: int
    rejection_conditioned_steps: int

    schema_id: ClassVar[str] = "runtime.v4.phase16.fair_search_certificate.v1"

    def __post_init__(self) -> None:
        _nonnegative(self.promotion_index, "phase16.fairness.promotion_index")
        if not self.enumerator_id:
            raise SchemaValidationError("phase16.fairness.enumerator_id", "expected nonempty string")
        legal = tuple(self.legal_program_hashes)
        fair = tuple(self.fair_order_hashes)
        considered = tuple(self.considered_program_hashes)
        for path, values in (
            ("legal_program_hashes", legal),
            ("fair_order_hashes", fair),
            ("considered_program_hashes", considered),
        ):
            for index, value in enumerate(values):
                validate_hash256(value, f"phase16.fairness.{path}[{index}]")
            if len(set(values)) != len(values):
                raise SchemaValidationError(f"phase16.fairness.{path}", "duplicate program hash")
        if set(fair) != set(legal) or len(fair) != len(legal):
            raise SchemaValidationError("phase16.fairness.fair_order_hashes", "not a legal-set permutation")
        if not set(considered).issubset(set(legal)):
            raise SchemaValidationError("phase16.fairness.considered_program_hashes", "unknown program")
        if self.exhausted:
            if self.accepted_program_hash is not None or self.accepted_considered_index is not None:
                raise SchemaValidationError("phase16.fairness", "exhaustion cannot contain acceptance")
            if set(considered) != set(legal):
                raise SchemaValidationError("phase16.fairness", "exhaustion omitted a legal program")
        else:
            if self.accepted_program_hash is None or self.accepted_considered_index is None:
                raise SchemaValidationError("phase16.fairness", "acceptance evidence is missing")
            validate_hash256(self.accepted_program_hash, "phase16.fairness.accepted_program_hash")
            if self.accepted_program_hash not in considered:
                raise SchemaValidationError("phase16.fairness.accepted_program_hash", "program not considered")
            if not 0 <= self.accepted_considered_index < len(considered):
                raise SchemaValidationError(
                    "phase16.fairness.accepted_considered_index",
                    "index is outside the considered trace",
                )
            if considered[self.accepted_considered_index] != self.accepted_program_hash:
                raise SchemaValidationError("phase16.fairness.accepted_considered_index", "index mismatch")
        limits = tuple(self.resource_envelope_limits)
        if not limits or any(value <= 0 for value in limits):
            raise SchemaValidationError("phase16.fairness.resource_envelope_limits", "positive limits required")
        if tuple(sorted(set(limits))) != limits:
            raise SchemaValidationError("phase16.fairness.resource_envelope_limits", "limits must strictly expand")
        _nonnegative(self.learned_prefix_count, "phase16.fairness.learned_prefix_count")
        _nonnegative(
            self.rejection_conditioned_steps,
            "phase16.fairness.rejection_conditioned_steps",
        )
        object.__setattr__(self, "legal_program_hashes", legal)
        object.__setattr__(self, "fair_order_hashes", fair)
        object.__setattr__(self, "considered_program_hashes", considered)
        object.__setattr__(self, "resource_envelope_limits", limits)

    @property
    def certificate_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "promotion_index": self.promotion_index,
            "enumerator_id": self.enumerator_id,
            "legal_program_hashes": list(self.legal_program_hashes),
            "fair_order_hashes": list(self.fair_order_hashes),
            "considered_program_hashes": list(self.considered_program_hashes),
            "accepted_program_hash": self.accepted_program_hash,
            "accepted_considered_index": self.accepted_considered_index,
            "exhausted": self.exhausted,
            "resource_envelope_limits": list(self.resource_envelope_limits),
            "learned_prefix_count": self.learned_prefix_count,
            "rejection_conditioned_steps": self.rejection_conditioned_steps,
        }


__all__ = ["FairSearchCertificate", "ModelState", "MutationProgram"]
