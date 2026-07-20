from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    ALPHA_PROGRAM_BYTES,
    BETA_PROGRAM_BYTES,
    INVALID_PROGRAM_BYTES,
)
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import build_phase11b_reference


class Phase11BPortableLifecycleTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11b-tests-")
        cls.root = Path(cls.temporary.name)
        cls.reference = build_phase11b_reference(cls.root / "reference")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_three_model_programs_are_exact_and_replayed(self) -> None:
        reference = self.reference
        self.assertEqual(reference.invalid_invocation.program_text.encode("ascii"), INVALID_PROGRAM_BYTES)
        self.assertEqual(reference.alpha_invocation.program_text.encode("ascii"), ALPHA_PROGRAM_BYTES)
        self.assertEqual(reference.beta_invocation.program_text.encode("ascii"), BETA_PROGRAM_BYTES)
        self.assertTrue(reference.invalid_invocation.model_generated)
        self.assertTrue(reference.alpha_invocation.model_generated)
        self.assertTrue(reference.beta_invocation.model_generated)

    def test_invalid_proposal_is_rejected_before_candidate_count(self) -> None:
        validation = self.reference.invalid_validation
        self.assertFalse(validation.accepted)
        reasons = {reason.value for reason in validation.reason_codes}
        self.assertEqual(
            reasons,
            {"PHASE11_BUDGET_EXCEEDED", "PHASE11_FORBIDDEN_UPDATE_CLASS"},
        )

    def test_alpha_candidate_is_realized_then_rejected_for_protected_regression(self) -> None:
        reference = self.reference
        self.assertTrue(reference.alpha_validation.accepted)
        self.assertTrue(reference.alpha_candidate.structurally_valid)
        self.assertTrue(reference.alpha_phase6.accepted)
        self.assertFalse(reference.alpha_candidate.evaluation.accepted)
        self.assertEqual(
            reference.alpha_candidate.evaluation.rejection_reason,
            "protected_capability_regression",
        )
        realization = reference.alpha_phase6.phase6.report.realization
        self.assertIsNotNone(realization)
        self.assertTrue(realization and realization.rollback.verified)

    def test_beta_candidate_retains_frontier_and_passes_gate_d(self) -> None:
        reference = self.reference
        self.assertTrue(reference.beta_validation.accepted)
        self.assertTrue(reference.beta_candidate.structurally_valid)
        self.assertTrue(reference.beta_phase6.accepted)
        self.assertTrue(reference.beta_candidate.evaluation.accepted)
        self.assertTrue(reference.lifecycle_transition.accepted)
        self.assertEqual(
            set(reference.lifecycle_transition.changed_components),
            {
                "adapter_manifest",
                "data_curriculum",
                "generator_policy",
                "model_weights",
                "planner_policy",
            },
        )
        self.assertEqual(
            set(reference.lifecycle_transition.retained_task_ids),
            {
                "lean.phase10.protected.reflexive_seven",
                "lean.phase10.heldout.linear_gap",
            },
        )
        self.assertEqual(
            tuple(reference.lifecycle_transition.new_task_ids),
            ("lean.phase11.heldout.add_zero_macro",),
        )

    def test_successor_generator_and_planner_are_substantive_package_changes(self) -> None:
        reference = self.reference
        self.assertNotEqual(
            reference.active.active_manifest.generator_policy_hash,
            reference.beta_candidate.manifest.generator_policy_hash,
        )
        self.assertNotEqual(
            reference.active.active_manifest.planner_policy_hash,
            reference.beta_candidate.manifest.planner_policy_hash,
        )
        self.assertEqual(
            reference.beta_candidate.invocation.program.successor_generator_generation,
            2,
        )
        self.assertEqual(
            reference.beta_candidate.invocation.program.successor_planner_generation,
            2,
        )

    def test_original_fixed_budget_and_zero_manual_repair_are_retained(self) -> None:
        summary = self.reference.summary_json()
        budget = summary["budget"]
        self.assertEqual(budget["generator_invocations"], 3)
        self.assertEqual(budget["candidate_realizations"], 2)
        self.assertEqual(budget["candidate_evaluations"], 2)
        self.assertEqual(budget["manual_repairs"], 0)
        self.assertFalse(summary["heldout_material_consumed"])
        self.assertTrue(summary["deterministic_generator_replay"])

    def test_portable_reference_closes_lifecycle_but_not_promotion(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        boundary = summary["claim_boundary"]
        self.assertTrue(boundary["model_generated_candidate_realized"])
        self.assertTrue(boundary["model_generated_candidate_rejected"])
        self.assertTrue(boundary["later_fresh_candidate_accepted"])
        self.assertTrue(boundary["successor_generator_planner_installed"])
        self.assertFalse(boundary["candidate_promoted"])
        self.assertFalse(boundary["modified_successor_generator_used_recursively"])
        self.assertFalse(boundary["phase11_exit_closed"])


if __name__ == "__main__":
    unittest.main()
