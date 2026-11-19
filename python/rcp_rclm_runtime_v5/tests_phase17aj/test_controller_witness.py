"""AJ witness ownership, external anchors, native transport and crash refusal.

The public fixture key is a protocol test credential. These tests do not supply
external identity authentication, physical rollback protection or live authority.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import controller_witness as aj

ROOT = Path(__file__).resolve().parents[3]
KEY = aj.PUBLIC_FIXTURE_KEY
OWNER = '11' * 32
OTHER = '22' * 32


@lru_cache(maxsize=1)
def fixture():
    return aj.ai.PreparedControllerAuthority((ROOT / aj.AI_ROOT / 'packet.json').read_bytes())


class WitnessAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = fixture()
        cls.identity = aj.witness_identity(ROOT)
        cls.derived = aj._derive(cls.prepared, cls.identity)
        cls.cases = {case['name']: case for case in cls.derived['witness_cases']}

    def setUp(self):
        self.serial = 0

    def provision(self, name='shared_two_sources'):
        return aj.make_provision(self.prepared, case_name=name,
                                 witness_id='phase17aj.unit.' + name, key=KEY)

    def witness(self, *, path=None, name='shared_two_sources'):
        provision = self.provision(name)
        if path is not None:
            path.mkdir()
        result = aj.WitnessAuthority(path, self.prepared, provision, KEY,
                                    expected_provision_sha256=aj.digest(provision))
        self.addCleanup(result.close)
        return result

    def call(self, witness, op, *, nonce=None, cursor=None, source='af_before', owner=OWNER, **options):
        self.serial += 1
        nonce = nonce or aj._nonce('unit', str(self.serial))
        if op != 'read' and cursor is None:
            cursor = witness.cursor
        command = aj.request(witness.provision_sha256, KEY, op=op, nonce=nonce,
            cursor=cursor, source_id=source if op == 'reserve' else None,
            owner_commitment=aj.sha(bytes.fromhex(owner)) if op == 'reserve' else None,
            owner_token=owner if op == 'execute' else None, **options)
        response = witness.dispatch(command)
        return command, response, aj.verify_reply(response, command,
            expected_provision_sha256=witness.provision_sha256, key=KEY)

    def reserve(self, witness, **options):
        command, response, payload = self.call(witness, 'reserve', **options)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['outcome'], 'reserve')
        return payload['lease']

    def reopen(self, witness):
        raw, authority, head = witness.raw, witness._ai.raw, witness.state['witness_head']
        provision, directory = witness.provision, witness.directory
        witness.close()
        result = aj.WitnessAuthority(directory, self.prepared, provision, KEY,
            expected_provision_sha256=aj.digest(provision), expected_head=head,
            retained_ledger=raw if directory is None else None,
            retained_authority=authority if directory is None else None)
        self.addCleanup(result.close)
        result.reopen(aj._nonce('unit', 'boot-' + str(self.serial)))
        return result

    def test_exact_completed_ai_packet_and_source_execution(self):
        self.assertEqual(aj.BASE, 'e8d3c035f1ebbb6a725db2a49583185e10016490')
        self.assertEqual(aj.sha(self.prepared.packet_bytes), aj.AI_PACKET_SHA)
        execution = aj._execution((ROOT / aj.AI_ROOT / 'execution.json').read_bytes())
        self.assertEqual(len(execution['source_sha256']), 565)

    def test_implementation_and_retained_ai_code_are_bound(self):
        expected = set(aj.ai.CODE_PATHS) | {aj.CODE_PATH}
        self.assertEqual(set(self.identity['code_sha256']), expected)
        for name, checksum in self.identity['code_sha256'].items():
            self.assertEqual(aj.sha((ROOT / name).read_bytes()), checksum)

    def test_provision_pins_unchanged_policy_and_explicit_scope(self):
        provision = self.provision()
        old = self.prepared.packet['cases'][0]
        self.assertEqual(provision['authority_policy'], old['authority_policy'])
        self.assertEqual(provision['authority_policy_sha256'], old['policy_sha256'])
        self.assertTrue(provision['public_reference_fixture_key'])
        self.assertFalse(provision['external_issuer_authenticated'])
        self.assertFalse(provision['complete_resource_accounting'])

    def test_wrong_independent_provision_anchor_refused(self):
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, self.provision(), KEY,
                                expected_provision_sha256='00' * 32)

    def test_self_rehashed_objective_substitution_refused(self):
        provision = self.provision()
        provision['authority_policy']['objective'] = 'caller-chosen-objective'
        provision['authority_policy_sha256'] = aj.digest(provision['authority_policy'])
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, KEY,
                                expected_provision_sha256=aj.digest(provision))

    def test_self_rehashed_evaluator_substitution_refused(self):
        provision = self.provision()
        provision['authority_policy']['evaluator'] = 'caller-chosen-evaluator'
        provision['authority_policy_sha256'] = aj.digest(provision['authority_policy'])
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, KEY,
                                expected_provision_sha256=aj.digest(provision))

    def test_substituted_implementation_commitment_refused(self):
        provision = self.provision()
        provision['witness_identity']['implementation_sha256'] = '00' * 32
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, KEY,
                                expected_provision_sha256=aj.digest(provision))

    def test_wrong_key_is_not_authority(self):
        provision = self.provision()
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, b'x' * 32,
                                expected_provision_sha256=aj.digest(provision))

    def test_mutating_caller_provision_cannot_change_live_policy(self):
        provision = self.provision()
        witness = aj.WitnessAuthority(None, self.prepared, provision, KEY,
                                      expected_provision_sha256=aj.digest(provision))
        self.addCleanup(witness.close)
        provision['authority_policy']['objective'] = 'mutated-after-open'
        self.assertEqual(witness.provision['authority_policy']['objective'], aj.ai.OBJECTIVE)
        self.assertTrue(self.reserve(witness)['lease_hash'])

    def test_live_provision_accessor_returns_detached_snapshot(self):
        witness = self.witness()
        returned = witness.provision
        returned['authority_policy']['objective'] = 'substituted-through-accessor'
        returned['reference_case'] = 'aggregate_denial'
        self.assertEqual(witness.provision['authority_policy']['objective'], aj.ai.OBJECTIVE)
        self.assertEqual(witness.provision['reference_case'], 'shared_two_sources')
        self.assertTrue(self.reserve(witness)['lease_hash'])

    def test_read_does_not_advance_or_reveal_execution_token(self):
        witness = self.witness()
        self.reserve(witness)
        before = witness.raw
        _, reply, payload = self.call(witness, 'read')
        self.assertEqual(before, witness.raw)
        self.assertNotIn(OWNER, aj.canonical(reply).decode())
        self.assertNotIn('owner_token', payload['state'])

    def test_request_with_wrong_mac_fails_before_state_change(self):
        witness = self.witness(); before = witness.raw
        command = aj.request(witness.provision_sha256, KEY, op='read', nonce='33' * 32)
        command['mac'] = '00' * 32
        with self.assertRaises(ValueError):
            witness.dispatch(command)
        self.assertEqual(witness.raw, before)

    def test_request_for_another_witness_is_refused(self):
        witness = self.witness(); before = witness.raw
        command = aj.request('00' * 32, KEY, op='read', nonce='33' * 32)
        with self.assertRaises(ValueError):
            witness.dispatch(command)
        self.assertEqual(witness.raw, before)

    def test_old_signed_reply_cannot_answer_fresh_nonce(self):
        witness = self.witness()
        command, reply, _ = self.call(witness, 'read')
        newer = aj.request(witness.provision_sha256, KEY, op='read', nonce='44' * 32)
        with self.assertRaises(ValueError):
            aj.verify_reply(reply, newer, expected_provision_sha256=witness.provision_sha256, key=KEY)
        self.assertTrue(aj.verify_reply(reply, command,
            expected_provision_sha256=witness.provision_sha256, key=KEY)['ok'])

    def test_changed_signed_reply_payload_refused(self):
        witness = self.witness()
        command, reply, _ = self.call(witness, 'read')
        reply['payload']['state']['revision'] += 1
        with self.assertRaises(ValueError):
            aj.verify_reply(reply, command, expected_provision_sha256=witness.provision_sha256, key=KEY)

    def test_same_nonce_with_changed_command_cannot_use_old_reply(self):
        witness = self.witness()
        command, reply, _ = self.call(witness, 'read')
        different = aj.request(witness.provision_sha256, KEY, op='stop', nonce=command['body']['nonce'],
                               cursor=witness.cursor)
        with self.assertRaises(ValueError):
            aj.verify_reply(reply, different, expected_provision_sha256=witness.provision_sha256, key=KEY)

    def test_stale_controller_fork_cannot_reserve_twice(self):
        witness = self.witness(); old = witness.cursor
        self.reserve(witness)
        before = witness.raw
        _, _, payload = self.call(witness, 'reserve', cursor=old, owner=OTHER, source='af_after')
        self.assertFalse(payload['ok'])
        self.assertEqual(witness.raw, before)
        self.assertEqual(witness.state['authority_state']['serial'], 1)

    def test_exact_current_revision_and_both_heads_are_required(self):
        witness = self.witness()
        for field, value in [('revision', 1), ('witness_head', '00' * 32), ('authority_head', '00' * 32)]:
            with self.subTest(field=field):
                cursor = witness.cursor; cursor[field] = value; before = witness.raw
                _, _, payload = self.call(witness, 'reserve', cursor=cursor)
                self.assertFalse(payload['ok'])
                self.assertEqual(witness.raw, before)

    def test_boolean_revision_is_not_integer_revision(self):
        witness = self.witness(); cursor = witness.cursor; cursor['revision'] = False
        _, _, payload = self.call(witness, 'reserve', cursor=cursor)
        self.assertFalse(payload['ok'])

    def test_consumed_nonce_cannot_advance_again_with_current_cursor(self):
        witness = self.witness(); nonce = '55' * 32
        lease = self.reserve(witness, nonce=nonce)
        _, _, payload = self.call(witness, 'execute', nonce=nonce, lease_hash=lease['lease_hash'])
        self.assertFalse(payload['ok'])
        self.assertEqual(witness.state['authority_state']['status'], 'pending')

    def test_controller_cannot_invoke_administrative_reopen(self):
        witness = self.witness(); before = witness.raw
        _, _, payload = self.call(witness, 'reopen')
        self.assertFalse(payload['ok'])
        self.assertEqual(witness.raw, before)

    def test_caller_cannot_supply_next_state_or_completion_verdict(self):
        witness = self.witness(); before = witness.raw
        command = aj.request(witness.provision_sha256, KEY, op='read', nonce='66' * 32)
        command['body']['next_state'] = {'status': 'accepted'}
        core = {name: command[name] for name in ('schema', 'provision_sha256', 'body')}
        command['mac'] = aj._mac(KEY, aj.REQUEST_DOMAIN, core)
        with self.assertRaises(ValueError):
            witness.dispatch(command)
        with self.assertRaises(ValueError):
            witness.dispatch(aj.request(witness.provision_sha256, KEY,
                op='complete', nonce='77' * 32, cursor=witness.cursor))
        self.assertEqual(witness.raw, before)

    def test_unknown_source_cannot_receive_a_grant(self):
        witness = self.witness(); before = witness.raw
        _, _, payload = self.call(witness, 'reserve', source='invented-source')
        self.assertFalse(payload['ok'])
        self.assertEqual(witness.raw, before)

    def test_reservation_charges_before_execution(self):
        witness = self.witness(); self.reserve(witness)
        state = witness.state['authority_state']
        self.assertEqual(state['status'], 'pending')
        self.assertEqual(state['reserved_cost'], 3584)
        self.assertEqual(len(state['completed']), 0)

    def test_foreign_controller_cannot_execute_observed_lease(self):
        witness = self.witness(); lease = self.reserve(witness); before = witness.raw
        _, _, payload = self.call(witness, 'execute', owner=OTHER, lease_hash=lease['lease_hash'])
        self.assertFalse(payload['ok'])
        self.assertEqual(witness.raw, before)

    def test_wrong_lease_hash_cannot_execute(self):
        witness = self.witness(); self.reserve(witness); before = witness.raw
        _, _, payload = self.call(witness, 'execute', lease_hash='00' * 32)
        self.assertFalse(payload['ok'])
        self.assertEqual(witness.raw, before)

    def test_pending_reopen_retains_reservation_and_revokes_ownership(self):
        witness = self.witness(); lease = self.reserve(witness)
        old_authority = witness.state['authority_state']
        witness = self.reopen(witness)
        self.assertEqual(witness.state['authority_state'], old_authority)
        for operation, extra in [('execute', {'lease_hash': lease['lease_hash']}), ('reserve', {'source': 'af_after'}), ('stop', {})]:
            with self.subTest(operation=operation):
                before = witness.raw
                _, _, payload = self.call(witness, operation, **extra)
                self.assertFalse(payload['ok'])
                self.assertEqual(witness.raw, before)

    def test_different_boot_invalidates_an_old_controller_cursor(self):
        witness = self.witness(); old = witness.cursor
        witness = self.reopen(witness)
        self.assertEqual(witness.cursor['authority_head'], old['authority_head'])
        self.assertNotEqual(witness.cursor['witness_head'], old['witness_head'])
        _, _, payload = self.call(witness, 'reserve', cursor=old)
        self.assertFalse(payload['ok'])

    def test_pending_journal_requires_independent_current_head(self):
        witness = self.witness(); genesis = witness.state['witness_head']; self.reserve(witness)
        raw, authority, provision = witness.raw, witness._ai.raw, witness.provision
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, KEY,
                expected_provision_sha256=aj.digest(provision), expected_head=genesis,
                retained_ledger=raw, retained_authority=authority)
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, KEY,
                expected_provision_sha256=aj.digest(provision), retained_ledger=raw, retained_authority=authority)

    def test_rolled_back_two_journal_copy_refused_by_newer_external_anchor(self):
        with tempfile.TemporaryDirectory() as temp:
            witness = self.witness(path=Path(temp) / 'witness')
            old_witness, old_authority = witness.raw, witness._ai.raw
            self.reserve(witness)
            current, provision, directory = witness.state['witness_head'], witness.provision, witness.directory
            witness.close()
            (directory / 'witness.jsonl').write_bytes(old_witness)
            (directory / 'authority.jsonl').write_bytes(old_authority)
            with self.assertRaises(ValueError):
                aj.WitnessAuthority(directory, self.prepared, provision, KEY,
                    expected_provision_sha256=aj.digest(provision), expected_head=current)

    def test_failure_after_inner_reserve_preserves_split_and_refuses_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            witness = self.witness(path=Path(temp) / 'witness')
            before, head, provision, directory = witness.raw, witness.state['witness_head'], witness.provision, witness.directory
            with patch.object(witness, '_append', side_effect=OSError('controlled outer append failure')):
                with self.assertRaises(OSError):
                    self.call(witness, 'reserve')
            self.assertTrue(witness._poisoned)
            self.assertEqual(witness._ai.state.reserved, (32, 64, 256, 256))
            with self.assertRaises(ValueError):
                witness.dispatch(aj.request(witness.provision_sha256, KEY, op='read', nonce='88' * 32))
            witness.close()
            self.assertEqual((directory / 'witness.jsonl').read_bytes(), before)
            inner = (directory / 'authority.jsonl').read_bytes()
            self.assertGreater(len(inner.splitlines()), 1)
            with self.assertRaises(ValueError):
                aj.WitnessAuthority(directory, self.prepared, provision, KEY,
                    expected_provision_sha256=aj.digest(provision), expected_head=head)
            self.assertEqual((directory / 'authority.jsonl').read_bytes(), inner)

    def test_failure_after_inner_completion_cannot_be_repaired_from_old_head(self):
        witness = self.witness(); lease = self.reserve(witness)
        before, head, provision = witness.raw, witness.state['witness_head'], witness.provision
        with patch.object(witness, '_append', side_effect=OSError('controlled completion split')):
            with self.assertRaises(OSError):
                self.call(witness, 'execute', lease_hash=lease['lease_hash'])
        authority = witness._ai.raw
        self.assertTrue(witness._poisoned)
        self.assertEqual(len(witness._ai.sessions), 1)
        with self.assertRaises(ValueError):
            aj.WitnessAuthority(None, self.prepared, provision, KEY,
                expected_provision_sha256=aj.digest(provision), expected_head=head,
                retained_ledger=before, retained_authority=authority)

    def test_external_witness_journal_substitution_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            witness = self.witness(path=Path(temp) / 'witness')
            try:
                (witness.directory / 'witness.jsonl').write_bytes(witness.raw + b'\n')
                with self.assertRaises(ValueError):
                    _ = witness.state
            finally:
                witness.close()

    def test_duplicate_provisioning_never_overwrites_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'witness'; provision = self.provision()
            head = aj.provision_directory(directory, self.prepared, provision, KEY,
                expected_provision_sha256=aj.digest(provision))
            before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
            with self.assertRaises(ValueError):
                aj.provision_directory(directory, self.prepared, provision, KEY,
                    expected_provision_sha256=aj.digest(provision))
            self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()})
            self.assertEqual(len(head), 64)

    def test_rehashed_fabricated_witness_transition_is_rejected(self):
        case = self.cases['interrupted_reservation']; provision = case['provision']
        raw = bytes.fromhex(self.derived['journal_images']['interrupted_reservation-witness.jsonl']['hex'])
        rows = [aj.load_json_strict(line) for line in raw.splitlines()]
        rows[-1]['body']['authority_state_after']['reserved_cost'] = 0
        changed = []
        for index, row in enumerate(rows):
            changed.append(aj._event(row['body'], index, changed[-1]['hash'] if changed else aj.ai.ZERO))
        with self.assertRaises(ValueError):
            aj.replay_witness(b''.join(aj.canonical(row) + b'\n' for row in changed),
                self.prepared, provision, KEY, expected_provision_sha256=case['provision_sha256'],
                expected_head=changed[-1]['hash'])

    def test_selected_two_source_sequence_reuses_exact_ai_results(self):
        main = self.cases['shared_two_sources']
        self.assertEqual(main['sessions'], self.prepared.packet['cases'][0]['sessions'])
        self.assertEqual([s['result']['examined'] for s in main['sessions']], [1, 8])
        self.assertEqual(main['final_state']['authority_state']['reserved_cost'], 7168)
        self.assertEqual(main['final_state']['authority_state']['status'], 'external_stop')

    def test_selected_aggregate_denial_retains_prior_charge(self):
        denied = self.cases['aggregate_denial']
        self.assertEqual(denied['final_state']['authority_state']['status'], 'resource_denied')
        self.assertEqual(denied['final_state']['authority_state']['reserved_cost'], 3584)
        self.assertEqual([r['kind'] for r in denied['records']], ['reopen', 'reserve', 'execute', 'deny'])

    def test_record_inventory_separates_ai_heads_from_witness_heads(self):
        self.assertEqual([len(c['records']) for c in self.derived['witness_cases']], [7, 3, 4])
        for case in self.derived['witness_cases']:
            for row in case['records']:
                self.assertEqual(row['revision_after'], row['revision_before'] + 1)
                self.assertNotEqual(row['witness_head_after'], row['witness_head_before'])
                if row['kind'] == 'reopen':
                    self.assertEqual(row['authority_head_after'], row['authority_head_before'])
                else:
                    self.assertNotEqual(row['authority_head_after'], row['authority_head_before'])
        # Guard the decoded protocol even if a primitive violates the expected
        # head relation. Publication must poison the witness after an inner write.
        witness = self.witness(); before = witness._raw; event = aj._event
        with patch.object(aj, '_event', side_effect=lambda body, index, previous:
                          {**event(body, index, previous), 'hash': previous}):
            with self.assertRaises(ValueError):
                self.call(witness, 'reserve')
        self.assertTrue(witness._poisoned)
        self.assertEqual(witness._raw, before)
        self.assertEqual(witness._ai.state.reserved, (32, 64, 256, 256))
        witness = self.witness()
        fake_lease = self.prepared.packet['cases'][0]['sessions'][0]['lease']
        with patch.object(witness._ai, 'reserve', return_value=fake_lease):
            with self.assertRaises(ValueError):
                self.call(witness, 'reserve')
        self.assertTrue(witness._poisoned)

    def test_pure_reconstruction_does_not_launch_native_processes(self):
        case = self.cases['interrupted_reservation']
        raw = bytes.fromhex(self.derived['journal_images']['interrupted_reservation-witness.jsonl']['hex'])
        with patch.object(aj.subprocess, 'Popen', side_effect=AssertionError('no process during reconstruction')):
            witness = aj.replay_witness(raw, self.prepared, case['provision'], KEY,
                expected_provision_sha256=case['provision_sha256'],
                expected_head=case['final_state']['witness_head'])
            try:
                self.assertEqual(witness.state, case['final_state'])
            finally:
                witness.close()

    def test_every_retained_image_is_nonempty_flat_and_checksums_match(self):
        images = aj.witness_journal_images(self.derived)
        self.assertEqual(len(images), 12)
        for name, raw in images.items():
            self.assertTrue(raw.endswith(b'\n'))
            self.assertEqual(aj.sha(raw), self.derived['journal_images'][name]['sha256'])

    def test_image_path_escape_and_altered_bytes_refused(self):
        sample = copy.deepcopy(self.derived['journal_images'])
        name = next(iter(sample)); sample['../escape.jsonl'] = sample.pop(name)
        with self.assertRaises(ValueError):
            aj.witness_journal_images({'journal_images': sample})
        sample = copy.deepcopy(self.derived['journal_images'])
        sample[name]['hex'] += '0a'
        with self.assertRaises(ValueError):
            aj.witness_journal_images({'journal_images': sample})

    def test_scope_does_not_inflate_public_fixture_or_reference_tariff(self):
        summary = self.derived['summary']
        self.assertEqual(summary['reference_candidate_attempts'], 10)
        self.assertEqual(summary['metered_reference_operations'], 30)
        self.assertTrue(summary['public_reference_fixture_key'])
        for name in ('external_issuer_authenticated', 'witness_machine_rollback_resistance_established',
                     'complete_resource_accounting'):
            self.assertFalse(summary[name])
        self.assertEqual(summary['fresh_worker_sessions'], 0)
        self.assertEqual(summary['fresh_live_challenges'], 0)


class WitnessNativeTests(unittest.TestCase):
    """One actual process checks lost replies; the full gate runs five lifetimes."""
    @classmethod
    def setUpClass(cls):
        cls.prepared = fixture(); cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name); directory = cls.root / 'authority'
        provision = aj.make_provision(cls.prepared, case_name='shared_two_sources',
                                     witness_id='phase17aj.native-test', key=KEY)
        cls.pin = aj.digest(provision)
        head = aj.provision_directory(directory, cls.prepared, provision, KEY,
                                      expected_provision_sha256=cls.pin)
        cls.boot = {'name': 'native-lost-replies-0', 'case': 'shared_two_sources',
            'expected_head': head, 'boot_nonce': aj._nonce('native', 'boot'),
            'provision_sha256': cls.pin, 'request_sha256': [], 'response_sha256': []}
        cls.native = cls.root / 'native'; wire = []; sequence = 0
        transport = aj._NativeTransport(ROOT, directory, cls.native / cls.boot['name'],
            provision_sha256=cls.pin, expected_head=head, boot_nonce=cls.boot['boot_nonce'])

        def call(op, *, cursor=None, owner=None, lease=None):
            nonlocal sequence
            sequence += 1
            command = aj.request(cls.pin, KEY, op=op, nonce=aj._nonce('native', str(sequence)),
                cursor=cursor, source_id='af_before' if op == 'reserve' else None,
                owner_commitment=aj.sha(bytes.fromhex(owner)) if op == 'reserve' else None,
                owner_token=owner if op == 'execute' else None, lease_hash=lease)
            response = transport.call(command)
            wire.append({'boot': cls.boot['name'], 'request': command, 'response': response})
            cls.boot['request_sha256'].append(aj.sha(aj.canonical(command) + b'\n'))
            cls.boot['response_sha256'].append(aj.sha(aj.canonical(response) + b'\n'))
            return aj.verify_reply(response, command, expected_provision_sha256=cls.pin, key=KEY)

        def cursor(payload):
            return {name: payload['state'][name] for name in ('revision', 'witness_head', 'authority_head')}

        try:
            read = call('read'); initial = cursor(read)
            reserve_reply = call('reserve', cursor=initial, owner=OWNER)
            # The controller discards the acknowledgment but the witness has committed.
            cls.reserve_retry = call('reserve', cursor=initial, owner=OTHER)
            current = call('read'); pending = current['state']['authority_state']['pending']
            execution_cursor = cursor(current)
            cls.execution = call('execute', cursor=execution_cursor, owner=OWNER, lease=pending['lease_hash'])
            # The completed response is lost to the caller, which retries its old cursor.
            cls.execute_retry = call('execute', cursor=execution_cursor, owner=OWNER, lease=pending['lease_hash'])
            cls.final = call('read')
            if not reserve_reply['ok'] or not cls.execution['ok']:
                raise AssertionError('actual native fixture did not execute')
        finally:
            transport.close()
        raw = b''.join(aj.canonical(row) + b'\n' for row in wire)
        # This verifier fixture describes this one native invocation only. The full
        # PreparedControllerWitness packet and gate require all five selected boots.
        cls.packet = {'schema': aj.SCHEMA, 'base_commit': aj.BASE, 'witness_identity': aj.witness_identity(),
            'native_boots': [cls.boot], 'journal_images': {'native-test-rpc.jsonl': {'hex': raw.hex(), 'sha256': aj.sha(raw)}}}
        cls.hashes = aj.verify_witness_native_records(cls.native, cls.packet)

    def test_lost_native_reservation_reply_does_not_duplicate_charge(self):
        self.assertFalse(self.reserve_retry['ok'])
        self.assertEqual(self.reserve_retry['state']['authority_state']['serial'], 1)
        self.assertEqual(self.reserve_retry['state']['authority_state']['reserved_cost'], 3584)

    def test_lost_native_execution_reply_does_not_repeat_evaluation(self):
        self.assertFalse(self.execute_retry['ok'])
        state = self.final['state']['authority_state']
        self.assertEqual(len(state['completed']), 1)
        self.assertEqual(self.execution['session']['result']['examined'], 1)
        self.assertEqual(state['reserved_cost'], 3584)

    def test_original_native_inventory_has_five_files(self):
        self.assertEqual(len(self.hashes), 5)
        self.assertEqual(set(name.rsplit('/', 1)[1] for name in self.hashes),
                         {'start.json', 'native-result.json', 'stdin.bin', 'stdout.bin', 'stderr.bin'})

    def test_copied_original_native_evidence_verifies_without_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'copied-native'; shutil.copytree(self.native, destination)
            with patch.object(aj.subprocess, 'Popen', side_effect=AssertionError('read-only verification')):
                self.assertEqual(aj.verify_witness_native_records(destination, self.packet), self.hashes)

    def test_native_command_carries_no_bootstrap_key(self):
        start = aj.load_json_strict((self.native / self.boot['name'] / 'start.json').read_bytes())
        self.assertNotIn(KEY.hex(), '\0'.join(start['argv']))
        self.assertNotIn('fixture-key.bin', '\0'.join(start['argv']))
        self.assertEqual(start['expected_head'], self.boot['expected_head'])

    def test_native_unobserved_or_nonzero_exit_cannot_be_credited(self):
        for field, value in [('returncode', 1), ('returncode', False), ('timed_out', True),
                             ('native_wait_completed', False), ('reader_finished', False), ('reader_error', 'truncated')]:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
                path = destination / self.boot['name'] / 'native-result.json'
                result = aj.load_json_strict(path.read_bytes()); result[field] = value; path.write_bytes(aj.canonical(result))
                with self.assertRaises(ValueError):
                    aj.verify_witness_native_records(destination, self.packet)

    def test_native_stream_changes_remain_rejected_after_rehash(self):
        for name in ('stdin.bin', 'stdout.bin', 'stderr.bin'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
                here = destination / self.boot['name']; changed = (here / name).read_bytes() + b'\n'
                (here / name).write_bytes(changed)
                result = aj.load_json_strict((here / 'native-result.json').read_bytes())
                result['streams'][name] = {'bytes': len(changed), 'sha256': aj.sha(changed)}
                (here / 'native-result.json').write_bytes(aj.canonical(result))
                with self.assertRaises(ValueError):
                    aj.verify_witness_native_records(destination, self.packet)

    def test_native_source_anchor_changes_remain_rejected_after_rehash(self):
        for field, value in [('expected_head', '00' * 32), ('provision_sha256', '00' * 32),
                             ('boot_nonce', '00' * 32), ('ai_packet_sha256', '00' * 32)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
                here = destination / self.boot['name']
                start = aj.load_json_strict((here / 'start.json').read_bytes()); start[field] = value
                raw = aj.canonical(start); (here / 'start.json').write_bytes(raw)
                result = aj.load_json_strict((here / 'native-result.json').read_bytes()); result['start_sha256'] = aj.sha(raw)
                (here / 'native-result.json').write_bytes(aj.canonical(result))
                with self.assertRaises(ValueError):
                    aj.verify_witness_native_records(destination, self.packet)

    def test_missing_and_extra_native_files_are_rejected(self):
        for missing in (True, False):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
                if missing:
                    (destination / self.boot['name'] / 'stderr.bin').unlink()
                else:
                    (destination / 'unexplained.txt').write_bytes(b'extra')
                with self.assertRaises(ValueError):
                    aj.verify_witness_native_records(destination, self.packet)

    def test_extra_native_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
            (destination / 'unexpected-empty-directory').mkdir()
            with self.assertRaises(ValueError):
                aj.verify_witness_native_records(destination, self.packet)

    def test_unrecognized_native_metadata_is_rejected(self):
        for name in ('start.json', 'native-result.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
                here = destination / self.boot['name']; path = here / name
                value = aj.load_json_strict(path.read_bytes()); value['unaccounted'] = True
                raw = aj.canonical(value); path.write_bytes(raw)
                if name == 'start.json':
                    result = aj.load_json_strict((here / 'native-result.json').read_bytes())
                    result['start_sha256'] = aj.sha(raw)
                    (here / 'native-result.json').write_bytes(aj.canonical(result))
                with self.assertRaises(ValueError):
                    aj.verify_witness_native_records(destination, self.packet)

    def test_boolean_native_stream_size_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'native'; shutil.copytree(self.native, destination)
            here = destination / self.boot['name']
            result = aj.load_json_strict((here / 'native-result.json').read_bytes())
            result['streams']['stderr.bin']['bytes'] = False
            (here / 'native-result.json').write_bytes(aj.canonical(result))
            with self.assertRaises(ValueError):
                aj.verify_witness_native_records(destination, self.packet)

    def test_response_timeout_is_recorded_as_timeout(self):
        import queue
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'authority'; native = Path(temp) / 'native'
            provision = aj.make_provision(self.prepared, case_name='interrupted_reservation',
                witness_id='phase17aj.timeout-test', key=KEY)
            pin = aj.digest(provision)
            head = aj.provision_directory(directory, self.prepared, provision, KEY,
                expected_provision_sha256=pin)
            transport = aj._NativeTransport(ROOT, directory, native,
                provision_sha256=pin, expected_head=head, boot_nonce=aj._nonce('timeout', 'boot'))
            try:
                with patch.object(transport._queue, 'get', side_effect=queue.Empty):
                    with self.assertRaises(ValueError):
                        transport.call(aj.request(pin, KEY, op='read', nonce=aj._nonce('timeout', 'read')))
            finally:
                with self.assertRaises(ValueError):
                    transport.close()
            result = aj.load_json_strict((native / 'native-result.json').read_bytes())
            self.assertTrue(result['timed_out'])
            self.assertTrue(result['native_wait_completed'])
            self.assertNotEqual(result['returncode'], 0)


if __name__ == '__main__':
    unittest.main()
