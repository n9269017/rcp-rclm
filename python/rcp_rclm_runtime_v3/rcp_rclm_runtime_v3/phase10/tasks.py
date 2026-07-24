from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.lean_process import run_pinned_lean_source
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.sparse_profile import DecodeResult, decode_completion

_COMPLETION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(rfl|omega)$")
_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = ("sorry", "admit", "sorryAx", "axiom")


@dataclass(frozen=True, slots=True)
class TaskVerifierReport:
    task_id: str
    model_identity_hash: str
    completion: str
    completion_hash: str
    source_hash: str
    decode_result_hash: str
    grammar_accepted: bool
    lean_invoked: bool
    lean_exit_code: int | None
    lean_toolchain: str
    verdict: str

    schema_id: ClassVar[str] = "runtime.v3.phase10.lean_task_verifier_report.v1"

    def __post_init__(self) -> None:
        if self.verdict not in {"accept", "reject"}:
            raise SchemaValidationError("phase10.task_verifier.verdict", "unsupported verdict")
        if self.verdict == "accept":
            if not self.grammar_accepted or not self.lean_invoked or self.lean_exit_code != 0:
                raise SchemaValidationError(
                    "phase10.task_verifier", "accepted report requires successful Lean invocation"
                )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @property
    def solved(self) -> bool:
        return self.verdict == "accept"

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "model_identity_hash": self.model_identity_hash,
            "completion": self.completion,
            "completion_hash": self.completion_hash,
            "source_hash": self.source_hash,
            "decode_result_hash": self.decode_result_hash,
            "grammar_accepted": self.grammar_accepted,
            "lean_invoked": self.lean_invoked,
            "lean_exit_code": self.lean_exit_code,
            "lean_toolchain": self.lean_toolchain,
            "verdict": self.verdict,
            "verifier_kind": "pinned_lean_theorem_verifier_v1",
            "candidate_self_report_consumed": False,
        }


def _completion_grammar(completion: str) -> bool:
    return _COMPLETION_PATTERN.fullmatch(completion) is not None


def _read_toolchain(project_root: Path) -> str:
    path = project_root.resolve(strict=True) / "lean-toolchain"
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise SchemaValidationError("phase10.lean.toolchain", "toolchain file is empty")
    return value


def verify_decoded_task(
    package_root: Path,
    task: LeanCompletionTask,
    lean_project_root: Path,
) -> TaskVerifierReport:
    decode = decode_completion(package_root, task.model_prompt)
    try:
        completion = decode.completion_text
    except (UnicodeDecodeError, SchemaValidationError):
        completion = ""
    grammar = decode.stopped_on_eos and _completion_grammar(completion)
    source = task.render_source(completion) if grammar else task.source_prefix
    source_bytes = source.encode("utf-8")
    source_hash = sha256_hex(source_bytes)
    toolchain = _read_toolchain(lean_project_root)
    if not grammar:
        return TaskVerifierReport(
            task_id=task.task_id,
            model_identity_hash=decode.model_identity_hash,
            completion=completion,
            completion_hash=sha256_hex(completion.encode("utf-8")),
            source_hash=source_hash,
            decode_result_hash=decode.result_hash,
            grammar_accepted=False,
            lean_invoked=False,
            lean_exit_code=None,
            lean_toolchain=toolchain,
            verdict="reject",
        )
    lower_source = source.lower()
    if any(token.lower() in lower_source for token in _FORBIDDEN_SOURCE_TOKENS):
        raise SchemaValidationError("phase10.lean.source", "forbidden proof token")
    completed = run_pinned_lean_source(
        source_bytes,
        lean_project_root,
        temporary_prefix="rcp-rclm-phase10-lean-",
        source_file_name="Phase10Task.lean",
    )
    if completed.returncode == 0 and (completed.stdout or completed.stderr):
        raise SchemaValidationError(
            "phase10.lean.output", "successful selected task must produce empty stdout and stderr"
        )
    verdict = "accept" if completed.returncode == 0 else "reject"
    return TaskVerifierReport(
        task_id=task.task_id,
        model_identity_hash=decode.model_identity_hash,
        completion=completion,
        completion_hash=sha256_hex(completion.encode("ascii")),
        source_hash=source_hash,
        decode_result_hash=decode.result_hash,
        grammar_accepted=True,
        lean_invoked=True,
        lean_exit_code=completed.returncode,
        lean_toolchain=toolchain,
        verdict=verdict,
    )


def expected_success_report(
    decode: DecodeResult,
    task: LeanCompletionTask,
    *,
    lean_toolchain: str,
) -> TaskVerifierReport:
    completion = decode.completion_text
    if not decode.stopped_on_eos or not _completion_grammar(completion):
        raise SchemaValidationError("phase10.task_verifier", "decode is not a valid completion")
    source = task.render_source(completion)
    return TaskVerifierReport(
        task_id=task.task_id,
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


__all__ = [
    "TaskVerifierReport",
    "expected_success_report",
    "verify_decoded_task",
]
