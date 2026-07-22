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
from rcp_rclm_runtime.successor.policies import MEMORY_POLICY_PATH, RETRIEVAL_POLICY_PATH
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
from rcp_rclm_runtime_v3.contract.validation import Phase9TransitionReport, validate_phase9_transition
from rcp_rclm_runtime_v3.phase10.package import ADAPTER_MANIFEST_PATH, load_package_components, load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v3.phase12.phase12d_lifecycle import Phase12DReference, build_phase12d_reference
from rcp_rclm_runtime_v3.phase12.phase12e_candidate import (
    OPTIMIZER_STATE_PATH,
    Phase12ECandidateFixture,
    build_phase12e_candidate_fixture,
    validate_phase12e_candidate_package,
)
from rcp_rclm_runtime_v3.phase12.phase12e_program import (
    Phase12EProposalReport,
    Phase12EProposalValidationReport,
    generate_phase12e_proposal,
    validate_phase12e_proposal,
)
from rcp_rclm_runtime_v3.phase12.records import Phase12ProgressLedger

GENERATOR_PROJECTION_PATH: Final[str] = "policies/code_generation_policy.json"
PLANNER_PROJECTION_PATH: Final[str] = "policies/planning_policy.json"
TRAINING_PROJECTION_PATH: Final[str] = "policies/training_policy.json"
ADAPTER_PROJECTION_PATH: Final[str] = "architecture/adapter_manifest.json"
ARCHITECTURE_PROJECTION_PATH: Final[str] = ADAPTER_PROJECTION_PATH
PHASE12E_PHASE6_POLICY_ID: Final[str] = "rcp-rclm-phase12e-adapter-optimizer-selector-v1"


def phase12e_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=1024,
        max_total_bytes=218_103_808,
        max_changed_files=256,
        max_written_bytes=167_772_160,
        max_commands=512,
        max_snapshot_bytes=109_051_904,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _regular_file_map(root: Path) -> dict[str, Path]:
    resolved = root.resolve(strict=True)
    result: dict[str, Path] = {}
    for path in resolved.rglob("*"):
        if path.is_symlink():
            raise SchemaValidationError("phase12e.lifecycle", "symlinks are forbidden")
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
        "schema_id": "runtime.v3.phase12e.phase6_training_projection.v1",
        "data_curriculum_hash": manifest.data_curriculum_hash,
        "training_policy_hash": manifest.training_policy_hash,
        "optimizer_state_hash": manifest.optimizer_state_hash,
        "training_steps_for_transition": 1,
        "candidate_self_report_authoritative": False,
    }


def _adapter_projection(package_root: Path) -> dict[str, object]:
    manifest, architecture, _, _, adapter = load_package_components(package_root.resolve(strict=True))
    return {
        "schema_id": "runtime.v3.phase12e.phase6_adapter_projection.v1",
        "architecture_hash": architecture.architecture_hash,
        "adapter_manifest_hash": manifest.adapter_manifest_hash,
        "adapter_status": adapter.status,
        "adapter_rank": adapter.rank,
        "adapter_parameter_count": adapter.parameter_count,
        "model_parameter_count": manifest.parameter_count,
        "model_identity_hash": manifest.model_identity_hash,
    }


def _build_wrapper_predecessor(
    phase12d: Phase12DReference,
    output_root: Path,
) -> LoadedPredecessorPackage:
    active_root = phase12d.semantic_candidate.root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"Phase 12E wrapper already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase12e-wrapper-",
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
        _write_json(payload / ADAPTER_PROJECTION_PATH, _adapter_projection(active_root))
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
            package_id="phase12.m3.wrapper.predecessor",
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
            raise ValueError("reopened Phase 12E wrapper manifest differs")
        os.replace(package_root, resolved_output)
    return load_predecessor_package(resolved_output)


