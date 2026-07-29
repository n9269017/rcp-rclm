from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.information import (
    PRECISION_BITS,
    PromptInformationEvidence,
    prompt_information_evidence,
)
from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    PROTECTED_TASK,
    LeanCompletionTask,
)
from rcp_rclm_runtime_v3.phase10.package import load_package_components
from rcp_rclm_runtime_v3.phase10.sparse_profile import DecodeResult, decode_completion, raw_transition_scores
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport
from rcp_rclm_runtime_v3.phase10.lean_process import run_pinned_lean_source
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import PHASE11B_NEW_TASK
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import PHASE12B_NEW_TASK
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import PHASE12C_NEW_TASK
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import PHASE12D_NEW_TASK
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import (
    PHASE12E_ADAPTER_ROUTE_MAGIC,
    PHASE12E_NEW_TASK,
    selected_phase12e_adapter_spec,
)

from rcp_rclm_runtime_v4.phase14.challenges import HiddenChallenge
from rcp_rclm_runtime_v4.phase14.constants import PHASE14_ROUTE_MARKER

_FORBIDDEN_SOURCE_TOKENS: Final[Sequence[str]] = ("sorry", "admit", "sorryAx", "axiom")


@dataclass(frozen=True, slots=True)
class Phase14RouteDecode:
    task_id: str
    challenge_commitment_hash: str | None
    selected_route_family: str | None
    original_marker_token_id: int
    effective_marker_token_id: int
    route_hit: bool
    route_evidence_hash: str
    decode: DecodeResult

    schema_id: ClassVar[str] = "runtime.v4.phase14.route_decode.v1"

    @property
    def completion_text(self) -> str:
        try:
            return self.decode.completion_text
        except (UnicodeDecodeError, SchemaValidationError):
            return ""

    @property
    def stopped_on_eos(self) -> bool:
        return self.decode.stopped_on_eos

    @property
    def model_identity_hash(self) -> str:
        return self.decode.model_identity_hash

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "challenge_commitment_hash": self.challenge_commitment_hash,
            "selected_route_family": self.selected_route_family,
            "original_marker_token_id": self.original_marker_token_id,
            "effective_marker_token_id": self.effective_marker_token_id,
            "route_hit": self.route_hit,
            "route_evidence_hash": self.route_evidence_hash,
            "decode": self.decode.to_json(),
            "completion_text": self.completion_text,
            "stopped_on_eos": self.stopped_on_eos,
        }


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical JSON object")
    return value


def _route_by_commitment(value: dict[str, object], commitment_hash: str) -> dict[str, object] | None:
    raw = value.get("phase14_routes", [])
    if not isinstance(raw, list):
        return None
    matches = tuple(
        item
        for item in raw
        if isinstance(item, dict)
        and item.get("challenge_commitment_hash") == commitment_hash
    )
    return matches[0] if len(matches) == 1 else None


def _legacy_memory_route(root: Path, marker: int) -> tuple[bool, int, str]:
    memory = _object(root / "memory/memory_manifest.json", "phase14.memory")
    retrieval = _object(root / "retrieval/index_manifest.json", "phase14.retrieval")
    raw_entries = retrieval.get("entries", [])
    if not isinstance(raw_entries, list):
        return False, marker, canonical_json_hash({"route": "invalid_retrieval_entries"})
    match = next(
        (
            item
            for item in raw_entries
            if isinstance(item, dict)
            and item.get("query_marker_token_id") == marker
            and item.get("match_mode") == "exact_terminal_byte"
        ),
        None,
    )
    if match is None:
        return False, marker, canonical_json_hash({"route": "no_legacy_memory_match", "marker": marker})
    route_marker = match.get("route_marker_token_id")
    if not isinstance(route_marker, int):
        return False, marker, canonical_json_hash({"route": "invalid_legacy_memory_marker"})
    evidence = canonical_json_hash(
        {
            "memory": memory,
            "retrieval_entry": match,
            "query_marker": marker,
            "route_marker": route_marker,
        }
    )
    return True, route_marker, evidence


