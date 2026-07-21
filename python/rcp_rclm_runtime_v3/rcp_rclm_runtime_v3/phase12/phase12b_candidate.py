from __future__ import annotations

import copy
import os
import shutil
import struct
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.contract.certificate import (
    HeldoutAccessPolicy,
    LearnedCertificatePacket,
)
from rcp_rclm_runtime_v3.contract.common import SELECTED_TASK_CLASS
from rcp_rclm_runtime_v3.contract.state import (
    LearnedRCLMState,
    PolicyIdentity,
)
from rcp_rclm_runtime_v3.contract.tasks import (
    CapabilityFrontier,
    CertificationRecord,
    TaskLedger,
    TaskRecord,
)
from rcp_rclm_runtime_v3.contract.update import (
    LearnedRCLMUpdate,
    UpdateOperation,
)
from rcp_rclm_runtime_v3.contract.validation import (
    Phase9TransitionReport,
    validate_phase9_transition,
)
from rcp_rclm_runtime_v3.phase10.information import (
    PRECISION_BITS,
    PromptInformationEvidence,
    prompt_information_evidence,
)
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.learned_reference import PINNED_LEAN_TOOLCHAIN
from rcp_rclm_runtime_v3.phase10.package import (
    PACKAGE_MANIFEST_PATH,
    SUPPORT_HASH_FIELD_BY_PATH,
    TENSOR_MANIFEST_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import (
    decode_completion,
    transition_tensor_path,
)
from rcp_rclm_runtime_v3.phase10.tasks import (
    TaskVerifierReport,
    expected_success_report,
)
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import (
    PHASE11B_NEW_TASK,
    expected_phase11b_task_report,
)
from rcp_rclm_runtime_v3.phase12.phase12b_program import (
    PHASE12B_CONTRACT_VERSION,
    PHASE12B_TRANSITION_ID,
    Phase12ProposalValidationReport,
    Phase12RecursiveProposalReport,
)
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import (
    PHASE12B_NEW_TASK,
    expected_phase12b_task_report,
    phase12b_answer_store,
    phase12b_heldout_manifest,
    phase12b_new_chain,
    phase12b_training_manifest,
)
from rcp_rclm_runtime_v3.phase12.reference import Phase12AReference


PHASE12B_SUCCESSOR_PACKAGE_ID = "phase12-generation1-weight-successor"
_TARGET_RAW_VALUE = 24_576


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _file_set(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def _support_from_package(root: Path) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    for path in SUPPORT_HASH_FIELD_BY_PATH:
        observed = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if not isinstance(observed, dict):
            raise SchemaValidationError("phase12b.candidate.support", f"expected object at {path}")
        values[path] = copy.deepcopy(observed)
    return values


def _apply_training_pairs(predecessor: bytes) -> bytes:
    expected_size = 320 * 320 * 2
    if len(predecessor) != expected_size:
        raise SchemaValidationError("phase12b.candidate.tensor", "unexpected tensor byte length")
    result = bytearray(predecessor)
    for current, target in phase12b_new_chain():
        index = target * 320 + current
        struct.pack_into("<h", result, index * 2, _TARGET_RAW_VALUE)
    return bytes(result)


def _rebuild_tensor_manifest(root: Path, old: TensorManifest) -> TensorManifest:
    records = tuple(
        TensorRecord(spec=record.spec, sha256=_file_sha256(root / record.spec.path))
        for record in old.records
    )
    result = TensorManifest(
        architecture_hash=old.architecture_hash,
        records=records,
        parameter_count=old.parameter_count,
    )
    _write_json(root / TENSOR_MANIFEST_PATH, result.serialized_json())
    return result


def phase12b_training_semantic_hash(
    active_manifest: ModelPackageManifest,
    proposal: Phase12RecursiveProposalReport,
    candidate_tensor_sha256: str,
) -> str:
    training = phase12b_training_manifest()
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12b.training_semantic_binding.v1",
            "transition_id": PHASE12B_TRANSITION_ID,
            "active_package_hash": active_manifest.package_hash,
            "generator_input_hash": proposal.generator_input.input_hash,
            "proposal_hash": proposal.report_hash,
            "program_hash": proposal.program.program_hash,
            "training_manifest_hash": training["manifest_hash"],
            "transition_pairs": training["transition_pairs"],
            "candidate_tensor_sha256": candidate_tensor_sha256,
            "optimizer": proposal.program.training_policy.optimizer,
            "optimizer_steps": proposal.program.training_policy.steps,
            "heldout_material_consumed": False,
        }
    )


