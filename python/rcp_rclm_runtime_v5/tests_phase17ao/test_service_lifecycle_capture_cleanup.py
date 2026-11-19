"""Owned-process cleanup regressions with controlled real Python children.

The children emit tiny protocol fixtures and wait on their inherited pipe. They
are neither authorities nor task workers and establish no campaign acceptance.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import service_lifecycle_capture as capture

ROOT = Path(__file__).resolve().parents[3]
REAL_POPEN = subprocess.Popen


class OriginalFailure(RuntimeError):
    pass


class ControlledLedger:
    cursor = {'fixture': 'synthetic-closeout-boundary'}

    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.charges = []

    def charge(self, grant, delta, *, event_id, expected_cursor, evidence_sha256):
        self.charges.append(event_id)
        if event_id == self.fail_on:
            raise OriginalFailure('original ledger failure: ' + event_id)


class NativeResidentCleanupTests(unittest.TestCase):
    def setUp(self):
        parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self.directory = tempfile.TemporaryDirectory(prefix='rcp-phase17ao-cleanup-', dir=str(parent))
        self.base = Path(self.directory.name)
        self.children = []
        self.instances = []

    def tearDown(self):
        for resident in self.instances:
            if not resident.closed:
                resident.abort()
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
            for stream in (child.stdin, child.stdout):
                if stream is not None and not stream.closed:
                    stream.close()
        self.directory.cleanup()

    def start(self, *, bad_ready=False, stop_frame=False, exit_code=0,
              fail_on=None, fail_write=None):
        config = {'lifetime_id': 'synthetic-cleanup-fixture',
            'limits': {'max_response_bytes': 65536},
            'lifecycle_evidence': {'scope': 'synthetic-nonnative-prepaid-prefix'}}
        grant = {'grant_sha256': capture.sha(b'synthetic-cleanup-grant')}
        pin = capture.sha(capture.canonical(config))
        ready_pin = capture.sha(b'wrong-ready-config') if bad_ready else pin
        body = f'''
import json, os, sys
# Exercise Windows text translation on every host; protocol frames use bytes.
sys.stdout.reconfigure(newline='\\r\\n')
def emit(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\\n'
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()
emit({{'schema': {capture.resident_api.READY_SCHEMA!r}, 'pid': os.getpid(),
      'parent_pid': os.getppid(), 'config_sha256': {ready_pin!r},
      'grant_sha256': {grant['grant_sha256']!r}}})
if {stop_frame!r}:
    emit({{'schema': {capture.resident_api.STOPPED_SCHEMA!r},
          'pid': os.getpid(), 'completed': True}})
sys.stdin.buffer.read()
raise SystemExit({exit_code})
'''
        def spawn(command, **kwargs):
            child = REAL_POPEN([sys.executable, '-u', '-c', body], **kwargs)
            self.children.append(child)
            return child
        original_write = capture._write
        def write(path, raw):
            if Path(path).name == fail_write:
                raise OSError('secondary fixture write failure: ' + fail_write)
            return original_write(path, raw)
        outer = self
        class ObservedResident(capture.NativeResident):
            def __init__(self, *args, **kwargs):
                outer.instances.append(self)
                super().__init__(*args, **kwargs)
        ledger = ControlledLedger(fail_on)
        with patch.object(capture.subprocess, 'Popen', side_effect=spawn), \
                patch.object(capture, '_write', side_effect=write):
            return ObservedResident(ROOT, self.base / 'native', self.base / 'config.json', config, ledger, grant)

    def assert_reaped(self, resident):
        self.assertTrue(resident.closed)
        self.assertIsNotNone(resident.process.returncode)
        self.assertIsNotNone(resident.process.poll())
        self.assertTrue(resident._thread is None or not resident._thread.is_alive())
        for stream in (resident.process.stdin, resident.process.stdout,
                       resident._input, resident._output, resident._error):
            self.assertTrue(stream.closed)

    def assert_failed_record(self, resident):
        record = load_json_strict((resident.native / 'failure.json').read_bytes(), require_canonical=True)
        self.assertFalse(record['completed'])
        self.assertFalse(record['reservation_refunded'])
        self.assertFalse(record['automatic_takeover_permitted'])
        self.assertTrue(record['native_wait_completed'])
        self.assertTrue(record['reader_finished'])
        self.assertTrue(record['streams_closed'])

    def test_readiness_rejection_reaps_child_when_constructor_never_returns(self):
        with self.assertRaisesRegex(ValueError, 'resident readiness differs from prepaid child'):
            self.start(bad_ready=True)
        resident = self.instances[-1]
        self.assert_reaped(resident)
        self.assert_failed_record(resident)
        self.assertFalse((resident.native / 'result.json').exists())

    def test_ready_charge_failure_preserves_original_failure_and_reaps_child(self):
        with self.assertRaisesRegex(OriginalFailure, 'original ledger failure: resident-ready'):
            self.start(fail_on='resident-ready')
        resident = self.instances[-1]
        self.assert_reaped(resident)
        self.assert_failed_record(resident)
        self.assertEqual(resident.ledger.charges, ['resident-ready'])

    def test_post_popen_observation_failure_cleans_up_before_reader_exists(self):
        with self.assertRaisesRegex(OSError, 'secondary fixture write failure: child.json'):
            self.start(fail_write='child.json')
        resident = self.instances[-1]
        self.assertIsNone(resident._thread)
        self.assert_reaped(resident)
        self.assert_failed_record(resident)

    def test_stopped_charge_failure_keeps_finally_cleanup_enabled(self):
        resident = self.start(stop_frame=True, fail_on='resident-stopped')
        with self.assertRaisesRegex(OriginalFailure, 'original ledger failure: resident-stopped'):
            try:
                resident.close()
            finally:
                if not resident.closed:
                    resident.abort()
        self.assert_reaped(resident)
        self.assert_failed_record(resident)
        self.assertFalse((resident.native / 'result.json').exists())

    def test_nonzero_child_exit_is_retained_as_failure_after_real_wait(self):
        resident = self.start(stop_frame=True, exit_code=7)
        with self.assertRaisesRegex(ValueError, 'resident native lifetime did not complete'):
            try:
                resident.close()
            finally:
                if not resident.closed:
                    resident.abort()
        self.assert_reaped(resident)
        self.assert_failed_record(resident)
        result = load_json_strict((resident.native / 'result.json').read_bytes(), require_canonical=True)
        self.assertEqual(result['returncode'], 7)
        self.assertTrue(result['native_wait_completed'])

    def test_cleanup_record_failure_cannot_mask_primary_error_or_leak_child(self):
        with self.assertRaisesRegex(OriginalFailure, 'original ledger failure: resident-ready'):
            self.start(fail_on='resident-ready', fail_write='failure.json')
        resident = self.instances[-1]
        self.assert_reaped(resident)
        self.assertFalse((resident.native / 'result.json').exists())
        self.assertIsNone(resident.abort())


if __name__ == '__main__':
    unittest.main()
