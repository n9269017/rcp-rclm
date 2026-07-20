from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer, strict_object
from rcp_rclm_runtime_v3.contract.common import require_hash, require_schema
from rcp_rclm_runtime_v3.phase10.constants import MODEL_WIDTH, VOCAB_SIZE
from rcp_rclm_runtime_v3.phase10.learned_data import TRANSITION_RAW_VALUE

TrainingMode = Literal["bootstrap", "successor"]


@dataclass(frozen=True, slots=True)
class TrainingPair:
    current_token_id: int
    target_token_id: int

    schema_id: ClassVar[str] = "runtime.v3.phase10.training_pair.v1"

    def __post_init__(self) -> None:
        for name, value in (
            ("current_token_id", self.current_token_id),
            ("target_token_id", self.target_token_id),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < VOCAB_SIZE:
                raise SchemaValidationError(f"phase10.training_pair.{name}", "outside vocabulary")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "current_token_id": self.current_token_id,
            "target_token_id": self.target_token_id,
        }

    @classmethod
    def from_json(cls, value: object) -> "TrainingPair":
        obj = strict_object(
            value,
            "phase10.training_pair",
            {"schema_id", "current_token_id", "target_token_id"},
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.training_pair.schema_id")
        return cls(
            current_token_id=require_structural_integer(
                obj["current_token_id"], "phase10.training_pair.current_token_id", minimum=0, maximum=VOCAB_SIZE - 1
            ),
            target_token_id=require_structural_integer(
                obj["target_token_id"], "phase10.training_pair.target_token_id", minimum=0, maximum=VOCAB_SIZE - 1
            ),
        )


@dataclass(frozen=True, slots=True)
class TrainingRequest:
    transition_id: str
    mode: TrainingMode
    predecessor_tensor_sha256: str
    training_data_manifest_hash: str
    pairs: Sequence[TrainingPair]
    seed: int = 1729
    optimizer_steps: int = 1
    learning_rate_numerator: int = 1
    learning_rate_denominator: int = 1
    target_raw_value: int = TRANSITION_RAW_VALUE

    schema_id: ClassVar[str] = "runtime.v3.phase10.training_request.v1"

    def __post_init__(self) -> None:
        if not self.transition_id:
            raise SchemaValidationError("phase10.training_request.transition_id", "must be nonempty")
        if self.mode not in {"bootstrap", "successor"}:
            raise SchemaValidationError("phase10.training_request.mode", "unsupported mode")
        require_hash(self.predecessor_tensor_sha256, "phase10.training_request.predecessor_tensor_sha256")
        require_hash(self.training_data_manifest_hash, "phase10.training_request.training_data_manifest_hash")
        pairs = tuple(self.pairs)
        if not pairs:
            raise SchemaValidationError("phase10.training_request.pairs", "at least one pair is required")
        currents = tuple(pair.current_token_id for pair in pairs)
        if len(set(currents)) != len(currents):
            raise SchemaValidationError("phase10.training_request.pairs", "current tokens must be unique")
        ordered = tuple(sorted(pairs, key=lambda pair: (pair.current_token_id, pair.target_token_id)))
        if pairs != ordered:
            raise SchemaValidationError("phase10.training_request.pairs", "pairs must be sorted")
        object.__setattr__(self, "pairs", pairs)
        constants = {
            "seed": 1729,
            "optimizer_steps": 1,
            "learning_rate_numerator": 1,
            "learning_rate_denominator": 1,
            "target_raw_value": TRANSITION_RAW_VALUE,
        }
        for name, expected in constants.items():
            if getattr(self, name) != expected:
                raise SchemaValidationError(f"phase10.training_request.{name}", f"expected {expected}")

    @property
    def request_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "transition_id": self.transition_id,
            "mode": self.mode,
            "predecessor_tensor_sha256": self.predecessor_tensor_sha256,
            "training_data_manifest_hash": self.training_data_manifest_hash,
            "pairs": [pair.to_json() for pair in self.pairs],
            "seed": self.seed,
            "optimizer_steps": self.optimizer_steps,
            "learning_rate_numerator": self.learning_rate_numerator,
            "learning_rate_denominator": self.learning_rate_denominator,
            "target_raw_value": self.target_raw_value,
            "heldout_task_ids_present": False,
            "heldout_prompts_present": False,
            "heldout_reference_answers_present": False,
        }

    @classmethod
    def from_json(cls, value: object) -> "TrainingRequest":
        obj = strict_object(
            value,
            "phase10.training_request",
            {
                "schema_id",
                "transition_id",
                "mode",
                "predecessor_tensor_sha256",
                "training_data_manifest_hash",
                "pairs",
                "seed",
                "optimizer_steps",
                "learning_rate_numerator",
                "learning_rate_denominator",
                "target_raw_value",
                "heldout_task_ids_present",
                "heldout_prompts_present",
                "heldout_reference_answers_present",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.training_request.schema_id")
        for name in (
            "heldout_task_ids_present",
            "heldout_prompts_present",
            "heldout_reference_answers_present",
        ):
            if obj[name] is not False:
                raise SchemaValidationError(f"phase10.training_request.{name}", "must be false")
        mode = require_string(obj["mode"], "phase10.training_request.mode")
        if mode not in {"bootstrap", "successor"}:
            raise SchemaValidationError("phase10.training_request.mode", "unsupported mode")
        raw_pairs = obj["pairs"]
        if not isinstance(raw_pairs, list):
            raise SchemaValidationError("phase10.training_request.pairs", "expected an array")
        return cls(
            transition_id=require_string(obj["transition_id"], "phase10.training_request.transition_id"),
            mode=mode,  # type: ignore[arg-type]
            predecessor_tensor_sha256=require_hash(
                obj["predecessor_tensor_sha256"], "phase10.training_request.predecessor_tensor_sha256"
            ),
            training_data_manifest_hash=require_hash(
                obj["training_data_manifest_hash"], "phase10.training_request.training_data_manifest_hash"
            ),
            pairs=tuple(TrainingPair.from_json(item) for item in raw_pairs),
            seed=require_structural_integer(obj["seed"], "phase10.training_request.seed"),
            optimizer_steps=require_structural_integer(
                obj["optimizer_steps"], "phase10.training_request.optimizer_steps", minimum=1
            ),
            learning_rate_numerator=require_structural_integer(
                obj["learning_rate_numerator"], "phase10.training_request.learning_rate_numerator", minimum=1
            ),
            learning_rate_denominator=require_structural_integer(
                obj["learning_rate_denominator"], "phase10.training_request.learning_rate_denominator", minimum=1
            ),
            target_raw_value=require_structural_integer(
                obj["target_raw_value"], "phase10.training_request.target_raw_value", minimum=1, maximum=32767
            ),
        )


@dataclass(frozen=True, slots=True)
class TrainingReport:
    request_hash: str
    predecessor_tensor_sha256: str
    candidate_tensor_sha256: str
    mode: TrainingMode
    torch_version: str
    device: str
    training_dtype: str
    optimizer: str
    optimizer_steps: int
    loss_before: str
    loss_after: str
    gradient_finite: bool
    changed_entry_count: int

    schema_id: ClassVar[str] = "runtime.v3.phase10.training_report.v1"

    def __post_init__(self) -> None:
        for name in ("request_hash", "predecessor_tensor_sha256", "candidate_tensor_sha256"):
            require_hash(getattr(self, name), f"phase10.training_report.{name}")
        if self.mode not in {"bootstrap", "successor"}:
            raise SchemaValidationError("phase10.training_report.mode", "unsupported mode")
        if self.device != "cpu" or self.training_dtype != "float64" or self.optimizer != "sgd":
            raise SchemaValidationError("phase10.training_report", "unexpected training configuration")
        if self.optimizer_steps != 1:
            raise SchemaValidationError("phase10.training_report.optimizer_steps", "expected one step")
        if self.gradient_finite is not True:
            raise SchemaValidationError("phase10.training_report.gradient_finite", "must be true")
        if self.changed_entry_count < 1:
            raise SchemaValidationError("phase10.training_report.changed_entry_count", "must be positive")
        if self.predecessor_tensor_sha256 == self.candidate_tensor_sha256:
            raise SchemaValidationError("phase10.training_report", "candidate tensor must change")

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "request_hash": self.request_hash,
            "predecessor_tensor_sha256": self.predecessor_tensor_sha256,
            "candidate_tensor_sha256": self.candidate_tensor_sha256,
            "mode": self.mode,
            "torch_version": self.torch_version,
            "device": self.device,
            "training_dtype": self.training_dtype,
            "optimizer": self.optimizer,
            "optimizer_steps": self.optimizer_steps,
            "loss_before": self.loss_before,
            "loss_after": self.loss_after,
            "gradient_finite": self.gradient_finite,
            "changed_entry_count": self.changed_entry_count,
            "heldout_task_ids_consumed": False,
            "heldout_prompts_consumed": False,
            "heldout_reference_answers_consumed": False,
        }

    @classmethod
    def from_json(cls, value: object) -> "TrainingReport":
        obj = strict_object(
            value,
            "phase10.training_report",
            {
                "schema_id",
                "request_hash",
                "predecessor_tensor_sha256",
                "candidate_tensor_sha256",
                "mode",
                "torch_version",
                "device",
                "training_dtype",
                "optimizer",
                "optimizer_steps",
                "loss_before",
                "loss_after",
                "gradient_finite",
                "changed_entry_count",
                "heldout_task_ids_consumed",
                "heldout_prompts_consumed",
                "heldout_reference_answers_consumed",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase10.training_report.schema_id")
        for name in (
            "heldout_task_ids_consumed",
            "heldout_prompts_consumed",
            "heldout_reference_answers_consumed",
        ):
            if obj[name] is not False:
                raise SchemaValidationError(f"phase10.training_report.{name}", "must be false")
        mode = require_string(obj["mode"], "phase10.training_report.mode")
        if mode not in {"bootstrap", "successor"}:
            raise SchemaValidationError("phase10.training_report.mode", "unsupported mode")
        gradient = obj["gradient_finite"]
        if not isinstance(gradient, bool):
            raise SchemaValidationError("phase10.training_report.gradient_finite", "expected Boolean")
        return cls(
            request_hash=require_hash(obj["request_hash"], "phase10.training_report.request_hash"),
            predecessor_tensor_sha256=require_hash(
                obj["predecessor_tensor_sha256"], "phase10.training_report.predecessor_tensor_sha256"
            ),
            candidate_tensor_sha256=require_hash(
                obj["candidate_tensor_sha256"], "phase10.training_report.candidate_tensor_sha256"
            ),
            mode=mode,  # type: ignore[arg-type]
            torch_version=require_string(obj["torch_version"], "phase10.training_report.torch_version"),
            device=require_string(obj["device"], "phase10.training_report.device"),
            training_dtype=require_string(obj["training_dtype"], "phase10.training_report.training_dtype"),
            optimizer=require_string(obj["optimizer"], "phase10.training_report.optimizer"),
            optimizer_steps=require_structural_integer(
                obj["optimizer_steps"], "phase10.training_report.optimizer_steps", minimum=1
            ),
            loss_before=require_string(obj["loss_before"], "phase10.training_report.loss_before"),
            loss_after=require_string(obj["loss_after"], "phase10.training_report.loss_after"),
            gradient_finite=gradient,
            changed_entry_count=require_structural_integer(
                obj["changed_entry_count"], "phase10.training_report.changed_entry_count", minimum=1
            ),
        )


def expected_trained_tensor(predecessor: bytes, request: TrainingRequest) -> bytes:
    expected_size = MODEL_WIDTH * MODEL_WIDTH * 2
    if len(predecessor) != expected_size:
        raise SchemaValidationError("phase10.training.tensor", "unexpected tensor byte length")
    if sha256_hex(predecessor) != request.predecessor_tensor_sha256:
        raise SchemaValidationError("phase10.training.tensor", "predecessor hash mismatch")
    result = bytearray(predecessor)
    for pair in request.pairs:
        index = pair.target_token_id * MODEL_WIDTH + pair.current_token_id
        struct.pack_into("<h", result, index * 2, request.target_raw_value)
    return bytes(result)


__all__ = [
    "TrainingPair",
    "TrainingReport",
    "TrainingRequest",
    "expected_trained_tensor",
]
