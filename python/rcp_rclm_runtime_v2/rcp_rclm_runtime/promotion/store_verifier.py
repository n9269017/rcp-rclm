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
from rcp_rclm_runtime.promotion.store_types import ACTIVE_POINTER_NAME, LEDGER_DIRECTORY_NAME, LOCK_DIRECTORY_NAME, PACKAGES_DIRECTORY_NAME, RUNS_DIRECTORY_NAME, Phase7PromotionCommit, Phase7StoreError, Phase7StoreSnapshot
from rcp_rclm_runtime.promotion.store_support import _build_next_predecessor_package, _commit_active_pointer, _copy_measured_tree, _initialize_store_directories, _load_pointer, _measure_directory_tree, _restore_active_pointer, _verify_ledger_chain, _write_ledger_entry

def bootstrap_phase7_store(store_root: Path, predecessor_package_root: Path, policy: Phase7ControllerPolicyRecord, *, bootstrap_id: str) -> Phase7StoreSnapshot:
    resolved_store = store_root.resolve(strict=False)
    if resolved_store.exists():
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'controller store already exists')
    resolved_store.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='rcp-rclm-phase7-bootstrap-', dir=resolved_store.parent) as temporary_directory:
            temporary_root = Path(temporary_directory)
            staging_store = temporary_root / 'store'
            staging_store.mkdir(parents=True, exist_ok=False)
            _initialize_store_directories(staging_store)
            package_work = temporary_root / 'package'
            predecessor_copy = package_work / 'predecessor'
            _copy_measured_tree(predecessor_package_root, predecessor_copy)
            predecessor = load_predecessor_package(predecessor_copy)
            evidence_root = package_work / 'evidence'
            evidence_root.mkdir(parents=True, exist_ok=False)
            write_canonical_json(evidence_root / 'policy.json', policy.to_json())
            write_canonical_json(evidence_root / 'bootstrap.json', {'schema_id': 'runtime.phase7_bootstrap_evidence.v2', 'bootstrap_id': bootstrap_id, 'controller_policy_hash': policy.policy_hash, 'predecessor_manifest_hash': predecessor.manifest.manifest_hash, 'predecessor_payload_tree_hash': predecessor.manifest.payload_tree_hash, 'state_hash': predecessor.manifest.state_hash})
            predecessor_package_tree_hash = _measure_directory_tree(predecessor_copy)
            evidence_tree_hash = _measure_directory_tree(evidence_root)
            manifest = Phase7ImmutablePackageManifestRecord(package_id=f'{predecessor.manifest.package_id}.phase7-root', status='root', parent_package_hash=None, predecessor_package_tree_hash=predecessor_package_tree_hash, predecessor_manifest_hash=predecessor.manifest.manifest_hash, predecessor_payload_tree_hash=predecessor.manifest.payload_tree_hash, state_hash=predecessor.manifest.state_hash, source_candidate_package_tree_hash=None, source_candidate_manifest_hash=None, source_candidate_payload_tree_hash=None, evidence_tree_hash=evidence_tree_hash, accepted_attempt_report_hash=None, controller_policy_hash=policy.policy_hash, substantive_component_kinds=())
            write_canonical_json(package_work / 'manifest.json', manifest.to_json())
            verify_immutable_phase7_package(package_work, policy)
            package_destination = staging_store / PACKAGES_DIRECTORY_NAME / manifest.package_hash
            os.replace(package_work, package_destination)
            ledger = Phase7LedgerEntryRecord(sequence_number=0, event='bootstrap', previous_entry_hash=None, active_package_hash_before=manifest.package_hash, active_package_hash_after=manifest.package_hash, attempt_report_hash=None, controller_policy_hash=policy.policy_hash, run_id=bootstrap_id, reason_codes=())
            _write_ledger_entry(staging_store, ledger)
            pointer = Phase7ActivePointerRecord(active_package_hash=manifest.package_hash, active_package_id=manifest.package_id, predecessor_manifest_hash=predecessor.manifest.manifest_hash, predecessor_payload_tree_hash=predecessor.manifest.payload_tree_hash, state_hash=predecessor.manifest.state_hash, ledger_head_hash=ledger.entry_hash, ledger_sequence_number=0, controller_policy_hash=policy.policy_hash)
            write_canonical_json(staging_store / ACTIVE_POINTER_NAME, pointer.to_json())
            snapshot = load_active_phase7_store(staging_store, policy)
            os.replace(staging_store, resolved_store)
    except Phase7StoreError:
        raise
    except (CanonicalizationError, SchemaValidationError, Phase6WorkspaceError, OSError, TypeError, ValueError) as exc:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, f'could not bootstrap controller store: {type(exc).__name__}: {exc}') from exc
    return Phase7StoreSnapshot(store_root=resolved_store, pointer=snapshot.pointer, package_root=resolved_store / PACKAGES_DIRECTORY_NAME / snapshot.pointer.active_package_hash, package_manifest=snapshot.package_manifest, predecessor_root=resolved_store / PACKAGES_DIRECTORY_NAME / snapshot.pointer.active_package_hash / 'predecessor', predecessor=load_predecessor_package(resolved_store / PACKAGES_DIRECTORY_NAME / snapshot.pointer.active_package_hash / 'predecessor'), ledger_head=snapshot.ledger_head)

