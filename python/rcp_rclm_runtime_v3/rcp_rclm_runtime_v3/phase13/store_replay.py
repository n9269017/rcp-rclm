from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.promotion.records import (
    Phase7ActivePointerRecord,
    Phase7AttemptReport,
    Phase7ControllerPolicyRecord,
    Phase7ImmutablePackageManifestRecord,
    Phase7LedgerEntryRecord,
)
from rcp_rclm_runtime.promotion.store_verifier import (
    load_active_phase7_store,
    verify_immutable_phase7_package,
)

from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase13.full_records import Phase13CheckRecord


EMBEDDED_PHASE12_ROOT = "model/weights/phase12_package"
_PHASE12_CONTROLLER_POLICY_ID = "rcp-rclm-v3-phase12-first-self-hosted-promotion-v1"
_EXPECTED_EVENTS = (
    "bootstrap",
    "rejection",
    "promotion",
    "rejection",
    "promotion",
    "promotion",
    "promotion",
)
_EXPECTED_TRANSITIONS = {
    1: "phase12-self-hosted-four-promotion-trajectory-v1",
    2: "phase12-m0-to-m1-weight-successor",
    3: "phase12-m1-to-m2-memory-retrieval-successor",
    4: "phase12-m1-to-m2-memory-retrieval-successor",
    5: "phase12-m2-to-m3-generator-planner-successor",
    6: "phase12-m3-to-m4-adapter-optimizer-successor",
}
_EXPECTED_COMPONENTS = {
    0: (),
    2: ("model_weights",),
    4: ("memory_policy", "retrieval_policy"),
    5: ("code_generation_policy", "planning_policy"),
    6: ("architecture_code", "training_policy"),
}
_EXPECTED_REASONS = {
    1: ("PHASE7_PROPOSAL_INVALID",),
    3: ("PHASE7_PROPOSAL_INVALID",),
}
_REFERENCE_PACKAGE_PATHS = {
    "M0": "phase12d/phase12c/phase12b/wrapper_predecessor/payload/model/weights/phase12_package",
    "M1": "phase12d/phase12c/phase12b/semantic_candidate",
    "M2": "phase12d/phase12c/semantic_candidate",
    "M3": "phase12d/semantic_candidate",
    "M4": "semantic_candidate",
}


