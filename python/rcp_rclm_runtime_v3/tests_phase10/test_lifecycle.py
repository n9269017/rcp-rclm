from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase10.lifecycle import (
    build_phase10_phase6_fixture,
    replay_phase10_phase6,
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
            detail = (
                report_path.read_text(encoding="utf-8")
                if report_path.is_file()
                else "retained fixture report was not written"
            )
            raise AssertionError(
                f"Phase 10 lifecycle fixture failed: {exc}; retained={detail}"
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
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn(
            "rcp_rclm_runtime_v3.phase10.training_process",
            sys.modules,
        )

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


if __name__ == "__main__":
    unittest.main()
