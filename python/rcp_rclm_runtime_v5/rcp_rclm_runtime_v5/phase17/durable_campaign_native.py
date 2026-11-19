"""Original native records for the fixed Phase17O worker admitted by AL.

The observation is made by the trusted reference launcher. It is evidence of a
completed local process, not remote attestation or isolation from the same UID.
No recorded bytes are synthesized from a reconstructed transcript.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import uuid

from rcp_rclm_runtime.canonical.json import load_json_strict
from .campaign_client import CampaignEvaluatorClient
from .campaign_budget import validate_grant
from .challenge_client import worker_environment
from .challenge_protocol import MAX_WIRE_BYTES, parse_wire, wire_bytes, require
from .resource_ledger import canonical, sha, _no_links, exact
from .metered_worker import WORKER_PROTOCOL

SCHEMA = 'rcp-rclm.phase17al.worker-native.v1'
FILES = ('start.json', 'child.json', 'stdin.jsonl', 'stdout.jsonl', 'stderr.txt', 'result.json')
MAX_CAPTURE_BYTES = 32 * 1024 * 1024


def _hash(value, length=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None,
            'exact native hexadecimal identity required')
    return value


def _pid(value):
    require(type(value) is int and 0 < value < 2**63, 'exact positive native process identity required')
    return value


def _stamp(value):
    require(type(value) is str, 'native UTC timestamp required')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError('invalid native UTC timestamp') from error
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
            'native timestamp is not UTC')
    return parsed


def _now():
    return datetime.now(timezone.utc).isoformat()


def _new(path, raw):
    _no_links(path)
    with path.open('xb') as handle:
        require(handle.write(raw) == len(raw), 'short native record write')
        handle.flush()
        os.fsync(handle.fileno())


class RecordedCampaignEvaluatorClient(CampaignEvaluatorClient):
    """Use the unchanged worker protocol while retaining its original streams."""

    def __init__(self, grant, *, native_directory, response_timeout=30.0):
        self.native_directory = Path(native_directory).absolute()
        _no_links(self.native_directory)
        require(not self.native_directory.exists(), 'new worker native directory required')
        self.native_directory.mkdir(parents=True)
        self._native_id = uuid.uuid4().hex
        self._native_result = None
        self._native_failed = False
        self._native_child_written = False
        self._native_input = self.native_directory.joinpath('stdin.jsonl').open('xb')
        self._native_output = self.native_directory.joinpath('stdout.jsonl').open('xb')
        root = Path(__file__).resolve().parents[4]
        self._fixed_script = root / 'scripts/phase17_campaign_worker.py'
        self._fixed_command = [sys.executable, '-I', '-S', '-B', '-u', str(self._fixed_script)]
        self._native_start = {
            'schema': SCHEMA, 'invocation_id': self._native_id, 'started_at_utc': _now(),
            'observer_pid': os.getpid(), 'command': self._fixed_command,
            'python_path': sys.executable, 'python_sha256': sha(Path(sys.executable).read_bytes()),
            'worker_source_sha256': sha(self._fixed_script.read_bytes()),
            'grant_sha256': sha(canonical(validate_grant(grant))),
            'environment_sha256': sha(canonical(worker_environment())),
            'shell': False, 'close_fds': True,
            'observer_is_trusted_reference_launcher': True, 'physical_attestation': False,
        }
        _new(self.native_directory / 'start.json', canonical(self._native_start))
        try:
            super().__init__(grant, response_timeout=response_timeout)
        except BaseException:
            self._native_failed = True
            if not getattr(self, 'closed', True):
                self.close()
            for handle in (self._native_input, self._native_output):
                if not handle.closed:
                    handle.close()
            raise

    def _write(self, value):
        if not self._native_child_written:
            require(self.process.args == self._fixed_command, 'worker command changed')
            _new(self.native_directory / 'child.json', canonical({
                'schema': SCHEMA, 'invocation_id': self._native_id,
                'observed_at_utc': _now(), 'child_pid': self.process.pid,
                'observer_pid': os.getpid(), 'command': self.process.args,
                'cwd': self._directory.name,
            }))
            self._native_child_written = True
        raw = wire_bytes(value) + b'\n'
        require(self.process.stdin.write(raw) == len(raw), 'short worker input write')
        self.process.stdin.flush()
        require(self._native_input.write(raw) == len(raw), 'short native input capture')
        self._native_input.flush()

    def _read(self):
        try:
            while True:
                raw = self.process.stdout.readline(MAX_WIRE_BYTES + 2)
                if raw:
                    require(self._native_output.tell() + len(raw) <= MAX_CAPTURE_BYTES,
                            'native output exceeds capture profile')
                    require(self._native_output.write(raw) == len(raw), 'short native output capture')
                    self._native_output.flush()
                self._responses.put(raw if raw else None, timeout=1)
                if not raw or len(raw) > MAX_WIRE_BYTES + 1:
                    return
        except (OSError, ValueError, queue.Full):
            self._native_failed = True

    def close(self):
        if getattr(self, 'closed', False):
            return
        self.closed = True
        native_wait, killed, reader_finished = False, False, False
        result = None
        try:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.kill()
                    killed = True
                result = self.process.wait(timeout=10)
                native_wait = True
                if self._reader is not None:
                    self._reader.join(timeout=2)
                    reader_finished = not self._reader.is_alive()
                for pipe in (self.process.stdin, self.process.stdout):
                    if pipe is not None and not pipe.closed:
                        pipe.close()
            self._stderr.seek(0)
            error = self._stderr.read(MAX_CAPTURE_BYTES + 1)
            require(len(error) <= MAX_CAPTURE_BYTES, 'native stderr exceeds capture profile')
            _new(self.native_directory / 'stderr.txt', error)
            for handle in (self._native_input, self._native_output):
                if not handle.closed:
                    handle.flush()
                    os.fsync(handle.fileno())
                    handle.close()
            self._native_result = {
                'schema': SCHEMA, 'invocation_id': self._native_id, 'completed_at_utc': _now(),
                'child_pid': None if self.process is None else self.process.pid,
                'returncode': result, 'native_wait_completed': native_wait,
                'reader_finished': reader_finished, 'killed_by_observer': killed,
                'capture_failed': self._native_failed, 'sealed': self.sealed,
                'stream_sha256': {name: sha((self.native_directory / name).read_bytes())
                                  for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')},
                'grant_sha256': self._native_start['grant_sha256'],
                'physical_attestation': False,
            }
            _new(self.native_directory / 'result.json', canonical(self._native_result))
        finally:
            self._stderr.close()
            self._directory.cleanup()

    def evidence(self):
        require(self.closed and self._native_result is not None, 'worker observation unfinished')
        require(self._native_result['native_wait_completed'] is True and
                self._native_result['reader_finished'] is True and
                self._native_result['returncode'] == 0 and self._native_result['sealed'] is True and
                self._native_result['killed_by_observer'] is False and
                self._native_result['capture_failed'] is False,
                'worker native observation did not complete cleanly')
        return {name: (self.native_directory / name).read_bytes() for name in FILES}


def verify_native_records(directory, grant, transcript, accounting, *, source_root=None):
    """Check original records against sealed semantics; start no process."""
    directory = Path(directory)
    _no_links(directory)
    require(directory.is_dir() and {p.name for p in directory.iterdir()} == set(FILES),
            'exact native worker record inventory required')
    raw = {}
    for name in FILES:
        path = directory / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_CAPTURE_BYTES, 'invalid native worker file')
        raw[name] = path.read_bytes()
    start, child, result = [load_json_strict(raw[name], require_canonical=True)
                            for name in ('start.json', 'child.json', 'result.json')]
    exact(start, {'schema', 'invocation_id', 'started_at_utc', 'observer_pid', 'command',
        'python_path', 'python_sha256', 'worker_source_sha256', 'grant_sha256',
        'environment_sha256', 'shell', 'close_fds', 'observer_is_trusted_reference_launcher',
        'physical_attestation'})
    exact(child, {'schema', 'invocation_id', 'observed_at_utc', 'child_pid', 'observer_pid', 'command', 'cwd'})
    exact(result, {'schema', 'invocation_id', 'completed_at_utc', 'child_pid', 'returncode',
        'native_wait_completed', 'reader_finished', 'killed_by_observer', 'capture_failed',
        'sealed', 'stream_sha256', 'grant_sha256', 'physical_attestation'})
    for value in (start, child, result):
        _hash(value['invocation_id'], 32)
    for key in ('python_sha256', 'worker_source_sha256', 'grant_sha256', 'environment_sha256'):
        _hash(start[key])
    _hash(result['grant_sha256'])
    exact(result['stream_sha256'], {'stdin.jsonl', 'stdout.jsonl', 'stderr.txt'})
    for value in result['stream_sha256'].values():
        _hash(value)
    require(_stamp(start['started_at_utc']) <= _stamp(child['observed_at_utc']) <=
            _stamp(result['completed_at_utc']), 'native worker observation timestamps out of order')
    for value in (start['observer_pid'], child['observer_pid'], child['child_pid'], result['child_pid']):
        _pid(value)
    require(type(child['cwd']) is str and child['cwd'] and
            type(start['python_path']) is str and start['python_path'], 'native process path missing')
    require(all(value.get('schema') == SCHEMA for value in (start, child, result)), 'native schema differs')
    require(type(start['invocation_id']) is str and len(start['invocation_id']) == 32 and
            start['invocation_id'] == child['invocation_id'] == result['invocation_id'],
            'native invocation identities differ')
    require(type(child['child_pid']) is int and type(child['observer_pid']) is int and
            child['child_pid'] > 0 and child['observer_pid'] > 0 and
            child['child_pid'] != child['observer_pid'] and
            child['child_pid'] == result['child_pid'] and child['observer_pid'] == start['observer_pid'],
            'native worker process identities differ')
    command = start['command']
    require(type(command) is list and len(command) == 6 and all(type(arg) is str and arg for arg in command) and
            command[0] == start['python_path'] and command[1:5] == ['-I', '-S', '-B', '-u'] and
            command[-1].replace('\\', '/').endswith('/scripts/phase17_campaign_worker.py') and
            command == child['command'] and start['shell'] is False and start['close_fds'] is True,
            'native fixed worker command differs')
    require(start['observer_is_trusted_reference_launcher'] is True and
            start['physical_attestation'] is False and result['physical_attestation'] is False,
            'native worker trust scope changed')
    require(type(result['returncode']) is int and result['returncode'] == 0 and
            all(result[name] is True for name in ('native_wait_completed', 'reader_finished', 'sealed')) and
            all(result[name] is False for name in ('killed_by_observer', 'capture_failed')),
            'no completed native worker observation')
    require(result['stream_sha256'] == {name: sha(raw[name]) for name in
            ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')} and raw['stderr.txt'] == b'',
            'native worker stream identity or diagnostic mismatch')
    require(start['grant_sha256'] == result['grant_sha256'] == sha(canonical(validate_grant(grant))),
            'native worker grant differs')
    if source_root is not None:
        require(start['worker_source_sha256'] == sha((Path(source_root) /
                'scripts/phase17_campaign_worker.py').read_bytes()), 'native worker source changed')
    inputs = [parse_wire(line) for line in raw['stdin.jsonl'].splitlines()]
    outputs = [parse_wire(line) for line in raw['stdout.jsonl'].splitlines()]
    require(raw['stdin.jsonl'] == b''.join(wire_bytes(row) + b'\n' for row in inputs) and
            raw['stdout.jsonl'] == b''.join(wire_bytes(row) + b'\n' for row in outputs),
            'native wire framing differs')
    events = load_json_strict(transcript)['events']
    require(len(inputs) == len(outputs) == len(events) + 1 and wire_bytes(inputs[0]) ==
            wire_bytes({'protocol': WORKER_PROTOCOL, 'grant': grant}) and wire_bytes(outputs[0]) ==
            wire_bytes({'protocol': WORKER_PROTOCOL, 'event': 'grant_received', 'grant_hash': grant['grant_hash']}),
            'native worker handshake differs')
    for index, event in enumerate(events, 1):
        expected = {'protocol': WORKER_PROTOCOL, 'grant_hash': grant['grant_hash'],
                    'response': event['response'],
                    'accounting': accounting if index == len(events) else None}
        require(wire_bytes(inputs[index]) == wire_bytes(event['request']) and
                wire_bytes(outputs[index]) == wire_bytes(expected),
                'native worker stream differs from sealed evidence')
    return {name: sha(value) for name, value in raw.items()}
