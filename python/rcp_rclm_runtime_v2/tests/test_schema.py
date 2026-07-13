from __future__ import annotations

import unittest

from helpers import sample_certificate, sample_rclm_state, sample_rclm_update
from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema.candidate import CandidateRecord, apply_candidate
from rcp_rclm_runtime.schema.package import PackageManifestRecord
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord, QuantumStateRecord, RclmStateRecord
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    QuantumUpdateRecord,
    RclmUpdateRecord,
)
from rcp_rclm_runtime.schema.verdict import (
    CheckVerdictRecord,
    FrozenHashMap,
    LeanVerifierReportRecord,
    ReasonCode,
)


ZERO_HASH = "0" * 64
ONE_HASH = "1" * 64


class SchemaRecordTests(unittest.TestCase):
    def test_classical_state_and_update_round_trip(self) -> None:
        state = ClassicalBinaryStateRecord("initial")
        update = ClassicalBinaryUpdateRecord("improve")
        self.assertEqual(ClassicalBinaryStateRecord.from_json(state.to_json()), state)
        self.assertEqual(ClassicalBinaryUpdateRecord.from_json(update.to_json()), update)

    def test_quantum_state_and_update_are_canonical(self) -> None:
        source = QuantumStateRecord.canonical("source")
        swap = QuantumUpdateRecord.canonical("swap")
        self.assertEqual(QuantumStateRecord.from_json(source.to_json()), source)
        self.assertEqual(QuantumUpdateRecord.from_json(swap.to_json()), swap)
        bad = source.to_json()
        bad["state"] = "target"
        with self.assertRaises(SchemaValidationError):
            QuantumStateRecord.from_json(bad)

    def test_candidate_scope_and_application(self) -> None:
        predecessor = ClassicalBinaryStateRecord("initial")
        candidate = CandidateRecord(
            ClassicalBinaryUpdateRecord("improve"),
            ClassicalBinaryStateRecord("target"),
        )
        self.assertEqual(apply_candidate(predecessor, candidate), candidate.next)
        with self.assertRaises(SchemaValidationError):
            CandidateRecord(
                ClassicalBinaryUpdateRecord("improve"),
                QuantumStateRecord.canonical("target"),
            )

    def test_rclm_records_round_trip_strictly(self) -> None:
        state = sample_rclm_state()
        update = sample_rclm_update()
        certificate = sample_certificate()
        self.assertEqual(RclmStateRecord.from_json(state.to_json()), state)
        self.assertEqual(RclmUpdateRecord.from_json(update.to_json()), update)
        self.assertEqual(type(certificate).from_json(certificate.to_json()), certificate)
        malformed = state.to_json()
        malformed["extra"] = True
        with self.assertRaises(SchemaValidationError):
            RclmStateRecord.from_json(malformed)

    def test_root_package_manifest_round_trip(self) -> None:
        manifest = PackageManifestRecord(
            package_id="root",
            parent_package_id=None,
            parent_manifest_hash=None,
            semantic_tree_hash=ZERO_HASH,
            candidate_hash=ZERO_HASH,
            certificate_packet_hash=ONE_HASH,
            checker_policy_hash=ZERO_HASH,
            lean_verifier_policy_hash=ZERO_HASH,
            trust_anchor_hash=ZERO_HASH,
            resource_record_hash=ZERO_HASH,
            claim_boundary_hash=ZERO_HASH,
        )
        self.assertEqual(manifest.contract_version, CONTRACT_VERSION)
        self.assertEqual(PackageManifestRecord.from_json(manifest.to_json()), manifest)
        self.assertEqual(manifest.content_hash(), canonical_json_hash(manifest.to_json()))

    def test_package_parent_link_fields_are_atomic(self) -> None:
        with self.assertRaises(SchemaValidationError):
            PackageManifestRecord(
                package_id="child",
                parent_package_id="root",
                parent_manifest_hash=None,
                semantic_tree_hash=ZERO_HASH,
                candidate_hash=ZERO_HASH,
                certificate_packet_hash=ZERO_HASH,
                checker_policy_hash=ZERO_HASH,
                lean_verifier_policy_hash=ZERO_HASH,
                trust_anchor_hash=ZERO_HASH,
                resource_record_hash=ZERO_HASH,
                claim_boundary_hash=ZERO_HASH,
            )

    def test_verdict_rules_are_fail_closed(self) -> None:
        accepted = CheckVerdictRecord(
            verdict="accept",
            reason_codes=(),
            input_hashes=FrozenHashMap.from_mapping({"candidate": ZERO_HASH}, "input"),
            evidence_hashes=FrozenHashMap.from_mapping({"typing": ONE_HASH}, "evidence"),
            checker_implementation_hash=ZERO_HASH,
            lean_verifier_report_hash=ONE_HASH,
        )
        self.assertEqual(CheckVerdictRecord.from_json(accepted.to_json()), accepted)
        with self.assertRaises(SchemaValidationError):
            CheckVerdictRecord(
                verdict="reject",
                reason_codes=(),
                input_hashes=FrozenHashMap(()),
                evidence_hashes=FrozenHashMap(()),
                checker_implementation_hash=ZERO_HASH,
                lean_verifier_report_hash=ZERO_HASH,
            )
        with self.assertRaises(SchemaValidationError):
            CheckVerdictRecord(
                verdict="accept",
                reason_codes=(ReasonCode.INTERNAL_ERROR,),
                input_hashes=FrozenHashMap(()),
                evidence_hashes=FrozenHashMap(()),
                checker_implementation_hash=ZERO_HASH,
                lean_verifier_report_hash=ZERO_HASH,
            )

    def test_lean_verifier_report_requires_clean_success(self) -> None:
        report = LeanVerifierReportRecord(
            verdict="accept",
            source_hash=ZERO_HASH,
            exit_code=0,
            stdout_hash=ZERO_HASH,
            stderr_hash=ZERO_HASH,
        )
        self.assertEqual(LeanVerifierReportRecord.from_json(report.to_json()), report)
        with self.assertRaises(SchemaValidationError):
            LeanVerifierReportRecord(
                verdict="accept",
                source_hash=ZERO_HASH,
                exit_code=1,
                stdout_hash=ZERO_HASH,
                stderr_hash=ZERO_HASH,
            )


if __name__ == "__main__":
    unittest.main()
