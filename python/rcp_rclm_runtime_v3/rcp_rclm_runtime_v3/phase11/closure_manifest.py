from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import CanonicalizationError

from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import build_phase11b_reference

PHASE11_CLOSURE_MANIFEST_RELATIVE_PATH: Final[Path] = Path(
    "python/rcp_rclm_runtime_v3/phase_11_closure_manifest.json"
)
PHASE11A_MANIFEST_RELATIVE_PATH: Final[Path] = Path(
    "python/rcp_rclm_runtime_v3/phase_11_generator_manifest.json"
)

_EXPECTED_STATUS: Final[str] = "phase11_exit_closed_at_exact_code_proof"
_EXPECTED_SCHEMA_VERSION: Final[str] = (
    "rcp-rclm-runtime-v3-phase-11-closure-manifest-v1"
)
_EXPECTED_CLAIM_BOUNDARY: Final[dict[str, bool]] = {
    "active_predecessor_model_generated_proposals": True,
    "atomic_content_addressed_promotion": True,
    "autonomous_unbounded_rsi": False,
    "generic_successor_availability": False,
    "heldout_material_consumed": False,
    "later_fresh_model_generated_candidate_promoted": True,
    "model_generated_candidate_realization": True,
    "model_generated_candidate_rejection": True,
    "phase11_exit_closed": True,
    "protected_capability_retention": True,
    "recursive_use_of_modified_successor_generator": False,
    "selected_entropy_kl_diagonal_qre": True,
    "selected_lean_frontier_expansion": True,
    "successor_generator_planner_installed": True,
    "untrusted_isolated_training_worker": True,
    "zero_manual_repairs": True,
}
_EXPECTED_SELECTED_SCOPE: Final[dict[str, object]] = {
    "active_predecessor_count": 1,
    "model_family": "compact_decoder_only_transformer_v1",
    "model_generated_candidate_realizations": 2,
    "model_generator_invocations": 3,
    "promoted_candidate_count": 1,
    "recursive_successor_use_deferred_to_phase": 12,
    "rejected_candidate_count": 1,
    "successor_generator_generation": 2,
    "successor_planner_generation": 2,
    "task_class": "lean_theorem_completion_v1",
}
_EXPECTED_ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
    {"final", "macos", "pinned", "training", "ubuntu", "windows"}
)
_STABLE_REFERENCE_COMPONENT_KEYS: Final[Sequence[str]] = (
    "active_generator_hash",
    "active_package_hash",
    "active_planner_hash",
    "active_state_hash",
    "alpha_candidate_fixture_hash",
    "alpha_invocation_hash",
    "beta_candidate_model_identity_hash",
    "beta_candidate_package_hash",
    "invalid_invocation_hash",
    "invalid_validation_hash",
    "successor_generator_hash",
    "successor_planner_hash",
)
_STABLE_REFERENCE_KEYS: Final[frozenset[str]] = frozenset(
    (*_STABLE_REFERENCE_COMPONENT_KEYS, "portable_summary_hash")
)
_EXACT_RUNTIME_HASH_KEYS: Final[frozenset[str]] = frozenset(
    {
        "active_package_hash_after_rejection",
        "alpha_phase6_hash",
        "beta_candidate_fixture_hash",
        "beta_invocation_hash",
        "beta_phase6_hash",
        "initial_active_package_hash",
        "installed_generator_bytes_hash",
        "installed_planner_bytes_hash",
        "lifecycle_certificate_hash",
        "lifecycle_transition_hash",
        "parent_package_hash",
        "promoted_package_hash",
        "promotion_attempt_report_hash",
        "promotion_ledger_hash",
        "promotion_report_hash",
        "reference_summary_hash",
        "rejection_attempt_report_hash",
        "rejection_ledger_hash",
        "verification_report_hash",
    }
)
_CLOSURE_REPORT_HASH_KEYS: Final[frozenset[str]] = frozenset(
    {
        "exact_runtime_reference_hash",
        "final_report_hash",
        "promotion_hash",
        "report_hash",
        "verification_hash",
    }
)
_HEX40: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
_SHA256_DIGEST: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def load_phase11_closure_manifest(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve(strict=True)
    return _load_json(root / PHASE11_CLOSURE_MANIFEST_RELATIVE_PATH)


def _valid_hash(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        validate_hash256(value, "phase11_closure_manifest.hash")
    except (CanonicalizationError, ValueError):
        return False
    return True


def _valid_hash_map(value: object, expected_keys: frozenset[str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == expected_keys
        and all(_valid_hash(item) for item in value.values())
    )


def _portable_reference_hashes(summary: Mapping[str, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in _STABLE_REFERENCE_COMPONENT_KEYS:
        value = summary.get(name)
        if not _valid_hash(value):
            raise ValueError(f"Phase 11 portable summary is missing a valid {name}")
        result[name] = str(value)
    result["portable_summary_hash"] = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase11b.portable_reference_hashes.v1",
            "hashes": result,
        }
    )
    return result


def _expected_artifact_name(kind: str, run_id: int, attempt: int) -> str:
    suffix = f"{run_id}-{attempt}"
    if kind == "ubuntu":
        return f"runtime-v3-phase-11-ubuntu-latest-{suffix}"
    if kind == "windows":
        return f"runtime-v3-phase-11-windows-latest-{suffix}"
    if kind == "macos":
        return f"runtime-v3-phase-11-macos-latest-{suffix}"
    if kind == "training":
        return f"runtime-v3-phase-11-training-{suffix}"
    if kind == "pinned":
        return f"runtime-v3-phase-11-pinned-{suffix}"
    if kind == "final":
        return f"runtime-v3-phase-11-final-{suffix}"
    raise ValueError(f"unsupported Phase 11 artifact kind: {kind}")


def _validate_code_proof(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    branch_head = value.get("branch_head")
    merge_commit = value.get("pr_merge_test_commit")
    run_id = value.get("workflow_run_id")
    attempt = value.get("workflow_run_attempt")
    if not isinstance(branch_head, str) or _HEX40.fullmatch(branch_head) is None:
        return False
    if not isinstance(merge_commit, str) or _HEX40.fullmatch(merge_commit) is None:
        return False
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
        return False
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        return False
    closure_report = value.get("closure_report")
    runtime_hashes = value.get("exact_runtime_hashes")
    if not _valid_hash_map(closure_report, _CLOSURE_REPORT_HASH_KEYS):
        return False
    if not _valid_hash_map(runtime_hashes, _EXACT_RUNTIME_HASH_KEYS):
        return False
    if not isinstance(closure_report, dict) or not isinstance(runtime_hashes, dict):
        return False
    if closure_report["promotion_hash"] != runtime_hashes["promotion_report_hash"]:
        return False
    if runtime_hashes["initial_active_package_hash"] != runtime_hashes[
        "active_package_hash_after_rejection"
    ]:
        return False
    if runtime_hashes["initial_active_package_hash"] != runtime_hashes[
        "parent_package_hash"
    ]:
        return False
    if value.get("runtime_claims") != {
        "installed_generator_bytes_verified": True,
        "installed_planner_bytes_verified": True,
        "ledger_sequence_number": 2,
        "promotion_parent_is_unchanged_active_package": True,
        "rejection_preserved_active_package": True,
    }:
        return False
    if value.get("pinned_toolchain") != "leanprover/lean4:v4.31.0":
        return False

    git_trees = value.get("git_trees")
    if not isinstance(git_trees, dict) or set(git_trees) != {
        "formal_core_v2",
        "formal_core_v3",
        "runtime_v3",
    }:
        return False
    if any(
        not isinstance(item, str) or _HEX40.fullmatch(item) is None
        for item in git_trees.values()
    ):
        return False

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != _EXPECTED_ARTIFACT_KINDS:
        return False
    artifact_ids: set[int] = set()
    for kind, record in artifacts.items():
        if not isinstance(kind, str) or not isinstance(record, dict):
            return False
        artifact_id = record.get("id")
        name = record.get("name")
        digest = record.get("digest")
        if isinstance(artifact_id, bool) or not isinstance(artifact_id, int):
            return False
        if artifact_id < 1 or artifact_id in artifact_ids:
            return False
        artifact_ids.add(artifact_id)
        if name != _expected_artifact_name(kind, run_id, attempt):
            return False
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            return False
    return True


def _recompute_stable_reference_hashes() -> dict[str, str]:
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase11-closure-manifest-"
    ) as temporary:
        summary = build_phase11b_reference(Path(temporary) / "reference").summary_json()
    return _portable_reference_hashes(summary)


def validate_phase11_closure_manifest(
    repo_root: Path,
    *,
    recompute_reference: bool = True,
) -> dict[str, object]:
    root = repo_root.resolve(strict=True)
    manifest = load_phase11_closure_manifest(root)
    checks: dict[str, bool] = {
        "schema_version": manifest.get("schema_version") == _EXPECTED_SCHEMA_VERSION,
        "status": manifest.get("status") == _EXPECTED_STATUS,
        "claim_boundary": manifest.get("claim_boundary") == _EXPECTED_CLAIM_BOUNDARY,
        "selected_scope": manifest.get("selected_scope") == _EXPECTED_SELECTED_SCOPE,
        "code_proof": _validate_code_proof(manifest.get("code_proof")),
        "dependency": manifest.get("dependency")
        == {
            "phase10_merge_commit": "52acaa820d75380b8766a2d7f4f78226645acc1f",
            "phase11a_manifest": (
                "python/rcp_rclm_runtime_v3/phase_11_generator_manifest.json"
            ),
            "runtime_v2_trust_boundary_required_unchanged": True,
        },
        "non_circular_binding": manifest.get("non_circular_exact_head_binding")
        == {
            "artifact_self_digest_is_not_embedded": True,
            "committed_manifest_binds_stable_reference_hashes": True,
            "committed_manifest_retains_prior_exact_code_proof": True,
            "final_head_is_bound_by_workflow_artifacts_and_pr_record": True,
        },
    }

    required_paths = manifest.get("required_source_paths")
    checks["required_source_paths_shape"] = (
        isinstance(required_paths, list)
        and bool(required_paths)
        and required_paths == sorted(set(required_paths))
    )
    checks["required_source_paths_present"] = isinstance(required_paths, list) and all(
        isinstance(path, str) and (root / path).is_file() for path in required_paths
    )

    phase11a = _load_json(root / PHASE11A_MANIFEST_RELATIVE_PATH)
    checks["phase11a_manifest_closed"] = (
        phase11a.get("status")
        == "phase11a_active_model_typed_proposal_complete_at_declared_scope"
    )

    declared_stable = manifest.get("stable_reference_hashes")
    observed_stable: dict[str, str] | None = None
    if recompute_reference:
        observed_stable = _recompute_stable_reference_hashes()
        checks["stable_reference_hashes"] = declared_stable == observed_stable
    else:
        checks["stable_reference_hash_shape"] = _valid_hash_map(
            declared_stable,
            _STABLE_REFERENCE_KEYS,
        )

    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    return {
        "schema_version": "rcp-rclm-runtime-v3-phase-11-closure-validation-v1",
        "manifest_hash": canonical_json_hash(manifest),
        "checks": checks,
        "observed_stable_reference_hashes": observed_stable,
        "failures": failures,
        "ok": not failures,
    }


def validate_phase11_closure_report(
    manifest: dict[str, object],
    report: dict[str, object],
) -> dict[str, object]:
    stable = manifest.get("stable_reference_hashes")
    if not isinstance(stable, dict):
        raise ValueError("Phase 11 stable reference hashes are absent")
    summary = report.get("reference_summary")
    bindings = report.get("runtime_bindings")
    checks: dict[str, bool] = {
        "accepted": report.get("accepted") is True,
        "phase11_exit_closed": report.get("phase11_exit_closed") is True,
        "candidate_rejected": report.get("model_generated_candidate_rejected") is True,
        "later_candidate_accepted": report.get("later_fresh_proposal_accepted") is True,
        "manual_repairs": report.get("manual_repairs") == 0,
        "heldout_material": report.get("heldout_material_consumed") is False,
        "generator_changed": report.get("successor_generator_bytes_changed") is True,
        "planner_changed": report.get("successor_planner_bytes_changed") is True,
        "successor_policies_installed": (
            report.get("successor_generator_planner_installed") is True
        ),
        "recursive_use_reserved": (
            report.get("recursive_use_of_modified_successor_generator") is False
        ),
        "next_phase": report.get("next_phase") == 12,
        "reference_summary_shape": isinstance(summary, dict),
        "runtime_bindings_shape": isinstance(bindings, dict),
    }
    if isinstance(summary, dict):
        checks["runtime_summary_self_binding"] = (
            report.get("stable_reference_summary_hash") == summary.get("summary_hash")
        )
        checks["runtime_phase6_hashes"] = all(
            _valid_hash(summary.get(name))
            for name in (
                "alpha_phase6_hash",
                "beta_candidate_fixture_hash",
                "beta_invocation_hash",
                "beta_phase6_hash",
                "lifecycle_certificate_hash",
                "lifecycle_transition_hash",
                "summary_hash",
            )
        )
        try:
            observed_portable = _portable_reference_hashes(summary)
        except ValueError:
            observed_portable = None
        checks["portable_reference_hashes"] = observed_portable == stable
    if isinstance(bindings, dict):
        checks.update(
            {
                "rejection_preserved_active": (
                    bindings.get("rejection_preserved_active_package") is True
                    and bindings.get("initial_active_package_hash")
                    == bindings.get("active_package_hash_after_rejection")
                ),
                "promotion_parent": (
                    bindings.get("promotion_parent_is_unchanged_active_package") is True
                    and bindings.get("parent_package_hash")
                    == bindings.get("initial_active_package_hash")
                ),
                "ledger_sequence": bindings.get("ledger_sequence_number") == 2,
                "generator_semantic_hash_changed": (
                    bindings.get("active_generator_hash")
                    != bindings.get("successor_generator_hash")
                    and _valid_hash(bindings.get("active_generator_hash"))
                    and _valid_hash(bindings.get("successor_generator_hash"))
                ),
                "planner_semantic_hash_changed": (
                    bindings.get("active_planner_hash")
                    != bindings.get("successor_planner_hash")
                    and _valid_hash(bindings.get("active_planner_hash"))
                    and _valid_hash(bindings.get("successor_planner_hash"))
                ),
                "installed_generator_bytes": (
                    bindings.get("installed_generator_bytes_verified") is True
                    and _valid_hash(bindings.get("installed_generator_bytes_hash"))
                ),
                "installed_planner_bytes": (
                    bindings.get("installed_planner_bytes_verified") is True
                    and _valid_hash(bindings.get("installed_planner_bytes_hash"))
                ),
            }
        )
    checks["run_specific_hashes"] = all(
        _valid_hash(report.get(name))
        for name in (
            "exact_runtime_reference_hash",
            "final_report_hash",
            "promotion_hash",
            "report_hash",
            "verification_hash",
        )
    )
    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    return {
        "schema_version": "rcp-rclm-runtime-v3-phase-11-report-validation-v1",
        "manifest_hash": canonical_json_hash(manifest),
        "report_hash": canonical_json_hash(report),
        "checks": checks,
        "failures": failures,
        "ok": not failures,
    }


__all__ = [
    "PHASE11_CLOSURE_MANIFEST_RELATIVE_PATH",
    "load_phase11_closure_manifest",
    "validate_phase11_closure_manifest",
    "validate_phase11_closure_report",
]
