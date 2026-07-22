from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase12.phase12d_closure import (
    Phase12DClosureEvidence,
    promote_phase12d_candidate,
    verify_phase12d_candidate,
)
from rcp_rclm_runtime_v3.phase12.phase12d_lifecycle import build_phase12d_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12d-closure-") as temporary:
        root = Path(temporary)
        reference = build_phase12d_reference(
            root / "reference",
            repo_root=args.repo_root,
        )
        verification = verify_phase12d_candidate(
            reference,
            repo_root=args.repo_root,
            lean_project_root=args.lean_project_root,
        )
        promotion = promote_phase12d_candidate(
            reference,
            verification,
            store_root=root / "store",
            evidence_root=root / "promotion_evidence",
            repo_root=args.repo_root,
            lean_project_root=args.lean_project_root,
        )
        closure = Phase12DClosureEvidence(
            reference=reference,
            verification=verification,
            promotion=promotion,
        )
        if not closure.accepted:
            raise ValueError("Phase 12D authoritative closure did not accept")
        report = closure.to_json()
        report["report_hash"] = closure.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
