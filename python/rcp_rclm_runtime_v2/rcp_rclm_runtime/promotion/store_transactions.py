from __future__ import annotations
import os
import tempfile
from pathlib import Path
from typing import Literal
from rcp_rclm_runtime.canonical.hashing import build_tree_records, canonical_json_hash, semantic_tree_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.successor.package_builder import verify_candidate_package
from rcp_rclm_runtime.successor.records import Phase6CandidateManifestRecord, Phase6PackageReport, Phase6SelectionRecord
from rcp_rclm_runtime.successor.workspace import Phase6WorkspaceError, load_predecessor_package, write_canonical_json
from rcp_rclm_runtime.promotion.records import Phase7ActivePointerRecord, Phase7AttemptReport, Phase7ControllerPolicyRecord, Phase7ImmutablePackageManifestRecord, Phase7LedgerEntryRecord, Phase7ReasonCode
from rcp_rclm_runtime.promotion.store_types import ACTIVE_POINTER_NAME, LEDGER_DIRECTORY_NAME, PACKAGES_DIRECTORY_NAME, RUNS_DIRECTORY_NAME, Phase7PromotionCommit, Phase7StoreError, Phase7StoreSnapshot
from rcp_rclm_runtime.promotion.store_support import _build_next_predecessor_package, _commit_active_pointer, _copy_measured_tree, _initialize_store_directories, _load_pointer, _measure_directory_tree, _restore_active_pointer, _verify_ledger_chain, _write_ledger_entry
from rcp_rclm_runtime.promotion.store_verifier import load_active_phase7_store, verify_immutable_phase7_package
def publish_phase7_attempt_directory(store_root: Path, run_id: str, attempt_index: int, staging_attempt_root: Path) -> Path:
    resolved_store = store_root.resolve(strict=True)
    final_root = resolved_store / RUNS_DIRECTORY_NAME / run_id / f'attempt-{attempt_index:04d}'
    if final_root.exists():
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'attempt artifact directory already exists')
    final_root.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging_attempt_root, final_root)
    return final_root
def append_phase7_nonpromotion(snapshot: Phase7StoreSnapshot, attempt: Phase7AttemptReport, policy: Phase7ControllerPolicyRecord, *, event: Literal['rejection', 'indeterminate']) -> tuple[Phase7StoreSnapshot, Phase7LedgerEntryRecord]:
    if event == 'rejection' and attempt.verdict != 'reject':
        raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'rejection ledger entry requires a rejected attempt')
    if event == 'indeterminate' and attempt.verdict != 'indeterminate':
        raise Phase7StoreError(Phase7ReasonCode.LEDGER_FAILED, 'indeterminate ledger entry requires an indeterminate attempt')
    entry = Phase7LedgerEntryRecord(sequence_number=snapshot.pointer.ledger_sequence_number + 1, event=event, previous_entry_hash=snapshot.pointer.ledger_head_hash, active_package_hash_before=snapshot.pointer.active_package_hash, active_package_hash_after=snapshot.pointer.active_package_hash, attempt_report_hash=attempt.report_hash, controller_policy_hash=policy.policy_hash, run_id=attempt.run_id, reason_codes=attempt.reason_codes)
    _write_ledger_entry(snapshot.store_root, entry)
    new_pointer = Phase7ActivePointerRecord(active_package_hash=snapshot.pointer.active_package_hash, active_package_id=snapshot.pointer.active_package_id, predecessor_manifest_hash=snapshot.pointer.predecessor_manifest_hash, predecessor_payload_tree_hash=snapshot.pointer.predecessor_payload_tree_hash, state_hash=snapshot.pointer.state_hash, ledger_head_hash=entry.entry_hash, ledger_sequence_number=entry.sequence_number, controller_policy_hash=policy.policy_hash)
    _commit_active_pointer(snapshot.store_root, snapshot.pointer, new_pointer)
    try:
        verified = load_active_phase7_store(snapshot.store_root, policy)
    except Phase7StoreError:
        _restore_active_pointer(snapshot.store_root, snapshot.pointer)
        raise
    return (verified, entry)
