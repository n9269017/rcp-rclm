from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import SemanticFileRecord
from rcp_rclm_runtime.successor.filesystem import safe_payload_path
from rcp_rclm_runtime.successor.records import (
    Phase6FileChangeRecord,
    Phase6ReasonCode,
    SelectedFileOperationRecord,
)
from rcp_rclm_runtime.successor.semantic_change import semantic_content_hash
from rcp_rclm_runtime.successor.workspace_types import Phase6WorkspaceError


def diff_payload_trees(
    before_root: Path,
    before_records: Sequence[SemanticFileRecord],
    after_root: Path,
    after_records: Sequence[SemanticFileRecord],
    operations: Sequence[SelectedFileOperationRecord],
) -> Sequence[Phase6FileChangeRecord]:
    before_by_path = {record.path: record for record in before_records}
    after_by_path = {record.path: record for record in after_records}
    operation_by_path = {operation.path: operation for operation in operations}
    changed_paths = sorted(
        {
            path
            for path in set(before_by_path) | set(after_by_path)
            if before_by_path.get(path) != after_by_path.get(path)
        },
        key=lambda item: item.encode("utf-8"),
    )
    planned_paths = sorted(
        operation_by_path,
        key=lambda item: item.encode("utf-8"),
    )
    if changed_paths != planned_paths:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.UNDECLARED_MODIFICATION,
            "actual changed paths do not equal selected operation paths",
        )
    changes: list[Phase6FileChangeRecord] = []
    for path in changed_paths:
        before = before_by_path.get(path)
        after = after_by_path.get(path)
        operation = operation_by_path[path]
        if before is None:
            change_kind = "added"
        elif after is None:
            change_kind = "deleted"
        else:
            change_kind = "modified"
        before_content = (
            None if before is None else safe_payload_path(before_root, path).read_bytes()
        )
        after_content = (
            None if after is None else safe_payload_path(after_root, path).read_bytes()
        )
        semantic_before = semantic_content_hash(
            before_content,
            path,
            operation.component_kind,
        )
        semantic_after = semantic_content_hash(
            after_content,
            path,
            operation.component_kind,
        )
        substantive = (
            operation.component_kind is not None
            and semantic_before != semantic_after
        )
        if operation.component_kind is not None and not substantive:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.METADATA_ONLY_CHANGE,
                f"component change is metadata-only: {path}",
            )
        changes.append(
            Phase6FileChangeRecord(
                path=path,
                change_kind=change_kind,
                component_kind=operation.component_kind,
                before=before,
                after=after,
                semantic_before_hash=semantic_before,
                semantic_after_hash=semantic_after,
                substantive=substantive,
            )
        )
    if not any(change.substantive for change in changes):
        raise Phase6WorkspaceError(
            Phase6ReasonCode.SUBSTANTIVE_CHANGE_REQUIRED,
            "candidate tree has no substantive changed component",
        )
    return tuple(changes)
