"""Phase 17A present-only search controller; never a promotion authority.

A checkpoint authenticates no external evaluator. Its digest must be retained by
an independent caller. Candidate-pass receipts stop search for subsequent root
verification, not for a self-declared successful trajectory.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from math import gcd
import re
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict

FIXED_VERIFIER = "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e"
SEMANTICS = "gate-c-diagonal-qre-kl-fixed-semantics-v1"
RANKING_POLICY = "phase16-inherited-m9-planner-ranking-novelty-rejection-v1"
FAMILIES = (
    "adapter_policy", "architecture_policy", "memory_policy", "optimizer_policy",
    "planner_policy", "retrieval_policy", "tool_policy", "verification_automation_policy",
)
LEARNED_PREFIX = 4
REJECTION_PRESSURE = 797
ENUMERATION_STRIDE = 17
SCHEMA = "runtime.v5.phase17.control_prefix.v1"


class ControlError(ValueError):
    """Malformed, stale, or unauthorized controller input."""


def _integer(value: object, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ControlError(f"{name}: expected integer >= {minimum}")
    return value


def _hash(value: object, name: str) -> str:
    try:
        return validate_hash256(value, name)
    except (ValueError, TypeError) as exc:
        raise ControlError(f"{name}: invalid digest") from exc


def _keys(value: object, expected: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != expected:
        raise ControlError(f"{name}: exact field set required")
    return value


class Action(str, Enum):
    EVALUATE = "evaluate"
    AWAIT_ROOT_VERIFICATION = "await_root_verification"
    SEARCH_EXHAUSTED = "search_exhausted"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    EXTERNAL_STOP = "external_stop_valid_prefix"
    SAFETY_HALT = "fail_closed_safety_halt"


@dataclass(frozen=True, slots=True)
class CurrentView:
    """Only information available now, not a future schedule or total horizon."""
    predecessor_state_hash: str
    active_package_hash: str
    challenge_commitment_hash: str
    public_nonce_hash: str
    turn_index: int
    family_counts: tuple[int, ...]
    fixed_verifier_hash: str = FIXED_VERIFIER
    semantics_id: str = SEMANTICS

    def __post_init__(self) -> None:
        for name in ("predecessor_state_hash", "active_package_hash",
                     "challenge_commitment_hash", "public_nonce_hash", "fixed_verifier_hash"):
            _hash(getattr(self, name), name)
        _integer(self.turn_index, "turn_index")
        counts = tuple(self.family_counts)
        if len(counts) != len(FAMILIES):
            raise ControlError("exact Phase 16 family counts required")
        for count in counts:
            _integer(count, "family_count")
        object.__setattr__(self, "family_counts", counts)
        if self.fixed_verifier_hash != FIXED_VERIFIER or self.semantics_id != SEMANTICS:
            raise ControlError("fixed verifier or semantics changed")

    def to_json(self) -> dict:
        result = asdict(self)
        result["family_counts"] = list(self.family_counts)
        return result

    @classmethod
    def from_json(cls, value: object) -> CurrentView:
        fields = set(cls.__dataclass_fields__)
        obj = _keys(value, fields, "current_view")
        if type(obj["family_counts"]) is not list:
            raise ControlError("family_counts must be a list")
        return cls(**obj)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Current grammar identity plus inherited Phase 16 rank before rejection."""
    program_hash: str
    family: str
    variant: int
    base_score: int

    def __post_init__(self) -> None:
        _hash(self.program_hash, "program_hash")
        if self.family not in FAMILIES:
            raise ControlError("unknown update family")
        _integer(self.variant, "variant")
        if self.variant >= 4 or type(self.base_score) is not int:
            raise ControlError("invalid Phase 16 variant or rank")


