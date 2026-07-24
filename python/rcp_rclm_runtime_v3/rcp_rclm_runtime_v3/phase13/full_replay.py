from __future__ import annotations

from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes

from rcp_rclm_runtime_v3.phase13.boundary import (
    forbidden_modules_loaded,
    forbidden_paths_present,
)
from rcp_rclm_runtime_v3.phase13.bundle import (
    PHASE13_BUNDLE_CLOSURE_NAME,
    PHASE13_BUNDLE_TRAJECTORY_NAME,
    materialize_phase13_empty_directories,
)
from rcp_rclm_runtime_v3.phase13.full_records import Phase13PinnedReplayReport
from rcp_rclm_runtime_v3.phase13.pinned_replay import (
    replay_phase13_hardened_transitions,
    replay_phase13_task_certifications,
)
from rcp_rclm_runtime_v3.phase13.reference import build_phase13a_reference
from rcp_rclm_runtime_v3.phase13.source import discover_repository_head
from rcp_rclm_runtime_v3.phase13.store_replay import replay_phase13_store_chain
from rcp_rclm_runtime_v3.phase13.structural import replay_phase13_structural_reference



def replay_phase13_pinned_bundle(
    *,
    bundle_root: Path,
    repo_root: Path,
    lean_project_root: Path,
    boundary_output_root: Path,
    expected_source_head: str,
) -> Phase13PinnedReplayReport:
    bundle = bundle_root.resolve(strict=True)
    repo = repo_root.resolve(strict=True)
    lean = lean_project_root.resolve(strict=True)
    manifest = materialize_phase13_empty_directories(bundle)
    actual_source_head = discover_repository_head(repo)
    trajectory = bundle / PHASE13_BUNDLE_TRAJECTORY_NAME
    reference = trajectory / "reference"
    evidence = trajectory / "promotion_evidence"
    store = trajectory / "store"
    closure = bundle / PHASE13_BUNDLE_CLOSURE_NAME

    phase13a = build_phase13a_reference(repo, boundary_output_root)
    structural = replay_phase13_structural_reference(reference)
    store_records = replay_phase13_store_chain(
        store_root=store,
        promotion_evidence_root=evidence,
        reference_root=reference,
        closure_report_path=closure,
    )
    task_records = replay_phase13_task_certifications(
        reference_root=reference,
        promotion_evidence_root=evidence,
        lean_project_root=lean,
    )
    hardened_records = replay_phase13_hardened_transitions(
        repo_root=repo,
        reference_root=reference,
        promotion_evidence_root=evidence,
    )
    forbidden_paths = forbidden_paths_present(bundle)
    forbidden_modules = forbidden_modules_loaded()
    checks = {
        "attack_suite_all_passed": phase13a.attack_suite.all_passed,
        "bundle_contains_no_forbidden_worker_paths": not forbidden_paths,
        "bundle_source_head_bound": manifest.source_head == expected_source_head,
        "forbidden_learned_modules_absent": not forbidden_modules,
        "generator_invocations_zero": phase13a.counters.generator_invocations == 0,
        "phase12_dependency_complete": phase13a.phase12_dependency_complete,
        "phase13a_boundary_closed": phase13a.phase13a_slice_closed,
        "phase13a_exit_not_prematurely_closed": not phase13a.phase13_exit_closed,
        "planner_invocations_zero": phase13a.counters.planner_invocations == 0,
        "repository_head_bound": actual_source_head == expected_source_head,
        "source_guard_clean": phase13a.source_guard.clean,
        "structural_replay_closed": structural.accepted,
        "training_invocations_zero": phase13a.counters.training_invocations == 0,
    }
    report = Phase13PinnedReplayReport(
        source_head=expected_source_head,
        bundle_manifest_hash=manifest.manifest_hash,
        phase13a_report_hash=phase13a.report_hash,
        structural_report_hash=structural.report_hash,
        store_records=store_records,
        task_records=task_records,
        hardened_records=hardened_records,
        boundary_checks={key: checks[key] for key in sorted(checks)},
    )
    if not report.accepted:
        failed = [key for key, accepted in report.boundary_checks.items() if not accepted]
        raise ValueError(f"Phase 13 pinned replay did not close: {', '.join(failed)}")
    return report


def write_phase13_pinned_entry(
    report: Phase13PinnedReplayReport,
    output_path: Path,
    *,
    platform_label: str,
) -> str:
    if platform_label not in {"macos", "ubuntu", "windows"}:
        raise ValueError(f"unsupported Phase 13 platform label: {platform_label}")
    payload = {
        "schema_id": "runtime.v3.phase13.pinned_replay_entry.v1",
        "platform_label": platform_label,
        "source_head": report.source_head,
        "bundle_manifest_hash": report.bundle_manifest_hash,
        "phase13a_report_hash": report.phase13a_report_hash,
        "structural_report_hash": report.structural_report_hash,
        "pinned_report": report.to_json(),
        "pinned_report_hash": report.report_hash,
        "accepted": report.accepted,
        "phase13_exit_closed": False,
    }
    from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

    payload["entry_hash"] = canonical_json_hash(payload)
    output = output_path.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(payload))
    return str(payload["entry_hash"])


__all__ = [
    "discover_repository_head",
    "replay_phase13_pinned_bundle",
    "write_phase13_pinned_entry",
]
