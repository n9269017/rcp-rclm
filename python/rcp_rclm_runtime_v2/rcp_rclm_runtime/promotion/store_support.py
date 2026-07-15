from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Final, Literal
from rcp_rclm_runtime.canonical.hashing import build_tree_records, canonical_json_hash, semantic_tree_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord, RclmStateRecord
from rcp_rclm_runtime.successor.filesystem import atomic_write, safe_payload_path
from rcp_rclm_runtime.successor.package_builder import verify_candidate_package
from rcp_rclm_runtime.successor.policies import STATE_PATH
from rcp_rclm_runtime.successor.records import Phase6CandidateManifestRecord, Phase6PackageReport, Phase6PredecessorManifestRecord, Phase6SelectionRecord
from rcp_rclm_runtime.successor.workspace import LoadedPredecessorPackage, Phase6WorkspaceError, load_predecessor_package, measure_payload_tree, write_canonical_json
from rcp_rclm_runtime.promotion.records import LedgerEvent, Phase7ActivePointerRecord, Phase7AttemptReport, Phase7ControllerPolicyRecord, Phase7ImmutablePackageManifestRecord, Phase7LedgerEntryRecord, Phase7ReasonCode
ACTIVE_POINTER_NAME: Final[str] = 'active.json'
PACKAGES_DIRECTORY_NAME: Final[str] = 'packages'
LEDGER_DIRECTORY_NAME: Final[str] = 'ledger'
RUNS_DIRECTORY_NAME: Final[str] = 'runs'
LOCK_DIRECTORY_NAME: Final[str] = '.controller-lock'

from rcp_rclm_runtime.promotion.store_types import Phase7StoreError
def _build_next_predecessor_package(candidate_package_root: Path, output_root: Path) -> LoadedPredecessorPackage:
    from rcp_rclm_runtime.generator.reference import reference_generator_input
    candidate_manifest: Phase6CandidateManifestRecord = verify_candidate_package(candidate_package_root)
    state_value = load_json_strict((candidate_package_root / 'payload' / Path(*STATE_PATH.split('/'))).read_bytes(), require_canonical=True)
    state = RclmStateRecord.from_json(state_value, 'phase7_promoted_state')
    if not isinstance(state.core, ClassicalBinaryStateRecord):
        raise Phase7StoreError(Phase7ReasonCode.PROMOTION_FAILED, 'Phase 7 finite reference promotion supports only Gate B states')
    if state.core.state not in {'initial', 'target'}:
        raise Phase7StoreError(Phase7ReasonCode.PROMOTION_FAILED, 'promoted state is outside the finite reference seed domain')
    template = reference_generator_input(state.core.state)
    payload_root = output_root / 'payload'
    _copy_measured_tree(candidate_package_root / 'payload', payload_root)
    measurement = measure_payload_tree(payload_root)
    if measurement.tree_hash != candidate_manifest.payload_tree_hash:
        raise Phase7StoreError(Phase7ReasonCode.CANDIDATE_MUTATED, 'promoted predecessor payload differs from the accepted candidate')
    manifest = Phase6PredecessorManifestRecord(package_id=template.predecessor.package_id, phase5_manifest_hash=template.predecessor.manifest_hash, payload_tree_hash=measurement.tree_hash, state_path=STATE_PATH, state_hash=canonical_json_hash(state.to_json()), file_count=measurement.file_count, total_bytes=measurement.total_bytes)
    write_canonical_json(output_root / 'manifest.json', manifest.to_json())
    return load_predecessor_package(output_root)
def _initialize_store_directories(store_root: Path) -> None:
    for name in (PACKAGES_DIRECTORY_NAME, LEDGER_DIRECTORY_NAME, RUNS_DIRECTORY_NAME):
        (store_root / name).mkdir(parents=False, exist_ok=False)
def _measure_directory_tree(root: Path) -> str:
    records = build_tree_records(root)
    return semantic_tree_hash(records)
def _copy_measured_tree(source_root: Path, output_root: Path) -> str:
    resolved_source = source_root.resolve(strict=True)
    if not resolved_source.is_dir():
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'copy source must be a directory')
    records = build_tree_records(resolved_source)
    expected_hash = semantic_tree_hash(records)
    output_root.mkdir(parents=True, exist_ok=False)
    for record in records:
        source = safe_payload_path(resolved_source, record.path)
        content = source.read_bytes()
        if sha256_hex(content) != record.sha256:
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, f'source changed during immutable copy: {record.path}')
        destination = safe_payload_path(output_root, record.path)
        atomic_write(destination, content, record.mode)
    observed_hash = _measure_directory_tree(output_root)
    if observed_hash != expected_hash:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'immutable directory copy changed the semantic tree hash')
    return observed_hash
def _write_ledger_entry(store_root: Path, entry: Phase7LedgerEntryRecord) -> None:
    ledger_root = store_root / LEDGER_DIRECTORY_NAME
    output = ledger_root / f'{entry.entry_hash}.json'
    content = canonical_json_bytes(entry.to_json())
    if output.exists():
        observed = output.read_bytes()
        if observed != content:
            raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'content-addressed ledger entry collision')
        return
    atomic_write(output, content, '0644')
def _verify_ledger_chain(store_root: Path, pointer: Phase7ActivePointerRecord) -> Phase7LedgerEntryRecord:
    expected_hash = pointer.ledger_head_hash
    expected_sequence = pointer.ledger_sequence_number
    head: Phase7LedgerEntryRecord | None = None
    while True:
        path = store_root / LEDGER_DIRECTORY_NAME / f'{expected_hash}.json'
        if path.is_symlink() or not path.is_file():
            raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger chain references a missing or non-regular entry')
        entry = Phase7LedgerEntryRecord.from_json(load_json_strict(path.read_bytes(), require_canonical=True))
        if entry.entry_hash != expected_hash:
            raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger filename does not match entry hash')
        if entry.sequence_number != expected_sequence:
            raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger sequence is not contiguous')
        if head is None:
            head = entry
            if entry.active_package_hash_after != pointer.active_package_hash:
                raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger head does not bind the active package')
        if expected_sequence == 0:
            if entry.event != 'bootstrap' or entry.previous_entry_hash is not None:
                raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger root is not a valid bootstrap entry')
            break
        if entry.previous_entry_hash is None:
            raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger entry is missing its predecessor hash')
        expected_hash = entry.previous_entry_hash
        expected_sequence -= 1
    if head is None:
        raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'ledger chain is empty')
    return head
def _load_pointer(store_root: Path) -> Phase7ActivePointerRecord:
    return Phase7ActivePointerRecord.from_json(load_json_strict((store_root / ACTIVE_POINTER_NAME).read_bytes(), require_canonical=True))
def _commit_active_pointer(store_root: Path, expected: Phase7ActivePointerRecord, replacement: Phase7ActivePointerRecord) -> None:
    observed = _load_pointer(store_root)
    if observed.pointer_hash != expected.pointer_hash:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'active pointer changed during the controller transaction')
    target = store_root / ACTIVE_POINTER_NAME
    temporary = store_root / '.active.phase7-tmp'
    if temporary.exists():
        temporary.unlink()
    atomic_write(temporary, canonical_json_bytes(replacement.to_json()), '0644')
    os.replace(temporary, target)
def _restore_active_pointer(store_root: Path, pointer: Phase7ActivePointerRecord) -> None:
    target = store_root / ACTIVE_POINTER_NAME
    temporary = store_root / '.active.phase7-restore'
    if temporary.exists():
        temporary.unlink()
    atomic_write(temporary, canonical_json_bytes(pointer.to_json()), '0644')
    os.replace(temporary, target)
