from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID, VOCAB_SIZE
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import exact_dyadic_distribution
from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    ACTIVE_GENERATOR_GENERATION,
    ACTIVE_PLANNER_GENERATION,
    ALLOWED_UPDATE_CLASSES_V2,
    BANK_CAPACITY,
    BANK_START_BY_INVOCATION,
    COMPONENT_CODE_ORDER_V2,
    COMPONENT_CODE_TO_COMPONENT_V2,
    FORBIDDEN_UPDATE_CLASSES_V2,
    PHASE11B_ARCHITECTURE_MUTATION,
    PHASE11B_DATA_SELECTION_ALPHA,
    PHASE11B_GENERATOR_PROFILE,
    PHASE11B_OBJECTIVE,
    PHASE11B_PROPOSAL_PROTOCOL_HASH,
    PHASE11B_ROLLBACK_MODE,
    PROGRAM_BY_INVOCATION,
    UPDATE_CLASS_TO_COMPONENT_V2,
    UPDATE_CODE_ORDER_V2,
    UPDATE_CODE_TO_CLASS_V2,
)
from rcp_rclm_runtime_v3.phase11.constants import PHASE11_PROGRAM_VERSION
from rcp_rclm_runtime_v3.phase11.records import (
    ArchitectureMutationDirective,
    DataSelectionDirective,
    GeneratorDecodeStep,
    GeneratorInvocationReport,
    ModelGeneratorInput,
    Phase11ReasonCode,
    ProgramValidationReport,
    ResourceRequest,
    RollbackDeclaration,
    TrainingDirective,
    TypedMutationProgram,
)

_FIELD_ORDER: Sequence[str] = ("O", "U", "D", "A", "R", "E", "B", "G", "P")


def phase11b_objective_hash() -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase11b.objective.v1",
            "objective": PHASE11B_OBJECTIVE,
            "strict_capability_frontier_expansion_required": True,
            "protected_capability_retention_required": True,
            "candidate_self_report_authoritative": False,
            "candidate_rejection_feedback_permitted": True,
        }
    )


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
    return tuple(
        sorted(
            (mapping[code] for code in value),
            key=lambda item: item.encode("utf-8"),
        )
    )


def _codes_for_values(
    values: Sequence[str],
    mapping: Mapping[str, str],
    order: Sequence[str],
    path: str,
) -> str:
    inverse = {value: code for code, value in mapping.items()}
    unknown = tuple(value for value in values if value not in inverse)
    if unknown:
        raise SchemaValidationError(path, f"unsupported values: {unknown}")
    selected = {inverse[value] for value in values}
    return "".join(code for code in order if code in selected)


def parse_phase11b_program(raw: bytes) -> TypedMutationProgram:
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaValidationError("phase11b.program", "program must be ASCII") from exc
    if not text or text != text.strip() or any(character.isspace() for character in text):
        raise SchemaValidationError("phase11b.program", "whitespace is forbidden")
    parts = text.split(";")
    if parts[0] != PHASE11_PROGRAM_VERSION:
        raise SchemaValidationError("phase11b.program.version", "unsupported program version")
    if len(parts) != len(_FIELD_ORDER) + 1:
        raise SchemaValidationError("phase11b.program", "field count mismatch")
    fields: dict[str, str] = {}
    for expected_key, part in zip(_FIELD_ORDER, parts[1:], strict=True):
        if "=" not in part:
            raise SchemaValidationError("phase11b.program", "field assignment is missing")
        key, value = part.split("=", 1)
        if key != expected_key:
            raise SchemaValidationError(
                "phase11b.program",
                f"expected field {expected_key}, observed {key}",
            )
        fields[key] = value
    if fields["O"] != "F":
        raise SchemaValidationError("phase11b.program.objective", "unsupported objective code")
    if fields["D"] != "A":
        raise SchemaValidationError("phase11b.program.data", "unsupported data-selection code")
    if fields["A"] != "N":
        raise SchemaValidationError("phase11b.program.architecture", "unsupported architecture code")
    if fields["B"] != "X":
        raise SchemaValidationError("phase11b.program.rollback", "unsupported rollback code")
    resource_parts = fields["R"].split(",")
    if len(resource_parts) != 6:
        raise SchemaValidationError("phase11b.program.resource", "expected six resource integers")
    wall_clock, accelerators, steps, output_bytes, candidates, evaluations = tuple(
        _parse_uint(value, f"phase11b.program.resource[{index}]")
        for index, value in enumerate(resource_parts)
    )
    if wall_clock < 1 or output_bytes < 1 or candidates < 1 or evaluations < 1:
        raise SchemaValidationError(
            "phase11b.program.resource",
            "wall clock, output bytes, candidates, and evaluations must be positive",
        )
    program = TypedMutationProgram(
        objective=PHASE11B_OBJECTIVE,
        selected_update_classes=_parse_codes(
            fields["U"], UPDATE_CODE_TO_CLASS_V2, "phase11b.program.update_classes"
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
            COMPONENT_CODE_TO_COMPONENT_V2,
            "phase11b.program.expected_components",
        ),
        rollback_declaration=RollbackDeclaration(
            mode=PHASE11B_ROLLBACK_MODE,
            predecessor_bytes_required=True,
        ),
        successor_generator_generation=_parse_uint(
            fields["G"], "phase11b.program.successor_generator_generation", minimum=1
        ),
        successor_planner_generation=_parse_uint(
            fields["P"], "phase11b.program.successor_planner_generation", minimum=1
        ),
    )
    if encode_phase11b_program(program) != raw:
        raise SchemaValidationError("phase11b.program", "program is not in canonical form")
    return program


