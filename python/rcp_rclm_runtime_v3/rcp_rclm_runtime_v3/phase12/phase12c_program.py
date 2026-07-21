from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    PHASE11B_ARCHITECTURE_MUTATION,
    PHASE11B_DATA_SELECTION_ALPHA,
    PHASE11B_OBJECTIVE,
    PHASE11B_ROLLBACK_MODE,
)
from rcp_rclm_runtime_v3.phase11.records import (
    ArchitectureMutationDirective,
    DataSelectionDirective,
    GeneratorInvocationReport,
    ModelGeneratorInput,
    ResourceRequest,
    RollbackDeclaration,
    TrainingDirective,
    TypedMutationProgram,
)
from rcp_rclm_runtime_v3.phase12.constants import (
    PHASE12_ACTIVE_GENERATOR_GENERATION,
    PHASE12_ACTIVE_PLANNER_GENERATION,
    PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH,
    PHASE12_COMPONENT_SCHEDULE,
    PHASE12_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v3.phase12.generator import (
    generate_phase12_first_program,
    phase12_first_invocation_budget,
    phase12_objective_hash,
    phase12_package_tree_hash,
)
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import Phase12BReference

PHASE12C_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-12c"
PHASE12C_TRANSITION_ID: Final[str] = "phase12-m1-to-m2-memory-retrieval-successor"
PHASE12C_PLANNER_PROFILE: Final[str] = "generation2_memory_retrieval_schedule_projection_v1"
PHASE12C_INVALID_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=R;D=A;A=N;R=1,0,0,96,1,1;E=R;B=X;G=2;P=2"
)
PHASE12C_ACCEPTED_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=MR;D=A;A=N;R=1,0,0,96,1,1;E=MR;B=X;G=2;P=2"
)
PHASE12C_INVALID_PROGRAM_BYTES: Final[bytes] = PHASE12C_INVALID_PROGRAM_TEXT.encode("ascii")
PHASE12C_ACCEPTED_PROGRAM_BYTES: Final[bytes] = PHASE12C_ACCEPTED_PROGRAM_TEXT.encode("ascii")

ProposalKind = Literal["schedule_incomplete_rejected", "memory_retrieval_accepted"]

_UPDATE_CODE_TO_CLASS: Final[Mapping[str, str]] = {
    "M": "memory_update",
    "R": "retrieval_update",
}
_COMPONENT_CODE_TO_COMPONENT: Final[Mapping[str, str]] = {
    "M": "memory_state",
    "R": "retrieval_policy",
}
_CODE_ORDER: Final[Sequence[str]] = ("M", "R")
_FIELD_ORDER: Final[Sequence[str]] = ("O", "U", "D", "A", "R", "E", "B", "G", "P")


def _parse_uint(value: str, path: str, *, minimum: int = 0) -> int:
    if not value or any(character not in "0123456789" for character in value):
        raise SchemaValidationError(path, "expected an unsigned decimal integer")
    result = int(value)
    if result < minimum:
        raise SchemaValidationError(path, f"expected an integer >= {minimum}")
    return result


def _parse_codes(value: str, mapping: Mapping[str, str], path: str) -> Sequence[str]:
    if not value:
        raise SchemaValidationError(path, "at least one code is required")
    if len(set(value)) != len(value):
        raise SchemaValidationError(path, "duplicate code")
    unknown = tuple(code for code in value if code not in mapping)
    if unknown:
        raise SchemaValidationError(path, f"unsupported code sequence: {''.join(unknown)}")
    expected = "".join(code for code in _CODE_ORDER if code in value)
    if value != expected:
        raise SchemaValidationError(path, "codes are not in canonical order")
    return tuple(sorted((mapping[code] for code in value), key=lambda item: item.encode("utf-8")))


def _codes_for_values(
    values: Sequence[str],
    mapping: Mapping[str, str],
    path: str,
) -> str:
    inverse = {value: code for code, value in mapping.items()}
    unknown = tuple(value for value in values if value not in inverse)
    if unknown:
        raise SchemaValidationError(path, f"unsupported values: {unknown}")
    selected = {inverse[value] for value in values}
    return "".join(code for code in _CODE_ORDER if code in selected)


