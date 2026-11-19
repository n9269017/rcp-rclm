"""Pure AN parser/observation guards using expressly synthetic records.

No fixture here is an authority lifetime, worker, TLS connection, protected
namespace observation, or accepted campaign. Actual application evidence is
captured and validated separately. These tests start no subprocess or network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import protected_authority_capture as capture
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha


def stamp(second):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=second)).isoformat()


def process_fixture(role='authority'):
    """Syntactic observation only; every PID/clock/stream is synthetic."""
    root = capture.SOURCE_ROOT
    directory = 'authority/synthetic' if role == 'authority' else 'frontend/synthetic'
    script = capture.SERVICE if role == 'authority' else capture.FRONTEND
    command = [sys.executable, '-I', '-S', '-B', '-u', str(root / script)]
    start = {'schema': capture.NATIVE_SCHEMA, 'role': role,
        'invocation_id': sha(b'AN synthetic invocation')[:32], 'started_at_utc': stamp(0),
        'observer_pid': 100, 'command': command, 'cwd': str(root), 'source_root': str(root),
        'python_sha256': sha(b'synthetic interpreter identity; no executable observation'),
        'entrypoint_sha256': sha((root / script).read_bytes()),
        'root_provision_sha256': sha(b'synthetic root pin'),
        'commission_sha256': sha(b'synthetic commission pin'),
        'shell': False, 'close_fds': True, 'physical_attestation': False}
    if role == 'authority':
        start['boot_nonce'] = sha(b'synthetic boot nonce')
    else:
        # _process checks process-record joins only. The full packet validator
        # separately validates the actual role-specific isolation specification.
        start.update(action='synthetic', entrypoint_command=command, isolation_specification=None)
    child = {'schema': capture.NATIVE_SCHEMA, 'invocation_id': start['invocation_id'],
             'child_pid': 200, 'observer_pid': 100, 'observed_at_utc': stamp(1)}
    streams = {'stdin.jsonl': b'{"synthetic":true}\n',
               'stdout.jsonl': b'{"synthetic":true}\n', 'stderr.txt': b''}
    result = {'schema': capture.NATIVE_SCHEMA, 'invocation_id': start['invocation_id'],
        'child_pid': 200, 'completed_at_utc': stamp(2), 'elapsed_ns': 2 * 10 ** 9,
        'returncode': 0, 'native_wait_completed': True, 'reader_finished': True,
        'stream_sha256': {name: sha(raw) for name, raw in streams.items()}}
    if role == 'authority':
        result.update(timed_out=False, reader_error=None, export_sha256=sha(b'synthetic export'))
    else:
        result.update(reader_errors=[], killed_by_observer=False)
    images = {directory + '/' + name: raw for name, raw in streams.items()}
    for name, value in [('start.json', start), ('child.json', child), ('result.json', result)]:
        images[directory + '/' + name] = canonical(value)
    return images, directory, root


class ProtectedAuthorityCaptureTests(unittest.TestCase):
    def rewrite(self, images, directory, name, update):
        path = directory + '/' + name
        value = load_json_strict(images[path], require_canonical=True)
        update(value)
        images[path] = canonical(value)

    def rejected_mutation(self, name, update, *, role='authority'):
        images, directory, root = process_fixture(role)
        self.rewrite(images, directory, name, update)
        with self.assertRaises(ValueError): capture._process(images, directory, root, role)

    def test_synthetic_authority_and_frontend_process_joins(self):
        for role in ('authority', 'frontend'):
            with self.subTest(role=role):
                images, directory, root = process_fixture(role)
                start, child, result = capture._process(images, directory, root, role)
                self.assertEqual(start['invocation_id'], child['invocation_id'])
                self.assertEqual(child['child_pid'], result['child_pid'])
                self.assertIs(start['physical_attestation'], False)

    def test_relative_paths_are_canonical_bounded_and_scoped(self):
        self.assertEqual(capture._relative('broker/action/dispatch.json'), 'broker/action/dispatch.json')
        rejected = ('', '.', './authority/a.json', '/authority/a.json', 'authority//a.json',
                    'authority/../a.json', 'authority\\a.json', 'C:/authority/a.json',
                    'private/key.pem', 'authority/a\x00.json', 'authority/' + 'a' * 501)
        for name in rejected:
            with self.subTest(name=name), self.assertRaises(ValueError): capture._relative(name)

    def test_images_require_exact_hex_and_refuse_private_material(self):
        self.assertEqual(capture._images({'native_images': {'provisioning/public.bin': '6162'}}),
                         {'provisioning/public.bin': b'ab'})
        for raw in ('AB', '61 62', '0', 'xz', b'6162',
                    b'-----BEGIN PRIVATE KEY-----\nprivate\n-----END PRIVATE KEY-----'.hex()):
            with self.subTest(raw=str(raw)[:80]), self.assertRaises(ValueError):
                capture._images({'native_images': {'provisioning/public.bin': raw}})

    def test_images_inventory_count_type_and_path_guards(self):
        variants = ({}, [], None, True,
                    {'authority/file-%04d.bin' % i: '' for i in range(capture.MAX_NATIVE_FILES + 1)},
                    {'workers/../../private.key': '61'})
        for value in variants:
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                capture._images({'native_images': value})

    def test_json_requires_present_canonical_original_bytes(self):
        with self.assertRaises(ValueError): capture._json({}, 'broker/absent.json')
        for raw in (b'{"b":2,"a":1}', b'{ "a":1}', b'{"a":1}\n', b'{"a":1,"a":1}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                capture._json({'broker/synthetic.json': raw}, 'broker/synthetic.json')

    def test_native_record_field_inventory_is_exact(self):
        for name in ('start.json', 'child.json', 'result.json'):
            with self.subTest(name=name, change='extra'):
                self.rejected_mutation(name, lambda v: v.update(untrusted=True))
            with self.subTest(name=name, change='missing'):
                self.rejected_mutation(name, lambda v: v.pop('schema'))

    def test_native_schema_and_invocation_joins_are_exact(self):
        for name in ('start.json', 'child.json', 'result.json'):
            with self.subTest(name=name, field='schema'):
                self.rejected_mutation(name, lambda v: v.update(schema='foreign.native-record'))
            with self.subTest(name=name, field='invocation_id'):
                self.rejected_mutation(name, lambda v: v.update(invocation_id=sha(b'other')[:32]))
        self.rejected_mutation('start.json', lambda v: v.update(role='frontend'))

    def test_pid_types_range_and_parent_child_join(self):
        for name, field in (('start.json', 'observer_pid'), ('child.json', 'observer_pid'),
                            ('child.json', 'child_pid'), ('result.json', 'child_pid')):
            for invalid in (True, 0, -1, 2 ** 63, '200'):
                with self.subTest(name=name, field=field, value=invalid):
                    self.rejected_mutation(name, lambda v, f=field, x=invalid: v.update({f: x}))
        self.rejected_mutation('child.json', lambda v: v.update(observer_pid=101))
        self.rejected_mutation('result.json', lambda v: v.update(child_pid=201))
        images, directory, root = process_fixture()
        for name in ('child.json', 'result.json'):
            self.rewrite(images, directory, name, lambda v: v.update(child_pid=100))
        with self.assertRaises(ValueError): capture._process(images, directory, root, 'authority')

    def test_original_timestamps_are_utc_and_ordered(self):
        for invalid in ('not-a-timestamp', '2026-01-01T00:00:01', '2026-01-01T00:00:01+01:00', 1):
            with self.subTest(value=invalid):
                self.rejected_mutation('child.json', lambda v, x=invalid: v.update(observed_at_utc=x))
        self.rejected_mutation('child.json', lambda v: v.update(observed_at_utc=stamp(-1)))
        self.rejected_mutation('result.json', lambda v: v.update(completed_at_utc=stamp(0)))

    def test_elapsed_time_and_exit_code_are_exact_bounded_integers(self):
        for field, values in [('elapsed_ns', (True, -1, 1200 * 10 ** 9 + 1, '2')),
                              ('returncode', (False, True, -1, 1, '0'))]:
            for invalid in values:
                with self.subTest(field=field, value=invalid):
                    self.rejected_mutation('result.json', lambda v, f=field, x=invalid: v.update({f: x}))

    def test_completed_native_wait_and_reader_are_exact_booleans(self):
        for field in ('native_wait_completed', 'reader_finished'):
            for invalid in (1, False, 'true', None):
                with self.subTest(field=field, value=invalid):
                    self.rejected_mutation('result.json', lambda v, f=field, x=invalid: v.update({f: x}))

    def test_source_root_cwd_and_entrypoint_byte_binding(self):
        for field in ('source_root', 'cwd'):
            self.rejected_mutation('start.json', lambda v, f=field: v.update({f: str(capture.SOURCE_ROOT) + '/suffix'}))
        self.rejected_mutation('start.json', lambda v: v.update(entrypoint_sha256=sha(b'changed script')))
        self.rejected_mutation('start.json', lambda v: v.update(python_sha256='not-a-digest'))

    def test_launch_and_attestation_flags_cannot_use_integer_substitutes(self):
        for field, values in [('shell', (0, True)), ('close_fds', (1, False)),
                              ('physical_attestation', (0, True))]:
            for invalid in values:
                with self.subTest(field=field, value=invalid):
                    self.rejected_mutation('start.json', lambda v, f=field, x=invalid: v.update({f: x}))

    def test_stream_inventory_and_each_original_digest_are_required(self):
        for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt'):
            images, directory, root = process_fixture()
            images[directory + '/' + name] += b'tampered'
            with self.subTest(stream=name), self.assertRaises(ValueError):
                capture._process(images, directory, root, 'authority')
        self.rejected_mutation('result.json', lambda v: v['stream_sha256'].pop('stdin.jsonl'))
        self.rejected_mutation('result.json', lambda v: v['stream_sha256'].update(extra=sha(b'')))

    def test_self_consistent_nonempty_diagnostics_still_reject(self):
        images, directory, root = process_fixture()
        images[directory + '/stderr.txt'] = b'original diagnostic'
        self.rewrite(images, directory, 'result.json',
                     lambda v: v['stream_sha256'].update({'stderr.txt': sha(b'original diagnostic')}))
        with self.assertRaises(ValueError): capture._process(images, directory, root, 'authority')

    def test_timeout_reader_failure_or_killed_frontend_never_counts_as_completion(self):
        for field, invalid in (('timed_out', True), ('timed_out', 0), ('reader_error', 'capture failed')):
            with self.subTest(field=field, value=invalid):
                self.rejected_mutation('result.json', lambda v, f=field, x=invalid: v.update({f: x}))
        for field, invalid in (('reader_errors', ['capture failed']), ('killed_by_observer', True),
                               ('killed_by_observer', 0)):
            with self.subTest(field=field, value=invalid):
                self.rejected_mutation('result.json', lambda v, f=field, x=invalid: v.update({f: x}),
                                       role='frontend')

    def test_observation_parser_starts_no_process_network_or_database(self):
        images, directory, root = process_fixture()
        with patch.object(capture.subprocess, 'Popen', side_effect=AssertionError('process forbidden')) as process, \
             patch.object(capture.transport.socket, 'create_connection', side_effect=AssertionError('network forbidden')) as network, \
             patch.object(capture.sqlite3, 'connect', side_effect=AssertionError('database forbidden')) as database:
            capture._process(images, directory, root, 'authority')
            process.assert_not_called(); network.assert_not_called(); database.assert_not_called()
