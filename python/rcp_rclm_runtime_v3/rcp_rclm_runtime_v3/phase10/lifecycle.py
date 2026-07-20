from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.checker.reference import canonical_rclm_update
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord
from rcp_rclm_runtime.successor.package_builder import (
    Phase6PackageBuildEvidence,
    build_candidate_package,
    verify_candidate_package,
)
from rcp_rclm_runtime.successor.record_budget import Phase6ResourceBudgetRecord
from rcp_rclm_runtime.successor.record_operation import SelectedFileOperationRecord
from rcp_rclm_runtime.successor.record_predecessor import Phase6PredecessorManifestRecord
from rcp_rclm_runtime.successor.record_selection import Phase6SelectionRecord
from rcp_rclm_runtime.successor.reference import build_reference_predecessor_package
from rcp_rclm_runtime.successor.workspace import (
    LoadedPredecessorPackage,
    load_predecessor_package,
    measure_payload_tree,
    write_canonical_json,
)
from rcp_rclm_runtime_v3.contract.certificate import HeldoutAccessPolicy, LearnedCertificatePacket
from rcp_rclm_runtime_v3.contract.state import LearnedRCLMState
from rcp_rclm_runtime_v3.contract.update import LearnedRCLMUpdate
from rcp_rclm_runtime_v3.contract.validation import (
    Phase9TransitionReport,
    validate_phase9_transition,
)
from rcp_rclm_runtime_v3.phase10.information import build_information_report
from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    LEARNED_CHAIN,
    PROTECTED_CHAIN,
    PROTECTED_TASK,
)
from rcp_rclm_runtime_v3.phase10.learned_package import validate_learned_package
from rcp_rclm_runtime_v3.phase10.learned_reference import (
    Phase10LearnedReference,
    build_phase10_learned_reference,
)
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import decode_completion

EMBEDDED_PHASE10_ROOT: Final[str] = "model/weights/phase10_package"
PHASE10_PHASE6_POLICY_ID: Final[str] = "rcp-rclm-phase10-learned-host-selector-v1"
PHASE10_PHASE6_SCHEMA_ID: Final[str] = "runtime.v3.phase10.phase6_fixture.v1"
PHASE10_REPLAY_SCHEMA_ID: Final[str] = "runtime.v3.phase10.phase6_replay.v1"


def phase10_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=512,
        max_total_bytes=134_217_728,
        max_changed_files=128,
        max_written_bytes=100_663_296,
        max_commands=256,
        max_snapshot_bytes=67_108_864,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _regular_file_map(root: Path) -> dict[str, Path]:
    resolved = root.resolve(strict=True)
    result: dict[str, Path] = {}
    for path in resolved.rglob("*"):
        if path.is_symlink():
            raise SchemaValidationError("phase10.lifecycle", "symlinks are forbidden")
        if path.is_file():
            relative = path.relative_to(resolved).as_posix()
            result[relative] = path
    return result


def _build_wrapper_predecessor(
    phase10_predecessor_root: Path,
    output_root: Path,
) -> LoadedPredecessorPackage:
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"Phase 6 wrapper already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase10-wrapper-",
        dir=resolved_output.parent,
    ) as temporary:
        package_root = build_reference_predecessor_package(
            generator_input,
            Path(temporary) / "wrapper",
        )
        embedded = package_root / "payload" / EMBEDDED_PHASE10_ROOT
        embedded.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            phase10_predecessor_root.resolve(strict=True),
            embedded,
            symlinks=False,
        )
        manifest_value = load_json_strict(
            (package_root / "manifest.json").read_bytes(),
            require_canonical=True,
        )
        base_manifest = Phase6PredecessorManifestRecord.from_json(manifest_value)
        measurement = measure_payload_tree(package_root / "payload")
        updated = Phase6PredecessorManifestRecord(
            package_id="phase10.learned.wrapper.predecessor",
            phase5_manifest_hash=base_manifest.phase5_manifest_hash,
            payload_tree_hash=measurement.tree_hash,
            state_path=base_manifest.state_path,
            state_hash=base_manifest.state_hash,
            file_count=measurement.file_count,
            total_bytes=measurement.total_bytes,
        )
        write_canonical_json(package_root / "manifest.json", updated.to_json())
        loaded = load_predecessor_package(package_root)
        if loaded.manifest != updated:
            raise ValueError("reopened Phase 10 wrapper manifest differs")
        os.replace(package_root, resolved_output)
    return load_predecessor_package(resolved_output)


