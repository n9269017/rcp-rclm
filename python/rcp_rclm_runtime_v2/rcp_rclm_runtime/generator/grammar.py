from __future__ import annotations

from typing import Final

from rcp_rclm_runtime._version import FORMAL_SOURCE_COMMIT
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord
from rcp_rclm_runtime.generator.protocol import (
    GeneratorProposalName,
    GeneratorReasonCode,
    GeneratorStageResult,
    GeneratorWitness,
    GeneratorWord,
    ReferenceBudgetRecord,
    ReferenceGeneratorInputRecord,
    ReferenceGeneratorPolicyRecord,
    ReferenceObjectiveRecord,
    ReferenceProposalRecord,
)

REFERENCE_GRAMMAR_ID: Final[str] = (
    "RcpRclmFormalCoreV2.RCLM.ClassicalBinary.boundedPacketGrammar"
)
REFERENCE_GENERATOR_IMPLEMENTATION_ID: Final[str] = (
    "rcp-rclm-phase5a-bounded-reference-generator-v1"
)
REFERENCE_GENERATOR_POLICY_VERSION: Final[str] = (
    "rcp-rclm-phase5a-reference-policy-v1"
)
REFERENCE_OBJECTIVE_ID: Final[str] = "gate-b-biased-target-alignment-v1"
REFERENCE_WORD_DEPTH: Final[int] = 1
REFERENCE_PROOF_LENGTH: Final[int] = 1
REFERENCE_MAX_PROPOSALS: Final[int] = 1
REFERENCE_MAX_BUDGET_UNITS: Final[int] = 1
REFERENCE_PROCESS_TIMEOUT_SECONDS: Final[int] = 30


def reference_policy() -> ReferenceGeneratorPolicyRecord:
    return ReferenceGeneratorPolicyRecord(
        grammar_id=REFERENCE_GRAMMAR_ID,
        implementation_id=REFERENCE_GENERATOR_IMPLEMENTATION_ID,
        formal_source_commit=FORMAL_SOURCE_COMMIT,
        scope="gate_b_classical",
        max_word_depth=REFERENCE_WORD_DEPTH,
        max_proof_length=REFERENCE_PROOF_LENGTH,
        max_proposals=REFERENCE_MAX_PROPOSALS,
        process_mode="isolated_stdin_stdout",
        policy_version=REFERENCE_GENERATOR_POLICY_VERSION,
    )


def reference_objective() -> ReferenceObjectiveRecord:
    return ReferenceObjectiveRecord(
        objective_id=REFERENCE_OBJECTIVE_ID,
        scope="gate_b_classical",
        target_state="target",
        strict_from_states=("initial",),
        stable_from_states=("target",),
    )


def reference_budget() -> ReferenceBudgetRecord:
    return ReferenceBudgetRecord(
        max_budget_units=REFERENCE_MAX_BUDGET_UNITS,
        max_word_depth=REFERENCE_WORD_DEPTH,
        max_proof_length=REFERENCE_PROOF_LENGTH,
        max_proposals=REFERENCE_MAX_PROPOSALS,
        process_timeout_seconds=REFERENCE_PROCESS_TIMEOUT_SECONDS,
    )


def expected_word_for_state(state: str) -> GeneratorWord:
    if state == "initial":
        return "improve"
    if state == "target":
        return "stabilize"
    raise SchemaValidationError(
        "reference_generator_input.predecessor.state",
        "predecessor is outside the bounded seed domain",
    )


def witness_for_word(word: GeneratorWord) -> GeneratorWitness:
    if word == "improve":
        return "strict_improvement"
    return "stable_continuation"


def proposal_for_word(word: GeneratorWord) -> GeneratorProposalName:
    if word == "improve":
        return "improve"
    return "stabilize"


def certificate_name_for_word(word: GeneratorWord) -> str:
    if word == "improve":
        return "improvement"
    return "stability"


def update_name_for_proposal(proposal: GeneratorProposalName) -> str:
    if proposal == "improve":
        return "improve"
    return "stay"


def engine_resource_used_for_word(word: GeneratorWord) -> int:
    if word == "improve":
        return 1
    return 0


