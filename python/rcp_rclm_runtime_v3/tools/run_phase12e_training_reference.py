from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase12.phase12e_training import run_phase12e_training_request
from rcp_rclm_runtime_v3.phase12.phase12e_training_binding import (
    load_phase12e_training_binding,
)


def default_binding_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "rcp_rclm_runtime_v3"
        / "phase12"
        / "phase12e_training_binding.json"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path, default=default_binding_path())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    binding = load_phase12e_training_binding(args.binding)
    request = binding["request"]
    semantic_hash = binding["semantic_candidate_tensor_hash"]
    if not isinstance(request, dict) or not isinstance(semantic_hash, str):
        raise TypeError("validated Phase 12E training binding is malformed")
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12e-training-") as temporary:
        root = Path(temporary)
        evidence = run_phase12e_training_request(
            request,
            semantic_hash,
            root / "training",
        )
        report = evidence.to_json()
        report["binding_hash"] = binding["binding_hash"]
        report["source_semantic_hash"] = binding["source_semantic_hash"]
        report["report_hash"] = evidence.report_hash
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["accepted"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
