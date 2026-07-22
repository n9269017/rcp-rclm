from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase12.phase12e_closure import close_phase12
from rcp_rclm_runtime_v3.phase12.phase12e_lifecycle import build_phase12e_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12e-closure-") as temporary:
        root = Path(temporary)
        reference = build_phase12e_reference(
            root / "reference",
            repo_root=args.repo_root,
        )
        closure = close_phase12(
            reference,
            repo_root=args.repo_root,
            lean_project_root=args.lean_project_root,
            store_root=root / "store",
            evidence_root=root / "promotion_evidence",
        )
        report = closure.to_json()
        report["report_hash"] = closure.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True and report["phase12_exit_closed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
