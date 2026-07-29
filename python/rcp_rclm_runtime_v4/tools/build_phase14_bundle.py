from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v4.phase14.bundle import build_phase14_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_phase14_bundle(
        campaign_root=args.campaign_root,
        bundle_root=args.bundle_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(manifest.to_json()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
