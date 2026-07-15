from __future__ import annotations

from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.successor.filesystem import safe_payload_path
from rcp_rclm_runtime.successor.records import (
    Phase6PredecessorManifestRecord,
    Phase6ReasonCode,
)
from rcp_rclm_runtime.successor.workspace_types import (
    LoadedPredecessorPackage,
    PayloadMeasurement,
    Phase6WorkspaceError,
)

PREDECESSOR_MANIFEST_PATH = "manifest.json"
PAYLOAD_DIRECTORY_NAME = "payload"


def measure_payload_tree(payload_root: Path) -> PayloadMeasurement:
    try:
        records = build_tree_records(payload_root)
        tree_hash = semantic_tree_hash(records)
    except (CanonicalizationError, OSError) as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            str(exc),
        ) from exc
    return PayloadMeasurement(
        records=records,
        tree_hash=tree_hash,
        file_count=len(records),
        total_bytes=sum(record.size for record in records),
    )


def load_predecessor_package(package_root: Path) -> LoadedPredecessorPackage:
    try:
        resolved = package_root.resolve(strict=True)
    except OSError as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            f"predecessor package cannot be resolved: {exc}",
        ) from exc
    if not resolved.is_dir():
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            "predecessor package root must be a directory",
        )
    allowed_top_level = {PAYLOAD_DIRECTORY_NAME, PREDECESSOR_MANIFEST_PATH}
    observed_top_level = {entry.name for entry in resolved.iterdir()}
    if observed_top_level != allowed_top_level:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            "predecessor package must contain exactly payload/ and manifest.json",
        )
    manifest_path = resolved / PREDECESSOR_MANIFEST_PATH
    payload_root = resolved / PAYLOAD_DIRECTORY_NAME
    if manifest_path.is_symlink() or payload_root.is_symlink():
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            "predecessor control paths cannot be symlinks",
        )
    if not manifest_path.is_file() or not payload_root.is_dir():
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            "predecessor manifest or payload directory is missing",
        )
    try:
        manifest_json = load_json_strict(
            manifest_path.read_bytes(),
            require_canonical=True,
        )
        manifest = Phase6PredecessorManifestRecord.from_json(manifest_json)
    except (CanonicalizationError, SchemaValidationError, OSError) as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            f"invalid predecessor manifest: {exc}",
        ) from exc
    measurement = measure_payload_tree(payload_root)
    if measurement.tree_hash != manifest.payload_tree_hash:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "predecessor payload tree hash does not match manifest",
        )
    if measurement.file_count != manifest.file_count:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "predecessor file count does not match manifest",
        )
    if measurement.total_bytes != manifest.total_bytes:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "predecessor byte count does not match manifest",
        )
    state_path = safe_payload_path(payload_root, manifest.state_path)
    try:
        state_json = load_json_strict(state_path.read_bytes(), require_canonical=True)
        state = RclmStateRecord.from_json(state_json)
    except (CanonicalizationError, SchemaValidationError, OSError) as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            f"predecessor state is invalid: {exc}",
        ) from exc
    if canonical_json_hash(state.to_json()) != manifest.state_hash:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "predecessor state hash does not match manifest",
        )
    return LoadedPredecessorPackage(
        root=resolved,
        payload_root=payload_root,
        manifest=manifest,
        measurement=measurement,
        state=state,
    )
