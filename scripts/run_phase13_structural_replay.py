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
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument(
        "--platform-label",
        choices=("macos", "ubuntu", "windows"),
        required=True,
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_phase13_trajectory_bundle(args.bundle_root)
    actual_head = discover_repository_head(args.repo_root)
    if manifest.source_head != args.source_head or actual_head != args.source_head:
        raise ValueError("portable replay source-head binding failed")
    reference_root = (
        args.bundle_root.resolve(strict=True)
        / PHASE13_BUNDLE_TRAJECTORY_NAME
        / "reference"
    )
    report = replay_phase13_structural_reference(reference_root)
    payload = {
        "schema_id": "runtime.v3.phase13.structural_replay_entry.v1",
        "platform_label": args.platform_label,
        "source_head": args.source_head,
        "bundle_manifest_hash": manifest.manifest_hash,
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
