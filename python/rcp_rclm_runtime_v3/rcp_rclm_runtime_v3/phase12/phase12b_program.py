from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, TYPE_CHECKING

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase11.phase11b_program import (
    encode_phase11b_program,
    parse_phase11b_program,
)
from rcp_rclm_runtime_v3.phase11.records import (
    ModelGeneratorInput,
    TypedMutationProgram,
)
from rcp_rclm_runtime_v3.phase12.constants import (
    PHASE12_ACTIVE_GENERATOR_GENERATION,
    PHASE12_ACTIVE_PLANNER_GENERATION,
    PHASE12_COMPONENT_SCHEDULE,
    PHASE12_PROPOSAL_PROTOCOL_HASH,
    PHASE12_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v3.phase12.generator import (
    phase12_first_invocation_budget,
    phase12_objective_hash,
    phase12_package_tree_hash,
)

if TYPE_CHECKING:
    from rcp_rclm_runtime_v3.phase12.reference import Phase12AReference


PHASE12B_CONTRACT_VERSION = "rcp-rclm-executable-v3-phase-12b"
PHASE12B_ACCEPTED_PROGRAM_TEXT = (
    "V1;O=F;U=W;D=A;A=N;R=1,0,1,96,1,1;E=W;B=X;G=2;P=2"
)
PHASE12B_ACCEPTED_PROGRAM_BYTES = PHASE12B_ACCEPTED_PROGRAM_TEXT.encode("ascii")
PHASE12B_TRANSITION_ID = "phase12-m0-to-m1-weight-successor"
PHASE12B_PLANNER_PROFILE = "generation2_rejection_conditioned_schedule_projection_v1"


@dataclass(frozen=True, slots=True)
class Phase12RecursiveProposalReport:
    generator_input: ModelGeneratorInput
    draft_invocation_hash: str
    prior_validation_hash: str
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

    schema_id: ClassVar[str] = "runtime.v3.phase12.recursive_proposal_report.v1"

    @property
    def package_unchanged(self) -> bool:
        return self.package_tree_hash_before == self.package_tree_hash_after

    @property
    def package_generated(self) -> bool:
        return (
            self.generator_input.active_package_hash == self.package_hash
            and self.generator_input.model_identity_hash == self.model_identity_hash
            and self.generator_input.active_generator_hash == self.generator_policy_hash
            and self.generator_input.active_planner_hash == self.planner_policy_hash
            and self.generator_input.proposal_protocol_hash
            == PHASE12_PROPOSAL_PROTOCOL_HASH
            and self.generator_input.objective_hash == phase12_objective_hash()
            and self.planner_profile == PHASE12B_PLANNER_PROFILE
            and self.transition_index == 0
            and self.program_text.encode("ascii") == PHASE12B_ACCEPTED_PROGRAM_BYTES
            and self.program_raw_sha256 == sha256_hex(PHASE12B_ACCEPTED_PROGRAM_BYTES)
            and self.package_unchanged
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12B_CONTRACT_VERSION,
            "generator_input": self.generator_input.to_json(),
            "generator_input_hash": self.generator_input.input_hash,
            "draft_invocation_hash": self.draft_invocation_hash,
            "prior_validation_hash": self.prior_validation_hash,
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
class Phase12ProposalValidationReport:
    proposal_hash: str
    program_hash: str
    binding_checks: dict[str, bool]
    reason_codes: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase12.proposal_validation.v1"

    @property
    def accepted(self) -> bool:
        return not self.reason_codes and all(self.binding_checks.values())

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE12B_CONTRACT_VERSION,
            "proposal_hash": self.proposal_hash,
            "program_hash": self.program_hash,
            "binding_checks": {
                key: self.binding_checks[key]
                for key in sorted(self.binding_checks, key=lambda item: item.encode("utf-8"))
            },
            "reason_codes": list(self.reason_codes),
            "accepted": self.accepted,
        }


def _policy_object(package_root: Path, relative_path: str) -> dict[str, object]:
    value = load_json_strict(
        (package_root.resolve(strict=True) / relative_path).read_bytes(),
        require_canonical=True,
    )
    if not isinstance(value, dict):
        raise SchemaValidationError("phase12b.policy", f"expected object at {relative_path}")
    return value


def _fresh_input(reference: Phase12AReference) -> ModelGeneratorInput:
    active = reference.phase11.beta_candidate
    state = active.candidate_state
    if state is None:
        raise ValueError("Phase 12 active state is unavailable")
    observation_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12.rejection_conditioned_observation.v1",
            "trajectory_id": PHASE12_TRAJECTORY_ID,
            "active_state_hash": state.state_hash,
            "first_invocation_hash": reference.first_invocation.report_hash,
            "first_validation_hash": reference.first_validation.report_hash,
            "first_rejection_reason_codes": [
                item.value for item in reference.first_validation.reason_codes
            ],
            "active_package_unchanged": reference.package_unchanged,
            "transition_index": 0,
            "required_components": PHASE12_COMPONENT_SCHEDULE[0]["required_components"],
            "heldout_answer_material_present": False,
        }
    )
    return ModelGeneratorInput(
        transition_id=PHASE12B_TRANSITION_ID,
        invocation_id="phase12-generation2-rejection-conditioned-invocation-1",
        invocation_index=1,
        active_package_hash=active.manifest.package_hash,
        active_state_hash=state.state_hash,
        model_identity_hash=active.manifest.model_identity_hash,
        active_generator_hash=active.manifest.generator_policy_hash,
        active_planner_hash=active.manifest.planner_policy_hash,
        proposal_protocol_hash=PHASE12_PROPOSAL_PROTOCOL_HASH,
        objective_hash=phase12_objective_hash(),
        observation_hash=observation_hash,
        budget=phase12_first_invocation_budget(),
        manual_repair_count=0,
    )


