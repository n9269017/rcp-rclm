from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord
from rcp_rclm_runtime.generator.records import (
    REFERENCE_GENERATOR_GRAMMAR_ID,
    REFERENCE_GENERATOR_OBJECTIVE_ID,
    REFERENCE_GENERATOR_POLICY_ID,
    DeclaredObjectiveRecord,
    GeneratorReasonCode,
    GeneratorResourceBudgetRecord,
    ReferenceGeneratorInputRecord,
    ReferenceGeneratorPolicyRecord,
    UntrustedProposalRecord,
)

REFERENCE_WORD_DEPTH: Final[int] = 1
REFERENCE_PROOF_LENGTH: Final[int] = 1
REFERENCE_PROPOSAL_LIMIT: Final[int] = 1


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
    expected_package_id = f"{_transition_id(generator_input)}.predecessor"
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


def _transition_id(generator_input: ReferenceGeneratorInputRecord) -> str:
    seed = canonical_json_hash(
        {
            "schema_id": "runtime.phase5_reference_transition_seed.v2",
            "state": generator_input.predecessor_package.state.core.to_json(),
            "policy": generator_input.policy.to_json(),
            "objective": generator_input.objective.to_json(),
            "resource_budget": generator_input.resource_budget.to_json(),
        }
    )
    return f"phase5a.{seed[:40]}"


def _policy_reasons(
    policy: ReferenceGeneratorPolicyRecord,
) -> Sequence[GeneratorReasonCode]:
    valid = (
        policy.policy_id == REFERENCE_GENERATOR_POLICY_ID
        and policy.grammar_id == REFERENCE_GENERATOR_GRAMMAR_ID
        and policy.supported_scope == "gate_b_classical"
        and policy.max_word_depth == REFERENCE_WORD_DEPTH
        and policy.max_proof_length == REFERENCE_PROOF_LENGTH
        and policy.proposal_limit == REFERENCE_PROPOSAL_LIMIT
        and not policy.open_ended_generation_allowed
        and policy.model_invocation_limit == 0
        and policy.network_request_limit == 0
        and policy.file_write_limit == 0
    )
    return () if valid else (GeneratorReasonCode.POLICY_MISMATCH,)


def _objective_reasons(
    objective: DeclaredObjectiveRecord,
) -> Sequence[GeneratorReasonCode]:
    valid = (
        objective.objective_id == REFERENCE_GENERATOR_OBJECTIVE_ID
        and objective.scope == "gate_b_classical"
        and objective.goal == "biased_target"
        and objective.trajectory_mode == "strict_then_stable"
    )
    return () if valid else (GeneratorReasonCode.OBJECTIVE_MISMATCH,)


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
