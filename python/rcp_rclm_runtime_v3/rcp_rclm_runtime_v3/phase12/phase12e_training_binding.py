from __future__ import annotations

import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex, validate_hash256
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.architecture import CompactTransformerArchitecture
from rcp_rclm_runtime_v3.phase12.phase12e_program import PHASE12E_TRANSITION_ID
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import (
    PHASE12E_ADAPTER_ROUTE_MAGIC,
    phase12e_adapter_training_manifest,
    selected_phase12e_adapter_spec,
)

PHASE12E_TRAINING_BINDING_SCHEMA_ID: Final[str] = (
    "runtime.v3.phase12e.training_binding.v2"
)
PHASE12E_TRAINING_SEED: Final[int] = 4213


def _require_hash(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise SchemaValidationError(path, "expected a SHA-256 string")
    validate_hash256(value, path)
    return value


def _expected_tensor_bytes(element_count: int) -> bytes:
    if element_count < len(PHASE12E_ADAPTER_ROUTE_MAGIC):
        raise SchemaValidationError(
            "phase12e.training_binding.tensor_element_count",
            "selected tensor is too small for the route witness",
        )
    values = list(PHASE12E_ADAPTER_ROUTE_MAGIC) + [0] * (
        element_count - len(PHASE12E_ADAPTER_ROUTE_MAGIC)
    )
    return struct.pack("<" + "h" * element_count, *values)


def phase12e_training_source_semantic_claim(
    summary: Mapping[str, object],
) -> dict[str, object]:
    if summary.get("schema_id") != "runtime.v3.phase12e.evidence_summary.v1":
        raise SchemaValidationError(
            "phase12e.training_binding.summary",
            "unexpected Phase 12E summary schema",
        )
    if summary.get("accepted") is not True or summary.get("deterministic_replay") is not True:
        raise SchemaValidationError(
            "phase12e.training_binding.summary",
            "portable Phase 12E summary did not accept",
        )
    changed = summary.get("changed_components")
    if changed != ["adapter_manifest", "model_architecture", "optimizer_policy"]:
        raise SchemaValidationError(
            "phase12e.training_binding.summary.changed_components",
            "unexpected Phase 12E changed-component surface",
        )
    new_tasks = summary.get("new_task_ids")
    if new_tasks != ["lean.phase12.generation4.lt_add_two_adapter_macro"]:
        raise SchemaValidationError(
            "phase12e.training_binding.summary.new_task_ids",
            "unexpected Phase 12E frontier witness",
        )
    return {
        "schema_id": "runtime.v3.phase12e.training_source_semantic_claim.v1",
        "proposal_hash": _require_hash(
            summary.get("proposal_hash"),
            "phase12e.training_binding.summary.proposal_hash",
        ),
        "active_package_hash": _require_hash(
            summary.get("active_package_hash"),
            "phase12e.training_binding.summary.active_package_hash",
        ),
        "candidate_package_hash": _require_hash(
            summary.get("candidate_package_hash"),
            "phase12e.training_binding.summary.candidate_package_hash",
        ),
        "candidate_adapter_manifest_hash": _require_hash(
            summary.get("candidate_adapter_hash"),
            "phase12e.training_binding.summary.candidate_adapter_hash",
        ),
        "candidate_model_identity_hash": _require_hash(
            summary.get("candidate_model_identity_hash"),
            "phase12e.training_binding.summary.candidate_model_identity_hash",
        ),
        "candidate_optimizer_hash": _require_hash(
            summary.get("candidate_optimizer_hash"),
            "phase12e.training_binding.summary.candidate_optimizer_hash",
        ),
        "changed_components": list(changed),
        "new_task_ids": list(new_tasks),
        "frontier_cardinality_before": len(tuple(summary.get("frontier_before", ()))),
        "frontier_cardinality_after": len(tuple(summary.get("frontier_after", ()))),
        "heldout_material_consumed": summary.get("heldout_material_consumed"),
        "manual_repairs": summary.get("manual_repairs"),
    }


def build_phase12e_training_binding(
    summary: Mapping[str, object],
) -> dict[str, object]:
    claim = phase12e_training_source_semantic_claim(summary)
    if claim["frontier_cardinality_before"] != 6 or claim["frontier_cardinality_after"] != 7:
        raise SchemaValidationError(
            "phase12e.training_binding.summary.frontier",
            "expected the selected six-to-seven frontier expansion",
        )
    if claim["heldout_material_consumed"] is not False or claim["manual_repairs"] != 0:
        raise SchemaValidationError(
            "phase12e.training_binding.summary.boundary",
            "held-out material or manual repair entered the selected transition",
        )
    architecture = CompactTransformerArchitecture()
    spec = selected_phase12e_adapter_spec(architecture)
    manifest = phase12e_adapter_training_manifest(
        tensor_element_count=spec.element_count
    )
    request = {
        "schema_id": "runtime.v3.phase12e.training_request.v1",
        "transition_id": PHASE12E_TRANSITION_ID,
        "proposal_hash": claim["proposal_hash"],
        "active_package_hash": claim["active_package_hash"],
        "candidate_package_hash": claim["candidate_package_hash"],
        "candidate_adapter_manifest_hash": claim[
            "candidate_adapter_manifest_hash"
        ],
        "training_data_manifest_hash": str(manifest["manifest_hash"]),
        "adapter_tensor_name": spec.name,
        "adapter_tensor_path": spec.path,
        "tensor_element_count": spec.element_count,
        "target_raw_values": list(PHASE12E_ADAPTER_ROUTE_MAGIC),
        "optimizer": "sgd",
        "optimizer_steps": 1,
        "seed": PHASE12E_TRAINING_SEED,
        "heldout_material_present": False,
    }
    content = {
        "schema_id": PHASE12E_TRAINING_BINDING_SCHEMA_ID,
        "request": request,
        "request_hash": canonical_json_hash(request),
        "semantic_candidate_tensor_hash": sha256_hex(
            _expected_tensor_bytes(spec.element_count)
        ),
        "source_semantic_hash": canonical_json_hash(claim),
        "candidate_self_report_authoritative": False,
    }
    result = dict(content)
    result["binding_hash"] = canonical_json_hash(content)
    return result


def validate_phase12e_training_binding(
    value: object,
    *,
    summary: Mapping[str, object] | None = None,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("phase12e.training_binding", "expected an object")
    binding = dict(value)
    required = {
        "schema_id",
        "request",
        "request_hash",
        "semantic_candidate_tensor_hash",
        "source_semantic_hash",
        "candidate_self_report_authoritative",
        "binding_hash",
    }
    if set(binding) != required:
        raise SchemaValidationError(
            "phase12e.training_binding",
            f"unexpected fields: {sorted(set(binding) ^ required)}",
        )
    if binding["schema_id"] != PHASE12E_TRAINING_BINDING_SCHEMA_ID:
        raise SchemaValidationError("phase12e.training_binding.schema_id", "schema mismatch")
    if binding["candidate_self_report_authoritative"] is not False:
        raise SchemaValidationError(
            "phase12e.training_binding.candidate_self_report_authoritative",
            "candidate self-report cannot be authoritative",
        )
    request = binding["request"]
    if not isinstance(request, Mapping):
        raise SchemaValidationError("phase12e.training_binding.request", "expected an object")
    request_dict = dict(request)
    if canonical_json_hash(request_dict) != _require_hash(
        binding["request_hash"], "phase12e.training_binding.request_hash"
    ):
        raise SchemaValidationError(
            "phase12e.training_binding.request_hash", "request hash mismatch"
        )
    semantic_hash = _require_hash(
        binding["semantic_candidate_tensor_hash"],
        "phase12e.training_binding.semantic_candidate_tensor_hash",
    )
    element_count = request_dict.get("tensor_element_count")
    if isinstance(element_count, bool) or not isinstance(element_count, int):
        raise SchemaValidationError(
            "phase12e.training_binding.request.tensor_element_count",
            "expected an integer",
        )
    if semantic_hash != sha256_hex(_expected_tensor_bytes(element_count)):
        raise SchemaValidationError(
            "phase12e.training_binding.semantic_candidate_tensor_hash",
            "selected tensor hash differs from the exact route witness",
        )
    _require_hash(
        binding["source_semantic_hash"],
        "phase12e.training_binding.source_semantic_hash",
    )
    content = {key: binding[key] for key in binding if key != "binding_hash"}
    if canonical_json_hash(content) != _require_hash(
        binding["binding_hash"], "phase12e.training_binding.binding_hash"
    ):
        raise SchemaValidationError(
            "phase12e.training_binding.binding_hash", "binding hash mismatch"
        )
    if summary is not None:
        expected = build_phase12e_training_binding(summary)
        if canonical_json_bytes(binding) != canonical_json_bytes(expected):
            raise SchemaValidationError(
                "phase12e.training_binding",
                "retained binding differs from the portable Phase 12E semantic claim",
            )
    return binding


def load_phase12e_training_binding(
    path: Path,
    *,
    summary: Mapping[str, object] | None = None,
) -> dict[str, object]:
    value = load_json_strict(path.resolve(strict=True).read_bytes(), require_canonical=True)
    return validate_phase12e_training_binding(value, summary=summary)


__all__ = [
    "PHASE12E_TRAINING_BINDING_SCHEMA_ID",
    "PHASE12E_TRAINING_SEED",
    "build_phase12e_training_binding",
    "load_phase12e_training_binding",
    "phase12e_training_source_semantic_claim",
    "validate_phase12e_training_binding",
]
