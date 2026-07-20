from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime_v3.contract.certificate import HeldoutAccessPolicy, LearnedCertificatePacket
from rcp_rclm_runtime_v3.contract.common import (
    SELECTED_MODEL_FAMILY,
    SELECTED_TASK_CLASS,
)
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
from rcp_rclm_runtime_v3.phase10.information import Phase10InformationReport, build_information_report
from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    LEARNED_CHAIN,
    OMEGA_TRAINING_EXAMPLES,
    PROTECTED_CHAIN,
    PROTECTED_TASK,
    PROTECTED_TRAINING_EXAMPLE,
    heldout_answer_store,
    heldout_manifest,
    training_manifest,
)
from rcp_rclm_runtime_v3.phase10.learned_package import (
    build_sparse_candidate_package,
    build_sparse_predecessor_package,
    validate_learned_package,
)
from rcp_rclm_runtime_v3.phase10.package import ModelPackageManifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import (
    decode_completion,
    transition_tensor_path,
)
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, expected_success_report
from rcp_rclm_runtime_v3.phase10.training_protocol import (
    TrainingPair,
    TrainingRequest,
    expected_trained_tensor,
)

PINNED_LEAN_TOOLCHAIN: Final[str] = "leanprover/lean4:v4.31.0"


def _pairs(values: Sequence[tuple[int, int]]) -> Sequence[TrainingPair]:
    return tuple(
        sorted(
            (TrainingPair(current_token_id=current, target_token_id=target) for current, target in values),
            key=lambda pair: (pair.current_token_id, pair.target_token_id),
        )
    )


def training_semantic_hash(
    request: TrainingRequest,
    candidate_tensor_sha256: str,
) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase10.training_semantic_binding.v1",
            "request_hash": request.request_hash,
            "candidate_tensor_sha256": candidate_tensor_sha256,
            "objective": "sparse_transition_squared_logit_v1",
            "optimizer": "sgd",
            "optimizer_steps": 1,
            "heldout_material_consumed": False,
        }
    )


def bootstrap_training_request() -> TrainingRequest:
    zero_tensor = b"\x00" * (320 * 320 * 2)
    manifest = training_manifest((PROTECTED_TRAINING_EXAMPLE,))
    return TrainingRequest(
        transition_id="phase10-bootstrap-protected",
        mode="bootstrap",
        predecessor_tensor_sha256=sha256_hex(zero_tensor),
        training_data_manifest_hash=str(manifest["manifest_hash"]),
        pairs=_pairs(PROTECTED_CHAIN),
    )


def successor_training_request(predecessor_tensor: bytes) -> TrainingRequest:
    manifest = training_manifest(OMEGA_TRAINING_EXAMPLES)
    return TrainingRequest(
        transition_id="phase10-successor-omega",
        mode="successor",
        predecessor_tensor_sha256=sha256_hex(predecessor_tensor),
        training_data_manifest_hash=str(manifest["manifest_hash"]),
        pairs=_pairs(LEARNED_CHAIN),
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


def _self_hosting(policies: PolicyIdentity) -> SelfHostingBinding:
    return SelfHostingBinding(
        generator_component_hash=policies.generator_policy_hash,
        planner_component_hash=policies.planner_policy_hash,
        proposal_protocol_hash=canonical_json_hash(
            {"phase10_proposal_protocol": "external_untrusted_training_worker_v1"}
        ),
        self_hosting_contract_hash=canonical_json_hash(
            {"phase10_self_hosting_contract": "phase11_not_yet_authorized"}
        ),
    )


def _task_record(task) -> TaskRecord:
    return TaskRecord(
        task_id=task.task_id,
        task_class=SELECTED_TASK_CLASS,
        prompt_hash=task.prompt_hash,
        verifier_spec_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "source_prefix_hash": task.source_prefix_hash,
            }
        ),
        partition=task.partition,
    )


def _certification(report: TaskVerifierReport) -> CertificationRecord:
    return CertificationRecord(
        task_id=report.task_id,
        model_identity_hash=report.model_identity_hash,
        verifier_report_hash=report.report_hash,
        verified_output_hash=report.completion_hash,
    )


