from __future__ import annotations

import hashlib
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime_v3.phase10.constants import (
    EOS_TOKEN_ID,
    MODEL_WIDTH,
    VOCAB_SIZE,
)
from rcp_rclm_runtime_v3.phase10.learned_data import (
    MAX_COMPLETION_TOKENS,
    TRANSITION_RAW_VALUE,
    TRANSITION_SCORE_DIVISOR,
)
from rcp_rclm_runtime_v3.phase10.package import load_package_components
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord, file_is_all_zero

EMBEDDING_TENSOR: Final[str] = "model.token_embedding.weight"
FINAL_NORM_TENSOR: Final[str] = "model.final_norm.weight"
ATTN_QKV_TENSOR: Final[str] = "model.layers.00.attn_qkv.weight"
ATTN_OUTPUT_TENSOR: Final[str] = "model.layers.00.attn_output.weight"
IDENTITY_RAW_VALUE: Final[int] = 4_096
DYADIC_LOGIT_CLIP: Final[int] = 15


def _layer_norm_names() -> Sequence[str]:
    values: list[str] = [FINAL_NORM_TENSOR]
    for layer_index in range(8):
        prefix = f"model.layers.{layer_index:02d}"
        values.append(f"{prefix}.attn_norm.weight")
        values.append(f"{prefix}.mlp_norm.weight")
    return tuple(values)


NORM_TENSORS: Final[Sequence[str]] = _layer_norm_names()


def _record_map(manifest: TensorManifest) -> dict[str, TensorRecord]:
    return {record.spec.name: record for record in manifest.records}


def _offset(shape: Sequence[int], indices: Sequence[int]) -> int:
    if len(shape) != len(indices):
        raise ValueError("index rank mismatch")
    flat = 0
    for dimension, index in zip(shape, indices, strict=True):
        if not 0 <= index < dimension:
            raise ValueError("tensor index out of range")
        flat = flat * dimension + index
    return flat


def _expected_entries(
    transition_pairs: Sequence[tuple[int, int]],
) -> dict[str, dict[int, int]]:
    entries: dict[str, dict[int, int]] = {}
    embedding: dict[int, int] = {}
    for token_id in range(VOCAB_SIZE):
        embedding[_offset((VOCAB_SIZE, MODEL_WIDTH), (token_id, token_id))] = IDENTITY_RAW_VALUE
    entries[EMBEDDING_TENSOR] = embedding

    for name in NORM_TENSORS:
        entries[name] = {index: IDENTITY_RAW_VALUE for index in range(MODEL_WIDTH)}

    qkv: dict[int, int] = {}
    qkv_shape = (3 * MODEL_WIDTH, MODEL_WIDTH)
    value_row_offset = 2 * MODEL_WIDTH
    for index in range(MODEL_WIDTH):
        qkv[_offset(qkv_shape, (value_row_offset + index, index))] = IDENTITY_RAW_VALUE
    entries[ATTN_QKV_TENSOR] = qkv

    transition: dict[int, int] = {}
    transition_shape = (MODEL_WIDTH, MODEL_WIDTH)
    seen_currents: set[int] = set()
    for current, target in transition_pairs:
        if current in seen_currents:
            raise SchemaValidationError(
                "phase10.sparse_profile.transition_pairs",
                f"multiple targets declared for current token {current}",
            )
        if not 0 <= current < VOCAB_SIZE or not 0 <= target < VOCAB_SIZE:
            raise SchemaValidationError(
                "phase10.sparse_profile.transition_pairs", "token id outside vocabulary"
            )
        seen_currents.add(current)
        transition[_offset(transition_shape, (target, current))] = TRANSITION_RAW_VALUE
    entries[ATTN_OUTPUT_TENSOR] = transition
    return entries


def _expected_tensor_bytes(element_count: int, entries: Mapping[int, int]) -> bytes:
    payload = bytearray(element_count * 2)
    for index, value in entries.items():
        if not -32768 <= value <= 32767:
            raise ValueError("int16 value out of range")
        struct.pack_into("<h", payload, index * 2, value)
    return bytes(payload)