def promote_phase7_candidate(snapshot: Phase7StoreSnapshot, candidate_package_root: Path, attempt_evidence_root: Path, attempt: Phase7AttemptReport, policy: Phase7ControllerPolicyRecord) -> Phase7PromotionCommit:
    if attempt.verdict != 'accept':
        raise Phase7StoreError(Phase7ReasonCode.PROMOTION_FAILED, 'only an accepted attempt may be promoted')
    current_pointer = _load_pointer(snapshot.store_root)
    if current_pointer.pointer_hash != snapshot.pointer.pointer_hash:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'active pointer changed before promotion')
    try:
        candidate_manifest = verify_candidate_package(candidate_package_root)
        candidate_package_tree_hash = _measure_directory_tree(candidate_package_root)
        if candidate_package_tree_hash != attempt.candidate_package_tree_hash:
            raise Phase7StoreError(Phase7ReasonCode.CANDIDATE_MUTATED, 'candidate package changed after checker acceptance')
        with tempfile.TemporaryDirectory(prefix='rcp-rclm-phase7-promotion-', dir=snapshot.store_root) as temporary_directory:
            temporary_root = Path(temporary_directory)
            package_work = temporary_root / 'package'
            predecessor_root = package_work / 'predecessor'
            predecessor = _build_next_predecessor_package(candidate_package_root, predecessor_root)
            source_candidate_root = package_work / 'source_candidate'
            _copy_measured_tree(candidate_package_root, source_candidate_root)
            evidence_root = package_work / 'evidence'
            _copy_measured_tree(attempt_evidence_root, evidence_root)
            predecessor_package_tree_hash = _measure_directory_tree(predecessor_root)
            evidence_tree_hash = _measure_directory_tree(evidence_root)
            source_candidate_tree_hash = _measure_directory_tree(source_candidate_root)
            manifest = Phase7ImmutablePackageManifestRecord(package_id=f'{predecessor.manifest.package_id}.phase7.{attempt.report_hash[:16]}', status='promoted', parent_package_hash=snapshot.pointer.active_package_hash, predecessor_package_tree_hash=predecessor_package_tree_hash, predecessor_manifest_hash=predecessor.manifest.manifest_hash, predecessor_payload_tree_hash=predecessor.manifest.payload_tree_hash, state_hash=predecessor.manifest.state_hash, source_candidate_package_tree_hash=source_candidate_tree_hash, source_candidate_manifest_hash=candidate_manifest.manifest_hash, source_candidate_payload_tree_hash=candidate_manifest.payload_tree_hash, evidence_tree_hash=evidence_tree_hash, accepted_attempt_report_hash=attempt.report_hash, controller_policy_hash=policy.policy_hash, substantive_component_kinds=candidate_manifest.substantive_component_kinds)
            write_canonical_json(package_work / 'manifest.json', manifest.to_json())
            verify_immutable_phase7_package(package_work, policy)
            package_destination = snapshot.store_root / PACKAGES_DIRECTORY_NAME / manifest.package_hash
            if package_destination.exists():
                existing = verify_immutable_phase7_package(package_destination, policy)
                if existing != manifest:
                    raise Phase7StoreError(Phase7ReasonCode.PROMOTION_FAILED, 'content-addressed promotion package collision')
            else:
                os.replace(package_work, package_destination)
        entry = Phase7LedgerEntryRecord(sequence_number=snapshot.pointer.ledger_sequence_number + 1, event='promotion', previous_entry_hash=snapshot.pointer.ledger_head_hash, active_package_hash_before=snapshot.pointer.active_package_hash, active_package_hash_after=manifest.package_hash, attempt_report_hash=attempt.report_hash, controller_policy_hash=policy.policy_hash, run_id=attempt.run_id, reason_codes=())
        _write_ledger_entry(snapshot.store_root, entry)
        new_pointer = Phase7ActivePointerRecord(active_package_hash=manifest.package_hash, active_package_id=manifest.package_id, predecessor_manifest_hash=predecessor.manifest.manifest_hash, predecessor_payload_tree_hash=predecessor.manifest.payload_tree_hash, state_hash=predecessor.manifest.state_hash, ledger_head_hash=entry.entry_hash, ledger_sequence_number=entry.sequence_number, controller_policy_hash=policy.policy_hash)
        _commit_active_pointer(snapshot.store_root, snapshot.pointer, new_pointer)
        try:
            verified = load_active_phase7_store(snapshot.store_root, policy)
        except Phase7StoreError:
            _restore_active_pointer(snapshot.store_root, snapshot.pointer)
            raise
        return Phase7PromotionCommit(snapshot=verified, ledger_entry=entry, package_manifest=manifest)
    except Phase7StoreError:
        raise
    except (CanonicalizationError, SchemaValidationError, Phase6WorkspaceError, OSError, TypeError, ValueError) as exc:
        raise Phase7StoreError(Phase7ReasonCode.PROMOTION_FAILED, f'promotion transaction failed: {type(exc).__name__}: {exc}') from exc
def write_phase7_run_report(store_root: Path, run_id: str, report_json: object) -> Path:
    run_root = store_root.resolve(strict=True) / RUNS_DIRECTORY_NAME / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    output = run_root / 'controller_report.json'
    if output.exists():
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'controller report already exists for this deterministic run ID')
    write_canonical_json(output, report_json)
    return output
