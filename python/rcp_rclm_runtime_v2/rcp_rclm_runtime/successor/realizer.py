from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rcp_rclm_runtime.successor.records import (
    Phase6CommandRecord,
    Phase6EnvironmentRecord,
    Phase6FileChangeRecord,
    Phase6RealizationRecord,
    Phase6ResourceBudgetRecord,
    Phase6ResourceUsageRecord,
    Phase6RollbackSnapshotRecord,
    Phase6SelectionRecord,
    Phase6ReasonCode,
)
from rcp_rclm_runtime.successor.workspace import (
    LoadedPredecessorPackage,
    OperationApplication,
    PayloadMeasurement,
    Phase6WorkspaceError,
    apply_selected_operations,
    build_and_verify_rollback_snapshot,
    capture_realizer_environment,
    copy_payload_to_workspace,
    diff_payload_trees,
    measure_payload_tree,
)


@dataclass(frozen=True, slots=True)
class Phase6RealizationDraft:
    transition_id: str
    predecessor_manifest_hash: str
    selection_hash: str
    workspace_copy_tree_hash: str
    candidate_measurement: PayloadMeasurement
    changes: Sequence[Phase6FileChangeRecord]
    commands: Sequence[Phase6CommandRecord]
    environment: Phase6EnvironmentRecord
    rollback: Phase6RollbackSnapshotRecord
    budget: Phase6ResourceBudgetRecord
    predecessor_file_count: int
    predecessor_bytes: int
    bytes_read: int
    bytes_written: int


def realize_selected_successor(
    predecessor: LoadedPredecessorPackage,
    selection: Phase6SelectionRecord,
    budget: Phase6ResourceBudgetRecord,
    staging_root: Path,
) -> Phase6RealizationDraft:
    if selection.predecessor_manifest_hash != predecessor.manifest.manifest_hash:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.PREDECESSOR_MISMATCH,
            detail="selection is not bound to the measured predecessor manifest",
        )
    if selection.predecessor_package_id != predecessor.manifest.package_id:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.PREDECESSOR_MISMATCH,
            detail="selection predecessor package ID mismatch",
        )
    if predecessor.measurement.file_count > budget.max_file_count:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="predecessor file count exceeds the realization budget",
        )
    if predecessor.measurement.total_bytes > budget.max_total_bytes:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="predecessor byte count exceeds the realization budget",
        )
    if len(selection.operations) > budget.max_changed_files:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="selected operation count exceeds the changed-file budget",
        )
    selected_write_bytes = sum(
        len(operation.decoded_content())
        for operation in selection.operations
        if operation.operation == "write"
    )
    if selected_write_bytes > budget.max_written_bytes:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="selected content exceeds the write budget",
        )

    payload_root = staging_root / "payload"
    copy_command = copy_payload_to_workspace(
        predecessor.payload_root,
        predecessor.measurement.records,
        payload_root,
    )
    copied_measurement = measure_payload_tree(payload_root)
    if copied_measurement.tree_hash != predecessor.measurement.tree_hash:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.WORKSPACE_INVALID,
            detail="workspace copy tree differs from predecessor tree",
        )

    application: OperationApplication = apply_selected_operations(
        payload_root,
        selection.operations,
        starting_sequence=1,
    )
    candidate_measurement = measure_payload_tree(payload_root)
    if candidate_measurement.file_count > budget.max_file_count:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="candidate file count exceeds the realization budget",
        )
    if candidate_measurement.total_bytes > budget.max_total_bytes:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="candidate byte count exceeds the realization budget",
        )

    rollback, rollback_commands = build_and_verify_rollback_snapshot(
        predecessor.payload_root,
        predecessor.measurement.records,
        staging_root / "rollback" / "predecessor.tar",
        starting_sequence=1 + len(application.commands),
    )
    if rollback.archive_bytes > budget.max_snapshot_bytes:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="rollback snapshot exceeds the snapshot budget",
        )

    changes = diff_payload_trees(
        predecessor.payload_root,
        predecessor.measurement.records,
        payload_root,
        candidate_measurement.records,
        selection.operations,
    )
    commands = (
        copy_command,
        *application.commands,
        *rollback_commands,
    )
    if len(commands) + 1 > budget.max_commands:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="realization command count exceeds the budget",
        )
    bytes_read = (
        predecessor.measurement.total_bytes
        + application.bytes_read
        + predecessor.measurement.total_bytes
    )
    bytes_written = (
        predecessor.measurement.total_bytes
        + application.bytes_written
        + rollback.archive_bytes
    )
    if bytes_written > budget.max_written_bytes:
        raise Phase6WorkspaceError(
            reason_code=Phase6ReasonCode.RESOURCE_EXCEEDED,
            detail="realization writes exceed the declared budget",
        )
    return Phase6RealizationDraft(
        transition_id=selection.transition_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        selection_hash=selection.selection_hash,
        workspace_copy_tree_hash=copied_measurement.tree_hash,
        candidate_measurement=candidate_measurement,
        changes=changes,
        commands=commands,
        environment=capture_realizer_environment(),
        rollback=rollback,
        budget=budget,
        predecessor_file_count=predecessor.measurement.file_count,
        predecessor_bytes=predecessor.measurement.total_bytes,
        bytes_read=bytes_read,
        bytes_written=bytes_written,
    )


def finalize_realization(
    draft: Phase6RealizationDraft,
    package_command: Phase6CommandRecord,
) -> Phase6RealizationRecord:
    commands = (*draft.commands, package_command)
    usage = Phase6ResourceUsageRecord(
        budget=draft.budget,
        predecessor_file_count=draft.predecessor_file_count,
        candidate_file_count=draft.candidate_measurement.file_count,
        predecessor_bytes=draft.predecessor_bytes,
        candidate_bytes=draft.candidate_measurement.total_bytes,
        bytes_read=draft.bytes_read,
        bytes_written=draft.bytes_written,
        changed_files=len(draft.changes),
        commands=len(commands),
        snapshot_bytes=draft.rollback.archive_bytes,
    )
    return Phase6RealizationRecord(
        transition_id=draft.transition_id,
        predecessor_manifest_hash=draft.predecessor_manifest_hash,
        selection_hash=draft.selection_hash,
        workspace_copy_tree_hash=draft.workspace_copy_tree_hash,
        candidate_payload_tree_hash=draft.candidate_measurement.tree_hash,
        changes=draft.changes,
        commands=commands,
        environment=draft.environment,
        resources=usage,
        rollback=draft.rollback,
    )