def apply_sparse_profile(
    package_root: Path,
    transition_pairs: Sequence[tuple[int, int]],
) -> None:
    root = package_root.resolve(strict=True)
    _, _, _, manifest, _ = load_package_components(root)
    records = _record_map(manifest)
    expected = _expected_entries(transition_pairs)
    for name, entries in expected.items():
        record = records.get(name)
        if record is None:
            raise SchemaValidationError("phase10.sparse_profile", f"missing tensor {name}")
        payload = _expected_tensor_bytes(record.spec.element_count, entries)
        path = root / record.spec.path
        path.write_bytes(payload)


def validate_sparse_profile(
    package_root: Path,
    transition_pairs: Sequence[tuple[int, int]],
) -> dict[str, object]:
    root = package_root.resolve(strict=True)
    manifest, architecture, _, tensors, adapter = load_package_components(root)
    records = _record_map(tensors)
    expected = _expected_entries(transition_pairs)
    failures: list[str] = []
    tensor_hashes: dict[str, str] = {}

    if adapter.status != "absent":
        failures.append("adapter_not_absent")
    if architecture.model_width != MODEL_WIDTH or architecture.vocabulary_size != VOCAB_SIZE:
        failures.append("architecture_mismatch")

    for name, record in records.items():
        path = root / record.spec.path
        if name in expected:
            expected_bytes = _expected_tensor_bytes(record.spec.element_count, expected[name])
            observed_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            expected_hash = hashlib.sha256(expected_bytes).hexdigest()
            tensor_hashes[name] = observed_hash
            if observed_hash != expected_hash:
                failures.append(f"tensor_profile_mismatch:{name}")
        elif not file_is_all_zero(path):
            failures.append(f"unexpected_nonzero_tensor:{name}")

    for name in expected:
        if name not in records:
            failures.append(f"missing_tensor:{name}")

    content = {
        "schema_id": "runtime.v3.phase10.sparse_profile_report.v1",
        "package_hash": manifest.package_hash,
        "model_identity_hash": manifest.model_identity_hash,
        "transition_pairs": [
            {"current_token_id": current, "target_token_id": target}
            for current, target in transition_pairs
        ],
        "tensor_hashes": {
            key: tensor_hashes[key] for key in sorted(tensor_hashes, key=lambda item: item.encode("utf-8"))
        },
        "failures": sorted(failures),
        "accepted": not failures,
        "selected_inference_profile": "sparse_last_token_transition_v1",
        "full_native_float_transformer_equivalence_claimed": False,
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
    return result


def transition_tensor_path(package_root: Path) -> Path:
    root = package_root.resolve(strict=True)
    _, _, _, tensors, _ = load_package_components(root)
    record = _record_map(tensors).get(ATTN_OUTPUT_TENSOR)
    if record is None:
        raise SchemaValidationError("phase10.sparse_profile", "transition tensor is absent")
    return root / record.spec.path


def transition_tensor_sha256(package_root: Path) -> str:
    return sha256_hex(transition_tensor_path(package_root).read_bytes())


def raw_transition_scores(package_root: Path, current_token_id: int) -> Sequence[int]:
    if not 0 <= current_token_id < VOCAB_SIZE:
        raise SchemaValidationError("phase10.inference.current_token_id", "outside vocabulary")
    payload = transition_tensor_path(package_root).read_bytes()
    shape = (MODEL_WIDTH, MODEL_WIDTH)
    result: list[int] = []
    for target_token_id in range(VOCAB_SIZE):
        index = _offset(shape, (target_token_id, current_token_id))
        raw = struct.unpack_from("<h", payload, index * 2)[0]
        if raw % TRANSITION_SCORE_DIVISOR != 0:
            raise SchemaValidationError(
                "phase10.inference.transition_score",
                "raw transition value is not divisible by the frozen score divisor",
            )
        result.append(raw // TRANSITION_SCORE_DIVISOR)
    return tuple(result)


def exact_dyadic_distribution(
    package_root: Path,
    current_token_id: int,
) -> tuple[Sequence[int], Sequence[Rational]]:
    scores = raw_transition_scores(package_root, current_token_id)
    clipped = tuple(max(-DYADIC_LOGIT_CLIP, min(DYADIC_LOGIT_CLIP, score)) for score in scores)
    minimum = min(clipped)
    masses = tuple(1 << (score - minimum) for score in clipped)
    total = sum(masses)
    distribution = tuple(Rational(mass, total) for mass in masses)
    normalized = Rational.zero()
    for probability in distribution:
        normalized = normalized + probability
    if normalized != Rational.one():
        raise AssertionError("distribution normalization failed")
    return scores, distribution


@dataclass(frozen=True, slots=True)
class DecodeStep:
    position: int
    current_token_id: int
    selected_token_id: int
    selected_score: int
    runner_up_score: int
    distribution_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase10.decode_step.v1"

    @property
    def margin(self) -> int:
        return self.selected_score - self.runner_up_score

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "position": self.position,
            "current_token_id": self.current_token_id,
            "selected_token_id": self.selected_token_id,
            "selected_score": self.selected_score,
            "runner_up_score": self.runner_up_score,
            "margin": self.margin,
            "distribution_hash": self.distribution_hash,
        }


@dataclass(frozen=True, slots=True)
class DecodeResult:
    model_identity_hash: str
    model_prompt_hash: str
    completion_token_ids: Sequence[int]
    stopped_on_eos: bool
    steps: Sequence[DecodeStep]

    schema_id: ClassVar[str] = "runtime.v3.phase10.decode_result.v1"

    @property
    def completion_bytes(self) -> bytes:
        if any(not 0 <= token < 256 for token in self.completion_token_ids):
            raise SchemaValidationError("phase10.decode.completion", "non-byte token in completion")
        return bytes(self.completion_token_ids)

    @property
    def completion_text(self) -> str:
        return self.completion_bytes.decode("ascii", errors="strict")

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "model_identity_hash": self.model_identity_hash,
            "model_prompt_hash": self.model_prompt_hash,
            "completion_token_ids": list(self.completion_token_ids),
            "completion_sha256": sha256_hex(self.completion_bytes),
            "stopped_on_eos": self.stopped_on_eos,
            "steps": [step.to_json() for step in self.steps],
        }


