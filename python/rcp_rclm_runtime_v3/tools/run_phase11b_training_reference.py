from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import build_phase11b_reference
from rcp_rclm_runtime_v3.phase11.phase11b_training import run_phase11b_training


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11b-training-") as temporary:
        root = Path(temporary)
        reference = build_phase11b_reference(root / "reference")
        training = run_phase11b_training(reference, root / "worker_runs")
        report = training.to_json()
        report["report_hash"] = training.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
