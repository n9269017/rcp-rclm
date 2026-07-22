from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID, VOCAB_SIZE
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import exact_dyadic_distribution
from rcp_rclm_runtime_v3.phase11.phase11b_program import parse_phase11b_program
from rcp_rclm_runtime_v3.phase11.records import (
    DataSelectionDirective,
    GeneratorDecodeStep,
    GeneratorInvocationReport,
    ModelGeneratorInput,
    ResourceRequest,
    RollbackDeclaration,
    TrainingDirective,
)
from rcp_rclm_runtime_v3.phase11.constants import (
    PHASE11_DATA_SELECTION,
    PHASE11_OBJECTIVE,
    PHASE11_ROLLBACK_MODE,
)
from rcp_rclm_runtime_v3.phase12.constants import (
    PHASE12_COMPONENT_SCHEDULE,
    PHASE12_EXPECTED_FIRST_PROGRAM_BYTES,
    PHASE12_RECURSIVE_BANK_CAPACITY,
    PHASE12_RECURSIVE_BANK_START,
    PHASE12_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v3.phase12.generator import (
    phase12_first_invocation_budget,
    phase12_objective_hash,
    phase12_package_tree_hash,
)
from rcp_rclm_runtime_v3.phase12.phase12d_lifecycle import Phase12DReference
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import (
    PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
)

PHASE12E_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-12e"
PHASE12E_PROGRAM_VERSION: Final[str] = "V2"
PHASE12E_TRANSITION_ID: Final[str] = "phase12-m3-to-m4-adapter-optimizer-successor"
PHASE12E_PLANNER_PROFILE: Final[str] = "generation3_rank8_lora_optimizer_projection_v1"
PHASE12E_ARCHITECTURE_KIND: Final[str] = "lora_rank8"
PHASE12E_ACCEPTED_PROGRAM_TEXT: Final[str] = (
    "V2;O=F;U=ALO;D=A;A=L8;R=1,0,1,96,1,1;E=AMO;B=X;G=3;P=3"
)
PHASE12E_ACCEPTED_PROGRAM_BYTES: Final[bytes] = PHASE12E_ACCEPTED_PROGRAM_TEXT.encode("ascii")


@dataclass(frozen=True, slots=True)
class Phase12EArchitectureDirective:
    kind: str
    lora_rank: int
    target_modules: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase12e.architecture_directive.v1"

    def __post_init__(self) -> None:
        targets = tuple(sorted(self.target_modules, key=lambda item: item.encode("utf-8")))
        if self.kind != PHASE12E_ARCHITECTURE_KIND or self.lora_rank != 8 or not targets:
            raise SchemaValidationError(
                "phase12e.architecture",
                "selected final transition requires the frozen rank-8 LoRA extension",
            )
        if len(set(targets)) != len(targets):
            raise SchemaValidationError("phase12e.architecture.targets", "duplicate target")
        object.__setattr__(self, "target_modules", targets)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "kind": self.kind,
            "lora_rank": self.lora_rank,
            "target_modules": list(self.target_modules),
        }


@dataclass(frozen=True, slots=True)
class Phase12ETypedProgram:
    objective: str
    selected_update_classes: Sequence[str]
    training_policy: TrainingDirective
    data_selection: DataSelectionDirective
    architecture_mutation: Phase12EArchitectureDirective
    resource_request: ResourceRequest
    expected_affected_components: Sequence[str]
    rollback_declaration: RollbackDeclaration
    successor_generator_generation: int
    successor_planner_generation: int

    schema_id: ClassVar[str] = "runtime.v3.phase12e.typed_mutation_program.v1"

    def __post_init__(self) -> None:
        updates = tuple(sorted(self.selected_update_classes, key=lambda item: item.encode("utf-8")))
        components = tuple(sorted(self.expected_affected_components, key=lambda item: item.encode("utf-8")))
        if updates != ("adapter_update", "architecture_extension", "optimizer_policy_update"):
            raise SchemaValidationError("phase12e.program.updates", "unexpected update class set")
        if components != ("adapter_manifest", "model_architecture", "optimizer_policy"):
            raise SchemaValidationError("phase12e.program.components", "unexpected component set")
        if self.objective != PHASE11_OBJECTIVE:
            raise SchemaValidationError("phase12e.program.objective", "unexpected objective")
        if self.training_policy.optimizer != "sgd" or self.training_policy.steps != 1:
            raise SchemaValidationError("phase12e.program.training", "one SGD step is required")
        if self.data_selection.heldout_material_visible:
            raise SchemaValidationError("phase12e.program.data", "held-out material is forbidden")
        if not self.rollback_declaration.exact:
            raise SchemaValidationError("phase12e.program.rollback", "exact rollback is required")
        if self.successor_generator_generation != 3 or self.successor_planner_generation != 3:
            raise SchemaValidationError("phase12e.program.generation", "generation-3 authority must be retained")
        object.__setattr__(self, "selected_update_classes", updates)
        object.__setattr__(self, "expected_affected_components", components)

    @property
    def program_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
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


