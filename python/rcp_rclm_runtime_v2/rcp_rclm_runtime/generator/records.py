from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final, Literal, TypeAlias

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import (
    canonical_json_hash,
    file_record_from_bytes,
    semantic_tree_hash,
    validate_hash256,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
)
from rcp_rclm_runtime.schema.package import PackageManifestRecord
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord, RclmStateRecord

REFERENCE_GENERATOR_POLICY_SCHEMA_ID: Final[str] = (
    "runtime.phase5_reference_generator_policy.v2"
)
DECLARED_OBJECTIVE_SCHEMA_ID: Final[str] = "runtime.phase5_declared_objective.v2"
GENERATOR_RESOURCE_BUDGET_SCHEMA_ID: Final[str] = (
    "runtime.phase5_generator_resource_budget.v2"
)
REFERENCE_PREDECESSOR_PACKAGE_SCHEMA_ID: Final[str] = (
    "runtime.phase5_reference_predecessor_package.v2"
)
REFERENCE_GENERATOR_INPUT_SCHEMA_ID: Final[str] = (
    "runtime.phase5_reference_generator_input.v2"
)
UNTRUSTED_PROPOSAL_SCHEMA_ID: Final[str] = "runtime.phase5_untrusted_proposal.v2"
WORKER_SANDBOX_SCHEMA_ID: Final[str] = "runtime.phase5_worker_sandbox.v2"
WORKER_RESPONSE_SCHEMA_ID: Final[str] = "runtime.phase5_worker_response.v2"
PROCESS_OBSERVATION_SCHEMA_ID: Final[str] = (
    "runtime.phase5_generator_process_observation.v2"
)
GENERATOR_REPLAY_SCHEMA_ID: Final[str] = "runtime.phase5_generator_replay.v2"

REFERENCE_GENERATOR_POLICY_ID: Final[str] = (
    "rclm-classical-binary-bounded-seed-v1"
)
REFERENCE_GENERATOR_GRAMMAR_ID: Final[str] = (
    "rclm-classical-binary-bounded-packet-grammar-v1"
)
REFERENCE_GENERATOR_OBJECTIVE_ID: Final[str] = "biased-target-strict-then-stable-v1"
REFERENCE_GENERATOR_WORKER_VERSION: Final[str] = (
    "rcp-rclm-phase5-reference-generator-worker-v1"
)
REFERENCE_GENERATOR_MAX_INPUT_BYTES: Final[int] = 1_048_576

GeneratorStatus: TypeAlias = Literal["generated", "reject", "indeterminate"]
ReferenceWord: TypeAlias = Literal["improve", "stabilize"]
ReferenceWitness: TypeAlias = Literal[
    "strict_improvement",
    "stable_continuation",
]
ReferenceProposalName: TypeAlias = Literal["improve", "stabilize"]


