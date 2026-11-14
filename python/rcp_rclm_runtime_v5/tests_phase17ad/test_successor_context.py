"""AD physical successor projection and context-substitution controls.

Only setUpClass materializes the pinned fixture.  These checks do not run live
workers, make a new challenge, or replace the real Lean gate.
"""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import successor_context as ad
from rcp_rclm_runtime_v5.phase17.bootstrap import SELECTED_STATE_HASH, WEIGHTS_SHA256
from rcp_rclm_runtime_v5.phase17.controller import (Action, FAMILIES, FIXED_VERIFIER,
                                                 SEMANTICS, checkpoint, decide, restore)
from rcp_rclm_runtime_v5.phase17.finite_kernel import FALSE_CLAIMS
from rcp_rclm_runtime_v5.phase17.materialized import snapshot


ROOT = Path(__file__).resolve().parents[3]


class SuccessorContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='phase17ad-physical-')
        cls.packages = Path(cls.temp.name) / 'packages'
        cls.prepared = ad.prepare_successor_context(ROOT, cls.packages)
        cls.packet = cls.prepared.packet
        cls.raw = cls.prepared.packet_bytes
        cls.initial_snapshots = (snapshot(cls.packages / 'before'), snapshot(cls.packages / 'after'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rejected(self, mutation):
        value = copy.deepcopy(self.packet)
        mutation(value)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            ad.PreparedSuccessorContext(ad.canonical(value))

    def request(self, **overrides):
        p = self.packet
        args = {'expected_state_hash': p['prospective_state_hash'],
                'expected_history_hash': p['prospective_history_hash'],
                'turn_index': p['transition']['next_turn_index'],
                'public_nonce_hash': ad.SELECTED_NONCE,
                'challenge_commitment_hash': ad.SELECTED_COMMITMENT,
                'candidate_credits': 32}
        args.update(overrides)
        return ad.context_for(self.prepared, **args)

    def test_actual_candidate_is_next_parent(self):
        p = self.packet
        physical = p['finite_packet']['bindings']['candidate_physical_hash']
        self.assertEqual(p['prospective_state']['active_package_hash'], physical)
        self.assertEqual(p['next_context']['provenance_context']['parent_package'], physical)
        self.assertNotEqual(physical, p['finite_packet']['bindings']['predecessor_physical_hash'])

    def test_exact_append_and_preserved_frontier(self):
        p = self.packet
        before, after = p['projection']['before_program_hashes'], p['projection']['after_program_hashes']
        self.assertEqual(len(before), 8)
        self.assertEqual(len(after), 9)
        self.assertEqual(after, before + [p['transition']['program_hash']])
        self.assertEqual(len(p['projection']['before_frontier']), 21)
        self.assertEqual(len(p['projection']['after_frontier']), 22)
        self.assertTrue(set(p['projection']['before_frontier']) < set(p['projection']['after_frontier']))

    def test_only_selected_generation_advances(self):
        p = self.packet
        before = p['historical_state']['component_generations']
        after = p['prospective_state']['component_generations']
        self.assertEqual({k: after[k] - before[k] for k in FAMILIES},
                         {k: int(k == 'tool_policy') for k in FAMILIES})
        self.assertEqual(p['projection']['added_generation'], 2)

    def test_no_new_archive_or_recursive_frontier(self):
        old, new = self.packet['historical_state'], self.packet['prospective_state']
        self.assertEqual(old['archive_root_hash'], new['archive_root_hash'])
        self.assertEqual(old['recursive_productivity_frontier'], new['recursive_productivity_frontier'])
        self.assertEqual(len(new['recursive_productivity_frontier']), 19)
        self.assertNotEqual(self.packet['prospective_history_hash'], new['archive_root_hash'])

    def test_historical_and_prospective_state_identities_distinct(self):
        self.assertEqual(ad.digest(self.packet['historical_state']), SELECTED_STATE_HASH)
        self.assertEqual(ad.digest(self.packet['prospective_state']), self.packet['prospective_state_hash'])
        self.assertNotEqual(self.packet['prospective_state_hash'], SELECTED_STATE_HASH)

    def test_complete_measured_planner(self):
        p = self.packet
        for side in ('before', 'after'):
            raw = bytes.fromhex(p['captured_inputs'][side][ad.PLANNER])
            self.assertEqual(len(raw), 65536)
            self.assertEqual(ad.sha(raw), WEIGHTS_SHA256)
        self.assertEqual(len(p['projection']['nonzero_weights']), 84)
        self.assertEqual(p['projection']['planner_word_count'], 32768)

    def test_next_grammar_and_context_are_complete(self):
        context = self.packet['next_context']
        self.assertEqual(len(context['programs']), 32)
        self.assertEqual(len(context['rows']), 32)
        self.assertEqual({(p['family'], p['variant']) for p in context['programs']},
                         {(family, variant) for family in FAMILIES for variant in range(4)})
        self.assertEqual({p['generation'] for p in context['programs'] if p['family'] == 'tool_policy'}, {3})
        self.assertEqual({p['generation'] for p in context['programs'] if p['family'] != 'tool_policy'}, {2})

    def test_decision_starts_without_invented_verdict(self):
        context = self.packet['next_context']
        self.assertEqual(context['initial_action'], Action.EVALUATE.value)
        self.assertEqual(context['initial_checkpoint']['observations'], [])
        self.assertIsNone(context['initial_checkpoint']['stop'])
        self.assertIn(context['initial_candidate_hash'], [row['key'] for row in context['rows']])
        self.assertNotIn('accepted_candidate', context)
        self.assertNotIn('verdicts', context)

    def test_initial_checkpoint_replays_with_production_controller(self):
        context = self.packet['next_context']
        raw = ad.canonical(context['initial_checkpoint'])
        prefix = restore(raw, expected_prefix_hash=context['initial_prefix_hash'])
        self.assertEqual(checkpoint(prefix), raw)
        self.assertEqual(decide(prefix).decision_hash, context['initial_decision_hash'])

    def test_every_objective_is_scored_before_choice(self):
        rows = self.packet['objective']['ranked_objectives']
        self.assertEqual(len(rows), 8)
        self.assertEqual({r['family'] for r in rows}, set(FAMILIES))
        self.assertTrue(all(len(r['terms']) == 84 for r in rows))
        self.assertEqual(rows, sorted(rows, key=lambda r: (r['score'], r['tie_break'], r['family']), reverse=True))
        self.assertEqual(self.packet['objective']['objective_family'], rows[0]['family'])

    def test_reference_history_has_real_parent_binding(self):
        p = self.packet
        self.assertEqual(ad.digest(p['transition']), p['prospective_history_hash'])
        self.assertEqual(p['transition']['parent_state_hash'], SELECTED_STATE_HASH)
        self.assertEqual(p['transition']['parent_archive_root_hash'], p['historical_state']['archive_root_hash'])
        self.assertEqual(p['next_context']['provenance_context']['transcript_hash'], p['prospective_history_hash'])
        self.assertEqual(p['transition']['next_turn_index'], p['transition']['prior_turn_index'] + 1)

    def test_no_authority_flags_escape(self):
        self.assertEqual(self.packet['claims'], {key: False for key in FALSE_CLAIMS})
        self.assertFalse(self.packet['transition']['physical_candidate_active'])
        self.assertFalse(self.packet['transition']['root_authorized'])
        self.assertFalse(self.packet['objective']['promotion_authorized'])
        self.assertFalse(self.packet['objective_freeze']['challenge_bound'])
        for side in ('before', 'after'):
            registry = ad.load_json_strict(bytes.fromhex(self.packet['captured_inputs'][side]['registry/manifest.json']))
            self.assertFalse(registry['candidate_active'])

    def test_fixed_constitution_preserved(self):
        for state in (self.packet['historical_state'], self.packet['prospective_state']):
            self.assertEqual(state['fixed_verifier_hash'], FIXED_VERIFIER)
            self.assertEqual(state['semantics_id'], SEMANTICS)

    def test_reconstruction_is_deterministic(self):
        reconstructed = ad.PreparedSuccessorContext(self.raw)
        self.assertEqual(reconstructed.packet_bytes, self.raw)
        self.assertEqual(self.request(), {k: self.packet[k] for k in ('objective', 'objective_freeze', 'next_context')})

    def test_packets_do_not_alias_mutable_caller_data(self):
        value = self.prepared.packet
        value['prospective_state']['component_generations']['tool_policy'] = 100
        self.assertEqual(self.prepared.packet['prospective_state']['component_generations']['tool_policy'], 2)

    def test_exact_external_packet_anchor_required(self):
        ad.verify_packet_bytes(self.raw, self.prepared, expected_sha256=ad.sha(self.raw))
        with self.assertRaises(ValueError):
            ad.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)

    def test_physical_preparation_leaves_packages_unchanged(self):
        self.assertEqual(self.initial_snapshots,
                         (snapshot(self.packages / 'before'), snapshot(self.packages / 'after')))

    def test_existing_package_directory_cannot_be_reused(self):
        with self.assertRaises(ValueError):
            ad.prepare_successor_context(ROOT, self.packages)

    def test_stale_context_parent_rejected(self):
        self.rejected(lambda p: p['next_context']['provenance_context'].__setitem__(
            'parent_package', p['finite_packet']['bindings']['predecessor_physical_hash']))

    def test_entire_old_context_cannot_be_substituted(self):
        self.rejected(lambda p: p.__setitem__('next_context',
            p['finite_packet']['protected_packet']['joint_packet']['producer_provenance']['trace']))

    def test_swapped_state_identity_rejected(self):
        self.rejected(lambda p: p.__setitem__('prospective_state_hash', SELECTED_STATE_HASH))

    def test_parent_history_rewrite_rejected_after_rehash(self):
        def mutation(p):
            p['transition']['parent_archive_root_hash'] = '1' * 64
            p['prospective_history_hash'] = ad.digest(p['transition'])
        self.rejected(mutation)

    def test_changed_next_turn_rejected(self):
        self.rejected(lambda p: p['transition'].__setitem__('next_turn_index', 2))

    def test_changed_nonce_rejected(self):
        self.rejected(lambda p: p['next_context']['view'].__setitem__('public_nonce_hash', '3' * 64))

    def test_changed_opaque_commitment_rejected_in_selected_packet(self):
        self.rejected(lambda p: p['next_context']['view'].__setitem__('challenge_commitment_hash', '4' * 64))

    def test_changed_planner_image_rejected_even_with_new_projection(self):
        def mutation(p):
            raw = bytearray.fromhex(p['captured_inputs']['after'][ad.PLANNER]); raw[0] ^= 1
            p['captured_inputs']['after'][ad.PLANNER] = raw.hex()
            p['projection']['planner_image_sha256'] = ad.sha(raw)
        self.rejected(mutation)

    def test_changed_generation_rejected(self):
        self.rejected(lambda p: p['prospective_state']['component_generations'].__setitem__('planner_policy', 2))

    def test_removed_protected_frontier_rejected(self):
        self.rejected(lambda p: p['prospective_state']['capability_frontier'].pop(0))

    def test_invented_recursive_gain_rejected(self):
        self.rejected(lambda p: p['prospective_state']['recursive_productivity_frontier'].append('recursive.invented'))

    def test_replacement_program_rejected(self):
        def mutation(p):
            key = p['transition']['program_hash']
            path = 'registry/programs/' + key + '.json'
            program = ad.load_json_strict(bytes.fromhex(p['captured_inputs']['after'][path]))
            program['parameter_a'] += 1
            p['captured_inputs']['after'][path] = ad.canonical(program).hex()
        self.rejected(mutation)

    def test_changed_manifest_cannot_self_authenticate(self):
        def mutation(p):
            manifest = ad.load_json_strict(bytes.fromhex(p['captured_inputs']['after'][ad.MANIFEST]))
            manifest['claims']['promotion_authorized'] = True
            manifest['materialized_package_hash'] = ad.digest({k: v for k, v in manifest.items()
                                                               if k != 'materialized_package_hash'})
            p['captured_inputs']['after'][ad.MANIFEST] = ad.canonical(manifest).hex()
        self.rejected(mutation)

    def test_declared_active_registry_rejected(self):
        def mutation(p):
            registry = ad.load_json_strict(bytes.fromhex(p['captured_inputs']['after']['registry/manifest.json']))
            registry['candidate_active'] = True
            p['captured_inputs']['after']['registry/manifest.json'] = ad.canonical(registry).hex()
        self.rejected(mutation)

    def test_extra_captured_file_rejected(self):
        self.rejected(lambda p: p['captured_inputs']['after'].__setitem__('future_schedule.json', '7b7d'))

    def test_missing_generator_metadata_rejected(self):
        self.rejected(lambda p: p['captured_inputs']['after'].pop('base/policies/generator_policy.json'))

    def test_context_score_change_rejected(self):
        self.rejected(lambda p: p['next_context']['rows'][0].__setitem__('base_score', 99999))

    def test_objective_winner_change_rejected(self):
        self.rejected(lambda p: p['objective'].__setitem__('objective_family', 'invented_policy'))

    def test_objective_term_change_rejected(self):
        self.rejected(lambda p: p['objective']['ranked_objectives'][0]['terms'].__setitem__(0, 99999))

    def test_source_binding_substitution_rejected(self):
        self.rejected(lambda p: p['producer']['source_files'][0].__setitem__('sha256', '0' * 64))

    def test_candidate_first_action_substitution_rejected(self):
        self.rejected(lambda p: p['next_context'].__setitem__('initial_action', 'await_root_verification'))

    def test_context_hash_recalculation_does_not_rescue_wrong_parent(self):
        def mutation(p):
            p['next_context']['context_binding']['prospective_state_hash'] = SELECTED_STATE_HASH
            p['next_context']['provenance_context']['context_hash'] = ad.digest(p['next_context']['context_binding'])
        self.rejected(mutation)

    def test_claim_escalation_rejected(self):
        self.rejected(lambda p: p['claims'].__setitem__('root_transition_verified', True))

    def test_scope_escalation_rejected(self):
        self.rejected(lambda p: p['scope'].__setitem__('fresh_challenges', 1))

    def test_future_horizon_field_rejected(self):
        self.rejected(lambda p: p.__setitem__('target_promotions', 10))

    def test_future_winner_hidden_in_view_rejected(self):
        self.rejected(lambda p: p['next_context']['view'].__setitem__('winning_program_hash', '2' * 64))

    def test_generic_context_rejects_old_state_anchor(self):
        with self.assertRaises(ValueError):
            self.request(expected_state_hash=SELECTED_STATE_HASH)

    def test_generic_context_rejects_wrong_history_anchor(self):
        with self.assertRaises(ValueError):
            self.request(expected_history_hash='0' * 64)

    def test_generic_context_rejects_stale_turn(self):
        with self.assertRaises(ValueError):
            self.request(turn_index=self.packet['transition']['prior_turn_index'])

    def test_generic_context_rejects_consumed_commitment(self):
        with self.assertRaises(ValueError):
            self.request(challenge_commitment_hash=self.packet['finite_packet']['bindings']['challenge_commitment_hash'])

    def test_generic_context_rejects_boolean_credits(self):
        with self.assertRaises(ValueError):
            self.request(candidate_credits=True)

    def test_generic_context_rejects_credits_outside_provenance_domain(self):
        with self.assertRaises(ValueError):
            self.request(candidate_credits=33)

    def test_zero_credits_make_resource_terminal(self):
        value = self.request(candidate_credits=0)['next_context']
        self.assertEqual(value['initial_action'], Action.RESOURCE_EXHAUSTED.value)
        self.assertIsNone(value['initial_candidate_hash'])
        self.assertEqual(value['initial_checkpoint']['initial_credits'], 0)

    def test_public_request_can_change_without_mutating_projection(self):
        new = self.request(public_nonce_hash='1' * 64, challenge_commitment_hash='2' * 64)
        self.assertNotEqual(new['next_context']['freeze_hash'], self.packet['next_context']['freeze_hash'])
        self.assertEqual(new['next_context']['view']['active_package_hash'],
                         self.packet['prospective_state']['active_package_hash'])
        self.assertEqual(self.prepared.packet_bytes, self.raw)

    def test_general_api_rejects_arbitrary_model_state(self):
        with self.assertRaises(ValueError):
            ad.context_for(ad._model(self.packet['prospective_state']),
                           expected_state_hash=self.packet['prospective_state_hash'],
                           expected_history_hash=self.packet['prospective_history_hash'],
                           turn_index=1, public_nonce_hash=ad.SELECTED_NONCE,
                           challenge_commitment_hash=ad.SELECTED_COMMITMENT, candidate_credits=32)

    def test_forged_prepared_claims_are_revalidated(self):
        altered = self.prepared.packet
        altered['claims']['promotion_authorized'] = True
        forged = object.__new__(ad.PreparedSuccessorContext)
        object.__setattr__(forged, 'packet_bytes', ad.canonical(altered))
        object.__setattr__(forged, '_finite', self.prepared.finite())
        with self.assertRaises(ValueError):
            ad.context_for(forged, expected_state_hash=self.packet['prospective_state_hash'],
                           expected_history_hash=self.packet['prospective_history_hash'],
                           turn_index=1, public_nonce_hash=ad.SELECTED_NONCE,
                           challenge_commitment_hash=ad.SELECTED_COMMITMENT, candidate_credits=32)

    def test_production_rank_disagreement_fails_closed(self):
        with patch.object(ad, 'score_table', return_value=[]):
            with self.assertRaises(ValueError):
                self.request()

    def test_production_grammar_disagreement_fails_closed(self):
        with patch.object(ad, 'reference_grammar', return_value=()):
            with self.assertRaises(ValueError):
                self.request()


class PacketBoundaryTests(unittest.TestCase):
    def test_mutable_bytes_rejected(self):
        with self.assertRaises(ValueError):
            ad.PreparedSuccessorContext(bytearray(b'{}'))

    def test_empty_bytes_rejected(self):
        with self.assertRaises(ValueError):
            ad.PreparedSuccessorContext(b'')

    def test_oversized_bytes_rejected_before_parse(self):
        with self.assertRaises(ValueError):
            ad.PreparedSuccessorContext(b' ' * (ad.MAX_BYTES + 1))

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            ad.PreparedSuccessorContext(b'{"schema":1,"schema":2}')

    def test_unknown_packet_fields_rejected(self):
        with self.assertRaises(ValueError):
            ad.PreparedSuccessorContext(b'{"active":true}')
