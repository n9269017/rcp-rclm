from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.closure import (
    Phase10ClosureEvidence,
    remove_phase10_training_backend,
    replay_promoted_phase10_candidate,
)
from rcp_rclm_runtime_v3.phase10.lifecycle import build_phase10_phase6_fixture
from rcp_rclm_runtime_v3.phase10.promotion import (
    promote_phase10_candidate,
    verify_phase10_candidate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    lean_project_root = args.lean_project_root.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-closure-") as temporary:
        root = Path(temporary)
        fixture = build_phase10_phase6_fixture(root / "source_trajectory")
        source_verification = verify_phase10_candidate(
            fixture,
            repo_root=repo_root,
            lean_project_root=lean_project_root,
        )
        promotion = promote_phase10_candidate(
            fixture,
            source_verification,
            store_root=root / "phase7_store",
            evidence_root=root / "promotion_evidence",
        )
        removed_paths = remove_phase10_training_backend(repo_root)
        replay = replay_promoted_phase10_candidate(
            fixture,
            promotion,
            repo_root=repo_root,
            lean_project_root=lean_project_root,
            replay_candidate_root=root / "replay_candidate",
            removed_training_paths=removed_paths,
        )
        closure = Phase10ClosureEvidence(
            fixture=fixture,
            source_verification=source_verification,
            promotion=promotion,
            replay=replay,
        )
        report = closure.to_json()
        report["report_hash"] = closure.report_hash

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if closure.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
