#!/usr/bin/env python3
"""Create an auditable run-specific no-leakage/no-oracle/no-manual-repair attestation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from crsi_re_bench_schema import (
    NO_LEAKAGE_CONFIRMATION,
    SCHEMA_VERSION,
    SUITE_NAME,
    hash_file_or_tree,
    safe_rel,
    sha256_obj,
    utc_now,
    validate_no_leakage_manifest,
    write_json,
)


def parse_evidence(values: Sequence[str], repo_root: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for value in values:
        path = Path(value)
        path = path if path.is_absolute() else repo_root / path
        if not path.exists():
            raise FileNotFoundError(f"evidence path does not exist: {path}")
        hashes[safe_rel(path, repo_root)] = hash_file_or_tree(path)
    return hashes


def create_attestation(args: argparse.Namespace) -> Dict[str, Any]:
    if args.confirm_attestation != NO_LEAKAGE_CONFIRMATION:
        raise ValueError(f"--confirm-attestation must equal {NO_LEAKAGE_CONFIRMATION}")
    if not args.confirm_provider_no_training_use:
        raise ValueError("--confirm-provider-no-training-use is required")
    repo_root = args.repo_root.resolve()
    evidence_hashes = parse_evidence(args.evidence, repo_root)
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "kind": "run_specific_no_leakage_attestation",
        "attested": True,
        "operator": args.operator,
        "benchmark_answers_in_prompt": False,
        "hidden_tests_exposed": False,
        "hidden_reference_solution_access": False,
        "protected_solution_material_access": False,
        "private_solution_material_used": False,
        "benchmark_training_use": False,
        "diagnostic_oracle": False,
        "manual_repair_inside_run": False,
        "manual_repair_inside_chain": False,
        "human_patch_inside_run": False,
        "human_patch_inside_chain": False,
        "human_intervention_enabled": False,
        "scorer_modified": False,
        "task_environment_modified_outside_agent_submission": False,
        "post_hoc_score_selection": False,
        "results_manually_declared": False,
        "provider_no_training_use_confirmed": True,
        "official_scorer_outputs_required": True,
        "all_operator_interventions_logged": True,
        "provider_data_policy_id": args.provider_data_policy_id,
        "service_or_model_access_policy_id": args.model_access_policy_id,
        "official_task_material_storage_policy": "outside_public_rcp_rclm_repository",
        "protected_solution_publication_prohibited": True,
        "secrets_committed_to_repository": False,
        "evidence_hashes": evidence_hashes,
        "notes": args.notes,
        "created_utc": utc_now(),
    }
    manifest["attestation_hash"] = sha256_obj({k: v for k, v in manifest.items() if k != "attestation_hash"})
    errors = validate_no_leakage_manifest(manifest)
    manifest["errors"] = errors
    manifest["ok"] = not errors
    manifest["attestation_hash"] = sha256_obj({k: v for k, v in manifest.items() if k != "attestation_hash"})
    return manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create a run-specific no-leakage/no-oracle/no-manual-repair attestation.")
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--operator", required=True)
    p.add_argument("--provider-data-policy-id", required=True)
    p.add_argument("--model-access-policy-id", default="same_model_family_and_provider_access_for_all_packages_v1")
    p.add_argument("--confirm-provider-no-training-use", action="store_true")
    p.add_argument("--confirm-attestation", required=True)
    p.add_argument("--evidence", action="append", default=[], help="Optional evidence file or directory; may be repeated.")
    p.add_argument("--notes", default="")
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        manifest = create_attestation(args)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2, sort_keys=True))
        return 1
    write_json(args.out, manifest)
    print(json.dumps({
        "ok": manifest["ok"],
        "attestation": str(args.out),
        "attestation_hash": manifest["attestation_hash"],
        "evidence_count": len(manifest["evidence_hashes"]),
        "errors": manifest["errors"],
    }, indent=2, sort_keys=True))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
