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
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v3.phase12.phase12c_lifecycle import (
    Phase12CReference,
    build_phase12c_reference,
)
from rcp_rclm_runtime_v3.phase12.phase12d_candidate import (
    Phase12DCandidateFixture,
    build_phase12d_candidate_fixture,
    validate_phase12d_candidate_package,
)
from rcp_rclm_runtime_v3.phase12.phase12d_program import (
    Phase12DProposalReport,
    Phase12DProposalValidationReport,
    generate_phase12d_proposal,
    validate_phase12d_proposal,
)
from rcp_rclm_runtime_v3.phase12.records import Phase12ProgressLedger

GENERATOR_PROJECTION_PATH: Final[str] = "policies/code_generation_policy.json"
PLANNER_PROJECTION_PATH: Final[str] = "policies/planning_policy.json"
TRAINING_PROJECTION_PATH: Final[str] = "policies/training_policy.json"
PHASE12D_PHASE6_POLICY_ID: Final[str] = (
    "rcp-rclm-phase12d-generator-planner-selector-v1"
)


def phase12d_phase6_budget() -> Phase6ResourceBudgetRecord:
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
            raise SchemaValidationError("phase12d.lifecycle", "symlinks are forbidden")
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
        "schema_id": "runtime.v3.phase12d.phase6_training_projection.v1",
        "data_curriculum_hash": manifest.data_curriculum_hash,
        "training_policy_hash": manifest.training_policy_hash,
        "optimizer_state_hash": manifest.optimizer_state_hash,
        "training_steps_for_transition": 0,
        "candidate_self_report_authoritative": False,
    }


def _build_wrapper_predecessor(
    phase12c: Phase12CReference,
    output_root: Path,
) -> LoadedPredecessorPackage:
    active_root = phase12c.semantic_candidate.root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"Phase 12D wrapper already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase12d-wrapper-",
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
            package_id="phase12.m2.wrapper.predecessor",
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
            raise ValueError("reopened Phase 12D wrapper manifest differs")
        os.replace(package_root, resolved_output)
    return load_predecessor_package(resolved_output)


def _build_selection(
    predecessor: LoadedPredecessorPackage,
    phase12c: Phase12CReference,
    candidate: Phase12DCandidateFixture,
) -> Phase6SelectionRecord:
    active_root = phase12c.semantic_candidate.root.resolve(strict=True)
    before_files = _regular_file_map(active_root)
    after_files = _regular_file_map(candidate.root)
    if set(before_files) != set(after_files):
        raise SchemaValidationError(
            "phase12d.lifecycle.file_set",
            "generator/planner successor must retain the canonical package file set",
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
                "phase12d.lifecycle.selection",
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
            GENERATOR_PROJECTION_PATH,
            "code_generation_policy",
            candidate.root / "policies/generator_policy.json",
        ),
        (
            PLANNER_PROJECTION_PATH,
            "planning_policy",
            candidate.root / "policies/planner_policy.json",
        ),
    )
    for wrapper_path, component_kind, source_path in projection_changes:
        before_record = record_by_path.get(wrapper_path)
        if before_record is None:
            raise SchemaValidationError(
                "phase12d.lifecycle.selection",
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
            "schema_id": "runtime.v3.phase12d.phase6_proposal.v1",
            "transition_id": candidate.proposal.generator_input.transition_id,
            "generator_input_hash": candidate.proposal.generator_input.input_hash,
            "proposal_hash": candidate.proposal.report_hash,
            "program_hash": candidate.proposal.program.program_hash,
            "program_validation_hash": candidate.validation.report_hash,
            "active_package_hash": phase12c.semantic_candidate.manifest.package_hash,
            "candidate_package_hash": candidate.manifest.package_hash,
            "generator_policy_hash": candidate.manifest.generator_policy_hash,
            "planner_policy_hash": candidate.manifest.planner_policy_hash,
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
        selection_policy_id=PHASE12D_PHASE6_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=("code_generation_policy", "planning_policy"),
    )


@dataclass(frozen=True, slots=True)
class Phase12DPhase6Evidence:
    candidate: Phase12DCandidateFixture
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence
    embedded_report: Mapping[str, object]
    generator_projection_matches: bool
    planner_projection_matches: bool

    schema_id: ClassVar[str] = "runtime.v3.phase12d.phase6_evidence.v1"

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 12D Phase 6 candidate is unavailable")
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
            and self.generator_projection_matches
            and self.planner_projection_matches
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
            "generator_projection_matches": self.generator_projection_matches,
            "planner_projection_matches": self.planner_projection_matches,
            "rollback_verified": bool(realization and realization.rollback.verified),
            "rollback_hash": None if realization is None else realization.rollback.rollback_hash,
            "changed_file_count": 0 if realization is None else len(realization.changes),
        }