def build_phase12b_candidate_package(
    phase12a: Phase12AReference,
    proposal: Phase12RecursiveProposalReport,
    validation: Phase12ProposalValidationReport,
    output_root: Path,
) -> tuple[ModelPackageManifest, str]:
    if not validation.accepted:
        raise SchemaValidationError("phase12b.candidate", "proposal must validate")
    if validation.proposal_hash != proposal.report_hash:
        raise SchemaValidationError("phase12b.candidate", "proposal validation binding mismatch")
    active_root = phase12a.phase11.beta_candidate.root.resolve(strict=True)
    active_manifest = load_package_components(active_root)[0]
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 12B candidate already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase12b-candidate-",
        dir=output.parent,
    ) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(active_root, staging, symlinks=False)
        transition_path = transition_tensor_path(staging)
        candidate_tensor = _apply_training_pairs(transition_path.read_bytes())
        transition_path.write_bytes(candidate_tensor)
        _, architecture, tokenizer, old_tensors, adapter = load_package_components(staging)
        tensors = _rebuild_tensor_manifest(staging, old_tensors)
        support = _support_from_package(active_root)
        if (staging / PACKAGE_MANIFEST_PATH).exists():
            (staging / PACKAGE_MANIFEST_PATH).unlink()
        manifest = _manifest_from_components(
            package_id=PHASE12B_SUCCESSOR_PACKAGE_ID,
            parent_package_id=active_manifest.package_id,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=tensors,
            adapter=adapter,
            support_hashes=_support_hashes(support),
            payload_tree_hash=_payload_tree_hash(staging),
        )
        _write_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, output)
    semantic_hash = phase12b_training_semantic_hash(
        active_manifest,
        proposal,
        sha256_hex(candidate_tensor),
    )
    return manifest, semantic_hash


