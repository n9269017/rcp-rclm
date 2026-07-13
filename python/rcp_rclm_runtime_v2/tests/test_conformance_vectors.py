from __future__ import annotations

import json
import unittest
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import canonical_json_text
from rcp_rclm_runtime.mathematics.classical import (
    BIASED_BINARY,
    SOURCE_BINARY,
    UNIFORM_BINARY,
    DistributionRecord,
    kl_divergence_interval,
    shannon_entropy_interval,
)
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    SOURCE_DENSITY,
    TARGET_DENSITY,
    quantum_relative_entropy_interval,
)
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence, log_rational_interval
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.schema.candidate import CandidateRecord


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((PACKAGE_ROOT / "tests" / "conformance_vectors.json").read_text(encoding="utf-8"))


class ConformanceVectorTests(unittest.TestCase):
    def test_uniform_distribution_vector(self) -> None:
        vector = VECTORS["vectors"]["uniform_distribution"]
        record = DistributionRecord.from_json(vector["value"])
        self.assertEqual(record, UNIFORM_BINARY)
        self.assertEqual(canonical_json_text(record.to_json()), vector["canonical_json"])
        self.assertEqual(canonical_json_hash(record.to_json()), vector["canonical_hash"])

    def test_quantum_swap_candidate_vector(self) -> None:
        vector = VECTORS["vectors"]["quantum_swap_candidate"]
        candidate = CandidateRecord.from_json(vector["value"])
        self.assertEqual(canonical_json_hash(candidate.to_json()), vector["canonical_hash"])

    def test_log_two_vector(self) -> None:
        vector = VECTORS["vectors"]["log_two_256"]
        computed = log_rational_interval(Rational.from_json(vector["input"]), 256)
        expected = IntervalEvidence.from_json(vector["output"])
        self.assertEqual(computed, expected)
        self.assertEqual(canonical_json_hash(computed.to_json()), vector["canonical_hash"])

    def test_entropy_and_kl_vectors(self) -> None:
        entropy_vector = VECTORS["vectors"]["uniform_entropy_256"]
        entropy = shannon_entropy_interval(UNIFORM_BINARY, 256)
        self.assertEqual(entropy, IntervalEvidence.from_json(entropy_vector["output"]))
        self.assertEqual(canonical_json_hash(entropy.to_json()), entropy_vector["canonical_hash"])

        kl_vector = VECTORS["vectors"]["uniform_to_biased_kl_256"]
        divergence = kl_divergence_interval(UNIFORM_BINARY, BIASED_BINARY, 256)
        self.assertEqual(divergence, IntervalEvidence.from_json(kl_vector["output"]))
        self.assertEqual(canonical_json_hash(divergence.to_json()), kl_vector["canonical_hash"])

    def test_qre_vector(self) -> None:
        vector = VECTORS["vectors"]["source_to_target_qre_256"]
        qre = quantum_relative_entropy_interval(SOURCE_DENSITY, TARGET_DENSITY, 256)
        self.assertEqual(qre, IntervalEvidence.from_json(vector["output"]))
        self.assertEqual(canonical_json_hash(qre.to_json()), vector["canonical_hash"])
        self.assertEqual(qre, kl_divergence_interval(SOURCE_BINARY, BIASED_BINARY, 256))

    def test_semantic_tree_vector(self) -> None:
        vector = VECTORS["vectors"]["semantic_tree"]
        records = tuple(
            SemanticFileRecord(
                path=item["path"],
                mode=item["mode"],
                size=int(item["size"]),
                sha256=item["sha256"],
            )
            for item in vector["records"]
        )
        self.assertEqual(semantic_tree_hash(records), vector["tree_hash"])

    def test_vector_metadata_matches_runtime_contract(self) -> None:
        self.assertEqual(
            VECTORS["contract_version"],
            "rcp-rclm-runtime-contract-v2.0.0",
        )
        self.assertEqual(
            VECTORS["numeric_backend_id"],
            "rcp-rclm-rational-atanh-log-v1",
        )


if __name__ == "__main__":
    unittest.main()