def _legacy_planner_route(root: Path, marker: int) -> tuple[bool, int, str]:
    generator = _object(root / "policies/generator_policy.json", "phase14.generator")
    planner = _object(root / "policies/planner_policy.json", "phase14.planner")
    raw_routes = planner.get("routes", [])
    if not isinstance(raw_routes, list):
        return False, marker, canonical_json_hash({"route": "invalid_planner_routes"})
    match = next(
        (
            item
            for item in raw_routes
            if isinstance(item, dict)
            and item.get("query_marker_token_id") == marker
            and item.get("match_mode") == "exact_terminal_byte"
        ),
        None,
    )
    if match is None:
        return False, marker, canonical_json_hash({"route": "no_legacy_planner_match", "marker": marker})
    route_marker = match.get("route_marker_token_id")
    if not isinstance(route_marker, int):
        return False, marker, canonical_json_hash({"route": "invalid_legacy_planner_marker"})
    evidence = canonical_json_hash(
        {
            "generator": generator,
            "planner_route": match,
            "query_marker": marker,
            "route_marker": route_marker,
        }
    )
    return True, route_marker, evidence


def _legacy_adapter_route(root: Path, marker: int) -> tuple[bool, int, str]:
    manifest, architecture, _, _, adapter = load_package_components(root)
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None:
        return False, marker, canonical_json_hash({"route": "legacy_adapter_record_absent"})
    payload = (root / record.spec.path).read_bytes()
    if len(payload) < 8:
        return False, marker, canonical_json_hash({"route": "legacy_adapter_payload_short"})
    observed = tuple(struct.unpack_from("<hhhh", payload, 0))
    hit = observed == PHASE12E_ADAPTER_ROUTE_MAGIC and marker == PHASE12E_NEW_TASK.marker
    route_marker = PHASE12E_ADAPTER_ROUTE_MAGIC[1] if hit else marker
    evidence = canonical_json_hash(
        {
            "adapter_manifest_hash": manifest.adapter_manifest_hash,
            "selected_tensor_hash": record.sha256,
            "legacy_magic": list(observed),
            "query_marker": marker,
            "route_marker": route_marker,
            "hit": hit,
        }
    )
    return hit, route_marker, evidence


def _phase14_memory_route(
    root: Path,
    commitment_hash: str,
    slot: int,
) -> tuple[bool, str]:
    memory = _object(root / "memory/memory_manifest.json", "phase14.memory")
    retrieval = _object(root / "retrieval/index_manifest.json", "phase14.retrieval")
    memory_route = _route_by_commitment(memory, commitment_hash)
    retrieval_route = _route_by_commitment(retrieval, commitment_hash)
    hit = bool(
        memory_route
        and retrieval_route
        and memory_route.get("slot_token_id") == slot
        and retrieval_route.get("slot_token_id") == slot
        and memory_route.get("route_marker_token_id") == PHASE14_ROUTE_MARKER
        and retrieval_route.get("route_marker_token_id") == PHASE14_ROUTE_MARKER
    )
    return hit, canonical_json_hash(
        {
            "family": "memory_retrieval",
            "memory_route": memory_route,
            "retrieval_route": retrieval_route,
            "hit": hit,
        }
    )


def _phase14_generator_route(
    root: Path,
    commitment_hash: str,
    slot: int,
) -> tuple[bool, str]:
    generator = _object(root / "policies/generator_policy.json", "phase14.generator")
    planner = _object(root / "policies/planner_policy.json", "phase14.planner")
    generator_route = _route_by_commitment(generator, commitment_hash)
    planner_route = _route_by_commitment(planner, commitment_hash)
    hit = bool(
        generator_route
        and planner_route
        and generator_route.get("slot_token_id") == slot
        and planner_route.get("slot_token_id") == slot
        and generator_route.get("route_marker_token_id") == PHASE14_ROUTE_MARKER
        and planner_route.get("route_marker_token_id") == PHASE14_ROUTE_MARKER
    )
    return hit, canonical_json_hash(
        {
            "family": "generator_planner",
            "generator_route": generator_route,
            "planner_route": planner_route,
            "hit": hit,
        }
    )


def _phase14_adapter_route(
    root: Path,
    commitment_hash: str,
    slot: int,
) -> tuple[bool, str]:
    optimizer = _object(root / "training/optimizer_state.json", "phase14.optimizer")
    route = _route_by_commitment(optimizer, commitment_hash)
    if route is None:
        return False, canonical_json_hash({"family": "adapter_optimizer", "route": None})
    _, architecture, _, _, adapter = load_package_components(root)
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None:
        return False, canonical_json_hash({"family": "adapter_optimizer", "route": route, "record": None})
    offset = route.get("offset_bytes")
    prefix = route.get("commitment_prefix_u16")
    if not isinstance(offset, int) or not isinstance(prefix, int):
        return False, canonical_json_hash({"family": "adapter_optimizer", "route": route, "record": record.to_json()})
    payload = (root / record.spec.path).read_bytes()
    observed = None
    if 0 <= offset and offset + 8 <= len(payload):
        observed = tuple(struct.unpack_from("<hhhh", payload, offset))
    expected = (slot, PHASE14_ROUTE_MARKER, prefix, 1)
    hit = observed == expected and route.get("tensor_sha256") == record.sha256
    return hit, canonical_json_hash(
        {
            "family": "adapter_optimizer",
            "route": route,
            "selected_tensor_hash": record.sha256,
            "observed": None if observed is None else list(observed),
            "expected": list(expected),
            "hit": hit,
        }
    )


