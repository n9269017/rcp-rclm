from __future__ import annotations

import copy
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
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
    SelfHostingBinding,
)
from rcp_rclm_runtime_v3.contract.tasks import (
    CapabilityFrontier,
    CertificationRecord,
    TaskLedger,
    TaskRecord,
)
from rcp_rclm_runtime_v3.contract.update import LearnedRCLMUpdate, UpdateOperation
from rcp_rclm_runtime_v3.contract.validation import (
    Phase9TransitionReport,
    validate_phase9_transition,
)
from rcp_rclm_runtime_v3.phase10.information import (
    PRECISION_BITS,
    PromptInformationEvidence,
    prompt_information_evidence,
)
from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    PROTECTED_TASK,
    LeanCompletionTask,
)
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.learned_reference import PINNED_LEAN_TOOLCHAIN
from rcp_rclm_runtime_v3.phase10.package import (
    PACKAGE_MANIFEST_PATH,
    SUPPORT_HASH_FIELD_BY_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import decode_completion
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, expected_success_report
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import (
    PHASE11B_NEW_TASK,
    expected_phase11b_task_report,
)
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import (
    PHASE12B_NEW_TASK,
    expected_phase12b_task_report,
)
from rcp_rclm_runtime_v3.phase12.phase12c_lifecycle import Phase12CReference
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import (
    PHASE12C_NEW_TASK,
    Phase12CRetrievalDecode,
    decode_phase12c_task,
    expected_phase12c_task_report,
)
from rcp_rclm_runtime_v3.phase12.phase12d_program import (
    PHASE12D_CONTRACT_VERSION,
    PHASE12D_TRANSITION_ID,
    Phase12DProposalReport,
    Phase12DProposalValidationReport,
)
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import (
    PHASE12D_NEW_TASK,
    PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
    PHASE12D_SELF_HOSTING_CONTRACT_HASH,
    Phase12DPlannerDecode,
    decode_phase12d_task,
    expected_phase12d_task_report,
    phase12d_answer_store,
    phase12d_generator_policy,
    phase12d_heldout_manifest,
    phase12d_planner_policy,
    phase12d_update_provenance,
)

PHASE12D_SUCCESSOR_PACKAGE_ID: Final[str] = (
    "phase12-generation3-generator-planner-successor"
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


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
            raise SchemaValidationError("phase12d.candidate.support", f"expected object at {path}")
        values[path] = copy.deepcopy(observed)
    return values


def _successor_support(
    active_root: Path,
    active_manifest: ModelPackageManifest,
    proposal: Phase12DProposalReport,
) -> dict[str, dict[str, object]]:
    values = _support_from_package(active_root)
    values["policies/generator_policy.json"] = phase12d_generator_policy(
        active_manifest,
        proposal.program.program_hash,
    )
    values["policies/planner_policy.json"] = phase12d_planner_policy(
        active_manifest,
        proposal.program.program_hash,
    )
    return values


def phase12d_update_semantic_hash(
    active_manifest: ModelPackageManifest,
    proposal: Phase12DProposalReport,
    generator_hash: str,
    planner_hash: str,
) -> str:
    provenance = phase12d_update_provenance(
        active_manifest,
        proposal.program.program_hash,
    )
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12d.update_semantic_binding.v1",
            "transition_id": PHASE12D_TRANSITION_ID,
            "active_package_hash": active_manifest.package_hash,
            "generator_input_hash": proposal.generator_input.input_hash,
            "proposal_hash": proposal.report_hash,
            "program_hash": proposal.program.program_hash,
            "generator_policy_hash": generator_hash,
            "planner_policy_hash": planner_hash,
            "successor_proposal_protocol_hash": PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
            "provenance_hash": provenance["provenance_hash"],
            "training_steps": 0,
            "heldout_material_consumed": False,
        }
    )


