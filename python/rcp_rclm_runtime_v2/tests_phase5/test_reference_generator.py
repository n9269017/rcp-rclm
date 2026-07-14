from __future__ import annotations

import unittest
from dataclasses import replace

from phase5_helpers import accepting_lean_report
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.source_guard import scan_source_bytes
from rcp_rclm_runtime.schema._common import thaw_json
from rcp_rclm_runtime.generator.lean_conformance import reference_grammar_lean_source
from rcp_rclm_runtime.generator.pipeline import (
    finalize_reference_transition,
    prepare_reference_transition,
)
from rcp_rclm_runtime.generator.process import (
    run_reference_generator_process,
    run_reference_generator_replay,
)
from rcp_rclm_runtime.generator.records import GeneratorReasonCode
from rcp_rclm_runtime.generator.reference import (
    build_reference_generator_input,
    reference_generator_policy,
)
from rcp_rclm_runtime.generator.sandbox import (
    REFERENCE_WORKER_AUDIT_POLICY_VERSION,
    audit_denial_reason,
)


class Phase5ReferenceGeneratorProcessTests(unittest.TestCase):
    def test_initial_predecessor_generates_improvement_only(self) -> None:
        generator_input = build_reference_generator_input("initial")
        observation = run_reference_generator_process(generator_input)
        self.assertEqual(observation.status, "generated")
        self.assertIsNotNone(observation.response)
        self.assertIsNotNone(observation.response.proposal)
        proposal = observation.response.proposal
        self.assertEqual(proposal.word, "improve")
        self.assertEqual(proposal.witness, "strict_improvement")
        self.assertEqual(proposal.proposal, "improve")
        self.assertEqual(proposal.word_depth, 1)
        self.assertEqual(proposal.proof_length, 1)
        self.assertNotIn("certificate", proposal.to_json())
        self.assertNotIn("candidate", proposal.to_json())
        self.assertNotIn("successor", proposal.to_json())
        self.assertNotIn("accepted", proposal.to_json())

    def test_target_predecessor_generates_stability_only(self) -> None:
        generator_input = build_reference_generator_input("target")
        replay = run_reference_generator_replay(generator_input)
        self.assertEqual(replay.status, "generated")
        self.assertIsNotNone(replay.proposal)
        self.assertEqual(replay.proposal.word, "stabilize")
        self.assertEqual(replay.proposal.witness, "stable_continuation")
        self.assertEqual(replay.proposal.resource_units, 0)

    def test_outside_predecessor_is_rejected(self) -> None:
        replay = run_reference_generator_replay(
            build_reference_generator_input("outside")
        )
        self.assertEqual(replay.status, "reject")
        self.assertIn(
            GeneratorReasonCode.PREDECESSOR_OUTSIDE_DOMAIN,
            replay.reason_codes,
        )
        self.assertIsNone(replay.proposal)

    def test_insufficient_resource_budget_is_rejected(self) -> None:
        replay = run_reference_generator_replay(
            build_reference_generator_input("initial", resource_units=0)
        )
        self.assertEqual(replay.status, "reject")
        self.assertIn(GeneratorReasonCode.BUDGET_EXCEEDED, replay.reason_codes)

    def test_open_ended_policy_is_rejected_in_phase_5a(self) -> None:
        generator_input = build_reference_generator_input("initial")
        policy = replace(
            reference_generator_policy(),
            open_ended_generation_allowed=True,
        )
        mutated = replace(generator_input, policy=policy)
        replay = run_reference_generator_replay(mutated)
        self.assertEqual(replay.status, "reject")
        self.assertIn(GeneratorReasonCode.POLICY_MISMATCH, replay.reason_codes)

    def test_process_replay_is_byte_deterministic(self) -> None:
        generator_input = build_reference_generator_input("initial")
        replay = run_reference_generator_replay(generator_input)
        self.assertTrue(replay.deterministic)
        self.assertEqual(replay.first.stdout_hash, replay.second.stdout_hash)
        self.assertEqual(
            replay.first.response.response_hash,
            replay.second.response.response_hash,
        )
        self.assertEqual(replay.first.stderr_hash, replay.second.stderr_hash)

    def test_worker_records_forbidden_capabilities_as_absent(self) -> None:
        observation = run_reference_generator_process(
            build_reference_generator_input("initial")
        )
        sandbox = observation.response.sandbox
        self.assertEqual(
            sandbox.audit_policy_version,
            REFERENCE_WORKER_AUDIT_POLICY_VERSION,
        )
        self.assertEqual(sandbox.file_write_probe, "denied")
        self.assertEqual(sandbox.network_probe, "denied")
        self.assertEqual(sandbox.subprocess_probe, "denied")
        self.assertFalse(sandbox.checker_input_present)
        self.assertFalse(sandbox.trust_anchor_present)
        self.assertFalse(sandbox.previous_manifest_history_present)
        self.assertFalse(sandbox.promotion_ledger_present)
        self.assertFalse(sandbox.reference_answer_present)

    def test_worker_audit_denies_all_filesystem_reads_and_writes(self) -> None:
        self.assertEqual(
            audit_denial_reason("open", ("probe", "rb", 0)),
            "filesystem_access_denied",
        )
        self.assertEqual(
            audit_denial_reason("open", ("probe", "wb", 1)),
            "filesystem_access_denied",
        )

    def test_input_schema_contains_only_declared_read_only_inputs(self) -> None:
        value = build_reference_generator_input("initial").to_json()
        self.assertEqual(
            set(value),
            {
                "schema_id",
                "contract_version",
                "predecessor_package",
                "policy",
                "objective",
                "resource_budget",
            },
        )
        for forbidden in (
            "checker_source",
            "trust_anchor",
            "previous_manifests",
            "promotion_ledger",
            "reference_answers",
        ):
            self.assertNotIn(forbidden, value)

    def test_unknown_control_plane_field_is_rejected(self) -> None:
        generator_input = build_reference_generator_input("initial")
        value = generator_input.to_json()
        value["trust_anchor"] = {"forged": True}
        with self.assertRaises(SchemaValidationError):
            type(generator_input).from_json(value)