@dataclass(frozen=True, slots=True)
class FrozenSearch:
    view: CurrentView
    candidates: tuple[RankedCandidate, ...]

    def __post_init__(self) -> None:
        if type(self.view) is not CurrentView:
            raise ControlError("current view required")
        candidates = tuple(self.candidates)
        if len(candidates) != 32 or any(type(c) is not RankedCandidate for c in candidates):
            raise ControlError("exact 32-program Phase 16 grammar required")
        if len({c.program_hash for c in candidates}) != 32:
            raise ControlError("duplicate candidate")
        if {(c.family, c.variant) for c in candidates} != {
            (family, variant) for family in FAMILIES for variant in range(4)
        }:
            raise ControlError("incomplete Phase 16 family/variant coverage")
        object.__setattr__(self, "candidates", tuple(sorted(candidates, key=lambda c: c.program_hash)))

    def to_json(self) -> dict:
        return {"view": self.view.to_json(), "candidates": [asdict(c) for c in self.candidates]}

    @property
    def freeze_hash(self) -> str:
        return canonical_json_hash({"schema": "runtime.v5.phase17.freeze.v1", **self.to_json()})

    @classmethod
    def from_json(cls, value: object) -> FrozenSearch:
        obj = _keys(value, {"view", "candidates"}, "frozen_search")
        if type(obj["candidates"]) is not list:
            raise ControlError("candidates must be a list")
        candidates = tuple(RankedCandidate(**_keys(c, set(RankedCandidate.__dataclass_fields__),
                                                  "candidate")) for c in obj["candidates"])
        return cls(CurrentView.from_json(obj["view"]), candidates)


