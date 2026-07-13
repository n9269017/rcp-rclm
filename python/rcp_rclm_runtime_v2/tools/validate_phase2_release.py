from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from rcp_rclm_runtime._version import (
    CONTRACT_VERSION,
    FORMAL_SOURCE_COMMIT,
    LEAN_TOOLCHAIN,
    MATHLIB_COMMIT,
)
from rcp_rclm_runtime.canonical.hashing import validate_hash256

_SCHEMA_VERSION = "rcp-rclm-runtime-phase-2-validation-v1"
_RELEASE_STATUS = "phase_2_initial_lean_conformance_bridge_validated"
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ReleaseEvidenceError(ValueError):
    pass


def validate_release_evidence(value: object) -> dict[str, object]:
    root = _object(value, "phase_2_validation")
    _exact_keys(
        root,
        {
            "schema_version",
            "contract_version",
            "phase_name",
            "release_status",
            "formal_source_commit",
            "validated_implementation_head",
            "workflow_run",
            "workflow_conclusion",
            "jobs",
            "project_pin",
            "toolchain_runtime",
            "source_guard",
            "differential_suite",
            "artifacts",
            "validation_summary",
            "licenses_after_phase_2",
            "claim_boundary",
        },
        "phase_2_validation",
    )
    _equal(root["schema_version"], _SCHEMA_VERSION, "schema_version")
    _equal(root["contract_version"], CONTRACT_VERSION, "contract_version")
    _equal(root["release_status"], _RELEASE_STATUS, "release_status")
    _equal(root["formal_source_commit"], FORMAL_SOURCE_COMMIT, "formal_source_commit")
    _commit(root["validated_implementation_head"], "validated_implementation_head")
    workflow_run = root["workflow_run"]
    if isinstance(workflow_run, bool) or not isinstance(workflow_run, int) or workflow_run < 1:
        raise ReleaseEvidenceError("workflow_run must be a positive integer")
    _equal(root["workflow_conclusion"], "success", "workflow_conclusion")

    jobs = _object(root["jobs"], "jobs")
    _exact_keys(
        jobs,
        {
            "lean_conformance",
            "macos_python",
            "ubuntu_python",
            "windows_python",
            "workflow_closure",
        },
        "jobs",
    )
    for name, conclusion in jobs.items():
        _equal(conclusion, "success", f"jobs.{name}")

    project_pin = _object(root["project_pin"], "project_pin")
    _exact_keys(
        project_pin,
        {
            "formal_source_tree",
            "lakefile_sha256",
            "lean_toolchain",
            "manifest_sha256",
            "mathlib_commit",
            "pin_hash",
            "theorem_surface_hash",
            "toolchain_file_sha256",
        },
        "project_pin",
    )
    _commit(project_pin["formal_source_tree"], "project_pin.formal_source_tree")
    _equal(project_pin["lean_toolchain"], LEAN_TOOLCHAIN, "project_pin.lean_toolchain")
    _equal(project_pin["mathlib_commit"], MATHLIB_COMMIT, "project_pin.mathlib_commit")
    for field in (
        "lakefile_sha256",
        "manifest_sha256",
        "pin_hash",
        "theorem_surface_hash",
        "toolchain_file_sha256",
    ):
        _hash(project_pin[field], f"project_pin.{field}")

    toolchain_runtime = _object(root["toolchain_runtime"], "toolchain_runtime")
    _exact_keys(
        toolchain_runtime,
        {"lake_version", "lean_version", "runtime_hash"},
        "toolchain_runtime",
    )
    lean_version = _string(toolchain_runtime["lean_version"], "toolchain_runtime.lean_version")
    lake_version = _string(toolchain_runtime["lake_version"], "toolchain_runtime.lake_version")
    if "version 4.31.0" not in lean_version:
        raise ReleaseEvidenceError("toolchain_runtime.lean_version must identify Lean 4.31.0")
    if "Lean version 4.31.0" not in lake_version:
        raise ReleaseEvidenceError("toolchain_runtime.lake_version must identify Lean 4.31.0")
    _hash(toolchain_runtime["runtime_hash"], "toolchain_runtime.runtime_hash")

    source_guard = _object(root["source_guard"], "source_guard")
    _exact_keys(
        source_guard,
        {
            "admit_rejected",
            "invalid_utf8_rejected",
            "local_axiom_rejected",
            "pre_compilation",
            "sorry_ax_rejected",
            "sorry_rejected",
        },
        "source_guard",
    )
    _all_true(source_guard, "source_guard")

    suite = _object(root["differential_suite"], "differential_suite")
    _exact_keys(
        suite,
        {
            "accepting_case_count",
            "all_bridge_reports_accepted",
            "all_differential_matches",
            "case_count",
            "classical_theorem_surface_hash",
            "conformance_report_hash",
            "quantum_theorem_surface_hash",
            "rejecting_case_count",
        },
        "differential_suite",
    )
    _equal(suite["case_count"], 10, "differential_suite.case_count")
    _equal(suite["accepting_case_count"], 4, "differential_suite.accepting_case_count")
    _equal(suite["rejecting_case_count"], 6, "differential_suite.rejecting_case_count")
    _is_true(suite["all_bridge_reports_accepted"], "differential_suite.all_bridge_reports_accepted")
    _is_true(suite["all_differential_matches"], "differential_suite.all_differential_matches")
    for field in (
        "classical_theorem_surface_hash",
        "conformance_report_hash",
        "quantum_theorem_surface_hash",
    ):
        _hash(suite[field], f"differential_suite.{field}")

    artifacts = _object(root["artifacts"], "artifacts")
    _exact_keys(
        artifacts,
        {"final", "lean", "python_macos", "python_ubuntu", "python_windows"},
        "artifacts",
    )
    for name, artifact_value in artifacts.items():
        artifact = _object(artifact_value, f"artifacts.{name}")
        _exact_keys(artifact, {"name", "sha256"}, f"artifacts.{name}")
        _string(artifact["name"], f"artifacts.{name}.name")
        _hash(artifact["sha256"], f"artifacts.{name}.sha256")

    validation_summary = _object(root["validation_summary"], "validation_summary")
    _exact_keys(
        validation_summary,
        {
            "formal_core_build",
            "generated_source_admission_scan",
            "lean_compilation",
            "phase_1_regression",
            "phase_2_unit_tests",
            "python_compileall",
            "source_quality",
            "structured_verdicts",
            "workflow_artifacts",
            "ok",
        },
        "validation_summary",
    )
    _all_true(validation_summary, "validation_summary")

    licenses = _object(root["licenses_after_phase_2"], "licenses_after_phase_2")
    _exact_keys(
        licenses,
        {
            "benchmark_adapter",
            "candidate_acceptance",
            "generator",
            "independent_replay",
            "phase_3_checker_development_may_begin",
            "promotion_controller",
            "pytorch_backend",
            "successor_realizer",
        },
        "licenses_after_phase_2",
    )
    _is_true(
        licenses["phase_3_checker_development_may_begin"],
        "licenses_after_phase_2.phase_3_checker_development_may_begin",
    )
    for field in (
        "benchmark_adapter",
        "candidate_acceptance",
        "generator",
        "independent_replay",
        "promotion_controller",
        "pytorch_backend",
        "successor_realizer",
    ):
        _is_false(licenses[field], f"licenses_after_phase_2.{field}")

    boundary = _object(root["claim_boundary"], "claim_boundary")
    _exact_keys(
        boundary,
        {
            "arbitrary_rclm_packet_refinement_established",
            "benchmark_claim",
            "candidate_acceptance_licensed",
            "executable_rsi_claim",
            "mature_packet_executable_complete",
            "production_checker_soundness_established",
            "reference_bridge_complete",
        },
        "claim_boundary",
    )
    _is_true(boundary["reference_bridge_complete"], "claim_boundary.reference_bridge_complete")
    for field in (
        "arbitrary_rclm_packet_refinement_established",
        "benchmark_claim",
        "candidate_acceptance_licensed",
        "executable_rsi_claim",
        "mature_packet_executable_complete",
        "production_checker_soundness_established",
    ):
        _is_false(boundary[field], f"claim_boundary.{field}")

    return root