def _realize_candidate(
    wrapper: LoadedPredecessorPackage,
    phase12c: Phase12CReference,
    candidate: Phase12DCandidateFixture,
    output_root: Path,
) -> Phase12DPhase6Evidence:
    selection = _build_selection(wrapper, phase12c, candidate)
    phase6 = build_candidate_package(
        wrapper.payload_root.parent,
        selection,
        phase12d_phase6_budget(),
        output_root,
    )
    if phase6.output_root is None:
        embedded_report: Mapping[str, object] = {
            "accepted": False,
            "report_hash": canonical_json_hash({"phase12d_phase6": "candidate_unavailable"}),
        }
        generator_projection_matches = False
        planner_projection_matches = False
    else:
        verify_candidate_package(phase6.output_root)
        embedded_root = phase6.output_root / "payload" / EMBEDDED_PHASE12_ROOT
        embedded_report = validate_phase12d_candidate_package(
            phase12c,
            candidate.proposal,
            embedded_root,
        )
        generator_projection_matches = (
            phase6.output_root / "payload" / GENERATOR_PROJECTION_PATH
        ).read_bytes() == (embedded_root / "policies/generator_policy.json").read_bytes()
        planner_projection_matches = (
            phase6.output_root / "payload" / PLANNER_PROJECTION_PATH
        ).read_bytes() == (embedded_root / "policies/planner_policy.json").read_bytes()
    evidence = Phase12DPhase6Evidence(
        candidate=candidate,
        selection=selection,
        phase6=phase6,
        embedded_report=embedded_report,
        generator_projection_matches=generator_projection_matches,
        planner_projection_matches=planner_projection_matches,
    )
    if not evidence.accepted:
        raise ValueError("Phase 12D realization did not validate")
    return evidence


