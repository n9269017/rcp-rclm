from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID

TaskPartition = Literal["training", "protected", "heldout"]

TRANSITION_RAW_VALUE: Final[int] = 24_576
TRANSITION_SCORE_DIVISOR: Final[int] = 2_048
TRANSITION_SCORE: Final[int] = TRANSITION_RAW_VALUE // TRANSITION_SCORE_DIVISOR
MAX_COMPLETION_TOKENS: Final[int] = 16
PROTECTED_MARKER: Final[int] = ord("R")
LEARNED_MARKER: Final[int] = ord("O")


def completion_chain(marker: int, completion: bytes) -> Sequence[tuple[int, int]]:
    if not completion:
        raise ValueError("completion must be nonempty")
    values = [marker, *completion]
    pairs = [(values[index], values[index + 1]) for index in range(len(values) - 1)]
    pairs.append((values[-1], EOS_TOKEN_ID))
    return tuple(pairs)


PROTECTED_CHAIN: Final[Sequence[tuple[int, int]]] = completion_chain(
    PROTECTED_MARKER, b"rfl"
)
LEARNED_CHAIN: Final[Sequence[tuple[int, int]]] = completion_chain(
    LEARNED_MARKER, b"omega"
)


@dataclass(frozen=True, slots=True)
class TrainingExample:
    example_id: str
    model_prompt: bytes
    completion: bytes

    schema_id: ClassVar[str] = "runtime.v3.phase10.training_example.v1"

    def __post_init__(self) -> None:
        if not self.example_id:
            raise SchemaValidationError("phase10.training_example.example_id", "must be nonempty")
        if not self.model_prompt:
            raise SchemaValidationError("phase10.training_example.model_prompt", "must be nonempty")
        if not self.completion:
            raise SchemaValidationError("phase10.training_example.completion", "must be nonempty")
        if any(value >= 256 for value in self.model_prompt + self.completion):
            raise SchemaValidationError(
                "phase10.training_example", "selected training text must use byte tokens"
            )

    @property
    def marker(self) -> int:
        return self.model_prompt[-1]

    @property
    def transition_pairs(self) -> Sequence[tuple[int, int]]:
        return completion_chain(self.marker, self.completion)

    @property
    def prompt_hash(self) -> str:
        return sha256_hex(self.model_prompt)

    @property
    def completion_hash(self) -> str:
        return sha256_hex(self.completion)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "example_id": self.example_id,
            "model_prompt_sha256": self.prompt_hash,
            "completion_sha256": self.completion_hash,
            "prompt_token_count": len(self.model_prompt),
            "completion_token_count": len(self.completion),
            "marker_token_id": self.marker,
            "transition_pairs": [
                {"current_token_id": current, "target_token_id": target}
                for current, target in self.transition_pairs
            ],
        }


@dataclass(frozen=True, slots=True)
class LeanCompletionTask:
    task_id: str
    partition: TaskPartition
    model_prompt: bytes
    source_prefix: str
    expected_completion: str

    schema_id: ClassVar[str] = "runtime.v3.phase10.lean_completion_task.v1"

    def __post_init__(self) -> None:
        if not self.task_id:
            raise SchemaValidationError("phase10.task.task_id", "must be nonempty")
        if self.partition not in {"training", "protected", "heldout"}:
            raise SchemaValidationError("phase10.task.partition", "unsupported partition")
        if not self.model_prompt:
            raise SchemaValidationError("phase10.task.model_prompt", "must be nonempty")
        if not self.source_prefix.endswith("  "):
            raise SchemaValidationError(
                "phase10.task.source_prefix", "source prefix must end at an indented tactic position"
            )
        completion_bytes = self.expected_completion.encode("ascii")
        if not completion_bytes or any(value >= 128 for value in completion_bytes):
            raise SchemaValidationError(
                "phase10.task.expected_completion", "completion must be nonempty ASCII"
            )

    @property
    def marker(self) -> int:
        return self.model_prompt[-1]

    @property
    def prompt_hash(self) -> str:
        return sha256_hex(self.model_prompt)

    @property
    def source_prefix_hash(self) -> str:
        return sha256_hex(self.source_prefix.encode("utf-8"))

    @property
    def expected_completion_hash(self) -> str:
        return sha256_hex(self.expected_completion.encode("ascii"))

    @property
    def task_hash(self) -> str:
        return canonical_json_hash(self.to_json(include_answer=False))

    def render_source(self, completion: str) -> str:
        if not completion or any(ord(character) >= 128 for character in completion):
            raise SchemaValidationError("phase10.task.completion", "completion must be ASCII")
        if "\n" in completion or "\r" in completion:
            raise SchemaValidationError("phase10.task.completion", "multiline completion is forbidden")
        return f"{self.source_prefix}{completion}\n"

    def to_json(self, *, include_answer: bool) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "partition": self.partition,
            "model_prompt_sha256": self.prompt_hash,
            "source_prefix_sha256": self.source_prefix_hash,
            "marker_token_id": self.marker,
        }
        if include_answer:
            value["expected_completion"] = self.expected_completion
            value["expected_completion_sha256"] = self.expected_completion_hash
        return value


