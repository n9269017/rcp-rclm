from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_INHERITED_PLANNER_PROJECTION,
    PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
    PHASE16_RANKING_POLICY_ID,
    UPDATE_FAMILIES,
)
from rcp_rclm_runtime_v4.phase16.records import MutationProgram


def _planner_projection_score(
    program: MutationProgram,
    *,
    active_package_hash: str,
    seed: str,
    challenge_stream: str,
) -> int:
    feature_hash = canonical_json_hash(
        {
            "domain": "phase16.inherited_planner_feature_projection.v1",
            "planner_weights_sha256": PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
            "active_package_hash": active_package_hash,
            "program": program.to_json(),
            "seed": seed,
            "challenge_stream": challenge_stream,
        }
    )
    family_index = UPDATE_FAMILIES.index(program.family)
    total = 0
    for projection_index, (weight_index, weight) in enumerate(
        PHASE16_INHERITED_PLANNER_PROJECTION
    ):
        nibble_offset = (weight_index + projection_index * 11) % len(feature_hash)
        nibble = int(feature_hash[nibble_offset], 16)
        feature = (
            nibble
            + family_index * 3
            + program.variant * 5
            + program.generation
            + projection_index
        ) % 9 - 4
        total += weight * feature
    return total


def ranking_score(
    program: MutationProgram,
    *,
    active_package_hash: str,
    verified_family_counts: Mapping[str, int],
    rejected_families: Sequence[str],
    seed: str,
    challenge_stream: str,
) -> tuple[int, int, str]:
    family_count = verified_family_counts.get(program.family, 0)
    rejection_count = Counter(rejected_families)[program.family]
    novelty_pressure = 20_000 - family_count * 521
    rejection_conditioned_pressure = rejection_count * 797
    inherited_planner_score = _planner_projection_score(
        program,
        active_package_hash=active_package_hash,
        seed=seed,
        challenge_stream=challenge_stream,
    )
    deterministic_tie_break = int(
        canonical_json_hash(
            {
                "policy_id": PHASE16_RANKING_POLICY_ID,
                "program_hash": program.program_hash,
                "active_package_hash": active_package_hash,
                "family_count": family_count,
                "rejection_count": rejection_count,
            }
        )[:16],
        16,
    )
    return (
        novelty_pressure
        + rejection_conditioned_pressure
        + inherited_planner_score,
        deterministic_tie_break,
        program.program_hash,
    )


def ranked_programs(
    programs: Sequence[MutationProgram],
    *,
    active_package_hash: str,
    verified_family_counts: Mapping[str, int],
    rejected_families: Sequence[str],
    seed: str,
    challenge_stream: str,
) -> tuple[MutationProgram, ...]:
    return tuple(
        sorted(
            programs,
            key=lambda program: ranking_score(
                program,
                active_package_hash=active_package_hash,
                verified_family_counts=verified_family_counts,
                rejected_families=rejected_families,
                seed=seed,
                challenge_stream=challenge_stream,
            ),
            reverse=True,
        )
    )


def ranking_manifest(
    programs: Sequence[MutationProgram],
    *,
    active_package_hash: str,
    verified_family_counts: Mapping[str, int],
    rejected_families: Sequence[str],
    seed: str,
    challenge_stream: str,
) -> dict[str, object]:
    ranked = ranked_programs(
        programs,
        active_package_hash=active_package_hash,
        verified_family_counts=verified_family_counts,
        rejected_families=rejected_families,
        seed=seed,
        challenge_stream=challenge_stream,
    )
    payload: dict[str, object] = {
        "schema_id": "runtime.v4.phase16.ranking_manifest.v1",
        "policy_id": PHASE16_RANKING_POLICY_ID,
        "planner_weights_sha256": PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
        "projection_nonzero_count": len(PHASE16_INHERITED_PLANNER_PROJECTION),
        "ranked_program_hashes": [program.program_hash for program in ranked],
    }
    payload["manifest_hash"] = canonical_json_hash(payload)
    return payload


__all__ = ["ranked_programs", "ranking_manifest", "ranking_score"]