def build_phase12d_candidate_package(
    phase12c: Phase12CReference,
    proposal: Phase12DProposalReport,
    validation: Phase12DProposalValidationReport,
    output_root: Path,
) -> tuple[ModelPackageManifest, str]:
    if not validation.accepted:
        raise SchemaValidationError("phase12d.candidate", "proposal must validate")
    if validation.proposal_hash != proposal.report_hash:
        raise SchemaValidationError("phase12d.candidate", "proposal validation binding mismatch")
    active_root = phase12c.semantic_candidate.root.resolve(strict=True)
    active_manifest, architecture, tokenizer, tensors, adapter = load_package_components(active_root)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 12D candidate already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase12d-candidate-",
        dir=output.parent,
    ) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(active_root, staging, symlinks=False)
        support = _successor_support(active_root, active_manifest, proposal)
        for path, value in support.items():
            _write_json(staging / path, value)
        if (staging / PACKAGE_MANIFEST_PATH).exists():
            (staging / PACKAGE_MANIFEST_PATH).unlink()
        manifest = _manifest_from_components(
            package_id=PHASE12D_SUCCESSOR_PACKAGE_ID,
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
    semantic_hash = phase12d_update_semantic_hash(
        active_manifest,
        proposal,
        manifest.generator_policy_hash,
        manifest.planner_policy_hash,
    )
    return manifest, semantic_hash


def validate_phase12d_candidate_package(
    phase12c: Phase12CReference,
    proposal: Phase12DProposalReport,
    candidate_root: Path,
) -> dict[str, object]:
    active_root = phase12c.semantic_candidate.root.resolve(strict=True)
    root = candidate_root.resolve(strict=True)
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(root)
    active_manifest, active_architecture, active_tokenizer, active_tensors, active_adapter = (
        load_package_components(active_root)
    )
    failures: list[str] = []
    if manifest.payload_tree_hash != _payload_tree_hash(root):
        failures.append("payload_tree_hash_mismatch")
    if manifest.parent_package_id != active_manifest.package_id:
        failures.append("parent_package_id_mismatch")
    if architecture != active_architecture or tokenizer != active_tokenizer:
        failures.append("architecture_or_tokenizer_changed")
    if tensors != active_tensors or adapter != active_adapter:
        failures.append("model_or_adapter_changed")
    if manifest.model_identity_hash != active_manifest.model_identity_hash:
        failures.append("model_identity_changed")
    expected_changed = {"generator_policy_hash", "planner_policy_hash"}
    support_fields = {
        "training_policy_hash",
        "optimizer_state_hash",
        "data_curriculum_hash",
        "generator_policy_hash",
        "planner_policy_hash",
        "tool_policy_hash",
        "verification_policy_hash",
        "resource_policy_hash",
        "retrieval_index_hash",
        "memory_manifest_hash",
        "self_model_hash",
        "rng_state_hash",
        "environment_hash",
        "resource_measurement_hash",
    }
    changed_fields = {
        field
        for field in support_fields
        if getattr(manifest, field) != getattr(active_manifest, field)
    }
    if changed_fields != expected_changed:
        failures.append("unexpected_support_change_set")
    if manifest.memory_manifest_hash != active_manifest.memory_manifest_hash:
        failures.append("memory_changed")
    if manifest.retrieval_index_hash != active_manifest.retrieval_index_hash:
        failures.append("retrieval_changed")
    if manifest.generator_policy_hash == active_manifest.generator_policy_hash:
        failures.append("generator_unchanged")
    if manifest.planner_policy_hash == active_manifest.planner_policy_hash:
        failures.append("planner_unchanged")
    if _file_set(root) != _file_set(active_root):
        failures.append("package_file_set_changed")
    expected_support = _successor_support(active_root, active_manifest, proposal)
    for path, expected in expected_support.items():
        observed = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if observed != expected:
            failures.append(f"support_mismatch:{path}")
        field_name = SUPPORT_HASH_FIELD_BY_PATH[path]
        if getattr(manifest, field_name) != canonical_json_hash(expected):
            failures.append(f"support_hash_mismatch:{path}")

    protected_decode = decode_completion(root, PROTECTED_TASK.model_prompt)
    phase10_decode = decode_completion(root, HELDOUT_TASK.model_prompt)
    phase11_decode = decode_completion(root, PHASE11B_NEW_TASK.model_prompt)
    phase12b_decode = decode_completion(root, PHASE12B_NEW_TASK.model_prompt)
    phase12c_decode = decode_phase12c_task(root)
    phase12d_decode = decode_phase12d_task(root)
    retained = {
        "protected": protected_decode.stopped_on_eos
        and protected_decode.completion_text == PROTECTED_TASK.expected_completion,
        "phase10": phase10_decode.stopped_on_eos
        and phase10_decode.completion_text == HELDOUT_TASK.expected_completion,
        "phase11": phase11_decode.stopped_on_eos
        and phase11_decode.completion_text == PHASE11B_NEW_TASK.expected_completion,
        "phase12b": phase12b_decode.stopped_on_eos
        and phase12b_decode.completion_text == PHASE12B_NEW_TASK.expected_completion,
        "phase12c": phase12c_decode.retrieval_hit
        and phase12c_decode.stopped_on_eos
        and phase12c_decode.completion_text == PHASE12C_NEW_TASK.expected_completion,
    }
    for label, accepted in retained.items():
        if not accepted:
            failures.append(f"{label}_task_not_retained")
    new_task_solved = (
        phase12d_decode.planner_route_hit
        and phase12d_decode.generator_capability_hit
        and phase12d_decode.retrieval_hit
        and phase12d_decode.stopped_on_eos
        and phase12d_decode.completion_text == PHASE12D_NEW_TASK.expected_completion
    )
    if not new_task_solved:
        failures.append("new_planner_task_not_solved")

    content = {
        "schema_id": "runtime.v3.phase12d.candidate_package_report.v1",
        "contract_version": PHASE12D_CONTRACT_VERSION,
        "active_package_hash": active_manifest.package_hash,
        "candidate_package_hash": manifest.package_hash,
        "active_model_identity_hash": active_manifest.model_identity_hash,
        "candidate_model_identity_hash": manifest.model_identity_hash,
        "active_generator_hash": active_manifest.generator_policy_hash,
        "candidate_generator_hash": manifest.generator_policy_hash,
        "active_planner_hash": active_manifest.planner_policy_hash,
        "candidate_planner_hash": manifest.planner_policy_hash,
        "active_memory_hash": active_manifest.memory_manifest_hash,
        "candidate_memory_hash": manifest.memory_manifest_hash,
        "active_retrieval_hash": active_manifest.retrieval_index_hash,
        "candidate_retrieval_hash": manifest.retrieval_index_hash,
        "proposal_hash": proposal.report_hash,
        "retained_tasks": retained,
        "new_task_decode": phase12d_decode.to_json(),
        "new_task_solved": new_task_solved,
        "changed_support_fields": sorted(changed_fields),
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


def _effective_task(task: LeanCompletionTask, marker: int) -> LeanCompletionTask:
    return LeanCompletionTask(
        task_id=task.task_id,
        partition=task.partition,
        model_prompt=task.model_prompt[:-1] + bytes((marker,)),
        source_prefix=task.source_prefix,
        expected_completion=task.expected_completion,
    )


@dataclass(frozen=True, slots=True)
class Phase12DInformationReport:
    protected_pairs: Sequence[tuple[PromptInformationEvidence, PromptInformationEvidence]]
    active_retrieval: Phase12CRetrievalDecode
    candidate_retrieval: Phase12CRetrievalDecode
    new_task_predecessor: PromptInformationEvidence
    new_task_candidate: PromptInformationEvidence
    predecessor_planner: Phase12DPlannerDecode
    candidate_planner: Phase12DPlannerDecode

    schema_id: ClassVar[str] = "runtime.v3.phase12d.information_report.v1"

    @property
    def protected_unchanged(self) -> bool:
        return all(_same_prompt_density(before, after) for before, after in self.protected_pairs)

    @property
    def retrieval_unchanged(self) -> bool:
        return self.active_retrieval.to_json() == self.candidate_retrieval.to_json()

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
            and self.retrieval_unchanged
            and not self.predecessor_planner.planner_route_hit
            and not self.predecessor_planner.generator_capability_hit
            and self.candidate_planner.planner_route_hit
            and self.candidate_planner.generator_capability_hit
            and self.candidate_planner.retrieval_hit
            and self.new_task_improvement_interval.strictly_positive()
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "protected_pairs": [
                {"predecessor": before.to_json(), "candidate": after.to_json()}
                for before, after in self.protected_pairs
            ],
            "active_retrieval": self.active_retrieval.to_json(),
            "candidate_retrieval": self.candidate_retrieval.to_json(),
            "new_task_predecessor": self.new_task_predecessor.to_json(),
            "new_task_candidate": self.new_task_candidate.to_json(),
            "predecessor_planner": self.predecessor_planner.to_json(),
            "candidate_planner": self.candidate_planner.to_json(),
            "protected_unchanged": self.protected_unchanged,
            "retrieval_unchanged": self.retrieval_unchanged,
            "new_task_improvement_interval": self.new_task_improvement_interval.to_json(),
            "selected_kl_qre_nonregression": (
                self.protected_unchanged and self.retrieval_unchanged
            ),
            "strict_information_witness": self.new_task_improvement_interval.strictly_positive(),
            "qre_equals_kl_by_diagonal_construction": True,
            "von_neumann_equals_shannon_by_diagonal_construction": True,
            "precision_bits": PRECISION_BITS,
            "accepted": self.accepted,
        }


def build_phase12d_information_report(
    active_root: Path,
    candidate_root: Path,
) -> Phase12DInformationReport:
    raw_protected_tasks = (PROTECTED_TASK, HELDOUT_TASK, PHASE11B_NEW_TASK, PHASE12B_NEW_TASK)
    active_retrieval = decode_phase12c_task(active_root)
    candidate_retrieval = decode_phase12c_task(candidate_root)
    active_retrieval_task = _effective_task(
        PHASE12C_NEW_TASK,
        active_retrieval.route_marker_token_id,
    )
    candidate_retrieval_task = _effective_task(
        PHASE12C_NEW_TASK,
        candidate_retrieval.route_marker_token_id,
    )
    predecessor_planner = decode_phase12d_task(active_root)
    candidate_planner = decode_phase12d_task(candidate_root)
    candidate_effective_task = _effective_task(
        PHASE12D_NEW_TASK,
        candidate_planner.retrieval_decode.route_marker_token_id,
    )
    protected_pairs = tuple(
        (
            prompt_information_evidence(active_root, task),
            prompt_information_evidence(candidate_root, task),
        )
        for task in raw_protected_tasks
    ) + (
        (
            prompt_information_evidence(active_root, active_retrieval_task),
            prompt_information_evidence(candidate_root, candidate_retrieval_task),
        ),
    )
    return Phase12DInformationReport(
        protected_pairs=protected_pairs,
        active_retrieval=active_retrieval,
        candidate_retrieval=candidate_retrieval,
        new_task_predecessor=prompt_information_evidence(active_root, PHASE12D_NEW_TASK),
        new_task_candidate=prompt_information_evidence(candidate_root, candidate_effective_task),
        predecessor_planner=predecessor_planner,
        candidate_planner=candidate_planner,
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
    phase12c: Phase12CReference,
    manifest: ModelPackageManifest,
    reports: Sequence[TaskVerifierReport],
) -> LearnedRCLMState:
    active_state = phase12c.semantic_candidate.candidate_state
    ordered_reports = tuple(sorted(reports, key=lambda item: item.task_id.encode("utf-8")))
    tasks = tuple(
        sorted(
            (
                _task_record(PROTECTED_TASK),
                _task_record(HELDOUT_TASK),
                _task_record(PHASE11B_NEW_TASK),
                _task_record(PHASE12B_NEW_TASK),
                _task_record(PHASE12C_NEW_TASK),
                _task_record(PHASE12D_NEW_TASK),
            ),
            key=lambda item: item.task_id.encode("utf-8"),
        )
    )
    self_hosting = SelfHostingBinding(
        generator_component_hash=manifest.generator_policy_hash,
        planner_component_hash=manifest.planner_policy_hash,
        proposal_protocol_hash=PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
        self_hosting_contract_hash=PHASE12D_SELF_HOSTING_CONTRACT_HASH,
    )
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=active_state.package_id,
        base_state_hash=canonical_json_hash(
            {
                "phase": 12,
                "generation": 3,
                "successor": "self_hosted_generator_planner_update",
                "proposal_source": "promoted_m2_generation2_generator_planner",
                "next_proposal_source": "promoted_m3_generation3_generator_planner",
            }
        ),
        model=manifest.model_identity(),
        policies=_policy_identity(manifest),
        self_hosting=self_hosting,
        task_ledger=TaskLedger(
            tasks=tasks,
            certifications=tuple(_certification(report) for report in ordered_reports),
        ),
        capability_frontier=CapabilityFrontier(
            task_ids=tuple(report.task_id for report in ordered_reports)
        ),
    )


