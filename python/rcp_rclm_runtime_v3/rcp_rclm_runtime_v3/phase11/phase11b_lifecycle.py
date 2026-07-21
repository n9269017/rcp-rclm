from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
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
from rcp_rclm_runtime_v3.phase11.phase11b_bootstrap import (
    Phase11BActiveFixture,
    build_phase11b_active_fixture,
)
from rcp_rclm_runtime_v3.phase11.phase11b_candidate import (
    Phase11CandidateFixture,
    build_phase11b_candidate_fixture,
    validate_phase11b_candidate_package,
)
from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    PHASE11B_CONTRACT_VERSION,
    PHASE11B_PROPOSAL_PROTOCOL_HASH,
)
from rcp_rclm_runtime_v3.phase11.phase11b_program import (
    generate_phase11b_program,
    phase11b_objective_hash,
    validate_phase11b_program,
)
from rcp_rclm_runtime_v3.phase11.records import (
    GeneratorInvocationReport,
    ModelGeneratorInput,
    ProgramValidationReport,
)

EMBEDDED_PHASE11_ROOT: Final[str] = "model/weights/phase11_package"
GENERATOR_PROJECTION_PATH: Final[str] = "policies/code_generation_policy.json"
PLANNER_PROJECTION_PATH: Final[str] = "policies/planning_policy.json"
TRAINING_PROJECTION_PATH: Final[str] = "policies/training_policy.json"
PHASE11B_PHASE6_POLICY_ID: Final[str] = "rcp-rclm-phase11b-model-program-selector-v1"


def phase11b_phase6_budget() -> Phase6ResourceBudgetRecord:
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
            raise SchemaValidationError("phase11b.lifecycle", "symlinks are forbidden")
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
        "schema_id": "runtime.v3.phase11b.phase6_training_projection.v1",
        "data_curriculum_hash": manifest.data_curriculum_hash,
        "training_policy_hash": manifest.training_policy_hash,
        "candidate_self_report_authoritative": False,
    }


