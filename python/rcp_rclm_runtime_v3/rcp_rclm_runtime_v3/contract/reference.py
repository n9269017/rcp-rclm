from __future__ import annotations

from dataclasses import dataclass

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.contract.records import (
    CapabilityFrontier,
    CertificationRecord,
    HeldoutAccessPolicy,
    LearnedCertificatePacket,
    LearnedRCLMState,
    LearnedRCLMUpdate,
    ModelIdentity,
    PolicyIdentity,
    SELECTED_MODEL_FAMILY,
    SELECTED_TASK_CLASS,
    SelfHostingBinding,
    TaskLedger,
    TaskRecord,
    UpdateOperation,
)
from rcp_rclm_runtime_v3.contract.validation import (
    Phase9TransitionReport,
    validate_phase9_transition,
)


@dataclass(frozen=True, slots=True)
class Phase9ReferenceFixture:
    predecessor: LearnedRCLMState
    update: LearnedRCLMUpdate
    candidate: LearnedRCLMState
    certificate: LearnedCertificatePacket
    heldout_policy: HeldoutAccessPolicy
    report: Phase9TransitionReport

    def to_json(self) -> dict[str, object]:
        return {
            "predecessor": self.predecessor.to_json(),
            "update": self.update.to_json(),
            "candidate": self.candidate.to_json(),
            "certificate": self.certificate.to_json(),
            "heldout_policy": self.heldout_policy.to_json(),
            "report": self.report.to_json(),
        }


def _hash(label: str) -> str:
    return canonical_json_hash({"phase9_reference": label})


def _model(*, changed: bool) -> ModelIdentity:
    suffix = "candidate" if changed else "predecessor"
    return ModelIdentity(
        model_family=SELECTED_MODEL_FAMILY,
        architecture_hash=_hash("architecture"),
        weights_tree_hash=_hash(f"weights-{suffix}"),
        adapter_manifest_hash=_hash("adapter-empty"),
        tensor_manifest_hash=_hash(f"tensor-manifest-{suffix}"),
        tokenizer_hash=_hash("tokenizer"),
        vocabulary_hash=_hash("vocabulary"),
        parameter_count=1_024,
    )


def _policies() -> PolicyIdentity:
    return PolicyIdentity(
        training_policy_hash=_hash("training-policy"),
        optimizer_policy_hash=_hash("optimizer-policy"),
        data_curriculum_hash=_hash("data-curriculum"),
        generator_policy_hash=_hash("generator-policy"),
        planner_policy_hash=_hash("planner-policy"),
        retrieval_policy_hash=_hash("retrieval-policy"),
        memory_state_hash=_hash("memory-state"),
        tool_policy_hash=_hash("tool-policy"),
        verification_policy_hash=_hash("verification-policy"),
        resource_policy_hash=_hash("resource-policy"),
        self_model_hash=_hash("self-model"),
    )


def _self_hosting(policies: PolicyIdentity) -> SelfHostingBinding:
    return SelfHostingBinding(
        generator_component_hash=policies.generator_policy_hash,
        planner_component_hash=policies.planner_policy_hash,
        proposal_protocol_hash=_hash("proposal-protocol"),
        self_hosting_contract_hash=_hash("self-hosting-contract"),
    )


