"""AH producer coverage, truthful evaluator receipts and finite reference grants.

These are local reference computations. The separate pinned Lean gate supplies
formal evidence; no test claims a live campaign, activation or new physical step.
"""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import producer_domain as ah

ROOT = Path(__file__).resolve().parents[3]


class ProducerDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.interface = ah.ag.PreparedSuccessorInterface((ROOT / ah.AG_ROOT / 'packet.json').read_bytes())
        cls.fixed = ah._fixed_interpretation(cls.interface.second_step().interpretation().packet_bytes)
        cls.derived = ah._derive(cls.interface)
        cls.cases = {case['name']: case for case in cls.derived['cases']}
        cls.first = cls.cases['first_source']
        cls.second = cls.cases['second_source']

    def inspect(self, case=None, *, request=None, grant=None, journal_path=None):
        case = self.first if case is None else case
        request = copy.deepcopy(case['request'] if request is None else request)
        grant = copy.deepcopy(case['grant'] if grant is None else grant)
        return ah.inspect_session(self.interface, request, grant,
            expected_source_sha256=request['source_sha256'], expected_request_sha256=ah.digest(request),
            expected_authorization_sha256=ah.digest(grant), journal_path=journal_path)

    def request_refused(self, change, case=None):
        case = self.first if case is None else case
        request = copy.deepcopy(case['request']); change(request)
        grant = ah.make_grant(request)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            self.inspect(case, request=request, grant=grant)

    def grant_refused(self, change, case=None):
        case = self.first if case is None else case
        grant = copy.deepcopy(case['grant']); change(grant)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            self.inspect(case, grant=grant)

    def test_exact_completed_ag_packet_and_base(self):
        self.assertEqual(ah.BASE, '187b13a08dcddb76152a1f66f45872e554d36cb8')
        self.assertEqual(ah.sha(self.interface.packet_bytes), ah.AG_PACKET_SHA)
        self.assertEqual(len(ah._execution((ROOT / ah.AG_ROOT / 'execution.json').read_bytes())['source_sha256']), 545)

    def test_two_sources_bind_the_retained_af_physical_pair(self):
        second = self.interface.second_step().packet
        for basis, side in zip(self.derived['sources'], ('before', 'after'), strict=True):
            self.assertEqual(basis['source'], ah.ag._state_from_af(second['finite_projection'][side]))
            self.assertEqual(basis['model_state']['active_package_hash'], basis['source']['package_hash'])
            self.assertEqual(basis['model_state']['installed_program_hashes'], sorted(basis['source']['keys']))
            self.assertEqual(basis['model_state']['capability_frontier'], basis['source']['named_frontier'])

    def test_second_source_increments_only_selected_generation_and_model_index(self):
        before, after = self.derived['sources']
        self.assertEqual(after['model_state']['model_index'], before['model_state']['model_index'] + 1)
        for family in ah.FAMILIES:
            self.assertEqual(after['model_state']['component_generations'][family],
                before['model_state']['component_generations'][family] + int(family == 'adapter_policy'))
        self.assertEqual(after['turn_index'], before['turn_index'] + 1)

    def test_reference_source_history_preserves_historical_archive_root(self):
        before, after = self.derived['sources']
        self.assertEqual(after['history']['parent_state_hash'], before['model_state_hash'])
        self.assertEqual(after['history']['parent_history_hash'], before['history_hash'])
        self.assertEqual(after['history_hash'], ah.digest(after['history']))
        self.assertEqual(before['model_state']['archive_root_hash'], after['model_state']['archive_root_hash'])
        self.assertFalse(after['history']['root_authorized'])
        self.assertFalse(after['physical_candidate_active'])

    def test_reference_public_fields_are_pinned_before_selection(self):
        before, after = self.derived['sources']
        self.assertEqual(after['public_nonce_hash'], ah.digest(
            {'domain': ah.POLICY, 'source': 'af_after', 'field': 'public_nonce'}))
        self.assertEqual(after['challenge_commitment_hash'], ah.digest(
            {'domain': ah.POLICY, 'source': 'af_after', 'field': 'opaque_commitment'}))
        self.assertNotEqual(before['public_nonce_hash'], after['public_nonce_hash'])
        self.assertNotEqual(before['challenge_commitment_hash'], after['challenge_commitment_hash'])

    def test_each_source_uses_full_actual_32_descriptor_domain(self):
        for case in (self.first, self.second):
            request = case['request']; programs = request['programs']
            self.assertEqual(len(programs), 32)
            self.assertEqual([ah.digest(program) for program in programs],
                             [row['key'] for row in request['context']['rows']])
            self.assertEqual({(program['family'], program['variant']) for program in programs},
                             {(family, variant) for family in ah.FAMILIES for variant in range(4)})
            self.assertEqual(request['grammar_sha256'], ah.digest(programs))

    def test_source_specific_grammar_context_and_keys_change(self):
        first, second = self.first['request'], self.second['request']
        self.assertNotEqual(first['source_sha256'], second['source_sha256'])
        self.assertNotEqual(first['grammar_sha256'], second['grammar_sha256'])
        self.assertNotEqual(first['context']['context_hash'], second['context']['context_hash'])
        self.assertNotEqual(first['context']['generator'], second['context']['generator'])
        self.assertEqual(first['fixed_catalog_sha256'], second['fixed_catalog_sha256'])

    def test_actual_domain_table_uses_captured_84_term_planner_projection(self):
        for basis in self.derived['sources']:
            self.assertEqual(len(basis['planner_projection']), 84)
            self.assertEqual(basis['planner_weights_sha256'], ah.WEIGHTS_SHA256)
        self.assertEqual(self.derived['sources'][0]['planner_projection'],
                         self.derived['sources'][1]['planner_projection'])

    def test_selected_af_first_program_is_in_actual_domain(self):
        result = self.first['result']; trial = result['trials'][0]
        self.assertEqual((result['status'], result['examined'], trial['index']), ('accepted', 1, 30))
        self.assertEqual(trial['program_hash'], ah.ag.af.SELECTED_PROGRAM)
        self.assertEqual(trial['canonical_task'], 41)
        self.assertTrue(all(trial['check']['obligations'].values()))

    def test_second_source_has_seven_recomputed_rejections_then_success(self):
        result = self.second['result']
        self.assertEqual((result['status'], result['examined']), ('accepted', 8))
        self.assertEqual([trial['verdict'] for trial in result['trials']], [False] * 7 + [True])
        self.assertTrue(all(trial['canonical_task'] is None for trial in result['trials'][:-1]))
        self.assertEqual(result['trials'][-1]['canonical_task'], 56)
        self.assertEqual(result['controller_action'], ah.Action.AWAIT_ROOT_VERIFICATION.value)

    def test_evaluator_selects_least_fixed_missing_realized_contract(self):
        for case in (self.first, self.second):
            trial = case['result']['trials'][-1]
            matches = [i for i, (before, after) in enumerate(
                zip(trial['source_holds'], trial['candidate_holds'], strict=True)) if not before and after]
            self.assertEqual(matches, trial['missing_realized_tasks'])
            self.assertEqual(trial['canonical_task'], min(matches))
            self.assertFalse(trial['source_holds'][trial['canonical_task']])
            self.assertTrue(trial['candidate_holds'][trial['canonical_task']])

    def test_descriptor_with_already_solved_contract_cannot_supply_novelty(self):
        source = self.second['request']['source']
        program = self.interface.second_step().packet['update']['program']
        meaning = ah.missing_contract(self.fixed, source, program)
        self.assertIsNone(meaning['canonical_task'])
        self.assertEqual(meaning['missing_realized_tasks'], [])

    def test_semantically_solved_but_undeclared_contract_is_not_novel(self):
        source = self.first['request']['source']
        self.assertNotIn(259, source['declared'])
        self.assertTrue(self.fixed.check(source, 259))
        program = next(program for program in source['programs']
                       if program['family'] == 'adapter_policy' and program['variant'] == 3
                       and program['parameter_a'] - program['parameter_b'] == 10)
        meaning = ah.missing_contract(self.fixed, source, program)
        self.assertTrue(meaning['source_holds'][259])
        self.assertIsNone(meaning['canonical_task'])

    def test_nonadapter_cannot_rename_a_missing_affine_contract(self):
        program = next(program for program in self.second['request']['programs']
                       if program['family'] == 'optimizer_policy')
        meaning = ah.missing_contract(self.fixed, self.second['request']['source'], program)
        self.assertIsNone(meaning['canonical_task'])
        self.assertEqual(meaning['source_holds'], meaning['candidate_holds'])

    def test_probe_outputs_are_checked_against_fixed_coefficient_characterization(self):
        program = self.interface.second_step().packet['update']['program']
        with self.assertRaisesRegex(ValueError, 'coefficient'):
            ah._missing_contract(self.fixed, self.first['request']['source'], program,
                                 outputs=[[999] * 4, [999] * 4])

    def test_public_contract_checker_cannot_accept_caller_cached_verdicts(self):
        program = self.interface.second_step().packet['update']['program']
        for cached in ({'source_holds': [False] * ah.ae.CATALOG_BOUND},
                       {'outputs': [[999] * 4, [999] * 4]}):
            with self.subTest(cached=tuple(cached)):
                with self.assertRaises(TypeError):
                    ah.missing_contract(self.fixed, self.second['request']['source'], program, **cached)

    def test_old_meanings_and_protected_semantics_survive_accepted_append(self):
        for case in (self.first, self.second):
            source = case['request']['source']; trial = case['result']['trials'][-1]
            after = trial['trial_offer']['next']
            self.assertEqual(after['semantic'], source['semantic'])
            self.assertEqual(after['frozen'], source['frozen'])
            self.assertEqual(after['proofs'], source['proofs'])
            self.assertEqual(after['programs'][:-1], source['programs'])
            self.assertTrue(set(source['declared']) < set(after['declared']))
            self.assertTrue(all(trial['candidate_holds'][:22]))

    def test_actual_controller_decisions_match_independent_present_prefix(self):
        for case in (self.first, self.second):
            context = case['request']['context']; seen = []
            for trial in case['result']['trials']:
                self.assertEqual(trial['index'], ah.reference_choice(context['rows'], seen, context['offset']))
                seen.append(trial['index'])
            self.assertEqual(len(seen), len(set(seen)))

    def test_actual_receipts_reconstruct_every_controller_observation(self):
        result = self.second['result']
        observations = result['final_checkpoint']['observations']
        for trial, observation in zip(result['trials'], observations, strict=True):
            self.assertEqual(observation['program_hash'], trial['program_hash'])
            self.assertEqual(observation['evaluation_hash'], ah.digest(trial['receipt']))
            self.assertEqual(observation['decision_hash'], trial['receipt']['decision_hash'])
            self.assertEqual(observation['verdict'], 'candidate_passed' if trial['verdict'] else 'reject')
        restored = ah.restore(ah.canonical(result['final_checkpoint']),
                              expected_prefix_hash=result['final_prefix_hash'])
        self.assertEqual(ah.decide(restored).action.value, result['controller_action'])

    def test_accepted_proposal_prefix_agrees_with_actual_prior_rejections(self):
        result = self.second['result']; proposal = result['trials'][-1]['trial_offer']['evidence']['proposal']
        self.assertEqual(proposal['choices'], [trial['index'] for trial in result['trials']])
        self.assertEqual(proposal['verdicts'], [trial['verdict'] for trial in result['trials']])
        self.assertEqual(proposal['verdicts'], [False] * 7 + [True])

    def test_complete_ag_acceptance_bridge_uses_recomputed_prefix_charges(self):
        for case in (self.first, self.second):
            result = case['result']; request = result['accepted_ag_request']
            self.assertEqual(request['expected_charges'], result['resource']['charge_sequence'])
            self.assertEqual(request['offers'][0]['update']['charges'], request['expected_charges'])
            self.assertEqual(result['accepted_ag_result']['status'], 'accepted')
            self.assertTrue(all(result['accepted_ag_result']['checks'][0]['obligations'].values()))

    def test_credit_stop_preserves_unexamined_domain(self):
        result = self.cases['second_source_credit_stop']['result']
        self.assertEqual((result['status'], result['examined'], result['unexamined']), ('budget_stop', 4, 28))
        self.assertEqual(result['controller_action'], ah.Action.RESOURCE_EXHAUSTED.value)
        self.assertFalse(result['producer_domain_exhausted'])
        self.assertIsNone(result['accepted_ag_request'])

    def test_zero_credits_produce_no_candidate_or_vector_work(self):
        result = self.cases['second_source_zero_credit']['result']
        self.assertEqual((result['status'], result['examined'], result['resource']['operation_count']),
                         ('budget_stop', 0, 0))
        self.assertEqual(result['resource']['spent'], [0, 0, 0, 0])
        self.assertFalse(result['all_producer_candidates_truthfully_rejected'])

    def test_resource_denial_does_not_forge_controller_exhaustion(self):
        result = self.cases['second_source_resource_stop']['result']
        self.assertEqual((result['status'], result['examined'], result['unexamined']), ('resource_stop', 3, 29))
        self.assertEqual(result['controller_action'], ah.Action.EVALUATE.value)
        self.assertFalse(result['producer_domain_exhausted'])
        self.assertFalse(result['global_successor_nonexistence_established'])
        rows = [ah.load_json_strict(row) for row in bytes.fromhex(result['resource']['journal_hex']).splitlines()]
        self.assertEqual(rows[-2]['body']['kind'], 'denied')
        self.assertEqual(rows[-2]['body']['spent_unchanged'], result['resource']['spent'])

    def test_reference_tariff_counts_exact_operations(self):
        for case in self.derived['cases']:
            result = case['result']; count = result['examined']; resource = result['resource']
            self.assertEqual(resource['operation_count'], 3 * count)
            self.assertEqual(resource['spent'], [count, 2 * count, 8 * count, 8 * count])
            self.assertEqual(resource['charged_cost'], 112 * count)
            self.assertEqual(resource['charge_sequence'], list(ah.ATTEMPT_CHARGES) * count)
            self.assertFalse(resource['timing_measured'])
        self.assertEqual(ah.reference_policy(32).cost_limit, 3584)

    def test_every_result_is_bound_to_preceding_reservation(self):
        resource = self.second['result']['resource']
        rows = [ah.load_json_strict(row) for row in bytes.fromhex(resource['journal_hex']).splitlines()]
        self.assertEqual(ah.sha(bytes.fromhex(resource['journal_hex'])), resource['journal_sha256'])
        previous = '0' * 64
        for index, row in enumerate(rows):
            self.assertEqual(row, ah._event(row['body'], index, previous)); previous = row['hash']
        for index, task in enumerate(resource['work']):
            reserved, result = rows[1 + 2 * index], rows[2 + 2 * index]
            self.assertEqual(reserved['body']['kind'], 'reserve')
            self.assertEqual(reserved['body']['input_sha256'], ah.sha(ah.canonical(task['input'])))
            self.assertEqual(result['body']['reservation_hash'], reserved['hash'])
            self.assertEqual(result['body']['result_sha256'], ah.sha(ah.canonical(task['output'])))

    def test_partial_vector_or_cost_budget_refuses_before_any_attempt(self):
        for limits, cost_limit in (([1, 1, 8, 8], 112), ([1, 2, 8, 8], 111)):
            with self.subTest(limits=limits, cost_limit=cost_limit):
                grant = copy.deepcopy(self.first['grant'])
                grant['policy'] = ah.Policy(tuple(limits), cost_limit).to_json()
                with patch.object(ah, '_admit', side_effect=AssertionError('admission without reservation')), \
                     patch.object(ah, '_probe', side_effect=AssertionError('probe without reservation')):
                    result = self.inspect(grant=grant)
                self.assertEqual((result['status'], result['examined']), ('resource_stop', 0))
                self.assertEqual(result['resource']['spent'], [0, 0, 0, 0])

    def test_durable_reservation_exists_before_each_trusted_probe(self):
        original = ah._probe
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'reference.jsonl'; seen = []
            def observe(program, vector):
                rows = [ah.load_json_strict(row) for row in path.read_bytes().splitlines()]
                self.assertEqual(rows[-1]['body']['kind'], 'reserve')
                self.assertEqual(rows[-1]['body']['operation'], 'vector')
                seen.append(rows[-1]['hash'])
                return original(program, vector)
            with patch.object(ah, '_probe', side_effect=observe):
                result = self.inspect(journal_path=path)
            self.assertEqual(len(seen), 2)
            self.assertEqual(path.read_bytes(), bytes.fromhex(result['resource']['journal_hex']))

    def test_evaluator_failure_retains_unfinished_reservation_without_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'failed.jsonl'
            with patch.object(ah, 'execute_matrix', return_value=[999] * 4):
                with self.assertRaisesRegex(ValueError, 'evaluators disagree'):
                    self.inspect(journal_path=path)
            rows = [ah.load_json_strict(row) for row in path.read_bytes().splitlines()]
            self.assertEqual(rows[-1]['body']['kind'], 'reserve')
            self.assertEqual(rows[-1]['body']['operation'], 'vector')
            self.assertFalse(any(row['body']['kind'] == 'seal' for row in rows))

    def test_existing_reference_journal_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'preserved.jsonl'; path.write_bytes(b'preserve original\n')
            with self.assertRaises(ValueError):
                self.inspect(journal_path=path)
            self.assertEqual(path.read_bytes(), b'preserve original\n')

    def test_changed_source_even_under_new_self_hash_is_refused(self):
        def change(request):
            request['source']['package_hash'] = ah.digest(['substituted package'])
            request['source_sha256'] = ah.digest(request['source'])
        self.request_refused(change)

    def test_source_model_hash_substitution_is_refused(self):
        self.request_refused(lambda request: request.update(model_state_hash=ah.digest(['wrong model'])))

    def test_source_history_substitution_is_refused(self):
        self.request_refused(lambda request: request.update(history_hash=ah.digest(['wrong history'])))

    def test_other_source_domain_cannot_be_reused(self):
        self.request_refused(lambda request: request.update(programs=copy.deepcopy(self.second['request']['programs'])))

    def test_missing_grammar_descriptor_is_refused(self):
        self.request_refused(lambda request: request['programs'].pop())

    def test_duplicate_grammar_descriptor_is_refused(self):
        self.request_refused(lambda request: request['programs'].__setitem__(0, copy.deepcopy(request['programs'][1])))

    def test_reordered_grammar_descriptors_are_refused(self):
        self.request_refused(lambda request: request['programs'].reverse())

    def test_changed_seeded_parameter_is_refused(self):
        def change(request):
            program = request['programs'][0]
            program['parameter_a'] = 1 if program['parameter_a'] != 1 else 2
        self.request_refused(change)

    def test_changed_program_key_even_with_same_family_is_refused(self):
        self.request_refused(lambda request: request['context']['rows'][0].update(key=ah.digest(['wrong program'])))

    def test_changed_planner_rank_is_refused(self):
        self.request_refused(lambda request: request['context']['rows'][0].update(base_score=99999999))

    def test_changed_rejection_tie_is_refused(self):
        self.request_refused(lambda request: request['context']['rows'][0]['ties'].__setitem__(1, 0))

    def test_changed_fallback_offset_is_refused(self):
        self.request_refused(lambda request: request['context'].update(offset=(request['context']['offset'] + 1) % 32))

    def test_changed_context_parent_is_refused(self):
        self.request_refused(lambda request: request['context'].update(parent_package=ah.digest(['wrong parent'])))

    def test_changed_catalog_identity_is_refused(self):
        self.request_refused(lambda request: request.update(fixed_catalog_sha256=ah.digest(['new meanings'])))

    def test_changed_evaluator_policy_is_refused(self):
        self.request_refused(lambda request: request.update(evaluator='caller-supplied-pass-policy'))

    def test_extra_request_field_cannot_select_desired_task(self):
        self.request_refused(lambda request: request.update(desired_task=56))

    def test_bool_credits_cannot_be_normalized_into_integer(self):
        self.request_refused(lambda request: request['context'].update(credits=True))

    def test_tuple_grammar_is_rejected_before_canonicalization(self):
        self.request_refused(lambda request: request.update(programs=tuple(request['programs'])))

    def test_external_request_hash_is_required(self):
        case = self.first
        with self.assertRaisesRegex(ValueError, 'external anchor'):
            ah.inspect_session(self.interface, case['request'], case['grant'],
                expected_source_sha256=case['request']['source_sha256'],
                expected_request_sha256=ah.digest(['different request']),
                expected_authorization_sha256=ah.digest(case['grant']))

    def test_external_grant_hash_is_required(self):
        case = self.first
        with self.assertRaisesRegex(ValueError, 'external anchor'):
            ah.inspect_session(self.interface, case['request'], case['grant'],
                expected_source_sha256=case['request']['source_sha256'],
                expected_request_sha256=ah.digest(case['request']),
                expected_authorization_sha256=ah.digest(['different grant']))

    def test_external_source_hash_is_required(self):
        case = self.first
        with self.assertRaisesRegex(ValueError, 'external anchor'):
            ah.inspect_session(self.interface, case['request'], case['grant'],
                expected_source_sha256=ah.digest(['different source']),
                expected_request_sha256=ah.digest(case['request']),
                expected_authorization_sha256=ah.digest(case['grant']))

    def test_grant_cannot_be_moved_between_source_states(self):
        with self.assertRaisesRegex(ValueError, 'stale or retargeted'):
            self.inspect(self.second, grant=self.first['grant'])

    def test_grant_context_substitution_is_refused(self):
        self.grant_refused(lambda grant: grant.update(context_hash=ah.digest(['other context'])))

    def test_grant_history_substitution_is_refused(self):
        self.grant_refused(lambda grant: grant.update(history_hash=ah.digest(['other history'])))

    def test_grant_catalog_substitution_is_refused(self):
        self.grant_refused(lambda grant: grant.update(fixed_catalog_sha256=ah.digest(['other catalog'])))

    def test_grant_request_substitution_is_refused(self):
        self.grant_refused(lambda grant: grant.update(request_sha256=ah.digest(['other request'])))

    def test_grant_candidate_limit_cannot_retarget_context_credits(self):
        self.grant_refused(lambda grant: grant.update(candidate_limit=31))

    def test_grant_issuer_is_an_external_string_not_authenticated_authority(self):
        grant = copy.deepcopy(self.first['grant']); grant['issuer'] = 'different explicitly pinned reference issuer'
        result = self.inspect(grant=grant)
        self.assertEqual(result['status'], 'accepted')
        self.assertFalse(result['issuer_authenticated'])
        self.assertFalse(result['campaign_authority_integrated'])

    def test_grant_cannot_claim_authenticated_issuer_or_campaign_authority(self):
        for key in ('issuer_authenticated', 'campaign_authority', 'promotion_authorized'):
            with self.subTest(key=key):
                self.grant_refused(lambda grant, key=key: grant.update({key: True}))

    def test_grant_cannot_expand_reference_resource_profile(self):
        def change(grant):
            grant['policy']['limits'][0] = 33
        self.grant_refused(change)

    def test_grant_cannot_change_tariff_weights(self):
        self.grant_refused(lambda grant: grant['policy']['weights'].__setitem__(0, 0))

    def test_grant_bool_resource_limit_is_refused(self):
        self.grant_refused(lambda grant: grant['policy']['limits'].__setitem__(0, True))

    def test_input_mutation_after_anchor_does_not_change_evaluation(self):
        request = copy.deepcopy(self.first['request']); grant = copy.deepcopy(self.first['grant'])
        source_hash, request_hash, grant_hash = request['source_sha256'], ah.digest(request), ah.digest(grant)
        original = ah.reference_choice
        def mutate_original(rows, seen, offset):
            request['programs'].clear(); request['source']['declared'].clear()
            grant['policy']['limits'][0] = 0
            return original(rows, seen, offset)
        with patch.object(ah, 'reference_choice', side_effect=mutate_original):
            result = ah.inspect_session(self.interface, request, grant,
                expected_source_sha256=source_hash, expected_request_sha256=request_hash,
                expected_authorization_sha256=grant_hash)
        self.assertEqual(result, self.first['result'])

    def test_returned_request_is_detached_from_retained_source(self):
        request = ah.make_request(self.interface, 'af_before')
        request['source']['declared'].clear(); request['programs'].clear()
        self.assertEqual(ah.make_request(self.interface, 'af_before'), self.first['request'])

    def test_false_result_receipt_or_verdict_is_rejected_by_reconstruction(self):
        result = copy.deepcopy(self.first['result']); result['trials'][0]['verdict'] = False
        case = self.first
        with self.assertRaisesRegex(ValueError, 'complete recomputation'):
            ah.verify_session(self.interface, case['request'], case['grant'], result,
                expected_source_sha256=case['request']['source_sha256'],
                expected_request_sha256=ah.digest(case['request']),
                expected_authorization_sha256=ah.digest(case['grant']))

    def test_fixed_scope_never_claims_live_or_physical_success(self):
        self.assertEqual(ah.SCOPE['fresh_worker_sessions'], 0)
        self.assertEqual(ah.SCOPE['fresh_live_challenges'], 0)
        for case in self.derived['cases']:
            result = case['result']
            self.assertFalse(result['new_physical_successor_created'])
            self.assertFalse(result['physical_execution_attested'])
            self.assertFalse(result['promotion_authorized'])
            self.assertFalse(result['global_successor_nonexistence_established'])
        self.assertEqual(len(ah.FALSE_CLAIMS), 24)

    def test_source_selector_and_budget_bounds_are_strict(self):
        with self.assertRaises(ValueError):
            ah.source_basis(self.interface, 'arbitrary-source')
        for value in (-1, 33, True, 1.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ah.make_request(self.interface, 'af_before', candidate_credits=value)

    def test_reconstruction_mode_preserves_packet_without_creating_durable_journals(self):
        # The inherited physical reconstruction already has its own gate. Reuse
        # its pinned AG result here to exercise only the new preparation mode.
        def retained_inherited(root, packages):
            self.assertEqual(root, ROOT)
            packages.mkdir(parents=True)
            return self.interface
        with tempfile.TemporaryDirectory() as temporary, patch.object(
                ah.ag, 'prepare_successor_interface', side_effect=retained_inherited):
            memory = Path(temporary) / 'memory'
            durable = Path(temporary) / 'durable'
            reconstructed = ah.prepare_producer_domain(
                ROOT, memory, persist_reference_journals=False)
            self.assertFalse((memory / 'reference-sessions').exists())
            prepared = ah.prepare_producer_domain(ROOT, durable)
            self.assertEqual(reconstructed.packet_bytes, prepared.packet_bytes)
            self.assertEqual({path.name for path in (durable / 'reference-sessions').iterdir()},
                             {case['name'] + '.jsonl' for case in prepared.packet['cases']})
            for case in prepared.packet['cases']:
                self.assertEqual((durable / 'reference-sessions' / (case['name'] + '.jsonl')).read_bytes(),
                                 bytes.fromhex(case['result']['resource']['journal_hex']))

    def test_preparation_journal_mode_requires_exact_bool_before_work(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(
                ah.ag, 'prepare_successor_interface', side_effect=AssertionError('work before mode check')):
            packages = Path(temporary) / 'unused'
            for value in (0, 1, None, 'false', [], {}):
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'exact bool'):
                    ah.prepare_producer_domain(ROOT, packages, persist_reference_journals=value)
            self.assertFalse(packages.exists())


if __name__ == '__main__':
    unittest.main()
