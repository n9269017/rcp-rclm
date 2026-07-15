from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.successor.filesystem import (
    atomic_write,
    command_record,
    safe_payload_path,
)
from rcp_rclm_runtime.successor.measurement import measure_payload_tree
from rcp_rclm_runtime.successor.records import (
    Phase6CommandRecord,
    Phase6ReasonCode,
    SelectedFileOperationRecord,
)
from rcp_rclm_runtime.successor.workspace_types import (
    OperationApplication,
    Phase6WorkspaceError,
)


def copy_payload_to_workspace(
    source_root: Path,
    records: Sequence[SemanticFileRecord],
    workspace_root: Path,
) -> Phase6CommandRecord:
    workspace_root.mkdir(parents=True, exist_ok=False)
    for record in records:
        source = safe_payload_path(source_root, record.path)
        target = safe_payload_path(workspace_root, record.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()
        if sha256_hex(content) != record.sha256:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PREDECESSOR_MISMATCH,
                f"source file changed during copy: {record.path}",
            )
        target.write_bytes(content)
        target.chmod(int(record.mode, 8))
    copied = measure_payload_tree(workspace_root)
    expected = semantic_tree_hash(records)
    if copied.tree_hash != expected:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.WORKSPACE_INVALID,
            "isolated workspace copy does not match predecessor tree",
        )
    return command_record(
        sequence_number=0,
        command_kind="copy_payload",
        argv=(
            "internal:copy_payload",
            f"file_count={len(records)}",
            f"tree={expected}",
        ),
        working_directory_policy="isolated_workspace",
        stdin_hash=expected,
        stdout_hash=copied.tree_hash,
    )


def apply_selected_operations(
    workspace_root: Path,
    operations: Sequence[SelectedFileOperationRecord],
    *,
    starting_sequence: int,
) -> OperationApplication:
    commands: list[Phase6CommandRecord] = []
    bytes_read = 0
    bytes_written = 0
    for offset, operation in enumerate(operations):
        target = safe_payload_path(workspace_root, operation.path)
        before_content: bytes | None = None
        before_mode: str | None = None
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.WORKSPACE_INVALID,
                    f"operation target is not a regular file: {operation.path}",
                )
            before_content = target.read_bytes()
            bytes_read += len(before_content)
            before_mode = "0755" if (target.stat().st_mode & 0o111) else "0644"
        if operation.expected_before_hash is None:
            if before_content is not None:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PREDECESSOR_MISMATCH,
                    f"add operation found an existing path: {operation.path}",
                )
        else:
            if before_content is None:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PREDECESSOR_MISMATCH,
                    f"operation target is missing: {operation.path}",
                )
            if sha256_hex(before_content) != operation.expected_before_hash:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PREDECESSOR_MISMATCH,
                    f"before hash mismatch for {operation.path}",
                )
            if before_mode != operation.expected_before_mode:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PREDECESSOR_MISMATCH,
                    f"before mode mismatch for {operation.path}",
                )
        sequence_number = starting_sequence + offset
        if operation.operation == "write":
            content = operation.decoded_content()
            if sha256_hex(content) != operation.after_hash:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.SELECTION_FAILED,
                    f"selected content hash mismatch for {operation.path}",
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, content, operation.after_mode or "0644")
            bytes_written += len(content)
            after_hash = sha256_hex(target.read_bytes())
            if after_hash != operation.after_hash:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.COMMAND_FAILED,
                    f"written file hash mismatch for {operation.path}",
                )
            commands.append(
                command_record(
                    sequence_number=sequence_number,
                    command_kind="write_file",
                    argv=(
                        "internal:write_file",
                        operation.path,
                        operation.after_mode or "0644",
                        operation.after_hash or sha256_hex(b""),
                    ),
                    working_directory_policy="isolated_workspace",
                    stdin_hash=operation.operation_hash,
                    stdout_hash=after_hash,
                )
            )
        else:
            target.unlink()
            commands.append(
                command_record(
                    sequence_number=sequence_number,
                    command_kind="delete_file",
                    argv=("internal:delete_file", operation.path),
                    working_directory_policy="isolated_workspace",
                    stdin_hash=operation.operation_hash,
                    stdout_hash=sha256_hex(b"deleted"),
                )
            )
    return OperationApplication(
        commands=tuple(commands),
        bytes_read=bytes_read,
        bytes_written=bytes_written,
    )
