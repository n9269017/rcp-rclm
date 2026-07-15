from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    canonical_json_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, strict_object
from rcp_rclm_runtime.successor.change_detection import diff_payload_trees
from rcp_rclm_runtime.successor.filesystem import command_record, safe_payload_path
from rcp_rclm_runtime.successor.records import (
    Phase6CandidateManifestRecord,
    Phase6CommandRecord,
    Phase6EnvironmentRecord,
    Phase6FileChangeRecord,
    Phase6PredecessorManifestRecord,
    Phase6RealizationRecord,
    Phase6ReasonCode,
    Phase6ResourceUsageRecord,
    Phase6RollbackSnapshotRecord,
    Phase6SelectionRecord,
)
from rcp_rclm_runtime.successor.rollback_io import (
    PHASE6_ROLLBACK_FORMAT_ID,
    restore_rollback_snapshot_archive,
)
from rcp_rclm_runtime.successor.workspace import (
    PHASE6_REALIZER_POLICY_ID,
    Phase6WorkspaceError,
    measure_payload_tree,
    package_command_record,
)
from rcp_rclm_runtime.successor.workspace_types import PayloadMeasurement

_CAPTURED_ENVIRONMENT_KEYS: Final[Sequence[str]] = (
    "LANG",
    "LC_ALL",
    "PYTHONHASHSEED",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
)


