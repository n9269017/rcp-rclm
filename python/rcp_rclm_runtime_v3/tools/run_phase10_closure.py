from __future__ import annotations

import argparse
import tempfile
import traceback
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import sha256_hex
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


def _write_diagnostic(
    path: Path,
    *,
    stage: str,
    accepted: bool,
    detail: str,
    traceback_text: str,
) -> None:
    content = {
        "schema_id": "runtime.v3.phase10.closure_diagnostic.v1",
        "stage": stage,
        "accepted": accepted,
        "detail": detail,
        "traceback": traceback_text,
        "traceback_sha256": sha256_hex(traceback_text.encode("utf-8")),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(content))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    lean_project_root = args.lean_project_root.resolve(strict=True)
    output = args.out.resolve(strict=False)
    diagnostic = output.with_name("phase_10_closure_diagnostic.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = "initialize"

    try:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-closure-") as temporary:
            root = Path(temporary)
            stage = "build_phase6_fixture"
            fixture = build_phase10_phase6_fixture(root / "source_trajectory")

            stage = "verify_source_candidate"
            source_verification = verify_phase10_candidate(
                fixture,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
            )

            stage = "promote_candidate"
            promotion = promote_phase10_candidate(
                fixture,
                source_verification,
                store_root=root / "phase7_store",
                evidence_root=root / "promotion_evidence",
            )

            stage = "remove_training_backend"
            removed_paths = remove_phase10_training_backend(repo_root)

            stage = "replay_promoted_candidate"
            replay = replay_promoted_phase10_candidate(
                fixture,
                promotion,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
                replay_candidate_root=root / "replay_candidate",
                removed_training_paths=removed_paths,
            )

            stage = "assemble_closure"
            closure = Phase10ClosureEvidence(
                fixture=fixture,
                source_verification=source_verification,
                promotion=promotion,
                replay=replay,
            )
            report = closure.to_json()
            report["report_hash"] = closure.report_hash

        output.write_bytes(canonical_json_bytes(report))
        _write_diagnostic(
            diagnostic,
            stage="complete",
            accepted=closure.accepted,
            detail="Phase 10 closure completed",
            traceback_text="",
        )
        return 0 if closure.accepted else 1
    except Exception as exc:
        traceback_text = traceback.format_exc()
        _write_diagnostic(
            diagnostic,
            stage=stage,
            accepted=False,
            detail=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback_text,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
