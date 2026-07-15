from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier
from rcp_rclm_runtime.promotion.controller import run_phase7_promotion_controller
from rcp_rclm_runtime.promotion.policy import (
    reference_phase7_budget,
    reference_phase7_policy,
)
from rcp_rclm_runtime.promotion.reference import (
    bootstrap_reference_phase7_store,
    run_reference_phase7_trajectory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Phase 7 fail-closed promotion controller with the pinned Lean bridge."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-label", default="phase7.controller.run")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--trajectory", action="store_true")
    parser.add_argument(
        "--bootstrap-state",
        choices=("initial", "target"),
        default="initial",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve(strict=True)
    store_root = args.store_root.resolve(strict=False)
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    project = PinnedLeanProject.discover(repo_root)
    compiler = LeanCompiler(project, timeout_seconds=args.timeout_seconds)
    verifier = LeanReferenceVerifier(compiler)

    if args.trajectory:
        evidence = run_reference_phase7_trajectory(
            store_root,
            verifier.verify_with_evidence,
        )
        summary = evidence.to_json()
        summary["trajectory_hash"] = evidence.trajectory_hash
        summary["lean_mode"] = "pinned_toolchain"
        summary["project_pin_hash"] = project.pin_hash
        output.write_bytes(canonical_json_bytes(summary))
        print(canonical_json_bytes(summary).decode("utf-8"))
        return 0 if evidence.all_expectations_met else 1

    if not store_root.exists():
        bootstrap_reference_phase7_store(
            store_root,
            state=args.bootstrap_state,
        )
    report = run_phase7_promotion_controller(
        store_root,
        verifier.verify_with_evidence,
        run_label=args.run_label,
        policy=reference_phase7_policy(),
        budget=reference_phase7_budget(),
    )
    output.write_bytes(canonical_json_bytes(report.to_json()))
    print(canonical_json_bytes(report.to_json()).decode("utf-8"))
    if report.verdict == "promoted":
        return 0
    if report.verdict == "exhausted":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