def phase12e_program() -> Phase12ETypedProgram:
    return Phase12ETypedProgram(
        objective=PHASE11_OBJECTIVE,
        selected_update_classes=("adapter_update", "architecture_extension", "optimizer_policy_update"),
        training_policy=TrainingDirective(
            optimizer="sgd",
            steps=1,
            learning_rate_numerator=1,
            learning_rate_denominator=1,
            seed=4213,
        ),
        data_selection=DataSelectionDirective(
            selection_id=PHASE11_DATA_SELECTION,
            heldout_task_ids_visible=False,
            heldout_prompts_visible=False,
            heldout_reference_answers_visible=False,
        ),
        architecture_mutation=Phase12EArchitectureDirective(
            kind=PHASE12E_ARCHITECTURE_KIND,
            lora_rank=8,
            target_modules=("attn_output", "attn_qkv", "mlp_down", "mlp_gate", "mlp_up"),
        ),
        resource_request=ResourceRequest(
            wall_clock_seconds=1,
            accelerator_count=0,
            training_steps=1,
            output_bytes=96,
            candidate_count=1,
            evaluation_calls=1,
        ),
        expected_affected_components=("adapter_manifest", "model_architecture", "optimizer_policy"),
        rollback_declaration=RollbackDeclaration(
            mode=PHASE11_ROLLBACK_MODE,
            predecessor_bytes_required=True,
        ),
        successor_generator_generation=3,
        successor_planner_generation=3,
    )


def encode_phase12e_program(program: Phase12ETypedProgram) -> bytes:
    if program.to_json() != phase12e_program().to_json():
        raise SchemaValidationError("phase12e.program", "program differs from the frozen selected form")
    return PHASE12E_ACCEPTED_PROGRAM_BYTES


def parse_phase12e_program(raw: bytes) -> Phase12ETypedProgram:
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaValidationError("phase12e.program", "program must be ASCII") from exc
    if text != PHASE12E_ACCEPTED_PROGRAM_TEXT:
        raise SchemaValidationError("phase12e.program", "program is not the canonical selected V2 form")
    program = phase12e_program()
    if encode_phase12e_program(program) != raw:
        raise SchemaValidationError("phase12e.program", "canonical round trip mismatch")
    return program


@dataclass(frozen=True, slots=True)
class Phase12EProposalReport:
    generator_input: ModelGeneratorInput
    model_draft: GeneratorInvocationReport
    prior_evidence_hash: str
    program_text: str
    program_raw_sha256: str
    program: Phase12ETypedProgram
    package_hash: str
    model_identity_hash: str
    generator_policy_hash: str
    planner_policy_hash: str
    planner_profile: str
    transition_index: int
    package_tree_hash_before: str
    package_tree_hash_after: str

    schema_id: ClassVar[str] = "runtime.v3.phase12e.proposal_report.v1"

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
            and self.model_draft.generator_input.to_json() == self.generator_input.to_json()
            and self.generator_input.proposal_protocol_hash == PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH
            and self.generator_input.objective_hash == phase12_objective_hash()
            and self.planner_profile == PHASE12E_PLANNER_PROFILE
            and self.transition_index == 3
            and self.program_text.encode("ascii") == PHASE12E_ACCEPTED_PROGRAM_BYTES
            and self.program_raw_sha256 == sha256_hex(PHASE12E_ACCEPTED_PROGRAM_BYTES)
            and self.package_unchanged
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12E_CONTRACT_VERSION,
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
class Phase12EProposalValidationReport:
    proposal_hash: str
    program_hash: str
    binding_checks: Mapping[str, bool]
    reason_codes: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase12e.proposal_validation.v1"

    @property
    def accepted(self) -> bool:
        return not self.reason_codes and all(self.binding_checks.values())

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12E_CONTRACT_VERSION,
            "proposal_hash": self.proposal_hash,
            "program_hash": self.program_hash,
            "binding_checks": {
                key: self.binding_checks[key]
                for key in sorted(self.binding_checks, key=lambda item: item.encode("utf-8"))
            },
            "reason_codes": list(self.reason_codes),
            "accepted": self.accepted,
        }


