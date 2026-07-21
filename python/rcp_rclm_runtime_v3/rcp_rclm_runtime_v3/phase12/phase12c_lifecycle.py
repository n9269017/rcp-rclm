from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
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
from rcp_rclm_runtime.successor.policies import (
    MEMORY_POLICY_PATH,
    RETRIEVAL_POLICY_PATH,
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

from rcp_rclm_runtime_v3.contract.certificate import LearnedCertificatePacket
from rcp_rclm_runtime_v3.contract.validation import (
    Phase9TransitionReport,
    validate_phase9_transition,
)
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import (
    EMBEDDED_PHASE12_ROOT,
    Phase12BReference,
    build_phase12b_reference,
)
from rcp_rclm_runtime_v3.phase12.phase12c_candidate import (
    Phase12CCandidateFixture,
    build_phase12c_candidate_fixture,
    validate_phase12c_candidate_package,
)
from rcp_rclm_runtime_v3.phase12.phase12c_program import (
    Phase12CProposalReport,
    Phase12CProposalValidationReport,
    generate_phase12c_proposal,
    validate_phase12c_proposal,
)
from rcp_rclm_runtime_v3.phase12.records import Phase12ProgressLedger

GENERATOR_PROJECTION_PATH: Final[str] = "policies/code_generation_policy.json"
PLANNER_PROJECTION_PATH: Final[str] = "policies/planning_policy.json"
TRAINING_PROJECTION_PATH: Final[str] = "policies/training_policy.json"
PHASE12C_PHASE6_POLICY_ID: Final[str] = "rcp-rclm-phase12c-memory-retrieval-selector-v1"


def phase12c_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=768,
        max_total_bytes=201_326_592,
        max_changed_files=192,
        max_written_bytes=150_994_944,
        max_commands=384,
        max_snapshot_bytes=100_663_296,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _regular_file_map(root: Path) -> dict[str, Path]:
    resolved = root.resolve(strict=True)
    result: dict[str, Path] = {}
    for path in resolved.rglob("*"):
        if path.is_symlink():
            raise SchemaValidationError("phase12c.lifecycle", "symlinks are forbidden")
        if path.is_file():
            result[path.relative_to(resolved).as_posix()] = path
    return result


def _policy_projection(package_root: Path, relative: str) -> object:
    return load_json_strict(
        (package_root.resolve(strict=True) / relative).read_bytes(),
        require_canonical=True,
    )


def _training_projection(package_root: Path) -> dict[str, object]:
    manifest = load_package_manifest(package_root.resolve(strict=True))
    return {
        "schema_id": "runtime.v3.phase12c.phase6_training_projection.v1",
        "data_curriculum_hash": manifest.data_curriculum_hash,
        "training_policy_hash": manifest.training_policy_hash,
        "optimizer_state_hash": manifest.optimizer_state_hash,
        "training_steps_for_transition": 0,
        "candidate_self_report_authoritative": False,
    }


def _build_wrapper_predecessor(
    phase12b: Phase12BReference,
    output_root: Path,
) -> LoadedPredecessorPackage:
    active_root = phase12b.semantic_candidate.root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"Phase 12C wrapper already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase12c-wrapper-",
        dir=resolved_output.parent,
    ) as temporary:
        package_root = build_reference_predecessor_package(
            generator_input,
            Path(temporary) / "wrapper",
        )
        payload = package_root / "payload"
        embedded = payload / EMBEDDED_PHASE12_ROOT
        embedded.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(active_root, embedded, symlinks=False)
        _write_json(
            payload / GENERATOR_PROJECTION_PATH,
            _policy_projection(active_root, "policies/generator_policy.json"),
        )
        _write_json(
            payload / PLANNER_PROJECTION_PATH,
            _policy_projection(active_root, "policies/planner_policy.json"),
        )
        _write_json(payload / TRAINING_PROJECTION_PATH, _training_projection(active_root))
        _write_json(
            payload / MEMORY_POLICY_PATH,
            _policy_projection(active_root, "memory/memory_manifest.json"),
        )
        _write_json(
            payload / RETRIEVAL_POLICY_PATH,
            _policy_projection(active_root, "retrieval/index_manifest.json"),
        )
        manifest_value = load_json_strict(
            (package_root / "manifest.json").read_bytes(),
            require_canonical=True,
        )
        base_manifest = Phase6PredecessorManifestRecord.from_json(manifest_value)
        measurement = measure_payload_tree(payload)
        updated = Phase6PredecessorManifestRecord(
            package_id="phase12.m1.wrapper.predecessor",
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
            raise ValueError("reopened Phase 12C wrapper manifest differs")
        os.replace(package_root, resolved_output)
    return load_predecessor_package(resolved_output)


def _build_selection(
    predecessor: LoadedPredecessorPackage,
    phase12b: Phase12BReference,
    candidate: Phase12CCandidateFixture,
) -> Phase6SelectionRecord:
    active_root = phase12b.semantic_candidate.root.resolve(strict=True)
    before_files = _regular_file_map(active_root)
    after_files = _regular_file_map(candidate.root)
    if set(before_files) != set(after_files):
        raise SchemaValidationError(
            "phase12c.lifecycle.file_set",
            "memory/retrieval successor must retain the canonical package file set",
        )
    record_by_path = {record.path: record for record in predecessor.measurement.records}
    operations: list[SelectedFileOperationRecord] = []
    for relative in sorted(after_files, key=lambda item: item.encode("utf-8")):
        before_content = before_files[relative].read_bytes()
        after_content = after_files[relative].read_bytes()
        if before_content == after_content:
            continue
        wrapper_path = f"{EMBEDDED_PHASE12_ROOT}/{relative}"
        before_record = record_by_path.get(wrapper_path)
        if before_record is None:
            raise SchemaValidationError(
                "phase12c.lifecycle.selection",
                f"wrapper predecessor is missing {wrapper_path}",
            )
        operations.append(
            SelectedFileOperationRecord.write(
                path=wrapper_path,
                component_kind=None,
                expected_before_hash=before_record.sha256,
                expected_before_mode=before_record.mode,
                after_mode="0644",
                content=after_content,
            )
        )

    projection_changes = (
        (
            MEMORY_POLICY_PATH,
            "memory_policy",
            candidate.root / "memory/memory_manifest.json",
        ),
        (
            RETRIEVAL_POLICY_PATH,
            "retrieval_policy",
            candidate.root / "retrieval/index_manifest.json",
        ),
    )
    for wrapper_path, component_kind, source_path in projection_changes:
        before_record = record_by_path.get(wrapper_path)
        if before_record is None:
            raise SchemaValidationError(
                "phase12c.lifecycle.selection",
                f"wrapper predecessor is missing {wrapper_path}",
            )
        operations.append(
            SelectedFileOperationRecord.write(
                path=wrapper_path,
                component_kind=component_kind,
                expected_before_hash=before_record.sha256,
                expected_before_mode=before_record.mode,
                after_mode="0644",
                content=source_path.read_bytes(),
            )
        )

    operations.sort(key=lambda item: item.path.encode("utf-8"))
    proposal_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12c.phase6_proposal.v1",
            "transition_id": candidate.proposal.generator_input.transition_id,
            "generator_input_hash": candidate.proposal.generator_input.input_hash,
            "proposal_hash": candidate.proposal.report_hash,
            "program_hash": candidate.proposal.program.program_hash,
            "program_validation_hash": candidate.validation.report_hash,
            "active_package_hash": phase12b.semantic_candidate.manifest.package_hash,
            "candidate_package_hash": candidate.manifest.package_hash,
            "memory_manifest_hash": candidate.manifest.memory_manifest_hash,
            "retrieval_manifest_hash": candidate.manifest.retrieval_index_hash,
            "heldout_material_consumed": False,
            "manual_repair_count": 0,
        }
    )
    logical_update = canonical_rclm_update(ClassicalBinaryUpdateRecord("stay"))
    update_json = logical_update.to_json()
    return Phase6SelectionRecord(
        transition_id=candidate.update.transition_id,
        proposal_hash=proposal_hash,
        generator_request_hash=candidate.proposal.generator_input.input_hash,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=predecessor.manifest.phase5_manifest_hash,
        selection_policy_id=PHASE12C_PHASE6_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=("memory_policy", "retrieval_policy"),
    )


