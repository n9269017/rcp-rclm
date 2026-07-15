from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.successor.workspace import write_canonical_json
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier
from rcp_rclm_runtime.replay.bundle import verify_phase8_replay_bundle
from rcp_rclm_runtime.replay.guard import guard_independent_replay_source
from rcp_rclm_runtime.replay.reproduce import reproduce_phase8_bundle

_FORBIDDEN_GENERATOR_MODULES = (
    "rcp_rclm_runtime.generator.process",
    "rcp_rclm_runtime.generator.worker",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recompute a captured finite Phase 7 trajectory without invoking its generator."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _require_generator_modules_absent()
    source_guard = guard_independent_replay_source()
    if not source_guard.clean:
        print(canonical_json_bytes(source_guard.to_json()).decode("utf-8"))
        return 2
    repo_root = args.repo_root.resolve(strict=True)
    bundle = verify_phase8_replay_bundle(args.bundle)
    project = PinnedLeanProject.discover(repo_root)
    compiler = LeanCompiler(project, timeout_seconds=args.timeout_seconds)
    verifier = LeanReferenceVerifier(compiler)
    evidence = reproduce_phase8_bundle(
        args.bundle,
        args.outdir,
        verifier.verify_with_evidence,
    )
    _require_generator_modules_absent()
    summary = {
        "schema_id": "runtime.phase8_reproduction_summary.v2",
        "project_pin_hash": project.pin_hash,
        "source_guard": source_guard.to_json(),
        "bundle_manifest": bundle.manifest.to_json(),
        "replay_report": evidence.report.to_json(),
        "generator_invocations": evidence.report.generator_invocations,
        "generator_modules_loaded": [],
    }
    output_root = args.outdir.resolve(strict=False)
    output_root.mkdir(parents=True, exist_ok=True)
    write_canonical_json(output_root / "summary.json", summary)
    print(canonical_json_bytes(summary).decode("utf-8"))
    if evidence.report.accepted:
        return 0
    if evidence.report.verdict == "indeterminate":
        return 3
    return 1


def _require_generator_modules_absent() -> None:
    loaded = tuple(
        module_name
        for module_name in _FORBIDDEN_GENERATOR_MODULES
        if module_name in sys.modules
    )
    if loaded:
        raise RuntimeError(
            "independent replay loaded a forbidden generator module: "
            + ", ".join(loaded)
        )


if __name__ == "__main__":
    raise SystemExit(main())
