from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.successor._record_common import (
    CommandKind,
    WorkingDirectoryPolicy,
)
from rcp_rclm_runtime.successor.records import (
    Phase6CommandRecord,
    Phase6ReasonCode,
)
from rcp_rclm_runtime.successor.workspace_types import Phase6WorkspaceError
from rcp_rclm_runtime.canonical.hashing import sha256_hex


def safe_payload_path(root: Path, semantic_path: str) -> Path:
    validated = validate_semantic_path(semantic_path)
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*validated.split("/"))
    resolved_parent = candidate.parent.resolve(strict=False)
    try:
        resolved_parent.relative_to(resolved_root)
    except ValueError as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            f"semantic path escapes payload root: {semantic_path}",
        ) from exc
    return candidate


def atomic_write(path: Path, content: bytes, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.phase6-tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(content)
    temporary.chmod(int(mode, 8))
    os.replace(temporary, path)


def command_record(
    *,
    sequence_number: int,
    command_kind: CommandKind,
    argv: Sequence[str],
    working_directory_policy: WorkingDirectoryPolicy,
    stdin_hash: str,
    stdout_hash: str,
) -> Phase6CommandRecord:
    return Phase6CommandRecord(
        sequence_number=sequence_number,
        command_kind=command_kind,
        argv=tuple(argv),
        working_directory_policy=working_directory_policy,
        stdin_hash=stdin_hash,
        stdout_hash=stdout_hash,
        stderr_hash=sha256_hex(b""),
        exit_code=0,
        internal_executor=True,
    )