def phase12e_invocation_budget():
    return phase12_first_invocation_budget()


def _m3_generator_input(reference: Phase12DReference) -> ModelGeneratorInput:
    state = reference.semantic_candidate.candidate_state
    manifest = reference.semantic_candidate.manifest
    observation = {
        "schema_id": "runtime.v3.phase12e.m3_observation.v1",
        "trajectory_id": PHASE12_TRAJECTORY_ID,
        "active_state_hash": state.state_hash,
        "phase12d_summary_hash": reference.summary_json()["summary_hash"],
        "accepted_phase12_promotions": 3,
        "prior_phase12_rejections": 2,
        "transition_index": 3,
        "required_components": PHASE12_COMPONENT_SCHEDULE[3]["required_components"],
        "remaining_generator_invocations": 1,
        "remaining_candidate_realizations": 1,
        "remaining_candidate_evaluations": 1,
        "remaining_promotions": 1,
        "remaining_rejections": 0,
        "heldout_answer_material_present": False,
    }
    return ModelGeneratorInput(
        transition_id=PHASE12E_TRANSITION_ID,
        invocation_id="phase12-m3-generation3-invocation-5",
        invocation_index=5,
        active_package_hash=manifest.package_hash,
        active_state_hash=state.state_hash,
        model_identity_hash=manifest.model_identity_hash,
        active_generator_hash=manifest.generator_policy_hash,
        active_planner_hash=manifest.planner_policy_hash,
        proposal_protocol_hash=state.self_hosting.proposal_protocol_hash,
        objective_hash=phase12_objective_hash(),
        observation_hash=canonical_json_hash(observation),
        budget=phase12e_invocation_budget(),
        manual_repair_count=0,
    )


def _decode_generation3_model_draft(package_root: Path, generator_input: ModelGeneratorInput) -> GeneratorInvocationReport:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    bindings = (
        (generator_input.active_package_hash, manifest.package_hash, "package"),
        (generator_input.model_identity_hash, manifest.model_identity_hash, "model"),
        (generator_input.active_generator_hash, manifest.generator_policy_hash, "generator"),
        (generator_input.active_planner_hash, manifest.planner_policy_hash, "planner"),
        (generator_input.proposal_protocol_hash, PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH, "protocol"),
    )
    for observed, expected, label in bindings:
        if observed != expected:
            raise SchemaValidationError("phase12e.generator.input", f"{label} binding mismatch")
    output = bytearray()
    steps: list[GeneratorDecodeStep] = []
    stopped = False
    for position in range(PHASE12_RECURSIVE_BANK_CAPACITY):
        state_token = PHASE12_RECURSIVE_BANK_START + position
        scores, distribution = exact_dyadic_distribution(root, state_token)
        selected = min(range(VOCAB_SIZE), key=lambda token: (-scores[token], token))
        ordered = sorted(scores, reverse=True)
        runner_up = ordered[1] if len(ordered) > 1 else ordered[0]
        steps.append(
            GeneratorDecodeStep(
                position=position,
                state_token_id=state_token,
                selected_token_id=selected,
                selected_score=scores[selected],
                runner_up_score=runner_up,
                distribution_hash=canonical_json_hash([p.to_json() for p in distribution]),
            )
        )
        if selected == EOS_TOKEN_ID:
            stopped = True
            break
        if not 0 <= selected < 256:
            raise SchemaValidationError("phase12e.generator.output", "non-byte token")
        output.append(selected)
    if not stopped or bytes(output) != PHASE12_EXPECTED_FIRST_PROGRAM_BYTES:
        raise SchemaValidationError("phase12e.generator.output", "unexpected model draft")
    raw = bytes(output)
    return GeneratorInvocationReport(
        generator_input=generator_input,
        program_text=raw.decode("ascii"),
        program_raw_sha256=sha256_hex(raw),
        program=parse_phase11b_program(raw),
        steps=tuple(steps),
        stopped_on_eos=True,
        package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
    )