class Phase5ReferencePipelineTests(unittest.TestCase):
    def test_generated_grammar_source_is_clean_and_binds_exact_words(self) -> None:
        source = reference_grammar_lean_source()
        report = scan_source_bytes(
            source,
            source_path="generated/Phase5AReferenceGrammarConformance.lean",
        )
        self.assertTrue(report.clean)
        text = source.decode("utf-8")
        self.assertIn("initialBoundedSeedPacket.word", text)
        self.assertIn("targetBoundedSeedPacket.word", text)
        self.assertIn("boundedWordDepth", text)
        self.assertIn("boundedProofLength", text)
        self.assertIn("BoundedPacketWord.rejected ∉", text)

    def test_initial_pipeline_constructs_and_accepts_without_manual_successor(self) -> None:
        generator_input = build_reference_generator_input("initial")
        prepared = prepare_reference_transition(generator_input)
        self.assertEqual(prepared.proposal.word, "improve")
        self.assertEqual(prepared.selection.update.core.update, "improve")
        self.assertEqual(prepared.realization.candidate.next.core.state, "target")
        self.assertEqual(
            prepared.realization.predecessor_state_hash,
            canonical_json_hash(generator_input.predecessor_package.state.to_json()),
        )
        self.assertEqual(
            thaw_json(
                prepared.certificate_construction.certificate.core.value
            )["certificate"],
            "improvement",
        )
        report = finalize_reference_transition(
            prepared,
            accepting_lean_report(prepared),
        )
        self.assertTrue(report.accepted)
        self.assertEqual(report.verdict, "accept")
        self.assertEqual(report.reason_codes, ())
        self.assertTrue(report.hardened_checker_report.accepted)
        self.assertTrue(report.generator_replay.deterministic)

    def test_target_pipeline_constructs_stability_and_accepts(self) -> None:
        generator_input = build_reference_generator_input("target")
        prepared = prepare_reference_transition(generator_input)
        self.assertEqual(prepared.proposal.word, "stabilize")
        self.assertEqual(prepared.selection.update.core.update, "stay")
        self.assertEqual(prepared.realization.candidate.next.core.state, "target")
        report = finalize_reference_transition(
            prepared,
            accepting_lean_report(prepared),
        )
        self.assertTrue(report.accepted)
        self.assertEqual(report.hardened_checker_report.verdict, "accept")

    def test_pipeline_is_repeatable_before_lean_verification(self) -> None:
        generator_input = build_reference_generator_input("initial")
        first = prepare_reference_transition(generator_input)
        second = prepare_reference_transition(generator_input)
        self.assertEqual(first.proposal.to_json(), second.proposal.to_json())
        self.assertEqual(
            first.certificate_construction.to_json(),
            second.certificate_construction.to_json(),
        )
        self.assertEqual(first.selection.to_json(), second.selection.to_json())
        self.assertEqual(first.realization.to_json(), second.realization.to_json())
        self.assertEqual(first.lean_packet.to_json(), second.lean_packet.to_json())


if __name__ == "__main__":
    unittest.main()
