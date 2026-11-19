"""AI authority provenance, durable issuance, truthful completion and refusal.

These controlled reference tests do not confer live campaign or promotion
authority. The separate pinned Lean gate supplies the formal result.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import controller_authority as ai

ROOT = Path(__file__).resolve().parents[3]


class ControllerAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = ai.ah.PreparedProducerDomain((ROOT / ai.AH_ROOT / 'packet.json').read_bytes())
        cls.identity = ai.authority_identity(ROOT)
        cls.derived = ai._derive(cls.prepared, cls.identity)
        cls.cases = {case['name']: case for case in cls.derived['cases']}
        cls.main = cls.cases['shared_two_sources']
        cls.first_result = cls.main['sessions'][0]['result']
        cls.second_result = cls.main['sessions'][1]['result']

    def policy(self, **options):
        return ai.make_authority_policy(self.prepared, self.identity,
                                        authority_id='phase17ai.unit-test-authority', **options)

    @contextmanager
    def authority(self, *, path=None, policy=None, **options):
        policy = self.policy(**options) if policy is None else policy
        authority = ai.ControllerAuthority(path, self.prepared, self.identity,
            expected_policy=policy, expected_policy_sha256=ai.digest(policy))
        try:
            yield authority
        finally:
            authority.close()

    def reserve(self, authority, source_id='af_before'):
        return authority.reserve(source_id, expected_head=authority.state.head,
            expected_prefix_hash=authority.state.source_states[source_id]['prefix_hash'])

    def complete_first(self, authority):
        lease = self.reserve(authority)
        session = authority.complete(lease, self.first_result, expected_head=authority.state.head)
        return lease, session

    def reopen(self, authority, *, head=None, sessions=None, raw=None):
        image = authority.raw if raw is None else raw
        expected = authority.state.head if head is None else head
        policy = authority.policy
        completed = authority.sessions if sessions is None else sessions
        path = authority.path; authority.close()
        return ai.ControllerAuthority(path, self.prepared, self.identity,
            expected_policy=policy, expected_policy_sha256=ai.digest(policy), expected_head=expected,
            completed_sessions=completed, retained_raw=image if path is None else None)

    def replay(self, case=None, *, events=None, sessions=None, head=None, policy=None):
        case = self.main if case is None else case
        events = case['events'] if events is None else events
        raw = b''.join(ai.canonical(row) + b'\n' for row in events)
        return ai.replay_authority(raw, self.prepared, self.identity,
            expected_policy=case['authority_policy'] if policy is None else policy,
            expected_policy_sha256=case['policy_sha256'],
            expected_head=case['final_state']['head'] if head is None else head,
            sessions=case['sessions'] if sessions is None else sessions)

    @staticmethod
    def rechain(events):
        result = []
        for index, row in enumerate(events):
            result.append(ai._event(row['body'], index, result[-1]['hash'] if result else ai.ZERO))
        return result

    def test_exact_completed_ah_packet_and_execution(self):
        self.assertEqual(ai.BASE, '8903e306229a1caf22315121b519443639537204')
        self.assertEqual(ai.sha(self.prepared.packet_bytes), ai.AH_PACKET_SHA)
        record = ai._execution((ROOT / ai.AH_ROOT / 'execution.json').read_bytes())
        self.assertEqual(len(record['source_sha256']), 555)

    def test_actual_implementation_bytes_are_bound(self):
        self.assertEqual(set(self.identity['code_sha256']), set(ai.CODE_PATHS))
        for path, expected in self.identity['code_sha256'].items():
            self.assertEqual(ai.sha((ROOT / path).read_bytes()), expected)

    def test_policy_preserves_unchanged_objective_catalog_and_evaluator(self):
        policy = self.policy()
        self.assertEqual(policy['objective'], ai.OBJECTIVE)
        self.assertEqual(policy['evaluator'], ai.ah.EVALUATOR)
        self.assertEqual({p['fixed_catalog_sha256'] for p in policy['source_permits']},
                         {policy['fixed_catalog_sha256']})
        self.assertFalse(policy['external_issuer_authenticated'])
        self.assertFalse(policy['campaign_authority_integrated'])
        self.assertFalse(policy['complete_resource_accounting'])

    def test_policy_binds_actual_restored_initial_controller_checkpoints(self):
        for permit in self.policy()['source_permits']:
            prefix = ai.restore(ai.canonical(permit['initial_checkpoint']),
                                expected_prefix_hash=permit['initial_prefix_hash'])
            self.assertEqual(ai.sha(ai.checkpoint(prefix)), permit['initial_checkpoint_sha256'])
            self.assertEqual(prefix.frozen.freeze_hash, permit['freeze_hash'])
            self.assertEqual(ai.decide(prefix).action, ai.Action.EVALUATE)

    def test_source_permits_have_distinct_model_history_context_and_controller(self):
        before, after = self.policy()['source_permits']
        for key in ('source_sha256', 'model_state_hash', 'history_hash', 'context_hash',
                    'request_sha256', 'freeze_hash', 'initial_prefix_hash'):
            self.assertNotEqual(before[key], after[key])

    def test_shared_authority_reserves_full_two_session_envelopes(self):
        state = self.main['final_state']
        self.assertEqual(state['reserved'], [64, 128, 512, 512])
        self.assertEqual(state['reserved_cost'], 7168)
        self.assertEqual(state['serial'], 2)
        self.assertEqual(state['consumed'], ['af_before', 'af_after'])

    def test_actual_work_is_distinct_from_nonrefundable_reserved_envelope(self):
        self.assertEqual([s['result']['examined'] for s in self.main['sessions']], [1, 8])
        self.assertEqual(sum(s['result']['resource']['charged_cost'] for s in self.main['sessions']), 1008)
        self.assertGreater(self.main['final_state']['reserved_cost'], 1008)

    def test_completed_sources_record_exact_final_actual_controller_checkpoints(self):
        for session in self.main['sessions']:
            final = self.main['final_state']['source_states'][session['source_id']]
            self.assertEqual(final['prefix_hash'], session['result']['final_prefix_hash'])
            self.assertEqual(final['checkpoint'], session['result']['final_checkpoint'])
            self.assertEqual(final['checkpoint_sha256'], ai.sha(ai.canonical(final['checkpoint'])))

    def test_selected_source_results_match_the_inherited_ah_results(self):
        cases = {c['name']: c for c in self.prepared.packet['cases']}
        for source, old in zip(self.main['sessions'], ('first_source', 'second_source'), strict=True):
            self.assertEqual(ai.canonical(source['result']), ai.canonical(cases[old]['result']))

    def test_aggregate_denial_happens_before_second_evaluation(self):
        case = self.cases['aggregate_denial']
        self.assertEqual(case['status'], 'resource_denied')
        self.assertEqual(len(case['sessions']), 1)
        self.assertTrue(case['budget_denied_before_evaluation'])
        self.assertEqual(case['final_state']['reserved'], [32, 64, 256, 256])
        self.assertEqual(case['events'][-1]['body']['kind'], 'deny')

    def test_reference_denial_is_not_controller_exhaustion(self):
        case = self.cases['reference_stop']; result = case['sessions'][0]['result']
        self.assertEqual((result['status'], result['examined']), ('resource_stop', 3))
        self.assertEqual(result['controller_action'], ai.Action.EVALUATE.value)
        self.assertFalse(result['producer_domain_exhausted'])

    def test_credit_stop_is_not_producer_domain_exhaustion(self):
        result = self.cases['credit_stop']['sessions'][0]['result']
        self.assertEqual((result['status'], result['examined']), ('budget_stop', 4))
        self.assertFalse(result['producer_domain_exhausted'])
        self.assertFalse(result['global_successor_nonexistence_established'])

    def test_interrupted_reservation_remains_charged_and_unresolved(self):
        case = self.cases['interrupted_reservation']; state = case['final_state']
        self.assertEqual(state['status'], 'pending')
        self.assertEqual(state['reserved'], [32, 64, 256, 256])
        self.assertIsNotNone(state['pending'])
        self.assertEqual(case['sessions'], [])
        self.assertTrue(case['pending_takeover_refused'])

    def test_all_journals_have_exact_images_and_hashes(self):
        images = ai.authority_journal_images(self.derived)
        self.assertEqual(len(images), 10)
        for case in self.derived['cases']:
            self.assertEqual(images[case['journal_name']],
                             b''.join(ai.canonical(row) + b'\n' for row in case['events']))
        for name, raw in images.items():
            self.assertEqual(ai.sha(raw), self.derived['journal_images'][name]['sha256'])

    def test_summary_preserves_scope(self):
        summary = self.derived['summary']
        self.assertEqual((summary['completed_reference_sessions'], summary['issued_reference_leases']), (5, 6))
        self.assertEqual((summary['reference_candidate_attempts'], summary['metered_reference_operations']), (17, 51))
        self.assertFalse(summary['external_issuer_authenticated'])
        self.assertFalse(summary['complete_resource_accounting'])
        self.assertEqual(summary['fresh_worker_sessions'], 0)

    def test_wrong_independent_policy_hash_is_rejected(self):
        policy = self.policy()
        with self.assertRaises(ValueError):
            ai.ControllerAuthority(None, self.prepared, self.identity,
                expected_policy=policy, expected_policy_sha256='f' * 64)

    def test_self_rehashed_evaluator_substitution_is_rejected(self):
        policy = self.policy(); policy['evaluator'] = 'candidate-selected-evaluator'
        with self.assertRaises(ValueError), self.authority(policy=policy):
            pass

    def test_self_rehashed_objective_substitution_is_rejected(self):
        policy = self.policy(); policy['objective'] = 'candidate-selected-task-meaning'
        with self.assertRaises(ValueError), self.authority(policy=policy):
            pass

    def test_self_rehashed_source_permit_substitution_is_rejected(self):
        policy = self.policy(); policy['source_permits'][0]['model_state_hash'] = 'd' * 64
        with self.assertRaises(ValueError), self.authority(policy=policy):
            pass

    def test_self_rehashed_initial_controller_substitution_is_rejected(self):
        policy = self.policy(); policy['source_permits'][0]['initial_prefix_hash'] = 'd' * 64
        with self.assertRaises(ValueError), self.authority(policy=policy):
            pass

    def test_code_identity_substitution_is_rejected_even_with_updated_identity_hash(self):
        identity = copy.deepcopy(self.identity)
        key = next(iter(identity['code_sha256'])); identity['code_sha256'][key] = 'b' * 64
        identity['implementation_sha256'] = ai.digest(identity['code_sha256'])
        with self.assertRaises(ValueError):
            ai.make_authority_policy(self.prepared, identity, authority_id='forged')

    def test_boolean_allowances_and_extra_policy_fields_are_rejected(self):
        for key in ('total_attempts', 'session_attempts', 'candidate_credits'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.policy(**{key: True})
        policy = self.policy(); policy['candidate_authorizes_itself'] = True
        with self.assertRaises(ValueError), self.authority(policy=policy):
            pass

    def test_policy_scope_escalation_is_rejected(self):
        for key in ('external_issuer_authenticated', 'campaign_authority_integrated',
                    'complete_resource_accounting', 'promotion_authorized'):
            policy = self.policy(); policy[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError), self.authority(policy=policy):
                pass

    def test_policy_and_identity_properties_are_detached_snapshots(self):
        policy = self.policy(); identity = copy.deepcopy(self.identity)
        with self.authority(policy=policy) as authority:
            policy['total_attempts'] = 999
            authority.policy['source_permits'][0]['source_sha256'] = 'b' * 64
            authority.identity['code_sha256'].clear()
            self.assertEqual(authority.policy['total_attempts'], 64)
            self.assertEqual(authority.identity, identity)
            self.reserve(authority)

    def test_stale_authority_head_cannot_issue_a_lease(self):
        with self.authority() as authority:
            before = authority.raw
            with self.assertRaises(ValueError):
                authority.reserve('af_before', expected_head='d' * 64,
                    expected_prefix_hash=authority.state.source_states['af_before']['prefix_hash'])
            self.assertEqual(authority.raw, before)

    def test_stale_controller_prefix_cannot_issue_a_lease(self):
        with self.authority() as authority:
            before = authority.raw
            with self.assertRaises(ValueError):
                authority.reserve('af_before', expected_head=authority.state.head,
                                  expected_prefix_hash='d' * 64)
            self.assertEqual(authority.raw, before)

    def test_unknown_source_cannot_issue_a_lease(self):
        with self.authority() as authority:
            with self.assertRaises(ValueError):
                authority.reserve('invented', expected_head=authority.state.head,
                                  expected_prefix_hash='d' * 64)

    def test_terminal_initial_controller_cannot_receive_a_lease(self):
        with self.authority(candidate_credits=0) as authority:
            before = authority.raw
            with self.assertRaises(ValueError):
                self.reserve(authority)
            self.assertEqual(authority.raw, before)

    def test_zero_session_allowance_cannot_receive_a_lease(self):
        with self.authority(session_attempts=0) as authority:
            before = authority.raw
            with self.assertRaises(ValueError):
                self.reserve(authority)
            self.assertEqual(authority.raw, before)

    def test_budget_denial_calls_no_reference_evaluator(self):
        with self.authority(total_attempts=31) as authority, patch.object(ai.ah, 'inspect_session') as inspect:
            with self.assertRaises(ai.ResourceExhausted):
                self.reserve(authority)
            inspect.assert_not_called()
            self.assertEqual(authority.state.status, 'resource_denied')
            self.assertEqual(authority.state.reserved, (0, 0, 0, 0))

    def test_lease_is_bound_to_policy_source_prefix_and_exact_envelope(self):
        with self.authority() as authority:
            before = authority.state.head; lease = self.reserve(authority)
            self.assertEqual(lease['previous_head'], before)
            self.assertEqual(lease['authority_policy_sha256'], authority.policy_sha256)
            self.assertEqual(lease['source_permit']['source_id'], 'af_before')
            self.assertEqual(lease['reserved_envelope']['limits'], [32, 64, 256, 256])
            self.assertEqual(authority.state.pending, lease)

    def test_returned_lease_mutation_cannot_change_pending_authority_state(self):
        with self.authority() as authority:
            lease = self.reserve(authority); original = authority.state.pending
            lease['reference_grant']['policy']['limits'][0] = 999
            self.assertEqual(authority.state.pending, original)
            with self.assertRaises(ValueError):
                authority.execute(lease, expected_head=authority.state.head)

    def test_pending_reservation_cannot_issue_another_lease(self):
        with self.authority() as authority:
            self.reserve(authority); before = authority.raw
            with self.assertRaises(ValueError):
                self.reserve(authority, 'af_after')
            self.assertEqual(authority.raw, before)

    def test_completed_source_controller_revision_cannot_be_reset(self):
        with self.authority() as authority:
            self.complete_first(authority); before = authority.raw
            with self.assertRaises(ValueError):
                self.reserve(authority)
            self.assertEqual(authority.raw, before)

    def test_completion_cannot_refund_unused_envelope(self):
        with self.authority() as authority:
            lease = self.reserve(authority); reserved = authority.state.reserved
            authority.complete(lease, self.first_result, expected_head=authority.state.head)
            self.assertEqual(authority.state.reserved, reserved)
            self.assertEqual(authority.state.reserved[0], 32)

    def test_completion_requires_a_pending_issued_lease(self):
        with self.authority() as authority:
            with self.assertRaises(ValueError):
                authority.complete(self.main['sessions'][0]['lease'], self.first_result,
                                   expected_head=authority.state.head)

    def test_unissued_ah_grant_cannot_authorize_evaluator(self):
        with self.authority() as authority:
            with self.assertRaises(ValueError), patch.object(ai.ah, 'inspect_session') as inspect:
                authority.execute(self.main['sessions'][0]['grant'], expected_head=authority.state.head)
            inspect.assert_not_called()

    def test_completion_rejects_substituted_lease_serial(self):
        with self.authority() as authority:
            lease = self.reserve(authority); lease['serial'] += 1
            with self.assertRaises(ValueError):
                authority.complete(lease, self.first_result, expected_head=authority.state.head)
            self.assertEqual(authority.state.status, 'pending')

    def test_completion_rejects_another_source_result(self):
        with self.authority() as authority:
            lease = self.reserve(authority)
            with self.assertRaises(ValueError):
                authority.complete(lease, self.second_result, expected_head=authority.state.head)
            self.assertEqual(authority.state.status, 'pending')

    def test_completion_recomputes_verdict_and_semantic_receipt(self):
        with self.authority() as authority:
            lease = self.reserve(authority); forged = copy.deepcopy(self.first_result)
            forged['trials'][0]['verdict'] = False
            with self.assertRaises(ValueError):
                authority.complete(lease, forged, expected_head=authority.state.head)

    def test_completion_rejects_substituted_final_controller_prefix(self):
        with self.authority() as authority:
            lease = self.reserve(authority); forged = copy.deepcopy(self.first_result)
            forged['final_prefix_hash'] = 'd' * 64
            with self.assertRaises(ValueError):
                authority.complete(lease, forged, expected_head=authority.state.head)

    def test_duplicate_completion_is_rejected(self):
        with self.authority() as authority:
            lease, _ = self.complete_first(authority)
            with self.assertRaises(ValueError):
                authority.complete(lease, self.first_result, expected_head=authority.state.head)

    def test_failure_retains_pending_identity_and_all_charges(self):
        with self.authority() as authority:
            lease = self.reserve(authority); reserved = authority.state.reserved
            authority.fail(expected_head=authority.state.head, interrupted=True)
            self.assertEqual(authority.state.status, 'safety_halt')
            self.assertEqual(authority.state.pending, lease)
            self.assertEqual(authority.state.reserved, reserved)
            with self.assertRaises(ValueError):
                self.reserve(authority, 'af_after')

    def test_pending_authority_cannot_be_silently_stopped(self):
        with self.authority() as authority:
            self.reserve(authority); before = authority.raw
            with self.assertRaises(ValueError):
                authority.stop(expected_head=authority.state.head)
            self.assertEqual(authority.raw, before)

    def test_failed_evaluator_cannot_be_restarted_in_same_live_authority(self):
        with self.authority() as authority:
            lease = self.reserve(authority); head = authority.state.head
            with patch.object(ai.ah, 'inspect_session', side_effect=RuntimeError('interrupted')) as inspect:
                with self.assertRaises(RuntimeError):
                    authority.execute(lease, expected_head=head)
                with self.assertRaises(ValueError):
                    authority.execute(lease, expected_head=head)
                self.assertEqual(inspect.call_count, 1)
            self.assertEqual(authority.state.status, 'pending')
            self.assertEqual(authority.state.reserved, (32, 64, 256, 256))

    def test_reopened_pending_authority_cannot_execute_old_lease(self):
        with self.authority() as original:
            lease = self.reserve(original); reopened = self.reopen(original)
            try:
                with patch.object(ai.ah, 'inspect_session') as inspect, self.assertRaises(ValueError):
                    reopened.execute(lease, expected_head=reopened.state.head)
                inspect.assert_not_called()
                self.assertEqual(reopened.state.reserved, (32, 64, 256, 256))
            finally:
                reopened.close()

    def test_reopened_pending_authority_cannot_complete_old_lease(self):
        with self.authority() as original:
            lease = self.reserve(original); reopened = self.reopen(original)
            try:
                with self.assertRaises(ValueError):
                    reopened.complete(lease, self.first_result, expected_head=reopened.state.head)
                self.assertEqual(reopened.state.status, 'pending')
            finally:
                reopened.close()

    def test_successful_reopen_preserves_completed_controller_and_allows_next_source(self):
        with self.authority() as original:
            self.complete_first(original); prior = original.state.to_json(); reopened = self.reopen(original)
            try:
                self.assertEqual(reopened.state.to_json(), prior)
                second = self.reserve(reopened, 'af_after')
                self.assertEqual(second['serial'], 1)
                self.assertEqual(reopened.state.reserved, (64, 128, 512, 512))
            finally:
                reopened.close()

    def test_rollback_journal_cannot_match_independent_latest_head(self):
        case = self.main; old_events = case['events'][:1]
        with self.assertRaises(ValueError):
            self.replay(case, events=old_events, sessions=[])

    def test_replay_requires_all_completed_session_evidence(self):
        with self.assertRaises(ValueError):
            self.replay(sessions=[])

    def test_replay_rejects_extra_unissued_session_evidence(self):
        case = self.cases['interrupted_reservation']
        with self.assertRaises(ValueError):
            self.replay(case, sessions=[self.main['sessions'][0]])

    def test_public_replay_has_no_semantic_verification_bypass(self):
        with self.assertRaises(TypeError):
            ai.replay_authority(b'', self.prepared, self.identity, expected_policy=self.policy(),
                expected_policy_sha256='0' * 64, expected_head='0' * 64, verify_results=False)

    def test_replay_rejects_rehashed_forged_verdict_and_result_hash(self):
        case = copy.deepcopy(self.main)
        session = case['sessions'][-1]; session['result']['trials'][-1]['verdict'] = False
        completion = next(row['body'] for row in reversed(case['events']) if row['body']['kind'] == 'complete')
        completion['result_sha256'] = ai.digest(session['result'])
        changed = self.rechain(case['events'])
        with self.assertRaises(ValueError):
            self.replay(case, events=changed, head=changed[-1]['hash'])

    def test_replay_rejects_rehashed_false_budget_denial(self):
        case = copy.deepcopy(self.cases['aggregate_denial'])
        policy = case['authority_policy']; policy['total_attempts'] = 64
        policy['budget'] = ai._envelope(64).to_json()
        # A new policy anchor cannot validate a journal opened under the old one.
        with self.assertRaises(ValueError):
            ai.replay_authority(b''.join(ai.canonical(row)+b'\n' for row in case['events']),
                self.prepared, self.identity, expected_policy=policy,
                expected_policy_sha256=ai.digest(policy), expected_head=case['final_state']['head'],
                sessions=case['sessions'])

    def test_replay_rejects_rehashed_refund(self):
        case = copy.deepcopy(self.main)
        reservation = case['events'][1]['body']; reservation['reserved_after'] = [1, 2, 8, 8]
        changed = self.rechain(case['events'])
        with self.assertRaises(ValueError):
            self.replay(case, events=changed, head=changed[-1]['hash'])

    def test_replay_rejects_duplicate_event_index(self):
        case = copy.deepcopy(self.main); case['events'][-1]['index'] -= 1
        with self.assertRaises(ValueError):
            self.replay(case)

    def test_replay_rejects_truncation_and_noncanonical_newlines(self):
        case = self.main; raw = b''.join(ai.canonical(row)+b'\n' for row in case['events'])
        for changed in (raw[:-1], raw.replace(b'\n', b'\r\n')):
            with self.subTest(length=len(changed)), self.assertRaises(ValueError):
                ai.replay_authority(changed, self.prepared, self.identity,
                    expected_policy=case['authority_policy'], expected_policy_sha256=case['policy_sha256'],
                    expected_head=case['final_state']['head'], sessions=case['sessions'])

    def test_durable_reservation_exists_before_any_evaluator_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'authority.jsonl'; operation_path = Path(tmp) / 'operations.jsonl'
            with self.authority(path=path) as authority:
                lease = self.reserve(authority)
                original = ai.ah.inspect_session
                observed = []
                def inspect(*args, **kwargs):
                    rows = [ai.load_json_strict(line) for line in path.read_bytes().splitlines()]
                    observed.append(rows[-1]['body']['kind'])
                    self.assertEqual(rows[-1]['body']['lease']['lease_hash'], lease['lease_hash'])
                    self.assertEqual(rows[-1]['body']['reserved_after'], [32, 64, 256, 256])
                    return original(*args, **kwargs)
                with patch.object(ai.ah, 'inspect_session', side_effect=inspect):
                    authority.execute(lease, expected_head=authority.state.head, journal_path=operation_path)
                self.assertEqual(observed, ['reserve', 'reserve'])
                self.assertEqual(operation_path.read_bytes(), bytes.fromhex(self.first_result['resource']['journal_hex']))
                self.assertEqual(path.read_bytes(), authority.raw)

    def test_existing_disk_authority_cannot_be_recreated_without_external_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'authority.jsonl'
            with self.authority(path=path):
                pass
            with self.assertRaises(ValueError), self.authority(path=path):
                pass

    def test_disk_authority_enforces_single_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'authority.jsonl'
            with self.authority(path=path) as first:
                with self.assertRaises((OSError, ValueError)), self.authority(path=path):
                    pass
                self.assertEqual(first.state.status, 'open')

    def test_disk_journal_mutation_is_rejected_before_next_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'authority.jsonl'
            with self.authority(path=path) as authority:
                path.write_bytes(path.read_bytes()+b' ')
                with self.assertRaises(ValueError):
                    _ = authority.state

    def test_durable_write_failure_poison_keeps_evaluator_uncalled(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.authority(path=Path(tmp)/'authority.jsonl') as authority:
                with patch.object(ai.os, 'fsync', side_effect=OSError('simulated durable-write failure')):
                    with self.assertRaises(OSError):
                        self.reserve(authority)
                with patch.object(ai.ah, 'inspect_session') as inspect, self.assertRaises(ValueError):
                    authority.execute({}, expected_head='0'*64)
                inspect.assert_not_called()

    def test_closed_authority_cannot_issue_or_execute(self):
        with self.authority() as authority:
            head = authority.state.head; authority.close()
            with self.assertRaises(ValueError):
                authority.reserve('af_before', expected_head=head, expected_prefix_hash='0'*64)

    def test_journal_image_hash_substitution_is_rejected(self):
        value = {'journal_images': copy.deepcopy(self.derived['journal_images'])}
        value['journal_images'][next(iter(value['journal_images']))]['sha256'] = 'a'*64
        with self.assertRaises(ValueError):
            ai.authority_journal_images(value)

    def test_journal_image_path_traversal_is_rejected(self):
        item = next(iter(self.derived['journal_images'].values()))
        with self.assertRaises(ValueError):
            ai.authority_journal_images({'journal_images': {'../outside.jsonl': item}})

    def test_immutable_state_projection_cannot_change_actual_authority(self):
        with self.authority() as authority:
            original = authority.state.source_states
            authority.state.source_states['af_before']['prefix_hash'] = 'f'*64
            self.assertEqual(authority.state.source_states, original)


if __name__ == '__main__':
    unittest.main()
