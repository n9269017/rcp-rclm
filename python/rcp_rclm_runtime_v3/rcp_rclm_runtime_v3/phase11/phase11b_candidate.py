from __future__ import annotations

import copy
import os
import shutil
import struct
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.rational import Rational

from rcp_rclm_runtime_v3.contract.certificate import HeldoutAccessPolicy, LearnedCertificatePacket
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
from rcp_rclm_runtime_v3.contract.validation import Phase9TransitionReport, validate_phase9_transition
from rcp_rclm_runtime_v3.phase10.adapters import empty_adapter_manifest
from rcp_rclm_runtime_v3.phase10.information import (
    PRECISION_BITS,
    PromptInformationEvidence,
    prompt_information_evidence,
)
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.learned_reference import PINNED_LEAN_TOOLCHAIN
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    PACKAGE_MANIFEST_PATH,
    SUPPORT_HASH_FIELD_BY_PATH,
    TENSOR_MANIFEST_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
    load_package_manifest,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import decode_completion, transition_tensor_path
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, expected_success_report
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord
from rcp_rclm_runtime_v3.phase11.phase11b_bootstrap import Phase11BActiveFixture
from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    PHASE11B_CONTRACT_VERSION,
    PHASE11B_DATA_SELECTION_ALPHA,
    PHASE11B_DATA_SELECTION_BETA,
    PHASE11B_PROMOTED_CANDIDATE_ID,
    PHASE11B_PROPOSAL_PROTOCOL_HASH,
    PHASE11B_REJECTED_CANDIDATE_ID,
    SUCCESSOR_GENERATOR_GENERATION,
    SUCCESSOR_PLANNER_GENERATION,
)
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import (
    PHASE11B_NEW_TASK,
    expected_phase11b_task_report,
    phase11b_alpha_pairs,
    phase11b_answer_store,
    phase11b_beta_pairs,
    phase11b_heldout_manifest,
    phase11b_training_manifest,
)
from rcp_rclm_runtime_v3.phase11.records import GeneratorInvocationReport, ProgramValidationReport

CandidateKind = Literal["alpha_rejected", "beta_promoted"]
_TARGET_RAW_VALUE = 24_576


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _support_from_package(root: Path) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    for path in SUPPORT_HASH_FIELD_BY_PATH:
        observed = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if not isinstance(observed, dict):
            raise SchemaValidationError("phase11b.candidate.support", f"expected object at {path}")
        values[path] = copy.deepcopy(observed)
    return values


def _kind_from_program(invocation: GeneratorInvocationReport) -> CandidateKind:
    selected = set(invocation.program.selected_update_classes)
    expected_base = {"weight_update", "generator_update", "planner_update"}
    if selected == expected_base:
        return "alpha_rejected"
    if selected == expected_base | {"data_curriculum_update"}:
        return "beta_promoted"
    raise SchemaValidationError(
        "phase11b.candidate.program",
        "selected candidate builder supports only alpha or beta update classes",
    )


def _selection_id(kind: CandidateKind) -> str:
    return (
        PHASE11B_DATA_SELECTION_ALPHA
        if kind == "alpha_rejected"
        else PHASE11B_DATA_SELECTION_BETA
    )


def _pairs(kind: CandidateKind) -> Sequence[tuple[int, int]]:
    return phase11b_alpha_pairs() if kind == "alpha_rejected" else phase11b_beta_pairs()


def _apply_pairs(predecessor: bytes, pairs: Sequence[tuple[int, int]]) -> bytes:
    result = bytearray(predecessor)
    expected_size = 320 * 320 * 2
    if len(result) != expected_size:
        raise SchemaValidationError("phase11b.candidate.tensor", "unexpected tensor byte length")
    for current, target in pairs:
        index = target * 320 + current
        struct.pack_into("<h", result, index * 2, _TARGET_RAW_VALUE)
    return bytes(result)


