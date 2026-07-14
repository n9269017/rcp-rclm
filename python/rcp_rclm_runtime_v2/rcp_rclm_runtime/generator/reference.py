from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal

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
from rcp_rclm_runtime.generator.records import (
    REFERENCE_GENERATOR_GRAMMAR_ID,
    REFERENCE_GENERATOR_OBJECTIVE_ID,
    REFERENCE_GENERATOR_POLICY_ID,
    REFERENCE_GENERATOR_WORKER_VERSION,
    DeclaredObjectiveRecord,
    GeneratorReasonCode,
    GeneratorResourceBudgetRecord,
    ReferenceGeneratorInputRecord,
    ReferenceGeneratorPolicyRecord,
    ReferencePredecessorPackageRecord,
    UntrustedProposalRecord,
)

REFERENCE_WORD_DEPTH: Final[int] = 1
REFERENCE_PROOF_LENGTH: Final[int] = 1
REFERENCE_PROPOSAL_LIMIT: Final[int] = 1
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
            "filesystem_writes": "denied",
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


def interpret_reference_input(
    generator_input: ReferenceGeneratorInputRecord,
) -> tuple[UntrustedProposalRecord | None, Sequence[GeneratorReasonCode]]:
    policy_reasons = _policy_reasons(generator_input.policy)
    if policy_reasons:
        return None, policy_reasons
    objective_reasons = _objective_reasons(generator_input.objective)
    if objective_reasons:
        return None, objective_reasons
    core = generator_input.predecessor_package.state.core
    if not isinstance(core, ClassicalBinaryStateRecord):
        return None, (GeneratorReasonCode.UNSUPPORTED_SCOPE,)
    expected_transition_id = reference_transition_id(
        core,
        generator_input.policy,
        generator_input.objective,
        generator_input.resource_budget,
    )
    expected_package_id = f"{expected_transition_id}.predecessor"
    if generator_input.predecessor_package.manifest.package_id != expected_package_id:
        return None, (GeneratorReasonCode.PIPELINE_BINDING_MISMATCH,)
    if core.state == "outside":
        return None, (GeneratorReasonCode.PREDECESSOR_OUTSIDE_DOMAIN,)
    if core.state == "initial":
        word: Literal["improve", "stabilize"] = "improve"
        witness: Literal["strict_improvement", "stable_continuation"] = (
            "strict_improvement"
        )
        resource_units = 1
    else:
        word = "stabilize"
        witness = "stable_continuation"
        resource_units = 0
    budget_reasons = _budget_reasons(
        generator_input.resource_budget,
        resource_units=resource_units,
    )
    if budget_reasons:
        return None, budget_reasons
    proposal_payload = {
        "schema_id": "runtime.phase5_reference_proposal_identity.v2",
        "generator_input_hash": generator_input.input_hash,
        "word": word,
        "witness": witness,
        "proposal": word,
    }
    proposal_id = f"phase5a.proposal.{canonical_json_hash(proposal_payload)[:40]}"
    return (
        UntrustedProposalRecord(
            proposal_id=proposal_id,
            word=word,
            witness=witness,
            proposal=word,
            word_depth=REFERENCE_WORD_DEPTH,
            proof_length=REFERENCE_PROOF_LENGTH,
            resource_units=resource_units,
            predecessor_package_id=(
                generator_input.predecessor_package.manifest.package_id
            ),
            predecessor_manifest_hash=(
                generator_input.predecessor_package.manifest_hash
            ),
            policy_hash=generator_input.policy.policy_hash,
            objective_hash=generator_input.objective.objective_hash,
            budget_hash=generator_input.resource_budget.budget_hash,
            generator_input_hash=generator_input.input_hash,
        ),
        (),
    )


def _policy_reasons(
    policy: ReferenceGeneratorPolicyRecord,
) -> Sequence[GeneratorReasonCode]:
    expected = reference_generator_policy()
    return () if policy == expected else (GeneratorReasonCode.POLICY_MISMATCH,)


def _objective_reasons(
    objective: DeclaredObjectiveRecord,
) -> Sequence[GeneratorReasonCode]:
    if objective.objective_id != REFERENCE_GENERATOR_OBJECTIVE_ID:
        return (GeneratorReasonCode.OBJECTIVE_MISMATCH,)
    if (
        objective.scope != "gate_b_classical"
        or objective.goal != "biased_target"
        or objective.trajectory_mode != "strict_then_stable"
    ):
        return (GeneratorReasonCode.OBJECTIVE_MISMATCH,)
    return ()


def _budget_reasons(
    budget: GeneratorResourceBudgetRecord,
    *,
    resource_units: int,
) -> Sequence[GeneratorReasonCode]:
    sufficient = (
        budget.proposal_limit >= REFERENCE_PROPOSAL_LIMIT
        and budget.word_depth_limit >= REFERENCE_WORD_DEPTH
        and budget.proof_length_limit >= REFERENCE_PROOF_LENGTH
        and budget.resource_units >= resource_units
        and budget.model_invocation_limit == 0
        and budget.network_request_limit == 0
        and budget.file_write_limit == 0
    )
    return () if sufficient else (GeneratorReasonCode.BUDGET_EXCEEDED,)


def _root_certificate_hash(transition_id: str) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.phase4_root_certificate.v2",
            "transition_id": transition_id,
        }
    )