def encode_phase11b_program(program: TypedMutationProgram) -> bytes:
    request = program.resource_request
    update_codes = _codes_for_values(
        program.selected_update_classes,
        UPDATE_CODE_TO_CLASS_V2,
        UPDATE_CODE_ORDER_V2,
        "phase11b.program.selected_update_classes",
    )
    component_codes = _codes_for_values(
        program.expected_affected_components,
        COMPONENT_CODE_TO_COMPONENT_V2,
        COMPONENT_CODE_ORDER_V2,
        "phase11b.program.expected_affected_components",
    )
    text = (
        f"{PHASE11_PROGRAM_VERSION};O=F;U={update_codes};D=A;A=N;"
        f"R={request.wall_clock_seconds},{request.accelerator_count},"
        f"{request.training_steps},{request.output_bytes},"
        f"{request.candidate_count},{request.evaluation_calls};"
        f"E={component_codes};B=X;G={program.successor_generator_generation};"
        f"P={program.successor_planner_generation}"
    )
    return text.encode("ascii")


def _policy_object(package_root: Path, relative_path: str) -> dict[str, object]:
    value = load_json_strict(
        (package_root.resolve(strict=True) / relative_path).read_bytes(),
        require_canonical=True,
    )
    if not isinstance(value, dict):
        raise SchemaValidationError("phase11b.generator.policy", "expected policy object")
    return value


