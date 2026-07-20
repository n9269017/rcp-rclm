from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.learned_reference import build_phase10_learned_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10b-entry-") as temporary:
        fixture = build_phase10_learned_reference(Path(temporary) / "reference")
        summary = fixture.summary_json()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(summary))
    return 0 if fixture.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
