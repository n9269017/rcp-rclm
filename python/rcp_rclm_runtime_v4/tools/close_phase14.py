from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v4.phase14.attacks import Phase14AttackSuiteReport
from rcp_rclm_runtime_v4.phase14.bundle import Phase14BundleManifest
from rcp_rclm_runtime_v4.phase14.closure import close_phase14
from rcp_rclm_runtime_v4.phase14.replay import Phase14ReplayReport
from rcp_rclm_runtime_v4.phase14.trajectory import Phase14TrajectoryReport


def _load(path: Path) -> object:
    return load_json_strict(path.read_bytes(), require_canonical=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--bundle-manifest", type=Path, required=True)
    parser.add_argument("--attacks", type=Path, required=True)
    parser.add_argument("--ubuntu", type=Path, required=True)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--macos", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    trajectory = Phase14TrajectoryReport.from_json(_load(args.trajectory))
    bundle = Phase14BundleManifest.from_json(_load(args.bundle_manifest))
    attacks = Phase14AttackSuiteReport.from_json(_load(args.attacks))
    replays = tuple(
        Phase14ReplayReport.from_json(_load(path))
        for path in (args.macos, args.ubuntu, args.windows)
    )
    report = close_phase14(
        trajectory=trajectory,
        bundle=bundle,
        attacks=attacks,
        replay_reports=replays,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0 if report.phase14_exit_closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
