"""Ten integration checks against the exact historical Phase 16/M9 archives.

No archive extraction, network, Lean execution, fresh campaign, or promotion.
All three supplied/default inputs must match the fixed bootstrap digests.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-archive", type=Path)
    parser.add_argument("--closure-archive", type=Path)
    parser.add_argument("--phase15-bundle", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / "python" / f"rcp_rclm_runtime_v{v}") for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
    from rcp_rclm_runtime_v5.phase17 import bootstrap as b
    from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective

    capture = args.capture_archive or root / "artifacts/development/phase17b/phase16-capture-31153935872-1.zip"
    closure = args.closure_archive or root / (
        "artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/"
        "runtime-v4-phase16-final-closure-31153935872-1.zip")
    bundle = args.phase15_bundle or root / (
        "artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip")

    class HistoricalArchiveIntegration(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.parent = b.reopen_phase16(capture_archive=capture,
                                          closure_archive=closure, phase15_bundle=bundle)
            # Read the same archive through the pinned/bounded ingestion helpers.
            with b._read_pinned_archive(capture, b.CAPTURE_SHA256) as archive:
                cls.campaign = b._json(b._member(archive, "reference_campaign.json", 2 * 1024 * 1024))

        def tampered(self, mutate):
            c = copy.deepcopy(self.campaign)
            mutate(c)
            del c["report_hash"]
            c["report_hash"] = canonical_json_hash(c)
            with self.assertRaises((ValueError, KeyError)):
                b.validate_selected_lineage(c)

        def test_reopen_real_archives(self):
            self.parent.validate()
            self.assertEqual(self.parent.state["model_index"], 17)
            self.assertEqual(len(self.parent.accepted_programs), 8)
            self.assertEqual(len(self.parent.catalog["terminals"]), 17)

        def test_real_program_registry_reconstruction(self):
            self.assertEqual(b.validate_selected_lineage(self.campaign), self.parent.accepted_programs)

        def test_rehashed_archive_record_mutation(self):
            self.tampered(lambda c: c["archive"]["records"][0]["payload"].update(answer_visible=True))

        def test_rehashed_archive_parent_substitution(self):
            self.tampered(lambda c: c["archive"]["records"][0].update(parent_record_hash="0" * 64))

        def test_rehashed_terminal_substitution(self):
            self.tampered(lambda c: c["final_state"].update(active_package_hash="0" * 64))

        def test_rehashed_transition_payload_substitution(self):
            self.tampered(lambda c: c["transitions"][0]["accepted_program"].update(parameter_a=0))

        def test_rehashed_transition_order(self):
            self.tampered(lambda c: c["transitions"].reverse())

        def test_rehashed_archive_suffix(self):
            self.tampered(lambda c: c["archive"]["records"].pop())

        def test_real_objective_freeze(self):
            d = select_bootstrap_objective(self.parent, turn_index=0, public_nonce_hash="8" * 64)
            freeze = freeze_bootstrap_objective(d, self.parent, turn_index=0, public_nonce_hash="8" * 64)
            self.assertFalse(freeze["challenge_bound"])
            self.assertFalse(freeze["promotion_authorized"])

        def test_fixture_matches_real_reopening(self):
            fixture = b._json((root / "python/rcp_rclm_runtime_v5/tests_phase17/fixtures/"
                              "phase16_bootstrap_handoff.json").read_bytes())
            self.assertEqual(fixture["state"], self.parent.state)
            self.assertEqual(fixture["receipt"], self.parent.receipt)
            self.assertEqual(fixture["catalog"], self.parent.catalog)
            self.assertEqual(fixture["programs"], [b._json(p) for p in self.parent.accepted_programs])

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HistoricalArchiveIntegration)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("Historical archive integration only; fresh Lean: false; Phase17 exit: false; Gate E: false")
    return 0 if result.wasSuccessful() and result.testsRun == 10 and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
