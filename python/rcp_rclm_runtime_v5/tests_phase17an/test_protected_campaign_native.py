"""Synthetic AN native parser tests, distinct from actual admitted workers."""
from __future__ import annotations

import copy
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile
import unittest

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import protected_campaign_native as native
from rcp_rclm_runtime_v5.phase17 import protected_authority_isolation as boundary
from rcp_rclm_runtime_v5.phase17.campaign_budget import make_grant
from rcp_rclm_runtime_v5.phase17.controller import FIXED_VERIFIER
from rcp_rclm_runtime_v5.phase17.metered_worker import WORKER_PROTOCOL
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha
from test_protected_authority_isolation import synthetic_specification, synthetic_observation


def synthetic_records(source_root, platform='linux'):
    grant = make_grant({'campaign_id': '1' * 64, 'predecessor_state_hash': '2' * 64,
        'predecessor_package_hash': '3' * 64, 'fixed_verifier_hash': FIXED_VERIFIER,
        'installed_count': 8}, 0, '0' * 64, '4' * 64, 2)
    accounting = {'synthetic_parser_fixture': True, 'spent': [0, 0, 0, 0]}
    events = [{'request': {'op': 'open'}, 'response': {'sequence': 0, 'fixture': 'open'}},
              {'request': {'op': 'seal'}, 'response': {'sequence': 1, 'fixture': 'sealed'}}]
    spec = synthetic_specification('worker', platform=platform)
    RecordedPath = PureWindowsPath if platform == 'win32' else PurePosixPath
    for name in spec['readonly_files']:
        p = RecordedPath(name)
        try:
            relative = p.relative_to(RecordedPath(spec['repo']))
        except ValueError:
            continue
        spec['readonly_files'][name] = sha((source_root / Path(*relative.parts)).read_bytes())
    observation = synthetic_observation(spec)
    command = boundary._prefix(spec)
    start = {'schema': native.SCHEMA, 'invocation_id': 'a' * 32,
        'started_at_utc': '2026-01-01T00:00:00+00:00', 'observer_pid': 111,
        'command': command, 'worker_command': spec['command'], 'isolation_specification': spec,
        'python_path': spec['python_alias'], 'python_sha256': '5' * 64,
        'worker_source_sha256': sha((source_root / 'scripts/phase17_campaign_worker.py').read_bytes()),
        'grant_sha256': sha(canonical(grant)), 'environment_sha256': '6' * 64,
        'shell': False, 'close_fds': True, 'pass_fds': [],
        'observer_is_trusted_reference_launcher': True, 'physical_attestation': False,
        'stdout_capture': 'worker_frames_after_retained_preexec_frame' if platform == 'linux' else 'direct_worker_frames'}
    child = {'schema': native.SCHEMA, 'invocation_id': 'a' * 32,
        'observed_at_utc': '2026-01-01T00:00:01+00:00', 'child_pid': 222, 'launcher_pid': 220,
        'observer_pid': 111, 'command': command, 'cwd': spec['scratch_directory'],
        'worker_identity': {'launcher_pid': 220, 'worker_pid': 222,
            'identity_source': 'trusted_parent_proc_and_preexec_binding',
            'process_start_ticks': None if observation is None else observation['process_start_ticks'],
            'namespaces': None if observation is None else observation['namespaces']},
        'boundary': observation,
        'boundary_frame_hex': (boundary.FRAME_PREFIX + boundary._canonical(observation) + b'\n').hex()}
    if platform == 'win32':
        child.update(launcher_pid=222, boundary=None, boundary_frame_hex='',
            worker_identity={'launcher_pid': 222, 'worker_pid': 222,
                'identity_source': 'direct_native_child', 'process_start_ticks': None, 'namespaces': None})
    inputs = [{'protocol': WORKER_PROTOCOL, 'grant': grant}, *[e['request'] for e in events]]
    outputs = [{'protocol': WORKER_PROTOCOL, 'event': 'grant_received', 'grant_hash': grant['grant_hash']}]
    outputs.extend({'protocol': WORKER_PROTOCOL, 'grant_hash': grant['grant_hash'],
        'response': event['response'], 'accounting': accounting if index == 1 else None}
        for index, event in enumerate(events))
    raw = {'start.json': canonical(start), 'child.json': canonical(child),
        'stdin.jsonl': b''.join(canonical(v) + b'\n' for v in inputs),
        'stdout.jsonl': b''.join(canonical(v) + b'\n' for v in outputs), 'stderr.txt': b''}
    result = {'schema': native.SCHEMA, 'invocation_id': 'a' * 32,
        'completed_at_utc': '2026-01-01T00:00:02+00:00', 'child_pid': 222, 'launcher_pid': 220,
        'native_wait_role': 'launch_process', 'returncode': 0, 'native_wait_completed': True,
        'reader_finished': True, 'killed_by_observer': False, 'capture_failed': False, 'sealed': True,
        'stream_sha256': {n: sha(raw[n]) for n in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')},
        'grant_sha256': start['grant_sha256'], 'physical_attestation': False}
    if platform == 'win32': result['launcher_pid'] = 222
    raw['result.json'] = canonical(result)
    return raw, grant, canonical({'events': events}), accounting


class ProtectedNativeRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name) / 'source'
        for relative in ('scripts/phase17_campaign_worker.py', 'scripts/phase17_protected_isolation_probe.py',
                         'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_isolation.py'):
            p = self.root / relative; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'# Synthetic source binding only.\n')
        self.raw, self.grant, self.transcript, self.accounting = synthetic_records(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def change(self, name, function):
        value = load_json_strict(self.raw[name]); function(value); self.raw[name] = canonical(value)

    def verify(self):
        return native.verify_native_images(self.raw, self.grant, self.transcript, self.accounting, source_root=self.root)

    def test_synthetic_image_fixture_is_not_native_execution(self):
        self.assertEqual(self.verify(), {name: sha(raw) for name, raw in self.raw.items()})

    def test_exact_six_original_images_required(self):
        self.raw['unexpected.json'] = b'{}'
        with self.assertRaises(ValueError): self.verify()

    def test_old_al_schema_cannot_claim_new_execution(self):
        self.change('start.json', lambda v: v.update(schema='rcp-rclm.phase17al.worker-native.v1'))
        with self.assertRaises(ValueError): self.verify()

    def test_original_launcher_cannot_be_replaced_with_worker_command(self):
        self.change('start.json', lambda v: v.update(command=v['worker_command']))
        with self.assertRaises(ValueError): self.verify()

    def test_boundary_cannot_be_added_after_original_capture(self):
        self.change('child.json', lambda v: v.update(boundary_frame_hex=''))
        with self.assertRaises(ValueError): self.verify()

    def test_supervisor_and_actual_worker_pids_are_separately_bound(self):
        self.change('child.json', lambda v: v.update(child_pid=v['launcher_pid']))
        with self.assertRaises(ValueError): self.verify()

    def test_parent_observed_start_ticks_bind_preexec_target(self):
        self.change('child.json', lambda v: v['worker_identity'].update(process_start_ticks=999))
        with self.assertRaises(ValueError): self.verify()

    def test_parent_observed_namespaces_bind_preexec_target(self):
        self.change('child.json', lambda v: v['worker_identity']['namespaces'].update(net='net:[300]'))
        with self.assertRaises(ValueError): self.verify()

    def test_missing_native_wait_is_not_completion(self):
        self.change('result.json', lambda v: v.update(native_wait_completed=False))
        with self.assertRaises(ValueError): self.verify()

    def test_arbitrary_failure_is_not_semantic_acceptance(self):
        self.change('result.json', lambda v: v.update(returncode=1))
        with self.assertRaises(ValueError): self.verify()

    def test_boolean_zero_is_not_return_code_zero(self):
        self.change('result.json', lambda v: v.update(returncode=False))
        with self.assertRaises(ValueError): self.verify()

    def test_unapproved_physical_attestation_is_rejected(self):
        self.change('result.json', lambda v: v.update(physical_attestation=True))
        with self.assertRaises(ValueError): self.verify()

    def test_native_grant_substitution_is_rejected(self):
        self.change('start.json', lambda v: v.update(grant_sha256='f' * 64))
        with self.assertRaises(ValueError): self.verify()

    def test_rehashed_stream_still_must_equal_sealed_semantics(self):
        lines = [load_json_strict(v) for v in self.raw['stdout.jsonl'].splitlines()]
        lines[-1]['response']['fixture'] = 'substituted'
        self.raw['stdout.jsonl'] = b''.join(canonical(v) + b'\n' for v in lines)
        self.change('result.json', lambda v: v['stream_sha256'].update({'stdout.jsonl': sha(self.raw['stdout.jsonl'])}))
        with self.assertRaises(ValueError): self.verify()

    def test_source_binding_covers_actual_wrapper(self):
        (self.root / 'scripts/phase17_protected_isolation_probe.py').write_bytes(b'# Changed wrapper.\n')
        with self.assertRaises(ValueError): self.verify()

    def test_python_image_join_cannot_disagree(self):
        self.change('start.json', lambda v: v.update(python_sha256='e' * 64))
        with self.assertRaises(ValueError): self.verify()

    def test_filesystem_reader_wraps_the_same_pure_image_validator(self):
        directory = Path(self.tmp.name) / 'native'; directory.mkdir()
        for name, raw in self.raw.items(): (directory / name).write_bytes(raw)
        self.assertEqual(native.verify_native_records(directory, self.grant, self.transcript,
            self.accounting, source_root=self.root), self.verify())

    def test_windows_reference_native_images_validate_without_linux_credit(self):
        self.raw, self.grant, self.transcript, self.accounting = synthetic_records(self.root, 'win32')
        self.assertEqual(self.verify(), {name: sha(raw) for name, raw in self.raw.items()})
        self.assertIsNone(load_json_strict(self.raw['child.json'])['boundary'])

    def test_windows_reference_rejects_borrowed_linux_boundary(self):
        linux = load_json_strict(self.raw['child.json'])['boundary']
        self.raw, self.grant, self.transcript, self.accounting = synthetic_records(self.root, 'win32')
        self.change('child.json', lambda v: v.update(boundary=linux))
        with self.assertRaises(ValueError): self.verify()


if __name__ == '__main__':
    unittest.main()
