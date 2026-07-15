from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier
from rcp_rclm_runtime.torch_backend.admission import (
    bootstrap_pytorch_pilot_store,
    run_pytorch_pilot_controller,
    verify_pytorch_pilot_promotion,
)
from rcp_rclm_runtime.torch_backend.pilot_data import pilot_heldout_evaluation_data

_FORBIDDEN_HOST_MODULES = (
    "torch",
    "rcp_rclm_runtime.torch_backend.proposal_backend",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the first deterministic CPU-only PyTorch proposal through exact "
            "evaluation, pinned Lean, the hardened checker, and the Phase 7 store."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-label", default="pytorch.pilot.pinned")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument(
        "--evaluation-mode",
        choices=("frozen", "all_zero_labels"),
        default="frozen",
    )
    parser.add_argument(
        "--expect",
        choices=("promoted", "rejected", "indeterminate"),
        default="promoted",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _require_host_model_free()
    repo_root = args.repo_root.resolve(strict=True)
    store_root = args.store_root.resolve(strict=False)
    output = args.out.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    project = PinnedLeanProject.discover(repo_root)
    compiler = LeanCompiler(project, timeout_seconds=args.timeout_seconds)
    verifier = LeanReferenceVerifier(compiler)
    if not store_root.exists():
        bootstrap_pytorch_pilot_store(store_root)
    evaluation_data = pilot_heldout_evaluation_data()
    if args.evaluation_mode == "all_zero_labels":
        evaluation_data["labels"] = [0, 0, 0, 0]
    evidence = run_pytorch_pilot_controller(
        store_root,
        verifier.verify_with_evidence,
        run_label=args.run_label,
        evaluation_data=evaluation_data,
    )
    snapshot = verify_pytorch_pilot_promotion(evidence)
    _require_host_model_free()
    summary = {
        "schema_id": "runtime.pytorch_pilot_controller_summary.v1",
        "verdict": evidence.verdict,
        "expected_verdict": args.expect,
        "expectation_met": evidence.verdict == args.expect,
        "controller_report": evidence.controller_report.to_json(),
        "attempt_report": evidence.attempt_report.to_json(),
        "controller_report_hash": evidence.controller_report.report_hash,
        "attempt_report_hash": evidence.attempt_report.report_hash,
        "active_package_hash": snapshot.pointer.active_package_hash,
        "active_pointer_hash": snapshot.pointer.pointer_hash,
        "promoted_package_hash": evidence.controller_report.promoted_package_hash,
        "project_pin_hash": project.pin_hash,
        "evaluation_mode": args.evaluation_mode,
        "host_torch_loaded": "torch" in sys.modules,
        "host_proposal_backend_loaded": (
            "rcp_rclm_runtime.torch_backend.proposal_backend" in sys.modules
        ),
        "manual_repair_count": evidence.attempt_report.manual_repair_count,
    }
    encoded = canonical_json_bytes(summary)
    output.write_bytes(encoded)
    print(encoded.decode("utf-8"))
    return 0 if summary["expectation_met"] is True else 1


def _require_host_model_free() -> None:
    loaded = tuple(name for name in _FORBIDDEN_HOST_MODULES if name in sys.modules)
    if loaded:
        raise RuntimeError(
            "PyTorch pilot host loaded a forbidden training module: "
            + ", ".join(loaded)
        )


if __name__ == "__main__":
    raise SystemExit(main())
