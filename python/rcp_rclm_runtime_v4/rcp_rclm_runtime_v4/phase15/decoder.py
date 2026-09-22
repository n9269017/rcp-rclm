from __future__ import annotations

import hashlib
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase15.constants import (
    NAME_BY_TOKEN,
    PHASE15_DECODER_FEATURE_DIMENSION,
    PHASE15_DECODER_PARAMETER_COUNT,
    PHASE15_DECODER_VOCAB_SIZE,
    PHASE15_MAX_ABS_PARAMETER,
    PHASE15_MAX_PLAN_TOKENS,
    TOKEN_BY_NAME,
    CandidateVariant,
    TaskDomain,
    cast_candidate_variant,
    cast_task_domain,
)
from rcp_rclm_runtime_v4.phase15.curriculum import CurriculumExample


_DECODER_DIRECTORY = "model/phase15_planner"
DECODER_WEIGHTS_PATH = f"{_DECODER_DIRECTORY}/weights.i16le.bin"
DECODER_MANIFEST_PATH = f"{_DECODER_DIRECTORY}/manifest.json"
DECODER_VOCABULARY_PATH = f"{_DECODER_DIRECTORY}/vocabulary.json"
DECODER_TRAINING_REPORT_PATH = f"{_DECODER_DIRECTORY}/training_report.json"
DECODER_CURRICULUM_PATH = f"{_DECODER_DIRECTORY}/public_curriculum.json"


def vocabulary_json() -> dict[str, object]:
    return {
        "schema_id": "runtime.v4.phase15.plan_vocabulary.v1",
        "vocabulary_size": PHASE15_DECODER_VOCAB_SIZE,
        "tokens": [
            {"token_id": index, "name": NAME_BY_TOKEN[index]}
            for index in range(PHASE15_DECODER_VOCAB_SIZE)
        ],
    }


def _value_index(value: int) -> int:
    if value < -PHASE15_MAX_ABS_PARAMETER or value > PHASE15_MAX_ABS_PARAMETER:
        raise SchemaValidationError("phase15.decoder.parameter", "parameter outside selected range")
    return value + PHASE15_MAX_ABS_PARAMETER


def active_feature_indices(
    domain: TaskDomain,
    position: int,
    previous_token: int,
    parameter_a: int,
    parameter_b: int,
) -> tuple[int, ...]:
    cast_task_domain(domain)
    if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position < PHASE15_MAX_PLAN_TOKENS:
        raise SchemaValidationError("phase15.decoder.position", "invalid plan position")
    if isinstance(previous_token, bool) or not isinstance(previous_token, int) or not 0 <= previous_token < PHASE15_DECODER_VOCAB_SIZE:
        raise SchemaValidationError("phase15.decoder.previous_token", "invalid token")
    task_index = 0 if domain == "integer_program" else 1
    task_position_base = 1
    previous_base = task_position_base + 2 * PHASE15_MAX_PLAN_TOKENS
    parameter_value_base = previous_base + PHASE15_DECODER_VOCAB_SIZE
    b_position = 2 if domain == "lean_multistep" else 3
    # Parameter emissions use one shared value-copy feature across domains
    # and both argument positions. Context features are intentionally absent
    # at copy positions, so the public even-pair curriculum learns an
    # integer-token identity map that composes on every unseen odd pair
    # rather than memorizing observed parameter combinations.
    if position == 1 or position == b_position:
        parameter_value = parameter_a if position == 1 else parameter_b
        values_list = [
            parameter_value_base + _value_index(parameter_value)
        ]
    else:
        values_list = [
            0,
            task_position_base
            + task_index * PHASE15_MAX_PLAN_TOKENS
            + position,
            previous_base + previous_token,
        ]
    values = tuple(values_list)
    if max(values) >= PHASE15_DECODER_FEATURE_DIMENSION:
        raise SchemaValidationError("phase15.decoder.features", "feature index overflow")
    return values


def _score_row(row: Sequence[int], active: Sequence[int]) -> int:
    return sum(row[index] for index in active)


def predict_token(weights: Sequence[Sequence[int]], active: Sequence[int]) -> int:
    if len(weights) != PHASE15_DECODER_VOCAB_SIZE:
        raise SchemaValidationError("phase15.decoder.weights", "vocabulary row count mismatch")
    scores = tuple(_score_row(row, active) for row in weights)
    maximum = max(scores)
    return next(index for index, value in enumerate(scores) if value == maximum)


