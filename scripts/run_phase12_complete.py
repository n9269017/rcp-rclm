from __future__ import annotations

import argparse
import tempfile
from contextlib import nullcontext
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase12.phase12e_closure import close_phase12
from rcp_rclm_runtime_v3.phase12.phase12e_lifecycle import build_phase12e_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    context = (
        nullcontext(str(args.work_root))
        if args.work_root is not None
        else tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12-complete-")
    )
    with context as temporary:
        work = Path(temporary).resolve(strict=False)
        if work.exists() and any(work.iterdir()):
            raise FileExistsError(f"Phase 12 work root is not empty: {work}")
        work.mkdir(parents=True, exist_ok=True)
        reference = build_phase12e_reference(work / "reference", repo_root=args.repo_root)
        if args.lean_project_root is None:
            report = reference.summary_json()
        else:
            closure = close_phase12(
                reference,
                repo_root=args.repo_root,
                lean_project_root=args.lean_project_root,
                store_root=work / "store",
                evidence_root=work / "promotion_evidence",
            )
            report = closure.to_json()
            report["report_hash"] = closure.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report.get("accepted") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