@dataclass(frozen=True, slots=True)
class Observation:
    program_hash: str
    verdict: str
    evaluation_hash: str
    reason_codes: tuple[str, ...]
    decision_hash: str

    def __post_init__(self) -> None:
        for name in ("program_hash", "evaluation_hash", "decision_hash"):
            _hash(getattr(self, name), name)
        if self.verdict not in ("reject", "candidate_passed"):
            raise ControlError("only evaluator outcomes, never a promotion, are admissible")
        codes = tuple(self.reason_codes)
        if len(codes) > 16 or any(type(code) is not str or
                re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", code) is None for code in codes):
            raise ControlError("invalid reason code")
        if len(set(codes)) != len(codes) or (self.verdict == "reject" and not codes):
            raise ControlError("rejection requires unique reason codes")
        object.__setattr__(self, "reason_codes", codes)

    def to_json(self) -> dict:
        result = asdict(self)
        result["reason_codes"] = list(self.reason_codes)
        return result


@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    prefix_hash: str
    candidate_hash: str | None

    @property
    def decision_hash(self) -> str:
        return canonical_json_hash({"schema": "runtime.v5.phase17.decision.v1",
                                    "action": self.action.value, "prefix_hash": self.prefix_hash,
                                    "candidate_hash": self.candidate_hash})


@dataclass(frozen=True, slots=True)
class SearchPrefix:
    frozen: FrozenSearch
    initial_credits: int
    observations: tuple[Observation, ...] = ()
    stop: str | None = None
    schema_id: ClassVar[str] = SCHEMA

    def __post_init__(self) -> None:
        if type(self.frozen) is not FrozenSearch:
            raise ControlError("frozen search required")
        _integer(self.initial_credits, "initial_credits")
        observations = tuple(self.observations)
        if len(observations) > min(32, self.initial_credits):
            raise ControlError("search prefix exceeds grammar or resource envelope")
        if any(type(o) is not Observation for o in observations):
            raise ControlError("invalid observation")
        if self.stop not in (None, Action.EXTERNAL_STOP.value, Action.SAFETY_HALT.value):
            raise ControlError("invalid external stop")
        if self.stop is not None and (len(observations) == 32 or
                len(observations) == self.initial_credits or
                any(o.verdict == "candidate_passed" for o in observations)):
            raise ControlError("external stop may not overwrite an already terminal cause")
        object.__setattr__(self, "observations", observations)
        # Every prefix is revalidated by replay. A forged dataclass is not trusted.
        seen: list[Observation] = []
        for observation in observations:
            if any(o.verdict == "candidate_passed" for o in seen):
                raise ControlError("search continued after candidate pass")
            expected = _candidate(self.frozen, tuple(seen))
            if expected.program_hash != observation.program_hash:
                raise ControlError("candidate differs from deterministic present-only decision")
            before = _prefix_hash(self.frozen, self.initial_credits, tuple(seen), None)
            decision = Decision(Action.EVALUATE, before, expected.program_hash)
            if observation.decision_hash != decision.decision_hash:
                raise ControlError("stale or substituted decision")
            seen.append(observation)

    @property
    def credits_remaining(self) -> int:
        return self.initial_credits - len(self.observations)

    @property
    def prefix_hash(self) -> str:
        return _prefix_hash(self.frozen, self.initial_credits, self.observations, self.stop)

    def to_json(self) -> dict:
        return {"schema_id": SCHEMA, "frozen": self.frozen.to_json(),
                "initial_credits": self.initial_credits,
                "observations": [o.to_json() for o in self.observations], "stop": self.stop}


def _prefix_hash(frozen: FrozenSearch, credits: int,
                 observations: tuple[Observation, ...], stop: str | None) -> str:
    return canonical_json_hash({"schema_id": SCHEMA, "frozen": frozen.to_json(),
                                "initial_credits": credits,
                                "observations": [o.to_json() for o in observations], "stop": stop})


def _candidate(frozen: FrozenSearch, observations: tuple[Observation, ...]) -> RankedCandidate:
    seen = {o.program_hash for o in observations}
    remaining = tuple(c for c in frozen.candidates if c.program_hash not in seen)
    if not remaining:
        raise ControlError("grammar exhausted")
    if len(observations) < LEARNED_PREFIX:
        by_hash = {c.program_hash: c for c in frozen.candidates}
        rejected = Counter(by_hash[o.program_hash].family for o in observations)
        counts = dict(zip(FAMILIES, frozen.view.family_counts, strict=True))
        def score(c: RankedCandidate) -> tuple[int, int, str]:
            tie = int(canonical_json_hash({"policy_id": RANKING_POLICY,
                "program_hash": c.program_hash, "active_package_hash": frozen.view.active_package_hash,
                "family_count": counts[c.family], "rejection_count": rejected[c.family]})[:16], 16)
            return c.base_score + rejected[c.family] * REJECTION_PRESSURE, tie, c.program_hash
        return max(remaining, key=score)
    # Complete coprime-stride fallback over the frozen grammar, not a future route.
    count = len(frozen.candidates)
    stride = ENUMERATION_STRIDE % count
    if gcd(stride, count) != 1:
        raise ControlError("invalid fixed enumeration stride")
    offset = int(frozen.freeze_hash[:16], 16) % count
    for index in range(count):
        candidate = frozen.candidates[(offset + index * stride) % count]
        if candidate.program_hash not in seen:
            return candidate
    raise ControlError("inconsistent finite enumeration")


def decide(prefix: SearchPrefix) -> Decision:
    """No future horizon, future challenge seed, terminal hash, or success count."""
    if type(prefix) is not SearchPrefix:
        raise ControlError("validated prefix required")
    if prefix.stop is not None:
        return Decision(Action(prefix.stop), prefix.prefix_hash, None)
    if prefix.observations and prefix.observations[-1].verdict == "candidate_passed":
        return Decision(Action.AWAIT_ROOT_VERIFICATION, prefix.prefix_hash, None)
    if len(prefix.observations) == len(prefix.frozen.candidates):
        return Decision(Action.SEARCH_EXHAUSTED, prefix.prefix_hash, None)
    if prefix.credits_remaining == 0:
        return Decision(Action.RESOURCE_EXHAUSTED, prefix.prefix_hash, None)
    return Decision(Action.EVALUATE, prefix.prefix_hash,
                    _candidate(prefix.frozen, prefix.observations).program_hash)


def record_evaluation(prefix: SearchPrefix, decision: Decision, *, verdict: str,
                      evaluation_hash: str, reason_codes: Sequence[str],
                      predecessor_state_hash: str, challenge_commitment_hash: str) -> SearchPrefix:
    """Bind an evaluator receipt. This never changes an active package."""
    expected = decide(prefix)
    if decision != expected or expected.action != Action.EVALUATE:
        raise ControlError("stale, duplicate, or non-evaluation decision")
    view = prefix.frozen.view
    if (predecessor_state_hash != view.predecessor_state_hash or
            challenge_commitment_hash != view.challenge_commitment_hash):
        raise ControlError("receipt predecessor or hidden commitment mismatch")
    if isinstance(reason_codes, (str, bytes)):
        raise ControlError("reason codes must be a sequence, not text")
    observation = Observation(expected.candidate_hash, verdict, evaluation_hash,
                              tuple(reason_codes), decision.decision_hash)
    return SearchPrefix(prefix.frozen, prefix.initial_credits, (*prefix.observations, observation))


def halt(prefix: SearchPrefix, *, safety: bool = False) -> SearchPrefix:
    if type(safety) is not bool:
        raise ControlError("safety must be Boolean")
    if decide(prefix).action != Action.EVALUATE:
        raise ControlError("already stopped; terminal cause may not be rewritten")
    return SearchPrefix(prefix.frozen, prefix.initial_credits, prefix.observations,
                        Action.SAFETY_HALT.value if safety else Action.EXTERNAL_STOP.value)


def exhaustion_record(prefix: SearchPrefix) -> dict:
    """Bounded enumeration evidence, not a theorem of evaluator truth."""
    if decide(prefix).action != Action.SEARCH_EXHAUSTED:
        raise ControlError("partial search is not search exhaustion")
    return {"schema_id": "runtime.v5.phase17.bounded_exhaustion.v1",
            "prefix_hash": prefix.prefix_hash, "freeze_hash": prefix.frozen.freeze_hash,
            "legal_program_hashes": [c.program_hash for c in prefix.frozen.candidates],
            "rejected_program_hashes": [o.program_hash for o in prefix.observations],
            "evaluation_hashes": [o.evaluation_hash for o in prefix.observations],
            "scope": "exact_frozen_32_program_grammar",
            "requires_independent_evaluation_verification": True,
            "phase17_exit_closed": False, "gate_e_closed": False}


def checkpoint(prefix: SearchPrefix) -> bytes:
    return canonical_json_bytes(prefix.to_json())


def restore(data: bytes, *, expected_prefix_hash: str) -> SearchPrefix:
    """Replay every decision, and require an externally retained checkpoint hash."""
    _hash(expected_prefix_hash, "expected_prefix_hash")
    if type(data) is not bytes or len(data) > 262144:
        raise ControlError("checkpoint must be bounded bytes")
    obj = _keys(load_json_strict(data),
                {"schema_id", "frozen", "initial_credits", "observations", "stop"}, "checkpoint")
    if obj["schema_id"] != SCHEMA or type(obj["observations"]) is not list:
        raise ControlError("checkpoint schema mismatch")
    if len(obj["observations"]) > 32:
        raise ControlError("checkpoint history exceeds fixed grammar")
    observations = []
    for value in obj["observations"]:
        value = _keys(value, set(Observation.__dataclass_fields__), "observation")
        if type(value["reason_codes"]) is not list:
            raise ControlError("reason_codes must be a list")
        observations.append(Observation(**value))
    prefix = SearchPrefix(FrozenSearch.from_json(obj["frozen"]), obj["initial_credits"],
                          tuple(observations), obj["stop"])
    if prefix.prefix_hash != expected_prefix_hash:
        raise ControlError("checkpoint differs from externally retained identity")
    return prefix