class GeneratorReasonCode(StrEnum):
    SCHEMA_MALFORMED = "GENERATOR_SCHEMA_MALFORMED"
    POLICY_MISMATCH = "GENERATOR_POLICY_MISMATCH"
    OBJECTIVE_MISMATCH = "GENERATOR_OBJECTIVE_MISMATCH"
    UNSUPPORTED_SCOPE = "GENERATOR_UNSUPPORTED_SCOPE"
    PREDECESSOR_OUTSIDE_DOMAIN = "GENERATOR_PREDECESSOR_OUTSIDE_DOMAIN"
    BUDGET_EXCEEDED = "GENERATOR_BUDGET_EXCEEDED"
    PROCESS_TIMEOUT = "GENERATOR_PROCESS_TIMEOUT"
    PROCESS_FAILED = "GENERATOR_PROCESS_FAILED"
    OUTPUT_INVALID = "GENERATOR_OUTPUT_INVALID"
    REPLAY_MISMATCH = "GENERATOR_REPLAY_MISMATCH"
    SANDBOX_VIOLATION = "GENERATOR_SANDBOX_VIOLATION"
    PIPELINE_BINDING_MISMATCH = "GENERATOR_PIPELINE_BINDING_MISMATCH"
    LEAN_VERIFIER_FAILED = "GENERATOR_LEAN_VERIFIER_FAILED"
    CHECKER_REJECTED = "GENERATOR_CHECKER_REJECTED"
    INTERNAL_ERROR = "GENERATOR_INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class ReferenceGeneratorPolicyRecord:
    policy_id: str
    grammar_id: str
    supported_scope: Literal["gate_b_classical"]
    max_word_depth: int
    max_proof_length: int
    proposal_limit: int
    open_ended_generation_allowed: bool
    model_invocation_limit: int
    network_request_limit: int
    file_write_limit: int

    schema_id: ClassVar[str] = REFERENCE_GENERATOR_POLICY_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.policy_id, "generator_policy.policy_id")
        require_string(self.grammar_id, "generator_policy.grammar_id")
        if self.supported_scope != "gate_b_classical":
            raise SchemaValidationError(
                "generator_policy.supported_scope",
                "Phase 5A supports only gate_b_classical",
            )
        for field_name, minimum, maximum in (
            ("max_word_depth", 0, 64),
            ("max_proof_length", 0, 64),
            ("proposal_limit", 0, 64),
            ("model_invocation_limit", 0, 0),
            ("network_request_limit", 0, 0),
            ("file_write_limit", 0, 0),
        ):
            require_structural_integer(
                getattr(self, field_name),
                f"generator_policy.{field_name}",
                minimum=minimum,
                maximum=maximum,
            )
        if not isinstance(self.open_ended_generation_allowed, bool):
            raise SchemaValidationError(
                "generator_policy.open_ended_generation_allowed",
                "expected a Boolean",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "generator_policy",
    ) -> ReferenceGeneratorPolicyRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "policy_id",
                "grammar_id",
                "supported_scope",
                "max_word_depth",
                "max_proof_length",
                "proposal_limit",
                "open_ended_generation_allowed",
                "model_invocation_limit",
                "network_request_limit",
                "file_write_limit",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        supported_scope = require_string(
            obj["supported_scope"],
            f"{path}.supported_scope",
        )
        if supported_scope != "gate_b_classical":
            raise SchemaValidationError(
                f"{path}.supported_scope",
                "Phase 5A supports only gate_b_classical",
            )
        open_ended = obj["open_ended_generation_allowed"]
        if not isinstance(open_ended, bool):
            raise SchemaValidationError(
                f"{path}.open_ended_generation_allowed",
                "expected a Boolean",
            )
        return cls(
            policy_id=require_string(obj["policy_id"], f"{path}.policy_id"),
            grammar_id=require_string(obj["grammar_id"], f"{path}.grammar_id"),
            supported_scope=supported_scope,
            max_word_depth=require_structural_integer(
                obj["max_word_depth"],
                f"{path}.max_word_depth",
                minimum=0,
                maximum=64,
            ),
            max_proof_length=require_structural_integer(
                obj["max_proof_length"],
                f"{path}.max_proof_length",
                minimum=0,
                maximum=64,
            ),
            proposal_limit=require_structural_integer(
                obj["proposal_limit"],
                f"{path}.proposal_limit",
                minimum=0,
                maximum=64,
            ),
            open_ended_generation_allowed=open_ended,
            model_invocation_limit=require_structural_integer(
                obj["model_invocation_limit"],
                f"{path}.model_invocation_limit",
                minimum=0,
                maximum=0,
            ),
            network_request_limit=require_structural_integer(
                obj["network_request_limit"],
                f"{path}.network_request_limit",
                minimum=0,
                maximum=0,
            ),
            file_write_limit=require_structural_integer(
                obj["file_write_limit"],
                f"{path}.file_write_limit",
                minimum=0,
                maximum=0,
            ),
        )

    @property
    def policy_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "policy_id": self.policy_id,
            "grammar_id": self.grammar_id,
            "supported_scope": self.supported_scope,
            "max_word_depth": self.max_word_depth,
            "max_proof_length": self.max_proof_length,
            "proposal_limit": self.proposal_limit,
            "open_ended_generation_allowed": self.open_ended_generation_allowed,
            "model_invocation_limit": self.model_invocation_limit,
            "network_request_limit": self.network_request_limit,
            "file_write_limit": self.file_write_limit,
        }


