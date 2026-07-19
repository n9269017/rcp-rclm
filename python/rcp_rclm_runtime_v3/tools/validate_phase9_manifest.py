from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from rcp_rclm_runtime_v3.contract.reference import build_phase9_reference_fixture
from rcp_rclm_runtime_v3.contract.records import (
    SELECTED_MODEL_FAMILY,
    SELECTED_TASK_CLASS,
    SELECTED_VERIFIER_KIND,
)


def _git_blob_sha256(root: Path, relative_path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{relative_path}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"unable to read Git object {relative_path}: {stderr}")
    return hashlib.sha256(completed.stdout).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.repo_root.resolve(strict=True)
    runtime_root = root / "python/rcp_rclm_runtime_v3"
    manifest_path = runtime_root / "phase_9_manifest.json"
    validation_path = runtime_root / "phase_9_validation.json"
    schema_relative = (
        "python/rcp_rclm_executable_core_v3/contract/phase_9_contract.schema.json"
    )
    lean_contract_relative = (
        "lean/rcp_rclm_formal_core_v3/"
        "RcpRclmFormalCoreV3/Learned/ExecutableContract.lean"
    )
    audit_relative = "docs/formal_core_v3/audit/Phase9ContractAxiomAudit.lean"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    selected = manifest.get("selected_scope")
    if not isinstance(selected, dict):
        errors.append("selected scope is absent")
    else:
        expected_selected = {
            "model_family": SELECTED_MODEL_FAMILY,
            "maximum_parameter_count": 50_000_000,
            "task_class": SELECTED_TASK_CLASS,
            "task_verifier": SELECTED_VERIFIER_KIND,
        }
        if selected != expected_selected:
            errors.append("selected scope differs from the frozen Phase 9 scope")

    correspondence = manifest.get("object_correspondence")
    if not isinstance(correspondence, list) or len(correspondence) != 8:
        errors.append("expected exactly eight object-correspondence rows")
    elif len(
        {
            item.get("semantic_object")
            for item in correspondence
            if isinstance(item, dict)
        }
    ) != 8:
        errors.append("object-correspondence semantic identifiers are not unique")

    boundary = manifest.get("claim_boundary")
    if (
        not isinstance(boundary, dict)
        or not boundary
        or any(value is not False for value in boundary.values())
    ):
        errors.append("unsupported Phase 9 claim is enabled")

    fixture = build_phase9_reference_fixture()
    expected_hashes = {
        "predecessor_state_hash": fixture.predecessor.state_hash,
        "candidate_state_hash": fixture.candidate.state_hash,
        "update_hash": fixture.update.update_hash,
        "certificate_hash": fixture.certificate.certificate_hash,
        "heldout_policy_hash": fixture.heldout_policy.policy_hash,
        "transition_report_hash": fixture.report.semantic_report_hash,
    }
    if manifest.get("reference_hashes") != expected_hashes:
        errors.append("manifest reference hashes do not match recomputation")
    if validation.get("reference_hashes") != expected_hashes:
        errors.append("validation reference hashes do not match recomputation")

    expected_artifacts = {
        "phase_9_contract_schema_sha256": _git_blob_sha256(root, schema_relative),
        "lean_executable_contract_sha256": _git_blob_sha256(
            root, lean_contract_relative
        ),
        "phase_9_axiom_audit_sha256": _git_blob_sha256(root, audit_relative),
    }
    declared_artifacts = manifest.get("artifact_hashes")
    if declared_artifacts != expected_artifacts:
        pending = (
            manifest.get("status")
            == "implementation_started_pending_authoritative_ci"
        )
        empty_pending = isinstance(declared_artifacts, dict) and all(
            value is None for value in declared_artifacts.values()
        )
        if not (pending and empty_pending):
            errors.append("artifact hashes do not match repository Git-object bytes")

    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-9-manifest-validation-v1",
        "selected_scope": selected,
        "reference_hashes": expected_hashes,
        "artifact_hashes": expected_artifacts,
        "errors": errors,
        "ok": not errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