def encode_phase12c_program(program: TypedMutationProgram) -> bytes:
    request = program.resource_request
    update_codes = _codes_for_values(
        program.selected_update_classes,
        _UPDATE_CODE_TO_CLASS,
        "phase12c.program.selected_update_classes",
    )
    component_codes = _codes_for_values(
        program.expected_affected_components,
        _COMPONENT_CODE_TO_COMPONENT,
        "phase12c.program.expected_affected_components",
    )
    text = (
        f"V1;O=F;U={update_codes};D=A;A=N;"
        f"R={request.wall_clock_seconds},{request.accelerator_count},"
        f"{request.training_steps},{request.output_bytes},"
        f"{request.candidate_count},{request.evaluation_calls};"
        f"E={component_codes};B=X;G={program.successor_generator_generation};"
        f"P={program.successor_planner_generation}"
    )
    return text.encode("ascii")


def parse_phase12c_program(raw: bytes) -> TypedMutationProgram:
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaValidationError("phase12c.program", "program must be ASCII") from exc
    if not text or text != text.strip() or any(character.isspace() for character in text):
        raise SchemaValidationError("phase12c.program", "whitespace is forbidden")
    parts = text.split(";")
    if parts[0] != "V1" or len(parts) != len(_FIELD_ORDER) + 1:
        raise SchemaValidationError("phase12c.program", "version or field count mismatch")
    fields: dict[str, str] = {}
    for expected_key, part in zip(_FIELD_ORDER, parts[1:], strict=True):
        if "=" not in part:
            raise SchemaValidationError("phase12c.program", "field assignment is missing")
        key, value = part.split("=", 1)
        if key != expected_key:
            raise SchemaValidationError(
                "phase12c.program",
                f"expected field {expected_key}, observed {key}",
            )
        fields[key] = value
    if fields["O"] != "F" or fields["D"] != "A" or fields["A"] != "N":
        raise SchemaValidationError("phase12c.program", "unsupported objective, data, or architecture code")
    if fields["B"] != "X":
        raise SchemaValidationError("phase12c.program.rollback", "exact rollback is required")
    resource_parts = fields["R"].split(",")
    if len(resource_parts) != 6:
        raise SchemaValidationError("phase12c.program.resource", "expected six resource integers")
    wall_clock, accelerators, steps, output_bytes, candidates, evaluations = tuple(
        _parse_uint(value, f"phase12c.program.resource[{index}]")
        for index, value in enumerate(resource_parts)
    )
    program = TypedMutationProgram(
        objective=PHASE11B_OBJECTIVE,
        selected_update_classes=_parse_codes(
            fields["U"],
            _UPDATE_CODE_TO_CLASS,
            "phase12c.program.update_classes",
        ),
        training_policy=TrainingDirective(
            optimizer="sgd",
            steps=steps,
            learning_rate_numerator=1,
            learning_rate_denominator=1,
            seed=1729,
        ),
        data_selection=DataSelectionDirective(
            selection_id=PHASE11B_DATA_SELECTION_ALPHA,
            heldout_task_ids_visible=False,
            heldout_prompts_visible=False,
            heldout_reference_answers_visible=False,
        ),
        architecture_mutation=ArchitectureMutationDirective(
            kind=PHASE11B_ARCHITECTURE_MUTATION,
            lora_rank=0,
            target_modules=(),
        ),
        resource_request=ResourceRequest(
            wall_clock_seconds=wall_clock,
            accelerator_count=accelerators,
            training_steps=steps,
            output_bytes=output_bytes,
            candidate_count=candidates,
            evaluation_calls=evaluations,
        ),
        expected_affected_components=_parse_codes(
            fields["E"],
            _COMPONENT_CODE_TO_COMPONENT,
            "phase12c.program.expected_components",
        ),
        rollback_declaration=RollbackDeclaration(
            mode=PHASE11B_ROLLBACK_MODE,
            predecessor_bytes_required=True,
        ),
        successor_generator_generation=_parse_uint(
            fields["G"],
            "phase12c.program.successor_generator_generation",
            minimum=1,
        ),
        successor_planner_generation=_parse_uint(
            fields["P"],
            "phase12c.program.successor_planner_generation",
            minimum=1,
        ),
    )
    if encode_phase12c_program(program) != raw:
        raise SchemaValidationError("phase12c.program", "program is not in canonical form")
    return program


