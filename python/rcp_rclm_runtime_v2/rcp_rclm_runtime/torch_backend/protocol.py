from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    FrozenJsonObject,
    freeze_json,
    require_string,
    require_structural_integer,
    strict_object,
    thaw_json,
)

REQUEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_backend_request.v1"
PROPOSAL_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_proposal.v1"
OUTPUT_MANIFEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_output_manifest.v1"
BACKEND_ID: Final[str] = "rcp-rclm-pytorch-cpu-one-step-linear-v1"
HOST_SELECTION_POLICY_ID: Final[str] = "rcp-rclm-pytorch-pilot-host-selector-v1"
PILOT_PROCESS_COMMAND_TEMPLATE: Final[Sequence[str]] = (
    "python",
    "-I",
    "-B",
    "rcp_rclm_runtime/torch_backend/proposal_backend.py",
    "propose",
    "--request",
    "<canonical-request>",
    "--predecessor-root",
    "<immutable-predecessor-payload>",
    "--output-root",
    "<fresh-proposal-output>",
)

EXPECTED_MODEL_PATHS: Final[Sequence[str]] = (
    "model/architecture.json",
    "model/evaluation_request.json",
    "model/optimizer_manifest.json",
    "model/resource_usage.json",
    "model/rng_manifest.json",
    "model/rollback_binding.json",
    "model/training_command.json",
    "model/training_data_manifest.json",
    "model/weights/linear.bias.bin",
    "model/weights/linear.weight.bin",
    "model/weights_manifest.json",
)


def _require_schema(value: object, expected: str, path: str) -> None:
    if value != expected:
        raise SchemaValidationError(path, f"expected {expected}")


@dataclass(frozen=True, slots=True)
class PilotPolicyBinding:
    seed: int = 1729
    thread_count: int = 1
    optimizer_steps: int = 1
    learning_rate_numerator: int = 1
    learning_rate_denominator: int = 4
    quantization_scale: int = 1_000_000
    time_budget_millis: int = 60_000
    max_output_bytes: int = 1_048_576
    max_tensor_bytes: int = 65_536
    require_cpu: bool = True
    require_deterministic_algorithms: bool = True
    torch_version: str = "2.10.0"

    schema_id: ClassVar[str] = "runtime.pytorch_pilot_policy.v1"

    def __post_init__(self) -> None:
        expected = {
            "seed": 1729,
            "thread_count": 1,
            "optimizer_steps": 1,
            "learning_rate_numerator": 1,
            "learning_rate_denominator": 4,
            "quantization_scale": 1_000_000,
            "require_cpu": True,
            "require_deterministic_algorithms": True,
            "torch_version": "2.10.0",
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise SchemaValidationError(
                    f"pytorch_pilot.policy.{name}",
                    f"expected frozen value {value}",
                )
        if self.time_budget_millis < 1 or self.time_budget_millis > 300_000:
            raise SchemaValidationError(
                "pytorch_pilot.policy.time_budget_millis",
                "time budget must be between 1 and 300000 milliseconds",
            )
        for name in ("max_output_bytes", "max_tensor_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise SchemaValidationError(
                    f"pytorch_pilot.policy.{name}",
                    "expected a positive integer",
                )

    @classmethod
    def from_json(cls, value: object) -> "PilotPolicyBinding":
        obj = strict_object(
            value,
            "pytorch_pilot.policy",
            {
                "schema_id",
                "seed",
                "thread_count",
                "optimizer_steps",
                "learning_rate_numerator",
                "learning_rate_denominator",
                "quantization_scale",
                "time_budget_millis",
                "max_output_bytes",
                "max_tensor_bytes",
                "require_cpu",
                "require_deterministic_algorithms",
                "torch_version",
            },
        )
        _require_schema(
            obj["schema_id"], cls.schema_id, "pytorch_pilot.policy.schema_id"
        )
        for name in ("require_cpu", "require_deterministic_algorithms"):
            if not isinstance(obj[name], bool):
                raise SchemaValidationError(
                    f"pytorch_pilot.policy.{name}", "expected Boolean"
                )
        return cls(
            seed=require_structural_integer(
                obj["seed"], "pytorch_pilot.policy.seed", minimum=0
            ),
            thread_count=require_structural_integer(
                obj["thread_count"], "pytorch_pilot.policy.thread_count", minimum=1
            ),
            optimizer_steps=require_structural_integer(
                obj["optimizer_steps"],
                "pytorch_pilot.policy.optimizer_steps",
                minimum=1,
                maximum=1,
            ),
            learning_rate_numerator=require_structural_integer(
                obj["learning_rate_numerator"],
                "pytorch_pilot.policy.learning_rate_numerator",
                minimum=1,
            ),
            learning_rate_denominator=require_structural_integer(
                obj["learning_rate_denominator"],
                "pytorch_pilot.policy.learning_rate_denominator",
                minimum=1,
            ),
            quantization_scale=require_structural_integer(
                obj["quantization_scale"],
                "pytorch_pilot.policy.quantization_scale",
                minimum=1,
            ),
            time_budget_millis=require_structural_integer(
                obj["time_budget_millis"],
                "pytorch_pilot.policy.time_budget_millis",
                minimum=1,
                maximum=300_000,
            ),
            max_output_bytes=require_structural_integer(
                obj["max_output_bytes"],
                "pytorch_pilot.policy.max_output_bytes",
                minimum=1,
            ),
            max_tensor_bytes=require_structural_integer(
                obj["max_tensor_bytes"],
                "pytorch_pilot.policy.max_tensor_bytes",
                minimum=1,
            ),
            require_cpu=obj["require_cpu"],
            require_deterministic_algorithms=obj["require_deterministic_algorithms"],
            torch_version=require_string(
                obj["torch_version"], "pytorch_pilot.policy.torch_version"
            ),
        )

    @property
    def policy_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "seed": self.seed,
            "thread_count": self.thread_count,
            "optimizer_steps": self.optimizer_steps,
            "learning_rate_numerator": self.learning_rate_numerator,
            "learning_rate_denominator": self.learning_rate_denominator,
            "quantization_scale": self.quantization_scale,
            "time_budget_millis": self.time_budget_millis,
            "max_output_bytes": self.max_output_bytes,
            "max_tensor_bytes": self.max_tensor_bytes,
            "require_cpu": self.require_cpu,
            "require_deterministic_algorithms": self.require_deterministic_algorithms,
            "torch_version": self.torch_version,
        }


