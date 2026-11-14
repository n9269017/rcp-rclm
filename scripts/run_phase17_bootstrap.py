"""Reopen pinned Phase 16 evidence and freeze the first current-only objective.

No network access, candidate evaluation, training, Lean invocation, promotion,
Git writes or phase closure. The full capture defaults to the retained historical archive; a missing or
changed archive fails rather than regenerating a substitute.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-archive", type=Path)
    parser.add_argument("--closure-archive", type=Path)
    parser.add_argument("--phase15-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory outside the source repository")
    parser.add_argument("--public-nonce-hash", help="Explicit current nonce for deterministic reproduction")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / "python" / f"rcp_rclm_runtime_v{v}") for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import canonical_json_bytes
    from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
    from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective

    output = args.output.resolve()
    if output == root or root in output.parents or output.exists():
        raise SystemExit("Output must be a new directory outside the source repository")
    source_head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"]):
        raise SystemExit("A clean committed checkout is required")
    # Fail before archive ingestion when the caller supplies an invalid nonce.
    nonce = args.public_nonce_hash or secrets.token_hex(32)
    from rcp_rclm_runtime_v5.phase17.controller import _hash
    _hash(nonce, "public_nonce_hash")
    capture = args.capture_archive or root / "artifacts/development/phase17b/phase16-capture-31153935872-1.zip"
    closure = args.closure_archive or root / (
        "artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/"
        "runtime-v4-phase16-final-closure-31153935872-1.zip")
    bundle = args.phase15_bundle or root / (
        "artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip")
    predecessor = reopen_phase16(capture_archive=capture,
                                 closure_archive=closure, phase15_bundle=bundle)
    # This uses the normal Phase 16 imports on the complete checkout.
    state = predecessor.phase16_state()
    if state.state_record_hash != predecessor.receipt["terminal_state_hash"]:
        raise SystemExit("Phase 16 ModelState round-trip changed the terminal identity")
    objective = select_bootstrap_objective(predecessor, turn_index=0, public_nonce_hash=nonce)
    freeze = freeze_bootstrap_objective(objective, predecessor, turn_index=0, public_nonce_hash=nonce)
    records = {"bootstrap.json": predecessor.receipt, "terminal_catalog.json": predecessor.catalog,
               "objective.json": objective.to_json(), "objective_freeze.json": freeze,
               "execution.json": {"source_commit": source_head, "python_version": sys.version,
                    "public_nonce_hash": nonce, "turn_index": 0,
                    "phase17_exit_closed": False, "gate_e_closed": False, "egc0_started": False,
                    "fresh_lean_verification": False, "promotion_performed": False,
                    "phase16_constructor_round_trip": True}}
    # No overwrite: preserve failed or interrupted output for inspection.
    output.mkdir(parents=True, exist_ok=False)
    lines = []
    for name, record in sorted(records.items()):
        data = canonical_json_bytes(record) + b"\n"
        (output / name).write_bytes(data)
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
    manifest = "".join(lines).encode("ascii")
    (output / "SHA256SUMS.txt").write_bytes(manifest)
    print(json.dumps({"accepted_for_historical_handoff": True, "source_commit": source_head,
        "objective_family": objective.to_json()["objective_family"],
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "phase17_exit_closed": False, "gate_e_closed": False, "egc0_started": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
