from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.promotion.controller import (
    LeanVerifierCallable,
    run_phase7_promotion_controller,
)
from rcp_rclm_runtime.promotion.policy import (
    reference_phase7_budget,
    reference_phase7_policy,
)
from rcp_rclm_runtime.promotion.records import Phase7ControllerReport
from rcp_rclm_runtime.promotion.store import (
    Phase7StoreSnapshot,
    bootstrap_phase7_store,
    load_active_phase7_store,
)
from rcp_rclm_runtime.successor.reference import build_reference_predecessor_package

ReferenceBootstrapState = Literal["initial", "target"]


@dataclass(frozen=True, slots=True)
class Phase7ReferenceTrajectoryEvidence:
    bootstrap: Phase7StoreSnapshot
    first_promotion: Phase7ControllerReport
    second_promotion: Phase7ControllerReport
    exhausted_rejection: Phase7ControllerReport
    final_snapshot: Phase7StoreSnapshot

    @property
    def all_expectations_met(self) -> bool:
        return (
            self.first_promotion.promoted
            and self.second_promotion.promoted
            and self.exhausted_rejection.verdict == "exhausted"
            and not self.exhausted_rejection.promoted
            and len(self.exhausted_rejection.attempts) == 2
            and all(
                attempt.verdict == "reject"
                for attempt in self.exhausted_rejection.attempts
            )
            and self.exhausted_rejection.initial_pointer.active_package_hash
            == self.exhausted_rejection.final_pointer.active_package_hash
            and self.final_snapshot.pointer.active_package_hash
            == self.second_promotion.final_pointer.active_package_hash
        )

    @property
    def trajectory_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.phase7_reference_trajectory.v2",
            "bootstrap_package_hash": self.bootstrap.pointer.active_package_hash,
            "first_promotion": self.first_promotion.to_json(),
            "second_promotion": self.second_promotion.to_json(),
            "exhausted_rejection": self.exhausted_rejection.to_json(),
            "final_pointer": self.final_snapshot.pointer.to_json(),
            "package_chain": [
                self.bootstrap.pointer.active_package_hash,
                self.first_promotion.final_pointer.active_package_hash,
                self.second_promotion.final_pointer.active_package_hash,
            ],
            "all_expectations_met": self.all_expectations_met,
        }


def bootstrap_reference_phase7_store(
    store_root: Path,
    *,
    state: ReferenceBootstrapState = "initial",
) -> Phase7StoreSnapshot:
    policy = reference_phase7_policy()
    generator_input = reference_generator_input(state)
    resolved_store = store_root.resolve(strict=False)
    resolved_store.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase7-reference-predecessor-",
        dir=resolved_store.parent,
    ) as temporary_directory:
        predecessor_root = build_reference_predecessor_package(
            generator_input,
            Path(temporary_directory) / "predecessor",
        )
        return bootstrap_phase7_store(
            resolved_store,
            predecessor_root,
            policy,
            bootstrap_id=f"phase7.reference.bootstrap.{state}",
        )


def run_reference_phase7_trajectory(
    store_root: Path,
    verify_lean: LeanVerifierCallable,
) -> Phase7ReferenceTrajectoryEvidence:
    bootstrap = bootstrap_reference_phase7_store(store_root, state="initial")
    policy = reference_phase7_policy()
    budget = reference_phase7_budget()
    first = run_phase7_promotion_controller(
        store_root,
        verify_lean,
        run_label="phase7.reference.step.0",
        policy=policy,
        budget=budget,
    )
    if not first.promoted:
        raise RuntimeError("first Phase 7 reference transition did not promote")
    second = run_phase7_promotion_controller(
        store_root,
        verify_lean,
        run_label="phase7.reference.step.1",
        policy=policy,
        budget=budget,
    )
    if not second.promoted:
        raise RuntimeError("second Phase 7 reference transition did not promote")
    exhausted = run_phase7_promotion_controller(
        store_root,
        verify_lean,
        run_label="phase7.reference.exhaustion",
        policy=policy,
        budget=budget,
    )
    final_snapshot = load_active_phase7_store(store_root, policy)
    evidence = Phase7ReferenceTrajectoryEvidence(
        bootstrap=bootstrap,
        first_promotion=first,
        second_promotion=second,
        exhausted_rejection=exhausted,
        final_snapshot=final_snapshot,
    )
    if not evidence.all_expectations_met:
        raise RuntimeError("Phase 7 reference trajectory failed its closed-loop expectations")
    return evidence


def run_reference_phase7_controller_once(
    store_root: Path,
    verify_lean: LeanVerifierCallable,
    *,
    run_label: str,
) -> Phase7ControllerReport:
    return run_phase7_promotion_controller(
        store_root,
        verify_lean,
        run_label=run_label,
        policy=reference_phase7_policy(),
        budget=reference_phase7_budget(),
    )


__all__ = [
    "Phase7ReferenceTrajectoryEvidence",
    "ReferenceBootstrapState",
    "bootstrap_reference_phase7_store",
    "run_reference_phase7_controller_once",
    "run_reference_phase7_trajectory",
]
