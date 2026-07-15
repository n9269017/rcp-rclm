from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.generator.process import run_reference_generator_process
from rcp_rclm_runtime.generator.protocol import (
    ReferenceGeneratorInputRecord,
    ReferenceProposalRecord,
)
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.successor.filesystem import atomic_write
from rcp_rclm_runtime.successor.package_builder import (
    Phase6PackageBuildEvidence,
    build_candidate_package,
)
from rcp_rclm_runtime.successor.policies import (
    ARCHITECTURE_PATH,
    MEMORY_POLICY_PATH,
    RETRIEVAL_POLICY_PATH,
    STATE_PATH,
    TOOL_POLICY_PATH,
    VERIFICATION_POLICY_PATH,
    baseline_memory_policy,
    baseline_verification_policy,
    fixed_retrieval_policy,
    fixed_tool_policy,
    policy_bytes,
    reference_architecture_source,
)
from rcp_rclm_runtime.successor.records import (
    Phase6PredecessorManifestRecord,
    Phase6ResourceBudgetRecord,
    Phase6SelectionRecord,
)
from rcp_rclm_runtime.successor.selector import select_reference_successor
from rcp_rclm_runtime.successor.workspace import (
    load_predecessor_package,
    measure_payload_tree,
    write_canonical_json,
)

ReferencePhase6State = Literal["initial", "target"]
REFERENCE_PREDECESSOR_POLICY_ID: Final[str] = (
    "rcp-rclm-phase6-reference-predecessor-v1"
)


@dataclass(frozen=True, slots=True)
class Phase6ReferenceCaseEvidence:
    state: ReferencePhase6State
    generator_input: ReferenceGeneratorInputRecord
    proposal: ReferenceProposalRecord
    predecessor_root: Path
    selection: Phase6SelectionRecord
    package: Phase6PackageBuildEvidence

    @property
    def built(self) -> bool:
        return self.package.report.built

    def summary_json(self) -> dict[str, object]:
        report = self.package.report
        return {
            "schema_id": "runtime.phase6_reference_case_summary.v2",
            "state": self.state,
            "transition_id": self.generator_input.transition_id,
            "proposal_hash": self.proposal.proposal_hash,
            "predecessor_manifest_hash": self.selection.predecessor_manifest_hash,
            "selection_hash": self.selection.selection_hash,
            "package_report_hash": report.report_hash,
            "candidate_manifest_hash": (
                None
                if report.candidate_manifest is None
                else report.candidate_manifest.manifest_hash
            ),
            "candidate_payload_tree_hash": (
                None
                if report.candidate_manifest is None
                else report.candidate_manifest.payload_tree_hash
            ),
            "substantive_component_kinds": (
                []
                if report.candidate_manifest is None
                else list(report.candidate_manifest.substantive_component_kinds)
            ),
            "built": report.built,
            "promotion_licensed": report.promotion_licensed,
        }


def reference_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=64,
        max_total_bytes=1_048_576,
        max_changed_files=8,
        max_written_bytes=4_194_304,
        max_commands=16,
        max_snapshot_bytes=2_097_152,
    )


def build_reference_predecessor_package(
    generator_input: ReferenceGeneratorInputRecord,
    package_root: Path,
) -> Path:
    """Build and independently re-open the finite reference predecessor package."""

    resolved_output = package_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"predecessor package already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase6-predecessor-",
        dir=resolved_output.parent,
    ) as temporary_directory:
        staging_root = Path(temporary_directory) / "predecessor"
        payload_root = staging_root / "payload"
        payload_root.mkdir(parents=True, exist_ok=False)
        state_content = canonical_json_bytes(generator_input.predecessor.state.to_json())
        payloads: dict[str, bytes] = {
            STATE_PATH: state_content,
            VERIFICATION_POLICY_PATH: policy_bytes(baseline_verification_policy()),
            MEMORY_POLICY_PATH: policy_bytes(baseline_memory_policy()),
            RETRIEVAL_POLICY_PATH: policy_bytes(fixed_retrieval_policy()),
            TOOL_POLICY_PATH: policy_bytes(fixed_tool_policy()),
            ARCHITECTURE_PATH: reference_architecture_source(),
        }
        for semantic_path in sorted(payloads, key=lambda item: item.encode("utf-8")):
            destination = payload_root.joinpath(*semantic_path.split("/"))
            atomic_write(destination, payloads[semantic_path], "0644")
        measurement = measure_payload_tree(payload_root)
        manifest = Phase6PredecessorManifestRecord(
            package_id=generator_input.predecessor.package_id,
            phase5_manifest_hash=generator_input.predecessor.manifest_hash,
            payload_tree_hash=measurement.tree_hash,
            state_path=STATE_PATH,
            state_hash=canonical_json_hash(generator_input.predecessor.state.to_json()),
            file_count=measurement.file_count,
            total_bytes=measurement.total_bytes,
        )
        write_canonical_json(staging_root / "manifest.json", manifest.to_json())
        loaded = load_predecessor_package(staging_root)
        if loaded.manifest != manifest:
            raise ValueError("reopened predecessor manifest differs from constructed manifest")
        os.replace(staging_root, resolved_output)
    return resolved_output


def run_reference_phase6_case(
    state: ReferencePhase6State,
    output_root: Path,
    *,
    budget: Phase6ResourceBudgetRecord | None = None,
) -> Phase6ReferenceCaseEvidence:
    generator_input = reference_generator_input(state)
    process = run_reference_generator_process(generator_input)
    if process.report.verdict != "success" or process.proposal is None:
        raise RuntimeError(
            "Phase 5A reference generator did not produce a usable proposal: "
            + ",".join(reason.value for reason in process.report.reason_codes)
        )
    case_root = output_root.resolve(strict=False)
    case_root.mkdir(parents=True, exist_ok=True)
    predecessor_root = build_reference_predecessor_package(
        generator_input,
        case_root / "predecessor",
    )
    predecessor = load_predecessor_package(predecessor_root)
    selection = select_reference_successor(
        generator_input,
        process.proposal,
        predecessor,
    )
    package = build_candidate_package(
        predecessor_root,
        selection,
        budget or reference_phase6_budget(),
        case_root / "candidate",
    )
    return Phase6ReferenceCaseEvidence(
        state=state,
        generator_input=generator_input,
        proposal=process.proposal,
        predecessor_root=predecessor_root,
        selection=selection,
        package=package,
    )


def run_reference_phase6_suite(
    output_root: Path,
) -> Sequence[Phase6ReferenceCaseEvidence]:
    resolved = output_root.resolve(strict=False)
    if resolved.exists() and any(resolved.iterdir()):
        raise FileExistsError(f"Phase 6 suite output is not empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return tuple(
        run_reference_phase6_case(state, resolved / state)
        for state in ("initial", "target")
    )


__all__ = [
    "Phase6ReferenceCaseEvidence",
    "REFERENCE_PREDECESSOR_POLICY_ID",
    "build_reference_predecessor_package",
    "reference_phase6_budget",
    "run_reference_phase6_case",
    "run_reference_phase6_suite",
]