def _m1_generator_input(
    reference: Phase12BReference,
    *,
    invocation_index: int,
    observation: object,
) -> ModelGeneratorInput:
    state = reference.semantic_candidate.candidate_state
    manifest = reference.semantic_candidate.manifest
    return ModelGeneratorInput(
        transition_id=PHASE12C_TRANSITION_ID,
        invocation_id=f"phase12-m1-generation2-invocation-{invocation_index}",
        invocation_index=invocation_index,
        active_package_hash=manifest.package_hash,
        active_state_hash=state.state_hash,
        model_identity_hash=manifest.model_identity_hash,
        active_generator_hash=manifest.generator_policy_hash,
        active_planner_hash=manifest.planner_policy_hash,
        proposal_protocol_hash=PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH,
        objective_hash=phase12_objective_hash(),
        observation_hash=canonical_json_hash(observation),
        budget=phase12_first_invocation_budget(),
        manual_repair_count=0,
    )


def _planner_projection(
    draft: TypedMutationProgram,
    kind: ProposalKind,
) -> TypedMutationProgram:
    selected = (
        ("retrieval_update",)
        if kind == "schedule_incomplete_rejected"
        else ("memory_update", "retrieval_update")
    )
    components = (
        ("retrieval_policy",)
        if kind == "schedule_incomplete_rejected"
        else ("memory_state", "retrieval_policy")
    )
    return TypedMutationProgram(
        objective=draft.objective,
        selected_update_classes=selected,
        training_policy=TrainingDirective(
            optimizer=draft.training_policy.optimizer,
            steps=0,
            learning_rate_numerator=draft.training_policy.learning_rate_numerator,
            learning_rate_denominator=draft.training_policy.learning_rate_denominator,
            seed=draft.training_policy.seed,
        ),
        data_selection=draft.data_selection,
        architecture_mutation=draft.architecture_mutation,
        resource_request=ResourceRequest(
            wall_clock_seconds=1,
            accelerator_count=0,
            training_steps=0,
            output_bytes=96,
            candidate_count=1,
            evaluation_calls=1,
        ),
        expected_affected_components=components,
        rollback_declaration=draft.rollback_declaration,
        successor_generator_generation=PHASE12_ACTIVE_GENERATOR_GENERATION,
        successor_planner_generation=PHASE12_ACTIVE_PLANNER_GENERATION,
    )


@dataclass(frozen=True, slots=True)
class Phase12CProposalReport:
    kind: ProposalKind
    generator_input: ModelGeneratorInput
    model_draft: GeneratorInvocationReport
    prior_evidence_hash: str
    program_text: str
    program_raw_sha256: str
    program: TypedMutationProgram
    package_hash: str
    model_identity_hash: str
    generator_policy_hash: str
    planner_policy_hash: str
    planner_profile: str
    transition_index: int
    package_tree_hash_before: str
    package_tree_hash_after: str

    schema_id: ClassVar[str] = "runtime.v3.phase12c.proposal_report.v1"

    @property
    def package_unchanged(self) -> bool:
        return self.package_tree_hash_before == self.package_tree_hash_after

    @property
    def package_generated(self) -> bool:
        expected = (
            PHASE12C_INVALID_PROGRAM_BYTES
            if self.kind == "schedule_incomplete_rejected"
            else PHASE12C_ACCEPTED_PROGRAM_BYTES
        )
        return (
            self.model_draft.model_generated
            and self.model_draft.package_hash == self.package_hash
            and self.model_draft.model_identity_hash == self.model_identity_hash
            and self.model_draft.generator_policy_hash == self.generator_policy_hash
            and self.model_draft.planner_policy_hash == self.planner_policy_hash
            and self.generator_input.active_package_hash == self.package_hash
            and self.model_draft.generator_input.to_json()
            == self.generator_input.to_json()
            and self.generator_input.proposal_protocol_hash
            == PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH
            and self.generator_input.objective_hash == phase12_objective_hash()
            and self.planner_profile == PHASE12C_PLANNER_PROFILE
            and self.transition_index == 1
            and self.program_text.encode("ascii") == expected
            and self.program_raw_sha256 == sha256_hex(expected)
            and self.package_unchanged
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12C_CONTRACT_VERSION,
            "kind": self.kind,
            "generator_input": self.generator_input.to_json(),
            "generator_input_hash": self.generator_input.input_hash,
            "model_draft": self.model_draft.to_json(),
            "model_draft_hash": self.model_draft.report_hash,
            "prior_evidence_hash": self.prior_evidence_hash,
            "program_text": self.program_text,
            "program_raw_sha256": self.program_raw_sha256,
            "program": self.program.to_json(),
            "program_hash": self.program.program_hash,
            "package_hash": self.package_hash,
            "model_identity_hash": self.model_identity_hash,
            "generator_policy_hash": self.generator_policy_hash,
            "planner_policy_hash": self.planner_policy_hash,
            "planner_profile": self.planner_profile,
            "transition_index": self.transition_index,
            "package_tree_hash_before": self.package_tree_hash_before,
            "package_tree_hash_after": self.package_tree_hash_after,
            "package_unchanged": self.package_unchanged,
            "package_generated": self.package_generated,
            "heldout_material_consumed": False,
            "manual_repairs": 0,
        }


