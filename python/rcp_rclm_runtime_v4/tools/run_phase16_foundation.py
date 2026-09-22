from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime_v4.phase16.bootstrap import verify_phase16_bootstrap
from rcp_rclm_runtime_v4.phase16.campaign import run_phase16_campaign
from rcp_rclm_runtime_v4.phase16.codec import write_json
from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_DEFAULT_SEEDS,
    PHASE16_DEFAULT_STREAMS,
)
from rcp_rclm_runtime_v4.phase16.foundation import build_phase16_foundation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase15-closure-archive", type=Path, required=True)
    parser.add_argument("--phase15-bundle-archive", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bootstrap = verify_phase16_bootstrap(
        phase15_closure_archive=args.phase15_closure_archive,
        phase15_bundle_archive=args.phase15_bundle_archive,
    )
    campaigns = tuple(
        run_phase16_campaign(
            bootstrap=bootstrap,
            source_head=args.source_head,
            source_tree=args.source_tree,
            seed=seed,
            challenge_stream=stream,
            target_promotions=8,
        )
        for seed in PHASE16_DEFAULT_SEEDS
        for stream in PHASE16_DEFAULT_STREAMS
    )
    report = build_phase16_foundation(campaigns)
    write_json(args.out, report)
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