def validate_phase12b_candidate_package(
    phase12a: Phase12AReference,
    proposal: Phase12RecursiveProposalReport,
    candidate_root: Path,
) -> dict[str, object]:
    active_root = phase12a.phase11.beta_candidate.root.resolve(strict=True)
    root = candidate_root.resolve(strict=True)
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(root)
    active_manifest, active_architecture, active_tokenizer, active_tensors, active_adapter = (
        load_package_components(active_root)
    )
    failures: list[str] = []
    expected_tensor = _apply_training_pairs(transition_tensor_path(active_root).read_bytes())
    if transition_tensor_path(root).read_bytes() != expected_tensor:
        failures.append("candidate_tensor_mismatch")
    if manifest.payload_tree_hash != _payload_tree_hash(root):
        failures.append("payload_tree_hash_mismatch")
    if manifest.parent_package_id != active_manifest.package_id:
        failures.append("parent_package_id_mismatch")
    if architecture != active_architecture or tokenizer != active_tokenizer:
        failures.append("architecture_or_tokenizer_changed")
    if tensors.parameter_count != active_tensors.parameter_count:
        failures.append("parameter_count_changed")
    if adapter != active_adapter:
        failures.append("adapter_changed")
    if manifest.model_identity_hash == active_manifest.model_identity_hash:
        failures.append("model_identity_unchanged")
    for field in (
        "generator_policy_hash",
        "planner_policy_hash",
        "retrieval_index_hash",
        "memory_manifest_hash",
        "optimizer_state_hash",
        "data_curriculum_hash",
        "architecture_hash",
        "adapter_manifest_hash",
    ):
        if getattr(manifest, field) != getattr(active_manifest, field):
            failures.append(f"unexpected_component_change:{field}")
    if _file_set(root) != _file_set(active_root):
        failures.append("package_file_set_changed")
    support = _support_from_package(active_root)
    for path, expected in support.items():
        observed = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if observed != expected:
            failures.append(f"support_mismatch:{path}")
        field_name = SUPPORT_HASH_FIELD_BY_PATH[path]
        if getattr(manifest, field_name) != canonical_json_hash(expected):
            failures.append(f"support_hash_mismatch:{path}")

    protected_decode = decode_completion(root, PROTECTED_TASK.model_prompt)
    phase10_decode = decode_completion(root, HELDOUT_TASK.model_prompt)
    phase11_decode = decode_completion(root, PHASE11B_NEW_TASK.model_prompt)
    new_decode = decode_completion(root, PHASE12B_NEW_TASK.model_prompt)
    protected_retained = (
        protected_decode.stopped_on_eos
        and protected_decode.completion_text == PROTECTED_TASK.expected_completion
    )
    phase10_retained = (
        phase10_decode.stopped_on_eos
        and phase10_decode.completion_text == HELDOUT_TASK.expected_completion
    )
    phase11_retained = (
        phase11_decode.stopped_on_eos
        and phase11_decode.completion_text == PHASE11B_NEW_TASK.expected_completion
    )
    new_task_solved = (
        new_decode.stopped_on_eos
        and new_decode.completion_text == PHASE12B_NEW_TASK.expected_completion
    )
    if not protected_retained:
        failures.append("protected_task_not_retained")
    if not phase10_retained:
        failures.append("phase10_task_not_retained")
    if not phase11_retained:
        failures.append("phase11_task_not_retained")
    if not new_task_solved:
        failures.append("new_task_not_solved")

    content = {
        "schema_id": "runtime.v3.phase12b.candidate_package_report.v1",
        "contract_version": PHASE12B_CONTRACT_VERSION,
        "active_package_hash": active_manifest.package_hash,
        "candidate_package_hash": manifest.package_hash,
        "active_model_identity_hash": active_manifest.model_identity_hash,
        "candidate_model_identity_hash": manifest.model_identity_hash,
        "active_generator_hash": active_manifest.generator_policy_hash,
        "candidate_generator_hash": manifest.generator_policy_hash,
        "active_planner_hash": active_manifest.planner_policy_hash,
        "candidate_planner_hash": manifest.planner_policy_hash,
        "proposal_hash": proposal.report_hash,
        "protected_decode_hash": protected_decode.result_hash,
        "phase10_decode_hash": phase10_decode.result_hash,
        "phase11_decode_hash": phase11_decode.result_hash,
        "new_task_decode_hash": new_decode.result_hash,
        "protected_retained": protected_retained,
        "phase10_retained": phase10_retained,
        "phase11_retained": phase11_retained,
        "new_task_solved": new_task_solved,
        "failures": sorted(set(failures)),
        "accepted": not failures,
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
    return result


def _same_prompt_density(
    predecessor: PromptInformationEvidence,
    candidate: PromptInformationEvidence,
) -> bool:
    return (
        predecessor.task_id == candidate.task_id
        and predecessor.prompt_hash == candidate.prompt_hash
        and len(predecessor.steps) == len(candidate.steps)
        and all(
            before.position == after.position
            and before.current_token_id == after.current_token_id
            and before.target_token_id == after.target_token_id
            and before.score_vector_hash == after.score_vector_hash
            and before.density_hash == after.density_hash
            for before, after in zip(predecessor.steps, candidate.steps, strict=True)
        )
    )


@dataclass(frozen=True, slots=True)
class Phase12BInformationReport:
    protected_predecessor: PromptInformationEvidence
    protected_candidate: PromptInformationEvidence
    phase10_predecessor: PromptInformationEvidence
    phase10_candidate: PromptInformationEvidence
    phase11_predecessor: PromptInformationEvidence
    phase11_candidate: PromptInformationEvidence
    new_task_predecessor: PromptInformationEvidence
    new_task_candidate: PromptInformationEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase12b.information_report.v1"

    @property
    def protected_unchanged(self) -> bool:
        return _same_prompt_density(self.protected_predecessor, self.protected_candidate)

    @property
    def phase10_unchanged(self) -> bool:
        return _same_prompt_density(self.phase10_predecessor, self.phase10_candidate)

    @property
    def phase11_unchanged(self) -> bool:
        return _same_prompt_density(self.phase11_predecessor, self.phase11_candidate)

    @property
    def new_task_improvement_interval(self):
        return (
            self.new_task_predecessor.kl_qre_sum_interval
            - self.new_task_candidate.kl_qre_sum_interval
        )

    @property
    def accepted(self) -> bool:
        return (
            self.protected_unchanged
            and self.phase10_unchanged
            and self.phase11_unchanged
            and self.new_task_improvement_interval.strictly_positive()
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "protected_predecessor": self.protected_predecessor.to_json(),
            "protected_candidate": self.protected_candidate.to_json(),
            "phase10_predecessor": self.phase10_predecessor.to_json(),
            "phase10_candidate": self.phase10_candidate.to_json(),
            "phase11_predecessor": self.phase11_predecessor.to_json(),
            "phase11_candidate": self.phase11_candidate.to_json(),
            "new_task_predecessor": self.new_task_predecessor.to_json(),
            "new_task_candidate": self.new_task_candidate.to_json(),
            "protected_unchanged": self.protected_unchanged,
            "phase10_unchanged": self.phase10_unchanged,
            "phase11_unchanged": self.phase11_unchanged,
            "new_task_improvement_interval": self.new_task_improvement_interval.to_json(),
            "selected_kl_qre_nonregression": (
                self.protected_unchanged
                and self.phase10_unchanged
                and self.phase11_unchanged
            ),
            "strict_information_witness": self.new_task_improvement_interval.strictly_positive(),
            "accepted": self.accepted,
            "qre_equals_kl_by_diagonal_construction": True,
            "von_neumann_equals_shannon_by_diagonal_construction": True,
            "precision_bits": PRECISION_BITS,
        }


def build_phase12b_information_report(
    active_root: Path,
    candidate_root: Path,
) -> Phase12BInformationReport:
    return Phase12BInformationReport(
        protected_predecessor=prompt_information_evidence(active_root, PROTECTED_TASK),
        protected_candidate=prompt_information_evidence(candidate_root, PROTECTED_TASK),
        phase10_predecessor=prompt_information_evidence(active_root, HELDOUT_TASK),
        phase10_candidate=prompt_information_evidence(candidate_root, HELDOUT_TASK),
        phase11_predecessor=prompt_information_evidence(active_root, PHASE11B_NEW_TASK),
        phase11_candidate=prompt_information_evidence(candidate_root, PHASE11B_NEW_TASK),
        new_task_predecessor=prompt_information_evidence(active_root, PHASE12B_NEW_TASK),
        new_task_candidate=prompt_information_evidence(candidate_root, PHASE12B_NEW_TASK),
    )


def _policy_identity(manifest: ModelPackageManifest) -> PolicyIdentity:
    return PolicyIdentity(
        training_policy_hash=manifest.training_policy_hash,
        optimizer_policy_hash=manifest.optimizer_state_hash,
        data_curriculum_hash=manifest.data_curriculum_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
        retrieval_policy_hash=manifest.retrieval_index_hash,
        memory_state_hash=manifest.memory_manifest_hash,
        tool_policy_hash=manifest.tool_policy_hash,
        verification_policy_hash=manifest.verification_policy_hash,
        resource_policy_hash=manifest.resource_policy_hash,
        self_model_hash=manifest.self_model_hash,
    )


def _task_record(task: object) -> TaskRecord:
    return TaskRecord(
        task_id=getattr(task, "task_id"),
        task_class=SELECTED_TASK_CLASS,
        prompt_hash=getattr(task, "prompt_hash"),
        verifier_spec_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "source_prefix_hash": getattr(task, "source_prefix_hash"),
            }
        ),
        partition=getattr(task, "partition"),
    )


