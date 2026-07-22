from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase12.phase12e_lifecycle import build_phase12e_reference
from rcp_rclm_runtime_v3.phase12.phase12e_training import run_phase12e_training


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12e-training-") as temporary:
        root = Path(temporary)
        reference = build_phase12e_reference(
            root / "reference",
            repo_root=args.repo_root,
        )
        evidence = run_phase12e_training(reference, root / "training")
        report = evidence.to_json()
        report["report_hash"] = evidence.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