def load_active_phase7_store(store_root: Path, policy: Phase7ControllerPolicyRecord) -> Phase7StoreSnapshot:
    try:
        resolved = store_root.resolve(strict=True)
        if not resolved.is_dir():
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'controller store root must be a directory')
        allowed = {ACTIVE_POINTER_NAME, PACKAGES_DIRECTORY_NAME, LEDGER_DIRECTORY_NAME, RUNS_DIRECTORY_NAME, LOCK_DIRECTORY_NAME}
        observed = {entry.name for entry in resolved.iterdir()}
        unknown = observed - allowed
        required = {ACTIVE_POINTER_NAME, PACKAGES_DIRECTORY_NAME, LEDGER_DIRECTORY_NAME, RUNS_DIRECTORY_NAME}
        if unknown or not required.issubset(observed):
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'controller store layout is incomplete or contains unknown entries')
        pointer_path = resolved / ACTIVE_POINTER_NAME
        if pointer_path.is_symlink() or not pointer_path.is_file():
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'active pointer must be a regular file')
        pointer = Phase7ActivePointerRecord.from_json(load_json_strict(pointer_path.read_bytes(), require_canonical=True))
        if pointer.controller_policy_hash != policy.policy_hash:
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, 'active pointer controller-policy binding mismatch')
        package_root = resolved / PACKAGES_DIRECTORY_NAME / pointer.active_package_hash
        package_manifest = verify_immutable_phase7_package(package_root, policy)
        predecessor_root = package_root / 'predecessor'
        predecessor = load_predecessor_package(predecessor_root)
        checks = {'active_package_hash': package_manifest.package_hash == pointer.active_package_hash, 'active_package_id': package_manifest.package_id == pointer.active_package_id, 'predecessor_manifest_hash': predecessor.manifest.manifest_hash == pointer.predecessor_manifest_hash, 'predecessor_payload_tree_hash': predecessor.manifest.payload_tree_hash == pointer.predecessor_payload_tree_hash, 'state_hash': predecessor.manifest.state_hash == pointer.state_hash}
        if not all(checks.values()):
            failed = ', '.join((key for key, ok in checks.items() if not ok))
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, f'active pointer package bindings failed: {failed}')
        ledger_head = _verify_ledger_chain(resolved, pointer)
        return Phase7StoreSnapshot(store_root=resolved, pointer=pointer, package_root=package_root, package_manifest=package_manifest, predecessor_root=predecessor_root, predecessor=predecessor, ledger_head=ledger_head)
    except Phase7StoreError:
        raise
    except (CanonicalizationError, SchemaValidationError, Phase6WorkspaceError, OSError, TypeError, ValueError) as exc:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, f'controller store verification failed: {type(exc).__name__}: {exc}') from exc

