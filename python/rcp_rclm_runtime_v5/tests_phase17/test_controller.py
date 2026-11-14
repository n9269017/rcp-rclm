"""Control-plane tests use synthetic ranking inputs, not capability evidence."""
from __future__ import annotations

from dataclasses import replace
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v5.phase17.controller import (
    Action, ControlError, CurrentView, FAMILIES, FrozenSearch, Observation,
    RankedCandidate, SearchPrefix, checkpoint, decide, exhaustion_record,
    halt, record_evaluation, restore,
)


def h(value: object) -> str:
    return canonical_json_hash(value)


def fixture(credits: int = 32, offset: int = 0) -> SearchPrefix:
    view = CurrentView(h("state"), h("package"), h("commitment"), h("nonce"), 0, (0,) * 8)
    candidates = tuple(RankedCandidate(h([family, variant]), family, variant,
                                      (index * 13 + variant * 7 + offset) % 101)
                       for index, family in enumerate(FAMILIES) for variant in range(4))
    return SearchPrefix(FrozenSearch(view, candidates), credits)


def outcome(prefix: SearchPrefix, verdict: str = "reject") -> SearchPrefix:
    d = decide(prefix)
    return record_evaluation(prefix, d, verdict=verdict,
        evaluation_hash=h([d.candidate_hash, verdict]),
        reason_codes=("independent_fixture_rejection",) if verdict == "reject" else (),
        predecessor_state_hash=prefix.frozen.view.predecessor_state_hash,
        challenge_commitment_hash=prefix.frozen.view.challenge_commitment_hash)


