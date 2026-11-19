"""AK native root durability, fencing, transactional publication and boundaries.

These are concrete reference-runtime checks, not physical durability proofs.
The cloned-root counterexample deliberately preserves the documented premise.
"""
from __future__ import annotations

import copy
from functools import lru_cache
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import controller_durable_authority as ak

aj = ak.aj
ROOT = Path(__file__).resolve().parents[3]
KEY = aj.PUBLIC_FIXTURE_KEY
OWNER = '41' * 32
OTHER = '42' * 32


@lru_cache(maxsize=1)
def fixture():
    return aj.ai.PreparedControllerAuthority((ROOT / aj.AI_ROOT / 'packet.json').read_bytes())


def native_environment():
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join(str(ROOT / 'python' / ('rcp_rclm_runtime_v' + str(v)))
                                              for v in (2, 3, 4, 5))
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['PYTHONUTF8'] = '1'
    return environment


class DurableAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = fixture()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.serial = 0; self.lifetimes = 0
        self.root = self.directory / 'authority'
        self.provision = aj.make_provision(self.prepared, case_name='shared_two_sources',
            witness_id='phase17ak.test', key=KEY)
        self.witness_pin = aj.digest(self.provision)
        self.bootstrap = ak.provision_root(self.root, self.prepared, self.provision, KEY,
            expected_provision_sha256=self.witness_pin, authority_id='phase17ak.test.root',
            provisioning_nonce='01' * 32)
        self.pin = self.bootstrap['root_provision_sha256']

    def open(self, *, root=None, pin=None, key=KEY, boot_nonce=None):
        self.lifetimes += 1
        service = ak.DurableAuthority(self.root if root is None else root, self.prepared, key,
            expected_root_provision_sha256=self.pin if pin is None else pin,
            execution_directory=self.directory / ('stage-' + str(self.lifetimes)),
            boot_nonce=boot_nonce or aj._nonce('phase17ak.test.boot', str(self.lifetimes)))
        self.addCleanup(service.close)
        return service

    def request(self, service, op, *, nonce=None, cursor=None, owner=OWNER,
                source='af_before', lease_hash=None):
        self.serial += 1
        nonce = nonce or aj._nonce('phase17ak.test.request', str(self.serial))
        root_cursor = service.cursor if cursor is None else cursor
        inner = aj.request(self.witness_pin, KEY, op=op, nonce=nonce,
            cursor=None if op == 'read' else root_cursor['witness_cursor'],
            source_id=source if op == 'reserve' else None,
            owner_commitment=aj.sha(bytes.fromhex(owner)) if op == 'reserve' else None,
            owner_token=owner if op == 'execute' else None,
            lease_hash=lease_hash)
        return ak.make_request(self.pin, KEY, inner,
            expected_cursor=None if op == 'read' else root_cursor)

    def call(self, service, op, **options):
        command = self.request(service, op, **options)
        response = service.dispatch(command)
        checked = ak.verify_reply(response, command, key=KEY, expected_root_provision_sha256=self.pin)
        return command, response, checked

    def reserve(self, service, **options):
        _, _, checked = self.call(service, 'reserve', **options)
        self.assertTrue(checked['commit_applied'])
        self.assertEqual(checked['witness']['outcome'], 'reserve')
        return checked['witness']['lease']

    def execute(self, service, lease, **options):
        return self.call(service, 'execute', lease_hash=lease['lease_hash'], **options)

    def evidence(self, service):
        evidence = service.export_evidence()
        checked = ak.verify_evidence(evidence, self.prepared, KEY, expected_root_provision_sha256=self.pin)
        self.assertFalse(checked['native_execution_repeated'])
        self.assertFalse(checked['physical_currentness_established'])
        return evidence

    def test_provision_binds_source_backend_policy_key_and_exact_aj(self):
        service = self.open()
        self.assertEqual(aj.digest(service.provision), self.pin)
        self.assertEqual(service.provision['witness_provision'], self.provision)
        self.assertEqual(service.provision['backend_policy'], ak.BACKEND_POLICY)
        self.assertEqual(service.provision['durable_identity']['implementation_sha256'],
                         ak.durable_identity()['implementation_sha256'])
        self.assertTrue(service.provision['public_reference_fixture_key'])
        self.assertNotIn(KEY.hex(), ak.canonical(service.provision).decode())
        self.assertFalse(service.provision['external_issuer_authenticated'])

    def test_private_key_provisioning_does_not_export_secret_or_claim_trust(self):
        key = b'private-test-key-material-32byte'
        self.assertEqual(len(key), 32)
        provision = aj.make_provision(self.prepared, case_name='shared_two_sources', witness_id='private', key=key)
        value = ak.make_root_provision(self.prepared, provision, key,
            expected_provision_sha256=aj.digest(provision), authority_id='private-root', provisioning_nonce='02'*32)
        self.assertFalse(value['public_reference_fixture_key'])
        self.assertFalse(value['external_issuer_authenticated'])
        self.assertNotIn(key.hex(), ak.canonical(value).decode())

    def test_open_never_creates_a_missing_root(self):
        absent = self.directory / 'missing'
        with self.assertRaises(ValueError):
            self.open(root=absent)
        self.assertFalse(absent.exists())

    def test_provision_cannot_reset_existing_root(self):
        before = (self.root / 'authority.sqlite3').read_bytes()
        with self.assertRaises(ValueError):
            ak.provision_root(self.root, self.prepared, self.provision, KEY,
                expected_provision_sha256=self.witness_pin, authority_id='reset', provisioning_nonce='03'*32)
        self.assertEqual((self.root / 'authority.sqlite3').read_bytes(), before)

    def test_genesis_and_every_event_bind_the_independent_root_identity(self):
        service = self.open(); evidence = service.export_evidence()
        self.assertTrue(all(entry['event']['root_provision_sha256'] == self.pin for entry in evidence['events']))
        other = ak.provision_root(self.directory/'other-authority', self.prepared, self.provision, KEY,
            expected_provision_sha256=self.witness_pin, authority_id='distinct-root', provisioning_nonce='01'*32)
        self.assertNotEqual(other['root_provision_sha256'], self.pin)
        self.assertNotEqual(other['cursor']['root_head'], self.bootstrap['cursor']['root_head'])
        tampered = copy.deepcopy(evidence)
        tampered['events'][0]['event']['root_provision_sha256'] = other['root_provision_sha256']
        core = {name: value for name, value in tampered['events'][0]['event'].items() if name != 'hash'}
        tampered['events'][0]['event']['hash'] = ak.sha(ak.EVENT_DOMAIN + ak.canonical(core))
        with self.assertRaises(ValueError):
            ak.verify_evidence(tampered, self.prepared, KEY, expected_root_provision_sha256=self.pin)

    def test_wrong_independent_root_pin_and_key_refused_before_staging(self):
        with self.assertRaises(ValueError):
            self.open(pin='00'*32)
        with self.assertRaises(ValueError):
            self.open(key=b'x'*32)
        self.assertFalse((self.directory/'stage-1').exists())
        self.assertFalse((self.directory/'stage-2').exists())

    def test_existing_execution_directory_cannot_select_restart_history(self):
        stage = self.directory/'old-stage'; stage.mkdir()
        with self.assertRaises(ValueError):
            ak.DurableAuthority(self.root, self.prepared, KEY,
                expected_root_provision_sha256=self.pin, execution_directory=stage, boot_nonce='04'*32)

    def test_root_and_execution_directory_must_be_separate(self):
        with self.assertRaises(ValueError):
            ak.DurableAuthority(self.root, self.prepared, KEY,
                expected_root_provision_sha256=self.pin, execution_directory=self.root/'stage', boot_nonce='04'*32)

    def test_nonblocking_lifetime_lock_excludes_competing_service(self):
        service = self.open(); before = service.cursor
        with self.assertRaises((OSError, ValueError)):
            self.open()
        self.assertEqual(service.cursor, before)
        self.assertFalse((self.directory/'stage-2').exists())

    def test_subprocess_cannot_acquire_active_root(self):
        service = self.open(); before = service.cursor
        code = '''
from pathlib import Path
import sys
from rcp_rclm_runtime_v5.phase17 import controller_durable_authority as ak
try:
 ak._LifetimeLock(Path(sys.argv[1])/'authority.lock')
except (OSError,ValueError):
 raise SystemExit(23)
raise SystemExit(99)
'''
        completed = subprocess.run([sys.executable, '-B', '-c', code, str(self.root), self.pin,
            str(self.directory/'competing-process')], capture_output=True, text=True, timeout=120,
            env=native_environment())
        self.assertEqual(completed.returncode, 23, completed.stderr)
        self.assertEqual(service.cursor, before)
        self.assertFalse((self.directory/'competing-process').exists())

    def test_open_commits_reopen_and_monotone_epoch(self):
        service = self.open(); first = service.cursor
        self.assertEqual((first['epoch'], first['serial']), (1, 1))
        service.close()
        reopened = self.open(); second = reopened.cursor
        self.assertEqual((second['epoch'], second['serial']), (2, 2))
        self.assertNotEqual(first['root_head'], second['root_head'])
        self.assertEqual(self.evidence(reopened)['events'][-1]['event']['kind'], 'reopen')

    def test_read_does_not_advance_or_supply_execution_ownership(self):
        service = self.open(); before = service.cursor
        command, reply, checked = self.call(service, 'read')
        self.assertEqual(service.cursor, before)
        self.assertFalse(checked['commit_applied'])
        self.assertEqual(checked['witness']['outcome'], 'read')
        self.assertNotIn(OWNER, ak.canonical(reply).decode())
        self.assertEqual(reply['request_sha256'], aj.digest(command))

    def test_reserve_acknowledgement_binds_exact_committed_images(self):
        service = self.open(); before = service.cursor
        command, response, checked = self.call(service, 'reserve')
        evidence = self.evidence(service)
        event = evidence['events'][-1]['event']
        self.assertTrue(checked['commit_applied'])
        self.assertEqual(event['before'], before)
        self.assertEqual(event['request_sha256'], aj.digest(command['witness_request']))
        self.assertEqual(response['cursor']['root_head'], event['hash'])
        self.assertEqual(service.cursor, evidence['final_cursor'])
        self.assertEqual(checked['witness']['state']['authority_state']['reserved_cost'], 3584)

    def test_exact_execute_calls_native_reference_evaluator_not_selected_result(self):
        service = self.open(); lease = self.reserve(service)
        original = aj.ai.ah.inspect_session
        calls = []
        def observed(*args, **kwargs):
            if kwargs.get('journal_path') is not None:
                calls.append(kwargs['journal_path'])
            return original(*args, **kwargs)
        with patch.object(aj.WitnessAuthority, '_reference_result', side_effect=AssertionError('path-free result used')):
            with patch.object(aj.ai.ah, 'inspect_session', side_effect=observed):
                _, _, checked = self.execute(service, lease)
        self.assertTrue(checked['commit_applied'])
        self.assertEqual(checked['witness']['outcome'], 'execute')
        self.assertEqual(len(calls), 1)
        self.assertTrue(Path(calls[0]).is_file())
        self.assertEqual(self.evidence(service)['events'][-1]['event']['kind'], 'execute')

    def test_competing_old_root_cursor_and_exact_replay_refused(self):
        service = self.open()
        command = self.request(service, 'reserve')
        service.dispatch(command); current = service.cursor
        with self.assertRaises(ValueError):
            service.dispatch(command)
        self.assertEqual(service.cursor, current)

    def test_same_nonce_at_new_cursor_is_refused_without_publication(self):
        service = self.open()
        nonce = '06'*32
        self.reserve(service, nonce=nonce)
        before = service.cursor
        _, _, checked = self.call(service, 'reserve', nonce=nonce, source='af_after')
        self.assertFalse(checked['witness']['ok'])
        self.assertFalse(checked['commit_applied'])
        self.assertEqual(service.cursor, before)

    def test_old_epoch_request_cannot_advance_reopened_root(self):
        service = self.open(); old = self.request(service, 'reserve')
        service.close(); reopened = self.open(); before = reopened.cursor
        with self.assertRaises(ValueError):
            reopened.dispatch(old)
        self.assertEqual(reopened.cursor, before)

    def test_controller_cannot_request_root_reopen(self):
        service = self.open(); before = service.cursor
        with self.assertRaises(ValueError):
            service.dispatch(self.request(service, 'reopen'))
        self.assertEqual(service.cursor, before)

    def test_root_and_witness_authentication_are_both_required(self):
        service = self.open(); before = service.cursor
        command = self.request(service, 'read'); command['mac'] = '00'*32
        with self.assertRaises(ValueError):
            service.dispatch(command)
        command = self.request(service, 'read'); command['witness_request']['mac'] = '00'*32
        command = ak.make_request(self.pin, KEY, command['witness_request'])
        with self.assertRaises(ValueError):
            service.dispatch(command)
        self.assertEqual(service.cursor, before)

    def test_reply_replay_cursor_tampering_and_false_commit_flag_rejected(self):
        service = self.open()
        command, reply, _ = self.call(service, 'read')
        newer = self.request(service, 'read')
        with self.assertRaises(ValueError):
            ak.verify_reply(reply, newer, key=KEY, expected_root_provision_sha256=self.pin)
        for field, value in (('commit_applied', True), ('cursor', self.bootstrap['cursor'])):
            forged = copy.deepcopy(reply); forged[field] = value
            core = {name: data for name, data in forged.items() if name != 'mac'}
            forged['mac'] = ak._mac(KEY, ak.RESPONSE_DOMAIN, core)
            with self.assertRaises(ValueError):
                ak.verify_reply(forged, command, key=KEY, expected_root_provision_sha256=self.pin)

    def test_pending_restart_retains_full_charge_and_revokes_execution_owner(self):
        service = self.open(); lease = self.reserve(service)
        state = service._witness.state['authority_state']; service.close()
        reopened = self.open(); before = reopened.cursor
        _, _, checked = self.execute(reopened, lease)
        self.assertFalse(checked['witness']['ok'])
        after = checked['witness']['state']['authority_state']
        self.assertEqual(after['reserved'], state['reserved'])
        self.assertEqual(after['pending'], state['pending'])
        self.assertEqual(reopened.cursor, before)
        _, _, denied = self.call(reopened, 'reserve', source='af_after')
        self.assertFalse(denied['witness']['ok'])

    def test_completed_restart_retains_consumption_without_rerunning_evaluator(self):
        service = self.open(); lease = self.reserve(service); self.execute(service, lease)
        state = service._witness.state['authority_state']; service.close()
        original = aj.ai.ah.inspect_session
        def pure_only(*args, **kwargs):
            self.assertIsNone(kwargs.get('journal_path'), 'native evaluator rerun')
            return original(*args, **kwargs)
        with patch.object(aj.ai.ah, 'inspect_session', side_effect=pure_only):
            reopened = self.open()
        self.assertEqual(reopened._witness.state['authority_state'], state)
        self.assertEqual(reopened.cursor['epoch'], 2)
        self.assertFalse(self.call(reopened, 'reserve')[2]['witness']['ok'])

    def test_transaction_failure_before_commit_never_returns_ack(self):
        service = self.open(); before = service.cursor
        def crash(stage):
            if stage == 'after_insert':
                raise RuntimeError('controlled precommit failure')
        with patch.object(ak, '_fault', side_effect=crash):
            with self.assertRaisesRegex(RuntimeError, 'precommit'):
                self.call(service, 'reserve')
        with self.assertRaises(ValueError):
            service.export_evidence()
        stage = service.execution_directory; service.close()
        self.assertTrue((stage/'witness.jsonl').exists())
        reopened = self.open()
        events = self.evidence(reopened)['events']
        self.assertEqual([e['event']['kind'] for e in events], ['provision', 'reopen', 'reopen'])
        self.assertEqual(events[-1]['event']['before'], before)

    def test_commit_before_lost_ack_persists_charge_and_cannot_retry(self):
        service = self.open(); before = service.cursor
        def lost_ack(stage):
            if stage == 'after_commit':
                raise RuntimeError('controlled lost acknowledgement')
        with patch.object(ak, '_fault', side_effect=lost_ack):
            with self.assertRaisesRegex(RuntimeError, 'acknowledgement'):
                self.call(service, 'reserve')
        service.close(); reopened = self.open()
        evidence = self.evidence(reopened)
        self.assertEqual([e['event']['kind'] for e in evidence['events']], ['provision','reopen','reserve','reopen'])
        self.assertEqual(evidence['events'][-2]['event']['before'], before)
        self.assertEqual(reopened._witness.state['authority_state']['reserved_cost'], 3584)
        self.assertFalse(self.call(reopened, 'reserve', source='af_after')[2]['witness']['ok'])

    def test_executed_but_uncommitted_completion_is_never_rerun_after_restart(self):
        service = self.open(); lease = self.reserve(service)
        def fail_commit(stage):
            if stage == 'after_insert':
                raise RuntimeError('controlled completion persistence failure')
        with patch.object(ak, '_fault', side_effect=fail_commit):
            with self.assertRaisesRegex(RuntimeError, 'completion'):
                self.execute(service, lease)
        stage = service.execution_directory; service.close()
        self.assertTrue((stage/'work-0.jsonl').is_file())
        original = aj.ai.ah.inspect_session
        def pure_only(*args, **kwargs):
            self.assertIsNone(kwargs.get('journal_path'), 'interrupted native work rerun')
            return original(*args, **kwargs)
        with patch.object(aj.ai.ah, 'inspect_session', side_effect=pure_only):
            reopened = self.open()
            self.assertFalse(self.execute(reopened, lease)[2]['witness']['ok'])
        self.assertEqual(reopened._witness.state['authority_state']['reserved_cost'], 3584)
        self.assertIsNotNone(reopened._witness.state['authority_state']['pending'])

    def test_saved_evidence_reconstruction_launches_no_process_or_evaluator(self):
        service = self.open(); lease = self.reserve(service); self.execute(service, lease)
        evidence = service.export_evidence()
        original = aj.ai.ah.inspect_session
        def pure_only(*args, **kwargs):
            self.assertIsNone(kwargs.get('journal_path'), 'native work rerun')
            return original(*args, **kwargs)
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('process started')):
            with patch.object(aj.ai.ah, 'inspect_session', side_effect=pure_only):
                result = ak.verify_evidence(evidence, self.prepared, KEY, expected_root_provision_sha256=self.pin)
        self.assertFalse(result['native_execution_repeated'])

    def test_semantic_evidence_tamper_and_paired_image_substitution_rejected(self):
        service = self.open(); self.reserve(service); evidence = service.export_evidence()
        mutations = []
        wrong_epoch = copy.deepcopy(evidence); wrong_epoch['events'][-1]['event']['epoch'] += 1; mutations.append(wrong_epoch)
        wrong_pair = copy.deepcopy(evidence); wrong_pair['events'][-1]['authority_journal'] = evidence['events'][0]['authority_journal']; mutations.append(wrong_pair)
        wrong_serial = copy.deepcopy(evidence); wrong_serial['events'][-1]['event']['serial'] = 0; mutations.append(wrong_serial)
        wrong_final = copy.deepcopy(evidence); wrong_final['final_cursor'] = self.bootstrap['cursor']; mutations.append(wrong_final)
        for index, value in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                ak.verify_evidence(value, self.prepared, KEY, expected_root_provision_sha256=self.pin)

    def test_external_database_epoch_mutation_fences_open_handle(self):
        service = self.open(); db = sqlite3.connect(self.root/'authority.sqlite3')
        try:
            db.execute('DELETE FROM snapshots WHERE serial=1'); db.commit()
        finally:
            db.close()
        with self.assertRaises(ValueError):
            service.dispatch(self.request_from_saved_cursor(service, 'read'))

    def test_wrong_sql_snapshot_slot_refused_before_staging_or_mutation(self):
        connection = sqlite3.connect(self.root/'authority.sqlite3')
        try:
            connection.execute('UPDATE snapshots SET serial=100 WHERE serial=0')
            connection.commit()
            before = connection.execute('SELECT serial,event,witness,authority FROM snapshots').fetchall()
        finally:
            connection.close()
        with self.assertRaisesRegex(ValueError, 'SQL snapshot slot'):
            self.open()
        self.assertFalse((self.directory/'stage-1').exists())
        connection = sqlite3.connect(self.root/'authority.sqlite3')
        try:
            self.assertEqual(connection.execute('SELECT serial,event,witness,authority FROM snapshots').fetchall(), before)
        finally:
            connection.close()

    def request_from_saved_cursor(self, service, op):
        inner = aj.request(self.witness_pin, KEY, op=op, nonce='07'*32)
        return ak.make_request(self.pin, KEY, inner)

    def test_root_lock_replacement_refused(self):
        service = self.open(); before = service.cursor
        lock = self.root/'authority.lock'
        try:
            lock.rename(self.root/'old-authority.lock')
        except OSError:
            self.assertTrue(lock.is_file())
            self.assertEqual(service.cursor, before)
            return  # The host itself prevented replacement of the held lock.
        lock.write_bytes(b'L')
        with self.assertRaises(ValueError):
            _ = service.cursor

    def test_database_replacement_refused(self):
        service = self.open(); before = service.cursor
        path = self.root/'authority.sqlite3'
        image = path.read_bytes()
        try:
            path.rename(self.root/'replaced-authority.sqlite3')
        except OSError:
            self.assertTrue(path.is_file())
            self.assertEqual(service.cursor, before)
            return  # Windows may deny replacement before the runtime must.
        path.write_bytes(image)
        with self.assertRaises(ValueError):
            _ = service.cursor

    def test_whole_root_cloning_remains_an_explicit_counterexample(self):
        clone = self.directory/'cloned-root'; shutil.copytree(self.root, clone)
        first = self.open(); second = self.open(root=clone)
        first_lease = self.reserve(first); second_lease = self.reserve(second)
        self.assertEqual(first_lease['source_permit']['source_id'], second_lease['source_permit']['source_id'])
        self.assertFalse(ak.SCOPE['global_clone_exclusion_established'])
        self.assertFalse(ak.SCOPE['joint_root_rollback_resistance_established'])

    def _native_crash(self, boundary):
        code = '''
import os,sys
from rcp_rclm_runtime_v5.phase17 import controller_durable_authority as ak
aj=ak.aj
p=aj.ai.PreparedControllerAuthority((ak.SOURCE_ROOT/aj.AI_ROOT/'packet.json').read_bytes())
service=ak.DurableAuthority(sys.argv[1],p,aj.PUBLIC_FIXTURE_KEY,expected_root_provision_sha256=sys.argv[2],execution_directory=sys.argv[3],boot_nonce='81'*32)
inner=aj.request(service.provision['witness_provision_sha256'],aj.PUBLIC_FIXTURE_KEY,op='reserve',nonce='82'*32,cursor=service.cursor['witness_cursor'],source_id='af_before',owner_commitment=aj.sha(bytes.fromhex('83'*32)))
request=ak.make_request(sys.argv[2],aj.PUBLIC_FIXTURE_KEY,inner,expected_cursor=service.cursor)
def crash(stage):
 if stage==sys.argv[4]: os._exit(73)
ak._fault=crash
service.dispatch(request)
raise SystemExit(99)
'''
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.root), self.pin,
            str(self.directory/'native-crash-stage'), boundary], capture_output=True, text=True, timeout=600,
            env=native_environment())
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')
        self.assertTrue((self.directory/'native-crash-stage'/'witness.jsonl').is_file())

    def test_native_process_crash_before_commit_recovers_prior_root(self):
        self._native_crash('after_insert')
        reopened = self.open()
        self.assertEqual([entry['event']['kind'] for entry in self.evidence(reopened)['events']],
                         ['provision', 'reopen', 'reopen'])
        self.assertEqual(reopened._witness.state['authority_state']['reserved_cost'], 0)

    def test_native_process_crash_after_commit_keeps_reservation(self):
        self._native_crash('after_commit')
        reopened = self.open()
        self.assertEqual([entry['event']['kind'] for entry in self.evidence(reopened)['events']],
                         ['provision', 'reopen', 'reserve', 'reopen'])
        self.assertEqual(reopened._witness.state['authority_state']['reserved_cost'], 3584)
        self.assertFalse(self.call(reopened, 'reserve', source='af_after')[2]['witness']['ok'])


if __name__ == '__main__':
    unittest.main()