def phase11b_training_semantic_hash(
    active_manifest: ModelPackageManifest,
    invocation: GeneratorInvocationReport,
    kind: CandidateKind,
    candidate_tensor_sha256: str,
) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase11b.training_semantic_binding.v1",
            "active_package_hash": active_manifest.package_hash,
            "generator_input_hash": invocation.generator_input.input_hash,
            "invocation_hash": invocation.report_hash,
            "program_hash": invocation.program.program_hash,
            "selection_id": _selection_id(kind),
            "training_manifest_hash": phase11b_training_manifest(_selection_id(kind))[
                "manifest_hash"
            ],
            "transition_pairs": [
                {"current_token_id": current, "target_token_id": target}
                for current, target in _pairs(kind)
            ],
            "candidate_tensor_sha256": candidate_tensor_sha256,
            "optimizer": invocation.program.training_policy.optimizer,
            "optimizer_steps": invocation.program.training_policy.steps,
            "heldout_material_consumed": False,
        }
    )


def _successor_support(
    active_root: Path,
    active_manifest: ModelPackageManifest,
    invocation: GeneratorInvocationReport,
    kind: CandidateKind,
    candidate_tensor_sha256: str,
) -> dict[str, dict[str, object]]:
    values = _support_from_package(active_root)
    selection_id = _selection_id(kind)
    if kind == "beta_promoted":
        values["training/data_curriculum.json"] = phase11b_training_manifest(selection_id)
    training_hash = phase11b_training_semantic_hash(
        active_manifest,
        invocation,
        kind,
        candidate_tensor_sha256,
    )
    values["policies/generator_policy.json"] = {
        "schema_id": "runtime.v3.phase11b.successor_generator_policy.v1",
        "policy": "installed_self_hosted_typed_mutation_generator",
        "generation": SUCCESSOR_GENERATOR_GENERATION,
        "parent_generator_hash": active_manifest.generator_policy_hash,
        "installed_from_program_hash": invocation.program.program_hash,
        "proposal_protocol_hash": PHASE11B_PROPOSAL_PROTOCOL_HASH,
        "next_proposal_authority": True,
        "direct_candidate_write": False,
        "heldout_material_visible": False,
        "recursive_use_demonstrated": False,
    }
    values["policies/planner_policy.json"] = {
        "schema_id": "runtime.v3.phase11b.successor_planner_policy.v1",
        "policy": "installed_self_hosted_bounded_experiment_planner",
        "generation": SUCCESSOR_PLANNER_GENERATION,
        "parent_planner_hash": active_manifest.planner_policy_hash,
        "installed_from_program_hash": invocation.program.program_hash,
        "proposal_protocol_hash": PHASE11B_PROPOSAL_PROTOCOL_HASH,
        "objective": invocation.program.objective,
        "bounded_within_run": True,
        "fresh_proposal_after_rejection": True,
        "recursive_use_demonstrated": False,
    }
    values["training/training_policy.json"] = {
        "schema_id": "runtime.v3.phase11b.training_policy.v1",
        "backend_authority": "untrusted_external_only",
        "authoritative_evaluation_permitted": False,
        "objective": "model_programmed_sparse_transition_update_v1",
        "optimizer": invocation.program.training_policy.optimizer,
        "optimizer_steps": invocation.program.training_policy.steps,
        "training_semantic_hash": training_hash,
        "heldout_material_consumed": False,
    }
    return values


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


