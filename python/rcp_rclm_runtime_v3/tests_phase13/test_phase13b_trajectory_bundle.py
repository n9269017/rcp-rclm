from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase13.boundary import guard_phase13_replay_source
from rcp_rclm_runtime_v3.phase13.bundle import (
    Phase13BundleError,
    build_phase13_trajectory_bundle,
    materialize_phase13_empty_directories,
    verify_phase13_trajectory_bundle,
)
from rcp_rclm_runtime_v3.phase13.full_records import (
    Phase13CheckRecord,
    Phase13TrajectoryBundleManifest,
)


class Phase13BTrajectoryBundleTests(unittest.TestCase):
    def test_bundle_is_content_addressed_and_tamper_evident(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13b-bundle-") as temporary:
            root = Path(temporary)
            work = root / "work"
            for name in ("promotion_evidence", "reference", "store"):
                target = work / name
                target.mkdir(parents=True)
                (target / "evidence.json").write_bytes(
                    canonical_json_bytes({"schema_id": f"runtime.v3.phase13.test_{name}.v1"})
                )
            (work / "store/runs").mkdir()
            closure = {
                "accepted": True,
                "phase12_exit_closed": True,
                "schema_id": "runtime.v3.phase12e.closure_report.v1",
            }
            closure["report_hash"] = canonical_json_hash(closure)
            closure_path = root / "phase12_closure.json"
            closure_path.write_bytes(canonical_json_bytes(closure))
            bundle = root / "bundle"
            manifest = build_phase13_trajectory_bundle(
                work,
                closure_path,
                bundle,
                source_head="a" * 40,
            )
            self.assertEqual(verify_phase13_trajectory_bundle(bundle), manifest)
            self.assertIn("trajectory/store/runs", manifest.empty_directories)
            (bundle / "trajectory/store/runs").rmdir()
            self.assertEqual(verify_phase13_trajectory_bundle(bundle), manifest)
            self.assertEqual(materialize_phase13_empty_directories(bundle), manifest)
            self.assertTrue((bundle / "trajectory/store/runs").is_dir())
            reparsed = Phase13TrajectoryBundleManifest.from_json(manifest.to_json())
            self.assertEqual(reparsed, manifest)
            tampered = bundle / "trajectory/reference/evidence.json"
            tampered.write_bytes(tampered.read_bytes() + b"\n")
            with self.assertRaises(Phase13BundleError):
                verify_phase13_trajectory_bundle(bundle)

    def test_undeclared_empty_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13b-empty-") as temporary:
            root = Path(temporary)
            work = root / "work"
            for name in ("promotion_evidence", "reference", "store"):
                target = work / name
                target.mkdir(parents=True)
                (target / "evidence.json").write_bytes(
                    canonical_json_bytes({"schema_id": f"runtime.v3.phase13.test_{name}.v1"})
                )
            (work / "store/runs").mkdir()
            closure = {
                "accepted": True,
                "phase12_exit_closed": True,
                "schema_id": "runtime.v3.phase12e.closure_report.v1",
            }
            closure["report_hash"] = canonical_json_hash(closure)
            closure_path = root / "phase12_closure.json"
            closure_path.write_bytes(canonical_json_bytes(closure))
            bundle = root / "bundle"
            build_phase13_trajectory_bundle(
                work,
                closure_path,
                bundle,
                source_head="b" * 40,
            )
            (bundle / "trajectory/reference/undeclared-empty").mkdir()
            with self.assertRaises(Phase13BundleError):
                verify_phase13_trajectory_bundle(bundle)

    def test_check_record_acceptance_is_derived(self) -> None:
        record = Phase13CheckRecord(
            record_id="test.record",
            checks={"a": True, "b": True},
            evidence_hashes={"evidence": "0" * 64},
        )
        self.assertTrue(record.accepted)
        self.assertEqual(Phase13CheckRecord.from_json(record.to_json()), record)

    def test_extended_replay_source_guard_is_clean(self) -> None:
        report = guard_phase13_replay_source()
        self.assertTrue(report.clean)
        self.assertGreaterEqual(len(report.file_hashes), 8)


if __name__ == "__main__":
    unittest.main()
