from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.successor.record_predecessor import Phase6PredecessorManifestRecord
from rcp_rclm_runtime.successor.reference import build_reference_predecessor_package
from rcp_rclm_runtime.successor.workspace import (
    LoadedPredecessorPackage,
    load_predecessor_package,
    measure_payload_tree,
    write_canonical_json,
)
from rcp_rclm_runtime.torch_backend.pilot_data import pilot_training_data_manifest
from rcp_rclm_runtime.torch_backend.model_package import initialize_zero_predecessor_model
from rcp_rclm_runtime.torch_backend.protocol import (
    PilotPolicyBinding,
    PilotRequestBinding,
)

PILOT_PREDECESSOR_ID: Final[str] = "pytorch.pilot.target.predecessor"


def build_pytorch_pilot_predecessor(output_root: Path) -> LoadedPredecessorPackage:
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"pilot predecessor already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-pytorch-predecessor-",
        dir=resolved_output.parent,
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        package_root = build_reference_predecessor_package(
            generator_input,
            temporary_root / "predecessor",
        )
        model_root = temporary_root / "model"
        initialize_zero_predecessor_model(model_root)
        destination = package_root / "payload" / "model"
        shutil.copytree(model_root / "model", destination)
        manifest_value = load_json_strict(
            (package_root / "manifest.json").read_bytes(),
            require_canonical=True,
        )
        manifest = Phase6PredecessorManifestRecord.from_json(manifest_value)
        measurement = measure_payload_tree(package_root / "payload")
        updated = Phase6PredecessorManifestRecord(
            package_id=PILOT_PREDECESSOR_ID,
            phase5_manifest_hash=manifest.phase5_manifest_hash,
            payload_tree_hash=measurement.tree_hash,
            state_path=manifest.state_path,
            state_hash=manifest.state_hash,
            file_count=measurement.file_count,
            total_bytes=measurement.total_bytes,
        )
        write_canonical_json(package_root / "manifest.json", updated.to_json())
        loaded = load_predecessor_package(package_root)
        if loaded.manifest != updated:
            raise ValueError("reopened pilot predecessor differs from constructed package")
        os.replace(package_root, resolved_output)
    return load_predecessor_package(resolved_output)


def request_for_pytorch_pilot_predecessor(
    predecessor: LoadedPredecessorPackage,
    *,
    transition_id: str,
) -> PilotRequestBinding:
    manifest = pilot_training_data_manifest()
    return PilotRequestBinding(
        transition_id=transition_id,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=predecessor.manifest.phase5_manifest_hash,
        predecessor_payload_tree_hash=predecessor.measurement.tree_hash,
        training_data_manifest_hash=canonical_json_hash(manifest),
        heldout_feature_manifest_hash=str(manifest["heldout_feature_manifest_hash"]),
        policy=PilotPolicyBinding(),
    )


__all__ = [
    "PILOT_PREDECESSOR_ID",
    "build_pytorch_pilot_predecessor",
    "request_for_pytorch_pilot_predecessor",
]