def _state(
    manifest: ModelPackageManifest,
    reports: Sequence[TaskVerifierReport],
    *,
    parent_package_id: str | None,
) -> LearnedRCLMState:
    task_by_id = {
        PROTECTED_TASK.task_id: _task_record(PROTECTED_TASK),
        HELDOUT_TASK.task_id: _task_record(HELDOUT_TASK),
    }
    certified_ids = {report.task_id for report in reports}
    tasks = tuple(
        task_by_id[task_id]
        for task_id in sorted(certified_ids, key=lambda item: item.encode("utf-8"))
    )
    certifications = tuple(
        sorted((_certification(report) for report in reports), key=lambda item: item.task_id.encode("utf-8"))
    )
    frontier = CapabilityFrontier(
        task_ids=tuple(sorted(certified_ids, key=lambda item: item.encode("utf-8")))
    )
    policies = _policy_identity(manifest)
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=parent_package_id,
        base_state_hash=canonical_json_hash(
            {"gate_d_base_state": "gate_b_target_stability", "phase": 10}
        ),
        model=manifest.model_identity(),
        policies=policies,
        self_hosting=_self_hosting(policies),
        task_ledger=TaskLedger(tasks=tasks, certifications=certifications),
        capability_frontier=frontier,
    )


def _update(predecessor: LearnedRCLMState, candidate: LearnedRCLMState) -> LearnedRCLMUpdate:
    operation_specs = {
        "adapter_manifest": (
            "0001-adapter-binding-update",
            "adapter_update",
            "model/adapters/manifest.json",
        ),
        "data_curriculum": (
            "0002-data-curriculum-update",
            "data_curriculum_update",
            "training/data_curriculum.json",
        ),
        "model_weights": (
            "0003-learned-weight-update",
            "weight_update",
            "model/tensors",
        ),
        "optimizer_policy": (
            "0004-optimizer-state-update",
            "optimizer_policy_update",
            "training/optimizer_state.json",
        ),
    }
    operations = []
    for target, (operation_id, kind, path) in operation_specs.items():
        before = predecessor.component_hash(target)
        after = candidate.component_hash(target)
        if before != after:
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
        transition_id="phase10-learned-successor-transition",
        predecessor_state_hash=predecessor.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=tuple(sorted(operations, key=lambda item: item.operation_id.encode("utf-8"))),
    )


def _heldout_policy() -> HeldoutAccessPolicy:
    heldout = heldout_manifest()
    answers = heldout_answer_store()
    return HeldoutAccessPolicy(
        policy_id="phase10-heldout-isolation-v1",
        heldout_task_manifest_hash=str(heldout["manifest_hash"]),
        reference_answer_store_hash=str(answers["answer_store_hash"]),
        evaluator_policy_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "candidate_freeze_required": True,
                "training_backend_loaded": False,
            }
        ),
    )


