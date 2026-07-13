from __future__ import annotations

import argparse
import hashlib
import json
import platform
import unittest
from pathlib import Path

from validate_source_quality import evaluate_source_quality

from rcp_rclm_runtime import __version__
from rcp_rclm_runtime._version import (
    CONTRACT_VERSION,
    FORMAL_SOURCE_COMMIT,
    NUMERIC_BACKEND_ID,
)
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.refinement.theorem_surface import theorem_surface_metadata


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discovered_test_count(package_root: Path) -> int:
    suite = unittest.defaultTestLoader.discover(
        str(package_root / "tests"),
        pattern="test_*.py",
        top_level_dir=str(package_root / "tests"),
    )
    return suite.countTestCases()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--platform-label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    package_root = args.package_root.resolve(strict=True)
    manifest_path = package_root / "phase_1_manifest.json"
    vectors_path = package_root / "tests" / "conformance_vectors.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
    quality = evaluate_source_quality(package_root)

    report = {
        "schema_version": "rcp-rclm-runtime-phase-1-validation-report-v1",
        "platform_label": args.platform_label,
        "platform_system": platform.system(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "package_version": __version__,
        "contract_version": CONTRACT_VERSION,
        "formal_source_commit": FORMAL_SOURCE_COMMIT,
        "numeric_backend_id": NUMERIC_BACKEND_ID,
        "phase_status": manifest["phase_status"],
        "test_count": discovered_test_count(package_root),
        "conformance_vectors_sha256": sha256_file(vectors_path),
        "phase_1_manifest_sha256": sha256_file(manifest_path),
        "theorem_surface_hash": canonical_json_hash(theorem_surface_metadata()),
        "vector_schema_version": vectors["schema_version"],
        "source_quality": quality,
        "claim_boundary": manifest["claim_boundary"],
        "ok": quality["ok"] is True,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
