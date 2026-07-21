from __future__ import annotations

import unittest
from pathlib import Path

from rcp_rclm_runtime_v3.phase11.manifest import (
    load_phase11_manifest,
    validate_phase11_manifest,
)


class Phase11AManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.manifest = load_phase11_manifest(cls.repo_root)
        cls.report = validate_phase11_manifest(cls.repo_root)

    def test_manifest_recomputes_every_stable_reference_hash(self) -> None:
        self.assertTrue(self.report["ok"], self.report["failures"])
        self.assertEqual(
            self.report["observed_reference_hashes"],
            self.manifest["reference_hashes"],
        )

    def test_code_proof_retains_all_platform_artifacts(self) -> None:
        proof = self.manifest["code_proof"]
        self.assertEqual(set(proof["artifacts"]), {"final", "macos", "ubuntu", "windows"})
        self.assertEqual(proof["workflow_run_id"], 29724450584)
        self.assertEqual(
            proof["branch_head"],
            "4d408f4ec6ff62e1b60a6e2344a252d05bc1c9eb",
        )

    def test_phase11a_is_closed_but_full_phase11_remains_open(self) -> None:
        boundary = self.manifest["claim_boundary"]
        self.assertTrue(boundary["active_predecessor_model_generated_proposal"])
        self.assertTrue(boundary["model_generated_proposal_rejected"])
        self.assertTrue(boundary["fresh_model_generated_typed_program_validated"])
        self.assertFalse(boundary["model_generated_candidate_realized"])
        self.assertFalse(boundary["model_generated_candidate_promoted"])
        self.assertFalse(boundary["successor_generator_planner_installed"])
        self.assertFalse(boundary["phase11_exit_closed"])


if __name__ == "__main__":
    unittest.main()
