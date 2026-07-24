from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.lean_process import run_pinned_lean_source

from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.package import ModelPackageManifest
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import (
    PHASE12C_NEW_TASK_ID,
    PHASE12C_QUERY_MARKER,
    Phase12CRetrievalDecode,
    decode_phase12c_task,
)
from rcp_rclm_runtime_v3.phase12.phase12d_program import (
    PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
    PHASE12D_SUCCESSOR_PLANNER_GENERATION,
)

PHASE12D_NEW_TASK_ID: Final[str] = "lean.phase12.generation3.lt_succ_planner_macro"
PHASE12D_QUERY_MARKER: Final[int] = ord("V")
PHASE12D_PLANNER_ROUTE_MARKER: Final[int] = PHASE12C_QUERY_MARKER
PHASE12D_NEW_COMPLETION: Final[str] = "q"
PHASE12D_GENERATOR_CAPABILITY_ID: Final[str] = (
    "phase12d-certified-planner-order-capability"
)
PHASE12D_PLANNER_ROUTE_ID: Final[str] = "phase12d-exact-terminal-marker-route-v1"
_COMPLETION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^q$")
_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = (
    "sorry",
    "admit",
    "sorryAx",
    "axiom",
)

PHASE12D_NEW_TASK: Final[LeanCompletionTask] = LeanCompletionTask(
    task_id=PHASE12D_NEW_TASK_ID,
    partition="heldout",
    model_prompt=(
        b"Complete the following Lean theorem. Prove a natural number is below its successor. "
        b"Planner completion class V.\nV"
    ),
    source_prefix=(
        "import Mathlib\n\n"
        "macro \"q\" : tactic => `(tactic| omega)\n\n"
        "example (n : Nat) : n < n + 1 := by\n  "
    ),
    expected_completion=PHASE12D_NEW_COMPLETION,
)

PHASE12D_NEXT_PROPOSAL_PROTOCOL: Final[dict[str, object]] = {
    "schema_id": "runtime.v3.phase12d.next_proposal_protocol.v1",
    "trajectory_transition_index": 3,
    "authoritative_source": "promoted_generation3_generator_and_planner",
    "required_components": [
        "adapter_manifest",
        "model_architecture",
        "optimizer_policy",
    ],
    "typed_architecture_program_required": True,
    "generator_generation": PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
    "planner_generation": PHASE12D_SUCCESSOR_PLANNER_GENERATION,
    "candidate_direct_write": False,
    "heldout_material_permitted": False,
    "manual_repair_permitted": False,
    "remaining_generator_invocations": 1,
    "remaining_candidate_realizations": 1,
    "remaining_candidate_evaluations": 1,
    "remaining_promotions": 1,
    "remaining_rejections": 0,
}
PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH: Final[str] = canonical_json_hash(
    PHASE12D_NEXT_PROPOSAL_PROTOCOL
)
PHASE12D_SELF_HOSTING_CONTRACT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase12d.self_hosting_contract.v1",
        "generator_generation": PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
        "planner_generation": PHASE12D_SUCCESSOR_PLANNER_GENERATION,
        "proposal_protocol_hash": PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
        "next_proposal_authority": True,
        "candidate_direct_write": False,
        "heldout_material_visible": False,
        "manual_repair_permitted": False,
    }
)


def phase12d_generator_capability_entry() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12d.generator_capability_entry.v1",
        "capability_id": PHASE12D_GENERATOR_CAPABILITY_ID,
        "content_class": "certified_frontier_route",
        "source_frontier_task_id": PHASE12C_NEW_TASK_ID,
        "route_marker_token_id": PHASE12D_PLANNER_ROUTE_MARKER,
        "heldout_task_id_present": False,
        "heldout_prompt_present": False,
        "heldout_reference_answer_present": False,
    }
    result = dict(content)
    result["entry_hash"] = canonical_json_hash(content)
    return result


