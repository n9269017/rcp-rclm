from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.package_verifier import verify_candidate_package
from rcp_rclm_runtime.successor.realizer import (
    finalize_realization,
    realize_selected_successor,
)
from rcp_rclm_runtime.successor.records import (
    Phase6CandidateManifestRecord,
    Phase6PackageReport,
    Phase6RealizationRecord,
    Phase6ReasonCode,
    Phase6ResourceBudgetRecord,
    Phase6SelectionRecord,
)
from rcp_rclm_runtime.successor.workspace import (
    Phase6WorkspaceError,
    load_predecessor_package,
    measure_payload_tree,
    package_command_record,
    write_canonical_json,
)


@dataclass(frozen=True, slots=True)
class Phase6PackageBuildEvidence:
    report: Phase6PackageReport
    output_root: Path | None


def build_candidate_package(
    predecessor_package_root: Path,
    selection: Phase6SelectionRecord,
    budget: Phase6ResourceBudgetRecord,
    output_root: Path,
) -> Phase6PackageBuildEvidence:
    """Realize, verify, and atomically publish one unverified candidate package."""

    predecessor_manifest_hash = selection.predecessor_manifest_hash
    resolved_output = output_root.resolve(strict=False)
    try:
        predecessor = load_predecessor_package(predecessor_package_root)
        predecessor_manifest_hash = predecessor.manifest.manifest_hash
        if resolved_output.exists():
            raise Phase6WorkspaceError(
                Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                "candidate output path already exists",
            )
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase6-package-",
            dir=resolved_output.parent,
        ) as temporary_directory:
            staging_root = Path(temporary_directory) / "candidate"
            staging_root.mkdir(parents=True, exist_ok=False)
            draft = realize_selected_successor(
                predecessor,
                selection,
                budget,
                staging_root,
            )
            package_command = package_command_record(
                sequence_number=len(draft.commands),
                selection_hash=selection.selection_hash,
                payload_tree_hash=draft.candidate_measurement.tree_hash,
            )
            realization = finalize_realization(draft, package_command)
            manifest = Phase6CandidateManifestRecord(
                package_id=(
                    f"{selection.transition_id}.candidate."
                    f"{realization.candidate_payload_tree_hash[:16]}"
                ),
                parent_package_id=predecessor.manifest.package_id,
                parent_manifest_hash=predecessor.manifest.manifest_hash,
                payload_tree_hash=realization.candidate_payload_tree_hash,
                proposal_hash=selection.proposal_hash,
                selection_hash=selection.selection_hash,
                change_ledger_hash=realization.change_ledger_hash,
                command_log_hash=realization.command_log_hash,
                environment_hash=realization.environment.environment_hash,
                resource_usage_hash=realization.resources.usage_hash,
                rollback_snapshot_hash=realization.rollback.rollback_hash,
                substantive_component_kinds=(
                    realization.substantive_component_kinds
                ),
            )
            evidence_hashes = _write_package_evidence(
                staging_root,
                predecessor.manifest.to_json(),
                selection,
                realization,
            )
            write_canonical_json(staging_root / "manifest.json", manifest.to_json())
            evidence_measurement = measure_payload_tree(staging_root / "evidence")
            verified_manifest = verify_candidate_package(staging_root)
            if verified_manifest != manifest:
                raise Phase6WorkspaceError(
                    Phase6ReasonCode.PACKAGE_BUILD_FAILED,
                    "public package verifier returned a different manifest",
                )
            report_hashes = dict(evidence_hashes)
            report_hashes.update(
                {
                    "candidate_manifest": manifest.manifest_hash,
                    "candidate_payload_tree": manifest.payload_tree_hash,
                    "evidence_tree": evidence_measurement.tree_hash,
                    "predecessor_manifest": predecessor.manifest.manifest_hash,
                    "rollback_archive": realization.rollback.archive_hash,
                    "selection": selection.selection_hash,
                    "realization": realization.realization_hash,
                }
            )
            report = Phase6PackageReport(
                transition_id=selection.transition_id,
                verdict="success",
                reason_codes=(),
                predecessor_manifest_hash=predecessor.manifest.manifest_hash,
                selection=selection,
                realization=realization,
                candidate_manifest=manifest,
                evidence_hashes=FrozenHashMap.from_mapping(
                    report_hashes,
                    "phase6_package_report.evidence_hashes",
                ),
            )
            os.replace(staging_root, resolved_output)
            return Phase6PackageBuildEvidence(report=report, output_root=resolved_output)
    except Phase6WorkspaceError as exc:
        return Phase6PackageBuildEvidence(
            report=_failure_report(
                transition_id=selection.transition_id,
                predecessor_manifest_hash=predecessor_manifest_hash,
                reason_code=exc.reason_code,
                detail=exc.detail,
                selection=selection,
            ),
            output_root=None,
        )
    except (CanonicalizationError, SchemaValidationError, OSError, ValueError) as exc:
        return Phase6PackageBuildEvidence(
            report=_failure_report(
                transition_id=selection.transition_id,
                predecessor_manifest_hash=predecessor_manifest_hash,
                reason_code=Phase6ReasonCode.INTERNAL_ERROR,
                detail=f"{type(exc).__name__}: {exc}",
                selection=selection,
            ),
            output_root=None,
        )


def _write_package_evidence(
    staging_root: Path,
    predecessor_manifest: object,
    selection: Phase6SelectionRecord,
    realization: Phase6RealizationRecord,
) -> dict[str, str]:
    evidence_root = staging_root / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=False)
    payloads: dict[str, object] = {
        "predecessor_manifest.json": predecessor_manifest,
        "selection.json": selection.to_json(),
        "modified_files.json": {
            "schema_id": "runtime.phase6_modified_file_ledger.v2",
            "changes": [change.to_json() for change in realization.changes],
            "ledger_hash": realization.change_ledger_hash,
        },
        "commands.json": {
            "schema_id": "runtime.phase6_command_log.v2",
            "commands": [command.to_json() for command in realization.commands],
            "command_log_hash": realization.command_log_hash,
        },
        "environment.json": realization.environment.to_json(),
        "resources.json": realization.resources.to_json(),
        "rollback.json": realization.rollback.to_json(),
        "realization.json": realization.to_json(),
    }
    hashes: dict[str, str] = {}
    for name in sorted(payloads, key=lambda item: item.encode("utf-8")):
        content = canonical_json_bytes(payloads[name])
        write_canonical_json(evidence_root / name, payloads[name])
        hashes[f"evidence/{name}"] = sha256_hex(content)
    return hashes


def _failure_report(
    *,
    transition_id: str,
    predecessor_manifest_hash: str,
    reason_code: Phase6ReasonCode,
    detail: str,
    selection: Phase6SelectionRecord,
) -> Phase6PackageReport:
    return Phase6PackageReport(
        transition_id=transition_id,
        verdict="reject",
        reason_codes=(reason_code,),
        predecessor_manifest_hash=predecessor_manifest_hash,
        selection=selection,
        realization=None,
        candidate_manifest=None,
        evidence_hashes=FrozenHashMap.from_mapping(
            {
                "error": sha256_hex(detail.encode("utf-8")),
                "selection": selection.selection_hash,
            },
            "phase6_package_report.evidence_hashes",
        ),
    )


__all__ = [
    "Phase6PackageBuildEvidence",
    "build_candidate_package",
    "verify_candidate_package",
]
