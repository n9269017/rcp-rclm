from __future__ import annotations

import copy
import unittest
from dataclasses import replace

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.gatee.records import RouteHintPolicy
from rcp_rclm_runtime_v4.phase14.attacks import (
    Phase14AttackResult,
    Phase14AttackSuiteReport,
)
from rcp_rclm_runtime_v4.phase14.bundle import (
    Phase14BundleFile,
    Phase14BundleManifest,
)
from rcp_rclm_runtime_v4.phase14.challenges import (
    DEVELOPMENT_CHALLENGE_SEED,
    answer_store_json,
    challenge_manifest_json,
    challenge_suite_from_seed,
    challenges_from_answer_store,
)
from rcp_rclm_runtime_v4.phase14.closure import Phase14ClosureReport
from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH,
    PHASE14_OBJECTIVE_ID,
    PHASE14_ROUTE_MARKER,
    UPDATE_KINDS_BY_FAMILY,
)
from rcp_rclm_runtime_v4.phase14.records import (
    Phase14AttemptSummary,
    Phase14MutationProgram,
    Phase14SearchHistory,
    Phase14SearchHistoryEntry,
)
from rcp_rclm_runtime_v4.phase14.replay import Phase14ReplayReport
from rcp_rclm_runtime_v4.phase14.trajectory import Phase14TrajectoryReport


def _hash(label: str) -> str:
    return canonical_json_hash({"phase14_test": label})


def _program() -> Phase14MutationProgram:
    challenge = challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)[0]
    family = "model_weights"
    return Phase14MutationProgram(
        active_semantic_package_hash=_hash("active-package"),
        active_model_identity_hash=_hash("active-model"),
        active_generator_hash=_hash("active-generator"),
        active_planner_hash=_hash("active-planner"),
        challenge_commitment_hash=challenge.commitment_hash,
        history_hash=Phase14SearchHistory(entries=()).history_hash,
        objective_id=PHASE14_OBJECTIVE_ID,
        update_family=family,
        variant="probe",
        slot_token_id=challenge.slot_token_id,
        route_marker_token_id=challenge.slot_token_id,
        update_kinds=tuple(
            sorted(UPDATE_KINDS_BY_FAMILY[family], key=lambda item: item.encode("utf-8"))
        ),
        search_cost=1,
    )


def _attempt(index: int, verdict: str, family: str, rejection_conditioned: bool) -> Phase14AttemptSummary:
    before = _hash(f"store-before-{index}")
    after = before if verdict == "reject" else _hash(f"store-after-{index}")
    return Phase14AttemptSummary(
        global_attempt_index=index,
        challenge_index=min(index, 3),
        challenge_commitment_hash=_hash(f"challenge-{min(index, 3)}"),
        local_attempt_index=0,
        update_family=family,  # type: ignore[arg-type]
        program_variant=("probe" if verdict == "reject" else ("recover" if rejection_conditioned else "direct")),
        program_hash=_hash(f"program-{index}"),
        proposal_enumeration_hash=_hash(f"enumeration-{index}"),
        candidate_semantic_package_hash=_hash(f"candidate-{index}"),
        candidate_phase6_tree_hash=_hash(f"phase6-{index}"),
        verdict=verdict,
        reason_codes=() if verdict == "accept" else ("PHASE14_TEST_REJECTION",),
        hidden_task_report_hash=_hash(f"hidden-{index}"),
        gate_d_report_hash=_hash(f"gate-d-{index}"),
        gate_e_report_hash=_hash(f"gate-e-{index}"),
        recursive_productivity_report_hash=_hash(f"recursive-{index}"),
        active_store_package_hash_before=before,
        active_store_package_hash_after=after,
        phase7_ledger_entry_hash=_hash(f"ledger-{index}"),
        rejection_conditioned=rejection_conditioned,
    )


