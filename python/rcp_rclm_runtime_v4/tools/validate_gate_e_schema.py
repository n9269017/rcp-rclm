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
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: tuple(item.absolute_path))

    checks: dict[str, bool] = {
        "schema_valid": not errors,
        "attempt_hashes_valid": False,
        "enumeration_hash_valid": False,
        "report_hash_valid": False,
    }
    if not errors and isinstance(instance, dict):
        attempts = instance.get("attempts")
        if isinstance(attempts, list):
            observed_attempt_hashes: list[str] = []
            attempts_valid = True
            for attempt in attempts:
                if not isinstance(attempt, dict) or not isinstance(attempt.get("attempt_hash"), str):
                    attempts_valid = False
                    break
                payload = deepcopy(attempt)
                observed_hash = payload.pop("attempt_hash")
                expected_hash = canonical_json_hash(payload)
                if observed_hash != expected_hash:
                    attempts_valid = False
                    break
                observed_attempt_hashes.append(observed_hash)
            checks["attempt_hashes_valid"] = attempts_valid
            if attempts_valid:
                checks["enumeration_hash_valid"] = (
                    instance.get("enumeration_hash")
                    == canonical_json_hash(observed_attempt_hashes)
                )
        if isinstance(instance.get("report_hash"), str):
            payload = deepcopy(instance)
            observed_report_hash = payload.pop("report_hash")
            checks["report_hash_valid"] = observed_report_hash == canonical_json_hash(payload)

    ok = all(checks.values())
    report = {
        "schema_id": "runtime.v4.gatee.schema_validation.v1",
        "ok": ok,
        "schema": args.schema.name,
        "instance": args.instance.name,
        "checks": checks,
        "errors": [
            {
                "path": "/" + "/".join(str(item) for item in error.absolute_path),
                "message": error.message,
            }
            for error in errors
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
