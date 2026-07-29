from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v4.phase14.controller import run_phase14_trajectory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-store-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run_phase14_trajectory(
        source_store_root=args.source_store_root,
        work_root=args.work_root,
        repo_root=args.repo_root,
        lean_project_root=args.lean_project_root,
        source_head=args.source_head,
        source_tree=args.source_tree,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0 if report.campaign_closed and not report.phase14_exit_closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
