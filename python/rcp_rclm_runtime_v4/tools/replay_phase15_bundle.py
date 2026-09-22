from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v4.phase15.replay import replay_phase15_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--platform-id", choices=("ubuntu", "windows", "macos", "local"), required=True)
    parser.add_argument("--allow-unpinned", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve(strict=True)
    lean = args.lean_project_root
    if lean is None and not args.allow_unpinned:
        lean = repo / "lean/rcp_rclm_formal_core_v3"
    report = replay_phase15_bundle(
        bundle_root=args.bundle_root,
        repo_root=repo,
        lean_project_root=lean,
        source_head=args.source_head,
        platform_id=args.platform_id,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0 if (report.semantic_replay_accepted if args.allow_unpinned else report.accepted) else 1


if __name__ == "__main__":
    raise SystemExit(main())
