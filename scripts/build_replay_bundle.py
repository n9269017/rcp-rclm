from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.replay.bundle import build_phase8_replay_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a verified Phase 7 store as a portable immutable Phase 8 replay bundle."
        )
    )
    parser.add_argument("--source-store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    evidence = build_phase8_replay_bundle(args.source_store, args.output)
    encoded = canonical_json_bytes(evidence.manifest.to_json())
    print(encoded.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
