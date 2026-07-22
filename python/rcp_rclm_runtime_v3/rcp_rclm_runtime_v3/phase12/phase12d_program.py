from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase11.phase11b_program import (
    encode_phase11b_program,
    parse_phase11b_program,
)
from rcp_rclm_runtime_v3.phase11.records import (
    GeneratorInvocationReport,
    ModelGeneratorInput,
    ResourceRequest,
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
from rcp_rclm_runtime_v3.phase12.phase12c_lifecycle import Phase12CReference

PHASE12D_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-12d"
PHASE12D_TRANSITION_ID: Final[str] = "phase12-m2-to-m3-generator-planner-successor"
PHASE12D_PLANNER_PROFILE: Final[str] = (
    "generation2_generator_planner_self_modification_projection_v1"
)
PHASE12D_SUCCESSOR_GENERATOR_GENERATION: Final[int] = 3
PHASE12D_SUCCESSOR_PLANNER_GENERATION: Final[int] = 3
PHASE12D_ACCEPTED_PROGRAM_TEXT: Final[str] = (
    "V1;O=F;U=GP;D=A;A=N;R=1,0,0,96,1,1;E=GP;B=X;G=3;P=3"
)
PHASE12D_ACCEPTED_PROGRAM_BYTES: Final[bytes] = PHASE12D_ACCEPTED_PROGRAM_TEXT.encode(
    "ascii"
)


@dataclass(frozen=True, slots=True)
class Phase12DProposalReport:
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

    schema_id: ClassVar[str] = "runtime.v3.phase12d.proposal_report.v1"

    @property
    def package_unchanged(self) -> bool:
        return self.package_tree_hash_before == self.package_tree_hash_after

    @property
    def package_generated(self) -> bool:
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
            and self.planner_profile == PHASE12D_PLANNER_PROFILE
            and self.transition_index == 2
            and self.program_text.encode("ascii") == PHASE12D_ACCEPTED_PROGRAM_BYTES
            and self.program_raw_sha256 == sha256_hex(PHASE12D_ACCEPTED_PROGRAM_BYTES)
            and self.package_unchanged
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12D_CONTRACT_VERSION,
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


@dataclass(frozen=True, slots=True)
class Phase12DProposalValidationReport:
    proposal_hash: str
    program_hash: str
    binding_checks: Mapping[str, bool]
    reason_codes: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase12d.proposal_validation.v1"

    @property
    def accepted(self) -> bool:
        return not self.reason_codes and all(self.binding_checks.values())

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12D_CONTRACT_VERSION,
            "proposal_hash": self.proposal_hash,
            "program_hash": self.program_hash,
            "binding_checks": {
                key: self.binding_checks[key]
                for key in sorted(self.binding_checks, key=lambda item: item.encode("utf-8"))
            },
            "reason_codes": list(self.reason_codes),
            "accepted": self.accepted,
        }


def _m2_generator_input(reference: Phase12CReference) -> ModelGeneratorInput:
    state = reference.semantic_candidate.candidate_state
    manifest = reference.semantic_candidate.manifest
    observation = {
        "schema_id": "runtime.v3.phase12d.m2_observation.v1",
        "trajectory_id": PHASE12_TRAJECTORY_ID,
        "active_state_hash": state.state_hash,
        "phase12c_summary_hash": reference.summary_json()["summary_hash"],
        "accepted_phase12_promotions": 2,
        "prior_phase12_rejections": 2,
        "transition_index": 2,
        "required_components": PHASE12_COMPONENT_SCHEDULE[2]["required_components"],
        "remaining_generator_invocations": 2,
        "remaining_candidate_realizations": 2,
        "remaining_candidate_evaluations": 2,
        "remaining_promotions": 2,
        "remaining_rejections": 0,
        "heldout_answer_material_present": False,
    }
    return ModelGeneratorInput(
        transition_id=PHASE12D_TRANSITION_ID,
        invocation_id="phase12-m2-generation2-invocation-4",
        invocation_index=4,
        active_package_hash=manifest.package_hash,
        active_state_hash=state.state_hash,
        model_identity_hash=manifest.model_identity_hash,
        active_generator_hash=manifest.generator_policy_hash,
        active_planner_hash=manifest.planner_policy_hash,
        proposal_protocol_hash=state.self_hosting.proposal_protocol_hash,
        objective_hash=phase12_objective_hash(),
        observation_hash=canonical_json_hash(observation),
        budget=phase12_first_invocation_budget(),
        manual_repair_count=0,
    )


def _planner_projection(draft: TypedMutationProgram) -> TypedMutationProgram:
    return TypedMutationProgram(
        objective=draft.objective,
        selected_update_classes=("generator_update", "planner_update"),
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
        expected_affected_components=("generator_policy", "planner_policy"),
        rollback_declaration=draft.rollback_declaration,
        successor_generator_generation=PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
        successor_planner_generation=PHASE12D_SUCCESSOR_PLANNER_GENERATION,
    )


