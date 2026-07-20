from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer

from rcp_rclm_runtime_v3.phase11.constants import (
    ACTIVE_GENERATOR_GENERATION,
    ACTIVE_PLANNER_GENERATION,
    PHASE11_ARCHITECTURE_MUTATION,
    PHASE11_DATA_SELECTION,
    PHASE11_OBJECTIVE,
    PHASE11_PROGRAM_VERSION,
    PHASE11_ROLLBACK_MODE,
    PHASE11_SLICE_VERSION,
)


class Phase11ReasonCode(StrEnum):
    BINDING_MISMATCH = "PHASE11_BINDING_MISMATCH"
    BUDGET_EXCEEDED = "PHASE11_BUDGET_EXCEEDED"
    EXPECTED_COMPONENT_MISMATCH = "PHASE11_EXPECTED_COMPONENT_MISMATCH"
    FORBIDDEN_UPDATE_CLASS = "PHASE11_FORBIDDEN_UPDATE_CLASS"
    GENERATION_NOT_ADVANCED = "PHASE11_GENERATION_NOT_ADVANCED"
    HELDOUT_ACCESS_REQUESTED = "PHASE11_HELDOUT_ACCESS_REQUESTED"
    OBJECTIVE_MISMATCH = "PHASE11_OBJECTIVE_MISMATCH"
    OUTPUT_BUDGET_EXCEEDED = "PHASE11_OUTPUT_BUDGET_EXCEEDED"
    PROGRAM_MALFORMED = "PHASE11_PROGRAM_MALFORMED"
    ROLLBACK_NOT_EXACT = "PHASE11_ROLLBACK_NOT_EXACT"


def _require_hash(value: str, path: str) -> None:
    validate_hash256(value, path)


def _sorted_unique(values: Sequence[str], path: str) -> tuple[str, ...]:
    normalized = tuple(values)
    if any(not isinstance(item, str) or not item for item in normalized):
        raise SchemaValidationError(path, "entries must be nonempty strings")
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError(path, "entries must be unique")
    expected = tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))
    if normalized != expected:
        raise SchemaValidationError(path, "entries must be sorted by UTF-8 bytes")
    return normalized


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    wall_clock_seconds: int
    accelerator_count: int
    training_steps: int
    output_bytes: int
    candidate_count: int
    evaluation_calls: int

    schema_id: ClassVar[str] = "runtime.v3.phase11.resource_request.v1"

    def __post_init__(self) -> None:
        for name, value, minimum in (
            ("wall_clock_seconds", self.wall_clock_seconds, 1),
            ("accelerator_count", self.accelerator_count, 0),
            ("training_steps", self.training_steps, 0),
            ("output_bytes", self.output_bytes, 1),
            ("candidate_count", self.candidate_count, 1),
            ("evaluation_calls", self.evaluation_calls, 1),
        ):
            require_structural_integer(
                value,
                f"phase11.resource_request.{name}",
                minimum=minimum,
                maximum=65_536,
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "wall_clock_seconds": self.wall_clock_seconds,
            "accelerator_count": self.accelerator_count,
            "training_steps": self.training_steps,
            "output_bytes": self.output_bytes,
            "candidate_count": self.candidate_count,
            "evaluation_calls": self.evaluation_calls,
        }