def _build_phase6_selection(
    predecessor: LoadedPredecessorPackage,
    phase10_predecessor_root: Path,
    phase10_candidate_root: Path,
    reference: Phase10LearnedReference,
) -> Phase6SelectionRecord:
    before_files = _regular_file_map(phase10_predecessor_root)
    after_files = _regular_file_map(phase10_candidate_root)
    if set(before_files) != set(after_files):
        raise SchemaValidationError(
            "phase10.lifecycle.file_set",
            "selected Phase 10 successor must retain the canonical package file set",
        )
    wrapper_record_by_path = {
        record.path: record for record in predecessor.measurement.records
    }
    operations: list[SelectedFileOperationRecord] = []
    for relative in sorted(after_files, key=lambda item: item.encode("utf-8")):
        before_content = before_files[relative].read_bytes()
        after_content = after_files[relative].read_bytes()
        if before_content == after_content:
            continue
        wrapper_path = f"{EMBEDDED_PHASE10_ROOT}/{relative}"
        before_record = wrapper_record_by_path.get(wrapper_path)
        if before_record is None:
            raise SchemaValidationError(
                "phase10.lifecycle.selection",
                f"wrapper predecessor is missing {wrapper_path}",
            )
        operations.append(
            SelectedFileOperationRecord.write(
                path=wrapper_path,
                component_kind="model_weights",
                expected_before_hash=before_record.sha256,
                expected_before_mode=before_record.mode,
                after_mode="0644",
                content=after_content,
            )
        )
    if not operations:
        raise SchemaValidationError(
            "phase10.lifecycle.selection",
            "learned successor must change at least one model-package file",
        )
    proposal_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase10.phase6_proposal.v1",
            "transition_id": reference.update.transition_id,
            "predecessor_package_hash": reference.predecessor_manifest.package_hash,
            "candidate_package_hash": reference.candidate_manifest.package_hash,
            "successor_request_hash": reference.successor_request.request_hash,
            "candidate_model_identity_hash": (
                reference.candidate_manifest.model_identity_hash
            ),
            "heldout_material_consumed": False,
        }
    )
    logical_update = canonical_rclm_update(ClassicalBinaryUpdateRecord("stay"))
    update_json = logical_update.to_json()
    return Phase6SelectionRecord(
        transition_id=reference.update.transition_id,
        proposal_hash=proposal_hash,
        generator_request_hash=reference.successor_request.request_hash,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=(
            predecessor.manifest.phase5_manifest_hash
        ),
        selection_policy_id=PHASE10_PHASE6_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=("model_weights",),
    )


def _candidate_transition_pairs() -> Sequence[tuple[int, int]]:
    return tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN}))


def _bind_lifecycle_certificate(
    reference: Phase10LearnedReference,
    phase6: Phase6PackageBuildEvidence,
    candidate_report: Mapping[str, object],
) -> tuple[LearnedCertificatePacket, Phase9TransitionReport]:
    realization = phase6.report.realization
    if realization is None or not realization.rollback.verified:
        return reference.certificate, reference.transition_report
    certificate = replace(
        reference.certificate,
        architecture_compatibility_hash=str(candidate_report["report_hash"]),
        resource_evidence_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v3.phase10.lifecycle_resource_evidence.v1",
                "successor_training_semantic_hash": (
                    reference.successor_training_semantic_hash
                ),
                "phase6_usage_hash": realization.resources.usage_hash,
                "phase6_environment_hash": realization.environment.environment_hash,
                "changed_file_count": len(realization.changes),
                "rollback_hash": realization.rollback.rollback_hash,
            }
        ),
        rollback_evidence_hash=realization.rollback.rollback_hash,
    )
    transition = validate_phase9_transition(
        reference.predecessor_state,
        reference.update,
        reference.candidate_state,
        certificate,
        reference.heldout_policy,
    )
    return certificate, transition