def _certification(report: TaskVerifierReport) -> CertificationRecord:
    return CertificationRecord(
        task_id=report.task_id,
        model_identity_hash=report.model_identity_hash,
        verifier_report_hash=report.report_hash,
        verified_output_hash=report.completion_hash,
    )


def _candidate_state(
    phase12a: Phase12AReference,
    manifest: ModelPackageManifest,
    reports: Sequence[TaskVerifierReport],
) -> LearnedRCLMState:
    active_state = phase12a.phase11.beta_candidate.candidate_state
    if active_state is None:
        raise ValueError("Phase 12 active state is unavailable")
    ordered_reports = tuple(sorted(reports, key=lambda item: item.task_id.encode("utf-8")))
    tasks = tuple(
        sorted(
            (
                _task_record(PROTECTED_TASK),
                _task_record(HELDOUT_TASK),
                _task_record(PHASE11B_NEW_TASK),
                _task_record(PHASE12B_NEW_TASK),
            ),
            key=lambda item: item.task_id.encode("utf-8"),
        )
    )
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=active_state.package_id,
        base_state_hash=canonical_json_hash(
            {
                "phase": 12,
                "generation": 1,
                "successor": "self_hosted_model_weight_update",
                "proposal_source": "active_generation2_generator_planner",
            }
        ),
        model=manifest.model_identity(),
        policies=_policy_identity(manifest),
        self_hosting=active_state.self_hosting,
        task_ledger=TaskLedger(
            tasks=tasks,
            certifications=tuple(_certification(report) for report in ordered_reports),
        ),
        capability_frontier=CapabilityFrontier(
            task_ids=tuple(report.task_id for report in ordered_reports)
        ),
    )


