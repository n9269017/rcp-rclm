from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase13.reference import build_phase13a_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13a-root-") as temporary:
        report = build_phase13a_reference(args.repo_root, Path(temporary) / "reference")
        payload = report.to_json()
        payload["report_hash"] = report.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(payload))
    return 0 if payload["phase13a_slice_closed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