def phase12d_generator_policy(
    active_manifest: ModelPackageManifest,
    installed_from_program_hash: str,
) -> dict[str, object]:
    capability = phase12d_generator_capability_entry()
    return {
        "schema_id": "runtime.v3.phase12d.successor_generator_policy.v1",
        "policy": "installed_self_hosted_typed_mutation_generator",
        "generation": PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
        "parent_generator_hash": active_manifest.generator_policy_hash,
        "installed_from_program_hash": installed_from_program_hash,
        "proposal_protocol_hash": PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
        "next_proposal_authority": True,
        "direct_candidate_write": False,
        "heldout_material_visible": False,
        "manual_repair_permitted": False,
        "recursive_use_demonstrated": True,
        "next_transition_index": 3,
        "capability_entry_count": 1,
        "capability_entries": [capability],
    }


def phase12d_planner_route_entry() -> dict[str, object]:
    capability = phase12d_generator_capability_entry()
    content = {
        "schema_id": "runtime.v3.phase12d.planner_route_entry.v1",
        "route_id": PHASE12D_PLANNER_ROUTE_ID,
        "query_marker_token_id": PHASE12D_QUERY_MARKER,
        "generator_capability_id": PHASE12D_GENERATOR_CAPABILITY_ID,
        "generator_capability_hash": capability["entry_hash"],
        "route_marker_token_id": PHASE12D_PLANNER_ROUTE_MARKER,
        "match_mode": "exact_terminal_byte",
    }
    result = dict(content)
    result["entry_hash"] = canonical_json_hash(content)
    return result


def phase12d_planner_policy(
    active_manifest: ModelPackageManifest,
    installed_from_program_hash: str,
) -> dict[str, object]:
    route = phase12d_planner_route_entry()
    return {
        "schema_id": "runtime.v3.phase12d.successor_planner_policy.v1",
        "policy": "installed_self_hosted_bounded_experiment_planner",
        "generation": PHASE12D_SUCCESSOR_PLANNER_GENERATION,
        "parent_planner_hash": active_manifest.planner_policy_hash,
        "installed_from_program_hash": installed_from_program_hash,
        "proposal_protocol_hash": PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
        "objective": "expand_certified_frontier",
        "bounded_within_run": True,
        "fresh_proposal_after_rejection": False,
        "recursive_use_demonstrated": True,
        "manual_repair_permitted": False,
        "heldout_material_visible": False,
        "next_transition_index": 3,
        "route_entry_count": 1,
        "routes": [route],
    }


def phase12d_heldout_manifest() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12d.heldout_task_manifest.v1",
        "tasks": [PHASE12D_NEW_TASK.to_json(include_answer=False)],
        "answer_store_separate": True,
    }
    result = dict(content)
    result["manifest_hash"] = canonical_json_hash(content)
    return result


def phase12d_answer_store() -> dict[str, object]:
    content = {
        "schema_id": "runtime.v3.phase12d.heldout_answer_store.v1",
        "answers": [PHASE12D_NEW_TASK.to_json(include_answer=True)],
        "generator_access": False,
        "planner_access": False,
        "candidate_builder_access": False,
        "available_only_after_candidate_freeze": True,
    }
    result = dict(content)
    result["answer_store_hash"] = canonical_json_hash(content)
    return result