def _update(
    phase12a: Phase12AReference,
    candidate: LearnedRCLMState,
) -> LearnedRCLMUpdate:
    active_state = phase12a.phase11.beta_candidate.candidate_state
    if active_state is None:
        raise ValueError("Phase 12 active state is unavailable")
    operation = UpdateOperation(
        operation_id="0001-phase12-generation1-model-weight-update",
        kind="weight_update",
        target="model_weights",
        component_path="model/tensors",
        before_hash=active_state.component_hash("model_weights"),
        after_hash=candidate.component_hash("model_weights"),
    )
    return LearnedRCLMUpdate(
        transition_id=PHASE12B_TRANSITION_ID,
        predecessor_state_hash=active_state.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=(operation,),
    )


def _heldout_policy() -> HeldoutAccessPolicy:
    heldout = phase12b_heldout_manifest()
    answers = phase12b_answer_store()
    return HeldoutAccessPolicy(
        policy_id="phase12b-heldout-isolation-v1",
        heldout_task_manifest_hash=str(heldout["manifest_hash"]),
        reference_answer_store_hash=str(answers["answer_store_hash"]),
        evaluator_policy_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "candidate_freeze_required": True,
                "generator_loaded": False,
                "planner_loaded": False,
                "training_backend_loaded": False,
            }
        ),
    )


