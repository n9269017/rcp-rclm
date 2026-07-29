from __future__ import annotations

import copy
import hashlib
import os
import shutil
import struct
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.adapters import LoRAAdapterManifest
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    PACKAGE_MANIFEST_PATH,
    SUPPORT_HASH_FIELD_BY_PATH,
    TENSOR_MANIFEST_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import ATTN_OUTPUT_TENSOR
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import selected_phase12e_adapter_spec

from rcp_rclm_runtime_v4.phase14.constants import PHASE14_TRAJECTORY_ID, UpdateFamily
from rcp_rclm_runtime_v4.phase14.records import Phase14MutationProgram


@dataclass(frozen=True, slots=True)
class Phase14SemanticCandidate:
    root: Path
    active_semantic_package_hash: str
    manifest: ModelPackageManifest
    program: Phase14MutationProgram
    changed_paths: Sequence[str]
    family_evidence_hash: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.semantic_candidate.v1"

    @property
    def candidate_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.program.contract_version,
            "active_semantic_package_hash": self.active_semantic_package_hash,
            "candidate_semantic_package_hash": self.manifest.package_hash,
            "candidate_model_identity_hash": self.manifest.model_identity_hash,
            "program_hash": self.program.program_hash,
            "update_family": self.program.update_family,
            "challenge_commitment_hash": self.program.challenge_commitment_hash,
            "changed_paths": list(self.changed_paths),
            "family_evidence_hash": self.family_evidence_hash,
        }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical JSON object")
    return copy.deepcopy(value)


