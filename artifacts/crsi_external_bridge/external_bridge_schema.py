#!/usr/bin/env python3
"""Schema utilities for the CRSI-RE/METR external bridge.

The bridge is deliberately benchmark-adapter-first: it verifies that an external
score ledger is bound to a previously recorded CRSI-Core chain without breaking
RCP/RCLM certificate preservation, protected non-loss invariants, hash-chain
integrity, or no-oracle/no-leakage conditions. It does not itself claim an
official RE-Bench/METR result unless official evaluator artifacts are supplied
and the harness is invoked with the corresponding flags.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

SCHEMA_VERSION = "crsi-external-bridge-v1"
SUITE_NAME = "CRSI-RE/METR Bridge: Certificate-preserving external AI-R&D benchmark adapter"

CORE_PROTECTED_INVARIANT_KEYS = [
    "certificate_preserved",
    "predecessor_checker_accepts_successor",
    "all_pcs_checked",
    "residuals_nonpositive",
    "goal_identity_drift_zero",
    "trust_anchor_unchanged",
    "reality_containment",
    "non_loss_recovery_preserved",
    "hash_chain_valid",
    "no_oracle_or_manual_repair",
    "strict_ability_expansion",
    "invalid_adversarial_candidates_rejected",
]

BRIDGE_INVARIANT_KEYS = [
    "crsi_chain_ok",
    "crsi_chain_schema_valid",
    "core_certificates_preserved",
    "core_non_loss_invariants_preserved",
    "core_hash_chain_valid",
    "task_manifest_hash_logged",
    "external_score_ledger_hash_logged",
    "scorer_artifact_hash_logged_or_declared_absent",
    "no_benchmark_leakage",
    "no_oracle_access",
    "no_manual_repair",
    "successor_ids_match_chain",
    "external_scores_monotone_non_decreasing",
    "external_score_improved_or_policy_allows_nonregression",
]

BASE_CLAIM_BOUNDARY = {
    "certificate_preserving_external_bridge": True,
    "external_score_ledger_attached": True,
    "finite_executable_crsi_witness_required": True,
    "adapter_smoke_test_only": True,
    "official_re_bench_result": False,
    "official_metr_result": False,
    "external_public_benchmark_result": False,
    "full_autonomous_rsi": False,
    "unbounded_horizon_empirical_proof": False,
    "arbitrary_trained_system_entry": False,
    "frontier_scale_validation": False,
}


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def bool_all(mapping: Mapping[str, Any], keys: Sequence[str]) -> bool:
    return all(mapping.get(key) is True for key in keys)


def chain_successor_ids(chain: Mapping[str, Any]) -> List[str]:
    packages = chain.get("packages", [])
    if not isinstance(packages, list):
        return []
    ids: List[str] = []
    for package in packages:
        if isinstance(package, Mapping) and package.get("successor_id") is not None:
            ids.append(str(package["successor_id"]))
    return ids


def core_certificates_preserved(chain: Mapping[str, Any]) -> bool:
    packages = chain.get("packages", [])
    if not isinstance(packages, list) or not packages:
        return False
    for package in packages:
        if not isinstance(package, Mapping):
            return False
        cert = package.get("certificate_bundle", {})
        if not isinstance(cert, Mapping):
            return False
        if cert.get("certificate_preserved") is not True:
            return False
        if cert.get("rclm_checker_passed") is not True or cert.get("rcp_checker_passed") is not True:
            return False
    return True


def core_invariants_preserved(chain: Mapping[str, Any]) -> bool:
    packages = chain.get("packages", [])
    if not isinstance(packages, list) or not packages:
        return False
    for package in packages:
        if not isinstance(package, Mapping):
            return False
        invariants = package.get("protected_invariants", {})
        if not isinstance(invariants, Mapping) or not bool_all(invariants, CORE_PROTECTED_INVARIANT_KEYS):
            return False
    return True


def core_hash_chain_valid(chain: Mapping[str, Any]) -> bool:
    packages = chain.get("packages", [])
    transitions = chain.get("transitions", [])
    if not isinstance(packages, list) or not isinstance(transitions, list):
        return False
    if len(transitions) != max(0, len(packages) - 1):
        return False
    for idx in range(1, len(packages)):
        prev, cur = packages[idx - 1], packages[idx]
        if not isinstance(prev, Mapping) or not isinstance(cur, Mapping):
            return False
        if cur.get("parent_successor_id") != prev.get("successor_id"):
            return False
        if cur.get("parent_manifest_hash") != prev.get("manifest_without_hash_sha256"):
            return False
    for transition in transitions:
        if not isinstance(transition, Mapping):
            return False
        if transition.get("ok") is not True or transition.get("hash_chain_valid") is not True:
            return False
    return True


def normalize_score_entries(score_ledger: Mapping[str, Any]) -> List[Dict[str, Any]]:
    entries = score_ledger.get("scores", score_ledger.get("entries", []))
    if not isinstance(entries, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, Mapping):
            continue
        out.append({
            "package_index": int(item.get("package_index", len(out))),
            "successor_id": str(item.get("successor_id", "")),
            "score": float(item.get("score", 0.0)),
            "raw": dict(item),
        })
    return out


def score_monotonicity(entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    scores = [float(item["score"]) for item in entries]
    if not scores:
        return {"has_scores": False, "monotone_non_decreasing": False, "strictly_improved": False, "baseline_score": None, "final_score": None, "delta": None}
    mono = all(b >= a for a, b in zip(scores, scores[1:]))
    improved = any(b > a for a, b in zip(scores, scores[1:]))
    return {
        "has_scores": True,
        "monotone_non_decreasing": mono,
        "strictly_improved": improved,
        "baseline_score": scores[0],
        "final_score": scores[-1],
        "delta": scores[-1] - scores[0],
        "scores": scores,
    }


def score_ids_match_chain(entries: Sequence[Mapping[str, Any]], successor_ids: Sequence[str]) -> bool:
    if len(entries) != len(successor_ids):
        return False
    return all(str(item.get("successor_id")) == sid for item, sid in zip(entries, successor_ids))


def no_leakage(task_manifest: Mapping[str, Any], score_ledger: Mapping[str, Any]) -> bool:
    blocked_true_flags = [
        "benchmark_answers_in_prompt",
        "hidden_tests_exposed",
        "private_solution_material_used",
        "diagnostic_oracle",
        "manual_repair_inside_chain",
        "human_patch_inside_chain",
    ]
    for obj in [task_manifest, score_ledger]:
        for key in blocked_true_flags:
            if obj.get(key) is True:
                return False
    return True


def make_claim_boundary(*, official_re_bench: bool, official_metr: bool, public_benchmark: bool, adapter_smoke: bool) -> Dict[str, Any]:
    boundary = dict(BASE_CLAIM_BOUNDARY)
    boundary["adapter_smoke_test_only"] = bool(adapter_smoke)
    boundary["official_re_bench_result"] = bool(official_re_bench)
    boundary["official_metr_result"] = bool(official_metr)
    boundary["external_public_benchmark_result"] = bool(public_benchmark)
    return boundary


def validate_task_manifest(task_manifest: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in ["benchmark_id", "benchmark_kind", "task_count", "tasks"]:
        if key not in task_manifest:
            errors.append(f"missing_task_manifest_field:{key}")
    if not isinstance(task_manifest.get("tasks", []), list):
        errors.append("tasks_not_list")
    try:
        if int(task_manifest.get("task_count", -1)) != len(task_manifest.get("tasks", [])):
            errors.append("task_count_mismatch")
    except Exception as exc:
        errors.append(f"invalid_task_count:{exc}")
    return errors


def validate_score_ledger(score_ledger: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in ["benchmark_id", "scores"]:
        if key not in score_ledger:
            errors.append(f"missing_score_ledger_field:{key}")
    entries = normalize_score_entries(score_ledger)
    if not entries:
        errors.append("no_score_entries")
    return errors


def validate_bridge_sidecar(sidecar: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    required = [
        "schema_version", "suite_name", "benchmark_id", "benchmark_kind", "crsi_chain_summary_path",
        "crsi_chain_summary_hash", "task_manifest_path", "task_manifest_hash", "external_score_ledger_path",
        "external_score_ledger_hash", "external_score_summary", "bridge_invariants", "claim_boundary", "ok",
    ]
    for key in required:
        if key not in sidecar:
            errors.append(f"missing_sidecar_field:{key}")
    if sidecar.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    invariants = sidecar.get("bridge_invariants", {})
    if not isinstance(invariants, Mapping):
        errors.append("bridge_invariants_not_object")
    else:
        for key in BRIDGE_INVARIANT_KEYS:
            if key not in invariants:
                errors.append(f"missing_bridge_invariant:{key}")
            elif invariants[key] is not True:
                errors.append(f"bridge_invariant_false:{key}")
    if sidecar.get("ok") is not True:
        errors.append("sidecar_not_ok")
    return errors
