from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Literal, TypeAlias, TypeVar, cast

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    FrozenJson,
    freeze_json,
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
    thaw_json,
)
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord, RclmStateRecord

REFERENCE_POLICY_SCHEMA_ID = "runtime.phase5a_reference_generator_policy.v2"
REFERENCE_OBJECTIVE_SCHEMA_ID = "runtime.phase5a_reference_objective.v2"
REFERENCE_BUDGET_SCHEMA_ID = "runtime.phase5a_reference_budget.v2"
GENERATOR_PREDECESSOR_SCHEMA_ID = "runtime.phase5a_generator_predecessor_view.v2"
REFERENCE_GENERATOR_INPUT_SCHEMA_ID = "runtime.phase5a_reference_generator_input.v2"
REFERENCE_PROPOSAL_SCHEMA_ID = "runtime.phase5a_reference_proposal.v2"
GENERATOR_STAGE_RESULT_SCHEMA_ID = "runtime.phase5a_generator_stage_result.v2"

GeneratorWord: TypeAlias = Literal["improve", "stabilize"]
GeneratorWitness: TypeAlias = Literal["strict_improvement", "stable_continuation"]
GeneratorProposalName: TypeAlias = Literal["improve", "stabilize"]
GeneratorStageStatus: TypeAlias = Literal["pass", "fail", "indeterminate", "not_evaluated"]
GeneratorVerdict: TypeAlias = Literal["accept", "reject", "indeterminate"]
ProcessVerdict: TypeAlias = Literal["success", "failure", "indeterminate"]
LiteralText = TypeVar("LiteralText", bound=str)


class GeneratorReasonCode(StrEnum):
    SCHEMA_MALFORMED = "GENERATOR_SCHEMA_MALFORMED"
    UNSUPPORTED_SCOPE = "GENERATOR_UNSUPPORTED_SCOPE"
    OUTSIDE_SEED_DOMAIN = "GENERATOR_OUTSIDE_SEED_DOMAIN"
    POLICY_MISMATCH = "GENERATOR_POLICY_MISMATCH"
    OBJECTIVE_MISMATCH = "GENERATOR_OBJECTIVE_MISMATCH"
    BUDGET_EXCEEDED = "GENERATOR_BUDGET_EXCEEDED"
    PROCESS_FAILED = "GENERATOR_PROCESS_FAILED"
    PROCESS_TIMEOUT = "GENERATOR_PROCESS_TIMEOUT"
    OUTPUT_MALFORMED = "GENERATOR_OUTPUT_MALFORMED"
    WORKER_SOURCE_REJECTED = "GENERATOR_WORKER_SOURCE_REJECTED"
    REPLAY_MISMATCH = "GENERATOR_REPLAY_MISMATCH"
    GRAMMAR_MISMATCH = "GENERATOR_GRAMMAR_MISMATCH"
    CERTIFICATE_CONSTRUCTION_FAILED = "CERTIFICATE_CONSTRUCTION_FAILED"
    SELECTION_FAILED = "SELECTION_FAILED"
    REALIZATION_FAILED = "REALIZATION_FAILED"
    LEAN_VERIFICATION_FAILED = "LEAN_VERIFICATION_FAILED"
    CHECKER_REJECTED = "CHECKER_REJECTED"
    INTERNAL_ERROR = "GENERATOR_INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class ReferenceGeneratorPolicyRecord:
    grammar_id: str
    implementation_id: str
    formal_source_commit: str
    scope: Literal["gate_b_classical"]
    max_word_depth: int
    max_proof_length: int
    max_proposals: int
    process_mode: Literal["isolated_stdin_stdout"]
    policy_version: str

    schema_id: ClassVar[str] = REFERENCE_POLICY_SCHEMA_ID

    def __post_init__(self) -> None:
        for name in ("grammar_id", "implementation_id", "formal_source_commit", "policy_version"):
            require_string(getattr(self, name), f"reference_policy.{name}")
        _require_exact(self.scope, "gate_b_classical", "reference_policy.scope")
        _require_exact(
            self.process_mode,
            "isolated_stdin_stdout",
            "reference_policy.process_mode",
        )
        for name in ("max_word_depth", "max_proof_length", "max_proposals"):
            _require_positive(getattr(self, name), f"reference_policy.{name}")

    @property
    def policy_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object, path: str = "reference_policy") -> ReferenceGeneratorPolicyRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "grammar_id",
                "implementation_id",
                "formal_source_commit",
                "scope",
                "max_word_depth",
                "max_proof_length",
                "max_proposals",
                "process_mode",
                "policy_version",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            grammar_id=require_string(obj["grammar_id"], f"{path}.grammar_id"),
            implementation_id=require_string(obj["implementation_id"], f"{path}.implementation_id"),
            formal_source_commit=require_string(obj["formal_source_commit"], f"{path}.formal_source_commit"),
            scope=_literal(obj["scope"], f"{path}.scope", {"gate_b_classical"}),
            max_word_depth=require_structural_integer(obj["max_word_depth"], f"{path}.max_word_depth", minimum=1),
            max_proof_length=require_structural_integer(obj["max_proof_length"], f"{path}.max_proof_length", minimum=1),
            max_proposals=require_structural_integer(obj["max_proposals"], f"{path}.max_proposals", minimum=1),
            process_mode=_literal(
                obj["process_mode"],
                f"{path}.process_mode",
                {"isolated_stdin_stdout"},
            ),
            policy_version=require_string(obj["policy_version"], f"{path}.policy_version"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "grammar_id": self.grammar_id,
            "implementation_id": self.implementation_id,
            "formal_source_commit": self.formal_source_commit,
            "scope": self.scope,
            "max_word_depth": self.max_word_depth,
            "max_proof_length": self.max_proof_length,
            "max_proposals": self.max_proposals,
            "process_mode": self.process_mode,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True, slots=True)
