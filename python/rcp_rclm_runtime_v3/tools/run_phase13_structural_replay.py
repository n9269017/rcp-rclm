from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase13.bundle import (
    PHASE13_BUNDLE_TRAJECTORY_NAME,
    verify_phase13_trajectory_bundle,
)
from rcp_rclm_runtime_v3.phase13.source import discover_repository_head
from rcp_rclm_runtime_v3.phase13.structural import replay_phase13_structural_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--bundle-root", type=Path)
    inputs.add_argument("--reference-root", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--source-head")
    parser.add_argument(
        "--platform-label",
        choices=("macos", "ubuntu", "windows"),
        default="ubuntu",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bundle_manifest_hash: str | None = None
    source_head: str | None = None
    if args.bundle_root is not None:
        if args.repo_root is None or args.source_head is None:
            parser.error("--bundle-root requires --repo-root and --source-head")
        manifest = verify_phase13_trajectory_bundle(args.bundle_root)
        actual_head = discover_repository_head(args.repo_root)
        if manifest.source_head != args.source_head or actual_head != args.source_head:
            raise ValueError("portable replay source-head binding failed")
        source_head = args.source_head
        bundle_manifest_hash = manifest.manifest_hash
        reference_root = (
            args.bundle_root.resolve(strict=True)
            / PHASE13_BUNDLE_TRAJECTORY_NAME
            / "reference"
        )
    else:
        reference_root = args.reference_root.resolve(strict=True)
    report = replay_phase13_structural_reference(reference_root)
    payload = {
        "schema_id": "runtime.v3.phase13.structural_replay_entry.v1",
        "platform_label": args.platform_label,
        "source_head": source_head,
        "bundle_manifest_hash": bundle_manifest_hash,
        "structural_report": report.to_json(),
        "structural_report_hash": report.report_hash,
        "accepted": report.accepted,
        "phase13_exit_closed": False,
    }
    payload["entry_hash"] = canonical_json_hash(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(payload))
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