def decode_completion(
    package_root: Path,
    model_prompt: bytes,
    *,
    maximum_tokens: int = MAX_COMPLETION_TOKENS,
) -> DecodeResult:
    if not model_prompt:
        raise SchemaValidationError("phase10.inference.model_prompt", "must be nonempty")
    if maximum_tokens < 1 or maximum_tokens > MAX_COMPLETION_TOKENS:
        raise SchemaValidationError("phase10.inference.maximum_tokens", "outside frozen bound")
    manifest, _, _, _, _ = load_package_components(package_root.resolve(strict=True))
    current = model_prompt[-1]
    output: list[int] = []
    steps: list[DecodeStep] = []
    stopped = False
    for position in range(maximum_tokens):
        scores, distribution = exact_dyadic_distribution(package_root, current)
        selected = min(range(VOCAB_SIZE), key=lambda token: (-scores[token], token))
        ordered_scores = sorted(scores, reverse=True)
        runner_up = ordered_scores[1] if len(ordered_scores) > 1 else ordered_scores[0]
        distribution_json = [value.to_json() for value in distribution]
        steps.append(
            DecodeStep(
                position=position,
                current_token_id=current,
                selected_token_id=selected,
                selected_score=scores[selected],
                runner_up_score=runner_up,
                distribution_hash=canonical_json_hash(distribution_json),
            )
        )
        if selected == EOS_TOKEN_ID:
            stopped = True
            break
        if selected >= 256:
            break
        output.append(selected)
        current = selected
    return DecodeResult(
        model_identity_hash=manifest.model_identity_hash,
        model_prompt_hash=sha256_hex(model_prompt),
        completion_token_ids=tuple(output),
        stopped_on_eos=stopped,
        steps=tuple(steps),
    )


__all__ = [
    "ATTN_OUTPUT_TENSOR",
    "ATTN_QKV_TENSOR",
    "DecodeResult",
    "DecodeStep",
    "EMBEDDING_TENSOR",
    "NORM_TENSORS",
    "apply_sparse_profile",
    "decode_completion",
    "exact_dyadic_distribution",
    "raw_transition_scores",
    "transition_tensor_path",
    "transition_tensor_sha256",
    "validate_sparse_profile",
]
