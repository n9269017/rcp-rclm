"""AG finite observation decisions, truthful exhaustion, and binding failures.

Controlled observations exercise the generic API. They are not live physical
successors or Lean acceptance evidence; those claims require the separate gate.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import successor_interface as ag

ROOT = Path(__file__).resolve().parents[3]


class SuccessorInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.second = ag.af.PreparedSecondStep((ROOT / ag.AF_ROOT / 'packet.json').read_bytes())
        cls.fixed = ag.FixedInterpretation(cls.second.interpretation().packet_bytes)
        cls.request = ag.selected_request(cls.second)
        cls.cases = ag.case_requests(cls.second)
        retained = (ROOT / ag.AF_ROOT / 'execution.json').read_bytes()
        cls.packet = {'schema': ag.SCHEMA, 'policy': ag.POLICY, 'base_commit': ag.BASE,
            'second_step_packet': cls.second.packet,
            'retained_execution_hex': {ag.AF_ROOT + '/execution.json': retained.hex()},
            'retained_sha256': dict(ag.RETAINED_PINS),
            'inherited_source_sha256': ag._execution(retained)['source_sha256'],
            **ag._derive(cls.second), 'scope': dict(ag.SCOPE),
            'claims': {key: False for key in ag.FALSE_CLAIMS}}
        cls.raw = ag.canonical(cls.packet)
        cls.prepared = ag.PreparedSuccessorInterface(cls.raw)

    def inspect(self, request=None):
        request = copy.deepcopy(self.request if request is None else request)
        return ag.inspect_request(self.fixed, request,
            expected_source_sha256=ag.digest(request['source']), expected_request_sha256=ag.digest(request))

    def mutate(self, change):
        request = copy.deepcopy(self.request)
        change(request)
        return self.inspect(request)

    def packet_refused(self, change):
        packet = copy.deepcopy(self.packet); change(packet)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            ag.PreparedSuccessorInterface(ag.canonical(packet))

    def synthetic(self):
        """Independent finite fixture; no package, journal, or history is executed."""
        request = copy.deepcopy(self.request)
        source = request['source']
        source['package_hash'] = ag.digest({'fixture': 'AG synthetic source; no physical observation'})
        context = request['context']; context['parent_package'] = source['package_hash']
        context['context_hash'] = ag.digest({'fixture': 'AG synthetic context'})
        context['transcript_hash'] = ag.digest({'fixture': 'AG synthetic history'})
        offer = request['offers'][0]; update = offer['update']
        update['program']['parameter_a'] = -5
        update['key'] = ag.digest(update['program'])
        update['task'] = 42; update['task_name'] = 'phase17ae.adapter.affine.0.20'
        update['parent_package'] = source['package_hash']; update['context_hash'] = context['context_hash']
        update['candidate_package'] = ag.digest({'fixture': 'AG synthetic successor'})
        context['rows'][30]['key'] = update['key']
        offer['next'] = ag.apply_update(source, update)
        evidence = offer['evidence']
        for name in ('parent_package', 'context_hash', 'transcript_hash'):
            evidence[name] = context[name]; evidence['proposal'][name] = context[name]
        evidence['candidate_package'] = update['candidate_package']
        evidence['proposal']['candidate_package'] = update['candidate_package']
        evidence['proposal']['program'] = update['key']
        return request

    def test_selected_af_entry_passes_all_recomputed_obligations(self):
        result = self.inspect()
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['selected_index'], 0)
        self.assertEqual(tuple(result['checks'][0]['obligations']), ag.OBLIGATIONS)
        self.assertTrue(all(result['checks'][0]['obligations'].values()))

    def test_exact_fixed_catalog_and_original_af_identities(self):
        self.assertEqual(self.packet['base_commit'], 'ef4b009ad1308f1a56d9ef3f8cd9f5bd1ffac8ef')
        self.assertEqual(ag.sha(self.second.packet_bytes), ag.AF_PACKET_SHA)
        self.assertEqual(ag.sha(self.fixed.interpretation_bytes), ag.af.AE_PACKET_SHA)
        self.assertEqual(len(self.packet['inherited_source_sha256']), 535)

    def test_all_282_names_retain_the_existing_meanings(self):
        catalog = self.second.interpretation().packet['catalog']
        names = [*catalog['legacy_task_ids'], *[row['task_id'] for row in catalog['tail']]]
        self.assertEqual([self.fixed.task_name(i) for i in range(282)], names)
        self.assertEqual(self.fixed.task_name(282), '')
        self.assertFalse(self.fixed.check(self.request['source'], 282))

    def test_selected_semantics_fail_before_and_hold_after(self):
        checked = self.inspect()['checks'][0]
        self.assertFalse(checked['source_holds_task'])
        self.assertTrue(checked['successor_holds_task'])
        self.assertEqual(checked['before_frontier'], list(range(22)))
        self.assertEqual(checked['after_frontier'], [*range(22), 41])

    def test_refusal_is_local_to_the_offered_pair(self):
        result = self.inspect(self.cases['refusal'])
        self.assertEqual(result['status'], 'exhausted')
        self.assertEqual(result['checks'][0]['failed_obligations'], ['trusted'])
        self.assertTrue(result['no_passing_offer_in_supplied_pool'])
        self.assertFalse(result['wider_domain_exhaustion_established'])

    def test_empty_pool_is_exhausted_even_at_zero_budget(self):
        result = self.inspect(self.cases['empty'])
        self.assertEqual((result['status'], result['examined'], result['unexamined']), ('exhausted', 0, 0))
        self.assertIsNone(result['selected_index'])

    def test_zero_budget_on_nonempty_pool_proves_no_global_refusal(self):
        result = self.inspect(self.cases['zero_budget'])
        self.assertEqual((result['status'], result['examined'], result['unexamined']), ('budget_stop', 0, 1))
        self.assertFalse(result['finite_pool_exhausted'])
        self.assertFalse(result['no_passing_offer_in_supplied_pool'])
        self.assertFalse(result['guarded_nonexistence_established_in_supplied_pool'])

    def test_rejected_prefix_then_selected_returns_first_success(self):
        result = self.inspect(self.cases['refusal_then_selected'])
        self.assertEqual((result['status'], result['selected_index'], result['examined']), ('accepted', 1, 2))
        self.assertEqual([row['passes'] for row in result['checks']], [False, True])

    def test_fuel_exhaustion_does_not_hide_a_passing_suffix(self):
        result = self.inspect(self.cases['budget_before_selected'])
        self.assertEqual((result['status'], result['examined'], result['unexamined']), ('budget_stop', 1, 1))
        self.assertFalse(result['no_passing_offer_in_supplied_pool'])
        extended = copy.deepcopy(self.cases['budget_before_selected']); extended['inspection_budget'] = 2
        self.assertEqual(self.inspect(extended)['selected_index'], 1)

    def test_accepted_search_does_not_inspect_later_offers(self):
        request = copy.deepcopy(self.request)
        request['offers'].append(copy.deepcopy(request['offers'][0])); request['inspection_budget'] = 2
        with patch.object(ag, '_check_offer', wraps=ag._check_offer) as check:
            result = self.inspect(request)
        self.assertEqual((result['selected_index'], result['examined'], result['unexamined']), (0, 1, 1))
        self.assertEqual(check.call_count, 1)

    def test_budget_bounds_the_number_of_semantic_offer_inspections(self):
        with patch.object(ag, '_check_offer', wraps=ag._check_offer) as check:
            result = self.inspect(self.cases['budget_before_selected'])
        self.assertEqual(result['examined'], check.call_count)
        self.assertEqual(check.call_count, 1)

    def test_all_refusals_with_sufficient_fuel_exhaust_exact_pool(self):
        request = copy.deepcopy(self.cases['refusal'])
        request['offers'] *= 3; request['inspection_budget'] = 3
        result = self.inspect(request)
        self.assertEqual((result['status'], result['examined']), ('exhausted', 3))
        self.assertTrue(result['guarded_nonexistence_established_in_supplied_pool'])

    def test_more_fuel_than_pool_preserves_exhaustion(self):
        request = copy.deepcopy(self.cases['refusal']); request['inspection_budget'] = 64
        result = self.inspect(request)
        self.assertEqual((result['status'], result['examined']), ('exhausted', 1))

    def test_source_inadmissible_does_not_claim_guarded_nonexistence(self):
        result = self.inspect(self.cases['source_inadmissible'])
        self.assertFalse(result['source_admissible'])
        self.assertTrue(result['no_passing_offer_in_supplied_pool'])
        self.assertFalse(result['guarded_nonexistence_established_in_supplied_pool'])

    def test_generic_fixture_accepts_different_source_and_task(self):
        request = self.synthetic(); result = self.inspect(request)
        self.assertNotEqual(request['source']['package_hash'], self.request['source']['package_hash'])
        self.assertEqual(request['offers'][0]['update']['task'], 42)
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['checks'][0]['after_frontier'], [*range(22), 42])
        self.assertFalse(result['formal_acceptance_established'])

    def test_generic_fixture_can_use_another_variant_and_offset(self):
        request = self.synthetic(); update = request['offers'][0]['update']
        update['program']['variant'] = 2; update['program']['parameter_a'] = 4; update['program']['parameter_b'] = -3
        update['key'] = ag.digest(update['program']); update['task'] = 22 + 2 * 65 + 39
        update['task_name'] = self.fixed.task_name(update['task'])
        request['context']['rows'][30]['key'] = update['key']
        request['offers'][0]['evidence']['proposal']['program'] = update['key']
        request['offers'][0]['next'] = ag.apply_update(request['source'], update)
        self.assertEqual(self.inspect(request)['status'], 'accepted')

    def test_generic_fixture_still_refuses_wrong_interpretation(self):
        request = self.synthetic(); request['offers'][0]['update']['task'] = 43
        request['offers'][0]['update']['task_name'] = self.fixed.task_name(43)
        request['offers'][0]['next'] = ag.apply_update(request['source'], request['offers'][0]['update'])
        self.assertEqual(self.inspect(request)['status'], 'exhausted')

    def test_stale_parent_is_refused(self):
        result = self.inspect(self.cases['stale_parent'])
        self.assertIn('update_valid', result['checks'][0]['failed_obligations'])
        self.assertIn('matched', result['checks'][0]['failed_obligations'])

    def test_wrong_context_is_refused(self):
        self.assertIn('trusted', self.inspect(self.cases['wrong_context'])['checks'][0]['failed_obligations'])

    def test_wrong_candidate_is_refused(self):
        self.assertIn('trusted', self.inspect(self.cases['wrong_candidate'])['checks'][0]['failed_obligations'])

    def test_changed_protected_goal_is_refused(self):
        failed = self.inspect(self.cases['changed_protected'])['checks'][0]['failed_obligations']
        self.assertIn('after_admissible', failed); self.assertIn('typed', failed)

    def test_omitted_charge_is_refused(self):
        self.assertIn('resources', self.inspect(self.cases['omitted_charge'])['checks'][0]['failed_obligations'])

    def test_wrong_program_breaks_typed_transition(self):
        self.assertIn('typed', self.inspect(self.cases['wrong_program'])['checks'][0]['failed_obligations'])

    def test_renamed_task_does_not_acquire_semantics(self):
        self.assertIn('update_valid', self.inspect(self.cases['wrong_task_name'])['checks'][0]['failed_obligations'])

    def test_already_solved_undeclared_task_fails_semantic_guard(self):
        checked = self.inspect(self.cases['already_solved'])['checks'][0]
        self.assertTrue(checked['source_holds_task']); self.assertTrue(checked['successor_holds_task'])
        self.assertEqual(checked['failed_obligations'], ['semantic_failure'])

    def test_false_successor_task_has_no_frontier_expansion(self):
        checked = self.inspect(self.cases['false_successor'])['checks'][0]
        self.assertFalse(checked['successor_holds_task'])
        self.assertIn('after_admissible', checked['failed_obligations'])
        self.assertIn('expansion', checked['failed_obligations'])

    def test_forged_source_program_pair_is_not_tautologically_admissible(self):
        result = self.mutate(lambda r: r['source']['program_keys'].__setitem__(0, 'substituted-key'))
        self.assertFalse(result['source_admissible'])
        self.assertIn('before_admissible', result['checks'][0]['failed_obligations'])

    def test_duplicate_source_keys_are_refused(self):
        def change(r):
            r['source']['keys'][1] = r['source']['keys'][0]
            r['source']['program_keys'][1] = r['source']['program_keys'][0]
        self.assertFalse(self.mutate(change)['source_admissible'])

    def test_changed_frozen_images_breaks_typed_transition(self):
        result = self.mutate(lambda r: r['offers'][0]['next']['frozen'][0][0].__setitem__('size', 0))
        self.assertIn('typed', result['checks'][0]['failed_obligations'])

    def test_changed_protected_distribution_breaks_typed_transition(self):
        result = self.mutate(lambda r: r['offers'][0]['next']['semantic']['mass_minus_one_dictionary'][0].__setitem__(0, 7))
        self.assertIn('typed', result['checks'][0]['failed_obligations'])

    def test_bad_selector_is_not_admissible(self):
        result = self.mutate(lambda r: r['source']['semantic']['row_selectors'].__setitem__(0, 9999))
        self.assertFalse(result['source_admissible'])

    def test_unknown_declared_task_cannot_be_admitted(self):
        def change(r):
            r['source']['declared'].append(282); r['source']['named_frontier'].insert(0, '')
        self.assertFalse(self.mutate(change)['source_admissible'])

    def test_context_parent_is_checked_against_actual_source(self):
        result = self.mutate(lambda r: r['context'].__setitem__('parent_package', 'another-parent'))
        self.assertIn('trusted', result['checks'][0]['failed_obligations'])

    def test_context_requires_the_complete_32_row_inventory(self):
        result = self.mutate(lambda r: r['context']['rows'].pop())
        self.assertIn('trusted', result['checks'][0]['failed_obligations'])
        self.assertIn('matched', result['checks'][0]['failed_obligations'])

    def test_context_duplicate_production_keys_are_refused(self):
        result = self.mutate(lambda r: r['context']['rows'][1].__setitem__('key', r['context']['rows'][0]['key']))
        self.assertIn('matched', result['checks'][0]['failed_obligations'])

    def test_proposal_cannot_skip_the_selected_production_choice(self):
        result = self.mutate(lambda r: r['offers'][0]['evidence']['proposal'].__setitem__('choices', [0]))
        self.assertIn('matched', result['checks'][0]['failed_obligations'])

    def test_proposal_verdict_pattern_is_not_caller_acceptance(self):
        result = self.mutate(lambda r: r['offers'][0]['evidence']['proposal'].__setitem__('verdicts', [False]))
        self.assertIn('matched', result['checks'][0]['failed_obligations'])

    def test_empty_proposal_cannot_match(self):
        result = self.mutate(lambda r: r['offers'][0]['evidence']['proposal'].__setitem__('choices', []))
        self.assertIn('matched', result['checks'][0]['failed_obligations'])

    def test_generic_production_choices_match_independent_controller_for_all_32_rows(self):
        inherited = self.second.successor_context().packet['next_context']
        prefix = ag.af.restore(ag.canonical(inherited['initial_checkpoint']),
                               expected_prefix_hash=inherited['initial_prefix_hash'])
        context, seen = self.request['context'], []
        for turn in range(32):
            decision = ag.af.decide(prefix)
            index = ag._choose(context, seen)
            self.assertIsNotNone(index)
            self.assertEqual(context['rows'][index]['key'], decision.candidate_hash)
            seen.append(index)
            prefix = ag.af.record_evaluation(prefix, decision, verdict='reject',
                evaluation_hash=ag.digest({'synthetic_orchestration_control': turn}),
                reason_codes=('AG_CONTROLLED_REFUSAL',),
                predecessor_state_hash=prefix.frozen.view.predecessor_state_hash,
                challenge_commitment_hash=prefix.frozen.view.challenge_commitment_hash)
        self.assertEqual(set(seen), set(range(32)))
        self.assertIsNone(ag._choose(context, seen))
        self.assertEqual(ag.af.decide(prefix).action, ag.af.Action.SEARCH_EXHAUSTED)

    def test_produced_prefix_checks_fallback_order_and_complete_verdict_pattern(self):
        context, seen = self.request['context'], []
        for _ in range(7):
            seen.append(ag._choose(context, seen))
        proposal = copy.deepcopy(self.request['offers'][0]['evidence']['proposal'])
        proposal['choices'] = seen; proposal['verdicts'] = [False] * 6 + [True]
        proposal['program'] = context['rows'][seen[-1]]['key']
        self.assertTrue(ag._produced(context, proposal))
        swapped = copy.deepcopy(proposal); swapped['choices'][4:6] = reversed(swapped['choices'][4:6])
        self.assertFalse(ag._produced(context, swapped))
        forged = copy.deepcopy(proposal); forged['verdicts'][0] = True
        self.assertFalse(ag._produced(context, forged))

    def test_reference_tariff_matches_af_without_claiming_complete_cost(self):
        result = self.inspect(); check = result['checks'][0]
        self.assertEqual((check['reference_charges'], check['reference_cost']), ([1, 38, 152, 152], 976))
        self.assertFalse(result['resource_accounting_complete'])

    def test_self_consistent_over_budget_charges_still_fail(self):
        def change(r):
            charges = ['candidate'] * 33
            r['expected_charges'] = charges
            r['offers'][0]['update']['charges'] = charges
            r['offers'][0]['evidence']['charges'] = charges
        checked = self.mutate(change)['checks'][0]
        self.assertIn('resources', checked['failed_obligations'])

    def test_inspection_budget_cannot_override_resource_failure(self):
        request = copy.deepcopy(self.cases['omitted_charge']); request['inspection_budget'] = 64
        self.assertEqual(self.inspect(request)['status'], 'exhausted')

    def test_predeclared_task_is_not_strict_even_if_program_is_new(self):
        def change(r):
            u = r['offers'][0]['update']; u['task'] = 0; u['task_name'] = self.fixed.task_name(0)
            r['offers'][0]['next'] = ag.apply_update(r['source'], u)
        checked = self.mutate(change)['checks'][0]
        self.assertIn('update_valid', checked['failed_obligations'])
        self.assertIn('semantic_failure', checked['failed_obligations'])

    def test_same_candidate_package_is_refused(self):
        result = self.mutate(lambda r: r['offers'][0]['update'].__setitem__('candidate_package', r['source']['package_hash']))
        self.assertIn('update_valid', result['checks'][0]['failed_obligations'])

    def test_external_request_anchor_cannot_be_reused_after_mutation(self):
        request = copy.deepcopy(self.request); expected = ag.digest(request)
        request['inspection_budget'] = 0
        with self.assertRaises(ValueError):
            ag.inspect_request(self.fixed, request, expected_source_sha256=ag.digest(request['source']),
                               expected_request_sha256=expected)

    def test_request_mutation_after_anchor_cannot_change_inspected_snapshot(self):
        request = copy.deepcopy(self.request)
        source_hash, request_hash = ag.digest(request['source']), ag.digest(request)
        expected = ag.inspect_request(self.fixed, request,
            expected_source_sha256=source_hash, expected_request_sha256=request_hash)
        inspect_offer = ag._check_offer

        def mutate_caller_then_inspect(*args):
            # Deterministic mutation at the post-anchor evaluation boundary.
            # This checks alias isolation, not a general concurrency theorem.
            request['source']['root'] = 'changed-after-anchor'
            request['context']['context_hash'] = 'changed-after-anchor'
            request['expected_charges'].clear()
            request['offers'][0]['evidence']['root'] = 'changed-after-anchor'
            request['offers'].append(copy.deepcopy(request['offers'][0]))
            request['inspection_budget'] = 0
            return inspect_offer(*args)

        with patch.object(ag, '_check_offer', side_effect=mutate_caller_then_inspect) as check:
            actual = ag.inspect_request(self.fixed, request,
                expected_source_sha256=source_hash, expected_request_sha256=request_hash)
        self.assertEqual(check.call_count, 1)
        self.assertNotEqual(ag.digest(request), request_hash)
        self.assertEqual(actual, expected)

    def test_public_offer_check_detaches_all_inputs_before_evaluation(self):
        request = copy.deepcopy(self.request)
        source, context = request['source'], request['context']
        charges, offer = request['expected_charges'], request['offers'][0]
        expected = ag.check_offer(self.fixed, source, context, charges, offer)
        inspect_offer = ag._check_offer

        def mutate_caller_then_inspect(*args):
            source['root'] = 'changed-during-check'
            context['context_hash'] = 'changed-during-check'
            charges.clear()
            offer['evidence']['root'] = 'changed-during-check'
            return inspect_offer(*args)

        with patch.object(ag, '_check_offer', side_effect=mutate_caller_then_inspect) as check:
            actual = ag.check_offer(self.fixed, source, context, charges, offer)
        self.assertEqual(check.call_count, 1)
        self.assertNotEqual(ag.digest(offer), expected['offer_sha256'])
        self.assertEqual(actual, expected)

    def test_canonical_equivalent_bindings_use_the_hashed_interpretation(self):
        request = copy.deepcopy(self.request)
        request['context']['generator'] = 'e\u0301'
        request['offers'][0]['evidence']['proposal']['generator'] = '\u00e9'
        canonical_request = ag.load_json_strict(ag.canonical(request))
        self.assertNotEqual(request, canonical_request)
        self.assertEqual(ag.digest(request), ag.digest(canonical_request))
        expected = self.inspect(canonical_request)
        self.assertEqual(expected['status'], 'accepted')
        self.assertEqual(self.inspect(request), expected)
        raw_check = ag.check_offer(self.fixed, request['source'], request['context'],
                                   request['expected_charges'], request['offers'][0])
        canonical_check = ag.check_offer(self.fixed, canonical_request['source'], canonical_request['context'],
                                         canonical_request['expected_charges'], canonical_request['offers'][0])
        self.assertEqual(raw_check, canonical_check)

    def test_snapshot_preserves_exact_request_and_offer_schema_types(self):
        class RequestSubclass(dict):
            pass
        wrong_offers = copy.deepcopy(self.request)
        wrong_offers['offers'] = tuple(wrong_offers['offers'])
        for request in (RequestSubclass(self.request), wrong_offers):
            with self.assertRaises(ValueError):
                ag.inspect_request(self.fixed, request,
                    expected_source_sha256=ag.digest(request['source']), expected_request_sha256=ag.digest(request))
        with self.assertRaises(ValueError):
            ag.check_offer(self.fixed, self.request['source'], self.request['context'],
                           tuple(self.request['expected_charges']), self.request['offers'][0])

    def test_external_source_anchor_cannot_be_replaced(self):
        with self.assertRaises(ValueError):
            ag.inspect_request(self.fixed, self.request, expected_source_sha256='0' * 64,
                               expected_request_sha256=ag.digest(self.request))

    def test_task_catalog_identity_cannot_be_rehashed_away(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r.__setitem__('fixed_catalog_sha256', '0' * 64))

    def test_unknown_request_fields_are_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r.__setitem__('accepted', True))

    def test_unknown_offer_fields_are_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r['offers'][0].__setitem__('accepted', True))

    def test_bool_is_not_an_inspection_budget(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r.__setitem__('inspection_budget', True))

    def test_negative_inspection_budget_is_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r.__setitem__('inspection_budget', -1))

    def test_oversized_inspection_budget_is_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r.__setitem__('inspection_budget', ag.MAX_OFFERS + 1))

    def test_oversized_offer_inventory_is_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r.__setitem__('offers', r['offers'] * (ag.MAX_OFFERS + 1)))

    def test_integer_cannot_replace_a_proposal_verdict_boolean(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r['offers'][0]['evidence']['proposal'].__setitem__('verdicts', [1]))

    def test_program_pair_length_mismatch_is_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r['source']['program_keys'].pop())

    def test_noncanonical_declared_set_is_refused(self):
        with self.assertRaises(ValueError):
            self.mutate(lambda r: r['source']['declared'].reverse())

    def test_result_reconstruction_rejects_forged_exhaustion(self):
        request = self.cases['zero_budget']; result = self.inspect(request); result['status'] = 'exhausted'
        with self.assertRaises(ValueError):
            ag.verify_result(self.fixed, request, result, expected_source_sha256=ag.digest(request['source']),
                             expected_request_sha256=ag.digest(request))

    def test_result_reconstruction_rejects_forged_formal_acceptance(self):
        result = self.inspect(); result['formal_acceptance_established'] = True
        with self.assertRaises(ValueError):
            ag.verify_result(self.fixed, self.request, result,
                expected_source_sha256=ag.digest(self.request['source']), expected_request_sha256=ag.digest(self.request))

    def test_result_reconstruction_rejects_omitted_refusal(self):
        request = self.cases['refusal_then_selected']; result = self.inspect(request); result['checks'].pop(0)
        with self.assertRaises(ValueError):
            ag.verify_result(self.fixed, request, result, expected_source_sha256=ag.digest(request['source']),
                             expected_request_sha256=ag.digest(request))

    def test_pure_inspection_has_no_filesystem_process_or_network_work(self):
        with (patch('builtins.open', side_effect=AssertionError('unexpected filesystem')),
              patch('pathlib.Path.open', side_effect=AssertionError('unexpected filesystem')),
              patch('subprocess.Popen', side_effect=AssertionError('unexpected process')),
              patch('socket.socket', side_effect=AssertionError('unexpected network'))):
            self.assertEqual(self.inspect()['status'], 'accepted')

    def test_inspection_does_not_mutate_request_or_fixed_meanings(self):
        before = ag.canonical(self.request); fixed = self.fixed.interpretation_bytes
        self.inspect()
        self.assertEqual(ag.canonical(self.request), before)
        self.assertEqual(self.fixed.interpretation_bytes, fixed)

    def test_prepared_packet_is_frozen_and_returned_dictionary_detached(self):
        with self.assertRaises(FrozenInstanceError):
            self.prepared.packet_bytes = b'changed'
        packet = self.prepared.packet; packet['claims']['promotion_authorized'] = True
        self.assertIs(self.prepared.packet['claims']['promotion_authorized'], False)

    def test_fixed_configuration_copy_cannot_change_future_checks(self):
        cfg = self.fixed.configuration(); cfg['policy']['cost_limit'] = 0; cfg['root'] = 'changed'
        self.assertEqual(self.inspect()['status'], 'accepted')

    def test_all_broader_claims_are_strictly_false(self):
        self.assertEqual(len(self.packet['claims']), 24)
        self.assertEqual(set(self.packet['claims']), set(ag.FALSE_CLAIMS))
        self.assertTrue(all(value is False for value in self.packet['claims'].values()))
        self.assertIs(self.packet['summary']['formal_acceptance_required'], True)

    def test_packet_claim_escalation_is_refused(self):
        self.packet_refused(lambda p: p['claims'].__setitem__('promotion_authorized', True))

    def test_packet_scope_escalation_is_refused(self):
        self.packet_refused(lambda p: p['scope'].__setitem__('new_physical_successors', 1))

    def test_packet_baseline_substitution_is_refused(self):
        self.packet_refused(lambda p: p.__setitem__('base_commit', ag.af.BASE))

    def test_retained_execution_substitution_is_refused(self):
        self.packet_refused(lambda p: p['retained_execution_hex'].__setitem__(ag.AF_ROOT + '/execution.json', b'{}'.hex()))

    def test_retained_source_hash_substitution_is_refused(self):
        self.packet_refused(lambda p: p['inherited_source_sha256'].__setitem__(next(iter(p['inherited_source_sha256'])), '0' * 64))

    def test_packet_selected_result_is_recomputed(self):
        self.packet_refused(lambda p: p['selected_result'].__setitem__('examined', 0))

    def test_packet_cannot_omit_the_budget_stop_control(self):
        self.packet_refused(lambda p: p['cases'].pop(2))

    def test_packet_summary_is_not_a_source_of_acceptance(self):
        self.packet_refused(lambda p: p['summary'].__setitem__('selected_status', 'exhausted'))

    def test_fixed_interpretation_bytes_cannot_be_changed(self):
        with self.assertRaises(ValueError):
            ag.FixedInterpretation(self.fixed.interpretation_bytes + b' ')

    def test_existing_preparation_directory_is_refused_before_af_work(self):
        with tempfile.TemporaryDirectory(prefix='phase17ag-existing-') as tmp:
            with patch.object(ag.af, 'prepare_second_step', side_effect=AssertionError('must refuse first')):
                with self.assertRaises(ValueError):
                    ag.prepare_successor_interface(ROOT, Path(tmp))

    def test_repository_internal_preparation_is_refused_before_af_work(self):
        with patch.object(ag.af, 'prepare_second_step', side_effect=AssertionError('must refuse first')):
            with self.assertRaises(ValueError):
                ag.prepare_successor_interface(ROOT, ROOT / 'uncreated-ag-test-packages')

    def test_external_packet_anchor_is_required(self):
        with self.assertRaises(ValueError):
            ag.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)

    def test_controlled_case_inventory_and_scopes_are_exact(self):
        self.assertEqual(tuple(self.cases), ag.CASE_NAMES)
        self.assertEqual(len(self.cases), 16)
        self.assertEqual(self.packet['summary']['new_physical_successors'], 0)
        self.assertFalse(self.packet['summary']['inspection_fuel_is_resource_accounting'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
