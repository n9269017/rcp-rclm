from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.successor.filesystem import atomic_write
from rcp_rclm_runtime.torch_backend.exact_evaluator import (
    ARCHITECTURE_PATH,
    BIAS_PATH,
    MODEL_ID,
    QUANTIZATION_SCALE,
    WEIGHT_PATH,
    WEIGHTS_MANIFEST_PATH,
    load_quantized_linear_model,
)

ARCHITECTURE_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_architecture.v1"
WEIGHT_MANIFEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_weight_manifest.v1"


def frozen_architecture_manifest() -> dict[str, object]:
    return {
        "schema_id": ARCHITECTURE_SCHEMA_ID,
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


def initialize_zero_predecessor_model(output_root: Path) -> dict[str, object]:
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"predecessor model output already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-pytorch-model-init-",
        dir=resolved.parent,
    ) as temporary_directory:
        staging = Path(temporary_directory) / "model-package"
        staging.mkdir(parents=True, exist_ok=False)
        architecture = frozen_architecture_manifest()
        architecture_bytes = canonical_json_bytes(architecture)
        architecture_hash = canonical_json_hash(architecture)
        weight_bytes = struct.pack("<4q", 0, 0, 0, 0)
        bias_bytes = struct.pack("<2q", 0, 0)
        tensor_records = [
            {
                "name": "linear.bias",
                "path": BIAS_PATH,
                "shape": [2],
                "dtype": "int64",
                "byte_order": "little",
                "element_count": 2,
                "size_bytes": len(bias_bytes),
                "sha256": sha256_hex(bias_bytes),
            },
            {
                "name": "linear.weight",
                "path": WEIGHT_PATH,
                "shape": [2, 2],
                "dtype": "int64",
                "byte_order": "little",
                "element_count": 4,
                "size_bytes": len(weight_bytes),
                "sha256": sha256_hex(weight_bytes),
            },
        ]
        tensor_records.sort(key=lambda item: str(item["name"]).encode("utf-8"))
        manifest_core = {
            "schema_id": WEIGHT_MANIFEST_SCHEMA_ID,
            "model_id": MODEL_ID,
            "source": "frozen_zero_predecessor",
            "architecture_hash": architecture_hash,
            "quantization_scale": QUANTIZATION_SCALE,
            "tensors": tensor_records,
        }
        manifest = dict(manifest_core)
        manifest["model_hash"] = canonical_json_hash(manifest_core)
        atomic_write(staging / ARCHITECTURE_PATH, architecture_bytes, "0644")
        atomic_write(staging / WEIGHT_PATH, weight_bytes, "0644")
        atomic_write(staging / BIAS_PATH, bias_bytes, "0644")
        atomic_write(
            staging / WEIGHTS_MANIFEST_PATH,
            canonical_json_bytes(manifest),
            "0644",
        )
        observed = load_quantized_linear_model(staging)
        if observed.model_hash != manifest["model_hash"]:
            raise ValueError("reopened zero model hash differs from constructed model")
        os.replace(staging, resolved)
    result = load_json_strict(
        (resolved / WEIGHTS_MANIFEST_PATH).read_bytes(),
        require_canonical=True,
    )
    if not isinstance(result, dict):
        raise ValueError("zero model manifest is not an object")
    return result


__all__ = [
    "frozen_architecture_manifest",
    "initialize_zero_predecessor_model",
]
