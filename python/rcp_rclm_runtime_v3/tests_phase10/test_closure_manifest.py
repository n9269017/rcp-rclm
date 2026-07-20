from __future__ import annotations

import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase10.closure_manifest import (
    load_phase10_closure_manifest,
    validate_phase10_closure_manifest,
)


class Phase10ClosureManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.report = validate_phase10_closure_manifest(cls.repo_root)
        cls.manifest = load_phase10_closure_manifest(cls.repo_root)

    def test_manifest_recomputes_exact_reference_hashes(self) -> None:
        self.assertTrue(self.report["ok"], self.report["failures"])
        self.assertEqual(
            self.report["observed_reference_hashes"],
            self.manifest["reference_hashes"],
        )

    def test_code_proof_retains_every_required_artifact(self) -> None:
        proof = self.manifest["code_proof"]
        self.assertEqual(
            set(proof["artifacts"]),
            {"final", "macos", "pinned", "training", "ubuntu", "windows"},
        )
        self.assertEqual(proof["workflow_run_id"], 29718918742)
        self.assertEqual(
            proof["branch_head"],
            "23a33e4078766b404387d1fa9bb2737c664d9e54",
        )

    def test_full_phase10_boundary_is_closed_but_bounded(self) -> None:
        boundary = self.manifest["claim_boundary"]
        self.assertTrue(boundary["phase10_exit_closed"])
        self.assertTrue(boundary["actual_promoted_learned_successor"])
        self.assertTrue(boundary["independent_replay_without_training"])
        self.assertFalse(boundary["recursive_self_hosting"])
        self.assertFalse(boundary["generic_successor_availability"])
        self.assertFalse(boundary["autonomous_unbounded_rsi"])


if __name__ == "__main__":
    unittest.main()
