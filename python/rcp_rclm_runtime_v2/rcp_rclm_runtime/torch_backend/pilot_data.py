from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

TRAIN_FEATURES: Final[Sequence[tuple[int, int]]] = (
    (-2, -1),
    (-1, -2),
    (1, 2),
    (2, 1),
)
TRAIN_LABELS: Final[Sequence[int]] = (0, 0, 1, 1)
HELDOUT_FEATURES: Final[Sequence[tuple[int, int]]] = (
    (-3, -1),
    (-1, -3),
    (1, 3),
    (3, 1),
)
HELDOUT_LABELS: Final[Sequence[int]] = (0, 0, 1, 1)


def pilot_training_data_manifest() -> dict[str, object]:
    train_payload = {
        "features": [list(row) for row in TRAIN_FEATURES],
        "labels": list(TRAIN_LABELS),
    }
    heldout_features_payload = {
        "features": [list(row) for row in HELDOUT_FEATURES],
    }
    return {
        "schema_id": "runtime.pytorch_pilot_training_data.v1",
        "dataset_id": "rcp-rclm-pytorch-pilot-separable-2d-v1",
        "feature_dtype": "int64",
        "label_dtype": "int64",
        "feature_dimension": 2,
        "class_count": 2,
        "train_example_count": len(TRAIN_FEATURES),
        "heldout_example_count": len(HELDOUT_FEATURES),
        "train_manifest_hash": canonical_json_hash(train_payload),
        "heldout_feature_manifest_hash": canonical_json_hash(
            heldout_features_payload
        ),
        "heldout_labels_disclosed_to_backend": False,
    }


def pilot_heldout_evaluation_data() -> dict[str, object]:
    return {
        "schema_id": "runtime.pytorch_pilot_heldout_data.v1",
        "features": [list(row) for row in HELDOUT_FEATURES],
        "labels": list(HELDOUT_LABELS),
        "protected_class": 0,
    }


def pilot_heldout_evaluation_data_hash() -> str:
    return canonical_json_hash(pilot_heldout_evaluation_data())


__all__ = [
    "HELDOUT_FEATURES",
    "HELDOUT_LABELS",
    "TRAIN_FEATURES",
    "TRAIN_LABELS",
    "pilot_heldout_evaluation_data",
    "pilot_heldout_evaluation_data_hash",
    "pilot_training_data_manifest",
]
