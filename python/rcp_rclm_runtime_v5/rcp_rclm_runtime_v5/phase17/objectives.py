"""Present-only objective selection for the reopened historical predecessor.

This is a declared package-conditioned policy, not a learned policy-succession
claim. The 84 nonzero parameters are read from the authenticated inherited
planner tensor. No future challenge, evaluator seed, successful route, target
promotion count or EGC score is an input. Selection chooses an objective family,
not a winning mutation; the Phase 16 grammar remains unchanged and exhaustive.
"""
from __future__ import annotations

from dataclasses import dataclass

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v5.phase17.bootstrap import (
    HistoricalPredecessor, SELECTED_STATE_HASH, WEIGHTS_SHA256,
)
from rcp_rclm_runtime_v5.phase17.controller import (
    ControlError, FAMILIES, FIXED_VERIFIER, SEMANTICS, _hash, _integer, _keys,
)

OBJECTIVE_POLICY = "phase17.inherited-projection-current-objective.v1"
OBJECTIVE_SCHEMA = "runtime.v5.phase17.objective_decision.v1"
FREEZE_SCHEMA = "runtime.v5.phase17.objective_freeze.v1"


def _rank(predecessor: HistoricalPredecessor, turn_index: int, public_nonce_hash: str) -> list[dict]:
    state = predecessor.state
    candidates = []
    for family_index, family in enumerate(FAMILIES):
        generation = state["component_generations"][family]
        feature_hash = canonical_json_hash({
            "domain": OBJECTIVE_POLICY,
            "active_package_hash": state["active_package_hash"],
            "predecessor_state_hash": SELECTED_STATE_HASH,
            "planner_weights_sha256": WEIGHTS_SHA256,
            "turn_index": turn_index, "public_nonce_hash": public_nonce_hash,
            "objective_family": family,
            "capability_frontier": state["capability_frontier"],
            "recursive_productivity_frontier": state["recursive_productivity_frontier"],
        })
        score = 0
        for projection_index, (weight_index, weight) in enumerate(predecessor.planner_projection):
            offset = (weight_index + projection_index * 11) % len(feature_hash)
            feature = (int(feature_hash[offset], 16) + family_index * 3
                       + generation + projection_index) % 9 - 4
            score += weight * feature
        candidates.append({"family": family, "generation": generation,
                           "inherited_projection_score": score,
                           "score": 20_000 - generation * 521 + score,
                           "tie_break": canonical_json_hash({
                               "policy_id": OBJECTIVE_POLICY, "feature_hash": feature_hash,
                               "family": family})})
    return sorted(candidates, key=lambda x: (x["score"], x["tie_break"], x["family"]), reverse=True)


@dataclass(frozen=True, slots=True)
class ObjectiveDecision:
    """An untrusted serializable decision, verified by recomputing the policy."""
    payload: bytes

    def __post_init__(self) -> None:
        if type(self.payload) is not bytes:
            raise ControlError("objective decision requires immutable bytes")
        obj = load_json_strict(self.payload)
        _keys(obj, {"schema_id", "policy_id", "bootstrap_report_hash", "predecessor_state_hash",
                   "active_package_hash", "planner_weights_sha256", "turn_index", "public_nonce_hash",
                   "ranked_objectives", "objective_family", "goal", "fixed_verifier_hash",
                   "semantics_id", "promotion_authorized"}, "objective")
        if (obj["schema_id"] != OBJECTIVE_SCHEMA or obj["policy_id"] != OBJECTIVE_POLICY
                or obj["fixed_verifier_hash"] != FIXED_VERIFIER or obj["semantics_id"] != SEMANTICS
                or obj["promotion_authorized"] is not False):
            raise ControlError("objective schema/trust boundary mismatch")
        _integer(obj["turn_index"], "turn_index")
        for field in ("bootstrap_report_hash", "predecessor_state_hash", "active_package_hash",
                      "planner_weights_sha256", "public_nonce_hash"):
            _hash(obj[field], field)
        ranks = obj["ranked_objectives"]
        if type(ranks) is not list or len(ranks) != 8:
            raise ControlError("all eight objective families required")
        for rank in ranks:
            _keys(rank, {"family", "generation", "inherited_projection_score", "score", "tie_break"}, "rank")
            _integer(rank["generation"], "generation")
            if type(rank["inherited_projection_score"]) is not int or type(rank["score"]) is not int:
                raise ControlError("integer scores required")
            _hash(rank["tie_break"], "tie_break")
        if {r["family"] for r in ranks} != set(FAMILIES) or obj["objective_family"] != ranks[0]["family"]:
            raise ControlError("objective coverage or winner mismatch")
        if obj["goal"] != "extend_verified_capability_frontier":
            raise ControlError("unsupported objective")

    def to_json(self) -> dict:
        return load_json_strict(self.payload)

    @property
    def decision_hash(self) -> str:
        return canonical_json_hash(self.to_json())