def _trajectory() -> Phase14TrajectoryReport:
    attempts = (
        _attempt(0, "reject", "model_weights", False),
        _attempt(1, "accept", "memory_retrieval", True),
        _attempt(2, "reject", "adapter_optimizer", False),
        _attempt(3, "accept", "generator_planner", True),
        _attempt(4, "accept", "model_weights", False),
        _attempt(5, "accept", "adapter_optimizer", False),
    )
    initial = tuple(f"task.{index}" for index in range(7))
    final = (*initial, "task.7", "task.8", "task.9", "task.10")
    return Phase14TrajectoryReport(
        source_head="1" * 40,
        source_tree="2" * 40,
        phase13_exit_report_hash=_hash("phase13-exit"),
        phase13_bundle_manifest_hash=_hash("phase13-bundle"),
        initial_store_package_hash=_hash("initial-store"),
        initial_m4_semantic_package_hash=PHASE14_EXPECTED_M4_SEMANTIC_PACKAGE_HASH,
        final_store_package_hash=_hash("final-store"),
        final_semantic_package_hash=_hash("final-semantic"),
        initial_capability_frontier=initial,
        final_capability_frontier=final,
        initial_recursive_productivity_frontier=("recursive.generate",),
        final_recursive_productivity_frontier=("recursive.generate", "recursive.recover"),
        attempts=attempts,
        challenge_manifest_hash=_hash("manifest"),
        answer_store_hash=_hash("answers"),
        challenge_count=4,
        challenge_gate_e_report_hashes=tuple(_hash(f"gate-e-report-{i}") for i in range(4)),
        challenge_gate_e_validation_hashes=tuple(_hash(f"gate-e-validation-{i}") for i in range(4)),
    )


def _replay(platform: str, pinned: bool = True) -> Phase14ReplayReport:
    trajectory = _trajectory()
    return Phase14ReplayReport(
        source_head=trajectory.source_head,
        source_tree=trajectory.source_tree,
        platform_id=platform,
        bundle_manifest_hash=_hash("bundle"),
        trajectory_report_hash=trajectory.report_hash,
        final_store_package_hash=trajectory.final_store_package_hash,
        final_semantic_package_hash=trajectory.final_semantic_package_hash,
        history_count=len(trajectory.attempts),
        accepted_promotions=4,
        rejected_attempts=2,
        distinct_update_families=trajectory.substantive_update_families,
        task_replays=20,
        gate_d_replays=4,
        gate_e_replays=4,
        outer_replays=4,
        immutable_packages_verified=9,
        pinned_lean=pinned,
        forbidden_worker_modules=(),
    )


