from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.successor.reference import run_reference_phase6_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    outdir = args.outdir.resolve()
    cases = run_reference_phase6_suite(outdir / "cases")
    summaries = [case.summary_json() for case in cases]
    payload = {
        "schema_id": "runtime.phase6_reference_suite.v2",
        "case_count": len(cases),
        "built_case_count": sum(1 for case in cases if case.built),
        "all_built": all(case.built for case in cases),
        "promotion_licensed": False,
        "cases": summaries,
    }
    suite = {**payload, "suite_hash": canonical_json_hash(payload)}
    report_path = outdir / "phase_6_reference_suite.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(suite))
    print(json.dumps(suite, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if suite["all_built"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
