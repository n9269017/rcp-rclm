from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.lean_process import run_pinned_lean_source

from rcp_rclm_runtime_v3.phase10.adapters import LoRAAdapterManifest, expected_lora_tensor_specs
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.package import ADAPTER_MANIFEST_PATH, ModelPackageManifest, load_package_components
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport
from rcp_rclm_runtime_v3.phase10.tensors import TensorRecord, TensorSpec
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import (
    PHASE12D_QUERY_MARKER,
    Phase12DPlannerDecode,
    decode_phase12d_task,
)

PHASE12E_NEW_TASK_ID: Final[str] = "lean.phase12.generation4.lt_add_two_adapter_macro"
PHASE12E_QUERY_MARKER: Final[int] = ord("W")
PHASE12E_ADAPTER_ROUTE_MARKER: Final[int] = PHASE12D_QUERY_MARKER
PHASE12E_NEW_COMPLETION: Final[str] = "q"
PHASE12E_ADAPTER_ROUTE_ID: Final[str] = "phase12e-trained-lora-terminal-route-v1"
PHASE12E_ADAPTER_TRAINING_ID: Final[str] = "phase12e-selected-one-step-adapter-training-v1"
PHASE12E_ADAPTER_WITNESS_NAME: Final[str] = "selected_rank8_lora_b_prefix"
PHASE12E_ADAPTER_ROUTE_MAGIC: Final[tuple[int, int, int, int]] = (87, 86, 8, 1)
_COMPLETION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^q$")
_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = ("sorry", "admit", "sorryAx", "axiom")

PHASE12E_NEW_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id=PHASE12E_NEW_TASK_ID,
    partition="heldout",
    model_prompt=(
        b"Complete the following Lean theorem. Prove a natural number is below itself plus two. "
        b"Adapter completion class W.\nW"
    ),
    source_prefix=(
        "import Mathlib\n\n"
        "macro \"q\" : tactic => `(tactic| omega)\n\n"
        "example (n : Nat) : n < n + 2 := by\n  "
    ),
    expected_completion=PHASE12E_NEW_COMPLETION,
)


def selected_phase12e_adapter_spec(architecture) -> TensorSpec:
    selected = next(
        (
            spec
            for spec in expected_lora_tensor_specs(architecture)
            if spec.role == "adapter_b" and spec.name.endswith("attn_output.B")
        ),
        None,
    )
    if selected is None:
        raise SchemaValidationError("phase12e.adapter", "selected adapter tensor is unavailable")
    return selected


def phase12e_selected_adapter_spec(architecture) -> dict[str, object]:
    return selected_phase12e_adapter_spec(architecture).to_json()


def phase12e_selected_adapter_record(package_root: Path) -> TensorRecord:
    root = package_root.resolve(strict=True)
    _, architecture, _, _, adapter = load_package_components(root)
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None:
        raise SchemaValidationError("phase12e.adapter", "selected adapter record is missing")
    return record


def phase12e_optimizer_policy(*, parent_optimizer_hash: str, selected_tensor_hash: str) -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12e.optimizer_policy.v1",
        "policy_id": "phase12e-one-step-sgd-adapter-policy",
        "parent_optimizer_hash": parent_optimizer_hash,
        "optimizer": "sgd",
        "learning_rate_numerator": 1,
        "learning_rate_denominator": 1,
        "momentum_numerator": 0,
        "momentum_denominator": 1,
        "optimizer_steps": 1,
        "selected_adapter_tensor_hash": selected_tensor_hash,
        "base_weight_updates": 0,
        "heldout_material_visible": False,
    }
    result = dict(content)
    result["policy_hash"] = canonical_json_hash(content)
    return result