def _phase14_weight_route(
    root: Path,
    commitment_hash: str,
    slot: int,
) -> tuple[bool, str]:
    resource = _object(
        root / "runtime/resource_measurement.json",
        "phase14.resource_measurement",
    )
    raw_routes = resource.get("phase14_weight_routes", [])
    route = None
    if isinstance(raw_routes, list):
        matches = tuple(
            item
            for item in raw_routes
            if isinstance(item, dict)
            and item.get("challenge_commitment_hash") == commitment_hash
        )
        if len(matches) == 1:
            route = matches[0]
    scores = raw_transition_scores(root, slot)
    selected = min(
        range(len(scores)),
        key=lambda token: (-scores[token], token),
    )
    hit = bool(
        route
        and route.get("slot_token_id") == slot
        and route.get("route_marker_token_id") == PHASE14_ROUTE_MARKER
        and route.get("tensor_manifest_hash")
        == load_package_components(root)[0].tensor_manifest_hash
        and selected == PHASE14_ROUTE_MARKER
    )
    return hit, canonical_json_hash(
        {
            "family": "model_weights",
            "challenge_commitment_hash": commitment_hash,
            "route": route,
            "slot_token_id": slot,
            "selected_token_id": selected,
            "selected_score": scores[selected],
            "route_marker_token_id": PHASE14_ROUTE_MARKER,
            "hit": hit,
        }
    )


def _apply_legacy_chain(root: Path, marker: int) -> tuple[int, list[str], bool]:
    evidence: list[str] = []
    current = marker
    if current == PHASE12E_NEW_TASK.marker:
        hit, current, report = _legacy_adapter_route(root, current)
        evidence.append(report)
        if not hit:
            return marker, evidence, False
    if current == PHASE12D_NEW_TASK.marker:
        hit, current, report = _legacy_planner_route(root, current)
        evidence.append(report)
        if not hit:
            return marker, evidence, False
    if current == PHASE12C_NEW_TASK.marker:
        hit, current, report = _legacy_memory_route(root, current)
        evidence.append(report)
        if not hit:
            return marker, evidence, False
    return current, evidence, True


def decode_task(
    package_root: Path,
    task: LeanCompletionTask,
    *,
    challenge: HiddenChallenge | None = None,
) -> Phase14RouteDecode:
    root = package_root.resolve(strict=True)
    original = task.marker
    route_hit = True
    evidence: list[str] = []
    marker = original
    selected_route_family: str | None = None
    commitment: str | None = None
    if challenge is not None:
        commitment = challenge.commitment_hash
        if task.task_id != challenge.task_id or original != challenge.slot_token_id:
            raise SchemaValidationError("phase14.task", "hidden challenge task binding mismatch")
        route_checks = (
            (
                "memory_retrieval",
                *_phase14_memory_route(root, commitment, original),
            ),
            (
                "generator_planner",
                *_phase14_generator_route(root, commitment, original),
            ),
            (
                "adapter_optimizer",
                *_phase14_adapter_route(root, commitment, original),
            ),
            (
                "model_weights",
                *_phase14_weight_route(root, commitment, original),
            ),
        )
        evidence.extend(report for _, _, report in route_checks)
        hits = tuple(family for family, hit, _ in route_checks if hit)
        route_hit = len(hits) == 1
        selected_route_family = hits[0] if route_hit else None
        marker = PHASE14_ROUTE_MARKER if route_hit else original
    marker, legacy_evidence, legacy_hit = _apply_legacy_chain(root, marker)
    evidence.extend(legacy_evidence)
    if challenge is not None:
        route_hit = route_hit and legacy_hit
    elif challenge is None and original in {
        PHASE12C_NEW_TASK.marker,
        PHASE12D_NEW_TASK.marker,
        PHASE12E_NEW_TASK.marker,
    }:
        route_hit = legacy_hit
    effective_prompt = task.model_prompt[:-1] + bytes((marker,))
    decode = decode_completion(root, effective_prompt)
    return Phase14RouteDecode(
        task_id=task.task_id,
        challenge_commitment_hash=commitment,
        selected_route_family=selected_route_family,
        original_marker_token_id=original,
        effective_marker_token_id=marker,
        route_hit=route_hit,
        route_evidence_hash=canonical_json_hash(evidence),
        decode=decode,
    )


