from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.gatee.records import RouteHintPolicy
from rcp_rclm_runtime_v4.phase15.attacks import (
    Phase15AttackCase,
    Phase15AttackSuiteReport,
)
from rcp_rclm_runtime_v4.phase15.challenges import (
    DynamicHiddenChallenge,
    answer_store_json,
    challenge_manifest_json,
    challenge_suite_after_freeze,
    challenges_from_answer_store,
)
from rcp_rclm_runtime_v4.phase15.closure import Phase15ClosureReport
from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_DECODER_PARAMETER_COUNT,
    PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS,
    TOKEN_BY_NAME,
    integer_token,
    token_integer,
)
from rcp_rclm_runtime_v4.phase15.curriculum import (
    curriculum_manifest,
    expected_plan,
    public_curriculum,
)
from rcp_rclm_runtime_v4.phase15.decoder import (
    DECODER_CURRICULUM_PATH,
    DECODER_MANIFEST_PATH,
    DECODER_TRAINING_REPORT_PATH,
    DECODER_VOCABULARY_PATH,
    DECODER_WEIGHTS_PATH,
    active_feature_indices,
    decode_plan,
    train_perceptron,
    vocabulary_json,
    weights_bytes,
    weights_from_bytes,
)
from rcp_rclm_runtime.lean_bridge.compiler import PinnedLeanProject
from rcp_rclm_runtime_v4.phase15.outer import _pinned_gate_b_compiler
from rcp_rclm_runtime_v4.phase15.records import Phase15AttemptSummary
from rcp_rclm_runtime_v4.phase15.replay import (
    Phase15ReplayReport,
    _evaluation_semantic_projection,
    _outer_semantic_projection,
)
from rcp_rclm_runtime_v4.phase15.training import run_isolated_training_twice
from rcp_rclm_runtime_v4.phase15.training_worker import run_worker


_ZERO = "0" * 64
_ONE = "1" * 64
_TWO = "2" * 64
_THREE = "3" * 64