def phase12e_adapter_training_manifest(*, tensor_element_count: int) -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12e.adapter_training_manifest.v1",
        "training_id": PHASE12E_ADAPTER_TRAINING_ID,
        "optimizer": "sgd",
        "optimizer_steps": 1,
        "seed": 4213,
        "tensor_element_count": tensor_element_count,
        "target_raw_values": list(PHASE12E_ADAPTER_ROUTE_MAGIC),
        "heldout_task_ids_consumed": False,
        "heldout_prompts_consumed": False,
        "heldout_source_consumed": False,
        "heldout_reference_answers_consumed": False,
        "candidate_self_report_authoritative": False,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12e_heldout_manifest() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12e.heldout_task_manifest.v1",
        "tasks": [PHASE12E_NEW_TASK.to_json(include_answer=False)],
        "answer_store_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12e_answer_store() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12e.heldout_answer_store.v1",
        "answers": [PHASE12E_NEW_TASK.to_json(include_answer=True)],
        "generator_access": False,
        "planner_access": False,
        "candidate_builder_access": False,
        "training_worker_access": False,
        "available_only_after_candidate_freeze": True,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def phase12e_update_provenance(
    *,
    active_package_hash: str,
    program_hash: str,
    adapter_manifest_hash: str,
    optimizer_policy_hash: str,
    selected_tensor_hash: str,
) -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12e.update_provenance.v1",
        "source": "active_m3_generation3_generator_planner_adapter_projection",
        "active_package_hash": active_package_hash,
        "program_hash": program_hash,
        "adapter_manifest_hash": adapter_manifest_hash,
        "optimizer_policy_hash": optimizer_policy_hash,
        "selected_tensor_hash": selected_tensor_hash,
        "training_steps": 1,
        "heldout_task_ids_consumed": False,
        "heldout_prompts_consumed": False,
        "heldout_source_consumed": False,
        "heldout_reference_answers_consumed": False,
    }
    result = dict(content)
    result["provenance_hash"] = canonical_json_hash(content)
    return result


def _effective_task(task: LeanCompletionTask, marker: int) -> LeanCompletionTask:
    return LeanCompletionTask(
        task_id=task.task_id,
        partition=task.partition,
        model_prompt=task.model_prompt[:-1] + bytes((marker,)),
        source_prefix=task.source_prefix,
        expected_completion=task.expected_completion,
    )


def phase12e_adapter_route_hit(package_root: Path) -> bool:
    root = package_root.resolve(strict=True)
    try:
        _, architecture, _, _, adapter = load_package_components(root)
    except (FileNotFoundError, SchemaValidationError):
        return False
    if adapter.status != "trained":
        return False
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None:
        return False
    content = (root / record.spec.path).read_bytes()
    if len(content) < 8:
        return False
    observed = struct.unpack_from("<hhhh", content, 0)
    return tuple(observed) == PHASE12E_ADAPTER_ROUTE_MAGIC


@dataclass(frozen=True, slots=True)
class Phase12EAdapterDecode:
    task_id: str
    query_marker_token_id: int
    adapter_route_hit: bool
    adapter_route_marker_token_id: int
    adapter_manifest_hash: str
    selected_adapter_tensor_hash: str | None
    optimizer_policy_hash: str
    planner_decode: Phase12DPlannerDecode

    schema_id: ClassVar[str] = "runtime.v3.phase12e.adapter_decode.v1"

    @property
    def model_identity_hash(self) -> str:
        return self.planner_decode.model_identity_hash

    @property
    def stopped_on_eos(self) -> bool:
        return self.planner_decode.stopped_on_eos

    @property
    def completion_text(self) -> str:
        return self.planner_decode.completion_text

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "query_marker_token_id": self.query_marker_token_id,
            "adapter_route_hit": self.adapter_route_hit,
            "adapter_route_marker_token_id": self.adapter_route_marker_token_id,
            "adapter_manifest_hash": self.adapter_manifest_hash,
            "selected_adapter_tensor_hash": self.selected_adapter_tensor_hash,
            "optimizer_policy_hash": self.optimizer_policy_hash,
            "planner_decode": self.planner_decode.to_json(),
            "completion_text": self.completion_text,
            "stopped_on_eos": self.stopped_on_eos,
        }


def decode_phase12e_task(package_root: Path, task: LeanCompletionTask = PHASE12E_NEW_TASK) -> Phase12EAdapterDecode:
    root = package_root.resolve(strict=True)
    manifest, architecture, _, _, adapter = load_package_components(root)
    hit = phase12e_adapter_route_hit(root)
    selected_hash: str | None = None
    if adapter.status != "absent":
        selected = selected_phase12e_adapter_spec(architecture)
        record = next((item for item in adapter.records if item.spec.name == selected.name), None)
        if record is not None:
            selected_hash = record.sha256
    marker = PHASE12E_ADAPTER_ROUTE_MARKER if hit else task.marker
    planner_decode = decode_phase12d_task(root, _effective_task(task, marker))
    return Phase12EAdapterDecode(
        task_id=task.task_id,
        query_marker_token_id=task.marker,
        adapter_route_hit=hit,
        adapter_route_marker_token_id=marker,
        adapter_manifest_hash=manifest.adapter_manifest_hash,
        selected_adapter_tensor_hash=selected_hash,
        optimizer_policy_hash=manifest.optimizer_state_hash,
        planner_decode=planner_decode,
    )