@dataclass(frozen=True, slots=True)
class Phase10Phase6Fixture:
    root: Path
    reference: Phase10LearnedReference
    wrapper_predecessor: LoadedPredecessorPackage
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence
    embedded_predecessor_report: Mapping[str, object]
    embedded_candidate_report: Mapping[str, object]
    lifecycle_certificate: LearnedCertificatePacket
    lifecycle_transition: Phase9TransitionReport

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 6 candidate is unavailable")
        return self.phase6.output_root

    @property
    def embedded_predecessor_root(self) -> Path:
        return self.wrapper_predecessor.payload_root / EMBEDDED_PHASE10_ROOT

    @property
    def embedded_candidate_root(self) -> Path:
        return self.candidate_root / "payload" / EMBEDDED_PHASE10_ROOT

    @property
    def accepted(self) -> bool:
        rollback_verified = bool(
            self.phase6.report.realization
            and self.phase6.report.realization.rollback.verified
        )
        if not self.phase6.report.built or self.phase6.output_root is None:
            return False
        observed_candidate = load_package_manifest(self.embedded_candidate_root)
        return (
            self.reference.accepted
            and self.embedded_predecessor_report["accepted"] is True
            and self.embedded_candidate_report["accepted"] is True
            and rollback_verified
            and self.lifecycle_transition.accepted
            and self.lifecycle_certificate.rollback_evidence_hash
            == self.phase6.report.realization.rollback.rollback_hash
            and observed_candidate.package_hash
            == self.reference.candidate_manifest.package_hash
            and observed_candidate.model_identity_hash
            == self.reference.candidate_manifest.model_identity_hash
        )

    def to_json(self) -> dict[str, object]:
        realization = self.phase6.report.realization
        content = {
            "schema_id": PHASE10_PHASE6_SCHEMA_ID,
            "accepted": self.accepted,
            "reference_hash": self.reference.reference_hash,
            "predecessor_wrapper_manifest_hash": (
                self.wrapper_predecessor.manifest.manifest_hash
            ),
            "selection_hash": self.selection.selection_hash,
            "phase6_report_hash": self.phase6.report.report_hash,
            "lifecycle_certificate_hash": self.lifecycle_certificate.certificate_hash,
            "lifecycle_transition_report_hash": (
                self.lifecycle_transition.semantic_report_hash
            ),
            "lifecycle_transition_accepted": self.lifecycle_transition.accepted,
            "phase6_candidate_manifest_hash": (
                None
                if self.phase6.report.candidate_manifest is None
                else self.phase6.report.candidate_manifest.manifest_hash
            ),
            "predecessor_model_identity_hash": (
                self.reference.predecessor_manifest.model_identity_hash
            ),
            "candidate_model_identity_hash": (
                self.reference.candidate_manifest.model_identity_hash
            ),
            "embedded_predecessor_report_hash": self.embedded_predecessor_report[
                "report_hash"
            ],
            "embedded_candidate_report_hash": self.embedded_candidate_report[
                "report_hash"
            ],
            "rollback_verified": bool(
                realization and realization.rollback.verified
            ),
            "rollback_hash": (
                None if realization is None else realization.rollback.rollback_hash
            ),
            "changed_file_count": (
                0 if realization is None else len(realization.changes)
            ),
            "substantive_component_kinds": ["model_weights"],
        }
        value = dict(content)
        value["fixture_hash"] = canonical_json_hash(content)
        return value


