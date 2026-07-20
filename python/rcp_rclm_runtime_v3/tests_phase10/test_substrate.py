from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v3.phase10.adapters import LoRAAdapterManifest
from rcp_rclm_runtime_v3.phase10.architecture import CompactTransformerArchitecture
from rcp_rclm_runtime_v3.phase10.constants import (
    BASE_PARAMETER_COUNT,
    EXTENDED_PARAMETER_COUNT,
    LORA_PARAMETER_COUNT,
)
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    PACKAGE_MANIFEST_PATH,
    TENSOR_MANIFEST_PATH,
    load_package_components,
)
from rcp_rclm_runtime_v3.phase10.reference import build_phase10_reference_fixture
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest
from rcp_rclm_runtime_v3.phase10.tokenizer import (
    ByteTokenizer,
    ByteTokenizerManifest,
    tokenizer_bytes,
    vocabulary_json,
)
from rcp_rclm_runtime_v3.phase10.validation import (
    validate_conservative_extension,
    validate_model_package,
)


class Phase10SubstrateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10-tests-")
        cls.root = Path(cls._temporary.name)
        cls.fixture = build_phase10_reference_fixture(cls.root / "reference")
        cls.predecessor_root = cls.root / "reference" / "predecessor"
        cls.successor_root = cls.root / "reference" / "zero_lora_extension"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def test_fixed_architecture_has_real_compact_parameter_count(self) -> None:
        architecture = CompactTransformerArchitecture()
        self.assertEqual(architecture.base_parameter_count, BASE_PARAMETER_COUNT)
        self.assertEqual(
            sum(item.element_count for item in architecture.base_tensor_blueprints()),
            BASE_PARAMETER_COUNT,
        )
        self.assertGreaterEqual(BASE_PARAMETER_COUNT, 5_000_000)
        self.assertLessEqual(EXTENDED_PARAMETER_COUNT, 50_000_000)
        self.assertEqual(architecture.architecture_hash, "6b00c2df239868a4e7359cd2ee9e0292a9c877d06e893248bb36521450e32a0a")

    def test_frozen_byte_tokenizer_round_trips_lean_and_unicode(self) -> None:
        text = "example (n : Nat) : n = n := by\n  rfl\n-- coherence λ"
        tokens = ByteTokenizer.encode(text, add_bos=True, add_eos=True)
        self.assertEqual(ByteTokenizer.decode(tokens), text)
        manifest = ByteTokenizerManifest.frozen()
        self.assertEqual(manifest.tokenizer_bytes_hash, sha256_hex(tokenizer_bytes()))
        self.assertEqual(manifest.vocabulary_hash, canonical_json_hash(vocabulary_json()))

    def test_reference_packages_and_extension_accept(self) -> None:
        self.assertTrue(self.fixture.accepted)
        self.assertTrue(self.fixture.predecessor_report.accepted)
        self.assertTrue(self.fixture.successor_report.accepted)
        self.assertTrue(self.fixture.extension_report.accepted)
        self.assertEqual(self.fixture.predecessor.parameter_count, BASE_PARAMETER_COUNT)
        self.assertEqual(self.fixture.successor.parameter_count, EXTENDED_PARAMETER_COUNT)
        self.assertEqual(
            self.fixture.successor.parameter_count - self.fixture.predecessor.parameter_count,
            LORA_PARAMETER_COUNT,
        )

    def test_phase9_model_identity_correspondence_is_exact(self) -> None:
        predecessor, _, _, _, _ = load_package_components(self.predecessor_root)
        successor, _, _, _, _ = load_package_components(self.successor_root)
        self.assertEqual(
            predecessor.model_identity().model_identity_hash,
            predecessor.model_identity_hash,
        )
        self.assertEqual(
            successor.model_identity().model_identity_hash,
            successor.model_identity_hash,
        )
        self.assertNotEqual(predecessor.model_identity_hash, successor.model_identity_hash)

    def test_zero_lora_extension_preserves_base_and_recovers_exactly(self) -> None:
        report = validate_conservative_extension(self.predecessor_root, self.successor_root)
        self.assertTrue(report.accepted)
        self.assertTrue(report.architecture_unchanged)
        self.assertTrue(report.base_weights_unchanged)
        self.assertTrue(report.tokenizer_unchanged)
        self.assertTrue(report.all_adapter_b_tensors_zero)
        self.assertTrue(report.at_least_one_adapter_a_tensor_nonzero)
        self.assertTrue(report.adapter_graph_exact)
        self.assertTrue(report.model_hash_changed)
        self.assertTrue(report.recovery_exact)

    def test_tensor_manifest_strict_round_trip(self) -> None:
        value = load_json_strict(
            (self.predecessor_root / TENSOR_MANIFEST_PATH).read_bytes(),
            require_canonical=True,
        )
        manifest = TensorManifest.from_json(value)
        self.assertEqual(manifest.serialized_json(), value)

    def test_adapter_manifest_strict_round_trip(self) -> None:
        value = load_json_strict(
            (self.successor_root / ADAPTER_MANIFEST_PATH).read_bytes(),
            require_canonical=True,
        )
        manifest = LoRAAdapterManifest.from_json(value)
        self.assertEqual(manifest.serialized_json(), value)

    def test_tampered_adapter_b_tensor_is_rejected(self) -> None:
        tampered = self.root / "tampered-adapter"
        shutil.copytree(self.successor_root, tampered)
        _, _, _, _, adapter = load_package_components(tampered)
        b_record = next(record for record in adapter.records if record.spec.role == "adapter_b")
        tensor_path = tampered / b_record.spec.path
        content = bytearray(tensor_path.read_bytes())
        content[0] = 1
        tensor_path.write_bytes(bytes(content))
        package_report = validate_model_package(tampered)
        extension_report = validate_conservative_extension(self.predecessor_root, tampered)
        self.assertFalse(package_report.accepted)
        self.assertFalse(extension_report.accepted)

    def test_unknown_payload_file_is_rejected(self) -> None:
        tampered = self.root / "tampered-extra-file"
        shutil.copytree(self.predecessor_root, tampered)
        (tampered / "model" / "unexpected.bin").write_bytes(b"unexpected")
        report = validate_model_package(tampered)
        self.assertFalse(report.accepted)
        self.assertIn("PHASE10_PAYLOAD_TREE_FAILED", report.reason_codes)
        self.assertIn("PHASE10_PACKAGE_FILE_SET_FAILED", report.reason_codes)

    def test_manifest_native_float_is_not_used(self) -> None:
        value = load_json_strict(
            (self.predecessor_root / PACKAGE_MANIFEST_PATH).read_bytes(),
            require_canonical=True,
        )
        encoded = canonical_json_bytes(value)
        self.assertNotIn(b".", encoded.split(b'"package_id"', 1)[0])
        self.assertNotIn(b"NaN", encoded)
        self.assertNotIn(b"Infinity", encoded)


if __name__ == "__main__":
    unittest.main()
