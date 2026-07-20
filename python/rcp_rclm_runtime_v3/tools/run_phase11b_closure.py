from __future__ import annotations

import argparse
import subprocess
import tempfile
import traceback
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase11.phase11b_closure import (
    Phase11BClosureEvidence,
    promote_phase11b_candidate,
    verify_phase11b_candidates,
)
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import build_phase11b_reference


def _prewarm_pinned_lean_identity(repo_root: Path) -> dict[str, str]:
    project_root = repo_root / "lean/rcp_rclm_formal_core_v2"
    commands = {
        "lean_version": ("lake", "env", "lean", "--version"),
        "lake_version": ("lake", "--version"),
        "lean_prefix": ("lake", "env", "lean", "--print-prefix"),
    }
    result: dict[str, str] = {}
    for label, command in commands.items():
        completed = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            check=False,
            timeout=180,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"pinned Lean identity prewarm failed for {label}: "
                f"{detail or completed.returncode}"
            )
        output = completed.stdout.decode("utf-8", errors="strict").strip()
        if not output:
            raise RuntimeError(f"pinned Lean identity prewarm returned no output for {label}")
        result[label] = sha256_hex(output.encode("utf-8"))
    return result


def _write_diagnostic(
    path: Path,
    *,
    stage: str,
    detail: str,
    traceback_text: str,
    context: dict[str, object],
) -> None:
    payload = {
        "schema_id": "runtime.v3.phase11b.closure_diagnostic.v1",
        "stage": stage,
        "accepted": False,
        "detail": detail,
        "traceback": traceback_text,
        "traceback_sha256": sha256_hex(traceback_text.encode("utf-8")),
        "context": context,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    lean_project_root = args.lean_project_root.resolve(strict=True)
    output = args.out.resolve(strict=False)
    diagnostic = output.with_name("phase_11_closure_diagnostic.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = "initialize"
    prewarm_hashes: dict[str, str] = {}
    reference = None
    verification = None
    promotion = None
    try:
        stage = "prewarm_pinned_lean_identity"
        prewarm_hashes = _prewarm_pinned_lean_identity(repo_root)
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11b-closure-") as temporary:
            root = Path(temporary)
            stage = "build_model_generated_candidate_sequence"
            reference = build_phase11b_reference(root / "source_trajectory")

            stage = "verify_rejected_and_accepted_candidates"
            verification = verify_phase11b_candidates(
                reference,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
            )

            stage = "record_rejection_and_promote_successor"
            promotion = promote_phase11b_candidate(
                reference,
                verification,
                store_root=root / "phase7_store",
                evidence_root=root / "promotion_evidence",
            )

            stage = "assemble_phase11_closure"
            closure = Phase11BClosureEvidence(
                reference=reference,
                verification=verification,
                promotion=promotion,
            )
            reference_summary = reference.summary_json()
            runtime_bindings = {
                "schema_id": "runtime.v3.phase11b.runtime_bindings.v1",
                "verification_report_hash": verification.report_hash,
                "promotion_report_hash": promotion.report_hash,
                "rejection_attempt_report_hash": promotion.rejection_attempt.report_hash,
                "rejection_ledger_hash": promotion.rejection_ledger_hash,
                "promotion_attempt_report_hash": promotion.promotion_attempt.report_hash,
                "promotion_ledger_hash": promotion.promotion.ledger_entry.entry_hash,
                "initial_active_package_hash": promotion.initial_active_package_hash,
                "active_package_hash_after_rejection": (
                    promotion.active_package_hash_after_rejection
                ),
                "promoted_package_hash": promotion.promotion.package_manifest.package_hash,
                "parent_package_hash": promotion.promotion.package_manifest.parent_package_hash,
                "ledger_sequence_number": (
                    promotion.promotion.snapshot.pointer.ledger_sequence_number
                ),
                "installed_generator_bytes_hash": promotion.installed_generator_bytes_hash,
                "installed_planner_bytes_hash": promotion.installed_planner_bytes_hash,
                "active_generator_hash": reference.active.active_manifest.generator_policy_hash,
                "successor_generator_hash": (
                    reference.beta_candidate.manifest.generator_policy_hash
                ),
                "active_planner_hash": reference.active.active_manifest.planner_policy_hash,
                "successor_planner_hash": (
                    reference.beta_candidate.manifest.planner_policy_hash
                ),
                "rejection_preserved_active_package": (
                    promotion.active_package_hash_after_rejection
                    == promotion.initial_active_package_hash
                ),
                "promotion_parent_is_unchanged_active_package": (
                    promotion.promotion.package_manifest.parent_package_hash
                    == promotion.initial_active_package_hash
                ),
                "installed_generator_bytes_verified": True,
                "installed_planner_bytes_verified": True,
            }
            report = closure.to_json()
            report["report_hash"] = closure.report_hash
            report["pinned_identity_prewarm_hashes"] = prewarm_hashes
            report["reference_summary"] = reference_summary
            report["stable_reference_summary_hash"] = reference_summary["summary_hash"]
            report["exact_runtime_reference_hash"] = reference.reference_hash
            report["runtime_bindings"] = runtime_bindings
            report["untrusted_training_evidence_required_by_workflow"] = True
            report["claim_boundary"] = {
                "one_active_predecessor_model": True,
                "one_model_generated_candidate_rejected": True,
                "one_later_fresh_model_generated_candidate_promoted": True,
                "successor_generator_planner_installed": True,
                "successor_generator_used_recursively": False,
                "phase11_exit_closed": closure.accepted,
                "phase12_required_for_recursive_use": True,
            }
            report["final_report_hash"] = canonical_json_hash(report)
            if not closure.accepted:
                raise ValueError("Phase 11B closure did not accept")

        output.write_bytes(canonical_json_bytes(report))
        diagnostic.write_bytes(
            canonical_json_bytes(
                {
                    "schema_id": "runtime.v3.phase11b.closure_diagnostic.v1",
                    "stage": "complete",
                    "accepted": True,
                    "detail": "Phase 11 closure completed",
                    "traceback": "",
                    "traceback_sha256": sha256_hex(b""),
                    "context": {
                        "pinned_identity_prewarm_hashes": prewarm_hashes,
                        "report_hash": report["report_hash"],
                        "final_report_hash": report["final_report_hash"],
                        "runtime_bindings_hash": canonical_json_hash(
                            report["runtime_bindings"]
                        ),
                    },
                }
            )
        )
        return 0
    except Exception as exc:
        traceback_text = traceback.format_exc()
        context: dict[str, object] = {
            "pinned_identity_prewarm_hashes": prewarm_hashes,
            "reference_accepted": bool(reference and reference.accepted),
            "verification_accepted": bool(verification and verification.accepted),
            "promotion_accepted": bool(promotion and promotion.accepted),
        }
        if reference is not None:
            context["reference_summary"] = reference.summary_json()
        if verification is not None:
            context["verification"] = verification.to_json()
        if promotion is not None:
            context["promotion"] = promotion.to_json()
        _write_diagnostic(
            diagnostic,
            stage=stage,
            detail=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback_text,
            context=context,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
