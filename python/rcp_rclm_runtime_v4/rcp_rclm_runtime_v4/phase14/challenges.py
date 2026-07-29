from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask

from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE14_COMPLETION,
    PHASE14_MIN_PROMOTIONS,
    PHASE14_PROBE_BIT_END,
    PHASE14_PROBE_BIT_START,
    PHASE14_SLOT_COUNT,
    PHASE14_SLOT_START,
)


@dataclass(frozen=True, slots=True)
class HiddenChallenge:
    challenge_id: str
    nonce: str
    theorem_statement: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.hidden_challenge.v2"

    def __post_init__(self) -> None:
        if not self.challenge_id or not self.nonce or not self.theorem_statement:
            raise SchemaValidationError(
                "phase14.challenge",
                "challenge fields must be nonempty",
            )

    @property
    def commitment_hash(self) -> str:
        return canonical_json_hash(self.private_json())

    @property
    def slot_token_id(self) -> int:
        return (
            PHASE14_SLOT_START
            + int(self.commitment_hash[:8], 16) % PHASE14_SLOT_COUNT
        )

    @property
    def probe_required(self) -> bool:
        probe_word = self.commitment_hash[
            PHASE14_PROBE_BIT_START:PHASE14_PROBE_BIT_END
        ]
        return int(probe_word, 16) % 2 == 0

    @property
    def task_id(self) -> str:
        return f"lean.phase14.{self.challenge_id}"

    @property
    def task(self) -> LeanCompletionTask:
        marker = bytes((self.slot_token_id,))
        return LeanCompletionTask(
            task_id=self.task_id,
            partition="heldout",
            model_prompt=(
                b"Complete the following hidden Phase 14 Lean theorem. "
                b"Use the committed schedule-free capability slot.\n"
                + marker
            ),
            source_prefix=(
                "import Mathlib\n\n"
                'macro "q" : tactic => `(tactic| omega)\n\n'
                f"example (n : Nat) : {self.theorem_statement} := by\n  "
            ),
            expected_completion=PHASE14_COMPLETION,
        )

    def private_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "challenge_id": self.challenge_id,
            "nonce": self.nonce,
            "theorem_statement": self.theorem_statement,
        }

    @classmethod
    def from_private_json(cls, value: object) -> HiddenChallenge:
        if not isinstance(value, dict):
            raise SchemaValidationError(
                "phase14.challenge",
                "expected private challenge object",
            )
        required = {
            "schema_id",
            "challenge_id",
            "nonce",
            "theorem_statement",
        }
        if set(value) != required or value.get("schema_id") != cls.schema_id:
            raise SchemaValidationError(
                "phase14.challenge",
                "private challenge schema mismatch",
            )
        return cls(
            challenge_id=str(value["challenge_id"]),
            nonce=str(value["nonce"]),
            theorem_statement=str(value["theorem_statement"]),
        )

    def commitment_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.v4.phase14.challenge_commitment.v2",
            "challenge_commitment_hash": self.commitment_hash,
            "task_class": "lean_theorem_completion_v1",
            "slot_derivation": "sha256_prefix_mod_64_plus_180",
            "probe_policy": "commitment_word_8_16_even_requires_exploration_probe",
            "slot_token_id": self.slot_token_id,
            "prompt_visible_before_freeze": False,
            "source_visible_before_freeze": False,
            "reference_answer_visible_before_freeze": False,
            "successful_update_family_visible_before_freeze": False,
        }

    def answer_store_json(self) -> dict[str, object]:
        task = self.task
        return {
            "schema_id": "runtime.v4.phase14.hidden_answer_record.v2",
            "challenge_commitment_hash": self.commitment_hash,
            "private_challenge": self.private_json(),
            "task": task.to_json(include_answer=True),
            "task_prompt_sha256": sha256_hex(task.model_prompt),
            "available_only_after_candidate_freeze": True,
            "generator_access": False,
            "planner_access": False,
            "proposal_worker_access": False,
            "candidate_builder_access": False,
            "successful_update_family_recorded": False,
        }


_THEOREM_POOL: Final[Sequence[tuple[str, str]]] = (
    ("add_zero", "n + 0 = n"),
    ("lt_add_three", "n < n + 3"),
    ("zero_lt_succ", "0 < n + 1"),
    ("succ_le_add_two", "n + 1 <= n + 2"),
    ("le_add_four", "n <= n + 4"),
    ("lt_add_five", "n < n + 5"),
    ("two_le_add_two", "2 <= n + 2"),
    ("add_one_positive", "0 < n + 1"),
)

DEVELOPMENT_CHALLENGE_SEED: Final[str] = sha256_hex(
    b"RCP-RCLM-PHASE14-DEVELOPMENT-HIDDEN-CHALLENGE-SEED-V2"
)


def _validate_seed(seed_hex: str) -> str:
    if len(seed_hex) != 64 or any(
        character not in "0123456789abcdef" for character in seed_hex
    ):
        raise SchemaValidationError(
            "phase14.challenge_seed",
            "expected lowercase 32-byte hexadecimal seed",
        )
    return seed_hex