@dataclass(frozen=True, slots=True)
class Phase12CPhase6Evidence:
    candidate: Phase12CCandidateFixture
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence
    embedded_report: Mapping[str, object]
    memory_projection_matches: bool
    retrieval_projection_matches: bool

    schema_id: ClassVar[str] = "runtime.v3.phase12c.phase6_evidence.v1"

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 12C Phase 6 candidate is unavailable")
        return self.phase6.output_root

    @property
    def embedded_candidate_root(self) -> Path:
        return self.candidate_root / "payload" / EMBEDDED_PHASE12_ROOT

    @property
    def accepted(self) -> bool:
        realization = self.phase6.report.realization
        if not self.phase6.report.built or self.phase6.output_root is None or realization is None:
            return False
        manifest = load_package_manifest(self.embedded_candidate_root)
        return (
            self.embedded_report["accepted"] is True
            and realization.rollback.verified
            and manifest.package_hash == self.candidate.manifest.package_hash
            and manifest.model_identity_hash == self.candidate.manifest.model_identity_hash
            and self.memory_projection_matches
            and self.retrieval_projection_matches
        )

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        realization = self.phase6.report.realization
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "candidate_fixture_hash": self.candidate.fixture_hash,
            "selection": self.selection.to_json(),
            "phase6_report": self.phase6.report.to_json(),
            "embedded_report": dict(self.embedded_report),
            "memory_projection_matches": self.memory_projection_matches,
            "retrieval_projection_matches": self.retrieval_projection_matches,
            "rollback_verified": bool(realization and realization.rollback.verified),
            "rollback_hash": None if realization is None else realization.rollback.rollback_hash,
            "changed_file_count": 0 if realization is None else len(realization.changes),
        }


