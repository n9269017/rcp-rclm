from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.lean_process import run_pinned_lean_source

from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.sparse_profile import DecodeResult, decode_completion
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport


PHASE12B_NEW_TASK_ID: Final[str] = "lean.phase12.generation1.le_refl_macro"
PHASE12B_NEW_MARKER: Final[int] = ord("T")
PHASE12B_NEW_COMPLETION: Final[bytes] = b"q"
PHASE12B_DATA_SELECTION: Final[str] = "phase12_generation1_weight_training"
_COMPLETION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^q$")
_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = ("sorry", "admit", "sorryAx", "axiom")

PHASE12B_NEW_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id=PHASE12B_NEW_TASK_ID,
    partition="heldout",
    model_prompt=(
        b"Complete the following Lean theorem. Prove reflexivity of natural-number order. "
        b"Completion class T.\nT"
    ),
    source_prefix=(
        "import Mathlib\n\n"
        "macro \"q\" : tactic => `(tactic| omega)\n\n"
        "example (n : Nat) : n <= n := by\n  "
    ),
    expected_completion=PHASE12B_NEW_COMPLETION.decode("ascii"),
)


def phase12b_new_chain() -> Sequence[tuple[int, int]]:
    return (
        (PHASE12B_NEW_MARKER, PHASE12B_NEW_COMPLETION[0]),
        (PHASE12B_NEW_COMPLETION[0], EOS_TOKEN_ID),
    )


def phase12b_training_manifest() -> dict[str, object]:
    pairs = tuple(sorted(phase12b_new_chain(), key=lambda item: (item[0], item[1])))
    content = {
        "schema_id": "runtime.v3.phase12b.training_data_manifest.v1",
        "selection_id": PHASE12B_DATA_SELECTION,
        "task_class": "lean_theorem_completion_v1",
        "examples": [
            {
                "example_id": "phase12.train.order_reflexivity_macro",
                "prompt_sha256": sha256_hex(
                    b"Generic Lean order reflexivity example. Completion class T.\nT"
                ),
                "completion_sha256": sha256_hex(PHASE12B_NEW_COMPLETION),
                "marker_token_id": PHASE12B_NEW_MARKER,
                "completion_token_ids": list(PHASE12B_NEW_COMPLETION),
            }
        ],
        "transition_pairs": [
            {"current_token_id": current, "target_token_id": target}
            for current, target in pairs
        ],
        "heldout_task_ids_visible": False,
        "heldout_prompts_visible": False,
        "heldout_source_visible": False,
        "heldout_reference_answers_visible": False,
        "persistent_curriculum_policy_changed": False,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12b_heldout_manifest() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12b.heldout_task_manifest.v1",
        "tasks": [PHASE12B_NEW_TASK.to_json(include_answer=False)],
        "answer_store_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12b_answer_store() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12b.heldout_answer_store.v1",
        "answers": [PHASE12B_NEW_TASK.to_json(include_answer=True)],
        "generator_access": False,
        "planner_access": False,
        "training_backend_access": False,
        "available_only_after_candidate_freeze": True,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def expected_phase12b_task_report(
    decode: DecodeResult,
    *,
    lean_toolchain: str,
) -> TaskVerifierReport:
    completion = decode.completion_text
    if (
        not decode.stopped_on_eos
        or _COMPLETION_PATTERN.fullmatch(completion) is None
        or completion != PHASE12B_NEW_TASK.expected_completion
    ):
        raise SchemaValidationError("phase12b.task_verifier", "decode is not the expected completion")
    source = PHASE12B_NEW_TASK.render_source(completion)
    return TaskVerifierReport(
        task_id=PHASE12B_NEW_TASK.task_id,
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


def verify_phase12b_task(
    package_root: Path,
    lean_project_root: Path,
) -> TaskVerifierReport:
    decode = decode_completion(package_root.resolve(strict=True), PHASE12B_NEW_TASK.model_prompt)
    try:
        completion = decode.completion_text
    except (UnicodeDecodeError, SchemaValidationError):
        completion = ""
    grammar = (
        decode.stopped_on_eos
        and _COMPLETION_PATTERN.fullmatch(completion) is not None
    )
    source = (
        PHASE12B_NEW_TASK.render_source(completion)
        if grammar
        else PHASE12B_NEW_TASK.source_prefix
    )
    source_bytes = source.encode("utf-8")
    toolchain_path = lean_project_root.resolve(strict=True) / "lean-toolchain"
    toolchain = toolchain_path.read_text(encoding="utf-8").strip()
    if not toolchain:
        raise SchemaValidationError("phase12b.lean.toolchain", "toolchain file is empty")
    if not grammar:
        return TaskVerifierReport(
            task_id=PHASE12B_NEW_TASK.task_id,
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
        raise SchemaValidationError("phase12b.lean.source", "forbidden proof token")
    completed = run_pinned_lean_source(
        source_bytes,
        lean_project_root,
        temporary_prefix="rcp-rclm-phase12b-lean-",
        source_file_name="Phase12Generation1Task.lean",
    )
    if completed.returncode == 0 and (completed.stdout or completed.stderr):
        raise SchemaValidationError(
            "phase12b.lean.output",
            "successful selected task must produce empty stdout and stderr",
        )
    return TaskVerifierReport(
        task_id=PHASE12B_NEW_TASK.task_id,
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


__all__ = [
    "PHASE12B_DATA_SELECTION",
    "PHASE12B_NEW_COMPLETION",
    "PHASE12B_NEW_MARKER",
    "PHASE12B_NEW_TASK",
    "PHASE12B_NEW_TASK_ID",
    "expected_phase12b_task_report",
    "phase12b_answer_store",
    "phase12b_heldout_manifest",
    "phase12b_new_chain",
    "phase12b_training_manifest",
    "verify_phase12b_task",
]
