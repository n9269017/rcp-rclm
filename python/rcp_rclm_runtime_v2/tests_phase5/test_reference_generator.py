from __future__ import annotations

import unittest
from dataclasses import replace

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord
from rcp_rclm_runtime.checker.reference import canonical_rclm_state
from rcp_rclm_runtime.generator.grammar import (
    generate_reference_proposal,
    validate_untrusted_proposal,
)
from rcp_rclm_runtime.generator.process import (
    guard_reference_worker_source,
    run_reference_generator_process,
    scan_generator_source_bytes,
)
from rcp_rclm_runtime.generator.protocol import (
    GeneratorPredecessorViewRecord,
    ReferenceGeneratorInputRecord,
    ReferenceProposalRecord,
)
from rcp_rclm_runtime.generator.reference import reference_generator_input


class Phase5AReferenceGeneratorTests(unittest.TestCase):
    def test_initial_state_generates_only_bounded_improvement_word(self) -> None:
        request = reference_generator_input("initial")
        proposal = generate_reference_proposal(request)
        self.assertEqual(proposal.word, "improve")
        self.assertEqual(proposal.witness, "strict_improvement")
        self.assertEqual(proposal.proposal, "improve")
        self.assertEqual(proposal.word_depth, 1)
        self.assertEqual(proposal.proof_length, 1)
        self.assertEqual(proposal.budget_units_used, 1)

    def test_target_state_generates_only_bounded_stability_word(self) -> None:
        request = reference_generator_input("target")
        proposal = generate_reference_proposal(request)
        self.assertEqual(proposal.word, "stabilize")
        self.assertEqual(proposal.witness, "stable_continuation")
        self.assertEqual(proposal.proposal, "stabilize")
        self.assertEqual(proposal.budget_units_used, 0)

    def test_generator_output_contains_no_certificate_successor_or_verdict(self) -> None:
        proposal_json = generate_reference_proposal(
            reference_generator_input("initial")
        ).to_json()
        forbidden = {
            "accepted",
            "candidate",
            "certificate",
            "certificate_preserved",
            "next",
            "reality_containment",
            "strict_improvement",
            "successor",
            "verdict",
        }
        self.assertTrue(forbidden.isdisjoint(proposal_json))

    def test_unknown_privileged_input_fields_are_rejected(self) -> None:
        for field in (
            "checker_source",
            "promotion_ledger",
            "reference_answers",
            "trust_anchor",
            "previous_manifests",
        ):
            with self.subTest(field=field):
                value = reference_generator_input("initial").to_json()
                value[field] = {"forbidden": True}
                with self.assertRaises(SchemaValidationError):
                    ReferenceGeneratorInputRecord.from_json(value)

    def test_outside_state_is_not_in_the_bounded_seed_domain(self) -> None:
        outside = canonical_rclm_state(ClassicalBinaryStateRecord("outside"))
        with self.assertRaises(SchemaValidationError):
            GeneratorPredecessorViewRecord(
                package_id="outside",
                manifest_hash="0" * 64,
                semantic_tree_hash="1" * 64,
                state_hash=canonical_json_hash(outside.to_json()),
                state=outside,
            )

    def test_tampered_untrusted_proposal_is_rejected(self) -> None:
        request = reference_generator_input("initial")
        proposal = generate_reference_proposal(request)
        tampered = replace(proposal, proposal="stabilize")
        result = validate_untrusted_proposal(request, tampered)
        self.assertEqual(result.status, "fail")

    def test_generator_output_rejects_hidden_acceptance_fields(self) -> None:
        value = generate_reference_proposal(
            reference_generator_input("initial")
        ).to_json()
        value["accepted"] = True
        with self.assertRaises(SchemaValidationError):
            ReferenceProposalRecord.from_json(value)

    def test_worker_source_guard_is_clean(self) -> None:
        report = guard_reference_worker_source()
        self.assertTrue(report.clean)
        self.assertEqual(report.findings, ())
        self.assertGreaterEqual(len(report.file_hashes.entries), 4)

    def test_worker_source_guard_rejects_file_and_network_capabilities(self) -> None:
        file_findings = scan_generator_source_bytes(
            "synthetic_file.py",
            b"def write():\n    open('candidate', 'w')\n",
        )
        network_findings = scan_generator_source_bytes(
            "synthetic_network.py",
            b"import socket\n",
        )
        self.assertEqual(file_findings[0].code, "GENERATOR_FORBIDDEN_CALL")
        self.assertEqual(network_findings[0].code, "GENERATOR_FORBIDDEN_IMPORT")

    def test_worker_source_guard_rejects_privileged_runtime_imports(self) -> None:
        findings = scan_generator_source_bytes(
            "synthetic_checker_import.py",
            b"from rcp_rclm_runtime.checker import aggregate\n",
        )
        self.assertEqual(findings[0].code, "GENERATOR_PRIVILEGED_IMPORT")

    def test_worker_source_guard_rejects_dynamic_module_table_access(self) -> None:
        findings = scan_generator_source_bytes(
            "synthetic_module_table.py",
            b"import sys\nvalue = sys.modules\n",
        )
        self.assertEqual(findings[0].code, "GENERATOR_FORBIDDEN_ATTRIBUTE_READ")

    def test_worker_source_guard_rejects_dynamic_getattr_escape(self) -> None:
        findings = scan_generator_source_bytes(
            "synthetic_dynamic_getattr.py",
            b"import sys\nvalue = getattr(sys, 'modules')\n",
        )
        self.assertEqual(findings[0].code, "GENERATOR_FORBIDDEN_CALL")

    def test_separate_process_is_deterministic(self) -> None:
        request = reference_generator_input("initial")
        first = run_reference_generator_process(request)
        second = run_reference_generator_process(request)
        self.assertEqual(first.report.verdict, "success")
        self.assertEqual(second.report.verdict, "success")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, second.stderr)
        self.assertEqual(first.proposal, second.proposal)
        self.assertEqual(first.report.to_json(), second.report.to_json())
        self.assertEqual(first.report.input_hash, canonical_json_hash(request.to_json()))


if __name__ == "__main__":
    unittest.main()
