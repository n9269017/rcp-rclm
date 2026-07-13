from __future__ import annotations

import unittest

from rcp_rclm_runtime.lean_bridge.packet import reference_packets
from rcp_rclm_runtime.lean_bridge.source_generator import generate_reference_source
from rcp_rclm_runtime.lean_bridge.source_guard import scan_source_bytes


class LeanSourceGeneratorTests(unittest.TestCase):
    def test_generation_is_deterministic_and_guard_clean(self) -> None:
        for packet in reference_packets():
            first = generate_reference_source(packet)
            second = generate_reference_source(packet)
            self.assertEqual(first.source_text, second.source_text)
            self.assertEqual(first.source_hash, second.source_hash)
            self.assertTrue(scan_source_bytes(first.source_bytes).clean)
            self.assertIn(packet.case_id, first.source_text)
            self.assertIn("#eval IO.println", first.source_text)
            self.assertIn("namespace RCPReference", first.source_text)
            self.assertIn("namespace RCLMReference", first.source_text)
            self.assertGreaterEqual(len(first.theorem_surface), 6)

    def test_scope_specific_imports_are_emitted(self) -> None:
        classical = generate_reference_source(reference_packets()[0]).source_text
        quantum = generate_reference_source(reference_packets()[5]).source_text
        self.assertIn("RCP.ClassicalBinary", classical)
        self.assertIn("RCLM.ClassicalBinary", classical)
        self.assertIn("RCP.QuantumFinite", quantum)
        self.assertIn("RCLM.QuantumBinary", quantum)


if __name__ == "__main__":
    unittest.main()