def build_phase10_phase6_fixture(output_root: Path) -> Phase10Phase6Fixture:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 10 lifecycle root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    reference_root = root / "semantic_reference"
    reference = build_phase10_learned_reference(reference_root)
    phase10_predecessor_root = reference_root / "predecessor"
    phase10_candidate_root = reference_root / "candidate"
    wrapper = _build_wrapper_predecessor(
        phase10_predecessor_root,
        root / "wrapper_predecessor",
    )
    selection = _build_phase6_selection(
        wrapper,
        phase10_predecessor_root,
        phase10_candidate_root,
        reference,
    )
    phase6 = build_candidate_package(
        wrapper.payload_root.parent,
        selection,
        phase10_phase6_budget(),
        root / "phase6_candidate",
    )
    embedded_predecessor_report = validate_learned_package(
        wrapper.payload_root / EMBEDDED_PHASE10_ROOT,
        PROTECTED_CHAIN,
    )
    if phase6.output_root is None:
        embedded_candidate_report: Mapping[str, object] = {
            "accepted": False,
            "report_hash": canonical_json_hash(
                {"phase10_phase6": "candidate_unavailable"}
            ),
        }
    else:
        verify_candidate_package(phase6.output_root)
        embedded_candidate_report = validate_learned_package(
            phase6.output_root / "payload" / EMBEDDED_PHASE10_ROOT,
            _candidate_transition_pairs(),
        )
    lifecycle_certificate, lifecycle_transition = _bind_lifecycle_certificate(
        reference,
        phase6,
        embedded_candidate_report,
    )
    fixture = Phase10Phase6Fixture(
        root=root,
        reference=reference,
        wrapper_predecessor=wrapper,
        selection=selection,
        phase6=phase6,
        embedded_predecessor_report=embedded_predecessor_report,
        embedded_candidate_report=embedded_candidate_report,
        lifecycle_certificate=lifecycle_certificate,
        lifecycle_transition=lifecycle_transition,
    )
    evidence_root = root / "retained"
    _write_json(evidence_root / "reference.json", reference.to_json())
    _write_json(evidence_root / "selection.json", selection.to_json())
    _write_json(evidence_root / "phase6_report.json", phase6.report.to_json())
    _write_json(
        evidence_root / "lifecycle_certificate.json",
        lifecycle_certificate.to_json(),
    )
    _write_json(
        evidence_root / "lifecycle_transition.json",
        lifecycle_transition.to_json(),
    )
    _write_json(evidence_root / "fixture.json", fixture.to_json())
    if not fixture.accepted:
        raise ValueError("Phase 10 Phase 6 fixture did not satisfy its exit conditions")
    return fixture


