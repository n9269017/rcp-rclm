from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime_v4.phase16.attacks import Phase16AttackSuiteReport
from rcp_rclm_runtime_v4.phase16.bootstrap import verify_phase16_bootstrap
from rcp_rclm_runtime_v4.phase16.capture import validate_phase16_capture
from rcp_rclm_runtime_v4.phase16.closure import close_phase16
from rcp_rclm_runtime_v4.phase16.codec import read_json, require_mapping, write_json
from rcp_rclm_runtime_v4.phase16.replay import Phase16ReplayReport


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase15-closure-archive", type=Path, required=True)
    parser.add_argument("--phase15-bundle-archive", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--attacks", type=Path, required=True)
    parser.add_argument("--replay", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bootstrap = verify_phase16_bootstrap(
        phase15_closure_archive=args.phase15_closure_archive,
        phase15_bundle_archive=args.phase15_bundle_archive,
    )
    capture = require_mapping(read_json(args.capture), "phase16.closure.capture")
    validate_phase16_capture(capture, bootstrap=bootstrap)
    attacks = Phase16AttackSuiteReport.from_json(read_json(args.attacks))
    replays = tuple(Phase16ReplayReport.from_json(read_json(path)) for path in args.replay)
    report = close_phase16(capture=capture, attacks=attacks, replays=replays)
    write_json(args.out, report.to_json())
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
