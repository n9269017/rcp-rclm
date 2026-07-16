from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import (
    canonical_json_hash,
    sha256_hex,
    validate_hash256,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    require_structural_integer,
    strict_object,
)

ARCHITECTURE_PATH: Final[str] = "model/architecture.json"
WEIGHTS_MANIFEST_PATH: Final[str] = "model/weights_manifest.json"
WEIGHT_PATH: Final[str] = "model/weights/linear.weight.bin"
BIAS_PATH: Final[str] = "model/weights/linear.bias.bin"
MODEL_ID: Final[str] = "tiny-linear-classifier-2x2-v1"
QUANTIZATION_SCALE: Final[int] = 1_000_000
EVALUATION_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_evaluation_result.v1"


@dataclass(frozen=True, slots=True)
class QuantizedLinearModel:
    weights: tuple[tuple[int, int], tuple[int, int]]
    bias: tuple[int, int]
    model_hash: str
    weight_manifest_hash: str
    architecture_hash: str


@dataclass(frozen=True, slots=True)
class ExactMetricRecord:
    example_count: int
    correct_count: int
    protected_example_count: int
    protected_correct_count: int
    predictions: Sequence[int]

    def __post_init__(self) -> None:
        predictions = tuple(self.predictions)
        object.__setattr__(self, "predictions", predictions)
        for name, value in (
            ("example_count", self.example_count),
            ("correct_count", self.correct_count),
            ("protected_example_count", self.protected_example_count),
            ("protected_correct_count", self.protected_correct_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchemaValidationError(
                    f"pytorch_pilot.metric.{name}",
                    "expected a nonnegative integer",
                )
        if self.example_count < 1 or len(predictions) != self.example_count:
            raise SchemaValidationError(
                "pytorch_pilot.metric.example_count",
                "example count must be positive and equal prediction count",
            )
        if self.correct_count > self.example_count:
            raise SchemaValidationError(
                "pytorch_pilot.metric.correct_count",
                "correct count exceeds example count",
            )
        if self.protected_example_count < 1 or self.protected_example_count > self.example_count:
            raise SchemaValidationError(
                "pytorch_pilot.metric.protected_example_count",
                "protected count must be between one and example count",
            )
        if self.protected_correct_count > self.protected_example_count:
            raise SchemaValidationError(
                "pytorch_pilot.metric.protected_correct_count",
                "protected correct count exceeds protected example count",
            )
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item not in {0, 1}
            for item in predictions
        ):
            raise SchemaValidationError(
                "pytorch_pilot.metric.predictions",
                "predictions must be binary integers",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "pytorch_pilot.metric",
    ) -> ExactMetricRecord:
        obj = strict_object(
            value,
            path,
            {
                "example_count",
                "correct_count",
                "protected_example_count",
                "protected_correct_count",
                "predictions",
            },
        )
        raw_predictions = obj["predictions"]
        if not isinstance(raw_predictions, list):
            raise SchemaValidationError(f"{path}.predictions", "expected an array")
        predictions = tuple(
            require_structural_integer(
                item,
                f"{path}.predictions[{index}]",
                minimum=0,
                maximum=1,
            )
            for index, item in enumerate(raw_predictions)
        )
        return cls(
            example_count=require_structural_integer(
                obj["example_count"], f"{path}.example_count", minimum=1
            ),
            correct_count=require_structural_integer(
                obj["correct_count"], f"{path}.correct_count", minimum=0
            ),
            protected_example_count=require_structural_integer(
                obj["protected_example_count"],
                f"{path}.protected_example_count",
                minimum=1,
            ),
            protected_correct_count=require_structural_integer(
                obj["protected_correct_count"],
                f"{path}.protected_correct_count",
                minimum=0,
            ),
            predictions=predictions,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "example_count": self.example_count,
            "correct_count": self.correct_count,
            "protected_example_count": self.protected_example_count,
            "protected_correct_count": self.protected_correct_count,
            "predictions": list(self.predictions),
        }


@dataclass(frozen=True, slots=True)
class ExactEvaluationRecord:
    predecessor_model_hash: str
    candidate_model_hash: str
    before: ExactMetricRecord
    after: ExactMetricRecord
    objective_improved: bool
    protected_nonregression: bool

    def __post_init__(self) -> None:
        validate_hash256(
            self.predecessor_model_hash,
            "pytorch_pilot.evaluation.predecessor_model_hash",
        )
        validate_hash256(
            self.candidate_model_hash,
            "pytorch_pilot.evaluation.candidate_model_hash",
        )
        if not isinstance(self.objective_improved, bool):
            raise SchemaValidationError(
                "pytorch_pilot.evaluation.objective_improved",
                "expected a Boolean",
            )
        if not isinstance(self.protected_nonregression, bool):
            raise SchemaValidationError(
                "pytorch_pilot.evaluation.protected_nonregression",
                "expected a Boolean",
            )
        computed_objective = self.after.correct_count > self.before.correct_count
        computed_protected = (
            self.after.protected_correct_count * self.before.protected_example_count
            >= self.before.protected_correct_count * self.after.protected_example_count
        )
        if self.objective_improved != computed_objective:
            raise SchemaValidationError(
                "pytorch_pilot.evaluation.objective_improved",
                "flag does not match exact count comparison",
            )
        if self.protected_nonregression != computed_protected:
            raise SchemaValidationError(
                "pytorch_pilot.evaluation.protected_nonregression",
                "flag does not match exact protected-rate comparison",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "pytorch_pilot.evaluation",
    ) -> ExactEvaluationRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "predecessor_model_hash",
                "candidate_model_hash",
                "before",
                "after",
                "objective",
                "objective_improved",
                "protected_metric",
                "protected_nonregression",
                "arithmetic",
                "torch_used_for_evaluation",
                "evaluation_conditions_met",
                "evaluation_hash",
            },
        )
        constants = {
            "schema_id": EVALUATION_SCHEMA_ID,
            "objective": "heldout_correct_count",
            "protected_metric": "class_0_recall",
            "arithmetic": "exact_integer_counts",
            "torch_used_for_evaluation": False,
        }
        for name, expected in constants.items():
            if obj[name] != expected:
                raise SchemaValidationError(
                    f"{path}.{name}",
                    f"expected {expected}",
                )
        for name in (
            "objective_improved",
            "protected_nonregression",
            "evaluation_conditions_met",
        ):
            if not isinstance(obj[name], bool):
                raise SchemaValidationError(f"{path}.{name}", "expected a Boolean")
        record = cls(
            predecessor_model_hash=validate_hash256(
                obj["predecessor_model_hash"],
                f"{path}.predecessor_model_hash",
            ),
            candidate_model_hash=validate_hash256(
                obj["candidate_model_hash"],
                f"{path}.candidate_model_hash",
            ),
            before=ExactMetricRecord.from_json(obj["before"], f"{path}.before"),
            after=ExactMetricRecord.from_json(obj["after"], f"{path}.after"),
            objective_improved=obj["objective_improved"],
            protected_nonregression=obj["protected_nonregression"],
        )
        if obj["evaluation_conditions_met"] != record.evaluation_conditions_met:
            raise SchemaValidationError(
                f"{path}.evaluation_conditions_met",
                "flag does not match recomputed conditions",
            )
        declared_hash = validate_hash256(
            obj["evaluation_hash"], f"{path}.evaluation_hash"
        )
        if declared_hash != record.evaluation_hash:
            raise SchemaValidationError(
                f"{path}.evaluation_hash",
                "evaluation hash mismatch",
            )
        return record

    @property
    def evaluation_conditions_met(self) -> bool:
        return (
            self.predecessor_model_hash != self.candidate_model_hash
            and self.objective_improved
            and self.protected_nonregression
        )

    @property
    def evaluation_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": EVALUATION_SCHEMA_ID,
            "predecessor_model_hash": self.predecessor_model_hash,
            "candidate_model_hash": self.candidate_model_hash,
            "before": self.before.to_json(),
            "after": self.after.to_json(),
            "objective": "heldout_correct_count",
            "objective_improved": self.objective_improved,
            "protected_metric": "class_0_recall",
            "protected_nonregression": self.protected_nonregression,
            "arithmetic": "exact_integer_counts",
            "torch_used_for_evaluation": False,
            "evaluation_conditions_met": self.evaluation_conditions_met,
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["evaluation_hash"] = self.evaluation_hash
        return value


