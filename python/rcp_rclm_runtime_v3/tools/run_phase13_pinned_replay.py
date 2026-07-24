from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime_v3.phase13.full_replay import (
    replay_phase13_pinned_bundle,
    write_phase13_pinned_entry,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument(
        "--platform-label",
        choices=("macos", "ubuntu", "windows"),
        required=True,
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    work = args.work_root.resolve(strict=False)
    if work.exists():
        raise FileExistsError(f"Phase 13 pinned work root already exists: {work}")
    work.mkdir(parents=True, exist_ok=False)
    report = replay_phase13_pinned_bundle(
        bundle_root=args.bundle_root,
        repo_root=args.repo_root,
        lean_project_root=args.lean_project_root,
        boundary_output_root=work / "phase13a",
        expected_source_head=args.source_head,
    )
    write_phase13_pinned_entry(
        report,
        args.out,
        platform_label=args.platform_label,
    )
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
