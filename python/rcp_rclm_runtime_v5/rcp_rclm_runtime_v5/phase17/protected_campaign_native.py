"""AN native records for the actual fixed worker, with honest launcher identity.

The AL six-file binding is retained, but these records use a new AN schema.
Linux's first original stdout frame is the trusted pre-exec observation stored
in child.json; stdout.jsonl contains the subsequent worker protocol frames.
The bwrap supervisor PID and actual worker PID are recorded separately.
"""
from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import uuid

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import protected_authority_isolation as isolation
from .campaign_client import CampaignEvaluatorClient
from .campaign_budget import validate_grant
from .challenge_client import worker_environment
from .challenge_protocol import MAX_WIRE_BYTES, parse_wire, wire_bytes, require
from .resource_ledger import canonical, sha, _no_links, exact
from .metered_worker import WORKER_PROTOCOL
from .durable_campaign_native import FILES, MAX_CAPTURE_BYTES, _hash, _pid, _stamp, _now, _new

SCHEMA = 'rcp-rclm.phase17an.protected-worker-native.v1'


def observe_worker_identity(launcher_pid, boundary):
    """Read direct-child proc identity while the fixed worker awaits its grant."""
    if boundary is None:
        return {'launcher_pid': launcher_pid, 'worker_pid': launcher_pid,
                'identity_source': 'direct_native_child', 'process_start_ticks': None,
                'namespaces': None}
    candidates = [launcher_pid]
    # /proc/PID/task/PID/children is absent on kernels without checkpoint/restore
    # support. A bounded status scan observes the same direct-child relation.
    entries = [p for p in Path('/proc').iterdir() if p.name.isdigit()]
    require(len(entries) <= 4096, 'process identity observation exceeds its bound')
    children = []
    for path in entries:
        try:
            status = dict(line.split(':', 1) for line in (path / 'status').read_text().splitlines() if ':' in line)
            if int(status['PPid'].strip()) == launcher_pid:
                children.append(int(path.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    require(len(children) <= 4, 'unexpected protected launcher process fanout')
    candidates.extend(children)
    found = []
    for pid in candidates:
        try:
            fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
            namespaces = {name: os.readlink('/proc/' + str(pid) + '/ns/' + name)
                          for name in isolation.PRIVATE_NAMESPACES}
            if int(fields[19]) == boundary['process_start_ticks'] and namespaces == boundary['namespaces']:
                found.append(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    require(len(found) == 1, 'actual protected worker process identity is ambiguous')
    return {'launcher_pid': launcher_pid, 'worker_pid': found[0],
            'identity_source': 'trusted_parent_proc_and_preexec_binding',
            'process_start_ticks': boundary['process_start_ticks'], 'namespaces': boundary['namespaces']}


class ProtectedCampaignEvaluatorClient(CampaignEvaluatorClient):
    """Reuse the fixed metered wire protocol with an additive protected launcher."""

    def __init__(self, grant, *, native_directory, protected_paths, response_timeout=30.0):
        require(type(response_timeout) in (int, float) and 0 < response_timeout <= 120,
                'response timeout outside bounded profile')
        self.grant = validate_grant(grant); self.timeout = response_timeout
        self.events = []; self.previous = '0' * 64
        self.closed = False; self.sealed = False; self.accounting = None
        self.process = None; self._reader = None; self.worker_pid = None
        self.native_directory = Path(native_directory).absolute(); _no_links(self.native_directory)
        require(not self.native_directory.exists(), 'new protected worker native directory required')
        self.native_directory.mkdir(parents=True)
        # Windows TEMP may name the existing parent through a valid 8.3 alias.
        # Allocate our owned scratch under its strict canonical spelling so
        # the unchanged no-alias/no-link launch guard can still be enforced.
        temporary_parent = Path(tempfile.gettempdir()).resolve(strict=True)
        self._directory = tempfile.TemporaryDirectory(
            prefix='rcp-phase17an-worker-', dir=str(temporary_parent))
        self._stderr = tempfile.TemporaryFile()
        self._responses = queue.Queue(maxsize=2)
        self._boundary_ready = threading.Event(); self._boundary = None; self._boundary_frame = b''
        self._native_id = uuid.uuid4().hex; self._native_result = None; self._native_failed = False
        self._native_input = (self.native_directory / 'stdin.jsonl').open('xb')
        self._native_output = (self.native_directory / 'stdout.jsonl').open('xb')
        root = Path(__file__).resolve().parents[4]
        self._fixed_script = root / 'scripts/phase17_campaign_worker.py'
        self._worker_command = [sys.executable, '-I', '-S', '-B', '-u', str(self._fixed_script)]
        try:
            self._fixed_command, self._specification = isolation.build_command(root, self._worker_command,
                Path(self._directory.name), protected_paths, 'worker')
        except BaseException:
            self._native_input.close(); self._native_output.close()
            self._stderr.close(); self._directory.cleanup()
            self.closed = True
            raise
        self._native_start = {'schema': SCHEMA, 'invocation_id': self._native_id,
            'started_at_utc': _now(), 'observer_pid': os.getpid(), 'command': self._fixed_command,
            'worker_command': self._worker_command, 'isolation_specification': self._specification,
            'python_path': sys.executable, 'python_sha256': sha(Path(sys.executable).read_bytes()),
            'worker_source_sha256': sha(self._fixed_script.read_bytes()),
            'grant_sha256': sha(canonical(self.grant)),
            'environment_sha256': sha(canonical(worker_environment())),
            'shell': False, 'close_fds': True, 'pass_fds': [],
            'observer_is_trusted_reference_launcher': True, 'physical_attestation': False,
            'stdout_capture': 'worker_frames_after_retained_preexec_frame' if sys.platform == 'linux'
                              else 'direct_worker_frames'}
        _new(self.native_directory / 'start.json', canonical(self._native_start))
        try:
            self.process = subprocess.Popen(self._fixed_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self._stderr, cwd=self._directory.name, env=worker_environment(),
                shell=False, close_fds=True)
            self._reader = threading.Thread(target=self._read, daemon=True); self._reader.start()
            require(self._boundary_ready.wait(timeout=self.timeout), 'protected boundary observation timed out')
            require(not self._native_failed, 'protected pre-exec boundary failed')
            isolation.validate_observation(self._specification, self._boundary)
            identity = observe_worker_identity(self.process.pid, self._boundary)
            self.worker_pid = identity['worker_pid']
            _new(self.native_directory / 'child.json', canonical({'schema': SCHEMA,
                'invocation_id': self._native_id, 'observed_at_utc': _now(),
                'child_pid': self.worker_pid, 'launcher_pid': self.process.pid, 'observer_pid': os.getpid(),
                'command': self.process.args, 'cwd': self._directory.name,
                'worker_identity': identity, 'boundary': self._boundary,
                'boundary_frame_hex': self._boundary_frame.hex()}))
            self._write({'protocol': WORKER_PROTOCOL, 'grant': self.grant})
            ack = self._receive()
            require(ack == {'protocol': WORKER_PROTOCOL, 'event': 'grant_received',
                            'grant_hash': self.grant['grant_hash']}, 'protected worker grant substitution')
        except BaseException:
            self._native_failed = True; self.close(); raise

    def _write(self, value):
        raw = wire_bytes(value) + b'\n'
        require(self.process.stdin.write(raw) == len(raw), 'short protected worker input write')
        self.process.stdin.flush()
        require(self._native_input.write(raw) == len(raw), 'short protected native input capture')
        self._native_input.flush()

    def _read(self):
        try:
            if self._specification['profile']['platform'] == 'linux':
                raw = self.process.stdout.readline(isolation.MAX_BOUNDARY_BYTES + 1)
                self._boundary_frame = raw
                self._boundary = isolation.parse_boundary_frame(raw)
                isolation.validate_observation(self._specification, self._boundary)
            self._boundary_ready.set()
            while True:
                raw = self.process.stdout.readline(MAX_WIRE_BYTES + 2)
                if raw:
                    require(self._native_output.tell() + len(raw) <= MAX_CAPTURE_BYTES,
                            'protected worker output exceeds capture profile')
                    require(self._native_output.write(raw) == len(raw), 'short protected native output capture')
                    self._native_output.flush()
                self._responses.put(raw if raw else None, timeout=1)
                if not raw or len(raw) > MAX_WIRE_BYTES + 1:
                    return
        except (OSError, ValueError, queue.Full, TypeError, KeyError):
            self._native_failed = True
        finally:
            self._boundary_ready.set()

    def close(self):
        if self.closed:
            return
        self.closed = True
        native_wait = killed = reader_finished = False
        result = None
        try:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.kill(); killed = True
                result = self.process.wait(timeout=10); native_wait = True
                if self._reader is not None:
                    self._reader.join(timeout=2); reader_finished = not self._reader.is_alive()
                for pipe in (self.process.stdin, self.process.stdout):
                    if pipe is not None and not pipe.closed: pipe.close()
            self._stderr.seek(0); error = self._stderr.read(MAX_CAPTURE_BYTES + 1)
            require(len(error) <= MAX_CAPTURE_BYTES, 'protected worker stderr exceeds capture profile')
            _new(self.native_directory / 'stderr.txt', error)
            for handle in (self._native_input, self._native_output):
                if not handle.closed:
                    handle.flush(); os.fsync(handle.fileno()); handle.close()
            self._native_result = {'schema': SCHEMA, 'invocation_id': self._native_id,
                'completed_at_utc': _now(), 'child_pid': self.worker_pid,
                'launcher_pid': None if self.process is None else self.process.pid,
                'native_wait_role': 'launch_process', 'returncode': result,
                'native_wait_completed': native_wait, 'reader_finished': reader_finished,
                'killed_by_observer': killed, 'capture_failed': self._native_failed, 'sealed': self.sealed,
                'stream_sha256': {name: sha((self.native_directory / name).read_bytes())
                                  for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')},
                'grant_sha256': self._native_start['grant_sha256'], 'physical_attestation': False}
            _new(self.native_directory / 'result.json', canonical(self._native_result))
        finally:
            self._stderr.close(); self._directory.cleanup()

    def evidence(self):
        require(self.closed and self._native_result is not None and
                self._native_result['native_wait_completed'] is True and
                self._native_result['reader_finished'] is True and
                self._native_result['returncode'] == 0 and self._native_result['sealed'] is True and
                self._native_result['killed_by_observer'] is False and
                self._native_result['capture_failed'] is False, 'protected worker observation unfinished or failed')
        return {name: (self.native_directory / name).read_bytes() for name in FILES}


def verify_native_records(directory, grant, transcript, accounting, *, source_root=None):
    """Validate original AN records and wire bindings without launching anything."""
    directory = Path(directory); _no_links(directory)
    require(directory.is_dir() and {p.name for p in directory.iterdir()} == set(FILES),
            'exact protected native worker inventory required')
    raw = {}
    for name in FILES:
        path = directory / name; _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_CAPTURE_BYTES, 'invalid protected native file')
        raw[name] = path.read_bytes()
    return verify_native_images(raw, grant, transcript, accounting, source_root=source_root)


def verify_native_images(raw, grant, transcript, accounting, *, source_root=None):
    """Pure original-image validation; no temporary files or native processes."""
    require(type(raw) is dict and set(raw) == set(FILES) and
            all(type(value) is bytes and len(value) <= MAX_CAPTURE_BYTES for value in raw.values()),
            'exact bounded protected native image inventory required')
    start, child, result = [load_json_strict(raw[name], require_canonical=True)
                           for name in ('start.json', 'child.json', 'result.json')]
    exact(start, {'schema', 'invocation_id', 'started_at_utc', 'observer_pid', 'command', 'worker_command',
        'isolation_specification', 'python_path', 'python_sha256', 'worker_source_sha256', 'grant_sha256',
        'environment_sha256', 'shell', 'close_fds', 'pass_fds', 'observer_is_trusted_reference_launcher',
        'physical_attestation', 'stdout_capture'})
    exact(child, {'schema', 'invocation_id', 'observed_at_utc', 'child_pid', 'launcher_pid', 'observer_pid',
        'command', 'cwd', 'worker_identity', 'boundary', 'boundary_frame_hex'})
    exact(result, {'schema', 'invocation_id', 'completed_at_utc', 'child_pid', 'launcher_pid', 'native_wait_role',
        'returncode', 'native_wait_completed', 'reader_finished', 'killed_by_observer', 'capture_failed',
        'sealed', 'stream_sha256', 'grant_sha256', 'physical_attestation'})
    for row in (start, child, result):
        _hash(row['invocation_id'], 32); require(row['schema'] == SCHEMA, 'protected native schema differs')
    require(start['invocation_id'] == child['invocation_id'] == result['invocation_id'],
            'protected native invocation identities differ')
    for key in ('python_sha256', 'worker_source_sha256', 'grant_sha256', 'environment_sha256'):
        _hash(start[key])
    _hash(result['grant_sha256'])
    require(_stamp(start['started_at_utc']) <= _stamp(child['observed_at_utc']) <= _stamp(result['completed_at_utc']),
            'protected native timestamps out of order')
    for value in (start['observer_pid'], child['observer_pid'], child['child_pid'], child['launcher_pid'],
                  result['child_pid'], result['launcher_pid']): _pid(value)
    require(start['observer_pid'] == child['observer_pid'] and child['child_pid'] == result['child_pid'] and
            child['launcher_pid'] == result['launcher_pid'] and child['child_pid'] != child['observer_pid'],
            'protected native process identities differ')
    spec = start['isolation_specification']; isolation._validate_specification(spec)
    require(start['python_sha256'] == spec['readonly_files'][spec['python_executable']] and
            start['worker_source_sha256'] == spec['readonly_files'][spec['command'][-1]],
            'protected executable/source observations disagree')
    require(spec['profile']['role'] == 'worker' and spec['command'] == start['worker_command'] and
            start['worker_command'][0] == start['python_path'] and
            start['command'] == child['command'] == isolation._prefix(spec) and
            child['cwd'] == spec['scratch_directory'] and spec['host_pid'] == start['observer_pid'],
            'actual protected launcher/worker command differs')
    require(start['shell'] is False and start['close_fds'] is True and start['pass_fds'] == [] and
            start['observer_is_trusted_reference_launcher'] is True and
            start['physical_attestation'] is False and result['physical_attestation'] is False,
            'protected native trust scope differs')
    isolation.validate_observation(spec, child['boundary'])
    identity = child['worker_identity']
    exact(identity, {'launcher_pid', 'worker_pid', 'identity_source', 'process_start_ticks', 'namespaces'})
    require(identity['launcher_pid'] == child['launcher_pid'] and identity['worker_pid'] == child['child_pid'],
            'observed worker identity differs from native process')
    if spec['profile']['platform'] == 'linux':
        frame = bytes.fromhex(child['boundary_frame_hex'])
        require(frame.hex() == child['boundary_frame_hex'] and
                isolation.parse_boundary_frame(frame) == child['boundary'] and
                identity['identity_source'] == 'trusted_parent_proc_and_preexec_binding' and
                identity['process_start_ticks'] == child['boundary']['process_start_ticks'] and
                identity['namespaces'] == child['boundary']['namespaces'] and
                start['stdout_capture'] == 'worker_frames_after_retained_preexec_frame',
                'protected original boundary/process binding differs')
    else:
        require(child['boundary_frame_hex'] == '' and identity['identity_source'] == 'direct_native_child' and
                identity['launcher_pid'] == identity['worker_pid'] and identity['process_start_ticks'] is None and
                identity['namespaces'] is None and start['stdout_capture'] == 'direct_worker_frames',
                'Windows reference supplied unsupported confinement')
    require(type(result['returncode']) is int and result['returncode'] == 0 and
            result['native_wait_role'] == 'launch_process' and
            all(result[n] is True for n in ('native_wait_completed', 'reader_finished', 'sealed')) and
            all(result[n] is False for n in ('killed_by_observer', 'capture_failed')),
            'no completed protected native worker observation')
    exact(result['stream_sha256'], {'stdin.jsonl', 'stdout.jsonl', 'stderr.txt'})
    require(result['stream_sha256'] == {n: sha(raw[n]) for n in result['stream_sha256']} and raw['stderr.txt'] == b'',
            'protected native stream identity or diagnostic mismatch')
    require(start['grant_sha256'] == result['grant_sha256'] == sha(canonical(validate_grant(grant))),
            'protected native grant identity differs')
    if source_root is not None:
        source_root = Path(source_root)
        require(start['worker_source_sha256'] == sha((source_root / 'scripts/phase17_campaign_worker.py').read_bytes()),
                'protected fixed worker source changed')
        for relative in ('scripts/phase17_campaign_worker.py', 'scripts/phase17_protected_isolation_probe.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_isolation.py'):
            recorded = [h for p, h in spec['readonly_files'].items() if p.replace('\\', '/').endswith('/' + relative)]
            require(recorded == [sha((source_root / relative).read_bytes())], 'protected wrapper/source binding changed')
    inputs = [parse_wire(line) for line in raw['stdin.jsonl'].splitlines()]
    outputs = [parse_wire(line) for line in raw['stdout.jsonl'].splitlines()]
    require(raw['stdin.jsonl'] == b''.join(wire_bytes(row) + b'\n' for row in inputs) and
            raw['stdout.jsonl'] == b''.join(wire_bytes(row) + b'\n' for row in outputs), 'protected wire framing differs')
    events = load_json_strict(transcript)['events']
    require(len(inputs) == len(outputs) == len(events) + 1 and wire_bytes(inputs[0]) ==
            wire_bytes({'protocol': WORKER_PROTOCOL, 'grant': grant}) and wire_bytes(outputs[0]) ==
            wire_bytes({'protocol': WORKER_PROTOCOL, 'event': 'grant_received', 'grant_hash': grant['grant_hash']}),
            'protected worker handshake differs')
    for i, event in enumerate(events, 1):
        expected = {'protocol': WORKER_PROTOCOL, 'grant_hash': grant['grant_hash'], 'response': event['response'],
                    'accounting': accounting if i == len(events) else None}
        require(wire_bytes(inputs[i]) == wire_bytes(event['request']) and wire_bytes(outputs[i]) == wire_bytes(expected),
                'protected native stream differs from sealed evidence')
    return {name: sha(value) for name, value in raw.items()}