@dataclass(frozen=True, slots=True)
class InvocationBudget:
    max_wall_clock_seconds: int
    max_accelerator_count: int
    max_training_steps: int
    max_output_bytes: int
    max_candidate_count: int
    max_evaluation_calls: int

    schema_id: ClassVar[str] = "runtime.v3.phase11.invocation_budget.v1"

    def __post_init__(self) -> None:
        require_structural_integer(
            self.max_wall_clock_seconds,
            "phase11.budget.max_wall_clock_seconds",
            minimum=1,
            maximum=300,
        )
        require_structural_integer(
            self.max_accelerator_count,
            "phase11.budget.max_accelerator_count",
            minimum=0,
            maximum=8,
        )
        require_structural_integer(
            self.max_training_steps,
            "phase11.budget.max_training_steps",
            minimum=0,
            maximum=10_000,
        )
        require_structural_integer(
            self.max_output_bytes,
            "phase11.budget.max_output_bytes",
            minimum=1,
            maximum=65_536,
        )
        require_structural_integer(
            self.max_candidate_count,
            "phase11.budget.max_candidate_count",
            minimum=1,
            maximum=1_024,
        )
        require_structural_integer(
            self.max_evaluation_calls,
            "phase11.budget.max_evaluation_calls",
            minimum=1,
            maximum=10_000,
        )

    @property
    def budget_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def permits(self, request: ResourceRequest) -> bool:
        return (
            request.wall_clock_seconds <= self.max_wall_clock_seconds
            and request.accelerator_count <= self.max_accelerator_count
            and request.training_steps <= self.max_training_steps
            and request.output_bytes <= self.max_output_bytes
            and request.candidate_count <= self.max_candidate_count
            and request.evaluation_calls <= self.max_evaluation_calls
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "max_wall_clock_seconds": self.max_wall_clock_seconds,
            "max_accelerator_count": self.max_accelerator_count,
            "max_training_steps": self.max_training_steps,
            "max_output_bytes": self.max_output_bytes,
            "max_candidate_count": self.max_candidate_count,
            "max_evaluation_calls": self.max_evaluation_calls,
        }


@dataclass(frozen=True, slots=True)
class TrainingDirective:
    optimizer: str
    steps: int
    learning_rate_numerator: int
    learning_rate_denominator: int
    seed: int

    schema_id: ClassVar[str] = "runtime.v3.phase11.training_directive.v1"

    def __post_init__(self) -> None:
        if self.optimizer != "sgd":
            raise SchemaValidationError("phase11.training.optimizer", "selected slice permits SGD")
        require_structural_integer(self.steps, "phase11.training.steps", minimum=0, maximum=10_000)
        require_structural_integer(
            self.learning_rate_numerator,
            "phase11.training.learning_rate_numerator",
            minimum=0,
            maximum=10_000,
        )
        require_structural_integer(
            self.learning_rate_denominator,
            "phase11.training.learning_rate_denominator",
            minimum=1,
            maximum=10_000,
        )
        require_structural_integer(self.seed, "phase11.training.seed", minimum=0, maximum=2**31 - 1)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "optimizer": self.optimizer,
            "steps": self.steps,
            "learning_rate_numerator": self.learning_rate_numerator,
            "learning_rate_denominator": self.learning_rate_denominator,
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class DataSelectionDirective:
    selection_id: str
    heldout_task_ids_visible: bool
    heldout_prompts_visible: bool
    heldout_reference_answers_visible: bool

    schema_id: ClassVar[str] = "runtime.v3.phase11.data_selection_directive.v1"

    def __post_init__(self) -> None:
        if self.selection_id != PHASE11_DATA_SELECTION:
            raise SchemaValidationError("phase11.data.selection_id", "unsupported data selection")
        for name in (
            "heldout_task_ids_visible",
            "heldout_prompts_visible",
            "heldout_reference_answers_visible",
        ):
            if not isinstance(getattr(self, name), bool):
                raise SchemaValidationError(f"phase11.data.{name}", "expected Boolean")

    @property
    def heldout_material_visible(self) -> bool:
        return any(
            (
                self.heldout_task_ids_visible,
                self.heldout_prompts_visible,
                self.heldout_reference_answers_visible,
            )
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "selection_id": self.selection_id,
            "heldout_task_ids_visible": self.heldout_task_ids_visible,
            "heldout_prompts_visible": self.heldout_prompts_visible,
            "heldout_reference_answers_visible": self.heldout_reference_answers_visible,
        }


@dataclass(frozen=True, slots=True)
class ArchitectureMutationDirective:
    kind: str
    lora_rank: int
    target_modules: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase11.architecture_mutation_directive.v1"

    def __post_init__(self) -> None:
        if self.kind != PHASE11_ARCHITECTURE_MUTATION:
            raise SchemaValidationError("phase11.architecture.kind", "unsupported architecture mutation")
        require_structural_integer(self.lora_rank, "phase11.architecture.lora_rank", minimum=0, maximum=64)
        normalized = _sorted_unique(tuple(self.target_modules), "phase11.architecture.target_modules")
        if self.kind == "none" and (self.lora_rank != 0 or normalized):
            raise SchemaValidationError(
                "phase11.architecture",
                "no architecture mutation requires zero rank and no targets",
            )
        object.__setattr__(self, "target_modules", normalized)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "kind": self.kind,
            "lora_rank": self.lora_rank,
            "target_modules": list(self.target_modules),
        }