@dataclass(frozen=True, slots=True)
class DeclaredObjectiveRecord:
    task_id: str
    objective_id: str
    scope: Literal["gate_b_classical"]
    goal: Literal["biased_target"]
    trajectory_mode: Literal["strict_then_stable"]

    schema_id: ClassVar[str] = DECLARED_OBJECTIVE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.task_id, "declared_objective.task_id")
        require_string(self.objective_id, "declared_objective.objective_id")
        if self.scope != "gate_b_classical":
            raise SchemaValidationError(
                "declared_objective.scope",
                "Phase 5A supports only gate_b_classical",
            )
        if self.goal != "biased_target":
            raise SchemaValidationError(
                "declared_objective.goal",
                "unsupported reference goal",
            )
        if self.trajectory_mode != "strict_then_stable":
            raise SchemaValidationError(
                "declared_objective.trajectory_mode",
                "unsupported reference trajectory mode",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "declared_objective",
    ) -> DeclaredObjectiveRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "task_id",
                "objective_id",
                "scope",
                "goal",
                "trajectory_mode",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        scope = require_string(obj["scope"], f"{path}.scope")
        goal = require_string(obj["goal"], f"{path}.goal")
        trajectory_mode = require_string(
            obj["trajectory_mode"],
            f"{path}.trajectory_mode",
        )
        if scope != "gate_b_classical":
            raise SchemaValidationError(f"{path}.scope", "unsupported scope")
        if goal != "biased_target":
            raise SchemaValidationError(f"{path}.goal", "unsupported goal")
        if trajectory_mode != "strict_then_stable":
            raise SchemaValidationError(
                f"{path}.trajectory_mode",
                "unsupported trajectory mode",
            )
        return cls(
            task_id=require_string(obj["task_id"], f"{path}.task_id"),
            objective_id=require_string(
                obj["objective_id"],
                f"{path}.objective_id",
            ),
            scope=scope,
            goal=goal,
            trajectory_mode=trajectory_mode,
        )

    @property
    def objective_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "objective_id": self.objective_id,
            "scope": self.scope,
            "goal": self.goal,
            "trajectory_mode": self.trajectory_mode,
        }


@dataclass(frozen=True, slots=True)
class GeneratorResourceBudgetRecord:
    proposal_limit: int
    word_depth_limit: int
    proof_length_limit: int
    resource_units: int
    timeout_seconds: int
    model_invocation_limit: int
    network_request_limit: int
    file_write_limit: int

    schema_id: ClassVar[str] = GENERATOR_RESOURCE_BUDGET_SCHEMA_ID

    def __post_init__(self) -> None:
        for field_name, minimum, maximum in (
            ("proposal_limit", 0, 64),
            ("word_depth_limit", 0, 64),
            ("proof_length_limit", 0, 64),
            ("resource_units", 0, 1_000_000),
            ("timeout_seconds", 1, 300),
            ("model_invocation_limit", 0, 0),
            ("network_request_limit", 0, 0),
            ("file_write_limit", 0, 0),
        ):
            require_structural_integer(
                getattr(self, field_name),
                f"generator_budget.{field_name}",
                minimum=minimum,
                maximum=maximum,
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "generator_budget",
    ) -> GeneratorResourceBudgetRecord:
        fields = {
            "schema_id",
            "proposal_limit",
            "word_depth_limit",
            "proof_length_limit",
            "resource_units",
            "timeout_seconds",
            "model_invocation_limit",
            "network_request_limit",
            "file_write_limit",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        limits = {
            "proposal_limit": (0, 64),
            "word_depth_limit": (0, 64),
            "proof_length_limit": (0, 64),
            "resource_units": (0, 1_000_000),
            "timeout_seconds": (1, 300),
            "model_invocation_limit": (0, 0),
            "network_request_limit": (0, 0),
            "file_write_limit": (0, 0),
        }
        parsed = {
            field_name: require_structural_integer(
                obj[field_name],
                f"{path}.{field_name}",
                minimum=minimum,
                maximum=maximum,
            )
            for field_name, (minimum, maximum) in limits.items()
        }
        return cls(**parsed)

    @property
    def budget_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "proposal_limit": self.proposal_limit,
            "word_depth_limit": self.word_depth_limit,
            "proof_length_limit": self.proof_length_limit,
            "resource_units": self.resource_units,
            "timeout_seconds": self.timeout_seconds,
            "model_invocation_limit": self.model_invocation_limit,
            "network_request_limit": self.network_request_limit,
            "file_write_limit": self.file_write_limit,
        }