def _update(
    phase12c: Phase12CReference,
    candidate: LearnedRCLMState,
) -> LearnedRCLMUpdate:
    active_state = phase12c.semantic_candidate.candidate_state
    operations = (
        UpdateOperation(
            operation_id="0001-phase12-generation3-generator-policy-update",
            kind="generator_update",
            target="generator_policy",
            component_path="policies/generator_policy.json",
            before_hash=active_state.component_hash("generator_policy"),
            after_hash=candidate.component_hash("generator_policy"),
        ),
        UpdateOperation(
            operation_id="0002-phase12-generation3-planner-policy-update",
            kind="planner_update",
            target="planner_policy",
            component_path="policies/planner_policy.json",
            before_hash=active_state.component_hash("planner_policy"),
            after_hash=candidate.component_hash("planner_policy"),
        ),
    )
    return LearnedRCLMUpdate(
        transition_id=PHASE12D_TRANSITION_ID,
        predecessor_state_hash=active_state.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=operations,
    )


def _heldout_policy() -> HeldoutAccessPolicy:
    heldout = phase12d_heldout_manifest()
    answers = phase12d_answer_store()
    return HeldoutAccessPolicy(
        policy_id="phase12d-heldout-isolation-v1",
        heldout_task_manifest_hash=str(heldout["manifest_hash"]),
        reference_answer_store_hash=str(answers["answer_store_hash"]),
        evaluator_policy_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "candidate_freeze_required": True,
                "planner_route_recomputed": True,
                "retrieval_evidence_recomputed": True,
                "generator_loaded_for_verification": False,
                "planner_loaded_for_verification": False,
                "training_backend_loaded": False,
            }
        ),
    )