class Phase15DynamicHiddenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.runtime_package_root = cls.repo_root / "python/rcp_rclm_runtime_v4"
        cls.temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase15-unit-")
        cls.root = Path(cls.temporary.name)
        cls.training = run_isolated_training_twice(
            variant="multidomain",
            active_semantic_package_hash=_ONE,
            active_model_identity_hash=_TWO,
            work_root=cls.root / "training",
            package_root=cls.runtime_package_root,
        )
        cls.package_root = cls.root / "package"
        first = cls.training.first_root
        mapping = {
            "manifest.json": DECODER_MANIFEST_PATH,
            "public_curriculum.json": DECODER_CURRICULUM_PATH,
            "training_report.json": DECODER_TRAINING_REPORT_PATH,
            "vocabulary.json": DECODER_VOCABULARY_PATH,
            "weights.i16le.bin": DECODER_WEIGHTS_PATH,
        }
        for source_name, relative in mapping.items():
            destination = cls.package_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(first / source_name, destination)
        cls.challenges = challenge_suite_after_freeze(
            source_head="a" * 40,
            candidate_freeze_hashes=(_ONE, _TWO),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_01_public_curriculum_uses_only_even_partition(self) -> None:
        examples = public_curriculum("multidomain")
        self.assertTrue(examples)
        self.assertTrue(all((item.parameter_a + item.parameter_b) % 2 == 0 for item in examples))
        self.assertEqual({"integer_program", "lean_multistep"}, {item.domain for item in examples})

    def test_02_lean_only_curriculum_excludes_program_domain(self) -> None:
        examples = public_curriculum("lean_only")
        self.assertTrue(examples)
        self.assertEqual({"lean_multistep"}, {item.domain for item in examples})

    def test_03_expected_plans_are_multitoken_and_terminated(self) -> None:
        lean = expected_plan("lean_multistep", 1, 4)
        program = expected_plan("integer_program", -3, 2)
        self.assertGreaterEqual(len(lean), 7)
        self.assertGreaterEqual(len(program), 7)
        self.assertEqual(TOKEN_BY_NAME["EOS"], lean[-1])
        self.assertEqual(TOKEN_BY_NAME["EOS"], program[-1])

    def test_04_integer_token_round_trip(self) -> None:
        for value in range(-8, 9):
            self.assertEqual(value, token_integer(integer_token(value)))

    def test_05_parameter_copy_features_are_shared_and_context_free(self) -> None:
        grammar = active_feature_indices(
            "integer_program",
            0,
            TOKEN_BY_NAME["BOS"],
            2,
            3,
        )
        program_a_copy = active_feature_indices(
            "integer_program",
            1,
            TOKEN_BY_NAME["PROGRAM_BEGIN"],
            2,
            3,
        )
        program_b_copy = active_feature_indices(
            "integer_program",
            3,
            TOKEN_BY_NAME["PROGRAM_MUL"],
            7,
            2,
        )
        lean_b_copy = active_feature_indices(
            "lean_multistep",
            2,
            TOKEN_BY_NAME["INT_0"],
            0,
            2,
        )
        changed_previous = active_feature_indices(
            "integer_program",
            1,
            TOKEN_BY_NAME["ERROR"],
            2,
            -8,
        )
        self.assertEqual(3, len(grammar))
        self.assertEqual(1, len(program_a_copy))
        self.assertEqual(program_a_copy, program_b_copy)
        self.assertEqual(program_a_copy, lean_b_copy)
        self.assertEqual(program_a_copy, changed_previous)

    def test_06_perceptron_training_is_deterministic(self) -> None:
        examples = public_curriculum("multidomain")
        first = train_perceptron(examples, epochs=24)
        second = train_perceptron(tuple(reversed(examples)), epochs=24)
        self.assertEqual(first, second)

    def test_07_quantized_weights_round_trip(self) -> None:
        weights = train_perceptron(public_curriculum("lean_only"), epochs=24)
        payload = weights_bytes(weights)
        self.assertEqual(PHASE15_DECODER_PARAMETER_COUNT * 2, len(payload))
        self.assertEqual(weights, weights_from_bytes(payload))

    def test_08_isolated_training_outputs_are_byte_identical(self) -> None:
        self.assertTrue(self.training.two_run_replay_equal)
        first = sorted(
            (path.relative_to(self.training.first_root).as_posix(), path.read_bytes())
            for path in self.training.first_root.rglob("*")
            if path.is_file()
        )
        second = sorted(
            (path.relative_to(self.training.second_root).as_posix(), path.read_bytes())
            for path in self.training.second_root.rglob("*")
            if path.is_file()
        )
        self.assertEqual(first, second)

    def test_09_multidomain_decoder_generalizes_to_every_heldout_pair(self) -> None:
        heldout = [
            ("lean_multistep", parameter_a, parameter_b)
            for parameter_a in range(0, 8)
            for parameter_b in range(parameter_a + 1, 9)
            if (parameter_a + parameter_b) % 2 == 1
        ]
        heldout.extend(
            ("integer_program", parameter_a, parameter_b)
            for parameter_a in range(-4, 5)
            if parameter_a != 0
            for parameter_b in range(-8, 9)
            if (parameter_a + parameter_b) % 2 == 1
        )
        self.assertEqual(88, len(heldout))
        for domain, parameter_a, parameter_b in heldout:
            report = decode_plan(
                self.package_root,
                domain,
                parameter_a,
                parameter_b,
            )
            context = (
                domain,
                parameter_a,
                parameter_b,
                report.plan_text,
            )
            self.assertTrue(report.stopped_on_eos, context)
            self.assertEqual(
                expected_plan(domain, parameter_a, parameter_b),
                tuple(report.tokens),
                context,
            )

    def test_10_dynamic_challenges_are_postfreeze_and_out_of_curriculum(self) -> None:
        self.assertEqual(2, len(self.challenges))
        self.assertEqual({"integer_program", "lean_multistep"}, {item.domain for item in self.challenges})
        self.assertTrue(all(item.generated_after_candidate_freeze for item in self.challenges))
        self.assertTrue(all((item.parameter_a + item.parameter_b) % 2 == 1 for item in self.challenges))

    def test_11_dynamic_challenge_generation_is_deterministic_and_freeze_bound(self) -> None:
        repeated = challenge_suite_after_freeze(
            source_head="a" * 40,
            candidate_freeze_hashes=(_ONE, _TWO),
        )
        changed = challenge_suite_after_freeze(
            source_head="a" * 40,
            candidate_freeze_hashes=(_ONE, _THREE),
        )
        self.assertEqual(self.challenges, repeated)
        self.assertNotEqual(
            tuple(item.commitment_hash for item in self.challenges),
            tuple(item.commitment_hash for item in changed),
        )

    def test_12_private_answer_store_round_trips(self) -> None:
        store = answer_store_json(self.challenges)
        self.assertEqual(self.challenges, challenges_from_answer_store(store))
        manifest = challenge_manifest_json(self.challenges, candidate_freeze_hashes=(_ONE, _TWO))
        self.assertTrue(manifest["generated_after_candidate_freeze"])
        self.assertFalse(manifest["private_parameters_visible_before_freeze"])

    def test_13_prefreeze_challenge_is_rejected(self) -> None:
        with self.assertRaises(SchemaValidationError):
            DynamicHiddenChallenge(
                challenge_id="invalid",
                domain="lean_multistep",
                commitment_hash=_ZERO,
                parameter_a=0,
                parameter_b=1,
                generated_after_candidate_freeze=False,
            )

    def test_14_route_hints_are_rejected(self) -> None:
        with self.assertRaises(Exception):
            RouteHintPolicy(host_selected_objective_present=True)

    def test_15_training_worker_rejects_hidden_material(self) -> None:
        request = {
            "schema_id": "runtime.v4.phase15.training_request.v1",
            "variant": "multidomain",
            "active_semantic_package_hash": _ONE,
            "active_model_identity_hash": _TWO,
            "public_curriculum_manifest": curriculum_manifest("multidomain"),
            "epochs": 24,
            "private_challenge_material_present": True,
            "heldout_prompt_present": False,
            "heldout_reference_answer_present": False,
        }
        request_path = self.root / "invalid-request.json"
        request_path.write_bytes(canonical_json_bytes(request))
        with self.assertRaises(SchemaValidationError):
            run_worker(request_path, self.root / "invalid-worker-output")

    def test_16_attempt_summary_enforces_store_transition_semantics(self) -> None:
        accepted = Phase15AttemptSummary(
            attempt_index=1,
            variant="multidomain",
            candidate_semantic_package_hash=_ONE,
            candidate_freeze_hash=_TWO,
            decoder_manifest_hash=_THREE,
            training_result_hash="4" * 64,
            candidate_phase6_tree_hash="5" * 64,
            verdict="accept",
            reason_codes=(),
            protected_report_hashes=("6" * 64,),
            predecessor_dynamic_report_hashes=("7" * 64,),
            candidate_dynamic_report_hashes=("8" * 64,),
            information_report_hash="9" * 64,
            recursive_productivity_report_hash="a" * 64,
            gate_d_report_hash="b" * 64,
            gate_e_report_hash="c" * 64,
            gate_e_validation_hash="d" * 64,
            outer_verification_hash="e" * 64,
            active_store_package_hash_before="f" * 64,
            active_store_package_hash_after=_ONE,
            phase7_ledger_entry_hash=_TWO,
            rejection_evidence_hash=None,
        )
        self.assertEqual(accepted, Phase15AttemptSummary.from_json(accepted.to_json()))
        with self.assertRaises(SchemaValidationError):
            replace(accepted, active_store_package_hash_after="f" * 64)

    def test_17_replay_requires_pinned_lean(self) -> None:
        report = Phase15ReplayReport(
            source_head="a" * 40,
            source_tree="b" * 40,
            platform_id="ubuntu",
            bundle_manifest_hash=_ONE,
            trajectory_report_hash=_TWO,
            final_store_package_hash=_THREE,
            final_m9_semantic_package_hash="4" * 64,
            immutable_packages_verified=10,
            protected_task_replays=22,
            dynamic_task_replays=4,
            gate_d_replays=1,
            gate_e_replays=1,
            outer_replays=1,
            accepted_promotions=1,
            rejected_attempts=1,
            pinned_lean=False,
            forbidden_worker_modules=(),
        )
        self.assertTrue(report.semantic_replay_accepted)
        self.assertFalse(report.accepted)
        self.assertTrue(replace(report, pinned_lean=True).accepted)

    def test_18_three_pinned_reports_are_required_for_closure(self) -> None:
        base = Phase15ReplayReport(
            source_head="a" * 40,
            source_tree="b" * 40,
            platform_id="ubuntu",
            bundle_manifest_hash=_ONE,
            trajectory_report_hash=_TWO,
            final_store_package_hash=_THREE,
            final_m9_semantic_package_hash="4" * 64,
            immutable_packages_verified=10,
            protected_task_replays=22,
            dynamic_task_replays=4,
            gate_d_replays=1,
            gate_e_replays=1,
            outer_replays=1,
            accepted_promotions=1,
            rejected_attempts=1,
            pinned_lean=True,
            forbidden_worker_modules=(),
        )
        closure = Phase15ClosureReport(
            source_head=base.source_head,
            source_tree=base.source_tree,
            trajectory_report_hash=base.trajectory_report_hash,
            bundle_manifest_hash=base.bundle_manifest_hash,
            attack_report_hash="5" * 64,
            final_store_package_hash=base.final_store_package_hash,
            final_m9_semantic_package_hash=base.final_m9_semantic_package_hash,
            replay_reports=tuple(
                replace(base, platform_id=platform)
                for platform in ("macos", "ubuntu", "windows")
            ),
        )
        self.assertTrue(closure.accepted)
        self.assertTrue(closure.to_json()["phase15_exit_closed"])
        self.assertEqual(16, closure.to_json()["next_phase"])

    def test_19_attack_report_requires_all_twelve_rejections(self) -> None:
        cases = tuple(
            Phase15AttackCase(
                attack_id=f"attack-{index:02d}",
                rejected=True,
                reason_class="SchemaValidationError",
            )
            for index in range(12)
        )
        report = Phase15AttackSuiteReport(
            source_head="a" * 40,
            bundle_manifest_hash=_ONE,
            cases=cases,
        )
        self.assertTrue(report.accepted)
        self.assertEqual(report, Phase15AttackSuiteReport.from_json(report.to_json()))

    def test_20_recursive_productivity_additions_are_distinct(self) -> None:
        self.assertEqual(3, len(PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS))
        self.assertEqual(3, len(set(PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS)))

    def test_21_outer_compiler_uses_pinned_v4_execution_root(self) -> None:
        repo = self.root / "outer-compiler-repo"
        execution_root = repo / "lean/rcp_rclm_formal_core_v4"
        pinned_root = repo / "lean/rcp_rclm_formal_core_v2"
        execution_root.mkdir(parents=True, exist_ok=True)
        pinned_root.mkdir(parents=True, exist_ok=True)
        pinned = PinnedLeanProject(
            repository_root=repo,
            root=pinned_root,
            toolchain="leanprover/lean4:v4.31.0",
            mathlib_commit=_ONE,
            formal_source_commit=_TWO,
            formal_source_tree=_THREE,
            toolchain_file_hash="4" * 64,
            manifest_hash="5" * 64,
            lakefile_hash="6" * 64,
            theorem_surface_hash="7" * 64,
            pin_hash="8" * 64,
        )
        with (
            patch.object(
                PinnedLeanProject,
                "discover",
                return_value=pinned,
            ) as discover,
            patch(
                "rcp_rclm_runtime_v4.phase15.outer.LeanCompiler"
            ) as compiler,
        ):
            observed = _pinned_gate_b_compiler(
                repo_root=repo,
                lean_project_root=execution_root,
            )
        self.assertIs(observed, compiler.return_value)
        discover.assert_called_once_with(repo.resolve(strict=True))
        execution_project = compiler.call_args.kwargs["project"]
        self.assertEqual(execution_root.resolve(), execution_project.root)
        self.assertEqual(pinned.pin_hash, execution_project.pin_hash)
        self.assertEqual(600, compiler.call_args.kwargs["timeout_seconds"])
        wrong_root = repo / "lean/rcp_rclm_formal_core_v3"
        wrong_root.mkdir(parents=True, exist_ok=True)
        with self.assertRaisesRegex(ValueError, "Formal Core v4"):
            _pinned_gate_b_compiler(
                repo_root=repo,
                lean_project_root=wrong_root,
            )


    def test_22_unpinned_evaluation_projection_removes_only_pin_bit(self) -> None:
        pinned = {
            "predecessor_dynamic_reports": [
                {"pinned_lean": True, "lean_exit_code": None}
            ],
            "candidate_dynamic_reports": [
                {"pinned_lean": True, "lean_exit_code": 0}
            ],
            "candidate_state": {"state_hash": _ONE},
        }
        unpinned = json.loads(json.dumps(pinned))
        unpinned["predecessor_dynamic_reports"][0]["pinned_lean"] = False
        unpinned["candidate_dynamic_reports"][0]["pinned_lean"] = False
        self.assertEqual(
            _evaluation_semantic_projection(pinned),
            _evaluation_semantic_projection(unpinned),
        )
        unpinned["candidate_dynamic_reports"][0]["lean_exit_code"] = 1
        self.assertNotEqual(
            _evaluation_semantic_projection(pinned),
            _evaluation_semantic_projection(unpinned),
        )

    def test_23_unpinned_outer_projection_removes_only_execution_evidence(self) -> None:
        pinned = {
            "logical_evaluation_hash": _ONE,
            "lean_report_hash": _TWO,
            "checker_report_hash": _THREE,
            "candidate_tree_hash_before": "4" * 64,
            "candidate_tree_hash_after": "4" * 64,
            "lean_invoked": True,
            "checker_invoked": True,
        }
        unpinned = {
            **pinned,
            "lean_report_hash": "5" * 64,
            "checker_report_hash": "6" * 64,
            "lean_invoked": False,
            "checker_invoked": False,
        }
        self.assertEqual(
            _outer_semantic_projection(pinned),
            _outer_semantic_projection(unpinned),
        )
        unpinned["candidate_tree_hash_after"] = "7" * 64
        self.assertNotEqual(
            _outer_semantic_projection(pinned),
            _outer_semantic_projection(unpinned),
        )


if __name__ == "__main__":
    unittest.main()
