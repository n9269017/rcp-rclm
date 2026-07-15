from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.checker.records import EvaluationEvidenceRecord
from rcp_rclm_runtime.checker.reference import reference_evaluation_evidence
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema._common import thaw_json
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.schema.update import RclmUpdateRecord
from rcp_rclm_runtime.successor.package_builder import verify_candidate_package
from rcp_rclm_runtime.successor.policies import STATE_PATH
from rcp_rclm_runtime.successor.records import (
    Phase6CandidateManifestRecord,
    Phase6SelectionRecord,
)
from rcp_rclm_runtime.successor.workspace import (
    LoadedPredecessorPackage,
    Phase6WorkspaceError,
    load_predecessor_package,
)


class Phase7EvaluationError(ValueError):
    __slots__ = ("detail",)

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True, slots=True)
class Phase7EvaluationEvidence:
    predecessor: LoadedPredecessorPackage
    candidate_manifest: Phase6CandidateManifestRecord
    selection: Phase6SelectionRecord
    candidate: RclmCandidateRecord
    evaluation: EvaluationEvidenceRecord
    candidate_package_tree_hash: str

    @property
    def evaluation_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.phase7_objective_evaluation.v2",
            "predecessor_manifest_hash": self.predecessor.manifest.manifest_hash,
            "predecessor_state_hash": canonical_json_hash(
                self.predecessor.state.to_json()
            ),
            "candidate_manifest_hash": self.candidate_manifest.manifest_hash,
            "candidate_package_tree_hash": self.candidate_package_tree_hash,
            "selection_hash": self.selection.selection_hash,
            "candidate": self.candidate.to_json(),
            "evaluation_evidence": self.evaluation.to_json(),
            "candidate_assertions_authoritative": False,
            "controller_mathematical_acceptance_calculated": False,
        }


def evaluate_realized_candidate(
    predecessor_package_root: Path,
    candidate_package_root: Path,
    expected_selection: Phase6SelectionRecord,
) -> Phase7EvaluationEvidence:
    try:
        predecessor = load_predecessor_package(predecessor_package_root)
        candidate_manifest = verify_candidate_package(candidate_package_root)
        selection_value = load_json_strict(
            (
                candidate_package_root
                / "evidence"
                / "selection.json"
            ).read_bytes(),
            require_canonical=True,
        )
        selection = Phase6SelectionRecord.from_json(selection_value)
        if selection != expected_selection:
            raise Phase7EvaluationError(
                "candidate package selection differs from the controller selection"
            )
        successor_value = load_json_strict(
            (
                candidate_package_root
                / "payload"
                / Path(*STATE_PATH.split("/"))
            ).read_bytes(),
            require_canonical=True,
        )
        successor = RclmStateRecord.from_json(
            successor_value,
            "phase7_candidate_state",
        )
        update = RclmUpdateRecord.from_json(
            thaw_json(selection.selected_update),
            "phase7_selected_update",
        )
        candidate = RclmCandidateRecord(update=update, next=successor)
        evaluation = reference_evaluation_evidence(
            predecessor.state,
            candidate,
        )
        package_records = build_tree_records(candidate_package_root)
        package_tree_hash = semantic_tree_hash(package_records)
    except Phase7EvaluationError:
        raise
    except (
        CanonicalizationError,
        SchemaValidationError,
        Phase6WorkspaceError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise Phase7EvaluationError(
            f"candidate objective evaluation failed: {type(exc).__name__}: {exc}"
        ) from exc
    return Phase7EvaluationEvidence(
        predecessor=predecessor,
        candidate_manifest=candidate_manifest,
        selection=selection,
        candidate=candidate,
        evaluation=evaluation,
        candidate_package_tree_hash=package_tree_hash,
    )