@dataclass(frozen=True, slots=True)
class ReferencePredecessorPackageRecord:
    manifest: PackageManifestRecord
    state: RclmStateRecord

    schema_id: ClassVar[str] = REFERENCE_PREDECESSOR_PACKAGE_SCHEMA_ID

    def __post_init__(self) -> None:
        if not isinstance(self.state.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError(
                "predecessor_package.state.core",
                "Phase 5A requires a classical binary predecessor",
            )
        expected_state_hash = canonical_json_hash(self.state.to_json())
        expected_file = file_record_from_bytes(
            "state/predecessor.json",
            "0644",
            canonical_json_bytes(self.state.to_json()),
        )
        expected_tree_hash = semantic_tree_hash((expected_file,))
        if self.manifest.candidate_hash != expected_state_hash:
            raise SchemaValidationError(
                "predecessor_package.manifest.candidate_hash",
                "predecessor state hash does not match the package manifest",
            )
        if self.manifest.semantic_tree_hash != expected_tree_hash:
            raise SchemaValidationError(
                "predecessor_package.manifest.semantic_tree_hash",
                "predecessor semantic tree does not match canonical state bytes",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "predecessor_package",
    ) -> ReferencePredecessorPackageRecord:
        obj = strict_object(value, path, {"schema_id", "manifest", "state"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            manifest=PackageManifestRecord.from_json(
                obj["manifest"],
                f"{path}.manifest",
            ),
            state=RclmStateRecord.from_json(obj["state"], f"{path}.state"),
        )

    @property
    def manifest_hash(self) -> str:
        return self.manifest.content_hash()

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "manifest": self.manifest.to_json(),
            "state": self.state.to_json(),
        }


@dataclass(frozen=True, slots=True)
class ReferenceGeneratorInputRecord:
    predecessor_package: ReferencePredecessorPackageRecord
    policy: ReferenceGeneratorPolicyRecord
    objective: DeclaredObjectiveRecord
    resource_budget: GeneratorResourceBudgetRecord
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = REFERENCE_GENERATOR_INPUT_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "generator_input.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "generator_input",
    ) -> ReferenceGeneratorInputRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "contract_version",
                "predecessor_package",
                "policy",
                "objective",
                "resource_budget",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            predecessor_package=ReferencePredecessorPackageRecord.from_json(
                obj["predecessor_package"],
                f"{path}.predecessor_package",
            ),
            policy=ReferenceGeneratorPolicyRecord.from_json(
                obj["policy"],
                f"{path}.policy",
            ),
            objective=DeclaredObjectiveRecord.from_json(
                obj["objective"],
                f"{path}.objective",
            ),
            resource_budget=GeneratorResourceBudgetRecord.from_json(
                obj["resource_budget"],
                f"{path}.resource_budget",
            ),
            contract_version=require_string(
                obj["contract_version"],
                f"{path}.contract_version",
            ),
        )

    @property
    def input_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "predecessor_package": self.predecessor_package.to_json(),
            "policy": self.policy.to_json(),
            "objective": self.objective.to_json(),
            "resource_budget": self.resource_budget.to_json(),
        }