def train_perceptron(
    examples: Sequence[CurriculumExample],
    *,
    epochs: int,
) -> tuple[tuple[int, ...], ...]:
    if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 1:
        raise SchemaValidationError("phase15.training.epochs", "expected positive integer")
    matrix = [
        [0 for _ in range(PHASE15_DECODER_FEATURE_DIMENSION)]
        for _ in range(PHASE15_DECODER_VOCAB_SIZE)
    ]
    ordered = tuple(sorted(examples, key=lambda item: item.example_id.encode("utf-8")))
    for _ in range(epochs):
        for example in ordered:
            previous = TOKEN_BY_NAME["BOS"]
            for position, target in enumerate(example.plan_tokens):
                active = active_feature_indices(
                    example.domain,
                    position,
                    previous,
                    example.parameter_a,
                    example.parameter_b,
                )
                predicted = predict_token(matrix, active)
                if predicted != target:
                    for feature in active:
                        matrix[target][feature] += 1
                        matrix[predicted][feature] -= 1
                previous = target
    maximum = max(abs(value) for row in matrix for value in row)
    if maximum > 32_767:
        raise SchemaValidationError("phase15.training.weights", "int16 range exceeded")
    return tuple(tuple(row) for row in matrix)


def weights_bytes(weights: Sequence[Sequence[int]]) -> bytes:
    if len(weights) != PHASE15_DECODER_VOCAB_SIZE:
        raise SchemaValidationError("phase15.decoder.weights", "row count mismatch")
    payload = bytearray()
    for row in weights:
        if len(row) != PHASE15_DECODER_FEATURE_DIMENSION:
            raise SchemaValidationError("phase15.decoder.weights", "feature dimension mismatch")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int) or not -32_768 <= value <= 32_767:
                raise SchemaValidationError("phase15.decoder.weights", "invalid int16 value")
            payload.extend(struct.pack("<h", value))
    return bytes(payload)


def weights_from_bytes(payload: bytes) -> tuple[tuple[int, ...], ...]:
    expected = PHASE15_DECODER_PARAMETER_COUNT * 2
    if len(payload) != expected:
        raise SchemaValidationError("phase15.decoder.weights", "byte length mismatch")
    values = struct.unpack(f"<{PHASE15_DECODER_PARAMETER_COUNT}h", payload)
    return tuple(
        tuple(
            values[
                row * PHASE15_DECODER_FEATURE_DIMENSION :
                (row + 1) * PHASE15_DECODER_FEATURE_DIMENSION
            ]
        )
        for row in range(PHASE15_DECODER_VOCAB_SIZE)
    )


