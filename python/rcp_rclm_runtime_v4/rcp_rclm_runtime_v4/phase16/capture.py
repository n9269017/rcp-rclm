from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.bootstrap import Phase16BootstrapReport
from rcp_rclm_runtime_v4.phase16.campaign import (
    run_phase16_campaign,
    validate_phase16_campaign,
)
from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_CAPTURE_SCHEMA_ID,
    PHASE16_DEFAULT_SEEDS,
    PHASE16_DEFAULT_STREAMS,
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_FIXED_VERIFIER_HASH,
    PHASE16_SCALING_LADDER,
    PHASE16_STRETCH_TARGET,
    UPDATE_FAMILIES,
)
from rcp_rclm_runtime_v4.phase16.foundation import build_phase16_foundation


def _capture_content(
    *,
    bootstrap: Phase16BootstrapReport,
    source_head: str,
    source_tree: str,
    seeds: Sequence[str],
    challenge_streams: Sequence[str],
    scaling_ladder: Sequence[int],
    include_stretch: bool,
) -> dict[str, object]:
    campaigns: list[dict[str, object]] = []
    for seed in seeds:
        for challenge_stream in challenge_streams:
            for target in scaling_ladder:
                campaigns.append(
                    run_phase16_campaign(
                        bootstrap=bootstrap,
                        source_head=source_head,
                        source_tree=source_tree,
                        seed=seed,
                        challenge_stream=challenge_stream,
                        target_promotions=target,
                    )
                )
    stretch_campaign: dict[str, object] | None = None
    if include_stretch:
        stretch_campaign = run_phase16_campaign(
            bootstrap=bootstrap,
            source_head=source_head,
            source_tree=source_tree,
            seed=seeds[0],
            challenge_stream=f"{challenge_streams[0]}-stretch",
            target_promotions=PHASE16_STRETCH_TARGET,
        )
    foundation = build_phase16_foundation(campaigns)
    expected_campaign_count = len(seeds) * len(challenge_streams) * len(
        scaling_ladder
    )
    rung_status = {
        str(target): (
            sum(
                campaign.get("target_promotions") == target
                and campaign.get("accepted") is True
                for campaign in campaigns
            )
            == len(seeds) * len(challenge_streams)
        )
        for target in scaling_ladder
    }
    campaign_hashes = [str(campaign["report_hash"]) for campaign in campaigns]
    family_union = sorted(
        {
            str(family)
            for campaign in campaigns
            for family in campaign["update_families_used"]
        }
    )
    accepted = (
        len(campaigns) == expected_campaign_count
        and all(campaign.get("accepted") is True for campaign in campaigns)
        and all(rung_status.values())
        and foundation["accepted"] is True
        and set(family_union) == set(UPDATE_FAMILIES)
        and all(campaign.get("manual_repairs") == 0 for campaign in campaigns)
        and all(
            campaign.get("host_authored_success_schedule_present") is False
            for campaign in campaigns
        )
        and all(campaign.get("frontier_retained") is True for campaign in campaigns)
        and all(
            campaign.get("recursive_productivity_frontier_retained") is True
            for campaign in campaigns
        )
        and all(
            campaign["exhaustion_probe"]["bounded_search_exhausted"] is True
            for campaign in campaigns
        )
        and (
            stretch_campaign is None
            or stretch_campaign.get("accepted") is True
        )
    )
    total_promotions = sum(
        int(campaign["accepted_promotions"]) for campaign in campaigns
    ) + (
        0
        if stretch_campaign is None
        else int(stretch_campaign["accepted_promotions"])
    )
    total_rejections = sum(
        int(campaign["rejected_attempts"]) for campaign in campaigns
    ) + (
        0
        if stretch_campaign is None
        else int(stretch_campaign["rejected_attempts"])
    )
    return {
        "schema_id": PHASE16_CAPTURE_SCHEMA_ID,
        "source_head": source_head,
        "source_tree": source_tree,
        "bootstrap": bootstrap.to_json(),
        "bootstrap_report_hash": bootstrap.report_hash,
        "seeds": list(seeds),
        "challenge_streams": list(challenge_streams),
        "scaling_ladder": list(scaling_ladder),
        "campaigns": campaigns,
        "campaign_hashes": campaign_hashes,
        "campaign_count": len(campaigns),
        "foundation": foundation,
        "rung_status": rung_status,
        "stretch_target": PHASE16_STRETCH_TARGET,
        "stretch_campaign": stretch_campaign,
        "stretch_target_executed": stretch_campaign is not None,
        "stretch_target_accepted": (
            False
            if stretch_campaign is None
            else stretch_campaign.get("accepted") is True
        ),
        "total_accepted_promotions": total_promotions,
        "total_rejected_attempts": total_rejections,
        "update_families_demonstrated": family_union,
        "multi_seed_reproduction": len(seeds) >= 2,
        "multi_challenge_stream_reproduction": len(challenge_streams) >= 2,
        "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
        "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
        "host_authored_success_schedule_present": False,
        "manual_repairs": 0,
        "accepted": accepted,
        "phase16_foundation_closed": foundation["accepted"] is True,
        "phase16_exit_closed": False,
        "gate_e_closed": False,
        "next_phase": 16,
    }