def _build_wrapper_predecessor(
    active: Phase11BActiveFixture,
    output_root: Path,
) -> LoadedPredecessorPackage:
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"Phase 11B wrapper already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase11b-wrapper-",
        dir=resolved_output.parent,
    ) as temporary:
        package_root = build_reference_predecessor_package(
            generator_input,
            Path(temporary) / "wrapper",
        )
        payload = package_root / "payload"
        embedded = payload / EMBEDDED_PHASE11_ROOT
        embedded.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(active.active_package_root, embedded, symlinks=False)
        _write_json(
            payload / GENERATOR_PROJECTION_PATH,
            _policy_projection(active.active_package_root, "policies/generator_policy.json"),
        )
        _write_json(
            payload / PLANNER_PROJECTION_PATH,
            _policy_projection(active.active_package_root, "policies/planner_policy.json"),
        )
        _write_json(
            payload / TRAINING_PROJECTION_PATH,
            _training_projection(active.active_package_root),
        )
        manifest_value = load_json_strict(
            (package_root / "manifest.json").read_bytes(),
            require_canonical=True,
        )
        base_manifest = Phase6PredecessorManifestRecord.from_json(manifest_value)
        measurement = measure_payload_tree(payload)
        updated = Phase6PredecessorManifestRecord(
            package_id="phase11b.active.wrapper.predecessor",
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
            raise ValueError("reopened Phase 11B wrapper manifest differs")
        os.replace(package_root, resolved_output)
    return load_predecessor_package(resolved_output)


def _projection_operations(
    predecessor: LoadedPredecessorPackage,
    candidate: Phase11CandidateFixture,
) -> Sequence[SelectedFileOperationRecord]:
    record_by_path = {record.path: record for record in predecessor.measurement.records}
    candidate_root = candidate.root.resolve(strict=True)
    projected: dict[str, tuple[str, bytes]] = {
        GENERATOR_PROJECTION_PATH: (
            "code_generation_policy",
            (candidate_root / "policies/generator_policy.json").read_bytes(),
        ),
        PLANNER_PROJECTION_PATH: (
            "planning_policy",
            (candidate_root / "policies/planner_policy.json").read_bytes(),
        ),
        TRAINING_PROJECTION_PATH: (
            "training_policy",
            canonical_json_bytes(_training_projection(candidate_root)),
        ),
    }
    result: list[SelectedFileOperationRecord] = []
    for path in sorted(projected, key=lambda item: item.encode("utf-8")):
        component_kind, content = projected[path]
        record = record_by_path[path]
        if (predecessor.payload_root / path).read_bytes() == content:
            continue
        result.append(
            SelectedFileOperationRecord.write(
                path=path,
                component_kind=component_kind,  # type: ignore[arg-type]
                expected_before_hash=record.sha256,
                expected_before_mode=record.mode,
                after_mode="0644",
                content=content,
            )
        )
    return tuple(result)


def _build_selection(
    predecessor: LoadedPredecessorPackage,
    active: Phase11BActiveFixture,
    candidate: Phase11CandidateFixture,
) -> Phase6SelectionRecord:
    before_files = _regular_file_map(active.active_package_root)
    after_files = _regular_file_map(candidate.root)
    if set(before_files) != set(after_files):
        raise SchemaValidationError(
            "phase11b.lifecycle.file_set",
            "model-generated successor must retain the canonical package file set",
        )
    record_by_path = {record.path: record for record in predecessor.measurement.records}
    operations: list[SelectedFileOperationRecord] = []
    for relative in sorted(after_files, key=lambda item: item.encode("utf-8")):
        before_content = before_files[relative].read_bytes()
        after_content = after_files[relative].read_bytes()
        if before_content == after_content:
            continue
        wrapper_path = f"{EMBEDDED_PHASE11_ROOT}/{relative}"
        before_record = record_by_path.get(wrapper_path)
        if before_record is None:
            raise SchemaValidationError(
                "phase11b.lifecycle.selection",
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
    operations.extend(_projection_operations(predecessor, candidate))
    operations.sort(key=lambda item: item.path.encode("utf-8"))
    if not operations:
        raise SchemaValidationError(
            "phase11b.lifecycle.selection",
            "model-generated successor must change at least one file",
        )
    proposal_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase11b.phase6_proposal.v1",
            "transition_id": candidate.invocation.generator_input.transition_id,
            "generator_input_hash": candidate.invocation.generator_input.input_hash,
            "invocation_hash": candidate.invocation.report_hash,
            "program_hash": candidate.invocation.program.program_hash,
            "program_validation_hash": candidate.validation.report_hash,
            "active_package_hash": active.active_manifest.package_hash,
            "candidate_package_hash": candidate.manifest.package_hash,
            "candidate_model_identity_hash": candidate.manifest.model_identity_hash,
            "heldout_material_consumed": False,
            "manual_repair_count": 0,
        }
    )
    logical_update = canonical_rclm_update(ClassicalBinaryUpdateRecord("stay"))
    update_json = logical_update.to_json()
    component_kinds = tuple(
        sorted(
            {
                operation.component_kind
                for operation in operations
                if operation.component_kind is not None
            }
        )
    )
    return Phase6SelectionRecord(
        transition_id=f"phase11b-{candidate.kind}",
        proposal_hash=proposal_hash,
        generator_request_hash=candidate.invocation.generator_input.input_hash,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=predecessor.manifest.phase5_manifest_hash,
        selection_policy_id=PHASE11B_PHASE6_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=component_kinds,  # type: ignore[arg-type]
    )


@dataclass(frozen=True, slots=True)
class Phase11BPhase6Evidence:
    candidate: Phase11CandidateFixture
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence
    embedded_report: Mapping[str, object]

    schema_id: ClassVar[str] = "runtime.v3.phase11b.phase6_evidence.v1"

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 11B Phase 6 candidate is unavailable")
        return self.phase6.output_root

    @property
    def embedded_candidate_root(self) -> Path:
        return self.candidate_root / "payload" / EMBEDDED_PHASE11_ROOT

    @property
    def accepted(self) -> bool:
        realization = self.phase6.report.realization
        if (
            not self.phase6.report.built
            or self.phase6.output_root is None
            or realization is None
        ):
            return False
        manifest = load_package_manifest(self.embedded_candidate_root)
        return (
            self.embedded_report["accepted"] is True
            and realization.rollback.verified
            and manifest.package_hash == self.candidate.manifest.package_hash
            and manifest.model_identity_hash
            == self.candidate.manifest.model_identity_hash
        )

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        realization = self.phase6.report.realization
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "candidate_kind": self.candidate.kind,
            "candidate_fixture_hash": self.candidate.fixture_hash,
            "selection": self.selection.to_json(),
            "phase6_report": self.phase6.report.to_json(),
            "embedded_report": dict(self.embedded_report),
            "rollback_verified": bool(realization and realization.rollback.verified),
            "rollback_hash": (
                None if realization is None else realization.rollback.rollback_hash
            ),
            "changed_file_count": (
                0 if realization is None else len(realization.changes)
            ),
        }