@dataclass(frozen=True, slots=True)
class DecoderManifest:
    variant: CandidateVariant
    supported_domains: Sequence[TaskDomain]
    curriculum_manifest_hash: str
    training_report_hash: str
    weights_sha256: str
    vocabulary_hash: str
    active_semantic_package_hash: str
    active_model_identity_hash: str
    parameter_count: int = PHASE15_DECODER_PARAMETER_COUNT
    feature_dimension: int = PHASE15_DECODER_FEATURE_DIMENSION
    vocabulary_size: int = PHASE15_DECODER_VOCAB_SIZE
    dtype: str = "int16"
    byte_order: str = "little"
    decoding: str = "greedy_autoregressive_lowest_token_tie_break"

    schema_id: ClassVar[str] = "runtime.v4.phase15.decoder_manifest.v1"

    def __post_init__(self) -> None:
        cast_candidate_variant(self.variant, "phase15.decoder.variant")
        domains = tuple(sorted((cast_task_domain(item) for item in self.supported_domains), key=lambda item: item.encode("utf-8")))
        if not domains or len(set(domains)) != len(domains):
            raise SchemaValidationError("phase15.decoder.supported_domains", "invalid domains")
        object.__setattr__(self, "supported_domains", domains)
        for name in (
            "curriculum_manifest_hash",
            "training_report_hash",
            "weights_sha256",
            "vocabulary_hash",
            "active_semantic_package_hash",
            "active_model_identity_hash",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise SchemaValidationError(f"phase15.decoder.{name}", "expected lowercase SHA-256")
        if self.parameter_count != PHASE15_DECODER_PARAMETER_COUNT:
            raise SchemaValidationError("phase15.decoder.parameter_count", "unexpected parameter count")
        if self.feature_dimension != PHASE15_DECODER_FEATURE_DIMENSION:
            raise SchemaValidationError("phase15.decoder.feature_dimension", "unexpected feature dimension")
        if self.vocabulary_size != PHASE15_DECODER_VOCAB_SIZE:
            raise SchemaValidationError("phase15.decoder.vocabulary_size", "unexpected vocabulary size")

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "variant": self.variant,
            "supported_domains": list(self.supported_domains),
            "curriculum_manifest_hash": self.curriculum_manifest_hash,
            "training_report_hash": self.training_report_hash,
            "weights_sha256": self.weights_sha256,
            "vocabulary_hash": self.vocabulary_hash,
            "active_semantic_package_hash": self.active_semantic_package_hash,
            "active_model_identity_hash": self.active_model_identity_hash,
            "parameter_count": self.parameter_count,
            "feature_dimension": self.feature_dimension,
            "vocabulary_size": self.vocabulary_size,
            "dtype": self.dtype,
            "byte_order": self.byte_order,
            "decoding": self.decoding,
            "candidate_self_report_authoritative": False,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["manifest_hash"] = self.manifest_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> "DecoderManifest":
        if not isinstance(value, dict):
            raise SchemaValidationError("phase15.decoder_manifest", "expected object")
        domains = value.get("supported_domains")
        if not isinstance(domains, list):
            raise SchemaValidationError("phase15.decoder_manifest.supported_domains", "expected array")
        result = cls(
            variant=cast_candidate_variant(str(value.get("variant"))),
            supported_domains=tuple(cast_task_domain(str(item)) for item in domains),
            curriculum_manifest_hash=str(value.get("curriculum_manifest_hash")),
            training_report_hash=str(value.get("training_report_hash")),
            weights_sha256=str(value.get("weights_sha256")),
            vocabulary_hash=str(value.get("vocabulary_hash")),
            active_semantic_package_hash=str(value.get("active_semantic_package_hash")),
            active_model_identity_hash=str(value.get("active_model_identity_hash")),
            parameter_count=int(value.get("parameter_count", -1)),
            feature_dimension=int(value.get("feature_dimension", -1)),
            vocabulary_size=int(value.get("vocabulary_size", -1)),
            dtype=str(value.get("dtype")),
            byte_order=str(value.get("byte_order")),
            decoding=str(value.get("decoding")),
        )
        if value.get("manifest_hash") != result.manifest_hash:
            raise SchemaValidationError("phase15.decoder_manifest.manifest_hash", "content hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class DecodeReport:
    domain: TaskDomain
    parameter_a: int
    parameter_b: int
    tokens: Sequence[int]
    stopped_on_eos: bool
    decoder_manifest_hash: str

    schema_id: ClassVar[str] = "runtime.v4.phase15.decode_report.v1"

    def __post_init__(self) -> None:
        cast_task_domain(self.domain)
        tokens = tuple(self.tokens)
        if not tokens or len(tokens) > PHASE15_MAX_PLAN_TOKENS:
            raise SchemaValidationError("phase15.decode.tokens", "invalid token count")
        object.__setattr__(self, "tokens", tokens)

    @property
    def plan_text(self) -> str:
        return " ".join(NAME_BY_TOKEN[token] for token in self.tokens)

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "domain": self.domain,
            "parameter_a": self.parameter_a,
            "parameter_b": self.parameter_b,
            "tokens": list(self.tokens),
            "token_names": [NAME_BY_TOKEN[token] for token in self.tokens],
            "stopped_on_eos": self.stopped_on_eos,
            "decoder_manifest_hash": self.decoder_manifest_hash,
        }


def decode_plan(
    package_root: Path,
    domain: TaskDomain,
    parameter_a: int,
    parameter_b: int,
) -> DecodeReport:
    root = package_root.resolve(strict=True)
    manifest_value = load_json_strict((root / DECODER_MANIFEST_PATH).read_bytes(), require_canonical=True)
    manifest = DecoderManifest.from_json(manifest_value)
    cast_task_domain(domain)
    if domain not in manifest.supported_domains:
        return DecodeReport(
            domain=domain,
            parameter_a=parameter_a,
            parameter_b=parameter_b,
            tokens=(TOKEN_BY_NAME["ERROR"],),
            stopped_on_eos=False,
            decoder_manifest_hash=manifest.manifest_hash,
        )
    payload = (root / DECODER_WEIGHTS_PATH).read_bytes()
    if sha256_hex(payload) != manifest.weights_sha256:
        raise SchemaValidationError("phase15.decoder.weights", "weights hash mismatch")
    weights = weights_from_bytes(payload)
    previous = TOKEN_BY_NAME["BOS"]
    tokens: list[int] = []
    for position in range(PHASE15_MAX_PLAN_TOKENS):
        active = active_feature_indices(domain, position, previous, parameter_a, parameter_b)
        token = predict_token(weights, active)
        tokens.append(token)
        previous = token
        if token == TOKEN_BY_NAME["EOS"]:
            break
    return DecodeReport(
        domain=domain,
        parameter_a=parameter_a,
        parameter_b=parameter_b,
        tokens=tuple(tokens),
        stopped_on_eos=bool(tokens and tokens[-1] == TOKEN_BY_NAME["EOS"]),
        decoder_manifest_hash=manifest.manifest_hash,
    )


def directory_decoder_hash(root: Path) -> str:
    resolved = root.resolve(strict=True)
    digest = hashlib.sha256()
    for relative in (
        DECODER_CURRICULUM_PATH,
        DECODER_MANIFEST_PATH,
        DECODER_TRAINING_REPORT_PATH,
        DECODER_VOCABULARY_PATH,
        DECODER_WEIGHTS_PATH,
    ):
        path = resolved / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


__all__ = [
    "DECODER_CURRICULUM_PATH",
    "DECODER_MANIFEST_PATH",
    "DECODER_TRAINING_REPORT_PATH",
    "DECODER_VOCABULARY_PATH",
    "DECODER_WEIGHTS_PATH",
    "DecodeReport",
    "DecoderManifest",
    "active_feature_indices",
    "decode_plan",
    "directory_decoder_hash",
    "predict_token",
    "train_perceptron",
    "vocabulary_json",
    "weights_bytes",
    "weights_from_bytes",
]
