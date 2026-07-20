from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v3.phase11.closure_manifest import (
    load_phase11_closure_manifest,
    validate_phase11_closure_manifest,
    validate_phase11_closure_report,
)


def _load_object(path: Path) -> dict[str, object]:
    value = load_json_strict(path.resolve(strict=True).read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-recompute", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    manifest_report = validate_phase11_closure_manifest(
        args.repo_root,
        recompute_reference=not args.no_recompute,
    )
    result: dict[str, object] = {
        "schema_version": "rcp-rclm-runtime-v3-phase-11-retained-validation-v1",
        "manifest_validation": manifest_report,
        "ok": manifest_report["ok"] is True,
    }
    if args.report is not None:
        manifest = load_phase11_closure_manifest(args.repo_root)
        report_validation = validate_phase11_closure_report(
            manifest,
            _load_object(args.report),
        )
        result["closure_report_validation"] = report_validation
        result["ok"] = result["ok"] is True and report_validation["ok"] is True

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(result))
    return 0 if result["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
