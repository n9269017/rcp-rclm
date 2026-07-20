from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    ARCHITECTURE_PATH,
    TENSOR_MANIFEST_PATH,
    TOKENIZER_MANIFEST_PATH,
)
from rcp_rclm_runtime_v3.phase10.reference import build_phase10_reference_fixture


def _definition_schema(schema: dict[str, object], definition: str) -> dict[str, object]:
    return {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{definition}",
    }


def _errors(validator: Draft202012Validator, value: object) -> list[str]:
    return [
        f"{'/'.join(str(item) for item in error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    schema_value = json.loads(args.schema.resolve(strict=True).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema_value)
    reference_validator = Draft202012Validator(schema_value)

    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-schema-") as temp_dir:
        reference_root = Path(temp_dir) / "reference"
        fixture = build_phase10_reference_fixture(reference_root)
        values = {
            "Phase10ReferenceFixture": fixture.to_json(),
            "Architecture": load_json_strict(
                (reference_root / "predecessor" / ARCHITECTURE_PATH).read_bytes(),
                require_canonical=True,
            ),
            "TokenizerManifest": load_json_strict(
                (reference_root / "predecessor" / TOKENIZER_MANIFEST_PATH).read_bytes(),
                require_canonical=True,
            ),
            "TensorManifest": load_json_strict(
                (reference_root / "predecessor" / TENSOR_MANIFEST_PATH).read_bytes(),
                require_canonical=True,
            ),
            "AdapterManifest": load_json_strict(
                (reference_root / "zero_lora_extension" / ADAPTER_MANIFEST_PATH).read_bytes(),
                require_canonical=True,
            ),
            "ModelPackageManifest": fixture.successor.to_json(),
            "PackageReport": fixture.successor_report.to_json(),
            "ExtensionReport": fixture.extension_report.to_json(),
        }
        errors: dict[str, list[str]] = {}
        for definition, value in values.items():
            validator = (
                reference_validator
                if definition == "Phase10ReferenceFixture"
                else Draft202012Validator(_definition_schema(schema_value, definition))
            )
            definition_errors = _errors(validator, value)
            if definition_errors:
                errors[definition] = definition_errors

    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-10-schema-validation-v1",
        "schema_path": args.schema.as_posix(),
        "draft": "2020-12",
        "definitions_checked": sorted(values),
        "errors": errors,
        "ok": not errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
