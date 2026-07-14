from __future__ import annotations

from typing import Literal

from rcp_rclm_runtime.canonical.hashing import (
    canonical_json_hash,
    file_record_from_bytes,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.schema.package import PackageManifestRecord
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord
from rcp_rclm_runtime.checker.policy import (
    CHECKER_POLICY_HASH,
    CLAIM_BOUNDARY_HASH,
    LEAN_VERIFIER_POLICY_HASH,
)
from rcp_rclm_runtime.checker.reference import (
    canonical_rclm_state,
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.generator.grammar import (
    REFERENCE_PROOF_LENGTH,
    REFERENCE_PROPOSAL_LIMIT,
    REFERENCE_WORD_DEPTH,
    interpret_reference_input,
)
from rcp_rclm_runtime.generator.records import (
    REFERENCE_GENERATOR_GRAMMAR_ID,
    REFERENCE_GENERATOR_OBJECTIVE_ID,
    REFERENCE_GENERATOR_POLICY_ID,
    REFERENCE_GENERATOR_WORKER_VERSION,
    DeclaredObjectiveRecord,
    GeneratorResourceBudgetRecord,
    ReferenceGeneratorInputRecord,
    ReferenceGeneratorPolicyRecord,
    ReferencePredecessorPackageRecord,
)

ReferencePredecessorName = Literal["outside", "initial", "target"]


def reference_generator_policy() -> ReferenceGeneratorPolicyRecord:
    return ReferenceGeneratorPolicyRecord(
        policy_id=REFERENCE_GENERATOR_POLICY_ID,
        grammar_id=REFERENCE_GENERATOR_GRAMMAR_ID,
        supported_scope="gate_b_classical",
        max_word_depth=REFERENCE_WORD_DEPTH,
        max_proof_length=REFERENCE_PROOF_LENGTH,
        proposal_limit=REFERENCE_PROPOSAL_LIMIT,
        open_ended_generation_allowed=False,
        model_invocation_limit=0,
        network_request_limit=0,
        file_write_limit=0,
    )


def reference_declared_objective(
    task_id: str = "phase5a.reference.binary",
) -> DeclaredObjectiveRecord:
    return DeclaredObjectiveRecord(
        task_id=task_id,
        objective_id=REFERENCE_GENERATOR_OBJECTIVE_ID,
        scope="gate_b_classical",
        goal="biased_target",
        trajectory_mode="strict_then_stable",
    )


def reference_generator_budget(
    *,
    resource_units: int = 1,
    timeout_seconds: int = 30,
) -> GeneratorResourceBudgetRecord:
    return GeneratorResourceBudgetRecord(
        proposal_limit=REFERENCE_PROPOSAL_LIMIT,
        word_depth_limit=REFERENCE_WORD_DEPTH,
        proof_length_limit=REFERENCE_PROOF_LENGTH,
        resource_units=resource_units,
        timeout_seconds=timeout_seconds,
        model_invocation_limit=0,
        network_request_limit=0,
        file_write_limit=0,
    )


def reference_transition_seed(
    state: ClassicalBinaryStateRecord,
    policy: ReferenceGeneratorPolicyRecord,
    objective: DeclaredObjectiveRecord,
    budget: GeneratorResourceBudgetRecord,
) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.phase5_reference_transition_seed.v2",
            "state": state.to_json(),
            "policy": policy.to_json(),
            "objective": objective.to_json(),
            "resource_budget": budget.to_json(),
        }
    )


def reference_transition_id(
    state: ClassicalBinaryStateRecord,
    policy: ReferenceGeneratorPolicyRecord,
    objective: DeclaredObjectiveRecord,
    budget: GeneratorResourceBudgetRecord,
) -> str:
    seed = reference_transition_seed(state, policy, objective, budget)
    return f"phase5a.{seed[:40]}"


def build_reference_generator_input(
    predecessor: ReferencePredecessorName = "initial",
    *,
    task_id: str = "phase5a.reference.binary",
    resource_units: int = 1,
    timeout_seconds: int = 30,
) -> ReferenceGeneratorInputRecord:
    policy = reference_generator_policy()
    objective = reference_declared_objective(task_id)
    budget = reference_generator_budget(
        resource_units=resource_units,
        timeout_seconds=timeout_seconds,
    )
    core_state = ClassicalBinaryStateRecord(predecessor)
    state = canonical_rclm_state(core_state)
    transition_id = reference_transition_id(core_state, policy, objective, budget)
    environment_hash = canonical_json_hash(
        {
            "schema_id": "runtime.phase5_reference_environment.v2",
            "transition_id": transition_id,
            "worker_version": REFERENCE_GENERATOR_WORKER_VERSION,
            "network": "denied",
            "model": "absent",
            "filesystem_access_after_startup": "denied",
        }
    )
    resource_record = reference_resource_record(
        precision_bits=256,
        budget_units=resource_units,
        consumed_units=resource_units,
        environment_hash=environment_hash,
    )
    trust_anchor_hash = canonical_json_hash(reference_trust_anchor().to_json())
    resource_record_hash = canonical_json_hash(resource_record.to_json())
    state_file = file_record_from_bytes(
        "state/predecessor.json",
        "0644",
        canonical_json_bytes(state.to_json()),
    )
    manifest = PackageManifestRecord(
        package_id=f"{transition_id}.predecessor",
        parent_package_id=None,
        parent_manifest_hash=None,
        semantic_tree_hash=semantic_tree_hash((state_file,)),
        candidate_hash=canonical_json_hash(state.to_json()),
        certificate_packet_hash=_root_certificate_hash(transition_id),
        checker_policy_hash=CHECKER_POLICY_HASH,
        lean_verifier_policy_hash=LEAN_VERIFIER_POLICY_HASH,
        trust_anchor_hash=trust_anchor_hash,
        resource_record_hash=resource_record_hash,
        claim_boundary_hash=CLAIM_BOUNDARY_HASH,
    )
    return ReferenceGeneratorInputRecord(
        predecessor_package=ReferencePredecessorPackageRecord(
            manifest=manifest,
            state=state,
        ),
        policy=policy,
        objective=objective,
        resource_budget=budget,
    )


def _root_certificate_hash(transition_id: str) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.phase4_root_certificate.v2",
            "transition_id": transition_id,
        }
    )


__all__ = [
    "build_reference_generator_input",
    "interpret_reference_input",
    "reference_declared_objective",
    "reference_generator_budget",
    "reference_generator_policy",
    "reference_transition_id",
    "reference_transition_seed",
]
