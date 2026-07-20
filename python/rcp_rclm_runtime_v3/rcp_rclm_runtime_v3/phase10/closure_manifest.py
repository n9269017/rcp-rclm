from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime_v3.phase10.lifecycle import (
    build_phase10_phase6_fixture,
    replay_phase10_phase6,
)

PHASE10_CLOSURE_MANIFEST_RELATIVE_PATH: Final[Path] = Path(
    "python/rcp_rclm_runtime_v3/phase_10_closure_manifest.json"
)
PHASE10B_MANIFEST_RELATIVE_PATH: Final[Path] = Path(
    "python/rcp_rclm_runtime_v3/phase_10_learned_manifest.json"
)

_EXPECTED_STATUS: Final[str] = "phase10_exit_closed_at_exact_code_proof"
_EXPECTED_SCHEMA_VERSION: Final[str] = (
    "rcp-rclm-runtime-v3-phase-10-closure-manifest-v1"
)
_EXPECTED_CLAIM_BOUNDARY: Final[dict[str, bool]] = {
    "actual_promoted_learned_successor": True,
    "atomic_content_addressed_promotion": True,
    "authoritative_exact_sparse_inference": True,
    "autonomous_unbounded_rsi": False,
    "full_native_float_transformer_equivalence": False,
    "generic_successor_availability": False,
    "independent_replay_without_training": True,
    "phase10_exit_closed": True,
    "phase6_realization_and_rollback": True,
    "phase9_gate_d_transition_accepts": True,
    "recursive_self_hosting": False,
    "selected_entropy_kl_diagonal_qre": True,
    "selected_lean_task_frontier_expansion": True,
    "untrusted_isolated_training_worker": True,
}
_EXPECTED_REPORT_BOUNDARY: Final[dict[str, bool]] = {
    "autonomous_unbounded_rsi": False,
    "generic_successor_availability": False,
    "one_promoted_learned_successor": True,
    "one_selected_compact_model_family": True,
    "one_selected_lean_task_class": True,
    "self_hosted_recursive_generation": False,
}
_EXPECTED_ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
    {"final", "macos", "pinned", "training", "ubuntu", "windows"}
)
_HEX40: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
_SHA256_DIGEST: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def load_phase10_closure_manifest(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve(strict=True)
    return _load_json(root / PHASE10_CLOSURE_MANIFEST_RELATIVE_PATH)


def _valid_hash(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        validate_hash256(value, "phase10_closure_manifest.hash")
    except ValueError:
        return False
    return True


def _expected_artifact_name(kind: str, run_id: int, attempt: int) -> str:
    suffix = f"{run_id}-{attempt}"
    if kind == "ubuntu":
        return f"runtime-v3-phase-10-closure-ubuntu-latest-{suffix}"
    if kind == "windows":
        return f"runtime-v3-phase-10-closure-windows-latest-{suffix}"
    if kind == "macos":
        return f"runtime-v3-phase-10-closure-macos-latest-{suffix}"
    if kind == "training":
        return f"runtime-v3-phase-10-closure-training-{suffix}"
    if kind == "pinned":
        return f"runtime-v3-phase-10-closure-pinned-{suffix}"
    if kind == "final":
        return f"runtime-v3-phase-10-closure-final-{suffix}"
    raise ValueError(f"unsupported Phase 10 artifact kind: {kind}")


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
    if not isinstance(closure_report, dict) or not closure_report:
        return False
    if not all(_valid_hash(item) for item in closure_report.values()):
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


def _recompute_reference_hashes(repo_root: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-closure-manifest-") as temporary:
        temporary_root = Path(temporary)
        fixture = build_phase10_phase6_fixture(temporary_root / "fixture")
        replay = replay_phase10_phase6(
            fixture.root,
            temporary_root / "replay_candidate",
        )
        realization = fixture.phase6.report.realization
        if realization is None:
            raise ValueError("Phase 10 closure manifest requires Phase 6 realization")
        return {
            "candidate_model_identity_hash": (
                fixture.reference.candidate_manifest.model_identity_hash
            ),
            "candidate_package_hash": fixture.reference.candidate_manifest.package_hash,
            "information_report_hash": fixture.reference.information_report.report_hash,
            "lifecycle_certificate_hash": fixture.lifecycle_certificate.certificate_hash,
            "lifecycle_transition_report_hash": (
                fixture.lifecycle_transition.semantic_report_hash
            ),
            "phase10b_transition_report_hash": (
                fixture.reference.transition_report.semantic_report_hash
            ),
            "phase6_fixture_hash": str(fixture.to_json()["fixture_hash"]),
            "phase6_replay_report_hash": str(replay["report_hash"]),
            "phase6_report_hash": fixture.phase6.report.report_hash,
            "predecessor_model_identity_hash": (
                fixture.reference.predecessor_manifest.model_identity_hash
            ),
            "predecessor_package_hash": (
                fixture.reference.predecessor_manifest.package_hash
            ),
            "rollback_hash": realization.rollback.rollback_hash,
        }


def validate_phase10_closure_manifest(
    repo_root: Path,
    *,
    recompute_reference: bool = True,
) -> dict[str, object]:
    root = repo_root.resolve(strict=True)
    manifest = load_phase10_closure_manifest(root)
    checks: dict[str, bool] = {
        "schema_version": manifest.get("schema_version") == _EXPECTED_SCHEMA_VERSION,
        "status": manifest.get("status") == _EXPECTED_STATUS,
        "claim_boundary": manifest.get("claim_boundary") == _EXPECTED_CLAIM_BOUNDARY,
        "code_proof": _validate_code_proof(manifest.get("code_proof")),
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

    phase10b = _load_json(root / PHASE10B_MANIFEST_RELATIVE_PATH)
    checks["phase10b_manifest_closed"] = (
        phase10b.get("status")
        == "phase10b_learned_execution_complete_at_declared_scope"
    )

    declared_reference = manifest.get("reference_hashes")
    observed_reference: dict[str, str] | None = None
    if recompute_reference:
        observed_reference = _recompute_reference_hashes(root)
        checks["reference_hashes"] = declared_reference == observed_reference
    else:
        checks["reference_hash_shape"] = (
            isinstance(declared_reference, dict)
            and bool(declared_reference)
            and all(_valid_hash(value) for value in declared_reference.values())
        )

    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    return {
        "schema_version": "rcp-rclm-runtime-v3-phase-10-closure-validation-v1",
        "manifest_hash": canonical_json_hash(manifest),
        "checks": checks,
        "observed_reference_hashes": observed_reference,
        "failures": failures,
        "ok": not failures,
    }


def validate_phase10_closure_report(
    manifest: dict[str, object],
    report: dict[str, object],
) -> dict[str, object]:
    reference = manifest.get("reference_hashes")
    if not isinstance(reference, dict):
        raise ValueError("Phase 10 closure manifest reference hashes are absent")
    checks = {
        "accepted": report.get("accepted") is True,
        "phase10_exit_closed": report.get("phase10_exit_closed") is True,
        "atomic_promotion": report.get("atomic_promotion") is True,
        "independent_replay": report.get("independent_replay_without_retraining") is True,
        "rollback_exact": report.get("rollback_exact") is True,
        "protected_retained": report.get("protected_retained") is True,
        "new_heldout_task_certified": report.get("new_heldout_task_certified") is True,
        "selected_kl_qre_nonregression": (
            report.get("selected_kl_qre_nonregression") is True
        ),
        "training_invocations": report.get("training_invocations_during_replay") == 0,
        "generator_invocations": report.get("generator_invocations_during_replay") == 0,
        "claim_boundary": report.get("claim_boundary") == _EXPECTED_REPORT_BOUNDARY,
        "frontier_before": report.get("frontier_before")
        == ["lean.phase10.protected.reflexive_seven"],
        "frontier_after": report.get("frontier_after")
        == [
            "lean.phase10.heldout.linear_gap",
            "lean.phase10.protected.reflexive_seven",
        ],
        "candidate_model_identity_hash": report.get("candidate_model_identity_hash")
        == reference.get("candidate_model_identity_hash"),
        "predecessor_model_identity_hash": report.get("predecessor_model_identity_hash")
        == reference.get("predecessor_model_identity_hash"),
        "phase6_fixture_hash": report.get("phase6_fixture_hash")
        == reference.get("phase6_fixture_hash"),
        "information_report_hash": report.get("information_report_hash")
        == reference.get("information_report_hash"),
        "phase9_transition_report_hash": report.get("phase9_transition_report_hash")
        == reference.get("lifecycle_transition_report_hash"),
        "run_specific_hashes": all(
            _valid_hash(report.get(name))
            for name in (
                "promoted_package_hash",
                "promotion_report_hash",
                "replay_report_hash",
                "report_hash",
                "source_verification_hash",
            )
        ),
    }
    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    return {
        "schema_version": "rcp-rclm-runtime-v3-phase-10-report-validation-v1",
        "checks": checks,
        "failures": failures,
        "ok": not failures,
    }


__all__ = [
    "PHASE10_CLOSURE_MANIFEST_RELATIVE_PATH",
    "load_phase10_closure_manifest",
    "validate_phase10_closure_manifest",
    "validate_phase10_closure_report",
]
