"""Original native-evidence binding controls, using labeled parser fixtures.

These synthetic process records are not an execution or Lean acceptance claim.
They test exact framing/attribution refusals; fresh capture is a separate gate.
"""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from rcp_rclm_runtime_v5.phase17 import controller_durable_capture as capture


class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'native'; self.here = self.directory / 'case-0'
        self.here.mkdir(parents=True)
        self.cursor = {'serial': 0, 'controlled_fixture': True}
        self.request = {'controlled_fixture': 'request'}
        self.response = {'cursor': self.cursor, 'controlled_fixture': 'response'}
        self.evidence = {'events': [{'controlled_fixture': 'committed-image'}],
                         'final_cursor': self.cursor, 'controlled_fixture': True}
        self.boot = {'name': 'case-0', 'case': 'case', 'boot_nonce': '1'*64,
                     'root_provision_sha256': '2'*64,
                     'request_sha256': [capture.sha(capture.canonical(self.request) + b'\n')],
                     'response_sha256': [capture.sha(capture.canonical(self.response) + b'\n')]}
        identity = {'controlled_fixture': 'implementation'}
        self.packet = {'schema': capture.SCHEMA, 'base_commit': capture.BASE,
                      'native_boots': [self.boot], 'durable_identity': identity,
                      'durable_cases': [{'name': 'case', 'evidence': self.evidence,
                        'wire': [{'boot': 'case-0', 'request': self.request, 'response': self.response}]}]}
        self.start = {'schema': 'phase17ak.durable-native-start.v1', 'invocation_id': 'a'*32,
            'source_root': '/controlled/source', 'authority_directory': '/controlled/root',
            'execution_directory': '/controlled/execution', 'export_path': '/controlled/export.json',
            'root_provision_sha256': '2'*64, 'boot_nonce': '1'*64,
            'aj_packet_sha256': capture.AJ_PACKET_SHA, 'durable_identity': identity,
            'python_sha256': '3'*64, 'started_at_utc': '2026-01-01T00:00:00+00:00'}
        self.start['argv'] = capture._argv('/controlled/python', self.start['source_root'],
            self.start['authority_directory'], self.start['execution_directory'],
            self.start['export_path'], '2'*64, '1'*64)
        self.images = {'stdin.bin': capture.canonical(self.request) + b'\n',
                       'stdout.bin': capture.canonical(self.response) + b'\n', 'stderr.bin': b'',
                       'export.json': capture.canonical(self.evidence)}
        for name, raw in self.images.items():
            (self.here / name).write_bytes(raw)
        self.result = {'schema': 'phase17ak.durable-native-result.v1', 'invocation_id': 'a'*32,
            'pid': 123, 'started_at_utc': self.start['started_at_utc'],
            'finished_at_utc': '2026-01-01T00:00:01+00:00', 'elapsed_ns': 1000000000,
            'returncode': 0, 'timed_out': False, 'native_wait_completed': True,
            'reader_finished': True, 'reader_error': None,
            'start_sha256': capture.sha(capture.canonical(self.start)),
            'export': {'bytes': len(self.images['export.json']), 'sha256': capture.sha(self.images['export.json'])},
            'streams': {name: {'bytes': len(self.images[name]), 'sha256': capture.sha(self.images[name])}
                        for name in ('stdin.bin','stdout.bin','stderr.bin')}}
        self.write_metadata()

    def write_metadata(self):
        (self.here / 'start.json').write_bytes(capture.canonical(self.start))
        self.result['start_sha256'] = capture.sha(capture.canonical(self.start))
        (self.here / 'native-result.json').write_bytes(capture.canonical(self.result))

    def verify(self):
        return capture.verify_durable_native_records(self.directory, self.packet)

    def test_exact_controlled_original_inventory(self):
        self.assertEqual(len(self.verify()), 6)

    def test_original_stdout_tamper_refused(self):
        (self.here / 'stdout.bin').write_bytes(b'other\n')
        with self.assertRaisesRegex(ValueError, 'wire differs'):
            self.verify()

    def test_original_export_tamper_refused(self):
        (self.here / 'export.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'root export differs'):
            self.verify()

    def test_export_hash_tamper_refused(self):
        self.result['export']['sha256'] = '0'*64; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'export identity differs'):
            self.verify()

    def test_unobserved_native_completion_refused(self):
        self.result['native_wait_completed'] = False; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'observed completion'):
            self.verify()

    def test_nonzero_native_exit_refused(self):
        self.result['returncode'] = 73; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'observed completion'):
            self.verify()

    def test_boolean_native_exit_refused(self):
        self.result['returncode'] = False; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'observed completion'):
            self.verify()

    def test_empty_native_command_refused(self):
        self.start['argv'] = []; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'command differs'):
            self.verify()

    def test_another_native_module_refused(self):
        self.start['argv'][3] = 'untrusted'; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'command differs'):
            self.verify()

    def test_nonhex_interpreter_identity_refused(self):
        self.start['python_sha256'] = 'z'*64; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'interpreter identity'):
            self.verify()

    def test_another_root_provision_refused(self):
        self.start['root_provision_sha256'] = '9'*64; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'provision differs'):
            self.verify()

    def test_extra_native_file_refused(self):
        (self.here / 'invented.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            self.verify()

    def test_missing_native_export_refused(self):
        (self.here / 'export.json').unlink()
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            self.verify()

    def test_native_export_cannot_include_unobserved_future_event(self):
        changed = dict(self.evidence, events=self.evidence['events'] + [{'controlled_fixture': 'future'}])
        raw = capture.canonical(changed); (self.here / 'export.json').write_bytes(raw)
        self.result['export'] = {'bytes': len(raw), 'sha256': capture.sha(raw)}; self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'root export differs'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
