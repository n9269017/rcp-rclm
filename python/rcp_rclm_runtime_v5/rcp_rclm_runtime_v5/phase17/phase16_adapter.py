"""Build a Phase 17 control view from the unchanged Phase 16 grammar and ranker.

This bridge does not run hidden evaluation, certify a predecessor, or promote a
successor. A caller must independently verify the starting Phase 16 package.
No evaluation seed or future challenge stream enters the controller interface.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime_v5.phase17.controller import (
    ControlError, CurrentView, ENUMERATION_STRIDE, FAMILIES, FIXED_VERIFIER,
    FrozenSearch, LEARNED_PREFIX, RANKING_POLICY, RankedCandidate, SEMANTICS,
    SearchPrefix,
)

if TYPE_CHECKING:
    from rcp_rclm_runtime_v4.phase16.records import ModelState, MutationProgram


@dataclass(frozen=True, slots=True)
class Phase16SearchBinding:
    prefix: SearchPrefix
    programs: Mapping[str, MutationProgram]
    public_ranking_seed: str


def bind_phase16_search(state: ModelState, *, turn_index: int,
                        challenge_commitment_hash: str, public_nonce_hash: str,
                        candidate_credits: int) -> Phase16SearchBinding:
    from rcp_rclm_runtime_v4.phase16 import constants as c
    from rcp_rclm_runtime_v4.phase16.grammar import legal_mutation_programs
    from rcp_rclm_runtime_v4.phase16.ranking import ranking_score
    from rcp_rclm_runtime_v4.phase16.records import ModelState

    if type(state) is not ModelState:
        raise ControlError("exact Phase 16 ModelState required")
    if (tuple(c.UPDATE_FAMILIES) != FAMILIES or c.PHASE16_VARIANTS_PER_FAMILY != 4 or
            c.PHASE16_FIXED_VERIFIER_HASH != FIXED_VERIFIER or
            c.PHASE16_DIAGONAL_SEMANTICS_ID != SEMANTICS or
            c.PHASE16_RANKING_POLICY_ID != RANKING_POLICY or
            c.PHASE16_LEARNED_PREFIX != LEARNED_PREFIX or
            c.PHASE16_ENUMERATION_STRIDE != ENUMERATION_STRIDE):
        raise ControlError("Phase 16 grammar, ranker, or fixed trust boundary changed")
    # ModelState contains a mutable mapping despite being a frozen dataclass.
    # Copy and validate it before deriving identities or candidate programs.
    frozen_state = ModelState(
        model_index=state.model_index, active_package_hash=state.active_package_hash,
        component_generations=dict(state.component_generations),
        installed_program_hashes=tuple(state.installed_program_hashes),
        capability_frontier=tuple(state.capability_frontier),
        recursive_productivity_frontier=tuple(state.recursive_productivity_frontier),
        archive_root_hash=state.archive_root_hash,
        fixed_verifier_hash=state.fixed_verifier_hash, semantics_id=state.semantics_id,
    )
    counts = tuple(frozen_state.component_generations[f] for f in FAMILIES)
    view = CurrentView(frozen_state.state_record_hash, frozen_state.active_package_hash,
                       challenge_commitment_hash, public_nonce_hash, turn_index, counts)
    seed = canonical_json_hash({"domain": "phase17.present_only_ranking_seed.v1",
                                "view": view.to_json()})
    programs = legal_mutation_programs(frozen_state, promotion_index=turn_index,
                                      public_nonce_hash=public_nonce_hash)
    scores = tuple(RankedCandidate(
        p.program_hash, p.family, p.variant,
        ranking_score(p, active_package_hash=view.active_package_hash,
                      verified_family_counts=dict(zip(FAMILIES, counts, strict=True)),
                      rejected_families=(), seed=seed,
                      challenge_stream="phase17-present-only-v1")[0],
    ) for p in programs)
    prefix = SearchPrefix(FrozenSearch(view, scores), candidate_credits)
    return Phase16SearchBinding(prefix, MappingProxyType({p.program_hash: p for p in programs}), seed)
