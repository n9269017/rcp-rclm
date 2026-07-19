from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, strict_object

from rcp_rclm_runtime_v3.contract.common import (
    CERTIFICATE_SCHEMA_ID,
    CONTRACT_VERSION,
    HELDOUT_POLICY_SCHEMA_ID,
    SELECTED_TASK_CLASS,
    normalize_sorted_unique_strings,
    require_boolean,
    require_hash,
    require_schema,
    require_string_array,
)


@dataclass(frozen=True, slots=True)
class HeldoutAccessPolicy:
    policy_id: str
    heldout_task_manifest_hash: str
    reference_answer_store_hash: str
    evaluator_policy_hash: str
    generator_task_ids_visible_before_candidate_freeze: bool = False
    generator_prompts_visible_before_candidate_freeze: bool = False
    generator_reference_answers_visible: bool = False
    training_backend_heldout_prompts_visible: bool = False
    training_backend_reference_answers_visible: bool = False
    evaluator_prompts_visible_after_candidate_freeze: bool = True
    evaluator_reference_answers_visible: bool = True
    selected_task_class: str = SELECTED_TASK_CLASS
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = HELDOUT_POLICY_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.policy_id, "phase9.heldout_policy.policy_id")
        for name in (
            "heldout_task_manifest_hash",
            "reference_answer_store_hash",
            "evaluator_policy_hash",
        ):
            require_hash(getattr(self, name), f"phase9.heldout_policy.{name}")
        expected = {
            "generator_task_ids_visible_before_candidate_freeze": False,
            "generator_prompts_visible_before_candidate_freeze": False,
            "generator_reference_answers_visible": False,
            "training_backend_heldout_prompts_visible": False,
            "training_backend_reference_answers_visible": False,
            "evaluator_prompts_visible_after_candidate_freeze": True,
            "evaluator_reference_answers_visible": True,
        }
        for name, required in expected.items():
            if getattr(self, name) is not required:
                raise SchemaValidationError(
                    f"phase9.heldout_policy.{name}",
                    f"expected frozen value {required}",
                )
        if self.selected_task_class != SELECTED_TASK_CLASS:
            raise SchemaValidationError(
                "phase9.heldout_policy.selected_task_class",
                f"expected {SELECTED_TASK_CLASS}",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase9.heldout_policy.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def policy_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "selected_task_class": self.selected_task_class,
            "policy_id": self.policy_id,
            "heldout_task_manifest_hash": self.heldout_task_manifest_hash,
            "reference_answer_store_hash": self.reference_answer_store_hash,
            "evaluator_policy_hash": self.evaluator_policy_hash,
            "generator_task_ids_visible_before_candidate_freeze": self.generator_task_ids_visible_before_candidate_freeze,
            "generator_prompts_visible_before_candidate_freeze": self.generator_prompts_visible_before_candidate_freeze,
            "generator_reference_answers_visible": self.generator_reference_answers_visible,
            "training_backend_heldout_prompts_visible": self.training_backend_heldout_prompts_visible,
            "training_backend_reference_answers_visible": self.training_backend_reference_answers_visible,
            "evaluator_prompts_visible_after_candidate_freeze": self.evaluator_prompts_visible_after_candidate_freeze,
            "evaluator_reference_answers_visible": self.evaluator_reference_answers_visible,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["policy_hash"] = self.policy_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> HeldoutAccessPolicy:
        fields = {
            "schema_id",
            "contract_version",
            "selected_task_class",
            "policy_id",
            "heldout_task_manifest_hash",
            "reference_answer_store_hash",
            "evaluator_policy_hash",
            "generator_task_ids_visible_before_candidate_freeze",
            "generator_prompts_visible_before_candidate_freeze",
            "generator_reference_answers_visible",
            "training_backend_heldout_prompts_visible",
            "training_backend_reference_answers_visible",
            "evaluator_prompts_visible_after_candidate_freeze",
            "evaluator_reference_answers_visible",
            "policy_hash",
        }
        obj = strict_object(value, "phase9.heldout_policy", fields)
        require_schema(obj["schema_id"], cls.schema_id, "phase9.heldout_policy.schema_id")
        result = cls(
            policy_id=require_string(obj["policy_id"], "phase9.heldout_policy.policy_id"),
            heldout_task_manifest_hash=require_hash(
                obj["heldout_task_manifest_hash"],
                "phase9.heldout_policy.heldout_task_manifest_hash",
            ),
            reference_answer_store_hash=require_hash(
                obj["reference_answer_store_hash"],
                "phase9.heldout_policy.reference_answer_store_hash",
            ),
            evaluator_policy_hash=require_hash(
                obj["evaluator_policy_hash"],
                "phase9.heldout_policy.evaluator_policy_hash",
            ),
            generator_task_ids_visible_before_candidate_freeze=require_boolean(
                obj["generator_task_ids_visible_before_candidate_freeze"],
                "phase9.heldout_policy.generator_task_ids_visible_before_candidate_freeze",
            ),
            generator_prompts_visible_before_candidate_freeze=require_boolean(
                obj["generator_prompts_visible_before_candidate_freeze"],
                "phase9.heldout_policy.generator_prompts_visible_before_candidate_freeze",
            ),
            generator_reference_answers_visible=require_boolean(
                obj["generator_reference_answers_visible"],
                "phase9.heldout_policy.generator_reference_answers_visible",
            ),
            training_backend_heldout_prompts_visible=require_boolean(
                obj["training_backend_heldout_prompts_visible"],
                "phase9.heldout_policy.training_backend_heldout_prompts_visible",
            ),
            training_backend_reference_answers_visible=require_boolean(
                obj["training_backend_reference_answers_visible"],
                "phase9.heldout_policy.training_backend_reference_answers_visible",
            ),
            evaluator_prompts_visible_after_candidate_freeze=require_boolean(
                obj["evaluator_prompts_visible_after_candidate_freeze"],
                "phase9.heldout_policy.evaluator_prompts_visible_after_candidate_freeze",
            ),
            evaluator_reference_answers_visible=require_boolean(
                obj["evaluator_reference_answers_visible"],
                "phase9.heldout_policy.evaluator_reference_answers_visible",
            ),
            selected_task_class=require_string(
                obj["selected_task_class"],
                "phase9.heldout_policy.selected_task_class",
            ),
            contract_version=require_string(
                obj["contract_version"],
                "phase9.heldout_policy.contract_version",
            ),
        )
        if require_hash(obj["policy_hash"], "phase9.heldout_policy.policy_hash") != result.policy_hash:
            raise SchemaValidationError(
                "phase9.heldout_policy.policy_hash",
                "content hash mismatch",
            )
        return result


@dataclass(frozen=True, slots=True)
class LearnedCertificatePacket:
    transition_id: str
    predecessor_state_hash: str
    candidate_state_hash: str
    update_hash: str
    base_certificate_hash: str
    capability_frontier_before_hash: str
    capability_frontier_after_hash: str
    protected_task_ids: Sequence[str]
    new_task_ids: Sequence[str]
    task_frontier_retention_evidence_hash: str
    new_task_capability_evidence_hash: str
    model_output_density_evidence_hash: str
    entropy_kl_qre_evidence_hash: str
    goal_drift_evidence_hash: str
    training_data_provenance_hash: str
    heldout_isolation_evidence_hash: str
    architecture_compatibility_hash: str
    self_hosting_evidence_hash: str
    resource_evidence_hash: str
    rollback_evidence_hash: str
    heldout_access_policy_hash: str
    active_generator_hash: str
    active_planner_hash: str
    proposal_protocol_hash: str
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = CERTIFICATE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase9.certificate.transition_id")
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase9.certificate.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        for name in self.hash_field_names():
            require_hash(getattr(self, name), f"phase9.certificate.{name}")
        object.__setattr__(
            self,
            "protected_task_ids",
            normalize_sorted_unique_strings(
                tuple(self.protected_task_ids),
                "phase9.certificate.protected_task_ids",
            ),
        )
        object.__setattr__(
            self,
            "new_task_ids",
            normalize_sorted_unique_strings(
                tuple(self.new_task_ids),
                "phase9.certificate.new_task_ids",
            ),
        )
        if not self.new_task_ids:
            raise SchemaValidationError(
                "phase9.certificate.new_task_ids",
                "strict expansion requires at least one newly certified task",
            )

    @staticmethod
    def hash_field_names() -> Sequence[str]:
        return (
            "predecessor_state_hash",
            "candidate_state_hash",
            "update_hash",
            "base_certificate_hash",
            "capability_frontier_before_hash",
            "capability_frontier_after_hash",
            "task_frontier_retention_evidence_hash",
            "new_task_capability_evidence_hash",
            "model_output_density_evidence_hash",
            "entropy_kl_qre_evidence_hash",
            "goal_drift_evidence_hash",
            "training_data_provenance_hash",
            "heldout_isolation_evidence_hash",
            "architecture_compatibility_hash",
            "self_hosting_evidence_hash",
            "resource_evidence_hash",
            "rollback_evidence_hash",
            "heldout_access_policy_hash",
            "active_generator_hash",
            "active_planner_hash",
            "proposal_protocol_hash",
        )

    @property
    def certificate_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "protected_task_ids": list(self.protected_task_ids),
            "new_task_ids": list(self.new_task_ids),
        }
        for name in self.hash_field_names():
            value[name] = getattr(self, name)
        return value

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["certificate_hash"] = self.certificate_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> LearnedCertificatePacket:
        fields = {
            "schema_id",
            "contract_version",
            "transition_id",
            "protected_task_ids",
            "new_task_ids",
            "certificate_hash",
            *cls.hash_field_names(),
        }
        obj = strict_object(value, "phase9.certificate", fields)
        require_schema(obj["schema_id"], cls.schema_id, "phase9.certificate.schema_id")
        kwargs: dict[str, object] = {
            "transition_id": require_string(
                obj["transition_id"],
                "phase9.certificate.transition_id",
            ),
            "protected_task_ids": require_string_array(
                obj["protected_task_ids"],
                "phase9.certificate.protected_task_ids",
            ),
            "new_task_ids": require_string_array(
                obj["new_task_ids"],
                "phase9.certificate.new_task_ids",
            ),
            "contract_version": require_string(
                obj["contract_version"],
                "phase9.certificate.contract_version",
            ),
        }
        for name in cls.hash_field_names():
            kwargs[name] = require_hash(obj[name], f"phase9.certificate.{name}")
        result = cls(**kwargs)
        if require_hash(
            obj["certificate_hash"],
            "phase9.certificate.certificate_hash",
        ) != result.certificate_hash:
            raise SchemaValidationError(
                "phase9.certificate.certificate_hash",
                "content hash mismatch",
            )
        return result


__all__ = ["HeldoutAccessPolicy", "LearnedCertificatePacket"]