def build_phase9_reference_fixture() -> Phase9ReferenceFixture:
    baseline = TaskRecord(
        task_id="lean.baseline",
        task_class=SELECTED_TASK_CLASS,
        prompt_hash=_hash("baseline-prompt"),
        verifier_spec_hash=_hash("lean-verifier-spec"),
        partition="protected",
    )
    frontier_one = TaskRecord(
        task_id="lean.frontier_one",
        task_class=SELECTED_TASK_CLASS,
        prompt_hash=_hash("frontier-one-prompt"),
        verifier_spec_hash=_hash("lean-verifier-spec"),
        partition="heldout",
    )
    policies = _policies()
    self_hosting = _self_hosting(policies)
    predecessor_model = _model(changed=False)
    candidate_model = _model(changed=True)

    predecessor = LearnedRCLMState(
        package_id="phase9-reference-root",
        parent_package_id=None,
        base_state_hash=_hash("gate-d-base-initial"),
        model=predecessor_model,
        policies=policies,
        self_hosting=self_hosting,
        task_ledger=TaskLedger(
            tasks=(baseline,),
            certifications=(
                CertificationRecord(
                    task_id=baseline.task_id,
                    model_identity_hash=predecessor_model.model_identity_hash,
                    verifier_report_hash=_hash("baseline-predecessor-verifier-report"),
                    verified_output_hash=_hash("baseline-predecessor-output"),
                ),
            ),
        ),
        capability_frontier=CapabilityFrontier(task_ids=(baseline.task_id,)),
    )

    candidate = LearnedRCLMState(
        package_id="phase9-reference-successor",
        parent_package_id=predecessor.package_id,
        base_state_hash=_hash("gate-d-base-target"),
        model=candidate_model,
        policies=policies,
        self_hosting=self_hosting,
        task_ledger=TaskLedger(
            tasks=(baseline, frontier_one),
            certifications=(
                CertificationRecord(
                    task_id=baseline.task_id,
                    model_identity_hash=candidate_model.model_identity_hash,
                    verifier_report_hash=_hash("baseline-candidate-verifier-report"),
                    verified_output_hash=_hash("baseline-candidate-output"),
                ),
                CertificationRecord(
                    task_id=frontier_one.task_id,
                    model_identity_hash=candidate_model.model_identity_hash,
                    verifier_report_hash=_hash("frontier-one-verifier-report"),
                    verified_output_hash=_hash("frontier-one-output"),
                ),
            ),
        ),
        capability_frontier=CapabilityFrontier(
            task_ids=(baseline.task_id, frontier_one.task_id)
        ),
    )

    operation = UpdateOperation(
        operation_id="0001-model-weight-update",
        kind="weight_update",
        target="model_weights",
        component_path="model/weights",
        before_hash=predecessor.component_hash("model_weights"),
        after_hash=candidate.component_hash("model_weights"),
    )
    update = LearnedRCLMUpdate(
        transition_id="phase9-reference-transition",
        predecessor_state_hash=predecessor.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=_hash("gate-d-base-improvement-update"),
        operations=(operation,),
    )

    heldout_policy = HeldoutAccessPolicy(
        policy_id="phase9-heldout-isolation-v1",
        heldout_task_manifest_hash=_hash("heldout-task-manifest"),
        reference_answer_store_hash=_hash("external-reference-answer-store"),
        evaluator_policy_hash=_hash("pinned-lean-evaluator-policy"),
    )

    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=predecessor.state_hash,
        candidate_state_hash=candidate.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=_hash("gate-d-base-certificate"),
        capability_frontier_before_hash=predecessor.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate.capability_frontier.frontier_hash,
        protected_task_ids=(baseline.task_id,),
        new_task_ids=(frontier_one.task_id,),
        task_frontier_retention_evidence_hash=_hash("frontier-retention-evidence"),
        new_task_capability_evidence_hash=_hash("new-task-capability-evidence"),
        model_output_density_evidence_hash=_hash("model-output-density-evidence"),
        entropy_kl_qre_evidence_hash=_hash("entropy-kl-qre-evidence"),
        goal_drift_evidence_hash=_hash("goal-drift-evidence"),
        training_data_provenance_hash=_hash("training-data-provenance"),
        heldout_isolation_evidence_hash=_hash("heldout-isolation-evidence"),
        architecture_compatibility_hash=_hash("architecture-compatibility"),
        self_hosting_evidence_hash=_hash("self-hosting-evidence"),
        resource_evidence_hash=_hash("resource-evidence"),
        rollback_evidence_hash=_hash("rollback-evidence"),
        heldout_access_policy_hash=heldout_policy.policy_hash,
        active_generator_hash=predecessor.policies.generator_policy_hash,
        active_planner_hash=predecessor.policies.planner_policy_hash,
        proposal_protocol_hash=predecessor.self_hosting.proposal_protocol_hash,
    )

    report = validate_phase9_transition(
        predecessor,
        update,
        candidate,
        certificate,
        heldout_policy,
    )
    return Phase9ReferenceFixture(
        predecessor=predecessor,
        update=update,
        candidate=candidate,
        certificate=certificate,
        heldout_policy=heldout_policy,
        report=report,
    )


__all__ = ["Phase9ReferenceFixture", "build_phase9_reference_fixture"]