def _object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReleaseEvidenceError(f"{path} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise ReleaseEvidenceError(f"{path} keys must be strings")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], path: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ReleaseEvidenceError(
            f"{path} fields differ: missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseEvidenceError(f"{path} must be a nonempty string")
    return value


def _equal(value: object, expected: object, path: str) -> None:
    if value != expected:
        raise ReleaseEvidenceError(f"{path} must equal {expected!r}, found {value!r}")


def _commit(value: object, path: str) -> None:
    text = _string(value, path)
    if _COMMIT_PATTERN.fullmatch(text) is None:
        raise ReleaseEvidenceError(f"{path} must be a lowercase 40-character Git object ID")


def _hash(value: object, path: str) -> None:
    text = _string(value, path)
    try:
        validate_hash256(text, path)
    except Exception as exc:
        raise ReleaseEvidenceError(str(exc)) from exc


def _is_true(value: object, path: str) -> None:
    if value is not True:
        raise ReleaseEvidenceError(f"{path} must be true")


def _is_false(value: object, path: str) -> None:
    if value is not False:
        raise ReleaseEvidenceError(f"{path} must be false")


def _all_true(value: Mapping[str, object], path: str) -> None:
    for key, item in value.items():
        _is_true(item, f"{path}.{key}")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the frozen Executable Core v2 Phase 2 release evidence."
    )
    parser.add_argument("path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        raw = args.path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        evidence = validate_release_evidence(parsed)
    except (OSError, UnicodeError, json.JSONDecodeError, ReleaseEvidenceError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": evidence["schema_version"],
                "release_status": evidence["release_status"],
                "workflow_run": evidence["workflow_run"],
                "validated_implementation_head": evidence["validated_implementation_head"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