def generate_phase11b_program(
    package_root: Path,
    generator_input: ModelGeneratorInput,
) -> GeneratorInvocationReport:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    generator_policy = _policy_object(root, "policies/generator_policy.json")
    planner_policy = _policy_object(root, "policies/planner_policy.json")
    binding_pairs = (
        (generator_input.active_package_hash, manifest.package_hash, "active package"),
        (generator_input.model_identity_hash, manifest.model_identity_hash, "model identity"),
        (generator_input.active_generator_hash, manifest.generator_policy_hash, "generator"),
        (generator_input.active_planner_hash, manifest.planner_policy_hash, "planner"),
        (
            generator_input.proposal_protocol_hash,
            PHASE11B_PROPOSAL_PROTOCOL_HASH,
            "proposal protocol",
        ),
        (generator_input.objective_hash, phase11b_objective_hash(), "objective"),
    )
    for observed, expected, label in binding_pairs:
        if observed != expected:
            raise SchemaValidationError("phase11b.generator.input", f"{label} hash mismatch")
    if generator_policy.get("generator_profile") != PHASE11B_GENERATOR_PROFILE:
        raise SchemaValidationError("phase11b.generator.policy", "generator profile mismatch")
    if generator_policy.get("proposal_protocol_hash") != PHASE11B_PROPOSAL_PROTOCOL_HASH:
        raise SchemaValidationError("phase11b.generator.policy", "proposal protocol mismatch")
    if generator_policy.get("learned_proposal_authority") is not True:
        raise SchemaValidationError("phase11b.generator.policy", "proposal authority is disabled")
    if planner_policy.get("proposal_protocol_hash") != PHASE11B_PROPOSAL_PROTOCOL_HASH:
        raise SchemaValidationError("phase11b.planner.policy", "proposal protocol mismatch")
    if planner_policy.get("typed_mutation_program_required") is not True:
        raise SchemaValidationError("phase11b.planner.policy", "typed output is not required")
    if generator_policy.get("generation") != ACTIVE_GENERATOR_GENERATION:
        raise SchemaValidationError("phase11b.generator.policy", "active generation mismatch")
    if planner_policy.get("generation") != ACTIVE_PLANNER_GENERATION:
        raise SchemaValidationError("phase11b.planner.policy", "active generation mismatch")
    invocation_index = generator_input.invocation_index
    if invocation_index not in BANK_START_BY_INVOCATION:
        raise SchemaValidationError(
            "phase11b.generator.invocation_index",
            "selected Phase 11B profile contains exactly three invocations",
        )
    output = bytearray()
    decode_steps: list[GeneratorDecodeStep] = []
    stopped = False
    bank_start = BANK_START_BY_INVOCATION[invocation_index]
    for position in range(BANK_CAPACITY):
        state_token = bank_start + position
        scores, distribution = exact_dyadic_distribution(root, state_token)
        selected = min(range(VOCAB_SIZE), key=lambda token: (-scores[token], token))
        ordered = sorted(scores, reverse=True)
        runner_up = ordered[1] if len(ordered) > 1 else ordered[0]
        decode_steps.append(
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
                "phase11b.generator.output",
                "typed mutation output contains a non-byte token",
            )
        output.append(selected)
        if len(output) > generator_input.budget.max_output_bytes:
            raise SchemaValidationError(
                "phase11b.generator.output",
                "model output exceeded the fixed byte budget",
            )
    if not stopped:
        raise SchemaValidationError("phase11b.generator.output", "model output did not terminate")
    expected_program = PROGRAM_BY_INVOCATION[invocation_index]
    raw = bytes(output)
    if raw != expected_program:
        raise SchemaValidationError("phase11b.generator.output", "model output binding mismatch")
    expected_prefix = f"program_{invocation_index}"
    if generator_policy.get(f"{expected_prefix}_length") != len(raw):
        raise SchemaValidationError("phase11b.generator.policy", "output length binding mismatch")
    raw_hash = sha256_hex(raw)
    if generator_policy.get(f"{expected_prefix}_sha256") != raw_hash:
        raise SchemaValidationError("phase11b.generator.policy", "output hash binding mismatch")
    program = parse_phase11b_program(raw)
    return GeneratorInvocationReport(
        generator_input=generator_input,
        program_text=raw.decode("ascii"),
        program_raw_sha256=raw_hash,
        program=program,
        steps=tuple(decode_steps),
        stopped_on_eos=stopped,
        package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
    )


def _expected_components(update_classes: Sequence[str]) -> Sequence[str] | None:
    components: list[str] = []
    for update_class in update_classes:
        component = UPDATE_CLASS_TO_COMPONENT_V2.get(update_class)
        if component is None:
            return None
        components.append(component)
    return tuple(sorted(components, key=lambda item: item.encode("utf-8")))


def validate_phase11b_program(
    invocation: GeneratorInvocationReport,
) -> ProgramValidationReport:
    program = invocation.program
    generator_input = invocation.generator_input
    bindings: dict[str, bool] = {
        "active_package_bound": invocation.package_hash == generator_input.active_package_hash,
        "active_model_bound": invocation.model_identity_hash == generator_input.model_identity_hash,
        "active_generator_bound": (
            invocation.generator_policy_hash == generator_input.active_generator_hash
        ),
        "active_planner_bound": invocation.planner_policy_hash == generator_input.active_planner_hash,
        "proposal_protocol_bound": (
            generator_input.proposal_protocol_hash == PHASE11B_PROPOSAL_PROTOCOL_HASH
        ),
        "objective_bound": generator_input.objective_hash == phase11b_objective_hash(),
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
    if not generator_input.budget.permits(program.resource_request):
        reasons.add(Phase11ReasonCode.BUDGET_EXCEEDED)
    selected = set(program.selected_update_classes)
    if selected & FORBIDDEN_UPDATE_CLASSES_V2 or not selected <= (
        ALLOWED_UPDATE_CLASSES_V2 | FORBIDDEN_UPDATE_CLASSES_V2
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
    "encode_phase11b_program",
    "generate_phase11b_program",
    "parse_phase11b_program",
    "phase11b_objective_hash",
    "validate_phase11b_program",
]