def _realize_candidate(
    wrapper: LoadedPredecessorPackage,
    phase12b: Phase12BReference,
    candidate: Phase12CCandidateFixture,
    output_root: Path,
) -> Phase12CPhase6Evidence:
    selection = _build_selection(wrapper, phase12b, candidate)
    phase6 = build_candidate_package(
        wrapper.payload_root.parent,
        selection,
        phase12c_phase6_budget(),
        output_root,
    )
    if phase6.output_root is None:
        embedded_report: Mapping[str, object] = {
            "accepted": False,
            "report_hash": canonical_json_hash({"phase12c_phase6": "candidate_unavailable"}),
        }
        memory_projection_matches = False
        retrieval_projection_matches = False
    else:
        verify_candidate_package(phase6.output_root)
        embedded_root = phase6.output_root / "payload" / EMBEDDED_PHASE12_ROOT
        embedded_report = validate_phase12c_candidate_package(
            phase12b,
            candidate.proposal,
            embedded_root,
        )
        memory_projection_matches = (
            phase6.output_root / "payload" / MEMORY_POLICY_PATH
        ).read_bytes() == (embedded_root / "memory/memory_manifest.json").read_bytes()
        retrieval_projection_matches = (
            phase6.output_root / "payload" / RETRIEVAL_POLICY_PATH
        ).read_bytes() == (embedded_root / "retrieval/index_manifest.json").read_bytes()
    evidence = Phase12CPhase6Evidence(
        candidate=candidate,
        selection=selection,
        phase6=phase6,
        embedded_report=embedded_report,
        memory_projection_matches=memory_projection_matches,
        retrieval_projection_matches=retrieval_projection_matches,
    )
    if not evidence.accepted:
        raise ValueError("Phase 12C realization did not validate")
    return evidence