def generate_phase12e_proposal(reference: Phase12DReference) -> Phase12EProposalReport:
    active_root = reference.semantic_candidate.root.resolve(strict=True)
    generator_input = _m3_generator_input(reference)
    tree_before = phase12_package_tree_hash(active_root)
    draft = _decode_generation3_model_draft(active_root, generator_input)
    program = phase12e_program()
    raw = encode_phase12e_program(program)
    reparsed = parse_phase12e_program(raw)
    if reparsed.to_json() != program.to_json():
        raise SchemaValidationError("phase12e.program", "canonical round trip mismatch")
    tree_after = phase12_package_tree_hash(active_root)
    report = Phase12EProposalReport(
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
        planner_profile=PHASE12E_PLANNER_PROFILE,
        transition_index=3,
        package_tree_hash_before=tree_before,
        package_tree_hash_after=tree_after,
    )
    if not report.package_generated:
        raise ValueError("Phase 12E proposal package binding failed")
    return report


def validate_phase12e_proposal(reference: Phase12DReference, proposal: Phase12EProposalReport) -> Phase12EProposalValidationReport:
    state = reference.semantic_candidate.candidate_state
    manifest = reference.semantic_candidate.manifest
    program = proposal.program
    bindings = {
        "active_package_bound": proposal.package_hash == manifest.package_hash,
        "active_state_bound": proposal.generator_input.active_state_hash == state.state_hash,
        "active_model_bound": proposal.model_identity_hash == manifest.model_identity_hash,
        "active_generator_bound": proposal.generator_policy_hash == manifest.generator_policy_hash,
        "active_planner_bound": proposal.planner_policy_hash == manifest.planner_policy_hash,
        "proposal_protocol_bound": proposal.generator_input.proposal_protocol_hash == PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
        "objective_bound": proposal.generator_input.objective_hash == phase12_objective_hash(),
        "package_generated": proposal.package_generated,
        "package_unchanged": proposal.package_unchanged,
        "heldout_material_hidden": not program.data_selection.heldout_material_visible,
        "manual_repair_absent": proposal.generator_input.manual_repair_count == 0,
        "resource_budget_respected": proposal.generator_input.budget.permits(program.resource_request),
        "training_step_exact": program.training_policy.steps == 1,
        "component_schedule_respected": set(program.expected_affected_components) == {"adapter_manifest", "model_architecture", "optimizer_policy"},
        "authority_retained": program.successor_generator_generation == 3 and program.successor_planner_generation == 3,
        "program_bytes_bound": proposal.program_text.encode("ascii") == PHASE12E_ACCEPTED_PROGRAM_BYTES,
    }
    reasons = tuple(() if all(bindings.values()) else ("PHASE12E_BINDING_MISMATCH",))
    if reasons:
        raise SchemaValidationError("phase12e.validation", ",".join(reasons))
    return Phase12EProposalValidationReport(
        proposal_hash=proposal.report_hash,
        program_hash=program.program_hash,
        binding_checks=bindings,
        reason_codes=(),
    )


__all__ = [name for name in globals() if name.startswith("PHASE12E_")] + [
    "Phase12EArchitectureDirective",
    "Phase12EProposalReport",
    "Phase12EProposalValidationReport",
    "Phase12ETypedProgram",
    "encode_phase12e_program",
    "generate_phase12e_proposal",
    "parse_phase12e_program",
    "phase12e_invocation_budget",
    "phase12e_program",
    "validate_phase12e_proposal",
]
