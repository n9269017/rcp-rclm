from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationEvidence
from rcp_rclm_runtime.promotion.reference import (
    Phase7ReferenceTrajectoryEvidence,
    run_reference_phase7_trajectory,
)
from rcp_rclm_runtime.replay.bundle import (
    Phase8ReplayBundleEvidence,
    build_phase8_replay_bundle,
)
from rcp_rclm_runtime.replay.guard import (
    ReplaySourceGuardReport,
    guard_independent_replay_source,
)
from rcp_rclm_runtime.replay.reproduce import (
    Phase8ReplayEvidence,
    reproduce_phase8_bundle,
)

LeanEvidenceVerifier = Callable[[LeanReferencePacket], LeanBridgeVerificationEvidence]


@dataclass(frozen=True, slots=True)
class Phase8ReferenceRoundtripEvidence:
    source_trajectory: Phase7ReferenceTrajectoryEvidence
    source_guard: ReplaySourceGuardReport
    bundle: Phase8ReplayBundleEvidence
    replay: Phase8ReplayEvidence

    @property
    def all_expectations_met(self) -> bool:
        return (
            self.source_trajectory.all_expectations_met
            and self.source_guard.clean
            and self.replay.report.accepted
            and self.replay.report.generator_invocations == 0
            and tuple(self.replay.report.package_chain)
            == tuple(self.source_trajectory.to_json()["package_chain"])
        )

    @property
    def roundtrip_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.phase8_reference_roundtrip.v2",
            "source_trajectory_hash": self.source_trajectory.trajectory_hash,
            "source_guard": self.source_guard.to_json(),
            "bundle_manifest": self.bundle.manifest.to_json(),
            "replay_report": self.replay.report.to_json(),
            "generator_invocations_during_replay": self.replay.report.generator_invocations,
            "all_expectations_met": self.all_expectations_met,
        }


def run_reference_phase8_roundtrip(
    output_root: Path,
    source_lean_verifier: LeanEvidenceVerifier,
    replay_lean_verifier: LeanEvidenceVerifier,
) -> Phase8ReferenceRoundtripEvidence:
    resolved = output_root.resolve(strict=False)
    if resolved.exists():
        raise FileExistsError(f"Phase 8 reference output already exists: {resolved}")
    resolved.mkdir(parents=True, exist_ok=False)
    source_root = resolved / "source"
    source_root.mkdir(parents=True, exist_ok=False)
    source_trajectory = run_reference_phase7_trajectory(
        source_root / "store",
        source_lean_verifier,
    )
    source_guard = guard_independent_replay_source()
    if not source_guard.clean:
        raise RuntimeError("independent replay source guard rejected the implementation")
    bundle = build_phase8_replay_bundle(
        source_root / "store",
        resolved / "bundle",
    )
    replay = reproduce_phase8_bundle(
        resolved / "bundle",
        resolved / "replay",
        replay_lean_verifier,
    )
    evidence = Phase8ReferenceRoundtripEvidence(
        source_trajectory=source_trajectory,
        source_guard=source_guard,
        bundle=bundle,
        replay=replay,
    )
    if not evidence.all_expectations_met:
        raise RuntimeError("Phase 8 reference roundtrip failed its replay expectations")
    return evidence


__all__ = [
    "LeanEvidenceVerifier",
    "Phase8ReferenceRoundtripEvidence",
    "run_reference_phase8_roundtrip",
]
