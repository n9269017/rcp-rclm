from __future__ import annotations

import json
import unittest
from pathlib import Path

from rcp_rclm_runtime._version import CONTRACT_VERSION, LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.lean_bridge.packet import reference_packets


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class Phase2ManifestTests(unittest.TestCase):
    def test_manifest_preserves_bridge_boundary(self) -> None:
        manifest = json.loads((PACKAGE_ROOT / "phase_2_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["contract_version"], CONTRACT_VERSION)
        self.assertEqual(manifest["lean_toolchain"], LEAN_TOOLCHAIN)
        self.assertEqual(manifest["mathlib_commit"], MATHLIB_COMMIT)
        self.assertTrue(manifest["claim_boundary"]["reference_bridge_only"])
        self.assertFalse(manifest["claim_boundary"]["candidate_acceptance_licensed"])
        self.assertTrue(manifest["not_implemented"]["production_checker"])
        self.assertTrue(manifest["not_implemented"]["generator"])
        self.assertTrue(manifest["bridge"]["rcp_and_rclm_checks_required"])
        self.assertTrue(manifest["bridge"]["formal_source_git_pin_required"])

    def test_manifest_case_count_matches_closed_reference_grammar(self) -> None:
        manifest = json.loads((PACKAGE_ROOT / "phase_2_manifest.json").read_text(encoding="utf-8"))
        packets = reference_packets()
        self.assertEqual(manifest["bridge"]["case_count"], len(packets))
        self.assertEqual(
            manifest["bridge"]["reference_accepting_cases"],
            sum(
                1
                for packet in packets
                if packet.case_id.startswith("gate_b.accept")
                or packet.case_id.startswith("gate_c.accept")
            ),
        )


if __name__ == "__main__":
    unittest.main()
