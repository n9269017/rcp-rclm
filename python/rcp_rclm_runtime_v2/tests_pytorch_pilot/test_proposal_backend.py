from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rcp_rclm_runtime.successor.record_selection import Phase6SelectionRecord
from rcp_rclm_runtime.torch_backend import proposal_backend as backend

MODULE_PATH = Path(backend.__file__).resolve()


class PilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pytorch-pilot-tests-")
        self.root = Path(self.temp.name)
        self.predecessor = self.root / "predecessor"
        backend.initialize_predecessor_model(self.predecessor)
        self.request = backend.make_default_request(
            transition_id="pytorch.pilot.test",
            predecessor_package_id="pytorch.pilot.test.predecessor",
            predecessor_manifest_hash="1" * 64,
            phase5_predecessor_manifest_hash="2" * 64,
            predecessor_payload_tree_hash="3" * 64,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_exactly_one_weight_update_and_exact_evaluation(self) -> None:
        artifacts = backend.run_proposal_backend(
            self.request,
            self.predecessor,
            self.root / "proposal",
        )
        self.assertNotEqual(
            artifacts.proposal["predecessor_model_hash"],
            artifacts.proposal["candidate_model_hash"],
        )
        self.assertEqual(artifacts.proposal["optimizer_steps"], 1)
        evaluation = backend.evaluate_proposal_exact(
            artifacts.output_root,
            backend.fixed_heldout_evaluation_data(),
            self.root / "evaluation.json",
        )
        self.assertTrue(evaluation.result["objective_improved"])
        self.assertTrue(evaluation.result["protected_nonregression"])
        self.assertTrue(evaluation.result["evaluation_conditions_met"])
        self.assertEqual(evaluation.result["before"]["correct_count"], 2)
        self.assertEqual(evaluation.result["after"]["correct_count"], 4)
        self.assertFalse(evaluation.result["torch_used_for_evaluation"])

    def test_phase6_selection_contains_genuine_model_weight_operations(self) -> None:
        artifacts = backend.run_proposal_backend(
            self.request,
            self.predecessor,
            self.root / "proposal",
        )
        operations = artifacts.phase6_selection["operations"]
        paths = [item["path"] for item in operations]
        self.assertEqual(paths, sorted(paths, key=lambda item: item.encode("utf-8")))
        weight_ops = [item for item in operations if item["component_kind"] == "model_weights"]
        self.assertEqual(len(weight_ops), 1)
        self.assertEqual(weight_ops[0]["path"], backend.MODEL_WEIGHT_PATH)
        self.assertEqual(
            artifacts.phase6_selection["substantive_component_kinds"],
            ["model_weights"],
        )
        parsed = Phase6SelectionRecord.from_json(artifacts.phase6_selection)
        self.assertEqual(parsed.selection_hash, backend._canonical_hash(artifacts.phase6_selection))

    def test_proposal_does_not_self_certify_or_report_acceptance(self) -> None:
        artifacts = backend.run_proposal_backend(
            self.request,
            self.predecessor,
            self.root / "proposal",
        )
        self.assertIsNone(artifacts.proposal["candidate_reported_acceptance"])
        self.assertIsNone(artifacts.proposal["candidate_reported_certificate"])
        self.assertIsNone(artifacts.proposal["candidate_reported_aggregate_score"])

    def test_rng_state_is_reset_before_the_nonstochastic_update(self) -> None:
        artifacts = backend.run_proposal_backend(
            self.request,
            self.predecessor,
            self.root / "proposal",
        )
        rng = backend._load_canonical_json(
            artifacts.output_root / "files" / backend.RNG_MANIFEST_PATH
        )
        self.assertEqual(
            rng["torch_rng_before_sha256"],
            rng["torch_rng_after_sha256"],
        )

    def test_importing_backend_does_not_import_torch(self) -> None:
        command = [
            sys.executable,
            "-c",
            (
                "import sys; import rcp_rclm_runtime.torch_backend.proposal_backend; "
                'print(int("torch" in sys.modules))'
            ),
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=dict(os.environ),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(completed.stdout.splitlines(), [b"0"])

    def test_predecessor_is_not_mutated(self) -> None:
        before = self._tree_hash(self.predecessor)
        backend.run_proposal_backend(
            self.request,
            self.predecessor,
            self.root / "proposal",
        )
        after = self._tree_hash(self.predecessor)
        self.assertEqual(before, after)

    def test_request_rejects_heldout_labels(self) -> None:
        value = self.request.to_json()
        value["heldout_labels"] = [0, 0, 1, 1]
        with self.assertRaises(backend.BackendError):
            backend.BackendRequest.from_json(value)

    def test_existing_output_fails_closed(self) -> None:
        output = self.root / "proposal"
        output.mkdir()
        with self.assertRaises(backend.BackendError):
            backend.run_proposal_backend(self.request, self.predecessor, output)

    def test_tampered_predecessor_is_rejected(self) -> None:
        target = self.predecessor / backend.MODEL_WEIGHT_PATH
        target.write_bytes(target.read_bytes() + b"\x00")
        with self.assertRaises(backend.BackendError):
            backend.run_proposal_backend(
                self.request,
                self.predecessor,
                self.root / "proposal",
            )

    def test_two_fresh_processes_emit_identical_semantic_results(self) -> None:
        request_path = self.root / "request.json"
        request_path.write_bytes(backend._canonical_bytes(self.request.to_json()))
        outputs: list[object] = []
        for index in range(2):
            output = self.root / f"proposal-{index}"
            command = [
                sys.executable,
                str(MODULE_PATH),
                "propose",
                "--request",
                str(request_path),
                "--predecessor-root",
                str(self.predecessor),
                "--output-root",
                str(output),
            ]
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
                env=dict(os.environ),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
            outputs.append(json.loads(completed.stdout))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(
            (self.root / "proposal-0" / "manifest.json").read_bytes(),
            (self.root / "proposal-1" / "manifest.json").read_bytes(),
        )
        self.assertEqual(
            self._tree_hash(self.root / "proposal-0" / "files"),
            self._tree_hash(self.root / "proposal-1" / "files"),
        )

    @staticmethod
    def _tree_hash(root: Path) -> str:
        digest = hashlib.sha256()
        paths = sorted(
            (item for item in root.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(root).as_posix(),
        )
        for path in paths:
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\x00")
            digest.update(path.read_bytes())
            digest.update(b"\x00")
        return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