def verify_candidate_package(package_root: Path) -> Phase6CandidateManifestRecord:
    try:
        resolved = package_root.resolve(strict=True)
    except OSError as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate package cannot be resolved: {exc}",
        ) from exc
    if not resolved.is_dir():
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate package root must be a directory",
        )
    observed_names = {entry.name for entry in resolved.iterdir()}
    if observed_names != {"payload", "rollback", "evidence", "manifest.json"}:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate package layout is incomplete or contains unknown top-level entries",
        )
    for name in ("payload", "rollback", "evidence", "manifest.json"):
        if (resolved / name).is_symlink():
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                f"candidate control path cannot be a symlink: {name}",
            )
    rollback_root = resolved / "rollback"
    if not rollback_root.is_dir() or {
        entry.name for entry in rollback_root.iterdir()
    } != {"predecessor.tar"}:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback directory must contain exactly predecessor.tar",
        )
    rollback_archive_path = rollback_root / "predecessor.tar"
    if rollback_archive_path.is_symlink() or not rollback_archive_path.is_file():
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback archive must be a regular file",
        )
    try:
        manifest = Phase6CandidateManifestRecord.from_json(
            load_json_strict(
                (resolved / "manifest.json").read_bytes(),
                require_canonical=True,
            )
        )
        payload_root = resolved / "payload"
        payload_measurement = measure_payload_tree(payload_root)
        evidence_root = resolved / "evidence"
        expected_evidence_names = {
            "commands.json",
            "environment.json",
            "modified_files.json",
            "predecessor_manifest.json",
            "realization.json",
            "resources.json",
            "rollback.json",
            "selection.json",
        }
        observed_evidence_names = {
            entry.name for entry in evidence_root.iterdir()
        }
        if observed_evidence_names != expected_evidence_names:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                "candidate evidence file set is incomplete or contains unknown files",
            )
        predecessor_manifest = Phase6PredecessorManifestRecord.from_json(
            _load_evidence_json(evidence_root / "predecessor_manifest.json")
        )
        selection = Phase6SelectionRecord.from_json(
            _load_evidence_json(evidence_root / "selection.json")
        )
        realization = Phase6RealizationRecord.from_json(
            _load_evidence_json(evidence_root / "realization.json")
        )
        environment = Phase6EnvironmentRecord.from_json(
            _load_evidence_json(evidence_root / "environment.json")
        )
        resources = Phase6ResourceUsageRecord.from_json(
            _load_evidence_json(evidence_root / "resources.json")
        )
        rollback = Phase6RollbackSnapshotRecord.from_json(
            _load_evidence_json(evidence_root / "rollback.json")
        )
        command_log = _parse_command_log(evidence_root / "commands.json")
        declared_changes, change_ledger_hash = _parse_change_ledger(
            evidence_root / "modified_files.json"
        )
    except Phase6WorkspaceError:
        raise
    except (CanonicalizationError, SchemaValidationError, OSError) as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate package evidence is invalid: {exc}",
        ) from exc

    expected_package_id = (
        f"{selection.transition_id}.candidate."
        f"{manifest.payload_tree_hash[:16]}"
    )
    checks = {
        "package_id": manifest.package_id == expected_package_id,
        "payload_tree_hash": (
            payload_measurement.tree_hash == manifest.payload_tree_hash
        ),
        "parent_package_id": (
            predecessor_manifest.package_id == manifest.parent_package_id
        ),
        "parent_manifest_hash": (
            predecessor_manifest.manifest_hash == manifest.parent_manifest_hash
        ),
        "selection_parent_package": (
            selection.predecessor_package_id == predecessor_manifest.package_id
        ),
        "selection_parent_manifest": (
            selection.predecessor_manifest_hash
            == predecessor_manifest.manifest_hash
        ),
        "selection_phase5_parent": (
            selection.phase5_predecessor_manifest_hash
            == predecessor_manifest.phase5_manifest_hash
        ),
        "proposal_hash": selection.proposal_hash == manifest.proposal_hash,
        "selection_hash": selection.selection_hash == manifest.selection_hash,
        "selection_transition": (
            selection.transition_id == realization.transition_id
        ),
        "selection_realization_binding": (
            selection.selection_hash == realization.selection_hash
        ),
        "realization_parent_binding": (
            realization.predecessor_manifest_hash
            == predecessor_manifest.manifest_hash
        ),
        "realization_payload_binding": (
            realization.candidate_payload_tree_hash
            == manifest.payload_tree_hash
        ),
        "candidate_file_count": (
            resources.candidate_file_count == payload_measurement.file_count
        ),
        "candidate_bytes": (
            resources.candidate_bytes == payload_measurement.total_bytes
        ),
        "predecessor_file_count": (
            resources.predecessor_file_count == predecessor_manifest.file_count
        ),
        "predecessor_bytes": (
            resources.predecessor_bytes == predecessor_manifest.total_bytes
        ),
        "change_ledger_hash": (
            change_ledger_hash
            == realization.change_ledger_hash
            == manifest.change_ledger_hash
        ),
        "declared_change_ledger": (
            declared_changes == tuple(realization.changes)
        ),
        "command_log": command_log == tuple(realization.commands),
        "command_log_hash": (
            realization.command_log_hash == manifest.command_log_hash
        ),
        "environment": environment == realization.environment,
        "environment_hash": (
            environment.environment_hash == manifest.environment_hash
        ),
        "environment_policy": (
            environment.realizer_policy_id == PHASE6_REALIZER_POLICY_ID
        ),
        "environment_keys": (
            tuple(key for key, _ in environment.environment_value_hashes.entries)
            == tuple(sorted(_CAPTURED_ENVIRONMENT_KEYS))
        ),
        "resources": resources == realization.resources,
        "resource_usage_hash": (
            resources.usage_hash == manifest.resource_usage_hash
        ),
        "rollback": rollback == realization.rollback,
        "rollback_record_hash": (
            rollback.rollback_hash == manifest.rollback_snapshot_hash
        ),
        "rollback_parent_tree": (
            rollback.predecessor_tree_hash
            == predecessor_manifest.payload_tree_hash
        ),
        "rollback_restored_tree": (
            rollback.restored_tree_hash
            == predecessor_manifest.payload_tree_hash
        ),
        "component_kinds": (
            tuple(realization.substantive_component_kinds)
            == tuple(selection.substantive_component_kinds)
            == tuple(manifest.substantive_component_kinds)
        ),
    }
    if not all(checks.values()):
        failed = ", ".join(key for key, ok in checks.items() if not ok)
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate package binding checks failed: {failed}",
        )

    rollback_path = resolved / rollback.archive_relative_path
    try:
        archive_bytes = rollback_path.read_bytes()
    except OSError as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate rollback archive cannot be read: {exc}",
        ) from exc
    if sha256_hex(archive_bytes) != rollback.archive_hash:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback archive hash mismatch",
        )
    if len(archive_bytes) != rollback.archive_bytes:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback archive byte count mismatch",
        )

    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase6-package-verify-"
    ) as temporary_directory:
        restored_root = Path(temporary_directory) / "predecessor"
        restored_measurement = restore_rollback_snapshot_archive(
            rollback_path,
            restored_root,
            predecessor_manifest.payload_tree_hash,
        )
        _verify_operation_bindings(
            selection,
            restored_root,
            restored_measurement,
            payload_root,
            payload_measurement,
        )
        computed_changes = tuple(
            diff_payload_trees(
                restored_root,
                restored_measurement.records,
                payload_root,
                payload_measurement.records,
                selection.operations,
            )
        )

    computed_components = tuple(
        sorted(
            {
                change.component_kind
                for change in computed_changes
                if change.substantive and change.component_kind is not None
            }
        )
    )
    expected_commands = _expected_commands(
        selection,
        restored_measurement,
        payload_measurement,
        rollback,
    )
    expected_resources = _expected_resources(
        selection,
        restored_measurement,
        payload_measurement,
        rollback,
        computed_changes,
        expected_commands,
        resources,
    )
    recomputed_checks = {
        "restored_file_count": (
            restored_measurement.file_count == predecessor_manifest.file_count
        ),
        "restored_total_bytes": (
            restored_measurement.total_bytes == predecessor_manifest.total_bytes
        ),
        "workspace_copy_tree": (
            realization.workspace_copy_tree_hash == restored_measurement.tree_hash
        ),
        "recomputed_changes": computed_changes == tuple(realization.changes),
        "recomputed_change_hash": (
            canonical_json_hash([change.to_json() for change in computed_changes])
            == change_ledger_hash
        ),
        "recomputed_components": (
            computed_components
            == tuple(selection.substantive_component_kinds)
            == tuple(realization.substantive_component_kinds)
            == tuple(manifest.substantive_component_kinds)
        ),
        "recomputed_commands": (
            expected_commands
            == command_log
            == tuple(realization.commands)
        ),
        "recomputed_resources": expected_resources == resources,
        "rollback_restored_tree": (
            restored_measurement.tree_hash == rollback.restored_tree_hash
        ),
    }
    if not all(recomputed_checks.values()):
        failed = ", ".join(
            key for key, ok in recomputed_checks.items() if not ok
        )
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate package recomputation checks failed: {failed}",
        )
    return manifest


