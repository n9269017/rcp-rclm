from __future__ import annotations

import unittest
from dataclasses import replace

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.contract.records import (
    CapabilityFrontier,
    HeldoutAccessPolicy,
    LearnedCertificatePacket,
    LearnedRCLMState,
    LearnedRCLMUpdate,
)
from rcp_rclm_runtime_v3.contract.reference import build_phase9_reference_fixture
from rcp_rclm_runtime_v3.contract.validation import validate_phase9_transition


class Phase9ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_phase9_reference_fixture()

    def test_reference_accepts(self) -> None:
        self.assertTrue(self.fixture.report.accepted)
        self.assertEqual(self.fixture.report.new_task_ids, ("lean.frontier_one",))
        self.assertEqual(self.fixture.report.changed_components, ("model_weights",))

    def test_strict_round_trips(self) -> None:
        self.assertEqual(
            LearnedRCLMState.from_json(self.fixture.predecessor.to_json()),
            self.fixture.predecessor,
        )
        self.assertEqual(
            LearnedRCLMUpdate.from_json(self.fixture.update.to_json()),
            self.fixture.update,
        )
        self.assertEqual(
            LearnedCertificatePacket.from_json(self.fixture.certificate.to_json()),
            self.fixture.certificate,
        )
        self.assertEqual(
            HeldoutAccessPolicy.from_json(self.fixture.heldout_policy.to_json()),
            self.fixture.heldout_policy,
        )

    def test_frontier_must_expand(self) -> None:
        candidate = replace(
            self.fixture.candidate,
            capability_frontier=CapabilityFrontier(task_ids=("lean.baseline",)),
        )
        update = replace(self.fixture.update, candidate_state_hash=candidate.state_hash)
        certificate = replace(
            self.fixture.certificate,
            candidate_state_hash=candidate.state_hash,
            update_hash=update.update_hash,
            capability_frontier_after_hash=candidate.capability_frontier.frontier_hash,
        )
        report = validate_phase9_transition(
            self.fixture.predecessor,
            update,
            candidate,
            certificate,
            self.fixture.heldout_policy,
        )
        self.assertFalse(report.accepted)
        self.assertIn("PHASE9_FRONTIER_EXPANSION_FAILED", report.reason_codes)

    def test_new_task_must_be_heldout(self) -> None:
        tasks = list(self.fixture.candidate.task_ledger.tasks)
        tasks[1] = replace(tasks[1], partition="training")
        candidate = replace(
            self.fixture.candidate,
            task_ledger=replace(self.fixture.candidate.task_ledger, tasks=tuple(tasks)),
        )
        update = replace(self.fixture.update, candidate_state_hash=candidate.state_hash)
        certificate = replace(
            self.fixture.certificate,
            candidate_state_hash=candidate.state_hash,
            update_hash=update.update_hash,
        )
        report = validate_phase9_transition(
            self.fixture.predecessor,
            update,
            candidate,
            certificate,
            self.fixture.heldout_policy,
        )
        self.assertFalse(report.accepted)
        self.assertIn("PHASE9_HELDOUT_ISOLATION_FAILED", report.reason_codes)

    def test_heldout_answers_never_visible_to_generator(self) -> None:
        with self.assertRaises(SchemaValidationError):
            replace(
                self.fixture.heldout_policy,
                generator_reference_answers_visible=True,
            )

    def test_self_hosting_is_in_state_hash(self) -> None:
        changed_binding = replace(
            self.fixture.predecessor.self_hosting,
            proposal_protocol_hash="0" * 64,
        )
        changed = replace(self.fixture.predecessor, self_hosting=changed_binding)
        self.assertNotEqual(changed.state_hash, self.fixture.predecessor.state_hash)

    def test_generator_update_requires_matching_target(self) -> None:
        with self.assertRaises(SchemaValidationError):
            replace(
                self.fixture.update.operations[0],
                operation_id="0001-generator-update",
                kind="generator_update",
                target="model_weights",
            )

    def test_unknown_field_is_rejected(self) -> None:
        value = self.fixture.predecessor.to_json()
        value["accepted"] = True
        with self.assertRaises(SchemaValidationError):
            LearnedRCLMState.from_json(value)

    def test_state_requires_current_model_certifications(self) -> None:
        certification = replace(
            self.fixture.candidate.task_ledger.certifications[0],
            model_identity_hash="0" * 64,
        )
        with self.assertRaises(SchemaValidationError):
            replace(
                self.fixture.candidate,
                task_ledger=replace(
                    self.fixture.candidate.task_ledger,
                    certifications=(
                        certification,
                        self.fixture.candidate.task_ledger.certifications[1],
                    ),
                ),
            )

    def test_operation_set_must_equal_actual_component_changes(self) -> None:
        policies = replace(
            self.fixture.candidate.policies,
            memory_state_hash="1" * 64,
        )
        candidate = replace(self.fixture.candidate, policies=policies)
        update = replace(self.fixture.update, candidate_state_hash=candidate.state_hash)
        certificate = replace(
            self.fixture.certificate,
            candidate_state_hash=candidate.state_hash,
            update_hash=update.update_hash,
        )
        report = validate_phase9_transition(
            self.fixture.predecessor,
            update,
            candidate,
            certificate,
            self.fixture.heldout_policy,
        )
        self.assertFalse(report.accepted)
        self.assertIn("PHASE9_COMPONENT_CHANGE_MISMATCH", report.reason_codes)


if __name__ == "__main__":
    unittest.main()
