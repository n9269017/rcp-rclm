from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.lean_bridge.source_guard import (
    LeanSourceRejected,
    require_clean_source_bytes,
    require_clean_source_file,
    scan_source_bytes,
    scan_source_text,
)


class SourceGuardTests(unittest.TestCase):
    def test_clean_source_is_accepted(self) -> None:
        report = scan_source_text("theorem identity (p : Prop) (h : p) : p := by\n  exact h\n")
        self.assertTrue(report.clean)
        self.assertEqual(report.findings, ())

    def test_each_forbidden_proof_token_is_rejected(self) -> None:
        for token in ("sorry", "sorryAx", "admit"):
            with self.subTest(token=token):
                report = scan_source_text(f"theorem bad : True := by\n  {token}\n")
                self.assertFalse(report.clean)
                self.assertEqual(report.findings[0].token, token)
                self.assertEqual(report.findings[0].line, 2)

    def test_identifier_substrings_do_not_trigger(self) -> None:
        report = scan_source_text(
            "def sorryState : Nat := 0\ndef admittedValue : Nat := sorryState\n"
        )
        self.assertTrue(report.clean)

    def test_project_local_axiom_declaration_is_rejected(self) -> None:
        report = scan_source_text("axiom unsafePremise : Prop\n")
        self.assertFalse(report.clean)
        self.assertEqual(report.findings[0].code, "LEAN_SOURCE_LOCAL_AXIOM")

    def test_invalid_utf8_is_rejected_structurally(self) -> None:
        report = scan_source_bytes(b"\xff\xfe")
        self.assertFalse(report.clean)
        self.assertEqual(report.findings[0].code, "LEAN_SOURCE_INVALID_UTF8")

    def test_require_clean_source_raises_structured_error(self) -> None:
        with self.assertRaises(LeanSourceRejected) as captured:
            require_clean_source_bytes(b"theorem bad : True := by\n  sorry\n")
        self.assertEqual(captured.exception.code, "LEAN_SOURCE_FORBIDDEN_TOKEN")
        self.assertFalse(captured.exception.report.clean)

    def test_file_scan_hashes_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Certificate.lean"
            path.write_text("theorem ok : True := by\n  trivial\n", encoding="utf-8")
            report = require_clean_source_file(path)
            self.assertTrue(report.clean)
            self.assertEqual(report.byte_count, len(path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
