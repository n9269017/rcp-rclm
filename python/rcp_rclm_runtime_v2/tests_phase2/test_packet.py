from __future__ import annotations

import unittest

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.packet import (
    LeanReferencePacket,
    interpret_reference_packet,
    reference_packets,
)


class LeanReferencePacketTests(unittest.TestCase):
    def test_reference_suite_has_declared_accept_reject_balance(self) -> None:
        packets = reference_packets()
        self.assertEqual(len(packets), 10)
        results = [interpret_reference_packet(packet) for packet in packets]
        self.assertEqual(results.count(True), 4)
        self.assertEqual(results.count(False), 6)
        self.assertEqual(len({packet.case_id for packet in packets}), len(packets))

    def test_round_trip_is_strict(self) -> None:
        packet = reference_packets()[0]
        self.assertEqual(LeanReferencePacket.from_json(packet.to_json()), packet)
        malformed = dict(packet.to_json())
        malformed["unexpected"] = True
        with self.assertRaises(SchemaValidationError):
            LeanReferencePacket.from_json(malformed)

    def test_cross_scope_values_are_rejected(self) -> None:
        with self.assertRaises(SchemaValidationError):
            LeanReferencePacket(
                case_id="bad.cross.scope",
                scope="gate_b_classical",
                predecessor="source",
                update="improve",
                successor="target",
                certificate="improvement",
            )


if __name__ == "__main__":
    unittest.main()