@dataclass(frozen=True, slots=True)
class RollbackDeclaration:
    mode: str
    predecessor_bytes_required: bool

    schema_id: ClassVar[str] = "runtime.v3.phase11.rollback_declaration.v1"

    def __post_init__(self) -> None:
        if self.mode != PHASE11_ROLLBACK_MODE:
            raise SchemaValidationError("phase11.rollback.mode", "unsupported rollback mode")
        if not isinstance(self.predecessor_bytes_required, bool):
            raise SchemaValidationError(
                "phase11.rollback.predecessor_bytes_required",
                "expected Boolean",
            )

    @property
    def exact(self) -> bool:
        return self.mode == PHASE11_ROLLBACK_MODE and self.predecessor_bytes_required

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "mode": self.mode,
            "predecessor_bytes_required": self.predecessor_bytes_required,
        }


@dataclass(frozen=True, slots=True)
class TypedMutationProgram:
    objective: str
    selected_update_classes: Sequence[str]
    training_policy: TrainingDirective
    data_selection: DataSelectionDirective
    architecture_mutation: ArchitectureMutationDirective
    resource_request: ResourceRequest
    expected_affected_components: Sequence[str]
    rollback_declaration: RollbackDeclaration
    successor_generator_generation: int
    successor_planner_generation: int
    program_version: str = PHASE11_PROGRAM_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase11.typed_mutation_program.v1"

    def __post_init__(self) -> None:
        if self.program_version != PHASE11_PROGRAM_VERSION:
            raise SchemaValidationError("phase11.program.program_version", "unsupported version")
        if self.objective != PHASE11_OBJECTIVE:
            raise SchemaValidationError("phase11.program.objective", "unsupported objective")
        object.__setattr__(
            self,
            "selected_update_classes",
            _sorted_unique(tuple(self.selected_update_classes), "phase11.program.selected_update_classes"),
        )
        object.__setattr__(
            self,
            "expected_affected_components",
            _sorted_unique(
                tuple(self.expected_affected_components),
                "phase11.program.expected_affected_components",
            ),
        )
        require_structural_integer(
            self.successor_generator_generation,
            "phase11.program.successor_generator_generation",
            minimum=1,
            maximum=1_000_000,
        )
        require_structural_integer(
            self.successor_planner_generation,
            "phase11.program.successor_planner_generation",
            minimum=1,
            maximum=1_000_000,
        )
        if self.training_policy.steps != self.resource_request.training_steps:
            raise SchemaValidationError(
                "phase11.program.training_policy.steps",
                "training steps must equal the resource request",
            )

    @property
    def program_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "program_version": self.program_version,
            "objective": self.objective,
            "selected_update_classes": list(self.selected_update_classes),
            "training_policy": self.training_policy.to_json(),
            "data_selection": self.data_selection.to_json(),
            "architecture_mutation": self.architecture_mutation.to_json(),
            "resource_request": self.resource_request.to_json(),
            "expected_affected_components": list(self.expected_affected_components),
            "rollback_declaration": self.rollback_declaration.to_json(),
            "successor_generator_generation": self.successor_generator_generation,
            "successor_planner_generation": self.successor_planner_generation,
        }


