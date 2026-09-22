from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.phase16.archive import ExperimentArchive
from rcp_rclm_runtime_v4.phase16.attacks import run_phase16_attacks
from rcp_rclm_runtime_v4.phase16.bootstrap import verify_phase16_bootstrap
from rcp_rclm_runtime_v4.phase16.campaign import (
    initial_phase16_state,
    run_phase16_campaign,
    validate_phase16_campaign,
)
from rcp_rclm_runtime_v4.phase16.capture import run_phase16_capture
from rcp_rclm_runtime_v4.phase16.challenge import (
    evaluate_hidden_candidate,
    generate_hidden_challenge,
)
from rcp_rclm_runtime_v4.phase16.closure import close_phase16
from rcp_rclm_runtime_v4.phase16.constants import (
    ARCHIVE_KINDS,
    PHASE16_DEFAULT_SEEDS,
    PHASE16_DEFAULT_STREAMS,
    PHASE16_EXPECTED_PARENT_HEAD,
    PHASE16_INHERITED_PLANNER_PROJECTION,
    PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
    PHASE16_PHASE15_SOURCE_TREE,
    UPDATE_FAMILIES,
)
from rcp_rclm_runtime_v4.phase16.foundation import build_phase16_foundation
from rcp_rclm_runtime_v4.phase16.grammar import (
    execute_program,
    legal_mutation_programs,
)
from rcp_rclm_runtime_v4.phase16.ranking import ranked_programs, ranking_manifest
from rcp_rclm_runtime_v4.phase16.replay import Phase16ReplayReport, replay_phase16_capture
from rcp_rclm_runtime_v4.phase16.scheduler import fair_order, search_programs