def select_bootstrap_objective(predecessor: HistoricalPredecessor, *, turn_index: int,
                               public_nonce_hash: str) -> ObjectiveDecision:
    if type(predecessor) is not HistoricalPredecessor:
        raise ControlError("reopened historical predecessor required, not an unverified fixture")
    predecessor.validate()
    _integer(turn_index, "turn_index")
    _hash(public_nonce_hash, "public_nonce_hash")
    ranks = _rank(predecessor, turn_index, public_nonce_hash)
    return ObjectiveDecision(canonical_json_bytes({
        "schema_id": OBJECTIVE_SCHEMA, "policy_id": OBJECTIVE_POLICY,
        "bootstrap_report_hash": predecessor.receipt["report_hash"],
        "predecessor_state_hash": SELECTED_STATE_HASH,
        "active_package_hash": predecessor.state["active_package_hash"],
        "planner_weights_sha256": WEIGHTS_SHA256,
        "turn_index": turn_index, "public_nonce_hash": public_nonce_hash,
        "ranked_objectives": ranks, "objective_family": ranks[0]["family"],
        "goal": "extend_verified_capability_frontier",
        "fixed_verifier_hash": FIXED_VERIFIER, "semantics_id": SEMANTICS,
        "promotion_authorized": False,
    }))


def verify_bootstrap_objective(decision: ObjectiveDecision, predecessor: HistoricalPredecessor,
                               *, turn_index: int, public_nonce_hash: str) -> None:
    expected = select_bootstrap_objective(predecessor, turn_index=turn_index,
                                         public_nonce_hash=public_nonce_hash)
    if type(decision) is not ObjectiveDecision or decision.payload != expected.payload:
        raise ControlError("objective differs from independently recomputed present-only policy")


def freeze_bootstrap_objective(decision: ObjectiveDecision, predecessor: HistoricalPredecessor,
                               *, turn_index: int, public_nonce_hash: str) -> dict:
    """Bind the selected objective before asking a separate evaluator for a challenge.

    The receipt is deterministic data, not evidence of wall-clock ordering,
    evaluator independence, candidate freeze, or successful challenge solving.
    """
    verify_bootstrap_objective(decision, predecessor, turn_index=turn_index,
                               public_nonce_hash=public_nonce_hash)
    payload = {"schema_id": FREEZE_SCHEMA, "objective_decision_hash": decision.decision_hash,
               "predecessor_state_hash": SELECTED_STATE_HASH,
               "active_package_hash": predecessor.state["active_package_hash"],
               "turn_index": turn_index, "public_nonce_hash": public_nonce_hash,
               "fixed_verifier_hash": FIXED_VERIFIER, "semantics_id": SEMANTICS,
               "challenge_bound": False, "promotion_authorized": False}
    payload["freeze_hash"] = canonical_json_hash(payload)
    return payload