@dataclass(frozen=True, slots=True)
class ModelGeneratorInput:
    transition_id: str
    invocation_id: str
    invocation_index: int
    active_package_hash: str
    active_state_hash: str
    model_identity_hash: str
    active_generator_hash: str
    active_planner_hash: str
    proposal_protocol_hash: str
    objective_hash: str
    observation_hash: str
    budget: InvocationBudget
    manual_repair_count: int = 0
    contract_version: str = PHASE11_SLICE_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase11.model_generator_input.v1"

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase11.input.transition_id")
        require_string(self.invocation_id, "phase11.input.invocation_id")
        require_structural_integer(
            self.invocation_index,
            "phase11.input.invocation_index",
            minimum=0,
            maximum=1_000_000,
        )
        for name in (
            "active_package_hash",
            "active_state_hash",
            "model_identity_hash",
            "active_generator_hash",
            "active_planner_hash",
            "proposal_protocol_hash",
            "objective_hash",
            "observation_hash",
        ):
            _require_hash(getattr(self, name), f"phase11.input.{name}")
        require_structural_integer(
            self.manual_repair_count,
            "phase11.input.manual_repair_count",
            minimum=0,
            maximum=1_000_000,
        )
        if self.manual_repair_count != 0:
            raise SchemaValidationError("phase11.input.manual_repair_count", "manual repair is forbidden")
        if self.contract_version != PHASE11_SLICE_VERSION:
            raise SchemaValidationError("phase11.input.contract_version", "version mismatch")

    @property
    def input_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "invocation_id": self.invocation_id,
            "invocation_index": self.invocation_index,
            "active_package_hash": self.active_package_hash,
            "active_state_hash": self.active_state_hash,
            "model_identity_hash": self.model_identity_hash,
            "active_generator_hash": self.active_generator_hash,
            "active_planner_hash": self.active_planner_hash,
            "proposal_protocol_hash": self.proposal_protocol_hash,
            "objective_hash": self.objective_hash,
            "observation_hash": self.observation_hash,
            "budget": self.budget.to_json(),
            "manual_repair_count": self.manual_repair_count,
        }


@dataclass(frozen=True, slots=True)
class GeneratorDecodeStep:
    position: int
    state_token_id: int
    selected_token_id: int
    selected_score: int
    runner_up_score: int
    distribution_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase11.generator_decode_step.v1"

    def __post_init__(self) -> None:
        for name in ("position", "state_token_id", "selected_token_id"):
            require_structural_integer(
                getattr(self, name),
                f"phase11.decode_step.{name}",
                minimum=0,
                maximum=1_000_000,
            )
        if isinstance(self.selected_score, bool) or not isinstance(self.selected_score, int):
            raise SchemaValidationError("phase11.decode_step.selected_score", "expected integer")
        if isinstance(self.runner_up_score, bool) or not isinstance(self.runner_up_score, int):
            raise SchemaValidationError("phase11.decode_step.runner_up_score", "expected integer")
        _require_hash(self.distribution_hash, "phase11.decode_step.distribution_hash")

    @property
    def margin(self) -> int:
        return self.selected_score - self.runner_up_score

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "position": self.position,
            "state_token_id": self.state_token_id,
            "selected_token_id": self.selected_token_id,
            "selected_score": self.selected_score,
            "runner_up_score": self.runner_up_score,
            "margin": self.margin,
            "distribution_hash": self.distribution_hash,
        }


@dataclass(frozen=True, slots=True)
class GeneratorInvocationReport:
    generator_input: ModelGeneratorInput
    program_text: str
    program_raw_sha256: str
    program: TypedMutationProgram
    steps: Sequence[GeneratorDecodeStep]
    stopped_on_eos: bool
    package_hash: str
    model_identity_hash: str
    generator_policy_hash: str
    planner_policy_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase11.generator_invocation_report.v1"

    def __post_init__(self) -> None:
        require_string(self.program_text, "phase11.invocation.program_text")
        _require_hash(self.program_raw_sha256, "phase11.invocation.program_raw_sha256")
        for name in (
            "package_hash",
            "model_identity_hash",
            "generator_policy_hash",
            "planner_policy_hash",
        ):
            _require_hash(getattr(self, name), f"phase11.invocation.{name}")
        object.__setattr__(self, "steps", tuple(self.steps))
        if not isinstance(self.stopped_on_eos, bool):
            raise SchemaValidationError("phase11.invocation.stopped_on_eos", "expected Boolean")
        if not self.steps:
            raise SchemaValidationError("phase11.invocation.steps", "at least one model step is required")

    @property
    def model_generated(self) -> bool:
        return self.stopped_on_eos and all(step.margin > 0 for step in self.steps)

    @property
    def output_within_budget(self) -> bool:
        return len(self.program_text.encode("ascii")) <= self.generator_input.budget.max_output_bytes

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "generator_input": self.generator_input.to_json(),
            "input_hash": self.generator_input.input_hash,
            "program_text": self.program_text,
            "program_raw_sha256": self.program_raw_sha256,
            "program": self.program.to_json(),
            "program_hash": self.program.program_hash,
            "steps": [step.to_json() for step in self.steps],
            "stopped_on_eos": self.stopped_on_eos,
            "model_generated": self.model_generated,
            "output_within_budget": self.output_within_budget,
            "package_hash": self.package_hash,
            "model_identity_hash": self.model_identity_hash,
            "generator_policy_hash": self.generator_policy_hash,
            "planner_policy_hash": self.planner_policy_hash,
        }