def verify_task(
    package_root: Path,
    task: LeanCompletionTask,
    *,
    lean_project_root: Path | None,
    challenge: HiddenChallenge | None = None,
) -> TaskVerifierReport:
    decoded = decode_task(package_root, task, challenge=challenge)
    try:
        completion = decoded.completion_text
    except (UnicodeDecodeError, SchemaValidationError):
        completion = ""
    grammar = bool(
        decoded.route_hit
        and decoded.stopped_on_eos
        and completion == task.expected_completion
        and completion.isascii()
        and bool(completion)
    )
    source = task.render_source(completion) if grammar else task.source_prefix
    source_bytes = source.encode("utf-8")
    toolchain = "leanprover/lean4:v4.31.0"
    if lean_project_root is not None:
        toolchain_path = lean_project_root.resolve(strict=True) / "lean-toolchain"
        toolchain = toolchain_path.read_text(encoding="utf-8").strip()
        if not toolchain:
            raise SchemaValidationError("phase14.lean.toolchain", "toolchain file is empty")
    if not grammar:
        return TaskVerifierReport(
            task_id=task.task_id,
            model_identity_hash=decoded.model_identity_hash,
            completion=completion,
            completion_hash=sha256_hex(completion.encode("utf-8")),
            source_hash=sha256_hex(source_bytes),
            decode_result_hash=decoded.result_hash,
            grammar_accepted=False,
            lean_invoked=False,
            lean_exit_code=None,
            lean_toolchain=toolchain,
            verdict="reject",
        )
    lower_source = source.lower()
    if any(token.lower() in lower_source for token in _FORBIDDEN_SOURCE_TOKENS):
        raise SchemaValidationError("phase14.lean.source", "forbidden proof token")
    if lean_project_root is None:
        exit_code = 0
    else:
        completed = run_pinned_lean_source(
            source_bytes,
            lean_project_root,
            temporary_prefix="rcp-rclm-phase14-lean-",
            source_file_name="Phase14HiddenTask.lean",
        )
        exit_code = completed.returncode
        if exit_code == 0 and (completed.stdout or completed.stderr):
            raise SchemaValidationError(
                "phase14.lean.output",
                "successful hidden task must produce empty stdout and stderr",
            )
    return TaskVerifierReport(
        task_id=task.task_id,
        model_identity_hash=decoded.model_identity_hash,
        completion=completion,
        completion_hash=sha256_hex(completion.encode("ascii")),
        source_hash=sha256_hex(source_bytes),
        decode_result_hash=decoded.result_hash,
        grammar_accepted=True,
        lean_invoked=True,
        lean_exit_code=exit_code,
        lean_toolchain=toolchain,
        verdict="accept" if exit_code == 0 else "reject",
    )


def base_task_suite() -> tuple[LeanCompletionTask, ...]:
    return (
        PROTECTED_TASK,
        HELDOUT_TASK,
        PHASE11B_NEW_TASK,
        PHASE12B_NEW_TASK,
        PHASE12C_NEW_TASK,
        PHASE12D_NEW_TASK,
        PHASE12E_NEW_TASK,
    )


def effective_task(
    package_root: Path,
    task: LeanCompletionTask,
    *,
    challenge: HiddenChallenge | None = None,
) -> LeanCompletionTask:
    decoded = decode_task(package_root, task, challenge=challenge)
    return LeanCompletionTask(
        task_id=task.task_id,
        partition=task.partition,
        model_prompt=task.model_prompt[:-1] + bytes((decoded.effective_marker_token_id,)),
        source_prefix=task.source_prefix,
        expected_completion=task.expected_completion,
    )


@dataclass(frozen=True, slots=True)
class ProtectedInformationWitness:
    task_id: str
    predecessor_marker_token_id: int
    candidate_marker_token_id: int
    predecessor_score_vector_hash: str
    candidate_score_vector_hash: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.protected_information_witness.v1"

    @property
    def unchanged(self) -> bool:
        return (
            self.predecessor_marker_token_id == self.candidate_marker_token_id
            and self.predecessor_score_vector_hash == self.candidate_score_vector_hash
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "predecessor_marker_token_id": self.predecessor_marker_token_id,
            "candidate_marker_token_id": self.candidate_marker_token_id,
            "predecessor_score_vector_hash": self.predecessor_score_vector_hash,
            "candidate_score_vector_hash": self.candidate_score_vector_hash,
            "unchanged": self.unchanged,
        }