def _support_values(root: Path) -> dict[str, dict[str, object]]:
    return {
        path: _object(root / path, f"phase14.support.{path}")
        for path in SUPPORT_HASH_FIELD_BY_PATH
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _rebuild_tensor_manifest(root: Path, old: TensorManifest) -> TensorManifest:
    records = tuple(
        TensorRecord(spec=record.spec, sha256=_file_hash(root / record.spec.path))
        for record in old.records
    )
    result = TensorManifest(
        architecture_hash=old.architecture_hash,
        records=records,
        parameter_count=old.parameter_count,
    )
    _write_json(root / TENSOR_MANIFEST_PATH, result.serialized_json())
    return result


def _with_content_hash(value: dict[str, object], field: str) -> dict[str, object]:
    content = {key: item for key, item in value.items() if key != field}
    result = dict(content)
    result[field] = canonical_json_hash(content)
    return result


def _append_unique_route(
    container: dict[str, object],
    *,
    route: dict[str, object],
    count_field: str,
) -> dict[str, object]:
    raw = container.get("phase14_routes", [])
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise SchemaValidationError("phase14.routes", "invalid route list")
    routes = [copy.deepcopy(item) for item in raw]
    commitment = route["challenge_commitment_hash"]
    if any(item.get("challenge_commitment_hash") == commitment for item in routes):
        raise SchemaValidationError("phase14.routes", "duplicate challenge route")
    routes.append(route)
    routes.sort(key=lambda item: str(item["challenge_commitment_hash"]).encode("utf-8"))
    result = dict(container)
    result["phase14_routes"] = routes
    result[count_field] = len(routes)
    result["heldout_material_visible"] = False
    result["candidate_self_report_authoritative"] = False
    return result


def _route_content(program: Phase14MutationProgram, family: UpdateFamily) -> dict[str, object]:
    content = {
        "schema_id": f"runtime.v4.phase14.{family}_route.v1",
        "challenge_commitment_hash": program.challenge_commitment_hash,
        "slot_token_id": program.slot_token_id,
        "route_marker_token_id": program.route_marker_token_id,
        "update_family": family,
        "program_variant": program.variant,
        "package_generated": True,
        "heldout_prompt_present": False,
        "heldout_reference_answer_present": False,
        "successful_family_hint_visible": False,
    }
    result = dict(content)
    result["route_hash"] = canonical_json_hash(content)
    return result


def _apply_memory_retrieval(
    root: Path,
    support: dict[str, dict[str, object]],
    program: Phase14MutationProgram,
) -> tuple[object, object, str]:
    memory_path = "memory/memory_manifest.json"
    retrieval_path = "retrieval/index_manifest.json"
    memory = _append_unique_route(
        support[memory_path],
        route=_route_content(program, "memory_retrieval"),
        count_field="phase14_route_count",
    )
    memory["schema_id"] = "runtime.v4.phase14.memory_manifest.v1"
    memory = _with_content_hash(memory, "manifest_hash")
    route = _route_content(program, "memory_retrieval")
    route["memory_manifest_hash"] = memory["manifest_hash"]
    route["route_hash"] = canonical_json_hash(
        {key: item for key, item in route.items() if key != "route_hash"}
    )
    retrieval = _append_unique_route(
        support[retrieval_path],
        route=route,
        count_field="phase14_route_count",
    )
    retrieval["schema_id"] = "runtime.v4.phase14.retrieval_index.v1"
    retrieval["memory_manifest_hash"] = memory["manifest_hash"]
    retrieval = _with_content_hash(retrieval, "manifest_hash")
    support[memory_path] = memory
    support[retrieval_path] = retrieval
    _write_json(root / memory_path, memory)
    _write_json(root / retrieval_path, retrieval)
    evidence = canonical_json_hash(
        {
            "family": "memory_retrieval",
            "memory_manifest_hash": memory["manifest_hash"],
            "retrieval_manifest_hash": retrieval["manifest_hash"],
            "challenge_commitment_hash": program.challenge_commitment_hash,
        }
    )
    return memory, retrieval, evidence


def _apply_generator_planner(
    root: Path,
    support: dict[str, dict[str, object]],
    program: Phase14MutationProgram,
) -> tuple[object, object, str]:
    generator_path = "policies/generator_policy.json"
    planner_path = "policies/planner_policy.json"
    generator = _append_unique_route(
        support[generator_path],
        route=_route_content(program, "generator_planner"),
        count_field="phase14_route_count",
    )
    generator["schema_id"] = "runtime.v4.phase14.generator_policy.v1"
    generator["generation"] = int(generator.get("generation", 3)) + 1
    generator["next_proposal_authority"] = True
    generator["manual_repair_permitted"] = False
    generator["heldout_material_visible"] = False
    planner = _append_unique_route(
        support[planner_path],
        route=_route_content(program, "generator_planner"),
        count_field="phase14_route_count",
    )
    planner["schema_id"] = "runtime.v4.phase14.planner_policy.v1"
    planner["generation"] = int(planner.get("generation", 3)) + 1
    planner["fresh_proposal_after_rejection"] = True
    planner["manual_repair_permitted"] = False
    planner["heldout_material_visible"] = False
    support[generator_path] = generator
    support[planner_path] = planner
    _write_json(root / generator_path, generator)
    _write_json(root / planner_path, planner)
    evidence = canonical_json_hash(
        {
            "family": "generator_planner",
            "generator_policy_hash": canonical_json_hash(generator),
            "planner_policy_hash": canonical_json_hash(planner),
            "challenge_commitment_hash": program.challenge_commitment_hash,
        }
    )
    return generator, planner, evidence


def _apply_model_weights(
    root: Path,
    support: dict[str, dict[str, object]],
    old_tensors: TensorManifest,
    program: Phase14MutationProgram,
) -> tuple[TensorManifest, str]:
    record = next((item for item in old_tensors.records if item.spec.name == ATTN_OUTPUT_TENSOR), None)
    if record is None:
        raise SchemaValidationError("phase14.weights", "transition tensor is absent")
    transition = root / record.spec.path
    payload = bytearray(transition.read_bytes())
    width = 320
    target = program.route_marker_token_id
    index = target * width + program.slot_token_id
    struct.pack_into("<h", payload, index * 2, 28_672)
    transition.write_bytes(bytes(payload))
    tensors = _rebuild_tensor_manifest(root, old_tensors)
    resource_path = "runtime/resource_measurement.json"
    resource = support[resource_path]
    raw_routes = resource.get("phase14_weight_routes", [])
    if not isinstance(raw_routes, list) or any(
        not isinstance(item, dict) for item in raw_routes
    ):
        raise SchemaValidationError(
            "phase14.weights.phase14_weight_routes",
            "invalid route list",
        )
    routes = [copy.deepcopy(item) for item in raw_routes]
    if any(
        item.get("challenge_commitment_hash")
        == program.challenge_commitment_hash
        for item in routes
    ):
        raise SchemaValidationError(
            "phase14.weights",
            "duplicate model-weight challenge route",
        )
    route = _route_content(program, "model_weights")
    route["transition_tensor_hash"] = _file_hash(transition)
    route["tensor_manifest_hash"] = tensors.manifest_hash
    route["route_hash"] = canonical_json_hash(
        {key: item for key, item in route.items() if key != "route_hash"}
    )
    routes.append(route)
    routes.sort(
        key=lambda item: str(item["challenge_commitment_hash"]).encode(
            "utf-8"
        )
    )
    resource = dict(resource)
    resource["schema_id"] = "runtime.v4.phase14.resource_measurement.v1"
    resource["phase14_weight_route_count"] = len(routes)
    resource["phase14_weight_routes"] = routes
    resource["heldout_material_visible"] = False
    resource["candidate_self_report_authoritative"] = False
    support[resource_path] = resource
    _write_json(root / resource_path, resource)
    evidence = canonical_json_hash(
        {
            "family": "model_weights",
            "challenge_commitment_hash": program.challenge_commitment_hash,
            "slot_token_id": program.slot_token_id,
            "target_token_id": target,
            "program_variant": program.variant,
            "transition_tensor_hash": _file_hash(transition),
            "tensor_manifest_hash": tensors.manifest_hash,
            "route_hash": route["route_hash"],
        }
    )
    return tensors, evidence


def _apply_adapter_optimizer(
    root: Path,
    support: dict[str, dict[str, object]],
    old_adapter: LoRAAdapterManifest,
    architecture: object,
    program: Phase14MutationProgram,
) -> tuple[LoRAAdapterManifest, str]:
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in old_adapter.records if item.spec.name == selected.name), None)
    if record is None:
        raise SchemaValidationError("phase14.adapter", "selected adapter route tensor is absent")
    tensor_path = root / record.spec.path
    payload = bytearray(tensor_path.read_bytes())
    optimizer_path = "training/optimizer_state.json"
    optimizer = support[optimizer_path]
    raw_routes = optimizer.get("phase14_routes", [])
    if not isinstance(raw_routes, list) or any(not isinstance(item, dict) for item in raw_routes):
        raise SchemaValidationError("phase14.optimizer.phase14_routes", "invalid route list")
    routes = [copy.deepcopy(item) for item in raw_routes]
    if any(item.get("challenge_commitment_hash") == program.challenge_commitment_hash for item in routes):
        raise SchemaValidationError("phase14.adapter", "duplicate adapter challenge route")
    offset = 8 + len(routes) * 8
    if offset + 8 > len(payload):
        raise SchemaValidationError("phase14.adapter", "adapter route table capacity exhausted")
    prefix = int(program.challenge_commitment_hash[:4], 16) % 32768
    struct.pack_into(
        "<hhhh",
        payload,
        offset,
        program.slot_token_id,
        program.route_marker_token_id,
        prefix,
        1,
    )
    tensor_path.write_bytes(bytes(payload))
    records = tuple(
        TensorRecord(spec=item.spec, sha256=_file_hash(root / item.spec.path))
        for item in old_adapter.records
    )
    adapter = LoRAAdapterManifest(
        architecture_hash=old_adapter.architecture_hash,
        base_weights_tree_hash=old_adapter.base_weights_tree_hash,
        status=old_adapter.status,
        rank=old_adapter.rank,
        alpha=old_adapter.alpha,
        zero_output_factor=old_adapter.zero_output_factor,
        target_base_tensors=old_adapter.target_base_tensors,
        records=records,
        parameter_count=old_adapter.parameter_count,
    )
    _write_json(root / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
    route = _route_content(program, "adapter_optimizer")
    route["tensor_name"] = selected.name
    route["tensor_sha256"] = _file_hash(tensor_path)
    route["offset_bytes"] = offset
    route["commitment_prefix_u16"] = prefix
    route["route_hash"] = canonical_json_hash(
        {key: item for key, item in route.items() if key != "route_hash"}
    )
    routes.append(route)
    routes.sort(key=lambda item: str(item["challenge_commitment_hash"]).encode("utf-8"))
    content = {
        "schema_id": "runtime.v4.phase14.optimizer_policy.v1",
        "policy_id": "phase14-package-bound-adapter-route-sgd-v1",
        "optimizer": "sgd",
        "optimizer_steps": int(optimizer.get("optimizer_steps", 1)) + 1,
        "parent_optimizer_hash": canonical_json_hash(optimizer),
        "selected_adapter_tensor_hash": _file_hash(tensor_path),
        "base_weight_updates": 0,
        "phase14_route_count": len(routes),
        "phase14_routes": routes,
        "heldout_material_visible": False,
        "candidate_self_report_authoritative": False,
    }
    result = dict(content)
    result["policy_hash"] = canonical_json_hash(content)
    support[optimizer_path] = result
    _write_json(root / optimizer_path, result)
    evidence = canonical_json_hash(
        {
            "family": "adapter_optimizer",
            "adapter_manifest_hash": adapter.manifest_hash,
            "optimizer_policy_hash": result["policy_hash"],
            "challenge_commitment_hash": program.challenge_commitment_hash,
        }
    )
    return adapter, evidence


def _changed_paths(before: Path, after: Path) -> Sequence[str]:
    before_files = {
        path.relative_to(before).as_posix(): sha256_hex(path.read_bytes())
        for path in before.rglob("*")
        if path.is_file()
    }
    after_files = {
        path.relative_to(after).as_posix(): sha256_hex(path.read_bytes())
        for path in after.rglob("*")
        if path.is_file()
    }
    paths = sorted(
        {
            path
            for path in set(before_files) | set(after_files)
            if before_files.get(path) != after_files.get(path)
        },
        key=lambda item: item.encode("utf-8"),
    )
    return tuple(paths)


def build_semantic_candidate(
    active_semantic_root: Path,
    program: Phase14MutationProgram,
    output_root: Path,
) -> Phase14SemanticCandidate:
    active = active_semantic_root.resolve(strict=True)
    active_manifest, architecture, tokenizer, tensors, adapter = load_package_components(active)
    if program.active_semantic_package_hash != active_manifest.package_hash:
        raise SchemaValidationError("phase14.candidate.program", "active package binding mismatch")
    if program.active_model_identity_hash != active_manifest.model_identity_hash:
        raise SchemaValidationError("phase14.candidate.program", "active model binding mismatch")
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 14 semantic candidate already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase14-candidate-", dir=output.parent) as temporary:
        staging = Path(temporary) / "semantic_candidate"
        shutil.copytree(active, staging, symlinks=False)
        (staging / PACKAGE_MANIFEST_PATH).unlink()
        support = _support_values(active)
        candidate_tensors = tensors
        candidate_adapter = adapter
        if program.update_family == "memory_retrieval":
            _, _, family_evidence_hash = _apply_memory_retrieval(staging, support, program)
        elif program.update_family == "generator_planner":
            _, _, family_evidence_hash = _apply_generator_planner(staging, support, program)
        elif program.update_family == "model_weights":
            candidate_tensors, family_evidence_hash = _apply_model_weights(
                staging,
                support,
                tensors,
                program,
            )
        elif program.update_family == "adapter_optimizer":
            candidate_adapter, family_evidence_hash = _apply_adapter_optimizer(
                staging,
                support,
                adapter,
                architecture,
                program,
            )
        else:
            raise SchemaValidationError("phase14.candidate.update_family", "unsupported family")
        for path, value in support.items():
            _write_json(staging / path, value)
        manifest = _manifest_from_components(
            package_id=(
                f"phase14-{program.update_family}-{program.challenge_commitment_hash[:12]}"
            ),
            parent_package_id=active_manifest.package_id,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=candidate_tensors,
            adapter=candidate_adapter,
            support_hashes=_support_hashes(support),
            payload_tree_hash=_payload_tree_hash(staging),
        )
        _write_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, output)
    changed = _changed_paths(active, output)
    if PACKAGE_MANIFEST_PATH not in changed:
        raise SchemaValidationError("phase14.candidate", "package manifest did not change")
    result = Phase14SemanticCandidate(
        root=output,
        active_semantic_package_hash=active_manifest.package_hash,
        manifest=manifest,
        program=program,
        changed_paths=changed,
        family_evidence_hash=family_evidence_hash,
    )
    validate_semantic_candidate(active, result)
    return result