def _schedule_projected_program(draft: TypedMutationProgram) -> TypedMutationProgram:
    return TypedMutationProgram(
        objective=draft.objective,
        selected_update_classes=("weight_update",),
        training_policy=draft.training_policy,
        data_selection=draft.data_selection,
        architecture_mutation=draft.architecture_mutation,
        resource_request=draft.resource_request,
        expected_affected_components=("model_weights",),
        rollback_declaration=draft.rollback_declaration,
        successor_generator_generation=PHASE12_ACTIVE_GENERATOR_GENERATION,
        successor_planner_generation=PHASE12_ACTIVE_PLANNER_GENERATION,
    )


def generate_phase12_rejection_conditioned_proposal(
    reference: Phase12AReference,
) -> Phase12RecursiveProposalReport:
    active_root = reference.phase11.beta_candidate.root.resolve(strict=True)
    manifest = load_package_manifest(active_root)
    generator_policy = _policy_object(active_root, "policies/generator_policy.json")
    planner_policy = _policy_object(active_root, "policies/planner_policy.json")
    if generator_policy.get("policy") != "installed_self_hosted_typed_mutation_generator":
        raise SchemaValidationError("phase12b.generator_policy", "unexpected active generator")
    if generator_policy.get("generation") != PHASE12_ACTIVE_GENERATOR_GENERATION:
        raise SchemaValidationError("phase12b.generator_policy", "generation mismatch")
    if generator_policy.get("next_proposal_authority") is not True:
        raise SchemaValidationError("phase12b.generator_policy", "proposal authority disabled")
    if planner_policy.get("policy") != "installed_self_hosted_bounded_experiment_planner":
        raise SchemaValidationError("phase12b.planner_policy", "unexpected active planner")
    if planner_policy.get("generation") != PHASE12_ACTIVE_PLANNER_GENERATION:
        raise SchemaValidationError("phase12b.planner_policy", "generation mismatch")
    if planner_policy.get("fresh_proposal_after_rejection") is not True:
        raise SchemaValidationError(
            "phase12b.planner_policy",
            "active planner does not authorize a fresh rejection-conditioned proposal",
        )
    if planner_policy.get("bounded_within_run") is not True:
        raise SchemaValidationError("phase12b.planner_policy", "planner is not bounded")
    if canonical_json_hash(generator_policy) != manifest.generator_policy_hash:
        raise SchemaValidationError("phase12b.generator_policy", "manifest binding mismatch")
    if canonical_json_hash(planner_policy) != manifest.planner_policy_hash:
        raise SchemaValidationError("phase12b.planner_policy", "manifest binding mismatch")
    if reference.first_validation.accepted or not reference.package_unchanged:
        raise SchemaValidationError(
            "phase12b.prior_rejection",
            "fresh proposal requires the retained fail-closed rejection",
        )

    generator_input = _fresh_input(reference)
    tree_before = phase12_package_tree_hash(active_root)
    program = _schedule_projected_program(reference.first_invocation.program)
    raw = encode_phase11b_program(program)
    if raw != PHASE12B_ACCEPTED_PROGRAM_BYTES:
        raise SchemaValidationError(
            "phase12b.program",
            "package-bound planner produced an unexpected scheduled program",
        )
    reparsed = parse_phase11b_program(raw)
    if reparsed.to_json() != program.to_json():
        raise SchemaValidationError("phase12b.program", "canonical round trip mismatch")
    tree_after = phase12_package_tree_hash(active_root)
    report = Phase12RecursiveProposalReport(
        generator_input=generator_input,
        draft_invocation_hash=reference.first_invocation.report_hash,
        prior_validation_hash=reference.first_validation.report_hash,
        program_text=raw.decode("ascii"),
        program_raw_sha256=sha256_hex(raw),
        program=program,
        package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
        planner_profile=PHASE12B_PLANNER_PROFILE,
        transition_index=0,
        package_tree_hash_before=tree_before,
        package_tree_hash_after=tree_after,
    )
    if not report.package_generated:
        raise ValueError("Phase 12 rejection-conditioned proposal binding failed")
    return report


