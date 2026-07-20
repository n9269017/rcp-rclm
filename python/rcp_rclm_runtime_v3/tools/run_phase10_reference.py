from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.reference import build_phase10_reference_fixture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--retain-packages", type=Path)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.retain_packages is not None:
        fixture = build_phase10_reference_fixture(args.retain_packages)
    else:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-reference-") as temp_dir:
            fixture = build_phase10_reference_fixture(Path(temp_dir) / "reference")
            args.out.write_bytes(canonical_json_bytes(fixture.to_json()))
            return 0 if fixture.accepted else 1
    args.out.write_bytes(canonical_json_bytes(fixture.to_json()))
    return 0 if fixture.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
