from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.architecture import CompactTransformerArchitecture
from rcp_rclm_runtime_v3.phase10.reference import build_phase10_reference_fixture
from rcp_rclm_runtime_v3.phase10.tokenizer import ByteTokenizerManifest


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

    repo_root = args.repo_root.resolve(strict=True)
    runtime_root = repo_root / "python" / "rcp_rclm_runtime_v3"
    manifest_path = runtime_root / "phase_10_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    phase9 = json.loads((runtime_root / "phase_9_manifest.json").read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}

    checks["phase9_complete"] = phase9.get("status") == "phase9_contract_complete_at_declared_scope"
    checks["phase10_status_open"] = manifest.get("status") == "phase10_substrate_started_not_exit_closed"

    architecture = CompactTransformerArchitecture()
    tokenizer = ByteTokenizerManifest.frozen()
    architecture_record = manifest["architecture"]
    tokenizer_record = manifest["tokenizer"]
    checks["architecture_hash"] = architecture_record["architecture_hash"] == architecture.architecture_hash
    checks["base_parameter_count"] = architecture_record["base_parameter_count"] == architecture.base_parameter_count
    checks["tokenizer_hash"] = tokenizer_record["tokenizer_raw_hash"] == tokenizer.tokenizer_bytes_hash
    checks["vocabulary_hash"] = tokenizer_record["vocabulary_hash"] == tokenizer.vocabulary_hash
    checks["tokenizer_manifest_hash"] = tokenizer_record["tokenizer_manifest_hash"] == tokenizer.manifest_hash

    paths = {
        "phase_10_schema_sha256": (
            "python/rcp_rclm_executable_core_v3/contract/"
            "phase_10_substrate.schema.json"
        ),
        "transformer_extension_lean_sha256": (
            "lean/rcp_rclm_formal_core_v3/RcpRclmFormalCoreV3/"
            "Learned/TransformerExtension.lean"
        ),
        "phase_10_transformer_axiom_audit_sha256": (
            "docs/formal_core_v3/audit/"
            "Phase10TransformerExtensionAxiomAudit.lean"
        ),
    }
    artifact_hashes = manifest["artifact_hashes"]
    for name, relative_path in paths.items():
        checks[name] = (
            (repo_root / relative_path).is_file()
            and artifact_hashes[name] == _git_blob_sha256(repo_root, relative_path)
        )

    required_source_paths = (
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/__init__.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/adapters.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/architecture.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/constants.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/package.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/reference.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/tensors.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/tokenizer.py",
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/validation.py",
        "python/rcp_rclm_runtime_v3/tests_phase10/test_substrate.py",
    )
    checks["required_source_paths"] = all((repo_root / path).is_file() for path in required_source_paths)
    committed_binary_paths = tuple(
        path
        for path in (runtime_root / "rcp_rclm_runtime_v3" / "phase10").rglob("*.bin")
        if path.is_file()
    )
    checks["no_committed_model_binary"] = not committed_binary_paths

    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-manifest-") as temp_dir:
        fixture = build_phase10_reference_fixture(Path(temp_dir) / "reference")
        reference = manifest["reference_hashes"]
        observed_reference = {
            "reference_hash": fixture.to_json()["reference_hash"],
            "predecessor_package_hash": fixture.predecessor.package_hash,
            "successor_package_hash": fixture.successor.package_hash,
            "predecessor_model_identity_hash": fixture.predecessor.model_identity_hash,
            "successor_model_identity_hash": fixture.successor.model_identity_hash,
            "predecessor_report_hash": fixture.predecessor_report.semantic_report_hash,
            "successor_report_hash": fixture.successor_report.semantic_report_hash,
            "extension_report_hash": fixture.extension_report.semantic_report_hash,
        }
        checks["reference_accepts"] = fixture.accepted
        for name, value in observed_reference.items():
            checks[f"reference_{name}"] = reference[name] == value

    claim_boundary = manifest["claim_boundary"]
    checks["claim_substrate_true"] = (
        claim_boundary["canonical_compact_transformer_package"] is True
        and claim_boundary["zero_lora_conservative_extension"] is True
    )
    checks["claim_exit_false"] = (
        claim_boundary["actual_compact_language_model_training"] is False
        and claim_boundary["actual_promoted_learned_successor"] is False
        and claim_boundary["authoritative_deterministic_inference"] is False
        and claim_boundary["frontier_expansion"] is False
        and claim_boundary["independent_replay_without_retraining"] is False
        and claim_boundary["kl_qre_evidence"] is False
        and claim_boundary["lean_task_completion"] is False
        and claim_boundary["phase_10_exit_closed"] is False
    )

    failures = tuple(sorted(name for name, accepted in checks.items() if not accepted))
    report = {
        "schema_version": "rcp-rclm-runtime-v3-phase-10-manifest-validation-v1",
        "manifest_path": manifest_path.relative_to(repo_root).as_posix(),
        "checks": checks,
        "failures": list(failures),
        "ok": not failures,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
