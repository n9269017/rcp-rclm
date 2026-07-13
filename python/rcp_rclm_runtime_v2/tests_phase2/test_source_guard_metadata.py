from __future__ import annotations

import unittest

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.lean_bridge.packet import reference_packets
from rcp_rclm_runtime.lean_bridge.source_guard import (
    SOURCE_GUARD_VERSION,
    LeanSourceRejected,
    require_clean_source_bytes,
    scan_source_bytes,
)
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier


class _UnavailableProject:
    pin_hash = "c" * 64


class _UnavailableCompiler:
    project = _UnavailableProject()

    def compile_source(
        self,
        source: bytes,
        *,
        source_name: str = "generated/reference.lean",
    ) -> object:
        raise RuntimeValidationError(
            "TEST_COMPILER_UNAVAILABLE",
            source_name,
            f"compiler intentionally unavailable for {sha256_hex(source)}",
        )


class SourceGuardMetadataTests(unittest.TestCase):
    def test_rejection_records_path_hash_token_position_and_gate_version(self) -> None:
        source = b"theorem bad : True := by\n  sorry\n"
        source_path = "generated/contract-case.lean"
        report = scan_source_bytes(source, source_path=source_path)

        self.assertFalse(report.clean)
        self.assertEqual(report.source_path, source_path)
        self.assertEqual(report.source_hash, sha256_hex(source))
        self.assertEqual(report.gate_version, SOURCE_GUARD_VERSION)
        self.assertEqual(report.findings[0].token, "sorry")
        self.assertEqual(report.findings[0].line, 2)
        self.assertEqual(report.findings[0].column, 3)

        with self.assertRaises(LeanSourceRejected) as captured:
            require_clean_source_bytes(source, source_path=source_path)
        self.assertEqual(captured.exception.path, source_path)
        self.assertEqual(captured.exception.report, report)
        self.assertIn(SOURCE_GUARD_VERSION, captured.exception.detail)
        self.assertIn(report.source_hash, captured.exception.detail)

    def test_verifier_uses_a_content_addressed_guard_path(self) -> None:
        evidence = LeanReferenceVerifier(_UnavailableCompiler()).verify_with_evidence(
            reference_packets()[0]
        )
        self.assertEqual(
            evidence.source_guard.source_path,
            f"generated/sha256-{evidence.generated.source_hash}.lean",
        )
        self.assertEqual(evidence.source_guard.gate_version, SOURCE_GUARD_VERSION)
        self.assertEqual(evidence.report.bridge_verdict, "indeterminate")
        self.assertIn("TEST_COMPILER_UNAVAILABLE", evidence.report.reason_codes)


if __name__ == "__main__":
    unittest.main()
