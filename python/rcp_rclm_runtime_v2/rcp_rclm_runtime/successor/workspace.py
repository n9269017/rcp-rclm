from __future__ import annotations

import os
import platform
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.change_detection import diff_payload_trees
from rcp_rclm_runtime.successor.filesystem import atomic_write, command_record
from rcp_rclm_runtime.successor.measurement import (
    PAYLOAD_DIRECTORY_NAME,
    PREDECESSOR_MANIFEST_PATH,
    load_predecessor_package,
    measure_payload_tree,
)
from rcp_rclm_runtime.successor.rollback_io import (
    PHASE6_ROLLBACK_FORMAT_ID,
    ROLLBACK_ARCHIVE_RELATIVE_PATH,
    build_and_verify_rollback_snapshot,
    verify_rollback_snapshot_archive,
)
from rcp_rclm_runtime.successor.records import (
    Phase6CommandRecord,
    Phase6EnvironmentRecord,
)
from rcp_rclm_runtime.successor.workspace_io import (
    apply_selected_operations,
    copy_payload_to_workspace,
)
from rcp_rclm_runtime.successor.workspace_types import (
    LoadedPredecessorPackage,
    OperationApplication,
    PayloadMeasurement,
    Phase6WorkspaceError,
)

PHASE6_REALIZER_POLICY_ID: Final[str] = "rcp-rclm-phase6-isolated-realizer-v1"
_CAPTURED_ENVIRONMENT_KEYS: Final[Sequence[str]] = (
    "LANG",
    "LC_ALL",
    "PYTHONHASHSEED",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
)


def capture_realizer_environment() -> Phase6EnvironmentRecord:
    value_hashes = {
        key: sha256_hex(os.environ.get(key, "").encode("utf-8"))
        for key in _CAPTURED_ENVIRONMENT_KEYS
    }
    return Phase6EnvironmentRecord(
        realizer_policy_id=PHASE6_REALIZER_POLICY_ID,
        python_implementation=sys.implementation.name,
        python_version=platform.python_version(),
        os_name=os.name,
        platform_system=platform.system() or "unknown",
        platform_machine=platform.machine() or "unknown",
        filesystem_encoding=sys.getfilesystemencoding(),
        environment_value_hashes=FrozenHashMap.from_mapping(
            value_hashes,
            "phase6_environment.environment_value_hashes",
        ),
    )


def package_command_record(
    *,
    sequence_number: int,
    selection_hash: str,
    payload_tree_hash: str,
) -> Phase6CommandRecord:
    return command_record(
        sequence_number=sequence_number,
        command_kind="build_package",
        argv=(
            "internal:build_package",
            f"selection={selection_hash}",
            f"payload_tree={payload_tree_hash}",
        ),
        working_directory_policy="candidate_package_staging",
        stdin_hash=selection_hash,
        stdout_hash=payload_tree_hash,
    )


def write_canonical_json(path: Path, value: object) -> bytes:
    content = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, content, "0644")
    return content


__all__ = [
    "LoadedPredecessorPackage",
    "OperationApplication",
    "PAYLOAD_DIRECTORY_NAME",
    "PHASE6_REALIZER_POLICY_ID",
    "PHASE6_ROLLBACK_FORMAT_ID",
    "PREDECESSOR_MANIFEST_PATH",
    "PayloadMeasurement",
    "Phase6WorkspaceError",
    "ROLLBACK_ARCHIVE_RELATIVE_PATH",
    "apply_selected_operations",
    "build_and_verify_rollback_snapshot",
    "capture_realizer_environment",
    "copy_payload_to_workspace",
    "diff_payload_trees",
    "load_predecessor_package",
    "measure_payload_tree",
    "package_command_record",
    "verify_rollback_snapshot_archive",
    "write_canonical_json",
]