class ReferenceObjectiveRecord:
    objective_id: str
    scope: Literal["gate_b_classical"]
    target_state: Literal["target"]
    strict_from_states: Sequence[Literal["initial"]]
    stable_from_states: Sequence[Literal["target"]]

    schema_id: ClassVar[str] = REFERENCE_OBJECTIVE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.objective_id, "reference_objective.objective_id")
        object.__setattr__(self, "strict_from_states", tuple(self.strict_from_states))
        object.__setattr__(self, "stable_from_states", tuple(self.stable_from_states))
        _require_exact(self.scope, "gate_b_classical", "reference_objective.scope")
        _require_exact(self.target_state, "target", "reference_objective.target_state")
        if self.strict_from_states != ("initial",):
            raise SchemaValidationError("reference_objective.strict_from_states", "expected exactly the initial state")
        if self.stable_from_states != ("target",):
            raise SchemaValidationError("reference_objective.stable_from_states", "expected exactly the target state")

    @property
    def objective_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object, path: str = "reference_objective") -> ReferenceObjectiveRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "objective_id",
                "scope",
                "target_state",
                "strict_from_states",
                "stable_from_states",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            objective_id=require_string(obj["objective_id"], f"{path}.objective_id"),
            scope=_literal(obj["scope"], f"{path}.scope", {"gate_b_classical"}),
            target_state=_literal(obj["target_state"], f"{path}.target_state", {"target"}),
            strict_from_states=_literal_array(obj["strict_from_states"], f"{path}.strict_from_states", {"initial"}),
            stable_from_states=_literal_array(obj["stable_from_states"], f"{path}.stable_from_states", {"target"}),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "objective_id": self.objective_id,
            "scope": self.scope,
            "target_state": self.target_state,
            "strict_from_states": list(self.strict_from_states),
            "stable_from_states": list(self.stable_from_states),
        }