@dataclass(frozen=True, slots=True)
class PilotRequestBinding:
    transition_id: str
    predecessor_package_id: str
    predecessor_manifest_hash: str
    phase5_predecessor_manifest_hash: str
    predecessor_payload_tree_hash: str
    training_data_manifest_hash: str
    heldout_feature_manifest_hash: str
    policy: PilotPolicyBinding

    schema_id: ClassVar[str] = REQUEST_SCHEMA_ID

    @classmethod
    def from_json(cls, value: object) -> "PilotRequestBinding":
        obj = strict_object(
            value,
            "pytorch_pilot.request",
            {
                "schema_id",
                "transition_id",
                "predecessor_package_id",
                "predecessor_manifest_hash",
                "phase5_predecessor_manifest_hash",
                "predecessor_payload_tree_hash",
                "training_data_manifest_hash",
                "heldout_feature_manifest_hash",
                "policy",
            },
        )
        _require_schema(obj["schema_id"], cls.schema_id, "pytorch_pilot.request.schema_id")
        for name in (
            "predecessor_manifest_hash",
            "phase5_predecessor_manifest_hash",
            "predecessor_payload_tree_hash",
            "training_data_manifest_hash",
            "heldout_feature_manifest_hash",
        ):
            validate_hash256(
                require_string(obj[name], f"pytorch_pilot.request.{name}"),
                f"pytorch_pilot.request.{name}",
            )
        return cls(
            transition_id=require_string(
                obj["transition_id"], "pytorch_pilot.request.transition_id"
            ),
            predecessor_package_id=require_string(
                obj["predecessor_package_id"],
                "pytorch_pilot.request.predecessor_package_id",
            ),
            predecessor_manifest_hash=require_string(
                obj["predecessor_manifest_hash"],
                "pytorch_pilot.request.predecessor_manifest_hash",
            ),
            phase5_predecessor_manifest_hash=require_string(
                obj["phase5_predecessor_manifest_hash"],
                "pytorch_pilot.request.phase5_predecessor_manifest_hash",
            ),
            predecessor_payload_tree_hash=require_string(
                obj["predecessor_payload_tree_hash"],
                "pytorch_pilot.request.predecessor_payload_tree_hash",
            ),
            training_data_manifest_hash=require_string(
                obj["training_data_manifest_hash"],
                "pytorch_pilot.request.training_data_manifest_hash",
            ),
            heldout_feature_manifest_hash=require_string(
                obj["heldout_feature_manifest_hash"],
                "pytorch_pilot.request.heldout_feature_manifest_hash",
            ),
            policy=PilotPolicyBinding.from_json(obj["policy"]),
        )

    @property
    def request_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "transition_id": self.transition_id,
            "predecessor_package_id": self.predecessor_package_id,
            "predecessor_manifest_hash": self.predecessor_manifest_hash,
            "phase5_predecessor_manifest_hash": self.phase5_predecessor_manifest_hash,
            "predecessor_payload_tree_hash": self.predecessor_payload_tree_hash,
            "training_data_manifest_hash": self.training_data_manifest_hash,
            "heldout_feature_manifest_hash": self.heldout_feature_manifest_hash,
            "policy": self.policy.to_json(),
        }


