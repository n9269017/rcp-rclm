from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.generator.grammar import generate_reference_proposal
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.successor.package_builder import (
    build_candidate_package,
    verify_candidate_package,
)
from rcp_rclm_runtime.successor.policies import (
    MEMORY_POLICY_PATH,
    STATE_PATH,
    VERIFICATION_POLICY_PATH,
    baseline_verification_policy,
    policy_bytes,
)
from rcp_rclm_runtime.successor.records import (
    Phase6CandidateManifestRecord,
    Phase6PackageReport,
    Phase6RealizationRecord,
    Phase6ReasonCode,
    Phase6SelectionRecord,
    SelectedFileOperationRecord,
)
from rcp_rclm_runtime.successor.reference import (
    build_reference_predecessor_package,
    reference_phase6_budget,
)
from rcp_rclm_runtime.successor.selector import select_reference_successor
from rcp_rclm_runtime.successor.workspace import (
    Phase6WorkspaceError,
    load_predecessor_package,
    measure_payload_tree,
)


class Phase6SuccessorPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase6-test-")
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _prepared(self, state: str, name: str = "case"):
        request = reference_generator_input(state)
        proposal = generate_reference_proposal(request)
        predecessor_root = build_reference_predecessor_package(
            request,
            self.root / name / "predecessor",
        )
        predecessor = load_predecessor_package(predecessor_root)
        selection = select_reference_successor(request, proposal, predecessor)
        return request, proposal, predecessor_root, predecessor, selection

    def _built(self, state: str, name: str = "case"):
        request, proposal, predecessor_root, predecessor, selection = self._prepared(
            state,
            name,
        )
        evidence = build_candidate_package(
            predecessor_root,
            selection,
            reference_phase6_budget(),
            self.root / name / "candidate",
        )
        self.assertTrue(evidence.report.built, evidence.report.to_json())
        self.assertIsNotNone(evidence.output_root)
        return request, proposal, predecessor, selection, evidence

    def test_initial_selection_changes_state_and_verification_policy(self) -> None:
        _, _, _, _, selection = self._prepared("initial")
        paths = tuple(operation.path for operation in selection.operations)
        self.assertEqual(paths, (VERIFICATION_POLICY_PATH, STATE_PATH))
        self.assertEqual(selection.substantive_component_kinds, ("verification_policy",))

    def test_target_selection_changes_memory_policy_only(self) -> None:
        _, _, _, _, selection = self._prepared("target")
        self.assertEqual(
            tuple(operation.path for operation in selection.operations),
            (MEMORY_POLICY_PATH,),
        )
        self.assertEqual(selection.substantive_component_kinds, ("memory_policy",))

    def test_initial_candidate_records_before_and_after_hashes(self) -> None:
        _, _, _, _, evidence = self._built("initial")
        realization = evidence.report.realization
        self.assertIsNotNone(realization)
        changes = {change.path: change for change in realization.changes}
        self.assertIn(STATE_PATH, changes)
        self.assertIn(VERIFICATION_POLICY_PATH, changes)
        for change in changes.values():
            self.assertIsNotNone(change.before)
            self.assertIsNotNone(change.after)
            self.assertNotEqual(change.before.sha256, change.after.sha256)
        self.assertTrue(changes[VERIFICATION_POLICY_PATH].substantive)
        self.assertFalse(changes[STATE_PATH].substantive)

    def test_target_candidate_preserves_state_and_changes_memory_policy(self) -> None:
        request, _, _, _, evidence = self._built("target")
        candidate_root = evidence.output_root
        self.assertIsNotNone(candidate_root)
        state_bytes = (candidate_root / "payload" / STATE_PATH).read_bytes()
        self.assertEqual(
            state_bytes,
            canonical_json_bytes(request.predecessor.state.to_json()),
        )
        realization = evidence.report.realization
        self.assertEqual(
            tuple(change.path for change in realization.changes),
            (MEMORY_POLICY_PATH,),
        )
        self.assertEqual(realization.substantive_component_kinds, ("memory_policy",))

    def test_commands_environment_and_resources_are_recorded(self) -> None:
        _, _, _, _, evidence = self._built("initial")
        realization = evidence.report.realization
        kinds = tuple(command.command_kind for command in realization.commands)
        self.assertEqual(kinds[0], "copy_payload")
        self.assertEqual(kinds[-1], "build_package")
        self.assertIn("build_rollback", kinds)
        self.assertIn("verify_rollback", kinds)
        self.assertTrue(realization.environment.realizer_policy_id)
        self.assertTrue(realization.resources.within_budget)
        self.assertEqual(
            realization.resources.changed_files,
            len(realization.changes),
        )
        self.assertEqual(realization.resources.commands, len(realization.commands))

    def test_rollback_snapshot_restores_predecessor_tree(self) -> None:
        _, _, predecessor, _, evidence = self._built("initial")
        realization = evidence.report.realization
        self.assertTrue(realization.rollback.verified)
        self.assertEqual(
            realization.rollback.restored_tree_hash,
            predecessor.measurement.tree_hash,
        )
        verified = verify_candidate_package(evidence.output_root)
        self.assertEqual(verified, evidence.report.candidate_manifest)

    def test_strict_records_round_trip(self) -> None:
        _, _, _, selection, evidence = self._built("initial")
        report = evidence.report
        self.assertEqual(Phase6SelectionRecord.from_json(selection.to_json()), selection)
        self.assertEqual(
            Phase6RealizationRecord.from_json(report.realization.to_json()),
            report.realization,
        )
        self.assertEqual(
            Phase6CandidateManifestRecord.from_json(
                report.candidate_manifest.to_json()
            ),
            report.candidate_manifest,
        )
        self.assertEqual(Phase6PackageReport.from_json(report.to_json()), report)

    def test_public_package_verifier_accepts_clean_package(self) -> None:
        _, _, _, _, evidence = self._built("target")
        manifest = verify_candidate_package(evidence.output_root)
        self.assertEqual(
            manifest.manifest_hash,
            evidence.report.candidate_manifest.manifest_hash,
        )

    def test_payload_tampering_is_rejected(self) -> None:
        _, _, _, _, evidence = self._built("initial")
        path = evidence.output_root / "payload" / VERIFICATION_POLICY_PATH
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaises(Phase6WorkspaceError):
            verify_candidate_package(evidence.output_root)

    def test_evidence_tampering_is_rejected(self) -> None:
        _, _, _, _, evidence = self._built("initial")
        (evidence.output_root / "evidence" / "selection.json").write_bytes(b"{}")
        with self.assertRaises(Phase6WorkspaceError):
            verify_candidate_package(evidence.output_root)

    def test_coherent_selection_substitution_is_rejected(self) -> None:
        _, _, predecessor, selection, evidence = self._built("initial")
        original_realization = evidence.report.realization
        original_manifest = evidence.report.candidate_manifest
        by_path = {operation.path: operation for operation in selection.operations}
        before = next(
            record
            for record in predecessor.measurement.records
            if record.path == VERIFICATION_POLICY_PATH
        )
        alternate_policy = baseline_verification_policy()
        semantics = alternate_policy["policy_semantics"]
        self.assertIsInstance(semantics, dict)
        semantics["required_verifiers"] = [
            "phase3_checker",
            "substituted_verifier",
        ]
        forged_operation = SelectedFileOperationRecord.write(
            path=VERIFICATION_POLICY_PATH,
            component_kind="verification_policy",
            expected_before_hash=before.sha256,
            expected_before_mode=before.mode,
            after_mode="0644",
            content=policy_bytes(alternate_policy),
        )
        forged_selection = replace(
            selection,
            operations=(forged_operation, by_path[STATE_PATH]),
        )
        forged_realization = replace(
            original_realization,
            selection_hash=forged_selection.selection_hash,
        )
        forged_manifest = replace(
            original_manifest,
            selection_hash=forged_selection.selection_hash,
        )
        evidence_root = evidence.output_root / "evidence"
        (evidence_root / "selection.json").write_bytes(
            canonical_json_bytes(forged_selection.to_json())
        )
        (evidence_root / "realization.json").write_bytes(
            canonical_json_bytes(forged_realization.to_json())
        )
        (evidence.output_root / "manifest.json").write_bytes(
            canonical_json_bytes(forged_manifest.to_json())
        )
        with self.assertRaises(Phase6WorkspaceError):
            verify_candidate_package(evidence.output_root)

    def test_rollback_archive_tampering_is_rejected(self) -> None:
        _, _, _, _, evidence = self._built("initial")
        archive = evidence.output_root / "rollback" / "predecessor.tar"
        data = bytearray(archive.read_bytes())
        data[len(data) // 2] ^= 1
        archive.write_bytes(bytes(data))
        with self.assertRaises(Phase6WorkspaceError):
            verify_candidate_package(evidence.output_root)

    def test_unknown_package_entry_is_rejected(self) -> None:
        _, _, _, _, evidence = self._built("target")
        (evidence.output_root / "unexpected.txt").write_text(
            "unexpected",
            encoding="utf-8",
        )
        with self.assertRaises(Phase6WorkspaceError):
            verify_candidate_package(evidence.output_root)

    def test_metadata_only_policy_change_is_rejected(self) -> None:
        _, _, predecessor_root, predecessor, selection = self._prepared("initial")
        by_path = {operation.path: operation for operation in selection.operations}
        policy = baseline_verification_policy()
        policy["policy_id"] = "reference.verification.renamed.v1"
        before = next(
            record
            for record in predecessor.measurement.records
            if record.path == VERIFICATION_POLICY_PATH
        )
        metadata_operation = SelectedFileOperationRecord.write(
            path=VERIFICATION_POLICY_PATH,
            component_kind="verification_policy",
            expected_before_hash=before.sha256,
            expected_before_mode=before.mode,
            after_mode="0644",
            content=policy_bytes(policy),
        )
        mutated = replace(
            selection,
            operations=(metadata_operation, by_path[STATE_PATH]),
        )
        evidence = build_candidate_package(
            predecessor_root,
            mutated,
            reference_phase6_budget(),
            self.root / "case" / "metadata-candidate",
        )
        self.assertEqual(evidence.report.verdict, "reject")
        self.assertIn(
            Phase6ReasonCode.METADATA_ONLY_CHANGE,
            evidence.report.reason_codes,
        )

    def test_state_only_successor_is_rejected_by_selection_schema(self) -> None:
        _, _, _, _, selection = self._prepared("initial")
        state_operation = next(
            operation
            for operation in selection.operations
            if operation.path == STATE_PATH
        )
        with self.assertRaises(SchemaValidationError):
            replace(
                selection,
                operations=(state_operation,),
                substantive_component_kinds=(),
            )

    def test_component_kind_cannot_be_attached_to_wrong_path(self) -> None:
        with self.assertRaises(SchemaValidationError):
            SelectedFileOperationRecord.write(
                path=MEMORY_POLICY_PATH,
                component_kind="verification_policy",
                expected_before_hash=None,
                expected_before_mode=None,
                after_mode="0644",
                content=b"{}",
            )

    def test_resource_overflow_is_rejected(self) -> None:
        _, _, predecessor_root, _, selection = self._prepared("initial")
        budget = replace(reference_phase6_budget(), max_written_bytes=1)
        evidence = build_candidate_package(
            predecessor_root,
            selection,
            budget,
            self.root / "case" / "overflow-candidate",
        )
        self.assertEqual(evidence.report.verdict, "reject")
        self.assertIn(
            Phase6ReasonCode.RESOURCE_EXCEEDED,
            evidence.report.reason_codes,
        )

    def test_predecessor_payload_tampering_is_rejected(self) -> None:
        _, _, predecessor_root, _, _ = self._prepared("initial")
        path = predecessor_root / "payload" / MEMORY_POLICY_PATH
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaises(Phase6WorkspaceError):
            load_predecessor_package(predecessor_root)

    def test_existing_candidate_output_is_not_overwritten(self) -> None:
        _, _, predecessor_root, _, selection = self._prepared("initial")
        output = self.root / "case" / "candidate"
        first = build_candidate_package(
            predecessor_root,
            selection,
            reference_phase6_budget(),
            output,
        )
        self.assertTrue(first.report.built)
        marker_hash = first.report.candidate_manifest.manifest_hash
        second = build_candidate_package(
            predecessor_root,
            selection,
            reference_phase6_budget(),
            output,
        )
        self.assertEqual(second.report.verdict, "reject")
        self.assertEqual(
            verify_candidate_package(output).manifest_hash,
            marker_hash,
        )

    def test_hard_link_alias_is_rejected(self) -> None:
        request = reference_generator_input("initial")
        predecessor_root = build_reference_predecessor_package(
            request,
            self.root / "hardlink" / "predecessor",
        )
        source = predecessor_root / "payload" / MEMORY_POLICY_PATH
        alias = predecessor_root / "payload" / "policies" / "memory_alias.json"
        try:
            os.link(source, alias)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        with self.assertRaises(Phase6WorkspaceError):
            measure_payload_tree(predecessor_root / "payload")

    def test_symlink_is_rejected(self) -> None:
        request = reference_generator_input("initial")
        predecessor_root = build_reference_predecessor_package(
            request,
            self.root / "symlink" / "predecessor",
        )
        target = predecessor_root / "payload" / MEMORY_POLICY_PATH
        link = predecessor_root / "payload" / "policies" / "memory_link.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaises(Phase6WorkspaceError):
            measure_payload_tree(predecessor_root / "payload")

    def test_package_construction_is_deterministic_on_one_platform(self) -> None:
        first = self._built("initial", "first")[-1]
        second = self._built("initial", "second")[-1]
        self.assertEqual(
            first.report.candidate_manifest.to_json(),
            second.report.candidate_manifest.to_json(),
        )
        self.assertEqual(
            first.report.realization.to_json(),
            second.report.realization.to_json(),
        )
        self.assertEqual(
            first.report.evidence_hashes.to_json(),
            second.report.evidence_hashes.to_json(),
        )
        self.assertEqual(
            (first.output_root / "rollback" / "predecessor.tar").read_bytes(),
            (second.output_root / "rollback" / "predecessor.tar").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