@dataclass(frozen=True, slots=True)
class Phase10LearnedReference:
    predecessor_manifest: ModelPackageManifest
    candidate_manifest: ModelPackageManifest
    predecessor_package_report: dict[str, object]
    candidate_package_report: dict[str, object]
    predecessor_protected: TaskVerifierReport
    candidate_protected: TaskVerifierReport
    candidate_heldout: TaskVerifierReport
    predecessor_heldout_decode_hash: str
    information_report: Phase10InformationReport
    predecessor_state: LearnedRCLMState
    candidate_state: LearnedRCLMState
    update: LearnedRCLMUpdate
    certificate: LearnedCertificatePacket
    heldout_policy: HeldoutAccessPolicy
    transition_report: Phase9TransitionReport
    bootstrap_request: TrainingRequest
    successor_request: TrainingRequest
    bootstrap_training_semantic_hash: str
    successor_training_semantic_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase10.learned_reference.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.predecessor_package_report["accepted"] is True
            and self.candidate_package_report["accepted"] is True
            and self.predecessor_protected.solved
            and self.candidate_protected.solved
            and self.candidate_heldout.solved
            and self.information_report.accepted
            and self.transition_report.accepted
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        content = {
            "schema_id": "runtime.v3.phase10.learned_evidence_summary.v1",
            "accepted": self.accepted,
            "predecessor_package_hash": self.predecessor_manifest.package_hash,
            "candidate_package_hash": self.candidate_manifest.package_hash,
            "predecessor_model_identity_hash": self.predecessor_manifest.model_identity_hash,
            "candidate_model_identity_hash": self.candidate_manifest.model_identity_hash,
            "protected_task_id": PROTECTED_TASK.task_id,
            "new_heldout_task_id": HELDOUT_TASK.task_id,
            "predecessor_protected_verifier_report_hash": self.predecessor_protected.report_hash,
            "candidate_protected_verifier_report_hash": self.candidate_protected.report_hash,
            "candidate_heldout_verifier_report_hash": self.candidate_heldout.report_hash,
            "information_report_hash": self.information_report.report_hash,
            "phase9_transition_report_hash": self.transition_report.semantic_report_hash,
            "phase9_transition_accepted": self.transition_report.accepted,
            "bootstrap_request_hash": self.bootstrap_request.request_hash,
            "successor_request_hash": self.successor_request.request_hash,
            "heldout_policy_hash": self.heldout_policy.policy_hash,
            "claim_boundary": {
                "trained_sparse_language_model": True,
                "untrusted_worker_protocol": True,
                "authoritative_exact_inference": True,
                "pinned_lean_task_certification": True,
                "selected_kl_diagonal_qre": True,
                "phase9_gate_d_transition": True,
                "phase6_realization": False,
                "atomic_promotion": False,
                "independent_replay": False,
                "phase10_exit_closed": False,
            },
        }
        value = dict(content)
        value["summary_hash"] = canonical_json_hash(content)
        return value

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "predecessor_manifest": self.predecessor_manifest.to_json(),
            "candidate_manifest": self.candidate_manifest.to_json(),
            "predecessor_package_report": self.predecessor_package_report,
            "candidate_package_report": self.candidate_package_report,
            "predecessor_protected": self.predecessor_protected.to_json(),
            "candidate_protected": self.candidate_protected.to_json(),
            "candidate_heldout": self.candidate_heldout.to_json(),
            "predecessor_heldout_decode_hash": self.predecessor_heldout_decode_hash,
            "information_report": self.information_report.to_json(),
            "predecessor_state": self.predecessor_state.to_json(),
            "candidate_state": self.candidate_state.to_json(),
            "update": self.update.to_json(),
            "certificate": self.certificate.to_json(),
            "heldout_policy": self.heldout_policy.to_json(),
            "transition_report": self.transition_report.to_json(),
            "bootstrap_request": self.bootstrap_request.to_json(),
            "successor_request": self.successor_request.to_json(),
            "bootstrap_training_semantic_hash": self.bootstrap_training_semantic_hash,
            "successor_training_semantic_hash": self.successor_training_semantic_hash,
            "claim_boundary": {
                "actual_nontrivial_compact_language_model_weights": True,
                "isolated_untrusted_training_worker_protocol": True,
                "deterministic_authoritative_sparse_inference": True,
                "protected_lean_task_retention": True,
                "new_heldout_lean_task_certified": True,
                "selected_entropy_kl_diagonal_qre_evidence": True,
                "phase9_gate_d_transition_accepts": True,
                "phase6_realization_and_rollback": False,
                "atomic_promotion": False,
                "independent_replay_without_training": False,
                "phase10_exit_closed": False,
            },
        }


