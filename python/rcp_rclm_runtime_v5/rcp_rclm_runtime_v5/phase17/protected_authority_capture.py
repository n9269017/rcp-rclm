"""Original AN protected-broker and confined-worker reference capture.

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
from . import authority_accounting as accounting
from . import protected_authority_isolation as isolation
from . import protected_campaign_native as worker_native
from .authority_transport_pki import generate_reference_pki
from .durable_campaign_capture import predecessor
from .controller_durable_authority import FALSE_CLAIMS
from .resource_ledger import Policy, canonical, sha, require, exact, full_grammar_policy, _no_links
from .authenticated_authority_capture import _tls_records, _frame, _stamp

BASE = '7a3bc388309e9184012a1f772ea19727882abd07'
SOURCE_ROOT = Path(__file__).resolve().parents[4]
SCHEMA = 'rcp-rclm.phase17an.protected-authority-packet.v1'
POLICY = 'phase17an.protected-reference-campaign.v1'
AM_EXECUTION = 'artifacts/development/phase17am/op-028a865724dc/gate/execution.json'
AM_EXECUTION_SHA = 'f558faeb7bf88e7ad3ae415578ba812df76f2b53fdb2a2109bd0f4d4ae582cc2'
MAX_BYTES = 128 * 1024 * 1024
MAX_NATIVE_FILES = 1024
SERVICE = 'scripts/phase17_protected_authority_service.py'
FRONTEND = 'scripts/phase17_protected_frontend.py'
NATIVE_SCHEMA = 'phase17an.process-observation.v1'
CASE_NAME = 'protected_campaign'
ACTIONS = ('initial_read', 'run_one', 'replayed_nonce', 'forbidden_operation',
           'extra_field', 'wrong_commission', 'promotion_denial', 'run_abandon',
           'blocked_retry', 'reconcile', 'aggregate_denial')
REFUSALS = ('replayed_nonce', 'forbidden_operation', 'extra_field',
            'wrong_commission', 'promotion_denial', 'blocked_retry')
SCOPE = {
    'deployment': 'locally_commissioned_protected_broker_reference',
    'broker': 'trusted broker owns TLS credential and independently initialized retained anchors; frontend receives bounded intents/replies only',
    'frontend': 'reference run-request frontend; inherited present-prefix controller remains inside authority',
    'linux_boundary': 'private user/mount/PID/IPC/UTS/network namespaces, no capabilities or authority mounts; actual evaluator workers use same restricted role-specific profile',
    'windows_boundary': 'explicit unconfined protocol reference; no Linux boundary credit',
    'currentness': 'protected prefix under trusted host/kernel and retention premises; joint rollback and cloning remain external',
    'accounting': 'fixed 14-category coverage contract; unknown categories block promotion admission and are never zero-priced',
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
    return sha(('Phase17AN/' + purpose).encode())


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
            and path.parts[0] in ('authority', 'frontend', 'broker', 'workers', 'provisioning'),
            'native path outside fixed inventory roots')
    return name


def retained_baseline(root):
    raw = (Path(root) / AM_EXECUTION).read_bytes()
    require(sha(raw) == AM_EXECUTION_SHA, 'exact completed AM execution required')
    record = load_json_strict(raw, require_canonical=False)
    require(record['completed'] is True and
            record['source_commit'] == '028a865724dcbf4e1dde8e39b06d84fa72f52d33' and
            record['source_tree'] == '3c41983b2306d115a00ff74572d1d92a859fb0cd' and
            record['authenticated_authority_transport_checked'] is True and
            record['pinned_authority_client_checked'] is True and
            set(record['claims']) == set(FALSE_CLAIMS) and all(v is False for v in record['claims'].values()),
            'completed AM scope differs')
    for name, hashed in record['source_sha256'].items():
        require(sha((Path(root) / name).read_bytes()) == hashed, 'inherited AM source changed: ' + name)
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
              port, protected_paths):
    """Launch an actual low-authority process; broker stays outside its view."""
    native = native_root / 'frontend' / action
    native.mkdir(parents=True, exist_ok=False)
    broker_native = native_root / 'broker' / action
    broker_native.mkdir(parents=True, exist_ok=False)
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
    client = transport.AuthorityTransportClient(authority_commission,
        expected_commission_sha256=authority_pin, expected_root_pin=root_pin,
        anchor_path=state / 'anchor.json', host='127.0.0.1', port=port,
        ca_file=bundle / 'ca.pem', client_cert=bundle / 'client.pem',
        client_key=bundle / 'client.key', native_directory=broker_native / 'transport')
    broker = broker_api.ProtectedAuthorityBroker(commission, expected_commission_sha256=pin,
        client=client, state_path=state / 'broker.json', source_root=root)
    before_state, before_anchor = _load(state / 'broker.json'), _load(state / 'anchor.json')
    begin = time.monotonic_ns()
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
        try:
            dispatch = broker.dispatch(actual_intent, abandon_response=abandoned, mode=mode)
            public = dispatch['response']
        except ValueError as error:
            error_name, error_message = type(error).__name__, str(error)
            dispatch = broker.last_record
            public = {'schema': 'phase17an.frontend-refusal.v1',
                      'intent_sha256': sha(canonical(actual_intent)), 'refused': True, 'reason': 'broker_refused'}
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
    record = {'schema': 'phase17an.broker-action-observation.v1', 'action': action,
        'observer_pid': os.getpid(), 'intent': intent, 'mode': mode, 'abandon_response': abandoned,
        'state_before': before_state, 'anchor_before': before_anchor,
        'state_after': _load(state / 'broker.json'), 'anchor_after': _load(state / 'anchor.json'),
        'dispatch': dispatch, 'error_type': error_name, 'error_message': error_message,
        'frontend_response': public, 'network_attempts': client.sequence}
    _write(broker_native / 'dispatch.json', canonical(record))
    return record


def prepare_protected_authority(root, physical):
    root, physical = Path(root).absolute(), Path(physical).absolute()
    require(not physical.exists(), 'new AN physical workspace required'); physical.mkdir(parents=True)
    retained_baseline(root); parent = predecessor(str(root))
    native_root = physical / 'campaign-native'; native_root.mkdir()
    one = full_grammar_policy(len(parent.accepted_programs), candidate_limit=2)
    policy = Policy(tuple(2 * value for value in one.limits), 2 * one.cost_limit)
    provisioned = runtime.provision_root(physical / 'root', root, parent, policy,
        authority_id='phase17an.reference.protected_campaign', nonce=secrets.token_hex(32))
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
    protected_paths = [physical / name for name in ('root', 'private', 'broker-bundle', 'broker-state', 'campaign-native')]
    boots = []
    for index in (0, 1):
        name = 'lifetime-' + str(index); exported = physical / 'exports' / (name + '.json')
        authority = NativeAuthority(root, physical / 'root', native_root / 'authority' / name,
            exported, pki, commission_file, authority_pin, pin, _nonce('boot-' + str(index)), protected_paths)
        try:
            for action in (ACTIONS[:9] if index == 0 else ACTIONS[9:]):
                _frontend(root, physical, native_root, action=action, commission=commission,
                    authority_commission=authority_commission, port=authority.ready['address'][1],
                    protected_paths=protected_paths)
        finally: authority.close()
        boots.append(name)
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
        'retained_am_execution_sha256': AM_EXECUTION_SHA, 'scope': SCOPE, 'platform': platform.system(),
        'cases': [{'name': CASE_NAME, 'commission': commission, 'authority_commission': authority_commission,
            'certificates': {name: Path(path).read_bytes().hex() for name, path in pki['public'].items()},
            'root_provision_sha256': pin, 'evidence': evidence, 'native_boots': boots, 'worker_grants': grants}],
        'native_images': images, 'claims': {name: False for name in FALSE_CLAIMS}}
    packet['summary'] = summarize(packet, root)
    packet['formal_projection'] = formal_projection(packet, root)
    packet['accounting_closeout'] = accounting_closeout(packet, root)
    prepared = PreparedProtectedAuthority(canonical(packet), root)
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
    protected = [physical / name for name in ('root', 'private', 'broker-bundle', 'broker-state', 'campaign-native')]
    expected_files = {'provisioning/pki.json', 'provisioning/commissioning.json'}
    servers = []; services = []; all_ids = []; python_identity = None
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
                outer['observer_pid'] == start['observer_pid'] and outer['intent'] == proposed == _intent(action, broker_pin) and
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
            'broker_dispatch_refusals': len(REFUSALS), 'actions': actions}

def formal_projection(packet, root):
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
    return {'schema': 'phase17an.selected-accounting-closeout.v1', 'worker_evidence': evidence,
            'coverage': coverage, 'report': accounting.coverage_report(coverage),
            'promotion_admission': accounting.admission_report(coverage, mode='promotion'),
            'complete_resource_accounting': False}


def summarize(packet, root):
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE and
            packet['retained_am_execution_sha256'] == AM_EXECUTION_SHA and packet['scope'] == SCOPE and
            packet['platform'] in ('Linux', 'Windows') and type(packet['cases']) is list and len(packet['cases']) == 1 and
            packet['cases'][0]['name'] == CASE_NAME and packet['cases'][0]['native_boots'] == ['lifetime-0', 'lifetime-1'] and
            set(packet['claims']) == set(FALSE_CLAIMS) and all(value is False for value in packet['claims'].values()),
            'AN packet scope or inventory differs')
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
            'native_frontend_processes', 'native_authority_lifetimes', 'native_tls_connections', 'broker_dispatch_refusals')},
        'abandoned_responses': 1, 'reconciliations_without_worker_reissue': 1,
        'protected_namespace_profile': 'observed_linux_frontend_and_workers' if packet['platform'] == 'Linux' else 'not_exercised_on_this_platform',
        'credentials_supplied_via_frontend_protocol': False,
        'retained_anchor_supplied_via_frontend_protocol': False,
        'frontend_credential_access_denials_observed': packet['platform'] == 'Linux',
        'old_proof_campaigns_rerun': False, 'old_acceptance_reinterpreted': False,
        'complete_resource_accounting': False, 'independently_protected_deployment_established': False}


class PreparedProtectedAuthority:
    def __init__(self, raw, root=SOURCE_ROOT):
        require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'bounded original AN packet bytes required')
        self.packet = load_json_strict(raw, require_canonical=True)
        exact(self.packet, {'schema', 'policy', 'base_commit', 'retained_am_execution_sha256', 'scope', 'platform',
            'cases', 'native_images', 'claims', 'summary', 'formal_projection', 'accounting_closeout'})
        retained_baseline(root)
        require(self.packet['summary'] == summarize(self.packet, root), 'selected AN summary differs')
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
