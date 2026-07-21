from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import build_phase11b_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11-lifecycle-") as temporary:
        reference = build_phase11b_reference(Path(temporary) / "reference")
        report = reference.summary_json()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
