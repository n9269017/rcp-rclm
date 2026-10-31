"""Integration tests require the real v4.6 Phase 16 modules, not stubs."""
from dataclasses import replace
import unittest
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as h
from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_INITIAL_CAPABILITY_FRONTIER, PHASE16_INITIAL_RECURSIVE_FRONTIER,
    PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH, UPDATE_FAMILIES,
)
from rcp_rclm_runtime_v4.phase16.grammar import legal_mutation_programs
from rcp_rclm_runtime_v4.phase16.ranking import ranked_programs
from rcp_rclm_runtime_v4.phase16.records import ModelState
from rcp_rclm_runtime_v5.phase17.controller import (
    Action, ControlError, checkpoint, decide, record_evaluation, restore,
)
from rcp_rclm_runtime_v5.phase17.phase16_adapter import bind_phase16_search


def state():
    return ModelState(9, PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
        {f: 0 for f in UPDATE_FAMILIES}, (),
        tuple(sorted(PHASE16_INITIAL_CAPABILITY_FRONTIER)),
        tuple(sorted(PHASE16_INITIAL_RECURSIVE_FRONTIER)), h("fixture-archive"))


def bind(s=None, credits=32):
    return bind_phase16_search(state() if s is None else s, turn_index=0,
        challenge_commitment_hash=h("fixture-commitment"), public_nonce_hash=h("fixture-nonce"),
        candidate_credits=credits)


class Phase16AdapterTests(unittest.TestCase):
    def test_retained_phase16_terminal_state_bridge(self):
        record = json.loads((Path(__file__).parent / "fixtures/phase16_reference_terminal.json").read_text())
        self.assertEqual(h(record["state"]), record["state_hash"])
        payload = dict(record["state"])
        payload.pop("schema_id")
        predecessor = ModelState(**payload)
        before = predecessor.to_json()
        binding = bind_phase16_search(predecessor,
            turn_index=record["accepted_promotions"],
            challenge_commitment_hash=h("new-post-freeze-fixture-commitment"),
            public_nonce_hash=h("new-public-fixture-nonce"), candidate_credits=32)
        self.assertEqual(binding.prefix.frozen.view.predecessor_state_hash, record["state_hash"])
        self.assertEqual(len(binding.programs), 32)
        self.assertEqual(predecessor.to_json(), before)

    def test_exact_unchanged_grammar(self):
        s = state(); b = bind(s)
        programs = legal_mutation_programs(s, promotion_index=0, public_nonce_hash=h("fixture-nonce"))
        self.assertEqual(set(b.programs), {p.program_hash for p in programs})
        self.assertEqual(b.prefix.frozen.view.predecessor_state_hash, s.state_record_hash)

    def test_learned_prefix_matches_phase16_after_each_rejection(self):
        b = bind(); p = b.prefix; rejected = []
        for _ in range(4):
            seen = {o.program_hash for o in p.observations}
            remaining = tuple(x for x in b.programs.values() if x.program_hash not in seen)
            expected = ranked_programs(remaining,
                active_package_hash=p.frozen.view.active_package_hash,
                verified_family_counts={f: 0 for f in UPDATE_FAMILIES}, rejected_families=rejected,
                seed=b.public_ranking_seed, challenge_stream="phase17-present-only-v1")[0]
            decision = decide(p)
            self.assertEqual(decision.candidate_hash, expected.program_hash)
            rejected.append(expected.family)
            p = record_evaluation(p, decision, verdict="reject", evaluation_hash=h(expected.to_json()),
                reason_codes=("fixture-reject",), predecessor_state_hash=p.frozen.view.predecessor_state_hash,
                challenge_commitment_hash=p.frozen.view.challenge_commitment_hash)

    def test_nonzero_family_counts_preserved(self):
        s = state()
        s = replace(s, component_generations={f: i for i, f in enumerate(UPDATE_FAMILIES)})
        b = bind(s)
        self.assertEqual(b.prefix.frozen.view.family_counts, tuple(range(8)))
        self.assertTrue(all(p.generation == s.component_generations[p.family] + 1
                            for p in b.programs.values()))

    def test_predecessor_mapping_mutation_cannot_change_frozen_view(self):
        s = state(); b = bind(s); original = checkpoint(b.prefix)
        s.component_generations[UPDATE_FAMILIES[0]] += 1
        self.assertEqual(checkpoint(b.prefix), original)
        with self.assertRaises(TypeError):
            b.programs["injected"] = next(iter(b.programs.values()))

    def test_bridge_resume_and_budget_stop(self):
        b = bind(credits=0); p = b.prefix
        self.assertEqual(decide(p).action, Action.RESOURCE_EXHAUSTED)
        self.assertEqual(restore(checkpoint(p), expected_prefix_hash=p.prefix_hash), p)

    def test_bridge_has_no_future_schedule_argument(self):
        with self.assertRaises(TypeError):
            bind_phase16_search(state(), turn_index=0, challenge_commitment_hash=h("c"),
                public_nonce_hash=h("n"), candidate_credits=32, target_promotions=100)
        with self.assertRaises(ControlError):
            bind_phase16_search({}, turn_index=0, challenge_commitment_hash=h("c"),
                public_nonce_hash=h("n"), candidate_credits=32)


if __name__ == "__main__":
    unittest.main()
