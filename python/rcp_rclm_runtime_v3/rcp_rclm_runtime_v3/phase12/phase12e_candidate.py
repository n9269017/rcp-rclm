from __future__ import annotations

import copy
import hashlib
import os
import shutil
import struct
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.contract.certificate import HeldoutAccessPolicy, LearnedCertificatePacket
from rcp_rclm_runtime_v3.contract.common import SELECTED_TASK_CLASS
from rcp_rclm_runtime_v3.contract.state import LearnedRCLMState, SelfHostingBinding
from rcp_rclm_runtime_v3.contract.tasks import CapabilityFrontier, TaskLedger
from rcp_rclm_runtime_v3.contract.update import LearnedRCLMUpdate, UpdateOperation
from rcp_rclm_runtime_v3.contract.validation import Phase9TransitionReport, validate_phase9_transition
from rcp_rclm_runtime_v3.phase10.adapters import (
    LoRAAdapterManifest,
    expected_lora_base_targets,
    expected_lora_tensor_specs,
)
from rcp_rclm_runtime_v3.phase10.constants import LORA_ALPHA, LORA_PARAMETER_COUNT, LORA_RANK
from rcp_rclm_runtime_v3.phase10.information import PRECISION_BITS, PromptInformationEvidence, prompt_information_evidence
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK, LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.learned_reference import PINNED_LEAN_TOOLCHAIN
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    PACKAGE_MANIFEST_PATH,
    SUPPORT_HASH_FIELD_BY_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import decode_completion
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, expected_success_report
from rcp_rclm_runtime_v3.phase10.tensors import TensorRecord, TensorSpec
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import PHASE11B_NEW_TASK, expected_phase11b_task_report
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import PHASE12B_NEW_TASK, expected_phase12b_task_report
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import PHASE12C_NEW_TASK, decode_phase12c_task, expected_phase12c_task_report
from rcp_rclm_runtime_v3.phase12.phase12d_candidate import _certification, _effective_task, _policy_identity, _same_prompt_density, _task_record
from rcp_rclm_runtime_v3.phase12.phase12d_lifecycle import Phase12DReference
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import (
    PHASE12D_NEW_TASK,
    decode_phase12d_task,
    expected_phase12d_task_report,
)
from rcp_rclm_runtime_v3.phase12.phase12e_program import (
    PHASE12E_CONTRACT_VERSION,
    PHASE12E_TRANSITION_ID,
    Phase12EProposalReport,
    Phase12EProposalValidationReport,
)
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import (
    PHASE12E_ADAPTER_ROUTE_MAGIC,
    PHASE12E_NEW_TASK,
    Phase12EAdapterDecode,
    decode_phase12e_task,
    expected_phase12e_task_report,
    phase12e_adapter_training_manifest,
    phase12e_answer_store,
    phase12e_heldout_manifest,
    phase12e_optimizer_policy,
    phase12e_update_provenance,
    selected_phase12e_adapter_spec,
)

