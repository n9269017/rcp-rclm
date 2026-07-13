from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    build_tree_records,
    canonical_json_hash,
    file_record_from_bytes,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import (
    canonical_json_bytes,
    canonical_json_text,
    load_json_strict,
)
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import CanonicalizationError


class CanonicalizationTests(unittest.TestCase):
    def test_unicode_is_normalized_to_nfc(self) -> None:
        decomposed = "e\u0301"
        composed = "\u00e9"
        self.assertEqual(canonical_json_text({"value": decomposed}), canonical_json_text({"value": composed}))

    def test_object_keys_are_sorted_and_whitespace_free(self) -> None:
        self.assertEqual(canonical_json_bytes({"z": 1, "a": True}), b'{"a":true,"z":1}')

    def test_duplicate_keys_and_native_float_are_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            load_json_strict(b'{"a":1,"a":2}', require_canonical=False)
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes({"value": 1.5})

    def test_noncanonical_json_bytes_are_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            load_json_strict(b'{ "a": 1 }', require_canonical=True)
        self.assertEqual(load_json_strict(b'{"a":1}', require_canonical=True), {"a": 1})

    def test_semantic_path_attacks_are_rejected(self) -> None:
        invalid = (
            "",
            "/absolute",
            "C:/drive",
            "../escape",
            "a/./b",
            "a//b",
            "a\\b",
            "//server/share",
        )
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(CanonicalizationError):
                    validate_semantic_path(path)
        self.assertEqual(validate_semantic_path("safe/path.txt"), "safe/path.txt")

    def test_canonical_hash_matches_frozen_uniform_vector(self) -> None:
        value = {
            "schema_id": "gate_b.distribution.v2",
            "dimension": 2,
            "masses": [
                {"numerator": "1", "denominator": "2"},
                {"numerator": "1", "denominator": "2"},
            ],
        }
        self.assertEqual(
            canonical_json_hash(value),
            "8fc8b1f129f0ad63ecb3d857d3dc6b1a8dc3fb4bca59dcfd0f697bd4c0bf0d9e",
        )

    def test_tree_hash_is_order_independent(self) -> None:
        first = file_record_from_bytes("alpha.txt", "0644", b"alpha\n")
        second = file_record_from_bytes("bin/run.py", "0755", b"#!/usr/bin/env python3\n")
        expected = "adc80e042b0040b54cbdb7e72bba4c31188d979f50368b60d747caf4f2c1fb92"
        self.assertEqual(semantic_tree_hash((first, second)), expected)
        self.assertEqual(semantic_tree_hash((second, first)), expected)

    def test_duplicate_tree_paths_are_rejected(self) -> None:
        record = SemanticFileRecord(
            path="a.txt",
            mode="0644",
            size=1,
            sha256="ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        )
        with self.assertRaises(CanonicalizationError):
            semantic_tree_hash((record, record))

    def test_filesystem_tree_records_use_declared_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sub").mkdir()
            (root / "a.txt").write_bytes(b"a")
            (root / "sub" / "run.py").write_bytes(b"print(1)\n")
            records = build_tree_records(
                root,
                declared_modes={"a.txt": "0644", "sub/run.py": "0755"},
            )
            self.assertEqual([record.path for record in records], ["a.txt", "sub/run.py"])
            self.assertEqual([record.mode for record in records], ["0644", "0755"])


if __name__ == "__main__":
    unittest.main()