def load_quantized_linear_model(payload_root: Path) -> QuantizedLinearModel:
    resolved = payload_root.resolve(strict=True)
    architecture_value = load_json_strict(
        (resolved / ARCHITECTURE_PATH).read_bytes(), require_canonical=True
    )
    if not isinstance(architecture_value, dict):
        raise SchemaValidationError("pytorch_pilot.architecture", "expected an object")
    required_architecture = {
        "schema_id": "runtime.pytorch_pilot_architecture.v1",
        "model_id": MODEL_ID,
        "module": "Linear",
        "input_features": 2,
        "output_classes": 2,
        "bias": True,
        "training_dtype": "float64",
        "package_weight_dtype": "int64",
        "quantization_scale": QUANTIZATION_SCALE,
        "activation": "identity",
        "prediction": "argmax_lowest_index_tiebreak",
    }
    if architecture_value != required_architecture:
        raise SchemaValidationError(
            "pytorch_pilot.architecture", "architecture differs from the frozen pilot"
        )
    architecture_hash = canonical_json_hash(architecture_value)

    manifest_value = load_json_strict(
        (resolved / WEIGHTS_MANIFEST_PATH).read_bytes(), require_canonical=True
    )
    if not isinstance(manifest_value, dict):
        raise SchemaValidationError("pytorch_pilot.weights_manifest", "expected an object")
    expected_manifest_keys = {
        "schema_id",
        "model_id",
        "source",
        "architecture_hash",
        "quantization_scale",
        "tensors",
        "model_hash",
    }
    if set(manifest_value) != expected_manifest_keys:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest", "unexpected manifest fields"
        )
    if manifest_value["schema_id"] != "runtime.pytorch_pilot_weight_manifest.v1":
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.schema_id", "unsupported schema"
        )
    if manifest_value["model_id"] != MODEL_ID:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.model_id", "unsupported model"
        )
    if manifest_value["architecture_hash"] != architecture_hash:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.architecture_hash",
            "architecture hash mismatch",
        )
    if manifest_value["quantization_scale"] != QUANTIZATION_SCALE:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.quantization_scale",
            "quantization scale mismatch",
        )

    weight_bytes = (resolved / WEIGHT_PATH).read_bytes()
    bias_bytes = (resolved / BIAS_PATH).read_bytes()
    if len(weight_bytes) != 32 or len(bias_bytes) != 16:
        raise SchemaValidationError(
            "pytorch_pilot.tensor_bytes", "unexpected frozen tensor byte length"
        )
    tensor_values = manifest_value["tensors"]
    if not isinstance(tensor_values, list) or len(tensor_values) != 2:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.tensors", "expected two tensors"
        )
    tensors_by_name: dict[str, dict[str, object]] = {}
    for index, item in enumerate(tensor_values):
        if not isinstance(item, dict):
            raise SchemaValidationError(
                f"pytorch_pilot.weights_manifest.tensors[{index}]", "expected object"
            )
        name = item.get("name")
        if not isinstance(name, str):
            raise SchemaValidationError(
                f"pytorch_pilot.weights_manifest.tensors[{index}].name",
                "expected string",
            )
        if name in tensors_by_name:
            raise SchemaValidationError(
                "pytorch_pilot.weights_manifest.tensors", "duplicate tensor name"
            )
        tensors_by_name[name] = item
    if set(tensors_by_name) != {"linear.bias", "linear.weight"}:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.tensors", "unexpected tensor names"
        )
    _verify_tensor_record(
        tensors_by_name["linear.weight"],
        name="linear.weight",
        path=WEIGHT_PATH,
        shape=[2, 2],
        element_count=4,
        content=weight_bytes,
    )
    _verify_tensor_record(
        tensors_by_name["linear.bias"],
        name="linear.bias",
        path=BIAS_PATH,
        shape=[2],
        element_count=2,
        content=bias_bytes,
    )

    model_hash = manifest_value["model_hash"]
    if not isinstance(model_hash, str):
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.model_hash", "expected string"
        )
    manifest_core = dict(manifest_value)
    del manifest_core["model_hash"]
    if canonical_json_hash(manifest_core) != model_hash:
        raise SchemaValidationError(
            "pytorch_pilot.weights_manifest.model_hash", "model hash mismatch"
        )
    weights_flat = struct.unpack("<4q", weight_bytes)
    bias_flat = struct.unpack("<2q", bias_bytes)
    return QuantizedLinearModel(
        weights=(
            (weights_flat[0], weights_flat[1]),
            (weights_flat[2], weights_flat[3]),
        ),
        bias=(bias_flat[0], bias_flat[1]),
        model_hash=model_hash,
        weight_manifest_hash=canonical_json_hash(manifest_value),
        architecture_hash=architecture_hash,
    )


