from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase11.reference import build_phase11a_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    schema = json.loads(args.schema.resolve(strict=True).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11a-schema-") as temporary:
        summary = build_phase11a_reference(Path(temporary) / "reference").summary_json()
    errors = sorted(
        Draft202012Validator(schema).iter_errors(summary),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    declared_hash = summary.get("summary_hash")
    content = dict(summary)
    content.pop("summary_hash", None)
    hash_matches = declared_hash == canonical_json_hash(content)
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-11a-schema-validation-v1",
        "schema_id": schema.get("$id"),
        "schema_valid": True,
        "reference_accepted": summary.get("accepted") is True,
        "summary_hash_matches": hash_matches,
        "errors": [error.message for error in errors],
        "ok": not errors and hash_matches and summary.get("accepted") is True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
