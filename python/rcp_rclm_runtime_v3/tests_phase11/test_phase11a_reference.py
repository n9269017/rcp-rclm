from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase11.constants import (
    ACCEPTED_PROGRAM_BYTES,
    PROPOSAL_PROTOCOL_HASH,
    REJECTED_PROGRAM_BYTES,
)
from rcp_rclm_runtime_v3.phase11.generator import generate_typed_mutation_program
from rcp_rclm_runtime_v3.phase11.grammar import (
    encode_typed_mutation_program,
    parse_typed_mutation_program,
)
from rcp_rclm_runtime_v3.phase11.records import Phase11ReasonCode
from rcp_rclm_runtime_v3.phase11.reference import build_phase11a_reference


class Phase11AReferenceTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11a-tests-")
        cls.root = Path(cls.temporary.name)
        cls.reference = build_phase11a_reference(cls.root / "reference")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_bootstrap_installs_bounded_active_generator_without_counting_it(self) -> None:
        bootstrap = self.reference.bootstrap
        self.assertTrue(bootstrap.accepted)
        self.assertNotEqual(
            bootstrap.phase10_reference.candidate_manifest.model_identity_hash,
            bootstrap.active_manifest.model_identity_hash,
        )
        self.assertNotEqual(
            bootstrap.phase10_reference.candidate_manifest.generator_policy_hash,
            bootstrap.active_manifest.generator_policy_hash,
        )
        self.assertNotEqual(
            bootstrap.phase10_reference.candidate_manifest.planner_policy_hash,
            bootstrap.active_manifest.planner_policy_hash,
        )
        self.assertEqual(
            bootstrap.active_state.self_hosting.proposal_protocol_hash,
            PROPOSAL_PROTOCOL_HASH,
        )
        self.assertTrue(bootstrap.protected_report.solved)
        self.assertTrue(bootstrap.heldout_report.solved)
        self.assertFalse(
            bootstrap.to_json()["claim_boundary"]["bootstrap_counted_as_autonomous_improvement"]
        )

    def test_active_model_emits_exact_rejected_and_fresh_programs(self) -> None:
        reference = self.reference
        self.assertTrue(reference.first_invocation.model_generated)
        self.assertTrue(reference.second_invocation.model_generated)
        self.assertEqual(
            reference.first_invocation.program_text.encode("ascii"),
            REJECTED_PROGRAM_BYTES,
        )
        self.assertEqual(
            reference.second_invocation.program_text.encode("ascii"),
            ACCEPTED_PROGRAM_BYTES,
        )
        self.assertNotEqual(
            reference.first_invocation.generator_input.input_hash,
            reference.second_invocation.generator_input.input_hash,
        )
        self.assertNotEqual(
            reference.first_invocation.program.program_hash,
            reference.second_invocation.program.program_hash,
        )

    def test_first_program_is_rejected_and_second_program_validates(self) -> None:
        first = self.reference.first_validation
        second = self.reference.second_validation
        self.assertFalse(first.accepted)
        self.assertIn(Phase11ReasonCode.FORBIDDEN_UPDATE_CLASS, first.reason_codes)
        self.assertIn(Phase11ReasonCode.BUDGET_EXCEEDED, first.reason_codes)
        self.assertTrue(second.accepted, second.reason_codes)

    def test_accepted_program_requests_weight_generator_and_planner_updates(self) -> None:
        program = self.reference.second_invocation.program
        self.assertEqual(
            program.selected_update_classes,
            ("generator_update", "planner_update", "weight_update"),
        )
        self.assertEqual(
            program.expected_affected_components,
            ("generator_policy", "model_weights", "planner_policy"),
        )
        self.assertEqual(program.successor_generator_generation, 2)
        self.assertEqual(program.successor_planner_generation, 2)
        self.assertFalse(program.data_selection.heldout_material_visible)
        self.assertTrue(program.rollback_declaration.exact)
        self.assertEqual(program.training_policy.steps, 1)

    def test_fixed_budget_and_zero_manual_repair_are_retained(self) -> None:
        ledger = self.reference.ledger
        self.assertEqual(ledger.generator_invocations, 2)
        self.assertEqual(ledger.candidate_count_consumed, 2)
        self.assertEqual(ledger.evaluation_calls_consumed, 2)
        self.assertEqual(ledger.manual_repair_count, 0)
        self.assertEqual(ledger.budget_hash, self.reference.bootstrap.budget.budget_hash)

    def test_grammar_round_trip_is_canonical_and_whitespace_fails(self) -> None:
        for raw in (REJECTED_PROGRAM_BYTES, ACCEPTED_PROGRAM_BYTES):
            program = parse_typed_mutation_program(raw)
            self.assertEqual(encode_typed_mutation_program(program), raw)
        with self.assertRaises(SchemaValidationError):
            parse_typed_mutation_program(b" " + ACCEPTED_PROGRAM_BYTES)

    def test_input_binding_tampering_fails_closed(self) -> None:
        tampered = dataclasses.replace(
            self.reference.second_invocation.generator_input,
            model_identity_hash="0" * 64,
        )
        with self.assertRaises(SchemaValidationError):
            generate_typed_mutation_program(
                self.reference.bootstrap.active_package_root,
                tampered,
            )

    def test_phase11a_summary_keeps_full_phase_exit_open(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        boundary = summary["claim_boundary"]
        self.assertTrue(boundary["active_predecessor_model_generated_proposal"])
        self.assertTrue(boundary["model_generated_proposal_rejected"])
        self.assertTrue(boundary["fresh_model_generated_typed_program_validated"])
        self.assertFalse(boundary["model_generated_candidate_realized"])
        self.assertFalse(boundary["model_generated_candidate_promoted"])
        self.assertFalse(boundary["successor_generator_planner_installed"])
        self.assertFalse(boundary["phase11_exit_closed"])


if __name__ == "__main__":
    unittest.main()