@dataclass(frozen=True, slots=True)
class Phase12DCandidateEvaluation:
    package_report_hash: str
    protected_tasks_retained: bool
    new_task_solved: bool
    model_identity_unchanged: bool
    memory_unchanged: bool
    retrieval_unchanged: bool
    generator_changed: bool
    planner_changed: bool
    successor_generation_three: bool
    rejection_reason: str | None

    schema_id: ClassVar[str] = "runtime.v3.phase12d.candidate_evaluation.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.protected_tasks_retained
            and self.new_task_solved
            and self.model_identity_unchanged
            and self.memory_unchanged
            and self.retrieval_unchanged
            and self.generator_changed
            and self.planner_changed
            and self.successor_generation_three
            and self.rejection_reason is None
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "package_report_hash": self.package_report_hash,
            "protected_tasks_retained": self.protected_tasks_retained,
            "new_task_solved": self.new_task_solved,
            "model_identity_unchanged": self.model_identity_unchanged,
            "memory_unchanged": self.memory_unchanged,
            "retrieval_unchanged": self.retrieval_unchanged,
            "generator_changed": self.generator_changed,
            "planner_changed": self.planner_changed,
            "successor_generation_three": self.successor_generation_three,
            "rejection_reason": self.rejection_reason,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class Phase12DCandidateFixture:
    root: Path
    proposal: Phase12DProposalReport
    validation: Phase12DProposalValidationReport
    manifest: ModelPackageManifest
    package_report: Mapping[str, object]
    update_semantic_hash: str
    evaluation: Phase12DCandidateEvaluation
    information_report: Phase12DInformationReport
    candidate_state: LearnedRCLMState
    update: LearnedRCLMUpdate
    certificate: LearnedCertificatePacket
    heldout_policy: HeldoutAccessPolicy
    transition_report: Phase9TransitionReport

    schema_id: ClassVar[str] = "runtime.v3.phase12d.candidate_fixture.v1"

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
            "update_semantic_hash": self.update_semantic_hash,
            "evaluation": self.evaluation.to_json(),
            "information_report": self.information_report.to_json(),
            "candidate_state": self.candidate_state.to_json(),
            "update": self.update.to_json(),
            "certificate": self.certificate.to_json(),
            "heldout_policy": self.heldout_policy.to_json(),
            "transition_report": self.transition_report.to_json(),
        }


