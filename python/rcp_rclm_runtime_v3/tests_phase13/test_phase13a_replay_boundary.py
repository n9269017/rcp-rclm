from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase13.constants import PHASE13_ATTACKS
from rcp_rclm_runtime_v3.phase13.reference import build_phase13a_reference


class Phase13AReplayBoundaryTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13a-tests-")
        cls.root = Path(cls.temporary.name)
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.report = build_phase13a_reference(cls.repo_root, cls.root / "reference")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_replay_boundary_is_worker_free(self) -> None:
        report = self.report
        self.assertTrue(report.source_guard.clean)
        self.assertEqual(report.forbidden_modules_loaded, ())
        self.assertEqual(report.forbidden_paths_present, ())
        self.assertEqual(report.counters.training_invocations, 0)
        self.assertEqual(report.counters.generator_invocations, 0)
        self.assertEqual(report.counters.planner_invocations, 0)
        self.assertTrue(report.replay_boundary_closed)

    def test_complete_attack_registry_is_fail_closed(self) -> None:
        suite = self.report.attack_suite
        self.assertEqual(len(suite.results), len(PHASE13_ATTACKS))
        self.assertTrue(suite.all_passed)
        self.assertEqual({item.attack_id for item in suite.results}, {item[0] for item in PHASE13_ATTACKS})

    def test_retained_bundle_excludes_workers(self) -> None:
        manifest = self.report.retained_manifest
        self.assertFalse(manifest.excluded_forbidden_paths)
        self.assertTrue(manifest.files)
        for record in manifest.files:
            self.assertNotIn("training_worker", record.path)
            self.assertNotIn("training_process", record.path)

    def test_phase12_dependency_audit_is_explicit(self) -> None:
        report = self.report
        self.assertEqual(
            report.phase12_dependency_complete,
            not report.phase12_required_paths_missing,
        )
        self.assertGreaterEqual(
            len(report.phase12_required_paths_present) + len(report.phase12_required_paths_missing),
            8,
        )

    def test_phase13a_closes_without_overclaiming_phase13(self) -> None:
        report = self.report
        self.assertTrue(report.phase13a_slice_closed)
        self.assertFalse(report.phase13_exit_closed)
        payload = report.to_json()
        self.assertTrue(payload["phase13a_slice_closed"])
        self.assertFalse(payload["phase13_exit_closed"])
        self.assertEqual(payload["attack_suite"]["case_count"], 21)


if __name__ == "__main__":
    unittest.main()
