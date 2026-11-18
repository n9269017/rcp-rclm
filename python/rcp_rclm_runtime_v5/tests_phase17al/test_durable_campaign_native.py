"""Synthetic native-record parser tests; no process or fresh-work evidence."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import durable_campaign_native as native
from rcp_rclm_runtime_v5.phase17.campaign_budget import make_grant
from rcp_rclm_runtime_v5.phase17.controller import FIXED_VERIFIER
from rcp_rclm_runtime_v5.phase17.metered_worker import WORKER_PROTOCOL
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha


def synthetic_records(source_root):
    """Wire-binding fixture only; its fake events are not evaluator semantics."""
    grant = make_grant({'campaign_id': '1' * 64, 'predecessor_state_hash': '2' * 64,
        'predecessor_package_hash': '3' * 64, 'fixed_verifier_hash': FIXED_VERIFIER,
        'installed_count': 8}, 0, '0' * 64, '4' * 64, 2)
    accounting = {'synthetic_parser_fixture': True, 'spent': [0, 0, 0, 0]}
    events = [{'request': {'op': 'open'}, 'response': {'sequence': 0, 'fixture': 'open'}},
              {'request': {'op': 'seal'}, 'response': {'sequence': 1, 'fixture': 'sealed'}}]
    inputs = [{'protocol': WORKER_PROTOCOL, 'grant': grant}, *[e['request'] for e in events]]
    outputs = [{'protocol': WORKER_PROTOCOL, 'event': 'grant_received', 'grant_hash': grant['grant_hash']}]
    outputs.extend({'protocol': WORKER_PROTOCOL, 'grant_hash': grant['grant_hash'],
        'response': event['response'], 'accounting': accounting if index == 1 else None}
        for index, event in enumerate(events))
    command = ['/synthetic/python', '-I', '-S', '-B', '-u',
               str(source_root / 'scripts/phase17_campaign_worker.py')]
    start = {'schema': native.SCHEMA, 'invocation_id': 'a' * 32,
        'started_at_utc': '2026-01-01T00:00:00+00:00', 'observer_pid': 111,
        'command': command, 'python_path': command[0], 'python_sha256': '5' * 64,
        'worker_source_sha256': sha((source_root / 'scripts/phase17_campaign_worker.py').read_bytes()),
        'grant_sha256': sha(canonical(grant)), 'environment_sha256': '6' * 64,
        'shell': False, 'close_fds': True, 'observer_is_trusted_reference_launcher': True,
        'physical_attestation': False}
    child = {'schema': native.SCHEMA, 'invocation_id': 'a' * 32,
        'observed_at_utc': '2026-01-01T00:00:01+00:00', 'child_pid': 222,
        'observer_pid': 111, 'command': command, 'cwd': '/synthetic/worker'}
    raw = {'start.json': canonical(start), 'child.json': canonical(child),
        'stdin.jsonl': b''.join(canonical(row) + b'\n' for row in inputs),
        'stdout.jsonl': b''.join(canonical(row) + b'\n' for row in outputs), 'stderr.txt': b''}
    result = {'schema': native.SCHEMA, 'invocation_id': 'a' * 32,
        'completed_at_utc': '2026-01-01T00:00:02+00:00', 'child_pid': 222,
        'returncode': 0, 'native_wait_completed': True, 'reader_finished': True,
        'killed_by_observer': False, 'capture_failed': False, 'sealed': True,
        'stream_sha256': {name: sha(raw[name]) for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')},
        'grant_sha256': start['grant_sha256'], 'physical_attestation': False}
    raw['result.json'] = canonical(result)
    return raw, grant, canonical({'events': events}), accounting


class WorkerNativeRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'source'
        (self.root / 'scripts').mkdir(parents=True)
        (self.root / 'scripts/phase17_campaign_worker.py').write_bytes(b'# Synthetic source binding only.\n')
        self.directory = Path(self.tmp.name) / 'native'; self.directory.mkdir()
        self.raw, self.grant, self.transcript, self.accounting = synthetic_records(self.root)
        self.write_all()

    def tearDown(self):
        self.tmp.cleanup()

    def write_all(self):
        for path in self.directory.iterdir(): path.unlink()
        for name, raw in self.raw.items(): (self.directory / name).write_bytes(raw)

    def change(self, name, fn):
        value = load_json_strict(self.raw[name]); fn(value)
        self.raw[name] = canonical(value); self.write_all()

    def rehash_streams(self):
        self.change('result.json', lambda r: r.update(stream_sha256={name: sha(self.raw[name])
            for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')}))

    def verify(self):
        return native.verify_native_records(self.directory, self.grant, self.transcript,
                                            self.accounting, source_root=self.root)

    def test_synthetic_binding_fixture_is_not_native_execution(self):
        self.assertEqual(self.verify(), {name: sha(raw) for name, raw in self.raw.items()})

    def test_exact_file_inventory_required(self):
        (self.directory / 'result.json').unlink()
        with self.assertRaisesRegex(ValueError, 'exact native worker record inventory'): self.verify()
        self.write_all(); (self.directory / 'unexpected.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'exact native worker record inventory'): self.verify()

    def test_metadata_fields_are_exact(self):
        original = copy.deepcopy(self.raw)
        for name in ('start.json', 'child.json', 'result.json'):
            self.raw = copy.deepcopy(original)
            self.change(name, lambda r: r.update(promotion_authorized=True))
            with self.subTest(name=name), self.assertRaises(ValueError): self.verify()

    def test_identity_hash_and_time_fields_are_well_formed(self):
        original = copy.deepcopy(self.raw)
        mutations = [('start.json', 'python_sha256', 'g' * 64),
                     ('start.json', 'environment_sha256', 0),
                     ('start.json', 'invocation_id', 'z' * 32),
                     ('child.json', 'observed_at_utc', 'not-a-timestamp'),
                     ('result.json', 'completed_at_utc', '2025-12-31T23:59:59+00:00')]
        for name, key, value in mutations:
            self.raw = copy.deepcopy(original)
            self.change(name, lambda r, k=key, v=value: r.__setitem__(k, v))
            with self.subTest(name=name, key=key), self.assertRaises(ValueError): self.verify()

    def test_boolean_completion_fields_are_not_integer_aliases(self):
        original = copy.deepcopy(self.raw)
        for field, replacement in [('native_wait_completed', 1), ('physical_attestation', 0), ('returncode', False)]:
            self.raw = copy.deepcopy(original)
            self.change('result.json', lambda r, f=field, v=replacement: r.__setitem__(f, v))
            with self.subTest(field=field), self.assertRaises(ValueError): self.verify()

    def test_arbitrary_failure_is_not_completed_native_evidence(self):
        original = copy.deepcopy(self.raw)
        for field, replacement in [('returncode', 2), ('reader_finished', False),
                                   ('killed_by_observer', True), ('sealed', False)]:
            self.raw = copy.deepcopy(original)
            self.change('result.json', lambda r, f=field, v=replacement: r.__setitem__(f, v))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'no completed native worker observation'):
                self.verify()

    def test_fixed_worker_command_cannot_select_another_program(self):
        for name in ('start.json', 'child.json'):
            self.change(name, lambda r: r['command'].__setitem__(-1, '/synthetic/other-worker.py'))
        with self.assertRaisesRegex(ValueError, 'native fixed worker command differs'): self.verify()

    def test_rehashed_stream_substitution_still_rejects(self):
        rows = [load_json_strict(line) for line in self.raw['stdout.jsonl'].splitlines()]
        rows[-1]['response']['fixture'] = 'substituted-result'
        self.raw['stdout.jsonl'] = b''.join(canonical(row) + b'\n' for row in rows)
        self.rehash_streams()
        with self.assertRaisesRegex(ValueError, 'native worker stream differs from sealed evidence'): self.verify()

    def test_native_grant_identity_is_bound(self):
        original = copy.deepcopy(self.raw)
        self.change('start.json', lambda r: r.update(grant_sha256='f' * 64))
        with self.assertRaisesRegex(ValueError, 'native worker grant differs'): self.verify()
        self.raw = original
        rows = [load_json_strict(line) for line in self.raw['stdin.jsonl'].splitlines()]
        rows[0]['grant']['session_index'] = False  # Must not alias the authorized integer zero.
        self.raw['stdin.jsonl'] = b''.join(canonical(row) + b'\n' for row in rows)
        self.rehash_streams()
        with self.assertRaisesRegex(ValueError, 'native worker handshake differs'): self.verify()

    def test_accounting_cannot_be_revealed_before_final_response(self):
        rows = [load_json_strict(line) for line in self.raw['stdout.jsonl'].splitlines()]
        rows[1]['accounting'] = self.accounting
        self.raw['stdout.jsonl'] = b''.join(canonical(row) + b'\n' for row in rows)
        self.rehash_streams()
        with self.assertRaisesRegex(ValueError, 'native worker stream differs from sealed evidence'): self.verify()

    def test_source_bytes_are_rechecked(self):
        (self.root / 'scripts/phase17_campaign_worker.py').write_bytes(b'# Different fixed source.\n')
        with self.assertRaisesRegex(ValueError, 'native worker source changed'): self.verify()

    def test_process_identity_is_consistent_and_separate(self):
        self.change('result.json', lambda r: r.update(child_pid=333))
        with self.assertRaisesRegex(ValueError, 'native worker process identities differ'): self.verify()


if __name__ == '__main__':
    unittest.main()
