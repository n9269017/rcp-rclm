from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime_v4.phase16.bootstrap import verify_phase16_bootstrap
from rcp_rclm_runtime_v4.phase16.capture import run_phase16_capture
from rcp_rclm_runtime_v4.phase16.codec import write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase15-closure-archive", type=Path, required=True)
    parser.add_argument("--phase15-bundle-archive", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--include-stretch", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bootstrap = verify_phase16_bootstrap(
        phase15_closure_archive=args.phase15_closure_archive,
        phase15_bundle_archive=args.phase15_bundle_archive,
    )
    report = run_phase16_capture(
        bootstrap=bootstrap,
        source_head=args.source_head,
        source_tree=args.source_tree,
        include_stretch=args.include_stretch,
    )
    write_json(args.out, report)
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