class Phase14ContractTests(unittest.TestCase):
    def test_dynamic_challenge_suite_is_deterministic(self) -> None:
        first = challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)
        second = challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(len({item.slot_token_id for item in first}), 4)
        self.assertEqual([item.probe_required for item in first], [True, True, False, False])
        self.assertTrue(all("expected_family" not in item.private_json() for item in first))

    def test_commitment_manifest_discloses_no_private_route(self) -> None:
        manifest = challenge_manifest_json(
            challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)
        )
        text = repr(manifest)
        self.assertNotIn("theorem_statement", text)
        self.assertNotIn("expected_family", text)
        self.assertFalse(manifest["successful_route_disclosed"])

    def test_answer_store_round_trip(self) -> None:
        challenges = challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)
        store = answer_store_json(challenges)
        self.assertEqual(challenges_from_answer_store(store), challenges)

    def test_answer_store_substitution_rejects(self) -> None:
        challenges = challenge_suite_from_seed(DEVELOPMENT_CHALLENGE_SEED)
        store = copy.deepcopy(answer_store_json(challenges))
        answers = store["answers"]
        assert isinstance(answers, list)
        assert isinstance(answers[0], dict)
        answers[0]["challenge_commitment_hash"] = _hash("forged")
        with self.assertRaises(SchemaValidationError):
            challenges_from_answer_store(store)

    def test_program_round_trip(self) -> None:
        program = _program()
        self.assertEqual(Phase14MutationProgram.from_json(program.to_json()), program)

    def test_direct_program_requires_certified_m4_route_marker(self) -> None:
        probe = _program()
        direct = replace(
            probe,
            variant="direct",
            route_marker_token_id=PHASE14_ROUTE_MARKER,
        )
        self.assertEqual(Phase14MutationProgram.from_json(direct.to_json()), direct)
        with self.assertRaises(SchemaValidationError):
            replace(direct, route_marker_token_id=direct.slot_token_id)

    def test_manual_repair_rejects(self) -> None:
        with self.assertRaises(SchemaValidationError):
            replace(_program(), manual_repair_count=1)

    def test_heldout_visibility_rejects(self) -> None:
        with self.assertRaises(SchemaValidationError):
            replace(_program(), heldout_material_visible=True)

    def test_route_hint_rejects(self) -> None:
        with self.assertRaises(SchemaValidationError):
            RouteHintPolicy(expected_candidate_hash_present=True)

    def test_rejection_must_preserve_active_pointer(self) -> None:
        with self.assertRaises(SchemaValidationError):
            Phase14SearchHistoryEntry(
                sequence_number=0,
                challenge_commitment_hash=_hash("challenge"),
                attempt_index=0,
                update_family="model_weights",
                program_variant="probe",
                program_hash=_hash("program"),
                candidate_semantic_package_hash=_hash("candidate"),
                verdict="reject",
                reason_codes=("REJECTED",),
                active_package_hash_before=_hash("before"),
                active_package_hash_after=_hash("after"),
                rejection_evidence_hash=_hash("evidence"),
            )

    def test_trajectory_closes_campaign_but_not_phase_exit(self) -> None:
        trajectory = _trajectory()
        self.assertTrue(trajectory.campaign_closed)
        value = trajectory.to_json()
        self.assertTrue(value["phase14_campaign_closed"])
        self.assertFalse(value["phase14_exit_closed"])
        self.assertEqual(value["next_phase"], 14)
        self.assertEqual(Phase14TrajectoryReport.from_json(value), trajectory)

    def test_replay_round_trip(self) -> None:
        replay = _replay("ubuntu")
        self.assertTrue(replay.accepted)
        self.assertEqual(Phase14ReplayReport.from_json(replay.to_json()), replay)

    def test_final_closure_requires_all_pinned_platforms(self) -> None:
        reports = (
            _replay("macos", pinned=True),
            _replay("ubuntu", pinned=False),
            _replay("windows", pinned=True),
        )
        trajectory = _trajectory()
        closure = Phase14ClosureReport(
            source_head=trajectory.source_head,
            source_tree=trajectory.source_tree,
            bundle_manifest_hash=_hash("bundle"),
            trajectory_report_hash=trajectory.report_hash,
            attack_report_hash=_hash("attacks"),
            final_store_package_hash=trajectory.final_store_package_hash,
            final_semantic_package_hash=trajectory.final_semantic_package_hash,
            replay_reports=reports,
            accepted_promotions=4,
            rejected_attempts=2,
            substantive_update_families=trajectory.substantive_update_families,
            initial_frontier_cardinality=7,
            final_frontier_cardinality=11,
        )
        self.assertFalse(closure.phase14_exit_closed)

    def test_final_closure_round_trip_when_all_platforms_are_pinned(self) -> None:
        trajectory = _trajectory()
        closure = Phase14ClosureReport(
            source_head=trajectory.source_head,
            source_tree=trajectory.source_tree,
            bundle_manifest_hash=_hash("bundle"),
            trajectory_report_hash=trajectory.report_hash,
            attack_report_hash=_hash("attacks"),
            final_store_package_hash=trajectory.final_store_package_hash,
            final_semantic_package_hash=trajectory.final_semantic_package_hash,
            replay_reports=(
                _replay("macos", pinned=True),
                _replay("ubuntu", pinned=True),
                _replay("windows", pinned=True),
            ),
            accepted_promotions=4,
            rejected_attempts=2,
            substantive_update_families=trajectory.substantive_update_families,
            initial_frontier_cardinality=7,
            final_frontier_cardinality=11,
        )
        self.assertTrue(closure.phase14_exit_closed)
        self.assertEqual(
            Phase14ClosureReport.from_json(closure.to_json()),
            closure,
        )

    def test_bundle_manifest_rejects_duplicate_paths(self) -> None:
        record = Phase14BundleFile(path="campaign/a.json", size_bytes=1, sha256=_hash("a"))
        with self.assertRaises(SchemaValidationError):
            Phase14BundleManifest(
                source_head="1" * 40,
                source_tree="2" * 40,
                trajectory_report_hash=_hash("trajectory"),
                files=(record, record),
                empty_directories=(),
            )

    def test_attack_report_round_trip(self) -> None:
        report = Phase14AttackSuiteReport(
            cases=tuple(
                Phase14AttackResult(
                    attack_id=f"attack-{index}",
                    rejected=True,
                    reason="rejected",
                )
                for index in range(8)
            )
        )
        self.assertTrue(report.accepted)
        self.assertEqual(Phase14AttackSuiteReport.from_json(report.to_json()), report)


if __name__ == "__main__":
    unittest.main()