def evaluate_quantized_transition(
    predecessor_payload_root: Path,
    candidate_payload_root: Path,
    evaluation_data: object,
) -> ExactEvaluationRecord:
    predecessor = load_quantized_linear_model(predecessor_payload_root)
    candidate = load_quantized_linear_model(candidate_payload_root)
    features, labels, protected_class = _parse_evaluation_data(evaluation_data)
    before = _evaluate_model(predecessor, features, labels, protected_class)
    after = _evaluate_model(candidate, features, labels, protected_class)
    objective_improved = after.correct_count > before.correct_count
    protected_nonregression = (
        after.protected_correct_count * before.protected_example_count
        >= before.protected_correct_count * after.protected_example_count
    )
    return ExactEvaluationRecord(
        predecessor_model_hash=predecessor.model_hash,
        candidate_model_hash=candidate.model_hash,
        before=before,
        after=after,
        objective_improved=objective_improved,
        protected_nonregression=protected_nonregression,
    )


def _verify_tensor_record(
    value: dict[str, object],
    *,
    name: str,
    path: str,
    shape: list[int],
    element_count: int,
    content: bytes,
) -> None:
    expected = {
        "name": name,
        "path": path,
        "shape": shape,
        "dtype": "int64",
        "byte_order": "little",
        "element_count": element_count,
        "size_bytes": len(content),
        "sha256": sha256_hex(content),
    }
    if value != expected:
        raise SchemaValidationError(
            f"pytorch_pilot.weights_manifest.{name}", "tensor record mismatch"
        )


