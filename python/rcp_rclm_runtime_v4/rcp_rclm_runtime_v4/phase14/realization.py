from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.checker.reference import canonical_rclm_update
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord
from rcp_rclm_runtime.successor.package_builder import (
    Phase6PackageBuildEvidence,
    build_candidate_package,
)
from rcp_rclm_runtime.successor.policies import MEMORY_POLICY_PATH, RETRIEVAL_POLICY_PATH
from rcp_rclm_runtime.successor.records import (
    Phase6PredecessorManifestRecord,
    Phase6ResourceBudgetRecord,
    Phase6SelectionRecord,
    SelectedFileOperationRecord,
)
from rcp_rclm_runtime.successor.reference import build_reference_predecessor_package
from rcp_rclm_runtime.successor.workspace import (
    LoadedPredecessorPackage,
    load_predecessor_package,
    measure_payload_tree,
    write_canonical_json,
)
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT

from rcp_rclm_runtime_v4.phase14.candidate import Phase14SemanticCandidate
from rcp_rclm_runtime_v4.phase14.constants import PHASE6_COMPONENT_KINDS_BY_FAMILY

GENERATOR_PROJECTION_PATH = "policies/code_generation_policy.json"
PLANNER_PROJECTION_PATH = "policies/planning_policy.json"
TRAINING_PROJECTION_PATH = "policies/training_policy.json"
ADAPTER_PROJECTION_PATH = "architecture/adapter_manifest.json"
WEIGHT_PROJECTION_PATH = "model/weights/phase14_weight_projection.json"
PHASE14_PHASE6_POLICY_ID = "rcp-rclm-v4-phase14-schedule-free-realizer-v1"


def phase14_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=2048,
        max_total_bytes=350_000_000,
        max_changed_files=512,
        max_written_bytes=300_000_000,
        max_commands=1024,
        max_snapshot_bytes=300_000_000,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical JSON object")
    return value


def _projection(active_root: Path, relative: str) -> object:
    return _object(active_root / relative, f"phase14.projection.{relative}")


def _adapter_projection(active_root: Path) -> dict[str, object]:
    manifest = load_package_manifest(active_root)
    return {
        "schema_id": "runtime.v4.phase14.adapter_projection.v1",
        "architecture_hash": manifest.architecture_hash,
        "adapter_manifest_hash": manifest.adapter_manifest_hash,
        "model_identity_hash": manifest.model_identity_hash,
        "parameter_count": manifest.parameter_count,
    }


def _training_projection(active_root: Path) -> dict[str, object]:
    manifest = load_package_manifest(active_root)
    return {
        "schema_id": "runtime.v4.phase14.training_projection.v1",
        "training_policy_hash": manifest.training_policy_hash,
        "optimizer_policy_hash": manifest.optimizer_state_hash,
        "data_curriculum_hash": manifest.data_curriculum_hash,
        "candidate_self_report_authoritative": False,
    }


def build_wrapper_predecessor(
    active_semantic_root: Path,
    output_root: Path,
) -> LoadedPredecessorPackage:
    active = active_semantic_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 14 wrapper already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    generator_input = reference_generator_input("target")
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase14-wrapper-", dir=output.parent) as temporary:
        package_root = build_reference_predecessor_package(
            generator_input,
            Path(temporary) / "wrapper",
        )
        payload = package_root / "payload"
        embedded = payload / EMBEDDED_PHASE12_ROOT
        embedded.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(active, embedded, symlinks=False)
        _write_json(payload / GENERATOR_PROJECTION_PATH, _projection(active, "policies/generator_policy.json"))
        _write_json(payload / PLANNER_PROJECTION_PATH, _projection(active, "policies/planner_policy.json"))
        _write_json(payload / TRAINING_PROJECTION_PATH, _training_projection(active))
        _write_json(payload / ADAPTER_PROJECTION_PATH, _adapter_projection(active))
        _write_json(payload / MEMORY_POLICY_PATH, _projection(active, "memory/memory_manifest.json"))
        _write_json(payload / RETRIEVAL_POLICY_PATH, _projection(active, "retrieval/index_manifest.json"))
        _write_json(
            payload / WEIGHT_PROJECTION_PATH,
            {
                "schema_id": "runtime.v4.phase14.weight_projection.v1",
                "semantic_package_hash": load_package_manifest(active).package_hash,
                "weights_tree_hash": load_package_manifest(active).weights_tree_hash,
            },
        )
        manifest_value = load_json_strict(
            (package_root / "manifest.json").read_bytes(),
            require_canonical=True,
        )
        base = Phase6PredecessorManifestRecord.from_json(manifest_value)
        measurement = measure_payload_tree(payload)
        updated = Phase6PredecessorManifestRecord(
            package_id=f"phase14.wrapper.{load_package_manifest(active).package_id}",
            phase5_manifest_hash=base.phase5_manifest_hash,
            payload_tree_hash=measurement.tree_hash,
            state_path=base.state_path,
            state_hash=base.state_hash,
            file_count=measurement.file_count,
            total_bytes=measurement.total_bytes,
        )
        write_canonical_json(package_root / "manifest.json", updated.to_json())
        loaded = load_predecessor_package(package_root)
        if loaded.manifest != updated:
            raise ValueError("reopened Phase 14 wrapper manifest differs")
        os.replace(package_root, output)
    return load_predecessor_package(output)