@dataclass(frozen=True, slots=True)
class ReferenceBudgetRecord:
    max_budget_units: int
    max_word_depth: int
    max_proof_length: int
    max_proposals: int
    process_timeout_seconds: int

    schema_id: ClassVar[str] = REFERENCE_BUDGET_SCHEMA_ID

    def __post_init__(self) -> None:
        for name in (
            "max_budget_units",
            "max_word_depth",
            "max_proof_length",
            "max_proposals",
            "process_timeout_seconds",
        ):
            _require_positive(getattr(self, name), f"reference_budget.{name}")
        if self.process_timeout_seconds > 300:
            raise SchemaValidationError("reference_budget.process_timeout_seconds", "timeout must not exceed 300 seconds")

    @classmethod
    def from_json(cls, value: object, path: str = "reference_budget") -> ReferenceBudgetRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "max_budget_units",
                "max_word_depth",
                "max_proof_length",
                "max_proposals",
                "process_timeout_seconds",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            max_budget_units=require_structural_integer(obj["max_budget_units"], f"{path}.max_budget_units", minimum=1),
            max_word_depth=require_structural_integer(obj["max_word_depth"], f"{path}.max_word_depth", minimum=1),
            max_proof_length=require_structural_integer(obj["max_proof_length"], f"{path}.max_proof_length", minimum=1),
            max_proposals=require_structural_integer(obj["max_proposals"], f"{path}.max_proposals", minimum=1),
            process_timeout_seconds=require_structural_integer(
                obj["process_timeout_seconds"],
                f"{path}.process_timeout_seconds",
                minimum=1,
                maximum=300,
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "max_budget_units": self.max_budget_units,
            "max_word_depth": self.max_word_depth,
            "max_proof_length": self.max_proof_length,
            "max_proposals": self.max_proposals,
            "process_timeout_seconds": self.process_timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class GeneratorPredecessorViewRecord:
    package_id: str
    manifest_hash: str
    semantic_tree_hash: str
    state_hash: str
    state: RclmStateRecord

    schema_id: ClassVar[str] = GENERATOR_PREDECESSOR_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.package_id, "generator_predecessor.package_id")
        for name in ("manifest_hash", "semantic_tree_hash", "state_hash"):
            validate_hash256(getattr(self, name), f"generator_predecessor.{name}")
        if canonical_json_hash(self.state.to_json()) != self.state_hash:
            raise SchemaValidationError("generator_predecessor.state_hash", "state hash does not match canonical state")
        if not isinstance(self.state.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("generator_predecessor.state.core", "Phase 5A supports only Gate B")
        if self.state.core.state not in {"initial", "target"}:
            raise SchemaValidationError("generator_predecessor.state.core.state", "outside bounded seed domain")

    @classmethod
    def from_json(cls, value: object, path: str = "generator_predecessor") -> GeneratorPredecessorViewRecord:
        obj = strict_object(
            value,
            path,
            {"schema_id", "package_id", "manifest_hash", "semantic_tree_hash", "state_hash", "state"},
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            package_id=require_string(obj["package_id"], f"{path}.package_id"),
            manifest_hash=require_string(obj["manifest_hash"], f"{path}.manifest_hash"),
            semantic_tree_hash=require_string(obj["semantic_tree_hash"], f"{path}.semantic_tree_hash"),
            state_hash=require_string(obj["state_hash"], f"{path}.state_hash"),
            state=RclmStateRecord.from_json(obj["state"], f"{path}.state"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "package_id": self.package_id,
            "manifest_hash": self.manifest_hash,
            "semantic_tree_hash": self.semantic_tree_hash,
            "state_hash": self.state_hash,
            "state": self.state.to_json(),
        }


@dataclass(frozen=True, slots=True)
class ReferenceGeneratorInputRecord:
    transition_id: str
    predecessor: GeneratorPredecessorViewRecord
    policy: ReferenceGeneratorPolicyRecord
    objective: ReferenceObjectiveRecord
    budget: ReferenceBudgetRecord
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = REFERENCE_GENERATOR_INPUT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "reference_generator_input.transition_id")
        _require_exact(self.contract_version, CONTRACT_VERSION, "reference_generator_input.contract_version")
        if self.policy.scope != self.objective.scope:
            raise SchemaValidationError("reference_generator_input.scope", "policy and objective scopes differ")
        if self.budget.max_word_depth < self.policy.max_word_depth:
            raise SchemaValidationError("reference_generator_input.budget.max_word_depth", "budget below policy bound")
        if self.budget.max_proof_length < self.policy.max_proof_length:
            raise SchemaValidationError("reference_generator_input.budget.max_proof_length", "budget below policy bound")
        if self.budget.max_proposals < self.policy.max_proposals:
            raise SchemaValidationError("reference_generator_input.budget.max_proposals", "budget below policy bound")

    @property
    def input_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object, path: str = "reference_generator_input") -> ReferenceGeneratorInputRecord:
        obj = strict_object(
            value,
            path,
            {"schema_id", "contract_version", "transition_id", "predecessor", "policy", "objective", "budget"},
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            transition_id=require_string(obj["transition_id"], f"{path}.transition_id"),
            predecessor=GeneratorPredecessorViewRecord.from_json(obj["predecessor"], f"{path}.predecessor"),
            policy=ReferenceGeneratorPolicyRecord.from_json(obj["policy"], f"{path}.policy"),
            objective=ReferenceObjectiveRecord.from_json(obj["objective"], f"{path}.objective"),
            budget=ReferenceBudgetRecord.from_json(obj["budget"], f"{path}.budget"),
            contract_version=require_string(obj["contract_version"], f"{path}.contract_version"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "predecessor": self.predecessor.to_json(),
            "policy": self.policy.to_json(),
            "objective": self.objective.to_json(),
            "budget": self.budget.to_json(),
        }


@dataclass(frozen=True, slots=True)
class ReferenceProposalRecord:
    request_hash: str
    policy_hash: str
    predecessor_manifest_hash: str
    objective_hash: str
    word: GeneratorWord
    witness: GeneratorWitness
    proposal: GeneratorProposalName
    word_depth: int
    proof_length: int
    budget_units_used: int

    schema_id: ClassVar[str] = REFERENCE_PROPOSAL_SCHEMA_ID

    def __post_init__(self) -> None:
        for name in ("request_hash", "policy_hash", "predecessor_manifest_hash", "objective_hash"):
            validate_hash256(getattr(self, name), f"reference_proposal.{name}")
        _require_exact_set(self.word, {"improve", "stabilize"}, "reference_proposal.word")
        _require_exact_set(
            self.witness,
            {"strict_improvement", "stable_continuation"},
            "reference_proposal.witness",
        )
        _require_exact_set(self.proposal, {"improve", "stabilize"}, "reference_proposal.proposal")
        for name in ("word_depth", "proof_length", "budget_units_used"):
            _require_nonnegative(getattr(self, name), f"reference_proposal.{name}")

    @property
    def proposal_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object, path: str = "reference_proposal") -> ReferenceProposalRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "request_hash",
                "policy_hash",
                "predecessor_manifest_hash",
                "objective_hash",
                "word",
                "witness",
                "proposal",
                "word_depth",
                "proof_length",
                "budget_units_used",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            request_hash=require_string(obj["request_hash"], f"{path}.request_hash"),
            policy_hash=require_string(obj["policy_hash"], f"{path}.policy_hash"),
            predecessor_manifest_hash=require_string(obj["predecessor_manifest_hash"], f"{path}.predecessor_manifest_hash"),
            objective_hash=require_string(obj["objective_hash"], f"{path}.objective_hash"),
            word=_literal(obj["word"], f"{path}.word", {"improve", "stabilize"}),
            witness=_literal(
                obj["witness"],
                f"{path}.witness",
                {"strict_improvement", "stable_continuation"},
            ),
            proposal=_literal(obj["proposal"], f"{path}.proposal", {"improve", "stabilize"}),
            word_depth=require_structural_integer(obj["word_depth"], f"{path}.word_depth", minimum=0),
            proof_length=require_structural_integer(obj["proof_length"], f"{path}.proof_length", minimum=0),
            budget_units_used=require_structural_integer(obj["budget_units_used"], f"{path}.budget_units_used", minimum=0),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "request_hash": self.request_hash,
            "policy_hash": self.policy_hash,
            "predecessor_manifest_hash": self.predecessor_manifest_hash,
            "objective_hash": self.objective_hash,
            "word": self.word,
            "witness": self.witness,
            "proposal": self.proposal,
            "word_depth": self.word_depth,
            "proof_length": self.proof_length,
            "budget_units_used": self.budget_units_used,
        }


