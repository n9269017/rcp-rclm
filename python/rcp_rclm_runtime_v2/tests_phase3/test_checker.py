from __future__ import annotations

import json
import unittest
from dataclasses import replace

from phase3_helpers import (
    classical_request,
    lean_report_for,
    quantum_request,
    with_refreshed_lean,
)
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.mathematics.classical import UNIFORM_BINARY
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.schema._common import TypedArtifactRecord
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.aggregate import check_transition, check_transition_bytes
from rcp_rclm_runtime.checker.records import ProtectedDistinctionRecord


class Phase3CheckerAcceptanceTests(unittest.TestCase):
    def test_classical_improvement_is_accepted(self) -> None:
        report = check_transition(classical_request())
        self.assertTrue(report.accepted)
        self.assertEqual(report.verdict, "accept")
        self.assertEqual(report.reason_codes, ())
        self.assertEqual(
            [item.value for item in report.computed_residuals],
            [Rational(-1), Rational(-1)],
        )
        self.assertEqual(report.strict_witness_result.status, "pass")
        self.assertEqual(report.invariant_result.status, "pass")
        self.assertEqual(report.containment_result.status, "pass")
        self.assertTrue(
            report.strict_witness_result.to_json()["evidence"][
                "strict_witness_derived"
            ]
        )

    def test_classical_stability_is_accepted(self) -> None:
        report = check_transition(classical_request(stability=True))
        self.assertTrue(report.accepted)
        self.assertEqual(report.metric_bounds.progress_delta.lower, Rational.zero())
        self.assertFalse(
            report.strict_witness_result.to_json()["evidence"][
                "strict_obligation_required"
            ]
        )

    def test_quantum_improvement_is_accepted(self) -> None:
        report = check_transition(quantum_request())
        self.assertTrue(report.accepted)
        self.assertEqual(report.metric_bounds.scope, "gate_c_diagonal_quantum")
        self.assertEqual(report.recovery_result.status, "pass")
        self.assertEqual(report.monitor_result.status, "pass")

    def test_quantum_stability_is_accepted(self) -> None:
        report = check_transition(quantum_request(stability=True))
        self.assertTrue(report.accepted)
        self.assertEqual(report.metric_bounds.progress_delta.lower, Rational.zero())
        self.assertEqual(report.metric_bounds.progress_delta.upper, Rational.zero())

    def test_checker_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        request = classical_request()
        before = canonical_json_hash(request.to_json())
        first = check_transition(request)
        second = check_transition(request)
        after = canonical_json_hash(request.to_json())
        self.assertEqual(before, after)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.report_hash, second.report_hash)