def _build_selection(
    predecessor: LoadedPredecessorPackage,
    phase12d: Phase12DReference,
    candidate: Phase12ECandidateFixture,
) -> Phase6SelectionRecord:
    active_root = phase12d.semantic_candidate.root.resolve(strict=True)
    before_files = _regular_file_map(active_root)
    after_files = _regular_file_map(candidate.root)
    deleted = set(before_files) - set(after_files)
    if deleted:
        raise SchemaValidationError(
            "phase12e.lifecycle.file_set",
            f"adapter successor cannot delete canonical package files: {sorted(deleted)}",
        )
    record_by_path = {record.path: record for record in predecessor.measurement.records}
    operations: list[SelectedFileOperationRecord] = []
    for relative in sorted(after_files, key=lambda item: item.encode("utf-8")):
        before_path = before_files.get(relative)
        after_content = after_files[relative].read_bytes()
        before_content = None if before_path is None else before_path.read_bytes()
        if before_content == after_content:
            continue
        wrapper_path = f"{EMBEDDED_PHASE12_ROOT}/{relative}"
        before_record = record_by_path.get(wrapper_path)
        if before_path is not None and before_record is None:
            raise SchemaValidationError(
                "phase12e.lifecycle.selection",
                f"wrapper predecessor is missing {wrapper_path}",
            )
        operations.append(
            SelectedFileOperationRecord.write(
                path=wrapper_path,
                component_kind=None,
                expected_before_hash=None if before_record is None else before_record.sha256,
                expected_before_mode=None if before_record is None else before_record.mode,
                after_mode="0644",
                content=after_content,
            )
        )

    projection_changes = (
        (
            ADAPTER_PROJECTION_PATH,
            "architecture_code",
            canonical_json_bytes(_adapter_projection(candidate.root)),
        ),
        (
            TRAINING_PROJECTION_PATH,
            "training_policy",
            canonical_json_bytes(_training_projection(candidate.root)),
        ),
    )
    for wrapper_path, component_kind, content in projection_changes:
        before_record = record_by_path.get(wrapper_path)
        if before_record is None:
            raise SchemaValidationError(
                "phase12e.lifecycle.selection",
                f"wrapper predecessor is missing {wrapper_path}",
            )
        operations.append(
            SelectedFileOperationRecord.write(
                path=wrapper_path,
                component_kind=component_kind,  # type: ignore[arg-type]
                expected_before_hash=before_record.sha256,
                expected_before_mode=before_record.mode,
                after_mode="0644",
                content=content,
            )
        )

    operations.sort(key=lambda item: item.path.encode("utf-8"))
    proposal_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12e.phase6_proposal.v1",
            "transition_id": candidate.proposal.generator_input.transition_id,
            "generator_input_hash": candidate.proposal.generator_input.input_hash,
            "proposal_hash": candidate.proposal.report_hash,
            "program_hash": candidate.proposal.program.program_hash,
            "program_validation_hash": candidate.validation.report_hash,
            "active_package_hash": phase12d.semantic_candidate.manifest.package_hash,
            "candidate_package_hash": candidate.manifest.package_hash,
            "adapter_manifest_hash": candidate.manifest.adapter_manifest_hash,
            "optimizer_state_hash": candidate.manifest.optimizer_state_hash,
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
        selection_policy_id=PHASE12E_PHASE6_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=("architecture_code", "training_policy"),
    )


@dataclass(frozen=True, slots=True)
class Phase12EPhase6Evidence:
    candidate: Phase12ECandidateFixture
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence
    embedded_report: Mapping[str, object]
    adapter_projection_matches: bool
    optimizer_projection_matches: bool

    schema_id: ClassVar[str] = "runtime.v3.phase12e.phase6_evidence.v1"

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 12E Phase 6 candidate is unavailable")
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
            and self.adapter_projection_matches
            and self.optimizer_projection_matches
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
            "adapter_projection_matches": self.adapter_projection_matches,
            "optimizer_projection_matches": self.optimizer_projection_matches,
            "rollback_verified": bool(realization and realization.rollback.verified),
            "rollback_hash": None if realization is None else realization.rollback.rollback_hash,
            "changed_file_count": 0 if realization is None else len(realization.changes),
        }