class Phase16FairSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo = Path(__file__).resolve().parents[3]
        cls.closure_archive = (
            repo
            / "artifacts/private_phase16/bootstrap/phase15-final-closure-30969783629-1.zip"
        )
        cls.bundle_archive = (
            repo
            / "artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip"
        )
        cls.bootstrap = verify_phase16_bootstrap(
            phase15_closure_archive=cls.closure_archive,
            phase15_bundle_archive=cls.bundle_archive,
        )
        cls.source_head = PHASE16_EXPECTED_PARENT_HEAD
        cls.source_tree = PHASE16_PHASE15_SOURCE_TREE
        cls.campaign = run_phase16_campaign(
            bootstrap=cls.bootstrap,
            source_head=cls.source_head,
            source_tree=cls.source_tree,
            seed=PHASE16_DEFAULT_SEEDS[0],
            challenge_stream=PHASE16_DEFAULT_STREAMS[0],
            target_promotions=8,
        )
        cls.capture: dict[str, object] | None = None

    @classmethod
    def authoritative_capture(cls) -> dict[str, object]:
        if cls.capture is None:
            cls.capture = run_phase16_capture(
                bootstrap=cls.bootstrap,
                source_head=cls.source_head,
                source_tree=cls.source_tree,
            )
        return cls.capture

    def test_01_bootstrap_is_exact_and_accepted(self) -> None:
        self.assertTrue(self.bootstrap.accepted)
        self.assertEqual(
            self.bootstrap.inherited_planner_weights_sha256,
            PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
        )
        self.assertEqual(
            self.bootstrap.inherited_planner_nonzero_count,
            len(PHASE16_INHERITED_PLANNER_PROJECTION),
        )

    def test_02_tampered_closure_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.zip"
            payload = bytearray(self.closure_archive.read_bytes())
            payload[-1] ^= 1
            path.write_bytes(payload)
            with self.assertRaises(SchemaValidationError):
                verify_phase16_bootstrap(
                    phase15_closure_archive=path,
                    phase15_bundle_archive=self.bundle_archive,
                )

    def test_03_tampered_bundle_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.zip"
            payload = bytearray(self.bundle_archive.read_bytes())
            payload[-1] ^= 1
            path.write_bytes(payload)
            with self.assertRaises(SchemaValidationError):
                verify_phase16_bootstrap(
                    phase15_closure_archive=self.closure_archive,
                    phase15_bundle_archive=path,
                )

    def test_04_initial_state_is_bound_to_m9(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        self.assertEqual(state.model_index, 9)
        self.assertEqual(set(state.component_generations), set(UPDATE_FAMILIES))
        self.assertEqual(state.archive_root_hash, self.bootstrap.report_hash)

    def test_05_legal_grammar_has_32_programs(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="1" * 64,
        )
        self.assertEqual(len(programs), 32)
        self.assertEqual(len({program.program_hash for program in programs}), 32)

    def test_06_legal_grammar_covers_eight_families(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="2" * 64,
        )
        self.assertEqual({program.family for program in programs}, set(UPDATE_FAMILIES))

    def test_07_program_execution_is_deterministic(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        program = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="3" * 64,
        )[0]
        public_input = {"input_vector": [1, 2, 3, 4]}
        self.assertEqual(
            execute_program(program, public_input),
            execute_program(program, public_input),
        )

    def test_08_inherited_ranking_is_deterministic(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="4" * 64,
        )
        kwargs = {
            "active_package_hash": state.active_package_hash,
            "verified_family_counts": {},
            "rejected_families": (),
            "seed": "seed",
            "challenge_stream": "stream",
        }
        self.assertEqual(ranked_programs(programs, **kwargs), ranked_programs(programs, **kwargs))
        manifest = ranking_manifest(programs, **kwargs)
        self.assertEqual(
            manifest["planner_weights_sha256"],
            PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
        )

    def test_09_fair_order_is_a_permutation(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="5" * 64,
        )
        ordered = fair_order(programs, "6" * 64)
        self.assertEqual(
            {program.program_hash for program in ordered},
            {program.program_hash for program in programs},
        )

    def test_10_search_acceptance_has_fair_certificate(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="7" * 64,
        )
        target = programs[-1]
        result = search_programs(
            programs,
            promotion_index=0,
            active_package_hash=state.active_package_hash,
            seed="seed",
            challenge_stream="stream",
            verified_family_counts={},
            evaluator=lambda program: (
                program.program_hash == target.program_hash,
                () if program.program_hash == target.program_hash else ("REJECT",),
                program.program_hash,
            ),
        )
        self.assertEqual(result.accepted_program, target)
        self.assertFalse(result.certificate.exhausted)

    def test_11_search_exhaustion_considers_all_legal_programs(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="8" * 64,
        )
        result = search_programs(
            programs,
            promotion_index=0,
            active_package_hash=state.active_package_hash,
            seed="seed",
            challenge_stream="stream",
            verified_family_counts={},
            evaluator=lambda program: (False, ("REJECT",), program.program_hash),
        )
        self.assertTrue(result.certificate.exhausted)
        self.assertEqual(len(result.certificate.considered_program_hashes), 32)

    def test_12_archive_is_content_addressed_and_hash_chained(self) -> None:
        archive = ExperimentArchive(self.bootstrap.report_hash)
        first = archive.append("proposal_hypothesis", {"value": 1})
        second = archive.append("candidate_program", {"value": 2})
        self.assertNotEqual(first, second)
        self.assertEqual(archive.root_hash, second)
        self.assertEqual(
            ExperimentArchive.from_json(archive.to_json()).root_hash,
            second,
        )

    def test_13_archive_payload_tampering_is_rejected(self) -> None:
        archive = ExperimentArchive(self.bootstrap.report_hash)
        archive.append("proposal_hypothesis", {"value": 1})
        value = archive.to_json()
        value["records"][0]["payload"]["value"] = 2
        with self.assertRaises(SchemaValidationError):
            ExperimentArchive.from_json(value)

    def test_14_hidden_challenge_is_generated_after_freeze(self) -> None:
        state = initial_phase16_state(self.bootstrap)
        programs = legal_mutation_programs(
            state,
            promotion_index=0,
            public_nonce_hash="9" * 64,
        )
        challenge = generate_hidden_challenge(
            state=state,
            programs=programs,
            promotion_index=0,
            predecessor_freeze_hash="a" * 64,
            public_nonce_hash="9" * 64,
            seed="seed",
            challenge_stream="stream",
            verified_family_counts={},
        )
        self.assertTrue(challenge.generated_after_predecessor_freeze)
        self.assertFalse(challenge.public_json()["target_output_visible_before_candidate_freeze"])

    def test_15_wrong_candidate_fails_hidden_challenge(self) -> None:
        transition = self.campaign["transitions"][0]
        evaluations = transition["independent_evaluations"]
        self.assertFalse(evaluations[0]["accepted"])
        self.assertFalse(evaluations[0]["candidate_passed_hidden_challenge"])

    def test_16_target_candidate_passes_hidden_challenge(self) -> None:
        transition = self.campaign["transitions"][0]
        self.assertTrue(transition["independent_evaluations"][-1]["accepted"])
        self.assertTrue(
            transition["independent_evaluations"][-1][
                "candidate_passed_hidden_challenge"
            ]
        )

    def test_17_eight_promotion_campaign_is_accepted(self) -> None:
        self.assertTrue(self.campaign["accepted"])
        self.assertEqual(self.campaign["accepted_promotions"], 8)

    def test_18_campaign_uses_all_eight_update_families(self) -> None:
        self.assertEqual(set(self.campaign["update_families_used"]), set(UPDATE_FAMILIES))

    def test_19_campaign_contains_rejection_recovery_cycles(self) -> None:
        self.assertGreaterEqual(self.campaign["rejection_recovery_cycles"], 2)
        self.assertGreaterEqual(self.campaign["rejected_attempts"], 8)

    def test_20_campaign_retains_both_frontiers(self) -> None:
        self.assertTrue(self.campaign["frontier_retained"])
        self.assertTrue(self.campaign["recursive_productivity_frontier_retained"])

    def test_21_campaign_strictly_expands_recursive_productivity(self) -> None:
        self.assertEqual(self.campaign["strict_recursive_productivity_expansions"], 8)

    def test_22_campaign_archive_contains_all_declared_kinds(self) -> None:
        self.assertTrue(
            set(ARCHIVE_KINDS).issubset(self.campaign["archive_kinds_present"])
        )
        self.assertTrue(self.campaign["archive_untrusted_for_acceptance"])

    def test_23_campaign_exhaustion_probe_is_complete(self) -> None:
        probe = self.campaign["exhaustion_probe"]
        self.assertTrue(probe["bounded_search_exhausted"])
        self.assertTrue(probe["every_legal_program_considered"])
        self.assertEqual(probe["considered_program_count"], 32)

    def test_24_campaign_is_deterministic(self) -> None:
        duplicate = run_phase16_campaign(
            bootstrap=self.bootstrap,
            source_head=self.source_head,
            source_tree=self.source_tree,
            seed=PHASE16_DEFAULT_SEEDS[0],
            challenge_stream=PHASE16_DEFAULT_STREAMS[0],
            target_promotions=8,
        )
        self.assertEqual(self.campaign, duplicate)

    def test_25_campaign_semantic_tampering_is_rejected(self) -> None:
        candidate = deepcopy(self.campaign)
        candidate["manual_repairs"] = 1
        payload = dict(candidate)
        payload.pop("report_hash")
        from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

        candidate["report_hash"] = canonical_json_hash(payload)
        with self.assertRaises(SchemaValidationError):
            validate_phase16_campaign(candidate, bootstrap=self.bootstrap)

    def test_26_foundation_closes_four_independent_eight_step_campaigns(self) -> None:
        campaigns = tuple(
            run_phase16_campaign(
                bootstrap=self.bootstrap,
                source_head=self.source_head,
                source_tree=self.source_tree,
                seed=seed,
                challenge_stream=stream,
                target_promotions=8,
            )
            for seed in PHASE16_DEFAULT_SEEDS
            for stream in PHASE16_DEFAULT_STREAMS
        )
        foundation = build_phase16_foundation(campaigns)
        self.assertTrue(foundation["phase16_foundation_closed"])
        self.assertEqual(foundation["campaign_count"], 4)

    def test_27_selected_attack_suite_rejects_twelve_cases(self) -> None:
        report = run_phase16_attacks(
            reference_campaign=self.campaign,
            bootstrap=self.bootstrap,
            source_head=self.source_head,
        )
        self.assertTrue(report.accepted)
        self.assertEqual(len(report.cases), 12)

    def test_28_full_scaling_capture_closes_all_ladder_rungs(self) -> None:
        capture = self.authoritative_capture()
        self.assertTrue(capture["accepted"])
        self.assertEqual(capture["campaign_count"], 16)
        self.assertEqual(capture["total_accepted_promotions"], 480)
        self.assertTrue(all(capture["rung_status"].values()))

    def test_29_worker_free_replay_reconstructs_capture(self) -> None:
        capture = self.authoritative_capture()
        report = replay_phase16_capture(
            capture=capture,
            bootstrap=self.bootstrap,
            platform_id="ubuntu",
        )
        self.assertTrue(report.accepted)
        self.assertEqual(report.capture_report_hash, report.reconstructed_capture_hash)

    def test_30_closure_keeps_gate_e_open_for_phase17(self) -> None:
        capture = self.authoritative_capture()
        attacks = run_phase16_attacks(
            reference_campaign=capture["campaigns"][0],
            bootstrap=self.bootstrap,
            source_head=self.source_head,
        )
        replays = tuple(
            Phase16ReplayReport(
                platform_id=platform,
                source_head=str(capture["source_head"]),
                source_tree=str(capture["source_tree"]),
                bootstrap_report_hash=self.bootstrap.report_hash,
                capture_report_hash=str(capture["report_hash"]),
                reconstructed_capture_hash=str(capture["report_hash"]),
                campaign_count=int(capture["campaign_count"]),
                accepted_promotions=int(capture["total_accepted_promotions"]),
                rejected_attempts=int(capture["total_rejected_attempts"]),
                stretch_target_executed=False,
            )
            for platform in ("macos", "ubuntu", "windows")
        )
        closure = close_phase16(capture=capture, attacks=attacks, replays=replays)
        value = closure.to_json()
        self.assertTrue(value["phase16_exit_closed"])
        self.assertFalse(value["gate_e_closed"])
        self.assertEqual(value["next_phase"], 17)


if __name__ == "__main__":
    unittest.main()
