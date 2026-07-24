from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase10.constants import EXTENDED_PARAMETER_COUNT
from rcp_rclm_runtime_v3.phase12.phase12e_lifecycle import build_phase12e_reference
from rcp_rclm_runtime_v3.phase12.phase12e_program import PHASE12E_ACCEPTED_PROGRAM_BYTES
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import PHASE12E_NEW_TASK_ID
from rcp_rclm_runtime_v3.phase12.phase12e_training_binding import (
    build_phase12e_training_binding,
    load_phase12e_training_binding,
)


class Phase12ECompleteTrajectoryTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12e-tests-")
        cls.root = Path(cls.temporary.name)
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.reference = build_phase12e_reference(
            cls.root / "reference",
            repo_root=cls.repo_root,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_m3_generation3_authority_produces_final_program(self) -> None:
        reference = self.reference
        self.assertTrue(reference.proposal.package_generated)
        self.assertTrue(reference.proposal.model_draft.model_generated)
        self.assertEqual(
            reference.proposal.program_text.encode("ascii"),
            PHASE12E_ACCEPTED_PROGRAM_BYTES,
        )
        self.assertTrue(reference.validation.accepted)
        self.assertTrue(reference.deterministic_replay)
        self.assertEqual(
            tuple(reference.proposal.program.selected_update_classes),
            ("adapter_update", "architecture_extension", "optimizer_policy_update"),
        )

    def test_m3_to_m4_changes_selected_architecture_surface(self) -> None:
        reference = self.reference
        active = reference.phase12d.semantic_candidate.manifest
        candidate = reference.semantic_candidate.manifest
        self.assertNotEqual(candidate.model_identity_hash, active.model_identity_hash)
        self.assertNotEqual(candidate.adapter_manifest_hash, active.adapter_manifest_hash)
        self.assertNotEqual(candidate.optimizer_state_hash, active.optimizer_state_hash)
        self.assertEqual(candidate.parameter_count, EXTENDED_PARAMETER_COUNT)
        self.assertEqual(candidate.generator_policy_hash, active.generator_policy_hash)
        self.assertEqual(candidate.planner_policy_hash, active.planner_policy_hash)
        self.assertEqual(candidate.memory_manifest_hash, active.memory_manifest_hash)
        self.assertEqual(candidate.retrieval_index_hash, active.retrieval_index_hash)
        self.assertEqual(
            set(reference.lifecycle_transition.changed_components),
            {"adapter_manifest", "model_architecture", "optimizer_policy"},
        )

    def test_phase6_realization_and_exact_rollback_close(self) -> None:
        reference = self.reference
        self.assertTrue(reference.phase6.accepted)
        self.assertTrue(reference.phase6.adapter_projection_matches)
        self.assertTrue(reference.phase6.optimizer_projection_matches)
        realization = reference.phase6.phase6.report.realization
        self.assertIsNotNone(realization)
        if realization is None:
            self.fail("Phase 12E realization is unavailable")
        self.assertTrue(realization.rollback.verified)

    def test_frontier_expands_from_six_to_seven(self) -> None:
        reference = self.reference
        before = set(
            reference.phase12d.semantic_candidate.candidate_state.capability_frontier.task_ids
        )
        after = set(reference.semantic_candidate.candidate_state.capability_frontier.task_ids)
        self.assertEqual(len(before), 6)
        self.assertEqual(len(after), 7)
        self.assertTrue(before < after)
        self.assertEqual(after - before, {PHASE12E_NEW_TASK_ID})
        self.assertTrue(reference.semantic_candidate.information_report.accepted)
        self.assertTrue(reference.lifecycle_transition.accepted)

    def test_final_precommitted_progress_is_respected(self) -> None:
        ledger = self.reference.ledger
        self.assertEqual(ledger.generator_invocations, 6)
        self.assertEqual(ledger.rejected_attempts, 2)
        self.assertEqual(ledger.candidate_realizations, 4)
        self.assertEqual(ledger.candidate_evaluations, 4)
        self.assertEqual(ledger.accepted_promotions, 3)
        self.assertEqual(ledger.frontier_expansions, 3)
        self.assertEqual(ledger.manual_repairs, 0)

    def test_retained_training_binding_matches_portable_reference(self) -> None:
        summary = self.reference.summary_json()
        expected = build_phase12e_training_binding(summary)
        binding_path = (
            Path(__file__).resolve().parents[1]
            / "rcp_rclm_runtime_v3"
            / "phase12"
            / "phase12e_training_binding.json"
        )
        observed = load_phase12e_training_binding(binding_path, summary=summary)
        self.assertEqual(observed, expected)
        self.assertEqual(
            observed["semantic_candidate_tensor_hash"],
            "eca5b8e8f126965047155360b96a796265c24c323ad038e04d455f6be12b84ab",
        )

    def test_portable_boundary_waits_for_atomic_promotion(self) -> None:
        summary = self.reference.summary_json()
        self.assertTrue(summary["accepted"])
        self.assertFalse(summary["heldout_material_consumed"])
        self.assertEqual(summary["manual_repairs"], 0)
        self.assertEqual(len(summary["frontier_before"]), 6)
        self.assertEqual(len(summary["frontier_after"]), 7)
        boundary = summary["claim_boundary"]
        self.assertIsInstance(boundary, dict)
        if not isinstance(boundary, dict):
            self.fail("Phase 12E claim boundary is unavailable")
        self.assertTrue(boundary["m3_generator_used_for_authoritative_proposal"])
        self.assertTrue(boundary["m3_to_m4_candidate_realized"])
        self.assertTrue(boundary["m3_to_m4_gate_d_transition_accepted"])
        self.assertTrue(boundary["trained_lora_adapter_installed"])
        self.assertFalse(boundary["m3_to_m4_promotion"])
        self.assertFalse(boundary["phase12_exit_closed"])


if __name__ == "__main__":
    unittest.main()
