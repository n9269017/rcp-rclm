from __future__ import annotations

import unittest

from phase5_helpers import fixture_lean_report
from rcp_rclm_runtime.generator.pipeline import run_phase5a_reference_loop
from rcp_rclm_runtime.generator.reference import reference_generator_input


class Phase5AReferencePipelineTests(unittest.TestCase):
    def test_initial_improvement_runs_end_to_end(self) -> None:
        evidence = run_phase5a_reference_loop(
            reference_generator_input("initial"),
            fixture_lean_report,
        )
        report = evidence.report
        self.assertTrue(report.accepted)
        self.assertEqual(report.verdict, "accept")
        self.assertEqual(report.reason_codes, ())
        self.assertEqual(report.replay_result.status, "pass")
        self.assertEqual(report.proposal_validation_result.status, "pass")
        self.assertEqual(report.certificate_construction_result.status, "pass")
        self.assertEqual(report.selection_result.status, "pass")
        self.assertEqual(report.realization_result.status, "pass")
        self.assertIsNotNone(report.hardened_checker_report)
        self.assertTrue(report.hardened_checker_report.accepted)

    def test_target_stability_runs_end_to_end(self) -> None:
        evidence = run_phase5a_reference_loop(
            reference_generator_input("target"),
            fixture_lean_report,
        )
        report = evidence.report
        self.assertTrue(report.accepted)
        self.assertIsNotNone(report.proposal)
        self.assertEqual(report.proposal.word, "stabilize")
        realization = report.realization_result.to_json()["evidence"]
        candidate = realization["candidate"]
        self.assertEqual(candidate["next"]["core"]["state"], "target")

    def test_successor_is_derived_after_generator_output(self) -> None:
        evidence = run_phase5a_reference_loop(
            reference_generator_input("initial"),
            fixture_lean_report,
        )
        self.assertIsNotNone(evidence.report.proposal)
        proposal_json = evidence.report.proposal.to_json()
        realization = evidence.report.realization_result.to_json()["evidence"]
        self.assertNotIn("successor", proposal_json)
        self.assertNotIn("candidate", proposal_json)
        self.assertFalse(realization["generator_successor_field_consumed"])
        self.assertFalse(realization["manual_successor_output_consumed"])

    def test_certificate_is_constructed_outside_generator(self) -> None:
        evidence = run_phase5a_reference_loop(
            reference_generator_input("initial"),
            fixture_lean_report,
        )
        self.assertIsNotNone(evidence.report.proposal)
        proposal_json = evidence.report.proposal.to_json()
        construction = evidence.report.certificate_construction_result.to_json()[
            "evidence"
        ]
        self.assertNotIn("certificate", proposal_json)
        self.assertFalse(construction["generator_certificate_field_consumed"])
        self.assertEqual(construction["certificate_name"], "improvement")

    def test_two_complete_runs_are_identical(self) -> None:
        request = reference_generator_input("initial")
        first = run_phase5a_reference_loop(request, fixture_lean_report).report
        second = run_phase5a_reference_loop(request, fixture_lean_report).report
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.report_hash, second.report_hash)


if __name__ == "__main__":
    unittest.main()