def _realize_candidate(
    wrapper: LoadedPredecessorPackage,
    active: Phase11BActiveFixture,
    candidate: Phase11CandidateFixture,
    output_root: Path,
) -> Phase11BPhase6Evidence:
    selection = _build_selection(wrapper, active, candidate)
    phase6 = build_candidate_package(
        wrapper.payload_root.parent,
        selection,
        phase11b_phase6_budget(),
        output_root,
    )
    if phase6.output_root is None:
        embedded_report: Mapping[str, object] = {
            "accepted": False,
            "report_hash": canonical_json_hash(
                {"phase11b_phase6": "candidate_unavailable"}
            ),
        }
    else:
        verify_candidate_package(phase6.output_root)
        embedded_report = validate_phase11b_candidate_package(
            active,
            candidate.invocation,
            phase6.output_root / "payload" / EMBEDDED_PHASE11_ROOT,
            candidate.kind,
        )
    evidence = Phase11BPhase6Evidence(
        candidate=candidate,
        selection=selection,
        phase6=phase6,
        embedded_report=embedded_report,
    )
    if not evidence.accepted:
        raise ValueError(f"Phase 11B {candidate.kind} realization did not validate")
    return evidence


def _generate_replayed(
    active: Phase11BActiveFixture,
    generator_input: ModelGeneratorInput,
) -> GeneratorInvocationReport:
    first = generate_phase11b_program(active.active_package_root, generator_input)
    second = generate_phase11b_program(active.active_package_root, generator_input)
    if first.to_json() != second.to_json():
        raise SchemaValidationError(
            "phase11b.generator_replay",
            "fresh deterministic model-generation replays differ",
        )
    return first


def _model_input(
    active: Phase11BActiveFixture,
    *,
    invocation_index: int,
    observation: object,
) -> ModelGeneratorInput:
    return ModelGeneratorInput(
        transition_id="phase11b-autonomous-candidate-sequence",
        invocation_id=f"phase11b-generator-invocation-{invocation_index}",
        invocation_index=invocation_index,
        active_package_hash=active.active_manifest.package_hash,
        active_state_hash=active.active_state.state_hash,
        model_identity_hash=active.active_manifest.model_identity_hash,
        active_generator_hash=active.active_manifest.generator_policy_hash,
        active_planner_hash=active.active_manifest.planner_policy_hash,
        proposal_protocol_hash=PHASE11B_PROPOSAL_PROTOCOL_HASH,
        objective_hash=phase11b_objective_hash(),
        observation_hash=canonical_json_hash(observation),
        budget=active.budget,
        manual_repair_count=0,
    )