class ControllerTests(unittest.TestCase):
    def test_no_future_arguments(self):
        self.assertEqual(tuple(inspect.signature(decide).parameters), ("prefix",))
        for name in ("target_promotions", "terminal_package", "future_challenges", "future_seed",
                     "successful_route", "stop_after_promotions"):
            obj = fixture().frozen.view.to_json()
            obj[name] = 100
            with self.subTest(name=name), self.assertRaises(ControlError):
                CurrentView.from_json(obj)

    def test_no_promotion_or_success_action(self):
        self.assertFalse(any("promot" in a.value or a.value == "success" for a in Action))
        p = outcome(fixture(), "candidate_passed")
        self.assertEqual(decide(p).action, Action.AWAIT_ROOT_VERIFICATION)
        self.assertEqual(p.frozen.view.active_package_hash, h("package"))
        self.assertEqual(p.frozen.view.predecessor_state_hash, h("state"))
        with self.assertRaises(ControlError):
            outcome(p)

    def test_partial_budget_is_not_exhaustion(self):
        for credits in (0, 1, 4, 8, 16, 31):
            p = fixture(credits)
            for _ in range(credits):
                p = outcome(p)
            with self.subTest(credits=credits):
                self.assertEqual(decide(p).action, Action.RESOURCE_EXHAUSTED)
                self.assertEqual(p.credits_remaining, 0)
                with self.assertRaises(ControlError):
                    exhaustion_record(p)

    def test_complete_enumeration_exactly_once(self):
        for offset in range(20):
            p = fixture(credits=40, offset=offset)
            while decide(p).action == Action.EVALUATE:
                p = outcome(p)
            self.assertEqual(decide(p).action, Action.SEARCH_EXHAUSTED)
            record = exhaustion_record(p)
            self.assertEqual(len(record["rejected_program_hashes"]), 32)
            self.assertEqual(set(record["rejected_program_hashes"]), set(record["legal_program_hashes"]))
            self.assertTrue(record["requires_independent_evaluation_verification"])
            self.assertFalse(record["phase17_exit_closed"])
            self.assertFalse(record["gate_e_closed"])

    def test_full_search_takes_precedence_over_zero_balance(self):
        p = fixture()
        for _ in range(32):
            p = outcome(p)
        self.assertEqual(p.credits_remaining, 0)
        self.assertEqual(decide(p).action, Action.SEARCH_EXHAUSTED)

    def test_pass_on_last_credit_is_not_resource_exhaustion(self):
        p = outcome(fixture(1), "candidate_passed")
        self.assertEqual(p.credits_remaining, 0)
        self.assertEqual(decide(p).action, Action.AWAIT_ROOT_VERIFICATION)

    def test_bounded_learned_prefix_then_fair_fallback(self):
        p = fixture()
        for _ in range(4):
            p = outcome(p)
        ordered = p.frozen.candidates
        offset = int(p.frozen.freeze_hash[:16], 16) % 32
        fair = [ordered[(offset + i * 17) % 32].program_hash for i in range(32)]
        expected = [x for x in fair if x not in {o.program_hash for o in p.observations}]
        actual = []
        while decide(p).action == Action.EVALUATE:
            actual.append(decide(p).candidate_hash)
            p = outcome(p)
        self.assertEqual(actual, expected)

    def test_rejection_conditions_next_rank(self):
        p = fixture()
        first = decide(p).candidate_hash
        family = next(c.family for c in p.frozen.candidates if c.program_hash == first)
        q = outcome(p)
        selected = next(c for c in q.frozen.candidates if c.program_hash == decide(q).candidate_hash)
        self.assertEqual(selected.family, family)  # Phase 16 positive pressure retained.

    def test_horizon_noninterference(self):
        # These external stopping horizons are never passed to the controller.
        histories = []
        for external_stop_at in (5, 11, 29):
            p = fixture(32)
            prefix_decisions = []
            for _ in range(external_stop_at):
                prefix_decisions.append(decide(p).decision_hash)
                p = outcome(p)
            p = halt(p)
            self.assertEqual(decide(p).action, Action.EXTERNAL_STOP)
            histories.append(prefix_decisions)
        self.assertEqual(histories[0], histories[1][:5])
        self.assertEqual(histories[0], histories[2][:5])
        self.assertEqual(histories[1], histories[2][:11])

    def test_future_driver_data_not_part_of_current_view(self):
        p = fixture()
        expected = decide(p)
        for future in ({"promotions": 1}, {"promotions": 1000000},
                       {"terminal": h("arbitrary"), "sequence": [9, 3, 7]}):
            self.assertEqual(decide(p), expected)
            with self.assertRaises(TypeError):
                decide(p, future=future)

    def test_resume_every_prefix(self):
        p = fixture()
        for _ in range(32):
            q = restore(checkpoint(p), expected_prefix_hash=p.prefix_hash)
            self.assertEqual(q, p)
            self.assertEqual(decide(q), decide(p))
            p = outcome(q)
        self.assertEqual(restore(checkpoint(p), expected_prefix_hash=p.prefix_hash), p)

    def test_tampering_detected_even_with_rehashed_outer_record(self):
        p = outcome(outcome(fixture()))
        original = json.loads(checkpoint(p))
        mutations = []
        for key, value in (("program_hash", h("substitute")), ("decision_hash", h("stale"))):
            obj = json.loads(checkpoint(p)); obj["observations"][0][key] = value
            mutations.append(obj)
        obj = json.loads(checkpoint(p)); obj["initial_credits"] += 1
        mutations.append(obj)
        obj = json.loads(checkpoint(p)); obj["observations"].reverse()
        mutations.append(obj)
        obj = json.loads(checkpoint(p)); obj["observations"][0]["verdict"] = "candidate_passed"
        mutations.append(obj)
        for obj in mutations:
            with self.assertRaises(ControlError):
                restore(canonical_json_bytes(obj), expected_prefix_hash=h(obj))
        self.assertEqual(json.loads(checkpoint(p)), original)

    def test_evaluation_hash_substitution_requires_external_anchor(self):
        p = outcome(fixture())
        obj = json.loads(checkpoint(p)); obj["observations"][0]["evaluation_hash"] = h("forged")
        with self.assertRaises(ControlError):
            restore(canonical_json_bytes(obj), expected_prefix_hash=p.prefix_hash)

    def test_stale_receipt_rejected_without_mutating_prefix(self):
        p = fixture(); d = decide(p); q = outcome(p)
        old = checkpoint(q)
        with self.assertRaises(ControlError):
            record_evaluation(q, d, verdict="reject", evaluation_hash=h("report"), reason_codes=("fail",),
                predecessor_state_hash=h("state"), challenge_commitment_hash=h("commitment"))
        self.assertEqual(checkpoint(q), old)

    def test_receipts_bound_to_parent_and_challenge(self):
        p = fixture()
        for parent, commitment in ((h("wrong"), h("commitment")), (h("state"), h("wrong"))):
            with self.assertRaises(ControlError):
                record_evaluation(p, decide(p), verdict="reject", evaluation_hash=h("report"),
                    reason_codes=("fail",), predecessor_state_hash=parent,
                    challenge_commitment_hash=commitment)

    def test_boolean_and_negative_structural_values_rejected(self):
        for bad in (True, False, -1, 1.5, "32"):
            with self.assertRaises(ControlError):
                fixture(bad)
            with self.assertRaises(ControlError):
                replace(fixture().frozen.view, turn_index=bad)
            with self.assertRaises(ControlError):
                RankedCandidate(h("p"), FAMILIES[0], bad, 1)

    def test_bad_grammar_and_trust_substitution(self):
        f = fixture().frozen
        for candidates in (f.candidates[:-1], (*f.candidates[:-1], f.candidates[0])):
            with self.assertRaises(ControlError):
                FrozenSearch(f.view, candidates)
        for changes in ({"fixed_verifier_hash": h("new")}, {"semantics_id": "noncommuting"}):
            with self.assertRaises(ControlError):
                replace(f.view, **changes)

    def test_external_stop_and_safety_are_distinct(self):
        p = outcome(fixture())
        self.assertEqual(decide(halt(p)).action, Action.EXTERNAL_STOP)
        self.assertEqual(decide(halt(p, safety=True)).action, Action.SAFETY_HALT)
        self.assertEqual(halt(p).observations, p.observations)
        with self.assertRaises(ControlError):
            halt(halt(p), safety=True)
        with self.assertRaises(ControlError):
            outcome(halt(p))

    def test_unknown_checkpoint_fields_rejected(self):
        p = fixture()
        for scope in (None, "frozen", "view", "candidate", "observation"):
            p = outcome(fixture()); obj = json.loads(checkpoint(p))
            target = obj if scope is None else (
                obj["frozen"] if scope == "frozen" else
                obj["frozen"]["view"] if scope == "view" else
                obj["frozen"]["candidates"][0] if scope == "candidate" else obj["observations"][0])
            target["future_route"] = ["planner", "memory"]
            with self.assertRaises(ControlError):
                restore(canonical_json_bytes(obj), expected_prefix_hash=h(obj))

    def test_noncanonical_and_duplicate_json_rejected(self):
        p = fixture()
        for bad in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.0}',
                    b'\xef\xbb\xbf' + checkpoint(p), checkpoint(p) + b'\n'):
            with self.assertRaises(ValueError):
                restore(bad, expected_prefix_hash=p.prefix_hash)

    def test_input_sequences_are_detached(self):
        counts = [0] * 8
        view = replace(fixture().frozen.view, family_counts=counts)
        counts[0] = 100
        self.assertEqual(view.family_counts, (0,) * 8)
        candidates = list(fixture().frozen.candidates)
        frozen = FrozenSearch(view, candidates)
        candidates.clear()
        self.assertEqual(len(frozen.candidates), 32)

    def test_terminal_cause_cannot_be_overwritten_via_constructor(self):
        cases = [fixture(0), outcome(fixture(), "candidate_passed")]
        p = fixture()
        for _ in range(32): p = outcome(p)
        cases.append(p)
        for case in cases:
            with self.assertRaises(ControlError):
                replace(case, stop=Action.EXTERNAL_STOP.value)

    def test_bounded_checkpoint_and_reason_codes(self):
        p = fixture()
        with self.assertRaises(ControlError):
            restore(b" " * 262145, expected_prefix_hash=p.prefix_hash)
        for codes in (("alias", "alias"), ("é",), tuple(str(i) for i in range(17)), ("a" * 129,)):
            with self.assertRaises(ControlError):
                record_evaluation(p, decide(p), verdict="reject", evaluation_hash=h("e"),
                    reason_codes=codes, predecessor_state_hash=h("state"),
                    challenge_commitment_hash=h("commitment"))

    def test_caller_cannot_claim_successful_stop(self):
        with self.assertRaises(ControlError):
            replace(fixture(), stop="success")
        with self.assertRaises(ControlError):
            outcome(fixture(), "promote")

    def test_candidate_order_cannot_control_decisions(self):
        p = fixture()
        shuffled = replace(p, frozen=FrozenSearch(p.frozen.view, tuple(reversed(p.frozen.candidates))))
        self.assertEqual(checkpoint(p), checkpoint(shuffled))
        self.assertEqual(decide(p), decide(shuffled))

    def test_cross_process_hash_seed_independence(self):
        code = ('from test_controller import fixture,outcome; '
                'from rcp_rclm_runtime_v5.phase17.controller import decide; '
                'p=fixture();\nfor _ in range(8): p=outcome(p)\nprint(p.prefix_hash)')
        expected = None
        for seed in ("0", "1", "927"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            env["PYTHONPATH"] = os.pathsep.join((str(Path(__file__).parent), env.get("PYTHONPATH", "")))
            value = subprocess.check_output([sys.executable, "-c", code], env=env, text=True).strip()
            if expected is None: expected = value
            self.assertEqual(value, expected)


if __name__ == "__main__":
    unittest.main()
