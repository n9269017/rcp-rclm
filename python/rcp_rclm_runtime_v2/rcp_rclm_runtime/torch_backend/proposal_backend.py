from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import time
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TYPE_CHECKING, cast

if TYPE_CHECKING:
    import torch


CANONICAL_JSON_HASH_DOMAIN: Final[bytes] = b"RCPRCLM-CANONICAL-JSON-V2\0"
TREE_HASH_DOMAIN: Final[bytes] = b"RCPRCLM-TREE-V2\0"

BACKEND_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_backend_request.v1"
POLICY_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_policy.v1"
PROPOSAL_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_proposal.v1"
MODEL_ARCHITECTURE_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_architecture.v1"
WEIGHT_MANIFEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_weight_manifest.v1"
OPTIMIZER_MANIFEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_optimizer_manifest.v1"
TRAINING_DATA_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_training_data.v1"
RNG_MANIFEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_rng_manifest.v1"
RESOURCE_MANIFEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_resource_manifest.v1"
EVALUATION_REQUEST_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_evaluation_request.v1"
EVALUATION_RESULT_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_evaluation_result.v1"
ROLLBACK_BINDING_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_rollback_binding.v1"
TRAINING_COMMAND_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_training_command.v1"
PHASE6_OPERATION_SCHEMA_ID: Final[str] = "runtime.phase6_selected_file_operation.v2"
PHASE6_SELECTION_SCHEMA_ID: Final[str] = "runtime.phase6_selection.v2"
PYTORCH_PILOT_UPDATE_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_update.v1"

BACKEND_ID: Final[str] = "rcp-rclm-pytorch-cpu-one-step-linear-v1"
MODEL_ID: Final[str] = "tiny-linear-classifier-2x2-v1"
SELECTION_POLICY_ID: Final[str] = "rcp-rclm-pytorch-pilot-selector-v1"
EXPECTED_TORCH_VERSION: Final[str] = "2.10.0"
FIXED_SEED: Final[int] = 1729
FIXED_THREAD_COUNT: Final[int] = 1
FIXED_STEP_COUNT: Final[int] = 1
LEARNING_RATE_NUMERATOR: Final[int] = 1
LEARNING_RATE_DENOMINATOR: Final[int] = 4
QUANTIZATION_SCALE: Final[int] = 1_000_000
MAX_GRADIENT_ABS_NUMERATOR: Final[int] = 4
MAX_GRADIENT_ABS_DENOMINATOR: Final[int] = 1
MAX_PARAMETER_COUNT: Final[int] = 6
DEFAULT_TIME_BUDGET_MILLIS: Final[int] = 30_000
DEFAULT_MAX_OUTPUT_BYTES: Final[int] = 1_000_000
DEFAULT_MAX_TENSOR_BYTES: Final[int] = 100_000

TRAIN_FEATURES: Final[Sequence[tuple[int, int]]] = (
    (-2, -1),
    (-1, -2),
    (1, 2),
    (2, 1),
)
TRAIN_LABELS: Final[Sequence[int]] = (0, 0, 1, 1)
HELDOUT_FEATURES: Final[Sequence[tuple[int, int]]] = (
    (-3, -1),
    (-1, -3),
    (1, 3),
    (3, 1),
)
HELDOUT_LABELS: Final[Sequence[int]] = (0, 0, 1, 1)

MODEL_WEIGHT_PATH: Final[str] = "model/weights/linear.weight.bin"
MODEL_BIAS_PATH: Final[str] = "model/weights/linear.bias.bin"
ARCHITECTURE_PATH: Final[str] = "model/architecture.json"
WEIGHTS_MANIFEST_PATH: Final[str] = "model/weights_manifest.json"
OPTIMIZER_MANIFEST_PATH: Final[str] = "model/optimizer_manifest.json"
TRAINING_DATA_MANIFEST_PATH: Final[str] = "model/training_data_manifest.json"
RNG_MANIFEST_PATH: Final[str] = "model/rng_manifest.json"
TRAINING_COMMAND_PATH: Final[str] = "model/training_command.json"
RESOURCE_MANIFEST_PATH: Final[str] = "model/resource_usage.json"
EVALUATION_REQUEST_PATH: Final[str] = "model/evaluation_request.json"
ROLLBACK_BINDING_PATH: Final[str] = "model/rollback_binding.json"

BackendVerdict = Literal["success", "reject", "indeterminate"]


class BackendError(RuntimeError):
    def __init__(self, code: str, detail: str, verdict: BackendVerdict = "reject") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.verdict = verdict


