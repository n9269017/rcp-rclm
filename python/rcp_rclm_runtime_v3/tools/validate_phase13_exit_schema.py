from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    schema = json.loads(
        args.schema.resolve(strict=True).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    instance = load_json_strict(
        args.instance.resolve(strict=True).read_bytes(),
        require_canonical=True,
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    declared_hash = instance.get("report_hash") if isinstance(instance, dict) else None
    content = dict(instance) if isinstance(instance, dict) else {}
    content.pop("report_hash", None)
    hash_matches = declared_hash == canonical_json_hash(content)
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-13-exit-schema-validation-v1",
        "schema_id": schema.get("$id"),
        "schema_valid": True,
        "instance_accepted": isinstance(instance, dict)
        and instance.get("phase13_exit_closed") is True,
        "report_hash_matches": hash_matches,
        "errors": [error.message for error in errors],
        "ok": not errors and hash_matches,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
