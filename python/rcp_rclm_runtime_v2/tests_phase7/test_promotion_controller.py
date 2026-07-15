from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.generator.process import (
    GeneratorProcessEvidence,
    run_reference_generator_process,
)
from rcp_rclm_runtime.promotion.controller import run_phase7_promotion_controller
from rcp_rclm_runtime.promotion.evaluator import evaluate_realized_candidate
from rcp_rclm_runtime.promotion.policy import (
    reference_phase7_budget,
    reference_phase7_policy,
)
from rcp_rclm_runtime.promotion.records import (
    Phase7ActivePointerRecord,
    Phase7ControllerPolicyRecord,
    Phase7ControllerReport,
    Phase7ImmutablePackageManifestRecord,
    Phase7LedgerEntryRecord,
    Phase7ReasonCode,
)
from rcp_rclm_runtime.promotion.reference import (
    bootstrap_reference_phase7_store,
    run_reference_phase7_trajectory,
)
from rcp_rclm_runtime.promotion.store import (
    Phase7StoreError,
    Phase7StoreLock,
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.successor.policies import (
    MEMORY_POLICY_PATH,
    VERIFICATION_POLICY_PATH,
)

from phase7_helpers import (
    fixture_indeterminate_lean_evidence,
    fixture_lean_evidence,
    fixture_rejected_lean_evidence,
)


class Phase7PromotionControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase7-test-"
        )
        self.root = Path(self._temporary.name)
        self.policy = reference_phase7_policy()
        self.budget = reference_phase7_budget()

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _store(self, name: str = "store") -> Path:
        store_root = self.root / name
        bootstrap_reference_phase7_store(store_root, state="initial")
        return store_root

    def _promote_once(self, store_root: Path, label: str = "step-0"):
        return run_phase7_promotion_controller(
            store_root,
            fixture_lean_evidence,
            run_label=label,
            policy=self.policy,
            budget=self.budget,
        )

    def test_initial_controller_promotes_verification_policy(self) -> None:
        store_root = self._store()
        before = load_active_phase7_store(store_root, self.policy)
        report = self._promote_once(store_root)
        self.assertTrue(report.promoted, report.to_json())
        after = load_active_phase7_store(store_root, self.policy)
        self.assertNotEqual(
            before.pointer.active_package_hash,
            after.pointer.active_package_hash,
        )
        self.assertEqual(
            after.package_manifest.parent_package_hash,
            before.pointer.active_package_hash,
        )
        self.assertEqual(
            after.package_manifest.substantive_component_kinds,
            ("verification_policy",),
        )
        self.assertEqual(after.predecessor.state.core.state, "target")
        self.assertTrue(
            (
                after.package_root
                / "source_candidate"
                / "payload"
                / VERIFICATION_POLICY_PATH
            ).is_file()
        )

    def test_second_controller_promotes_memory_policy(self) -> None:
        store_root = self._store()
        first = self._promote_once(store_root, "step-0")
        second = self._promote_once(store_root, "step-1")
        self.assertTrue(first.promoted)
        self.assertTrue(second.promoted)
        after = load_active_phase7_store(store_root, self.policy)
        self.assertEqual(
            after.package_manifest.parent_package_hash,
            first.final_pointer.active_package_hash,
        )
        self.assertEqual(
            after.package_manifest.substantive_component_kinds,
            ("memory_policy",),
        )
        self.assertTrue(
            (
                after.package_root
                / "source_candidate"
                / "payload"
                / MEMORY_POLICY_PATH
            ).is_file()
        )

    def test_rejection_retries_under_remaining_fixed_budget(self) -> None:
        store_root = self._store()

        def scripted_generator(request, attempt_index, replay_index):
            base = run_reference_generator_process(request)
            if attempt_index != 0:
                return base
            self.assertIsNotNone(base.proposal)
            invalid = replace(base.proposal, request_hash="0" * 64)
            stdout = canonical_json_bytes(invalid.to_json())
            process_report = replace(
                base.report,
                stdout_hash=sha256_hex(stdout),
                proposal_hash=invalid.proposal_hash,
            )
            return GeneratorProcessEvidence(
                input_bytes=base.input_bytes,
                stdout=stdout,
                stderr=base.stderr,
                source_guard=base.source_guard,
                proposal=invalid,
                report=process_report,
            )

        report = run_phase7_promotion_controller(
            store_root,
            fixture_lean_evidence,
            run_label="retry-then-promote",
            policy=self.policy,
            budget=self.budget,
            generator=scripted_generator,
        )
        self.assertTrue(report.promoted, report.to_json())
        self.assertEqual(len(report.attempts), 2)
        self.assertEqual(report.attempts[0].verdict, "reject")
        self.assertIn(
            Phase7ReasonCode.PROPOSAL_INVALID,
            report.attempts[0].reason_codes,
        )
        self.assertEqual(report.attempts[1].verdict, "accept")
        self.assertEqual(report.units_consumed, 2)

    def test_generator_replay_mismatch_exhausts_without_promotion(self) -> None:
        store_root = self._store()
        before = load_active_phase7_store(store_root, self.policy)

        def mismatching_generator(request, attempt_index, replay_index):
            base = run_reference_generator_process(request)
            if replay_index == 0:
                return base
            self.assertIsNotNone(base.proposal)
            changed = replace(base.proposal, objective_hash="9" * 64)
            stdout = canonical_json_bytes(changed.to_json())
            process_report = replace(
                base.report,
                stdout_hash=sha256_hex(stdout),
                proposal_hash=changed.proposal_hash,
            )
            return GeneratorProcessEvidence(
                input_bytes=base.input_bytes,
                stdout=stdout,
                stderr=base.stderr,
                source_guard=base.source_guard,
                proposal=changed,
                report=process_report,
            )

        report = run_phase7_promotion_controller(
            store_root,
            fixture_lean_evidence,
            run_label="replay-mismatch",
            policy=self.policy,
            budget=self.budget,
            generator=mismatching_generator,
        )
        self.assertEqual(report.verdict, "exhausted")
        self.assertEqual(len(report.attempts), 2)
        self.assertTrue(
            all(
                Phase7ReasonCode.GENERATOR_REPLAY_MISMATCH
                in attempt.reason_codes
                for attempt in report.attempts
            )
        )
        after = load_active_phase7_store(store_root, self.policy)
        self.assertEqual(
            before.pointer.active_package_hash,
            after.pointer.active_package_hash,
        )
        self.assertGreater(
            after.pointer.ledger_sequence_number,
            before.pointer.ledger_sequence_number,
        )

    def test_two_promotions_then_exhausted_rejection_preserves_active_package(self) -> None:
        store_root = self._store()
        self._promote_once(store_root, "step-0")
        self._promote_once(store_root, "step-1")
        before = load_active_phase7_store(store_root, self.policy)
        report = run_phase7_promotion_controller(
            store_root,
            fixture_lean_evidence,
            run_label="expected-exhaustion",
            policy=self.policy,
            budget=self.budget,
        )
        after = load_active_phase7_store(store_root, self.policy)
        self.assertEqual(report.verdict, "exhausted")
        self.assertEqual(len(report.attempts), 2)
        self.assertTrue(all(item.verdict == "reject" for item in report.attempts))
        self.assertEqual(
            before.pointer.active_package_hash,
            after.pointer.active_package_hash,
        )
        self.assertEqual(
            after.pointer.ledger_sequence_number,
            before.pointer.ledger_sequence_number + 2,
        )

    def test_lean_rejection_never_promotes(self) -> None:
        store_root = self._store()
        before = load_active_phase7_store(store_root, self.policy)
        report = run_phase7_promotion_controller(
            store_root,
            fixture_rejected_lean_evidence,
            run_label="lean-reject",
            policy=self.policy,
            budget=self.budget,
        )
        after = load_active_phase7_store(store_root, self.policy)
        self.assertEqual(report.verdict, "exhausted")
        self.assertTrue(
            all(
                Phase7ReasonCode.LEAN_REJECTED in attempt.reason_codes
                for attempt in report.attempts
            )
        )
        self.assertEqual(
            before.pointer.active_package_hash,
            after.pointer.active_package_hash,
        )

    def test_lean_indeterminate_stops_fail_closed(self) -> None:
        store_root = self._store()
        report = run_phase7_promotion_controller(
            store_root,
            fixture_indeterminate_lean_evidence,
            run_label="lean-indeterminate",
            policy=self.policy,
            budget=self.budget,
        )
        self.assertEqual(report.verdict, "indeterminate")
        self.assertEqual(len(report.attempts), 1)
        self.assertEqual(report.attempts[0].verdict, "indeterminate")
        self.assertFalse(report.promoted)

    def test_candidate_tampering_before_evaluation_is_rejected(self) -> None:
        store_root = self._store()
        original = evaluate_realized_candidate

        def tampering_evaluator(predecessor_root, candidate_root, selection):
            policy_path = (
                candidate_root
                / "payload"
                / VERIFICATION_POLICY_PATH
            )
            policy_path.write_bytes(policy_path.read_bytes() + b"\n")
            return original(predecessor_root, candidate_root, selection)

        with patch(
            "rcp_rclm_runtime.promotion.attempt.evaluate_realized_candidate",
            side_effect=tampering_evaluator,
        ):
            report = run_phase7_promotion_controller(
                store_root,
                fixture_lean_evidence,
                run_label="candidate-tamper",
                policy=self.policy,
                budget=self.budget,
            )
        self.assertEqual(report.verdict, "exhausted")
        self.assertTrue(
            all(
                Phase7ReasonCode.EVALUATION_FAILED in attempt.reason_codes
                for attempt in report.attempts
            )
        )

    def test_promoted_package_tampering_is_rejected(self) -> None:
        store_root = self._store()
        self._promote_once(store_root)
        snapshot = load_active_phase7_store(store_root, self.policy)
        target = (
            snapshot.predecessor_root
            / "payload"
            / VERIFICATION_POLICY_PATH
        )
        target.write_bytes(target.read_bytes() + b"\n")
        with self.assertRaises(Phase7StoreError):
            load_active_phase7_store(store_root, self.policy)

    def test_ledger_tampering_is_rejected(self) -> None:
        store_root = self._store()
        report = self._promote_once(store_root)
        ledger = (
            store_root
            / "ledger"
            / f"{report.final_pointer.ledger_head_hash}.json"
        )
        ledger.write_bytes(b"{}")
        with self.assertRaises(Phase7StoreError):
            load_active_phase7_store(store_root, self.policy)

    def test_concurrent_controller_lock_is_rejected(self) -> None:
        store_root = self._store()
        with Phase7StoreLock(store_root, "first"):
            with self.assertRaises(Phase7StoreError) as captured:
                with Phase7StoreLock(store_root, "second"):
                    self.fail("second lock unexpectedly acquired")
        self.assertEqual(
            captured.exception.reason_code,
            Phase7ReasonCode.STORE_LOCKED,
        )

    def test_manual_repair_policy_is_rejected(self) -> None:
        with self.assertRaises(Exception):
            replace(self.policy, allow_manual_repair=True)
        with self.assertRaises(Exception):
            replace(self.policy, allow_candidate_mutation=True)

    def test_controller_and_store_records_round_trip(self) -> None:
        store_root = self._store()
        report = self._promote_once(store_root)
        snapshot = load_active_phase7_store(store_root, self.policy)
        parsed_report = Phase7ControllerReport.from_json(report.to_json())
        parsed_pointer = Phase7ActivePointerRecord.from_json(
            snapshot.pointer.to_json()
        )
        parsed_manifest = Phase7ImmutablePackageManifestRecord.from_json(
            snapshot.package_manifest.to_json()
        )
        parsed_ledger = Phase7LedgerEntryRecord.from_json(
            snapshot.ledger_head.to_json()
        )
        self.assertEqual(parsed_report, report)
        self.assertEqual(parsed_pointer, snapshot.pointer)
        self.assertEqual(parsed_manifest, snapshot.package_manifest)
        self.assertEqual(parsed_ledger, snapshot.ledger_head)

    def test_promoted_package_public_verifier_accepts_clean_package(self) -> None:
        store_root = self._store()
        self._promote_once(store_root)
        snapshot = load_active_phase7_store(store_root, self.policy)
        manifest = verify_immutable_phase7_package(
            snapshot.package_root,
            self.policy,
        )
        self.assertEqual(manifest, snapshot.package_manifest)

    def test_reference_trajectory_closes_two_promotions_and_rejection(self) -> None:
        store_root = self.root / "trajectory"
        evidence = run_reference_phase7_trajectory(
            store_root,
            fixture_lean_evidence,
        )
        self.assertTrue(evidence.all_expectations_met)
        self.assertEqual(len(evidence.exhausted_rejection.attempts), 2)

    def test_deterministic_fresh_stores_produce_identical_reports(self) -> None:
        first_store = self._store("first-store")
        second_store = self._store("second-store")
        first = self._promote_once(first_store, "deterministic")
        second = self._promote_once(second_store, "deterministic")
        self.assertEqual(first.to_json(), second.to_json())
        first_snapshot = load_active_phase7_store(first_store, self.policy)
        second_snapshot = load_active_phase7_store(second_store, self.policy)
        self.assertEqual(
            first_snapshot.package_manifest.to_json(),
            second_snapshot.package_manifest.to_json(),
        )

    def test_every_attempt_records_zero_manual_repairs(self) -> None:
        store_root = self._store()
        report = self._promote_once(store_root)
        self.assertTrue(report.promoted)
        self.assertTrue(
            all(attempt.manual_repair_count == 0 for attempt in report.attempts)
        )
        self.assertTrue(
            all(attempt.fallback_rollback_verified for attempt in report.attempts)
        )


if __name__ == "__main__":
    unittest.main()
