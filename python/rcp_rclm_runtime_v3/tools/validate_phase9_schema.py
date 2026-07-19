from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime_v3.contract.reference import build_phase9_reference_fixture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    fixture = build_phase9_reference_fixture()
    instances = {
        "LearnedRCLMState": fixture.predecessor.to_json(),
        "LearnedRCLMUpdate": fixture.update.to_json(),
        "LearnedCertificatePacket": fixture.certificate.to_json(),
        "HeldoutAccessPolicy": fixture.heldout_policy.to_json(),
        "Phase9TransitionReport": fixture.report.to_json(),
    }
    errors: list[dict[str, object]] = []
    for definition, instance in instances.items():
        local_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#/$defs/{definition}",
            "$defs": schema["$defs"],
        }
        validator = Draft202012Validator(local_schema)
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
            errors.append(
                {
                    "definition": definition,
                    "path": list(error.path),
                    "message": error.message,
                }
            )
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-9-schema-validation-v1",
        "schema_id": schema["$id"],
        "definitions_validated": sorted(instances),
        "errors": errors,
        "ok": not errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
