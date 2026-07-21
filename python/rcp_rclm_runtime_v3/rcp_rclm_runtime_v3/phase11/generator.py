from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID, VOCAB_SIZE
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import exact_dyadic_distribution
from rcp_rclm_runtime_v3.phase11.constants import (
    ACCEPTED_BANK_CAPACITY,
    ACCEPTED_BANK_START,
    ACTIVE_GENERATOR_GENERATION,
    ACTIVE_PLANNER_GENERATION,
    ALLOWED_UPDATE_CLASSES,
    FORBIDDEN_UPDATE_CLASSES,
    PHASE11_GENERATOR_PROFILE,
    PHASE11_OBJECTIVE,
    PROPOSAL_PROTOCOL_HASH,
    REJECTED_BANK_CAPACITY,
    REJECTED_BANK_START,
    UPDATE_CLASS_TO_COMPONENT,
)
from rcp_rclm_runtime_v3.phase11.grammar import parse_typed_mutation_program
from rcp_rclm_runtime_v3.phase11.records import (
    GeneratorDecodeStep,
    GeneratorInvocationReport,
    ModelGeneratorInput,
    Phase11ReasonCode,
    ProgramValidationReport,
)


def phase11_objective_hash() -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase11.objective.v1",
            "objective": PHASE11_OBJECTIVE,
            "strict_capability_frontier_expansion_required": True,
            "protected_capability_retention_required": True,
            "candidate_self_report_authoritative": False,
        }
    )


def _policy_object(package_root: Path, relative_path: str) -> dict[str, object]:
    value = load_json_strict(
        (package_root.resolve(strict=True) / relative_path).read_bytes(),
        require_canonical=True,
    )
    if not isinstance(value, dict):
        raise SchemaValidationError(
            "phase11.generator.policy",
            "expected policy object",
        )
    return value


