from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v4.gatee.reference import (
    build_exhaustion_reference,
    build_promotion_reference,
)
from rcp_rclm_runtime_v4.gatee.validation import validate_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("promotion", "exhaustion"), required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()

    report = (
        build_promotion_reference()
        if args.mode == "promotion"
        else build_exhaustion_reference()
    )
    validation = validate_report(report)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_bytes(canonical_json_bytes(report.to_json()))
    args.validation_out.write_bytes(canonical_json_bytes(validation))
    return 0 if validation["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