class Phase3CheckerRejectionTests(unittest.TestCase):
    def test_wrong_successor_is_rejected(self) -> None:
        report = check_transition(classical_request(successor="initial"))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.TYPED_SUCCESSOR_FAILED, report.reason_codes)
        self.assertIn(ReasonCode.RESIDUAL_POSITIVE, report.reason_codes)
        self.assertIn(ReasonCode.LEAN_VERIFIER_FAILED, report.reason_codes)
        self.assertIn(ReasonCode.CONTAINMENT_FAILED, report.reason_codes)

    def test_outside_successor_rejects_invariant_containment_and_domain(self) -> None:
        report = check_transition(classical_request(successor="outside"))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.INVARIANT_FAILED, report.reason_codes)
        self.assertIn(ReasonCode.CONTAINMENT_FAILED, report.reason_codes)
        self.assertIn(ReasonCode.SUCCESSOR_DOMAIN_FAILED, report.reason_codes)

    def test_wrong_certificate_is_rejected(self) -> None:
        report = check_transition(classical_request(certificate_name="stability"))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.RESIDUAL_POSITIVE, report.reason_codes)
        self.assertIn(ReasonCode.RESOURCE_INVALID, report.reason_codes)

    def test_malformed_certificate_is_rejected(self) -> None:
        report = check_transition(
            classical_request(stability=True, certificate_name="malformed")
        )
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.TRUST_INVALID, report.reason_codes)
        self.assertIn(ReasonCode.MONITOR_FAILED, report.reason_codes)

    def test_network_activity_is_rejected(self) -> None:
        request = classical_request()
        resource = replace(request.resource_record, network_requests=1)
        report = check_transition(replace(request, resource_record=resource))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.RESOURCE_INVALID, report.reason_codes)
        self.assertFalse(report.resource_result.to_json()["evidence"]["network_free"])

    def test_model_activity_is_rejected(self) -> None:
        request = classical_request()
        resource = replace(request.resource_record, model_invocations=1)
        report = check_transition(replace(request, resource_record=resource))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.RESOURCE_INVALID, report.reason_codes)

    def test_manual_repair_is_rejected(self) -> None:
        request = classical_request()
        resource = replace(request.resource_record, manual_repair_count=1)
        report = check_transition(replace(request, resource_record=resource))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.MANUAL_REPAIR_DETECTED, report.reason_codes)

    def test_trust_anchor_replacement_is_rejected(self) -> None:
        request = classical_request()
        anchor = replace(request.trust_anchor, gate_c_audit_sha256="0" * 64)
        report = check_transition(replace(request, trust_anchor=anchor))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.TRUST_ANCHOR_CHANGED, report.reason_codes)

    def test_evaluation_evidence_is_recomputed(self) -> None:
        request = classical_request()
        evaluation = replace(
            request.evaluation_evidence,
            successor_observation=UNIFORM_BINARY,
        )
        report = check_transition(replace(request, evaluation_evidence=evaluation))
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.REFINEMENT_MISMATCH, report.reason_codes)
        self.assertEqual(report.evaluation_result.status, "fail")

    def test_nonzero_selected_loss_budget_is_rejected(self) -> None:
        request = classical_request()
        distinctions = tuple(
            ProtectedDistinctionRecord(
                item.distinction_id,
                Rational(1, 10)
                if item.distinction_id == "target_fit"
                else item.loss_budget,
            )
            for item in request.protected_distinctions
        )
        report = check_transition(
            replace(request, protected_distinctions=distinctions)
        )
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.NONLOSS_FAILED, report.reason_codes)

    def test_noncanonical_rclm_state_is_rejected(self) -> None:
        request = classical_request()
        bad_language = TypedArtifactRecord.from_value(
            "rclm.language_register.v2",
            {"register": "invalid"},
        )
        predecessor = replace(request.predecessor, language=bad_language)
        mutated = with_refreshed_lean(replace(request, predecessor=predecessor))
        report = check_transition(mutated)
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.REFINEMENT_MISMATCH, report.reason_codes)

    def test_indeterminate_lean_bridge_is_fail_closed(self) -> None:
        request = classical_request()
        lean = lean_report_for(
            request.predecessor,
            request.candidate,
            request.certificate,
            indeterminate=True,
        )
        report = check_transition(replace(request, lean_bridge_report=lean))
        self.assertFalse(report.accepted)
        self.assertEqual(report.verdict, "indeterminate")
        self.assertIn(ReasonCode.LEAN_VERIFIER_FAILED, report.reason_codes)


class Phase3CheckerParsingTests(unittest.TestCase):
    def test_candidate_success_assertions_are_not_accepted_as_evidence(self) -> None:
        for field in (
            "certificate_preserved",
            "reality_containment",
            "strict_improvement",
        ):
            with self.subTest(field=field):
                value = classical_request().to_json()
                value[field] = True
                report = check_transition_bytes(canonical_json_bytes(value))
                self.assertFalse(report.accepted)
                self.assertIn(ReasonCode.SCHEMA_MALFORMED, report.reason_codes)

    def test_noncanonical_json_is_rejected(self) -> None:
        value = classical_request().to_json()
        data = json.dumps(value, indent=2, sort_keys=False).encode("utf-8")
        report = check_transition_bytes(data)
        self.assertFalse(report.accepted)
        self.assertIn(ReasonCode.CANONICALIZATION_FAILED, report.reason_codes)

    def test_canonical_round_trip_executes(self) -> None:
        request = classical_request()
        report = check_transition_bytes(canonical_json_bytes(request.to_json()))
        self.assertTrue(report.accepted)
        self.assertIn("candidate", report.artifact_hashes.to_json())
        self.assertIn("lean_packet", report.artifact_hashes.to_json())


if __name__ == "__main__":
    unittest.main()
