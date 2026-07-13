from __future__ import annotations

import unittest

from helpers import sample_certificate, sample_rclm_state, sample_rclm_update
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.refinement.mapping import (
    PRESERVED_KERNEL_FIELDS,
    REFINEMENT_MAPPING_ID,
    KernelRefinementRecord,
    RclmCandidateRecord,
    compute_refinement_mapping_evidence,
    forget_rclm_candidate,
    forget_rclm_certificate,
    forget_rclm_state,
    forget_rclm_update,
)
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord


class RefinementMappingTests(unittest.TestCase):
    def test_forgetful_maps_preserve_core_records(self) -> None:
        state = sample_rclm_state()
        update = sample_rclm_update()
        certificate = sample_certificate()
        self.assertEqual(forget_rclm_state(state), state.core)
        self.assertEqual(forget_rclm_update(update), update.core)
        self.assertEqual(forget_rclm_certificate(certificate), certificate.core)

    def test_candidate_forgetting_preserves_update_and_successor(self) -> None:
        update = sample_rclm_update()
        successor = sample_rclm_state()
        successor = type(successor)(
            core=ClassicalBinaryStateRecord("target"),
            language=successor.language,
            world_reference=successor.world_reference,
            human_reference=successor.human_reference,
            definitiveness=successor.definitiveness,
            ambiguity=successor.ambiguity,
            memory=successor.memory,
            verifier=successor.verifier,
            resources=successor.resources,
            self_model=successor.self_model,
        )
        forgotten = forget_rclm_candidate(RclmCandidateRecord(update=update, next=successor))
        self.assertEqual(forgotten.update, update.core)
        self.assertEqual(forgotten.next, successor.core)

    def test_mapping_evidence_hashes_are_recomputed(self) -> None:
        state = sample_rclm_state()
        update = sample_rclm_update()
        certificate = sample_certificate()
        evidence = compute_refinement_mapping_evidence(state, update, certificate)
        self.assertEqual(evidence.mapping_id, REFINEMENT_MAPPING_ID)
        self.assertEqual(evidence.rclm_state_hash, canonical_json_hash(state.to_json()))
        self.assertEqual(evidence.core_state_hash, canonical_json_hash(state.core.to_json()))
        self.assertEqual(evidence.rclm_update_hash, canonical_json_hash(update.to_json()))
        self.assertEqual(evidence.core_update_hash, canonical_json_hash(update.core.to_json()))
        self.assertEqual(evidence.rclm_certificate_hash, canonical_json_hash(certificate.to_json()))
        self.assertEqual(evidence.core_certificate_hash, canonical_json_hash(certificate.core.to_json()))

    def test_kernel_refinement_surface_is_frozen(self) -> None:
        record = KernelRefinementRecord()
        self.assertEqual(record.mapping_id, REFINEMENT_MAPPING_ID)
        self.assertEqual(record.preserved_fields, PRESERVED_KERNEL_FIELDS)
        self.assertEqual(record.to_json()["preserved_fields"], list(PRESERVED_KERNEL_FIELDS))


if __name__ == "__main__":
    unittest.main()
