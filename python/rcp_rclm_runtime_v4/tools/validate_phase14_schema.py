from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    instance = json.loads(args.instance.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda item: tuple(item.absolute_path),
    )
    hash_field = "manifest_hash" if isinstance(instance, dict) and instance.get("schema_id") == "runtime.v4.phase14.bundle_manifest.v1" else "report_hash"
    hash_valid = False
    if not errors and isinstance(instance, dict) and isinstance(instance.get(hash_field), str):
        payload = deepcopy(instance)
        observed = payload.pop(hash_field)
        hash_valid = observed == canonical_json_hash(payload)
    report = {
        "schema_id": "runtime.v4.phase14.schema_validation.v1",
        "ok": not errors and hash_valid,
        "schema": args.schema.name,
        "instance": args.instance.name,
        "schema_valid": not errors,
        "content_hash_valid": hash_valid,
        "errors": [
            {
                "path": "/" + "/".join(str(part) for part in error.absolute_path),
                "message": error.message,
            }
            for error in errors
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
