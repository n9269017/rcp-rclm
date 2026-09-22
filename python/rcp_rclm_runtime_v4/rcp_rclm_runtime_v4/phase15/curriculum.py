from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase15.constants import (
    CandidateVariant,
    PHASE15_MAX_PLAN_TOKENS,
    TASK_DOMAINS,
    TOKEN_BY_NAME,
    TaskDomain,
    cast_candidate_variant,
    cast_task_domain,
    integer_token,
)


@dataclass(frozen=True, slots=True)
class CurriculumExample:
    example_id: str
    domain: TaskDomain
    parameter_a: int
    parameter_b: int
    plan_tokens: Sequence[int]

    schema_id: ClassVar[str] = "runtime.v4.phase15.curriculum_example.v1"

    def __post_init__(self) -> None:
        if not self.example_id:
            raise SchemaValidationError("phase15.curriculum.example_id", "must be nonempty")
        cast_task_domain(self.domain, "phase15.curriculum.domain")
        plan = tuple(self.plan_tokens)
        if not plan or len(plan) > PHASE15_MAX_PLAN_TOKENS:
            raise SchemaValidationError("phase15.curriculum.plan_tokens", "invalid plan length")
        if plan[-1] != TOKEN_BY_NAME["EOS"]:
            raise SchemaValidationError("phase15.curriculum.plan_tokens", "plan must end with EOS")
        if any(isinstance(token, bool) or not isinstance(token, int) or token < 0 or token >= 32 for token in plan):
            raise SchemaValidationError("phase15.curriculum.plan_tokens", "invalid token")
        object.__setattr__(self, "plan_tokens", plan)

    @property
    def example_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "example_id": self.example_id,
            "domain": self.domain,
            "parameter_a": self.parameter_a,
            "parameter_b": self.parameter_b,
            "plan_tokens": list(self.plan_tokens),
        }


def expected_plan(domain: TaskDomain, parameter_a: int, parameter_b: int) -> tuple[int, ...]:
    cast_task_domain(domain)
    a_token = integer_token(parameter_a)
    b_token = integer_token(parameter_b)
    if domain == "lean_multistep":
        if not (0 <= parameter_a < parameter_b <= 8):
            raise SchemaValidationError("phase15.curriculum.lean", "invalid selected Lean parameters")
        return (
            TOKEN_BY_NAME["LEAN_BEGIN"],
            a_token,
            b_token,
            TOKEN_BY_NAME["LEAN_HAVE"],
            TOKEN_BY_NAME["LEAN_OMEGA"],
            TOKEN_BY_NAME["LEAN_EXACT"],
            TOKEN_BY_NAME["EOS"],
        )
    if parameter_a == 0 or abs(parameter_a) > 4 or abs(parameter_b) > 8:
        raise SchemaValidationError("phase15.curriculum.program", "invalid selected program parameters")
    return (
        TOKEN_BY_NAME["PROGRAM_BEGIN"],
        a_token,
        TOKEN_BY_NAME["PROGRAM_MUL"],
        b_token,
        TOKEN_BY_NAME["PROGRAM_ADD"],
        TOKEN_BY_NAME["PROGRAM_RETURN"],
        TOKEN_BY_NAME["EOS"],
    )


def _lean_examples() -> tuple[CurriculumExample, ...]:
    values: list[CurriculumExample] = []
    for parameter_a in range(0, 8):
        for parameter_b in range(parameter_a + 1, 9):
            if (parameter_a + parameter_b) % 2 != 0:
                continue
            values.append(
                CurriculumExample(
                    example_id=f"phase15.public.lean.{parameter_a}.{parameter_b}",
                    domain="lean_multistep",
                    parameter_a=parameter_a,
                    parameter_b=parameter_b,
                    plan_tokens=expected_plan("lean_multistep", parameter_a, parameter_b),
                )
            )
    return tuple(values)


def _program_examples() -> tuple[CurriculumExample, ...]:
    values: list[CurriculumExample] = []
    for parameter_a in range(-4, 5):
        if parameter_a == 0:
            continue
        for parameter_b in range(-8, 9):
            if (parameter_a + parameter_b) % 2 != 0:
                continue
            values.append(
                CurriculumExample(
                    example_id=f"phase15.public.program.{parameter_a}.{parameter_b}",
                    domain="integer_program",
                    parameter_a=parameter_a,
                    parameter_b=parameter_b,
                    plan_tokens=expected_plan("integer_program", parameter_a, parameter_b),
                )
            )
    return tuple(values)


def public_curriculum(variant: CandidateVariant) -> tuple[CurriculumExample, ...]:
    cast_candidate_variant(variant)
    values = list(_lean_examples())
    if variant == "multidomain":
        values.extend(_program_examples())
    return tuple(sorted(values, key=lambda item: item.example_id.encode("utf-8")))


def curriculum_manifest(variant: CandidateVariant) -> dict[str, object]:
    examples = public_curriculum(variant)
    domains = tuple(sorted({item.domain for item in examples}, key=lambda item: item.encode("utf-8")))
    if any(domain not in TASK_DOMAINS for domain in domains):
        raise SchemaValidationError("phase15.curriculum.domains", "unsupported domain")
    content = {
        "schema_id": "runtime.v4.phase15.public_curriculum_manifest.v1",
        "variant": variant,
        "domains": list(domains),
        "example_count": len(examples),
        "examples": [item.to_json() for item in examples],
        "pair_partition": "even_parameter_sum_only",
        "heldout_task_ids_visible": False,
        "heldout_prompts_visible": False,
        "heldout_reference_answers_visible": False,
        "private_challenge_source_visible": False,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


__all__ = [
    "CurriculumExample",
    "curriculum_manifest",
    "expected_plan",
    "public_curriculum",
]