@dataclass(frozen=True, slots=True)
class PilotProposalRecord:
    value: FrozenJsonObject

    def __post_init__(self) -> None:
        if not isinstance(self.value, FrozenJsonObject):
            frozen = freeze_json(self.value, "pytorch_pilot.proposal")
            if not isinstance(frozen, FrozenJsonObject):
                raise SchemaValidationError(
                    "pytorch_pilot.proposal",
                    "proposal must freeze to an object",
                )
            object.__setattr__(self, "value", frozen)

    schema_id: ClassVar[str] = PROPOSAL_SCHEMA_ID

    @classmethod
    def from_json(cls, value: object) -> "PilotProposalRecord":
        if not isinstance(value, dict):
            raise SchemaValidationError("pytorch_pilot.proposal", "expected object")
        expected_fields = {
            "schema_id",
            "backend_id",
            "transition_id",
            "request_hash",
            "policy_hash",
            "predecessor_package_id",
            "predecessor_manifest_hash",
            "predecessor_payload_tree_hash",
            "predecessor_model_hash",
            "candidate_model_hash",
            "architecture_hash",
            "weights_manifest_hash",
            "optimizer_manifest_hash",
            "training_data_manifest_hash",
            "rng_manifest_hash",
            "training_command_hash",
            "resource_manifest_hash",
            "evaluation_request_hash",
            "rollback_binding_hash",
            "heldout_labels_accessed",
            "candidate_reported_acceptance",
            "candidate_reported_certificate",
            "candidate_reported_aggregate_score",
            "substantive_component_kinds",
            "optimizer_steps",
            "proposal_hash",
        }
        if set(value) != expected_fields:
            raise SchemaValidationError("pytorch_pilot.proposal", "unexpected proposal fields")
        _require_schema(value["schema_id"], cls.schema_id, "pytorch_pilot.proposal.schema_id")
        if value["backend_id"] != BACKEND_ID:
            raise SchemaValidationError("pytorch_pilot.proposal.backend_id", "unsupported backend")
        for name in (
            "request_hash",
            "policy_hash",
            "predecessor_manifest_hash",
            "predecessor_payload_tree_hash",
            "predecessor_model_hash",
            "candidate_model_hash",
            "architecture_hash",
            "weights_manifest_hash",
            "optimizer_manifest_hash",
            "training_data_manifest_hash",
            "rng_manifest_hash",
            "training_command_hash",
            "resource_manifest_hash",
            "evaluation_request_hash",
            "rollback_binding_hash",
            "proposal_hash",
        ):
            validate_hash256(
                require_string(value[name], f"pytorch_pilot.proposal.{name}"),
                f"pytorch_pilot.proposal.{name}",
            )
        require_string(value["transition_id"], "pytorch_pilot.proposal.transition_id")
        require_string(
            value["predecessor_package_id"],
            "pytorch_pilot.proposal.predecessor_package_id",
        )
        require_structural_integer(
            value["optimizer_steps"],
            "pytorch_pilot.proposal.optimizer_steps",
            minimum=1,
            maximum=1,
        )
        if value["heldout_labels_accessed"] is not False:
            raise SchemaValidationError(
                "pytorch_pilot.proposal.heldout_labels_accessed",
                "backend must not access held-out labels",
            )
        for name in (
            "candidate_reported_acceptance",
            "candidate_reported_certificate",
            "candidate_reported_aggregate_score",
        ):
            if value[name] is not None:
                raise SchemaValidationError(
                    f"pytorch_pilot.proposal.{name}",
                    "candidate self-certification field must be null",
                )
        if value["substantive_component_kinds"] != ["model_weights"]:
            raise SchemaValidationError(
                "pytorch_pilot.proposal.substantive_component_kinds",
                "expected exactly model_weights",
            )
        core = dict(value)
        declared = core.pop("proposal_hash")
        if canonical_json_hash(core) != declared:
            raise SchemaValidationError(
                "pytorch_pilot.proposal.proposal_hash", "proposal hash mismatch"
            )
        frozen = freeze_json(value, "pytorch_pilot.proposal")
        if not isinstance(frozen, FrozenJsonObject):
            raise SchemaValidationError(
                "pytorch_pilot.proposal",
                "proposal must freeze to an object",
            )
        return cls(value=frozen)

    @property
    def proposal_hash(self) -> str:
        value = self.to_json()
        return str(value["proposal_hash"])

    def to_json(self) -> dict[str, object]:
        value = thaw_json(self.value)
        if not isinstance(value, dict):
            raise SchemaValidationError(
                "pytorch_pilot.proposal",
                "frozen proposal did not thaw to an object",
            )
        return value