def generate_phase12d_proposal(reference: Phase12CReference) -> Phase12DProposalReport:
    active_root = reference.semantic_candidate.root.resolve(strict=True)
    generator_input = _m2_generator_input(reference)
    tree_before = phase12_package_tree_hash(active_root)
    draft = generate_phase12_first_program(active_root, generator_input)
    program = _planner_projection(draft.program)
    raw = encode_phase11b_program(program)
    if raw != PHASE12D_ACCEPTED_PROGRAM_BYTES:
        raise SchemaValidationError(
            "phase12d.program",
            "package-bound planner produced unexpected generator/planner program",
        )
    reparsed = parse_phase11b_program(raw)
    if reparsed.to_json() != program.to_json():
        raise SchemaValidationError("phase12d.program", "canonical round trip mismatch")
    tree_after = phase12_package_tree_hash(active_root)
    report = Phase12DProposalReport(
        generator_input=generator_input,
        model_draft=draft,
        prior_evidence_hash=str(reference.summary_json()["summary_hash"]),
        program_text=raw.decode("ascii"),
        program_raw_sha256=sha256_hex(raw),
        program=program,
        package_hash=reference.semantic_candidate.manifest.package_hash,
        model_identity_hash=reference.semantic_candidate.manifest.model_identity_hash,
        generator_policy_hash=reference.semantic_candidate.manifest.generator_policy_hash,
        planner_policy_hash=reference.semantic_candidate.manifest.planner_policy_hash,
        planner_profile=PHASE12D_PLANNER_PROFILE,
        transition_index=2,
        package_tree_hash_before=tree_before,
        package_tree_hash_after=tree_after,
    )
    if not report.package_generated:
        raise ValueError("Phase 12D proposal package binding failed")
    return report


def validate_phase12d_proposal(
    reference: Phase12CReference,
    proposal: Phase12DProposalReport,
) -> Phase12DProposalValidationReport:
    state = reference.semantic_candidate.candidate_state
    manifest = reference.semantic_candidate.manifest
    program = proposal.program
    bindings = {
        "active_package_bound": proposal.package_hash == manifest.package_hash,
        "active_state_bound": proposal.generator_input.active_state_hash == state.state_hash,
        "active_model_bound": proposal.model_identity_hash == manifest.model_identity_hash,
        "active_generator_bound": proposal.generator_policy_hash == manifest.generator_policy_hash,
        "active_planner_bound": proposal.planner_policy_hash == manifest.planner_policy_hash,
        "proposal_protocol_bound": proposal.generator_input.proposal_protocol_hash
        == state.self_hosting.proposal_protocol_hash,
        "objective_bound": proposal.generator_input.objective_hash == phase12_objective_hash(),
        "package_generated": proposal.package_generated,
        "package_unchanged": proposal.package_unchanged,
        "heldout_material_hidden": not program.data_selection.heldout_material_visible,
        "manual_repair_absent": proposal.generator_input.manual_repair_count == 0,
        "resource_budget_respected": proposal.generator_input.budget.permits(
            program.resource_request
        ),
        "training_steps_zero": program.training_policy.steps == 0,
        "component_schedule_respected": (
            set(program.selected_update_classes) == {"generator_update", "planner_update"}
            and set(program.expected_affected_components)
            == {"generator_policy", "planner_policy"}
        ),
        "generator_generation_advanced": program.successor_generator_generation
        == PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
        "planner_generation_advanced": program.successor_planner_generation
        == PHASE12D_SUCCESSOR_PLANNER_GENERATION,
        "program_bytes_bound": proposal.program_text.encode("ascii")
        == PHASE12D_ACCEPTED_PROGRAM_BYTES,
    }
    reasons: list[str] = []
    if not all(bindings.values()):
        reasons.append("PHASE12D_BINDING_MISMATCH")
    if set(program.selected_update_classes) != {"generator_update", "planner_update"}:
        reasons.append("PHASE12D_COMPONENT_SCHEDULE_MISMATCH")
    if set(program.expected_affected_components) != {"generator_policy", "planner_policy"}:
        reasons.append("PHASE12D_EXPECTED_COMPONENT_MISMATCH")
    if (
        program.successor_generator_generation <= PHASE12_ACTIVE_GENERATOR_GENERATION
        or program.successor_planner_generation <= PHASE12_ACTIVE_PLANNER_GENERATION
    ):
        reasons.append("PHASE12D_GENERATION_NOT_ADVANCED")
    if program.resource_request.training_steps != 0:
        reasons.append("PHASE12D_TRAINING_FORBIDDEN")
    if program.data_selection.heldout_material_visible:
        reasons.append("PHASE12D_HELDOUT_ACCESS_REQUESTED")
    if proposal.generator_input.manual_repair_count != 0:
        reasons.append("PHASE12D_MANUAL_REPAIR_REQUESTED")
    unique = tuple(dict.fromkeys(reasons))
    if unique:
        raise SchemaValidationError(
            "phase12d.validation",
            "selected generator/planner proposal must validate: " + ",".join(unique),
        )
    return Phase12DProposalValidationReport(
        proposal_hash=proposal.report_hash,
        program_hash=program.program_hash,
        binding_checks=bindings,
        reason_codes=(),
    )


__all__ = [
    "PHASE12D_ACCEPTED_PROGRAM_BYTES",
    "PHASE12D_ACCEPTED_PROGRAM_TEXT",
    "PHASE12D_CONTRACT_VERSION",
    "PHASE12D_PLANNER_PROFILE",
    "PHASE12D_SUCCESSOR_GENERATOR_GENERATION",
    "PHASE12D_SUCCESSOR_PLANNER_GENERATION",
    "PHASE12D_TRANSITION_ID",
    "Phase12DProposalReport",
    "Phase12DProposalValidationReport",
    "generate_phase12d_proposal",
    "validate_phase12d_proposal",
]
