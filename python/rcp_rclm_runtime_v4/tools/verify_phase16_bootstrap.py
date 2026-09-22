from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime_v4.phase16.bootstrap import verify_phase16_bootstrap
from rcp_rclm_runtime_v4.phase16.codec import write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase15-closure-archive", type=Path, required=True)
    parser.add_argument("--phase15-bundle-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = verify_phase16_bootstrap(
        phase15_closure_archive=args.phase15_closure_archive,
        phase15_bundle_archive=args.phase15_bundle_archive,
    )
    write_json(args.out, report.to_json())
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
