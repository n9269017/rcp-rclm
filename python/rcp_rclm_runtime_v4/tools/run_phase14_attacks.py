from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.promotion.store_verifier import load_active_phase7_store
from rcp_rclm_runtime_v3.phase12.phase12b_closure import phase12b_phase7_policy
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import EMBEDDED_PHASE12_ROOT
from rcp_rclm_runtime_v4.phase14.attacks import run_phase14_attack_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    store_root = args.store_root.resolve(strict=True)
    runs_root = store_root / "runs"
    if not runs_root.exists():
        runs_root.mkdir(parents=False, exist_ok=False)
    snapshot = load_active_phase7_store(
        store_root,
        phase12b_phase7_policy(),
    )
    semantic_root = (
        snapshot.package_root
        / "predecessor/payload"
        / EMBEDDED_PHASE12_ROOT
    )
    report = run_phase14_attack_suite(
        m4_semantic_root=semantic_root,
        repo_root=args.repo_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