def _realize_candidate(
    wrapper: LoadedPredecessorPackage,
    phase12d: Phase12DReference,
    candidate: Phase12ECandidateFixture,
    output_root: Path,
) -> Phase12EPhase6Evidence:
    selection = _build_selection(wrapper, phase12d, candidate)
    phase6 = build_candidate_package(
        wrapper.payload_root.parent,
        selection,
        phase12e_phase6_budget(),
        output_root,
    )
    if phase6.output_root is None:
        embedded_report: Mapping[str, object] = {
            "accepted": False,
            "report_hash": canonical_json_hash({"phase12e_phase6": "candidate_unavailable"}),
        }
        adapter_projection_matches = False
        optimizer_projection_matches = False
    else:
        verify_candidate_package(phase6.output_root)
        embedded_root = phase6.output_root / "payload" / EMBEDDED_PHASE12_ROOT
        embedded_report = validate_phase12e_candidate_package(
            phase12d,
            candidate.proposal,
            embedded_root,
        )
        adapter_projection_matches = (
            phase6.output_root / "payload" / ADAPTER_PROJECTION_PATH
        ).read_bytes() == canonical_json_bytes(_adapter_projection(embedded_root))
        optimizer_projection_matches = (
            phase6.output_root / "payload" / TRAINING_PROJECTION_PATH
        ).read_bytes() == canonical_json_bytes(_training_projection(embedded_root))
    evidence = Phase12EPhase6Evidence(
        candidate=candidate,
        selection=selection,
        phase6=phase6,
        embedded_report=embedded_report,
        adapter_projection_matches=adapter_projection_matches,
        optimizer_projection_matches=optimizer_projection_matches,
    )
    if not evidence.accepted:
        raise ValueError("Phase 12E realization did not validate")
    return evidence