def replay_phase10_phase6(
    fixture_root: Path,
    output_root: Path,
) -> dict[str, object]:
    source = fixture_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 10 replay output already exists: {output}")
    retained = source / "retained"
    reference_value = load_json_strict(
        (retained / "reference.json").read_bytes(), require_canonical=True
    )
    if not isinstance(reference_value, dict):
        raise SchemaValidationError("phase10.replay.reference", "expected an object")
    selection = Phase6SelectionRecord.from_json(
        load_json_strict(
            (retained / "selection.json").read_bytes(), require_canonical=True
        )
    )
    predecessor_root = source / "wrapper_predecessor"
    predecessor = load_predecessor_package(predecessor_root)
    before_modules = frozenset(sys.modules)
    phase6 = build_candidate_package(
        predecessor_root,
        selection,
        phase10_phase6_budget(),
        output,
    )
    if phase6.output_root is None or not phase6.report.built:
        raise ValueError("Phase 10 replay realization failed")
    verify_candidate_package(phase6.output_root)
    embedded_predecessor = predecessor.payload_root / EMBEDDED_PHASE10_ROOT
    embedded_candidate = phase6.output_root / "payload" / EMBEDDED_PHASE10_ROOT
    predecessor_package_report = validate_learned_package(
        embedded_predecessor,
        PROTECTED_CHAIN,
    )
    candidate_package_report = validate_learned_package(
        embedded_candidate,
        _candidate_transition_pairs(),
    )
    candidate_manifest = load_package_manifest(embedded_candidate)
    expected_candidate_manifest = reference_value["candidate_manifest"]
    if not isinstance(expected_candidate_manifest, dict):
        raise SchemaValidationError(
            "phase10.replay.candidate_manifest", "expected an object"
        )
    expected_candidate_hash = expected_candidate_manifest["package_hash"]
    expected_model_hash = expected_candidate_manifest["model_identity_hash"]

    predecessor_protected = decode_completion(
        embedded_predecessor, PROTECTED_TASK.model_prompt
    )
    candidate_protected = decode_completion(
        embedded_candidate, PROTECTED_TASK.model_prompt
    )
    predecessor_heldout = decode_completion(
        embedded_predecessor, HELDOUT_TASK.model_prompt
    )
    candidate_heldout = decode_completion(
        embedded_candidate, HELDOUT_TASK.model_prompt
    )
    information = build_information_report(
        embedded_predecessor,
        embedded_candidate,
        PROTECTED_TASK,
        HELDOUT_TASK,
    )
    predecessor_state = LearnedRCLMState.from_json(
        reference_value["predecessor_state"]
    )
    candidate_state = LearnedRCLMState.from_json(reference_value["candidate_state"])
    update = LearnedRCLMUpdate.from_json(reference_value["update"])
    certificate = LearnedCertificatePacket.from_json(
        load_json_strict(
            (retained / "lifecycle_certificate.json").read_bytes(),
            require_canonical=True,
        )
    )
    heldout_policy = HeldoutAccessPolicy.from_json(reference_value["heldout_policy"])
    transition = validate_phase9_transition(
        predecessor_state,
        update,
        candidate_state,
        certificate,
        heldout_policy,
    )
    after_modules = frozenset(sys.modules)
    newly_loaded = sorted(after_modules - before_modules)
    forbidden_loaded = [
        name
        for name in newly_loaded
        if name == "torch"
        or name.startswith("torch.")
        or name.endswith("training_process")
        or name.endswith("phase10_training_worker")
    ]
    realization = phase6.report.realization
    checks = {
        "phase6_realization_accepts": phase6.report.built,
        "rollback_verified": bool(realization and realization.rollback.verified),
        "rollback_evidence_recomputed": bool(
            realization
            and certificate.rollback_evidence_hash
            == realization.rollback.rollback_hash
        ),
        "predecessor_package_accepts": predecessor_package_report["accepted"] is True,
        "candidate_package_accepts": candidate_package_report["accepted"] is True,
        "candidate_package_hash_matches": candidate_manifest.package_hash
        == expected_candidate_hash,
        "candidate_model_hash_matches": candidate_manifest.model_identity_hash
        == expected_model_hash,
        "protected_predecessor_decodes": predecessor_protected.completion_text
        == PROTECTED_TASK.expected_completion,
        "protected_candidate_retains": candidate_protected.completion_text
        == PROTECTED_TASK.expected_completion,
        "heldout_predecessor_unsolved": predecessor_heldout.completion_text
        != HELDOUT_TASK.expected_completion,
        "heldout_candidate_solves": candidate_heldout.completion_text
        == HELDOUT_TASK.expected_completion,
        "information_accepts": information.accepted,
        "phase9_gate_d_transition_accepts": transition.accepted,
        "forbidden_training_modules_absent": not forbidden_loaded,
    }
    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    content = {
        "schema_id": PHASE10_REPLAY_SCHEMA_ID,
        "checks": checks,
        "failures": failures,
        "training_invocations": 0,
        "generator_invocations": 0,
        "forbidden_learned_modules_loaded": forbidden_loaded,
        "phase6_report_hash": phase6.report.report_hash,
        "candidate_package_hash": candidate_manifest.package_hash,
        "candidate_model_identity_hash": candidate_manifest.model_identity_hash,
        "information_report_hash": information.report_hash,
        "lifecycle_certificate_hash": certificate.certificate_hash,
        "phase9_transition_report_hash": transition.semantic_report_hash,
        "ok": not failures,
    }
    report = dict(content)
    report["report_hash"] = canonical_json_hash(content)
    _write_json(output.parent / f"{output.name}-replay-report.json", report)
    if failures:
        raise ValueError(f"Phase 10 replay failed: {', '.join(failures)}")
    return report


__all__ = [
    "EMBEDDED_PHASE10_ROOT",
    "Phase10Phase6Fixture",
    "build_phase10_phase6_fixture",
    "phase10_phase6_budget",
    "replay_phase10_phase6",
]