@dataclass(frozen=True, slots=True)
class UntrustedProposalRecord:
    proposal_id: str
    word: ReferenceWord
    witness: ReferenceWitness
    proposal: ReferenceProposalName
    word_depth: int
    proof_length: int
    resource_units: int
    predecessor_package_id: str
    predecessor_manifest_hash: str
    policy_hash: str
    objective_hash: str
    budget_hash: str
    generator_input_hash: str
    worker_version: str = REFERENCE_GENERATOR_WORKER_VERSION

    schema_id: ClassVar[str] = UNTRUSTED_PROPOSAL_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.proposal_id, "proposal.proposal_id")
        if self.word not in {"improve", "stabilize"}:
            raise SchemaValidationError("proposal.word", "unsupported word")
        expected_witness = (
            "strict_improvement" if self.word == "improve" else "stable_continuation"
        )
        if self.witness != expected_witness:
            raise SchemaValidationError(
                "proposal.witness",
                "word and witness do not match the bounded grammar",
            )
        if self.proposal != self.word:
            raise SchemaValidationError(
                "proposal.proposal",
                "word and proposal do not match the bounded grammar",
            )
        require_structural_integer(
            self.word_depth,
            "proposal.word_depth",
            minimum=1,
            maximum=1,
        )
        require_structural_integer(
            self.proof_length,
            "proposal.proof_length",
            minimum=1,
            maximum=1,
        )
        require_structural_integer(
            self.resource_units,
            "proposal.resource_units",
            minimum=0,
            maximum=1,
        )
        require_string(
            self.predecessor_package_id,
            "proposal.predecessor_package_id",
        )
        for field_name in (
            "predecessor_manifest_hash",
            "policy_hash",
            "objective_hash",
            "budget_hash",
            "generator_input_hash",
        ):
            validate_hash256(getattr(self, field_name), f"proposal.{field_name}")
        if self.worker_version != REFERENCE_GENERATOR_WORKER_VERSION:
            raise SchemaValidationError(
                "proposal.worker_version",
                f"expected {REFERENCE_GENERATOR_WORKER_VERSION}",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "proposal",
    ) -> UntrustedProposalRecord:
        fields = {
            "schema_id",
            "proposal_id",
            "word",
            "witness",
            "proposal",
            "word_depth",
            "proof_length",
            "resource_units",
            "predecessor_package_id",
            "predecessor_manifest_hash",
            "policy_hash",
            "objective_hash",
            "budget_hash",
            "generator_input_hash",
            "worker_version",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        word = require_string(obj["word"], f"{path}.word")
        witness = require_string(obj["witness"], f"{path}.witness")
        proposal = require_string(obj["proposal"], f"{path}.proposal")
        if word not in {"improve", "stabilize"}:
            raise SchemaValidationError(f"{path}.word", "unsupported word")
        if witness not in {"strict_improvement", "stable_continuation"}:
            raise SchemaValidationError(f"{path}.witness", "unsupported witness")
        if proposal not in {"improve", "stabilize"}:
            raise SchemaValidationError(f"{path}.proposal", "unsupported proposal")
        hash_values: dict[str, str] = {}
        for field_name in (
            "predecessor_manifest_hash",
            "policy_hash",
            "objective_hash",
            "budget_hash",
            "generator_input_hash",
        ):
            hash_value = require_string(obj[field_name], f"{path}.{field_name}")
            validate_hash256(hash_value, f"{path}.{field_name}")
            hash_values[field_name] = hash_value
        return cls(
            proposal_id=require_string(obj["proposal_id"], f"{path}.proposal_id"),
            word=word,
            witness=witness,
            proposal=proposal,
            word_depth=require_structural_integer(
                obj["word_depth"],
                f"{path}.word_depth",
                minimum=1,
                maximum=1,
            ),
            proof_length=require_structural_integer(
                obj["proof_length"],
                f"{path}.proof_length",
                minimum=1,
                maximum=1,
            ),
            resource_units=require_structural_integer(
                obj["resource_units"],
                f"{path}.resource_units",
                minimum=0,
                maximum=1,
            ),
            predecessor_package_id=require_string(
                obj["predecessor_package_id"],
                f"{path}.predecessor_package_id",
            ),
            predecessor_manifest_hash=hash_values["predecessor_manifest_hash"],
            policy_hash=hash_values["policy_hash"],
            objective_hash=hash_values["objective_hash"],
            budget_hash=hash_values["budget_hash"],
            generator_input_hash=hash_values["generator_input_hash"],
            worker_version=require_string(
                obj["worker_version"],
                f"{path}.worker_version",
            ),
        )

    @property
    def proposal_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "proposal_id": self.proposal_id,
            "word": self.word,
            "witness": self.witness,
            "proposal": self.proposal,
            "word_depth": self.word_depth,
            "proof_length": self.proof_length,
            "resource_units": self.resource_units,
            "predecessor_package_id": self.predecessor_package_id,
            "predecessor_manifest_hash": self.predecessor_manifest_hash,
            "policy_hash": self.policy_hash,
            "objective_hash": self.objective_hash,
            "budget_hash": self.budget_hash,
            "generator_input_hash": self.generator_input_hash,
            "worker_version": self.worker_version,
        }