def _challenge_for_probe_policy(
    *,
    seed: str,
    index: int,
    theorem_id: str,
    theorem_statement: str,
    require_probe: bool,
    occupied_slots: set[int],
) -> HiddenChallenge:
    for counter in range(10_000):
        nonce = canonical_json_hash(
            {
                "seed": seed,
                "index": index,
                "counter": counter,
                "theorem_id": theorem_id,
                "domain": "phase14-private-challenge-nonce-v2",
            }
        )
        challenge = HiddenChallenge(
            challenge_id=f"generation{5 + index}_{theorem_id}",
            nonce=nonce,
            theorem_statement=theorem_statement,
        )
        if challenge.probe_required != require_probe:
            continue
        if challenge.slot_token_id in occupied_slots:
            continue
        return challenge
    raise SchemaValidationError(
        "phase14.challenge_generation",
        "could not construct a unique challenge with the declared probe policy",
    )


def challenge_suite_from_seed(seed_hex: str) -> tuple[HiddenChallenge, ...]:
    seed = _validate_seed(seed_hex)
    theorem_pool = tuple(
        sorted(
            _THEOREM_POOL,
            key=lambda item: canonical_json_hash(
                {
                    "seed": seed,
                    "domain": "phase14-theorem-order-v2",
                    "theorem_id": item[0],
                }
            ),
        )
    )
    selected = theorem_pool[:PHASE14_MIN_PROMOTIONS]
    challenges: list[HiddenChallenge] = []
    occupied_slots: set[int] = set()
    for index, theorem in enumerate(selected):
        theorem_id, theorem_statement = theorem
        challenge = _challenge_for_probe_policy(
            seed=seed,
            index=index,
            theorem_id=theorem_id,
            theorem_statement=theorem_statement,
            require_probe=index < 2,
            occupied_slots=occupied_slots,
        )
        challenges.append(challenge)
        occupied_slots.add(challenge.slot_token_id)
    return tuple(challenges)


def development_challenge_suite() -> tuple[HiddenChallenge, ...]:
    return challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)


def challenge_by_commitment(
    commitment_hash: str,
    challenges: Sequence[HiddenChallenge],
) -> HiddenChallenge:
    matches = tuple(
        item for item in challenges if item.commitment_hash == commitment_hash
    )
    if len(matches) != 1:
        raise SchemaValidationError(
            "phase14.challenge_commitment_hash",
            "unknown or ambiguous hidden challenge commitment",
        )
    return matches[0]


def challenge_manifest_json(
    challenges: Sequence[HiddenChallenge],
) -> dict[str, object]:
    values = tuple(challenges)
    records = [challenge.commitment_json() for challenge in values]
    content = {
        "schema_id": "runtime.v4.phase14.challenge_manifest.v2",
        "challenge_count": len(records),
        "challenges": records,
        "successful_route_disclosed": False,
        "successful_update_family_recorded": False,
        "answers_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def answer_store_json(
    challenges: Sequence[HiddenChallenge],
) -> dict[str, object]:
    values = tuple(challenges)
    records = [challenge.answer_store_json() for challenge in values]
    content = {
        "schema_id": "runtime.v4.phase14.answer_store.v2",
        "answer_count": len(records),
        "answers": records,
        "available_only_after_candidate_freeze": True,
        "proposal_worker_access": False,
        "successful_update_family_recorded": False,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def challenges_from_answer_store(value: object) -> tuple[HiddenChallenge, ...]:
    if not isinstance(value, dict):
        raise SchemaValidationError(
            "phase14.answer_store",
            "expected object",
        )
    answers = value.get("answers")
    if not isinstance(answers, list):
        raise SchemaValidationError(
            "phase14.answer_store.answers",
            "expected array",
        )
    challenges: list[HiddenChallenge] = []
    for index, record in enumerate(answers):
        if not isinstance(record, dict):
            raise SchemaValidationError(
                f"phase14.answer_store.answers[{index}]",
                "expected object",
            )
        challenge = HiddenChallenge.from_private_json(
            record.get("private_challenge")
        )
        if record.get("challenge_commitment_hash") != challenge.commitment_hash:
            raise SchemaValidationError(
                f"phase14.answer_store.answers[{index}]",
                "challenge commitment mismatch",
            )
        challenges.append(challenge)
    result = tuple(challenges)
    expected = answer_store_json(result)
    if value != expected:
        raise SchemaValidationError(
            "phase14.answer_store",
            "answer store content mismatch",
        )
    return result


__all__ = [
    "DEVELOPMENT_CHALLENGE_SEED",
    "HiddenChallenge",
    "answer_store_json",
    "challenge_by_commitment",
    "challenge_manifest_json",
    "challenge_suite_from_seed",
    "challenges_from_answer_store",
    "development_challenge_suite",
]