def _verify_operation_bindings(
    selection: Phase6SelectionRecord,
    predecessor_root: Path,
    predecessor: PayloadMeasurement,
    candidate_root: Path,
    candidate: PayloadMeasurement,
) -> None:
    before_by_path = {record.path: record for record in predecessor.records}
    after_by_path = {record.path: record for record in candidate.records}
    for operation in selection.operations:
        before = before_by_path.get(operation.path)
        after = after_by_path.get(operation.path)
        if operation.expected_before_hash is None:
            before_matches = before is None
        else:
            before_matches = (
                before is not None
                and before.sha256 == operation.expected_before_hash
                and before.mode == operation.expected_before_mode
            )
        if not before_matches:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                f"selected before-file binding mismatch: {operation.path}",
            )
        if operation.operation == "delete":
            if after is not None:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                    f"selected delete path remains in candidate: {operation.path}",
                )
            continue
        content = operation.decoded_content()
        if after is None:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                f"selected write path is absent from candidate: {operation.path}",
            )
        candidate_content = safe_payload_path(
            candidate_root,
            operation.path,
        ).read_bytes()
        if (
            after.sha256 != operation.after_hash
            or after.mode != operation.after_mode
            or sha256_hex(content) != operation.after_hash
            or candidate_content != content
        ):
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                f"selected after-file binding mismatch: {operation.path}",
            )
        if before is not None:
            predecessor_content = safe_payload_path(
                predecessor_root,
                operation.path,
            ).read_bytes()
            if sha256_hex(predecessor_content) != before.sha256:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                    f"restored predecessor content mismatch: {operation.path}",
                )


def _expected_commands(
    selection: Phase6SelectionRecord,
    predecessor: PayloadMeasurement,
    candidate: PayloadMeasurement,
    rollback: Phase6RollbackSnapshotRecord,
) -> Sequence[Phase6CommandRecord]:
    commands: list[Phase6CommandRecord] = [
        command_record(
            sequence_number=0,
            command_kind="copy_payload",
            argv=(
                "internal:copy_payload",
                f"file_count={predecessor.file_count}",
                f"tree={predecessor.tree_hash}",
            ),
            working_directory_policy="isolated_workspace",
            stdin_hash=predecessor.tree_hash,
            stdout_hash=predecessor.tree_hash,
        )
    ]
    for offset, operation in enumerate(selection.operations):
        sequence_number = 1 + offset
        if operation.operation == "write":
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
                    stdout_hash=operation.after_hash or sha256_hex(b""),
                )
            )
        else:
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
    rollback_sequence = 1 + len(selection.operations)
    commands.append(
        command_record(
            sequence_number=rollback_sequence,
            command_kind="build_rollback",
            argv=(
                "internal:build_rollback",
                PHASE6_ROLLBACK_FORMAT_ID,
                f"tree={predecessor.tree_hash}",
            ),
            working_directory_policy="candidate_package_staging",
            stdin_hash=predecessor.tree_hash,
            stdout_hash=rollback.archive_hash,
        )
    )
    commands.append(
        command_record(
            sequence_number=rollback_sequence + 1,
            command_kind="verify_rollback",
            argv=(
                "internal:verify_rollback",
                PHASE6_ROLLBACK_FORMAT_ID,
                f"archive={rollback.archive_hash}",
            ),
            working_directory_policy="candidate_package_staging",
            stdin_hash=rollback.archive_hash,
            stdout_hash=rollback.restored_tree_hash,
        )
    )
    commands.append(
        package_command_record(
            sequence_number=rollback_sequence + 2,
            selection_hash=selection.selection_hash,
            payload_tree_hash=candidate.tree_hash,
        )
    )
    return tuple(commands)