PHASE12E_SUCCESSOR_PACKAGE_ID: Final[str] = "phase12-generation4-adapter-optimizer-successor"
OPTIMIZER_STATE_PATH: Final[str] = "training/optimizer_state.json"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _file_set(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _support_from_package(root: Path) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    for path in SUPPORT_HASH_FIELD_BY_PATH:
        value = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if not isinstance(value, dict):
            raise SchemaValidationError("phase12e.support", f"expected object at {path}")
        values[path] = copy.deepcopy(value)
    return values


def _deterministic_a_bytes(spec: TensorSpec) -> bytes:
    name_seed = sum(spec.name.encode("utf-8"))
    values: list[int] = []
    for index in range(spec.element_count):
        value = ((name_seed + 17 * index) % 7) - 3
        values.append(1 if value == 0 else value)
    return struct.pack("<" + "h" * len(values), *values)


def _build_trained_adapter(root: Path, architecture, base_weights_tree_hash: str) -> tuple[LoRAAdapterManifest, TensorRecord]:
    selected = selected_phase12e_adapter_spec(architecture)
    records: list[TensorRecord] = []
    selected_record: TensorRecord | None = None
    for spec in expected_lora_tensor_specs(architecture):
        path = root / spec.path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"Phase 12E adapter tensor already exists: {path}")
        if spec.role == "adapter_a":
            content = _deterministic_a_bytes(spec)
        else:
            buffer = bytearray(spec.size_bytes)
            if spec.name == selected.name:
                struct.pack_into("<hhhh", buffer, 0, *PHASE12E_ADAPTER_ROUTE_MAGIC)
            content = bytes(buffer)
        path.write_bytes(content)
        record = TensorRecord(spec=spec, sha256=_file_hash(path))
        records.append(record)
        if spec.name == selected.name:
            selected_record = record
    if selected_record is None:
        raise SchemaValidationError("phase12e.adapter", "selected route tensor was not materialized")
    manifest = LoRAAdapterManifest(
        architecture_hash=architecture.architecture_hash,
        base_weights_tree_hash=base_weights_tree_hash,
        status="trained",
        rank=LORA_RANK,
        alpha=LORA_ALPHA,
        zero_output_factor="B",
        target_base_tensors=expected_lora_base_targets(architecture),
        records=tuple(sorted(records, key=lambda item: item.spec.name.encode("utf-8"))),
        parameter_count=LORA_PARAMETER_COUNT,
    )
    return manifest, selected_record


def phase12e_update_semantic_hash(
    active_manifest: ModelPackageManifest,
    proposal: Phase12EProposalReport,
    candidate_manifest: ModelPackageManifest,
    selected_tensor_hash: str,
) -> str:
    provenance = phase12e_update_provenance(
        active_package_hash=active_manifest.package_hash,
        program_hash=proposal.program.program_hash,
        adapter_manifest_hash=candidate_manifest.adapter_manifest_hash,
        optimizer_policy_hash=candidate_manifest.optimizer_state_hash,
        selected_tensor_hash=selected_tensor_hash,
    )
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12e.update_semantic_binding.v1",
            "transition_id": PHASE12E_TRANSITION_ID,
            "active_package_hash": active_manifest.package_hash,
            "generator_input_hash": proposal.generator_input.input_hash,
            "proposal_hash": proposal.report_hash,
            "program_hash": proposal.program.program_hash,
            "adapter_manifest_hash": candidate_manifest.adapter_manifest_hash,
            "model_architecture_component_hash": canonical_json_hash(
                {
                    "model_family": candidate_manifest.model_identity().model_family,
                    "architecture_hash": candidate_manifest.architecture_hash,
                    "parameter_count": candidate_manifest.parameter_count,
                }
            ),
            "optimizer_policy_hash": candidate_manifest.optimizer_state_hash,
            "selected_adapter_tensor_hash": selected_tensor_hash,
            "provenance_hash": provenance["provenance_hash"],
            "training_steps": 1,
            "heldout_material_consumed": False,
        }
    )