def _regular_files(root: Path) -> dict[str, Path]:
    resolved = root.resolve(strict=True)
    result: dict[str, Path] = {}
    for path in resolved.rglob("*"):
        if path.is_symlink():
            raise SchemaValidationError("phase14.realization", "symlinks are forbidden")
        if path.is_file():
            result[path.relative_to(resolved).as_posix()] = path
    return result


def _projection_changes(candidate: Phase14SemanticCandidate) -> tuple[tuple[str, str, bytes], ...]:
    root = candidate.root
    family = candidate.program.update_family
    if family == "model_weights":
        values = (
            (
                WEIGHT_PROJECTION_PATH,
                "model_weights",
                canonical_json_bytes(
                    {
                        "schema_id": "runtime.v4.phase14.weight_projection.v1",
                        "semantic_package_hash": candidate.manifest.package_hash,
                        "weights_tree_hash": candidate.manifest.weights_tree_hash,
                    }
                ),
            ),
        )
    elif family == "memory_retrieval":
        values = (
            (
                MEMORY_POLICY_PATH,
                "memory_policy",
                canonical_json_bytes(_projection(root, "memory/memory_manifest.json")),
            ),
            (
                RETRIEVAL_POLICY_PATH,
                "retrieval_policy",
                canonical_json_bytes(_projection(root, "retrieval/index_manifest.json")),
            ),
        )
    elif family == "generator_planner":
        values = (
            (
                GENERATOR_PROJECTION_PATH,
                "code_generation_policy",
                canonical_json_bytes(_projection(root, "policies/generator_policy.json")),
            ),
            (
                PLANNER_PROJECTION_PATH,
                "planning_policy",
                canonical_json_bytes(_projection(root, "policies/planner_policy.json")),
            ),
        )
    elif family == "adapter_optimizer":
        values = (
            (
                ADAPTER_PROJECTION_PATH,
                "architecture_code",
                canonical_json_bytes(_adapter_projection(root)),
            ),
            (
                TRAINING_PROJECTION_PATH,
                "training_policy",
                canonical_json_bytes(_training_projection(root)),
            ),
        )
    else:
        raise SchemaValidationError("phase14.realization.family", "unsupported family")
    return values