@dataclass(frozen=True, slots=True)
class PilotOutputManifestRecord:
    proposal_hash: str
    candidate_reported_selection_hash: str
    files_tree_hash: str

    schema_id: ClassVar[str] = OUTPUT_MANIFEST_SCHEMA_ID

    @classmethod
    def from_json(cls, value: object) -> "PilotOutputManifestRecord":
        obj = strict_object(
            value,
            "pytorch_pilot.output_manifest",
            {
                "schema_id",
                "proposal_hash",
                "phase6_selection_hash",
                "files_tree_hash",
            },
        )
        _require_schema(
            obj["schema_id"], cls.schema_id, "pytorch_pilot.output_manifest.schema_id"
        )
        return cls(
            proposal_hash=validate_hash256(
                require_string(
                    obj["proposal_hash"], "pytorch_pilot.output_manifest.proposal_hash"
                ),
                "pytorch_pilot.output_manifest.proposal_hash",
            ),
            candidate_reported_selection_hash=validate_hash256(
                require_string(
                    obj["phase6_selection_hash"],
                    "pytorch_pilot.output_manifest.phase6_selection_hash",
                ),
                "pytorch_pilot.output_manifest.phase6_selection_hash",
            ),
            files_tree_hash=validate_hash256(
                require_string(
                    obj["files_tree_hash"],
                    "pytorch_pilot.output_manifest.files_tree_hash",
                ),
                "pytorch_pilot.output_manifest.files_tree_hash",
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "proposal_hash": self.proposal_hash,
            "phase6_selection_hash": self.candidate_reported_selection_hash,
            "files_tree_hash": self.files_tree_hash,
        }


__all__ = [
    "BACKEND_ID",
    "EXPECTED_MODEL_PATHS",
    "HOST_SELECTION_POLICY_ID",
    "PILOT_PROCESS_COMMAND_TEMPLATE",
    "PilotOutputManifestRecord",
    "PilotPolicyBinding",
    "PilotProposalRecord",
    "PilotRequestBinding",
]
