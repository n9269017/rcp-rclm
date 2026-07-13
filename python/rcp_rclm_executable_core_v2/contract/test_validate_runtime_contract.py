from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import validate_runtime_contract as contract


class ContractValidatorTests(unittest.TestCase):
    def test_git_blob_sha1_matches_known_empty_blob(self) -> None:
        self.assertEqual(
            contract.git_blob_sha1(b""),
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
        )

    def test_canonical_json_bytes_are_sorted_and_compact(self) -> None:
        value: contract.JsonValue = {"z": 1, "a": [True, None, "é"]}
        self.assertEqual(
            contract.canonical_json_bytes(value),
            '{"a":[true,null,"é"],"z":1}'.encode("utf-8"),
        )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(contract.DuplicateKeyError):
                contract.load_json_strict(path)

    def test_clean_generated_lean_source_passes_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Clean.lean"
            path.write_text(
                "def value : Nat := 1\ntheorem value_eq : value = 1 := by rfl\n",
                encoding="utf-8",
            )
            self.assertEqual(contract.scan_lean_source(path, True), ())

    def test_forbidden_lean_token_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Forbidden.lean"
            path.write_text("theorem invalid : True := by sorry\n", encoding="utf-8")
            issues = contract.scan_lean_source(path, True)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].code, "LEAN_FORBIDDEN_TOKEN")

    def test_local_axiom_is_rejected_for_generated_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Axiom.lean"
            path.write_text("axiom fabricated : True\n", encoding="utf-8")
            issues = contract.scan_lean_source(path, True)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].code, "LEAN_LOCAL_AXIOM")

    def test_report_json_is_valid(self) -> None:
        report = contract.ValidationReport(
            ok=True,
            contract_version=contract.CONTRACT_VERSION,
            manifest_path="manifest.json",
            schema_path="schema.json",
            mapped_object_count=25,
            scanned_lean_file_count=0,
            issues=(),
        )
        parsed = json.loads(contract.report_to_json(report))
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["issues"], [])


if __name__ == "__main__":
    unittest.main()