def build_phase11b_candidate_package(
    active: Phase11BActiveFixture,
    invocation: GeneratorInvocationReport,
    validation: ProgramValidationReport,
    output_root: Path,
) -> tuple[ModelPackageManifest, CandidateKind, str]:
    if not validation.accepted:
        raise SchemaValidationError("phase11b.candidate", "program must validate before realization")
    if validation.program_hash != invocation.program.program_hash:
        raise SchemaValidationError("phase11b.candidate", "program validation binding mismatch")
    kind = _kind_from_program(invocation)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 11B candidate already exists: {output}")
    active_root = active.active_package_root.resolve(strict=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11b-candidate-", dir=output.parent) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(active_root, staging, symlinks=False)
        transition_path = transition_tensor_path(staging)
        candidate_tensor = _apply_pairs(transition_path.read_bytes(), _pairs(kind))
        transition_path.write_bytes(candidate_tensor)
        _, architecture, tokenizer, old_tensors, _ = load_package_components(staging)
        tensors = _rebuild_tensor_manifest(staging, old_tensors)
        adapter = empty_adapter_manifest(architecture, tensors.weights_tree_hash)
        _write_json(staging / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
        support = _successor_support(
            active_root,
            active.active_manifest,
            invocation,
            kind,
            sha256_hex(candidate_tensor),
        )
        for path, value in support.items():
            _write_json(staging / path, value)
        if (staging / PACKAGE_MANIFEST_PATH).exists():
            (staging / PACKAGE_MANIFEST_PATH).unlink()
        manifest = _manifest_from_components(
            package_id=(
                PHASE11B_REJECTED_CANDIDATE_ID
                if kind == "alpha_rejected"
                else PHASE11B_PROMOTED_CANDIDATE_ID
            ),
            parent_package_id=active.active_manifest.package_id,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=tensors,
            adapter=adapter,
            support_hashes=_support_hashes(support),
            payload_tree_hash=_payload_tree_hash(staging),
        )
        _write_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, output)
    semantic_hash = phase11b_training_semantic_hash(
        active.active_manifest,
        invocation,
        kind,
        sha256_hex(candidate_tensor),
    )
    return manifest, kind, semantic_hash


def _file_set(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def validate_phase11b_candidate_package(
    active: Phase11BActiveFixture,
    invocation: GeneratorInvocationReport,
    candidate_root: Path,
    kind: CandidateKind,
) -> dict[str, object]:
    root = candidate_root.resolve(strict=True)
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(root)
    active_manifest, active_architecture, active_tokenizer, active_tensors, _ = load_package_components(
        active.active_package_root
    )
    failures: list[str] = []
    expected_tensor = _apply_pairs(
        transition_tensor_path(active.active_package_root).read_bytes(),
        _pairs(kind),
    )
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
    if adapter.status != "absent":
        failures.append("adapter_not_absent")
    if manifest.model_identity_hash == active_manifest.model_identity_hash:
        failures.append("model_identity_unchanged")
    if manifest.generator_policy_hash == active_manifest.generator_policy_hash:
        failures.append("generator_policy_unchanged")
    if manifest.planner_policy_hash == active_manifest.planner_policy_hash:
        failures.append("planner_policy_unchanged")
    if kind == "beta_promoted":
        if manifest.data_curriculum_hash == active_manifest.data_curriculum_hash:
            failures.append("data_curriculum_unchanged")
    elif manifest.data_curriculum_hash != active_manifest.data_curriculum_hash:
        failures.append("alpha_data_curriculum_changed")
    if _file_set(root) != _file_set(active.active_package_root):
        failures.append("package_file_set_changed")
    protected_decode = decode_completion(root, PROTECTED_TASK.model_prompt)
    phase10_heldout_decode = decode_completion(root, HELDOUT_TASK.model_prompt)
    new_decode = decode_completion(root, PHASE11B_NEW_TASK.model_prompt)
    protected_retained = (
        protected_decode.stopped_on_eos
        and protected_decode.completion_text == PROTECTED_TASK.expected_completion
    )
    phase10_heldout_retained = (
        phase10_heldout_decode.stopped_on_eos
        and phase10_heldout_decode.completion_text == HELDOUT_TASK.expected_completion
    )
    new_task_solved = (
        new_decode.stopped_on_eos
        and new_decode.completion_text == PHASE11B_NEW_TASK.expected_completion
    )
    expected_retention = kind == "beta_promoted"
    if protected_retained != expected_retention:
        failures.append("protected_retention_classification_mismatch")
    if not phase10_heldout_retained:
        failures.append("phase10_heldout_not_retained")
    if not new_task_solved:
        failures.append("new_task_not_solved")
    support = _successor_support(
        active.active_package_root,
        active.active_manifest,
        invocation,
        kind,
        sha256_hex(expected_tensor),
    )
    for path, expected in support.items():
        observed = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if observed != expected:
            failures.append(f"support_mismatch:{path}")
        field_name = SUPPORT_HASH_FIELD_BY_PATH[path]
        if getattr(manifest, field_name) != canonical_json_hash(expected):
            failures.append(f"support_hash_mismatch:{path}")
    content = {
        "schema_id": "runtime.v3.phase11b.candidate_package_report.v1",
        "contract_version": PHASE11B_CONTRACT_VERSION,
        "kind": kind,
        "active_package_hash": active_manifest.package_hash,
        "candidate_package_hash": manifest.package_hash,
        "active_model_identity_hash": active_manifest.model_identity_hash,
        "candidate_model_identity_hash": manifest.model_identity_hash,
        "active_generator_hash": active_manifest.generator_policy_hash,
        "candidate_generator_hash": manifest.generator_policy_hash,
        "active_planner_hash": active_manifest.planner_policy_hash,
        "candidate_planner_hash": manifest.planner_policy_hash,
        "program_hash": invocation.program.program_hash,
        "protected_decode_hash": protected_decode.result_hash,
        "phase10_heldout_decode_hash": phase10_heldout_decode.result_hash,
        "new_task_decode_hash": new_decode.result_hash,
        "protected_retained": protected_retained,
        "phase10_heldout_retained": phase10_heldout_retained,
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
class Phase11BInformationReport:
    protected_predecessor: PromptInformationEvidence
    protected_candidate: PromptInformationEvidence
    phase10_heldout_predecessor: PromptInformationEvidence
    phase10_heldout_candidate: PromptInformationEvidence
    new_task_predecessor: PromptInformationEvidence
    new_task_candidate: PromptInformationEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase11b.information_report.v1"

    @property
    def protected_unchanged(self) -> bool:
        return _same_prompt_density(self.protected_predecessor, self.protected_candidate)

    @property
    def phase10_heldout_unchanged(self) -> bool:
        return _same_prompt_density(
            self.phase10_heldout_predecessor,
            self.phase10_heldout_candidate,
        )

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
            and self.phase10_heldout_unchanged
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
            "phase10_heldout_predecessor": self.phase10_heldout_predecessor.to_json(),
            "phase10_heldout_candidate": self.phase10_heldout_candidate.to_json(),
            "new_task_predecessor": self.new_task_predecessor.to_json(),
            "new_task_candidate": self.new_task_candidate.to_json(),
            "protected_unchanged": self.protected_unchanged,
            "phase10_heldout_unchanged": self.phase10_heldout_unchanged,
            "new_task_improvement_interval": self.new_task_improvement_interval.to_json(),
            "selected_kl_qre_nonregression": (
                self.protected_unchanged and self.phase10_heldout_unchanged
            ),
            "strict_information_witness": self.new_task_improvement_interval.strictly_positive(),
            "accepted": self.accepted,
            "qre_equals_kl_by_diagonal_construction": True,
            "von_neumann_equals_shannon_by_diagonal_construction": True,
            "precision_bits": PRECISION_BITS,
        }


def build_phase11b_information_report(
    active_root: Path,
    candidate_root: Path,
) -> Phase11BInformationReport:
    return Phase11BInformationReport(
        protected_predecessor=prompt_information_evidence(active_root, PROTECTED_TASK),
        protected_candidate=prompt_information_evidence(candidate_root, PROTECTED_TASK),
        phase10_heldout_predecessor=prompt_information_evidence(active_root, HELDOUT_TASK),
        phase10_heldout_candidate=prompt_information_evidence(candidate_root, HELDOUT_TASK),
        new_task_predecessor=prompt_information_evidence(active_root, PHASE11B_NEW_TASK),
        new_task_candidate=prompt_information_evidence(candidate_root, PHASE11B_NEW_TASK),
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
    active: Phase11BActiveFixture,
    candidate_manifest: ModelPackageManifest,
    reports: Sequence[TaskVerifierReport],
) -> LearnedRCLMState:
    policies = _policy_identity(candidate_manifest)
    ordered_reports = tuple(sorted(reports, key=lambda item: item.task_id.encode("utf-8")))
    tasks = tuple(
        sorted(
            (
                _task_record(PROTECTED_TASK),
                _task_record(HELDOUT_TASK),
                _task_record(PHASE11B_NEW_TASK),
            ),
            key=lambda item: item.task_id.encode("utf-8"),
        )
    )
    return LearnedRCLMState(
        package_id=candidate_manifest.package_id,
        parent_package_id=active.active_manifest.package_id,
        base_state_hash=canonical_json_hash(
            {
                "phase": 11,
                "successor": "model_generated_candidate",
                "recursive_use_of_modified_generator": False,
            }
        ),
        model=candidate_manifest.model_identity(),
        policies=policies,
        self_hosting=SelfHostingBinding(
            generator_component_hash=policies.generator_policy_hash,
            planner_component_hash=policies.planner_policy_hash,
            proposal_protocol_hash=PHASE11B_PROPOSAL_PROTOCOL_HASH,
            self_hosting_contract_hash=canonical_json_hash(
                {
                    "phase11_self_hosting_contract": "successor_generator_planner_installed",
                    "recursive_use_of_modified_generator": False,
                }
            ),
        ),
        task_ledger=TaskLedger(
            tasks=tasks,
            certifications=tuple(_certification(report) for report in ordered_reports),
        ),
        capability_frontier=CapabilityFrontier(
            task_ids=tuple(report.task_id for report in ordered_reports)
        ),
    )


def _update(
    active: Phase11BActiveFixture,
    candidate: LearnedRCLMState,
) -> LearnedRCLMUpdate:
    specs = {
        "data_curriculum": (
            "0001-data-curriculum-update",
            "data_curriculum_update",
            "training/data_curriculum.json",
        ),
        "generator_policy": (
            "0002-generator-policy-update",
            "generator_update",
            "policies/generator_policy.json",
        ),
        "model_weights": (
            "0003-model-weight-update",
            "weight_update",
            "model/tensors",
        ),
        "planner_policy": (
            "0004-planner-policy-update",
            "planner_update",
            "policies/planner_policy.json",
        ),
    }
    operations: list[UpdateOperation] = []
    for target in sorted(specs, key=lambda item: item.encode("utf-8")):
        before = active.active_state.component_hash(target)
        after = candidate.component_hash(target)
        if before == after:
            continue
        operation_id, kind, path = specs[target]
        operations.append(
            UpdateOperation(
                operation_id=operation_id,
                kind=kind,  # type: ignore[arg-type]
                target=target,  # type: ignore[arg-type]
                component_path=path,
                before_hash=before,
                after_hash=after,
            )
        )
    return LearnedRCLMUpdate(
        transition_id="phase11-model-generated-promoted-successor",
        predecessor_state_hash=active.active_state.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=tuple(sorted(operations, key=lambda item: item.operation_id.encode("utf-8"))),
    )


def _heldout_policy() -> HeldoutAccessPolicy:
    heldout = phase11b_heldout_manifest()
    answers = phase11b_answer_store()
    return HeldoutAccessPolicy(
        policy_id="phase11b-heldout-isolation-v1",
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
class Phase11CandidateEvaluation:
    kind: CandidateKind
    package_report_hash: str
    protected_retained: bool
    phase10_heldout_retained: bool
    new_task_solved: bool
    generator_changed: bool
    planner_changed: bool
    data_curriculum_changed: bool
    rejection_reason: str | None

    schema_id: ClassVar[str] = "runtime.v3.phase11b.candidate_evaluation.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.kind == "beta_promoted"
            and self.protected_retained
            and self.phase10_heldout_retained
            and self.new_task_solved
            and self.generator_changed
            and self.planner_changed
            and self.data_curriculum_changed
            and self.rejection_reason is None
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "kind": self.kind,
            "package_report_hash": self.package_report_hash,
            "protected_retained": self.protected_retained,
            "phase10_heldout_retained": self.phase10_heldout_retained,
            "new_task_solved": self.new_task_solved,
            "generator_changed": self.generator_changed,
            "planner_changed": self.planner_changed,
            "data_curriculum_changed": self.data_curriculum_changed,
            "rejection_reason": self.rejection_reason,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class Phase11CandidateFixture:
    kind: CandidateKind
    root: Path
    invocation: GeneratorInvocationReport
    validation: ProgramValidationReport
    manifest: ModelPackageManifest
    package_report: Mapping[str, object]
    training_semantic_hash: str
    evaluation: Phase11CandidateEvaluation
    information_report: Phase11BInformationReport | None
    candidate_state: LearnedRCLMState | None
    update: LearnedRCLMUpdate | None
    certificate: LearnedCertificatePacket | None
    heldout_policy: HeldoutAccessPolicy | None
    transition_report: Phase9TransitionReport | None

    schema_id: ClassVar[str] = "runtime.v3.phase11b.candidate_fixture.v1"

    @property
    def structurally_valid(self) -> bool:
        return self.package_report["accepted"] is True

    @property
    def transition_accepted(self) -> bool:
        return bool(self.transition_report and self.transition_report.accepted)

    @property
    def fixture_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "kind": self.kind,
            "structurally_valid": self.structurally_valid,
            "invocation_hash": self.invocation.report_hash,
            "validation_hash": self.validation.report_hash,
            "manifest": self.manifest.to_json(),
            "package_report": dict(self.package_report),
            "training_semantic_hash": self.training_semantic_hash,
            "evaluation": self.evaluation.to_json(),
            "information_report": (
                None if self.information_report is None else self.information_report.to_json()
            ),
            "candidate_state": None if self.candidate_state is None else self.candidate_state.to_json(),
            "update": None if self.update is None else self.update.to_json(),
            "certificate": None if self.certificate is None else self.certificate.to_json(),
            "heldout_policy": None if self.heldout_policy is None else self.heldout_policy.to_json(),
            "transition_report": (
                None if self.transition_report is None else self.transition_report.to_json()
            ),
        }


def build_phase11b_candidate_fixture(
    active: Phase11BActiveFixture,
    invocation: GeneratorInvocationReport,
    validation: ProgramValidationReport,
    output_root: Path,
) -> Phase11CandidateFixture:
    manifest, kind, training_hash = build_phase11b_candidate_package(
        active,
        invocation,
        validation,
        output_root,
    )
    package_report = validate_phase11b_candidate_package(
        active,
        invocation,
        output_root,
        kind,
    )
    protected_decode = decode_completion(output_root, PROTECTED_TASK.model_prompt)
    phase10_heldout_decode = decode_completion(output_root, HELDOUT_TASK.model_prompt)
    new_decode = decode_completion(output_root, PHASE11B_NEW_TASK.model_prompt)
    protected_retained = (
        protected_decode.stopped_on_eos
        and protected_decode.completion_text == PROTECTED_TASK.expected_completion
    )
    phase10_heldout_retained = (
        phase10_heldout_decode.stopped_on_eos
        and phase10_heldout_decode.completion_text == HELDOUT_TASK.expected_completion
    )
    new_task_solved = (
        new_decode.stopped_on_eos
        and new_decode.completion_text == PHASE11B_NEW_TASK.expected_completion
    )
    evaluation = Phase11CandidateEvaluation(
        kind=kind,
        package_report_hash=str(package_report["report_hash"]),
        protected_retained=protected_retained,
        phase10_heldout_retained=phase10_heldout_retained,
        new_task_solved=new_task_solved,
        generator_changed=manifest.generator_policy_hash
        != active.active_manifest.generator_policy_hash,
        planner_changed=manifest.planner_policy_hash
        != active.active_manifest.planner_policy_hash,
        data_curriculum_changed=manifest.data_curriculum_hash
        != active.active_manifest.data_curriculum_hash,
        rejection_reason=(
            "protected_capability_regression" if not protected_retained else None
        ),
    )
    if kind == "alpha_rejected":
        return Phase11CandidateFixture(
            kind=kind,
            root=output_root,
            invocation=invocation,
            validation=validation,
            manifest=manifest,
            package_report=package_report,
            training_semantic_hash=training_hash,
            evaluation=evaluation,
            information_report=None,
            candidate_state=None,
            update=None,
            certificate=None,
            heldout_policy=None,
            transition_report=None,
        )
    protected_report = expected_success_report(
        protected_decode,
        PROTECTED_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    phase10_heldout_report = expected_success_report(
        phase10_heldout_decode,
        HELDOUT_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    new_task_report = expected_phase11b_task_report(
        new_decode,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    information = build_phase11b_information_report(active.active_package_root, output_root)
    candidate_state = _candidate_state(
        active,
        manifest,
        (protected_report, phase10_heldout_report, new_task_report),
    )
    update = _update(active, candidate_state)
    heldout_policy = _heldout_policy()
    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=active.active_state.state_hash,
        candidate_state_hash=candidate_state.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=active.active_state.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate_state.capability_frontier.frontier_hash,
        protected_task_ids=active.active_state.capability_frontier.task_ids,
        new_task_ids=(PHASE11B_NEW_TASK.task_id,),
        task_frontier_retention_evidence_hash=canonical_json_hash(
            {
                "protected": protected_report.report_hash,
                "phase10_heldout": phase10_heldout_report.report_hash,
            }
        ),
        new_task_capability_evidence_hash=new_task_report.report_hash,
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash({"goal_drift": 0, "budget": 0}),
        training_data_provenance_hash=training_hash,
        heldout_isolation_evidence_hash=canonical_json_hash(
            {
                "generator_input_hash": invocation.generator_input.input_hash,
                "program_hash": invocation.program.program_hash,
                "heldout_task_manifest_hash": heldout_policy.heldout_task_manifest_hash,
                "heldout_answer_store_hash": heldout_policy.reference_answer_store_hash,
                "heldout_material_consumed": False,
            }
        ),
        architecture_compatibility_hash=str(package_report["report_hash"]),
        self_hosting_evidence_hash=candidate_state.self_hosting.binding_hash,
        resource_evidence_hash=canonical_json_hash(
            {
                "generator_invocations": 3,
                "candidate_realizations": 2,
                "candidate_evaluations": 2,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=canonical_json_hash(
            {"phase11b_status": "bound_after_phase6_realization"}
        ),
        heldout_access_policy_hash=heldout_policy.policy_hash,
        active_generator_hash=active.active_state.policies.generator_policy_hash,
        active_planner_hash=active.active_state.policies.planner_policy_hash,
        proposal_protocol_hash=active.active_state.self_hosting.proposal_protocol_hash,
    )
    transition = validate_phase9_transition(
        active.active_state,
        update,
        candidate_state,
        certificate,
        heldout_policy,
    )
    return Phase11CandidateFixture(
        kind=kind,
        root=output_root,
        invocation=invocation,
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


__all__ = [
    "CandidateKind",
    "Phase11BInformationReport",
    "Phase11CandidateEvaluation",
    "Phase11CandidateFixture",
    "build_phase11b_candidate_fixture",
    "build_phase11b_candidate_package",
    "build_phase11b_information_report",
    "phase11b_training_semantic_hash",
    "validate_phase11b_candidate_package",
]
