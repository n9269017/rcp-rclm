from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.learned_reference import build_phase10_learned_reference


def _git_blob_sha256(root: Path, relative_path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{relative_path}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"unable to read Git object {relative_path}: "
            f"{completed.stderr.decode('utf-8', errors='replace')}"
        )
    return hashlib.sha256(completed.stdout).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve(strict=True)
    manifest_path = root / "python/rcp_rclm_runtime_v3/phase_10_learned_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}

    expected_profile = {
        "architecture_id": "rclm-compact-decoder-13m-v1",
        "authoritative_distribution": "exact_dyadic_logit_v1",
        "authoritative_inference": "sparse_last_token_transition_v1",
        "candidate_completion": "omega",
        "candidate_update": "model.layers.00.attn_output.weight",
        "decoding": "greedy_lowest_token_id_tiebreak",
        "heldout_task_id": "lean.phase10.heldout.linear_gap",
        "model_family": "compact_decoder_only_transformer_v1",
        "protected_completion": "rfl",
        "protected_task_id": "lean.phase10.protected.reflexive_seven",
        "training_backend": "untrusted_pytorch_cpu_float64_sgd_v1",
    }
    checks["selected_profile"] = manifest.get("selected_profile") == expected_profile
    required_paths = manifest.get("required_source_paths")
    checks["required_source_paths_shape"] = isinstance(required_paths, list) and bool(required_paths)
    if isinstance(required_paths, list):
        checks["required_source_paths_present"] = all(
            isinstance(path, str) and (root / path).is_file() for path in required_paths
        )
    else:
        checks["required_source_paths_present"] = False

    boundary = manifest.get("claim_boundary")
    checks["claim_boundary"] = isinstance(boundary, dict) and boundary == {
        "atomic_promotion": False,
        "authoritative_exact_sparse_inference": True,
        "full_native_float_transformer_equivalence": False,
        "independent_replay_without_training": False,
        "new_heldout_lean_task_certified": True,
        "phase10_exit_closed": False,
        "phase6_realization_and_rollback": False,
        "phase9_gate_d_transition_accepts": True,
        "selected_entropy_kl_diagonal_qre": True,
        "trained_nontrivial_compact_model_weights": True,
        "untrusted_isolated_training_worker": True,
    }

    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10b-manifest-") as temporary:
        fixture = build_phase10_learned_reference(Path(temporary) / "reference")
        summary = fixture.summary_json()
        observed_reference = {
            "candidate_model_identity_hash": fixture.candidate_manifest.model_identity_hash,
            "candidate_package_hash": fixture.candidate_manifest.package_hash,
            "information_report_hash": fixture.information_report.report_hash,
            "phase9_transition_report_hash": fixture.transition_report.semantic_report_hash,
            "predecessor_model_identity_hash": fixture.predecessor_manifest.model_identity_hash,
            "predecessor_package_hash": fixture.predecessor_manifest.package_hash,
            "summary_hash": summary["summary_hash"],
        }
        checks["reference_accepts"] = fixture.accepted

    artifact_paths = {
        "phase_10_information_lean_sha256": (
            "lean/rcp_rclm_formal_core_v3/"
            "RcpRclmFormalCoreV3/Learned/Phase10Information.lean"
        ),
        "phase_10_learned_schema_sha256": (
            "python/rcp_rclm_executable_core_v3/contract/phase_10_learned.schema.json"
        ),
        "phase_10_learned_workflow_sha256": (
            ".github/workflows/runtime-v3-phase-10-learned.yml"
        ),
        "phase_10_training_worker_sha256": (
            "python/rcp_rclm_runtime_v3/tools/phase10_training_worker.py"
        ),
    }
    observed_artifacts = {
        name: _git_blob_sha256(root, path) for name, path in artifact_paths.items()
    }
    status = manifest.get("status")
    if status == "implementation_started_pending_authoritative_ci":
        declared_reference = manifest.get("reference_hashes")
        declared_artifacts = manifest.get("artifact_hashes")
        checks["pending_reference_hashes"] = isinstance(declared_reference, dict) and all(
            value is None for value in declared_reference.values()
        )
        checks["pending_artifact_hashes"] = isinstance(declared_artifacts, dict) and all(
            value is None for value in declared_artifacts.values()
        )
    elif status == "phase10b_learned_execution_complete_at_declared_scope":
        checks["reference_hashes"] = manifest.get("reference_hashes") == observed_reference
        checks["artifact_hashes"] = manifest.get("artifact_hashes") == observed_artifacts
    else:
        checks["status"] = False

    failures = sorted(name for name, accepted in checks.items() if accepted is not True)
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-10b-manifest-validation-v1",
        "status": status,
        "checks": checks,
        "reference_hashes": observed_reference,
        "artifact_hashes": observed_artifacts,
        "failures": failures,
        "ok": not failures,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
