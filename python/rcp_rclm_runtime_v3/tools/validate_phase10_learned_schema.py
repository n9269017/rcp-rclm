from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.learned_reference import build_phase10_learned_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    schema = json.loads(args.schema.resolve(strict=True).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10b-schema-") as temporary:
        fixture = build_phase10_learned_reference(Path(temporary) / "reference")
        summary = fixture.summary_json()
    errors = sorted(validator.iter_errors(summary), key=lambda error: list(error.path))
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-10b-schema-validation-v1",
        "schema_id": schema.get("$id"),
        "reference_summary_hash": summary["summary_hash"],
        "errors": [error.message for error in errors],
        "ok": not errors and fixture.accepted,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
