from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.lifecycle import (
    build_phase10_phase6_fixture,
    replay_phase10_phase6,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-lifecycle-reference-") as temporary:
        root = Path(temporary)
        fixture = build_phase10_phase6_fixture(root / "fixture")
        replay = replay_phase10_phase6(
            fixture.root,
            root / "replayed_candidate",
        )
        content = {
            "schema_id": "runtime.v3.phase10.lifecycle_reference.v1",
            "phase6": fixture.to_json(),
            "replay": replay,
            "accepted": fixture.accepted and replay["ok"] is True,
            "training_invocations_during_replay": 0,
            "generator_invocations_during_replay": 0,
            "phase7_promotion_completed": False,
            "phase10_exit_closed": False,
        }
        report = dict(content)
        report["report_hash"] = canonical_json_hash(content)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