def _object(path: Path) -> dict[str, object]:
    value = load_json_strict(path.resolve(strict=True).read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError("phase13.store.json", f"expected object at {path}")
    return value


def _tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _phase13_controller_policy() -> Phase7ControllerPolicyRecord:
    return Phase7ControllerPolicyRecord(
        policy_id=_PHASE12_CONTROLLER_POLICY_ID,
        scope="pytorch_pilot_gate_b_stable",
        generator_backend="pytorch_pilot_process",
        selector_backend="pytorch_pilot_host_selector",
        realizer_backend="phase6_isolated_realizer",
        evaluator_backend="pytorch_pilot_exact_integer_evaluator",
        checker_backend="phase4_hardened_checker",
        require_two_run_generator_replay=True,
        require_public_package_verification=True,
        require_lean_acceptance=True,
        require_checker_acceptance=True,
        allow_manual_repair=False,
        allow_candidate_mutation=False,
    )


def _load_ledger(store_root: Path) -> Sequence[Phase7LedgerEntryRecord]:
    ledger_root = store_root.resolve(strict=True) / "ledger"
    entries: list[Phase7LedgerEntryRecord] = []
    for path in ledger_root.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise SchemaValidationError("phase13.store.ledger", "ledger contains a noncanonical entry")
        entry = Phase7LedgerEntryRecord.from_json(_object(path))
        if path.stem != entry.entry_hash:
            raise SchemaValidationError("phase13.store.ledger", "ledger filename/hash mismatch")
        entries.append(entry)
    return tuple(sorted(entries, key=lambda item: item.sequence_number))


def _load_packages(
    store_root: Path,
    policy: Phase7ControllerPolicyRecord,
) -> Mapping[str, tuple[Path, Phase7ImmutablePackageManifestRecord]]:
    packages_root = store_root.resolve(strict=True) / "packages"
    result: dict[str, tuple[Path, Phase7ImmutablePackageManifestRecord]] = {}
    for path in packages_root.iterdir():
        if path.is_symlink() or not path.is_dir():
            raise SchemaValidationError("phase13.store.packages", "package entry must be a directory")
        manifest = verify_immutable_phase7_package(path, policy)
        if path.name != manifest.package_hash:
            raise SchemaValidationError("phase13.store.packages", "package directory/hash mismatch")
        result[manifest.package_hash] = (path, manifest)
    return result


def _reference_package_hashes(reference_root: Path) -> Mapping[str, str]:
    root = reference_root.resolve(strict=True)
    return {
        label: load_package_manifest(root / relative).package_hash
        for label, relative in _REFERENCE_PACKAGE_PATHS.items()
    }


def _load_attempts(
    evidence_root: Path,
) -> Mapping[str, tuple[Path, Phase7AttemptReport]]:
    root = evidence_root.resolve(strict=True)
    result: dict[str, tuple[Path, Phase7AttemptReport]] = {}
    for path in root.rglob("attempt_report.json"):
        if path.is_symlink() or not path.is_file():
            raise SchemaValidationError("phase13.store.attempts", "attempt report must be regular")
        report = Phase7AttemptReport.from_json(_object(path))
        if report.report_hash in result:
            raise SchemaValidationError("phase13.store.attempts", "duplicate attempt report hash")
        result[report.report_hash] = (path.parent, report)
    return result


def _pointer_for_ledger_state(
    package: tuple[Path, Phase7ImmutablePackageManifestRecord],
    ledger: Phase7LedgerEntryRecord,
    policy: Phase7ControllerPolicyRecord,
) -> Phase7ActivePointerRecord:
    _, manifest = package
    return Phase7ActivePointerRecord(
        active_package_hash=manifest.package_hash,
        active_package_id=manifest.package_id,
        predecessor_manifest_hash=manifest.predecessor_manifest_hash,
        predecessor_payload_tree_hash=manifest.predecessor_payload_tree_hash,
        state_hash=manifest.state_hash,
        ledger_head_hash=ledger.entry_hash,
        ledger_sequence_number=ledger.sequence_number,
        controller_policy_hash=policy.policy_hash,
    )


def _artifact_binding_checks(attempt_root: Path, attempt: Phase7AttemptReport) -> Mapping[str, bool]:
    expected = attempt.artifact_hashes.to_json()
    observed_names = tuple(
        sorted(
            path.name
            for path in attempt_root.iterdir()
            if path.is_file() and path.name != "attempt_report.json"
        )
    )
    expected_names = tuple(sorted(expected))
    attempt_json = _object(attempt_root / "attempt_report.json")
    attempt_content = {key: value for key, value in attempt_json.items() if key != "report_hash"}
    checks: dict[str, bool] = {
        "artifact_name_set_exact": observed_names == expected_names,
        "attempt_report_hash_recomputed": canonical_json_hash(attempt_content) == attempt.report_hash,
    }
    for name, digest in expected.items():
        path = attempt_root / name
        checks[f"artifact_{name}_bound"] = (
            path.is_file() and not path.is_symlink() and sha256_hex(path.read_bytes()) == digest
        )
    return checks


def replay_phase13_store_chain(
    *,
    store_root: Path,
    promotion_evidence_root: Path,
    reference_root: Path,
    closure_report_path: Path,
) -> Sequence[Phase13CheckRecord]:
    store = store_root.resolve(strict=True)
    evidence = promotion_evidence_root.resolve(strict=True)
    reference = reference_root.resolve(strict=True)
    closure_path = closure_report_path.resolve(strict=True)
    policy = _phase13_controller_policy()

    snapshot = load_active_phase7_store(store, policy)
    ledger = _load_ledger(store)
    packages = _load_packages(store, policy)
    attempts = _load_attempts(evidence)
    reference_hashes = _reference_package_hashes(reference)

    sequence_checks: dict[str, bool] = {
        "active_pointer_sequence_six": snapshot.pointer.ledger_sequence_number == 6,
        "all_ledger_entries_present": len(ledger) == 7,
        "event_schedule_exact": tuple(item.event for item in ledger) == _EXPECTED_EVENTS,
        "ledger_sequences_contiguous": tuple(item.sequence_number for item in ledger)
        == tuple(range(7)),
        "policy_hash_bound": all(item.controller_policy_hash == policy.policy_hash for item in ledger),
    }
    for index, entry in enumerate(ledger):
        sequence_checks[f"entry_{index}_previous_hash_bound"] = (
            entry.previous_entry_hash is None
            if index == 0
            else entry.previous_entry_hash == ledger[index - 1].entry_hash
        )
        sequence_checks[f"entry_{index}_active_continuity"] = (
            index == 0 or entry.active_package_hash_before == ledger[index - 1].active_package_hash_after
        )
    records: list[Phase13CheckRecord] = [
        Phase13CheckRecord(
            record_id="store.ledger_chain",
            checks={key: sequence_checks[key] for key in sorted(sequence_checks)},
            evidence_hashes={
                "active_pointer_hash": snapshot.pointer.pointer_hash,
                "controller_policy_hash": policy.policy_hash,
                "ledger_head_hash": snapshot.ledger_head.entry_hash,
            },
        )
    ]

    referenced_package_hashes = {ledger[0].active_package_hash_after}
    referenced_package_hashes.update(
        item.active_package_hash_after for item in ledger if item.event == "promotion"
    )
    records.append(
        Phase13CheckRecord(
            record_id="store.package_set",
            checks={
                "active_package_is_final_promotion": snapshot.pointer.active_package_hash
                == ledger[-1].active_package_hash_after,
                "package_directory_set_exact": set(packages) == referenced_package_hashes,
                "promotion_count_four": sum(item.event == "promotion" for item in ledger) == 4,
                "root_package_count_one": sum(item[1].status == "root" for item in packages.values()) == 1,
            },
            evidence_hashes={
                "active_package_hash": snapshot.pointer.active_package_hash,
                "package_set_hash": canonical_json_hash(sorted(packages)),
            },
        )
    )

    package_label_by_sequence = {0: "M0", 2: "M1", 4: "M2", 5: "M3", 6: "M4"}
    for sequence, label in package_label_by_sequence.items():
        entry = ledger[sequence]
        package_hash = entry.active_package_hash_after
        package_root, manifest = packages[package_hash]
        embedded_root = package_root / "predecessor/payload" / EMBEDDED_PHASE12_ROOT
        installed = load_package_manifest(embedded_root)
        expected_parent = None if sequence == 0 else entry.active_package_hash_before
        expected_components = _EXPECTED_COMPONENTS[sequence]
        checks = {
            "embedded_semantic_package_bound": installed.package_hash == reference_hashes[label],
            "immutable_package_verified": True,
            "manifest_parent_bound": manifest.parent_package_hash == expected_parent,
            "status_bound": manifest.status == ("root" if sequence == 0 else "promoted"),
            "substantive_components_exact": tuple(manifest.substantive_component_kinds)
            == expected_components,
        }
        if sequence > 0:
            checks["accepted_attempt_bound"] = manifest.accepted_attempt_report_hash == entry.attempt_report_hash
            checks["external_and_immutable_evidence_equal"] = (
                entry.attempt_report_hash in attempts
                and _tree_hash(attempts[entry.attempt_report_hash][0])
                == _tree_hash(package_root / "evidence")
            )
        records.append(
            Phase13CheckRecord(
                record_id=f"store.package.{label}",
                checks={key: checks[key] for key in sorted(checks)},
                evidence_hashes={
                    "immutable_package_hash": manifest.package_hash,
                    "installed_semantic_package_hash": installed.package_hash,
                    "reference_semantic_package_hash": reference_hashes[label],
                },
            )
        )

    nonbootstrap = tuple(item for item in ledger if item.event != "bootstrap")
    records.append(
        Phase13CheckRecord(
            record_id="store.attempt_set",
            checks={
                "attempt_count_six": len(attempts) == 6,
                "ledger_attempt_set_exact": set(attempts)
                == {item.attempt_report_hash for item in nonbootstrap},
            },
            evidence_hashes={
                "attempt_set_hash": canonical_json_hash(sorted(attempts)),
                "ledger_attempt_set_hash": canonical_json_hash(
                    sorted(item.attempt_report_hash for item in nonbootstrap)
                ),
            },
        )
    )

    for entry in nonbootstrap:
        if entry.attempt_report_hash is None:
            raise SchemaValidationError("phase13.store.attempt", "missing attempt hash")
        attempt_root, attempt = attempts[entry.attempt_report_hash]
        prior = ledger[entry.sequence_number - 1]
        prior_package = packages[entry.active_package_hash_before]
        prior_pointer = _pointer_for_ledger_state(prior_package, prior, policy)
        artifact_checks = dict(_artifact_binding_checks(attempt_root, attempt))
        artifact_checks.update(
            {
                "active_pointer_before_bound": attempt.active_pointer_hash_before
                == prior_pointer.pointer_hash,
                "active_pointer_unchanged_during_attempt": attempt.active_pointer_hash_after
                == prior_pointer.pointer_hash,
                "attempt_hash_bound_to_ledger": attempt.report_hash == entry.attempt_report_hash,
                "manual_repair_zero": attempt.manual_repair_count == 0,
                "run_id_bound": attempt.run_id == entry.run_id,
                "transition_id_bound": attempt.transition_id
                == _EXPECTED_TRANSITIONS[entry.sequence_number],
                "verdict_matches_event": (
                    attempt.verdict == "accept"
                    if entry.event == "promotion"
                    else attempt.verdict == "reject"
                ),
            }
        )
        if entry.event == "rejection":
            artifact_checks.update(
                {
                    "ledger_reason_codes_bound": tuple(reason.value for reason in entry.reason_codes)
                    == _EXPECTED_REASONS[entry.sequence_number],
                    "attempt_reason_codes_bound": tuple(reason.value for reason in attempt.reason_codes)
                    == _EXPECTED_REASONS[entry.sequence_number],
                    "rejection_preserved_active_package": entry.active_package_hash_before
                    == entry.active_package_hash_after,
                }
            )
        else:
            promoted_root, promoted_manifest = packages[entry.active_package_hash_after]
            artifact_checks.update(
                {
                    "accepted_attempt_copied_to_immutable_package": _tree_hash(attempt_root)
                    == _tree_hash(promoted_root / "evidence"),
                    "candidate_tree_bound_to_immutable_manifest": attempt.candidate_package_tree_hash
                    == promoted_manifest.source_candidate_package_tree_hash,
                    "promotion_changed_active_package": entry.active_package_hash_before
                    != entry.active_package_hash_after,
                }
            )
        records.append(
            Phase13CheckRecord(
                record_id=f"store.attempt.{entry.sequence_number:02d}",
                checks={key: artifact_checks[key] for key in sorted(artifact_checks)},
                evidence_hashes={
                    "attempt_report_hash": attempt.report_hash,
                    "ledger_entry_hash": entry.entry_hash,
                    "prior_pointer_hash": prior_pointer.pointer_hash,
                },
            )
        )

    closure = _object(closure_path)
    closure_content = {key: value for key, value in closure.items() if key != "report_hash"}
    retained_closure = _object(evidence / "phase12_complete_closure.json")
    final_promotion = _object(evidence / "phase12e/phase12e_promotion_report.json")
    closure_checks = {
        "closure_accepted": closure.get("accepted") is True,
        "closure_bytes_match_retained_evidence": closure_content == retained_closure,
        "closure_report_hash_bound": closure.get("report_hash")
        == canonical_json_hash(closure_content),
        "final_ledger_hash_bound": final_promotion.get("promotion_ledger_hash")
        == ledger[-1].entry_hash,
        "final_package_hash_bound": final_promotion.get("promoted_package_hash")
        == snapshot.pointer.active_package_hash,
        "phase12_exit_closed": closure.get("phase12_exit_closed") is True,
        "reference_hash_bound": closure.get("reference_hash")
        == canonical_json_hash(_object(reference / "retained/reference.json")),
    }
    records.append(
        Phase13CheckRecord(
            record_id="store.phase12_closure_binding",
            checks={key: closure_checks[key] for key in sorted(closure_checks)},
            evidence_hashes={
                "closure_report_hash": str(closure["report_hash"]),
                "final_ledger_hash": ledger[-1].entry_hash,
                "final_package_hash": snapshot.pointer.active_package_hash,
            },
        )
    )

    result = tuple(sorted(records, key=lambda item: item.record_id.encode("utf-8")))
    if not all(item.accepted for item in result):
        failed = [f"{item.record_id}: {', '.join(key for key, ok in item.checks.items() if not ok)}" for item in result if not item.accepted]
        raise ValueError(f"Phase 13 store-chain replay failed: {'; '.join(failed)}")
    return result


__all__ = ["replay_phase13_store_chain"]