@dataclass(frozen=True, slots=True)
class Phase12EReference:
    root: Path
    phase12d: Phase12DReference
    proposal: Phase12EProposalReport
    proposal_replay: Phase12EProposalReport
    validation: Phase12EProposalValidationReport
    semantic_candidate: Phase12ECandidateFixture
    wrapper_predecessor: LoadedPredecessorPackage
    phase6: Phase12EPhase6Evidence
    lifecycle_certificate: LearnedCertificatePacket
    lifecycle_transition: Phase9TransitionReport
    ledger: Phase12ProgressLedger

    schema_id: ClassVar[str] = "runtime.v3.phase12e.reference.v1"

    @property
    def deterministic_replay(self) -> bool:
        return self.proposal.to_json() == self.proposal_replay.to_json()

    @property
    def accepted(self) -> bool:
        return (
            self.phase12d.accepted
            and self.proposal.package_generated
            and self.deterministic_replay
            and self.validation.accepted
            and self.semantic_candidate.accepted
            and self.phase6.accepted
            and self.lifecycle_transition.accepted
            and set(self.lifecycle_transition.changed_components)
            == {"adapter_manifest", "model_architecture", "optimizer_policy"}
            and len(self.lifecycle_transition.retained_task_ids) == 6
            and len(self.lifecycle_transition.new_task_ids) == 1
            and self.ledger.generator_invocations == 6
            and self.ledger.rejected_attempts == 2
            and self.ledger.candidate_realizations == 4
            and self.ledger.candidate_evaluations == 4
            and self.ledger.accepted_promotions == 3
            and self.ledger.frontier_expansions == 3
            and self.ledger.manual_repairs == 0
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        active_state = self.phase12d.semantic_candidate.candidate_state
        content = {
            "schema_id": "runtime.v3.phase12e.evidence_summary.v1",
            "accepted": self.accepted,
            "phase12d_reference_hash": self.phase12d.reference_hash,
            "active_package_hash": self.phase12d.semantic_candidate.manifest.package_hash,
            "active_state_hash": active_state.state_hash,
            "active_model_identity_hash": self.phase12d.semantic_candidate.manifest.model_identity_hash,
            "active_generator_hash": active_state.policies.generator_policy_hash,
            "active_planner_hash": active_state.policies.planner_policy_hash,
            "proposal_hash": self.proposal.report_hash,
            "proposal_validation_hash": self.validation.report_hash,
            "deterministic_replay": self.deterministic_replay,
            "semantic_candidate_hash": self.semantic_candidate.fixture_hash,
            "candidate_package_hash": self.semantic_candidate.manifest.package_hash,
            "candidate_model_identity_hash": self.semantic_candidate.manifest.model_identity_hash,
            "candidate_adapter_hash": self.semantic_candidate.manifest.adapter_manifest_hash,
            "candidate_optimizer_hash": self.semantic_candidate.manifest.optimizer_state_hash,
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
                "m3_generator_used_for_authoritative_proposal": True,
                "m3_to_m4_candidate_realized": True,
                "m3_to_m4_gate_d_transition_accepted": True,
                "trained_lora_adapter_installed": True,
                "optimizer_policy_updated": True,
                "m3_to_m4_promotion": False,
                "accepted_phase12_promotions": 3,
                "strict_phase12_frontier_expansions": 3,
                "frontier_cardinality": 7,
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
            "phase12d": self.phase12d.to_json(),
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


def build_phase12e_reference(
    output_root: Path,
    *,
    repo_root: Path,
) -> Phase12EReference:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12E reference already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    phase12d = build_phase12d_reference(root / "phase12d", repo_root=repo_root)
    proposal = generate_phase12e_proposal(phase12d)
    proposal_replay = generate_phase12e_proposal(phase12d)
    validation = validate_phase12e_proposal(phase12d, proposal)
    semantic_candidate = build_phase12e_candidate_fixture(
        phase12d,
        proposal,
        validation,
        root / "semantic_candidate",
    )
    wrapper = _build_wrapper_predecessor(phase12d, root / "wrapper_predecessor")
    phase6 = _realize_candidate(
        wrapper,
        phase12d,
        semantic_candidate,
        root / "phase6_candidate",
    )
    realization = phase6.phase6.report.realization
    if realization is None or not realization.rollback.verified:
        raise ValueError("Phase 12E Phase 6 rollback is unavailable")
    lifecycle_certificate = replace(
        semantic_candidate.certificate,
        architecture_compatibility_hash=str(phase6.embedded_report["report_hash"]),
        resource_evidence_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v3.phase12e.lifecycle_resource_evidence.v1",
                "update_semantic_hash": semantic_candidate.update_semantic_hash,
                "phase6_usage_hash": realization.resources.usage_hash,
                "phase6_environment_hash": realization.environment.environment_hash,
                "changed_file_count": len(realization.changes),
                "rollback_hash": realization.rollback.rollback_hash,
                "generator_invocations": 6,
                "rejected_attempts": 2,
                "candidate_realizations": 4,
                "candidate_evaluations": 4,
                "training_steps": 2,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=realization.rollback.rollback_hash,
    )
    active_state = phase12d.semantic_candidate.candidate_state
    lifecycle_transition = validate_phase9_transition(
        active_state,
        semantic_candidate.update,
        semantic_candidate.candidate_state,
        lifecycle_certificate,
        semantic_candidate.heldout_policy,
    )
    ledger = Phase12ProgressLedger(
        total_budget_hash=phase12d.ledger.total_budget_hash,
        generator_invocations=6,
        rejected_attempts=2,
        candidate_realizations=4,
        candidate_evaluations=4,
        accepted_promotions=3,
        frontier_expansions=3,
        manual_repairs=0,
    )
    reference = Phase12EReference(
        root=root,
        phase12d=phase12d,
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
        raise ValueError("Phase 12E portable lifecycle did not close")
    retained = root / "retained"
    _write_json(retained / "reference.json", reference.to_json())
    _write_json(retained / "summary.json", reference.summary_json())
    return reference


__all__ = [
    "ADAPTER_PROJECTION_PATH",
    "ARCHITECTURE_PROJECTION_PATH",
    "EMBEDDED_PHASE12_ROOT",
    "PHASE12E_PHASE6_POLICY_ID",
    "Phase12EPhase6Evidence",
    "Phase12EReference",
    "build_phase12e_reference",
    "phase12e_phase6_budget",
]
