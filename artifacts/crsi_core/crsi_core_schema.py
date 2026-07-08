#!/usr/bin/env python3
"""Schema and scoring utilities for the RCLM-CRSI-Core artifact.

The CRSI core test treats each RCLM_t as a versioned successor package.  A
package is accepted only when its predecessor verifier or the immutable root
verifier accepts the package, the existing RCP/RCLM executable certificates are
preserved, protected non-loss invariants hold, and the internal CoreScore
improves lexicographically across successor transitions.

This module is intentionally standard-library only so it can be used by the
main harness and the offline reproduction checker.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

SUITE_NAME = "RCLM-CRSI-Core: Certified Recursive Successor Improvement Core Test"
SCHEMA_VERSION = "crsi-core-v1"
DEFAULT_MODE = "rclm"

INVALID_CANDIDATE_KINDS = [
    "wrong_dimension_append",
    "noop_no_ability_expansion",
    "residual_positive",
    "recovery_breaking",
    "bad_goal_transport",
    "bad_trust_anchor",
    "bad_cost_bound",
    "bad_reality_containment",
]

PROTECTED_INVARIANT_KEYS = [
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

CLAIM_BOUNDARY = {
    "finite_executable_crsi_witness": True,
    "internal_core_score_improvement": True,
    "external_public_benchmark": False,
    "official_evalplus_cli_result": False,
    "evalplus_leaderboard_result": False,
    "swe_bench_result": False,
    "re_bench_result": False,
    "mle_bench_result": False,
    "arbitrary_trained_system_entry": False,
    "frontier_scale_validation": False,
    "full_autonomous_rsi": False,
    "unbounded_horizon_empirical_proof": False,
}


def canonical_json(obj: Any) -> bytes:
    """Return deterministic JSON bytes for hashing."""
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


def bool_count(mapping: Mapping[str, Any], keys: Sequence[str]) -> int:
    return sum(1 for key in keys if mapping.get(key) is True)


def rejection_kinds(rejected: Sequence[Mapping[str, Any]]) -> List[str]:
    return sorted({str(item.get("kind")) for item in rejected if item.get("kind") is not None})


def rejection_coverage_count(rejected: Sequence[Mapping[str, Any]]) -> int:
    present = set(rejection_kinds(rejected))
    return sum(1 for kind in INVALID_CANDIDATE_KINDS if kind in present)


def ability_count_from_artifact(artifact: Mapping[str, Any]) -> int:
    abilities = artifact.get("abilities")
    if isinstance(abilities, list) and abilities:
        last = abilities[-1]
        if isinstance(last, list):
            return len(last)
    return 0


def final_dimension_from_runlog(runlog: Mapping[str, Any], artifact: Mapping[str, Any]) -> int:
    if "final_dimension" in runlog:
        try:
            return int(runlog.get("final_dimension", 0))
        except (TypeError, ValueError):
            return 0
    states = artifact.get("states", {})
    if isinstance(states, Mapping):
        rho = states.get("rho")
        if isinstance(rho, list) and rho:
            try:
                return len(rho[-1])
            except TypeError:
                return 0
    return 0


def cost_units(runlog: Mapping[str, Any], artifact: Mapping[str, Any]) -> int:
    """Return a deterministic normalized cost proxy.

    The existing controlled artifacts expose dense and diagonal table bounds.
    For the CoreScore we prefer the diagonal bound because the canonical witness
    is diagonal/classical; when unavailable, fall back to N * final_dimension.
    """
    tractability = artifact.get("tractability", {}) if isinstance(artifact.get("tractability"), Mapping) else {}
    if "diagonal_table_cost_bound" in tractability:
        try:
            return int(tractability["diagonal_table_cost_bound"])
        except (TypeError, ValueError):
            pass
    try:
        return int(runlog.get("N", 0)) * int(runlog.get("final_dimension", 0))
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class CoreScore:
    """Lexicographic internal improvement functional.

    A successor improves a predecessor iff this tuple compares greater than the
    predecessor's tuple.  The final term is negative normalized cost, so lower
    cost is better only after all preceding capability/certificate terms tie.
    """

    certified_ability_count: int
    verified_horizon_capacity: int
    verifier_obligation_coverage: int
    adversarial_rejection_coverage: int
    generator_self_hosting_depth: int
    reproducibility_score: int
    negative_normalized_cost: int

    def as_tuple(self) -> Tuple[int, int, int, int, int, int, int]:
        return (
            self.certified_ability_count,
            self.verified_horizon_capacity,
            self.verifier_obligation_coverage,
            self.adversarial_rejection_coverage,
            self.generator_self_hosting_depth,
            self.reproducibility_score,
            self.negative_normalized_cost,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certified_ability_count": self.certified_ability_count,
            "verified_horizon_capacity": self.verified_horizon_capacity,
            "verifier_obligation_coverage": self.verifier_obligation_coverage,
            "adversarial_rejection_coverage": self.adversarial_rejection_coverage,
            "generator_self_hosting_depth": self.generator_self_hosting_depth,
            "reproducibility_score": self.reproducibility_score,
            "negative_normalized_cost": self.negative_normalized_cost,
            "lexicographic_tuple": list(self.as_tuple()),
        }

    @classmethod
    def from_dict(cls, obj: Mapping[str, Any]) -> "CoreScore":
        return cls(
            certified_ability_count=int(obj["certified_ability_count"]),
            verified_horizon_capacity=int(obj["verified_horizon_capacity"]),
            verifier_obligation_coverage=int(obj["verifier_obligation_coverage"]),
            adversarial_rejection_coverage=int(obj["adversarial_rejection_coverage"]),
            generator_self_hosting_depth=int(obj["generator_self_hosting_depth"]),
            reproducibility_score=int(obj["reproducibility_score"]),
            negative_normalized_cost=int(obj["negative_normalized_cost"]),
        )


def score_improved(predecessor: Mapping[str, Any], successor: Mapping[str, Any]) -> bool:
    return CoreScore.from_dict(successor).as_tuple() > CoreScore.from_dict(predecessor).as_tuple()


def compute_core_score(
    *,
    package_index: int,
    N: int,
    artifact: Mapping[str, Any],
    runlog: Mapping[str, Any],
    rejected: Sequence[Mapping[str, Any]],
    protected_invariants: Mapping[str, Any],
    reproducibility_score: int,
) -> CoreScore:
    ability_count = ability_count_from_artifact(artifact)
    coverage = bool_count(protected_invariants, PROTECTED_INVARIANT_KEYS)
    rejections = rejection_coverage_count(rejected)
    cost = cost_units(runlog, artifact)
    return CoreScore(
        certified_ability_count=ability_count,
        verified_horizon_capacity=int(N),
        verifier_obligation_coverage=coverage,
        adversarial_rejection_coverage=rejections,
        generator_self_hosting_depth=int(package_index),
        reproducibility_score=int(reproducibility_score),
        negative_normalized_cost=-int(cost),
    )


def validate_manifest(manifest: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    required = [
        "schema_version",
        "successor_id",
        "package_index",
        "mode",
        "N",
        "seed",
        "parent_successor_id",
        "source_commit_or_tree_hash",
        "generator_hash",
        "checker_hash",
        "schema_hash",
        "certificate_bundle_hash",
        "accepted_trajectory_hash",
        "rejected_candidates_hash",
        "ability_ledger_hash",
        "score_ledger_hash",
        "claim_boundary_hash",
        "protected_invariants",
        "core_score",
        "artifact_paths",
        "artifact_hashes",
    ]
    for key in required:
        if key not in manifest:
            errors.append(f"missing_manifest_field:{key}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    invariants = manifest.get("protected_invariants", {})
    if isinstance(invariants, Mapping):
        for key in PROTECTED_INVARIANT_KEYS:
            if key not in invariants:
                errors.append(f"missing_protected_invariant:{key}")
    else:
        errors.append("protected_invariants_not_object")
    try:
        CoreScore.from_dict(manifest.get("core_score", {}))
    except Exception as exc:  # noqa: BLE001 - schema diagnostic
        errors.append(f"invalid_core_score:{exc}")
    return errors


def validate_transition(transition: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    required = [
        "schema_version",
        "transition_id",
        "predecessor_successor_id",
        "successor_successor_id",
        "predecessor_core_score",
        "successor_core_score",
        "core_score_improved",
        "protected_invariants_preserved",
        "predecessor_checker_accepts_successor",
        "hash_chain_valid",
        "no_oracle_or_manual_repair",
        "ok",
    ]
    for key in required:
        if key not in transition:
            errors.append(f"missing_transition_field:{key}")
    if transition.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if transition.get("core_score_improved") is not True:
        errors.append("core_score_not_improved")
    if transition.get("protected_invariants_preserved") is not True:
        errors.append("protected_invariants_not_preserved")
    if transition.get("predecessor_checker_accepts_successor") is not True:
        errors.append("predecessor_checker_rejected_successor")
    if transition.get("hash_chain_valid") is not True:
        errors.append("hash_chain_invalid")
    if transition.get("no_oracle_or_manual_repair") is not True:
        errors.append("manual_or_oracle_intervention_flagged")
    return errors


def validate_chain_summary(summary: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if summary.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    packages = summary.get("packages", [])
    transitions = summary.get("transitions", [])
    if not isinstance(packages, list) or len(packages) < 2:
        errors.append("chain_requires_at_least_two_packages")
        return errors
    if not isinstance(transitions, list) or len(transitions) != len(packages) - 1:
        errors.append("transition_count_mismatch")
    for i, manifest in enumerate(packages):
        for err in validate_manifest(manifest):
            errors.append(f"package_{i}:{err}")
    for i in range(1, len(packages)):
        prev = packages[i - 1]["core_score"]
        succ = packages[i]["core_score"]
        if not score_improved(prev, succ):
            errors.append(f"package_{i}:core_score_not_strictly_improved")
    for i, transition in enumerate(transitions):
        for err in validate_transition(transition):
            errors.append(f"transition_{i}:{err}")
    k = int(summary.get("successor_cycles", 0))
    minimum_k = int(summary.get("minimum_successor_cycles_required", 3))
    if k < minimum_k:
        errors.append(f"insufficient_successor_cycles:{k}<{minimum_k}")
    pass_fail = summary.get("pass_fail", {})
    if isinstance(pass_fail, Mapping):
        for key, value in pass_fail.items():
            if value is not True:
                errors.append(f"pass_fail_false:{key}")
    else:
        errors.append("pass_fail_not_object")
    return errors
