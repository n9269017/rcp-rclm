from __future__ import annotations

import io
import tarfile
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.paths import validate_file_mode, validate_semantic_path
from rcp_rclm_runtime.errors import CanonicalizationError
from rcp_rclm_runtime.successor.filesystem import command_record, safe_payload_path
from rcp_rclm_runtime.successor.measurement import measure_payload_tree
from rcp_rclm_runtime.successor.records import (
    Phase6CommandRecord,
    Phase6ReasonCode,
    Phase6RollbackSnapshotRecord,
)
from rcp_rclm_runtime.successor.workspace_types import Phase6WorkspaceError

PHASE6_ROLLBACK_FORMAT_ID: Final[str] = "rcp-rclm-phase6-ustar-v1"
ROLLBACK_ARCHIVE_RELATIVE_PATH: Final[str] = "rollback/predecessor.tar"


def build_and_verify_rollback_snapshot(
    predecessor_payload_root: Path,
    predecessor_records: Sequence[SemanticFileRecord],
    archive_path: Path,
    *,
    starting_sequence: int,
) -> tuple[Phase6RollbackSnapshotRecord, Sequence[Phase6CommandRecord]]:
    file_contents: list[tuple[SemanticFileRecord, bytes]] = []
    for record in sorted(
        predecessor_records,
        key=lambda item: item.path.encode("utf-8"),
    ):
        content = safe_payload_path(
            predecessor_payload_root,
            record.path,
        ).read_bytes()
        if sha256_hex(content) != record.sha256:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PREDECESSOR_MISMATCH,
                f"predecessor changed during rollback capture: {record.path}",
            )
        file_contents.append((record, content))
    archive_bytes = _canonical_ustar_bytes(file_contents)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        archive_path.write_bytes(archive_bytes)
        archive_path.chmod(0o644)
    except OSError as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
            f"could not write rollback snapshot: {exc}",
        ) from exc
    archive_hash = sha256_hex(archive_bytes)
    predecessor_tree_hash = semantic_tree_hash(predecessor_records)
    build_command = command_record(
        sequence_number=starting_sequence,
        command_kind="build_rollback",
        argv=(
            "internal:build_rollback",
            PHASE6_ROLLBACK_FORMAT_ID,
            f"tree={predecessor_tree_hash}",
        ),
        working_directory_policy="candidate_package_staging",
        stdin_hash=predecessor_tree_hash,
        stdout_hash=archive_hash,
    )
    restored_tree_hash = verify_rollback_snapshot_archive(
        archive_path,
        predecessor_tree_hash,
    )
    verify_command = command_record(
        sequence_number=starting_sequence + 1,
        command_kind="verify_rollback",
        argv=(
            "internal:verify_rollback",
            PHASE6_ROLLBACK_FORMAT_ID,
            f"archive={archive_hash}",
        ),
        working_directory_policy="candidate_package_staging",
        stdin_hash=archive_hash,
        stdout_hash=restored_tree_hash,
    )
    record = Phase6RollbackSnapshotRecord(
        archive_relative_path=ROLLBACK_ARCHIVE_RELATIVE_PATH,
        archive_hash=archive_hash,
        archive_bytes=len(archive_bytes),
        predecessor_tree_hash=predecessor_tree_hash,
        restored_tree_hash=restored_tree_hash,
        verified=restored_tree_hash == predecessor_tree_hash,
    )
    return record, (build_command, verify_command)


def verify_rollback_snapshot_archive(
    archive_path: Path,
    expected_tree_hash: str,
) -> str:
    try:
        archive_bytes = archive_path.read_bytes()
        restored_files: list[tuple[SemanticFileRecord, bytes]] = []
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            if names != sorted(names, key=lambda item: item.encode("utf-8")):
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                    "rollback members are not canonically ordered",
                )
            if len(names) != len(set(names)):
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                    "rollback archive contains duplicate paths",
                )
            for member in members:
                validate_semantic_path(member.name)
                if not member.isfile():
                    raise Phase6WorkspaceError(
                        Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                        f"rollback member is not a regular file: {member.name}",
                    )
                mode = f"{member.mode & 0o777:04o}"
                validate_file_mode(mode)
                if (
                    member.mtime != 0
                    or member.uid != 0
                    or member.gid != 0
                    or member.uname != ""
                    or member.gname != ""
                ):
                    raise Phase6WorkspaceError(
                        Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                        f"rollback member metadata is not canonical: {member.name}",
                    )
                source = archive.extractfile(member)
                if source is None:
                    raise Phase6WorkspaceError(
                        Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                        f"rollback member has no content: {member.name}",
                    )
                content = source.read()
                restored_files.append(
                    (
                        SemanticFileRecord(
                            path=member.name,
                            mode=mode,
                            size=len(content),
                            sha256=sha256_hex(content),
                        ),
                        content,
                    )
                )
        if _canonical_ustar_bytes(restored_files) != archive_bytes:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                "rollback archive bytes are not canonical USTAR",
            )
        with tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase6-rollback-verify-"
        ) as temp_dir:
            restore_root = Path(temp_dir) / "payload"
            restore_root.mkdir(parents=True, exist_ok=False)
            for record, content in restored_files:
                target = safe_payload_path(restore_root, record.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(int(record.mode, 8))
            restored = measure_payload_tree(restore_root)
            if restored.tree_hash != expected_tree_hash:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                    "rollback restoration tree hash mismatch",
                )
            return restored.tree_hash
    except Phase6WorkspaceError:
        raise
    except (CanonicalizationError, OSError, tarfile.TarError) as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
            f"rollback verification failed: {exc}",
        ) from exc


def _canonical_ustar_bytes(
    files: Sequence[tuple[SemanticFileRecord, bytes]],
) -> bytes:
    buffer = io.BytesIO()
    try:
        with tarfile.open(
            fileobj=buffer,
            mode="w",
            format=tarfile.USTAR_FORMAT,
        ) as archive:
            for record, content in sorted(
                files,
                key=lambda item: item[0].path.encode("utf-8"),
            ):
                if len(content) != record.size or sha256_hex(content) != record.sha256:
                    raise Phase6WorkspaceError(
                        Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
                        f"rollback content does not match file record: {record.path}",
                    )
                info = tarfile.TarInfo(record.path)
                info.size = len(content)
                info.mode = int(record.mode, 8)
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(info, io.BytesIO(content))
    except (OSError, tarfile.TarError) as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.ROLLBACK_SNAPSHOT_FAILED,
            f"could not build canonical rollback archive: {exc}",
        ) from exc
    return buffer.getvalue()
