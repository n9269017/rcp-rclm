"""Original AO prepaid-lifetime and resident-broker reference capture.

The observer and kernel remain trusted. Public records contain no private keys.
No reference observation establishes an independently commissioned host, physical
anti-rollback storage, global exclusivity, or complete campaign accounting.
"""
from __future__ import annotations
from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import platform
import queue
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import authority_transport as transport
from . import durable_campaign as runtime
from . import protected_authority as broker_api
from . import service_lifecycle as lifecycle
from . import resident_broker as resident_api
from . import commissioned_service_deployment as deployment
from . import authority_accounting as accounting
from . import protected_authority_isolation as isolation
from . import protected_campaign_native as worker_native
from .authority_transport_pki import generate_reference_pki
from .durable_campaign_capture import predecessor
from .controller_durable_authority import FALSE_CLAIMS
from .resource_ledger import Policy, canonical, sha, require, exact, full_grammar_policy, _no_links
from .authenticated_authority_capture import _tls_records, _frame, _stamp

BASE = 'db7f9e622e14d7466319c5e21b41a20c768e7a12'
SOURCE_ROOT = Path(__file__).resolve().parents[4]
SCHEMA = 'rcp-rclm.phase17ao.service-lifecycle-packet.v1'
POLICY = 'phase17ao.prepaid-service-reference-campaign.v1'
AN_EXECUTION = 'artifacts/development/phase17an/op-201f5c8cd06b/gate/execution.json'
AN_EXECUTION_SHA = 'a792df0219fd53e7e33ef4147560e11d6b8566748a7bcb6ded55a75355e19d67'
MAX_BYTES = 128 * 1024 * 1024
MAX_NATIVE_FILES = 1024
SERVICE = 'scripts/phase17_protected_authority_service.py'
FRONTEND = 'scripts/phase17_protected_frontend.py'
RESIDENT = 'scripts/phase17_resident_broker_service.py'
RESIDENT_NATIVE_SCHEMA = 'phase17ao.resident-native-observation.v1'
LIFETIME_ENVELOPE = [1, 16, 12, 786444, 786444, 128]
SERVICE_LIMITS = {'max_attempts': 12, 'max_frame_bytes': 65537,
    'max_request_bytes': 786444, 'max_response_bytes': 786444,
    'max_authority_tls_connections': 128}
NATIVE_SCHEMA = 'phase17an.process-observation.v1'
CASE_NAME = 'service_campaign'
ACTIONS = ('initial_read', 'run_one', 'replayed_nonce', 'forbidden_operation',
           'extra_field', 'wrong_commission', 'promotion_denial', 'run_abandon',
           'blocked_retry', 'reconcile', 'aggregate_denial')
REFUSALS = ('replayed_nonce', 'forbidden_operation', 'extra_field',
            'wrong_commission', 'promotion_denial', 'blocked_retry')
SCOPE = {
    'deployment': 'locally_commissioned_prepaid_resident_service_reference',
    'broker': 'separate resident process owns TLS client and broker dispatch; a trusted supervisor prepays bounded lifetime work; frontend receives bounded intents/replies only',
    'frontend': 'reference run-request frontend; inherited present-prefix controller remains inside authority',
    'linux_boundary': 'private user/mount/PID/IPC/UTS/network namespaces, no capabilities or authority mounts; actual evaluator workers use same restricted role-specific profile',
    'windows_boundary': 'explicit unconfined protocol reference; no Linux boundary credit',
    'currentness': 'protected prefix under trusted host/kernel and retention premises; joint rollback and cloning remain external',
    'accounting': 'permanent six-dimensional service envelopes plus inherited AL evaluator reservations; operational counts are not a complete physical campaign cost; unknown AN categories still block promotion',
    'private_keys_in_public_evidence': False,
    'independently_protected_deployment_established': False,
    'global_authority_exclusivity_established': False,
    'complete_resource_accounting': False,
    'physical_execution_attested': False,
    'promotion_authorized': False,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _nonce(purpose):
    return sha(('Phase17AO/' + purpose).encode())


def _write(path, raw):
    transport._new(path, raw)


def _same(a, b, message):
    require(canonical(a) == canonical(b), message)


def _relative(name):
    require(type(name) is str and 0 < len(name) <= 500 and
            '\\' not in name and ':' not in name and '\x00' not in name,
            'bounded POSIX relative native name required')
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.as_posix() == name and bool(path.parts) and '..' not in path.parts
            and path.parts[0] in ('authority', 'frontend', 'broker', 'workers', 'provisioning', 'service', 'budget', 'deployment'),
            'native path outside fixed inventory roots')
    return name


def retained_baseline(root):
    raw = (Path(root) / AN_EXECUTION).read_bytes()
    require(sha(raw) == AN_EXECUTION_SHA, 'exact completed AN execution required')
    record = load_json_strict(raw, require_canonical=False)
    require(record['completed'] is True and
            record['source_commit'] == '201f5c8cd06b8b7851783ae58a17d837ce5dcbb5' and
            record['source_tree'] == '96b49a0fa23c92aa8806eb2b0a43e818eb3db103' and
            record['protected_broker_dispatch_checked'] is True and
            record['campaign_boundary_admission_checked'] is True and
            set(record['claims']) == set(FALSE_CLAIMS) and all(v is False for v in record['claims'].values()),
            'completed AN scope differs')
    for name, hashed in record['source_sha256'].items():
        require(sha((Path(root) / name).read_bytes()) == hashed, 'inherited AN source changed: ' + name)
    return record