@dataclass(frozen=True, slots=True)
class WorkerSandboxRecord:
    audit_policy_version: str
    file_write_probe: Literal["denied"]
    network_probe: Literal["denied"]
    subprocess_probe: Literal["denied"]
    checker_input_present: bool
    trust_anchor_present: bool
    previous_manifest_history_present: bool
    promotion_ledger_present: bool
    reference_answer_present: bool

    schema_id: ClassVar[str] = WORKER_SANDBOX_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.audit_policy_version, "worker_sandbox.audit_policy_version")
        for field_name in (
            "checker_input_present",
            "trust_anchor_present",
            "previous_manifest_history_present",
            "promotion_ledger_present",
            "reference_answer_present",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise SchemaValidationError(
                    f"worker_sandbox.{field_name}",
                    "expected a Boolean",
                )
        if any(
            (
                self.checker_input_present,
                self.trust_anchor_present,
                self.previous_manifest_history_present,
                self.promotion_ledger_present,
                self.reference_answer_present,
            )
        ):
            raise SchemaValidationError(
                "worker_sandbox",
                "forbidden control-plane input was exposed to the generator",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "worker_sandbox",
    ) -> WorkerSandboxRecord:
        fields = {
            "schema_id",
            "audit_policy_version",
            "file_write_probe",
            "network_probe",
            "subprocess_probe",
            "checker_input_present",
            "trust_anchor_present",
            "previous_manifest_history_present",
            "promotion_ledger_present",
            "reference_answer_present",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        probes: dict[str, str] = {}
        for field_name in (
            "file_write_probe",
            "network_probe",
            "subprocess_probe",
        ):
            text = require_string(obj[field_name], f"{path}.{field_name}")
            if text != "denied":
                raise SchemaValidationError(
                    f"{path}.{field_name}",
                    "sandbox probe was not denied",
                )
            probes[field_name] = text
        booleans: dict[str, bool] = {}
        for field_name in (
            "checker_input_present",
            "trust_anchor_present",
            "previous_manifest_history_present",
            "promotion_ledger_present",
            "reference_answer_present",
        ):
            raw = obj[field_name]
            if not isinstance(raw, bool):
                raise SchemaValidationError(
                    f"{path}.{field_name}",
                    "expected a Boolean",
                )
            booleans[field_name] = raw
        return cls(
            audit_policy_version=require_string(
                obj["audit_policy_version"],
                f"{path}.audit_policy_version",
            ),
            file_write_probe=probes["file_write_probe"],
            network_probe=probes["network_probe"],
            subprocess_probe=probes["subprocess_probe"],
            **booleans,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "audit_policy_version": self.audit_policy_version,
            "file_write_probe": self.file_write_probe,
            "network_probe": self.network_probe,
            "subprocess_probe": self.subprocess_probe,
            "checker_input_present": self.checker_input_present,
            "trust_anchor_present": self.trust_anchor_present,
            "previous_manifest_history_present": self.previous_manifest_history_present,
            "promotion_ledger_present": self.promotion_ledger_present,
            "reference_answer_present": self.reference_answer_present,
        }


@dataclass(frozen=True, slots=True)
class ReferenceWorkerResponse:
    status: GeneratorStatus
    reason_codes: Sequence[GeneratorReasonCode]
    proposal: UntrustedProposalRecord | None
    sandbox: WorkerSandboxRecord
    input_hash: str
    worker_version: str = REFERENCE_GENERATOR_WORKER_VERSION

    schema_id: ClassVar[str] = WORKER_RESPONSE_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.status not in {"generated", "reject", "indeterminate"}:
            raise SchemaValidationError("worker_response.status", "unsupported status")
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "worker_response.reason_codes",
                "reason codes must be unique",
            )
        if self.status == "generated":
            if self.reason_codes or self.proposal is None:
                raise SchemaValidationError(
                    "worker_response",
                    "generated response requires a proposal and no reason codes",
                )
        else:
            if not self.reason_codes or self.proposal is not None:
                raise SchemaValidationError(
                    "worker_response",
                    "non-generated response requires reasons and no proposal",
                )
        validate_hash256(self.input_hash, "worker_response.input_hash")
        if self.worker_version != REFERENCE_GENERATOR_WORKER_VERSION:
            raise SchemaValidationError(
                "worker_response.worker_version",
                f"expected {REFERENCE_GENERATOR_WORKER_VERSION}",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "worker_response",
    ) -> ReferenceWorkerResponse:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "status",
                "reason_codes",
                "proposal",
                "sandbox",
                "input_hash",
                "worker_version",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        status = require_string(obj["status"], f"{path}.status")
        if status not in {"generated", "reject", "indeterminate"}:
            raise SchemaValidationError(f"{path}.status", "unsupported status")
        reasons_raw = obj["reason_codes"]
        if not isinstance(reasons_raw, list):
            raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
        reasons: list[GeneratorReasonCode] = []
        for index, item in enumerate(reasons_raw):
            text = require_string(item, f"{path}.reason_codes[{index}]")
            try:
                reasons.append(GeneratorReasonCode(text))
            except ValueError as exc:
                raise SchemaValidationError(
                    f"{path}.reason_codes[{index}]",
                    f"unknown generator reason code: {text}",
                ) from exc
        proposal_raw = obj["proposal"]
        proposal = (
            None
            if proposal_raw is None
            else UntrustedProposalRecord.from_json(proposal_raw, f"{path}.proposal")
        )
        input_hash = require_string(obj["input_hash"], f"{path}.input_hash")
        validate_hash256(input_hash, f"{path}.input_hash")
        return cls(
            status=status,
            reason_codes=tuple(reasons),
            proposal=proposal,
            sandbox=WorkerSandboxRecord.from_json(
                obj["sandbox"],
                f"{path}.sandbox",
            ),
            input_hash=input_hash,
            worker_version=require_string(
                obj["worker_version"],
                f"{path}.worker_version",
            ),
        )

    @property
    def response_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "status": self.status,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "proposal": None if self.proposal is None else self.proposal.to_json(),
            "sandbox": self.sandbox.to_json(),
            "input_hash": self.input_hash,
            "worker_version": self.worker_version,
        }


