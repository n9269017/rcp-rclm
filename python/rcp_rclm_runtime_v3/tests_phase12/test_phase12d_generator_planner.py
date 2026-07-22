from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase12.phase12d_lifecycle import build_phase12d_reference
from rcp_rclm_runtime_v3.phase12.phase12d_program import (
    PHASE12D_ACCEPTED_PROGRAM_BYTES,
    PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
    PHASE12D_SUCCESSOR_PLANNER_GENERATION,
)
from rcp_rclm_runtime_v3.phase12.phase12d_tasks import (
    PHASE12D_NEW_TASK_ID,
    PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
)


class Phase12DGeneratorPlannerTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12d-tests-")
        cls.root = Path(cls.temporary.name)
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.reference = build_phase12d_reference(
            cls.root / "reference",
            repo_root=cls.repo_root,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_m2_generator_produces_generation3_self_modification(self) -> None:
        reference = self.reference
        self.assertTrue(reference.proposal.package_generated)
        self.assertEqual(
            reference.proposal.program_text.encode("ascii"),
            PHASE12D_ACCEPTED_PROGRAM_BYTES,
        )
        self.assertTrue(reference.validation.accepted)
        self.assertTrue(reference.deterministic_replay)
        self.assertEqual(
            reference.proposal.program.successor_generator_generation,
            PHASE12D_SUCCESSOR_GENERATOR_GENERATION,
        )
        self.assertEqual(
            reference.proposal.program.successor_planner_generation,
            PHASE12D_SUCCESSOR_PLANNER_GENERATION,
        )

    def test_m2_to_m3_changes_generator_and_planner_only(self) -> None:
        reference = self.reference
        active = reference.phase12c.semantic_candidate.manifest
        candidate = reference.semantic_candidate.manifest
        self.assertEqual(candidate.model_identity_hash, active.model_identity_hash)
        self.assertEqual(candidate.memory_manifest_hash, active.memory_manifest_hash)
        self.assertEqual(candidate.retrieval_index_hash, active.retrieval_index_hash)
        self.assertNotEqual(candidate.generator_policy_hash, active.generator_policy_hash)
        self.assertNotEqual(candidate.planner_policy_hash, active.planner_policy_hash)
        self.assertEqual(
            set(reference.lifecycle_transition.changed_components),
            {"generator_policy", "planner_policy"},
        )
        self.assertEqual(
            reference.semantic_candidate.candidate_state.self_hosting.proposal_protocol_hash,
            PHASE12D_NEXT_PROPOSAL_PROTOCOL_HASH,
        )

    def test_phase6_realization_and_exact_rollback_close(self) -> None:
        reference = self.reference
        self.assertTrue(reference.phase6.accepted)
        self.assertTrue(reference.phase6.generator_projection_matches)
        self.assertTrue(reference.phase6.planner_projection_matches)
        realization = reference.phase6.phase6.report.realization
        self.assertIsNotNone(realization)
        if realization is None:
            self.fail("Phase 12D realization is unavailable")
        self.assertTrue(realization.rollback.verified)

    def test_frontier_expands_from_five_to_six(self) -> None:
        reference = self.reference
        before = set(
            reference.phase12c.semantic_candidate.candidate_state.capability_frontier.task_ids
        )
        after = set(reference.semantic_candidate.candidate_state.capability_frontier.task_ids)
        self.assertEqual(len(before), 5)
        self.assertEqual(len(after), 6)
        self.assertTrue(before < after)
        self.assertEqual(after - before, {PHASE12D_NEW_TASK_ID})
        self.assertTrue(reference.semantic_candidate.information_report.accepted)
        self.assertTrue(reference.lifecycle_transition.accepted)

    def test_precommitted_progress_is_respected(self) -> None:
        ledger = self.reference.ledger
        self.assertEqual(ledger.generator_invocations, 5)
        self.assertEqual(ledger.rejected_attempts, 2)
        self.assertEqual(ledger.candidate_realizations, 3)
        self.assertEqual(ledger.candidate_evaluations, 3)
        self.assertEqual(ledger.accepted_promotions, 2)
        self.assertEqual(ledger.frontier_expansions, 2)
        self.assertEqual(ledger.manual_repairs, 0)

    def test_phase12d_closes_only_the_third_transition_portable_slice(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        self.assertFalse(summary["heldout_material_consumed"])
        self.assertEqual(summary["manual_repairs"], 0)
        boundary = summary["claim_boundary"]
        self.assertIsInstance(boundary, dict)
        if not isinstance(boundary, dict):
            self.fail("Phase 12D claim boundary is unavailable")
        self.assertTrue(boundary["m2_generator_used_for_authoritative_proposal"])
        self.assertTrue(boundary["m2_to_m3_candidate_realized"])
        self.assertTrue(boundary["m2_to_m3_gate_d_transition_accepted"])
        self.assertTrue(boundary["generation3_generator_installed"])
        self.assertTrue(boundary["generation3_planner_installed"])
        self.assertFalse(boundary["m2_to_m3_promotion"])
        self.assertFalse(boundary["phase12_exit_closed"])


if __name__ == "__main__":
    unittest.main()
