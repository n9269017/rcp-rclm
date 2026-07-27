from __future__ import annotations

from collections.abc import Sequence

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v4.gatee.constants import RESULT_EXHAUSTED, RESULT_PROMOTED
from rcp_rclm_runtime_v4.gatee.records import (
    AutonomousSearchReport,
    AttemptRecord,
    FrontierSnapshot,
    RouteHintPolicy,
    SearchExhaustionCertificate,
)
from rcp_rclm_runtime_v4.gatee.validation import validate_report


def _hash(label: str) -> str:
    return canonical_json_hash({"gate_e_reference_label": label})


def _ordered(*values: str) -> Sequence[str]:
    return tuple(sorted(values, key=lambda item: item.encode("utf-8")))


def _predecessor_frontier() -> FrontierSnapshot:
    return FrontierSnapshot(
        capability_tasks=_ordered(
            "capability.protected.alpha",
            "capability.protected.beta",
        ),
        recursive_productivity_tasks=("recursive.generate_valid_program",),
    )


def build_promotion_reference() -> AutonomousSearchReport:
    predecessor = _predecessor_frontier()
    attempts = (
        AttemptRecord(
            attempt_index=0,
            objective_id="expand_certified_frontier",
            update_kinds=("weight_update",),
            program_hash=_hash("promotion.program.0"),
            candidate_hash=_hash("promotion.candidate.0"),
            gate_d_certificate_hash=_hash("promotion.gate_d.0"),
            package_generated=True,
            evaluator_accepted=False,
            reason_codes=("PROTECTED_CAPABILITY_REGRESSION",),
            capability_frontier_after=predecessor.capability_tasks,
            recursive_productivity_frontier_after=(
                predecessor.recursive_productivity_tasks
            ),
            search_cost=2,
        ),
        AttemptRecord(
            attempt_index=1,
            objective_id="expand_certified_frontier",
            update_kinds=_ordered("memory_update", "retrieval_update"),
            program_hash=_hash("promotion.program.1"),
            candidate_hash=_hash("promotion.candidate.1"),
            gate_d_certificate_hash=_hash("promotion.gate_d.1"),
            package_generated=True,
            evaluator_accepted=True,
            reason_codes=(),
            capability_frontier_after=_ordered(
                *predecessor.capability_tasks,
                "capability.heldout.gamma",
            ),
            recursive_productivity_frontier_after=_ordered(
                *predecessor.recursive_productivity_tasks,
                "recursive.recover_after_rejection",
            ),
            search_cost=3,
        ),
    )
    report = AutonomousSearchReport(
        source_package_hash=_hash("promotion.source_package"),
        history_hash=_hash("promotion.history"),
        challenge_commitment_hash=_hash("promotion.challenge"),
        route_hints=RouteHintPolicy(),
        predecessor_frontier=predecessor,
        attempts=attempts,
        search_budget=5,
        manual_repairs=0,
        heldout_material_visible_before_freeze=False,
        result_kind=RESULT_PROMOTED,
        selected_attempt_index=1,
        exhaustion=None,
    )
    validate_report(report)
    return report


def build_exhaustion_reference() -> AutonomousSearchReport:
    predecessor = _predecessor_frontier()
    attempts = (
        AttemptRecord(
            attempt_index=0,
            objective_id="expand_certified_frontier",
            update_kinds=("planner_update",),
            program_hash=_hash("exhaustion.program.0"),
            candidate_hash=_hash("exhaustion.candidate.0"),
            gate_d_certificate_hash=_hash("exhaustion.gate_d.0"),
            package_generated=True,
            evaluator_accepted=False,
            reason_codes=("NO_STRICT_FRONTIER_EXPANSION",),
            capability_frontier_after=predecessor.capability_tasks,
            recursive_productivity_frontier_after=(
                predecessor.recursive_productivity_tasks
            ),
            search_cost=2,
        ),
        AttemptRecord(
            attempt_index=1,
            objective_id="expand_certified_frontier",
            update_kinds=("adapter_update",),
            program_hash=_hash("exhaustion.program.1"),
            candidate_hash=_hash("exhaustion.candidate.1"),
            gate_d_certificate_hash=_hash("exhaustion.gate_d.1"),
            package_generated=True,
            evaluator_accepted=False,
            reason_codes=("INFORMATION_NONREGRESSION_FAILED",),
            capability_frontier_after=predecessor.capability_tasks,
            recursive_productivity_frontier_after=(
                predecessor.recursive_productivity_tasks
            ),
            search_cost=2,
        ),
    )
    attempt_hashes = tuple(attempt.attempt_hash for attempt in attempts)
    enumeration_hash = canonical_json_hash(list(attempt_hashes))
    report = AutonomousSearchReport(
        source_package_hash=_hash("exhaustion.source_package"),
        history_hash=_hash("exhaustion.history"),
        challenge_commitment_hash=_hash("exhaustion.challenge"),
        route_hints=RouteHintPolicy(),
        predecessor_frontier=predecessor,
        attempts=attempts,
        search_budget=4,
        manual_repairs=0,
        heldout_material_visible_before_freeze=False,
        result_kind=RESULT_EXHAUSTED,
        selected_attempt_index=None,
        exhaustion=SearchExhaustionCertificate(
            enumeration_hash=enumeration_hash,
            attempt_hashes=attempt_hashes,
            complete_coverage=True,
            all_attempts_classified=True,
            no_accepted_attempt=True,
        ),
    )
    validate_report(report)
    return report