@dataclass(frozen=True, slots=True)
class Phase12CReference:
    root: Path
    phase12b: Phase12BReference
    invalid_proposal: Phase12CProposalReport
    invalid_proposal_replay: Phase12CProposalReport
    invalid_validation: Phase12CProposalValidationReport
    proposal: Phase12CProposalReport
    proposal_replay: Phase12CProposalReport
    validation: Phase12CProposalValidationReport
    semantic_candidate: Phase12CCandidateFixture
    wrapper_predecessor: LoadedPredecessorPackage
    phase6: Phase12CPhase6Evidence
    lifecycle_certificate: LearnedCertificatePacket
    lifecycle_transition: Phase9TransitionReport
    ledger: Phase12ProgressLedger

    schema_id: ClassVar[str] = "runtime.v3.phase12c.reference.v1"

    @property
    def deterministic_replays(self) -> bool:
        return (
            self.invalid_proposal.to_json() == self.invalid_proposal_replay.to_json()
            and self.proposal.to_json() == self.proposal_replay.to_json()
        )

    @property
    def accepted(self) -> bool:
        return (
            self.phase12b.accepted
            and self.invalid_proposal.package_generated
            and self.deterministic_replays
            and not self.invalid_validation.accepted
            and tuple(self.invalid_validation.reason_codes)
            == ("PHASE12C_COMPONENT_SCHEDULE_INCOMPLETE",)
            and self.invalid_proposal.package_unchanged
            and self.proposal.package_generated
            and self.validation.accepted
            and self.semantic_candidate.accepted
            and self.phase6.accepted
            and self.lifecycle_transition.accepted
            and set(self.lifecycle_transition.changed_components)
            == {"memory_state", "retrieval_policy"}
            and len(self.lifecycle_transition.retained_task_ids) == 4
            and len(self.lifecycle_transition.new_task_ids) == 1
            and self.ledger.generator_invocations == 4
            and self.ledger.rejected_attempts == 2
            and self.ledger.candidate_realizations == 2
            and self.ledger.candidate_evaluations == 2
            and self.ledger.accepted_promotions == 1
            and self.ledger.frontier_expansions == 1
            and self.ledger.manual_repairs == 0
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        active_state = self.phase12b.semantic_candidate.candidate_state
        content = {
            "schema_id": "runtime.v3.phase12c.evidence_summary.v1",
            "accepted": self.accepted,
            "phase12b_reference_hash": self.phase12b.reference_hash,
            "active_package_hash": self.phase12b.semantic_candidate.manifest.package_hash,
            "active_state_hash": active_state.state_hash,
            "active_model_identity_hash": self.phase12b.semantic_candidate.manifest.model_identity_hash,
            "active_generator_hash": active_state.policies.generator_policy_hash,
            "active_planner_hash": active_state.policies.planner_policy_hash,
            "invalid_proposal_hash": self.invalid_proposal.report_hash,
            "invalid_validation_hash": self.invalid_validation.report_hash,
            "invalid_proposal_package_unchanged": self.invalid_proposal.package_unchanged,
            "proposal_hash": self.proposal.report_hash,
            "proposal_validation_hash": self.validation.report_hash,
            "deterministic_replays": self.deterministic_replays,
            "semantic_candidate_hash": self.semantic_candidate.fixture_hash,
            "candidate_package_hash": self.semantic_candidate.manifest.package_hash,
            "candidate_model_identity_hash": self.semantic_candidate.manifest.model_identity_hash,
            "candidate_memory_hash": self.semantic_candidate.manifest.memory_manifest_hash,
            "candidate_retrieval_hash": self.semantic_candidate.manifest.retrieval_index_hash,
            "phase6_hash": self.phase6.evidence_hash,
            "lifecycle_certificate_hash": self.lifecycle_certificate.certificate_hash,
            "lifecycle_transition_hash": self.lifecycle_transition.semantic_report_hash,
            "frontier_before": list(active_state.capability_frontier.task_ids),
            "frontier_after": list(self.semantic_candidate.candidate_state.capability_frontier.task_ids),
            "new_task_ids": list(self.lifecycle_transition.new_task_ids),
            "changed_components": list(self.lifecycle_transition.changed_components),
            "progress_ledger": self.ledger.to_json(),
            "heldout_material_consumed": False,
            "manual_repairs": 0,
            "claim_boundary": {
                "m1_generator_used_for_authoritative_proposals": True,
                "second_phase12_rejection_retained": True,
                "rejection_preserved_m1": True,
                "m1_to_m2_candidate_realized": True,
                "m1_to_m2_gate_d_transition_accepted": True,
                "m1_to_m2_promotion": False,
                "accepted_phase12_promotions": 1,
                "strict_phase12_frontier_expansions": 1,
                "phase12_exit_closed": False,
            },
        }
        result = dict(content)
        result["summary_hash"] = canonical_json_hash(content)
        return result

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "phase12b": self.phase12b.to_json(),
            "invalid_proposal": self.invalid_proposal.to_json(),
            "invalid_proposal_replay": self.invalid_proposal_replay.to_json(),
            "invalid_validation": self.invalid_validation.to_json(),
            "proposal": self.proposal.to_json(),
            "proposal_replay": self.proposal_replay.to_json(),
            "validation": self.validation.to_json(),
            "semantic_candidate": self.semantic_candidate.to_json(),
            "wrapper_predecessor_manifest": self.wrapper_predecessor.manifest.to_json(),
            "phase6": self.phase6.to_json(),
            "lifecycle_certificate": self.lifecycle_certificate.to_json(),
            "lifecycle_transition": self.lifecycle_transition.to_json(),
            "ledger": self.ledger.to_json(),
            "summary": self.summary_json(),
        }