@dataclass(frozen=True, slots=True)
class PilotPolicy:
    seed: int = FIXED_SEED
    thread_count: int = FIXED_THREAD_COUNT
    optimizer_steps: int = FIXED_STEP_COUNT
    learning_rate_numerator: int = LEARNING_RATE_NUMERATOR
    learning_rate_denominator: int = LEARNING_RATE_DENOMINATOR
    quantization_scale: int = QUANTIZATION_SCALE
    time_budget_millis: int = DEFAULT_TIME_BUDGET_MILLIS
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES
    max_tensor_bytes: int = DEFAULT_MAX_TENSOR_BYTES
    require_cpu: bool = True
    require_deterministic_algorithms: bool = True
    torch_version: str = EXPECTED_TORCH_VERSION

    def __post_init__(self) -> None:
        if self.seed != FIXED_SEED:
            raise BackendError("PYTORCH_POLICY_MISMATCH", "seed differs from the frozen pilot")
        if self.thread_count != FIXED_THREAD_COUNT:
            raise BackendError("PYTORCH_POLICY_MISMATCH", "thread count differs from the frozen pilot")
        if self.optimizer_steps != FIXED_STEP_COUNT:
            raise BackendError("PYTORCH_POLICY_MISMATCH", "pilot requires exactly one optimizer step")
        if (self.learning_rate_numerator, self.learning_rate_denominator) != (
            LEARNING_RATE_NUMERATOR,
            LEARNING_RATE_DENOMINATOR,
        ):
            raise BackendError("PYTORCH_POLICY_MISMATCH", "learning rate differs from the frozen pilot")
        if self.quantization_scale != QUANTIZATION_SCALE:
            raise BackendError("PYTORCH_POLICY_MISMATCH", "quantization scale differs from the frozen pilot")
        if self.time_budget_millis < 1 or self.time_budget_millis > 300_000:
            raise BackendError("PYTORCH_POLICY_INVALID", "time budget is outside the supported range")
        if self.max_output_bytes < 1 or self.max_tensor_bytes < 1:
            raise BackendError("PYTORCH_POLICY_INVALID", "byte budgets must be positive")
        if not self.require_cpu or not self.require_deterministic_algorithms:
            raise BackendError("PYTORCH_POLICY_MISMATCH", "CPU and deterministic algorithms are mandatory")
        if self.torch_version != EXPECTED_TORCH_VERSION:
            raise BackendError("PYTORCH_VERSION_MISMATCH", "unexpected frozen PyTorch version")

    @classmethod
    def from_json(cls, value: object) -> PilotPolicy:
        obj = _strict_object(
            value,
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
            "policy",
        )
        _require_exact(obj["schema_id"], POLICY_SCHEMA_ID, "policy.schema_id")
        return cls(
            seed=_integer(obj["seed"], "policy.seed", minimum=0),
            thread_count=_integer(obj["thread_count"], "policy.thread_count", minimum=1),
            optimizer_steps=_integer(obj["optimizer_steps"], "policy.optimizer_steps", minimum=1),
            learning_rate_numerator=_integer(
                obj["learning_rate_numerator"], "policy.learning_rate_numerator", minimum=1
            ),
            learning_rate_denominator=_integer(
                obj["learning_rate_denominator"], "policy.learning_rate_denominator", minimum=1
            ),
            quantization_scale=_integer(
                obj["quantization_scale"], "policy.quantization_scale", minimum=1
            ),
            time_budget_millis=_integer(
                obj["time_budget_millis"], "policy.time_budget_millis", minimum=1
            ),
            max_output_bytes=_integer(obj["max_output_bytes"], "policy.max_output_bytes", minimum=1),
            max_tensor_bytes=_integer(obj["max_tensor_bytes"], "policy.max_tensor_bytes", minimum=1),
            require_cpu=_boolean(obj["require_cpu"], "policy.require_cpu"),
            require_deterministic_algorithms=_boolean(
                obj["require_deterministic_algorithms"],
                "policy.require_deterministic_algorithms",
            ),
            torch_version=_string(obj["torch_version"], "policy.torch_version"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": POLICY_SCHEMA_ID,
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
class BackendRequest:
    transition_id: str
    predecessor_package_id: str
    predecessor_manifest_hash: str
    phase5_predecessor_manifest_hash: str
    predecessor_payload_tree_hash: str
    training_data_manifest_hash: str
    heldout_feature_manifest_hash: str
    policy: PilotPolicy

    @classmethod
    def from_json(cls, value: object) -> BackendRequest:
        obj = _strict_object(
            value,
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
            "request",
        )
        _require_exact(obj["schema_id"], BACKEND_SCHEMA_ID, "request.schema_id")
        return cls(
            transition_id=_string(obj["transition_id"], "request.transition_id"),
            predecessor_package_id=_string(
                obj["predecessor_package_id"], "request.predecessor_package_id"
            ),
            predecessor_manifest_hash=_hash256(
                obj["predecessor_manifest_hash"], "request.predecessor_manifest_hash"
            ),
            phase5_predecessor_manifest_hash=_hash256(
                obj["phase5_predecessor_manifest_hash"],
                "request.phase5_predecessor_manifest_hash",
            ),
            predecessor_payload_tree_hash=_hash256(
                obj["predecessor_payload_tree_hash"],
                "request.predecessor_payload_tree_hash",
            ),
            training_data_manifest_hash=_hash256(
                obj["training_data_manifest_hash"],
                "request.training_data_manifest_hash",
            ),
            heldout_feature_manifest_hash=_hash256(
                obj["heldout_feature_manifest_hash"],
                "request.heldout_feature_manifest_hash",
            ),
            policy=PilotPolicy.from_json(obj["policy"]),
        )

    @property
    def request_hash(self) -> str:
        return _canonical_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": BACKEND_SCHEMA_ID,
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
class TensorArtifact:
    name: str
    path: str
    shape: Sequence[int]
    dtype: Literal["int64"]
    byte_order: Literal["little"]
    element_count: int
    size_bytes: int
    sha256: str

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "shape": list(self.shape),
            "dtype": self.dtype,
            "byte_order": self.byte_order,
            "element_count": self.element_count,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ExactEvaluation:
    correct_count: int
    example_count: int
    protected_correct_count: int
    protected_example_count: int
    predictions: Sequence[int]

    def to_json(self) -> dict[str, object]:
        return {
            "correct_count": self.correct_count,
            "example_count": self.example_count,
            "protected_correct_count": self.protected_correct_count,
            "protected_example_count": self.protected_example_count,
            "predictions": list(self.predictions),
        }


@dataclass(frozen=True, slots=True)
class ProposalArtifacts:
    proposal: dict[str, object]
    phase6_selection: dict[str, object]
    output_root: Path


@dataclass(frozen=True, slots=True)
class EvaluationArtifacts:
    result: dict[str, object]
    output_path: Path


def default_policy() -> PilotPolicy:
    return PilotPolicy()


def fixed_training_manifest() -> dict[str, object]:
    train_payload = {
        "features": [list(row) for row in TRAIN_FEATURES],
        "labels": list(TRAIN_LABELS),
    }
    heldout_features_payload = {
        "features": [list(row) for row in HELDOUT_FEATURES],
    }
    return {
        "schema_id": TRAINING_DATA_SCHEMA_ID,
        "dataset_id": "rcp-rclm-pytorch-pilot-separable-2d-v1",
        "feature_dtype": "int64",
        "label_dtype": "int64",
        "feature_dimension": 2,
        "class_count": 2,
        "train_example_count": len(TRAIN_FEATURES),
        "heldout_example_count": len(HELDOUT_FEATURES),
        "train_manifest_hash": _canonical_hash(train_payload),
        "heldout_feature_manifest_hash": _canonical_hash(heldout_features_payload),
        "heldout_labels_disclosed_to_backend": False,
    }


def fixed_heldout_evaluation_data() -> dict[str, object]:
    return {
        "schema_id": "runtime.pytorch_pilot_heldout_data.v1",
        "features": [list(row) for row in HELDOUT_FEATURES],
        "labels": list(HELDOUT_LABELS),
        "protected_class": 0,
    }


def initialize_predecessor_model(output_root: Path) -> dict[str, object]:
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise BackendError("PYTORCH_OUTPUT_EXISTS", "predecessor model output already exists")
    parent = resolved.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-pytorch-init-", dir=parent) as temporary:
        staging = Path(temporary) / "model"
        staging.mkdir(parents=True, exist_ok=False)
        weights = ((0, 0), (0, 0))
        bias = (0, 0)
        _write_model_files(staging, weights, bias, source="frozen_zero_predecessor")
        os.replace(staging, resolved)
    manifest = _load_canonical_json(resolved / WEIGHTS_MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise BackendError("PYTORCH_INTERNAL_ERROR", "weight manifest is not an object")
    return cast(dict[str, object], manifest)


def run_proposal_backend(
    request: BackendRequest,
    predecessor_root: Path,
    output_root: Path,
) -> ProposalArtifacts:
    start_ns = time.monotonic_ns()
    resolved_predecessor = predecessor_root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise BackendError("PYTORCH_OUTPUT_EXISTS", "proposal output already exists")
    _require_time_budget(start_ns, request.policy)
    _validate_training_manifest_bindings(request)
    before_snapshot = _snapshot_predecessor(resolved_predecessor)
    predecessor_weights = _load_quantized_model(resolved_predecessor)
    predecessor_manifest = _load_canonical_json(resolved_predecessor / WEIGHTS_MANIFEST_PATH)
    if not isinstance(predecessor_manifest, dict):
        raise BackendError("PYTORCH_PREDECESSOR_INVALID", "predecessor weight manifest is not an object")
    predecessor_model_hash = _hash256(
        predecessor_manifest.get("model_hash"),
        "predecessor.weights_manifest.model_hash",
    )
    _require_time_budget(start_ns, request.policy)

    torch = _load_torch(request.policy)
    model = _build_torch_model(torch)
    _load_quantized_into_model(torch, model, predecessor_weights, request.policy.quantization_scale)
    torch.manual_seed(request.policy.seed)
    rng_before = _torch_rng_bytes(torch)
    before_float_state = _float_state_snapshot(torch, model)
    optimizer = torch.optim.SGD(
        model.parameters(),
        lr=request.policy.learning_rate_numerator / request.policy.learning_rate_denominator,
        momentum=0.0,
        weight_decay=0.0,
    )
    train_x = torch.tensor(TRAIN_FEATURES, dtype=torch.float64, device="cpu")
    train_y = torch.tensor(TRAIN_LABELS, dtype=torch.long, device="cpu")
    optimizer.zero_grad(set_to_none=True)
    logits = model(train_x)
    if logits.device.type != "cpu":
        raise BackendError("PYTORCH_DEVICE_VIOLATION", "training logits are not on CPU")
    loss = torch.nn.functional.cross_entropy(logits, train_y, reduction="mean")
    if not bool(torch.isfinite(loss).item()):
        raise BackendError("PYTORCH_NONFINITE_LOSS", "training loss is not finite")
    loss.backward()
    _validate_gradients(torch, model)
    optimizer.step()
    after_float_state = _float_state_snapshot(torch, model)
    if before_float_state == after_float_state:
        raise BackendError("PYTORCH_NO_WEIGHT_CHANGE", "the optimizer step changed no parameter bytes")
    candidate_weights = _quantize_model(torch, model, request.policy.quantization_scale)
    if candidate_weights == predecessor_weights:
        raise BackendError("PYTORCH_NO_QUANTIZED_CHANGE", "quantized model is unchanged")
    rng_after = _torch_rng_bytes(torch)
    _require_time_budget(start_ns, request.policy)

    parent = resolved_output.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-pytorch-proposal-", dir=parent) as temporary:
        staging = Path(temporary) / "proposal"
        files_root = staging / "files"
        files_root.mkdir(parents=True, exist_ok=False)
        weight_manifest = _write_model_files(
            files_root,
            candidate_weights[0],
            candidate_weights[1],
            source="one_sgd_step_quantized",
        )
        candidate_model_hash = _hash256(
            weight_manifest["model_hash"],
            "candidate.weights_manifest.model_hash",
        )
        if candidate_model_hash == predecessor_model_hash:
            raise BackendError("PYTORCH_NO_MODEL_HASH_CHANGE", "candidate model hash equals predecessor")

        architecture = _load_canonical_json(files_root / ARCHITECTURE_PATH)
        weights_manifest = _load_canonical_json(files_root / WEIGHTS_MANIFEST_PATH)
        training_data_manifest = fixed_training_manifest()
        optimizer_manifest = {
            "schema_id": OPTIMIZER_MANIFEST_SCHEMA_ID,
            "optimizer": "SGD",
            "learning_rate": {
                "numerator": request.policy.learning_rate_numerator,
                "denominator": request.policy.learning_rate_denominator,
            },
            "momentum": {"numerator": 0, "denominator": 1},
            "weight_decay": {"numerator": 0, "denominator": 1},
            "step_count": request.policy.optimizer_steps,
            "parameter_count": MAX_PARAMETER_COUNT,
            "optimizer_state_hash": _canonical_hash(
                {
                    "optimizer": "SGD",
                    "state": [],
                    "step_count": request.policy.optimizer_steps,
                }
            ),
        }
        rng_manifest = {
            "schema_id": RNG_MANIFEST_SCHEMA_ID,
            "seed": request.policy.seed,
            "torch_rng_before_sha256": _sha256(rng_before),
            "torch_rng_after_sha256": _sha256(rng_after),
            "python_random_used": False,
            "numpy_used": False,
            "cuda_used": False,
        }
        training_command = {
            "schema_id": TRAINING_COMMAND_SCHEMA_ID,
            "argv": [
                sys.executable,
                "-m",
                "rcp_rclm_runtime.torch_backend.proposal_backend",
                "propose",
                "--request",
                "<canonical-request>",
                "--predecessor-root",
                "<read-only-predecessor>",
                "--output-root",
                "<isolated-output>",
            ],
            "shell": False,
            "network_allowed": False,
            "device": "cpu",
        }
        resource_manifest = {
            "schema_id": RESOURCE_MANIFEST_SCHEMA_ID,
            "optimizer_steps": request.policy.optimizer_steps,
            "model_forward_invocations": 1,
            "model_backward_invocations": 1,
            "thread_count": request.policy.thread_count,
            "parameter_count": MAX_PARAMETER_COUNT,
            "train_example_count": len(TRAIN_FEATURES),
            "tensor_bytes": _tensor_file_bytes(files_root),
            "time_budget_millis": request.policy.time_budget_millis,
            "max_output_bytes": request.policy.max_output_bytes,
            "max_tensor_bytes": request.policy.max_tensor_bytes,
            "network_requests": 0,
            "gpu_invocations": 0,
        }
        evaluation_request = {
            "schema_id": EVALUATION_REQUEST_SCHEMA_ID,
            "candidate_model_hash": candidate_model_hash,
            "predecessor_model_hash": predecessor_model_hash,
            "heldout_feature_manifest_hash": request.heldout_feature_manifest_hash,
            "heldout_labels_accessed_by_backend": False,
            "authoritative_evaluator": "framework_independent_exact_integer_v1",
        }
        rollback_binding = {
            "schema_id": ROLLBACK_BINDING_SCHEMA_ID,
            "predecessor_model_hash": predecessor_model_hash,
            "predecessor_weight_manifest_hash": _canonical_hash(predecessor_manifest),
            "predecessor_file_hashes": before_snapshot,
            "phase6_rollback_archive_required": True,
        }
        for relative_path, value in (
            (OPTIMIZER_MANIFEST_PATH, optimizer_manifest),
            (TRAINING_DATA_MANIFEST_PATH, training_data_manifest),
            (RNG_MANIFEST_PATH, rng_manifest),
            (TRAINING_COMMAND_PATH, training_command),
            (RESOURCE_MANIFEST_PATH, resource_manifest),
            (EVALUATION_REQUEST_PATH, evaluation_request),
            (ROLLBACK_BINDING_PATH, rollback_binding),
        ):
            _write_canonical_json(files_root / relative_path, value)

        operations = _phase6_operations(resolved_predecessor, files_root)
        selected_update = {
            "schema_id": PYTORCH_PILOT_UPDATE_SCHEMA_ID,
            "kind": "model_weight_update",
            "base_rclm_update": "stay",
            "model_before_hash": predecessor_model_hash,
            "model_after_hash": candidate_model_hash,
            "optimizer_steps": request.policy.optimizer_steps,
        }
        proposal_core = {
            "schema_id": PROPOSAL_SCHEMA_ID,
            "backend_id": BACKEND_ID,
            "transition_id": request.transition_id,
            "request_hash": request.request_hash,
            "policy_hash": _canonical_hash(request.policy.to_json()),
            "predecessor_package_id": request.predecessor_package_id,
            "predecessor_manifest_hash": request.predecessor_manifest_hash,
            "predecessor_payload_tree_hash": request.predecessor_payload_tree_hash,
            "predecessor_model_hash": predecessor_model_hash,
            "candidate_model_hash": candidate_model_hash,
            "architecture_hash": _canonical_hash(architecture),
            "weights_manifest_hash": _canonical_hash(weights_manifest),
            "optimizer_manifest_hash": _canonical_hash(optimizer_manifest),
            "training_data_manifest_hash": _canonical_hash(training_data_manifest),
            "rng_manifest_hash": _canonical_hash(rng_manifest),
            "training_command_hash": _canonical_hash(training_command),
            "resource_manifest_hash": _canonical_hash(resource_manifest),
            "evaluation_request_hash": _canonical_hash(evaluation_request),
            "rollback_binding_hash": _canonical_hash(rollback_binding),
            "heldout_labels_accessed": False,
            "candidate_reported_acceptance": None,
            "candidate_reported_certificate": None,
            "candidate_reported_aggregate_score": None,
            "substantive_component_kinds": ["model_weights"],
            "optimizer_steps": request.policy.optimizer_steps,
        }
        proposal_hash = _canonical_hash(proposal_core)
        proposal = dict(proposal_core)
        proposal["proposal_hash"] = proposal_hash
        selection = {
            "schema_id": PHASE6_SELECTION_SCHEMA_ID,
            "transition_id": request.transition_id,
            "proposal_hash": proposal_hash,
            "generator_request_hash": request.request_hash,
            "predecessor_package_id": request.predecessor_package_id,
            "predecessor_manifest_hash": request.predecessor_manifest_hash,
            "phase5_predecessor_manifest_hash": request.phase5_predecessor_manifest_hash,
            "selection_policy_id": SELECTION_POLICY_ID,
            "selected_update": selected_update,
            "selected_update_hash": _canonical_hash(selected_update),
            "operations": operations,
            "substantive_component_kinds": ["model_weights"],
        }
        _write_canonical_json(staging / "proposal.json", proposal)
        _write_canonical_json(staging / "phase6_selection.json", selection)
        semantic_manifest = {
            "schema_id": "runtime.pytorch_pilot_output_manifest.v1",
            "proposal_hash": proposal_hash,
            "phase6_selection_hash": _canonical_hash(selection),
            "files_tree_hash": _directory_tree_hash(files_root),
        }
        _write_canonical_json(staging / "manifest.json", semantic_manifest)
        output_size = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if output_size > request.policy.max_output_bytes:
            raise BackendError("PYTORCH_OUTPUT_BUDGET_EXCEEDED", "proposal output exceeds byte budget")
        if _tensor_file_bytes(files_root) > request.policy.max_tensor_bytes:
            raise BackendError("PYTORCH_TENSOR_BUDGET_EXCEEDED", "candidate tensor bytes exceed budget")
        _require_time_budget(start_ns, request.policy)
        os.replace(staging, resolved_output)

    after_snapshot = _snapshot_predecessor(resolved_predecessor)
    if after_snapshot != before_snapshot:
        shutil.rmtree(resolved_output, ignore_errors=True)
        raise BackendError("PYTORCH_PREDECESSOR_MUTATED", "predecessor bytes changed during proposal")
    return ProposalArtifacts(proposal=proposal, phase6_selection=selection, output_root=resolved_output)


def evaluate_proposal_exact(
    proposal_root: Path,
    evaluation_data: object,
    output_path: Path,
) -> EvaluationArtifacts:
    resolved_proposal = proposal_root.resolve(strict=True)
    proposal = _load_canonical_json(resolved_proposal / "proposal.json")
    if not isinstance(proposal, dict):
        raise BackendError("PYTORCH_PROPOSAL_INVALID", "proposal is not an object")
    candidate_model_hash = _hash256(proposal.get("candidate_model_hash"), "proposal.candidate_model_hash")
    predecessor_model_hash = _hash256(
        proposal.get("predecessor_model_hash"), "proposal.predecessor_model_hash"
    )
    return evaluate_model_root_exact(
        resolved_proposal / "files",
        predecessor_model_hash=predecessor_model_hash,
        candidate_model_hash=candidate_model_hash,
        evaluation_data=evaluation_data,
        output_path=output_path,
    )


def evaluate_model_root_exact(
    model_root: Path,
    *,
    predecessor_model_hash: str,
    candidate_model_hash: str,
    evaluation_data: object,
    output_path: Path,
) -> EvaluationArtifacts:
    resolved_model_root = model_root.resolve(strict=True)
    predecessor_model_hash = _hash256(predecessor_model_hash, "predecessor_model_hash")
    candidate_model_hash = _hash256(candidate_model_hash, "candidate_model_hash")
    data_obj = _strict_object(
        evaluation_data,
        {"schema_id", "features", "labels", "protected_class"},
        "evaluation_data",
    )
    _require_exact(
        data_obj["schema_id"],
        "runtime.pytorch_pilot_heldout_data.v1",
        "evaluation_data.schema_id",
    )
    features = _matrix_of_ints(data_obj["features"], "evaluation_data.features", columns=2)
    labels = _array_of_ints(data_obj["labels"], "evaluation_data.labels")
    protected_class = _integer(data_obj["protected_class"], "evaluation_data.protected_class", minimum=0)
    if len(features) != len(labels) or not features:
        raise BackendError("PYTORCH_EVALUATION_INVALID", "held-out features and labels differ in length")
    if protected_class not in {0, 1} or any(label not in {0, 1} for label in labels):
        raise BackendError("PYTORCH_EVALUATION_INVALID", "labels must be binary")

    candidate = _load_quantized_model(resolved_model_root)
    candidate_manifest = _load_canonical_json(
        resolved_model_root / WEIGHTS_MANIFEST_PATH
    )
    if not isinstance(candidate_manifest, dict):
        raise BackendError("PYTORCH_PROPOSAL_INVALID", "candidate weight manifest is not an object")
    if candidate_manifest.get("model_hash") != candidate_model_hash:
        raise BackendError("PYTORCH_PROPOSAL_INVALID", "candidate model hash mismatch")
    predecessor = (((0, 0), (0, 0)), (0, 0))
    if _model_hash_from_quantized(predecessor[0], predecessor[1]) != predecessor_model_hash:
        raise BackendError(
            "PYTORCH_PREDECESSOR_UNSUPPORTED",
            "pilot evaluator expects the frozen zero-weight predecessor",
        )
    before = _exact_evaluate(predecessor[0], predecessor[1], features, labels, protected_class)
    after = _exact_evaluate(candidate[0], candidate[1], features, labels, protected_class)
    objective_improved = after.correct_count > before.correct_count
    protected_nonregression = (
        after.protected_correct_count * before.protected_example_count
        >= before.protected_correct_count * after.protected_example_count
    )
    evaluation_conditions_met = objective_improved and protected_nonregression
    result_core = {
        "schema_id": EVALUATION_RESULT_SCHEMA_ID,
        "candidate_model_hash": candidate_model_hash,
        "predecessor_model_hash": predecessor_model_hash,
        "before": before.to_json(),
        "after": after.to_json(),
        "objective": "heldout_correct_count",
        "objective_improved": objective_improved,
        "protected_metric": "class_0_recall",
        "protected_nonregression": protected_nonregression,
        "arithmetic": "exact_integer_counts",
        "torch_used_for_evaluation": False,
        "evaluation_conditions_met": evaluation_conditions_met,
    }
    result = dict(result_core)
    result["evaluation_hash"] = _canonical_hash(result_core)
    resolved_output = output_path.resolve(strict=False)
    if resolved_output.exists():
        raise BackendError("PYTORCH_OUTPUT_EXISTS", "evaluation output already exists")
    _write_canonical_json(resolved_output, result)
    return EvaluationArtifacts(result=result, output_path=resolved_output)


def make_default_request(
    *,
    transition_id: str,
    predecessor_package_id: str,
    predecessor_manifest_hash: str,
    phase5_predecessor_manifest_hash: str,
    predecessor_payload_tree_hash: str,
) -> BackendRequest:
    training_manifest = fixed_training_manifest()
    return BackendRequest(
        transition_id=transition_id,
        predecessor_package_id=predecessor_package_id,
        predecessor_manifest_hash=_hash256(predecessor_manifest_hash, "predecessor_manifest_hash"),
        phase5_predecessor_manifest_hash=_hash256(
            phase5_predecessor_manifest_hash,
            "phase5_predecessor_manifest_hash",
        ),
        predecessor_payload_tree_hash=_hash256(
            predecessor_payload_tree_hash,
            "predecessor_payload_tree_hash",
        ),
        training_data_manifest_hash=_canonical_hash(training_manifest),
        heldout_feature_manifest_hash=_string(
            training_manifest["heldout_feature_manifest_hash"],
            "training_manifest.heldout_feature_manifest_hash",
        ),
        policy=default_policy(),
    )


def _load_torch(policy: PilotPolicy):
    try:
        import torch
    except ImportError as exc:
        raise BackendError("PYTORCH_NOT_INSTALLED", "PyTorch is unavailable", "indeterminate") from exc
    observed_version = torch.__version__.split("+", 1)[0]
    if observed_version != policy.torch_version:
        raise BackendError(
            "PYTORCH_VERSION_MISMATCH",
            f"expected {policy.torch_version}, observed {observed_version}",
        )
    if torch.cuda.is_available():
        raise BackendError("PYTORCH_GPU_VISIBLE", "the CPU-only pilot refuses a visible CUDA device")
    torch.set_num_threads(policy.thread_count)
    try:
        torch.set_num_interop_threads(policy.thread_count)
    except RuntimeError as exc:
        if torch.get_num_interop_threads() != policy.thread_count:
            raise BackendError(
                "PYTORCH_THREAD_CONFIGURATION_FAILED",
                "inter-op thread count must be configured before parallel work",
            ) from exc
    torch.manual_seed(policy.seed)
    torch.use_deterministic_algorithms(True, warn_only=False)
    if hasattr(torch, "set_deterministic_debug_mode"):
        torch.set_deterministic_debug_mode("error")
    if hasattr(torch.backends, "mkldnn"):
        torch.backends.mkldnn.enabled = False
    return torch


def _build_torch_model(torch):
    class TinyLinearClassifier(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear = torch.nn.Linear(2, 2, bias=True, dtype=torch.float64)

        def forward(self, inputs: "torch.Tensor") -> "torch.Tensor":
            return self.linear(inputs)

    return TinyLinearClassifier().to(device="cpu", dtype=torch.float64)


def _load_quantized_into_model(torch, model, quantized, scale: int) -> None:
    weights, bias = quantized
    with torch.no_grad():
        model.linear.weight.copy_(
            torch.tensor(weights, dtype=torch.float64, device="cpu") / scale
        )
        model.linear.bias.copy_(
            torch.tensor(bias, dtype=torch.float64, device="cpu") / scale
        )


def _validate_gradients(torch, model) -> None:
    gradient_count = 0
    for name, parameter in sorted(model.named_parameters(), key=lambda item: item[0].encode("utf-8")):
        gradient = parameter.grad
        if gradient is None:
            raise BackendError("PYTORCH_MISSING_GRADIENT", f"missing gradient for {name}")
        if gradient.device.type != "cpu":
            raise BackendError("PYTORCH_DEVICE_VIOLATION", f"gradient for {name} is not on CPU")
        if not bool(torch.isfinite(gradient).all().item()):
            raise BackendError("PYTORCH_NONFINITE_GRADIENT", f"nonfinite gradient for {name}")
        maximum = float(gradient.detach().abs().max().item())
        if maximum * MAX_GRADIENT_ABS_DENOMINATOR > MAX_GRADIENT_ABS_NUMERATOR:
            raise BackendError("PYTORCH_GRADIENT_BUDGET_EXCEEDED", f"gradient bound exceeded for {name}")
        gradient_count += int(gradient.numel())
    if gradient_count != MAX_PARAMETER_COUNT:
        raise BackendError("PYTORCH_ARCHITECTURE_MISMATCH", "unexpected gradient parameter count")


def _float_state_snapshot(torch, model) -> Sequence[tuple[str, bytes]]:
    items: list[tuple[str, bytes]] = []
    for name, tensor in sorted(model.state_dict().items(), key=lambda item: item[0].encode("utf-8")):
        if tensor.dtype != torch.float64 or tensor.device.type != "cpu":
            raise BackendError("PYTORCH_ARCHITECTURE_MISMATCH", f"unexpected tensor layout for {name}")
        values = cast(list[float], tensor.detach().contiguous().reshape(-1).tolist())
        if any(not math.isfinite(value) for value in values):
            raise BackendError("PYTORCH_NONFINITE_PARAMETER", f"nonfinite parameter {name}")
        items.append((name, b"".join(struct.pack("<d", value) for value in values)))
    return tuple(items)


def _quantize_model(torch, model, scale: int):
    state = model.state_dict()
    weight = state.get("linear.weight")
    bias = state.get("linear.bias")
    if weight is None or bias is None:
        raise BackendError("PYTORCH_ARCHITECTURE_MISMATCH", "expected linear weight and bias")
    if tuple(weight.shape) != (2, 2) or tuple(bias.shape) != (2,):
        raise BackendError("PYTORCH_ARCHITECTURE_MISMATCH", "unexpected model tensor shape")
    quantized_weight_tensor = torch.round(weight.detach() * scale).to(dtype=torch.int64, device="cpu")
    quantized_bias_tensor = torch.round(bias.detach() * scale).to(dtype=torch.int64, device="cpu")
    quantized_weight_rows = cast(list[list[int]], quantized_weight_tensor.tolist())
    quantized_bias_values = cast(list[int], quantized_bias_tensor.tolist())
    weights = tuple(tuple(int(value) for value in row) for row in quantized_weight_rows)
    bias_values = tuple(int(value) for value in quantized_bias_values)
    return cast(tuple[tuple[tuple[int, int], tuple[int, int]], tuple[int, int]], (weights, bias_values))


def _torch_rng_bytes(torch) -> bytes:
    state = torch.get_rng_state().detach().contiguous().to(dtype=torch.uint8, device="cpu")
    return bytes(cast(list[int], state.tolist()))


def _write_model_files(
    root: Path,
    weights: Sequence[Sequence[int]],
    bias: Sequence[int],
    *,
    source: str,
) -> dict[str, object]:
    normalized_weights = _normalize_weights(weights)
    normalized_bias = _normalize_bias(bias)
    architecture = {
        "schema_id": MODEL_ARCHITECTURE_SCHEMA_ID,
        "model_id": MODEL_ID,
        "module": "Linear",
        "input_features": 2,
        "output_classes": 2,
        "bias": True,
        "training_dtype": "float64",
        "package_weight_dtype": "int64",
        "quantization_scale": QUANTIZATION_SCALE,
        "activation": "identity",
        "prediction": "argmax_lowest_index_tiebreak",
    }
    weight_bytes = _pack_int64(value for row in normalized_weights for value in row)
    bias_bytes = _pack_int64(normalized_bias)
    weight_artifact = TensorArtifact(
        name="linear.weight",
        path=MODEL_WEIGHT_PATH,
        shape=(2, 2),
        dtype="int64",
        byte_order="little",
        element_count=4,
        size_bytes=len(weight_bytes),
        sha256=_sha256(weight_bytes),
    )
    bias_artifact = TensorArtifact(
        name="linear.bias",
        path=MODEL_BIAS_PATH,
        shape=(2,),
        dtype="int64",
        byte_order="little",
        element_count=2,
        size_bytes=len(bias_bytes),
        sha256=_sha256(bias_bytes),
    )
    _write_bytes(root / MODEL_WEIGHT_PATH, weight_bytes)
    _write_bytes(root / MODEL_BIAS_PATH, bias_bytes)
    _write_canonical_json(root / ARCHITECTURE_PATH, architecture)
    tensors = [weight_artifact.to_json(), bias_artifact.to_json()]
    tensors.sort(key=lambda item: cast(str, item["name"]).encode("utf-8"))
    manifest_core = {
        "schema_id": WEIGHT_MANIFEST_SCHEMA_ID,
        "model_id": MODEL_ID,
        "source": source,
        "architecture_hash": _canonical_hash(architecture),
        "quantization_scale": QUANTIZATION_SCALE,
        "tensors": tensors,
    }
    manifest = dict(manifest_core)
    manifest["model_hash"] = _canonical_hash(manifest_core)
    _write_canonical_json(root / WEIGHTS_MANIFEST_PATH, manifest)
    return manifest


def _load_quantized_model(root: Path):
    architecture = _load_canonical_json(root / ARCHITECTURE_PATH)
    if not isinstance(architecture, dict):
        raise BackendError("PYTORCH_MODEL_INVALID", "architecture manifest is not an object")
    if architecture.get("model_id") != MODEL_ID:
        raise BackendError("PYTORCH_MODEL_INVALID", "unsupported model architecture")
    if architecture.get("quantization_scale") != QUANTIZATION_SCALE:
        raise BackendError("PYTORCH_MODEL_INVALID", "unexpected quantization scale")
    manifest = _load_canonical_json(root / WEIGHTS_MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise BackendError("PYTORCH_MODEL_INVALID", "weight manifest is not an object")
    weight_bytes = (root / MODEL_WEIGHT_PATH).read_bytes()
    bias_bytes = (root / MODEL_BIAS_PATH).read_bytes()
    if len(weight_bytes) != 32 or len(bias_bytes) != 16:
        raise BackendError("PYTORCH_MODEL_INVALID", "unexpected tensor byte length")
    tensors = manifest.get("tensors")
    if not isinstance(tensors, list) or len(tensors) != 2:
        raise BackendError("PYTORCH_MODEL_INVALID", "unexpected tensor manifest")
    by_name = {
        _string(item.get("name"), "weights_manifest.tensor.name"): item
        for item in tensors
        if isinstance(item, dict)
    }
    if set(by_name) != {"linear.weight", "linear.bias"}:
        raise BackendError("PYTORCH_MODEL_INVALID", "tensor names differ from architecture")
    if by_name["linear.weight"].get("sha256") != _sha256(weight_bytes):
        raise BackendError("PYTORCH_MODEL_INVALID", "weight tensor hash mismatch")
    if by_name["linear.bias"].get("sha256") != _sha256(bias_bytes):
        raise BackendError("PYTORCH_MODEL_INVALID", "bias tensor hash mismatch")
    weights_flat = struct.unpack("<4q", weight_bytes)
    bias_values = struct.unpack("<2q", bias_bytes)
    weights = ((weights_flat[0], weights_flat[1]), (weights_flat[2], weights_flat[3]))
    expected_hash = _model_hash_from_quantized(weights, bias_values)
    if manifest.get("model_hash") != expected_hash:
        raise BackendError("PYTORCH_MODEL_INVALID", "model hash mismatch")
    return weights, (bias_values[0], bias_values[1])


def _model_hash_from_quantized(weights: Sequence[Sequence[int]], bias: Sequence[int]) -> str:
    normalized_weights = _normalize_weights(weights)
    normalized_bias = _normalize_bias(bias)
    architecture = {
        "schema_id": MODEL_ARCHITECTURE_SCHEMA_ID,
        "model_id": MODEL_ID,
        "module": "Linear",
        "input_features": 2,
        "output_classes": 2,
        "bias": True,
        "training_dtype": "float64",
        "package_weight_dtype": "int64",
        "quantization_scale": QUANTIZATION_SCALE,
        "activation": "identity",
        "prediction": "argmax_lowest_index_tiebreak",
    }
    weight_bytes = _pack_int64(value for row in normalized_weights for value in row)
    bias_bytes = _pack_int64(normalized_bias)
    tensors = [
        TensorArtifact(
            "linear.weight",
            MODEL_WEIGHT_PATH,
            (2, 2),
            "int64",
            "little",
            4,
            len(weight_bytes),
            _sha256(weight_bytes),
        ).to_json(),
        TensorArtifact(
            "linear.bias",
            MODEL_BIAS_PATH,
            (2,),
            "int64",
            "little",
            2,
            len(bias_bytes),
            _sha256(bias_bytes),
        ).to_json(),
    ]
    tensors.sort(key=lambda item: cast(str, item["name"]).encode("utf-8"))
    return _canonical_hash(
        {
            "schema_id": WEIGHT_MANIFEST_SCHEMA_ID,
            "model_id": MODEL_ID,
            "source": "frozen_zero_predecessor" if all(value == 0 for row in normalized_weights for value in row) and all(value == 0 for value in normalized_bias) else "one_sgd_step_quantized",
            "architecture_hash": _canonical_hash(architecture),
            "quantization_scale": QUANTIZATION_SCALE,
            "tensors": tensors,
        }
    )


def _phase6_operations(predecessor_root: Path, files_root: Path) -> list[dict[str, object]]:
    relative_paths = tuple(
        sorted(
            (
                ARCHITECTURE_PATH,
                WEIGHTS_MANIFEST_PATH,
                MODEL_WEIGHT_PATH,
                MODEL_BIAS_PATH,
                OPTIMIZER_MANIFEST_PATH,
                TRAINING_DATA_MANIFEST_PATH,
                RNG_MANIFEST_PATH,
                TRAINING_COMMAND_PATH,
                RESOURCE_MANIFEST_PATH,
                EVALUATION_REQUEST_PATH,
                ROLLBACK_BINDING_PATH,
            ),
            key=lambda item: item.encode("utf-8"),
        )
    )
    operations: list[dict[str, object]] = []
    for relative_path in relative_paths:
        source_path = files_root / relative_path
        content = source_path.read_bytes()
        predecessor_path = predecessor_root / relative_path
        expected_before_hash: str | None
        expected_before_mode: str | None
        if predecessor_path.is_file():
            predecessor_content = predecessor_path.read_bytes()
            expected_before_hash = _sha256(predecessor_content)
            expected_before_mode = "0644"
            if predecessor_content == content:
                continue
        else:
            expected_before_hash = None
            expected_before_mode = None
        operations.append(
            {
                "schema_id": PHASE6_OPERATION_SCHEMA_ID,
                "path": relative_path,
                "operation": "write",
                "component_kind": "model_weights" if relative_path.startswith("model/weights/") else None,
                "expected_before_hash": expected_before_hash,
                "expected_before_mode": expected_before_mode,
                "after_mode": "0644",
                "content_base64": base64.b64encode(content).decode("ascii"),
                "after_hash": _sha256(content),
            }
        )
    return operations


def _exact_evaluate(
    weights: Sequence[Sequence[int]],
    bias: Sequence[int],
    features: Sequence[Sequence[int]],
    labels: Sequence[int],
    protected_class: int,
) -> ExactEvaluation:
    normalized_weights = _normalize_weights(weights)
    normalized_bias = _normalize_bias(bias)
    predictions: list[int] = []
    correct_count = 0
    protected_correct = 0
    protected_total = 0
    for row, label in zip(features, labels, strict=True):
        if len(row) != 2:
            raise BackendError("PYTORCH_EVALUATION_INVALID", "feature row must have length two")
        logits = (
            normalized_weights[0][0] * int(row[0])
            + normalized_weights[0][1] * int(row[1])
            + normalized_bias[0],
            normalized_weights[1][0] * int(row[0])
            + normalized_weights[1][1] * int(row[1])
            + normalized_bias[1],
        )
        prediction = 0 if logits[0] >= logits[1] else 1
        predictions.append(prediction)
        if prediction == label:
            correct_count += 1
        if label == protected_class:
            protected_total += 1
            if prediction == label:
                protected_correct += 1
    if protected_total == 0:
        raise BackendError("PYTORCH_EVALUATION_INVALID", "protected class is absent")
    return ExactEvaluation(
        correct_count=correct_count,
        example_count=len(labels),
        protected_correct_count=protected_correct,
        protected_example_count=protected_total,
        predictions=tuple(predictions),
    )


def _validate_training_manifest_bindings(request: BackendRequest) -> None:
    manifest = fixed_training_manifest()
    if _canonical_hash(manifest) != request.training_data_manifest_hash:
        raise BackendError("PYTORCH_TRAINING_DATA_MISMATCH", "training-data manifest hash mismatch")
    if manifest["heldout_feature_manifest_hash"] != request.heldout_feature_manifest_hash:
        raise BackendError("PYTORCH_HELDOUT_FEATURE_MISMATCH", "held-out feature hash mismatch")


def _snapshot_predecessor(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for relative_path in (ARCHITECTURE_PATH, WEIGHTS_MANIFEST_PATH, MODEL_WEIGHT_PATH, MODEL_BIAS_PATH):
        path = root / relative_path
        if not path.is_file():
            raise BackendError("PYTORCH_PREDECESSOR_INVALID", f"missing predecessor file: {relative_path}")
        snapshot[relative_path] = _sha256(path.read_bytes())
    return snapshot


def _directory_tree_hash(root: Path) -> str:
    lines: list[bytes] = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    ):
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        lines.append(
            relative.encode("utf-8")
            + b"\0"
            + b"0644"
            + b"\0"
            + str(len(content)).encode("ascii")
            + b"\0"
            + _sha256(content).encode("ascii")
            + b"\n"
        )
    return _sha256(TREE_HASH_DOMAIN + b"".join(lines))


def _tensor_file_bytes(root: Path) -> int:
    return sum(
        (root / relative).stat().st_size
        for relative in (MODEL_WEIGHT_PATH, MODEL_BIAS_PATH)
    )


def _require_time_budget(start_ns: int, policy: PilotPolicy) -> None:
    elapsed_ns = time.monotonic_ns() - start_ns
    if elapsed_ns > policy.time_budget_millis * 1_000_000:
        raise BackendError("PYTORCH_TIME_BUDGET_EXCEEDED", "training exceeded the fixed time budget")


def _normalize_weights(weights: Sequence[Sequence[int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    if len(weights) != 2 or any(len(row) != 2 for row in weights):
        raise BackendError("PYTORCH_MODEL_INVALID", "weight matrix must be 2x2")
    rows = tuple(tuple(_signed_int64(value, "weight") for value in row) for row in weights)
    return cast(tuple[tuple[int, int], tuple[int, int]], rows)


def _normalize_bias(bias: Sequence[int]) -> tuple[int, int]:
    if len(bias) != 2:
        raise BackendError("PYTORCH_MODEL_INVALID", "bias vector must have length two")
    values = tuple(_signed_int64(value, "bias") for value in bias)
    return cast(tuple[int, int], values)


def _pack_int64(values: Sequence[int] | object) -> bytes:
    return b"".join(struct.pack("<q", _signed_int64(value, "tensor")) for value in cast(object, values))


def _signed_int64(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BackendError("PYTORCH_MODEL_INVALID", f"{path} must be an integer")
    if value < -(2**63) or value > 2**63 - 1:
        raise BackendError("PYTORCH_MODEL_INVALID", f"{path} is outside int64 range")
    return value


def _canonicalize(value: object) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise BackendError("PYTORCH_CANONICALIZATION_FAILED", "native floats are forbidden in JSON")
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise BackendError("PYTORCH_CANONICALIZATION_FAILED", "JSON keys must be strings")
            normalized = unicodedata.normalize("NFC", key)
            if normalized in result:
                raise BackendError("PYTORCH_CANONICALIZATION_FAILED", "keys collide after normalization")
            result[normalized] = _canonicalize(item)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonicalize(item) for item in value]
    raise BackendError(
        "PYTORCH_CANONICALIZATION_FAILED",
        f"unsupported JSON value type: {type(value).__name__}",
    )


def _canonical_bytes(value: object) -> bytes:
    normalized = _canonicalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_hash(value: object) -> str:
    return _sha256(CANONICAL_JSON_HASH_DOMAIN + _canonical_bytes(value))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def _write_canonical_json(path: Path, value: object) -> None:
    _write_bytes(path, _canonical_bytes(value))


def _load_canonical_json(path: Path) -> object:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise BackendError("PYTORCH_JSON_INVALID", "UTF-8 BOM is forbidden")
    try:
        parsed = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise BackendError("PYTORCH_JSON_INVALID", f"invalid canonical JSON: {exc}") from exc
    if _canonical_bytes(parsed) != data:
        raise BackendError("PYTORCH_JSON_NONCANONICAL", f"noncanonical JSON file: {path}")
    return parsed


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_float(text: str) -> object:
    raise ValueError(f"native JSON float is forbidden: {text}")


def _reject_constant(text: str) -> object:
    raise ValueError(f"nonfinite JSON value is forbidden: {text}")


def _strict_object(value: object, fields: set[str], path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be an object")
    observed = set(value)
    if observed != fields:
        missing = sorted(fields - observed)
        unknown = sorted(observed - fields)
        raise BackendError(
            "PYTORCH_SCHEMA_MALFORMED",
            f"{path} fields differ; missing={missing}, unknown={unknown}",
        )
    return cast(dict[str, object], value)


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be a nonempty string")
    return unicodedata.normalize("NFC", value)


def _integer(value: object, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be an integer")
    if minimum is not None and value < minimum:
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} is below its minimum")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be a Boolean")
    return value


def _hash256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be lowercase SHA-256")
    return text


def _require_exact(value: object, expected: object, path: str) -> None:
    if value != expected:
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must equal {expected!r}")


def _matrix_of_ints(value: object, path: str, *, columns: int) -> Sequence[Sequence[int]]:
    if not isinstance(value, list):
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be an array")
    rows: list[Sequence[int]] = []
    for index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != columns:
            raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path}[{index}] has wrong shape")
        rows.append(tuple(_integer(item, f"{path}[{index}][]") for item in row))
    return tuple(rows)


def _array_of_ints(value: object, path: str) -> Sequence[int]:
    if not isinstance(value, list):
        raise BackendError("PYTORCH_SCHEMA_MALFORMED", f"{path} must be an array")
    return tuple(_integer(item, f"{path}[{index}]") for index, item in enumerate(value))


def _success_payload(payload: object) -> bytes:
    return _canonical_bytes(
        {
            "schema_id": "runtime.pytorch_pilot_process_result.v1",
            "verdict": "success",
            "reason_codes": [],
            "payload": payload,
        }
    )


def _failure_payload(error: BackendError) -> bytes:
    return _canonical_bytes(
        {
            "schema_id": "runtime.pytorch_pilot_process_result.v1",
            "verdict": error.verdict,
            "reason_codes": [error.code],
            "detail_hash": _sha256(error.detail.encode("utf-8")),
        }
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic CPU-only PyTorch proposal pilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("initialize-predecessor")
    initialize.add_argument("--output-root", type=Path, required=True)

    propose = subparsers.add_parser("propose")
    propose.add_argument("--request", type=Path, required=True)
    propose.add_argument("--predecessor-root", type=Path, required=True)
    propose.add_argument("--output-root", type=Path, required=True)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--proposal-root", type=Path, required=True)
    evaluate.add_argument("--evaluation-data", type=Path, required=True)
    evaluate.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "initialize-predecessor":
            manifest = initialize_predecessor_model(args.output_root)
            sys.stdout.buffer.write(_success_payload(manifest) + b"\n")
            return 0
        if args.command == "propose":
            request_value = _load_canonical_json(args.request)
            request = BackendRequest.from_json(request_value)
            artifacts = run_proposal_backend(
                request,
                args.predecessor_root,
                args.output_root,
            )
            sys.stdout.buffer.write(
                _success_payload(
                    {
                        "proposal_hash": artifacts.proposal["proposal_hash"],
                        "phase6_selection_hash": _canonical_hash(artifacts.phase6_selection),
                        "output_manifest_hash": _canonical_hash(
                            _load_canonical_json(artifacts.output_root / "manifest.json")
                        ),
                    }
                )
                + b"\n"
            )
            return 0
        if args.command == "evaluate":
            evaluation_value = _load_canonical_json(args.evaluation_data)
            artifacts = evaluate_proposal_exact(
                args.proposal_root,
                evaluation_value,
                args.out,
            )
            sys.stdout.buffer.write(_success_payload(artifacts.result) + b"\n")
            return 0
        raise BackendError("PYTORCH_INTERNAL_ERROR", "unknown command")
    except BackendError as error:
        sys.stdout.buffer.write(_failure_payload(error) + b"\n")
        return 3 if error.verdict == "indeterminate" else 2
    except (MemoryError, OSError, RuntimeError, ValueError) as exc:
        error = BackendError(
            "PYTORCH_PROCESS_FAILURE",
            f"{type(exc).__name__}: {exc}",
            "indeterminate",
        )
        sys.stdout.buffer.write(_failure_payload(error) + b"\n")
        return 3


__all__ = [
    "BackendError",
    "BackendRequest",
    "EvaluationArtifacts",
    "PilotPolicy",
    "ProposalArtifacts",
    "default_policy",
    "evaluate_model_root_exact",
    "evaluate_proposal_exact",
    "fixed_heldout_evaluation_data",
    "fixed_training_manifest",
    "initialize_predecessor_model",
    "make_default_request",
    "run_proposal_backend",
]


if __name__ == "__main__":
    raise SystemExit(main())
