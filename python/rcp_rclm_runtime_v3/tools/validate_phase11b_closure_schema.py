from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    schema = json.loads(args.schema.resolve(strict=True).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    instance = load_json_strict(args.instance.resolve(strict=True).read_bytes(), require_canonical=True)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-11-closure-schema-validation-v1",
        "schema_id": schema.get("$id"),
        "schema_valid": True,
        "instance_accepted": isinstance(instance, dict) and instance.get("accepted") is True,
        "errors": [error.message for error in errors],
        "ok": not errors and isinstance(instance, dict) and instance.get("accepted") is True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
