from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rcp_rclm_runtime.promotion.record_policy import Phase7ControllerPolicyRecord
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.promotion.store import load_active_phase7_store
from rcp_rclm_runtime.torch_backend.exact_evaluator import ExactEvaluationRecord
from rcp_rclm_runtime.torch_backend.admission import (
    bootstrap_pytorch_pilot_store,
    run_pytorch_pilot_controller,
    verify_pytorch_pilot_promotion,
)
from rcp_rclm_runtime.torch_backend.pilot_policy import pytorch_pilot_phase7_policy
from rcp_rclm_runtime.torch_backend.replay import (
    PilotReplayReason,
    PilotReplayReport,
    guard_pytorch_pilot_replay_source,
    replay_pytorch_pilot_store,
    scan_pytorch_pilot_replay_source_bytes,
)
from tests_phase7.phase7_helpers import (
    fixture_lean_evidence,
    fixture_rejected_lean_evidence,
)


class PyTorchPilotAdmissionReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(
            prefix="rcp-rclm-pytorch-admission-tests-"
        )
        cls.root = Path(cls._temporary.name)
        cls.accepted_store = cls.root / "accepted-store"
        bootstrap_pytorch_pilot_store(cls.accepted_store)
        cls.accepted = run_pytorch_pilot_controller(
            cls.accepted_store,
            fixture_lean_evidence,
            run_label="pytorch-pilot-unit-accept",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()


    def _assert_model_free_host_imports(self) -> None:
        package_root = Path(__file__).resolve().parents[1]
        command = (
            sys.executable,
            "-I",
            "-B",
            "-c",
            (
                "import sys; "
                "import rcp_rclm_runtime.torch_backend.admission; "
                "import rcp_rclm_runtime.torch_backend.replay; "
                "print(int('torch' in sys.modules)); "
                "print(int('rcp_rclm_runtime.torch_backend.process' in sys.modules)); "
                "print(int('rcp_rclm_runtime.torch_backend.proposal_backend' in sys.modules))"
            ),
        )
        environment = dict(os.environ)
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            str(package_root)
            if not existing
            else os.pathsep.join((str(package_root), existing))
        )
        completed = subprocess.run(
            command,
            cwd=package_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("utf-8", errors="replace"),
        )
        self.assertEqual(completed.stdout.splitlines(), [b"0", b"0", b"0"])

    def test_pilot_policy_round_trip_is_strict(self) -> None:
        policy = pytorch_pilot_phase7_policy()
        self.assertEqual(
            Phase7ControllerPolicyRecord.from_json(policy.to_json()),
            policy,
        )
        value = policy.to_json()
        value["generator_backend"] = "phase5a_reference_process"
        with self.assertRaises(Exception):
            Phase7ControllerPolicyRecord.from_json(value)

    def test_accepted_candidate_promotes_through_lean_and_hardened_checker(self) -> None:
        self.assertEqual(self.accepted.verdict, "promoted")
        self.assertEqual(self.accepted.attempt_report.verdict, "accept")
        self.assertEqual(self.accepted.attempt_report.reason_codes, ())
        stages = {stage.stage: stage for stage in self.accepted.attempt_report.stages}
        self.assertEqual(stages["objective_evaluation"].status, "pass")
        self.assertEqual(stages["lean_bridge"].status, "pass")
        self.assertEqual(stages["hardened_checker"].status, "pass")
        self.assertEqual(stages["fallback_rollback"].status, "pass")
        self.assertIsNotNone(self.accepted.promoted_package_root)
        verified = verify_pytorch_pilot_promotion(self.accepted)
        self.assertEqual(
            verified.pointer.active_package_hash,
            self.accepted.controller_report.promoted_package_hash,
        )
        self._assert_model_free_host_imports()

    def test_failed_exact_objective_is_rejected_and_active_pointer_is_preserved(self) -> None:
        package_root = Path(__file__).resolve().parents[1]
        output_root = self.root / "rejected-fixture"
        command = (
            sys.executable,
            str(package_root / "tools" / "run_pytorch_pilot_admission_fixture.py"),
            "--outdir",
            str(output_root),
            "--case",
            "rejected",
        )
        completed = subprocess.run(
            command,
            cwd=package_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=180,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("utf-8", errors="replace"),
        )
        summary = load_json_strict(
            (output_root / "summary.json").read_bytes(),
            require_canonical=True,
        )
        self.assertIsInstance(summary, dict)
        self.assertEqual(summary["observed_verdict"], "rejected")
        self.assertTrue(summary["expectation_met"])
        self.assertFalse(summary["active_package_changed"])
        self.assertTrue(summary["fallback_rollback_verified"])
        self.assertEqual(summary["manual_repair_count"], 0)
        self.assertFalse(summary["host_torch_loaded"])
        self.assertFalse(summary["host_proposal_backend_loaded"])

    def test_independent_replay_accepts_without_training_backend(self) -> None:
        output = self.root / "accepted-replay"
        self._assert_model_free_host_imports()
        replay = replay_pytorch_pilot_store(
            self.accepted_store,
            output,
            fixture_lean_evidence,
        )
        self.assertTrue(replay.report.accepted)
        self.assertEqual(replay.report.generator_invocations, 0)
        self.assertEqual(replay.report.training_backend_modules_loaded, ())
        self.assertEqual(
            [stage.status for stage in replay.report.stages],
            ["pass"] * 12,
        )
        self._assert_model_free_host_imports()

    def test_replay_source_guard_is_clean_and_covers_model_free_modules(self) -> None:
        guard = guard_pytorch_pilot_replay_source()
        self.assertTrue(guard.clean)
        self.assertEqual(guard.findings, ())
        paths = set(guard.file_hashes.to_json())
        self.assertIn(
            "rcp_rclm_runtime/torch_backend/replay.py",
            paths,
        )
        self.assertNotIn(
            "rcp_rclm_runtime/torch_backend/proposal_backend.py",
            paths,
        )
        self.assertNotIn(
            "rcp_rclm_runtime/torch_backend/process.py",
            paths,
        )

    def test_host_removes_ephemeral_training_process_module(self) -> None:
        self.assertNotIn(
            "rcp_rclm_runtime.torch_backend.process",
            sys.modules,
        )
        package = sys.modules.get("rcp_rclm_runtime.torch_backend")
        self.assertIsNotNone(package)
        self.assertFalse(hasattr(package, "process"))
        self.assertNotIn("torch", sys.modules)

    def test_exact_evaluation_and_replay_report_round_trip_strictly(self) -> None:
        self.assertIsNotNone(self.accepted.promoted_package_root)
        evaluation_value = load_json_strict(
            (self.accepted.promoted_package_root / "evidence" / "evaluation.json").read_bytes(),
            require_canonical=True,
        )
        self.assertIsInstance(evaluation_value, dict)
        exact_value = evaluation_value["exact_model_evaluation"]
        exact = ExactEvaluationRecord.from_json(exact_value)
        self.assertEqual(exact.to_json(), exact_value)
        replay = replay_pytorch_pilot_store(
            self.accepted_store,
            self.root / "roundtrip-replay",
            fixture_lean_evidence,
        )
        parsed = PilotReplayReport.from_json(replay.report.to_json())
        self.assertEqual(parsed, replay.report)

    def test_replay_source_guard_rejects_training_import(self) -> None:
        findings = scan_pytorch_pilot_replay_source_bytes(
            "bad.py",
            b"import torch\n",
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "PYTORCH_REPLAY_FORBIDDEN_IMPORT")
        self.assertEqual(findings[0].detail, "torch")

    def test_loaded_training_backend_is_structured_nonacceptance(self) -> None:
        with patch.dict(sys.modules, {"torch": object()}):
            replay = replay_pytorch_pilot_store(
                self.accepted_store,
                self.root / "loaded-training-replay",
                fixture_lean_evidence,
            )
        self.assertFalse(replay.report.accepted)
        self.assertEqual(
            replay.report.reason_codes,
            (PilotReplayReason.TRAINING_BACKEND_DETECTED,),
        )
        self.assertEqual(replay.report.training_backend_modules_loaded, ("torch",))

    def test_unpromoted_store_replay_is_structured_nonacceptance(self) -> None:
        store = self.root / "bootstrap-only-store"
        bootstrap_pytorch_pilot_store(store)
        replay = replay_pytorch_pilot_store(
            store,
            self.root / "bootstrap-only-replay",
            fixture_lean_evidence,
        )
        self.assertFalse(replay.report.accepted)
        self.assertEqual(
            replay.report.reason_codes,
            (PilotReplayReason.SOURCE_BINDING_MISMATCH,),
        )

    def test_lean_rejection_is_nonpromoting(self) -> None:
        store = self.root / "lean-rejected-store"
        bootstrap_pytorch_pilot_store(store)
        before = load_active_phase7_store(store, pytorch_pilot_phase7_policy())
        result = run_pytorch_pilot_controller(
            store,
            fixture_rejected_lean_evidence,
            run_label="pytorch-pilot-unit-lean-reject",
        )
        after = load_active_phase7_store(store, pytorch_pilot_phase7_policy())
        self.assertEqual(result.verdict, "rejected")
        self.assertEqual(result.attempt_report.verdict, "reject")
        self.assertEqual(
            before.pointer.active_package_hash,
            after.pointer.active_package_hash,
        )
        stages = {stage.stage: stage for stage in result.attempt_report.stages}
        self.assertEqual(stages["lean_bridge"].status, "fail")
        self.assertEqual(stages["hardened_checker"].status, "not_evaluated")
        self.assertEqual(stages["fallback_rollback"].status, "pass")

    def test_tampered_candidate_package_is_nonaccepting(self) -> None:
        tampered = self.root / "tampered-candidate-store"
        shutil.copytree(self.accepted_store, tampered)
        target = next(
            (tampered / "packages").rglob(
                "source_candidate/payload/model/weights/linear.weight.bin"
            )
        )
        content = bytearray(target.read_bytes())
        content[0] ^= 1
        target.write_bytes(bytes(content))
        replay = replay_pytorch_pilot_store(
            tampered,
            self.root / "tampered-candidate-replay",
            fixture_lean_evidence,
        )
        self.assertFalse(replay.report.accepted)
        self.assertIn(
            replay.report.reason_codes[0],
            {
                PilotReplayReason.STORE_INVALID,
                PilotReplayReason.SOURCE_BINDING_MISMATCH,
            },
        )

    def test_tampered_retained_evaluation_is_nonaccepting(self) -> None:
        tampered = self.root / "tampered-store"
        shutil.copytree(self.accepted_store, tampered)
        target = next(
            (tampered / "packages").rglob("evidence/evaluation.json")
        )
        target.write_bytes(target.read_bytes() + b"\n")
        replay = replay_pytorch_pilot_store(
            tampered,
            self.root / "tampered-replay",
            fixture_lean_evidence,
        )
        self.assertFalse(replay.report.accepted)
        self.assertIn(
            replay.report.reason_codes[0],
            {
                PilotReplayReason.STORE_INVALID,
                PilotReplayReason.SOURCE_BINDING_MISMATCH,
            },
        )


if __name__ == "__main__":
    unittest.main()