def generate_phase12c_proposal(
    reference: Phase12BReference,
    kind: ProposalKind,
    *,
    prior_validation_hash: str | None = None,
) -> Phase12CProposalReport:
    active_root = reference.semantic_candidate.root.resolve(strict=True)
    if kind == "schedule_incomplete_rejected":
        invocation_index = 2
        prior_evidence_hash = reference.summary_json()["summary_hash"]
        observation = {
            "schema_id": "runtime.v3.phase12c.m1_observation.v1",
            "trajectory_id": PHASE12_TRAJECTORY_ID,
            "active_state_hash": reference.semantic_candidate.candidate_state.state_hash,
            "phase12b_summary_hash": prior_evidence_hash,
            "accepted_phase12_promotions": 1,
            "prior_phase12_rejections": 1,
            "transition_index": 1,
            "required_components": PHASE12_COMPONENT_SCHEDULE[1]["required_components"],
            "heldout_answer_material_present": False,
        }
    else:
        if prior_validation_hash is None:
            raise SchemaValidationError(
                "phase12c.proposal",
                "fresh proposal requires the retained invalid-proposal validation hash",
            )
        invocation_index = 3
        prior_evidence_hash = prior_validation_hash
        observation = {
            "schema_id": "runtime.v3.phase12c.rejection_observation.v1",
            "trajectory_id": PHASE12_TRAJECTORY_ID,
            "active_state_hash": reference.semantic_candidate.candidate_state.state_hash,
            "prior_validation_hash": prior_validation_hash,
            "prior_proposal_rejected": True,
            "active_package_unchanged": True,
            "accepted_phase12_promotions": 1,
            "prior_phase12_rejections": 2,
            "transition_index": 1,
            "required_components": PHASE12_COMPONENT_SCHEDULE[1]["required_components"],
            "heldout_answer_material_present": False,
        }
    generator_input = _m1_generator_input(
        reference,
        invocation_index=invocation_index,
        observation=observation,
    )
    tree_before = phase12_package_tree_hash(active_root)
    draft = generate_phase12_first_program(active_root, generator_input)
    program = _planner_projection(draft.program, kind)
    raw = encode_phase12c_program(program)
    expected = (
        PHASE12C_INVALID_PROGRAM_BYTES
        if kind == "schedule_incomplete_rejected"
        else PHASE12C_ACCEPTED_PROGRAM_BYTES
    )
    if raw != expected:
        raise SchemaValidationError(
            "phase12c.program",
            "package-bound planner produced unexpected program bytes",
        )
    reparsed = parse_phase12c_program(raw)
    if reparsed.to_json() != program.to_json():
        raise SchemaValidationError("phase12c.program", "canonical round trip mismatch")
    tree_after = phase12_package_tree_hash(active_root)
    report = Phase12CProposalReport(
        kind=kind,
        generator_input=generator_input,
        model_draft=draft,
        prior_evidence_hash=str(prior_evidence_hash),
        program_text=raw.decode("ascii"),
        program_raw_sha256=sha256_hex(raw),
        program=program,
        package_hash=reference.semantic_candidate.manifest.package_hash,
        model_identity_hash=reference.semantic_candidate.manifest.model_identity_hash,
        generator_policy_hash=reference.semantic_candidate.manifest.generator_policy_hash,
        planner_policy_hash=reference.semantic_candidate.manifest.planner_policy_hash,
        planner_profile=PHASE12C_PLANNER_PROFILE,
        transition_index=1,
        package_tree_hash_before=tree_before,
        package_tree_hash_after=tree_after,
    )
    if not report.package_generated:
        raise ValueError("Phase 12C proposal package binding failed")
    return report


@dataclass(frozen=True, slots=True)
class Phase12CProposalValidationReport:
    proposal_hash: str
    program_hash: str
    binding_checks: Mapping[str, bool]
    reason_codes: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase12c.proposal_validation.v1"

    @property
    def accepted(self) -> bool:
        return not self.reason_codes and all(self.binding_checks.values())

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12C_CONTRACT_VERSION,
            "proposal_hash": self.proposal_hash,
            "program_hash": self.program_hash,
            "binding_checks": {
                key: self.binding_checks[key]
                for key in sorted(self.binding_checks, key=lambda item: item.encode("utf-8"))
            },
            "reason_codes": list(self.reason_codes),
            "accepted": self.accepted,
        }