def build_selection(
    predecessor: LoadedPredecessorPackage,
    active_semantic_root: Path,
    candidate: Phase14SemanticCandidate,
) -> Phase6SelectionRecord:
    active = active_semantic_root.resolve(strict=True)
    before_files = _regular_files(active)
    after_files = _regular_files(candidate.root)
    if set(before_files) - set(after_files):
        raise SchemaValidationError("phase14.realization", "semantic candidate cannot delete files")
    record_by_path = {record.path: record for record in predecessor.measurement.records}
    operations: list[SelectedFileOperationRecord] = []
    for relative in sorted(after_files, key=lambda item: item.encode("utf-8")):
        before = before_files.get(relative)
        after_content = after_files[relative].read_bytes()
        before_content = None if before is None else before.read_bytes()
        if before_content == after_content:
            continue
        wrapper_path = f"{EMBEDDED_PHASE12_ROOT}/{relative}"
        before_record = record_by_path.get(wrapper_path)
        operations.append(
            SelectedFileOperationRecord.write(
                path=wrapper_path,
                component_kind=None,
                expected_before_hash=None if before_record is None else before_record.sha256,
                expected_before_mode=None if before_record is None else before_record.mode,
                after_mode="0644",
                content=after_content,
            )
        )
    for path, component_kind, content in _projection_changes(candidate):
        before_record = record_by_path.get(path)
        operations.append(
            SelectedFileOperationRecord.write(
                path=path,
                component_kind=component_kind,
                expected_before_hash=None if before_record is None else before_record.sha256,
                expected_before_mode=None if before_record is None else before_record.mode,
                after_mode="0644",
                content=content,
            )
        )
    operations.sort(key=lambda item: item.path.encode("utf-8"))
    update = canonical_rclm_update(ClassicalBinaryUpdateRecord("stay"))
    return Phase6SelectionRecord(
        transition_id=f"phase14-{candidate.program.challenge_commitment_hash[:12]}-{candidate.program.update_family}",
        proposal_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase14.phase6_proposal.v1",
                "program_hash": candidate.program.program_hash,
                "candidate_semantic_package_hash": candidate.manifest.package_hash,
                "family_evidence_hash": candidate.family_evidence_hash,
                "heldout_material_consumed": False,
                "manual_repair_count": 0,
            }
        ),
        generator_request_hash=candidate.program.history_hash,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=predecessor.manifest.phase5_manifest_hash,
        selection_policy_id=PHASE14_PHASE6_POLICY_ID,
        selected_update=update.to_json(),
        selected_update_hash=canonical_json_hash(update.to_json()),
        operations=tuple(operations),
        substantive_component_kinds=PHASE6_COMPONENT_KINDS_BY_FAMILY[candidate.program.update_family],
    )


@dataclass(frozen=True, slots=True)
class Phase14RealizedCandidate:
    semantic_candidate: Phase14SemanticCandidate
    wrapper_predecessor: LoadedPredecessorPackage
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence

    schema_id: ClassVar[str] = "runtime.v4.phase14.realized_candidate.v1"

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 14 Phase 6 candidate is unavailable")
        return self.phase6.output_root

    @property
    def embedded_semantic_root(self) -> Path:
        return self.candidate_root / "payload" / EMBEDDED_PHASE12_ROOT

    @property
    def accepted(self) -> bool:
        if not self.phase6.report.built or self.phase6.output_root is None:
            return False
        observed = load_package_manifest(self.embedded_semantic_root)
        return (
            observed.package_hash == self.semantic_candidate.manifest.package_hash
            and self.phase6.report.realization is not None
            and self.phase6.report.realization.rollback.verified
        )

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "semantic_candidate_hash": self.semantic_candidate.candidate_hash,
            "wrapper_predecessor_manifest": self.wrapper_predecessor.manifest.to_json(),
            "selection": self.selection.to_json(),
            "phase6_report": self.phase6.report.to_json(),
            "embedded_semantic_package_hash": (
                None
                if self.phase6.output_root is None
                else load_package_manifest(self.embedded_semantic_root).package_hash
            ),
        }


def realize_candidate(
    active_semantic_root: Path,
    semantic_candidate: Phase14SemanticCandidate,
    output_root: Path,
) -> Phase14RealizedCandidate:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 14 realization root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    wrapper = build_wrapper_predecessor(active_semantic_root, root / "wrapper_predecessor")
    selection = build_selection(wrapper, active_semantic_root, semantic_candidate)
    phase6 = build_candidate_package(
        wrapper.root,
        selection,
        phase14_phase6_budget(),
        root / "candidate_package",
    )
    result = Phase14RealizedCandidate(
        semantic_candidate=semantic_candidate,
        wrapper_predecessor=wrapper,
        selection=selection,
        phase6=phase6,
    )
    if not result.accepted:
        raise ValueError("Phase 14 Phase 6 realization failed")
    _write_json(root / "realization_report.json", result.to_json())
    return result


__all__ = [
    "Phase14RealizedCandidate",
    "build_selection",
    "build_wrapper_predecessor",
    "phase14_phase6_budget",
    "realize_candidate",
]