@dataclass(frozen=True, slots=True)
class GeneratorStageResult:
    status: GeneratorStageStatus
    reason_codes: Sequence[GeneratorReasonCode]
    evidence: FrozenJson

    schema_id: ClassVar[str] = GENERATOR_STAGE_RESULT_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "evidence", freeze_json(thaw_json(self.evidence)))
        _require_exact_set(
            self.status,
            {"pass", "fail", "indeterminate", "not_evaluated"},
            "generator_stage_result.status",
        )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError("generator_stage_result.reason_codes", "reason codes must be unique")
        if self.status == "pass" and self.reason_codes:
            raise SchemaValidationError("generator_stage_result.reason_codes", "passing stage cannot contain reasons")
        if self.status in {"fail", "indeterminate"} and not self.reason_codes:
            raise SchemaValidationError("generator_stage_result.reason_codes", "nonpassing stage requires a reason")
        if self.status == "not_evaluated" and self.reason_codes:
            raise SchemaValidationError("generator_stage_result.reason_codes", "not-evaluated stage cannot contain reasons")

    @classmethod
    def from_evidence(
        cls,
        status: GeneratorStageStatus,
        reason_codes: Sequence[GeneratorReasonCode],
        evidence: object,
    ) -> GeneratorStageResult:
        return cls(status, tuple(reason_codes), freeze_json(evidence))

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "status": self.status,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "evidence": thaw_json(self.evidence),
        }


def _literal(value: object, path: str, allowed: set[str]) -> LiteralText:
    text = require_string(value, path)
    _require_exact_set(text, allowed, path)
    return cast(LiteralText, text)


def _literal_array(value: object, path: str, allowed: set[str]) -> Sequence[LiteralText]:
    if not isinstance(value, list):
        raise SchemaValidationError(path, "expected an array")
    return tuple(_literal(item, f"{path}[{index}]", allowed) for index, item in enumerate(value))


def _require_exact(value: str, expected: str, path: str) -> None:
    if value != expected:
        raise SchemaValidationError(path, f"expected {expected}")


def _require_exact_set(value: str, allowed: set[str], path: str) -> None:
    if value not in allowed:
        raise SchemaValidationError(path, f"unsupported value: {value}")


def _require_positive(value: object, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SchemaValidationError(path, "expected a positive integer")


def _require_nonnegative(value: object, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaValidationError(path, "expected a nonnegative integer")