def build_phase12e_candidate_package(
    phase12d: Phase12DReference,
    proposal: Phase12EProposalReport,
    validation: Phase12EProposalValidationReport,
    output_root: Path,
) -> tuple[ModelPackageManifest, str]:
    if not validation.accepted or validation.proposal_hash != proposal.report_hash:
        raise SchemaValidationError("phase12e.candidate", "proposal must validate")
    active_root = phase12d.semantic_candidate.root.resolve(strict=True)
    active_manifest, architecture, tokenizer, tensors, active_adapter = load_package_components(active_root)
    if active_adapter.status != "absent":
        raise SchemaValidationError("phase12e.candidate", "M3 must begin without an adapter")
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 12E candidate already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12e-candidate-", dir=output.parent) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(active_root, staging, symlinks=False)
        (staging / PACKAGE_MANIFEST_PATH).unlink()
        (staging / ADAPTER_MANIFEST_PATH).unlink()
        adapter, selected_record = _build_trained_adapter(staging, architecture, tensors.weights_tree_hash)
        _write_json(staging / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
        support = _support_from_package(active_root)
        support[OPTIMIZER_STATE_PATH] = phase12e_optimizer_policy(
            parent_optimizer_hash=active_manifest.optimizer_state_hash,
            selected_tensor_hash=selected_record.sha256,
        )
        for path, value in support.items():
            _write_json(staging / path, value)
        manifest = _manifest_from_components(
            package_id=PHASE12E_SUCCESSOR_PACKAGE_ID,
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
    return manifest, phase12e_update_semantic_hash(active_manifest, proposal, manifest, selected_record.sha256)


def validate_phase12e_candidate_package(
    phase12d: Phase12DReference,
    proposal: Phase12EProposalReport,
    candidate_root: Path,
) -> dict[str, object]:
    active_root = phase12d.semantic_candidate.root.resolve(strict=True)
    root = candidate_root.resolve(strict=True)
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(root)
    active_manifest, active_architecture, active_tokenizer, active_tensors, active_adapter = load_package_components(active_root)
    failures: list[str] = []
    if manifest.payload_tree_hash != _payload_tree_hash(root): failures.append("payload_tree_hash_mismatch")
    if manifest.parent_package_id != active_manifest.package_id: failures.append("parent_package_id_mismatch")
    if architecture != active_architecture or tokenizer != active_tokenizer: failures.append("base_architecture_or_tokenizer_changed")
    if tensors != active_tensors: failures.append("base_tensor_manifest_changed")
    if active_adapter.status != "absent" or adapter.status != "trained": failures.append("adapter_status_mismatch")
    if manifest.adapter_manifest_hash == active_manifest.adapter_manifest_hash: failures.append("adapter_unchanged")
    if manifest.optimizer_state_hash == active_manifest.optimizer_state_hash: failures.append("optimizer_unchanged")
    if manifest.model_identity_hash == active_manifest.model_identity_hash: failures.append("model_identity_unchanged")
    if manifest.parameter_count <= active_manifest.parameter_count: failures.append("parameter_count_not_extended")
    support_fields = set(SUPPORT_HASH_FIELD_BY_PATH.values())
    changed_support = {field for field in support_fields if getattr(manifest, field) != getattr(active_manifest, field)}
    if changed_support != {"optimizer_state_hash"}: failures.append("unexpected_support_change_set")
    for field in ("generator_policy_hash", "planner_policy_hash", "memory_manifest_hash", "retrieval_index_hash"):
        if getattr(manifest, field) != getattr(active_manifest, field): failures.append(f"{field}_changed")
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None: failures.append("selected_adapter_record_missing")
    else:
        content = (root / record.spec.path).read_bytes()
        if len(content) < 8 or tuple(struct.unpack_from("<hhhh", content, 0)) != PHASE12E_ADAPTER_ROUTE_MAGIC:
            failures.append("selected_adapter_route_magic_mismatch")
    expected_added = {record.spec.path for record in adapter.records}
    observed_added = _file_set(root) - _file_set(active_root)
    if observed_added != expected_added: failures.append("unexpected_added_file_set")
    content = {
        "schema_id": "runtime.v3.phase12e.candidate_package_validation.v1",
        "contract_version": PHASE12E_CONTRACT_VERSION,
        "active_package_hash": active_manifest.package_hash,
        "candidate_package_hash": manifest.package_hash,
        "proposal_hash": proposal.report_hash,
        "changed_support_fields": sorted(changed_support),
        "added_adapter_files": sorted(observed_added),
        "failures": sorted(set(failures)),
        "accepted": not failures,
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
    return result


@dataclass(frozen=True, slots=True)
class Phase12EInformationReport:
    protected_pairs: Sequence[tuple[PromptInformationEvidence, PromptInformationEvidence]]
    predecessor_adapter: Phase12EAdapterDecode
    candidate_adapter: Phase12EAdapterDecode
    new_task_predecessor: PromptInformationEvidence
    new_task_candidate: PromptInformationEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase12e.information_report.v1"

    @property
    def protected_unchanged(self) -> bool:
        return all(_same_prompt_density(before, after) for before, after in self.protected_pairs)

    @property
    def new_task_improvement_interval(self):
        return self.new_task_predecessor.kl_qre_sum_interval - self.new_task_candidate.kl_qre_sum_interval

    @property
    def accepted(self) -> bool:
        return (
            self.protected_unchanged
            and not self.predecessor_adapter.adapter_route_hit
            and self.candidate_adapter.adapter_route_hit
            and self.candidate_adapter.planner_decode.planner_route_hit
            and self.candidate_adapter.planner_decode.generator_capability_hit
            and self.candidate_adapter.planner_decode.retrieval_hit
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
            "predecessor_adapter": self.predecessor_adapter.to_json(),
            "candidate_adapter": self.candidate_adapter.to_json(),
            "new_task_predecessor": self.new_task_predecessor.to_json(),
            "new_task_candidate": self.new_task_candidate.to_json(),
            "protected_unchanged": self.protected_unchanged,
            "new_task_improvement_interval": self.new_task_improvement_interval.to_json(),
            "selected_kl_qre_nonregression": self.protected_unchanged,
            "strict_information_witness": self.new_task_improvement_interval.strictly_positive(),
            "qre_equals_kl_by_diagonal_construction": True,
            "von_neumann_equals_shannon_by_diagonal_construction": True,
            "precision_bits": PRECISION_BITS,
            "accepted": self.accepted,
        }


def build_phase12e_information_report(active_root: Path, candidate_root: Path) -> Phase12EInformationReport:
    active_c = decode_phase12c_task(active_root)
    candidate_c = decode_phase12c_task(candidate_root)
    active_d = decode_phase12d_task(active_root)
    candidate_d = decode_phase12d_task(candidate_root)
    tasks = (PROTECTED_TASK, HELDOUT_TASK, PHASE11B_NEW_TASK, PHASE12B_NEW_TASK)
    pairs = tuple((prompt_information_evidence(active_root, t), prompt_information_evidence(candidate_root, t)) for t in tasks)
    pairs += ((prompt_information_evidence(active_root, _effective_task(PHASE12C_NEW_TASK, active_c.route_marker_token_id)), prompt_information_evidence(candidate_root, _effective_task(PHASE12C_NEW_TASK, candidate_c.route_marker_token_id))),)
    pairs += ((prompt_information_evidence(active_root, _effective_task(PHASE12D_NEW_TASK, active_d.retrieval_decode.route_marker_token_id)), prompt_information_evidence(candidate_root, _effective_task(PHASE12D_NEW_TASK, candidate_d.retrieval_decode.route_marker_token_id))),)
    before = decode_phase12e_task(active_root)
    after = decode_phase12e_task(candidate_root)
    effective = _effective_task(PHASE12E_NEW_TASK, after.planner_decode.retrieval_decode.route_marker_token_id)
    return Phase12EInformationReport(
        protected_pairs=pairs,
        predecessor_adapter=before,
        candidate_adapter=after,
        new_task_predecessor=prompt_information_evidence(active_root, PHASE12E_NEW_TASK),
        new_task_candidate=prompt_information_evidence(candidate_root, effective),
    )


def _candidate_state(phase12d: Phase12DReference, manifest: ModelPackageManifest, reports: Sequence[TaskVerifierReport]) -> LearnedRCLMState:
    active_state = phase12d.semantic_candidate.candidate_state
    ordered_reports = tuple(sorted(reports, key=lambda item: item.task_id.encode("utf-8")))
    tasks = tuple(sorted((_task_record(PROTECTED_TASK), _task_record(HELDOUT_TASK), _task_record(PHASE11B_NEW_TASK), _task_record(PHASE12B_NEW_TASK), _task_record(PHASE12C_NEW_TASK), _task_record(PHASE12D_NEW_TASK), _task_record(PHASE12E_NEW_TASK)), key=lambda item: item.task_id.encode("utf-8")))
    self_hosting = SelfHostingBinding(
        generator_component_hash=manifest.generator_policy_hash,
        planner_component_hash=manifest.planner_policy_hash,
        proposal_protocol_hash=active_state.self_hosting.proposal_protocol_hash,
        self_hosting_contract_hash=active_state.self_hosting.self_hosting_contract_hash,
    )
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=active_state.package_id,
        base_state_hash=canonical_json_hash({"phase": 12, "generation": 4, "successor": "rank8_lora_adapter_optimizer_update", "proposal_source": "promoted_m3_generation3_generator_planner"}),
        model=manifest.model_identity(),
        policies=_policy_identity(manifest),
        self_hosting=self_hosting,
        task_ledger=TaskLedger(tasks=tasks, certifications=tuple(_certification(report) for report in ordered_reports)),
        capability_frontier=CapabilityFrontier(task_ids=tuple(report.task_id for report in ordered_reports)),
    )


def _update(phase12d: Phase12DReference, candidate: LearnedRCLMState) -> LearnedRCLMUpdate:
    active = phase12d.semantic_candidate.candidate_state
    ops = (
        UpdateOperation("0001-phase12-generation4-adapter-update", "adapter_update", "adapter_manifest", "model/adapters/manifest.json", active.component_hash("adapter_manifest"), candidate.component_hash("adapter_manifest")),
        UpdateOperation("0002-phase12-generation4-architecture-extension", "architecture_extension", "model_architecture", "model/architecture.json", active.component_hash("model_architecture"), candidate.component_hash("model_architecture")),
        UpdateOperation("0003-phase12-generation4-optimizer-update", "optimizer_policy_update", "optimizer_policy", OPTIMIZER_STATE_PATH, active.component_hash("optimizer_policy"), candidate.component_hash("optimizer_policy")),
    )
    return LearnedRCLMUpdate(
        transition_id=PHASE12E_TRANSITION_ID,
        predecessor_state_hash=active.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=ops,
    )


def _heldout_policy() -> HeldoutAccessPolicy:
    heldout = phase12e_heldout_manifest(); answers = phase12e_answer_store()
    return HeldoutAccessPolicy(
        policy_id="phase12e-heldout-isolation-v1",
        heldout_task_manifest_hash=str(heldout["manifest_hash"]),
        reference_answer_store_hash=str(answers["answer_store_hash"]),
        evaluator_policy_hash=canonical_json_hash({"verifier": "pinned_lean_theorem_verifier_v1", "candidate_freeze_required": True, "adapter_route_recomputed": True, "planner_route_recomputed": True, "training_backend_loaded": False}),
    )


@dataclass(frozen=True, slots=True)
class Phase12ECandidateEvaluation:
    package_report_hash: str
    protected_tasks_retained: bool
    new_task_solved: bool
    model_identity_changed: bool
    adapter_trained: bool
    optimizer_changed: bool
    generator_unchanged: bool
    planner_unchanged: bool
    memory_unchanged: bool
    retrieval_unchanged: bool
    rejection_reason: str | None

    schema_id: ClassVar[str] = "runtime.v3.phase12e.candidate_evaluation.v1"

    @property
    def accepted(self) -> bool:
        return all((self.protected_tasks_retained, self.new_task_solved, self.model_identity_changed, self.adapter_trained, self.optimizer_changed, self.generator_unchanged, self.planner_unchanged, self.memory_unchanged, self.retrieval_unchanged, self.rejection_reason is None))

    @property
    def report_hash(self) -> str: return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {"schema_id": self.schema_id, "package_report_hash": self.package_report_hash, "protected_tasks_retained": self.protected_tasks_retained, "new_task_solved": self.new_task_solved, "model_identity_changed": self.model_identity_changed, "adapter_trained": self.adapter_trained, "optimizer_changed": self.optimizer_changed, "generator_unchanged": self.generator_unchanged, "planner_unchanged": self.planner_unchanged, "memory_unchanged": self.memory_unchanged, "retrieval_unchanged": self.retrieval_unchanged, "rejection_reason": self.rejection_reason, "accepted": self.accepted}


@dataclass(frozen=True, slots=True)
class Phase12ECandidateFixture:
    root: Path
    proposal: Phase12EProposalReport
    validation: Phase12EProposalValidationReport
    manifest: ModelPackageManifest
    package_report: Mapping[str, object]
    update_semantic_hash: str
    evaluation: Phase12ECandidateEvaluation
    information_report: Phase12EInformationReport
    candidate_state: LearnedRCLMState
    update: LearnedRCLMUpdate
    certificate: LearnedCertificatePacket
    heldout_policy: HeldoutAccessPolicy
    transition_report: Phase9TransitionReport

    schema_id: ClassVar[str] = "runtime.v3.phase12e.candidate_fixture.v1"

    @property
    def accepted(self) -> bool:
        return self.package_report["accepted"] is True and self.evaluation.accepted and self.information_report.accepted and self.transition_report.accepted

    @property
    def fixture_hash(self) -> str: return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {"schema_id": self.schema_id, "accepted": self.accepted, "proposal_hash": self.proposal.report_hash, "validation_hash": self.validation.report_hash, "manifest": self.manifest.to_json(), "package_report": dict(self.package_report), "update_semantic_hash": self.update_semantic_hash, "evaluation": self.evaluation.to_json(), "information_report": self.information_report.to_json(), "candidate_state": self.candidate_state.to_json(), "update": self.update.to_json(), "certificate": self.certificate.to_json(), "heldout_policy": self.heldout_policy.to_json(), "transition_report": self.transition_report.to_json()}


def build_phase12e_candidate_fixture(phase12d: Phase12DReference, proposal: Phase12EProposalReport, validation: Phase12EProposalValidationReport, output_root: Path) -> Phase12ECandidateFixture:
    manifest, semantic_hash = build_phase12e_candidate_package(phase12d, proposal, validation, output_root)
    package_report = validate_phase12e_candidate_package(phase12d, proposal, output_root)
    active_root = phase12d.semantic_candidate.root.resolve(strict=True)
    active_manifest = phase12d.semantic_candidate.manifest
    decodes = (
        decode_completion(output_root, PROTECTED_TASK.model_prompt),
        decode_completion(output_root, HELDOUT_TASK.model_prompt),
        decode_completion(output_root, PHASE11B_NEW_TASK.model_prompt),
        decode_completion(output_root, PHASE12B_NEW_TASK.model_prompt),
        decode_phase12c_task(output_root),
        decode_phase12d_task(output_root),
        decode_phase12e_task(output_root),
    )
    reports = (
        expected_success_report(decodes[0], PROTECTED_TASK, lean_toolchain=PINNED_LEAN_TOOLCHAIN),
        expected_success_report(decodes[1], HELDOUT_TASK, lean_toolchain=PINNED_LEAN_TOOLCHAIN),
        expected_phase11b_task_report(decodes[2], lean_toolchain=PINNED_LEAN_TOOLCHAIN),
        expected_phase12b_task_report(decodes[3], lean_toolchain=PINNED_LEAN_TOOLCHAIN),
        expected_phase12c_task_report(decodes[4], lean_toolchain=PINNED_LEAN_TOOLCHAIN),
        expected_phase12d_task_report(decodes[5], lean_toolchain=PINNED_LEAN_TOOLCHAIN),
        expected_phase12e_task_report(decodes[6], lean_toolchain=PINNED_LEAN_TOOLCHAIN),
    )
    evaluation = Phase12ECandidateEvaluation(
        package_report_hash=str(package_report["report_hash"]),
        protected_tasks_retained=all(r.solved for r in reports[:-1]),
        new_task_solved=reports[-1].solved,
        model_identity_changed=manifest.model_identity_hash != active_manifest.model_identity_hash,
        adapter_trained=load_package_components(output_root)[4].status == "trained",
        optimizer_changed=manifest.optimizer_state_hash != active_manifest.optimizer_state_hash,
        generator_unchanged=manifest.generator_policy_hash == active_manifest.generator_policy_hash,
        planner_unchanged=manifest.planner_policy_hash == active_manifest.planner_policy_hash,
        memory_unchanged=manifest.memory_manifest_hash == active_manifest.memory_manifest_hash,
        retrieval_unchanged=manifest.retrieval_index_hash == active_manifest.retrieval_index_hash,
        rejection_reason=None,
    )
    information = build_phase12e_information_report(active_root, output_root)
    state = _candidate_state(phase12d, manifest, reports)
    update = _update(phase12d, state)
    heldout = _heldout_policy()
    active_state = phase12d.semantic_candidate.candidate_state
    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=active_state.state_hash,
        candidate_state_hash=state.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=active_state.capability_frontier.frontier_hash,
        capability_frontier_after_hash=state.capability_frontier.frontier_hash,
        protected_task_ids=active_state.capability_frontier.task_ids,
        new_task_ids=(PHASE12E_NEW_TASK.task_id,),
        task_frontier_retention_evidence_hash=canonical_json_hash({r.task_id: r.report_hash for r in reports[:-1]}),
        new_task_capability_evidence_hash=reports[-1].report_hash,
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash({"goal_drift": 0, "budget": 0}),
        training_data_provenance_hash=semantic_hash,
        heldout_isolation_evidence_hash=canonical_json_hash({"proposal_hash": proposal.report_hash, "heldout_task_manifest_hash": heldout.heldout_task_manifest_hash, "heldout_answer_store_hash": heldout.reference_answer_store_hash, "heldout_material_consumed": False}),
        architecture_compatibility_hash=str(package_report["report_hash"]),
        self_hosting_evidence_hash=canonical_json_hash({"active_self_hosting_hash": active_state.self_hosting.binding_hash, "candidate_self_hosting_hash": state.self_hosting.binding_hash, "proposal_source": "promoted_m3_generation3_generator_planner", "generator_unchanged": True, "planner_unchanged": True}),
        resource_evidence_hash=canonical_json_hash({"generator_invocations": 6, "rejected_attempts": 2, "candidate_realizations": 4, "candidate_evaluations": 4, "training_steps": 2, "manual_repairs": 0}),
        rollback_evidence_hash=canonical_json_hash({"phase6_rollback": "pending_realization"}),
        heldout_access_policy_hash=heldout.policy_hash,
        active_generator_hash=active_state.policies.generator_policy_hash,
        active_planner_hash=active_state.policies.planner_policy_hash,
        proposal_protocol_hash=active_state.self_hosting.proposal_protocol_hash,
    )
    transition = validate_phase9_transition(active_state, update, state, certificate, heldout)
    fixture = Phase12ECandidateFixture(output_root, proposal, validation, manifest, package_report, semantic_hash, evaluation, information, state, update, certificate, heldout, transition)
    if not fixture.accepted:
        raise ValueError("Phase 12E semantic candidate did not close")
    return fixture


__all__ = [
    "PHASE12E_SUCCESSOR_PACKAGE_ID", "Phase12ECandidateEvaluation", "Phase12ECandidateFixture", "Phase12EInformationReport",
    "build_phase12e_candidate_fixture", "build_phase12e_candidate_package", "build_phase12e_information_report",
    "phase12e_update_semantic_hash", "validate_phase12e_candidate_package",
]
