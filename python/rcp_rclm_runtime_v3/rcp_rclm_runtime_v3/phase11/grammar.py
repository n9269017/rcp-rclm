from __future__ import annotations

from collections.abc import Sequence

from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase11.constants import (
    COMPONENT_CODE_TO_COMPONENT,
    PHASE11_ARCHITECTURE_MUTATION,
    PHASE11_DATA_SELECTION,
    PHASE11_OBJECTIVE,
    PHASE11_PROGRAM_VERSION,
    PHASE11_ROLLBACK_MODE,
    UPDATE_CODE_TO_CLASS,
)
from rcp_rclm_runtime_v3.phase11.records import (
    ArchitectureMutationDirective,
    DataSelectionDirective,
    ResourceRequest,
    RollbackDeclaration,
    TrainingDirective,
    TypedMutationProgram,
)

_FIELD_ORDER = ("O", "U", "D", "A", "R", "E", "B", "G", "P")
_UPDATE_CODE_ORDER = ("W", "G", "P", "V")
_COMPONENT_CODE_ORDER = ("W", "G", "P", "V")


def _parse_positive_int(value: str, path: str, *, minimum: int = 0) -> int:
    if not value or any(character not in "0123456789" for character in value):
        raise SchemaValidationError(path, "expected an unsigned decimal integer")
    parsed = int(value)
    if parsed < minimum:
        raise SchemaValidationError(path, f"expected an integer >= {minimum}")
    return parsed


def _parse_codes(
    value: str,
    mapping: dict[str, str],
    path: str,
) -> tuple[str, ...]:
    if not value:
        raise SchemaValidationError(path, "at least one code is required")
    if len(set(value)) != len(value):
        raise SchemaValidationError(path, "duplicate code")
    unknown = tuple(code for code in value if code not in mapping)
    if unknown:
        raise SchemaValidationError(path, f"unsupported code sequence: {''.join(unknown)}")
    return tuple(sorted((mapping[code] for code in value), key=lambda item: item.encode("utf-8")))


def parse_typed_mutation_program(raw: bytes) -> TypedMutationProgram:
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaValidationError("phase11.program", "program must be ASCII") from exc
    if not text or text != text.strip() or any(character.isspace() for character in text):
        raise SchemaValidationError("phase11.program", "whitespace is forbidden")
    parts = text.split(";")
    if parts[0] != PHASE11_PROGRAM_VERSION:
        raise SchemaValidationError("phase11.program.version", "unsupported program version")
    if len(parts) != len(_FIELD_ORDER) + 1:
        raise SchemaValidationError("phase11.program", "field count mismatch")
    fields: dict[str, str] = {}
    for expected_key, part in zip(_FIELD_ORDER, parts[1:], strict=True):
        if "=" not in part:
            raise SchemaValidationError("phase11.program", "field assignment is missing")
        key, value = part.split("=", 1)
        if key != expected_key:
            raise SchemaValidationError(
                "phase11.program",
                f"expected field {expected_key}, observed {key}",
            )
        fields[key] = value

    if fields["O"] != "F":
        raise SchemaValidationError("phase11.program.objective", "unsupported objective code")
    if fields["D"] != "A":
        raise SchemaValidationError("phase11.program.data", "unsupported data-selection code")
    if fields["A"] != "N":
        raise SchemaValidationError("phase11.program.architecture", "unsupported architecture code")
    if fields["B"] != "X":
        raise SchemaValidationError("phase11.program.rollback", "unsupported rollback code")

    resource_fields = fields["R"].split(",")
    if len(resource_fields) != 6:
        raise SchemaValidationError("phase11.program.resource", "expected six resource integers")
    resource_values = tuple(
        _parse_positive_int(value, f"phase11.program.resource[{index}]", minimum=0)
        for index, value in enumerate(resource_fields)
    )
    wall_clock, accelerators, training_steps, output_bytes, candidates, evaluations = resource_values
    if wall_clock < 1 or output_bytes < 1 or candidates < 1 or evaluations < 1:
        raise SchemaValidationError(
            "phase11.program.resource",
            "wall clock, output bytes, candidates, and evaluations must be positive",
        )

    program = TypedMutationProgram(
        objective=PHASE11_OBJECTIVE,
        selected_update_classes=_parse_codes(
            fields["U"],
            UPDATE_CODE_TO_CLASS,
            "phase11.program.update_classes",
        ),
        training_policy=TrainingDirective(
            optimizer="sgd",
            steps=training_steps,
            learning_rate_numerator=1,
            learning_rate_denominator=1,
            seed=1729,
        ),
        data_selection=DataSelectionDirective(
            selection_id=PHASE11_DATA_SELECTION,
            heldout_task_ids_visible=False,
            heldout_prompts_visible=False,
            heldout_reference_answers_visible=False,
        ),
        architecture_mutation=ArchitectureMutationDirective(
            kind=PHASE11_ARCHITECTURE_MUTATION,
            lora_rank=0,
            target_modules=(),
        ),
        resource_request=ResourceRequest(
            wall_clock_seconds=wall_clock,
            accelerator_count=accelerators,
            training_steps=training_steps,
            output_bytes=output_bytes,
            candidate_count=candidates,
            evaluation_calls=evaluations,
        ),
        expected_affected_components=_parse_codes(
            fields["E"],
            COMPONENT_CODE_TO_COMPONENT,
            "phase11.program.expected_components",
        ),
        rollback_declaration=RollbackDeclaration(
            mode=PHASE11_ROLLBACK_MODE,
            predecessor_bytes_required=True,
        ),
        successor_generator_generation=_parse_positive_int(
            fields["G"],
            "phase11.program.successor_generator_generation",
            minimum=1,
        ),
        successor_planner_generation=_parse_positive_int(
            fields["P"],
            "phase11.program.successor_planner_generation",
            minimum=1,
        ),
    )
    if encode_typed_mutation_program(program) != raw:
        raise SchemaValidationError("phase11.program", "program is not in canonical form")
    return program


def _codes_for_values(
    values: Sequence[str],
    mapping: dict[str, str],
    order: Sequence[str],
    path: str,
) -> str:
    inverse = {value: code for code, value in mapping.items()}
    unknown = tuple(value for value in values if value not in inverse)
    if unknown:
        raise SchemaValidationError(path, f"unsupported values: {unknown}")
    selected = {inverse[value] for value in values}
    return "".join(code for code in order if code in selected)


def encode_typed_mutation_program(program: TypedMutationProgram) -> bytes:
    if program.objective != PHASE11_OBJECTIVE:
        raise SchemaValidationError("phase11.program.objective", "unsupported objective")
    request = program.resource_request
    update_codes = _codes_for_values(
        program.selected_update_classes,
        UPDATE_CODE_TO_CLASS,
        _UPDATE_CODE_ORDER,
        "phase11.program.selected_update_classes",
    )
    component_codes = _codes_for_values(
        program.expected_affected_components,
        COMPONENT_CODE_TO_COMPONENT,
        _COMPONENT_CODE_ORDER,
        "phase11.program.expected_affected_components",
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


__all__ = ["encode_typed_mutation_program", "parse_typed_mutation_program"]