def validate_phase12c_proposal(
    reference: Phase12BReference,
    proposal: Phase12CProposalReport,
) -> Phase12CProposalValidationReport:
    program = proposal.program
    manifest = reference.semantic_candidate.manifest
    state = reference.semantic_candidate.candidate_state
    expected_classes = {"memory_update", "retrieval_update"}
    expected_components = {"memory_state", "retrieval_policy"}
    selected_classes = set(program.selected_update_classes)
    selected_components = set(program.expected_affected_components)
    expected_bytes = (
        PHASE12C_INVALID_PROGRAM_BYTES
        if proposal.kind == "schedule_incomplete_rejected"
        else PHASE12C_ACCEPTED_PROGRAM_BYTES
    )
    bindings = {
        "active_package_bound": proposal.package_hash == manifest.package_hash,
        "active_state_bound": proposal.generator_input.active_state_hash == state.state_hash,
        "active_model_bound": proposal.model_identity_hash == manifest.model_identity_hash,
        "active_generator_bound": proposal.generator_policy_hash == manifest.generator_policy_hash,
        "active_planner_bound": proposal.planner_policy_hash == manifest.planner_policy_hash,
        "proposal_protocol_bound": proposal.generator_input.proposal_protocol_hash
        == PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH,
        "objective_bound": proposal.generator_input.objective_hash == phase12_objective_hash(),
        "package_generated": proposal.package_generated,
        "package_unchanged": proposal.package_unchanged,
        "heldout_material_hidden": not program.data_selection.heldout_material_visible,
        "manual_repair_absent": proposal.generator_input.manual_repair_count == 0,
        "resource_budget_respected": proposal.generator_input.budget.permits(
            program.resource_request
        ),
        "training_steps_zero": program.training_policy.steps == 0,
        "program_bytes_bound": proposal.program_text.encode("ascii") == expected_bytes,
        "generation_preserved": (
            program.successor_generator_generation == PHASE12_ACTIVE_GENERATOR_GENERATION
            and program.successor_planner_generation == PHASE12_ACTIVE_PLANNER_GENERATION
        ),
    }
    reasons: list[str] = []
    if not all(bindings.values()):
        reasons.append("PHASE12C_BINDING_MISMATCH")
    if selected_classes != expected_classes or selected_components != expected_components:
        reasons.append("PHASE12C_COMPONENT_SCHEDULE_INCOMPLETE")
    if program.resource_request.training_steps != 0:
        reasons.append("PHASE12C_TRAINING_FORBIDDEN")
    if program.data_selection.heldout_material_visible:
        reasons.append("PHASE12C_HELDOUT_ACCESS_REQUESTED")
    if proposal.generator_input.manual_repair_count != 0:
        reasons.append("PHASE12C_MANUAL_REPAIR_REQUESTED")
    if proposal.kind == "schedule_incomplete_rejected" and reasons != [
        "PHASE12C_COMPONENT_SCHEDULE_INCOMPLETE"
    ]:
        raise SchemaValidationError(
            "phase12c.validation",
            "selected invalid proposal must fail only the component schedule",
        )
    if proposal.kind == "memory_retrieval_accepted" and reasons:
        raise SchemaValidationError(
            "phase12c.validation",
            "selected fresh memory/retrieval proposal must validate",
        )
    return Phase12CProposalValidationReport(
        proposal_hash=proposal.report_hash,
        program_hash=program.program_hash,
        binding_checks=bindings,
        reason_codes=tuple(reasons),
    )


__all__ = [
    "PHASE12C_ACCEPTED_PROGRAM_BYTES",
    "PHASE12C_ACCEPTED_PROGRAM_TEXT",
    "PHASE12C_CONTRACT_VERSION",
    "PHASE12C_INVALID_PROGRAM_BYTES",
    "PHASE12C_INVALID_PROGRAM_TEXT",
    "PHASE12C_PLANNER_PROFILE",
    "PHASE12C_TRANSITION_ID",
    "Phase12CProposalReport",
    "Phase12CProposalValidationReport",
    "ProposalKind",
    "encode_phase12c_program",
    "generate_phase12c_proposal",
    "parse_phase12c_program",
    "validate_phase12c_proposal",
]
