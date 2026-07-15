from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, strict_object
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
from rcp_rclm_runtime.successor.workspace import (
    Phase6WorkspaceError,
    measure_payload_tree,
    verify_rollback_snapshot_archive,
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
        payload_measurement = measure_payload_tree(resolved / "payload")
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
        change_ledger_hash = _parse_change_ledger_hash(
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
        "command_log": command_log == tuple(realization.commands),
        "command_log_hash": (
            realization.command_log_hash == manifest.command_log_hash
        ),
        "environment": environment == realization.environment,
        "environment_hash": (
            environment.environment_hash == manifest.environment_hash
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
        archive_hash = sha256_hex(rollback_path.read_bytes())
    except OSError as exc:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            f"candidate rollback archive cannot be read: {exc}",
        ) from exc
    if archive_hash != rollback.archive_hash:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback archive hash mismatch",
        )
    if rollback_path.stat().st_size != rollback.archive_bytes:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback archive byte count mismatch",
        )
    restored_tree_hash = verify_rollback_snapshot_archive(
        rollback_path,
        predecessor_manifest.payload_tree_hash,
    )
    if restored_tree_hash != rollback.restored_tree_hash:
        raise Phase6WorkspaceError(
            Phase6ReasonCode.PACKAGE_BUILD_FAILED,
            "candidate rollback archive restoration mismatch",
        )
    return manifest


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


def _parse_change_ledger_hash(path: Path) -> str:
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
    return computed_hash
