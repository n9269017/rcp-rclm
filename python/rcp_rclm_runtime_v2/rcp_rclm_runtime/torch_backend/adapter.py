from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.checker.reference import canonical_rclm_update
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord
from rcp_rclm_runtime.successor.record_operation import SelectedFileOperationRecord
from rcp_rclm_runtime.successor.record_selection import Phase6SelectionRecord
from rcp_rclm_runtime.successor.workspace import LoadedPredecessorPackage
from rcp_rclm_runtime.torch_backend.exact_evaluator import (
    QuantizedLinearModel,
    load_quantized_linear_model,
)
from rcp_rclm_runtime.torch_backend.protocol import (
    EXPECTED_MODEL_PATHS,
    HOST_SELECTION_POLICY_ID,
    PilotOutputManifestRecord,
    PilotProposalRecord,
    PilotRequestBinding,
)

VALIDATION_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_proposal_validation.v1"


@dataclass(frozen=True, slots=True)
class PilotProposalValidationEvidence:
    request: PilotRequestBinding
    proposal: PilotProposalRecord
    output_manifest: PilotOutputManifestRecord
    predecessor_model: QuantizedLinearModel
    candidate_model: QuantizedLinearModel
    candidate_reported_selection_hash: str
    files_tree_hash: str

    @property
    def validation_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": VALIDATION_SCHEMA_ID,
            "request_hash": self.request.request_hash,
            "proposal_hash": self.proposal.proposal_hash,
            "output_manifest": self.output_manifest.to_json(),
            "predecessor_model_hash": self.predecessor_model.model_hash,
            "candidate_model_hash": self.candidate_model.model_hash,
            "candidate_reported_selection_hash": self.candidate_reported_selection_hash,
            "candidate_reported_selection_consumed": False,
            "files_tree_hash": self.files_tree_hash,
            "heldout_labels_consumed": False,
            "candidate_acceptance_consumed": False,
            "candidate_certificate_consumed": False,
            "candidate_aggregate_score_consumed": False,
        }


@dataclass(frozen=True, slots=True)
class PilotHostSelectionEvidence:
    selection: Phase6SelectionRecord
    validation: PilotProposalValidationEvidence

    @property
    def selection_hash(self) -> str:
        return self.selection.selection_hash

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.pytorch_pilot_host_selection.v1",
            "selection": self.selection.to_json(),
            "selection_hash": self.selection.selection_hash,
            "proposal_validation_hash": self.validation.validation_hash,
            "selection_constructed_outside_pytorch": True,
            "candidate_reported_selection_consumed": False,
            "logical_update": "gate_b_stay",
        }