def _parse_evaluation_data(
    value: object,
) -> tuple[Sequence[tuple[int, int]], Sequence[int], int]:
    if not isinstance(value, dict):
        raise SchemaValidationError("pytorch_pilot.evaluation_data", "expected object")
    if set(value) != {"schema_id", "features", "labels", "protected_class"}:
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data", "unexpected evaluation fields"
        )
    if value["schema_id"] != "runtime.pytorch_pilot_heldout_data.v1":
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data.schema_id", "unsupported schema"
        )
    raw_features = value["features"]
    raw_labels = value["labels"]
    protected_class = value["protected_class"]
    if not isinstance(raw_features, list) or not isinstance(raw_labels, list):
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data", "features and labels must be arrays"
        )
    if isinstance(protected_class, bool) or not isinstance(protected_class, int):
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data.protected_class", "expected integer"
        )
    if protected_class not in {0, 1}:
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data.protected_class", "expected binary class"
        )
    features: list[tuple[int, int]] = []
    for index, row in enumerate(raw_features):
        if not isinstance(row, list) or len(row) != 2:
            raise SchemaValidationError(
                f"pytorch_pilot.evaluation_data.features[{index}]",
                "expected two-element array",
            )
        parsed_row: list[int] = []
        for column, item in enumerate(row):
            if isinstance(item, bool) or not isinstance(item, int):
                raise SchemaValidationError(
                    f"pytorch_pilot.evaluation_data.features[{index}][{column}]",
                    "expected integer",
                )
            parsed_row.append(item)
        features.append((parsed_row[0], parsed_row[1]))
    labels: list[int] = []
    for index, item in enumerate(raw_labels):
        if isinstance(item, bool) or not isinstance(item, int) or item not in {0, 1}:
            raise SchemaValidationError(
                f"pytorch_pilot.evaluation_data.labels[{index}]",
                "expected binary integer",
            )
        labels.append(item)
    if not features or len(features) != len(labels):
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data", "features and labels must have equal nonzero length"
        )
    return tuple(features), tuple(labels), protected_class


def _evaluate_model(
    model: QuantizedLinearModel,
    features: Sequence[tuple[int, int]],
    labels: Sequence[int],
    protected_class: int,
) -> ExactMetricRecord:
    predictions: list[int] = []
    correct = 0
    protected_examples = 0
    protected_correct = 0
    for feature, label in zip(features, labels, strict=True):
        logit0 = (
            model.weights[0][0] * feature[0]
            + model.weights[0][1] * feature[1]
            + model.bias[0]
        )
        logit1 = (
            model.weights[1][0] * feature[0]
            + model.weights[1][1] * feature[1]
            + model.bias[1]
        )
        prediction = 0 if logit0 >= logit1 else 1
        predictions.append(prediction)
        if prediction == label:
            correct += 1
        if label == protected_class:
            protected_examples += 1
            if prediction == label:
                protected_correct += 1
    if protected_examples == 0:
        raise SchemaValidationError(
            "pytorch_pilot.evaluation_data", "protected class has no examples"
        )
    return ExactMetricRecord(
        example_count=len(labels),
        correct_count=correct,
        protected_example_count=protected_examples,
        protected_correct_count=protected_correct,
        predictions=tuple(predictions),
    )


__all__ = [
    "ExactEvaluationRecord",
    "ExactMetricRecord",
    "QuantizedLinearModel",
    "evaluate_quantized_transition",
    "load_quantized_linear_model",
]
