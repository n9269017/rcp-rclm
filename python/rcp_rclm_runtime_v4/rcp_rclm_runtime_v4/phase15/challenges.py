from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask

from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_EXTERNAL_CHALLENGE_SEED,
    PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH,
    TaskDomain,
    cast_task_domain,
)
from rcp_rclm_runtime_v4.phase15.curriculum import expected_plan
from rcp_rclm_runtime_v4.phase15.decoder import NAME_BY_TOKEN


def _hex_digest(*values: str) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _odd_lean_pair(digest: str) -> tuple[int, int]:
    candidates = tuple(
        (a, b)
        for a in range(0, 8)
        for b in range(a + 1, 9)
        if (a + b) % 2 == 1
    )
    return candidates[int(digest[0:8], 16) % len(candidates)]


def _odd_program_pair(digest: str) -> tuple[int, int]:
    candidates = tuple(
        (a, b)
        for a in range(-4, 5)
        if a != 0
        for b in range(-8, 9)
        if (a + b) % 2 == 1
    )
    return candidates[int(digest[8:16], 16) % len(candidates)]


@dataclass(frozen=True, slots=True)
class DynamicHiddenChallenge:
    challenge_id: str
    domain: TaskDomain
    commitment_hash: str
    parameter_a: int
    parameter_b: int
    generated_after_candidate_freeze: bool
    predecessor_required_to_fail: bool = True
    novelty_partition: str = "odd_parameter_sum_unseen_pair"

    schema_id: ClassVar[str] = "runtime.v4.phase15.dynamic_hidden_challenge.v1"

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise SchemaValidationError("phase15.challenge.challenge_id", "must be nonempty")
        cast_task_domain(self.domain, "phase15.challenge.domain")
        if len(self.commitment_hash) != 64 or any(character not in "0123456789abcdef" for character in self.commitment_hash):
            raise SchemaValidationError("phase15.challenge.commitment_hash", "expected lowercase SHA-256")
        if self.generated_after_candidate_freeze is not True:
            raise SchemaValidationError("phase15.challenge", "challenge must be post-freeze")
        if self.predecessor_required_to_fail is not True:
            raise SchemaValidationError("phase15.challenge", "predecessor failure is required")
        expected_plan(self.domain, self.parameter_a, self.parameter_b)
        if (self.parameter_a + self.parameter_b) % 2 != 1:
            raise SchemaValidationError("phase15.challenge", "challenge pair is not outside public partition")

    @property
    def expected_plan_tokens(self) -> tuple[int, ...]:
        return expected_plan(self.domain, self.parameter_a, self.parameter_b)

    @property
    def expected_plan_text(self) -> str:
        return " ".join(NAME_BY_TOKEN[token] for token in self.expected_plan_tokens)

    @property
    def task_id(self) -> str:
        if self.domain == "lean_multistep":
            return f"lean.phase15.dynamic.multistep.{self.commitment_hash[:16]}"
        return f"program.phase15.dynamic.affine.{self.commitment_hash[:16]}"

    @property
    def public_prompt(self) -> str:
        if self.domain == "lean_multistep":
            return (
                "Construct a bounded multi-step Lean proof plan for the theorem "
                f"x + {self.parameter_a} < x + {self.parameter_b}."
            )
        return (
            "Synthesize a bounded integer program implementing "
            f"f(x) = {self.parameter_a} * x + {self.parameter_b}."
        )

    @property
    def prompt_hash(self) -> str:
        return sha256_hex(self.public_prompt.encode("utf-8"))

    @property
    def verifier_spec_hash(self) -> str:
        return canonical_json_hash(
            {
                "domain": self.domain,
                "plan_grammar": "phase15-selected-plan-grammar-v1",
                "pinned_lean": True,
                "exhaustive_integer_tests": self.domain == "integer_program",
                "novelty_partition": self.novelty_partition,
            }
        )

    def gate_d_task(self) -> LeanCompletionTask:
        source_prefix = (
            "import Mathlib\n\n"
            + (
                f"example (x : Nat) : x + {self.parameter_a} < x + {self.parameter_b} := by\n  "
                if self.domain == "lean_multistep"
                else (
                    f"def phase15Candidate (x : Int) : Int := {self.parameter_a} * x + {self.parameter_b}\n\n"
                    f"example (x : Int) : phase15Candidate x = {self.parameter_a} * x + {self.parameter_b} := by\n  "
                )
            )
        )
        marker = b"L" if self.domain == "lean_multistep" else b"P"
        return LeanCompletionTask(
            task_id=self.task_id,
            partition="heldout",
            model_prompt=self.public_prompt.encode("ascii") + b"\n" + marker,
            source_prefix=source_prefix,
            expected_completion=self.expected_plan_text,
        )

    def commitment_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.v4.phase15.challenge_commitment.v1",
            "challenge_id": self.challenge_id,
            "domain": self.domain,
            "commitment_hash": self.commitment_hash,
            "generated_after_candidate_freeze": True,
            "prompt_hash": self.prompt_hash,
            "verifier_spec_hash": self.verifier_spec_hash,
            "private_parameters_visible": False,
            "reference_answer_visible": False,
            "successful_candidate_visible": False,
        }

    def private_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "challenge_id": self.challenge_id,
            "domain": self.domain,
            "commitment_hash": self.commitment_hash,
            "parameter_a": self.parameter_a,
            "parameter_b": self.parameter_b,
            "public_prompt": self.public_prompt,
            "expected_plan_tokens": list(self.expected_plan_tokens),
            "expected_plan_text": self.expected_plan_text,
            "generated_after_candidate_freeze": True,
            "predecessor_required_to_fail": True,
            "novelty_partition": self.novelty_partition,
        }


