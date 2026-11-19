"""Actual TLS adapter tests with an explicitly synthetic state-machine backend.

No test below is credited as an AL live worker, protected production deployment,
or Lean acceptance. The selected application separately captures real workers.
"""
from __future__ import annotations

import copy
from pathlib import Path
import socket
import ssl
import struct
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError
from rcp_rclm_runtime_v5.phase17 import authority_transport as t
from rcp_rclm_runtime_v5.phase17 import durable_campaign as al
from rcp_rclm_runtime_v5.phase17.authority_transport_pki import generate_reference_pki
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, ResourceExhausted, canonical, sha, require


class SyntheticAuthority:
    """Small adapter fixture. It starts no campaign worker or Lean process."""
    def __init__(self):
        self.root_provision_sha256 = sha(b'AM synthetic test root')
        self.entries = []
        self.state = SimpleNamespace(status='open', reserved=[0, 0, 0, 0], completed=[])
        self.calls = 0
        self.nonces = set()
        self.commit('provision')
        self.commit('reopen', boot=sha(b'first test boot'))

    @property
    def cursor(self):
        return t.event_cursor(self.entries[-1]['event'])

    def commit(self, kind, request=None, boot=None):
        previous = None if not self.entries else self.cursor
        epoch = 0 if previous is None else previous['epoch'] + (kind == 'reopen')
        snapshot = {'journal_hex': b'{}\n'.hex(), 'pending': None, 'nonces': [], 'sessions': []}
        event = al._event(self.root_provision_sha256, snapshot, previous=previous,
            kind=kind, epoch=epoch, boot_nonce=boot, request=request,
            session={'synthetic': True} if kind == 'complete' else None)
        self.entries.append({'event': event, 'snapshot': snapshot})

    def export_evidence(self):
        return {'entries': copy.deepcopy(self.entries)}

    def run_session(self, *, expected_cursor, request_nonce, credits):
        require(expected_cursor == self.cursor and request_nonce not in self.nonces,
                'stale cursor or replayed nonce')
        request = {'expected_cursor': expected_cursor, 'request_nonce': request_nonce, 'credits': credits}
        self.nonces.add(request_nonce)
        if credits == 13:
            self.commit('deny', request)
            self.state.status = 'resource_exhausted'
            raise ResourceExhausted('synthetic aggregate denial')
        self.commit('reserve', request); self.commit('launch')
        self.calls += 1
        self.commit('complete')
        self.state.completed.append(request_nonce)
        return {'synthetic-session.json': canonical({'synthetic': True, 'nonce': request_nonce})}


class AuthorityTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory(prefix='phase17am-test-identities-')
        cls.pki = generate_reference_pki(Path(cls.shared.name) / 'private')

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='phase17am-test-')
        self.base = Path(self.tmp.name)
        self.authority = SyntheticAuthority()
        p = self.pki['public']
        self.commission = t.make_commission(t.SOURCE_ROOT, self.authority.root_provision_sha256,
                                           p['ca'], p['server'], p['client'])
        self.pin = t.commission_digest(self.commission)
        self.anchor = self.base / 'anchor.json'
        t.create_anchor(self.anchor, self.commission, expected_commission_sha256=self.pin,
            expected_root_pin=self.authority.root_provision_sha256,
            trusted_headers=[e['event'] for e in self.authority.entries])
        self.ready = threading.Event()
        self.failure = None
        self.result_condition = threading.Condition()
        self.completed_results = set()
        original_new = t._new

        def retain_completed(path, data):
            original_new(path, data)
            path = Path(path)
            if path.parent == self.base / 'server-native' and path.name.startswith('result-'):
                with self.result_condition:
                    self.completed_results.add(path)
                    self.result_condition.notify_all()

        writer = patch.object(t, '_new', side_effect=retain_completed)
        writer.start(); self.addCleanup(writer.stop)

        def serving():
            try:
                self.server = t.AuthorityTransportServer(self.authority, self.commission,
                    expected_commission_sha256=self.pin,
                    expected_root_pin=self.authority.root_provision_sha256,
                    ca_file=p['ca'], server_cert=p['server'], server_key=self.pki['private']['server'],
                    native_directory=self.base / 'server-native')
                self.address = self.server.start(); self.ready.set()
                self.server.serve_forever()
            except BaseException as error:
                with self.result_condition:
                    self.failure = error
                    self.result_condition.notify_all()
                self.ready.set()

        self.thread = threading.Thread(target=serving, daemon=True); self.thread.start()
        self.assertTrue(self.ready.wait(10))
        if self.failure:
            raise self.failure
        self.client_count = 0
        self.client = self.make_client()

    def tearDown(self):
        if hasattr(self, 'server'):
            self.server.stop()
            self.thread.join(15)
            self.assertFalse(self.thread.is_alive())
        if self.failure:
            raise self.failure
        self.tmp.cleanup()

    def make_client(self, commission=None, anchor=None):
        self.client_count += 1
        value = self.commission if commission is None else commission
        return t.AuthorityTransportClient(value,
            expected_commission_sha256=t.commission_digest(value),
            expected_root_pin=self.authority.root_provision_sha256,
            anchor_path=self.anchor if anchor is None else anchor,
            host=self.address[0], port=self.address[1], ca_file=self.pki['public']['ca'],
            client_cert=self.pki['public']['client'], client_key=self.pki['private']['client'],
            native_directory=self.base / ('client-' + str(self.client_count)), timeout=5)

    def anchor_value(self):
        return load_json_strict(self.anchor.read_bytes())

    def request(self, operation='read', **updates):
        result = self.client._request(operation, self.anchor_value(),
            credits=2 if operation == 'run' else None, request_nonce=sha(b'test request'))
        result.update(updates)
        return result

    def wait_results(self, count):
        # File creation precedes write/flush/fsync. Only the real writer's
        # successful return is a completion barrier; parse finalized bytes once.
        with self.result_condition:
            completed = self.result_condition.wait_for(
                lambda: self.failure is not None or len(self.completed_results) >= count, timeout=5)
            if self.failure is not None:
                raise self.failure
            self.assertTrue(completed, 'server native result write did not complete')
            files = sorted(self.completed_results)
        return [load_json_strict(p.read_bytes()) for p in files]

    def raw_tls(self, *, client='client', ca='ca', server_name='localhost', frame=None):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.load_verify_locations(cafile=self.pki['public'][ca])
        if client is not None:
            context.load_cert_chain(self.pki['public'][client], self.pki['private'][client])
        with socket.create_connection(self.address, timeout=5) as raw:
            with context.wrap_socket(raw, server_hostname=server_name) as connection:
                connection.sendall(t.frame_bytes(self.request()) if frame is None else frame)
                return t.receive_frame(connection, {}, 'frame')

    def test_actual_mutual_tls_read_records_both_observed_identities(self):
        reply = self.client.read()
        self.assertTrue(reply['accepted'])
        server = self.wait_results(1)[0]
        client = load_json_strict((self.base / 'client-1/result-0000.json').read_bytes())
        self.assertEqual(server['peer_certificate_sha256'], self.commission['client_certificate_sha256'])
        self.assertEqual(client['peer_certificate_sha256'], self.commission['server_certificate_sha256'])
        self.assertEqual(client['tls_version'], 'TLSv1.3')
        self.assertEqual(client['request_frame_hex'], server['request_frame_hex'])
        self.assertEqual(client['response_frame_hex'], server['response_frame_hex'])
        self.assertEqual(self.authority.calls, 0)

    def test_matching_run_resolves_only_after_durable_complete(self):
        reply = self.client.run(2, sha(b'authorized'))
        self.assertTrue(reply['accepted'])
        anchor = self.anchor_value()
        self.assertIsNone(anchor['pending'])
        self.assertEqual(anchor['resolved'][0]['outcome'], 'complete')
        operation = load_json_strict((self.base / 'client-1/operation-0000.json').read_bytes())
        self.assertIsNotNone(operation['pending_before_send']['pending'])
        self.assertEqual(self.authority.calls, 1)

    def test_aggregate_denial_is_terminal_without_extra_execution(self):
        reply = self.client.run(13, sha(b'denied'))
        self.assertFalse(reply['accepted'])
        self.assertEqual(reply['reason'], 'aggregate_budget_denied')
        self.assertEqual(self.anchor_value()['resolved'][0]['outcome'], 'denied')
        self.assertEqual(self.authority.calls, 0)

    def test_missing_client_certificate_rejected_by_actual_tls(self):
        with self.assertRaises((ssl.SSLError, OSError, EOFError)):
            self.raw_tls(client=None)
        self.assertFalse(self.wait_results(1)[0]['peer_pin_matched'])
        self.assertEqual(self.authority.calls, 0)

    def test_foreign_ca_client_rejected_by_actual_tls(self):
        with self.assertRaises((ssl.SSLError, OSError, EOFError)):
            self.raw_tls(client='foreign-client')
        self.assertFalse(self.wait_results(1)[0]['peer_pin_matched'])

    def test_same_ca_uncommissioned_client_rejected_after_handshake(self):
        with self.assertRaises((ssl.SSLError, OSError, EOFError)):
            self.raw_tls(client='other-client')
        observed = self.wait_results(1)[0]
        self.assertEqual(observed['phase'], 'tls_authenticated')
        self.assertEqual(observed['peer_certificate_sha256'], self.pki['identities']['other-client']['der_sha256'])
        self.assertFalse(observed['peer_pin_matched'])

    def test_wrong_server_ca_rejected_by_actual_tls(self):
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.raw_tls(ca='foreign-ca')
        self.wait_results(1)

    def test_wrong_server_hostname_rejected_by_actual_tls(self):
        # Deterministically expose the original create-before-write race using
        # this same TLS rejection. The production writer and protocol stay real.
        created = threading.Event(); release = threading.Event()
        reader_entered = threading.Event(); reader_done = threading.Event()
        observed = []; errors = []; reader = None
        target = self.base / 'server-native/result-0000.json'
        original_open = t.os.open

        def pause_created(path, *args, **kwargs):
            descriptor = original_open(path, *args, **kwargs)
            if Path(path) == target and threading.current_thread() is self.thread:
                created.set()
                if not release.wait(10):
                    t.os.close(descriptor)
                    raise TimeoutError('designated result writer pause was not released')
            return descriptor

        def reading():
            # Holding this condition until wait_results releases it lets the
            # test distinguish a blocked reader from one not yet scheduled.
            with self.result_condition:
                reader_entered.set()
                try:
                    observed.extend(self.wait_results(1))
                except BaseException as error:
                    errors.append(error)
                finally:
                    reader_done.set()

        try:
            with patch.object(t.os, 'open', side_effect=pause_created):
                with self.assertRaises(ssl.SSLCertVerificationError):
                    self.raw_tls(server_name='wrong.invalid')
                self.assertTrue(created.wait(5), 'server did not create the designated result')
                self.assertEqual(target.read_bytes(), b'')
                reader = threading.Thread(target=reading)
                reader.start()
                self.assertTrue(reader_entered.wait(5))
                with self.result_condition:
                    self.assertFalse(reader_done.is_set(), 'result reader finished before the native writer returned')
                    self.assertNotIn(target, self.completed_results)
        finally:
            release.set()
            if reader is not None:
                reader.join(10)
                self.assertFalse(reader.is_alive(), 'designated result reader did not finish')
        if errors:
            raise errors[0]
        self.assertTrue(reader_done.is_set())
        self.assertEqual(len(observed), 1)
        self.assertIsNotNone(observed[0]['error_type'])
        self.assertEqual(self.authority.calls, 0)

        # Completion waiting must not hide a malformed finalized record or a
        # writer failure. These are explicit fixture faults, not TLS evidence.
        malformed = self.base / 'malformed-completed-result.json'
        malformed.write_bytes(b'{')
        with patch.object(self, 'completed_results', {malformed}):
            with self.assertRaises(CanonicalizationError):
                self.wait_results(1)
        failure = OSError('designated completed-writer failure')
        with patch.object(self, 'failure', failure):
            with self.assertRaises(OSError) as caught:
                self.wait_results(1)
            self.assertIs(caught.exception, failure)

    def test_wrong_server_exact_pin_rejected_before_request(self):
        changed = copy.deepcopy(self.commission)
        changed['server_certificate_pem'] = Path(self.pki['public']['other-client']).read_text()
        changed['server_certificate_sha256'] = self.pki['identities']['other-client']['der_sha256']
        other_anchor = self.base / 'other-anchor.json'
        t.create_anchor(other_anchor, changed, expected_commission_sha256=t.commission_digest(changed),
            expected_root_pin=self.authority.root_provision_sha256,
            trusted_headers=self.anchor_value()['headers'])
        client = self.make_client(changed, other_anchor)
        with self.assertRaisesRegex(ResourceError, 'independently pinned'):
            client.read()
        observed = load_json_strict((self.base / 'client-2/result-0000.json').read_bytes())
        self.assertFalse(observed['request_sent'])
        self.wait_results(1)

    def test_independent_commission_digest_substitution_refused(self):
        with self.assertRaises(ResourceError):
            t.validate_commission(self.commission, expected_commission_sha256='1' * 64,
                                 expected_root_pin=self.authority.root_provision_sha256)

    def test_root_pin_substitution_refused_before_connection(self):
        with self.assertRaises(ResourceError):
            t.validate_commission(self.commission, expected_commission_sha256=self.pin,
                                 expected_root_pin='2' * 64)

    def test_missing_anchor_never_silently_initialized(self):
        with self.assertRaises(ResourceError):
            self.make_client(anchor=self.base / 'missing-anchor.json')
        self.assertFalse((self.base / 'missing-anchor.json').exists())

    def test_existing_anchor_cannot_be_reprovisioned(self):
        original = self.anchor.read_bytes()
        with self.assertRaises(ResourceError):
            t.create_anchor(self.anchor, self.commission, expected_commission_sha256=self.pin,
                expected_root_pin=self.authority.root_provision_sha256,
                trusted_headers=self.anchor_value()['headers'])
        self.assertEqual(original, self.anchor.read_bytes())

    def test_lost_reply_retains_pending_blocks_retry_and_reconciles_without_reissue(self):
        nonce = sha(b'lost response')
        self.assertIsNone(self.client.run(2, nonce, abandon_response=True))
        self.wait_results(1)
        self.assertIsNotNone(self.anchor_value()['pending'])
        with self.assertRaises(ResourceError):
            self.client.run(2, sha(b'forbidden retry'))
        with self.assertRaises(ResourceError):
            self.client.read()
        result = self.client.reconcile()
        self.assertFalse(result['pending_retained'])
        self.assertFalse(result['worker_reissued'])
        self.assertEqual(self.authority.calls, 1)

    def test_read_only_reconcile_without_matching_event_keeps_pending(self):
        anchor = self.anchor_value()
        request = self.request('run')
        anchor['pending'] = {'request': request, 'request_sha256': sha(canonical(request))}
        t._replace(self.anchor, anchor)
        result = self.client.reconcile()
        self.assertTrue(result['pending_retained'])
        self.assertEqual(result['observed_outcome'], 'unobserved')
        self.assertEqual(self.authority.calls, 0)

    def test_reconcile_does_not_match_nonce_with_different_exact_request(self):
        nonce = sha(b'existing old request')
        self.client.run(2, nonce)
        anchor = self.anchor_value()
        request = self.client._request('run', anchor, credits=3, request_nonce=nonce)
        anchor['pending'] = {'request': request, 'request_sha256': sha(canonical(request))}
        t._replace(self.anchor, anchor)
        result = self.client.reconcile()
        self.assertTrue(result['pending_retained'])
        self.assertEqual(self.authority.calls, 1)

    def test_stale_cursor_refused_without_new_mutation(self):
        stale = self.request('run')
        self.client.run(2, sha(b'advance'))
        before = self.authority.cursor
        reply = self.client._exchange(stale)
        self.assertFalse(reply['accepted'])
        self.assertEqual(before, self.authority.cursor)
        self.assertEqual(self.authority.calls, 1)

    def test_replayed_nonce_refused_with_updated_cursor(self):
        nonce = sha(b'used nonce')
        self.client.run(2, nonce)
        reply = self.client.run(2, nonce)
        self.assertFalse(reply['accepted'])
        self.assertEqual(self.anchor_value()['resolved'][-1]['outcome'], 'direct_refusal')
        self.assertEqual(self.authority.calls, 1)

    def test_remote_administrative_operations_never_dispatch(self):
        before = self.authority.cursor
        for op in ('finish', 'stop', 'reopen', 'provision', 'reserve_reference_test', 'export'):
            with self.subTest(operation=op):
                with self.assertRaises((OSError, EOFError, ValueError)):
                    self.client._exchange(self.request(operation=op))
        self.assertEqual(before, self.authority.cursor)
        self.assertEqual(self.authority.calls, 0)

    def test_injected_authority_fields_never_dispatch(self):
        for field in ('peer_certificate_sha256', 'evaluator', 'source_root', 'grant', 'backend', 'result'):
            with self.subTest(field=field):
                with self.assertRaises((OSError, EOFError, ValueError)):
                    self.client._exchange(self.request(**{field: 'attacker supplied'}))
        self.assertEqual(self.authority.calls, 0)

    def test_oversized_length_rejected_before_frame_body(self):
        with self.assertRaises((OSError, EOFError, ValueError)):
            self.raw_tls(frame=struct.pack('!I', t.MAX_FRAME + 1))
        self.assertEqual(self.wait_results(1)[0]['request_frame_hex'], struct.pack('!I', t.MAX_FRAME + 1).hex())

    def test_noncanonical_and_duplicate_json_rejected(self):
        for data in (b'{"x":1, "x":2}', b'{ "operation": "read" }'):
            with self.subTest(data=data):
                with self.assertRaises((OSError, EOFError, ValueError)):
                    self.raw_tls(frame=struct.pack('!I', len(data)) + data)
        self.assertEqual(self.authority.calls, 0)

    def test_response_challenge_substitution_preserves_pending(self):
        original = self.client._exchange
        def substitute(request, **kwargs):
            response = original(request, **kwargs)
            response['challenge'] = '1' * 64
            return response
        self.client._exchange = substitute
        with self.assertRaises(ResourceError):
            self.client.run(2, sha(b'bad reply'))
        self.assertIsNotNone(self.anchor_value()['pending'])
        self.assertEqual(self.authority.calls, 1)

    def test_observed_root_rollback_rejected_against_retained_anchor(self):
        old = copy.deepcopy(self.authority.entries)
        self.client.run(2, sha(b'advanced root'))
        saved = self.anchor.read_bytes()
        self.authority.entries = old
        with self.assertRaisesRegex(ResourceError, 'rolled back'):
            self.client.read()
        self.assertEqual(saved, self.anchor.read_bytes())

    def test_rehashed_fork_rejected_against_exact_anchor_prefix(self):
        self.client.run(2, sha(b'anchored request'))
        headers = copy.deepcopy(self.anchor_value()['headers'])
        headers[-1]['snapshot_sha256'] = 'a' * 64
        core = {k: v for k, v in headers[-1].items() if k != 'root_head'}
        headers[-1]['root_head'] = sha(al.DOMAIN + b'EVENT\0' + canonical(core))
        with self.assertRaisesRegex(ResourceError, 'forks'):
            t.verify_headers(headers, root_pin=self.authority.root_provision_sha256,
                             anchor_headers=self.anchor_value()['headers'])

    def test_joint_root_and_anchor_rollback_remains_outside_guarantee(self):
        initial = self.anchor_value()['headers']
        self.client.run(2, sha(b'future lost jointly'))
        checked = t.verify_headers(initial, root_pin=self.authority.root_provision_sha256,
                                   anchor_headers=initial)
        self.assertEqual(checked['cursor'], t.event_cursor(initial[-1]))
        self.assertFalse(self.commission['global_authority_exclusivity_established'])

    def test_header_hash_tamper_rejected(self):
        headers = self.anchor_value()['headers']
        headers[-1]['snapshot_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ResourceError, 'hash differs'):
            t.verify_headers(headers, root_pin=self.authority.root_provision_sha256)

    def test_anchor_exclusive_lock_blocks_competing_client(self):
        lock = t.ak._LifetimeLock(self.anchor.with_name(self.anchor.name + '.lock'))
        try:
            with self.assertRaises((OSError, ResourceError)):
                self.client.read()
        finally:
            lock.close()

    def test_client_pin_cannot_be_supplied_in_json(self):
        with self.assertRaises((OSError, EOFError, ValueError)):
            self.client._exchange(self.request(peer_certificate_sha256=self.commission['client_certificate_sha256']))
        self.assertEqual(self.authority.calls, 0)

    def test_commission_never_claims_independent_production_deployment(self):
        changed = copy.deepcopy(self.commission)
        changed['independently_protected_deployment_established'] = True
        with self.assertRaises(ResourceError):
            t.validate_commission(changed, expected_commission_sha256=t.commission_digest(changed),
                                 expected_root_pin=self.authority.root_provision_sha256)

    def test_transport_identity_includes_both_fixed_scripts(self):
        bound = self.commission['implementation']['code_sha256']
        for name in t.SCRIPTS:
            self.assertEqual(bound[name], sha((t.SOURCE_ROOT / name).read_bytes()))


if __name__ == '__main__':
    unittest.main()
