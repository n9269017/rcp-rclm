from __future__ import annotations

import unittest

from rcp_rclm_runtime.canonical.json import canonical_json_text
from rcp_rclm_runtime.lean_bridge.packet import reference_packets
from rcp_rclm_runtime.lean_bridge.source_generator import (
    LEAN_VERDICT_MARKER_PREFIX,
    LEAN_VERDICT_SCHEMA_ID,
    SOURCE_GENERATOR_VERSION,
    generate_reference_source,
)
from rcp_rclm_runtime.lean_bridge.verdict_parser import (
    LeanVerdictParseError,
    parse_lean_reference_verdict,
)


class LeanVerdictParserTests(unittest.TestCase):
    def test_structured_marker_is_parsed_amid_other_output(self) -> None:
        packet = reference_packets()[0]
        generated = generate_reference_source(packet)
        payload = canonical_json_text(
            {
                "schema_id": LEAN_VERDICT_SCHEMA_ID,
                "case_id": packet.case_id,
                "scope": packet.scope,
                "rcp_accepted": generated.expected_acceptance,
                "rclm_accepted": generated.expected_acceptance,
                "packet_hash": packet.packet_hash,
                "theorem_surface_hash": generated.theorem_surface_hash,
                "source_generator_version": SOURCE_GENERATOR_VERSION,
            }
        )
        stdout = (
            "RcpRclmFormalCoreV2 theorem surface\n"
            + LEAN_VERDICT_MARKER_PREFIX
            + payload
            + "\n"
        ).encode("utf-8")
        verdict = parse_lean_reference_verdict(stdout)
        self.assertEqual(verdict.case_id, packet.case_id)
        self.assertTrue(verdict.rcp_accepted)
        self.assertTrue(verdict.rclm_accepted)
        self.assertTrue(verdict.layers_agree)

    def test_missing_and_duplicate_markers_fail_closed(self) -> None:
        with self.assertRaises(LeanVerdictParseError):
            parse_lean_reference_verdict(b"no marker\n")
        marker = LEAN_VERDICT_MARKER_PREFIX + "{}\n"
        with self.assertRaises(LeanVerdictParseError):
            parse_lean_reference_verdict((marker + marker).encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