def _active_policy_bindings(
    package_root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    generator = _policy_object(package_root, "policies/generator_policy.json")
    planner = _policy_object(package_root, "policies/planner_policy.json")
    if generator.get("generator_profile") != PHASE11_GENERATOR_PROFILE:
        raise SchemaValidationError(
            "phase11.generator.policy",
            "generator profile mismatch",
        )
    if generator.get("proposal_protocol_hash") != PROPOSAL_PROTOCOL_HASH:
        raise SchemaValidationError(
            "phase11.generator.policy",
            "proposal protocol mismatch",
        )
    if generator.get("learned_proposal_authority") is not True:
        raise SchemaValidationError(
            "phase11.generator.policy",
            "proposal authority is disabled",
        )
    if planner.get("proposal_protocol_hash") != PROPOSAL_PROTOCOL_HASH:
        raise SchemaValidationError(
            "phase11.planner.policy",
            "proposal protocol mismatch",
        )
    if planner.get("typed_mutation_program_required") is not True:
        raise SchemaValidationError(
            "phase11.planner.policy",
            "typed output is not required",
        )
    return generator, planner


def _bank_for_invocation(invocation_index: int) -> tuple[int, int]:
    if invocation_index == 0:
        return REJECTED_BANK_START, REJECTED_BANK_CAPACITY
    if invocation_index == 1:
        return ACCEPTED_BANK_START, ACCEPTED_BANK_CAPACITY
    raise SchemaValidationError(
        "phase11.generator.invocation_index",
        "selected Phase 11A profile contains exactly two bounded invocations",
    )


def generate_typed_mutation_program(
    package_root: Path,
    generator_input: ModelGeneratorInput,
) -> GeneratorInvocationReport:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    generator_policy, planner_policy = _active_policy_bindings(root)
    if generator_input.active_package_hash != manifest.package_hash:
        raise SchemaValidationError(
            "phase11.generator.input",
            "active package hash mismatch",
        )
    if generator_input.model_identity_hash != manifest.model_identity_hash:
        raise SchemaValidationError(
            "phase11.generator.input",
            "model identity hash mismatch",
        )
    if generator_input.active_generator_hash != manifest.generator_policy_hash:
        raise SchemaValidationError(
            "phase11.generator.input",
            "active generator hash mismatch",
        )
    if generator_input.active_planner_hash != manifest.planner_policy_hash:
        raise SchemaValidationError(
            "phase11.generator.input",
            "active planner hash mismatch",
        )
    if generator_input.proposal_protocol_hash != PROPOSAL_PROTOCOL_HASH:
        raise SchemaValidationError(
            "phase11.generator.input",
            "proposal protocol hash mismatch",
        )
    if generator_input.objective_hash != phase11_objective_hash():
        raise SchemaValidationError(
            "phase11.generator.input",
            "objective hash mismatch",
        )

    bank_start, bank_capacity = _bank_for_invocation(
        generator_input.invocation_index
    )
    output = bytearray()
    steps: list[GeneratorDecodeStep] = []
    stopped = False
    for position in range(bank_capacity):
        state_token = bank_start + position
        scores, distribution = exact_dyadic_distribution(root, state_token)
        selected = min(
            range(VOCAB_SIZE),
            key=lambda token: (-scores[token], token),
        )
        ordered = sorted(scores, reverse=True)
        runner_up = ordered[1] if len(ordered) > 1 else ordered[0]
        steps.append(
            GeneratorDecodeStep(
                position=position,
                state_token_id=state_token,
                selected_token_id=selected,
                selected_score=scores[selected],
                runner_up_score=runner_up,
                distribution_hash=canonical_json_hash(
                    [probability.to_json() for probability in distribution]
                ),
            )
        )
        if selected == EOS_TOKEN_ID:
            stopped = True
            break
        if not 0 <= selected < 256:
            raise SchemaValidationError(
                "phase11.generator.output",
                "typed mutation output contains a non-byte token",
            )
        output.append(selected)
        if len(output) > generator_input.budget.max_output_bytes:
            raise SchemaValidationError(
                "phase11.generator.output",
                "model output exceeded the fixed byte budget",
            )
    if not stopped:
        raise SchemaValidationError(
            "phase11.generator.output",
            "model output did not terminate",
        )
    program = parse_typed_mutation_program(bytes(output))

    expected_length_field = (
        "rejected_program_length"
        if generator_input.invocation_index == 0
        else "accepted_program_length"
    )
    expected_hash_field = (
        "rejected_program_sha256"
        if generator_input.invocation_index == 0
        else "accepted_program_sha256"
    )
    if generator_policy.get(expected_length_field) != len(output):
        raise SchemaValidationError(
            "phase11.generator.policy",
            "output length binding mismatch",
        )
    raw_hash = sha256_hex(bytes(output))
    if generator_policy.get(expected_hash_field) != raw_hash:
        raise SchemaValidationError(
            "phase11.generator.policy",
            "output hash binding mismatch",
        )
    if generator_policy.get("generation") != ACTIVE_GENERATOR_GENERATION:
        raise SchemaValidationError(
            "phase11.generator.policy",
            "active generation mismatch",
        )
    if planner_policy.get("generation") != ACTIVE_PLANNER_GENERATION:
        raise SchemaValidationError(
            "phase11.planner.policy",
            "active generation mismatch",
        )

    return GeneratorInvocationReport(
        generator_input=generator_input,
        program_text=bytes(output).decode("ascii"),
        program_raw_sha256=raw_hash,
        program=program,
        steps=tuple(steps),
        stopped_on_eos=stopped,
        package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
    )


def _expected_components(
    update_classes: Sequence[str],
) -> Sequence[str] | None:
    components: list[str] = []
    for update_class in update_classes:
        component = UPDATE_CLASS_TO_COMPONENT.get(update_class)
        if component is None:
            return None
        components.append(component)
    return tuple(sorted(components, key=lambda item: item.encode("utf-8")))


def validate_generated_program(
    invocation: GeneratorInvocationReport,
) -> ProgramValidationReport:
    program = invocation.program
    generator_input = invocation.generator_input
    bindings: dict[str, bool] = {
        "active_package_bound": (
            invocation.package_hash == generator_input.active_package_hash
        ),
        "active_model_bound": (
            invocation.model_identity_hash == generator_input.model_identity_hash
        ),
        "active_generator_bound": (
            invocation.generator_policy_hash
            == generator_input.active_generator_hash
        ),
        "active_planner_bound": (
            invocation.planner_policy_hash == generator_input.active_planner_hash
        ),
        "proposal_protocol_bound": (
            generator_input.proposal_protocol_hash == PROPOSAL_PROTOCOL_HASH
        ),
        "objective_bound": (
            generator_input.objective_hash == phase11_objective_hash()
        ),
        "model_generated": invocation.model_generated,
        "output_within_budget": invocation.output_within_budget,
        "manual_repair_absent": generator_input.manual_repair_count == 0,
        "frozen_authorities_unaddressable": True,
    }
    reasons: set[Phase11ReasonCode] = set()
    if not all(bindings.values()):
        reasons.add(Phase11ReasonCode.BINDING_MISMATCH)
    if not invocation.model_generated:
        reasons.add(Phase11ReasonCode.PROGRAM_MALFORMED)
    if not invocation.output_within_budget:
        reasons.add(Phase11ReasonCode.OUTPUT_BUDGET_EXCEEDED)
    if program.objective != PHASE11_OBJECTIVE:
        reasons.add(Phase11ReasonCode.OBJECTIVE_MISMATCH)
    if not generator_input.budget.permits(program.resource_request):
        reasons.add(Phase11ReasonCode.BUDGET_EXCEEDED)

    selected = set(program.selected_update_classes)
    if selected & set(FORBIDDEN_UPDATE_CLASSES) or not selected <= set(
        ALLOWED_UPDATE_CLASSES
    ):
        reasons.add(Phase11ReasonCode.FORBIDDEN_UPDATE_CLASS)
    expected_components = _expected_components(program.selected_update_classes)
    if expected_components is None or tuple(expected_components) != tuple(
        program.expected_affected_components
    ):
        reasons.add(Phase11ReasonCode.EXPECTED_COMPONENT_MISMATCH)
    if program.data_selection.heldout_material_visible:
        reasons.add(Phase11ReasonCode.HELDOUT_ACCESS_REQUESTED)
    if not program.rollback_declaration.exact:
        reasons.add(Phase11ReasonCode.ROLLBACK_NOT_EXACT)
    if "generator_update" in selected and (
        program.successor_generator_generation <= ACTIVE_GENERATOR_GENERATION
    ):
        reasons.add(Phase11ReasonCode.GENERATION_NOT_ADVANCED)
    if "planner_update" in selected and (
        program.successor_planner_generation <= ACTIVE_PLANNER_GENERATION
    ):
        reasons.add(Phase11ReasonCode.GENERATION_NOT_ADVANCED)

    return ProgramValidationReport(
        invocation_hash=invocation.report_hash,
        program_hash=program.program_hash,
        reason_codes=tuple(reasons),
        binding_checks=bindings,
    )


__all__ = [
    "generate_typed_mutation_program",
    "phase11_objective_hash",
    "validate_generated_program",
]
