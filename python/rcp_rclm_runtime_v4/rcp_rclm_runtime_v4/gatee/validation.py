from __future__ import annotations

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.gatee.constants import RESULT_EXHAUSTED, RESULT_PROMOTED
from rcp_rclm_runtime_v4.gatee.records import AutonomousSearchReport
from rcp_rclm_runtime_v4.gatee.search import all_attempts_rejected, select_first_accepted


def _require_subset(left: tuple[str, ...], right: tuple[str, ...], path: str) -> None:
    missing = sorted(set(left) - set(right), key=lambda item: item.encode("utf-8"))
    if missing:
        raise SchemaValidationError(path, f"frontier regression: {missing}")


def validate_report(report: AutonomousSearchReport) -> dict[str, object]:
    expected_indices = tuple(range(len(report.attempts)))
    observed_indices = tuple(attempt.attempt_index for attempt in report.attempts)
    if observed_indices != expected_indices:
        raise SchemaValidationError(
            "report.attempts",
            f"attempt indices must be contiguous from zero; observed={observed_indices}",
        )

    attempt_hashes = tuple(attempt.attempt_hash for attempt in report.attempts)
    if len(set(attempt_hashes)) != len(attempt_hashes):
        raise SchemaValidationError("report.attempts", "duplicate canonical attempt hash")

    total_search_cost = sum(attempt.search_cost for attempt in report.attempts)
    if total_search_cost > report.search_budget:
        raise SchemaValidationError(
            "report.search_budget",
            f"search cost {total_search_cost} exceeds budget {report.search_budget}",
        )
    if report.manual_repairs != 0:
        raise SchemaValidationError("report.manual_repairs", "manual repair is forbidden")
    if report.heldout_material_visible_before_freeze:
        raise SchemaValidationError(
            "report.heldout_material_visible_before_freeze",
            "held-out material is forbidden before candidate freeze",
        )

    first_accepted = select_first_accepted(report.attempts)
    predecessor_capabilities = report.predecessor_frontier.capability_tasks
    predecessor_recursive = report.predecessor_frontier.recursive_productivity_tasks

    if report.result_kind == RESULT_PROMOTED:
        if report.exhaustion is not None:
            raise SchemaValidationError("report.exhaustion", "promoted search cannot include exhaustion")
        if first_accepted is None:
            raise SchemaValidationError("report.result_kind", "promotion requires an accepted attempt")
        if report.selected_attempt_index != first_accepted.attempt_index:
            raise SchemaValidationError(
                "report.selected_attempt_index",
                "selected attempt must be the first accepted attempt",
            )
        _require_subset(
            predecessor_capabilities,
            first_accepted.capability_frontier_after,
            "report.selected.capability_frontier_after",
        )
        if len(first_accepted.capability_frontier_after) <= len(predecessor_capabilities):
            raise SchemaValidationError(
                "report.selected.capability_frontier_after",
                "accepted successor must strictly expand the capability frontier",
            )
        _require_subset(
            predecessor_recursive,
            first_accepted.recursive_productivity_frontier_after,
            "report.selected.recursive_productivity_frontier_after",
        )
        selected_attempt_hash = first_accepted.attempt_hash
        exhaustion_verified = False
    elif report.result_kind == RESULT_EXHAUSTED:
        if report.selected_attempt_index is not None:
            raise SchemaValidationError(
                "report.selected_attempt_index",
                "exhausted search cannot select an attempt",
            )
        if report.exhaustion is None:
            raise SchemaValidationError("report.exhaustion", "exhausted result requires a certificate")
        if not all_attempts_rejected(report.attempts):
            raise SchemaValidationError("report.exhaustion", "accepted attempt exists in exhausted search")
        if report.exhaustion.enumeration_hash != report.enumeration_hash:
            raise SchemaValidationError("report.exhaustion.enumeration_hash", "enumeration hash mismatch")
        if report.exhaustion.attempt_hashes != attempt_hashes:
            raise SchemaValidationError("report.exhaustion.attempt_hashes", "attempt hash order mismatch")
        selected_attempt_hash = None
        exhaustion_verified = True
    else:
        raise SchemaValidationError("report.result_kind", "unreachable result kind")

    stable_summary = {
        "schema_id": "runtime.v4.gatee.validation_report.v1",
        "accepted": True,
        "contract_version": report.contract_version,
        "source_package_hash": report.source_package_hash,
        "history_hash": report.history_hash,
        "challenge_commitment_hash": report.challenge_commitment_hash,
        "enumeration_hash": report.enumeration_hash,
        "attempt_count": len(report.attempts),
        "total_search_cost": total_search_cost,
        "search_budget": report.search_budget,
        "result_kind": report.result_kind,
        "selected_attempt_index": report.selected_attempt_index,
        "selected_attempt_hash": selected_attempt_hash,
        "exhaustion_verified": exhaustion_verified,
        "route_hints_absent": True,
        "manual_repairs": report.manual_repairs,
        "heldout_material_visible_before_freeze": False,
        "gate_e_formal_foundation_closed": False,
        "gate_e_closed": False,
        "phase14_exit_closed": False,
        "report_hash": report.report_hash,
    }
    stable_summary["validation_hash"] = canonical_json_hash(stable_summary)
    return stable_summary