def validate_phase12_rejection_conditioned_proposal(
    reference: Phase12AReference,
    proposal: Phase12RecursiveProposalReport,
) -> Phase12ProposalValidationReport:
    program = proposal.program
    input_record = proposal.generator_input
    bindings = {
        "active_package_bound": proposal.package_hash
        == reference.phase11.beta_candidate.manifest.package_hash,
        "active_model_bound": proposal.model_identity_hash
        == reference.phase11.beta_candidate.manifest.model_identity_hash,
        "active_generator_bound": proposal.generator_policy_hash
        == reference.phase11.beta_candidate.manifest.generator_policy_hash,
        "active_planner_bound": proposal.planner_policy_hash
        == reference.phase11.beta_candidate.manifest.planner_policy_hash,
        "active_state_bound": (
            reference.phase11.beta_candidate.candidate_state is not None
            and input_record.active_state_hash
            == reference.phase11.beta_candidate.candidate_state.state_hash
        ),
        "prior_rejection_bound": proposal.prior_validation_hash
        == reference.first_validation.report_hash,
        "draft_invocation_bound": proposal.draft_invocation_hash
        == reference.first_invocation.report_hash,
        "proposal_protocol_bound": input_record.proposal_protocol_hash
        == PHASE12_PROPOSAL_PROTOCOL_HASH,
        "objective_bound": input_record.objective_hash == phase12_objective_hash(),
        "package_generated": proposal.package_generated,
        "active_package_unchanged": proposal.package_unchanged,
        "heldout_material_hidden": not program.data_selection.heldout_material_visible,
        "manual_repair_absent": input_record.manual_repair_count == 0,
        "resource_budget_respected": input_record.budget.permits(
            program.resource_request
        ),
        "component_schedule_respected": (
            tuple(program.selected_update_classes) == ("weight_update",)
            and tuple(program.expected_affected_components) == ("model_weights",)
        ),
        "program_bytes_bound": proposal.program_text.encode("ascii")
        == PHASE12B_ACCEPTED_PROGRAM_BYTES,
    }
    reasons: list[str] = []
    if not all(bindings.values()):
        reasons.append("PHASE12_PROPOSAL_BINDING_FAILED")
    if not bindings["resource_budget_respected"]:
        reasons.append("PHASE12_BUDGET_EXCEEDED")
    if not bindings["component_schedule_respected"]:
        reasons.append("PHASE12_COMPONENT_SCHEDULE_MISMATCH")
    if program.successor_generator_generation != PHASE12_ACTIVE_GENERATOR_GENERATION:
        reasons.append("PHASE12_UNSELECTED_GENERATOR_GENERATION_CHANGED")
    if program.successor_planner_generation != PHASE12_ACTIVE_PLANNER_GENERATION:
        reasons.append("PHASE12_UNSELECTED_PLANNER_GENERATION_CHANGED")
    result = Phase12ProposalValidationReport(
        proposal_hash=proposal.report_hash,
        program_hash=program.program_hash,
        binding_checks=bindings,
        reason_codes=tuple(sorted(set(reasons), key=lambda item: item.encode("utf-8"))),
    )
    if not result.accepted:
        raise ValueError("Phase 12 rejection-conditioned proposal did not validate")
    return result


__all__ = [
    "PHASE12B_ACCEPTED_PROGRAM_BYTES",
    "PHASE12B_ACCEPTED_PROGRAM_TEXT",
    "PHASE12B_CONTRACT_VERSION",
    "PHASE12B_PLANNER_PROFILE",
    "PHASE12B_TRANSITION_ID",
    "Phase12ProposalValidationReport",
    "Phase12RecursiveProposalReport",
    "generate_phase12_rejection_conditioned_proposal",
    "validate_phase12_rejection_conditioned_proposal",
]