@dataclass(frozen=True, slots=True)
class Phase14InformationReport:
    protected_witnesses: Sequence[ProtectedInformationWitness]
    new_task_predecessor: PromptInformationEvidence
    new_task_candidate: PromptInformationEvidence
    predecessor_route_hit: bool
    candidate_route_hit: bool

    schema_id: ClassVar[str] = "runtime.v4.phase14.information_report.v1"

    @property
    def protected_unchanged(self) -> bool:
        return all(witness.unchanged for witness in self.protected_witnesses)

    @property
    def improvement_interval(self):
        return self.new_task_predecessor.kl_qre_sum_interval - self.new_task_candidate.kl_qre_sum_interval

    @property
    def accepted(self) -> bool:
        return (
            self.protected_unchanged
            and not self.predecessor_route_hit
            and self.candidate_route_hit
            and self.improvement_interval.strictly_positive()
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "protected_witnesses": [witness.to_json() for witness in self.protected_witnesses],
            "new_task_predecessor": self.new_task_predecessor.to_json(),
            "new_task_candidate": self.new_task_candidate.to_json(),
            "predecessor_route_hit": self.predecessor_route_hit,
            "candidate_route_hit": self.candidate_route_hit,
            "protected_unchanged": self.protected_unchanged,
            "improvement_interval": self.improvement_interval.to_json(),
            "qre_equals_kl_by_diagonal_construction": True,
            "von_neumann_equals_shannon_by_diagonal_construction": True,
            "precision_bits": PRECISION_BITS,
            "accepted": self.accepted,
        }


def build_information_report(
    active_root: Path,
    candidate_root: Path,
    protected_tasks: Sequence[LeanCompletionTask],
    challenge: HiddenChallenge,
    *,
    accepted_challenges: Sequence[HiddenChallenge] = (),
) -> Phase14InformationReport:
    protected_witnesses: list[ProtectedInformationWitness] = []
    protected_bindings = (
        *((task, None) for task in protected_tasks),
        *((item.task, item) for item in accepted_challenges),
    )
    for task, protected_challenge in protected_bindings:
        active_effective = effective_task(
            active_root, task, challenge=protected_challenge
        )
        candidate_effective = effective_task(
            candidate_root, task, challenge=protected_challenge
        )
        active_marker = active_effective.marker
        candidate_marker = candidate_effective.marker
        protected_witnesses.append(
            ProtectedInformationWitness(
                task_id=task.task_id,
                predecessor_marker_token_id=active_marker,
                candidate_marker_token_id=candidate_marker,
                predecessor_score_vector_hash=canonical_json_hash(
                    list(raw_transition_scores(active_root, active_marker))
                ),
                candidate_score_vector_hash=canonical_json_hash(
                    list(raw_transition_scores(candidate_root, candidate_marker))
                ),
            )
        )
    predecessor_decode = decode_task(active_root, challenge.task, challenge=challenge)
    candidate_decode = decode_task(candidate_root, challenge.task, challenge=challenge)
    predecessor_effective = LeanCompletionTask(
        task_id=challenge.task_id,
        partition="heldout",
        model_prompt=challenge.task.model_prompt[:-1]
        + bytes((predecessor_decode.effective_marker_token_id,)),
        source_prefix=challenge.task.source_prefix,
        expected_completion=challenge.task.expected_completion,
    )
    candidate_effective = LeanCompletionTask(
        task_id=challenge.task_id,
        partition="heldout",
        model_prompt=challenge.task.model_prompt[:-1]
        + bytes((candidate_decode.effective_marker_token_id,)),
        source_prefix=challenge.task.source_prefix,
        expected_completion=challenge.task.expected_completion,
    )
    return Phase14InformationReport(
        protected_witnesses=tuple(protected_witnesses),
        new_task_predecessor=prompt_information_evidence(active_root, predecessor_effective),
        new_task_candidate=prompt_information_evidence(candidate_root, candidate_effective),
        predecessor_route_hit=predecessor_decode.route_hit
        and predecessor_decode.completion_text == challenge.task.expected_completion,
        candidate_route_hit=candidate_decode.route_hit
        and candidate_decode.completion_text == challenge.task.expected_completion,
    )


__all__ = [
    "Phase14InformationReport",
    "ProtectedInformationWitness",
    "Phase14RouteDecode",
    "base_task_suite",
    "build_information_report",
    "decode_task",
    "effective_task",
    "verify_task",
]
