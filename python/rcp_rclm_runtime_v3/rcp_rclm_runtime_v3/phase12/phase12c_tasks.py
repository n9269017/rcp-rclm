from __future__ import annotations

import re
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import DecodeResult, decode_completion
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import (
    PHASE12B_NEW_MARKER,
    PHASE12B_NEW_TASK_ID,
)

PHASE12C_NEW_TASK_ID: Final[str] = "lean.phase12.generation2.zero_le_macro"
PHASE12C_QUERY_MARKER: Final[int] = ord("U")
PHASE12C_ROUTE_MARKER: Final[int] = PHASE12B_NEW_MARKER
PHASE12C_NEW_COMPLETION: Final[str] = "q"
PHASE12C_MEMORY_ENTRY_ID: Final[str] = "phase12c-certified-order-skill-route"
PHASE12C_RETRIEVAL_POLICY_ID: Final[str] = "phase12c-exact-terminal-marker-route-v1"
_COMPLETION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^q$")
_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = (
    "sorry",
    "admit",
    "sorryAx",
    "axiom",
)

PHASE12C_NEW_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id=PHASE12C_NEW_TASK_ID,
    partition="heldout",
    model_prompt=(
        b"Complete the following Lean theorem. Prove zero is below every natural number. "
        b"Retrieval completion class U.\nU"
    ),
    source_prefix=(
        "import Mathlib\n\n"
        "macro \"q\" : tactic => `(tactic| omega)\n\n"
        "example (n : Nat) : 0 <= n := by\n  "
    ),
    expected_completion=PHASE12C_NEW_COMPLETION,
)