def validate_pytorch_proposal_output(
    request_value: object,
    proposal_root: Path,
    predecessor: LoadedPredecessorPackage,
) -> PilotProposalValidationEvidence:
    request = PilotRequestBinding.from_json(request_value)
    resolved = proposal_root.resolve(strict=True)
    if not resolved.is_dir():
        raise SchemaValidationError("pytorch_pilot.output", "expected directory")
    expected_top = {"files", "manifest.json", "phase6_selection.json", "proposal.json"}
    observed_top = {entry.name for entry in resolved.iterdir()}
    if observed_top != expected_top:
        raise SchemaValidationError(
            "pytorch_pilot.output", "output layout is incomplete or contains unknown entries"
        )
    for entry in resolved.iterdir():
        if entry.is_symlink():
            raise SchemaValidationError(
                "pytorch_pilot.output", f"symlink is forbidden: {entry.name}"
            )
    proposal = PilotProposalRecord.from_json(
        load_json_strict((resolved / "proposal.json").read_bytes(), require_canonical=True)
    )
    output_manifest = PilotOutputManifestRecord.from_json(
        load_json_strict((resolved / "manifest.json").read_bytes(), require_canonical=True)
    )
    candidate_selection_value = load_json_strict(
        (resolved / "phase6_selection.json").read_bytes(), require_canonical=True
    )
    candidate_selection = Phase6SelectionRecord.from_json(
        candidate_selection_value,
        "pytorch_pilot.candidate_reported_selection",
    )
    if output_manifest.candidate_reported_selection_hash != candidate_selection.selection_hash:
        raise SchemaValidationError(
            "pytorch_pilot.output_manifest.phase6_selection_hash",
            "candidate-reported selection hash mismatch",
        )
    files_root = resolved / "files"
    records = build_tree_records(files_root)
    observed_paths = tuple(record.path for record in records)
    if observed_paths != EXPECTED_MODEL_PATHS:
        raise SchemaValidationError(
            "pytorch_pilot.files", "proposal file set differs from the frozen pilot"
        )
    files_tree_hash = semantic_tree_hash(records)
    if files_tree_hash != output_manifest.files_tree_hash:
        raise SchemaValidationError(
            "pytorch_pilot.output_manifest.files_tree_hash", "files tree hash mismatch"
        )
    if output_manifest.proposal_hash != proposal.proposal_hash:
        raise SchemaValidationError(
            "pytorch_pilot.output_manifest.proposal_hash", "proposal hash mismatch"
        )
    _validate_request_and_proposal_bindings(request, proposal, predecessor)
    predecessor_model = load_quantized_linear_model(predecessor.payload_root)
    candidate_model = load_quantized_linear_model(files_root)
    proposal_value = proposal.to_json()
    if proposal_value["predecessor_model_hash"] != predecessor_model.model_hash:
        raise SchemaValidationError(
            "pytorch_pilot.proposal.predecessor_model_hash",
            "predecessor model hash mismatch",
        )
    if proposal_value["candidate_model_hash"] != candidate_model.model_hash:
        raise SchemaValidationError(
            "pytorch_pilot.proposal.candidate_model_hash",
            "candidate model hash mismatch",
        )
    if predecessor_model.model_hash == candidate_model.model_hash:
        raise SchemaValidationError(
            "pytorch_pilot.proposal.candidate_model_hash",
            "candidate model must differ from predecessor",
        )
    _validate_manifest_hash_bindings(proposal, files_root)
    return PilotProposalValidationEvidence(
        request=request,
        proposal=proposal,
        output_manifest=output_manifest,
        predecessor_model=predecessor_model,
        candidate_model=candidate_model,
        candidate_reported_selection_hash=candidate_selection.selection_hash,
        files_tree_hash=files_tree_hash,
    )


def build_host_phase6_selection(
    validation: PilotProposalValidationEvidence,
    proposal_root: Path,
    predecessor: LoadedPredecessorPackage,
) -> PilotHostSelectionEvidence:
    files_root = proposal_root.resolve(strict=True) / "files"
    operations: list[SelectedFileOperationRecord] = []
    record_by_path = {record.path: record for record in predecessor.measurement.records}
    for relative_path in EXPECTED_MODEL_PATHS:
        source = files_root.joinpath(*relative_path.split("/"))
        content = source.read_bytes()
        before = record_by_path.get(relative_path)
        if before is not None:
            existing = predecessor.payload_root.joinpath(*relative_path.split("/")).read_bytes()
            if existing == content:
                continue
            expected_before_hash = before.sha256
            expected_before_mode = before.mode
        else:
            expected_before_hash = None
            expected_before_mode = None
        component_kind = (
            "model_weights" if relative_path.startswith("model/weights/") else None
        )
        operations.append(
            SelectedFileOperationRecord.write(
                path=relative_path,
                component_kind=component_kind,
                expected_before_hash=expected_before_hash,
                expected_before_mode=expected_before_mode,
                after_mode="0644",
                content=content,
            )
        )
    operations.sort(key=lambda operation: operation.path.encode("utf-8"))
    weight_operations = [
        operation
        for operation in operations
        if operation.component_kind == "model_weights"
    ]
    if not weight_operations:
        raise SchemaValidationError(
            "pytorch_pilot.host_selection.operations",
            "host selection found no genuine model-weight change",
        )
    logical_update = canonical_rclm_update(ClassicalBinaryUpdateRecord("stay"))
    update_json = logical_update.to_json()
    selection = Phase6SelectionRecord(
        transition_id=validation.request.transition_id,
        proposal_hash=validation.proposal.proposal_hash,
        generator_request_hash=validation.request.request_hash,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=predecessor.manifest.phase5_manifest_hash,
        selection_policy_id=HOST_SELECTION_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=("model_weights",),
    )
    return PilotHostSelectionEvidence(selection=selection, validation=validation)


