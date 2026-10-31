"""Phase 17B unit tests. Historical archives are exercised separately by the CLI.

The fixture binds exact published identities but is not a substitute for the
three-archive reopening test. No test claims fresh Lean or Phase 17 closure.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v5.phase17 import bootstrap as b
from rcp_rclm_runtime_v5.phase17.controller import ControlError, FAMILIES
from rcp_rclm_runtime_v5.phase17.objectives import (
    ObjectiveDecision, freeze_bootstrap_objective,
    select_bootstrap_objective, verify_bootstrap_objective,
)

FIXTURE = Path(__file__).parent / "fixtures/phase16_bootstrap_handoff.json"
NONCE = "8" * 64


def fixture() -> b.HistoricalPredecessor:
    record = json.loads(FIXTURE.read_text(encoding="utf-8"))
    weights = bytearray(65536)
    for index, value in record["planner_projection"]:
        struct.pack_into("<h", weights, index * 2, value)
    return b.HistoricalPredecessor(canonical_json_bytes(record["state"]),
        tuple(canonical_json_bytes(p) for p in record["programs"]), bytes(weights),
        canonical_json_bytes(record["catalog"]), canonical_json_bytes(record["receipt"]))


def rebound(record: dict) -> bytes:
    record = dict(record)
    record.pop("report_hash", None)
    record["report_hash"] = canonical_json_hash(record)
    return canonical_json_bytes(record)


def raw_name_archive(name: str) -> bytes:
    """Keep malformed local/central header names identical on every host.

    writestr(name, ...) first constructs ZipInfo and may sanitize the name.
    Replace a same-length ASCII placeholder *after* serialization instead.
    Both names change; offsets, payload bytes and CRC remain valid.
    """
    raw_name = name.encode("ascii")
    placeholder = b"Q" * len(raw_name)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(zipfile.ZipInfo(placeholder.decode("ascii")), b"payload")
    data = buffer.getvalue()
    if not raw_name or data.count(placeholder) != 2:
        raise AssertionError("fixture must contain exactly two placeholder header names")
    return data.replace(placeholder, raw_name)


class HistoricalBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.parent = fixture()

    def test_exact_anchored_state_and_weights(self):
        self.assertEqual(canonical_json_hash(self.parent.state), b.SELECTED_STATE_HASH)
        self.assertEqual(hashlib.sha256(self.parent.planner_weights).hexdigest(), b.WEIGHTS_SHA256)
        self.assertEqual(len(self.parent.planner_projection), 84)
        self.assertEqual(len(self.parent.accepted_programs), 8)

    def test_catalog_preserves_all_terminal_identities(self):
        terminals = self.parent.catalog["terminals"]
        self.assertEqual(len(terminals), 17)
        self.assertEqual(len({t["report_hash"] for t in terminals}), 17)
        self.assertEqual(len({t["final_state_hash"] for t in terminals}), 17)
        self.assertEqual(sum(t["target_promotions"] for t in terminals), 580)
        self.assertFalse(self.parent.catalog["egc0_evaluation_performed"])

    def test_no_fresh_verification_or_promotion_claim(self):
        for key in ("phase17_exit_closed", "gate_e_closed", "fresh_lean_verification",
                    "fresh_full_tensor_execution", "phase18_independent_replay",
                    "promotion_authorized", "egc0_started"):
            self.assertIs(self.parent.receipt[key], False)

    def test_state_is_detached_on_access(self):
        state = self.parent.state
        state["component_generations"]["planner_policy"] = 999
        state["capability_frontier"].clear()
        self.parent.validate()
        self.assertEqual(self.parent.state["component_generations"]["planner_policy"], 1)

    def test_substituted_terminal_state_rejected(self):
        state = self.parent.state
        state["active_package_hash"] = "0" * 64
        with self.assertRaises(ControlError):
            replace(self.parent, state_bytes=canonical_json_bytes(state))

    def test_substituted_planner_bytes_rejected(self):
        data = bytearray(self.parent.planner_weights)
        data[0] ^= 1
        with self.assertRaises(ControlError):
            replace(self.parent, planner_weights=bytes(data))

    def test_reordered_installed_programs_rejected(self):
        with self.assertRaises(ControlError):
            replace(self.parent, accepted_programs=self.parent.accepted_programs[::-1])

    def test_rehashed_catalog_substitution_rejected(self):
        catalog = self.parent.catalog
        catalog["terminals"].pop()
        receipt = self.parent.receipt
        receipt["catalog_hash"] = canonical_json_hash(catalog)
        with self.assertRaises(ControlError):
            replace(self.parent, catalog_bytes=canonical_json_bytes(catalog), receipt_bytes=rebound(receipt))

    def test_rehashed_closure_claim_rejected(self):
        for key in ("phase17_exit_closed", "gate_e_closed", "fresh_lean_verification",
                    "fresh_full_tensor_execution", "phase18_independent_replay", "promotion_authorized"):
            with self.subTest(key=key):
                receipt = self.parent.receipt
                receipt[key] = True
                with self.assertRaises(ControlError):
                    replace(self.parent, receipt_bytes=rebound(receipt))

    def test_rehashed_source_identity_rejected(self):
        receipt = self.parent.receipt
        receipt["source_head"] = "0" * 40
        with self.assertRaises(ControlError):
            replace(self.parent, receipt_bytes=rebound(receipt))

    def test_noncanonical_state_rejected(self):
        with self.assertRaises(ControlError):
            replace(self.parent, state_bytes=self.parent.state_bytes + b"\n")

    def test_noncanonical_receipt_rejected(self):
        with self.assertRaises(ControlError):
            replace(self.parent, receipt_bytes=self.parent.receipt_bytes + b"\n")

    def test_noncanonical_catalog_rejected(self):
        with self.assertRaises(ControlError):
            replace(self.parent, catalog_bytes=self.parent.catalog_bytes + b"\n")

    def test_mutable_buffers_rejected(self):
        with self.assertRaises(ControlError):
            replace(self.parent, planner_weights=bytearray(self.parent.planner_weights))

    def test_state_shape_and_bool_counts_rejected(self):
        state = self.parent.state
        state["component_generations"]["planner_policy"] = True
        with self.assertRaises(ControlError):
            b.validate_state(state)
        state = self.parent.state
        state["future_promotions"] = 100
        with self.assertRaises(ControlError):
            b.validate_state(state)

    def test_duplicate_and_float_json_rejected(self):
        for data in (b'{"a":1,"a":2}', b'{"x":1.5}', b'{"x":NaN}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                b._json(data)

    def test_changed_archive_rejected_before_zip_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.zip"
            path.write_bytes(b"not the historical archive")
            with self.assertRaisesRegex(ControlError, "digest mismatch"):
                b._read_pinned_archive(path, b.CAPTURE_SHA256)

    def test_archive_ingestion_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversize.zip"
            path.write_bytes(b"abc")
            with self.assertRaisesRegex(ControlError, "ingestion bound"):
                b._read_pinned_archive(path, hashlib.sha256(b"abc").hexdigest(), max_bytes=2)

    def test_archive_path_traversal_rejected(self):
        for name in ("../escape", "/absolute", "C:/drive", "back\\slash", "nul\x00name"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.zip"
                data = raw_name_archive(name)
                path.write_bytes(data)
                with self.assertRaisesRegex(ControlError, "nonportable"):
                    b._read_pinned_archive(path, hashlib.sha256(data).hexdigest())

    def test_archive_fixture_retains_original_header_name(self):
        for name in ("../escape", "/absolute", "C:/drive", "back\\slash", "nul\x00name"):
            with self.subTest(name=name):
                data = raw_name_archive(name)
                self.assertEqual(data.count(name.encode("ascii")), 2)
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    self.assertEqual(archive.infolist()[0].orig_filename, name)

    def test_archive_windows_normalization_cannot_hide_bad_name(self):
        from unittest.mock import patch
        original_init = zipfile.ZipInfo.__init__

        def windows_init(info, filename="NoName", date_time=(1980, 1, 1, 0, 0, 0)):
            original_init(info, filename, date_time)
            # Model only ZipInfo's Windows normalization, not the whole OS.
            info.filename = filename.split("\x00", 1)[0].replace("\\", "/")

        for name in ("back\\slash", "nul\x00name"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                data = raw_name_archive(name)
                path = Path(directory) / "bad.zip"
                path.write_bytes(data)
                with patch.object(zipfile.ZipInfo, "__init__", windows_init):
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        info = archive.infolist()[0]
                        self.assertEqual(info.orig_filename, name)
                        self.assertNotEqual(info.filename, info.orig_filename)
                    with self.assertRaisesRegex(ControlError, "nonportable"):
                        b._read_pinned_archive(path, hashlib.sha256(data).hexdigest())

    def test_archive_valid_nested_member_accepted(self):
        from unittest.mock import patch
        original_init = zipfile.ZipInfo.__init__

        def windows_init(info, filename="NoName", date_time=(1980, 1, 1, 0, 0, 0)):
            original_init(info, filename, date_time)
            info.filename = filename.split("\x00", 1)[0].replace("\\", "/")

        for windows_model in (False, True):
            with self.subTest(windows_model=windows_model), tempfile.TemporaryDirectory() as directory:
                data = raw_name_archive("safe/nested")
                path = Path(directory) / "good.zip"
                path.write_bytes(data)
                initializer = windows_init if windows_model else original_init
                with patch.object(zipfile.ZipInfo, "__init__", initializer):
                    with b._read_pinned_archive(path, hashlib.sha256(data).hexdigest()) as archive:
                        self.assertEqual(b._member(archive, "safe/nested", 32), b"payload")

    def test_archive_duplicate_member_rejected(self):
        import warnings
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(path, "w") as z:
                    z.writestr("same", b"a")
                    z.writestr("same", b"b")
            with self.assertRaisesRegex(ControlError, "duplicate"):
                b._read_pinned_archive(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_archive_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.zip"
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            with zipfile.ZipFile(path, "w") as z:
                z.writestr(info, b"target")
            with self.assertRaisesRegex(ControlError, "symlink"):
                b._read_pinned_archive(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_reopen_interface_has_no_caller_trust_override(self):
        self.assertEqual(set(inspect.signature(b.reopen_phase16).parameters),
                         {"capture_archive", "closure_archive", "phase15_bundle"})


class ObjectiveTests(unittest.TestCase):
    def setUp(self):
        self.parent = fixture()
        self.decision = select_bootstrap_objective(self.parent, turn_index=0, public_nonce_hash=NONCE)

    def test_repeatable_complete_eight_family_ranking(self):
        other = select_bootstrap_objective(self.parent, turn_index=0, public_nonce_hash=NONCE)
        self.assertEqual(other, self.decision)
        self.assertEqual({r["family"] for r in other.to_json()["ranked_objectives"]}, set(FAMILIES))
        self.assertIs(other.to_json()["promotion_authorized"], False)

    def test_no_horizon_route_seed_or_score_inputs(self):
        self.assertEqual(set(inspect.signature(select_bootstrap_objective).parameters),
                         {"predecessor", "turn_index", "public_nonce_hash"})
        for field in ("future_horizon", "successful_route", "evaluator_seed", "egc_score", "target_family"):
            with self.subTest(field=field), self.assertRaises(TypeError):
                select_bootstrap_objective(self.parent, turn_index=0, public_nonce_hash=NONCE, **{field: 1})

    def test_present_index_and_nonce_validation(self):
        for index in (-1, True, 1.2):
            with self.subTest(index=index), self.assertRaises(ValueError):
                select_bootstrap_objective(self.parent, turn_index=index, public_nonce_hash=NONCE)
        with self.assertRaises(ControlError):
            select_bootstrap_objective(self.parent, turn_index=0, public_nonce_hash="not-a-digest")

    def test_unverified_state_dict_is_not_a_bootstrap(self):
        with self.assertRaises(ControlError):
            select_bootstrap_objective(self.parent.state, turn_index=0, public_nonce_hash=NONCE)

    def test_current_nonce_and_turn_are_bound(self):
        for turn, nonce in ((1, NONCE), (0, "9" * 64)):
            with self.subTest(turn=turn), self.assertRaises(ControlError):
                verify_bootstrap_objective(self.decision, self.parent, turn_index=turn, public_nonce_hash=nonce)

    def test_forged_rank_rejected_by_recomputation(self):
        value = self.decision.to_json()
        value["ranked_objectives"][0]["score"] += 1
        forged = ObjectiveDecision(canonical_json_bytes(value))
        with self.assertRaises(ControlError):
            verify_bootstrap_objective(forged, self.parent, turn_index=0, public_nonce_hash=NONCE)

    def test_forged_objective_winner_rejected(self):
        value = self.decision.to_json()
        value["ranked_objectives"].reverse()
        value["objective_family"] = value["ranked_objectives"][0]["family"]
        forged = ObjectiveDecision(canonical_json_bytes(value))
        with self.assertRaises(ControlError):
            verify_bootstrap_objective(forged, self.parent, turn_index=0, public_nonce_hash=NONCE)

    def test_future_field_smuggling_rejected(self):
        value = self.decision.to_json()
        value["terminal_package_hash"] = "f" * 64
        with self.assertRaises(ControlError):
            ObjectiveDecision(canonical_json_bytes(value))

    def test_forged_promotion_authority_rejected(self):
        value = self.decision.to_json()
        value["promotion_authorized"] = True
        with self.assertRaises(ControlError):
            ObjectiveDecision(canonical_json_bytes(value))

    def test_freeze_binds_exact_decision_without_challenge_claim(self):
        freeze = freeze_bootstrap_objective(self.decision, self.parent, turn_index=0, public_nonce_hash=NONCE)
        digest = freeze.pop("freeze_hash")
        self.assertEqual(digest, canonical_json_hash(freeze))
        self.assertEqual(freeze["objective_decision_hash"], self.decision.decision_hash)
        self.assertFalse(freeze["challenge_bound"])
        self.assertFalse(freeze["promotion_authorized"])

    def test_serialized_payload_has_no_hidden_answer_or_future_route(self):
        value = self.decision.to_json()
        for key in ("target_program_hash", "target_output_hash", "hidden_seed", "future_horizon", "successful_route"):
            self.assertNotIn(key, value)

    def test_hash_seed_does_not_change_objective(self):
        script = ("import sys;sys.path.insert(0,sys.argv[1]);"
                  "from test_bootstrap_objectives import fixture,NONCE;"
                  "from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective;"
                  "print(select_bootstrap_objective(fixture(),turn_index=0,public_nonce_hash=NONCE).decision_hash)")
        results = [subprocess.check_output([sys.executable, "-c", script, str(FIXTURE.parent.parent)],
                    env=dict(os.environ, PYTHONHASHSEED=seed), text=True).strip()
                   for seed in ("1", "23")]
        self.assertEqual(results, [self.decision.decision_hash] * 2)


if __name__ == "__main__":
    unittest.main()
