from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase11.phase11b_constants import BETA_PROGRAM_BYTES
from rcp_rclm_runtime_v3.phase12.records import Phase12StartReasonCode
from rcp_rclm_runtime_v3.phase12.reference import build_phase12a_reference


class Phase12ARecursiveStartTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12a-tests-")
        cls.root = Path(cls.temporary.name)
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.reference = build_phase12a_reference(
            cls.root / "reference",
            repo_root=cls.repo_root,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_phase11_promoted_semantic_successor_is_bound(self) -> None:
        reference = self.reference
        self.assertTrue(reference.promoted_semantic_binding)
        self.assertTrue(all(reference.promoted_semantic_checks.values()))
        self.assertEqual(
            reference.first_invocation.package_hash,
            reference.phase11.beta_candidate.manifest.package_hash,
        )

    def test_generation2_successor_generator_is_used_recursively(self) -> None:
        reference = self.reference
        self.assertTrue(reference.recursive_successor_use)
        self.assertTrue(reference.first_invocation.model_generated)
        self.assertEqual(
            reference.first_invocation.program_text.encode("ascii"),
            BETA_PROGRAM_BYTES,
        )
        self.assertNotEqual(
            reference.first_invocation.generator_policy_hash,
            reference.phase11.active.active_manifest.generator_policy_hash,
        )
        self.assertNotEqual(
            reference.first_invocation.planner_policy_hash,
            reference.phase11.active.active_manifest.planner_policy_hash,
        )

    def test_first_recursive_attempt_is_rejected_for_stale_generation(self) -> None:
        validation = self.reference.first_validation
        self.assertFalse(validation.accepted)
        self.assertEqual(
            validation.reason_codes,
            (Phase12StartReasonCode.GENERATION_NOT_ADVANCED,),
        )
        self.assertEqual(validation.active_generator_generation, 2)
        self.assertEqual(validation.active_planner_generation, 2)
        self.assertEqual(validation.requested_generator_generation, 2)
        self.assertEqual(validation.requested_planner_generation, 2)

    def test_rejection_is_deterministic_and_non_mutating(self) -> None:
        reference = self.reference
        self.assertTrue(reference.deterministic_replay)
        self.assertTrue(reference.package_unchanged)
        self.assertEqual(
            reference.package_tree_hash_before,
            reference.package_tree_hash_after,
        )

    def test_precommitted_progress_ledger_records_no_promotion(self) -> None:
        ledger = self.reference.ledger
        self.assertEqual(ledger.generator_invocations, 1)
        self.assertEqual(ledger.rejected_attempts, 1)
        self.assertEqual(ledger.candidate_realizations, 0)
        self.assertEqual(ledger.candidate_evaluations, 0)
        self.assertEqual(ledger.accepted_promotions, 0)
        self.assertEqual(ledger.frontier_expansions, 0)
        self.assertEqual(ledger.manual_repairs, 0)
        self.assertEqual(ledger.target_frontier_cardinality, 7)

    def test_phase12a_closes_only_the_recursive_start_slice(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        self.assertFalse(summary["first_validation_accepted"])
        self.assertFalse(summary["heldout_material_consumed"])
        self.assertEqual(summary["manual_repairs"], 0)
        boundary = summary["claim_boundary"]
        self.assertTrue(boundary["phase12_begun"])
        self.assertTrue(boundary["generation2_successor_generator_used_recursively"])
        self.assertTrue(boundary["first_phase12_model_generated_attempt_rejected"])
        self.assertTrue(boundary["rejection_preserved_active_package"])
        self.assertEqual(boundary["accepted_phase12_promotions"], 0)
        self.assertFalse(boundary["four_promotion_chain_complete"])
        self.assertFalse(boundary["phase12_exit_closed"])


if __name__ == "__main__":
    unittest.main()
