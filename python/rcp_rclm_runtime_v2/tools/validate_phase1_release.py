from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Final, Sequence

_HASH256: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_PLATFORMS: Final[frozenset[str]] = frozenset({"linux", "windows", "macos"})
_EXPECTED_STATUS: Final[str] = "phase_1_runtime_bedrock_cross_platform_validated"
_EXPECTED_SCHEMA: Final[str] = "rcp-rclm-runtime-phase-1-validation-v1"
_EXPECTED_CONTRACT: Final[str] = "rcp-rclm-runtime-contract-v2.0.0"


def validate_release_record(path: Path) -> tuple[str, ...]:
    record = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []

    expected_scalars = {
        "schema_version": _EXPECTED_SCHEMA,
        "contract_version": _EXPECTED_CONTRACT,
        "release_status": _EXPECTED_STATUS,
        "workflow_conclusion": "success",
        "test_count": 74,
    }
    for field, expected in expected_scalars.items():
        actual = record.get(field)
        if actual != expected:
            failures.append(f"{field}: expected {expected!r}, found {actual!r}")

    head = record.get("validated_branch_head")
    if not isinstance(head, str) or re.fullmatch(r"[0-9a-f]{40}", head) is None:
        failures.append("validated_branch_head must be a lowercase 40-character Git SHA")

    vectors_hash = record.get("conformance_vectors_sha256")
    if not isinstance(vectors_hash, str) or _HASH256.fullmatch(vectors_hash) is None:
        failures.append("conformance_vectors_sha256 must be a lowercase SHA-256 value")

    platforms = record.get("platforms")
    if not isinstance(platforms, dict):
        failures.append("platforms must be an object")
    else:
        platform_names = frozenset(platforms)
        if platform_names != _EXPECTED_PLATFORMS:
            failures.append(
                f"platforms: expected {sorted(_EXPECTED_PLATFORMS)}, found {sorted(platform_names)}"
            )
        for platform_name in sorted(_EXPECTED_PLATFORMS):
            platform = platforms.get(platform_name)
            if not isinstance(platform, dict):
                failures.append(f"platforms.{platform_name} must be an object")
                continue
            artifact = platform.get("artifact")
            if not isinstance(artifact, str) or not artifact:
                failures.append(f"platforms.{platform_name}.artifact must be nonempty")
            artifact_hash = platform.get("artifact_sha256")
            if not isinstance(artifact_hash, str) or _HASH256.fullmatch(artifact_hash) is None:
                failures.append(
                    f"platforms.{platform_name}.artifact_sha256 must be a lowercase SHA-256 value"
                )

    consistency = record.get("cross_platform_consistency")
    if not isinstance(consistency, dict):
        failures.append("cross_platform_consistency must be an object")
    else:
        if consistency.get("stable_fields_equal") is not True:
            failures.append("cross_platform_consistency.stable_fields_equal must be true")
        if consistency.get("platform_count") != 3:
            failures.append("cross_platform_consistency.platform_count must be 3")
        final_hash = consistency.get("artifact_sha256")
        if not isinstance(final_hash, str) or _HASH256.fullmatch(final_hash) is None:
            failures.append(
                "cross_platform_consistency.artifact_sha256 must be a lowercase SHA-256 value"
            )

    summary = record.get("validation_summary")
    if not isinstance(summary, dict):
        failures.append("validation_summary must be an object")
    else:
        required_true = (
            "python_compileall",
            "source_quality",
            "unit_tests",
            "frozen_conformance_vectors",
            "platform_reports_equal",
            "artifact_upload",
            "ok",
        )
        for field in required_true:
            if summary.get(field) is not True:
                failures.append(f"validation_summary.{field} must be true")
        if summary.get("issues") != []:
            failures.append("validation_summary.issues must be empty")

    licenses = record.get("licenses_after_phase_1")
    if not isinstance(licenses, dict):
        failures.append("licenses_after_phase_1 must be an object")
    else:
        if licenses.get("phase_2_lean_verifier_bridge_may_begin") is not True:
            failures.append("Phase 2 Lean verifier bridge must be licensed to begin")
        for field in (
            "production_checker",
            "generator",
            "successor_realizer",
            "promotion_controller",
            "independent_replay",
            "pytorch_backend",
            "benchmark_adapter",
        ):
            if licenses.get(field) is not False:
                failures.append(f"licenses_after_phase_1.{field} must remain false")

    claim_boundary = record.get("claim_boundary")
    if not isinstance(claim_boundary, dict):
        failures.append("claim_boundary must be an object")
    else:
        if claim_boundary.get("runtime_bedrock_complete") is not True:
            failures.append("claim_boundary.runtime_bedrock_complete must be true")
        for field in (
            "python_lean_refinement_established",
            "candidate_acceptance_licensed",
            "executable_rsi_claim",
            "external_benchmark_claim",
        ):
            if claim_boundary.get(field) is not False:
                failures.append(f"claim_boundary.{field} must remain false")

    return tuple(failures)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Phase 1 release evidence.")
    parser.add_argument("path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    failures = validate_release_record(args.path)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("Phase 1 release evidence is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