@dataclass(frozen=True, slots=True)
class Phase11BReference:
    root: Path
    active: Phase11BActiveFixture
    wrapper_predecessor: LoadedPredecessorPackage
    invalid_invocation: GeneratorInvocationReport
    invalid_validation: ProgramValidationReport
    alpha_invocation: GeneratorInvocationReport
    alpha_validation: ProgramValidationReport
    alpha_candidate: Phase11CandidateFixture
    alpha_phase6: Phase11BPhase6Evidence
    beta_invocation: GeneratorInvocationReport
    beta_validation: ProgramValidationReport
    beta_candidate: Phase11CandidateFixture
    beta_phase6: Phase11BPhase6Evidence
    lifecycle_certificate: LearnedCertificatePacket
    lifecycle_transition: Phase9TransitionReport

    schema_id: ClassVar[str] = "runtime.v3.phase11b.reference.v1"

    @property
    def accepted(self) -> bool:
        invalid_reasons = {reason.value for reason in self.invalid_validation.reason_codes}
        return (
            self.active.accepted
            and self.invalid_invocation.model_generated
            and not self.invalid_validation.accepted
            and "PHASE11_BUDGET_EXCEEDED" in invalid_reasons
            and "PHASE11_FORBIDDEN_UPDATE_CLASS" in invalid_reasons
            and self.alpha_invocation.model_generated
            and self.alpha_validation.accepted
            and self.alpha_candidate.structurally_valid
            and self.alpha_phase6.accepted
            and not self.alpha_candidate.evaluation.accepted
            and self.alpha_candidate.evaluation.rejection_reason
            == "protected_capability_regression"
            and self.beta_invocation.model_generated
            and self.beta_validation.accepted
            and self.beta_candidate.structurally_valid
            and self.beta_phase6.accepted
            and self.beta_candidate.evaluation.accepted
            and self.lifecycle_transition.accepted
            and self.lifecycle_certificate.active_generator_hash
            == self.active.active_manifest.generator_policy_hash
            and self.lifecycle_certificate.active_planner_hash
            == self.active.active_manifest.planner_policy_hash
            and self.beta_candidate.manifest.generator_policy_hash
            != self.active.active_manifest.generator_policy_hash
            and self.beta_candidate.manifest.planner_policy_hash
            != self.active.active_manifest.planner_policy_hash
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        content = {
            "schema_id": "runtime.v3.phase11b.evidence_summary.v1",
            "contract_version": PHASE11B_CONTRACT_VERSION,
            "accepted": self.accepted,
            "active_package_hash": self.active.active_manifest.package_hash,
            "active_state_hash": self.active.active_state.state_hash,
            "active_generator_hash": self.active.active_manifest.generator_policy_hash,
            "active_planner_hash": self.active.active_manifest.planner_policy_hash,
            "invalid_invocation_hash": self.invalid_invocation.report_hash,
            "invalid_validation_hash": self.invalid_validation.report_hash,
            "alpha_invocation_hash": self.alpha_invocation.report_hash,
            "alpha_candidate_fixture_hash": self.alpha_candidate.fixture_hash,
            "alpha_phase6_hash": self.alpha_phase6.evidence_hash,
            "alpha_rejection_reason": self.alpha_candidate.evaluation.rejection_reason,
            "beta_invocation_hash": self.beta_invocation.report_hash,
            "beta_candidate_fixture_hash": self.beta_candidate.fixture_hash,
            "beta_phase6_hash": self.beta_phase6.evidence_hash,
            "beta_candidate_package_hash": self.beta_candidate.manifest.package_hash,
            "beta_candidate_model_identity_hash": (
                self.beta_candidate.manifest.model_identity_hash
            ),
            "successor_generator_hash": self.beta_candidate.manifest.generator_policy_hash,
            "successor_planner_hash": self.beta_candidate.manifest.planner_policy_hash,
            "lifecycle_certificate_hash": self.lifecycle_certificate.certificate_hash,
            "lifecycle_transition_hash": self.lifecycle_transition.semantic_report_hash,
            "budget": {
                "budget_hash": self.active.budget.budget_hash,
                "generator_invocations": 3,
                "candidate_realizations": 2,
                "candidate_evaluations": 2,
                "manual_repairs": 0,
            },
            "heldout_material_consumed": False,
            "deterministic_generator_replay": True,
            "proposal_invocations": 3,
            "generator_replay_invocations": 3,
            "claim_boundary": {
                "model_generated_candidate_realized": True,
                "model_generated_candidate_rejected": True,
                "later_fresh_candidate_accepted": True,
                "candidate_promoted": False,
                "successor_generator_planner_installed": True,
                "modified_successor_generator_used_recursively": False,
                "phase11_exit_closed": False,
            },
        }
        result = dict(content)
        result["summary_hash"] = canonical_json_hash(content)
        return result

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "active": self.active.to_json(),
            "wrapper_predecessor_manifest": self.wrapper_predecessor.manifest.to_json(),
            "invalid_invocation": self.invalid_invocation.to_json(),
            "invalid_validation": self.invalid_validation.to_json(),
            "alpha_invocation": self.alpha_invocation.to_json(),
            "alpha_validation": self.alpha_validation.to_json(),
            "alpha_candidate": self.alpha_candidate.to_json(),
            "alpha_phase6": self.alpha_phase6.to_json(),
            "beta_invocation": self.beta_invocation.to_json(),
            "beta_validation": self.beta_validation.to_json(),
            "beta_candidate": self.beta_candidate.to_json(),
            "beta_phase6": self.beta_phase6.to_json(),
            "lifecycle_certificate": self.lifecycle_certificate.to_json(),
            "lifecycle_transition": self.lifecycle_transition.to_json(),
            "summary": self.summary_json(),
        }