PROTECTED_TRAINING_EXAMPLE: Final[TrainingExample] = TrainingExample(
    example_id="phase10.train.protected.rfl",
    model_prompt=(
        b"Lean theorem completion. Reflexive equality. Completion class R.\nR"
    ),
    completion=b"rfl",
)

OMEGA_TRAINING_EXAMPLES: Final[Sequence[TrainingExample]] = (
    TrainingExample(
        example_id="phase10.train.omega.successor",
        model_prompt=(
            b"Lean theorem completion. Linear natural arithmetic successor fact. "
            b"Completion class O.\nO"
        ),
        completion=b"omega",
    ),
    TrainingExample(
        example_id="phase10.train.omega.monotone",
        model_prompt=(
            b"Lean theorem completion. Linear natural arithmetic monotonicity fact. "
            b"Completion class O.\nO"
        ),
        completion=b"omega",
    ),
)

PROTECTED_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id="lean.phase10.protected.reflexive_seven",
    partition="protected",
    model_prompt=(
        b"Complete the following Lean theorem. Reflexive equality. Completion class R.\nR"
    ),
    source_prefix="import Mathlib\n\nexample : (7 : Nat) = 7 := by\n  ",
    expected_completion="rfl",
)

HELDOUT_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id="lean.phase10.heldout.linear_gap",
    partition="heldout",
    model_prompt=(
        b"Complete the following Lean theorem. Linear natural arithmetic gap. "
        b"Completion class O.\nO"
    ),
    source_prefix=(
        "import Mathlib\n\n"
        "example (a b : Nat) (h : a + 2 <= b) : a < b := by\n  "
    ),
    expected_completion="omega",
)


def training_manifest(examples: Sequence[TrainingExample]) -> dict[str, object]:
    ordered = tuple(sorted(examples, key=lambda item: item.example_id.encode("utf-8")))
    pairs = sorted(
        {pair for example in ordered for pair in example.transition_pairs},
        key=lambda item: (item[0], item[1]),
    )
    content = {
        "schema_id": "runtime.v3.phase10.training_data_manifest.v1",
        "task_class": "lean_theorem_completion_v1",
        "examples": [example.to_json() for example in ordered],
        "transition_pairs": [
            {"current_token_id": current, "target_token_id": target}
            for current, target in pairs
        ],
        "heldout_task_ids_visible": False,
        "heldout_prompts_visible": False,
        "heldout_reference_answers_visible": False,
    }
    value = dict(content)
    value["manifest_hash"] = canonical_json_hash(content)
    return value


def heldout_manifest() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase10.heldout_task_manifest.v1",
        "tasks": [HELDOUT_TASK.to_json(include_answer=False)],
        "answer_store_separate": True,
    }
    value = dict(content)
    value["manifest_hash"] = canonical_json_hash(content)
    return value


def heldout_answer_store() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase10.heldout_answer_store.v1",
        "answers": [HELDOUT_TASK.to_json(include_answer=True)],
        "training_backend_access": False,
        "available_only_after_candidate_freeze": True,
    }
    value = dict(content)
    value["answer_store_hash"] = canonical_json_hash(content)
    return value


__all__ = [
    "HELDOUT_TASK",
    "LEARNED_CHAIN",
    "LEARNED_MARKER",
    "LeanCompletionTask",
    "MAX_COMPLETION_TOKENS",
    "OMEGA_TRAINING_EXAMPLES",
    "PROTECTED_CHAIN",
    "PROTECTED_MARKER",
    "PROTECTED_TASK",
    "PROTECTED_TRAINING_EXAMPLE",
    "TRANSITION_RAW_VALUE",
    "TRANSITION_SCORE",
    "TRANSITION_SCORE_DIVISOR",
    "TrainingExample",
    "completion_chain",
    "heldout_answer_store",
    "heldout_manifest",
    "training_manifest",
]