def build_phase12d_candidate_fixture(
    phase12c: Phase12CReference,
    proposal: Phase12DProposalReport,
    validation: Phase12DProposalValidationReport,
    output_root: Path,
) -> Phase12DCandidateFixture:
    manifest, update_semantic_hash = build_phase12d_candidate_package(
        phase12c,
        proposal,
        validation,
        output_root,
    )
    package_report = validate_phase12d_candidate_package(
        phase12c,
        proposal,
        output_root,
    )
    active_root = phase12c.semantic_candidate.root.resolve(strict=True)
    active_manifest = phase12c.semantic_candidate.manifest

    protected_decode = decode_completion(output_root, PROTECTED_TASK.model_prompt)
    phase10_decode = decode_completion(output_root, HELDOUT_TASK.model_prompt)
    phase11_decode = decode_completion(output_root, PHASE11B_NEW_TASK.model_prompt)
    phase12b_decode = decode_completion(output_root, PHASE12B_NEW_TASK.model_prompt)
    phase12c_decode = decode_phase12c_task(output_root)
    phase12d_decode = decode_phase12d_task(output_root)
    reports = (
        expected_success_report(
            protected_decode,
            PROTECTED_TASK,
            lean_toolchain=PINNED_LEAN_TOOLCHAIN,
        ),
        expected_success_report(
            phase10_decode,
            HELDOUT_TASK,
            lean_toolchain=PINNED_LEAN_TOOLCHAIN,
        ),
        expected_phase11b_task_report(
            phase11_decode,
            lean_toolchain=PINNED_LEAN_TOOLCHAIN,
        ),
        expected_phase12b_task_report(
            phase12b_decode,
            lean_toolchain=PINNED_LEAN_TOOLCHAIN,
        ),
        expected_phase12c_task_report(
            phase12c_decode,
            lean_toolchain=PINNED_LEAN_TOOLCHAIN,
        ),
        expected_phase12d_task_report(
            phase12d_decode,
            lean_toolchain=PINNED_LEAN_TOOLCHAIN,
        ),
    )
    retained = all(report.solved for report in reports[:-1])
    new_task_solved = reports[-1].solved
    generator_policy = load_json_strict(
        (output_root / "policies/generator_policy.json").read_bytes(),
        require_canonical=True,
    )
    planner_policy = load_json_strict(
        (output_root / "policies/planner_policy.json").read_bytes(),
        require_canonical=True,
    )
    evaluation = Phase12DCandidateEvaluation(
        package_report_hash=str(package_report["report_hash"]),
        protected_tasks_retained=retained,
        new_task_solved=new_task_solved,
        model_identity_unchanged=manifest.model_identity_hash
        == active_manifest.model_identity_hash,
        memory_unchanged=manifest.memory_manifest_hash
        == active_manifest.memory_manifest_hash,
        retrieval_unchanged=manifest.retrieval_index_hash
        == active_manifest.retrieval_index_hash,
        generator_changed=manifest.generator_policy_hash
        != active_manifest.generator_policy_hash,
        planner_changed=manifest.planner_policy_hash != active_manifest.planner_policy_hash,
        successor_generation_three=(
            isinstance(generator_policy, dict)
            and isinstance(planner_policy, dict)
            and generator_policy.get("generation") == 3
            and planner_policy.get("generation") == 3
        ),
        rejection_reason=None,
    )
    information = build_phase12d_information_report(active_root, output_root)
    candidate_state = _candidate_state(phase12c, manifest, reports)
    update = _update(phase12c, candidate_state)
    heldout_policy = _heldout_policy()
    active_state = phase12c.semantic_candidate.candidate_state
    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=active_state.state_hash,
        candidate_state_hash=candidate_state.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=active_state.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate_state.capability_frontier.frontier_hash,
        protected_task_ids=active_state.capability_frontier.task_ids,
        new_task_ids=(PHASE12D_NEW_TASK.task_id,),
        task_frontier_retention_evidence_hash=canonical_json_hash(
            {report.task_id: report.report_hash for report in reports[:-1]}
        ),
        new_task_capability_evidence_hash=reports[-1].report_hash,
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash({"goal_drift": 0, "budget": 0}),
        training_data_provenance_hash=update_semantic_hash,
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
                "candidate_state_self_hosting_hash": candidate_state.self_hosting.binding_hash,
                "proposal_hash": proposal.report_hash,
                "proposal_source": "promoted_m2_generation2_generator_planner",
                "successor_generator_hash": manifest.generator_policy_hash,
                "successor_planner_hash": manifest.planner_policy_hash,
                "successor_proposal_protocol_hash": PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
                "next_proposal_authority": True,
            }
        ),
        resource_evidence_hash=canonical_json_hash(
            {
                "generator_invocations": 5,
                "rejected_attempts": 2,
                "candidate_realizations": 3,
                "candidate_evaluations": 3,
                "training_steps": 1,
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
    fixture = Phase12DCandidateFixture(
        root=output_root,
        proposal=proposal,
        validation=validation,
        manifest=manifest,
        package_report=package_report,
        update_semantic_hash=update_semantic_hash,
        evaluation=evaluation,
        information_report=information,
        candidate_state=candidate_state,
        update=update,
        certificate=certificate,
        heldout_policy=heldout_policy,
        transition_report=transition,
    )
    if not fixture.accepted:
        raise ValueError("Phase 12D semantic candidate did not close")
    return fixture


__all__ = [
    "PHASE12D_SUCCESSOR_PACKAGE_ID",
    "Phase12DCandidateEvaluation",
    "Phase12DCandidateFixture",
    "Phase12DInformationReport",
    "build_phase12d_candidate_fixture",
    "build_phase12d_candidate_package",
    "build_phase12d_information_report",
    "phase12d_update_semantic_hash",
    "validate_phase12d_candidate_package",
]
