from __future__ import annotations

import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase11.closure_manifest import (
    load_phase11_closure_manifest,
    validate_phase11_closure_manifest,
)


class Phase11ClosureManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.manifest = load_phase11_closure_manifest(cls.repo_root)
        cls.report = validate_phase11_closure_manifest(cls.repo_root)

    def test_manifest_recomputes_portable_lifecycle_hashes(self) -> None:
        self.assertTrue(self.report["ok"], self.report["failures"])
        self.assertEqual(
            self.report["observed_stable_reference_hashes"],
            self.manifest["stable_reference_hashes"],
        )

    def test_code_proof_retains_all_six_artifacts(self) -> None:
        proof = self.manifest["code_proof"]
        self.assertEqual(
            set(proof["artifacts"]),
            {"final", "macos", "pinned", "training", "ubuntu", "windows"},
        )
        self.assertEqual(proof["workflow_run_attempt"], 1)
        self.assertEqual(set(proof["git_trees"]), {"formal_core_v2", "formal_core_v3", "runtime_v3"})

    def test_phase11_closes_without_preclaiming_phase12(self) -> None:
        boundary = self.manifest["claim_boundary"]
        self.assertTrue(boundary["model_generated_candidate_rejection"])
        self.assertTrue(boundary["later_fresh_model_generated_candidate_promoted"])
        self.assertTrue(boundary["successor_generator_planner_installed"])
        self.assertTrue(boundary["phase11_exit_closed"])
        self.assertFalse(boundary["recursive_use_of_modified_successor_generator"])
        self.assertFalse(boundary["generic_successor_availability"])
        self.assertFalse(boundary["autonomous_unbounded_rsi"])


if __name__ == "__main__":
    unittest.main()
