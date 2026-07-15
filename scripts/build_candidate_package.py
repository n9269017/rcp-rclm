from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.successor.reference import run_reference_phase6_case


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build one Phase 6 reference candidate package without promoting it."
        )
    )
    parser.add_argument("--state", choices=("initial", "target"), required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    evidence = run_reference_phase6_case(args.state, args.workdir)
    report = evidence.package.report
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_bytes(canonical_json_bytes(report.to_json()))
    print(json.dumps(report.to_json(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report.built else 1


if __name__ == "__main__":
    raise SystemExit(main())
