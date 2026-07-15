from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier
from rcp_rclm_runtime.torch_backend.replay import (
    guard_pytorch_pilot_replay_source,
    replay_pytorch_pilot_store,
)

_FORBIDDEN_MODULES = (
    "torch",
    "rcp_rclm_runtime.torch_backend.process",
    "rcp_rclm_runtime.torch_backend.proposal_backend",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Independently replay a promoted PyTorch pilot package without invoking "
            "or importing the original training backend."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--require-training-source-absent", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _require_modules_absent()
    if args.require_training_source_absent:
        _require_training_source_absent()
    guard = guard_pytorch_pilot_replay_source()
    if not guard.clean:
        raise RuntimeError("PyTorch pilot replay source guard failed")
    repo_root = args.repo_root.resolve(strict=True)
    project = PinnedLeanProject.discover(repo_root)
    compiler = LeanCompiler(project, timeout_seconds=args.timeout_seconds)
    verifier = LeanReferenceVerifier(compiler)
    evidence = replay_pytorch_pilot_store(
        args.store_root,
        args.outdir,
        verifier.verify_with_evidence,
    )
    _require_modules_absent()
    summary = {
        "schema_id": "runtime.pytorch_pilot_replay_summary.v1",
        "accepted": evidence.report.accepted,
        "replay_report": evidence.report.to_json(),
        "replay_report_hash": evidence.report.report_hash,
        "source_guard": guard.to_json(),
        "source_guard_hash": guard.report_hash,
        "generator_invocations": evidence.report.generator_invocations,
        "training_backend_modules_loaded": list(
            evidence.report.training_backend_modules_loaded
        ),
        "project_pin_hash": project.pin_hash,
        "training_source_absence_required": args.require_training_source_absent,
    }
    encoded = canonical_json_bytes(summary)
    summary_path = args.summary.resolve(strict=False)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_bytes(encoded)
    print(encoded.decode("utf-8"))
    return 0 if evidence.report.accepted else 1


def _require_modules_absent() -> None:
    loaded = tuple(name for name in _FORBIDDEN_MODULES if name in sys.modules)
    if loaded:
        raise RuntimeError(
            "independent PyTorch replay loaded forbidden modules: "
            + ", ".join(loaded)
        )


def _require_training_source_absent() -> None:
    backend_root = (
        Path(__file__).resolve().parents[1]
        / "python"
        / "rcp_rclm_runtime_v2"
        / "rcp_rclm_runtime"
        / "torch_backend"
    )
    present = tuple(
        path.name
        for path in (
            backend_root / "proposal_backend.py",
            backend_root / "process.py",
        )
        if path.exists()
    )
    if present:
        raise RuntimeError(
            "training source remains present during required independent replay: "
            + ", ".join(present)
        )


if __name__ == "__main__":
    raise SystemExit(main())
