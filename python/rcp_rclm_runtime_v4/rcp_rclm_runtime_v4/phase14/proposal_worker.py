from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase14.proposal import generate_proposal_enumeration
from rcp_rclm_runtime_v4.phase14.records import Phase14SearchHistory


def _history(value: object) -> Phase14SearchHistory:
    try:
        return Phase14SearchHistory.from_json(value)
    except (TypeError, ValueError, KeyError) as exc:
        raise SchemaValidationError(
            "phase14.worker.history",
            "invalid history object",
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    request = load_json_strict(args.request.read_bytes(), require_canonical=True)
    if not isinstance(request, dict):
        raise SchemaValidationError("phase14.worker.request", "expected object")
    if request.get("network_permitted") is not False:
        raise SchemaValidationError("phase14.worker.request", "network must be disabled")
    if request.get("heldout_material_visible") is not False:
        raise SchemaValidationError("phase14.worker.request", "held-out material is forbidden")
    if request.get("manual_repair_permitted") is not False:
        raise SchemaValidationError("phase14.worker.request", "manual repair is forbidden")
    report = generate_proposal_enumeration(
        Path(str(request["active_semantic_root"])),
        str(request["challenge_commitment_hash"]),
        _history(request["history"]),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report.to_json()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
