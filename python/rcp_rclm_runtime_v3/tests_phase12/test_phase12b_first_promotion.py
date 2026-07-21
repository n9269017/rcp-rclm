from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import build_phase12b_reference
from rcp_rclm_runtime_v3.phase12.phase12b_program import (
    PHASE12B_ACCEPTED_PROGRAM_BYTES,
)
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import PHASE12B_NEW_TASK


class Phase12BFirstPromotionPortableTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12b-tests-")
        cls.root = Path(cls.temporary.name)
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.reference = build_phase12b_reference(
            cls.root / "reference",
            repo_root=cls.repo_root,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_fresh_rejection_conditioned_proposal_is_package_generated(self) -> None:
        reference = self.reference
        self.assertTrue(reference.proposal.package_generated)
        self.assertTrue(reference.validation.accepted)
        self.assertTrue(reference.deterministic_proposal_replay)
        self.assertEqual(
            reference.proposal.program_text.encode("ascii"),
            PHASE12B_ACCEPTED_PROGRAM_BYTES,
        )
        self.assertEqual(
            tuple(reference.proposal.program.selected_update_classes),
            ("weight_update",),
        )
        self.assertEqual(
            tuple(reference.proposal.program.expected_affected_components),
            ("model_weights",),
        )

    def test_first_phase12_candidate_is_realized_with_exact_rollback(self) -> None:
        reference = self.reference
        self.assertTrue(reference.semantic_candidate.accepted)
        self.assertTrue(reference.phase6.accepted)
        realization = reference.phase6.phase6.report.realization
        self.assertIsNotNone(realization)
        self.assertTrue(realization and realization.rollback.verified)
        self.assertTrue(reference.lifecycle_transition.accepted)
        self.assertEqual(
            tuple(reference.lifecycle_transition.changed_components),
            ("model_weights",),
        )

    def test_first_phase12_frontier_expands_from_three_to_four(self) -> None:
        reference = self.reference
        before = reference.phase12a.phase11.beta_candidate.candidate_state
        self.assertIsNotNone(before)
        self.assertEqual(len(before.capability_frontier.task_ids), 3)
        self.assertEqual(
            len(reference.semantic_candidate.candidate_state.capability_frontier.task_ids),
            4,
        )
        self.assertEqual(
            tuple(reference.lifecycle_transition.new_task_ids),
            (PHASE12B_NEW_TASK.task_id,),
        )
        self.assertEqual(len(reference.lifecycle_transition.retained_task_ids), 3)

    def test_selected_information_obligations_accept(self) -> None:
        information = self.reference.semantic_candidate.information_report
        self.assertTrue(information.protected_unchanged)
        self.assertTrue(information.phase10_unchanged)
        self.assertTrue(information.phase11_unchanged)
        self.assertTrue(information.new_task_improvement_interval.strictly_positive())
        self.assertTrue(information.accepted)

    def test_generator_and_planner_remain_the_active_generation2_policies(self) -> None:
        reference = self.reference
        active = reference.phase12a.phase11.beta_candidate.manifest
        candidate = reference.semantic_candidate.manifest
        self.assertEqual(candidate.generator_policy_hash, active.generator_policy_hash)
        self.assertEqual(candidate.planner_policy_hash, active.planner_policy_hash)
        self.assertNotEqual(candidate.model_identity_hash, active.model_identity_hash)

    def test_portable_ledger_retains_rejection_and_pending_promotion(self) -> None:
        ledger = self.reference.ledger
        self.assertEqual(ledger.generator_invocations, 2)
        self.assertEqual(ledger.rejected_attempts, 1)
        self.assertEqual(ledger.candidate_realizations, 1)
        self.assertEqual(ledger.candidate_evaluations, 1)
        self.assertEqual(ledger.accepted_promotions, 0)
        self.assertEqual(ledger.frontier_expansions, 0)
        self.assertEqual(ledger.manual_repairs, 0)

    def test_phase12b_closes_realization_not_yet_atomic_promotion(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        boundary = summary["claim_boundary"]
        self.assertTrue(boundary["fresh_rejection_conditioned_proposal_generated"])
        self.assertTrue(boundary["proposal_source_active_generation2_package"])
        self.assertTrue(boundary["first_phase12_candidate_realized"])
        self.assertTrue(boundary["first_phase12_gate_d_transition_accepted"])
        self.assertFalse(boundary["first_phase12_promotion"])
        self.assertEqual(boundary["accepted_phase12_promotions"], 0)
        self.assertFalse(boundary["phase12_exit_closed"])


if __name__ == "__main__":
    unittest.main()