def _expected_resources(
    selection: Phase6SelectionRecord,
    predecessor: PayloadMeasurement,
    candidate: PayloadMeasurement,
    rollback: Phase6RollbackSnapshotRecord,
    changes: Sequence[Phase6FileChangeRecord],
    commands: Sequence[Phase6CommandRecord],
    declared: Phase6ResourceUsageRecord,
) -> Phase6ResourceUsageRecord:
    before_by_path = {record.path: record for record in predecessor.records}
    operation_read_bytes = sum(
        before_by_path[operation.path].size
        for operation in selection.operations
        if operation.path in before_by_path
    )
    operation_write_bytes = sum(
        len(operation.decoded_content())
        for operation in selection.operations
        if operation.operation == "write"
    )
    return Phase6ResourceUsageRecord(
        budget=declared.budget,
        predecessor_file_count=predecessor.file_count,
        candidate_file_count=candidate.file_count,
        predecessor_bytes=predecessor.total_bytes,
        candidate_bytes=candidate.total_bytes,
        bytes_read=(
            predecessor.total_bytes
            + operation_read_bytes
            + predecessor.total_bytes
        ),
        bytes_written=(
            predecessor.total_bytes
            + operation_write_bytes
            + rollback.archive_bytes
        ),
        changed_files=len(changes),
        commands=len(commands),
        snapshot_bytes=rollback.archive_bytes,
    )


def _load_evidence_json(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate evidence path is not a regular file: {path.name}",
        )
    return load_json_strict(path.read_bytes(), require_canonical=True)


def _parse_command_log(path: Path) -> Sequence[Phase6CommandRecord]:
    value = _load_evidence_json(path)
    obj = strict_object(
        value,
        "phase6_command_log",
        {"schema_id", "commands", "command_log_hash"},
    )
    require_schema_id(
        obj["schema_id"],
        "phase6_command_log.schema_id",
        "runtime.phase6_command_log.v2",
    )
    commands_raw = obj["commands"]
    if not isinstance(commands_raw, list):
        raise SchemaValidationError(
            "phase6_command_log.commands",
            "expected an array",
        )
    commands = tuple(
        Phase6CommandRecord.from_json(
            item,
            f"phase6_command_log.commands[{index}]",
        )
        for index, item in enumerate(commands_raw)
    )
    declared_hash = obj["command_log_hash"]
    if not isinstance(declared_hash, str):
        raise SchemaValidationError(
            "phase6_command_log.command_log_hash",
            "expected a string",
        )
    computed_hash = canonical_json_hash(
        [command.to_json() for command in commands]
    )
    if declared_hash != computed_hash:
        raise SchemaValidationError(
            "phase6_command_log.command_log_hash",
            "command log hash mismatch",
        )
    return commands


def _parse_change_ledger(
    path: Path,
) -> tuple[Sequence[Phase6FileChangeRecord], str]:
    value = _load_evidence_json(path)
    obj = strict_object(
        value,
        "phase6_modified_file_ledger",
        {"schema_id", "changes", "ledger_hash"},
    )
    require_schema_id(
        obj["schema_id"],
        "phase6_modified_file_ledger.schema_id",
        "runtime.phase6_modified_file_ledger.v2",
    )
    changes_raw = obj["changes"]
    if not isinstance(changes_raw, list):
        raise SchemaValidationError(
            "phase6_modified_file_ledger.changes",
            "expected an array",
        )
    changes = tuple(
        Phase6FileChangeRecord.from_json(
            item,
            f"phase6_modified_file_ledger.changes[{index}]",
        )
        for index, item in enumerate(changes_raw)
    )
    computed_hash = canonical_json_hash(
        [change.to_json() for change in changes]
    )
    declared_hash = obj["ledger_hash"]
    if not isinstance(declared_hash, str) or declared_hash != computed_hash:
        raise SchemaValidationError(
            "phase6_modified_file_ledger.ledger_hash",
            "modified-file ledger hash mismatch",
        )
    return changes, computed_hash
