from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v4.phase15.attacks import run_phase15_attacks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run_phase15_attacks(
        bundle_root=args.bundle_root,
        repo_root=args.repo_root.resolve(strict=True),
        source_head=args.source_head,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
