from __future__ import annotations

from collections.abc import Mapping, Sequence

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_VARIANTS_PER_FAMILY,
    UPDATE_FAMILIES,
    UPDATE_OPERATION_BY_FAMILY,
    UpdateFamily,
)
from rcp_rclm_runtime_v4.phase16.records import ModelState, MutationProgram


def _signed_parameter(seed_hash: str, offset: int) -> int:
    start = (offset * 2) % 56
    value = int(seed_hash[start : start + 8], 16)
    return value % 33 - 16


def legal_mutation_programs(
    state: ModelState,
    *,
    promotion_index: int,
    public_nonce_hash: str,
) -> tuple[MutationProgram, ...]:
    programs: list[MutationProgram] = []
    for family_index, family in enumerate(UPDATE_FAMILIES):
        generation = state.component_generations[family] + 1
        for variant in range(PHASE16_VARIANTS_PER_FAMILY):
            seed_hash = canonical_json_hash(
                {
                    "domain": "phase16.legal_mutation_program.v1",
                    "active_package_hash": state.active_package_hash,
                    "promotion_index": promotion_index,
                    "family": family,
                    "variant": variant,
                    "generation": generation,
                    "public_nonce_hash": public_nonce_hash,
                }
            )
            programs.append(
                MutationProgram(
                    promotion_index=promotion_index,
                    family=family,
                    variant=variant,
                    generation=generation,
                    operation_id=UPDATE_OPERATION_BY_FAMILY[family],
                    parameter_a=_signed_parameter(seed_hash, family_index + variant),
                    parameter_b=_signed_parameter(seed_hash, family_index + variant + 7),
                    public_nonce_hash=public_nonce_hash,
                )
            )
    return tuple(
        sorted(programs, key=lambda program: program.program_hash.encode("ascii"))
    )


def execute_program(
    program: MutationProgram,
    public_input: Mapping[str, object],
) -> dict[str, object]:
    vector_value = public_input.get("input_vector")
    if not isinstance(vector_value, Sequence) or isinstance(
        vector_value, (str, bytes, bytearray)
    ):
        raise ValueError("public input vector is missing")
    vector = tuple(int(item) for item in vector_value)
    if len(vector) != 4:
        raise ValueError("public input vector must contain four integers")
    a = program.parameter_a
    b = program.parameter_b
    v = program.variant + 1
    family: UpdateFamily = program.family
    if family == "memory_policy":
        output = tuple(vector[(index + v) % 4] + (a if index == 0 else 0) for index in range(4))
    elif family == "retrieval_policy":
        output = tuple(vector[(index * v + abs(b)) % 4] for index in range(4))
    elif family == "planner_policy":
        output = (
            vector[0] + a,
            vector[1] * v,
            vector[2] - b,
            vector[3] + vector[0] * v,
        )
    elif family == "adapter_policy":
        output = tuple(item * v + a - b for item in vector)
    elif family == "optimizer_policy":
        current = sum(vector) + a
        values = []
        for index in range(4):
            current = current + (index + 1) * v - b
            values.append(current)
        output = tuple(values)
    elif family == "verification_automation_policy":
        output = tuple(sorted((item + a * v - b for item in vector)))
    elif family == "tool_policy":
        output = (
            vector[0] + vector[1] + a,
            vector[1] - vector[2] + b,
            vector[2] * v,
            vector[3] + a - b,
        )
    else:
        depth = v + 1
        output = tuple(
            vector[(index + depth) % 4] + a * (index + 1) + b
            for index in range(4)
        )
    return {
        "schema_id": "runtime.v4.phase16.program_execution.v1",
        "family": family,
        "variant": program.variant,
        "generation": program.generation,
        "operation_id": program.operation_id,
        "output_vector": list(output),
        "program_hash": program.program_hash,
    }


def output_hash(program: MutationProgram, public_input: Mapping[str, object]) -> str:
    return canonical_json_hash(execute_program(program, public_input))


__all__ = ["execute_program", "legal_mutation_programs", "output_hash"]