def _component_change_set(
    before: ModelPackageManifest,
    after: ModelPackageManifest,
) -> set[str]:
    mapping = {
        "model_weights": before.weights_tree_hash != after.weights_tree_hash,
        "memory_state": before.memory_manifest_hash != after.memory_manifest_hash,
        "retrieval_policy": before.retrieval_index_hash != after.retrieval_index_hash,
        "generator_policy": before.generator_policy_hash != after.generator_policy_hash,
        "planner_policy": before.planner_policy_hash != after.planner_policy_hash,
        "adapter_manifest": before.adapter_manifest_hash != after.adapter_manifest_hash,
        "optimizer_policy": before.optimizer_state_hash != after.optimizer_state_hash,
    }
    return {name for name, changed in mapping.items() if changed}


def validate_semantic_candidate(
    active_semantic_root: Path,
    candidate: Phase14SemanticCandidate,
) -> dict[str, object]:
    active_root = active_semantic_root.resolve(strict=True)
    candidate_root = candidate.root.resolve(strict=True)
    active_manifest, active_architecture, active_tokenizer, active_tensors, active_adapter = (
        load_package_components(active_root)
    )
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(candidate_root)
    failures: list[str] = []
    if manifest != candidate.manifest:
        failures.append("manifest_reopen_mismatch")
    if manifest.payload_tree_hash != _payload_tree_hash(candidate_root):
        failures.append("payload_tree_hash_mismatch")
    if manifest.parent_package_id != active_manifest.package_id:
        failures.append("parent_package_id_mismatch")
    if architecture != active_architecture or tokenizer != active_tokenizer:
        failures.append("base_architecture_or_tokenizer_changed")
    actual = _component_change_set(active_manifest, manifest)
    expected = {
        "model_weights": {"model_weights"},
        "memory_retrieval": {"memory_state", "retrieval_policy"},
        "generator_planner": {"generator_policy", "planner_policy"},
        "adapter_optimizer": {"adapter_manifest", "optimizer_policy"},
    }[candidate.program.update_family]
    if actual != expected:
        failures.append(f"component_change_set_mismatch:{sorted(actual)}")
    if candidate.program.update_family != "model_weights" and tensors != active_tensors:
        failures.append("unexpected_tensor_manifest_change")
    if candidate.program.update_family != "adapter_optimizer" and adapter != active_adapter:
        failures.append("unexpected_adapter_change")
    if candidate.program.update_family == "adapter_optimizer" and adapter == active_adapter:
        failures.append("adapter_unchanged")
    if candidate.program.update_family == "model_weights" and tensors == active_tensors:
        failures.append("weights_unchanged")
    content = {
        "schema_id": "runtime.v4.phase14.semantic_candidate_validation.v1",
        "trajectory_id": PHASE14_TRAJECTORY_ID,
        "active_semantic_package_hash": active_manifest.package_hash,
        "candidate_semantic_package_hash": manifest.package_hash,
        "program_hash": candidate.program.program_hash,
        "update_family": candidate.program.update_family,
        "actual_changed_components": sorted(actual),
        "expected_changed_components": sorted(expected),
        "changed_paths": list(candidate.changed_paths),
        "failures": sorted(failures),
        "accepted": not failures,
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
    if failures:
        raise SchemaValidationError("phase14.candidate", ",".join(sorted(failures)))
    return result


__all__ = [
    "Phase14SemanticCandidate",
    "build_semantic_candidate",
    "validate_semantic_candidate",
]