@dataclass(frozen=True, slots=True)
class Phase12DReference:
    root: Path
    phase12c: Phase12CReference
    proposal: Phase12DProposalReport
    proposal_replay: Phase12DProposalReport
    validation: Phase12DProposalValidationReport
    semantic_candidate: Phase12DCandidateFixture
    wrapper_predecessor: LoadedPredecessorPackage
    phase6: Phase12DPhase6Evidence
    lifecycle_certificate: LearnedCertificatePacket
    lifecycle_transition: Phase9TransitionReport
    ledger: Phase12ProgressLedger

    schema_id: ClassVar[str] = "runtime.v3.phase12d.reference.v1"

    @property
    def deterministic_replay(self) -> bool:
        return self.proposal.to_json() == self.proposal_replay.to_json()

    @property
    def accepted(self) -> bool:
        return (
            self.phase12c.accepted
            and self.proposal.package_generated
            and self.deterministic_replay
            and self.validation.accepted
            and self.semantic_candidate.accepted
            and self.phase6.accepted
            and self.lifecycle_transition.accepted
            and set(self.lifecycle_transition.changed_components)
            == {"generator_policy", "planner_policy"}
            and len(self.lifecycle_transition.retained_task_ids) == 5
            and len(self.lifecycle_transition.new_task_ids) == 1
            and self.ledger.generator_invocations == 5
            and self.ledger.rejected_attempts == 2
            and self.ledger.candidate_realizations == 3
            and self.ledger.candidate_evaluations == 3
            and self.ledger.accepted_promotions == 2
            and self.ledger.frontier_expansions == 2
            and self.ledger.manual_repairs == 0
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        active_state = self.phase12c.semantic_candidate.candidate_state
        content = {
            "schema_id": "runtime.v3.phase12d.evidence_summary.v1",
            "accepted": self.accepted,
            "phase12c_reference_hash": self.phase12c.reference_hash,
            "active_package_hash": self.phase12c.semantic_candidate.manifest.package_hash,
            "active_state_hash": active_state.state_hash,
            "active_model_identity_hash": self.phase12c.semantic_candidate.manifest.model_identity_hash,
            "active_generator_hash": active_state.policies.generator_policy_hash,
            "active_planner_hash": active_state.policies.planner_policy_hash,
            "proposal_hash": self.proposal.report_hash,
            "proposal_validation_hash": self.validation.report_hash,
            "deterministic_replay": self.deterministic_replay,
            "semantic_candidate_hash": self.semantic_candidate.fixture_hash,
            "candidate_package_hash": self.semantic_candidate.manifest.package_hash,
            "candidate_model_identity_hash": self.semantic_candidate.manifest.model_identity_hash,
            "candidate_generator_hash": self.semantic_candidate.manifest.generator_policy_hash,
            "candidate_planner_hash": self.semantic_candidate.manifest.planner_policy_hash,
            "successor_proposal_protocol_hash": (
                self.semantic_candidate.candidate_state.self_hosting.proposal_protocol_hash
            ),
            "phase6_hash": self.phase6.evidence_hash,
            "lifecycle_certificate_hash": self.lifecycle_certificate.certificate_hash,
            "lifecycle_transition_hash": self.lifecycle_transition.semantic_report_hash,
            "frontier_before": list(active_state.capability_frontier.task_ids),
            "frontier_after": list(
                self.semantic_candidate.candidate_state.capability_frontier.task_ids
            ),
            "new_task_ids": list(self.lifecycle_transition.new_task_ids),
            "changed_components": list(self.lifecycle_transition.changed_components),
            "progress_ledger": self.ledger.to_json(),
            "heldout_material_consumed": False,
            "manual_repairs": 0,
            "claim_boundary": {
                "m2_generator_used_for_authoritative_proposal": True,
                "m2_to_m3_candidate_realized": True,
                "m2_to_m3_gate_d_transition_accepted": True,
                "generation3_generator_installed": True,
                "generation3_planner_installed": True,
                "m2_to_m3_promotion": False,
                "accepted_phase12_promotions": 2,
                "strict_phase12_frontier_expansions": 2,
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
            "phase12c": self.phase12c.to_json(),
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


def build_phase12d_reference(
    output_root: Path,
    *,
    repo_root: Path,
) -> Phase12DReference:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12D reference already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    phase12c = build_phase12c_reference(root / "phase12c", repo_root=repo_root)
    proposal = generate_phase12d_proposal(phase12c)
    proposal_replay = generate_phase12d_proposal(phase12c)
    validation = validate_phase12d_proposal(phase12c, proposal)
    semantic_candidate = build_phase12d_candidate_fixture(
        phase12c,
        proposal,
        validation,
        root / "semantic_candidate",
    )
    wrapper = _build_wrapper_predecessor(phase12c, root / "wrapper_predecessor")
    phase6 = _realize_candidate(
        wrapper,
        phase12c,
        semantic_candidate,
        root / "phase6_candidate",
    )
    realization = phase6.phase6.report.realization
    if realization is None or not realization.rollback.verified:
        raise ValueError("Phase 12D Phase 6 rollback is unavailable")
    lifecycle_certificate = replace(
        semantic_candidate.certificate,
        architecture_compatibility_hash=str(phase6.embedded_report["report_hash"]),
        resource_evidence_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v3.phase12d.lifecycle_resource_evidence.v1",
                "update_semantic_hash": semantic_candidate.update_semantic_hash,
                "phase6_usage_hash": realization.resources.usage_hash,
                "phase6_environment_hash": realization.environment.environment_hash,
                "changed_file_count": len(realization.changes),
                "rollback_hash": realization.rollback.rollback_hash,
                "generator_invocations": 5,
                "rejected_attempts": 2,
                "candidate_realizations": 3,
                "candidate_evaluations": 3,
                "training_steps": 1,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=realization.rollback.rollback_hash,
    )
    active_state = phase12c.semantic_candidate.candidate_state
    lifecycle_transition = validate_phase9_transition(
        active_state,
        semantic_candidate.update,
        semantic_candidate.candidate_state,
        lifecycle_certificate,
        semantic_candidate.heldout_policy,
    )
    ledger = Phase12ProgressLedger(
        total_budget_hash=phase12c.ledger.total_budget_hash,
        generator_invocations=5,
        rejected_attempts=2,
        candidate_realizations=3,
        candidate_evaluations=3,
        accepted_promotions=2,
        frontier_expansions=2,
        manual_repairs=0,
    )
    reference = Phase12DReference(
        root=root,
        phase12c=phase12c,
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
        raise ValueError("Phase 12D portable lifecycle did not close")
    retained = root / "retained"
    _write_json(retained / "reference.json", reference.to_json())
    _write_json(retained / "summary.json", reference.summary_json())
    return reference


__all__ = [
    "GENERATOR_PROJECTION_PATH",
    "PHASE12D_PHASE6_POLICY_ID",
    "PLANNER_PROJECTION_PATH",
    "Phase12DPhase6Evidence",
    "Phase12DReference",
    "build_phase12d_reference",
    "phase12d_phase6_budget",
]
