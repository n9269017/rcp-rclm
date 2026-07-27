from __future__ import annotations

import json
import unittest
from dataclasses import replace

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.gatee.constants import RESULT_EXHAUSTED, RESULT_PROMOTED
from rcp_rclm_runtime_v4.gatee.records import (
    AutonomousSearchReport,
    AttemptRecord,
    RouteHintPolicy,
    SearchExhaustionCertificate,
)
from rcp_rclm_runtime_v4.gatee.reference import (
    build_exhaustion_reference,
    build_promotion_reference,
)
from rcp_rclm_runtime_v4.gatee.search import select_first_accepted
from rcp_rclm_runtime_v4.gatee.validation import validate_report


class GateEContractTests(unittest.TestCase):
    def test_promotion_reference_accepts(self) -> None:
        report = build_promotion_reference()
        validation = validate_report(report)
        self.assertTrue(validation["accepted"])
        self.assertEqual(validation["result_kind"], RESULT_PROMOTED)
        self.assertEqual(validation["selected_attempt_index"], 1)
        self.assertFalse(validation["gate_e_closed"])
        self.assertFalse(validation["phase14_exit_closed"])

    def test_exhaustion_reference_accepts(self) -> None:
        report = build_exhaustion_reference()
        validation = validate_report(report)
        self.assertTrue(validation["accepted"])
        self.assertEqual(validation["result_kind"], RESULT_EXHAUSTED)
        self.assertTrue(validation["exhaustion_verified"])
        self.assertIsNone(validation["selected_attempt_index"])

    def test_reference_serialization_is_deterministic(self) -> None:
        first = build_promotion_reference()
        second = build_promotion_reference()
        first_bytes = json.dumps(
            first.to_json(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        second_bytes = json.dumps(
            second.to_json(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first.report_hash, second.report_hash)

    def test_first_accepted_selection(self) -> None:
        report = build_promotion_reference()
        selected = select_first_accepted(report.attempts)
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.attempt_index, 1)

    def test_forbidden_route_hint_rejects(self) -> None:
        with self.assertRaises(SchemaValidationError):
            RouteHintPolicy(expected_candidate_hash_present=True)

    def test_noncontiguous_attempt_indices_reject(self) -> None:
        report = build_promotion_reference()
        changed = replace(report.attempts[1], attempt_index=2)
        mutated = replace(report, attempts=(report.attempts[0], changed))
        with self.assertRaises(SchemaValidationError):
            validate_report(mutated)

    def test_budget_overflow_rejects(self) -> None:
        report = build_promotion_reference()
        with self.assertRaises(SchemaValidationError):
            validate_report(replace(report, search_budget=4))

    def test_manual_repair_rejects(self) -> None:
        report = build_promotion_reference()
        with self.assertRaises(SchemaValidationError):
            validate_report(replace(report, manual_repairs=1))

    def test_heldout_visibility_rejects(self) -> None:
        report = build_promotion_reference()
        with self.assertRaises(SchemaValidationError):
            validate_report(replace(report, heldout_material_visible_before_freeze=True))

    def test_later_or_wrong_selected_attempt_rejects(self) -> None:
        report = build_promotion_reference()
        with self.assertRaises(SchemaValidationError):
            validate_report(replace(report, selected_attempt_index=0))

    def test_capability_regression_rejects(self) -> None:
        report = build_promotion_reference()
        selected = replace(
            report.attempts[1],
            capability_frontier_after=("capability.heldout.gamma",),
        )
        mutated = replace(report, attempts=(report.attempts[0], selected))
        with self.assertRaises(SchemaValidationError):
            validate_report(mutated)

    def test_no_strict_capability_expansion_rejects(self) -> None:
        report = build_promotion_reference()
        selected = replace(
            report.attempts[1],
            capability_frontier_after=report.predecessor_frontier.capability_tasks,
        )
        mutated = replace(report, attempts=(report.attempts[0], selected))
        with self.assertRaises(SchemaValidationError):
            validate_report(mutated)

    def test_recursive_productivity_regression_rejects(self) -> None:
        report = build_promotion_reference()
        selected = replace(
            report.attempts[1],
            recursive_productivity_frontier_after=(),
        )
        mutated = replace(report, attempts=(report.attempts[0], selected))
        with self.assertRaises(SchemaValidationError):
            validate_report(mutated)

    def test_exhaustion_with_accepted_attempt_rejects(self) -> None:
        promoted = build_promotion_reference()
        attempt_hashes = tuple(attempt.attempt_hash for attempt in promoted.attempts)
        exhaustion = SearchExhaustionCertificate(
            enumeration_hash=promoted.enumeration_hash,
            attempt_hashes=attempt_hashes,
            complete_coverage=True,
            all_attempts_classified=True,
            no_accepted_attempt=True,
        )
        mutated = AutonomousSearchReport(
            source_package_hash=promoted.source_package_hash,
            history_hash=promoted.history_hash,
            challenge_commitment_hash=promoted.challenge_commitment_hash,
            route_hints=promoted.route_hints,
            predecessor_frontier=promoted.predecessor_frontier,
            attempts=promoted.attempts,
            search_budget=promoted.search_budget,
            manual_repairs=0,
            heldout_material_visible_before_freeze=False,
            result_kind=RESULT_EXHAUSTED,
            selected_attempt_index=None,
            exhaustion=exhaustion,
        )
        with self.assertRaises(SchemaValidationError):
            validate_report(mutated)

    def test_exhaustion_hash_order_mismatch_rejects(self) -> None:
        report = build_exhaustion_reference()
        assert report.exhaustion is not None
        reversed_hashes = tuple(reversed(report.exhaustion.attempt_hashes))
        exhaustion = replace(report.exhaustion, attempt_hashes=reversed_hashes)
        with self.assertRaises(SchemaValidationError):
            validate_report(replace(report, exhaustion=exhaustion))

    def test_attempt_rejection_requires_reason(self) -> None:
        report = build_exhaustion_reference()
        source = report.attempts[0]
        with self.assertRaises(SchemaValidationError):
            AttemptRecord(
                attempt_index=source.attempt_index,
                objective_id=source.objective_id,
                update_kinds=source.update_kinds,
                program_hash=source.program_hash,
                candidate_hash=source.candidate_hash,
                gate_d_certificate_hash=source.gate_d_certificate_hash,
                package_generated=True,
                evaluator_accepted=False,
                reason_codes=(),
                capability_frontier_after=source.capability_frontier_after,
                recursive_productivity_frontier_after=source.recursive_productivity_frontier_after,
                search_cost=source.search_cost,
            )

    def test_candidate_self_report_cannot_replace_package_generation(self) -> None:
        report = build_exhaustion_reference()
        source = report.attempts[0]
        with self.assertRaises(SchemaValidationError):
            AttemptRecord(
                attempt_index=source.attempt_index,
                objective_id=source.objective_id,
                update_kinds=source.update_kinds,
                program_hash=source.program_hash,
                candidate_hash=source.candidate_hash,
                gate_d_certificate_hash=source.gate_d_certificate_hash,
                package_generated=False,
                evaluator_accepted=False,
                reason_codes=source.reason_codes,
                capability_frontier_after=source.capability_frontier_after,
                recursive_productivity_frontier_after=source.recursive_productivity_frontier_after,
                search_cost=source.search_cost,
            )


if __name__ == "__main__":
    unittest.main()