def verify_immutable_phase7_package(package_root: Path, policy: Phase7ControllerPolicyRecord) -> Phase7ImmutablePackageManifestRecord:
    try:
        resolved = package_root.resolve(strict=True)
        if not resolved.is_dir():
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'Phase 7 package root must be a directory')
        manifest_path = resolved / 'manifest.json'
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'Phase 7 package manifest must be a regular file')
        manifest = Phase7ImmutablePackageManifestRecord.from_json(load_json_strict(manifest_path.read_bytes(), require_canonical=True))
        expected_names = {'predecessor', 'evidence', 'manifest.json'}
        if manifest.status == 'promoted':
            expected_names.add('source_candidate')
        observed_names = {entry.name for entry in resolved.iterdir()}
        if observed_names != expected_names:
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, 'Phase 7 package layout is incomplete or contains unknown entries')
        for name in expected_names:
            if (resolved / name).is_symlink():
                raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, f'Phase 7 package control path cannot be a symlink: {name}')
        evidence_root = resolved / 'evidence'
        predecessor_root = resolved / 'predecessor'
        predecessor_package_tree_hash = _measure_directory_tree(predecessor_root)
        evidence_tree_hash = _measure_directory_tree(evidence_root)
        predecessor = load_predecessor_package(predecessor_root)
        policy_record = Phase7ControllerPolicyRecord.from_json(load_json_strict((evidence_root / 'policy.json').read_bytes(), require_canonical=True))
        checks = {'policy_record': policy_record == policy, 'policy_hash': manifest.controller_policy_hash == policy.policy_hash, 'predecessor_package_tree_hash': manifest.predecessor_package_tree_hash == predecessor_package_tree_hash, 'predecessor_manifest_hash': manifest.predecessor_manifest_hash == predecessor.manifest.manifest_hash, 'predecessor_payload_tree_hash': manifest.predecessor_payload_tree_hash == predecessor.manifest.payload_tree_hash, 'state_hash': manifest.state_hash == predecessor.manifest.state_hash, 'evidence_tree_hash': manifest.evidence_tree_hash == evidence_tree_hash}
        if manifest.status == 'root':
            if not (evidence_root / 'bootstrap.json').is_file():
                checks['bootstrap_evidence'] = False
        else:
            source_candidate_root = resolved / 'source_candidate'
            source_candidate_tree_hash = _measure_directory_tree(source_candidate_root)
            candidate_manifest = verify_candidate_package(source_candidate_root)
            attempt = Phase7AttemptReport.from_json(load_json_strict((evidence_root / 'attempt_report.json').read_bytes(), require_canonical=True))
            phase6_report = Phase6PackageReport.from_json(load_json_strict((evidence_root / 'phase6_report.json').read_bytes(), require_canonical=True))
            source_selection = Phase6SelectionRecord.from_json(load_json_strict((source_candidate_root / 'evidence' / 'selection.json').read_bytes(), require_canonical=True))
            checks.update({'attempt_accepted': attempt.verdict == 'accept', 'attempt_hash': manifest.accepted_attempt_report_hash == attempt.report_hash, 'attempt_candidate_tree': attempt.candidate_package_tree_hash == source_candidate_tree_hash, 'attempt_selection': attempt.selection_hash == source_selection.selection_hash, 'attempt_phase6_report': attempt.phase6_report_hash == phase6_report.report_hash, 'phase6_report_built': phase6_report.built, 'phase6_report_manifest': phase6_report.candidate_manifest == candidate_manifest, 'source_candidate_package_tree_hash': manifest.source_candidate_package_tree_hash == source_candidate_tree_hash, 'source_candidate_manifest_hash': manifest.source_candidate_manifest_hash == candidate_manifest.manifest_hash, 'source_candidate_payload_tree_hash': manifest.source_candidate_payload_tree_hash == candidate_manifest.payload_tree_hash, 'promoted_payload_matches_candidate': predecessor.manifest.payload_tree_hash == candidate_manifest.payload_tree_hash, 'substantive_component_kinds': tuple(manifest.substantive_component_kinds) == tuple(candidate_manifest.substantive_component_kinds)})
        if not all(checks.values()):
            failed = ', '.join((key for key, ok in checks.items() if not ok))
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, f'Phase 7 package binding checks failed: {failed}')
        return manifest
    except Phase7StoreError:
        raise
    except (CanonicalizationError, SchemaValidationError, Phase6WorkspaceError, OSError, TypeError, ValueError) as exc:
        raise Phase7StoreError(Phase7ReasonCode.ACTIVE_PACKAGE_MISMATCH, f'Phase 7 package verification failed: {type(exc).__name__}: {exc}') from exc
