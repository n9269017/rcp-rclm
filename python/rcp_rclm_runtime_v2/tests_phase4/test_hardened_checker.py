from __future__ import annotations

import unittest
from dataclasses import replace

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.hardened import check_hardened_transition
from rcp_rclm_runtime.adversarial.reference import reference_hardened_request


class HardenedCheckerTests(unittest.TestCase):
    def test_reference_classical_request_is_accepted(self) -> None:
        report = check_hardened_transition(reference_hardened_request())
        self.assertTrue(report.accepted)
        self.assertEqual(report.verdict, "accept")
        self.assertEqual(report.reason_codes, ())
        self.assertEqual(report.integrity_result.status, "pass")
        self.assertIsNotNone(report.checker_report)

    def test_reference_quantum_request_is_accepted(self) -> None:
        report = check_hardened_transition(
            reference_hardened_request("gate_c_diagonal_quantum")
        )
        self.assertTrue(report.accepted)
        self.assertEqual(report.integrity_result.status, "pass")

    def test_input_is_not_mutated_and_report_is_deterministic(self) -> None:
        request = reference_hardened_request()
        before = canonical_json_hash(request.to_json())
        first = check_hardened_transition(request)
        second = check_hardened_transition(request)
        after = canonical_json_hash(request.to_json())
        self.assertEqual(before, after)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.report_hash, second.report_hash)

    def test_parent_hash_substitution_is_rejected(self) -> None:
        request = reference_hardened_request()
        manifest = replace(
            request.package_integrity.candidate_manifest,
            parent_manifest_hash="0" * 64,
        )
        integrity = replace(
            request.package_integrity,
            candidate_manifest=manifest,
        )
        report = check_hardened_transition(
            replace(request, package_integrity=integrity)
        )
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.PARENT_LINK_MISMATCH, report.reason_codes)

    def test_checker_manifest_tamper_is_rejected(self) -> None:
        request = reference_hardened_request()
        integrity = replace(
            request.package_integrity,
            checker_manifest_hash="0" * 64,
        )
        report = check_hardened_transition(
            replace(request, package_integrity=integrity)
        )
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.HASH_MISMATCH, report.reason_codes)
        self.assertIn(ReasonCode.PROVENANCE_FAILED, report.reason_codes)


if __name__ == "__main__":
    unittest.main()