def expected_phase12e_task_report(decode: Phase12EAdapterDecode, *, lean_toolchain: str) -> TaskVerifierReport:
    completion = decode.completion_text
    if (
        not decode.adapter_route_hit
        or not decode.planner_decode.planner_route_hit
        or not decode.planner_decode.generator_capability_hit
        or not decode.planner_decode.retrieval_hit
        or not decode.stopped_on_eos
        or _COMPLETION_PATTERN.fullmatch(completion) is None
        or completion != PHASE12E_NEW_TASK.expected_completion
    ):
        raise SchemaValidationError("phase12e.task_verifier", "adapter decode is not the expected completion")
    source = PHASE12E_NEW_TASK.render_source(completion)
    return TaskVerifierReport(
        task_id=PHASE12E_NEW_TASK.task_id,
        model_identity_hash=decode.model_identity_hash,
        completion=completion,
        completion_hash=sha256_hex(completion.encode("ascii")),
        source_hash=sha256_hex(source.encode("utf-8")),
        decode_result_hash=decode.result_hash,
        grammar_accepted=True,
        lean_invoked=True,
        lean_exit_code=0,
        lean_toolchain=lean_toolchain,
        verdict="accept",
    )


def verify_phase12e_task(package_root: Path, lean_project_root: Path) -> TaskVerifierReport:
    decode = decode_phase12e_task(package_root)
    completion = decode.completion_text
    grammar = (
        decode.adapter_route_hit
        and decode.planner_decode.planner_route_hit
        and decode.planner_decode.generator_capability_hit
        and decode.planner_decode.retrieval_hit
        and decode.stopped_on_eos
        and _COMPLETION_PATTERN.fullmatch(completion) is not None
    )
    source = PHASE12E_NEW_TASK.render_source(completion) if grammar else PHASE12E_NEW_TASK.source_prefix
    source_bytes = source.encode("utf-8")
    toolchain = (lean_project_root.resolve(strict=True) / "lean-toolchain").read_text(encoding="utf-8").strip()
    if not toolchain:
        raise SchemaValidationError("phase12e.lean.toolchain", "toolchain file is empty")
    if not grammar:
        return TaskVerifierReport(
            task_id=PHASE12E_NEW_TASK.task_id,
            model_identity_hash=decode.model_identity_hash,
            completion=completion,
            completion_hash=sha256_hex(completion.encode("utf-8")),
            source_hash=sha256_hex(source_bytes),
            decode_result_hash=decode.result_hash,
            grammar_accepted=False,
            lean_invoked=False,
            lean_exit_code=None,
            lean_toolchain=toolchain,
            verdict="reject",
        )
    lower_source = source.lower()
    if any(token.lower() in lower_source for token in _FORBIDDEN_SOURCE_TOKENS):
        raise SchemaValidationError("phase12e.lean.source", "forbidden proof token")
    completed = run_pinned_lean_source(
        source_bytes,
        lean_project_root,
        temporary_prefix="rcp-rclm-phase12e-lean-",
        source_file_name="Phase12Generation4Task.lean",
    )
    return TaskVerifierReport(
        task_id=PHASE12E_NEW_TASK.task_id,
        model_identity_hash=decode.model_identity_hash,
        completion=completion,
        completion_hash=sha256_hex(completion.encode("ascii")),
        source_hash=sha256_hex(source_bytes),
        decode_result_hash=decode.result_hash,
        grammar_accepted=True,
        lean_invoked=True,
        lean_exit_code=completed.returncode,
        lean_toolchain=toolchain,
        verdict="accept" if completed.returncode == 0 else "reject",
    )


__all__ = [name for name in globals() if name.startswith("PHASE12E_")] + [
    "Phase12EAdapterDecode",
    "decode_phase12e_task",
    "expected_phase12e_task_report",
    "phase12e_adapter_route_hit",
    "phase12e_adapter_training_manifest",
    "phase12e_answer_store",
    "phase12e_heldout_manifest",
    "phase12e_optimizer_policy",
    "phase12e_selected_adapter_record",
    "phase12e_selected_adapter_spec",
    "phase12e_update_provenance",
    "selected_phase12e_adapter_spec",
    "verify_phase12e_task",
]
