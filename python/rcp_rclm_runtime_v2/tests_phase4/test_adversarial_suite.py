from __future__ import annotations

import unittest

from rcp_rclm_runtime.adversarial.runner import run_phase4_adversarial_suite


class Phase4AdversarialSuiteTests(unittest.TestCase):
    def test_required_attack_surface_is_closed(self) -> None:
        report = run_phase4_adversarial_suite()
        required_classes = {
            "malformed_schema",
            "unknown_schema_version",
            "missing_evidence",
            "parent_hash_substitution",
            "certificate_replay",
            "tampered_candidate_files",
            "tampered_checker_manifest",
            "nan",
            "infinity",
            "negative_probability",
            "non_normalized_probability",
            "unsupported_qre_support",
            "wrong_matrix_dimension",
            "non_diagonal_matrix",
            "unsupported_channel",
            "forged_recovery_witness",
            "forged_strict_progress_witness",
            "insufficient_numerical_margin",
            "resource_budget_overflow",
            "trust_anchor_replacement",
            "manual_repair_marker",
            "hidden_oracle_marker",
            "generated_lean_forbidden_source",
        }
        observed_classes = {item.attack_class for item in report.results}
        self.assertTrue(required_classes.issubset(observed_classes))
        self.assertGreaterEqual(report.case_count, 27)
        self.assertTrue(report.all_passed)
        self.assertEqual(report.failed_count, 0)

    def test_every_attack_is_a_first_class_deterministic_result(self) -> None:
        report = run_phase4_adversarial_suite()
        for result in report.results:
            with self.subTest(case_id=result.case_id):
                self.assertTrue(result.passed)
                self.assertTrue(result.deterministic_replay)
                self.assertNotEqual(result.observed_verdict, "accept")
                self.assertEqual(len(result.first_observation_hash), 64)
                self.assertEqual(len(result.second_observation_hash), 64)
                self.assertEqual(len(result.result_hash), 64)

    def test_forbidden_lean_tokens_are_individually_recorded(self) -> None:
        report = run_phase4_adversarial_suite()
        case_ids = {item.case_id for item in report.results}
        self.assertIn("phase4.lean_source.sorry", case_ids)
        self.assertIn("phase4.lean_source.sorry_ax", case_ids)
        self.assertIn("phase4.lean_source.admit", case_ids)
        self.assertIn("phase4.lean_source.local_axiom", case_ids)
        self.assertIn("phase4.lean_source.invalid_utf8", case_ids)

    def test_suite_report_is_deterministic(self) -> None:
        first = run_phase4_adversarial_suite()
        second = run_phase4_adversarial_suite()
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.report_hash, second.report_hash)


if __name__ == "__main__":
    unittest.main()
