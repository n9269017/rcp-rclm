from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256

from rcp_rclm_runtime_v3.phase11.reference import build_phase11a_reference

PHASE11_MANIFEST_RELATIVE_PATH: Final[Path] = Path(
    "python/rcp_rclm_runtime_v3/phase_11_generator_manifest.json"
)
_EXPECTED_STATUS: Final[str] = (
    "phase11a_active_model_typed_proposal_complete_at_declared_scope"
)
_EXPECTED_SCHEMA: Final[str] = "rcp-rclm-runtime-v3-phase-11a-manifest-v1"
_EXPECTED_CLAIM_BOUNDARY: Final[dict[str, bool]] = {
    "active_predecessor_model_generated_proposal": True,
    "bootstrap_counted_as_autonomous_improvement": False,
    "fresh_model_generated_typed_program_validated": True,
    "host_installed_active_generator_bootstrap": True,
    "model_generated_candidate_promoted": False,
    "model_generated_candidate_realized": False,
    "model_generated_candidate_rejected": False,
    "model_generated_proposal_rejected": True,
    "modified_successor_generator_used_recursively": False,
    "phase11_exit_closed": False,
    "successor_generator_planner_installed": False,
}
_EXPECTED_BUDGET: Final[dict[str, int]] = {
    "accelerator_count": 0,
    "candidate_count": 2,
    "evaluation_calls": 2,
    "output_bytes": 96,
    "training_steps": 1,
    "wall_clock_seconds": 1,
}
_EXPECTED_ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
    {"final", "macos", "ubuntu", "windows"}
)
_HEX40: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
_SHA256_DIGEST: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def load_phase11_manifest(repo_root: Path) -> dict[str, object]:
    return _load_json(repo_root.resolve(strict=True) / PHASE11_MANIFEST_RELATIVE_PATH)


def _valid_hash(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        validate_hash256(value, "phase11.manifest.hash")
    except ValueError:
        return False
    return True


def _expected_artifact_name(kind: str, run_id: int, attempt: int) -> str:
    suffix = f"{run_id}-{attempt}"
    if kind == "ubuntu":
        return f"runtime-v3-phase-11a-ubuntu-latest-{suffix}"
    if kind == "windows":
        return f"runtime-v3-phase-11a-windows-latest-{suffix}"
    if kind == "macos":
        return f"runtime-v3-phase-11a-macos-latest-{suffix}"
    if kind == "final":
        return f"runtime-v3-phase-11a-final-{suffix}"
    raise ValueError(f"unsupported Phase 11A artifact kind: {kind}")


def _code_proof_valid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    branch_head = value.get("branch_head")
    merge_commit = value.get("pr_merge_test_commit")
    run_id = value.get("workflow_run_id")
    attempt = value.get("workflow_run_attempt")
    cross_platform_hash = value.get("cross_platform_reference_file_sha256")
    if not isinstance(branch_head, str) or _HEX40.fullmatch(branch_head) is None:
        return False
    if not isinstance(merge_commit, str) or _HEX40.fullmatch(merge_commit) is None:
        return False
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
        return False
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        return False
    if not _valid_hash(cross_platform_hash):
        return False
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != _EXPECTED_ARTIFACT_KINDS:
        return False
    ids: set[int] = set()
    for kind, record in artifacts.items():
        if not isinstance(kind, str) or not isinstance(record, dict):
            return False
        artifact_id = record.get("id")
        name = record.get("name")
        digest = record.get("digest")
        if isinstance(artifact_id, bool) or not isinstance(artifact_id, int):
            return False
        if artifact_id < 1 or artifact_id in ids:
            return False
        ids.add(artifact_id)
        if name != _expected_artifact_name(kind, run_id, attempt):
            return False
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            return False
    return True


def _observed_reference_hashes(repo_root: Path) -> dict[str, str]:
    del repo_root
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11a-manifest-") as temporary:
        summary = build_phase11a_reference(Path(temporary) / "reference").summary_json()
    names = (
        "active_generator_hash",
        "active_model_identity_hash",
        "active_package_hash",
        "active_planner_hash",
        "active_state_hash",
        "bootstrap_report_hash",
        "budget_hash",
        "first_invocation_hash",
        "first_program_hash",
        "first_validation_hash",
        "objective_hash",
        "proposal_protocol_hash",
        "second_invocation_hash",
        "second_program_hash",
        "second_validation_hash",
        "summary_hash",
    )
    return {name: str(summary[name]) for name in names}


def validate_phase11_manifest(
    repo_root: Path,
    *,
    recompute_reference: bool = True,
) -> dict[str, object]:
    root = repo_root.resolve(strict=True)
    manifest = load_phase11_manifest(root)
    checks: dict[str, bool] = {
        "schema_version": manifest.get("schema_version") == _EXPECTED_SCHEMA,
        "status": manifest.get("status") == _EXPECTED_STATUS,
        "claim_boundary": manifest.get("claim_boundary") == _EXPECTED_CLAIM_BOUNDARY,
        "fixed_budget": manifest.get("fixed_invocation_budget") == _EXPECTED_BUDGET,
        "code_proof": _code_proof_valid(manifest.get("code_proof")),
        "dependency": manifest.get("dependency")
        == {
            "phase10_merge_commit": "52acaa820d75380b8766a2d7f4f78226645acc1f",
            "phase10_required_complete": True,
            "runtime_v2_trust_boundary_required_unchanged": True,
        },
        "rejection_contract": manifest.get("rejection_contract")
        == {
            "first_reason_codes": [
                "PHASE11_BUDGET_EXCEEDED",
                "PHASE11_FORBIDDEN_UPDATE_CLASS",
            ],
            "first_validation_accepted": False,
            "heldout_material_consumed": False,
            "manual_repair_count": 0,
            "second_validation_accepted": True,
        },
    }
    required_paths = manifest.get("required_source_paths")
    checks["required_paths_shape"] = (
        isinstance(required_paths, list)
        and bool(required_paths)
        and required_paths == sorted(set(required_paths))
    )
    checks["required_paths_present"] = isinstance(required_paths, list) and all(
        isinstance(path, str) and (root / path).is_file() for path in required_paths
    )
    declared_reference = manifest.get("reference_hashes")
    observed_reference: dict[str, str] | None = None
    if recompute_reference:
        observed_reference = _observed_reference_hashes(root)
        checks["reference_hashes"] = declared_reference == observed_reference
    else:
        checks["reference_hash_shape"] = (
            isinstance(declared_reference, dict)
            and bool(declared_reference)
            and all(_valid_hash(value) for value in declared_reference.values())
        )
    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    return {
        "schema_version": "rcp-rclm-runtime-v3-phase-11a-manifest-validation-v1",
        "manifest_hash": canonical_json_hash(manifest),
        "checks": checks,
        "observed_reference_hashes": observed_reference,
        "failures": failures,
        "ok": not failures,
    }


__all__ = [
    "PHASE11_MANIFEST_RELATIVE_PATH",
    "load_phase11_manifest",
    "validate_phase11_manifest",
]
