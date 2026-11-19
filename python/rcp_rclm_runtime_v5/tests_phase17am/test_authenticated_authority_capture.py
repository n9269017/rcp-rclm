"""Pure original-record parser/tamper fixtures. No TLS, worker or proof credit."""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import authenticated_authority_capture as c
from rcp_rclm_runtime_v5.phase17 import authority_transport as t
from rcp_rclm_runtime_v5.phase17 import durable_campaign as al
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, canonical, sha


def stamp(seconds):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat()


def fixture():
    """Syntactic observation fixture only, explicitly never a native capture."""
    root = t.SOURCE_ROOT
    physical = Path('/synthetic-phase17am') if sys.platform != 'win32' else Path('C:/synthetic-phase17am')
    private = physical / 'private'; native = physical / 'campaign-native'
    pin = sha(b'synthetic root')
    entries = []

    def event(kind, request=None, boot=None):
        previous = None if not entries else t.event_cursor(entries[-1]['event'])
        snapshot = {'journal_hex': b'{}\n'.hex(), 'pending': None, 'nonces': [], 'sessions': []}
        epoch = 0 if previous is None else previous['epoch'] + (kind == 'reopen')
        header = al._event(pin, snapshot, previous=previous, kind=kind, epoch=epoch,
            boot_nonce=boot, request=request, session={'synthetic': True} if kind == 'complete' else None)
        entries.append({'event': header, 'snapshot': snapshot})

    event('provision'); event('reopen', boot=c._nonce('boot-0'))
    for action in ('run_one', 'run_abandon'):
        request = {'expected_cursor': t.event_cursor(entries[-1]['event']),
                   'request_nonce': c._nonce(action), 'credits': 2}
        event('reserve', request); event('launch'); event('complete')
    event('reopen', boot=c._nonce('boot-1'))
    event('deny', {'expected_cursor': t.event_cursor(entries[-1]['event']),
                   'request_nonce': c._nonce('aggregate_denial'), 'credits': 2})
    headers = [e['event'] for e in entries]
    certificates = {}; der = {}
    for name in ('ca', 'server', 'client', 'other-client', 'foreign-ca', 'foreign-client'):
        der[name] = ('synthetic certificate ' + name).encode()
        certificates[name] = (b'-----BEGIN CERTIFICATE-----\n' + base64.b64encode(der[name]) +
                              b'\n-----END CERTIFICATE-----\n')
    commission = {'schema': 'synthetic-commission-not-native',
        'server_certificate_sha256': sha(der['server']), 'client_certificate_sha256': sha(der['client'])}
    commission_pin = t.commission_digest(commission)
    anchor = {'schema': t.ANCHOR_SCHEMA, 'commission_sha256': commission_pin,
        'root_provision_sha256': pin, 'headers': headers[:1], 'pending': None, 'resolved': []}
    images = {}
    def put(name, value):
        images[name] = value if isinstance(value, bytes) else canonical(value)
    pki = {'schema': 'phase17am.reference-pki-generation.v1', 'directory': str(private),
        'openssl_path': str(physical / 'openssl'), 'openssl_sha256': sha(b'synthetic openssl'),
        'command_records_directory': str(private / 'command-records'),
        'public': {n: str(private / (n + '.pem')) for n in der},
        'identities': {n: {'pem_sha256': sha(certificates[n]), 'der_sha256': sha(der[n])} for n in der},
        'commands': [{'command': [str(physical / 'openssl'), 'version'], 'cwd': str(private),
            'native_wait_completed': True, 'returncode': 0, 'timed_out': False, 'error_type': None,
            'shell': False, 'child_pid': 800 + i, 'elapsed_ns': 1, 'stdout_hex': '', 'stderr_hex': ''}
            for i in range(11)], 'independent_production_issuer_established': False,
        'private_material_is_publication_evidence': False}
    put('provisioning/pki.json', pki)
    put('provisioning/commissioning.json', {'commission': commission,
        'commission_sha256': commission_pin, 'root_provision_sha256': pin,
        'initial_anchor': copy.deepcopy(anchor), 'private_keys_published': False,
        'independent_production_issuer_established': False})
    evidence = {'entries': entries, 'final_cursor': t.event_cursor(headers[-1]), 'scope': {'synthetic': True}}
    grants = [sha(b'fixture grant0'), sha(b'fixture grant1')]
    case = {'commission': commission, 'root_provision_sha256': pin,
        'certificates': {n: raw.hex() for n, raw in certificates.items()}, 'evidence': evidence,
        'native_boots': ['lifetime-0', 'lifetime-1'], 'worker_grants': grants}
    identity = sha(b'synthetic interpreter')
    service_starts = []
    def process(directory, role, command, start_at, end_at, pid, extra, stdout, stdin=None, exported=None):
        entry = c.SERVICE if role == 'authority' else c.DRIVER
        start = {'schema': c.NATIVE_SCHEMA, 'role': role, 'invocation_id': sha(directory.encode())[:32],
            'started_at_utc': stamp(start_at), 'observer_pid': 100, 'command': command,
            'cwd': str(root), 'source_root': str(root), 'python_sha256': identity,
            'entrypoint_sha256': sha((root / entry).read_bytes()), 'root_provision_sha256': pin,
            'commission_sha256': commission_pin, 'shell': False, 'close_fds': True,
            'physical_attestation': False, **extra}
        child = {'schema': c.NATIVE_SCHEMA, 'invocation_id': start['invocation_id'],
            'child_pid': pid, 'observer_pid': 100, 'observed_at_utc': stamp(start_at + 1)}
        streams = {'stdout.jsonl': stdout, 'stderr.txt': b''}
        if stdin is not None: streams['stdin.jsonl'] = stdin
        result = {'schema': c.NATIVE_SCHEMA, 'invocation_id': start['invocation_id'],
            'child_pid': pid, 'completed_at_utc': stamp(end_at), 'elapsed_ns': (end_at-start_at)*10**9,
            'returncode': 0, 'native_wait_completed': True, 'timed_out': False,
            'stream_sha256': {n: sha(raw) for n, raw in streams.items()}}
        if role == 'authority':
            result.update(reader_finished=True, reader_error=None, export_sha256=sha(canonical(exported)))
            put(directory + '/export.json', exported)
        for name, raw in streams.items(): put(directory + '/' + name, raw)
        for name, value in [('start.json', start), ('child.json', child), ('result.json', result)]:
            put(directory + '/' + name, value)
    ports = (27101, 27102)
    for index in (0, 1):
        name = 'lifetime-' + str(index); directory = 'authority/' + name
        options = ['--directory', str(physical / 'root'), '--commission', str(physical / 'commission.json'),
            '--commission-pin', commission_pin, '--root-pin', pin, '--boot-nonce', c._nonce('boot-' + str(index)),
            '--ca-file', str(private / 'ca.pem'), '--server-cert', str(private / 'server.pem'),
            '--server-key', str(private / 'server.key'), '--native-directory', str(native / directory / 'transport'),
            '--export', str(physical / 'exports' / (name + '.json'))]
        ready = {'schema': 'phase17am.authority-ready.v1', 'pid': 200 + index,
            'address': ['127.0.0.1', ports[index]], 'commission_sha256': commission_pin,
            'root_provision_sha256': pin, 'cursor': t.event_cursor(headers[1 if index == 0 else 8])}
        count = 8 if index == 0 else 10
        exported = {**evidence, 'entries': entries[:count], 'final_cursor': t.event_cursor(headers[count-1])}
        stopped = {'schema': 'phase17am.authority-stopped.v1', 'pid': 200 + index,
            'export_sha256': sha(canonical(exported)), 'connections': 7 if index == 0 else 2}
        process(directory, 'authority', [sys.executable, '-I', '-S', '-B', '-u', str(root / c.SERVICE), *options],
            0 if index == 0 else 110, 100 if index == 0 else 150, 200 + index,
            {'boot_nonce': c._nonce('boot-' + str(index))}, canonical(ready)+b'\n'+canonical(stopped)+b'\n',
            canonical({'operation': 'stop'})+b'\n', exported)
        service_starts.append(ready)
    service_sequence = [0, 0]
    positions = {'initial_read': (1,1), 'run_one': (1,4), 'stale': (4,4), 'replayed_nonce': (4,4),
                 'run_abandon': (4,7), 'reconcile': (8,8), 'aggregate_denial': (8,9)}
    for i, action in enumerate(c.ACTIONS):
        lifetime = 0 if i < 8 else 1; pid = 300 + i
        begin = 10 + i * 10 if i < 8 else 120 + (i-8)*10
        directory = 'client/' + action; before = copy.deepcopy(anchor)
        nonce = c._nonce('run_one' if action == 'replayed_nonce' else action)
        operation = {'schema': 'phase17am.selected-client-operation.v1', 'action': action,
            'request_nonce': nonce, 'anchor_before_hex': canonical(before).hex(),
            'anchor_before_sha256': sha(canonical(before)), 'request': None, 'result': None,
            'error_type': None, 'network_attempts': 0 if action == 'blocked_retry' else 1,
            'completed': True, 'automatic_retries': 0, 'physical_attestation': False}
        request = None; written = None; reply = None
        if action == 'blocked_retry':
            operation['error_type'] = 'ResourceError'
        else:
            reqop = 'read' if action in ('initial_read', 'reconcile') else 'run'
            request = {'schema': t.REQUEST_SCHEMA, 'commission_sha256': commission_pin,
                'root_provision_sha256': pin, 'operation': reqop, 'request_nonce': nonce,
                'challenge': sha(('challenge/'+action).encode()), 'expected_cursor': t.event_cursor(before['headers'][-1])}
            if reqop == 'run': request['credits'] = 2
            if action == 'stale': request['expected_cursor'] = service_starts[0]['cursor']
            if action == 'forbidden_operation': request['operation'] = 'finish'
            if action == 'extra_field': request['evaluator'] = 'caller-selected-code'
            invalid = action in ('forbidden_operation', 'extra_field')
            if invalid:
                operation['request'] = request; operation['error_type'] = 'EOFError'
            else:
                first, last = positions[action]
                accepted = action not in ('stale', 'replayed_nonce', 'aggregate_denial')
                reply = {'schema': t.RESPONSE_SCHEMA, 'commission_sha256': commission_pin,
                    'root_provision_sha256': pin, 'request_sha256': sha(canonical(request)),
                    'challenge': request['challenge'], 'operation': reqop, 'accepted': accepted,
                    'reason': None if accepted else 'aggregate_budget_denied' if action == 'aggregate_denial'
                              else 'protocol_or_authority_refused',
                    'before': t.event_cursor(headers[first]), 'after': t.event_cursor(headers[last]),
                    'headers': headers[:last+1], 'result': {'synthetic': True} if accepted else None}
                if action in ('stale', 'replayed_nonce'):
                    operation['request'] = request; operation['result'] = reply
                elif action in ('run_one', 'run_abandon', 'aggregate_denial'):
                    pending = {'request': request, 'request_sha256': sha(canonical(request))}
                    written = {**copy.deepcopy(before), 'pending': pending}; anchor = copy.deepcopy(written)
                    if action != 'run_abandon':
                        anchor['resolved'].append({'request_sha256': pending['request_sha256'],
                            'request_nonce': nonce, 'outcome': 'denied' if action == 'aggregate_denial' else 'complete',
                            'at_cursor': reply['after']})
                        anchor['pending'] = None; anchor['headers'] = reply['headers']; operation['result'] = reply
                elif action == 'initial_read':
                    anchor['headers'] = reply['headers']; operation['result'] = reply
                elif action == 'reconcile':
                    pending = anchor['pending']
                    anchor['resolved'].append({'request_sha256': pending['request_sha256'],
                        'request_nonce': pending['request']['request_nonce'], 'outcome': 'complete', 'at_cursor': reply['after']})
                    anchor['pending'] = None; anchor['headers'] = reply['headers']
                    operation['result'] = {'response': reply, 'pending_retained': False,
                        'observed_outcome': 'complete', 'worker_reissued': False}
            for role in ('client', 'server'):
                sequence = 0 if role == 'client' else service_sequence[lifetime]
                prefix = directory + '/inside/transport/' if role == 'client' else f'authority/lifetime-{lifetime}/transport/'
                base = {'schema': t.NATIVE_SCHEMA, 'role': role, 'sequence': sequence,
                    'pid': pid if role == 'client' else 200+lifetime, 'started_at_utc': stamp(begin + (3 if role == 'client' else 4)),
                    'remote_address': ['127.0.0.1', ports[lifetime] if role == 'client' else 42000+i],
                    'commission_sha256': commission_pin, 'root_provision_sha256': pin,
                    'phase': 'before_connect' if role == 'client' else 'accepted_tcp',
                    'request_frame_hex': '', 'response_frame_hex': '', 'peer_pin_matched': False, 'error_type': None}
                if role == 'client': base.update(request_sent=False, abandoned_response=False)
                else: base['response_sent'] = False
                put(prefix+('start-%04d.json' % sequence), base)
                result = {**base, 'completed_at_utc': stamp(begin + 6),
                    'peer_certificate_der_hex': der['server' if role == 'client' else 'client'].hex(),
                    'peer_certificate_sha256': sha(der['server' if role == 'client' else 'client']),
                    'tls_version': 'TLSv1.3', 'cipher': ['TLS_AES_256_GCM_SHA384', 'TLSv1.3', 256],
                    'peer_pin_matched': True, 'request_frame_hex': t.frame_bytes(request).hex()}
                if role == 'client':
                    result['request_sent'] = True
                    if invalid:
                        result.update(phase='request_sent', error_type='EOFError', error_message='connection ended within authority frame')
                    elif action == 'run_abandon': result.update(phase='response_deliberately_unobserved', abandoned_response=True)
                    else: result.update(phase='response_received', response_frame_hex=t.frame_bytes(reply).hex())
                elif invalid:
                    result.update(phase='request_received', error_type='ResourceError',
                        error_message='controller operation is not admitted' if action == 'forbidden_operation' else 'exact record fields required')
                else: result.update(phase='response_sent', response_sent=True, response_frame_hex=t.frame_bytes(reply).hex())
                put(prefix+('result-%04d.json' % sequence), result)
            service_sequence[lifetime] += 1
        operation.update(anchor_after_hex=canonical(anchor).hex(), anchor_after_sha256=sha(canonical(anchor)))
        put(directory+'/inside/operation.json', operation)
        if action not in ('stale', 'replayed_nonce', 'forbidden_operation', 'extra_field'):
            core = {'schema': 'phase17am.client-operation.v1', 'operation': 'read' if action == 'initial_read'
                    else 'reconcile' if action == 'reconcile' else 'run', 'pid': pid, 'sequence': 0,
                'exchange_sequence': 0, 'started_at_utc': stamp(begin+2), 'completed_at_utc': stamp(begin+8),
                'anchor_before': before, 'pending_before_send': written, 'request': request,
                'completed': action != 'blocked_retry', 'error_type': 'ResourceError' if action == 'blocked_retry' else None,
                'anchor_after': copy.deepcopy(anchor), 'anchor_after_sha256': sha(canonical(anchor))}
            put(directory+'/inside/transport/operation-0000.json', core)
        argv = [sys.executable, '-I', '-S', '-B', '-u', str(root/c.DRIVER), '--bundle', str(physical/'client-bundle'),
            '--anchor', str(physical/'client-state/anchor.json'), '--native-directory', str(native/directory/'inside'),
            '--commission-pin', commission_pin, '--root-pin', pin, '--port', str(ports[lifetime]),
            '--action', action, '--request-nonce', nonce]
        if action == 'stale': argv += ['--stale-cursor-json', canonical(service_starts[0]['cursor']).decode()]
        stdout = canonical({'schema': 'phase17am.selected-client-result.v1', 'action': action,
            'completed': True, 'record_sha256': sha(canonical(operation))})+b'\n'
        process(directory, 'client', argv, begin, begin+9, pid,
            {'action': action, 'controller_namespace_profile_used': False, 'isolation_specification': None}, stdout)
    for i, grant in enumerate(grants):
        for name in c.WORKER_FILES:
            value = {'synthetic': True}
            if name == 'start.json': value.update(observer_pid=200, started_at_utc=stamp(25+i*40))
            if name == 'result.json': value['completed_at_utc'] = stamp(26+i*40)
            put('workers/'+grant+'/'+name, value)
    return {'cases': [case], 'native_images': {n: raw.hex() for n, raw in images.items()}}