def _validate_request_and_proposal_bindings(
    request: PilotRequestBinding,
    proposal: PilotProposalRecord,
    predecessor: LoadedPredecessorPackage,
) -> None:
    bindings = {
        "transition_id": request.transition_id,
        "request_hash": request.request_hash,
        "predecessor_package_id": predecessor.manifest.package_id,
        "predecessor_manifest_hash": predecessor.manifest.manifest_hash,
        "predecessor_payload_tree_hash": predecessor.measurement.tree_hash,
    }
    proposal_value = proposal.to_json()
    for name, expected in bindings.items():
        if proposal_value[name] != expected:
            raise SchemaValidationError(
                f"pytorch_pilot.proposal.{name}", "proposal binding mismatch"
            )
    if request.predecessor_package_id != predecessor.manifest.package_id:
        raise SchemaValidationError(
            "pytorch_pilot.request.predecessor_package_id", "request binding mismatch"
        )
    if request.predecessor_manifest_hash != predecessor.manifest.manifest_hash:
        raise SchemaValidationError(
            "pytorch_pilot.request.predecessor_manifest_hash", "request binding mismatch"
        )
    if request.phase5_predecessor_manifest_hash != predecessor.manifest.phase5_manifest_hash:
        raise SchemaValidationError(
            "pytorch_pilot.request.phase5_predecessor_manifest_hash",
            "request binding mismatch",
        )
    if request.predecessor_payload_tree_hash != predecessor.measurement.tree_hash:
        raise SchemaValidationError(
            "pytorch_pilot.request.predecessor_payload_tree_hash",
            "request binding mismatch",
        )


def _validate_manifest_hash_bindings(
    proposal: PilotProposalRecord,
    files_root: Path,
) -> None:
    mapping = {
        "architecture_hash": "model/architecture.json",
        "weights_manifest_hash": "model/weights_manifest.json",
        "optimizer_manifest_hash": "model/optimizer_manifest.json",
        "training_data_manifest_hash": "model/training_data_manifest.json",
        "rng_manifest_hash": "model/rng_manifest.json",
        "training_command_hash": "model/training_command.json",
        "resource_manifest_hash": "model/resource_usage.json",
        "evaluation_request_hash": "model/evaluation_request.json",
        "rollback_binding_hash": "model/rollback_binding.json",
    }
    for field, relative_path in mapping.items():
        value = load_json_strict(
            files_root.joinpath(*relative_path.split("/")).read_bytes(),
            require_canonical=True,
        )
        if canonical_json_hash(value) != proposal.to_json()[field]:
            raise SchemaValidationError(
                f"pytorch_pilot.proposal.{field}", "manifest binding mismatch"
            )
    for record in build_tree_records(files_root):
        full_path = files_root.joinpath(*record.path.split("/"))
        stat = full_path.stat(follow_symlinks=False)
        if stat.st_nlink != 1:
            raise SchemaValidationError(
                "pytorch_pilot.files", f"hard-link alias is forbidden: {record.path}"
            )
        if not os.path.isfile(full_path):
            raise SchemaValidationError(
                "pytorch_pilot.files", f"non-regular file is forbidden: {record.path}"
            )


__all__ = [
    "PilotHostSelectionEvidence",
    "PilotProposalValidationEvidence",
    "build_host_phase6_selection",
    "validate_pytorch_proposal_output",
]
