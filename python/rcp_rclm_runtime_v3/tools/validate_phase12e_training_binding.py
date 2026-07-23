from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v3.phase12.phase12e_training_binding import (
    load_phase12e_training_binding,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = load_json_strict(
        args.summary.resolve(strict=True).read_bytes(), require_canonical=True
    )
    if not isinstance(summary, dict):
        raise TypeError("Phase 12E summary must be an object")
    binding = load_phase12e_training_binding(args.binding, summary=summary)
    report = {
        "schema_id": "runtime.v3.phase12e.training_binding_validation.v1",
        "accepted": True,
        "binding_hash": binding["binding_hash"],
        "source_summary_hash": binding["source_summary_hash"],
        "candidate_package_hash": binding["request"]["candidate_package_hash"],
        "candidate_adapter_manifest_hash": binding["request"][
            "candidate_adapter_manifest_hash"
        ],
        "semantic_candidate_tensor_hash": binding[
            "semantic_candidate_tensor_hash"
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