def generate_reference_proposal(
    request: ReferenceGeneratorInputRecord,
) -> ReferenceProposalRecord:
    _validate_public_configuration(request)
    core = request.predecessor.state.core
    if not isinstance(core, ClassicalBinaryStateRecord):
        raise SchemaValidationError(
            "reference_generator_input.predecessor.state.core",
            "Phase 5A supports only the bounded classical grammar",
        )
    word = expected_word_for_state(core.state)
    used = engine_resource_used_for_word(word)
    if used > request.budget.max_budget_units:
        raise SchemaValidationError(
            "reference_generator_input.budget.max_budget_units",
            "bounded word exceeds the declared resource budget",
        )
    return ReferenceProposalRecord(
        request_hash=request.input_hash,
        policy_hash=request.policy.policy_hash,
        predecessor_manifest_hash=request.predecessor.manifest_hash,
        objective_hash=request.objective.objective_hash,
        word=word,
        witness=witness_for_word(word),
        proposal=proposal_for_word(word),
        word_depth=REFERENCE_WORD_DEPTH,
        proof_length=REFERENCE_PROOF_LENGTH,
        budget_units_used=used,
    )


def validate_untrusted_proposal(
    request: ReferenceGeneratorInputRecord,
    proposal: ReferenceProposalRecord,
) -> GeneratorStageResult:
    try:
        expected = generate_reference_proposal(request)
    except SchemaValidationError as exc:
        return GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.SCHEMA_MALFORMED,),
            {
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
    checks = {
        "request_hash": proposal.request_hash == request.input_hash,
        "policy_hash": proposal.policy_hash == request.policy.policy_hash,
        "predecessor_manifest_hash": (
            proposal.predecessor_manifest_hash == request.predecessor.manifest_hash
        ),
        "objective_hash": proposal.objective_hash == request.objective.objective_hash,
        "word": proposal.word == expected.word,
        "witness": proposal.witness == expected.witness,
        "proposal": proposal.proposal == expected.proposal,
        "word_depth": proposal.word_depth == expected.word_depth,
        "proof_length": proposal.proof_length == expected.proof_length,
        "budget_units_used": proposal.budget_units_used == expected.budget_units_used,
        "proposal_count": request.budget.max_proposals >= 1,
    }
    reasons: list[GeneratorReasonCode] = []
    if not checks["request_hash"] or not checks["predecessor_manifest_hash"]:
        reasons.append(GeneratorReasonCode.REPLAY_MISMATCH)
    if not checks["policy_hash"]:
        reasons.append(GeneratorReasonCode.POLICY_MISMATCH)
    if not checks["objective_hash"]:
        reasons.append(GeneratorReasonCode.OBJECTIVE_MISMATCH)
    grammar_fields = (
        "word",
        "witness",
        "proposal",
        "word_depth",
        "proof_length",
    )
    if not all(checks[field] for field in grammar_fields):
        reasons.append(GeneratorReasonCode.GRAMMAR_MISMATCH)
    if not checks["budget_units_used"] or not checks["proposal_count"]:
        reasons.append(GeneratorReasonCode.BUDGET_EXCEEDED)
    unique = tuple(dict.fromkeys(reasons))
    return GeneratorStageResult.from_evidence(
        "pass" if not unique else "fail",
        unique,
        {
            **checks,
            "expected_proposal_hash": expected.proposal_hash,
            "observed_proposal_hash": proposal.proposal_hash,
            "candidate_successor_field_consumed": False,
            "certificate_field_consumed": False,
            "acceptance_field_consumed": False,
        },
    )


def _validate_public_configuration(request: ReferenceGeneratorInputRecord) -> None:
    expected_policy = reference_policy()
    expected_objective = reference_objective()
    if request.policy != expected_policy:
        raise SchemaValidationError(
            "reference_generator_input.policy",
            "public policy differs from the frozen bounded grammar policy",
        )
    if request.objective != expected_objective:
        raise SchemaValidationError(
            "reference_generator_input.objective",
            "declared objective differs from the frozen reference objective",
        )
    if request.budget.max_word_depth < REFERENCE_WORD_DEPTH:
        raise SchemaValidationError(
            "reference_generator_input.budget.max_word_depth",
            "word-depth budget is insufficient",
        )
    if request.budget.max_proof_length < REFERENCE_PROOF_LENGTH:
        raise SchemaValidationError(
            "reference_generator_input.budget.max_proof_length",
            "proof-length budget is insufficient",
        )
    if request.budget.max_proposals < REFERENCE_MAX_PROPOSALS:
        raise SchemaValidationError(
            "reference_generator_input.budget.max_proposals",
            "proposal-count budget is insufficient",
        )