def phase12d_update_provenance(
    active_manifest: ModelPackageManifest,
    installed_from_program_hash: str,
) -> dict[str, object]:
    generator = phase12d_generator_policy(active_manifest, installed_from_program_hash)
    planner = phase12d_planner_policy(active_manifest, installed_from_program_hash)
    content = {
        "schema_id": "runtime.v3.phase12d.update_provenance.v1",
        "source": "active_m2_generator_planner_self_modification_projection",
        "parent_generator_hash": active_manifest.generator_policy_hash,
        "parent_planner_hash": active_manifest.planner_policy_hash,
        "successor_generator_hash": canonical_json_hash(generator),
        "successor_planner_hash": canonical_json_hash(planner),
        "successor_proposal_protocol_hash": PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
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


def _effective_task(task: LeanCompletionTask, marker: int) -> LeanCompletionTask:
    return LeanCompletionTask(
        task_id=task.task_id,
        partition=task.partition,
        model_prompt=task.model_prompt[:-1] + bytes((marker,)),
        source_prefix=task.source_prefix,
        expected_completion=task.expected_completion,
    )


@dataclass(frozen=True, slots=True)
class Phase12DPlannerDecode:
    task_id: str
    query_marker_token_id: int
    planner_route_hit: bool
    generator_capability_hit: bool
    planner_route_marker_token_id: int
    generator_capability_id: str | None
    generator_capability_hash: str | None
    generator_policy_hash: str
    planner_policy_hash: str
    retrieval_decode: Phase12CRetrievalDecode

    schema_id: ClassVar[str] = "runtime.v3.phase12d.planner_decode.v1"

    @property
    def model_identity_hash(self) -> str:
        return self.retrieval_decode.model_identity_hash

    @property
    def retrieval_hit(self) -> bool:
        return self.retrieval_decode.retrieval_hit

    @property
    def stopped_on_eos(self) -> bool:
        return self.retrieval_decode.stopped_on_eos

    @property
    def completion_text(self) -> str:
        return self.retrieval_decode.completion_text

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "query_marker_token_id": self.query_marker_token_id,
            "planner_route_hit": self.planner_route_hit,
            "generator_capability_hit": self.generator_capability_hit,
            "planner_route_marker_token_id": self.planner_route_marker_token_id,
            "generator_capability_id": self.generator_capability_id,
            "generator_capability_hash": self.generator_capability_hash,
            "generator_policy_hash": self.generator_policy_hash,
            "planner_policy_hash": self.planner_policy_hash,
            "retrieval_hit": self.retrieval_hit,
            "retrieval_decode": self.retrieval_decode.to_json(),
            "completion_text": self.completion_text,
            "stopped_on_eos": self.stopped_on_eos,
        }


def decode_phase12d_task(
    package_root: Path,
    task: LeanCompletionTask = PHASE12D_NEW_TASK,
) -> Phase12DPlannerDecode:
    root = package_root.resolve(strict=True)
    generator = _load_object(
        root / "policies/generator_policy.json",
        "phase12d.generator_policy",
    )
    planner = _load_object(
        root / "policies/planner_policy.json",
        "phase12d.planner_policy",
    )
    generator_hash = canonical_json_hash(generator)
    planner_hash = canonical_json_hash(planner)
    planner_hit = False
    capability_hit = False
    route_marker = task.marker
    capability_id: str | None = None
    capability_hash: str | None = None

    candidate_policy = (
        generator.get("schema_id")
        == "runtime.v3.phase12d.successor_generator_policy.v1"
        and planner.get("schema_id")
        == "runtime.v3.phase12d.successor_planner_policy.v1"
        and generator.get("generation") == PHASE12D_SUCCESSOR_GENERATOR_GENERATION
        and planner.get("generation") == PHASE12D_SUCCESSOR_PLANNER_GENERATION
        and generator.get("proposal_protocol_hash")
        == PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH
        and planner.get("proposal_protocol_hash")
        == PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH
    )
    if candidate_policy:
        routes = planner.get("routes")
        capabilities = generator.get("capability_entries")
        if not isinstance(routes, list) or not isinstance(capabilities, list):
            raise SchemaValidationError(
                "phase12d.policy_routes",
                "candidate policies require canonical route and capability arrays",
            )
        route = next(
            (
                item
                for item in routes
                if isinstance(item, dict)
                and item.get("query_marker_token_id") == task.marker
            ),
            None,
        )
        if route is not None:
            planner_hit = True
            capability_id = str(route.get("generator_capability_id"))
            capability_hash = str(route.get("generator_capability_hash"))
            capability = next(
                (
                    item
                    for item in capabilities
                    if isinstance(item, dict)
                    and item.get("capability_id") == capability_id
                    and item.get("entry_hash") == capability_hash
                ),
                None,
            )
            if capability is not None:
                capability_hit = True
                route_value = capability.get("route_marker_token_id")
                if isinstance(route_value, bool) or not isinstance(route_value, int):
                    raise SchemaValidationError(
                        "phase12d.generator_capability.route",
                        "expected integer route marker",
                    )
                if route.get("route_marker_token_id") != route_value:
                    raise SchemaValidationError(
                        "phase12d.planner_route",
                        "planner and generator route markers disagree",
                    )
                route_marker = route_value

    effective_task = _effective_task(task, route_marker)
    retrieval_decode = decode_phase12c_task(root, effective_task)
    return Phase12DPlannerDecode(
        task_id=task.task_id,
        query_marker_token_id=task.marker,
        planner_route_hit=planner_hit,
        generator_capability_hit=capability_hit,
        planner_route_marker_token_id=route_marker,
        generator_capability_id=capability_id,
        generator_capability_hash=capability_hash,
        generator_policy_hash=generator_hash,
        planner_policy_hash=planner_hash,
        retrieval_decode=retrieval_decode,
    )