def challenge_suite_after_freeze(
    *,
    source_head: str,
    candidate_freeze_hashes: Sequence[str],
    phase14_bundle_manifest_hash: str = PHASE15_EXPECTED_PHASE14_BUNDLE_MANIFEST_HASH,
    external_seed: str = PHASE15_EXTERNAL_CHALLENGE_SEED,
) -> tuple[DynamicHiddenChallenge, ...]:
    freezes = tuple(candidate_freeze_hashes)
    if len(freezes) != 2 or len(set(freezes)) != 2:
        raise SchemaValidationError("phase15.challenge.freeze_hashes", "exactly two unique candidate hashes required")
    if any(len(value) != 64 for value in freezes):
        raise SchemaValidationError("phase15.challenge.freeze_hashes", "expected SHA-256 values")
    seed = _hex_digest(
        source_head,
        phase14_bundle_manifest_hash,
        *freezes,
        external_seed,
    )
    lean_a, lean_b = _odd_lean_pair(seed)
    program_a, program_b = _odd_program_pair(seed)
    private_values = (
        ("phase15-dynamic-lean", "lean_multistep", lean_a, lean_b),
        ("phase15-dynamic-program", "integer_program", program_a, program_b),
    )
    challenges: list[DynamicHiddenChallenge] = []
    for challenge_id, domain, parameter_a, parameter_b in private_values:
        commitment = canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase15.challenge_private_commitment.v1",
                "challenge_id": challenge_id,
                "domain": domain,
                "parameter_a": parameter_a,
                "parameter_b": parameter_b,
                "source_head": source_head,
                "phase14_bundle_manifest_hash": phase14_bundle_manifest_hash,
                "candidate_freeze_hashes": list(freezes),
                "external_seed_hash": sha256_hex(external_seed.encode("utf-8")),
            }
        )
        challenges.append(
            DynamicHiddenChallenge(
                challenge_id=challenge_id,
                domain=cast_task_domain(domain),
                commitment_hash=commitment,
                parameter_a=parameter_a,
                parameter_b=parameter_b,
                generated_after_candidate_freeze=True,
            )
        )
    return tuple(challenges)


def challenge_manifest_json(
    challenges: Sequence[DynamicHiddenChallenge],
    *,
    candidate_freeze_hashes: Sequence[str],
) -> dict[str, object]:
    ordered = tuple(sorted(challenges, key=lambda item: item.challenge_id.encode("utf-8")))
    content = {
        "schema_id": "runtime.v4.phase15.challenge_manifest.v1",
        "challenges": [item.commitment_json() for item in ordered],
        "candidate_freeze_hashes": list(candidate_freeze_hashes),
        "generated_after_candidate_freeze": True,
        "private_parameters_visible_before_freeze": False,
        "reference_answers_visible_before_freeze": False,
        "answer_store_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def answer_store_json(challenges: Sequence[DynamicHiddenChallenge]) -> dict[str, object]:
    ordered = tuple(sorted(challenges, key=lambda item: item.challenge_id.encode("utf-8")))
    content = {
        "schema_id": "runtime.v4.phase15.private_answer_store.v1",
        "answers": [item.private_json() for item in ordered],
        "available_only_after_candidate_freeze": True,
        "training_backend_access": False,
        "candidate_builder_access": False,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def challenges_from_answer_store(value: object) -> tuple[DynamicHiddenChallenge, ...]:
    if not isinstance(value, dict):
        raise SchemaValidationError("phase15.answer_store", "expected object")
    raw = value.get("answers")
    if not isinstance(raw, list):
        raise SchemaValidationError("phase15.answer_store.answers", "expected array")
    result: list[DynamicHiddenChallenge] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SchemaValidationError(f"phase15.answer_store.answers[{index}]", "expected object")
        result.append(
            DynamicHiddenChallenge(
                challenge_id=str(item.get("challenge_id")),
                domain=cast_task_domain(str(item.get("domain"))),
                commitment_hash=str(item.get("commitment_hash")),
                parameter_a=int(item.get("parameter_a")),
                parameter_b=int(item.get("parameter_b")),
                generated_after_candidate_freeze=bool(item.get("generated_after_candidate_freeze")),
                predecessor_required_to_fail=bool(item.get("predecessor_required_to_fail")),
                novelty_partition=str(item.get("novelty_partition")),
            )
        )
    challenges = tuple(sorted(result, key=lambda item: item.challenge_id.encode("utf-8")))
    if answer_store_json(challenges) != value:
        raise SchemaValidationError("phase15.answer_store", "answer store does not round trip")
    return challenges


__all__ = [
    "DynamicHiddenChallenge",
    "answer_store_json",
    "challenges_from_answer_store",
    "challenge_manifest_json",
    "challenge_suite_after_freeze",
]
