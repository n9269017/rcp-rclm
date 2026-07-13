from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from rcp_rclm_runtime._version import CONTRACT_VERSION, FORMAL_SOURCE_COMMIT
from rcp_rclm_runtime.refinement.theorem_surface import (
    PHASE_1_THEOREM_SURFACE,
    theorem_surface_metadata,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class Phase1ManifestTests(unittest.TestCase):
    def test_manifest_preserves_phase_boundary(self) -> None:
        manifest = json.loads((PACKAGE_ROOT / "phase_1_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["contract_version"], CONTRACT_VERSION)
        self.assertEqual(manifest["formal_source_commit"], FORMAL_SOURCE_COMMIT)
        self.assertTrue(manifest["claim_boundary"]["runtime_bedrock_only"])
        self.assertFalse(manifest["claim_boundary"]["candidate_acceptance_licensed"])
        self.assertTrue(manifest["not_implemented"]["production_checker"])
        self.assertTrue(manifest["not_implemented"]["generator"])
        self.assertTrue(manifest["not_implemented"]["pytorch_backend"])

    def test_all_declared_bedrock_components_are_implemented(self) -> None:
        manifest = json.loads((PACKAGE_ROOT / "phase_1_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "canonical_json",
            "content_hashing",
            "gate_b_distributions",
            "gate_b_exact_recovery",
            "gate_b_shannon_entropy",
            "gate_b_support_aware_kl",
            "gate_b_zero_extension",
            "gate_c_basis_swap_channel",
            "gate_c_diagonal_density",
            "gate_c_diagonal_qre",
            "gate_c_exact_selected_recovery",
            "gate_c_identity_channel",
            "gate_c_spectral_entropy",
            "generated_lean_source_guard",
            "immutable_records",
            "rclm_forgetful_mapping",
            "semantic_paths",
            "strict_parsers",
            "tree_hashing",
        }
        self.assertEqual({key for key, value in manifest["implemented"].items() if value}, expected)

    def test_conformance_vector_hash_is_frozen(self) -> None:
        manifest = json.loads((PACKAGE_ROOT / "phase_1_manifest.json").read_text(encoding="utf-8"))
        vector_bytes = (PACKAGE_ROOT / "tests" / "conformance_vectors.json").read_bytes()
        self.assertEqual(
            hashlib.sha256(vector_bytes).hexdigest(),
            manifest["local_validation"]["conformance_vectors_hash"],
        )

    def test_theorem_surface_is_pinned_and_nonempty(self) -> None:
        metadata = theorem_surface_metadata()
        self.assertEqual(metadata["formal_source_commit"], FORMAL_SOURCE_COMMIT)
        self.assertGreaterEqual(len(PHASE_1_THEOREM_SURFACE), 10)
        self.assertTrue(all(entry.phase_1_status for entry in PHASE_1_THEOREM_SURFACE))
        object_ids = [entry.object_id for entry in PHASE_1_THEOREM_SURFACE]
        self.assertEqual(len(object_ids), len(set(object_ids)))


if __name__ == "__main__":
    unittest.main()