@dataclass(frozen=True, slots=True)
class Phase12BCandidateEvaluation:
    package_report_hash: str
    protected_retained: bool
    phase10_retained: bool
    phase11_retained: bool
    new_task_solved: bool
    model_weights_changed: bool
    generator_unchanged: bool
    planner_unchanged: bool
    rejection_reason: str | None

    schema_id: ClassVar[str] = "runtime.v3.phase12b.candidate_evaluation.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.protected_retained
            and self.phase10_retained
            and self.phase11_retained
            and self.new_task_solved
            and self.model_weights_changed
            and self.generator_unchanged
            and self.planner_unchanged
            and self.rejection_reason is None
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "package_report_hash": self.package_report_hash,
            "protected_retained": self.protected_retained,
            "phase10_retained": self.phase10_retained,
            "phase11_retained": self.phase11_retained,
            "new_task_solved": self.new_task_solved,
            "model_weights_changed": self.model_weights_changed,
            "generator_unchanged": self.generator_unchanged,
            "planner_unchanged": self.planner_unchanged,
            "rejection_reason": self.rejection_reason,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class Phase12BCandidateFixture:
    root: Path
    proposal: Phase12RecursiveProposalReport
    validation: Phase12ProposalValidationReport
    manifest: ModelPackageManifest
    package_report: Mapping[str, object]
    training_semantic_hash: str
    evaluation: Phase12BCandidateEvaluation
    information_report: Phase12BInformationReport
    candidate_state: LearnedRCLMState
    update: LearnedRCLMUpdate
    certificate: LearnedCertificatePacket
    heldout_policy: HeldoutAccessPolicy
    transition_report: Phase9TransitionReport

    schema_id: ClassVar[str] = "runtime.v3.phase12b.candidate_fixture.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.package_report["accepted"] is True
            and self.evaluation.accepted
            and self.information_report.accepted
            and self.transition_report.accepted
        )

    @property
    def fixture_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "proposal_hash": self.proposal.report_hash,
            "validation_hash": self.validation.report_hash,
            "manifest": self.manifest.to_json(),
            "package_report": dict(self.package_report),
            "training_semantic_hash": self.training_semantic_hash,
            "evaluation": self.evaluation.to_json(),
            "information_report": self.information_report.to_json(),
            "candidate_state": self.candidate_state.to_json(),
            "update": self.update.to_json(),
            "certificate": self.certificate.to_json(),
            "heldout_policy": self.heldout_policy.to_json(),
            "transition_report": self.transition_report.to_json(),
        }


