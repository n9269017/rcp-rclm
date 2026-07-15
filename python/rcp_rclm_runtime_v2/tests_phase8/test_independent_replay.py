from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.generator import process as generator_process
from rcp_rclm_runtime.replay.bundle import (
    PHASE8_MANIFEST_NAME,
    PHASE8_STORE_DIRECTORY_NAME,
    Phase8BundleError,
    build_phase8_replay_bundle,
    verify_phase8_replay_bundle,
)
from rcp_rclm_runtime.replay.guard import (
    ReplaySourceFinding,
    ReplaySourceGuardReport,
    guard_independent_replay_source,
    scan_replay_source_bytes,
)
from rcp_rclm_runtime.replay.records import (
    Phase8ReplayBundleManifestRecord,
    Phase8ReplayReport,
    Phase8ReasonCode,
)
from rcp_rclm_runtime.replay.reproduce import reproduce_phase8_bundle
from rcp_rclm_runtime.schema.verdict import FrozenHashMap

from phase8_helpers import (
    build_clean_reference_bundle,
    copy_bundle,
    fixture_lean_evidence,
    fixture_rejected_lean_evidence,
    fixture_semantic_mismatch_lean_evidence,
)


class IndependentReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="rcp-rclm-phase8-tests-")
        cls.root = Path(cls._temporary.name)
        cls.clean_bundle = build_clean_reference_bundle(cls.root / "clean")
        cls.clean_manifest = verify_phase8_replay_bundle(cls.clean_bundle)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def fresh_path(self, name: str) -> Path:
        path = self.root / name
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        return path

    def test_clean_bundle_verifies(self) -> None:
        manifest = verify_phase8_replay_bundle(self.clean_bundle)
        self.assertEqual(manifest, self.clean_manifest)
        self.assertEqual(len(manifest.package_chain), 3)
        self.assertEqual(len(manifest.attempts), 4)
        self.assertEqual(
            [attempt.ledger_event for attempt in manifest.attempts],
            ["promotion", "promotion", "rejection", "rejection"],
        )

    def test_clean_independent_replay_accepts_without_generator(self) -> None:
        output = self.fresh_path("replay-clean")
        with patch.object(
            generator_process,
            "run_reference_generator_process",
            side_effect=AssertionError("original generator must not run during replay"),
        ):
            evidence = reproduce_phase8_bundle(
                self.clean_bundle,
                output,
                fixture_lean_evidence,
            )
        self.assertTrue(evidence.report.accepted)
        self.assertEqual(evidence.report.generator_invocations, 0)
        self.assertEqual(len(evidence.report.attempts), 4)
        self.assertTrue(all(attempt.verdict == "accept" for attempt in evidence.report.attempts))
        self.assertTrue(
            all(attempt.generator_invocations == 0 for attempt in evidence.report.attempts)
        )
        observed = Phase8ReplayReport.from_json(
            load_json_strict(
                (output / "replay_report.json").read_bytes(),
                require_canonical=True,
            )
        )
        self.assertEqual(observed, evidence.report)

    def test_replay_is_deterministic_across_fresh_outputs(self) -> None:
        first = reproduce_phase8_bundle(
            self.clean_bundle,
            self.fresh_path("replay-first"),
            fixture_lean_evidence,
        )
        second = reproduce_phase8_bundle(
            self.clean_bundle,
            self.fresh_path("replay-second"),
            fixture_lean_evidence,
        )
        self.assertEqual(first.report.to_json(), second.report.to_json())
        self.assertEqual(first.report.report_hash, second.report.report_hash)

    def test_bundle_and_report_round_trip_strictly(self) -> None:
        manifest = Phase8ReplayBundleManifestRecord.from_json(
            self.clean_manifest.to_json()
        )
        self.assertEqual(manifest, self.clean_manifest)
        evidence = reproduce_phase8_bundle(
            self.clean_bundle,
            self.fresh_path("roundtrip-replay"),
            fixture_lean_evidence,
        )
        report = Phase8ReplayReport.from_json(evidence.report.to_json())
        self.assertEqual(report, evidence.report)

    def test_importing_replay_does_not_load_generator_process_or_worker(self) -> None:
        environment = dict(os.environ)
        package_root = Path(__file__).resolve().parents[1]
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            str(package_root)
            if not existing
            else os.pathsep.join((str(package_root), existing))
        )
        command = (
            sys.executable,
            "-c",
            (
                "import sys; import rcp_rclm_runtime.replay.reproduce; "
                "print(int('rcp_rclm_runtime.generator.process' in sys.modules)); "
                "print(int('rcp_rclm_runtime.generator.worker' in sys.modules))"
            ),
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
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(completed.stdout.splitlines(), [b"0", b"0"])

    def test_source_guard_proves_generator_process_absent(self) -> None:
        report = guard_independent_replay_source()
        self.assertTrue(report.clean)
        self.assertEqual(report.findings, ())
        self.assertGreaterEqual(len(report.file_hashes.entries), 6)

    def test_source_guard_rejects_generator_process_import(self) -> None:
        findings = scan_replay_source_bytes(
            "bad.py",
            b"from rcp_rclm_runtime.generator.process import run_reference_generator_process\n",
        )
        self.assertTrue(findings)
        self.assertEqual(findings[0].code, "REPLAY_FORBIDDEN_IMPORT")

    def test_core_replay_rejects_a_forbidden_generator_capability(self) -> None:
        rejected_guard = ReplaySourceGuardReport(
            file_hashes=FrozenHashMap.from_mapping(
                {"bad.py": "1" * 64},
                "phase8_test.file_hashes",
            ),
            findings=(
                ReplaySourceFinding(
                    code="REPLAY_FORBIDDEN_IMPORT",
                    path="bad.py",
                    line=1,
                    detail="rcp_rclm_runtime.generator.process",
                ),
            ),
        )
        with patch(
            "rcp_rclm_runtime.replay.reproduce.guard_independent_replay_source",
            return_value=rejected_guard,
        ):
            evidence = reproduce_phase8_bundle(
                self.clean_bundle,
                self.fresh_path("source-guard-rejected"),
                fixture_lean_evidence,
            )
        self.assertFalse(evidence.report.accepted)
        self.assertEqual(
            evidence.report.reason_codes,
            (Phase8ReasonCode.GENERATOR_INVOCATION_DETECTED,),
        )
        self.assertIsNone(evidence.output_root)

    def test_unknown_bundle_entry_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("unknown-entry"))
        (tampered / "unknown.bin").write_bytes(b"unknown")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_noncanonical_manifest_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("noncanonical"))
        value = json.loads((tampered / PHASE8_MANIFEST_NAME).read_text(encoding="utf-8"))
        (tampered / PHASE8_MANIFEST_NAME).write_text(
            json.dumps(value, indent=2),
            encoding="utf-8",
        )
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_raw_generator_output_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("generator-output-tamper"))
        target = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "first_generator_stdout.bin"
            )
        )
        target.write_bytes(target.read_bytes() + b"\n")
        evidence = reproduce_phase8_bundle(
            tampered,
            self.fresh_path("generator-output-tamper-replay"),
            fixture_lean_evidence,
        )
        self.assertFalse(evidence.report.accepted)
        self.assertEqual(
            evidence.report.reason_codes,
            (Phase8ReasonCode.BUNDLE_HASH_MISMATCH,),
        )

    def test_predecessor_package_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("predecessor-tamper"))
        state = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "packages").rglob(
                "predecessor/payload/state/rclm_state.json"
            )
        )
        state.write_bytes(state.read_bytes() + b"\n")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_candidate_package_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("candidate-tamper"))
        candidate = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "candidate/payload/policies/verification_policy.json"
            )
        )
        candidate.write_bytes(candidate.read_bytes() + b"\n")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_evaluation_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("evaluation-tamper"))
        evaluation = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "evidence/evaluation.json"
            )
        )
        evaluation.write_bytes(evaluation.read_bytes() + b"\n")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_certificate_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("certificate-tamper"))
        certificate = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "evidence/certificate.json"
            )
        )
        certificate.write_bytes(certificate.read_bytes() + b"\n")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_checker_report_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("checker-tamper"))
        report = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "evidence/hardened_checker_report.json"
            )
        )
        report.write_bytes(report.read_bytes() + b"\n")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_resource_evidence_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("resource-tamper"))
        resource = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "candidate/evidence/resources.json"
            )
        )
        resource.write_bytes(resource.read_bytes() + b"\n")
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_rollback_archive_tampering_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("rollback-tamper"))
        archive = next(
            (tampered / PHASE8_STORE_DIRECTORY_NAME / "runs").rglob(
                "candidate/rollback/predecessor.tar"
            )
        )
        data = bytearray(archive.read_bytes())
        data[0] ^= 1
        archive.write_bytes(bytes(data))
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_parent_hash_substitution_is_rejected(self) -> None:
        tampered = copy_bundle(self.clean_bundle, self.fresh_path("parent-tamper"))
        manifest = next(
            path
            for path in (tampered / PHASE8_STORE_DIRECTORY_NAME / "packages").rglob(
                "manifest.json"
            )
            if b'"status":"promoted"' in path.read_bytes()
        )
        value = load_json_strict(manifest.read_bytes(), require_canonical=True)
        self.assertIsInstance(value, dict)
        value["parent_package_hash"] = "f" * 64
        manifest.write_bytes(canonical_json_bytes(value))
        with self.assertRaises(Phase8BundleError):
            verify_phase8_replay_bundle(tampered)

    def test_rejected_source_attempts_are_reproduced_as_expected_outcomes(self) -> None:
        evidence = reproduce_phase8_bundle(
            self.clean_bundle,
            self.fresh_path("rejection-replay"),
            fixture_lean_evidence,
        )
        source_events = [attempt.ledger_event for attempt in self.clean_manifest.attempts]
        self.assertEqual(source_events[-2:], ["rejection", "rejection"])
        replay_attempts = evidence.report.attempts[-2:]
        self.assertTrue(all(attempt.verdict == "accept" for attempt in replay_attempts))
        for attempt in replay_attempts:
            stages = {stage.stage: stage for stage in attempt.stages}
            self.assertEqual(stages["selection_outcome"].status, "pass")
            self.assertEqual(stages["parent_link"].status, "pass")

    def test_rejected_lean_replay_is_fail_closed(self) -> None:
        evidence = reproduce_phase8_bundle(
            self.clean_bundle,
            self.fresh_path("rejected-lean"),
            fixture_rejected_lean_evidence,
        )
        self.assertFalse(evidence.report.accepted)
        self.assertIn(Phase8ReasonCode.LEAN_REPLAY_FAILED, evidence.report.reason_codes)

    def test_semantically_different_lean_evidence_is_rejected(self) -> None:
        evidence = reproduce_phase8_bundle(
            self.clean_bundle,
            self.fresh_path("mismatch-lean"),
            fixture_semantic_mismatch_lean_evidence,
        )
        self.assertFalse(evidence.report.accepted)
        self.assertIn(Phase8ReasonCode.LEAN_REPLAY_FAILED, evidence.report.reason_codes)

    def test_bundle_builder_refuses_existing_output(self) -> None:
        output = self.fresh_path("existing-bundle")
        output.mkdir()
        source_store = self.clean_bundle / PHASE8_STORE_DIRECTORY_NAME
        with self.assertRaises(Phase8BundleError):
            build_phase8_replay_bundle(source_store, output)


if __name__ == "__main__":
    unittest.main()
