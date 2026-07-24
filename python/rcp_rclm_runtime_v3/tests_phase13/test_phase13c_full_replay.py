from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase12.phase12b_closure import (
    PHASE12B_CONTROLLER_ENVIRONMENT_HASH,
    phase12b_phase7_policy,
)
from rcp_rclm_runtime_v3.phase12.phase12c_closure import (
    PHASE12C_CONTROLLER_ENVIRONMENT_HASH,
)
from rcp_rclm_runtime_v3.phase12.phase12d_closure import (
    PHASE12D_CONTROLLER_ENVIRONMENT_HASH,
)
from rcp_rclm_runtime_v3.phase12.phase12e_closure import (
    PHASE12E_CONTROLLER_ENVIRONMENT_HASH,
)
from rcp_rclm_runtime_v3.phase13.closure import close_phase13
from rcp_rclm_runtime_v3.phase13.full_records import (
    Phase13CheckRecord,
    Phase13ExitReport,
    Phase13PinnedReplayReport,
)
from rcp_rclm_runtime_v3.phase13.pinned_replay import (
    _checker_semantic_fingerprint,
    _environment_hash,
    _lean_semantic_fingerprint,
)
from rcp_rclm_runtime_v3.phase13.source import discover_repository_head
from rcp_rclm_runtime_v3.phase13.store_replay import _phase13_controller_policy


def _write_entry(path: Path, payload: dict[str, object]) -> None:
    payload["entry_hash"] = canonical_json_hash(payload)
    path.write_bytes(canonical_json_bytes(payload))


class Phase13CFullReplayTests(unittest.TestCase):
    def test_independent_environment_and_policy_constants_match_phase12(self) -> None:
        self.assertEqual(_environment_hash("M1"), PHASE12B_CONTROLLER_ENVIRONMENT_HASH)
        self.assertEqual(_environment_hash("M2"), PHASE12C_CONTROLLER_ENVIRONMENT_HASH)
        self.assertEqual(_environment_hash("M3"), PHASE12D_CONTROLLER_ENVIRONMENT_HASH)
        self.assertEqual(_environment_hash("M4"), PHASE12E_CONTROLLER_ENVIRONMENT_HASH)
        self.assertEqual(
            _phase13_controller_policy().policy_hash,
            phase12b_phase7_policy().policy_hash,
        )

    def test_semantic_fingerprints_remove_only_nondeterministic_bindings(self) -> None:
        lean_a = {
            "compiler_duration_ms": 1,
            "toolchain_runtime_hash": "0" * 64,
            "stable": "value",
        }
        lean_b = {
            "compiler_duration_ms": 999,
            "toolchain_runtime_hash": "1" * 64,
            "stable": "value",
        }
        self.assertEqual(
            _lean_semantic_fingerprint(lean_a),
            _lean_semantic_fingerprint(lean_b),
        )
        checker_a = {
            "checker_report": {
                "artifact_hashes": {"a": "0" * 64},
                "lean_bridge_result": {"evidence": {
                    "report_hash": "1" * 64,
                    "toolchain_runtime_hash": "4" * 64,
                    "x": 1,
                }},
                "stable": True,
            }
        }
        checker_b = {
            "checker_report": {
                "artifact_hashes": {"a": "2" * 64},
                "lean_bridge_result": {"evidence": {
                    "report_hash": "3" * 64,
                    "toolchain_runtime_hash": "5" * 64,
                    "x": 1,
                }},
                "stable": True,
            }
        }
        self.assertEqual(
            _checker_semantic_fingerprint(checker_a),
            _checker_semantic_fingerprint(checker_b),
        )

    def test_pinned_and_exit_claim_boundaries_are_derived(self) -> None:
        record = Phase13CheckRecord(
            record_id="record",
            checks={"closed": True},
            evidence_hashes={"evidence": "0" * 64},
        )
        pinned = Phase13PinnedReplayReport(
            source_head="a" * 40,
            bundle_manifest_hash="1" * 64,
            phase13a_report_hash="2" * 64,
            structural_report_hash="3" * 64,
            store_records=(record,),
            task_records=(record,),
            hardened_records=(record,),
            boundary_checks={"closed": True},
        )
        self.assertTrue(pinned.phase13c_slice_closed)
        self.assertFalse(pinned.phase13_exit_closed)
        exit_report = Phase13ExitReport(
            source_head="a" * 40,
            bundle_manifest_hash="1" * 64,
            phase13a_report_hash="2" * 64,
            structural_report_hash="3" * 64,
            pinned_report_hash=pinned.report_hash,
            pinned_entry_hashes={
                "macos": "7" * 64,
                "ubuntu": "8" * 64,
                "windows": "9" * 64,
            },
            portable_entry_hashes={
                "macos": "4" * 64,
                "ubuntu": "5" * 64,
                "windows": "6" * 64,
            },
            closure_checks={"closed": True},
        )
        self.assertTrue(exit_report.phase13_exit_closed)

    def test_cross_platform_aggregator_closes_only_exact_common_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13c-close-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            (repo / ".git").mkdir(parents=True)
            source_head = "a" * 40
            (repo / ".git/HEAD").write_text(source_head + "\n", encoding="utf-8")
            self.assertEqual(discover_repository_head(repo), source_head)
            bundle_hash = "1" * 64
            structural_hash = "2" * 64
            portable_paths: dict[str, Path] = {}
            for platform in ("macos", "ubuntu", "windows"):
                path = root / f"{platform}.json"
                payload = {
                    "schema_id": "runtime.v3.phase13.structural_replay_entry.v1",
                    "platform_label": platform,
                    "source_head": source_head,
                    "bundle_manifest_hash": bundle_hash,
                    "structural_report": {
                        "accepted": True,
                        "phase13b_slice_closed": True,
                        "phase13_exit_closed": False,
                    },
                    "structural_report_hash": structural_hash,
                    "accepted": True,
                    "phase13_exit_closed": False,
                }
                _write_entry(path, payload)
                portable_paths[platform] = path
            pinned_report = {
                "source_head": source_head,
                "accepted": True,
                "phase13c_slice_closed": True,
                "phase13_exit_closed": False,
            }
            pinned_paths: dict[str, Path] = {}
            for platform in ("macos", "ubuntu", "windows"):
                pinned_path = root / f"pinned-{platform}.json"
                pinned_payload = {
                    "schema_id": "runtime.v3.phase13.pinned_replay_entry.v1",
                    "platform_label": platform,
                    "source_head": source_head,
                    "bundle_manifest_hash": bundle_hash,
                    "phase13a_report_hash": "3" * 64,
                    "structural_report_hash": structural_hash,
                    "pinned_report": pinned_report,
                    "pinned_report_hash": canonical_json_hash(pinned_report),
                    "accepted": True,
                    "phase13_exit_closed": False,
                }
                _write_entry(pinned_path, pinned_payload)
                pinned_paths[platform] = pinned_path
            report = close_phase13(
                portable_entries=portable_paths,
                pinned_entries=pinned_paths,
                repo_root=repo,
                expected_source_head=source_head,
            )
            self.assertTrue(report.phase13_exit_closed)


if __name__ == "__main__":
    unittest.main()
