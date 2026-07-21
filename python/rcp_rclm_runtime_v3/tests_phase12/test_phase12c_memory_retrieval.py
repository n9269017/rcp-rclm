from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase12.phase12c_lifecycle import build_phase12c_reference
from rcp_rclm_runtime_v3.phase12.phase12c_program import (
    PHASE12C_ACCEPTED_PROGRAM_BYTES,
    PHASE12C_INVALID_PROGRAM_BYTES,
)
from rcp_rclm_runtime_v3.phase12.phase12c_tasks import PHASE12C_NEW_TASK_ID


class Phase12CMemoryRetrievalTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12c-tests-")
        cls.root = Path(cls.temporary.name)
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.reference = build_phase12c_reference(
            cls.root / "reference",
            repo_root=cls.repo_root,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_m1_generator_produces_second_rejection_and_fresh_proposal(self) -> None:
        reference = self.reference
        self.assertTrue(reference.invalid_proposal.package_generated)
        self.assertEqual(
            reference.invalid_proposal.program_text.encode("ascii"),
            PHASE12C_INVALID_PROGRAM_BYTES,
        )
        self.assertFalse(reference.invalid_validation.accepted)
        self.assertEqual(
            tuple(reference.invalid_validation.reason_codes),
            ("PHASE12C_COMPONENT_SCHEDULE_INCOMPLETE",),
        )
        self.assertTrue(reference.invalid_proposal.package_unchanged)
        self.assertTrue(reference.proposal.package_generated)
        self.assertEqual(
            reference.proposal.program_text.encode("ascii"),
            PHASE12C_ACCEPTED_PROGRAM_BYTES,
        )
        self.assertTrue(reference.validation.accepted)
        self.assertTrue(reference.deterministic_replays)

    def test_m1_to_m2_changes_memory_and_retrieval_only(self) -> None:
        reference = self.reference
        active = reference.phase12b.semantic_candidate.manifest
        candidate = reference.semantic_candidate.manifest
        self.assertEqual(candidate.model_identity_hash, active.model_identity_hash)
        self.assertNotEqual(candidate.memory_manifest_hash, active.memory_manifest_hash)
        self.assertNotEqual(candidate.retrieval_index_hash, active.retrieval_index_hash)
        self.assertEqual(candidate.generator_policy_hash, active.generator_policy_hash)
        self.assertEqual(candidate.planner_policy_hash, active.planner_policy_hash)
        self.assertEqual(
            set(reference.lifecycle_transition.changed_components),
            {"memory_state", "retrieval_policy"},
        )

    def test_phase6_realization_and_exact_rollback_close(self) -> None:
        reference = self.reference
        self.assertTrue(reference.phase6.accepted)
        self.assertTrue(reference.phase6.memory_projection_matches)
        self.assertTrue(reference.phase6.retrieval_projection_matches)
        realization = reference.phase6.phase6.report.realization
        self.assertIsNotNone(realization)
        if realization is None:
            self.fail("Phase 12C realization is unavailable")
        self.assertTrue(realization.rollback.verified)

    def test_frontier_expands_from_four_to_five(self) -> None:
        reference = self.reference
        before = set(reference.phase12b.semantic_candidate.candidate_state.capability_frontier.task_ids)
        after = set(reference.semantic_candidate.candidate_state.capability_frontier.task_ids)
        self.assertEqual(len(before), 4)
        self.assertEqual(len(after), 5)
        self.assertTrue(before < after)
        self.assertEqual(after - before, {PHASE12C_NEW_TASK_ID})
        self.assertTrue(reference.semantic_candidate.information_report.accepted)
        self.assertTrue(reference.lifecycle_transition.accepted)

    def test_precommitted_progress_is_respected(self) -> None:
        ledger = self.reference.ledger
        self.assertEqual(ledger.generator_invocations, 4)
        self.assertEqual(ledger.rejected_attempts, 2)
        self.assertEqual(ledger.candidate_realizations, 2)
        self.assertEqual(ledger.candidate_evaluations, 2)
        self.assertEqual(ledger.accepted_promotions, 1)
        self.assertEqual(ledger.frontier_expansions, 1)
        self.assertEqual(ledger.manual_repairs, 0)

    def test_phase12c_closes_only_the_second_transition_portable_slice(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        self.assertFalse(summary["heldout_material_consumed"])
        self.assertEqual(summary["manual_repairs"], 0)
        boundary = summary["claim_boundary"]
        self.assertIsInstance(boundary, dict)
        if not isinstance(boundary, dict):
            self.fail("Phase 12C claim boundary is unavailable")
        self.assertTrue(boundary["m1_generator_used_for_authoritative_proposals"])
        self.assertTrue(boundary["second_phase12_rejection_retained"])
        self.assertTrue(boundary["rejection_preserved_m1"])
        self.assertTrue(boundary["m1_to_m2_candidate_realized"])
        self.assertTrue(boundary["m1_to_m2_gate_d_transition_accepted"])
        self.assertFalse(boundary["m1_to_m2_promotion"])
        self.assertFalse(boundary["phase12_exit_closed"])


if __name__ == "__main__":
    unittest.main()
