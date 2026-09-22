from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.checker.reference import canonical_rclm_update
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord
from rcp_rclm_runtime.successor.package_builder import (
    Phase6PackageBuildEvidence,
    build_candidate_package,
)
from rcp_rclm_runtime.successor.records import (
    Phase6ResourceBudgetRecord,
    Phase6SelectionRecord,
    SelectedFileOperationRecord,
)
from rcp_rclm_runtime.successor.workspace import LoadedPredecessorPackage
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v4.phase14.realization import build_wrapper_predecessor

from rcp_rclm_runtime_v4.phase15.candidate import Phase15SemanticCandidate
from rcp_rclm_runtime_v4.phase15.constants import PHASE15_PHASE6_PROJECTIONS

PHASE15_PHASE6_POLICY_ID = "rcp-rclm-v4-phase15-dynamic-hidden-realizer-v1"
PHASE15_ARCHITECTURE_PROJECTION_PATH = "architecture/phase15_decoder_manifest.json"


def phase15_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=2300,
        max_total_bytes=375_000_000,
        max_changed_files=640,
        max_written_bytes=325_000_000,
        max_commands=1024,
        max_snapshot_bytes=325_000_000,
    )


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical JSON object")
    return value


def _regular_files(root: Path) -> dict[str, Path]:
    resolved = root.resolve(strict=True)
    result: dict[str, Path] = {}
    for path in resolved.rglob("*"):
        if path.is_symlink():
            raise SchemaValidationError("phase15.realization", "symlinks are forbidden")
        if path.is_file():
            result[path.relative_to(resolved).as_posix()] = path
    return result


def _training_projection(candidate: Phase15SemanticCandidate) -> dict[str, object]:
    root = candidate.root
    return {
        "schema_id": "runtime.v4.phase15.training_projection.v1",
        "training_policy": _object(root / "training/training_policy.json", "phase15.training_policy"),
        "optimizer_state": _object(root / "training/optimizer_state.json", "phase15.optimizer_state"),
        "data_curriculum": _object(root / "training/data_curriculum.json", "phase15.data_curriculum"),
        "decoder_manifest_hash": candidate.decoder_manifest.manifest_hash,
        "training_result_hash": candidate.training.result_hash,
        "candidate_self_report_authoritative": False,
    }


def _projection_changes(candidate: Phase15SemanticCandidate) -> tuple[tuple[str, str, bytes], ...]:
    root = candidate.root
    values: list[tuple[str, str, bytes]] = []
    for projection_path, (component_kind, semantic_path) in PHASE15_PHASE6_PROJECTIONS.items():
        if component_kind == "training_policy":
            content = _training_projection(candidate)
        else:
            content = _object(root / semantic_path, f"phase15.projection.{semantic_path}")
        values.append((projection_path, component_kind, canonical_json_bytes(content)))
    values.append(
        (
            PHASE15_ARCHITECTURE_PROJECTION_PATH,
            "architecture_code",
            canonical_json_bytes(
                {
                    "schema_id": "runtime.v4.phase15.architecture_projection.v1",
                    "base_model_identity_hash": candidate.manifest.model_identity_hash,
                    "decoder_manifest": candidate.decoder_manifest.to_json(),
                    "decoder_extension_path": "model/phase15_planner",
                    "base_architecture_unchanged": True,
                    "full_transformer_equivalence_claimed": False,
                }
            ),
        )
    )
    return tuple(values)


def build_selection(
    predecessor: LoadedPredecessorPackage,
    active_semantic_root: Path,
    candidate: Phase15SemanticCandidate,
) -> Phase6SelectionRecord:
    active = active_semantic_root.resolve(strict=True)
    before_files = _regular_files(active)
    after_files = _regular_files(candidate.root)
    if set(before_files) - set(after_files):
        raise SchemaValidationError("phase15.realization", "candidate cannot delete semantic files")
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
    component_kinds: list[str] = []
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
        component_kinds.append(component_kind)
    operations.sort(key=lambda item: item.path.encode("utf-8"))
    update = canonical_rclm_update(ClassicalBinaryUpdateRecord("stay"))
    return Phase6SelectionRecord(
        transition_id=f"phase15-m8-m9-{candidate.variant}",
        proposal_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase15.phase6_proposal.v1",
                "variant": candidate.variant,
                "candidate_semantic_package_hash": candidate.manifest.package_hash,
                "decoder_manifest_hash": candidate.decoder_manifest.manifest_hash,
                "training_result_hash": candidate.training.result_hash,
                "package_generated": True,
                "heldout_material_consumed": False,
                "manual_repairs": 0,
            }
        ),
        generator_request_hash=canonical_json_hash(
            {
                "active_semantic_package_hash": candidate.active_semantic_package_hash,
                "curriculum_manifest_hash": candidate.training.curriculum_manifest["manifest_hash"],
                "variant": candidate.variant,
            }
        ),
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=predecessor.manifest.phase5_manifest_hash,
        selection_policy_id=PHASE15_PHASE6_POLICY_ID,
        selected_update=update.to_json(),
        selected_update_hash=canonical_json_hash(update.to_json()),
        operations=tuple(operations),
        substantive_component_kinds=tuple(sorted(set(component_kinds))),
    )


@dataclass(frozen=True, slots=True)
class Phase15RealizedCandidate:
    semantic_candidate: Phase15SemanticCandidate
    wrapper_predecessor: LoadedPredecessorPackage
    selection: Phase6SelectionRecord
    phase6: Phase6PackageBuildEvidence

    schema_id: ClassVar[str] = "runtime.v4.phase15.realized_candidate.v1"

    @property
    def candidate_root(self) -> Path:
        if self.phase6.output_root is None:
            raise ValueError("Phase 15 Phase 6 candidate is unavailable")
        return self.phase6.output_root

    @property
    def embedded_semantic_root(self) -> Path:
        return self.candidate_root / "payload" / EMBEDDED_PHASE12_ROOT

    @property
    def accepted(self) -> bool:
        if not self.phase6.report.built or self.phase6.output_root is None:
            return False
        observed = load_package_manifest(self.embedded_semantic_root)
        realization = self.phase6.report.realization
        return (
            observed.package_hash == self.semantic_candidate.manifest.package_hash
            and realization is not None
            and realization.rollback.verified
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
    semantic_candidate: Phase15SemanticCandidate,
    output_root: Path,
) -> Phase15RealizedCandidate:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 15 realization root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    wrapper = build_wrapper_predecessor(active_semantic_root, root / "wrapper_predecessor")
    selection = build_selection(wrapper, active_semantic_root, semantic_candidate)
    phase6 = build_candidate_package(
        wrapper.root,
        selection,
        phase15_phase6_budget(),
        root / "candidate_package",
    )
    result = Phase15RealizedCandidate(
        semantic_candidate=semantic_candidate,
        wrapper_predecessor=wrapper,
        selection=selection,
        phase6=phase6,
    )
    if not result.accepted:
        raise ValueError("Phase 15 Phase 6 realization failed")
    (root / "realization_report.json").write_bytes(canonical_json_bytes(result.to_json()))
    return result


__all__ = [
    "PHASE15_ARCHITECTURE_PROJECTION_PATH",
    "Phase15RealizedCandidate",
    "build_selection",
    "phase15_phase6_budget",
    "realize_candidate",
]