def build_phase11b_reference(output_root: Path) -> Phase11BReference:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 11B reference already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    active = build_phase11b_active_fixture(root / "active_fixture")
    wrapper = _build_wrapper_predecessor(active, root / "wrapper_predecessor")

    invalid_input = _model_input(
        active,
        invocation_index=0,
        observation={
            "schema_id": "runtime.v3.phase11b.observation.v1",
            "active_state_hash": active.active_state.state_hash,
            "prior_result": None,
            "heldout_answer_material_present": False,
        },
    )
    invalid_invocation = _generate_replayed(active, invalid_input)
    invalid_validation = validate_phase11b_program(invalid_invocation)

    alpha_input = _model_input(
        active,
        invocation_index=1,
        observation={
            "schema_id": "runtime.v3.phase11b.observation.v1",
            "active_state_hash": active.active_state.state_hash,
            "prior_validation_hash": invalid_validation.report_hash,
            "prior_accepted": invalid_validation.accepted,
            "active_package_unchanged": True,
            "heldout_answer_material_present": False,
        },
    )
    alpha_invocation = _generate_replayed(active, alpha_input)
    alpha_validation = validate_phase11b_program(alpha_invocation)
    alpha_candidate = build_phase11b_candidate_fixture(
        active,
        alpha_invocation,
        alpha_validation,
        root / "alpha_semantic_candidate",
    )
    alpha_phase6 = _realize_candidate(
        wrapper,
        active,
        alpha_candidate,
        root / "alpha_phase6_candidate",
    )

    beta_input = _model_input(
        active,
        invocation_index=2,
        observation={
            "schema_id": "runtime.v3.phase11b.observation.v1",
            "active_state_hash": active.active_state.state_hash,
            "prior_candidate_evaluation_hash": alpha_candidate.evaluation.report_hash,
            "prior_candidate_phase6_hash": alpha_phase6.evidence_hash,
            "prior_candidate_accepted": alpha_candidate.evaluation.accepted,
            "prior_candidate_rejection_reason": (
                alpha_candidate.evaluation.rejection_reason
            ),
            "active_package_unchanged": True,
            "heldout_answer_material_present": False,
        },
    )
    beta_invocation = _generate_replayed(active, beta_input)
    beta_validation = validate_phase11b_program(beta_invocation)
    beta_candidate = build_phase11b_candidate_fixture(
        active,
        beta_invocation,
        beta_validation,
        root / "beta_semantic_candidate",
    )
    beta_phase6 = _realize_candidate(
        wrapper,
        active,
        beta_candidate,
        root / "beta_phase6_candidate",
    )
    if (
        beta_candidate.certificate is None
        or beta_candidate.candidate_state is None
        or beta_candidate.update is None
        or beta_candidate.heldout_policy is None
    ):
        raise ValueError("beta candidate Gate D evidence is unavailable")
    realization = beta_phase6.phase6.report.realization
    if realization is None or not realization.rollback.verified:
        raise ValueError("beta Phase 6 rollback is unavailable")
    lifecycle_certificate = replace(
        beta_candidate.certificate,
        architecture_compatibility_hash=str(beta_phase6.embedded_report["report_hash"]),
        resource_evidence_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v3.phase11b.lifecycle_resource_evidence.v1",
                "training_semantic_hash": beta_candidate.training_semantic_hash,
                "phase6_usage_hash": realization.resources.usage_hash,
                "phase6_environment_hash": realization.environment.environment_hash,
                "changed_file_count": len(realization.changes),
                "rollback_hash": realization.rollback.rollback_hash,
                "generator_invocations": 3,
                "candidate_realizations": 2,
                "candidate_evaluations": 2,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=realization.rollback.rollback_hash,
    )
    lifecycle_transition = validate_phase9_transition(
        active.active_state,
        beta_candidate.update,
        beta_candidate.candidate_state,
        lifecycle_certificate,
        beta_candidate.heldout_policy,
    )
    reference = Phase11BReference(
        root=root,
        active=active,
        wrapper_predecessor=wrapper,
        invalid_invocation=invalid_invocation,
        invalid_validation=invalid_validation,
        alpha_invocation=alpha_invocation,
        alpha_validation=alpha_validation,
        alpha_candidate=alpha_candidate,
        alpha_phase6=alpha_phase6,
        beta_invocation=beta_invocation,
        beta_validation=beta_validation,
        beta_candidate=beta_candidate,
        beta_phase6=beta_phase6,
        lifecycle_certificate=lifecycle_certificate,
        lifecycle_transition=lifecycle_transition,
    )
    if not reference.accepted:
        raise ValueError("Phase 11B portable lifecycle did not close")
    retained = root / "retained"
    _write_json(retained / "reference.json", reference.to_json())
    _write_json(retained / "summary.json", reference.summary_json())
    return reference


__all__ = [
    "EMBEDDED_PHASE11_ROOT",
    "Phase11BPhase6Evidence",
    "Phase11BReference",
    "build_phase11b_reference",
    "phase11b_phase6_budget",
]
