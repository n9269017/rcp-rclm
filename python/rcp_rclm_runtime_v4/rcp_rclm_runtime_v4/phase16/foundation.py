from __future__ import annotations

from collections.abc import Mapping, Sequence

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_DEFAULT_SEEDS,
    PHASE16_DEFAULT_STREAMS,
    PHASE16_FOUNDATION_SCHEMA_ID,
)


def build_phase16_foundation(
    campaigns: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    selected = tuple(
        campaign for campaign in campaigns if campaign.get("target_promotions") == 8
    )
    expected_pairs = {
        (seed, stream)
        for seed in PHASE16_DEFAULT_SEEDS
        for stream in PHASE16_DEFAULT_STREAMS
    }
    observed_pairs = {
        (str(campaign.get("seed")), str(campaign.get("challenge_stream")))
        for campaign in selected
    }
    campaign_hashes = sorted(
        str(campaign.get("report_hash")) for campaign in selected
    )
    accepted = (
        len(selected) == 4
        and observed_pairs == expected_pairs
        and all(campaign.get("accepted") is True for campaign in selected)
        and all(
            int(campaign.get("accepted_promotions", 0)) == 8
            for campaign in selected
        )
        and all(
            int(campaign.get("substantive_update_family_count", 0)) >= 8
            for campaign in selected
        )
        and all(
            int(campaign.get("rejection_recovery_cycles", 0)) >= 2
            for campaign in selected
        )
        and all(
            int(campaign.get("strict_recursive_productivity_expansions", 0))
            >= 8
            for campaign in selected
        )
        and all(campaign.get("frontier_retained") is True for campaign in selected)
        and all(
            campaign.get("recursive_productivity_frontier_retained") is True
            for campaign in selected
        )
        and all(campaign.get("manual_repairs") == 0 for campaign in selected)
    )
    content: dict[str, object] = {
        "schema_id": PHASE16_FOUNDATION_SCHEMA_ID,
        "campaign_hashes": campaign_hashes,
        "campaign_count": len(selected),
        "seeds": list(PHASE16_DEFAULT_SEEDS),
        "challenge_streams": list(PHASE16_DEFAULT_STREAMS),
        "accepted_promotions_per_campaign": 8,
        "multi_seed": True,
        "multi_challenge_stream": True,
        "eight_update_families_demonstrated": all(
            int(campaign.get("substantive_update_family_count", 0)) >= 8
            for campaign in selected
        ),
        "zero_manual_repair": all(
            campaign.get("manual_repairs") == 0 for campaign in selected
        ),
        "accepted": accepted,
        "phase16_foundation_closed": accepted,
        "phase16_exit_closed": False,
        "gate_e_closed": False,
        "next_phase": 16,
    }
    report = dict(content)
    report["report_hash"] = canonical_json_hash(content)
    if not accepted:
        raise SchemaValidationError(
            "phase16.foundation",
            "eight-promotion foundation predicates failed",
        )
    return report


__all__ = ["build_phase16_foundation"]