def expected_phase12d_task_report(
    decode: Phase12DPlannerDecode,
    *,
    lean_toolchain: str,
) -> TaskVerifierReport:
    completion = decode.completion_text
    if (
        not decode.planner_route_hit
        or not decode.generator_capability_hit
        or not decode.retrieval_hit
        or not decode.stopped_on_eos
        or _COMPLETION_PATTERN.fullmatch(completion) is None
        or completion != PHASE12D_NEW_TASK.expected_completion
    ):
        raise SchemaValidationError(
            "phase12d.task_verifier",
            "planner decode is not the expected completion",
        )
    source = PHASE12D_NEW_TASK.render_source(completion)
    return TaskVerifierReport(
        task_id=PHASE12D_NEW_TASK.task_id,
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


def verify_phase12d_task(
    package_root: Path,
    lean_project_root: Path,
) -> TaskVerifierReport:
    decode = decode_phase12d_task(package_root, PHASE12D_NEW_TASK)
    try:
        completion = decode.completion_text
    except (UnicodeDecodeError, SchemaValidationError):
        completion = ""
    grammar = (
        decode.planner_route_hit
        and decode.generator_capability_hit
        and decode.retrieval_hit
        and decode.stopped_on_eos
        and _COMPLETION_PATTERN.fullmatch(completion) is not None
    )
    source = (
        PHASE12D_NEW_TASK.render_source(completion)
        if grammar
        else PHASE12D_NEW_TASK.source_prefix
    )
    source_bytes = source.encode("utf-8")
    toolchain_path = lean_project_root.resolve(strict=True) / "lean-toolchain"
    toolchain = toolchain_path.read_text(encoding="utf-8").strip()
    if not toolchain:
        raise SchemaValidationError("phase12d.lean.toolchain", "toolchain file is empty")
    if not grammar:
        return TaskVerifierReport(
            task_id=PHASE12D_NEW_TASK.task_id,
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
        raise SchemaValidationError("phase12d.lean.source", "forbidden proof token")
    completed = run_pinned_lean_source(
        source_bytes,
        lean_project_root,
        temporary_prefix="rcp-rclm-phase12d-lean-",
        source_file_name="Phase12Generation3Task.lean",
    )
    if completed.returncode == 0 and (completed.stdout or completed.stderr):
        raise SchemaValidationError(
            "phase12d.lean.output",
            "successful selected task must produce empty stdout and stderr",
        )
    return TaskVerifierReport(
        task_id=PHASE12D_NEW_TASK.task_id,
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
    "PHASE12D_GENERATOR_CAPABILITY_ID",
    "PHASE12D_NEW_COMPLETION",
    "PHASE12D_NEW_TASK",
    "PHASE12D_NEW_TASK_ID",
    "PHASE12D_NEXT_PROPOSAL_PROTOCOL",
    "PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH",
    "PHASE12D_PLANNER_ROUTE_ID",
    "PHASE12D_PLANNER_ROUTE_MARKER",
    "PHASE12D_QUERY_MARKER",
    "PHASE12D_SELF_HOSTING_CONTRACT_HASH",
    "Phase12DPlannerDecode",
    "decode_phase12d_task",
    "expected_phase12d_task_report",
    "phase12d_answer_store",
    "phase12d_generator_capability_entry",
    "phase12d_generator_policy",
    "phase12d_heldout_manifest",
    "phase12d_planner_policy",
    "phase12d_planner_route_entry",
    "phase12d_update_provenance",
    "verify_phase12d_task",
]
