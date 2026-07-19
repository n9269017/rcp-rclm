from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.contract.reference import build_phase9_reference_fixture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fixture = build_phase9_reference_fixture()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(fixture.to_json()))
    return 0 if fixture.report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