def build_phase12c_reference(
    output_root: Path,
    *,
    repo_root: Path,
) -> Phase12CReference:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12C reference already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    phase12b = build_phase12b_reference(root / "phase12b", repo_root=repo_root)
    invalid_proposal = generate_phase12c_proposal(
        phase12b,
        "schedule_incomplete_rejected",
    )
    invalid_proposal_replay = generate_phase12c_proposal(
        phase12b,
        "schedule_incomplete_rejected",
    )
    invalid_validation = validate_phase12c_proposal(phase12b, invalid_proposal)
    proposal = generate_phase12c_proposal(
        phase12b,
        "memory_retrieval_accepted",
        prior_validation_hash=invalid_validation.report_hash,
    )
    proposal_replay = generate_phase12c_proposal(
        phase12b,
        "memory_retrieval_accepted",
        prior_validation_hash=invalid_validation.report_hash,
    )
    validation = validate_phase12c_proposal(phase12b, proposal)
    semantic_candidate = build_phase12c_candidate_fixture(
        phase12b,
        proposal,
        validation,
        root / "semantic_candidate",
    )
    wrapper = _build_wrapper_predecessor(phase12b, root / "wrapper_predecessor")
    phase6 = _realize_candidate(
        wrapper,
        phase12b,
        semantic_candidate,
        root / "phase6_candidate",
    )
    realization = phase6.phase6.report.realization
    if realization is None or not realization.rollback.verified:
        raise ValueError("Phase 12C Phase 6 rollback is unavailable")
    lifecycle_certificate = replace(
        semantic_candidate.certificate,
        architecture_compatibility_hash=str(phase6.embedded_report["report_hash"]),
        resource_evidence_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v3.phase12c.lifecycle_resource_evidence.v1",
                "update_semantic_hash": semantic_candidate.update_semantic_hash,
                "phase6_usage_hash": realization.resources.usage_hash,
                "phase6_environment_hash": realization.environment.environment_hash,
                "changed_file_count": len(realization.changes),
                "rollback_hash": realization.rollback.rollback_hash,
                "generator_invocations": 4,
                "rejected_attempts": 2,
                "candidate_realizations": 2,
                "candidate_evaluations": 2,
                "training_steps": 1,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=realization.rollback.rollback_hash,
    )
    active_state = phase12b.semantic_candidate.candidate_state
    lifecycle_transition = validate_phase9_transition(
        active_state,
        semantic_candidate.update,
        semantic_candidate.candidate_state,
        lifecycle_certificate,
        semantic_candidate.heldout_policy,
    )
    ledger = Phase12ProgressLedger(
        total_budget_hash=phase12b.ledger.total_budget_hash,
        generator_invocations=4,
        rejected_attempts=2,
        candidate_realizations=2,
        candidate_evaluations=2,
        accepted_promotions=1,
        frontier_expansions=1,
        manual_repairs=0,
    )
    reference = Phase12CReference(
        root=root,
        phase12b=phase12b,
        invalid_proposal=invalid_proposal,
        invalid_proposal_replay=invalid_proposal_replay,
        invalid_validation=invalid_validation,
        proposal=proposal,
        proposal_replay=proposal_replay,
        validation=validation,
        semantic_candidate=semantic_candidate,
        wrapper_predecessor=wrapper,
        phase6=phase6,
        lifecycle_certificate=lifecycle_certificate,
        lifecycle_transition=lifecycle_transition,
        ledger=ledger,
    )
    if not reference.accepted:
        raise ValueError("Phase 12C portable lifecycle did not close")
    retained = root / "retained"
    _write_json(retained / "reference.json", reference.to_json())
    _write_json(retained / "summary.json", reference.summary_json())
    return reference


__all__ = [
    "MEMORY_POLICY_PATH",
    "PHASE12C_PHASE6_POLICY_ID",
    "RETRIEVAL_POLICY_PATH",
    "Phase12CPhase6Evidence",
    "Phase12CReference",
    "build_phase12c_reference",
    "phase12c_phase6_budget",
]