@dataclass(frozen=True, slots=True)
class GeneratorProcessObservation:
    status: GeneratorStatus
    reason_codes: Sequence[GeneratorReasonCode]
    exit_code: int
    timed_out: bool
    input_hash: str
    stdout_hash: str
    stderr_hash: str
    command_hash: str
    environment_key_hash: str
    response: ReferenceWorkerResponse | None

    schema_id: ClassVar[str] = PROCESS_OBSERVATION_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.status not in {"generated", "reject", "indeterminate"}:
            raise SchemaValidationError("process_observation.status", "unsupported status")
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "process_observation.reason_codes",
                "reason codes must be unique",
            )
        require_structural_integer(
            self.exit_code,
            "process_observation.exit_code",
            minimum=0,
            maximum=255,
        )
        if not isinstance(self.timed_out, bool):
            raise SchemaValidationError(
                "process_observation.timed_out",
                "expected a Boolean",
            )
        for field_name in (
            "input_hash",
            "stdout_hash",
            "stderr_hash",
            "command_hash",
            "environment_key_hash",
        ):
            validate_hash256(getattr(self, field_name), f"process_observation.{field_name}")
        if self.status == "generated" and self.response is None:
            raise SchemaValidationError(
                "process_observation.response",
                "generated process observation requires a worker response",
            )

    @property
    def observation_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "status": self.status,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "input_hash": self.input_hash,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "command_hash": self.command_hash,
            "environment_key_hash": self.environment_key_hash,
            "response": None if self.response is None else self.response.to_json(),
        }


@dataclass(frozen=True, slots=True)
class GeneratorReplayReport:
    status: GeneratorStatus
    reason_codes: Sequence[GeneratorReasonCode]
    first: GeneratorProcessObservation
    second: GeneratorProcessObservation
    proposal: UntrustedProposalRecord | None

    schema_id: ClassVar[str] = GENERATOR_REPLAY_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.status not in {"generated", "reject", "indeterminate"}:
            raise SchemaValidationError("generator_replay.status", "unsupported status")
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "generator_replay.reason_codes",
                "reason codes must be unique",
            )
        if self.status == "generated":
            if self.reason_codes or self.proposal is None or not self.deterministic:
                raise SchemaValidationError(
                    "generator_replay",
                    "generated replay requires identical successful observations",
                )
        elif not self.reason_codes or self.proposal is not None:
            raise SchemaValidationError(
                "generator_replay",
                "non-generated replay requires reasons and no proposal",
            )

    @property
    def deterministic(self) -> bool:
        return (
            self.first.stdout_hash == self.second.stdout_hash
            and self.first.status == self.second.status
            and self.first.reason_codes == self.second.reason_codes
            and (
                (self.first.response is None and self.second.response is None)
                or (
                    self.first.response is not None
                    and self.second.response is not None
                    and self.first.response.response_hash
                    == self.second.response.response_hash
                )
            )
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "status": self.status,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "deterministic": self.deterministic,
            "first": self.first.to_json(),
            "second": self.second.to_json(),
            "proposal": None if self.proposal is None else self.proposal.to_json(),
        }


def parse_hash_mapping(value: object, path: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    parsed: dict[str, str] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise SchemaValidationError(path, "hash-map keys must be strings")
        hash_value = require_string(raw, f"{path}.{key}")
        validate_hash256(hash_value, f"{path}.{key}")
        parsed[key] = hash_value
    return parsed
