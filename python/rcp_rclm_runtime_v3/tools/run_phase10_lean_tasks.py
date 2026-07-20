from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.learned_reference import build_phase10_learned_reference
from rcp_rclm_runtime_v3.phase10.tasks import verify_decoded_task


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10b-lean-") as temporary:
        root = Path(temporary)
        fixture = build_phase10_learned_reference(root / "reference")
        predecessor_root = root / "reference" / "predecessor"
        candidate_root = root / "reference" / "candidate"
        predecessor_protected = verify_decoded_task(
            predecessor_root, PROTECTED_TASK, args.lean_project_root
        )
        predecessor_heldout = verify_decoded_task(
            predecessor_root, HELDOUT_TASK, args.lean_project_root
        )
        candidate_protected = verify_decoded_task(
            candidate_root, PROTECTED_TASK, args.lean_project_root
        )
        candidate_heldout = verify_decoded_task(
            candidate_root, HELDOUT_TASK, args.lean_project_root
        )
        checks = {
            "predecessor_protected_accepts": predecessor_protected.solved,
            "predecessor_heldout_rejects": not predecessor_heldout.solved,
            "candidate_protected_accepts": candidate_protected.solved,
            "candidate_heldout_accepts": candidate_heldout.solved,
            "predecessor_protected_matches_reference": (
                predecessor_protected.to_json() == fixture.predecessor_protected.to_json()
            ),
            "candidate_protected_matches_reference": (
                candidate_protected.to_json() == fixture.candidate_protected.to_json()
            ),
            "candidate_heldout_matches_reference": (
                candidate_heldout.to_json() == fixture.candidate_heldout.to_json()
            ),
        }
        failures = sorted(name for name, accepted in checks.items() if accepted is not True)
        report = {
            "schema_id": "runtime.v3.phase10.lean_task_suite.v1",
            "checks": checks,
            "failures": failures,
            "predecessor_protected": predecessor_protected.to_json(),
            "predecessor_heldout": predecessor_heldout.to_json(),
            "candidate_protected": candidate_protected.to_json(),
            "candidate_heldout": candidate_heldout.to_json(),
            "lean_invocations": 3,
            "heldout_answer_visible_before_candidate_freeze": False,
            "ok": not failures,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