def build_phase10_learned_reference(output_root: Path) -> Phase10LearnedReference:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"learned reference already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)

    bootstrap_request = bootstrap_training_request()
    zero_tensor = b"\x00" * (320 * 320 * 2)
    bootstrap_tensor = expected_trained_tensor(zero_tensor, bootstrap_request)
    bootstrap_semantic = training_semantic_hash(
        bootstrap_request, sha256_hex(bootstrap_tensor)
    )
    predecessor_root = root / "predecessor"
    predecessor_manifest = build_sparse_predecessor_package(
        predecessor_root,
        training_report_hash=bootstrap_semantic,
    )
    observed_predecessor_tensor = transition_tensor_path(predecessor_root).read_bytes()
    if observed_predecessor_tensor != bootstrap_tensor:
        raise ValueError("bootstrap host package differs from exact training result")

    successor_request = successor_training_request(observed_predecessor_tensor)
    candidate_tensor = expected_trained_tensor(observed_predecessor_tensor, successor_request)
    successor_semantic = training_semantic_hash(
        successor_request, sha256_hex(candidate_tensor)
    )
    candidate_root = root / "candidate"
    candidate_manifest = build_sparse_candidate_package(
        predecessor_root,
        candidate_root,
        transition_tensor_bytes=candidate_tensor,
        training_report_hash=successor_semantic,
        transition_pairs=tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN})),
    )

    predecessor_report = validate_learned_package(predecessor_root, PROTECTED_CHAIN)
    candidate_report = validate_learned_package(
        candidate_root, tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN}))
    )
    predecessor_protected_decode = decode_completion(predecessor_root, PROTECTED_TASK.model_prompt)
    candidate_protected_decode = decode_completion(candidate_root, PROTECTED_TASK.model_prompt)
    predecessor_heldout_decode = decode_completion(predecessor_root, HELDOUT_TASK.model_prompt)
    candidate_heldout_decode = decode_completion(candidate_root, HELDOUT_TASK.model_prompt)

    predecessor_protected = expected_success_report(
        predecessor_protected_decode,
        PROTECTED_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    candidate_protected = expected_success_report(
        candidate_protected_decode,
        PROTECTED_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    candidate_heldout = expected_success_report(
        candidate_heldout_decode,
        HELDOUT_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    if predecessor_heldout_decode.stopped_on_eos and predecessor_heldout_decode.completion_text == HELDOUT_TASK.expected_completion:
        raise ValueError("predecessor unexpectedly solves the held-out task")

    information = build_information_report(
        predecessor_root,
        candidate_root,
        PROTECTED_TASK,
        HELDOUT_TASK,
    )
    predecessor_state = _state(
        predecessor_manifest,
        (predecessor_protected,),
        parent_package_id=None,
    )
    candidate_state = _state(
        candidate_manifest,
        (candidate_heldout, candidate_protected),
        parent_package_id=predecessor_manifest.package_id,
    )
    update = _update(predecessor_state, candidate_state)
    heldout_policy = _heldout_policy()
    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=predecessor_state.state_hash,
        candidate_state_hash=candidate_state.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=predecessor_state.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate_state.capability_frontier.frontier_hash,
        protected_task_ids=predecessor_state.capability_frontier.task_ids,
        new_task_ids=(HELDOUT_TASK.task_id,),
        task_frontier_retention_evidence_hash=candidate_protected.report_hash,
        new_task_capability_evidence_hash=candidate_heldout.report_hash,
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash({"goal_drift": 0, "budget": 0}),
        training_data_provenance_hash=successor_semantic,
        heldout_isolation_evidence_hash=canonical_json_hash(
            {
                "request_hash": successor_request.request_hash,
                "heldout_task_manifest_hash": heldout_policy.heldout_task_manifest_hash,
                "heldout_answer_store_hash": heldout_policy.reference_answer_store_hash,
                "heldout_material_consumed": False,
            }
        ),
        architecture_compatibility_hash=str(candidate_report["report_hash"]),
        self_hosting_evidence_hash=candidate_state.self_hosting.binding_hash,
        resource_evidence_hash=canonical_json_hash(
            {"training_invocations": 1, "authoritative_inference_backend": "python_integer"}
        ),
        rollback_evidence_hash=canonical_json_hash(
            {"phase10b_status": "rollback_not_yet_integrated"}
        ),
        heldout_access_policy_hash=heldout_policy.policy_hash,
        active_generator_hash=predecessor_state.policies.generator_policy_hash,
        active_planner_hash=predecessor_state.policies.planner_policy_hash,
        proposal_protocol_hash=predecessor_state.self_hosting.proposal_protocol_hash,
    )
    transition_report = validate_phase9_transition(
        predecessor_state,
        update,
        candidate_state,
        certificate,
        heldout_policy,
    )
    return Phase10LearnedReference(
        predecessor_manifest=predecessor_manifest,
        candidate_manifest=candidate_manifest,
        predecessor_package_report=predecessor_report,
        candidate_package_report=candidate_report,
        predecessor_protected=predecessor_protected,
        candidate_protected=candidate_protected,
        candidate_heldout=candidate_heldout,
        predecessor_heldout_decode_hash=predecessor_heldout_decode.result_hash,
        information_report=information,
        predecessor_state=predecessor_state,
        candidate_state=candidate_state,
        update=update,
        certificate=certificate,
        heldout_policy=heldout_policy,
        transition_report=transition_report,
        bootstrap_request=bootstrap_request,
        successor_request=successor_request,
        bootstrap_training_semantic_hash=bootstrap_semantic,
        successor_training_semantic_hash=successor_semantic,
    )


__all__ = [
    "Phase10LearnedReference",
    "bootstrap_training_request",
    "build_phase10_learned_reference",
    "successor_training_request",
    "training_semantic_hash",
]
