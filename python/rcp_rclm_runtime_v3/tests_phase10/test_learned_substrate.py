from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    LEARNED_CHAIN,
    PROTECTED_CHAIN,
    PROTECTED_TASK,
)
from rcp_rclm_runtime_v3.phase10.learned_reference import (
    build_phase10_learned_reference,
)
from rcp_rclm_runtime_v3.phase10.learned_package import validate_learned_package
from rcp_rclm_runtime_v3.phase10.sparse_profile import (
    decode_completion,
    transition_tensor_path,
)
from rcp_rclm_runtime_v3.phase10.training_process import (
    default_worker_source,
    inspect_worker_source,
)
from rcp_rclm_runtime_v3.phase10.training_protocol import expected_trained_tensor


class Phase10LearnedSubstrateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10b-tests-")
        cls.root = Path(cls.temporary.name) / "reference"
        cls.fixture = build_phase10_learned_reference(cls.root)
        cls.predecessor_root = cls.root / "predecessor"
        cls.candidate_root = cls.root / "candidate"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_learned_reference_accepts(self) -> None:
        self.assertTrue(self.fixture.accepted)
        self.assertTrue(self.fixture.transition_report.accepted)
        self.assertTrue(self.fixture.information_report.accepted)

    def test_predecessor_and_candidate_generate_selected_lean_text(self) -> None:
        predecessor_protected = decode_completion(
            self.predecessor_root, PROTECTED_TASK.model_prompt
        )
        predecessor_heldout = decode_completion(
            self.predecessor_root, HELDOUT_TASK.model_prompt
        )
        candidate_protected = decode_completion(
            self.candidate_root, PROTECTED_TASK.model_prompt
        )
        candidate_heldout = decode_completion(
            self.candidate_root, HELDOUT_TASK.model_prompt
        )
        self.assertEqual(predecessor_protected.completion_text, "rfl")
        self.assertTrue(predecessor_protected.stopped_on_eos)
        self.assertNotEqual(predecessor_heldout.completion_text, "omega")
        self.assertEqual(candidate_protected.completion_text, "rfl")
        self.assertEqual(candidate_heldout.completion_text, "omega")
        self.assertTrue(candidate_heldout.stopped_on_eos)

    def test_frontier_retains_protected_and_adds_heldout(self) -> None:
        self.assertEqual(
            self.fixture.predecessor_state.capability_frontier.task_ids,
            (PROTECTED_TASK.task_id,),
        )
        self.assertEqual(
            self.fixture.candidate_state.capability_frontier.task_ids,
            tuple(sorted((HELDOUT_TASK.task_id, PROTECTED_TASK.task_id))),
        )
        self.assertEqual(self.fixture.transition_report.new_task_ids, (HELDOUT_TASK.task_id,))

    def test_update_set_matches_actual_semantic_component_changes(self) -> None:
        self.assertEqual(
            tuple(operation.target for operation in self.fixture.update.operations),
            (
                "adapter_manifest",
                "data_curriculum",
                "model_weights",
                "optimizer_policy",
            ),
        )
        self.assertEqual(
            self.fixture.transition_report.changed_components,
            (
                "adapter_manifest",
                "data_curriculum",
                "model_weights",
                "optimizer_policy",
            ),
        )

    def test_protected_qre_does_not_regress_and_heldout_strictly_improves(self) -> None:
        report = self.fixture.information_report
        self.assertTrue(report.protected_nonregression)
        self.assertTrue(report.strict_information_witness)
        self.assertEqual(report.protected_regression_interval.lower.numerator, 0)
        self.assertEqual(report.protected_regression_interval.upper.numerator, 0)
        self.assertTrue(report.heldout_improvement_interval.strictly_positive())

    def test_host_exact_training_recomputation_matches_packages(self) -> None:
        zero_tensor = bytes(320 * 320 * 2)
        bootstrap = expected_trained_tensor(zero_tensor, self.fixture.bootstrap_request)
        predecessor = transition_tensor_path(self.predecessor_root).read_bytes()
        self.assertEqual(bootstrap, predecessor)
        successor = expected_trained_tensor(predecessor, self.fixture.successor_request)
        candidate = transition_tensor_path(self.candidate_root).read_bytes()
        self.assertEqual(successor, candidate)

    def test_heldout_material_is_absent_from_training_requests(self) -> None:
        for request in (self.fixture.bootstrap_request, self.fixture.successor_request):
            value = request.to_json()
            self.assertFalse(value["heldout_task_ids_present"])
            self.assertFalse(value["heldout_prompts_present"])
            self.assertFalse(value["heldout_reference_answers_present"])
            serialized = str(value)
            self.assertNotIn(HELDOUT_TASK.task_id, serialized)
            self.assertNotIn(HELDOUT_TASK.expected_completion_hash, serialized)

    def test_worker_source_guard_is_clean(self) -> None:
        guard = inspect_worker_source(default_worker_source())
        self.assertTrue(guard.clean)
        self.assertIn("torch", guard.imported_roots)

    def test_tensor_tampering_is_rejected(self) -> None:
        tensor_path = transition_tensor_path(self.candidate_root)
        original = tensor_path.read_bytes()
        mutated = bytearray(original)
        mutated[0] ^= 1
        tensor_path.write_bytes(bytes(mutated))
        try:
            report = validate_learned_package(
                self.candidate_root,
                tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN})),
            )
            self.assertFalse(report["accepted"])
        finally:
            tensor_path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
