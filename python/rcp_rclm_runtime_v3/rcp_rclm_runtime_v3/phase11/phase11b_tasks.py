from __future__ import annotations

import re
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.sparse_profile import DecodeResult, decode_completion
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport
from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    PHASE11B_DATA_SELECTION_ALPHA,
    PHASE11B_DATA_SELECTION_BETA,
    PHASE11B_NEW_COMPLETION,
    PHASE11B_NEW_MARKER,
    PHASE11B_NEW_TASK_ID,
)

_COMPLETION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^z$")
_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = ("sorry", "admit", "sorryAx", "axiom")

PHASE11B_NEW_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id=PHASE11B_NEW_TASK_ID,
    partition="heldout",
    model_prompt=(
        b"Complete the following Lean theorem. Simplify natural-number addition by zero. "
        b"Completion class S.\nS"
    ),
    source_prefix=(
        "import Mathlib\n\n"
        "macro \"z\" : tactic => `(tactic| simp)\n\n"
        "example (n : Nat) : n + 0 = n := by\n  "
    ),
    expected_completion=PHASE11B_NEW_COMPLETION.decode("ascii"),
)


def phase11b_new_chain() -> Sequence[tuple[int, int]]:
    return (
        (PHASE11B_NEW_MARKER, PHASE11B_NEW_COMPLETION[0]),
        (PHASE11B_NEW_COMPLETION[0], EOS_TOKEN_ID),
    )


def phase11b_alpha_pairs() -> Sequence[tuple[int, int]]:
    return tuple(
        sorted(
            {
                *phase11b_new_chain(),
                (ord("R"), ord("a")),
            },
            key=lambda item: (item[0], item[1]),
        )
    )


def phase11b_beta_pairs() -> Sequence[tuple[int, int]]:
    return tuple(sorted(phase11b_new_chain(), key=lambda item: (item[0], item[1])))


def _training_examples(selection_id: str) -> Sequence[dict[str, object]]:
    examples: list[dict[str, object]] = [
        {
            "example_id": "phase11.train.simplify.successor_zero",
            "prompt_sha256": sha256_hex(
                b"Generic Lean simplification example. Completion class S.\nS"
            ),
            "completion_sha256": sha256_hex(PHASE11B_NEW_COMPLETION),
            "marker_token_id": PHASE11B_NEW_MARKER,
            "completion_token_ids": list(PHASE11B_NEW_COMPLETION),
        }
    ]
    if selection_id == PHASE11B_DATA_SELECTION_ALPHA:
        examples.append(
            {
                "example_id": "phase11.train.alpha.conflicting_reflexive_marker",
                "prompt_sha256": sha256_hex(
                    b"Alpha curriculum conflict probe. Completion class R.\nR"
                ),
                "completion_sha256": sha256_hex(b"a"),
                "marker_token_id": ord("R"),
                "completion_token_ids": [ord("a")],
            }
        )
    return tuple(sorted(examples, key=lambda item: str(item["example_id"]).encode("utf-8")))


def phase11b_training_manifest(selection_id: str) -> dict[str, object]:
    if selection_id == PHASE11B_DATA_SELECTION_ALPHA:
        pairs = phase11b_alpha_pairs()
    elif selection_id == PHASE11B_DATA_SELECTION_BETA:
        pairs = phase11b_beta_pairs()
    else:
        raise SchemaValidationError("phase11b.curriculum", "unsupported data selection")
    content = {
        "schema_id": "runtime.v3.phase11b.training_data_manifest.v1",
        "selection_id": selection_id,
        "task_class": "lean_theorem_completion_v1",
        "examples": list(_training_examples(selection_id)),
        "transition_pairs": [
            {"current_token_id": current, "target_token_id": target}
            for current, target in pairs
        ],
        "heldout_task_ids_visible": False,
        "heldout_prompts_visible": False,
        "heldout_source_visible": False,
        "heldout_reference_answers_visible": False,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase11b_heldout_manifest() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase11b.heldout_task_manifest.v1",
        "tasks": [PHASE11B_NEW_TASK.to_json(include_answer=False)],
        "answer_store_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase11b_answer_store() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase11b.heldout_answer_store.v1",
        "answers": [PHASE11B_NEW_TASK.to_json(include_answer=True)],
        "generator_access": False,
        "planner_access": False,
        "training_backend_access": False,
        "available_only_after_candidate_freeze": True,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def expected_phase11b_task_report(
    decode: DecodeResult,
    *,
    lean_toolchain: str,
) -> TaskVerifierReport:
    completion = decode.completion_text
    if (
        not decode.stopped_on_eos
        or _COMPLETION_PATTERN.fullmatch(completion) is None
        or completion != PHASE11B_NEW_TASK.expected_completion
    ):
        raise SchemaValidationError("phase11b.task_verifier", "decode is not the expected completion")
    source = PHASE11B_NEW_TASK.render_source(completion)
    return TaskVerifierReport(
        task_id=PHASE11B_NEW_TASK.task_id,
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


def verify_phase11b_task(
    package_root: Path,
    lean_project_root: Path,
) -> TaskVerifierReport:
    decode = decode_completion(package_root.resolve(strict=True), PHASE11B_NEW_TASK.model_prompt)
    try:
        completion = decode.completion_text
    except (UnicodeDecodeError, SchemaValidationError):
        completion = ""
    grammar = (
        decode.stopped_on_eos
        and _COMPLETION_PATTERN.fullmatch(completion) is not None
    )
    source = (
        PHASE11B_NEW_TASK.render_source(completion)
        if grammar
        else PHASE11B_NEW_TASK.source_prefix
    )
    source_bytes = source.encode("utf-8")
    toolchain_path = lean_project_root.resolve(strict=True) / "lean-toolchain"
    toolchain = toolchain_path.read_text(encoding="utf-8").strip()
    if not toolchain:
        raise SchemaValidationError("phase11b.lean.toolchain", "toolchain file is empty")
    if not grammar:
        return TaskVerifierReport(
            task_id=PHASE11B_NEW_TASK.task_id,
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
        raise SchemaValidationError("phase11b.lean.source", "forbidden proof token")
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11b-lean-") as temporary:
        source_path = Path(temporary) / "Phase11Task.lean"
        source_path.write_bytes(source_bytes)
        completed = subprocess.run(
            ["lake", "env", "lean", str(source_path)],
            cwd=lean_project_root.resolve(strict=True),
            capture_output=True,
            check=False,
            timeout=120,
        )
    if completed.returncode == 0 and (completed.stdout or completed.stderr):
        raise SchemaValidationError(
            "phase11b.lean.output",
            "successful selected task must produce empty stdout and stderr",
        )
    return TaskVerifierReport(
        task_id=PHASE11B_NEW_TASK.task_id,
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
    "PHASE11B_NEW_TASK",
    "expected_phase11b_task_report",
    "phase11b_alpha_pairs",
    "phase11b_answer_store",
    "phase11b_beta_pairs",
    "phase11b_heldout_manifest",
    "phase11b_new_chain",
    "phase11b_training_manifest",
    "verify_phase11b_task",
]
