from __future__ import annotations

import argparse
import subprocess
import tempfile
import traceback
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.closure import (
    Phase10ClosureEvidence,
    remove_phase10_training_backend,
    replay_promoted_phase10_candidate,
)
from rcp_rclm_runtime_v3.phase10.closure_manifest import (
    load_phase10_closure_manifest,
    validate_phase10_closure_manifest,
    validate_phase10_closure_report,
)
from rcp_rclm_runtime_v3.phase10.lifecycle import build_phase10_phase6_fixture
from rcp_rclm_runtime_v3.phase10.promotion import (
    promote_phase10_candidate,
    verify_phase10_candidate,
)


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


def _verification_context(error: BaseException) -> dict[str, object]:
    current = error.__traceback__
    while current is not None:
        frame = current.tb_frame
        evidence = frame.f_locals.get("evidence")
        if frame.f_code.co_name == "verify_phase10_candidate" and evidence is not None:
            checks = {
                "predecessor_protected_solved": evidence.predecessor_protected.solved,
                "predecessor_heldout_unsolved": not evidence.predecessor_heldout.solved,
                "candidate_protected_solved": evidence.candidate_protected.solved,
                "candidate_heldout_solved": evidence.candidate_heldout.solved,
                "information_accepted": evidence.information_report.accepted,
                "expected_task_reports_match": evidence.expected_task_reports_match,
                "gate_b_lean_accepted": evidence.gate_b_lean.report.accepted,
                "gate_b_source_guard_clean": evidence.gate_b_lean.source_guard.clean,
                "hardened_checker_accepted": evidence.hardened_checker.accepted,
                "candidate_unchanged": evidence.candidate_unchanged,
                "training_modules_absent": not evidence.forbidden_training_modules_loaded,
            }
            compilation = evidence.gate_b_lean.compilation
            compiler_output: dict[str, object]
            if compilation is None:
                compiler_output = {"invoked": False}
            else:
                compiler_output = {
                    "invoked": True,
                    "command": list(compilation.command),
                    "source_name": compilation.source_name,
                    "exit_code": compilation.exit_code,
                    "timed_out": compilation.timed_out,
                    "stdout": compilation.stdout.decode("utf-8", errors="replace"),
                    "stderr": compilation.stderr.decode("utf-8", errors="replace"),
                }
            return {
                "verification_checks": checks,
                "verification_failures": sorted(
                    name for name, accepted in checks.items() if accepted is not True
                ),
                "forbidden_training_modules_loaded": list(
                    evidence.forbidden_training_modules_loaded
                ),
                "gate_b_generated_source": evidence.gate_b_lean.generated.source_text,
                "gate_b_compilation": compiler_output,
                "gate_b_lean_report": evidence.gate_b_lean.report.to_json(),
                "gate_b_source_guard": evidence.gate_b_lean.source_guard.to_json(),
                "hardened_checker": evidence.hardened_checker.to_json(),
                "task_reports": {
                    "predecessor_protected": evidence.predecessor_protected.to_json(),
                    "predecessor_heldout": evidence.predecessor_heldout.to_json(),
                    "candidate_protected": evidence.candidate_protected.to_json(),
                    "candidate_heldout": evidence.candidate_heldout.to_json(),
                },
            }
        current = current.tb_next
    return {}


def _write_diagnostic(
    path: Path,
    *,
    stage: str,
    accepted: bool,
    detail: str,
    traceback_text: str,
    context: dict[str, object],
) -> None:
    content = {
        "schema_id": "runtime.v3.phase10.closure_diagnostic.v1",
        "stage": stage,
        "accepted": accepted,
        "detail": detail,
        "traceback": traceback_text,
        "traceback_sha256": sha256_hex(traceback_text.encode("utf-8")),
        "context": context,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(content))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lean-project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    lean_project_root = args.lean_project_root.resolve(strict=True)
    output = args.out.resolve(strict=False)
    diagnostic = output.with_name("phase_10_closure_diagnostic.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = "initialize"
    prewarm_hashes: dict[str, str] = {}
    closure_accepted = False
    manifest_validation: dict[str, object] | None = None

    try:
        stage = "validate_retained_closure_manifest"
        manifest_validation = validate_phase10_closure_manifest(
            repo_root,
            recompute_reference=False,
        )
        if manifest_validation["ok"] is not True:
            raise ValueError(
                "retained Phase 10 closure manifest failed: "
                f"{manifest_validation['failures']}"
            )
        retained_manifest = load_phase10_closure_manifest(repo_root)

        stage = "prewarm_pinned_lean_identity"
        prewarm_hashes = _prewarm_pinned_lean_identity(repo_root)
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-closure-") as temporary:
            root = Path(temporary)
            stage = "build_phase6_fixture"
            fixture = build_phase10_phase6_fixture(root / "source_trajectory")

            stage = "verify_source_candidate"
            source_verification = verify_phase10_candidate(
                fixture,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
            )

            stage = "promote_candidate"
            promotion = promote_phase10_candidate(
                fixture,
                source_verification,
                store_root=root / "phase7_store",
                evidence_root=root / "promotion_evidence",
            )

            stage = "remove_training_backend"
            removed_paths = remove_phase10_training_backend(repo_root)

            stage = "replay_promoted_candidate"
            replay = replay_promoted_phase10_candidate(
                fixture,
                promotion,
                repo_root=repo_root,
                lean_project_root=lean_project_root,
                replay_candidate_root=root / "replay_candidate",
                removed_training_paths=removed_paths,
            )

            stage = "assemble_closure"
            closure = Phase10ClosureEvidence(
                fixture=fixture,
                source_verification=source_verification,
                promotion=promotion,
                replay=replay,
            )
            report = closure.to_json()
            report["report_hash"] = closure.report_hash
            report["pinned_identity_prewarm_hashes"] = prewarm_hashes

            stage = "validate_closure_against_retained_manifest"
            report_validation = validate_phase10_closure_report(
                retained_manifest,
                report,
            )
            closure_accepted = closure.accepted and report_validation["ok"] is True
            if not closure_accepted:
                raise ValueError(
                    "Phase 10 closure report differs from the retained manifest: "
                    f"{report_validation['failures']}"
                )
            report["retained_closure_manifest_hash"] = manifest_validation[
                "manifest_hash"
            ]
            report["retained_manifest_validation_hash"] = canonical_json_hash(
                manifest_validation
            )
            report["retained_report_validation_hash"] = canonical_json_hash(
                report_validation
            )

        output.write_bytes(canonical_json_bytes(report))
        _write_diagnostic(
            diagnostic,
            stage="complete",
            accepted=closure_accepted,
            detail="Phase 10 closure completed",
            traceback_text="",
            context={
                "pinned_identity_prewarm_hashes": prewarm_hashes,
                "retained_closure_manifest_hash": manifest_validation["manifest_hash"],
            },
        )
        return 0 if closure_accepted else 1
    except Exception as exc:
        traceback_text = traceback.format_exc()
        context = _verification_context(exc)
        context["pinned_identity_prewarm_hashes"] = prewarm_hashes
        context["retained_manifest_validation"] = manifest_validation
        _write_diagnostic(
            diagnostic,
            stage=stage,
            accepted=False,
            detail=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback_text,
            context=context,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