def phase12c_memory_manifest() -> dict[str, object]:
    entry_content = {
        "schema_id": "runtime.v3.phase12c.memory_entry.v1",
        "entry_id": PHASE12C_MEMORY_ENTRY_ID,
        "content_class": "certified_capability_route",
        "source_frontier_task_id": PHASE12B_NEW_TASK_ID,
        "route_marker_token_id": PHASE12C_ROUTE_MARKER,
        "heldout_task_id_present": False,
        "heldout_prompt_present": False,
        "heldout_reference_answer_present": False,
    }
    entry = dict(entry_content)
    entry["entry_hash"] = canonical_json_hash(entry_content)
    content = {
        "schema_id": "runtime.v3.phase12c.memory_manifest.v1",
        "entry_count": 1,
        "persistence": "package_bound",
        "write_authority": "host_realizer_only",
        "candidate_self_report_authoritative": False,
        "heldout_material_present": False,
        "entries": [entry],
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12c_retrieval_manifest() -> dict[str, object]:
    memory = phase12c_memory_manifest()
    entries = memory["entries"]
    if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
        raise SchemaValidationError("phase12c.memory.entries", "expected one memory entry")
    memory_entry = entries[0]
    entry_content = {
        "schema_id": "runtime.v3.phase12c.retrieval_entry.v1",
        "query_marker_token_id": PHASE12C_QUERY_MARKER,
        "memory_entry_id": PHASE12C_MEMORY_ENTRY_ID,
        "memory_entry_hash": memory_entry["entry_hash"],
        "route_marker_token_id": PHASE12C_ROUTE_MARKER,
        "match_mode": "exact_terminal_byte",
    }
    entry = dict(entry_content)
    entry["entry_hash"] = canonical_json_hash(entry_content)
    content = {
        "schema_id": "runtime.v3.phase12c.retrieval_index.v1",
        "policy_id": PHASE12C_RETRIEVAL_POLICY_ID,
        "entry_count": 1,
        "memory_manifest_hash": memory["manifest_hash"],
        "candidate_self_report_authoritative": False,
        "heldout_material_visible": False,
        "entries": [entry],
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12c_heldout_manifest() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12c.heldout_task_manifest.v1",
        "tasks": [PHASE12C_NEW_TASK.to_json(include_answer=False)],
        "answer_store_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12c_answer_store() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12c.heldout_answer_store.v1",
        "answers": [PHASE12C_NEW_TASK.to_json(include_answer=True)],
        "generator_access": False,
        "planner_access": False,
        "candidate_builder_access": False,
        "available_only_after_candidate_freeze": True,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def phase12c_update_provenance() -> dict[str, object]:
    memory = phase12c_memory_manifest()
    retrieval = phase12c_retrieval_manifest()
    content = {
        "schema_id": "runtime.v3.phase12c.update_provenance.v1",
        "source": "active_frontier_capability_route_projection",
        "source_frontier_task_id": PHASE12B_NEW_TASK_ID,
        "memory_manifest_hash": memory["manifest_hash"],
        "retrieval_manifest_hash": retrieval["manifest_hash"],
        "training_steps": 0,
        "heldout_task_ids_consumed": False,
        "heldout_prompts_consumed": False,
        "heldout_reference_answers_consumed": False,
    }
    result = dict(content)
    result["provenance_hash"] = canonical_json_hash(content)
    return result


def _load_object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected a canonical JSON object")
    return value


def _validate_candidate_memory_and_retrieval(
    package_root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    root = package_root.resolve(strict=True)
    memory = _load_object(root / "memory/memory_manifest.json", "phase12c.memory")
    retrieval = _load_object(root / "retrieval/index_manifest.json", "phase12c.retrieval")
    expected_memory = phase12c_memory_manifest()
    expected_retrieval = phase12c_retrieval_manifest()
    if memory != expected_memory:
        raise SchemaValidationError("phase12c.memory", "memory manifest mismatch")
    if retrieval != expected_retrieval:
        raise SchemaValidationError("phase12c.retrieval", "retrieval manifest mismatch")
    return memory, retrieval


@dataclass(frozen=True, slots=True)
class Phase12CRetrievalDecode:
    task_id: str
    query_marker_token_id: int
    retrieval_hit: bool
    route_marker_token_id: int
    memory_entry_id: str | None
    memory_entry_hash: str | None
    retrieval_index_hash: str
    memory_manifest_hash: str
    effective_prompt_hash: str
    base_decode: DecodeResult

    schema_id: ClassVar[str] = "runtime.v3.phase12c.retrieval_decode.v1"

    @property
    def model_identity_hash(self) -> str:
        return self.base_decode.model_identity_hash

    @property
    def stopped_on_eos(self) -> bool:
        return self.base_decode.stopped_on_eos

    @property
    def completion_text(self) -> str:
        return self.base_decode.completion_text

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "query_marker_token_id": self.query_marker_token_id,
            "retrieval_hit": self.retrieval_hit,
            "route_marker_token_id": self.route_marker_token_id,
            "memory_entry_id": self.memory_entry_id,
            "memory_entry_hash": self.memory_entry_hash,
            "retrieval_index_hash": self.retrieval_index_hash,
            "memory_manifest_hash": self.memory_manifest_hash,
            "effective_prompt_hash": self.effective_prompt_hash,
            "base_decode": self.base_decode.to_json(),
            "completion_text": self.completion_text,
            "stopped_on_eos": self.stopped_on_eos,
        }


def decode_phase12c_task(
    package_root: Path,
    task: LeanCompletionTask = PHASE12C_NEW_TASK,
) -> Phase12CRetrievalDecode:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    memory = _load_object(root / "memory/memory_manifest.json", "phase12c.memory")
    retrieval = _load_object(root / "retrieval/index_manifest.json", "phase12c.retrieval")
    query_marker = task.marker
    retrieval_hit = False
    route_marker = query_marker
    memory_entry_id: str | None = None
    memory_entry_hash: str | None = None

    if retrieval.get("schema_id") == "runtime.v3.phase12c.retrieval_index.v1":
        _validate_candidate_memory_and_retrieval(root)
        entries = retrieval.get("entries")
        if not isinstance(entries, list):
            raise SchemaValidationError("phase12c.retrieval.entries", "expected an array")
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                raise SchemaValidationError("phase12c.retrieval.entry", "expected object")
            if raw_entry.get("query_marker_token_id") == query_marker:
                retrieval_hit = True
                route_value = raw_entry.get("route_marker_token_id")
                if isinstance(route_value, bool) or not isinstance(route_value, int):
                    raise SchemaValidationError("phase12c.retrieval.route", "expected integer")
                route_marker = route_value
                memory_entry_id = str(raw_entry["memory_entry_id"])
                memory_entry_hash = str(raw_entry["memory_entry_hash"])
                break

    effective_prompt = task.model_prompt[:-1] + bytes((route_marker,))
    decoded = decode_completion(root, effective_prompt)
    if decoded.model_identity_hash != manifest.model_identity_hash:
        raise SchemaValidationError("phase12c.decode", "model identity mismatch")
    return Phase12CRetrievalDecode(
        task_id=task.task_id,
        query_marker_token_id=query_marker,
        retrieval_hit=retrieval_hit,
        route_marker_token_id=route_marker,
        memory_entry_id=memory_entry_id,
        memory_entry_hash=memory_entry_hash,
        retrieval_index_hash=canonical_json_hash(retrieval),
        memory_manifest_hash=canonical_json_hash(memory),
        effective_prompt_hash=sha256_hex(effective_prompt),
        base_decode=decoded,
    )


def expected_phase12c_task_report(
    decode: Phase12CRetrievalDecode,
    *,
    lean_toolchain: str,
) -> TaskVerifierReport:
    completion = decode.completion_text
    if (
        not decode.retrieval_hit
        or not decode.stopped_on_eos
        or _COMPLETION_PATTERN.fullmatch(completion) is None
        or completion != PHASE12C_NEW_TASK.expected_completion
    ):
        raise SchemaValidationError(
            "phase12c.task_verifier",
            "retrieval decode is not the expected completion",
        )
    source = PHASE12C_NEW_TASK.render_source(completion)
    return TaskVerifierReport(
        task_id=PHASE12C_NEW_TASK.task_id,
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


def verify_phase12c_task(
    package_root: Path,
    lean_project_root: Path,
) -> TaskVerifierReport:
    decode = decode_phase12c_task(package_root, PHASE12C_NEW_TASK)
    try:
        completion = decode.completion_text
    except (UnicodeDecodeError, SchemaValidationError):
        completion = ""
    grammar = (
        decode.retrieval_hit
        and decode.stopped_on_eos
        and _COMPLETION_PATTERN.fullmatch(completion) is not None
    )
    source = (
        PHASE12C_NEW_TASK.render_source(completion)
        if grammar
        else PHASE12C_NEW_TASK.source_prefix
    )
    source_bytes = source.encode("utf-8")
    toolchain_path = lean_project_root.resolve(strict=True) / "lean-toolchain"
    toolchain = toolchain_path.read_text(encoding="utf-8").strip()
    if not toolchain:
        raise SchemaValidationError("phase12c.lean.toolchain", "toolchain file is empty")
    if not grammar:
        return TaskVerifierReport(
            task_id=PHASE12C_NEW_TASK.task_id,
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
        raise SchemaValidationError("phase12c.lean.source", "forbidden proof token")
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12c-lean-") as temporary:
        source_path = Path(temporary) / "Phase12Generation2Task.lean"
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
            "phase12c.lean.output",
            "successful selected task must produce empty stdout and stderr",
        )
    return TaskVerifierReport(
        task_id=PHASE12C_NEW_TASK.task_id,
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
    "PHASE12C_MEMORY_ENTRY_ID",
    "PHASE12C_NEW_COMPLETION",
    "PHASE12C_NEW_TASK",
    "PHASE12C_NEW_TASK_ID",
    "PHASE12C_QUERY_MARKER",
    "PHASE12C_RETRIEVAL_POLICY_ID",
    "PHASE12C_ROUTE_MARKER",
    "Phase12CRetrievalDecode",
    "decode_phase12c_task",
    "expected_phase12c_task_report",
    "phase12c_answer_store",
    "phase12c_heldout_manifest",
    "phase12c_memory_manifest",
    "phase12c_retrieval_manifest",
    "phase12c_update_provenance",
    "verify_phase12c_task",
]
