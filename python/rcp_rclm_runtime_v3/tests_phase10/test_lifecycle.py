from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase10.lifecycle import (
    build_phase10_phase6_fixture,
    phase10_phase6_budget,
    replay_phase10_phase6,
)
from rcp_rclm_runtime_v3.phase10.policy import (
    PHASE10_CONTROLLER_POLICY_ID,
    PHASE10_TRANSPORT_PROFILE,
    phase10_phase7_budget,
    phase10_phase7_policy,
)


class Phase10LifecycleTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase10-lifecycle-tests-"
        )
        cls.root = Path(cls.temporary.name)
        fixture_root = cls.root / "fixture"
        try:
            cls.fixture = build_phase10_phase6_fixture(fixture_root)
        except ValueError as exc:
            report_path = fixture_root / "retained" / "fixture.json"
            phase6_path = fixture_root / "retained" / "phase6_report.json"
            detail = (
                report_path.read_text(encoding="utf-8")
                if report_path.is_file()
                else "retained fixture report was not written"
            )
            phase6_detail = (
                phase6_path.read_text(encoding="utf-8")
                if phase6_path.is_file()
                else "retained Phase 6 report was not written"
            )
            raise AssertionError(
                "Phase 10 lifecycle fixture failed: "
                f"{exc}; retained={detail}; phase6={phase6_detail}"
            ) from exc

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_phase6_realization_and_rollback_accept(self) -> None:
        fixture = self.fixture
        self.assertTrue(fixture.accepted)
        self.assertTrue(fixture.phase6.report.built)
        self.assertIsNotNone(fixture.phase6.report.realization)
        assert fixture.phase6.report.realization is not None
        self.assertTrue(fixture.phase6.report.realization.rollback.verified)
        self.assertGreater(len(fixture.phase6.report.realization.changes), 0)
        self.assertEqual(
            fixture.phase6.report.realization.substantive_component_kinds,
            ("model_weights",),
        )
        self.assertNotEqual(
            fixture.reference.predecessor_manifest.model_identity_hash,
            fixture.reference.candidate_manifest.model_identity_hash,
        )

    def test_generator_free_replay_accepts(self) -> None:
        report = replay_phase10_phase6(
            self.fixture.root,
            self.root / "replayed_candidate",
        )
        self.assertTrue(report["ok"])
        self.assertEqual(report["training_invocations"], 0)
        self.assertEqual(report["generator_invocations"], 0)
        self.assertEqual(report["forbidden_learned_modules_loaded"], [])
        self.assertTrue(report["checks"]["forbidden_training_modules_absent"])

    def test_fixture_round_trip_hashes_are_bound(self) -> None:
        value = self.fixture.to_json()
        self.assertTrue(value["accepted"])
        self.assertEqual(
            value["candidate_model_identity_hash"],
            self.fixture.reference.candidate_manifest.model_identity_hash,
        )
        self.assertEqual(
            value["selection_hash"],
            self.fixture.selection.selection_hash,
        )
        self.assertTrue(value["rollback_verified"])

    def test_phase10_uses_unchanged_reviewed_phase7_transport(self) -> None:
        policy = phase10_phase7_policy()
        budget = phase10_phase7_budget()
        self.assertEqual(policy.policy_id, PHASE10_CONTROLLER_POLICY_ID)
        self.assertEqual(policy.scope, "pytorch_pilot_gate_b_stable")
        self.assertEqual(policy.generator_backend, "pytorch_pilot_process")
        self.assertEqual(policy.selector_backend, "pytorch_pilot_host_selector")
        self.assertEqual(
            policy.evaluator_backend,
            "pytorch_pilot_exact_integer_evaluator",
        )
        self.assertEqual(policy.checker_backend, "phase4_hardened_checker")
        self.assertEqual(budget.phase6_budget, phase10_phase6_budget())
        self.assertEqual(
            PHASE10_TRANSPORT_PROFILE,
            "runtime_v2_pytorch_profile_reused_as_immutable_transport_only",
        )


if __name__ == "__main__":
    unittest.main()