@dataclass(frozen=True, slots=True)
class ProgramValidationReport:
    invocation_hash: str
    program_hash: str
    reason_codes: Sequence[Phase11ReasonCode]
    binding_checks: dict[str, bool]

    schema_id: ClassVar[str] = "runtime.v3.phase11.program_validation_report.v1"

    def __post_init__(self) -> None:
        _require_hash(self.invocation_hash, "phase11.validation.invocation_hash")
        _require_hash(self.program_hash, "phase11.validation.program_hash")
        normalized = tuple(self.reason_codes)
        if len(set(normalized)) != len(normalized):
            raise SchemaValidationError("phase11.validation.reason_codes", "duplicate reason code")
        object.__setattr__(
            self,
            "reason_codes",
            tuple(sorted(normalized, key=lambda item: item.value.encode("utf-8"))),
        )
        if any(not isinstance(value, bool) for value in self.binding_checks.values()):
            raise SchemaValidationError("phase11.validation.binding_checks", "checks must be Boolean")

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
            "reason_codes": [reason.value for reason in self.reason_codes],
            "binding_checks": {
                key: self.binding_checks[key]
                for key in sorted(self.binding_checks, key=lambda item: item.encode("utf-8"))
            },
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class BudgetLedger:
    budget_hash: str
    generator_invocations: int
    candidate_count_consumed: int
    evaluation_calls_consumed: int
    manual_repair_count: int

    schema_id: ClassVar[str] = "runtime.v3.phase11.budget_ledger.v1"

    def __post_init__(self) -> None:
        _require_hash(self.budget_hash, "phase11.ledger.budget_hash")
        for name in (
            "generator_invocations",
            "candidate_count_consumed",
            "evaluation_calls_consumed",
            "manual_repair_count",
        ):
            require_structural_integer(
                getattr(self, name),
                f"phase11.ledger.{name}",
                minimum=0,
                maximum=1_000_000,
            )
        if self.manual_repair_count != 0:
            raise SchemaValidationError("phase11.ledger.manual_repair_count", "manual repair is forbidden")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "budget_hash": self.budget_hash,
            "generator_invocations": self.generator_invocations,
            "candidate_count_consumed": self.candidate_count_consumed,
            "evaluation_calls_consumed": self.evaluation_calls_consumed,
            "manual_repair_count": self.manual_repair_count,
        }


def default_phase11_budget() -> InvocationBudget:
    return InvocationBudget(
        max_wall_clock_seconds=1,
        max_accelerator_count=0,
        max_training_steps=1,
        max_output_bytes=96,
        max_candidate_count=2,
        max_evaluation_calls=2,
    )


def active_generations() -> tuple[int, int]:
    return ACTIVE_GENERATOR_GENERATION, ACTIVE_PLANNER_GENERATION


__all__ = [
    "ArchitectureMutationDirective",
    "BudgetLedger",
    "DataSelectionDirective",
    "GeneratorDecodeStep",
    "GeneratorInvocationReport",
    "InvocationBudget",
    "ModelGeneratorInput",
    "Phase11ReasonCode",
    "ProgramValidationReport",
    "ResourceRequest",
    "RollbackDeclaration",
    "TrainingDirective",
    "TypedMutationProgram",
    "active_generations",
    "default_phase11_budget",
]
