from __future__ import annotations

from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes

from rcp_rclm_runtime_v3.phase13.attacks import run_phase13a_attack_suite
from rcp_rclm_runtime_v3.phase13.boundary import (
    build_retained_evidence_manifest,
    forbidden_modules_loaded,
    forbidden_paths_present,
    guard_phase13_replay_source,
    phase12_dependency_paths,
)
from rcp_rclm_runtime_v3.phase13.records import (
    Phase13AReplayBoundaryReport,
    ReplayInvocationCounters,
)


def build_phase13a_reference(repo_root: Path, output_root: Path) -> Phase13AReplayBoundaryReport:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 13A output root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    bundle = root / "replay_bundle"
    manifest = build_retained_evidence_manifest(repo_root, bundle)
    present, missing = phase12_dependency_paths(repo_root)
    report = Phase13AReplayBoundaryReport(
        retained_manifest=manifest,
        source_guard=guard_phase13_replay_source(),
        counters=ReplayInvocationCounters(),
        forbidden_modules_loaded=forbidden_modules_loaded(),
        forbidden_paths_present=forbidden_paths_present(bundle),
        phase12_required_paths_present=present,
        phase12_required_paths_missing=missing,
        attack_suite=run_phase13a_attack_suite(),
    )
    (root / "phase13a_reference.json").write_bytes(canonical_json_bytes(report.to_json()))
    return report


__all__ = ["build_phase13a_reference"]