def run_phase16_capture(
    *,
    bootstrap: Phase16BootstrapReport,
    source_head: str,
    source_tree: str,
    seeds: Sequence[str] = PHASE16_DEFAULT_SEEDS,
    challenge_streams: Sequence[str] = PHASE16_DEFAULT_STREAMS,
    scaling_ladder: Sequence[int] = PHASE16_SCALING_LADDER,
    include_stretch: bool = False,
) -> dict[str, object]:
    if tuple(seeds) != tuple(PHASE16_DEFAULT_SEEDS):
        raise SchemaValidationError("phase16.capture.seeds", "authoritative seeds changed")
    if tuple(challenge_streams) != tuple(PHASE16_DEFAULT_STREAMS):
        raise SchemaValidationError(
            "phase16.capture.challenge_streams",
            "authoritative challenge streams changed",
        )
    if tuple(scaling_ladder) != tuple(PHASE16_SCALING_LADDER):
        raise SchemaValidationError(
            "phase16.capture.scaling_ladder",
            "authoritative scaling ladder changed",
        )
    content = _capture_content(
        bootstrap=bootstrap,
        source_head=source_head,
        source_tree=source_tree,
        seeds=seeds,
        challenge_streams=challenge_streams,
        scaling_ladder=scaling_ladder,
        include_stretch=include_stretch,
    )
    report = dict(content)
    report["report_hash"] = canonical_json_hash(content)
    if report["accepted"] is not True:
        raise SchemaValidationError("phase16.capture", "capture predicates failed")
    return report


def validate_phase16_capture(
    value: object,
    *,
    bootstrap: Phase16BootstrapReport,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("phase16.capture", "expected object")
    observed = value.get("report_hash")
    if not isinstance(observed, str):
        raise SchemaValidationError("phase16.capture.report_hash", "missing hash")
    payload = dict(value)
    del payload["report_hash"]
    if observed != canonical_json_hash(payload):
        raise SchemaValidationError("phase16.capture.report_hash", "hash mismatch")
    if value.get("bootstrap_report_hash") != bootstrap.report_hash:
        raise SchemaValidationError(
            "phase16.capture.bootstrap_report_hash",
            "bootstrap binding mismatch",
        )
    campaigns = value.get("campaigns")
    if not isinstance(campaigns, Sequence) or isinstance(
        campaigns, (str, bytes, bytearray)
    ):
        raise SchemaValidationError("phase16.capture.campaigns", "expected array")
    for campaign in campaigns:
        validate_phase16_campaign(campaign, bootstrap=bootstrap)
    stretch = value.get("stretch_campaign")
    if stretch is not None:
        validate_phase16_campaign(stretch, bootstrap=bootstrap)
    rebuilt = run_phase16_capture(
        bootstrap=bootstrap,
        source_head=str(value.get("source_head")),
        source_tree=str(value.get("source_tree")),
        include_stretch=value.get("stretch_target_executed") is True,
    )
    if value != rebuilt:
        raise SchemaValidationError(
            "phase16.capture",
            "deterministic capture reconstruction mismatch",
        )
    return deepcopy(rebuilt)


__all__ = ["run_phase16_capture", "validate_phase16_capture"]