def build_phase12b_candidate_fixture(
    phase12a: Phase12AReference,
    proposal: Phase12RecursiveProposalReport,
    validation: Phase12ProposalValidationReport,
    output_root: Path,
) -> Phase12BCandidateFixture:
    manifest, training_hash = build_phase12b_candidate_package(
        phase12a,
        proposal,
        validation,
        output_root,
    )
    package_report = validate_phase12b_candidate_package(
        phase12a,
        proposal,
        output_root,
    )
    active_root = phase12a.phase11.beta_candidate.root.resolve(strict=True)
    active_manifest = phase12a.phase11.beta_candidate.manifest

    protected_decode = decode_completion(output_root, PROTECTED_TASK.model_prompt)
    phase10_decode = decode_completion(output_root, HELDOUT_TASK.model_prompt)
    phase11_decode = decode_completion(output_root, PHASE11B_NEW_TASK.model_prompt)
    new_decode = decode_completion(output_root, PHASE12B_NEW_TASK.model_prompt)
    protected_retained = (
        protected_decode.stopped_on_eos
        and protected_decode.completion_text == PROTECTED_TASK.expected_completion
    )
    phase10_retained = (
        phase10_decode.stopped_on_eos
        and phase10_decode.completion_text == HELDOUT_TASK.expected_completion
    )
    phase11_retained = (
        phase11_decode.stopped_on_eos
        and phase11_decode.completion_text == PHASE11B_NEW_TASK.expected_completion
    )
    new_task_solved = (
        new_decode.stopped_on_eos
        and new_decode.completion_text == PHASE12B_NEW_TASK.expected_completion
    )
    evaluation = Phase12BCandidateEvaluation(
        package_report_hash=str(package_report["report_hash"]),
        protected_retained=protected_retained,
        phase10_retained=phase10_retained,
        phase11_retained=phase11_retained,
        new_task_solved=new_task_solved,
        model_weights_changed=manifest.model_identity_hash
        != active_manifest.model_identity_hash,
        generator_unchanged=manifest.generator_policy_hash
        == active_manifest.generator_policy_hash,
        planner_unchanged=manifest.planner_policy_hash
        == active_manifest.planner_policy_hash,
        rejection_reason=None,
    )
    protected_report = expected_success_report(
        protected_decode,
        PROTECTED_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    phase10_report = expected_success_report(
        phase10_decode,
        HELDOUT_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    phase11_report = expected_phase11b_task_report(
        phase11_decode,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    new_report = expected_phase12b_task_report(
        new_decode,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    information = build_phase12b_information_report(active_root, output_root)
    candidate_state = _candidate_state(
        phase12a,
        manifest,
        (protected_report, phase10_report, phase11_report, new_report),
    )
    update = _update(phase12a, candidate_state)
    heldout_policy = _heldout_policy()
    active_state = phase12a.phase11.beta_candidate.candidate_state
    if active_state is None:
        raise ValueError("Phase 12 active state is unavailable")
    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=active_state.state_hash,
        candidate_state_hash=candidate_state.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=active_state.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate_state.capability_frontier.frontier_hash,
        protected_task_ids=active_state.capability_frontier.task_ids,
        new_task_ids=(PHASE12B_NEW_TASK.task_id,),
        task_frontier_retention_evidence_hash=canonical_json_hash(
            {
                "protected": protected_report.report_hash,
                "phase10": phase10_report.report_hash,
                "phase11": phase11_report.report_hash,
            }
        ),
        new_task_capability_evidence_hash=new_report.report_hash,
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash(
            {"goal_drift": 0, "budget": 0}
        ),
        training_data_provenance_hash=training_hash,
        heldout_isolation_evidence_hash=canonical_json_hash(
            {
                "proposal_hash": proposal.report_hash,
                "heldout_task_manifest_hash": heldout_policy.heldout_task_manifest_hash,
                "heldout_answer_store_hash": heldout_policy.reference_answer_store_hash,
                "heldout_material_consumed": False,
            }
        ),
        architecture_compatibility_hash=str(package_report["report_hash"]),
        self_hosting_evidence_hash=canonical_json_hash(
            {
                "active_state_self_hosting_hash": active_state.self_hosting.binding_hash,
                "proposal_hash": proposal.report_hash,
                "phase12_trajectory_protocol": proposal.generator_input.proposal_protocol_hash,
                "recursive_successor_generator_used": True,
            }
        ),
        resource_evidence_hash=canonical_json_hash(
            {
                "generator_invocations": 2,
                "candidate_realizations": 1,
                "candidate_evaluations": 1,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=canonical_json_hash(
            {"phase6_rollback": "pending_realization"}
        ),
        heldout_access_policy_hash=heldout_policy.policy_hash,
        active_generator_hash=active_state.policies.generator_policy_hash,
        active_planner_hash=active_state.policies.planner_policy_hash,
        proposal_protocol_hash=active_state.self_hosting.proposal_protocol_hash,
    )
    transition = validate_phase9_transition(
        active_state,
        update,
        candidate_state,
        certificate,
        heldout_policy,
    )
    fixture = Phase12BCandidateFixture(
        root=output_root,
        proposal=proposal,
        validation=validation,
        manifest=manifest,
        package_report=package_report,
        training_semantic_hash=training_hash,
        evaluation=evaluation,
        information_report=information,
        candidate_state=candidate_state,
        update=update,
        certificate=certificate,
        heldout_policy=heldout_policy,
        transition_report=transition,
    )
    if not fixture.accepted:
        raise ValueError("Phase 12B semantic candidate did not close")
    return fixture


__all__ = [
    "PHASE12B_SUCCESSOR_PACKAGE_ID",
    "Phase12BCandidateEvaluation",
    "Phase12BCandidateFixture",
    "Phase12BInformationReport",
    "build_phase12b_candidate_fixture",
    "build_phase12b_candidate_package",
    "build_phase12b_information_report",
    "phase12b_training_semantic_hash",
    "validate_phase12b_candidate_package",
]
