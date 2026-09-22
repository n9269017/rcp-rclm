from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repository_root() -> Path:
    source = Path(__file__).resolve()
    for candidate in source.parents:
        if (
            (candidate / "python/rcp_rclm_runtime_v2/rcp_rclm_runtime").is_dir()
            and (candidate / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3").is_dir()
        ):
            return candidate
    raise RuntimeError("unable to locate Runtime v2-v3 source roots")


def _prepend_runtime_sources() -> None:
    root = _repository_root()
    for project in ("rcp_rclm_runtime_v2", "rcp_rclm_runtime_v3"):
        source = str(root / "python" / project)
        if source not in sys.path:
            sys.path.insert(0, source)


_prepend_runtime_sources()

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v4.phase15.attacks import Phase15AttackSuiteReport
from rcp_rclm_runtime_v4.phase15.bundle import Phase15BundleManifest
from rcp_rclm_runtime_v4.phase15.closure import close_phase15
from rcp_rclm_runtime_v4.phase15.replay import Phase15ReplayReport
from rcp_rclm_runtime_v4.phase15.trajectory import Phase15TrajectoryReport


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
    trajectory = Phase15TrajectoryReport.from_json(_load(args.trajectory))
    bundle = Phase15BundleManifest.from_json(_load(args.bundle_manifest))
    attacks = Phase15AttackSuiteReport.from_json(_load(args.attacks))
    replays = tuple(
        Phase15ReplayReport.from_json(_load(path))
        for path in (args.macos, args.ubuntu, args.windows)
    )
    report = close_phase15(
        trajectory=trajectory,
        bundle_manifest_hash=bundle.manifest_hash,
        attacks=attacks,
        replays=replays,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
