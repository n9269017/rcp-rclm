from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.promotion.policy import reference_phase7_policy
from rcp_rclm_runtime.promotion.records import (
    Phase7ActivePointerRecord,
    Phase7AttemptReport,
    Phase7ControllerPolicyRecord,
    Phase7ControllerReport,
    Phase7LedgerEntryRecord,
)
from rcp_rclm_runtime.promotion.store import (
    ACTIVE_POINTER_NAME,
    LEDGER_DIRECTORY_NAME,
    PACKAGES_DIRECTORY_NAME,
    RUNS_DIRECTORY_NAME,
    Phase7StoreError,
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.workspace import write_canonical_json
from rcp_rclm_runtime.replay.records import (
    Phase8AttemptIndexRecord,
    Phase8ReasonCode,
    Phase8ReplayBundleManifestRecord,
)

PHASE8_MANIFEST_NAME = "manifest.json"
PHASE8_STORE_DIRECTORY_NAME = "store"


class Phase8BundleError(ValueError):
    __slots__ = ("detail", "reason")

    def __init__(
        self,
        detail: str,
        reason: Phase8ReasonCode = Phase8ReasonCode.BUNDLE_SCHEMA_INVALID,
    ) -> None:
        super().__init__(reason.value, detail)
        self.detail = detail
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Phase8ReplayBundleEvidence:
    manifest: Phase8ReplayBundleManifestRecord
    bundle_root: Path


@dataclass(frozen=True, slots=True)
class _IndexedLedgerAttempt:
    ledger: Phase7LedgerEntryRecord
    controller: Phase7ControllerReport
    attempt: Phase7AttemptReport
    attempt_root: Path


def build_phase8_replay_bundle(
    source_store_root: Path,
    output_root: Path,
    *,
    policy: Phase7ControllerPolicyRecord | None = None,
) -> Phase8ReplayBundleEvidence:
    resolved_policy = policy or reference_phase7_policy()
    resolved_source = source_store_root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise Phase8BundleError(
            f"replay bundle output already exists: {resolved_output}",
            Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
        )
    load_active_phase7_store(resolved_source, resolved_policy)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase8-bundle-",
            dir=resolved_output.parent,
        ) as temporary_directory:
            staging = Path(temporary_directory) / "bundle"
            staging.mkdir(parents=True, exist_ok=False)
            copied_store = staging / PHASE8_STORE_DIRECTORY_NAME
            _copy_regular_tree(resolved_source, copied_store)
            source_tree_hash = _tree_hash(resolved_source)
            copied_tree_hash = _tree_hash(copied_store)
            if copied_tree_hash != source_tree_hash:
                raise Phase8BundleError(
                    "copied replay store differs from the source store",
                    Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
                )
            manifest = _manifest_from_store(copied_store, resolved_policy)
            if manifest.source_store_tree_hash != source_tree_hash:
                raise Phase8BundleError(
                    "manifest store hash differs from the measured source",
                    Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
                )
            write_canonical_json(staging / PHASE8_MANIFEST_NAME, manifest.to_json())
            verified = verify_phase8_replay_bundle(staging, policy=resolved_policy)
            if verified != manifest:
                raise Phase8BundleError(
                    "public replay-bundle verifier returned a different manifest",
                    Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
                )
            os.replace(staging, resolved_output)
    except Phase8BundleError:
        raise
    except (
        CanonicalizationError,
        SchemaValidationError,
        Phase7StoreError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        reason = (
            Phase8ReasonCode.STORE_VERIFICATION_FAILED
            if isinstance(exc, Phase7StoreError)
            else Phase8ReasonCode.BUNDLE_SCHEMA_INVALID
        )
        raise Phase8BundleError(
            f"replay bundle construction failed: {type(exc).__name__}: {exc}",
            reason,
        ) from exc
    return Phase8ReplayBundleEvidence(manifest=manifest, bundle_root=resolved_output)


def verify_phase8_replay_bundle(
    bundle_root: Path,
    *,
    policy: Phase7ControllerPolicyRecord | None = None,
) -> Phase8ReplayBundleManifestRecord:
    resolved_policy = policy or reference_phase7_policy()
    try:
        resolved = bundle_root.resolve(strict=True)
        if not resolved.is_dir():
            raise Phase8BundleError(
                "replay bundle root must be a directory",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
            )
        observed = {entry.name for entry in resolved.iterdir()}
        expected = {PHASE8_MANIFEST_NAME, PHASE8_STORE_DIRECTORY_NAME}
        if observed != expected:
            raise Phase8BundleError(
                "replay bundle layout is incomplete or contains unknown entries",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
            )
        manifest_path = resolved / PHASE8_MANIFEST_NAME
        store_root = resolved / PHASE8_STORE_DIRECTORY_NAME
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise Phase8BundleError(
                "replay bundle manifest must be a regular file",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
            )
        if store_root.is_symlink() or not store_root.is_dir():
            raise Phase8BundleError(
                "replay bundle store must be a regular directory",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
            )
        manifest = Phase8ReplayBundleManifestRecord.from_json(
            load_json_strict(manifest_path.read_bytes(), require_canonical=True)
        )
        recomputed = _manifest_from_store(store_root, resolved_policy)
        if recomputed != manifest:
            raise Phase8BundleError(
                "replay bundle manifest differs from recomputed store evidence",
                Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
            )
        return manifest
    except Phase8BundleError:
        raise
    except (
        CanonicalizationError,
        SchemaValidationError,
        Phase7StoreError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        reason = (
            Phase8ReasonCode.STORE_VERIFICATION_FAILED
            if isinstance(exc, Phase7StoreError)
            else Phase8ReasonCode.BUNDLE_SCHEMA_INVALID
        )
        raise Phase8BundleError(
            f"replay bundle verification failed: {type(exc).__name__}: {exc}",
            reason,
        ) from exc


def _manifest_from_store(
    store_root: Path,
    policy: Phase7ControllerPolicyRecord,
) -> Phase8ReplayBundleManifestRecord:
    snapshot = load_active_phase7_store(store_root, policy)
    pointer = _load_pointer(store_root)
    ledger_entries = _load_ledger_entries(store_root)
    indexed_attempts = _index_ledger_attempts(store_root, ledger_entries)
    package_chain = [ledger_entries[0].active_package_hash_after]
    attempt_records: list[Phase8AttemptIndexRecord] = []
    for indexed in indexed_attempts:
        ledger = indexed.ledger
        attempt = indexed.attempt
        if ledger.event == "promotion":
            package_chain.append(ledger.active_package_hash_after)
        attempt_records.append(_attempt_index_record(indexed))
    for package_hash in package_chain:
        verified = verify_immutable_phase7_package(
            store_root / PACKAGES_DIRECTORY_NAME / package_hash,
            policy,
        )
        if verified.package_hash != package_hash:
            raise Phase8BundleError(
                "package directory name differs from verified package hash",
                Phase8ReasonCode.PACKAGE_CHAIN_MISMATCH,
            )
    store_tree_hash = _tree_hash(store_root)
    replay_id = f"phase8.replay.{store_tree_hash[:40]}"
    manifest = Phase8ReplayBundleManifestRecord(
        replay_id=replay_id,
        source_phase7_policy_hash=policy.policy_hash,
        source_store_tree_hash=store_tree_hash,
        final_active_pointer_hash=pointer.pointer_hash,
        final_active_package_hash=pointer.active_package_hash,
        ledger_head_hash=ledger_entries[-1].entry_hash,
        ledger_entry_hashes=tuple(entry.entry_hash for entry in ledger_entries),
        package_chain=tuple(package_chain),
        attempts=tuple(attempt_records),
    )
    if manifest.final_active_package_hash != snapshot.pointer.active_package_hash:
        raise Phase8BundleError("replay manifest final package differs from the verified active store")
    return manifest


def _attempt_index_record(indexed: _IndexedLedgerAttempt) -> Phase8AttemptIndexRecord:
    ledger = indexed.ledger
    controller = indexed.controller
    attempt = indexed.attempt
    evidence_root = indexed.attempt_root / "evidence"
    candidate_root = indexed.attempt_root / "candidate"
    artifact_paths: dict[str, Path] = {
        "attempt_report": evidence_root / "attempt_report.json",
        "controller_report": indexed.attempt_root.parent / "controller_report.json",
        "first_generator_input": evidence_root / "first_generator_input.json",
        "first_generator_stderr": evidence_root / "first_generator_stderr.bin",
        "first_generator_stdout": evidence_root / "first_generator_stdout.bin",
        "first_process_report": evidence_root / "first_process_report.json",
        "first_source_guard": evidence_root / "first_source_guard.json",
        "generator_input": evidence_root / "generator_input.json",
        "proposal": evidence_root / "proposal.json",
        "second_generator_input": evidence_root / "second_generator_input.json",
        "second_generator_stderr": evidence_root / "second_generator_stderr.bin",
        "second_generator_stdout": evidence_root / "second_generator_stdout.bin",
        "second_process_report": evidence_root / "second_process_report.json",
        "second_source_guard": evidence_root / "second_source_guard.json",
    }
    optional_paths = {
        "selection": evidence_root / "selection.json",
        "phase6_report": evidence_root / "phase6_report.json",
        "evaluation": evidence_root / "evaluation.json",
        "certificate": evidence_root / "certificate.json",
        "generated_lean_source": evidence_root / "generated_certificate.lean",
        "generated_source_record": evidence_root / "generated_source.json",
        "lean_source_guard": evidence_root / "lean_source_guard.json",
        "lean_report": evidence_root / "lean_report.json",
        "lean_compilation": evidence_root / "lean_compilation.json",
        "lean_stdout": evidence_root / "lean_stdout.bin",
        "lean_stderr": evidence_root / "lean_stderr.bin",
        "parsed_lean_verdict": evidence_root / "parsed_lean_verdict.json",
        "checker_request": evidence_root / "checker_request.json",
        "package_integrity": evidence_root / "package_integrity.json",
        "hardened_checker_report": evidence_root / "hardened_checker_report.json",
        "resource_usage": candidate_root / "evidence" / "resources.json",
        "rollback_record": candidate_root / "evidence" / "rollback.json",
        "rollback_archive": candidate_root / "rollback" / "predecessor.tar",
    }
    for key, path in optional_paths.items():
        if path.exists():
            artifact_paths[key] = path
    hashes: dict[str, str] = {}
    for key, path in artifact_paths.items():
        if path.is_symlink() or not path.is_file():
            raise Phase8BundleError(
                f"replay artifact must be a regular file: {path}",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
            )
        hashes[key] = sha256_hex(path.read_bytes())
    if candidate_root.exists():
        hashes["candidate_package_tree"] = _tree_hash(candidate_root)
    if attempt.candidate_package_tree_hash is not None:
        if hashes.get("candidate_package_tree") != attempt.candidate_package_tree_hash:
            raise Phase8BundleError(
                "attempt candidate tree hash differs from measured bytes",
                Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
            )
    if ledger.attempt_report_hash != attempt.report_hash:
        raise Phase8BundleError(
            "ledger attempt hash differs from the indexed attempt report",
            Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
        )
    if ledger.entry_hash not in controller.ledger_entry_hashes:
        raise Phase8BundleError(
            "controller report does not bind the indexed ledger entry",
            Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
        )
    return Phase8AttemptIndexRecord(
        ledger_sequence_number=ledger.sequence_number,
        ledger_event=ledger.event,
        run_id=ledger.run_id,
        attempt_index=attempt.attempt_index,
        attempt_verdict=attempt.verdict,
        predecessor_package_hash=ledger.active_package_hash_before,
        successor_package_hash=ledger.active_package_hash_after,
        ledger_entry_hash=ledger.entry_hash,
        controller_report_hash=controller.report_hash,
        attempt_report_hash=attempt.report_hash,
        generator_input_hash=attempt.generator_input_hash,
        proposal_hash=attempt.proposal_hash,
        selection_hash=attempt.selection_hash,
        phase6_report_hash=attempt.phase6_report_hash,
        candidate_package_tree_hash=attempt.candidate_package_tree_hash,
        evaluation_hash=attempt.evaluation_hash,
        certificate_hash=attempt.certificate_hash,
        lean_report_hash=attempt.lean_report_hash,
        checker_report_hash=attempt.checker_report_hash,
        artifact_hashes=FrozenHashMap.from_mapping(
            hashes,
            "phase8_attempt_index.artifact_hashes",
        ),
    )


def _load_pointer(store_root: Path) -> Phase7ActivePointerRecord:
    path = store_root / ACTIVE_POINTER_NAME
    if path.is_symlink() or not path.is_file():
        raise Phase8BundleError(
            "Phase 7 active pointer is not a regular file",
            Phase8ReasonCode.STORE_VERIFICATION_FAILED,
        )
    return Phase7ActivePointerRecord.from_json(
        load_json_strict(path.read_bytes(), require_canonical=True)
    )


def _load_ledger_entries(store_root: Path) -> Sequence[Phase7LedgerEntryRecord]:
    ledger_root = store_root / LEDGER_DIRECTORY_NAME
    if ledger_root.is_symlink() or not ledger_root.is_dir():
        raise Phase8BundleError(
            "Phase 7 ledger root is not a regular directory",
            Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
        )
    entries: list[Phase7LedgerEntryRecord] = []
    for path in sorted(ledger_root.iterdir(), key=lambda item: item.name.encode("utf-8")):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise Phase8BundleError(
                "Phase 7 ledger contains an unsupported entry",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        entry = Phase7LedgerEntryRecord.from_json(
            load_json_strict(path.read_bytes(), require_canonical=True)
        )
        if path.stem != entry.entry_hash:
            raise Phase8BundleError(
                "ledger filename differs from its content hash",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        entries.append(entry)
    entries.sort(key=lambda item: item.sequence_number)
    if not entries:
        raise Phase8BundleError(
            "Phase 7 ledger is empty",
            Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
        )
    for index, entry in enumerate(entries):
        if entry.sequence_number != index:
            raise Phase8BundleError(
                "Phase 7 ledger sequence is not contiguous",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        expected_previous = None if index == 0 else entries[index - 1].entry_hash
        if entry.previous_entry_hash != expected_previous:
            raise Phase8BundleError(
                "Phase 7 ledger predecessor hash mismatch",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        if index > 0 and entry.active_package_hash_before != entries[index - 1].active_package_hash_after:
            raise Phase8BundleError(
                "Phase 7 ledger active-package chain mismatch",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
    return tuple(entries)


def _index_ledger_attempts(
    store_root: Path,
    entries: Sequence[Phase7LedgerEntryRecord],
) -> Sequence[_IndexedLedgerAttempt]:
    indexed: list[_IndexedLedgerAttempt] = []
    for entry in entries[1:]:
        run_root = store_root / RUNS_DIRECTORY_NAME / entry.run_id
        report_path = run_root / "controller_report.json"
        if report_path.is_symlink() or not report_path.is_file():
            raise Phase8BundleError(
                "ledger run is missing its controller report",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        controller = Phase7ControllerReport.from_json(
            load_json_strict(report_path.read_bytes(), require_canonical=True)
        )
        if controller.run_id != entry.run_id:
            raise Phase8BundleError(
                "controller report run ID differs from the ledger",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        matches = [
            attempt
            for attempt in controller.attempts
            if attempt.report_hash == entry.attempt_report_hash
        ]
        if len(matches) != 1:
            raise Phase8BundleError(
                "ledger attempt hash does not identify exactly one run attempt",
                Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            )
        attempt = matches[0]
        attempt_root = run_root / f"attempt-{attempt.attempt_index:04d}"
        attempt_path = attempt_root / "evidence" / "attempt_report.json"
        if attempt_path.is_symlink() or not attempt_path.is_file():
            raise Phase8BundleError(
                "indexed attempt is missing its immutable report",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
            )
        observed_attempt = Phase7AttemptReport.from_json(
            load_json_strict(attempt_path.read_bytes(), require_canonical=True)
        )
        if observed_attempt != attempt:
            raise Phase8BundleError(
                "controller and attempt-directory reports differ",
                Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
            )
        indexed.append(
            _IndexedLedgerAttempt(
                ledger=entry,
                controller=controller,
                attempt=attempt,
                attempt_root=attempt_root,
            )
        )
    return tuple(indexed)


def _copy_regular_tree(source: Path, destination: Path) -> None:
    records = build_tree_records(source)
    destination.mkdir(parents=True, exist_ok=False)
    resolved_source = source.resolve(strict=True)
    for record in records:
        source_path = resolved_source.joinpath(*record.path.split("/"))
        target_path = destination.joinpath(*record.path.split("/"))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = source_path.read_bytes()
        if sha256_hex(content) != record.sha256:
            raise Phase8BundleError(
                f"source changed during replay capture: {record.path}",
                Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
            )
        target_path.write_bytes(content)
        target_path.chmod(int(record.mode, 8))
    if _tree_hash(destination) != semantic_tree_hash(records):
        raise Phase8BundleError(
            "copied replay tree failed byte-for-byte verification",
            Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
        )


def _tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root))


__all__ = [
    "PHASE8_MANIFEST_NAME",
    "PHASE8_STORE_DIRECTORY_NAME",
    "Phase8BundleError",
    "Phase8ReplayBundleEvidence",
    "build_phase8_replay_bundle",
    "verify_phase8_replay_bundle",
]
