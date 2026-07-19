from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, require_structural_integer, strict_object

from rcp_rclm_runtime_v3.contract.common import (
    CONTRACT_VERSION,
    MAX_PARAMETER_COUNT,
    MODEL_SCHEMA_ID,
    POLICY_SCHEMA_ID,
    SELECTED_MODEL_FAMILY,
    SELECTED_TASK_CLASS,
    SELF_HOSTING_SCHEMA_ID,
    STATE_SCHEMA_ID,
    require_hash,
    require_optional_string,
    require_schema,
)
from rcp_rclm_runtime_v3.contract.tasks import CapabilityFrontier, TaskLedger


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    model_family: str
    architecture_hash: str
    weights_tree_hash: str
    adapter_manifest_hash: str
    tensor_manifest_hash: str
    tokenizer_hash: str
    vocabulary_hash: str
    parameter_count: int

    schema_id: ClassVar[str] = MODEL_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.model_family != SELECTED_MODEL_FAMILY:
            raise SchemaValidationError(
                "phase9.model.model_family",
                f"expected selected family {SELECTED_MODEL_FAMILY}",
            )
        for name in (
            "architecture_hash",
            "weights_tree_hash",
            "adapter_manifest_hash",
            "tensor_manifest_hash",
            "tokenizer_hash",
            "vocabulary_hash",
        ):
            require_hash(getattr(self, name), f"phase9.model.{name}")
        require_structural_integer(
            self.parameter_count,
            "phase9.model.parameter_count",
            minimum=1,
            maximum=MAX_PARAMETER_COUNT,
        )

    @property
    def model_identity_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object) -> ModelIdentity:
        obj = strict_object(
            value,
            "phase9.model",
            {
                "schema_id",
                "model_family",
                "architecture_hash",
                "weights_tree_hash",
                "adapter_manifest_hash",
                "tensor_manifest_hash",
                "tokenizer_hash",
                "vocabulary_hash",
                "parameter_count",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.model.schema_id")
        return cls(
            model_family=require_string(obj["model_family"], "phase9.model.model_family"),
            architecture_hash=require_hash(
                obj["architecture_hash"], "phase9.model.architecture_hash"
            ),
            weights_tree_hash=require_hash(
                obj["weights_tree_hash"], "phase9.model.weights_tree_hash"
            ),
            adapter_manifest_hash=require_hash(
                obj["adapter_manifest_hash"], "phase9.model.adapter_manifest_hash"
            ),
            tensor_manifest_hash=require_hash(
                obj["tensor_manifest_hash"], "phase9.model.tensor_manifest_hash"
            ),
            tokenizer_hash=require_hash(obj["tokenizer_hash"], "phase9.model.tokenizer_hash"),
            vocabulary_hash=require_hash(
                obj["vocabulary_hash"], "phase9.model.vocabulary_hash"
            ),
            parameter_count=require_structural_integer(
                obj["parameter_count"],
                "phase9.model.parameter_count",
                minimum=1,
                maximum=MAX_PARAMETER_COUNT,
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "model_family": self.model_family,
            "architecture_hash": self.architecture_hash,
            "weights_tree_hash": self.weights_tree_hash,
            "adapter_manifest_hash": self.adapter_manifest_hash,
            "tensor_manifest_hash": self.tensor_manifest_hash,
            "tokenizer_hash": self.tokenizer_hash,
            "vocabulary_hash": self.vocabulary_hash,
            "parameter_count": self.parameter_count,
        }


@dataclass(frozen=True, slots=True)
class PolicyIdentity:
    training_policy_hash: str
    optimizer_policy_hash: str
    data_curriculum_hash: str
    generator_policy_hash: str
    planner_policy_hash: str
    retrieval_policy_hash: str
    memory_state_hash: str
    tool_policy_hash: str
    verification_policy_hash: str
    resource_policy_hash: str
    self_model_hash: str

    schema_id: ClassVar[str] = POLICY_SCHEMA_ID

    def __post_init__(self) -> None:
        for name in (
            "training_policy_hash",
            "optimizer_policy_hash",
            "data_curriculum_hash",
            "generator_policy_hash",
            "planner_policy_hash",
            "retrieval_policy_hash",
            "memory_state_hash",
            "tool_policy_hash",
            "verification_policy_hash",
            "resource_policy_hash",
            "self_model_hash",
        ):
            require_hash(getattr(self, name), f"phase9.policies.{name}")

    @classmethod
    def from_json(cls, value: object) -> PolicyIdentity:
        fields = {
            "schema_id",
            "training_policy_hash",
            "optimizer_policy_hash",
            "data_curriculum_hash",
            "generator_policy_hash",
            "planner_policy_hash",
            "retrieval_policy_hash",
            "memory_state_hash",
            "tool_policy_hash",
            "verification_policy_hash",
            "resource_policy_hash",
            "self_model_hash",
        }
        obj = strict_object(value, "phase9.policies", fields)
        require_schema(obj["schema_id"], cls.schema_id, "phase9.policies.schema_id")
        kwargs = {
            name: require_hash(obj[name], f"phase9.policies.{name}")
            for name in fields
            if name != "schema_id"
        }
        return cls(**kwargs)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "training_policy_hash": self.training_policy_hash,
            "optimizer_policy_hash": self.optimizer_policy_hash,
            "data_curriculum_hash": self.data_curriculum_hash,
            "generator_policy_hash": self.generator_policy_hash,
            "planner_policy_hash": self.planner_policy_hash,
            "retrieval_policy_hash": self.retrieval_policy_hash,
            "memory_state_hash": self.memory_state_hash,
            "tool_policy_hash": self.tool_policy_hash,
            "verification_policy_hash": self.verification_policy_hash,
            "resource_policy_hash": self.resource_policy_hash,
            "self_model_hash": self.self_model_hash,
        }


@dataclass(frozen=True, slots=True)
class SelfHostingBinding:
    generator_component_hash: str
    planner_component_hash: str
    proposal_protocol_hash: str
    self_hosting_contract_hash: str

    schema_id: ClassVar[str] = SELF_HOSTING_SCHEMA_ID

    def __post_init__(self) -> None:
        for name in (
            "generator_component_hash",
            "planner_component_hash",
            "proposal_protocol_hash",
            "self_hosting_contract_hash",
        ):
            require_hash(getattr(self, name), f"phase9.self_hosting.{name}")

    @property
    def binding_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object) -> SelfHostingBinding:
        obj = strict_object(
            value,
            "phase9.self_hosting",
            {
                "schema_id",
                "generator_component_hash",
                "planner_component_hash",
                "proposal_protocol_hash",
                "self_hosting_contract_hash",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.self_hosting.schema_id")
        return cls(
            generator_component_hash=require_hash(
                obj["generator_component_hash"],
                "phase9.self_hosting.generator_component_hash",
            ),
            planner_component_hash=require_hash(
                obj["planner_component_hash"],
                "phase9.self_hosting.planner_component_hash",
            ),
            proposal_protocol_hash=require_hash(
                obj["proposal_protocol_hash"],
                "phase9.self_hosting.proposal_protocol_hash",
            ),
            self_hosting_contract_hash=require_hash(
                obj["self_hosting_contract_hash"],
                "phase9.self_hosting.self_hosting_contract_hash",
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "generator_component_hash": self.generator_component_hash,
            "planner_component_hash": self.planner_component_hash,
            "proposal_protocol_hash": self.proposal_protocol_hash,
            "self_hosting_contract_hash": self.self_hosting_contract_hash,
        }


@dataclass(frozen=True, slots=True)
class LearnedRCLMState:
    package_id: str
    parent_package_id: str | None
    base_state_hash: str
    model: ModelIdentity
    policies: PolicyIdentity
    self_hosting: SelfHostingBinding
    task_ledger: TaskLedger
    capability_frontier: CapabilityFrontier
    contract_version: str = CONTRACT_VERSION
    selected_task_class: str = SELECTED_TASK_CLASS

    schema_id: ClassVar[str] = STATE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.package_id, "phase9.state.package_id")
        require_optional_string(self.parent_package_id, "phase9.state.parent_package_id")
        require_hash(self.base_state_hash, "phase9.state.base_state_hash")
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase9.state.contract_version", f"expected {CONTRACT_VERSION}"
            )
        if self.selected_task_class != SELECTED_TASK_CLASS:
            raise SchemaValidationError(
                "phase9.state.selected_task_class", f"expected {SELECTED_TASK_CLASS}"
            )
        if self.policies.generator_policy_hash != self.self_hosting.generator_component_hash:
            raise SchemaValidationError(
                "phase9.state.self_hosting.generator_component_hash",
                "generator component hash must equal the generator policy hash",
            )
        if self.policies.planner_policy_hash != self.self_hosting.planner_component_hash:
            raise SchemaValidationError(
                "phase9.state.self_hosting.planner_component_hash",
                "planner component hash must equal the planner policy hash",
            )
        tasks = self.task_ledger.task_by_id
        certifications = self.task_ledger.certification_by_task_id
        for task_id in self.capability_frontier.task_ids:
            if task_id not in tasks:
                raise SchemaValidationError(
                    "phase9.state.capability_frontier", f"unknown frontier task {task_id}"
                )
            if task_id not in certifications:
                raise SchemaValidationError(
                    "phase9.state.capability_frontier",
                    f"frontier task lacks independent certification: {task_id}",
                )
            if certifications[task_id].model_identity_hash != self.model.model_identity_hash:
                raise SchemaValidationError(
                    "phase9.state.task_ledger",
                    f"certification for {task_id} is not bound to the current model",
                )

    @property
    def state_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def component_hash(self, target: str) -> str:
        mapping = {
            "model_weights": canonical_json_hash(
                {
                    "weights_tree_hash": self.model.weights_tree_hash,
                    "tensor_manifest_hash": self.model.tensor_manifest_hash,
                }
            ),
            "adapter_manifest": self.model.adapter_manifest_hash,
            "optimizer_policy": self.policies.optimizer_policy_hash,
            "training_policy": self.policies.training_policy_hash,
            "data_curriculum": self.policies.data_curriculum_hash,
            "retrieval_policy": self.policies.retrieval_policy_hash,
            "memory_state": self.policies.memory_state_hash,
            "planner_policy": self.policies.planner_policy_hash,
            "generator_policy": self.policies.generator_policy_hash,
            "model_architecture": canonical_json_hash(
                {
                    "model_family": self.model.model_family,
                    "architecture_hash": self.model.architecture_hash,
                    "parameter_count": self.model.parameter_count,
                }
            ),
            "tokenizer": canonical_json_hash(
                {
                    "tokenizer_hash": self.model.tokenizer_hash,
                    "vocabulary_hash": self.model.vocabulary_hash,
                }
            ),
            "tool_policy": self.policies.tool_policy_hash,
            "verification_policy": self.policies.verification_policy_hash,
            "resource_policy": self.policies.resource_policy_hash,
            "self_model": self.policies.self_model_hash,
        }
        if target not in mapping:
            raise SchemaValidationError("phase9.state.component", f"unsupported target {target}")
        return mapping[target]

    @classmethod
    def from_json(cls, value: object) -> LearnedRCLMState:
        obj = strict_object(
            value,
            "phase9.state",
            {
                "schema_id",
                "contract_version",
                "selected_task_class",
                "package_id",
                "parent_package_id",
                "base_state_hash",
                "model",
                "policies",
                "self_hosting",
                "task_ledger",
                "capability_frontier",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.state.schema_id")
        return cls(
            package_id=require_string(obj["package_id"], "phase9.state.package_id"),
            parent_package_id=require_optional_string(
                obj["parent_package_id"], "phase9.state.parent_package_id"
            ),
            base_state_hash=require_hash(
                obj["base_state_hash"], "phase9.state.base_state_hash"
            ),
            model=ModelIdentity.from_json(obj["model"]),
            policies=PolicyIdentity.from_json(obj["policies"]),
            self_hosting=SelfHostingBinding.from_json(obj["self_hosting"]),
            task_ledger=TaskLedger.from_json(obj["task_ledger"]),
            capability_frontier=CapabilityFrontier.from_json(obj["capability_frontier"]),
            contract_version=require_string(
                obj["contract_version"], "phase9.state.contract_version"
            ),
            selected_task_class=require_string(
                obj["selected_task_class"], "phase9.state.selected_task_class"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "selected_task_class": self.selected_task_class,
            "package_id": self.package_id,
            "parent_package_id": self.parent_package_id,
            "base_state_hash": self.base_state_hash,
            "model": self.model.to_json(),
            "policies": self.policies.to_json(),
            "self_hosting": self.self_hosting.to_json(),
            "task_ledger": self.task_ledger.to_json(),
            "capability_frontier": self.capability_frontier.to_json(),
        }


__all__ = ["LearnedRCLMState", "ModelIdentity", "PolicyIdentity", "SelfHostingBinding"]