class CaptureParserTests(unittest.TestCase):
    def setUp(self):
        self.packet = fixture()

    def get(self, name):
        return load_json_strict(bytes.fromhex(self.packet['native_images'][name]))

    def set(self, name, value):
        self.packet['native_images'][name] = canonical(value).hex()

    def check(self):
        return c.verify_transport_images(self.packet)

    def test_synthetic_structure_is_accepted_without_starting_any_process(self):
        with patch.object(c.subprocess, 'Popen', side_effect=AssertionError('must not execute')):
            result = self.check()
        self.assertEqual(result['native_tls_connections'], 9)
        self.assertFalse(result['independently_protected_deployment_established'])

    def test_empty_or_partial_native_stream_hash_map_rejected(self):
        name = 'client/run_one/result.json'; record = self.get(name)
        record['stream_sha256'] = {}; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'exact record fields'):
            self.check()

    def test_extra_native_process_field_rejected(self):
        name = 'authority/lifetime-0/start.json'; record = self.get(name)
        record['unobserved_authority_override'] = True; self.set(name, record)
        with self.assertRaises(ResourceError): self.check()

    def test_changed_interpreter_identity_rejected(self):
        name = 'client/reconcile/start.json'; record = self.get(name)
        record['python_sha256'] = '1'*64; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'interpreter'): self.check()

    def test_duplicate_command_option_rejected(self):
        name = 'authority/lifetime-0/start.json'; record = self.get(name)
        record['command'] += ['--root-pin', '1'*64]; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'command'): self.check()

    def test_changed_client_action_or_nonce_command_rejected(self):
        name = 'client/stale/start.json'; record = self.get(name)
        record['command'][-1] = canonical(self.packet['cases'][0]['evidence']['final_cursor']).decode()
        self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'intended action'): self.check()

    def test_client_tls_pid_must_join_original_child(self):
        for leaf in ('start-0000.json', 'result-0000.json'):
            name = 'client/run_one/inside/transport/'+leaf; record = self.get(name)
            record['pid'] = 999; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'actual process lifetime'): self.check()

    def test_client_listener_address_must_join_service_ready(self):
        for leaf in ('start-0000.json', 'result-0000.json'):
            name = 'client/run_one/inside/transport/'+leaf; record = self.get(name)
            record['remote_address'][1] += 20; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'different listener'): self.check()

    def test_altered_observed_server_der_identity_rejected(self):
        name = 'client/run_one/inside/transport/result-0000.json'; record = self.get(name)
        record['peer_certificate_der_hex'] = b'substituted'.hex(); self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'commissioned TLS peer'): self.check()

    def test_omitted_or_extra_tls_start_is_unresolved(self):
        name = 'client/run_one/inside/transport/start-0000.json'
        self.packet['native_images'][name.replace('0000', '0001')] = self.packet['native_images'][name]
        with self.assertRaisesRegex(ResourceError, 'unresolved or extra'): self.check()

    def test_arbitrary_failure_does_not_count_as_designated_refusal(self):
        name = 'authority/lifetime-0/transport/result-0004.json'; record = self.get(name)
        record['error_message'] = 'unrelated storage failure'; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'exact pre-dispatch refusal'): self.check()

    def test_same_type_different_field_failure_is_not_designated(self):
        name = 'authority/lifetime-0/transport/result-0005.json'; record = self.get(name)
        record['error_message'] = 'request authority binding differs'; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'exact pre-dispatch refusal'): self.check()

    def test_write_ahead_record_must_bind_exact_sent_credits(self):
        name = 'client/run_abandon/inside/transport/operation-0000.json'; record = self.get(name)
        record['pending_before_send']['pending']['request']['credits'] = 3; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'write-ahead pending'): self.check()

    def test_missing_write_ahead_record_rejected(self):
        del self.packet['native_images']['client/run_abandon/inside/transport/operation-0000.json']
        with self.assertRaisesRegex(ResourceError, 'original native file missing'): self.check()

    def test_client_operation_anchor_after_must_match_recorded_actual_file(self):
        name = 'client/reconcile/inside/transport/operation-0000.json'; record = self.get(name)
        record['anchor_after']['resolved'][-1]['request_nonce'] = 'a'*64; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'operation/anchor join'): self.check()

    def test_tls_cipher_pair_cannot_disagree(self):
        name = 'client/run_one/inside/transport/result-0000.json'; record = self.get(name)
        record['cipher'] = ['TLS_AES_128_GCM_SHA256', 'TLSv1.3', 128]; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'overlap or agree'): self.check()

    def test_worker_observer_must_be_the_launching_authority(self):
        grant = self.packet['cases'][0]['worker_grants'][0]; name = 'workers/'+grant+'/start.json'
        record = self.get(name); record['observer_pid'] = 201; self.set(name, record)
        with self.assertRaisesRegex(ResourceError, 'first admitted authority'): self.check()

    def test_unexplained_native_file_not_accepted_as_evidence(self):
        self.packet['native_images']['client/forged-note.json'] = b'{}'.hex()
        with self.assertRaisesRegex(ResourceError, 'unexplained files'): self.check()

    def test_private_pem_content_rejected(self):
        self.packet['native_images']['provisioning/key.txt'] = b'-----BEGIN PRIVATE KEY-----\nnot a real key'.hex()
        with self.assertRaisesRegex(ResourceError, 'private native image'): self.check()

    def test_relative_native_path_escape_rejected(self):
        for name in ('../authority/key', '/authority/key', 'client/../key', 'client\\key', 'client:C/key'):
            with self.subTest(name=name), self.assertRaises(ResourceError): c._relative(name)

    def test_frame_length_and_duplicate_keys_rejected(self):
        with self.assertRaises(ResourceError): c._frame('000000057b7d')
        raw = b'{"a":1,"a":2}'
        with self.assertRaises(ValueError): c._frame((struct.pack('!I', len(raw))+raw).hex())


if __name__ == '__main__':
    unittest.main()
