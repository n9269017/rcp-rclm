from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PATH = PACKAGE_ROOT / "phase_2_validation.json"
VALIDATOR_PATH = PACKAGE_ROOT / "tools" / "validate_phase2_release.py"


class Phase2ReleaseEvidenceTests(unittest.TestCase):
    def test_committed_release_evidence_is_accepted(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH), str(VALIDATION_PATH)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["workflow_run"], 29287943656)
        self.assertEqual(
            report["validated_implementation_head"],
            "01319d8be6c4025fb32092588e4f021a60596652",
        )

    def test_mutated_claim_boundary_is_rejected(self) -> None:
        value = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
        value["claim_boundary"]["candidate_acceptance_licensed"] = True
        temporary_path = PACKAGE_ROOT / "phase_2_validation.mutated.test.json"
        temporary_path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        try:
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), str(temporary_path)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        finally:
            temporary_path.unlink(missing_ok=True)
        self.assertNotEqual(completed.returncode, 0)
        report = json.loads(completed.stdout)
        self.assertFalse(report["ok"])


if __name__ == "__main__":
    unittest.main()
