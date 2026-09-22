from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import gcd

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_ENUMERATION_STRIDE,
    PHASE16_ENUMERATOR_ID,
    PHASE16_LEARNED_PREFIX,
    PHASE16_RESOURCE_STEPS,
)
from rcp_rclm_runtime_v4.phase16.ranking import ranked_programs
from rcp_rclm_runtime_v4.phase16.records import FairSearchCertificate, MutationProgram


@dataclass(frozen=True, slots=True)
class SearchResult:
    attempts: Sequence[dict[str, object]]
    certificate: FairSearchCertificate
    accepted_program: MutationProgram | None


def fair_order(programs: Sequence[MutationProgram], offset_hash: str) -> tuple[MutationProgram, ...]:
    ordered = tuple(sorted(programs, key=lambda program: program.program_hash.encode("ascii")))
    count = len(ordered)
    if count == 0:
        raise SchemaValidationError("phase16.scheduler.programs", "legal program set is empty")
    stride = PHASE16_ENUMERATION_STRIDE % count
    while gcd(stride, count) != 1:
        stride += 1
    offset = int(offset_hash[:16], 16) % count
    result = tuple(ordered[(offset + index * stride) % count] for index in range(count))
    if len({program.program_hash for program in result}) != count:
        raise SchemaValidationError("phase16.scheduler.fair_order", "enumeration is not a permutation")
    return result


def search_programs(
    programs: Sequence[MutationProgram],
    *,
    promotion_index: int,
    active_package_hash: str,
    seed: str,
    challenge_stream: str,
    verified_family_counts: Mapping[str, int],
    evaluator: Callable[[MutationProgram], tuple[bool, tuple[str, ...], str]],
) -> SearchResult:
    legal = tuple(programs)
    legal_by_hash = {program.program_hash: program for program in legal}
    if len(legal_by_hash) != len(legal):
        raise SchemaValidationError("phase16.scheduler.programs", "duplicate legal program")
    offset_hash = canonical_json_hash(
        {
            "domain": "phase16.fair_order_offset.v1",
            "active_package_hash": active_package_hash,
            "promotion_index": promotion_index,
            "seed": seed,
            "challenge_stream": challenge_stream,
        }
    )
    fair = fair_order(legal, offset_hash)
    considered: list[str] = []
    attempts: list[dict[str, object]] = []
    rejected_families: list[str] = []
    accepted: MutationProgram | None = None
    learned_steps = 0
    fair_cursor = 0
    limits_used: list[int] = []

    def next_learned() -> MutationProgram | None:
        remaining = tuple(program for program in legal if program.program_hash not in considered)
        if not remaining:
            return None
        ranked = ranked_programs(
            remaining,
            active_package_hash=active_package_hash,
            verified_family_counts=verified_family_counts,
            rejected_families=tuple(rejected_families),
            seed=seed,
            challenge_stream=challenge_stream,
        )
        return ranked[0]

    def next_fair() -> MutationProgram | None:
        nonlocal fair_cursor
        while fair_cursor < len(fair):
            candidate = fair[fair_cursor]
            fair_cursor += 1
            if candidate.program_hash not in considered:
                return candidate
        return None

    for limit in PHASE16_RESOURCE_STEPS:
        limits_used.append(limit)
        while len(considered) < min(limit, len(legal)):
            candidate: MutationProgram | None
            if learned_steps < PHASE16_LEARNED_PREFIX:
                candidate = next_learned()
                learned_steps += 1
            else:
                candidate = next_fair()
            if candidate is None:
                break
            accepted_verdict, reason_codes, evaluation_hash = evaluator(candidate)
            considered.append(candidate.program_hash)
            attempt = {
                "schema_id": "runtime.v4.phase16.search_attempt.v1",
                "attempt_index": len(attempts),
                "program": candidate.to_json(),
                "program_hash": candidate.program_hash,
                "search_mode": "learned_rejection_conditioned" if len(attempts) < PHASE16_LEARNED_PREFIX else "fair_enumeration_fallback",
                "verdict": "accept" if accepted_verdict else "reject",
                "reason_codes": list(reason_codes),
                "evaluation_hash": evaluation_hash,
                "resource_envelope_limit": limit,
                "candidate_self_report_authoritative": False,
            }
            attempt["attempt_hash"] = canonical_json_hash(attempt)
            attempts.append(attempt)
            if accepted_verdict:
                accepted = candidate
                break
            rejected_families.append(candidate.family)
        if accepted is not None or len(considered) == len(legal):
            break

    exhausted = accepted is None
    certificate = FairSearchCertificate(
        promotion_index=promotion_index,
        enumerator_id=PHASE16_ENUMERATOR_ID,
        legal_program_hashes=tuple(program.program_hash for program in legal),
        fair_order_hashes=tuple(program.program_hash for program in fair),
        considered_program_hashes=tuple(considered),
        accepted_program_hash=None if accepted is None else accepted.program_hash,
        accepted_considered_index=None if accepted is None else considered.index(accepted.program_hash),
        exhausted=exhausted,
        resource_envelope_limits=tuple(limits_used),
        learned_prefix_count=min(learned_steps, len(considered)),
        rejection_conditioned_steps=max(0, min(learned_steps, len(considered)) - 1),
    )
    return SearchResult(
        attempts=tuple(attempts),
        certificate=certificate,
        accepted_program=accepted,
    )


__all__ = ["SearchResult", "fair_order", "search_programs"]