class NativeAuthority:
    def __init__(self, root, directory, native, exported, pki, commission_file, commission_pin, root_pin, boot, protected_paths):
        self.root = Path(root); self.native = Path(native); self.exported = Path(exported)
        require(not self.native.exists(), 'fresh authority observation directory required')
        self.native.mkdir(parents=True)
        self._input = (self.native / 'stdin.jsonl').open('xb', buffering=0)
        self._output = (self.native / 'stdout.jsonl').open('xb', buffering=0)
        self._error = (self.native / 'stderr.txt').open('xb', buffering=0)
        self._queue = queue.Queue(); self._reader_error = None; self._closed = False
        self._timed_out = False
        command = [sys.executable, '-I', '-S', '-B', '-u', str(self.root / SERVICE),
            '--directory', str(directory), '--commission', str(commission_file),
            '--commission-pin', commission_pin, '--root-pin', root_pin,
            '--boot-nonce', boot, '--ca-file', pki['public']['ca'],
            '--server-cert', pki['public']['server'], '--server-key', pki['private']['server'],
            '--native-directory', str(self.native / 'transport'), '--export', str(self.exported)]
        for target in protected_paths:
            command += ['--protected-path', str(target)]
        self.start = {'schema': NATIVE_SCHEMA, 'role': 'authority', 'invocation_id': uuid.uuid4().hex,
            'started_at_utc': _now(), 'observer_pid': os.getpid(), 'command': command,
            'cwd': str(self.root), 'source_root': str(self.root),
            'python_sha256': sha(Path(sys.executable).read_bytes()),
            'entrypoint_sha256': sha((self.root / SERVICE).read_bytes()),
            'root_provision_sha256': root_pin, 'commission_sha256': commission_pin,
            'boot_nonce': boot, 'shell': False, 'close_fds': True, 'physical_attestation': False}
        _write(self.native / 'start.json', canonical(self.start))
        self.started_ns = time.monotonic_ns()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._error, cwd=self.root, shell=False, close_fds=True)
        _write(self.native / 'child.json', canonical({'schema': NATIVE_SCHEMA,
            'invocation_id': self.start['invocation_id'], 'child_pid': self.process.pid,
            'observer_pid': os.getpid(), 'observed_at_utc': _now()}))

        def read():
            try:
                while True:
                    line = self.process.stdout.readline(transport.MAX_FRAME + 1)
                    if not line:
                        self._queue.put(None); return
                    require(line.endswith(b'\n') and len(line) <= transport.MAX_FRAME, 'bounded authority stdout required')
                    self._output.write(line); self._queue.put(line)
            except BaseException as error:
                self._reader_error = type(error).__name__; self._queue.put(None)
        self._thread = threading.Thread(target=read, daemon=True); self._thread.start()
        line = self._queue.get(timeout=600)
        require(line is not None and self._reader_error is None, 'authority did not become ready')
        self.ready = load_json_strict(line[:-1], require_canonical=True)
        require(self.ready['schema'] == 'phase17an.authority-ready.v1' and
                self.ready['pid'] == self.process.pid and self.ready['commission_sha256'] == commission_pin and
                self.ready['root_provision_sha256'] == root_pin and self.ready['address'][0] == '127.0.0.1',
                'authority readiness identity differs')

    def close(self):
        if self._closed:
            return
        self._closed = True
        line = canonical({'operation': 'stop'}) + b'\n'
        try:
            require(self.process.stdin.write(line) == len(line), 'short administrative stop')
            self.process.stdin.flush(); self._input.write(line); self.process.stdin.close()
        except (OSError, BrokenPipeError):
            pass
        try:
            code = self.process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            self._timed_out = True; self.process.kill(); code = self.process.wait()
        self._thread.join(timeout=10)
        self.process.stdout.close(); self._input.close(); self._output.close(); self._error.close()
        exported = None
        if code == 0 and self.exported.is_file():
            raw = self.exported.read_bytes(); require(len(raw) <= MAX_BYTES, 'bounded authority export required')
            _write(self.native / 'export.json', raw); exported = sha(raw)
        result = {'schema': NATIVE_SCHEMA, 'invocation_id': self.start['invocation_id'],
            'child_pid': self.process.pid, 'completed_at_utc': _now(),
            'elapsed_ns': time.monotonic_ns() - self.started_ns, 'returncode': code,
            'native_wait_completed': True, 'timed_out': self._timed_out,
            'reader_finished': not self._thread.is_alive(), 'reader_error': self._reader_error,
            'export_sha256': exported,
            'stream_sha256': {name: sha((self.native / name).read_bytes())
                for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')}}
        _write(self.native / 'result.json', canonical(result))
        require(code == 0 and not self._timed_out and result['reader_finished'] and self._reader_error is None
                and (self.native / 'stderr.txt').read_bytes() == b'', 'authority native lifetime did not complete')


class NativeResident:
    """Trusted native observer; all broker dispatch runs in its distinct child."""
    def __init__(self, root, native, config_file, config, ledger, grant):
        self.root, self.native = Path(root), Path(native)
        self.config, self.ledger, self.grant = config, ledger, grant
        self.pin = sha(canonical(config)); self.closed = False
        self.process = self._thread = None
        self.native.mkdir(parents=True, exist_ok=False)
        self._input = (self.native / 'stdin.jsonl').open('xb', buffering=0)
        self._output = (self.native / 'stdout.jsonl').open('xb', buffering=0)
        self._error = (self.native / 'stderr.txt').open('xb', buffering=0)
        self._queue = queue.Queue(); self._reader_error = None; self._timed_out = False
        command = [sys.executable, '-I', '-S', '-B', '-u', str(self.root / RESIDENT),
                   '--config', str(config_file), '--config-pin', self.pin]
        self.start = {'schema': RESIDENT_NATIVE_SCHEMA, 'role': 'resident_broker',
            'invocation_id': uuid.uuid4().hex, 'started_at_utc': _now(),
            'observer_pid': os.getpid(), 'command': command, 'source_root': str(self.root),
            'cwd': str(self.root), 'python_sha256': sha(Path(sys.executable).read_bytes()),
            'entrypoint_sha256': sha((self.root / RESIDENT).read_bytes()),
            'config_sha256': self.pin, 'grant_sha256': grant['grant_sha256'],
            'prelaunch_ledger_sha256': sha(canonical(config['lifecycle_evidence'])),
            'shell': False, 'close_fds': True, 'physical_attestation': False}
        _write(self.native / 'start.json', canonical(self.start))
        self.started_ns = time.monotonic_ns()
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self._error, cwd=self.root, shell=False, close_fds=True)
            _write(self.native / 'child.json', canonical({'schema': RESIDENT_NATIVE_SCHEMA,
                'invocation_id': self.start['invocation_id'], 'child_pid': self.process.pid,
                'observer_pid': os.getpid(), 'observed_at_utc': _now()}))
            def read():
                try:
                    total = 0
                    while True:
                        line = self.process.stdout.readline(65538)
                        if not line:
                            self._queue.put(None); return
                        total += len(line)
                        require(line.endswith(b'\n') and len(line) <= 65537 and
                                total <= config['limits']['max_response_bytes'], 'bounded resident stdout required')
                        self._output.write(line); self._queue.put(line)
                except BaseException as error:
                    self._reader_error = type(error).__name__; self._queue.put(None)
            self._thread = threading.Thread(target=read, daemon=True); self._thread.start()
            raw = self._next()
            self.ready = load_json_strict(raw[:-1], require_canonical=True)
            require(self.ready['schema'] == resident_api.READY_SCHEMA and
                    self.ready['pid'] == self.process.pid and self.ready['parent_pid'] == os.getpid() and
                    self.ready['config_sha256'] == self.pin and self.ready['grant_sha256'] == grant['grant_sha256'],
                    'resident readiness differs from prepaid child')
            ledger.charge(grant, [0, 0, 0, 0, len(raw), 0], event_id='resident-ready',
                          expected_cursor=ledger.cursor, evidence_sha256=sha(raw))
            self.sequence = 0
        except BaseException:
            # A failed constructor never reaches the caller's resident variable.
            # Reap its owned child here while preserving the original failure.
            self.abort()
            raise

    def _next(self):
        line = self._queue.get(timeout=600)
        require(line is not None and self._reader_error is None, 'resident ended before complete response')
        return line

    def exchange(self, raw):
        require(type(raw) is bytes and raw.endswith(b'\n'), 'original resident frame required')
        number = self.sequence
        self.ledger.charge_input(self.grant, raw, event_id='input-%04d' % number,
                                 expected_cursor=self.ledger.cursor)
        require(self.process.stdin.write(raw) == len(raw), 'short resident input write')
        self.process.stdin.flush(); self._input.write(raw)
        reply_raw = self._next()
        reply = load_json_strict(reply_raw[:-1], require_canonical=True)
        require(reply['schema'] == resident_api.REPLY_SCHEMA and reply['pid'] == self.process.pid and
                reply['lifetime_id'] == self.config['lifetime_id'] and reply['sequence'] == number,
                'resident reply does not belong to original request slot')
        self.ledger.charge(self.grant, [0, 0, 0, 0, len(reply_raw), reply['authority_tls_connections']],
            event_id='reply-%04d' % number, expected_cursor=self.ledger.cursor,
            evidence_sha256=sha(reply_raw))
        self.sequence += 1
        return reply['response']

    def close(self):
        if self.closed: return
        raw = self._next()
        self.stopped = load_json_strict(raw[:-1], require_canonical=True)
        require(self.stopped['schema'] == resident_api.STOPPED_SCHEMA and
                self.stopped['pid'] == self.process.pid and self.stopped['completed'] is True,
                'resident did not finish its prepaid lifetime')
        self.ledger.charge(self.grant, [0, 0, 0, 0, len(raw), 0], event_id='resident-stopped',
            expected_cursor=self.ledger.cursor, evidence_sha256=sha(raw))
        self.process.stdin.close()
        try: code = self.process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self._timed_out = True; self.process.kill(); code = self.process.wait(timeout=10)
        self._thread.join(timeout=10)
        self.process.stdout.close(); self._input.close(); self._output.close(); self._error.close()
        result = {'schema': RESIDENT_NATIVE_SCHEMA, 'invocation_id': self.start['invocation_id'],
            'child_pid': self.process.pid, 'completed_at_utc': _now(),
            'elapsed_ns': time.monotonic_ns() - self.started_ns, 'returncode': code,
            'native_wait_completed': True, 'timed_out': self._timed_out,
            'reader_finished': not self._thread.is_alive(), 'reader_error': self._reader_error,
            'stream_sha256': {n: sha((self.native / n).read_bytes())
                for n in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')}}
        _write(self.native / 'result.json', canonical(result))
        require(code == 0 and not self._timed_out and result['reader_finished'] and
                self._reader_error is None and (self.native / 'stderr.txt').read_bytes() == b'' and
                self._queue.get(timeout=1) is None, 'resident native lifetime did not complete')
        self.closed = True
        return result

    def abort(self):
        """Best-effort owned-child cleanup without replacing a primary failure.

        Every outcome remains failed and nonrefunding. A secondary cleanup or
        recording error is retained by operation/type when possible; it never
        turns an interrupted lifetime into successful completion.
        """
        if self.closed: return
        errors = []; code = None; waited = self.process is None
        def attempt(operation, action):
            try: return action()
            except BaseException as error:
                errors.append({'operation': operation, 'error_type': type(error).__name__})
                return None
        if self.process is not None:
            attempt('terminate_owned_child', lambda: self.process.kill() if self.process.poll() is None else None)
            code = attempt('reap_owned_child', lambda: self.process.wait(timeout=10))
            waited = type(code) is int
        if self._thread is not None:
            attempt('join_reader', lambda: self._thread.join(timeout=10))
        reader_finished = self._thread is None or not self._thread.is_alive()
        streams = [('recorded_input', self._input), ('recorded_output', self._output),
                   ('recorded_error', self._error)]
        if self.process is not None:
            streams[:0] = [('child_stdin', self.process.stdin), ('child_stdout', self.process.stdout)]
        for name, stream in streams:
            # Closing a BufferedReader while its read thread still blocks can
            # itself block indefinitely. Preserve that unresolved cleanup state.
            if name in ('child_stdout', 'recorded_output') and not reader_finished:
                errors.append({'operation': 'close_' + name, 'error_type': 'ReaderStillRunning'})
                continue
            attempt('close_' + name, lambda stream=stream: stream.close() if not stream.closed else None)
        streams_closed = all(stream.closed for _, stream in streams)
        self.closed = waited and reader_finished and streams_closed
        record = {'schema': RESIDENT_NATIVE_SCHEMA,
            'child_pid': None if self.process is None else self.process.pid,
            'returncode': code, 'completed': False,
            'native_wait_completed': self.process is not None and waited, 'reader_finished': reader_finished,
            'streams_closed': streams_closed, 'cleanup_errors': errors,
            'automatic_takeover_permitted': False, 'reservation_refunded': False}
        attempt('retain_failure_record', lambda: _write(self.native / 'failure.json', canonical(record)))
        return record



def _load(path):
    return load_json_strict(Path(path).read_bytes(), require_canonical=True)


def _intent(action, pin):
    operation = 'read' if action == 'initial_read' else ('reconcile' if action == 'reconcile' else 'run')
    result = {'schema': 'phase17an.frontend-intent.v1', 'commission_sha256': pin,
              'operation': operation, 'nonce': _nonce('run_one' if action == 'replayed_nonce' else action)}
    if operation == 'run': result['credits'] = 2
    if action == 'forbidden_operation': result['operation'] = 'administrative_export'
    if action == 'extra_field': result['anchor_path'] = '/controller/chosen/anchor'
    if action == 'wrong_commission': result['commission_sha256'] = '0' * 64
    return result


def _frontend(root, physical, native_root, *, action, commission, authority_commission,
              port, protected_paths, resident, ledger, grant):
    """Launch an actual low-authority process; broker stays outside its view."""
    native = native_root / 'frontend' / action
    native.mkdir(parents=True, exist_ok=False)
    broker_native = native_root / 'broker' / action
    scratch = physical / 'untrusted-scratch' / action
    scratch.mkdir(parents=True, exist_ok=False)
    pin = broker_api.commission_digest(commission)
    root_pin = authority_commission['root_provision_sha256']
    authority_pin = transport.commission_digest(authority_commission)
    command = [sys.executable, '-I', '-S', '-B', '-u', str(root / FRONTEND)]
    actual, spec = isolation.build_command(root, command, scratch, protected_paths, 'frontend')
    start = {'schema': NATIVE_SCHEMA, 'role': 'frontend', 'action': action,
        'invocation_id': uuid.uuid4().hex, 'started_at_utc': _now(), 'observer_pid': os.getpid(),
        'command': actual, 'entrypoint_command': command, 'isolation_specification': spec,
        'source_root': str(root), 'cwd': str(root), 'python_sha256': sha(Path(sys.executable).read_bytes()),
        'entrypoint_sha256': sha((root / FRONTEND).read_bytes()),
        'commission_sha256': pin, 'root_provision_sha256': root_pin,
        'shell': False, 'close_fds': True, 'physical_attestation': False}
    _write(native / 'start.json', canonical(start))
    intent = _intent(action, pin)
    mode = 'promotion' if action == 'promotion_denial' else 'reference'
    abandoned = action == 'run_abandon'
    bundle, state = physical / 'broker-bundle', physical / 'broker-state'
    before_state, before_anchor = _load(state / 'broker.json'), _load(state / 'anchor.json')
    begin = time.monotonic_ns()
    ledger.charge(grant, [0, 1, 0, 0, 0, 0], event_id='frontend-launch-' + action,
        expected_cursor=ledger.cursor, evidence_sha256=sha(canonical(start)))
    process = subprocess.Popen(actual, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=root, shell=False, close_fds=True)
    _write(native / 'child.json', canonical({'schema': NATIVE_SCHEMA,
        'invocation_id': start['invocation_id'], 'child_pid': process.pid,
        'observer_pid': os.getpid(), 'observed_at_utc': _now()}))
    output = bytearray(); sent = bytearray(); messages = queue.Queue(maxsize=8)
    reader_errors = []
    def reader():
        try:
            while True:
                line = process.stdout.readline(65538)
                if not line: messages.put(None, timeout=1); return
                require(line.endswith(b'\n') and len(line) <= 65537 and len(output) + len(line) <= 256 * 1024,
                        'bounded frontend stdout required')
                output.extend(line); messages.put(line, timeout=1)
        except BaseException as error:
            reader_errors.append(type(error).__name__)
            try: messages.put(None, timeout=1)
            except queue.Full: pass
    thread = threading.Thread(target=reader, daemon=True); thread.start()
    boundary = None; dispatch = None; error_name = error_message = None
    killed = False; code = None; diagnostics = b''
    def next_line():
        value = messages.get(timeout=60)
        require(value is not None and not reader_errors, 'frontend ended before bounded response')
        return value
    def send(value):
        raw = canonical(value) + b'\n'
        require(process.stdin.write(raw) == len(raw), 'short frontend pipe write')
        process.stdin.flush(); sent.extend(raw)
    try:
        if platform.system() == 'Linux':
            boundary = isolation.parse_boundary_frame(next_line())
            isolation.validate_observation(spec, boundary)
        identity = worker_native.observe_worker_identity(process.pid, boundary)
        _write(native / 'target.json', canonical({'schema': 'phase17an.frontend-target.v1',
            'launcher_pid': identity['launcher_pid'], 'frontend_pid': identity['worker_pid'],
            'identity_source': identity['identity_source'], 'process_start_ticks': identity['process_start_ticks'],
            'namespaces': identity['namespaces']}))
        send(intent)
        actual_intent = load_json_strict(next_line()[:-1], require_canonical=True)
        _same(actual_intent, intent, 'original frontend proposed a different capture intent')
        public = resident.exchange(canonical(actual_intent) + b'\n')
        outer = _load(broker_native / 'dispatch.json')
        dispatch = outer['dispatch']
        error_name, error_message = outer['error_type'], outer['error_message']
        require(outer['frontend_response'] == public, 'resident reply differs from original broker record')
        require((action in REFUSALS) == (error_name is not None), 'selected broker refusal outcome differs')
        send(public)
        _same(load_json_strict(next_line()[:-1], require_canonical=True), public,
              'frontend received a different sanitized reply')
        process.stdin.close()
        code = process.wait(timeout=30)
        thread.join(timeout=5)
        diagnostics = process.stderr.read(65537)
        require(code == 0 and not thread.is_alive() and not reader_errors and diagnostics == b'' and
                messages.get(timeout=1) is None, 'frontend native lifetime did not complete cleanly')
    finally:
        if process.poll() is None:
            killed = True; process.kill(); code = process.wait(timeout=10)
        thread.join(timeout=5)
        for pipe in (process.stdin, process.stdout, process.stderr):
            if not pipe.closed: pipe.close()
        _write(native / 'stdin.jsonl', bytes(sent))
        _write(native / 'stdout.jsonl', bytes(output))
        _write(native / 'stderr.txt', diagnostics)
        if boundary is not None: _write(native / 'boundary.json', canonical(boundary))
        _write(native / 'result.json', canonical({'schema': NATIVE_SCHEMA,
            'invocation_id': start['invocation_id'], 'child_pid': process.pid,
            'completed_at_utc': _now(), 'elapsed_ns': time.monotonic_ns() - begin,
            'returncode': code, 'native_wait_completed': process.returncode is not None,
            'reader_finished': not thread.is_alive(), 'reader_errors': reader_errors,
            'killed_by_observer': killed,
            'stream_sha256': {n: sha((native / n).read_bytes()) for n in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')}}))
    record = _load(broker_native / 'dispatch.json')
    require(record['state_before'] == before_state and record['anchor_before'] == before_anchor and
            record['state_after'] == _load(state / 'broker.json') and
            record['anchor_after'] == _load(state / 'anchor.json'), 'resident broker filesystem join differs')
    return record


def prepare_service_lifecycle(root, physical):
    root, physical = Path(root).absolute(), Path(physical).absolute()
    require(not physical.exists(), 'new AO physical workspace required'); physical.mkdir(parents=True)
    retained_baseline(root); parent = predecessor(str(root))
    native_root = physical / 'campaign-native'; native_root.mkdir()
    one = full_grammar_policy(len(parent.accepted_programs), candidate_limit=2)
    policy = Policy(tuple(2 * value for value in one.limits), 2 * one.cost_limit)
    provisioned = runtime.provision_root(physical / 'root', root, parent, policy,
        authority_id='phase17ao.reference.service_campaign', nonce=secrets.token_hex(32))
    pin = provisioned['root_provision_sha256']
    connection = sqlite3.connect(physical / 'root/authority.sqlite3')
    try:
        headers = [load_json_strict(row[0], require_canonical=True)
                   for row in connection.execute('SELECT event FROM snapshots ORDER BY serial')]
    finally: connection.close()
    require(len(headers) == 1 and transport.event_cursor(headers[0]) == provisioned['cursor'],
            'independently supplied initial header differs')
    pki = generate_reference_pki(physical / 'private')
    authority_commission = transport.make_commission(root, pin, pki['public']['ca'],
        pki['public']['server'], pki['public']['client'])
    authority_pin = transport.commission_digest(authority_commission)
    commission_file = physical / 'commission.json'; _write(commission_file, canonical(authority_commission))
    bundle = physical / 'broker-bundle'; bundle.mkdir(mode=0o700)
    for name in ('ca', 'server', 'client'):
        _write(bundle / (name + '.pem'), Path(pki['public'][name]).read_bytes())
    _write(bundle / 'client.key', Path(pki['private']['client']).read_bytes())
    state = physical / 'broker-state'; state.mkdir(mode=0o700)
    initial_anchor = transport.create_anchor(state / 'anchor.json', authority_commission,
        expected_commission_sha256=authority_pin, expected_root_pin=pin, trusted_headers=headers)
    launch_profile = {role: isolation.launch_profile(role) for role in ('frontend', 'worker')}
    commission = broker_api.make_broker_commission(root, authority_commission,
        expected_authority_commission_sha256=authority_pin, expected_root_pin=pin,
        launch_profile=launch_profile)
    broker_pin = broker_api.commission_digest(commission)
    initial_broker = broker_api.provision_broker_state(state / 'broker.json', commission,
        expected_commission_sha256=broker_pin, trusted_headers=headers)
    _write(physical / 'broker-commission.json', canonical(commission))
    _write(native_root / 'provisioning/pki.json', canonical({k: v for k, v in pki.items() if k != 'private'}))
    _write(native_root / 'provisioning/commissioning.json', canonical({'commission': commission,
        'commission_sha256': broker_pin, 'authority_commission': authority_commission,
        'authority_commission_sha256': authority_pin, 'root_provision_sha256': pin,
        'initial_anchor': initial_anchor, 'initial_broker': initial_broker,
        'private_keys_published': False, 'independent_production_issuer_established': False}))
    for name in ('lifecycle-state', 'service-configs'):
        (physical / name).mkdir(mode=0o700)
    (native_root / 'broker').mkdir()
    report = deployment.reference_deployment_report(root, broker_pin)
    _write(native_root / 'deployment/reference.json', canonical(report))
    lifetime_commission = lifecycle.make_commission(bindings={
        'campaign_commission_sha256': broker_pin,
        'runtime_sha256': resident_api.runtime_identity(root),
        'principal_binding_sha256': sha(canonical(report)),
        'currentness_anchor_sha256': sha(canonical(initial_anchor))},
        lifetime_envelope=LIFETIME_ENVELOPE,
        total_budget=[2 * n for n in LIFETIME_ENVELOPE],
        commissioning_nonce=secrets.token_hex(32))
    lifetime_pin = lifecycle.commission_digest(lifetime_commission)
    ledger_path = physical / 'lifecycle-state/main.json'
    initial_ledger = lifecycle.provision(ledger_path, lifetime_commission,
                                        expected_commission_sha256=lifetime_pin)
    _write(native_root / 'budget/commissioning.json', canonical({
        'schema': 'phase17ao.reference-lifecycle-provisioning.v1',
        'commission': lifetime_commission, 'commission_sha256': lifetime_pin,
        'initial_evidence': initial_ledger, 'independent_production_issuer_established': False}))
    protected_paths = [physical / name for name in
        ('root', 'private', 'broker-bundle', 'broker-state', 'campaign-native', 'lifecycle-state', 'service-configs')]
    boots = []; previous_cursor = initial_ledger['final_cursor']; seen_workers = set()
    for index in (0, 1):
        name = 'lifetime-' + str(index)
        exported = physical / 'exports' / (name + '.json')
        ledger = lifecycle.ServiceLifecycleLedger(ledger_path,
            expected_commission_sha256=lifetime_pin, owner_nonce=_nonce('owner-' + str(index)),
            expected_cursor=previous_cursor)
        authority = resident = None
        try:
            grant = ledger.reserve(name, expected_cursor=ledger.cursor)
            ledger.consume_launch(grant, expected_cursor=ledger.cursor)
            prelaunch = ledger.export_evidence()
            _write(native_root / 'budget' / (name + '-prelaunch.json'), canonical(prelaunch))
            _write(native_root / 'budget' / (name + '-prelaunch-observation.json'), canonical({
                'schema': 'phase17ao.prelaunch-observation.v1', 'observer_pid': os.getpid(),
                'observed_at_utc': _now(), 'lifetime_id': name,
                'evidence_sha256': sha(canonical(prelaunch)), 'grant_sha256': grant['grant_sha256'],
                'processes_started': 0, 'physical_attestation': False}))
            authority = NativeAuthority(root, physical / 'root', native_root / 'authority' / name,
                exported, pki, commission_file, authority_pin, pin, _nonce('boot-' + str(index)), protected_paths)
            actions = list(ACTIONS[:9] if index == 0 else ACTIONS[9:])
            slots = [{'action': action, 'mode': 'promotion' if action == 'promotion_denial' else 'reference',
                      'abandon_response': action == 'run_abandon'} for action in actions]
            if index == 0:
                slots.insert(0, {'action': 'malformed_input', 'mode': 'reference', 'abandon_response': False})
            resident_root = native_root / 'service' / name
            resident_root.mkdir(parents=True)
            ledger.charge(grant, [0, 1, 0, 0, 0, 0], event_id='resident-process-launch',
                expected_cursor=ledger.cursor,
                evidence_sha256=sha(canonical({'entrypoint': RESIDENT, 'lifetime_id': name})))
            config = resident_api.make_config(source_root=root, lifetime_id=name,
                broker_commission=physical / 'broker-commission.json', broker_commission_sha256=broker_pin,
                authority_commission=commission_file, authority_commission_sha256=authority_pin,
                root_provision_sha256=pin, state_path=state / 'broker.json', anchor_path=state / 'anchor.json',
                ca_file=bundle / 'ca.pem', client_cert=bundle / 'client.pem', client_key=bundle / 'client.key',
                port=authority.ready['address'][1], native_directory=resident_root / 'resident',
                broker_native_root=native_root / 'broker', limits=SERVICE_LIMITS, slots=slots,
                lifecycle_commission_sha256=lifetime_pin, lifecycle_evidence=ledger.export_evidence(), grant=grant)
            config_file = physical / 'service-configs' / (name + '.json')
            _write(config_file, canonical(config))
            resident = NativeResident(root, resident_root / 'observer', config_file, config, ledger, grant)
            if index == 0:
                refusal = resident.exchange(b'{\n')
                require(refusal == {'schema': 'phase17ao.resident-input-refusal.v1',
                    'raw_frame_sha256': sha(b'{\n'), 'refused': True, 'reason': 'invalid_input_frame'},
                    'malformed resident input was not refused before broker dispatch')
            for action in actions:
                _frontend(root, physical, native_root, action=action, commission=commission,
                    authority_commission=authority_commission, port=authority.ready['address'][1],
                    protected_paths=protected_paths, resident=resident, ledger=ledger, grant=grant)
            resident_result = resident.close()
            authority.close()
            exported_evidence = _load(exported)
            checked_lifetime = runtime.verify_evidence(exported_evidence, parent,
                expected_root_provision_sha256=pin, source_root=root)
            worker_ids = [load_json_strict(bytes.fromhex(session['files_hex']['grant.json']))['grant_hash']
                          for session in checked_lifetime['snapshot']['sessions']]
            new_workers = [value for value in worker_ids if value not in seen_workers]
            seen_workers.update(new_workers)
            if new_workers:
                ledger.charge(grant, [0, len(new_workers), 0, 0, 0, 0], event_id='observed-worker-launches',
                    expected_cursor=ledger.cursor, evidence_sha256=sha(canonical(new_workers)))
            closeout = {'schema': 'phase17ao.service-lifetime-closeout.v1',
                'lifetime_id': name, 'commission_sha256': lifetime_pin, 'grant_sha256': grant['grant_sha256'],
                'config_sha256': sha(canonical(config)), 'observer_pid': os.getpid(),
                'observed_at_utc': _now(), 'resident_pid': resident.process.pid,
                'authority_pid': authority.process.pid, 'frontend_actions': actions,
                'new_worker_grants': new_workers, 'resident_counters': resident.stopped['counters'],
                'used': ledger.state['pending']['used'],
                'resident_result_sha256': sha(canonical(resident_result)),
                'authority_result_sha256': sha((native_root / 'authority' / name / 'result.json').read_bytes()),
                'authority_export_sha256': sha(canonical(exported_evidence)),
                'reservation_refunded': False, 'complete_resource_accounting': False}
            _write(native_root / 'budget' / (name + '-closeout.json'), canonical(closeout))
            ledger.finish(grant, expected_cursor=ledger.cursor, evidence_sha256=sha(canonical(closeout)))
            if index == 1:
                before_denial = ledger.export_evidence()
                error_type = error_message = None
                try: ledger.reserve('lifetime-2-denied', expected_cursor=ledger.cursor)
                except lifecycle.ResourceExhausted as error:
                    error_type, error_message = type(error).__name__, str(error)
                require(error_type == 'ResourceExhausted', 'third prepaid lifetime unexpectedly admitted')
                _write(native_root / 'budget/budget-denial.json', canonical({
                    'schema': 'phase17ao.service-budget-denial.v1', 'observer_pid': os.getpid(),
                    'observed_at_utc': _now(), 'before_cursor': before_denial['final_cursor'],
                    'after_cursor': ledger.cursor, 'requested_lifetime_id': 'lifetime-2-denied',
                    'error_type': error_type, 'error_message': error_message,
                    'processes_launched': 0, 'reserved': ledger.state['reserved']}))
            previous_cursor = ledger.cursor
        finally:
            if resident is not None and not resident.closed: resident.abort()
            if authority is not None and not authority._closed: authority.close()
            ledger.close()
        boots.append(name)
    main_evidence = lifecycle.read_evidence(ledger_path, expected_commission_sha256=lifetime_pin)
    _write(native_root / 'budget/main.json', canonical(main_evidence))
    # Isolated non-launching control: it cannot add work to the selected campaign.
    interrupted_path = physical / 'lifecycle-state/interrupted-control.json'
    lifecycle.provision(interrupted_path, lifetime_commission, expected_commission_sha256=lifetime_pin)
    with lifecycle.ServiceLifecycleLedger(interrupted_path, expected_commission_sha256=lifetime_pin,
            owner_nonce=_nonce('interrupted-owner')) as control:
        control.reserve('interrupted-control', expected_cursor=control.cursor)
    interrupted = lifecycle.read_evidence(interrupted_path, expected_commission_sha256=lifetime_pin)
    attempted_owner = _nonce('interrupted-reopen-owner')
    error_type = error_message = None
    try:
        resumed = lifecycle.ServiceLifecycleLedger(interrupted_path, expected_commission_sha256=lifetime_pin,
            owner_nonce=attempted_owner, expected_cursor=interrupted['final_cursor'])
    except ValueError as error:
        error_type, error_message = type(error).__name__, str(error)
    else:
        resumed.close(); require(False, 'interrupted reservation unexpectedly reopened')
    require(lifecycle.read_evidence(interrupted_path, expected_commission_sha256=lifetime_pin) == interrupted,
            'interrupted control changed during refused reopen')
    _write(native_root / 'budget/interrupted.json', canonical(interrupted))
    _write(native_root / 'budget/interruption-refusal.json', canonical({
        'schema': 'phase17ao.interrupted-lifetime-control.v1', 'attempted_owner_nonce': attempted_owner,
        'error_type': error_type, 'error_message': error_message, 'evidence_sha256': sha(canonical(interrupted)),
        'isolated_control': True, 'processes_launched': 0, 'reservation_refunded': False}))

    evidence = _load(exported)
    checked = runtime.verify_evidence(evidence, parent, expected_root_provision_sha256=pin, source_root=root)
    grants = []
    for session in checked['snapshot']['sessions']:
        grant = load_json_strict(bytes.fromhex(session['files_hex']['grant.json']))['grant_hash']; grants.append(grant)
        origin = physical / 'root/worker-native' / grant
        for name in worker_native.FILES:
            _write(native_root / 'workers' / grant / name, (origin / name).read_bytes())
    images = {}
    for path in sorted(native_root.rglob('*')):
        _no_links(path)
        if path.is_file():
            name = _relative(path.relative_to(native_root).as_posix()); raw = path.read_bytes()
            require(b'PRIVATE KEY-----' not in raw, 'private key unexpectedly entered public native evidence')
            images[name] = raw.hex()
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'retained_an_execution_sha256': AN_EXECUTION_SHA, 'scope': SCOPE, 'platform': platform.system(),
        'cases': [{'name': CASE_NAME, 'commission': commission, 'authority_commission': authority_commission,
            'certificates': {name: Path(path).read_bytes().hex() for name, path in pki['public'].items()},
            'root_provision_sha256': pin, 'evidence': evidence, 'native_boots': boots, 'worker_grants': grants}],
        'native_images': images, 'claims': {name: False for name in FALSE_CLAIMS}}
    packet['summary'] = summarize(packet, root)
    packet['formal_projection'] = formal_projection(packet, root)
    packet['accounting_closeout'] = accounting_closeout(packet, root)
    prepared = PreparedServiceLifecycle(canonical(packet), root)
    verify_all_native(native_root, prepared.packet, root)
    return prepared

def _images(packet):
    images = packet['native_images']
    require(type(images) is dict and 0 < len(images) <= MAX_NATIVE_FILES, 'bounded original native inventory required')
    result = {}; total = 0
    for name, encoded in images.items():
        _relative(name)
        require(type(encoded) is str and len(encoded) <= 2 * MAX_BYTES, 'bounded native bytes required')
        raw = bytes.fromhex(encoded)
        require(raw.hex() == encoded and b'PRIVATE KEY-----' not in raw, 'noncanonical or private native image')
        total += len(raw); require(total <= MAX_BYTES, 'native image total exceeds bound')
        result[name] = raw
    return result


def _json(images, name):
    require(name in images, 'missing original native file: ' + name)
    return load_json_strict(images[name], require_canonical=True)


def _process(images, directory, root, role):
    start, child, result = [_json(images, directory + '/' + n) for n in ('start.json', 'child.json', 'result.json')]
    base_start = {'schema', 'role', 'invocation_id', 'started_at_utc', 'observer_pid', 'command',
        'cwd', 'source_root', 'python_sha256', 'entrypoint_sha256', 'root_provision_sha256',
        'commission_sha256', 'shell', 'close_fds', 'physical_attestation'}
    exact(start, base_start | ({'boot_nonce'} if role == 'authority' else
                              {'action', 'entrypoint_command', 'isolation_specification'}))
    exact(child, {'schema', 'invocation_id', 'child_pid', 'observer_pid', 'observed_at_utc'})
    fields = {'schema', 'invocation_id', 'child_pid', 'completed_at_utc', 'elapsed_ns', 'returncode',
              'native_wait_completed', 'reader_finished', 'stream_sha256'}
    exact(result, fields | ({'timed_out', 'reader_error', 'export_sha256'} if role == 'authority' else
                           {'reader_errors', 'killed_by_observer'}))
    require(start['schema'] == child['schema'] == result['schema'] == NATIVE_SCHEMA and start['role'] == role,
            'native process schema/role differs')
    identifier = start['invocation_id']
    require(type(identifier) is str and len(identifier) == 32 and set(identifier) <= set('0123456789abcdef') and
            child['invocation_id'] == result['invocation_id'] == identifier, 'native invocation join differs')
    for value in (start['observer_pid'], child['observer_pid'], child['child_pid'], result['child_pid']):
        require(type(value) is int and 0 < value < 2**63, 'exact positive native PID required')
    require(start['observer_pid'] == child['observer_pid'] and child['child_pid'] == result['child_pid'] and
            child['child_pid'] != child['observer_pid'], 'native parent/child identities differ')
    require(_stamp(start['started_at_utc']) <= _stamp(child['observed_at_utc']) <= _stamp(result['completed_at_utc']),
            'native observation timestamp order differs')
    require(type(result['elapsed_ns']) is int and 0 <= result['elapsed_ns'] <= 1200 * 10**9 and
            type(result['returncode']) is int and result['returncode'] == 0 and
            result['native_wait_completed'] is True and result['reader_finished'] is True,
            'native process did not complete')
    script = SERVICE if role == 'authority' else FRONTEND
    require(start['source_root'] == start['cwd'] == str(Path(root).absolute()) and
            start['entrypoint_sha256'] == sha((Path(root) / script).read_bytes()) and
            start['shell'] is False and start['close_fds'] is True and start['physical_attestation'] is False,
            'native source or launch scope differs')
    for key in ('python_sha256', 'entrypoint_sha256', 'root_provision_sha256', 'commission_sha256'):
        transport.digest(start[key])
    exact(result['stream_sha256'], {'stdin.jsonl', 'stdout.jsonl', 'stderr.txt'})
    for name, digest in result['stream_sha256'].items():
        require(directory + '/' + name in images and sha(images[directory + '/' + name]) == digest,
                'native stream bytes differ')
    require(images[directory + '/stderr.txt'] == b'', 'selected native process emitted diagnostics')
    if role == 'authority':
        require(result['timed_out'] is False and result['reader_error'] is None, 'authority native lifetime incomplete')
    else:
        require(result['reader_errors'] == [] and result['killed_by_observer'] is False,
                'frontend reader or lifetime incomplete')
    return start, child, result


def _pkis(images, case):
    pki = _json(images, 'provisioning/pki.json')
    require(pki['schema'] == 'phase17am.reference-pki-generation.v1' and
            pki['independent_production_issuer_established'] is False and
            pki['private_material_is_publication_evidence'] is False and 'private' not in pki,
            'reference PKI scope differs')
    transport.digest(pki['openssl_sha256'])
    require(set(pki['public']) == set(pki['identities']) == set(case['certificates']) ==
            {'ca', 'server', 'client', 'other-client', 'foreign-ca', 'foreign-client'}, 'public PKI inventory differs')
    private = Path(pki['directory']); physical = private.parent
    require(private == physical / 'private' and pki['command_records_directory'] == str(private / 'command-records'),
            'PKI original path attribution differs')
    for name, encoded in case['certificates'].items():
        raw = bytes.fromhex(encoded); require(raw.hex() == encoded, 'canonical certificate image required')
        der = transport.ssl.PEM_cert_to_DER_cert(raw.decode('ascii'))
        require(pki['public'][name] == str(private / (name + '.pem')) and
                pki['identities'][name] == {'pem_sha256': sha(raw), 'der_sha256': sha(der)}, 'PKI certificate identity differs')
    require(type(pki['commands']) is list and len(pki['commands']) == 11, 'exact reference PKI commands required')
    for record in pki['commands']:
        require(record['command'][0] == pki['openssl_path'] and record['cwd'] == str(private) and
                record['native_wait_completed'] is True and type(record['returncode']) is int and record['returncode'] == 0 and
                record['timed_out'] is False and record['error_type'] is None and record['shell'] is False and
                type(record['child_pid']) is int and record['child_pid'] > 0 and
                type(record['elapsed_ns']) is int and 0 <= record['elapsed_ns'] <= 70 * 10**9, 'PKI command incomplete')
        for field in ('stdout_hex', 'stderr_hex'):
            require(type(record[field]) is str and len(record[field]) <= 2 * transport.MAX_FRAME and
                    bytes.fromhex(record[field]).hex() == record[field], 'bounded original PKI stream required')
    return physical


def _prefix_of(prefix, whole):
    count = len(prefix['events'])
    require(prefix == {**whole, 'events': whole['events'][:count],
            'final_cursor': lifecycle._cursor(whole['commission_sha256'], whole['events'][count - 1])},
            'service prelaunch prefix is not the retained authoritative history')


def verify_service_native(packet, root, physical):
    """Reconstruct original prepayment, process ownership and counted streams."""
    images = _images(packet); case = packet['cases'][0]
    provision = _json(images, 'budget/commissioning.json')
    exact(provision, {'schema', 'commission', 'commission_sha256', 'initial_evidence',
                     'independent_production_issuer_established'})
    require(provision['schema'] == 'phase17ao.reference-lifecycle-provisioning.v1' and
            provision['independent_production_issuer_established'] is False,
            'service commissioning broadens local reference scope')
    pin = provision['commission_sha256']; commission = provision['commission']
    main = _json(images, 'budget/main.json')
    main_checked = lifecycle.verify_evidence(main, expected_commission_sha256=pin)
    require(main['commission'] == commission and commission['lifetime_envelope'] == LIFETIME_ENVELOPE and
            commission['total_budget'] == [2 * n for n in LIFETIME_ENVELOPE],
            'selected service lifetime envelope or campaign budget differs')
    initial = provision['initial_evidence']
    lifecycle.verify_evidence(initial, expected_commission_sha256=pin)
    require(len(initial['events']) == 1 and initial['events'][0]['kind'] == 'provision',
            'service budget did not begin at original provisioning')
    _prefix_of(initial, main)
    report = _json(images, 'deployment/reference.json')
    deployment.verify_reference_deployment_report(report, source_root=root)
    broker_pin = broker_api.commission_digest(case['commission'])
    initial_broker = _json(images, 'provisioning/commissioning.json')
    require(report['broker_commission_sha256'] == broker_pin and commission['bindings'] == {
        'campaign_commission_sha256': broker_pin, 'runtime_sha256': resident_api.runtime_identity(root),
        'principal_binding_sha256': sha(canonical(report)),
        'currentness_anchor_sha256': sha(canonical(initial_broker['initial_anchor']))},
        'service commission substituted campaign, source, principal scope or retained reference anchor')
    expected_files = {'budget/commissioning.json', 'budget/main.json', 'budget/budget-denial.json',
        'budget/interrupted.json', 'budget/interruption-refusal.json', 'deployment/reference.json'}
    services = []; all_charge_events = []; main_events = main['events']; previous_end = None
    expected_event_kinds = ['provision']
    expected_grants = []
    for index in (0, 1):
        name = 'lifetime-' + str(index); prefix = 'service/' + name
        observed = prefix + '/observer'; native = prefix + '/resident'
        start, child, result = [_json(images, observed + '/' + n) for n in ('start.json', 'child.json', 'result.json')]
        config = _json(images, native + '/config.json'); config_pin = sha(canonical(config))
        resident_api.verify_config(config, expected_config_sha256=config_pin,
                                   source_root=root, verify_paths=False)
        grant = config['grant']; expected_grants.append(grant)
        require(config['lifetime_id'] == name and config['limits'] == SERVICE_LIMITS and
                config['lifecycle_commission_sha256'] == pin and
                config['broker_commission_sha256'] == broker_pin and
                config['authority_commission_sha256'] == transport.commission_digest(case['authority_commission']) and
                config['root_provision_sha256'] == case['root_provision_sha256'],
                'resident trusted commission/limits/lifetime differ')
        wanted_paths = {'source_root': root, 'broker_commission': physical / 'broker-commission.json',
            'authority_commission': physical / 'commission.json', 'state_path': physical / 'broker-state/broker.json',
            'anchor_path': physical / 'broker-state/anchor.json', 'ca_file': physical / 'broker-bundle/ca.pem',
            'client_cert': physical / 'broker-bundle/client.pem', 'client_key': physical / 'broker-bundle/client.key',
            'native_directory': physical / 'campaign-native' / native,
            'broker_native_root': physical / 'campaign-native/broker'}
        require(all(config[k] == str(Path(v)) for k, v in wanted_paths.items()),
                'resident path or credential configuration substituted')
        actions = list(ACTIONS[:9] if index == 0 else ACTIONS[9:])
        slots = [{'action': action, 'mode': 'promotion' if action == 'promotion_denial' else 'reference',
                  'abandon_response': action == 'run_abandon'} for action in actions]
        if index == 0: slots.insert(0, {'action': 'malformed_input', 'mode': 'reference', 'abandon_response': False})
        require(config['slots'] == slots, 'resident trusted schedule differs')
        _prefix_of(config['lifecycle_evidence'], main)
        prelaunch_name = 'budget/' + name + '-prelaunch.json'
        prelaunch = _json(images, prelaunch_name); _prefix_of(prelaunch, main)
        checked_prefix = lifecycle.verify_evidence(prelaunch, expected_commission_sha256=pin)
        require(prelaunch['events'][-1]['kind'] == 'launch' and
                checked_prefix['state']['pending']['grant'] == grant and
                config['lifecycle_evidence']['events'][:-1] == prelaunch['events'] and
                config['lifecycle_evidence']['events'][-1]['kind'] == 'charge' and
                config['lifecycle_evidence']['events'][-1]['payload']['event_id'] == 'resident-process-launch',
                'authority or broker process has no exact consumed prelaunch reservation')
        pre_observation_name = 'budget/' + name + '-prelaunch-observation.json'
        pre_observation = _json(images, pre_observation_name)
        require(pre_observation == {'schema': 'phase17ao.prelaunch-observation.v1',
            'observer_pid': start['observer_pid'], 'observed_at_utc': pre_observation['observed_at_utc'],
            'lifetime_id': name, 'evidence_sha256': sha(images[prelaunch_name]),
            'grant_sha256': grant['grant_sha256'], 'processes_started': 0, 'physical_attestation': False},
            'original prelaunch observation differs')
        authority_start = _json(images, 'authority/' + name + '/start.json')
        authority_child = _json(images, 'authority/' + name + '/child.json')
        authority_result = _json(images, 'authority/' + name + '/result.json')
        ready_authority = load_json_strict(images['authority/' + name + '/stdout.jsonl'].splitlines()[0], require_canonical=True)
        require(config['host'] == ready_authority['address'][0] and config['port'] == ready_authority['address'][1],
                'resident endpoint differs from actual pinned authority')
        require(_stamp(pre_observation['observed_at_utc']) <= _stamp(authority_start['started_at_utc']) <=
                _stamp(start['started_at_utc']) <= _stamp(child['observed_at_utc']) <=
                _stamp(result['completed_at_utc']) <= _stamp(authority_result['completed_at_utc']),
                'prepayment/authority/resident process ordering differs')
        require(previous_end is None or previous_end <= _stamp(pre_observation['observed_at_utc']),
                'prepaid service lifetimes overlap')
        previous_end = _stamp(authority_result['completed_at_utc'])
        expected_command = [authority_start['command'][0], '-I', '-S', '-B', '-u', str(Path(root) / RESIDENT),
            '--config', str(physical / 'service-configs' / (name + '.json')), '--config-pin', config_pin]
        require(start['schema'] == child['schema'] == result['schema'] == RESIDENT_NATIVE_SCHEMA and
                start['role'] == 'resident_broker' and start['command'] == expected_command and
                start['source_root'] == start['cwd'] == str(root) and
                start['entrypoint_sha256'] == sha((Path(root) / RESIDENT).read_bytes()) and
                start['python_sha256'] == authority_start['python_sha256'] and
                start['config_sha256'] == config_pin and start['grant_sha256'] == grant['grant_sha256'] and
                start['prelaunch_ledger_sha256'] == sha(canonical(config['lifecycle_evidence'])) and
                start['shell'] is False and start['close_fds'] is True and start['physical_attestation'] is False,
                'resident original source or launch identity differs')
        require(start['invocation_id'] == child['invocation_id'] == result['invocation_id'] and
                start['observer_pid'] == child['observer_pid'] == authority_start['observer_pid'] and
                child['child_pid'] == result['child_pid'] and child['child_pid'] not in
                (start['observer_pid'], authority_child['child_pid']), 'resident ownership process join differs')
        require(result['returncode'] == 0 and type(result['returncode']) is int and
                result['native_wait_completed'] is True and result['timed_out'] is False and
                result['reader_finished'] is True and result['reader_error'] is None and
                type(result['elapsed_ns']) is int and 0 <= result['elapsed_ns'] <= 1200 * 10**9,
                'resident process did not complete')
        exact(result['stream_sha256'], {'stdin.jsonl', 'stdout.jsonl', 'stderr.txt'})
        for filename, hashed in result['stream_sha256'].items():
            require(sha(images[observed + '/' + filename]) == hashed, 'resident original stream hash differs')
        require(images[observed + '/stderr.txt'] == b'', 'resident emitted unexpected diagnostics')
        attempts = []; admissions = []; frames = []
        for number in range(len(slots)):
            stem = native + '/attempt-%04d' % number
            attempts.append(_json(images, stem + '.json'))
            admissions.append(_json(images, stem + '.admission.json'))
            frames.append(images[stem + '.input.bin'])
            expected_files.update(stem + suffix for suffix in ('.json', '.admission.json', '.input.bin'))
        require(b''.join(frames) == images[observed + '/stdin.jsonl'], 'resident original input stream differs')
        summary = resident_api.verify_stream(images[observed + '/stdout.jsonl'], config=config,
            attempts=attempts, admissions=admissions, raw_frames=frames)
        lines = images[observed + '/stdout.jsonl'].splitlines(keepends=True)
        replies = [load_json_strict(line[:-1], require_canonical=True) for line in lines]
        ready, stopped = replies[0], replies[-1]
        require(ready == _json(images, native + '/ready.json') and stopped == _json(images, native + '/stopped.json') and
                summary['pid'] == child['child_pid'] and ready['parent_pid'] == start['observer_pid'] and
                ready['limits'] == SERVICE_LIMITS and ready['slots'] == len(slots) and
                ready['inherited_pipe_transport'] is True and ready['authenticated_remote_transport_established'] is False and
                ready['independently_protected_deployment_established'] is False,
                'resident original ready/stop records differ')
        for field in ('reservation_refunded', 'global_clone_exclusivity_established',
                      'independently_protected_deployment_established', 'complete_resource_accounting', 'promotion_authorized'):
            require(stopped[field] is False, 'resident closeout broadens scope')
        marker = _json(images, native + '/launch-owner.json')
        require(marker['schema'] == 'phase17ao.resident-launch-owner.v1' and
                marker['config_sha256'] == config_pin and marker['commission_sha256'] == pin and
                marker['grant_sha256'] == grant['grant_sha256'] and marker['lifetime_id'] == name and
                marker['pid'] == child['child_pid'] and
                marker['parent_consumed_cursor'] == config['lifecycle_evidence']['final_cursor'] and
                marker['automatic_reuse_permitted'] is False and marker['global_clone_exclusivity_established'] is False and
                ready['launch_owner_sha256'] == stopped['launch_owner_sha256'] == sha(canonical(marker)) and
                _stamp(start['started_at_utc']) <= _stamp(marker['claimed_at_utc']) <= _stamp(result['completed_at_utc']),
                'resident local launch-consumption marker differs')
        charges = [('resident-process-launch', [0, 1, 0, 0, 0, 0],
                    sha(canonical({'entrypoint': RESIDENT, 'lifetime_id': name}))),
                   ('resident-ready', [0, 0, 0, 0, len(lines[0]), 0], sha(lines[0]))]
        for number, slot in enumerate(slots):
            action = slot['action']; frame = frames[number]; reply = replies[number + 1]
            if action == 'malformed_input':
                require(index == number == 0 and frame == b'{\n' and
                        attempts[number]['parse_status'] == 'malformed' and
                        reply['response'] == {'schema': 'phase17ao.resident-input-refusal.v1',
                            'raw_frame_sha256': sha(frame), 'refused': True, 'reason': 'invalid_input_frame'},
                        'selected malformed input did not preserve exact refused raw bytes')
            else:
                frontend_start = _json(images, 'frontend/' + action + '/start.json')
                frontend_result = _json(images, 'frontend/' + action + '/result.json')
                require(_stamp(start['started_at_utc']) <= _stamp(frontend_start['started_at_utc']) <=
                        _stamp(frontend_result['completed_at_utc']) <= _stamp(result['completed_at_utc']),
                        'actual frontend action is outside its resident broker lifetime')
                dispatch = _json(images, 'broker/' + action + '/dispatch.json')
                require(frame == canonical(dispatch['intent']) + b'\n' and reply['response'] == dispatch['frontend_response'] and
                        attempts[number]['parse_status'] == 'canonical' and
                        attempts[number]['broker_record_sha256'] == sha(canonical(dispatch)) and
                        dispatch['observer_pid'] == child['child_pid'],
                        'resident input/reply is not the exact original AN broker action')
                charges.append(('frontend-launch-' + action, [0, 1, 0, 0, 0, 0], sha(canonical(frontend_start))))
            charges.append(('input-%04d' % number, [0, 0, 1, len(frame), 0, 0], sha(frame)))
            charges.append(('reply-%04d' % number, [0, 0, 0, 0, len(lines[number + 1]),
                            reply['authority_tls_connections']], sha(lines[number + 1])))
        charges.append(('resident-stopped', [0, 0, 0, 0, len(lines[-1]), 0], sha(lines[-1])))
        new_workers = case['worker_grants'] if index == 0 else []
        if new_workers:
            charges.append(('observed-worker-launches', [0, len(new_workers), 0, 0, 0, 0], sha(canonical(new_workers))))
        grant_events = [event for event in main_events if event['kind'] == 'charge' and
                        event['payload']['grant']['grant_sha256'] == grant['grant_sha256']]
        require([(event['payload']['event_id'], event['payload']['delta'], event['payload']['evidence_sha256'])
                 for event in grant_events] == charges, 'service ledger charges differ from original process and byte receipts')
        all_charge_events.extend(event['hash'] for event in grant_events)
        expected_event_kinds += ['open', 'reserve', 'launch'] + ['charge'] * len(charges) + ['finish']
        used = [1, 2 + len(actions) + len(new_workers), summary['counters']['input_attempts'],
                summary['counters']['request_bytes'], summary['counters']['response_bytes'],
                summary['counters']['authority_tls_connections']]
        closeout_name = 'budget/' + name + '-closeout.json'
        closeout = _json(images, closeout_name)
        require(closeout == {'schema': 'phase17ao.service-lifetime-closeout.v1',
            'lifetime_id': name, 'commission_sha256': pin, 'grant_sha256': grant['grant_sha256'],
            'config_sha256': config_pin, 'observer_pid': start['observer_pid'],
            'observed_at_utc': closeout['observed_at_utc'], 'resident_pid': child['child_pid'],
            'authority_pid': authority_child['child_pid'], 'frontend_actions': actions,
            'new_worker_grants': new_workers, 'resident_counters': summary['counters'], 'used': used,
            'resident_result_sha256': sha(canonical(result)), 'authority_result_sha256': sha(canonical(authority_result)),
            'authority_export_sha256': sha(images['authority/' + name + '/export.json']),
            'reservation_refunded': False, 'complete_resource_accounting': False},
            'service closeout does not reconstruct exact original work')
        closed = main_checked['state']['closed'][index]
        require(closed['grant'] == grant and closed['outcome'] == 'completed' and closed['used'] == used and
                closed['evidence_sha256'] == sha(canonical(closeout)) and
                _stamp(authority_result['completed_at_utc']) <= _stamp(closeout['observed_at_utc']),
                'permanent ledger closeout is not bound to original completed processes')
        last_action = _json(images, 'broker/' + actions[-1] + '/dispatch.json')
        require(stopped['state_sha256'] == sha(canonical(last_action['state_after'])) and
                stopped['anchor_sha256'] == sha(canonical(last_action['anchor_after'])),
                'resident stopped against another retained broker/anchor state')
        expected_files.update(observed + '/' + n for n in
            ('start.json', 'child.json', 'stdin.jsonl', 'stdout.jsonl', 'stderr.txt', 'result.json'))
        expected_files.update(native + '/' + n for n in ('config.json', 'launch-owner.json', 'ready.json', 'stopped.json'))
        expected_files.update((prelaunch_name, pre_observation_name, closeout_name))
        services.append({'child_pid': child['child_pid'], 'invocation_id': start['invocation_id'],
            'config_sha256': config_pin, 'used': used, 'grant': grant, 'counters': summary['counters']})
    require([event['kind'] for event in main_events] == expected_event_kinds + ['deny'] and
            main_checked['summary']['lifetimes_reserved'] == main_checked['summary']['lifetimes_closed'] == 2 and
            main_checked['summary']['epochs'] == 2 and main_checked['summary']['budget_denials'] == 1 and
            main_checked['summary']['pending_retained'] is False and
            main_checked['state']['reserved'] == commission['total_budget'] and
            main_checked['state']['used_lifetime_ids'] == ['lifetime-0', 'lifetime-1'],
            'selected full service lifecycle history differs')
    denial = _json(images, 'budget/budget-denial.json'); last = main_events[-1]
    require(denial['schema'] == 'phase17ao.service-budget-denial.v1' and
            denial['before_cursor'] == last['before_cursor'] and denial['after_cursor'] == main['final_cursor'] and
            denial['requested_lifetime_id'] == last['payload']['grant']['lifetime_id'] == 'lifetime-2-denied' and
            denial['processes_launched'] == 0 and denial['reserved'] == commission['total_budget'] and
            denial['error_type'] == 'ResourceExhausted' and
            denial['error_message'] == 'prepaid service lifetime budget exhausted before process launch',
            'aggregate service budget denial differs')
    interrupted = _json(images, 'budget/interrupted.json')
    control = lifecycle.verify_evidence(interrupted, expected_commission_sha256=pin)
    require(interrupted['commission'] == commission and [e['kind'] for e in interrupted['events']] ==
            ['provision', 'open', 'reserve'] and control['state']['pending']['phase'] == 'reserved' and
            control['state']['reserved'] == LIFETIME_ENVELOPE and control['state']['closed'] == [],
            'isolated interrupted reservation was refunded, launched or reinterpreted')
    refused = _json(images, 'budget/interruption-refusal.json')
    require(refused['schema'] == 'phase17ao.interrupted-lifetime-control.v1' and
            refused['evidence_sha256'] == sha(canonical(interrupted)) and refused['isolated_control'] is True and
            refused['processes_launched'] == 0 and refused['reservation_refunded'] is False,
            'interruption control scope differs')
    error_type = error_message = None
    try:
        lifecycle._transition(commission, control['state'], control['cursor'], 'open',
                              {'owner_nonce': refused['attempted_owner_nonce']})
    except ValueError as error:
        error_type, error_message = type(error).__name__, str(error)
    require(error_type is not None and (refused['error_type'], refused['error_message']) == (error_type, error_message),
            'interrupted reopen was not the exact intended refusal')
    return services, expected_files


def formal_projection(packet, root):
    images = _images(packet)
    from .service_lifecycle_lean import projection_from_evidence
    return projection_from_evidence(_json(images, 'budget/main.json'),
        _json(images, 'budget/interrupted.json'),
        interrupted_reopen_owner=_json(images, 'budget/interruption-refusal.json')['attempted_owner_nonce'])



def verify_packet_native(packet, root):
    images = _images(packet); case = packet['cases'][0]
    exact(case, {'name', 'commission', 'authority_commission', 'certificates',
                 'root_provision_sha256', 'evidence', 'native_boots', 'worker_grants'})
    commission, authority_commission = case['commission'], case['authority_commission']
    pin = case['root_provision_sha256']; broker_pin = broker_api.commission_digest(commission)
    authority_pin = transport.commission_digest(authority_commission)
    transport.validate_commission(authority_commission, expected_commission_sha256=authority_pin,
        expected_root_pin=pin, source_root=root)
    broker_api.validate_commission(commission, expected_commission_sha256=broker_pin, source_root=root)
    require(commission['authority_commission_sha256'] == authority_pin and commission['root_provision_sha256'] == pin and
            commission['server_certificate_sha256'] == authority_commission['server_certificate_sha256'] and
            commission['client_certificate_sha256'] == authority_commission['client_certificate_sha256'],
            'broker/authority commissioning join differs')
    physical = _pkis(images, case)
    root_policy = Policy.from_json(case['evidence']['provision']['policy'])
    _same(commission['accounting_coverage'], accounting.reference_coverage(root_policy.cost_limit),
          'reference accounting allowance differs from actual durable authority policy')
    expected_profiles = {role: isolation.launch_profile(role, platform_name='linux' if packet['platform'] == 'Linux' else 'win32')
                         for role in ('frontend', 'worker')}
    _same(commission['launch_profile'], expected_profiles, 'commission/platform profile differs')
    headers = [row['event'] for row in case['evidence']['entries']]
    require(len(headers) == 10 and [h['kind'] for h in headers] ==
            ['provision', 'reopen', 'reserve', 'launch', 'complete', 'reserve', 'launch', 'complete', 'reopen', 'deny'],
            'selected original AL event sequence differs')
    transport.verify_headers(headers, root_pin=pin)
    initial = _json(images, 'provisioning/commissioning.json')
    exact(initial, {'commission', 'commission_sha256', 'authority_commission', 'authority_commission_sha256',
        'root_provision_sha256', 'initial_anchor', 'initial_broker', 'private_keys_published',
        'independent_production_issuer_established'})
    require(initial['commission'] == commission and initial['commission_sha256'] == broker_pin and
            initial['authority_commission'] == authority_commission and initial['authority_commission_sha256'] == authority_pin and
            initial['root_provision_sha256'] == pin and initial['private_keys_published'] is False and
            initial['independent_production_issuer_established'] is False, 'original commissioning differs')
    broker_api.validate_anchor(initial['initial_anchor'], commission)
    broker_api.validate_state(initial['initial_broker'], commission)
    require(initial['initial_anchor']['headers'] == initial['initial_broker']['headers'] == headers[:1] and
            initial['initial_anchor']['pending'] is None and initial['initial_anchor']['resolved'] == [] and
            initial['initial_broker']['pending'] is None and initial['initial_broker']['consumed_nonces'] == [] and
            initial['initial_broker']['completed'] == [], 'trusted initialization was not the original provision prefix')
    protected = [physical / name for name in ('root', 'private', 'broker-bundle', 'broker-state', 'campaign-native', 'lifecycle-state', 'service-configs')]
    resident_services, ao_files = verify_service_native(packet, root, physical)
    expected_files = {'provisioning/pki.json', 'provisioning/commissioning.json'} | ao_files
    servers = []; services = []; all_ids = [item['invocation_id'] for item in resident_services]; python_identity = None
    for index, name in enumerate(case['native_boots']):
        directory = 'authority/' + name
        start, child, result = _process(images, directory, root, 'authority')
        all_ids.append(start['invocation_id'])
        command = start['command']
        require(type(command) is list and command[1:6] == ['-I', '-S', '-B', '-u', str(Path(root) / SERVICE)],
                'authority entrypoint differs')
        identity = command[0], start['python_sha256']
        if python_identity is None: python_identity = identity
        require(identity == python_identity, 'authority interpreter changed')
        wanted = [command[0], '-I', '-S', '-B', '-u', str(Path(root) / SERVICE),
            '--directory', str(physical / 'root'), '--commission', str(physical / 'commission.json'),
            '--commission-pin', authority_pin, '--root-pin', pin, '--boot-nonce', _nonce('boot-' + str(index)),
            '--ca-file', str(physical / 'private/ca.pem'), '--server-cert', str(physical / 'private/server.pem'),
            '--server-key', str(physical / 'private/server.key'),
            '--native-directory', str(physical / 'campaign-native' / directory / 'transport'),
            '--export', str(physical / 'exports' / (name + '.json'))]
        for target in protected: wanted += ['--protected-path', str(target)]
        require(command == wanted and start['boot_nonce'] == _nonce('boot-' + str(index)) and
                start['commission_sha256'] == authority_pin and start['root_provision_sha256'] == pin,
                'fixed administrative authority arguments differ')
        require(images[directory + '/stdin.jsonl'] == canonical({'operation': 'stop'}) + b'\n',
                'unexpected administrative command')
        lines = images[directory + '/stdout.jsonl'].splitlines(keepends=True)
        require(len(lines) == 2 and all(line.endswith(b'\n') for line in lines), 'authority ready/stop records required')
        ready, stopped = [load_json_strict(line[:-1], require_canonical=True) for line in lines]
        exact(ready, {'schema', 'pid', 'address', 'commission_sha256', 'root_provision_sha256', 'cursor'})
        exact(stopped, {'schema', 'pid', 'export_sha256', 'connections'})
        count = 8 if index == 0 else 10
        expected_export = {**case['evidence'], 'entries': case['evidence']['entries'][:count],
                           'final_cursor': transport.event_cursor(headers[count - 1])}
        require(_json(images, directory + '/export.json') == expected_export and
                result['export_sha256'] == stopped['export_sha256'] == sha(images[directory + '/export.json']),
                'authority export differs from retained exact prefix')
        require(ready['schema'] == 'phase17an.authority-ready.v1' and stopped['schema'] == 'phase17an.authority-stopped.v1' and
                ready['pid'] == stopped['pid'] == child['child_pid'] and ready['commission_sha256'] == authority_pin and
                ready['root_provision_sha256'] == pin and ready['cursor'] == transport.event_cursor(headers[1 if index == 0 else 8]),
                'authority readiness identity differs')
        require(type(ready['address']) is list and len(ready['address']) == 2 and ready['address'][0] == '127.0.0.1' and
                type(ready['address'][1]) is int and 0 < ready['address'][1] <= 65535, 'fixed TLS address differs')
        records = _tls_records(images, directory + '/transport/')
        require(type(stopped['connections']) is int and stopped['connections'] == len(records) == (3 if index == 0 else 2),
                'authority connection inventory differs')
        for path, record in records:
            require(record['role'] == 'server' and record['pid'] == child['child_pid'] and
                    _stamp(start['started_at_utc']) <= _stamp(record['started_at_utc']) <=
                    _stamp(record['completed_at_utc']) <= _stamp(result['completed_at_utc']), 'TLS authority lifetime join differs')
            expected_files.update((path, path.replace('/result-', '/start-')))
        servers.extend(records); services.append((start, child, result, ready))
        expected_files.update(directory + '/' + n for n in
                              ('start.json', 'child.json', 'stdin.jsonl', 'stdout.jsonl', 'stderr.txt', 'result.json', 'export.json'))
    require(_stamp(services[0][2]['completed_at_utc']) <= _stamp(services[1][0]['started_at_utc']), 'authority lifetimes overlap')
    previous_state, previous_anchor = initial['initial_broker'], initial['initial_anchor']
    clients = []; boundary_count = 0; actions = {}; previous_frontend_end = None
    for action in ACTIONS:
        directory = 'frontend/' + action; broker_directory = 'broker/' + action
        start, child, result = _process(images, directory, root, 'frontend')
        all_ids.append(start['invocation_id'])
        service_index = 0 if action in ACTIONS[:9] else 1
        service = services[service_index]
        require(_stamp(service[0]['started_at_utc']) <= _stamp(start['started_at_utc']) <=
                _stamp(result['completed_at_utc']) <= _stamp(service[2]['completed_at_utc']),
                'frontend lifetime is outside its authority lifetime')
        require(previous_frontend_end is None or previous_frontend_end <= _stamp(start['started_at_utc']),
                'sequential frontend lifetimes overlap')
        previous_frontend_end = _stamp(result['completed_at_utc'])
        expected_files.update(directory + '/' + n for n in ('start.json', 'child.json', 'target.json', 'stdin.jsonl', 'stdout.jsonl', 'stderr.txt', 'result.json'))
        expected_files.add(broker_directory + '/dispatch.json')
        require(start['action'] == action and start['commission_sha256'] == broker_pin and
                start['root_provision_sha256'] == pin and start['python_sha256'] == python_identity[1] and
                start['entrypoint_command'] == [python_identity[0], '-I', '-S', '-B', '-u', str(Path(root) / FRONTEND)],
                'fixed low-authority frontend command differs')
        spec = start['isolation_specification']
        # Rebuild exact executable and namespace profile without starting a process.
        isolation._validate_specification(spec)
        require(isolation._prefix(spec) == start['command'], 'frontend exact launch command differs')
        if packet['platform'] == 'Linux':
            recorded_spec = isolation.specification_from_command(start['command'])
            _same(spec, recorded_spec, 'frontend exact isolation specification differs')
        require(spec['profile'] == expected_profiles['frontend'] and spec['repo'] == str(root) and
                spec['command'] == start['entrypoint_command'] and
                spec['scratch_directory'] == str(physical / 'untrusted-scratch' / action) and
                spec['protected_targets'] == [{'path': str(p), 'kind': 'directory'} for p in protected] and
                spec['host_pid'] == start['observer_pid'], 'frontend launch is not the commissioned protected view')
        for path, hashed in spec['readonly_files'].items():
            require(sha(Path(path).read_bytes()) == hashed, 'frontend readonly source/interpreter changed')
        target = _json(images, directory + '/target.json')
        exact(target, {'schema', 'launcher_pid', 'frontend_pid', 'identity_source', 'process_start_ticks', 'namespaces'})
        require(target['schema'] == 'phase17an.frontend-target.v1' and target['launcher_pid'] == child['child_pid'] and
                type(target['frontend_pid']) is int and 0 < target['frontend_pid'] < 2**63 and
                target['frontend_pid'] != start['observer_pid'], 'actual frontend target identity differs')
        lines = images[directory + '/stdout.jsonl'].splitlines(keepends=True)
        if packet['platform'] == 'Linux':
            require(len(lines) == 3, 'frontend boundary/intent/reply framing differs')
            observation = isolation.parse_boundary_frame(lines.pop(0))
            isolation.validate_observation(spec, observation)
            require(target['identity_source'] == 'trusted_parent_proc_and_preexec_binding' and
                    target['process_start_ticks'] == observation['process_start_ticks'] and
                    target['namespaces'] == observation['namespaces'], 'actual frontend pre-exec identity join differs')
            _same(observation, _json(images, directory + '/boundary.json'), 'retained frontend boundary differs')
            expected_files.add(directory + '/boundary.json'); boundary_count += 1
        else:
            require(len(lines) == 2 and target['identity_source'] == 'direct_native_child' and
                    target['frontend_pid'] == child['child_pid'] and target['process_start_ticks'] is None and
                    target['namespaces'] is None, 'unconfined frontend identity or framing differs')
        original_inputs = images[directory + '/stdin.jsonl'].splitlines(keepends=True)
        require(original_inputs == lines and len(lines) == 2 and all(line.endswith(b'\n') for line in lines),
                'actual frontend proposed intent or received reply differs')
        proposed, delivered = [load_json_strict(line[:-1], require_canonical=True) for line in lines]
        outer = _json(images, broker_directory + '/dispatch.json')
        exact(outer, {'schema', 'action', 'observer_pid', 'intent', 'mode', 'abandon_response',
            'state_before', 'anchor_before', 'state_after', 'anchor_after', 'dispatch', 'error_type',
            'error_message', 'frontend_response', 'network_attempts'})
        require(outer['schema'] == 'phase17an.broker-action-observation.v1' and outer['action'] == action and
                outer['observer_pid'] == resident_services[service_index]['child_pid'] and outer['intent'] == proposed == _intent(action, broker_pin) and
                outer['frontend_response'] == delivered and outer['mode'] == ('promotion' if action == 'promotion_denial' else 'reference') and
                outer['abandon_response'] is (action == 'run_abandon'), 'broker original frontend join differs')
        _same(outer['state_before'], previous_state, 'broker state chain differs')
        _same(outer['anchor_before'], previous_anchor, 'protected AM anchor chain differs')
        records = _tls_records(images, broker_directory + '/transport/')
        if action in REFUSALS:
            require(outer['dispatch'] is None and outer['network_attempts'] == 0 and type(outer['network_attempts']) is int and
                    not records and outer['state_after'] == previous_state and outer['anchor_after'] == previous_anchor,
                    'refused frontend intent caused a dispatch or state mutation')
            failure = None
            try: broker_api._admit(previous_state, previous_anchor, proposed, commission, outer['mode'])
            except ValueError as error: failure = type(error).__name__, str(error)
            require(failure == (outer['error_type'], outer['error_message']) and failure is not None,
                    'broker refusal was not its exact intended pre-dispatch rejection')
            _same(delivered, {'schema': 'phase17an.frontend-refusal.v1', 'intent_sha256': sha(canonical(proposed)),
                             'refused': True, 'reason': 'broker_refused'}, 'public refusal differs')
        else:
            dispatch = outer['dispatch']
            checked = broker_api.verify_broker_record(dispatch, commission, source_root=root)
            require(outer['error_type'] is None and outer['error_message'] is None and
                    outer['network_attempts'] == len(records) == 1 and type(outer['network_attempts']) is int,
                    'selected broker operation did not issue exactly one exchange')
            for field in ('intent', 'mode', 'abandon_response', 'state_before', 'state_after', 'anchor_before', 'anchor_after'):
                _same(outer[field], dispatch[field], 'outer and original broker dispatch differ: ' + field)
            _same(delivered, dispatch['response'], 'sanitized reply differs from broker evidence')
            operation_path = broker_directory + '/transport/operation-0000.json'
            operation = _json(images, operation_path)
            _same(dispatch['am_operation'], operation, 'broker AM operation bytes differ')
            require(_stamp(start['started_at_utc']) <= _stamp(operation['started_at_utc']) <=
                    _stamp(operation['completed_at_utc']) <= _stamp(result['completed_at_utc']),
                    'broker operation lifetime is outside its frontend lifetime')
            _same(dispatch['am_exchange'], records[0][1], 'broker TLS exchange bytes differ')
            expected_files.add(operation_path)
            actions[action] = checked
        for path, record in records:
            require(record['role'] == 'client' and record['pid'] == outer['observer_pid'] and
                    record['remote_address'] == service[3]['address'] and
                    _stamp(start['started_at_utc']) <= _stamp(record['started_at_utc']) <=
                    _stamp(record['completed_at_utc']) <= _stamp(result['completed_at_utc']),
                    'credential-bearing broker client identity, address or lifetime differs')
            expected_files.update((path, path.replace('/result-', '/start-'))); clients.append((action, record))
        previous_state, previous_anchor = outer['state_after'], outer['anchor_after']
    require(len(all_ids) == len(set(all_ids)) and len(clients) == len(servers) == 5, 'process or TLS inventory differs')
    unmatched = list(servers)
    for action, client in clients:
        matches = [(path, server) for path, server in unmatched if server['request_frame_hex'] == client['request_frame_hex']]
        require(len(matches) == 1, 'original TLS request does not have one exact server match')
        path, server = matches[0]; unmatched.remove(matches[0])
        service_index = 0 if action in ACTIONS[:9] else 1
        require(path.startswith('authority/' + case['native_boots'][service_index] + '/transport/'),
                'matched TLS server belongs to a different authority lifetime')
        require(client['peer_certificate_sha256'] == authority_commission['server_certificate_sha256'] and
                server['peer_certificate_sha256'] == authority_commission['client_certificate_sha256'] and
                client['peer_pin_matched'] is True and server['peer_pin_matched'] is True and
                client['request_sent'] is True and client['error_type'] is None, 'actual mutual TLS identity differs')
        for endpoint in (client, server):
            require(endpoint['commission_sha256'] == authority_pin and
                    endpoint['root_provision_sha256'] == pin and endpoint['tls_version'] == 'TLSv1.3' and
                    sha(bytes.fromhex(endpoint['peer_certificate_der_hex'])) == endpoint['peer_certificate_sha256'],
                    'actual socket peer certificate or TLS version differs')
        request = _frame(client['request_frame_hex'])
        require(request['commission_sha256'] == authority_pin and request['root_provision_sha256'] == pin,
                'issued wire authority binding differs')
        if action == 'run_abandon':
            require(client['abandoned_response'] is True and client['response_frame_hex'] == '', 'abandoned reply was observed')
        else:
            require(client['abandoned_response'] is False and server['response_sent'] is True and server['error_type'] is None and
                    client['response_frame_hex'] == server['response_frame_hex'], 'original TLS reply pair differs')
        require(bool(server['response_frame_hex']), 'server lost original reply image')
        reply = _frame(server['response_frame_hex'])
        require(reply['request_sha256'] == sha(canonical(request)) and reply['challenge'] == request['challenge'] and
                reply['commission_sha256'] == authority_pin and reply['root_provision_sha256'] == pin and
                reply['operation'] == request['operation'], 'server reply/request binding differs')
        transport.verify_headers(reply['headers'], root_pin=pin)
        require(reply['headers'] == headers[:len(reply['headers'])], 'server reply forked original durable history')
    require(not unmatched and previous_anchor['pending'] is None and previous_state['pending'] is None and
            previous_anchor['headers'] == previous_state['headers'] == headers,
            'final protected state did not reconcile exact authority history')
    require(actions['run_abandon']['pending_retained'] is True and actions['reconcile']['mutation_issued'] is False and
            actions['reconcile']['pending_retained'] is False and actions['aggregate_denial']['outcome'] == 'denied',
            'ambiguity, read-only reconciliation or aggregate denial differs')
    checked = runtime.verify_evidence(case['evidence'], predecessor(str(root)),
                                     expected_root_provision_sha256=pin, source_root=root)
    sessions = checked['snapshot']['sessions']
    require(len(sessions) == len(case['worker_grants']) == 2, 'two actual admitted workers required')
    worker_boundaries = 0; challenge_commitments = []
    for session, grant_hash in zip(sessions, case['worker_grants'], strict=True):
        files = runtime._session_files(session); grant = load_json_strict(files['grant.json'])
        require(grant['grant_hash'] == grant_hash, 'worker grant inventory differs')
        directory = 'workers/' + grant_hash
        raw = {name: images[directory + '/' + name] for name in worker_native.FILES}
        verified = worker_native.verify_native_images(raw, grant, files['sealed_transcript.json'],
                    load_json_strict(files['worker-accounting.json']), source_root=root)
        require(verified == session['native_sha256'], 'actual worker native hashes differ from durable completion')
        expected_files.update(directory + '/' + name for name in worker_native.FILES)
        worker_start = load_json_strict(raw['start.json'], require_canonical=True)
        worker_child = load_json_strict(raw['child.json'], require_canonical=True)
        worker_result = load_json_strict(raw['result.json'], require_canonical=True)
        session_record = load_json_strict(files['session.json'], require_canonical=True)
        challenge = load_json_strict(files['public_challenge.json'], require_canonical=True)
        challenge_commitments.append(challenge['challenge_commitment_hash'])
        all_ids.append(worker_start['invocation_id'])
        require(session_record['controller_pid'] == services[0][1]['child_pid'] and
                session_record['worker_pid'] == worker_child['child_pid'] == worker_result['child_pid'] and
                (worker_start['python_path'], worker_start['python_sha256']) == python_identity and
                _stamp(services[0][0]['started_at_utc']) <= _stamp(worker_start['started_at_utc']) <=
                _stamp(worker_result['completed_at_utc']) <= _stamp(services[0][2]['completed_at_utc']),
                'worker session identity, interpreter or authority lifetime join differs')
        worker_spec = worker_start['isolation_specification']
        require(worker_spec['profile'] == expected_profiles['worker'] and worker_spec['repo'] == str(root) and
                worker_spec['protected_targets'] == [{'path': str(p), 'kind': 'directory'} for p in protected] and
                worker_start['observer_pid'] == services[0][1]['child_pid'] and
                worker_spec['host_pid'] == worker_start['observer_pid'],
                'actual worker differs from commissioned protected view or authority owner')
        for path, hashed in worker_spec['readonly_files'].items():
            require(sha(Path(path).read_bytes()) == hashed, 'worker readonly source/interpreter changed')
        if packet['platform'] == 'Linux': worker_boundaries += 1
    require(len(all_ids) == len(set(all_ids)) and len(set(challenge_commitments)) == 2,
            'native invocation identities or fresh challenge commitments repeat')
    require(set(images) == expected_files, 'original native file inventory has missing or additional records')
    return {'native_files': len(images), 'frontend_boundaries': boundary_count,
            'worker_boundaries': worker_boundaries, 'native_frontend_processes': len(ACTIONS),
            'native_authority_lifetimes': 2, 'native_tls_connections': len(clients),
            'broker_dispatch_refusals': len(REFUSALS), 'actions': actions,
            'native_resident_broker_lifetimes': len(resident_services),
            'resident_input_attempts': sum(item['counters']['input_attempts'] for item in resident_services),
            'malformed_input_refusals': 1, 'permanent_service_reservations': 2,
            'service_budget_denials': 1, 'service_operational_dimensions': list(lifecycle.DIMENSIONS),
            'service_reserved': [2 * n for n in LIFETIME_ENVELOPE],
            'observed_service_usage': [sum(item['used'][i] for item in resident_services) for i in range(6)],
            'isolated_interrupted_reservation_retained': True}

def broker_projection(packet, root):
    """Derive selected semantics from actual checked broker/wire records."""
    case = packet['cases'][0]; commission = case['commission']; images = _images(packet)
    selected = _json(images, 'broker/run_abandon/dispatch.json')['dispatch']
    broker_api.verify_broker_record(selected, commission, source_root=root)
    reconcile = _json(images, 'broker/reconcile/dispatch.json')['intent']
    def cursor(value):
        return {'epoch': value['epoch'], 'serial': value['serial'], 'head': value['root_head']}
    def state(value):
        pending = value['pending']
        return {'commission': value['commission_sha256'], 'root': commission['root_provision_sha256'],
            'current': cursor(transport.event_cursor(value['headers'][-1])),
            'pending': None if pending is None else {'current': cursor(pending['before_cursor']),
                'nonce': pending['intent']['nonce'], 'credits': pending['intent']['credits']},
            'consumed': value['consumed_nonces']}
    fixed = {'identity': broker_api.commission_digest(commission),
        'authority_commission': commission['authority_commission_sha256'],
        'root': commission['root_provision_sha256'],
        'broker_source': commission['source_identity']['implementation_sha256'],
        'controller_source': commission['controller_source_sha256'],
        'objective': commission['objective_policy_sha256'], 'evaluator': commission['evaluator_protocol_sha256'],
        'accounting_policy': commission['accounting_policy_sha256'],
        'max_credits': commission['max_credits'], 'max_intents': commission['max_intents']}
    # validate_commission recomputes these identities from actual executing source
    # and fixed policies. A frontend-provided Boolean is never substituted.
    broker_api.validate_commission(commission, expected_commission_sha256=fixed['identity'], source_root=root)
    request = selected['issued_request']; intent = selected['intent']; coverage = commission['accounting_coverage']
    value = {'commission': fixed,
        'runtime': {k: fixed[k] for k in ('broker_source', 'controller_source', 'objective', 'evaluator', 'accounting_policy')},
        'first_state': state(selected['state_before']),
        'run_intent': {'operation': intent['operation'], 'nonce': intent['nonce'], 'credits': intent['credits']},
        'first_issued': {'authority_commission': request['commission_sha256'], 'root': request['root_provision_sha256'],
            'current': cursor(request['expected_cursor']), 'operation': request['operation'],
            'nonce': request['request_nonce'], 'credits': request['credits']},
        'pending_state': state(selected['admitted_state']),
        'reconcile_intent': {'operation': reconcile['operation'], 'nonce': reconcile['nonce'], 'credits': 0},
        'required_categories': list(accounting.CATEGORIES), 'coverage': coverage['coverage'], 'budget': coverage['budget']}
    from .protected_authority_lean import validate_projection
    return validate_projection(value)


def service_accounting_closeout(packet):
    images = _images(packet)
    evidence = _json(images, 'budget/main.json')
    checked = lifecycle.verify_evidence(evidence, expected_commission_sha256=evidence['commission_sha256'])
    return {'schema': 'phase17ao.operational-accounting-closeout.v1',
        'dimensions': list(lifecycle.DIMENSIONS), 'commission_sha256': evidence['commission_sha256'],
        'ledger_sha256': sha(canonical(evidence)), 'reserved': checked['state']['reserved'],
        'observed': [sum(closed['used'][i] for closed in checked['state']['closed']) for i in range(6)],
        'closed_lifetimes': [closed['grant']['lifetime_id'] for closed in checked['state']['closed']],
        'lifetime_closeout_sha256': [closed['evidence_sha256'] for closed in checked['state']['closed']],
        'components_have_distinct_units': True, 'physical_total': None,
        'isolated_interruption_control_included_in_campaign_spend': False,
        'complete_resource_accounting': False}


def accounting_closeout(packet, root):
    """Join actual AL declared cost to the explicit unresolved coverage inventory."""
    case = packet['cases'][0]
    checked = runtime.verify_evidence(case['evidence'], predecessor(str(root)),
        expected_root_provision_sha256=case['root_provision_sha256'], source_root=root)
    evidence = []
    for session in checked['snapshot']['sessions']:
        raw = bytes.fromhex(session['files_hex']['worker-accounting.json'])
        value = load_json_strict(raw)
        evidence.append({'worker_accounting_sha256': sha(raw), 'grant_hash': value['grant_hash'],
                         'declared_cost': value['charged_cost']})
    coverage = load_json_strict(canonical(case['commission']['accounting_coverage']), require_canonical=True)
    coverage['coverage'][0]['observed'] = sum(row['declared_cost'] for row in evidence)
    coverage['coverage'][0]['meter'] = sha(canonical(evidence))
    return {'schema': 'phase17ao.selected-accounting-closeout.v1', 'worker_evidence': evidence,
            'coverage': coverage, 'report': accounting.coverage_report(coverage),
            'promotion_admission': accounting.admission_report(coverage, mode='promotion'),
            'service_operational_accounting': service_accounting_closeout(packet),
            'complete_resource_accounting': False}


def summarize(packet, root):
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE and
            packet['retained_an_execution_sha256'] == AN_EXECUTION_SHA and packet['scope'] == SCOPE and
            packet['platform'] in ('Linux', 'Windows') and type(packet['cases']) is list and len(packet['cases']) == 1 and
            packet['cases'][0]['name'] == CASE_NAME and packet['cases'][0]['native_boots'] == ['lifetime-0', 'lifetime-1'] and
            set(packet['claims']) == set(FALSE_CLAIMS) and all(value is False for value in packet['claims'].values()),
            'AO packet scope or inventory differs')
    native = verify_packet_native(packet, root)
    case = packet['cases'][0]
    checked = runtime.verify_evidence(case['evidence'], predecessor(str(root)),
        expected_root_provision_sha256=case['root_provision_sha256'], source_root=root)
    state = checked['state']
    # The original AL verifier owns the declared reservation and completion rules.
    return {'cases': [{'name': CASE_NAME, 'completed_sessions': 2, 'denials': 1,
        'epoch': case['evidence']['final_cursor']['epoch'], 'root_events': len(case['evidence']['entries']),
        'pending_retained': checked['snapshot']['pending'] is not None,
        'reserved': list(state.reserved), 'reserved_cost': state.charged_cost, 'status': state.status}],
        'fresh_worker_sessions': 2, 'fresh_live_challenges': 2,
        'completed_sessions': 2, 'denied_sessions': 1, 'pending_sessions': 0, 'permanent_reservations': 2,
        **{k: native[k] for k in ('native_files', 'frontend_boundaries', 'worker_boundaries',
            'native_frontend_processes', 'native_authority_lifetimes', 'native_tls_connections', 'broker_dispatch_refusals',
            'native_resident_broker_lifetimes', 'resident_input_attempts', 'malformed_input_refusals',
            'permanent_service_reservations', 'service_budget_denials', 'service_operational_dimensions',
            'service_reserved', 'observed_service_usage', 'isolated_interrupted_reservation_retained')},
        'abandoned_responses': 1, 'reconciliations_without_worker_reissue': 1,
        'protected_namespace_profile': 'observed_linux_frontend_and_workers' if packet['platform'] == 'Linux' else 'not_exercised_on_this_platform',
        'credentials_supplied_via_frontend_protocol': False,
        'retained_anchor_supplied_via_frontend_protocol': False,
        'frontend_credential_access_denials_observed': packet['platform'] == 'Linux',
        'old_proof_campaigns_rerun': False, 'old_acceptance_reinterpreted': False,
        'complete_resource_accounting': False, 'independently_protected_deployment_established': False}


class PreparedServiceLifecycle:
    def __init__(self, raw, root=SOURCE_ROOT):
        require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'bounded original AO packet bytes required')
        self.packet = load_json_strict(raw, require_canonical=True)
        exact(self.packet, {'schema', 'policy', 'base_commit', 'retained_an_execution_sha256', 'scope', 'platform',
            'cases', 'native_images', 'claims', 'summary', 'formal_projection', 'accounting_closeout'})
        retained_baseline(root)
        require(self.packet['summary'] == summarize(self.packet, root), 'selected AO summary differs')
        require(self.packet['formal_projection'] == formal_projection(self.packet, root),
                'formal projection differs from original broker/wire records')
        require(self.packet['accounting_closeout'] == accounting_closeout(self.packet, root),
                'accounting closeout differs from admitted worker evidence')
        self.packet_bytes = raw


def evidence_images(packet):
    require(type(packet['cases']) is list and len(packet['cases']) == 1, 'one selected durable export required')
    return {CASE_NAME + '.json': canonical(packet['cases'][0]['evidence'])}


def verify_all_native(directory, packet, root=SOURCE_ROOT):
    directory = Path(directory); _no_links(directory)
    expected = _images(packet); actual = {}
    for path in sorted(directory.rglob('*')):
        _no_links(path)
        if path.is_file():
            name = _relative(path.relative_to(directory).as_posix())
            require(path.stat().st_size <= MAX_BYTES, 'oversized original native file')
            actual[name] = path.read_bytes()
    require(actual == expected, 'retained native filesystem differs from exact packet bytes')
    verify_packet_native(packet, root)
    return {name: sha(raw) for name, raw in expected.items()}
