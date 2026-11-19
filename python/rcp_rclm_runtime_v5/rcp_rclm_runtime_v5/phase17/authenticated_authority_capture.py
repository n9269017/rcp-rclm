"""Original AM authenticated campaign capture and process-free reconstruction.

The public packet retains original observation bytes, never private TLS keys.
An accepted packet is not an attestation of its observer, kernel or physical disk.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import platform
import queue
import shutil
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import uuid

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import authority_transport as transport
from . import durable_campaign as runtime
from .authority_transport_pki import generate_reference_pki, certificate_der
from .durable_campaign_capture import predecessor
from .durable_campaign_native import verify_native_records, FILES as WORKER_FILES, _stamp
from .controller_durable_authority import FALSE_CLAIMS
from .resource_ledger import Policy, canonical, sha, require, exact, full_grammar_policy, _no_links

BASE = 'ce595d33e68ddd22f16a624d1a1c5d6fa26abd4c'
SOURCE_ROOT = Path(__file__).resolve().parents[4]
SCHEMA = 'rcp-rclm.phase17am.authenticated-authority-packet.v1'
POLICY = 'phase17am.authenticated-reference-campaign.v1'
AL_EXECUTION = 'artifacts/development/phase17al/op-643c0ad947d5/gate/execution.json'
AL_EXECUTION_SHA = 'e603c11f33bf9a8bbc4ac5fc979ca6881930612278333af360a3de7854e288b7'
MAX_BYTES = 128 * 1024 * 1024
MAX_NATIVE_FILES = 1024
SERVICE = 'scripts/phase17_authority_transport_service.py'
DRIVER = 'scripts/phase17_authority_transport_probe.py'
NATIVE_SCHEMA = 'phase17am.process-observation.v1'
CASE_NAME = 'authenticated_campaign'
ACTIONS = ('initial_read', 'run_one', 'stale', 'replayed_nonce', 'forbidden_operation',
           'extra_field', 'run_abandon', 'blocked_retry', 'reconcile', 'aggregate_denial')
SCOPE = {
    'deployment': 'authenticated_local_reference',
    'transport': 'dedicated-CA TLS1.3 with exact observed server/client certificate pins',
    'client': 'independently provisioned retained header prefix; write-ahead pending and read-only reconciliation',
    'controller_isolation': 'optional observed Linux namespace profile; Windows does not inherit it',
    'anchor_protection': 'trusted client storage; writable by its principal, not an independent immutable monitor',
    'worker': 'unchanged AL fixed evaluator; no new worker sandbox claim',
    'currentness': 'prefix continuity relative to retained trusted anchor; joint rollback and clones remain external',
    'accounting': 'unchanged nonrefundable AL declared reference-work tariff',
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
    return sha(('Phase17AM/' + purpose).encode())


def _write(path, raw):
    transport._new(path, raw)


def _same(a, b, message):
    require(canonical(a) == canonical(b), message)


def _relative(name):
    require(type(name) is str and 0 < len(name) <= 500 and '\\' not in name and
            ':' not in name and '\x00' not in name, 'bounded relative native name required')
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.as_posix() == name and '..' not in path.parts and
            path.parts[0] in ('authority', 'client', 'workers', 'provisioning'),
            'native path outside fixed inventory roots')
    return name


def retained_baseline(root):
    raw = (Path(root) / AL_EXECUTION).read_bytes()
    require(sha(raw) == AL_EXECUTION_SHA, 'exact completed AL execution required')
    record = load_json_strict(raw, require_canonical=False)
    require(record['completed'] is True and
            record['source_commit'] == '643c0ad947d5635ca6d0075397467f3df5483aa6' and
            record['source_tree'] == '4145435d3bb456673cd4186b31c8394c2f841ac9' and
            record['durable_campaign_reservation_checked'] is True and
            record['live_campaign_authorization_checked'] is True and
            set(record['claims']) == set(FALSE_CLAIMS) and all(v is False for v in record['claims'].values()),
            'completed AL scope differs')
    for name, digest in record['source_sha256'].items():
        require(sha((Path(root) / name).read_bytes()) == digest, 'inherited AL source changed: ' + name)
    return record


class NativeAuthority:
    def __init__(self, root, directory, native, exported, pki, commission_file, commission_pin, root_pin, boot):
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
        require(self.ready['schema'] == 'phase17am.authority-ready.v1' and
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


def _client(root, physical, bundle, state, native_root, *, action, port, commission_pin, root_pin, stale):
    native = native_root / 'client' / action
    require(not native.exists(), 'fresh client action observation required'); native.mkdir(parents=True)
    inside = native / 'inside'; inside.mkdir()
    nonce = _nonce('run_one' if action == 'replayed_nonce' else action)
    command = [sys.executable, '-I', '-S', '-B', '-u', str(root / DRIVER),
        '--bundle', str(bundle), '--anchor', str(state / 'anchor.json'),
        '--native-directory', str(inside), '--commission-pin', commission_pin,
        '--root-pin', root_pin, '--port', str(port), '--action', action, '--request-nonce', nonce]
    if action == 'stale':
        command += ['--stale-cursor-json', canonical(stale).decode()]
    isolated = platform.system() == 'Linux'
    specification = None
    if isolated:
        from .authority_isolation import build_client_command, specification_from_command
        command = build_client_command(root, bundle, inside, command, state_directory=state,
            protected_paths=[physical / 'root', physical / 'root/authority.sqlite3',
                physical / 'private/server.key', physical / 'private/ca.key'], probe_name=action)
        specification = specification_from_command(command)
    start = {'schema': NATIVE_SCHEMA, 'role': 'client', 'invocation_id': uuid.uuid4().hex,
        'action': action, 'started_at_utc': _now(), 'observer_pid': os.getpid(),
        'command': command, 'cwd': str(root), 'source_root': str(root),
        'python_sha256': sha(Path(sys.executable).read_bytes()),
        'entrypoint_sha256': sha((root / DRIVER).read_bytes()),
        'commission_sha256': commission_pin, 'root_provision_sha256': root_pin,
        'controller_namespace_profile_used': isolated, 'isolation_specification': specification,
        'shell': False, 'close_fds': True, 'physical_attestation': False}
    _write(native / 'start.json', canonical(start)); begin = time.monotonic_ns()
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, cwd=root, shell=False, close_fds=True)
    _write(native / 'child.json', canonical({'schema': NATIVE_SCHEMA, 'invocation_id': start['invocation_id'],
        'child_pid': process.pid, 'observer_pid': os.getpid(), 'observed_at_utc': _now()}))
    timed_out = False
    try:
        output, error = process.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        timed_out = True; process.kill(); output, error = process.communicate()
    _write(native / 'stdout.jsonl', output); _write(native / 'stderr.txt', error)
    result = {'schema': NATIVE_SCHEMA, 'invocation_id': start['invocation_id'], 'child_pid': process.pid,
        'completed_at_utc': _now(), 'elapsed_ns': time.monotonic_ns() - begin,
        'returncode': process.returncode, 'native_wait_completed': True, 'timed_out': timed_out,
        'stream_sha256': {'stdout.jsonl': sha(output), 'stderr.txt': sha(error)}}
    _write(native / 'result.json', canonical(result))
    require(process.returncode == 0 and not timed_out and not error, 'selected native client action failed: ' + action)
    lines = output.splitlines(keepends=True)
    if isolated:
        from .authority_isolation import parse_boundary_frame
        require(len(lines) == 2, 'isolated client observation framing differs')
        boundary = parse_boundary_frame(lines[0], specification)
        _write(native / 'boundary.json', canonical(boundary))
        lines = lines[1:]
    require(len(lines) == 1, 'one completed client result required')
    report = load_json_strict(lines[0].rstrip(b'\n'), require_canonical=True)
    raw = (inside / 'operation.json').read_bytes()
    require(report == {'schema': 'phase17am.selected-client-result.v1', 'action': action,
                      'completed': True, 'record_sha256': sha(raw)}, 'client result differs from original operation')
    return load_json_strict(raw, require_canonical=True)


def prepare_authenticated_authority(root, physical):
    root, physical = Path(root).absolute(), Path(physical).absolute()
    require(not physical.exists(), 'new AM physical workspace required'); physical.mkdir(parents=True)
    retained_baseline(root); parent = predecessor(str(root))
    native_root = physical / 'campaign-native'; native_root.mkdir()
    one = full_grammar_policy(len(parent.accepted_programs), candidate_limit=2)
    policy = Policy(tuple(2 * value for value in one.limits), 2 * one.cost_limit)
    provisioned = runtime.provision_root(physical / 'root', root, parent, policy,
        authority_id='phase17am.reference.authenticated_campaign', nonce=_nonce('provision'))
    pin = provisioned['root_provision_sha256']
    connection = sqlite3.connect(physical / 'root/authority.sqlite3')
    try:
        headers = [load_json_strict(row[0], require_canonical=True)
                   for row in connection.execute('SELECT event FROM snapshots ORDER BY serial')]
    finally:
        connection.close()
    require(len(headers) == 1 and transport.event_cursor(headers[0]) == provisioned['cursor'],
            'independently provisioned initial header differs')
    pki = generate_reference_pki(physical / 'private')
    commission = transport.make_commission(root, pin, pki['public']['ca'], pki['public']['server'], pki['public']['client'])
    commission_pin = transport.commission_digest(commission)
    commission_file = physical / 'commission.json'; _write(commission_file, canonical(commission))
    bundle = physical / 'client-bundle'; bundle.mkdir(mode=0o700)
    for name in ('ca', 'server', 'client'):
        _write(bundle / (name + '.pem'), Path(pki['public'][name]).read_bytes())
    _write(bundle / 'client.key', Path(pki['private']['client']).read_bytes())
    _write(bundle / 'commission.json', canonical(commission))
    state = physical / 'client-state'; state.mkdir(mode=0o700)
    initial_anchor = transport.create_anchor(state / 'anchor.json', commission,
        expected_commission_sha256=commission_pin, expected_root_pin=pin, trusted_headers=headers)
    public_pki = {key: value for key, value in pki.items() if key not in ('private',)}
    _write(native_root / 'provisioning/pki.json', canonical(public_pki))
    _write(native_root / 'provisioning/commissioning.json', canonical({'commission': commission,
        'commission_sha256': commission_pin, 'root_provision_sha256': pin, 'initial_anchor': initial_anchor,
        'private_keys_published': False, 'independent_production_issuer_established': False}))
    boots = []
    for index in (0, 1):
        name = 'lifetime-' + str(index)
        exported = physical / 'exports' / (name + '.json')
        authority = NativeAuthority(root, physical / 'root', native_root / 'authority' / name,
            exported, pki, commission_file, commission_pin, pin, _nonce('boot-' + str(index)))
        try:
            actions = ACTIONS[:8] if index == 0 else ACTIONS[8:]
            stale = authority.ready['cursor'] if index == 0 else None
            for action in actions:
                _client(root, physical, bundle, state, native_root, action=action,
                    port=authority.ready['address'][1], commission_pin=commission_pin, root_pin=pin, stale=stale)
        finally:
            authority.close()
        boots.append(name)
    evidence = load_json_strict(exported.read_bytes(), require_canonical=True)
    checked = runtime.verify_evidence(evidence, parent, expected_root_provision_sha256=pin, source_root=root)
    grants = []
    for session in checked['snapshot']['sessions']:
        grant = load_json_strict(bytes.fromhex(session['files_hex']['grant.json']))['grant_hash']; grants.append(grant)
        origin = physical / 'root/worker-native' / grant
        for name in WORKER_FILES:
            _write(native_root / 'workers' / grant / name, (origin / name).read_bytes())
    images = {}
    for path in sorted(native_root.rglob('*')):
        _no_links(path)
        if path.is_file():
            name = _relative(path.relative_to(native_root).as_posix())
            raw = path.read_bytes()
            require(b'PRIVATE KEY-----' not in raw, 'private key unexpectedly entered public native evidence')
            images[name] = raw.hex()
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'retained_al_execution_sha256': AL_EXECUTION_SHA, 'scope': SCOPE,
        'cases': [{'name': CASE_NAME, 'commission': commission,
            'certificates': {name: Path(path).read_bytes().hex() for name, path in pki['public'].items()},
            'root_provision_sha256': pin, 'evidence': evidence, 'native_boots': boots, 'worker_grants': grants}],
        'native_images': images, 'claims': {name: False for name in FALSE_CLAIMS}}
    packet['summary'] = summarize(packet, root)
    prepared = PreparedAuthenticatedAuthority(canonical(packet), root)
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


def _frame(encoded):
    require(type(encoded) is str and len(encoded) >= 8, 'complete original TLS application frame required')
    raw = bytes.fromhex(encoded)
    require(raw.hex() == encoded and len(raw) <= transport.MAX_FRAME + 4 and
            struct.unpack('!I', raw[:4])[0] == len(raw) - 4, 'original TLS frame length differs')
    return load_json_strict(raw[4:], require_canonical=True)


def _json(images, name):
    require(name in images, 'original native file missing: ' + name)
    return load_json_strict(images[name], require_canonical=True)


def _verify_process(images, directory, entrypoint, root, *, role):
    start = _json(images, directory + '/start.json')
    child = _json(images, directory + '/child.json')
    result = _json(images, directory + '/result.json')
    start_fields = {'schema', 'role', 'invocation_id', 'started_at_utc', 'observer_pid',
        'command', 'cwd', 'source_root', 'python_sha256', 'entrypoint_sha256',
        'root_provision_sha256', 'commission_sha256', 'shell', 'close_fds', 'physical_attestation'}
    start_fields |= ({'boot_nonce'} if role == 'authority' else
                     {'action', 'controller_namespace_profile_used', 'isolation_specification'})
    exact(start, start_fields)
    exact(child, {'schema', 'invocation_id', 'child_pid', 'observer_pid', 'observed_at_utc'})
    result_fields = {'schema', 'invocation_id', 'child_pid', 'completed_at_utc', 'elapsed_ns',
        'returncode', 'native_wait_completed', 'timed_out', 'stream_sha256'}
    if role == 'authority':
        result_fields |= {'reader_finished', 'reader_error', 'export_sha256'}
    exact(result, result_fields)
    require(start['schema'] == child['schema'] == result['schema'] == NATIVE_SCHEMA and start['role'] == role and
        type(start['invocation_id']) is str and len(start['invocation_id']) == 32 and
        set(start['invocation_id']) <= set('0123456789abcdef') and
        start['invocation_id'] == child['invocation_id'] == result['invocation_id'], 'native process identity differs')
    require(type(child['child_pid']) is int and 0 < child['child_pid'] < 2**63 and
        type(start['observer_pid']) is int and 0 < start['observer_pid'] < 2**63 and
        type(child['observer_pid']) is int and type(result['child_pid']) is int and
        child['child_pid'] == result['child_pid'] and child['observer_pid'] == start['observer_pid'] and
        child['child_pid'] != child['observer_pid'], 'native process parent/child observation differs')
    require(_stamp(start['started_at_utc']) <= _stamp(child['observed_at_utc']) <=
        _stamp(result['completed_at_utc']), 'native process timestamps differ')
    require(type(result['elapsed_ns']) is int and 0 <= result['elapsed_ns'] <= 1200 * 10**9 and
        result['native_wait_completed'] is True and result['returncode'] == 0 and
        type(result['returncode']) is int and result['timed_out'] is False,
        'native process did not complete within the selected bound')
    require(start['entrypoint_sha256'] == sha((Path(root) / entrypoint).read_bytes()) and
        start['source_root'] == str(Path(root).absolute()) and start['cwd'] == str(Path(root).absolute()) and
        start['shell'] is False and start['close_fds'] is True and start['physical_attestation'] is False,
        'native source/launch identity differs')
    for key in ('python_sha256', 'entrypoint_sha256', 'commission_sha256', 'root_provision_sha256'):
        transport.digest(start[key])
    command = start['command']
    require(type(command) is list and 6 <= len(command) <= 256 and
        all(type(arg) is str and 0 < len(arg) <= 65536 and '\x00' not in arg for arg in command),
        'bounded original native argv required')
    required_streams = {'stdout.jsonl', 'stderr.txt'}
    if role == 'authority':
        required_streams.add('stdin.jsonl')
    exact(result['stream_sha256'], required_streams)
    for name, hashed in result['stream_sha256'].items():
        transport.digest(hashed)
        require(directory + '/' + name in images and sha(images[directory + '/' + name]) == hashed,
                'original native stream differs')
    require(images[directory + '/stderr.txt'] == b'', 'selected native process diagnostics are not empty')
    return start, child, result


def _tls_records(images, prefix):
    records = []
    names = sorted(name for name in images if name.startswith(prefix) and
                   PurePosixPath(name).name.startswith('result-') and name.endswith('.json'))
    for number, name in enumerate(names):
        require(name == prefix + ('result-%04d.json' % number), 'TLS result inventory is not contiguous/direct')
        result = _json(images, name)
        role = result.get('role')
        require(role in ('server', 'client'), 'unknown TLS observer role')
        base = {'schema', 'role', 'sequence', 'pid', 'started_at_utc', 'remote_address',
            'commission_sha256', 'root_provision_sha256', 'phase', 'request_frame_hex',
            'response_frame_hex', 'peer_pin_matched', 'error_type'}
        base |= {'request_sent', 'abandoned_response'} if role == 'client' else {'response_sent'}
        start = _json(images, prefix + ('start-%04d.json' % number))
        exact(start, base)
        result_fields = base | {'completed_at_utc', 'peer_certificate_der_hex',
                               'peer_certificate_sha256', 'tls_version', 'cipher'}
        if result.get('error_type') is not None:
            result_fields.add('error_message')
        exact(result, result_fields)
        require(start['schema'] == result['schema'] == transport.NATIVE_SCHEMA and
            start['role'] == role and type(start['sequence']) is int and
            type(result['sequence']) is int and start['sequence'] == result['sequence'] == number and
            type(start['pid']) is int and type(result['pid']) is int and 0 < start['pid'] < 2**63 and
            start['pid'] == result['pid'] and start['started_at_utc'] == result['started_at_utc'] and
            _stamp(start['started_at_utc']) <= _stamp(result['completed_at_utc']), 'TLS native start/result join differs')
        for key in ('commission_sha256', 'root_provision_sha256', 'remote_address'):
            require(start[key] == result[key], 'TLS immutable connection identity changed')
        require(start['phase'] == ('before_connect' if role == 'client' else 'accepted_tcp') and
            start['request_frame_hex'] == start['response_frame_hex'] == '' and
            start['peer_pin_matched'] is False and start['error_type'] is None,
            'TLS start is not an original pre-connection observation')
        require(start['request_sent' if role == 'client' else 'response_sent'] is False,
                'TLS start asserts prior send')
        if role == 'client':
            require(start['abandoned_response'] is False and type(result['abandoned_response']) is bool,
                    'TLS abandonment state differs')
        require(type(result['peer_pin_matched']) is bool and
            type(result['request_sent' if role == 'client' else 'response_sent']) is bool,
            'exact TLS outcome booleans required')
        remote = result['remote_address']
        require(type(remote) is list and len(remote) == 2 and remote[0] == '127.0.0.1' and
                type(remote[1]) is int and 0 < remote[1] <= 65535, 'TLS loopback address differs')
        cipher = result['cipher']
        require(type(cipher) is list and len(cipher) == 3 and cipher[0] in
            ('TLS_AES_256_GCM_SHA384', 'TLS_CHACHA20_POLY1305_SHA256', 'TLS_AES_128_GCM_SHA256') and
            cipher[1] == 'TLSv1.3' and type(cipher[2]) is int and cipher[2] in (128, 256),
            'negotiated TLS cipher observation differs')
        for key in ('commission_sha256', 'root_provision_sha256', 'peer_certificate_sha256'):
            transport.digest(result[key])
        for key in ('peer_certificate_der_hex', 'request_frame_hex', 'response_frame_hex'):
            encoded = result[key]
            require(type(encoded) is str and len(encoded) <= 2 * (transport.MAX_FRAME + 4),
                    'bounded TLS original byte observation required')
            require(bytes.fromhex(encoded).hex() == encoded, 'noncanonical TLS byte encoding')
        if result['error_type'] is not None:
            require(type(result['error_type']) is str and 0 < len(result['error_type']) < 100 and
                    type(result['error_message']) is str and len(result['error_message']) <= 512,
                    'bounded original TLS error required')
        records.append((name, result))
    expected_starts = {prefix + ('start-%04d.json' % i) for i in range(len(records))}
    actual_starts = {name for name in images if name.startswith(prefix) and
                     PurePosixPath(name).name.startswith('start-') and name.endswith('.json')}
    require(actual_starts == expected_starts, 'unresolved or extra TLS start observation')
    return records


def verify_transport_images(packet, root=SOURCE_ROOT):
    images = _images(packet); case = packet['cases'][0]; commission = case['commission']
    pin = case['root_provision_sha256']; commission_pin = transport.commission_digest(commission)
    headers = [row['event'] for row in case['evidence']['entries']]
    transport.verify_headers(headers, root_pin=pin)
    expected_files = {'provisioning/pki.json', 'provisioning/commissioning.json'}
    commissioning = _json(images, 'provisioning/commissioning.json')
    exact(commissioning, {'commission', 'commission_sha256', 'root_provision_sha256', 'initial_anchor',
                          'private_keys_published', 'independent_production_issuer_established'})
    initial_anchor = {'schema': transport.ANCHOR_SCHEMA, 'commission_sha256': commission_pin,
        'root_provision_sha256': pin, 'headers': headers[:1], 'pending': None, 'resolved': []}
    require(commissioning['private_keys_published'] is False and
        commissioning['independent_production_issuer_established'] is False and
        commissioning['commission'] == commission and commissioning['commission_sha256'] == commission_pin and
        commissioning['root_provision_sha256'] == pin and commissioning['initial_anchor'] == initial_anchor,
        'administrative commissioning observation differs')
    pki = _json(images, 'provisioning/pki.json')
    require(pki['schema'] == 'phase17am.reference-pki-generation.v1' and
        pki['independent_production_issuer_established'] is False and pki['private_material_is_publication_evidence'] is False,
        'reference certificate generation scope differs')
    transport.digest(pki['openssl_sha256'])
    physical = Path(pki['directory']).parent
    private = physical / 'private'; native_root = physical / 'campaign-native'
    require(pki['directory'] == str(private) and pki['command_records_directory'] == str(private / 'command-records'),
            'original certificate provisioning directories differ')
    require(set(pki['public']) == set(pki['identities']) == set(case['certificates']),
            'original public identity inventory differs')
    for label, encoded in case['certificates'].items():
        raw = bytes.fromhex(encoded)
        require(encoded == raw.hex() and pki['public'][label] == str(private / (label + '.pem')),
                'public certificate encoding or original path differs')
        der = transport.ssl.PEM_cert_to_DER_cert(raw.decode('ascii'))
        require(pki['identities'][label] == {'pem_sha256': sha(raw), 'der_sha256': sha(der)},
                'original generated public certificate identity differs')
    require(type(pki['commands']) is list and len(pki['commands']) == 11,
            'original PKI command inventory differs')
    for observation in pki['commands']:
        require(type(observation['command']) is list and observation['command'][0] == pki['openssl_path'] and
            observation['cwd'] == str(private) and observation['native_wait_completed'] is True and
            type(observation['returncode']) is int and observation['returncode'] == 0 and
            observation['timed_out'] is False and observation['error_type'] is None and observation['shell'] is False and
            type(observation['child_pid']) is int and observation['child_pid'] > 0 and
            type(observation['elapsed_ns']) is int and 0 <= observation['elapsed_ns'] <= 70 * 10**9,
            'certificate generation command did not complete')
        for field in ('stdout_hex', 'stderr_hex'):
            require(type(observation[field]) is str and len(observation[field]) <= 2 * transport.MAX_FRAME and
                    bytes.fromhex(observation[field]).hex() == observation[field], 'invalid PKI original stream')

    def native_file_set(directory, authority=False, isolated=False):
        names = {'start.json', 'child.json', 'stdout.jsonl', 'stderr.txt', 'result.json'}
        if authority: names |= {'stdin.jsonl', 'export.json'}
        if isolated: names.add('boundary.json')
        expected_files.update(directory + '/' + name for name in names)

    def options(command, script, ordered):
        require(command[1:5] == ['-I', '-S', '-B', '-u'] and command[5] == str(Path(root) / script) and
            len(command) == 6 + 2 * len(ordered) and command[6::2] == ordered,
            'fixed native command or option inventory differs')
        require(Path(command[0]).is_absolute(), 'absolute recorded interpreter required')
        return dict(zip(command[6::2], command[7::2]))

    def observation_within(record, process_start, process_result, pid):
        require(record['pid'] == pid and _stamp(process_start['started_at_utc']) <= _stamp(record['started_at_utc']) <=
            _stamp(record['completed_at_utc']) <= _stamp(process_result['completed_at_utc']),
            'TLS or operation observation lies outside its actual process lifetime')

    all_ids = []; service_records = []; services = []; python_identity = observer_pid = None
    for index, name in enumerate(case['native_boots']):
        directory = 'authority/' + name; native_file_set(directory, authority=True)
        start, child, result = _verify_process(images, directory, SERVICE, root, role='authority')
        all_ids.append(start['invocation_id'])
        this_python = (start['command'][0], start['python_sha256'])
        if python_identity is None:
            python_identity = this_python; observer_pid = start['observer_pid']
        require(this_python == python_identity and start['observer_pid'] == observer_pid,
                'authority interpreter or original observer changed')
        require(start['commission_sha256'] == commission_pin and start['root_provision_sha256'] == pin and
            start['boot_nonce'] == _nonce('boot-' + str(index)) and result['reader_finished'] is True and
            result['reader_error'] is None, 'authority observer binding differs')
        names = ['--directory', '--commission', '--commission-pin', '--root-pin', '--boot-nonce',
                 '--ca-file', '--server-cert', '--server-key', '--native-directory', '--export']
        args = options(start['command'], SERVICE, names)
        wanted = {'--directory': str(physical / 'root'), '--commission': str(physical / 'commission.json'),
            '--commission-pin': commission_pin, '--root-pin': pin, '--boot-nonce': start['boot_nonce'],
            '--ca-file': str(private / 'ca.pem'), '--server-cert': str(private / 'server.pem'),
            '--server-key': str(private / 'server.key'), '--native-directory': str(native_root / directory / 'transport'),
            '--export': str(physical / 'exports' / (name + '.json'))}
        require(args == wanted, 'authority fixed command parameters differ')
        require(images[directory + '/stdin.jsonl'] == canonical({'operation': 'stop'}) + b'\n',
                'network controller acquired administrative command')
        lines = images[directory + '/stdout.jsonl'].splitlines(keepends=True)
        require(len(lines) == 2 and all(line.endswith(b'\n') for line in lines), 'authority ready/stop observations missing')
        ready, stopped = [load_json_strict(line[:-1], require_canonical=True) for line in lines]
        exact(ready, {'schema', 'pid', 'address', 'commission_sha256', 'root_provision_sha256', 'cursor'})
        exact(stopped, {'schema', 'pid', 'export_sha256', 'connections'})
        exported = _json(images, directory + '/export.json')
        count = 8 if index == 0 else 10
        expected_export = {**case['evidence'], 'entries': case['evidence']['entries'][:count],
                           'final_cursor': transport.event_cursor(headers[count - 1])}
        require(exported == expected_export and
                result['export_sha256'] == sha(images[directory + '/export.json']) == stopped['export_sha256'],
                'authority restart export is not the exact retained prefix')
        require(ready['schema'] == 'phase17am.authority-ready.v1' and
                stopped['schema'] == 'phase17am.authority-stopped.v1' and
                type(ready['pid']) is int and type(stopped['pid']) is int and
                ready['pid'] == stopped['pid'] == child['child_pid'] and
                ready['commission_sha256'] == commission_pin and ready['root_provision_sha256'] == pin and
                ready['cursor'] == transport.event_cursor(headers[1 if index == 0 else 8]) and
                headers[1 if index == 0 else 8]['boot_nonce'] == start['boot_nonce'], 'authority readiness differs')
        require(type(ready['address']) is list and len(ready['address']) == 2 and ready['address'][0] == '127.0.0.1' and
                type(ready['address'][1]) is int and 0 < ready['address'][1] <= 65535, 'authority bound address differs')
        records = _tls_records(images, directory + '/transport/')
        require(type(stopped['connections']) is int and stopped['connections'] == len(records) == (7 if index == 0 else 2),
                'selected service connection inventory differs')
        for record_name, record in records:
            require(record['role'] == 'server', 'server TLS role differs')
            observation_within(record, start, result, child['child_pid'])
            expected_files.update((record_name, record_name.replace('/result-', '/start-')))
        services.append({'start': start, 'child': child, 'result': result, 'ready': ready})
        service_records.extend(records)
    require(_stamp(services[0]['result']['completed_at_utc']) <= _stamp(services[1]['start']['started_at_utc']),
            'authority lifetimes overlap')

    clients = []; isolation = []; operations = {}; core_operations = {}; client_meta = {}
    previous_anchor = initial_anchor
    for action in ACTIONS:
        directory = 'client/' + action
        start, child, result = _verify_process(images, directory, DRIVER, root, role='client')
        all_ids.append(start['invocation_id'])
        require(start['action'] == action and start['commission_sha256'] == commission_pin and
            start['root_provision_sha256'] == pin and start['python_sha256'] == python_identity[1] and
            start['observer_pid'] == observer_pid and type(start['controller_namespace_profile_used']) is bool,
            'client command authority/interpreter binding differs')
        isolated = start['controller_namespace_profile_used']; native_file_set(directory, isolated=isolated)
        lines = images[directory + '/stdout.jsonl'].splitlines(keepends=True)
        observed = None
        if isolated:
            from .authority_isolation import parse_boundary_frame, specification_from_command
            spec = specification_from_command(start['command'])
            _same(spec, start['isolation_specification'], 'observed namespace command differs')
            expected_targets = [{'path': str(path), 'kind': kind} for path, kind in (
                (physical / 'root', 'directory'), (physical / 'root/authority.sqlite3', 'file'),
                (private / 'server.key', 'file'), (private / 'ca.key', 'file'))]
            require(spec['host_pid'] == observer_pid and spec['repo'] == str(Path(root).absolute()) and
                spec['client_bundle'] == str(physical / 'client-bundle') and
                spec['state_directory'] == str(physical / 'client-state') and
                spec['native_output'] == str(native_root / directory / 'inside') and
                spec['protected_targets'] == expected_targets and spec['probe_name'] == action,
                'namespace observation protects different authority/source paths')
            for name in ('scripts/phase17_authority_isolation_probe.py',
                         'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py'):
                require(spec['readonly_files'].get(str(Path(root) / name)) == sha((Path(root) / name).read_bytes()),
                        'namespace wrapper/module source identity differs')
            require(len(lines) == 2, 'namespace probe/client output inventory differs')
            observed = parse_boundary_frame(lines[0], spec)
            _same(observed, _json(images, directory + '/boundary.json'), 'original namespace observation differs')
            isolation.append(action); lines = lines[1:]; command = spec['command']; inner_pid = observed['pid']
        else:
            require(start['isolation_specification'] is None, 'unisolated client carries namespace claim')
            command = start['command']; inner_pid = child['child_pid']
        require(command[0] == python_identity[0], 'client selected another interpreter')
        option_names = ['--bundle', '--anchor', '--native-directory', '--commission-pin', '--root-pin',
                        '--port', '--action', '--request-nonce']
        if action == 'stale': option_names.append('--stale-cursor-json')
        args = options(command, DRIVER, option_names)
        lifetime = 0 if action in ACTIONS[:8] else 1
        service = services[lifetime]
        expected_nonce = _nonce('run_one' if action == 'replayed_nonce' else action)
        wanted = {'--bundle': str(physical / 'client-bundle'), '--anchor': str(physical / 'client-state/anchor.json'),
            '--native-directory': str(native_root / directory / 'inside'), '--commission-pin': commission_pin,
            '--root-pin': pin, '--port': str(service['ready']['address'][1]), '--action': action,
            '--request-nonce': expected_nonce}
        if action == 'stale': wanted['--stale-cursor-json'] = canonical(services[0]['ready']['cursor']).decode()
        require(args == wanted, 'selected client command differs from exact intended action')
        require(_stamp(service['start']['started_at_utc']) <= _stamp(start['started_at_utc']) <=
            _stamp(result['completed_at_utc']) <= _stamp(service['result']['completed_at_utc']),
            'client action occurred outside its authority lifetime')
        require(len(lines) == 1 and lines[0].endswith(b'\n'), 'one original client result required')
        operation_name = directory + '/inside/operation.json'; expected_files.add(operation_name)
        operation = _json(images, operation_name)
        exact(operation, {'schema', 'action', 'request_nonce', 'anchor_before_hex', 'anchor_after_hex',
            'anchor_before_sha256', 'anchor_after_sha256', 'request', 'result', 'error_type',
            'network_attempts', 'completed', 'automatic_retries', 'physical_attestation'})
        output = load_json_strict(lines[0][:-1], require_canonical=True)
        require(output == {'schema': 'phase17am.selected-client-result.v1', 'action': action,
            'completed': True, 'record_sha256': sha(images[operation_name])}, 'client result/operation bytes differ')
        require(operation['schema'] == 'phase17am.selected-client-operation.v1' and operation['action'] == action and
            operation['request_nonce'] == expected_nonce and operation['completed'] is True and
            type(operation['automatic_retries']) is int and operation['automatic_retries'] == 0 and
            operation['physical_attestation'] is False, 'selected client operation scope differs')
        before_raw = bytes.fromhex(operation['anchor_before_hex']); after_raw = bytes.fromhex(operation['anchor_after_hex'])
        before, after = [load_json_strict(raw, require_canonical=True) for raw in (before_raw, after_raw)]
        require(before_raw.hex() == operation['anchor_before_hex'] and after_raw.hex() == operation['anchor_after_hex'] and
            sha(before_raw) == operation['anchor_before_sha256'] and sha(after_raw) == operation['anchor_after_sha256'] and
            before == previous_anchor, 'client anchor continuation differs')
        for anchor in (before, after):
            exact(anchor, {'schema', 'commission_sha256', 'root_provision_sha256', 'headers', 'pending', 'resolved'})
            require(anchor['schema'] == transport.ANCHOR_SCHEMA and anchor['commission_sha256'] == commission_pin and
                anchor['root_provision_sha256'] == pin and 0 < len(anchor['headers']) <= len(headers) and
                anchor['headers'] == headers[:len(anchor['headers'])], 'client anchor not in actual root history')
            transport.verify_headers(anchor['headers'], root_pin=pin)
        previous_anchor = after
        records = _tls_records(images, directory + '/inside/transport/')
        require(type(operation['network_attempts']) is int and len(records) == operation['network_attempts'] ==
                (0 if action == 'blocked_retry' else 1), 'client retried or omitted a selected native attempt')
        for record_name, record in records:
            observation_within(record, start, result, inner_pid)
            require(record['remote_address'] == service['ready']['address'], 'client connected to a different listener')
            expected_files.update((record_name, record_name.replace('/result-', '/start-')))
        if action not in ('stale', 'replayed_nonce', 'forbidden_operation', 'extra_field'):
            core_name = directory + '/inside/transport/operation-0000.json'; expected_files.add(core_name)
            core = _json(images, core_name)
            exact(core, {'schema', 'operation', 'pid', 'sequence', 'exchange_sequence', 'started_at_utc',
                'anchor_before', 'pending_before_send', 'request', 'completed', 'error_type',
                'anchor_after', 'anchor_after_sha256', 'completed_at_utc'})
            observation_within(core, start, result, inner_pid)
            require(core['schema'] == 'phase17am.client-operation.v1' and type(core['sequence']) is int and
                core['sequence'] == 0 and type(core['exchange_sequence']) is int and core['exchange_sequence'] == 0 and
                core['anchor_before'] == before and core['anchor_after'] == after and
                core['anchor_after_sha256'] == sha(after_raw), 'original core operation/anchor join differs')
            expected_op = 'read' if action == 'initial_read' else 'reconcile' if action == 'reconcile' else 'run'
            require(core['operation'] == expected_op and operation['request'] is None,
                    'selected core operation differs')
            if action == 'blocked_retry':
                require(core['completed'] is False and core['error_type'] == operation['error_type'] == 'ResourceError' and
                    core['request'] is None and core['pending_before_send'] is None and before == after and
                    before['pending'] is not None and operation['result'] is None,
                    'pending retry was not refused before request construction/network')
            else:
                require(core['completed'] is True and core['error_type'] is None and operation['error_type'] is None,
                        'selected client core operation did not complete')
            core_operations[action] = core
        operations[action] = {'record': operation, 'before': before, 'after': after}
        client_meta[action] = {'start': start, 'child': child, 'result': result, 'lifetime': lifetime}
        clients.extend((action, name, record) for name, record in records)
    require(len(set(all_ids)) == len(all_ids), 'original native invocation identity reused')
    for first, second in zip(ACTIONS, ACTIONS[1:]):
        require(_stamp(client_meta[first]['result']['completed_at_utc']) <=
                _stamp(client_meta[second]['start']['started_at_utc']), 'selected client actions overlap/reorder')
    require(not isolation or isolation == list(ACTIONS), 'partial controller isolation cannot masquerade as complete selected coverage')

    used = set(); successes = 0; refusals = 0; abandoned = 0; challenges = set()
    expected_service_sequence = [0, 0]
    for action, name, client in clients:
        require(client['role'] == 'client' and client['peer_pin_matched'] is True and
            client['tls_version'] == 'TLSv1.3' and client['commission_sha256'] == commission_pin and
            client['root_provision_sha256'] == pin and
            sha(bytes.fromhex(client['peer_certificate_der_hex'])) == client['peer_certificate_sha256'] ==
            commission['server_certificate_sha256'] and client['request_sent'] is True,
            'client did not observe exact commissioned TLS peer')
        candidates = [(p, r) for p, r in service_records if r['request_frame_hex'] == client['request_frame_hex']]
        require(len(candidates) == 1 and candidates[0][0] not in used, 'original client/server request does not join uniquely')
        server_name, server = candidates[0]; used.add(server_name)
        lifetime = client_meta[action]['lifetime']; sequence = expected_service_sequence[lifetime]
        expected_service_sequence[lifetime] += 1
        require(server_name == 'authority/lifetime-%d/transport/result-%04d.json' % (lifetime, sequence),
                'authenticated action assigned to another authority lifetime/order')
        require(server['peer_pin_matched'] is True and server['tls_version'] == 'TLSv1.3' and
            sha(bytes.fromhex(server['peer_certificate_der_hex'])) == server['peer_certificate_sha256'] ==
            commission['client_certificate_sha256'] and server['commission_sha256'] == commission_pin and
            server['root_provision_sha256'] == pin and server['cipher'] == client['cipher'] and
            _stamp(client['started_at_utc']) <= _stamp(server['completed_at_utc']) and
            _stamp(server['started_at_utc']) <= _stamp(client['completed_at_utc']),
            'server/client authenticated observations do not overlap or agree')
        request = _frame(client['request_frame_hex']); group = operations[action]
        operation, before, after = group['record'], group['before'], group['after']
        require(request['request_nonce'] == operation['request_nonce'] if action not in ('initial_read', 'reconcile') else
                type(request['request_nonce']) is str, 'selected request nonce differs')
        require(request['challenge'] not in challenges, 'selected response challenge reused'); challenges.add(request['challenge'])
        expected_cursor = services[0]['ready']['cursor'] if action == 'stale' else transport.event_cursor(before['headers'][-1])
        require(request['expected_cursor'] == expected_cursor, 'selected request cursor differs')
        if action in ('forbidden_operation', 'extra_field'):
            repaired = dict(request)
            if action == 'forbidden_operation':
                require(repaired['operation'] == 'finish', 'designated forbidden operation differs')
                repaired['operation'] = 'run'; intended_error = 'controller operation is not admitted'
            else:
                require(repaired.pop('evaluator', None) == 'caller-selected-code', 'designated evaluator injection differs')
                intended_error = 'exact record fields required'
            transport._validate_request(repaired, commission_pin, pin)
            require(repaired['operation'] == 'run' and repaired['credits'] == 2 and
                operation['request'] == request and operation['result'] is None and before == after and
                not client['response_frame_hex'] and not server['response_frame_hex'] and
                client['phase'] == 'request_sent' and client['abandoned_response'] is False and
                client['error_type'] == operation['error_type'] and client['error_type'] in
                ('EOFError', 'SSLError', 'SSLEOFError', 'ConnectionResetError', 'OSError') and
                server['phase'] == 'request_received' and server['error_type'] == 'ResourceError' and
                server['error_message'] == intended_error and server['response_sent'] is False,
                'designated controller mutation did not cause its exact pre-dispatch refusal')
            refusals += 1; continue
        transport._validate_request(request, commission_pin, pin)
        expected_operation = 'read' if action in ('initial_read', 'reconcile') else 'run'
        require(request['operation'] == expected_operation and
                (request.get('credits') == 2 if expected_operation == 'run' else 'credits' not in request),
                'selected wire operation or credits differ')
        reply = _frame(server['response_frame_hex'])
        require(reply['headers'] == headers[:len(reply['headers'])], 'authenticated reply does not use actual root event prefix')
        checker = object.__new__(transport.AuthorityTransportClient); checker.pin = commission_pin; checker.root_pin = pin
        checked_reply = checker._checked_reply(reply, request, before)
        if action == 'run_abandon':
            require(client['phase'] == 'response_deliberately_unobserved' and client['error_type'] is None and
                client['abandoned_response'] is True and client['response_frame_hex'] == '' and reply['accepted'] is True and
                (server['phase'] == 'response_sent' and server['error_type'] is None and server['response_sent'] is True or
                 server['phase'] == 'response_prepared' and server['response_sent'] is False and server['error_type'] in
                    ('SSLError', 'SSLEOFError', 'BrokenPipeError', 'ConnectionResetError', 'OSError')),
                'lost reply did not retain one actual completed session')
            abandoned += 1
        else:
            require(client['response_frame_hex'] == server['response_frame_hex'] and
                server['phase'] == 'response_sent' and server['response_sent'] is True and server['error_type'] is None and
                client['phase'] == 'response_received' and client['error_type'] is None and client['abandoned_response'] is False,
                'original authenticated reply streams differ')
        expected_after = transport._copy(before)
        if action in ('stale', 'replayed_nonce'):
            require(operation['request'] == request and operation['result'] == reply and operation['error_type'] is None and
                reply['accepted'] is False and reply['reason'] == 'protocol_or_authority_refused' and
                reply['before'] == reply['after'] and before == after, 'stale/replayed call changed root')
            if action == 'stale':
                require(request['expected_cursor'] != reply['before'], 'designated stale request was current')
            else:
                require(request['expected_cursor'] == reply['before'] and request['request_nonce'] == _nonce('run_one') and
                    checked_reply['outcomes'].get(request['request_nonce']) == 'complete' and
                    checker._matching_outcome(checked_reply, request) == 'unobserved',
                    'designated nonce replay was not an already completed distinct mutation')
            refusals += 1
        else:
            core = core_operations[action]
            require(core['request'] == request, 'core operation request differs from original TLS bytes')
            if action in ('run_one', 'run_abandon', 'aggregate_denial'):
                require(before['pending'] is None, 'new run overwrote unresolved client request')
                pending = {'request': request, 'request_sha256': sha(canonical(request))}
                written = {**transport._copy(before), 'pending': pending}
                require(core['pending_before_send'] == written, 'write-ahead pending record differs from exact sent mutation')
                expected_after = written
                if action == 'run_abandon':
                    require(operation['result'] is None, 'abandoned result synthesized a received response')
                else:
                    require(operation['result'] == reply, 'selected run result differs from actual response')
                    outcome = checker._matching_outcome(checked_reply, request)
                    wanted_outcome = 'denied' if action == 'aggregate_denial' else 'complete'
                    require(outcome == wanted_outcome, 'selected run terminal history differs')
                    checker._resolve(expected_after, outcome, reply['after'])
                    expected_after['headers'] = reply['headers']
            elif action == 'initial_read':
                require(before['pending'] is None and core['pending_before_send'] is None and operation['result'] == reply,
                        'initial read altered pending request')
                expected_after['headers'] = reply['headers']
            elif action == 'reconcile':
                require(before['pending'] is not None and core['pending_before_send'] is None,
                        'reconciliation omitted prior ambiguity or created a mutation')
                saved_request = before['pending']['request']
                require(before['pending']['request_sha256'] == sha(canonical(saved_request)) and
                    checker._matching_outcome(checked_reply, saved_request) == 'complete',
                    'reconciliation does not prove the exact pending mutation completed')
                checker._resolve(expected_after, 'complete', reply['after'])
                expected_after['headers'] = reply['headers']
                require(operation['result'] == {'response': reply, 'pending_retained': False,
                    'observed_outcome': 'complete', 'worker_reissued': False}, 'reconciliation result differs')
            if action == 'aggregate_denial':
                require(reply['accepted'] is False and reply['reason'] == 'aggregate_budget_denied', 'budget denial differs')
            else:
                require(reply['accepted'] is True, 'selected authorized operation refused'); successes += 1
        require(after == expected_after, 'client anchor transition does not follow exact original operation')
    require(len(used) == len(service_records) == 9 and successes == 4 and refusals == 4 and abandoned == 1,
            'selected authenticated exchange coverage differs')
    require(previous_anchor['pending'] is None and len(previous_anchor['resolved']) == 3 and
            [r['outcome'] for r in previous_anchor['resolved']] == ['complete', 'complete', 'denied'],
            'client completion/reconciliation history differs')
    for grant in case['worker_grants']:
        directory = 'workers/' + grant
        expected_files.update(directory + '/' + name for name in WORKER_FILES)
        worker_start = _json(images, directory + '/start.json')
        worker_result = _json(images, directory + '/result.json')
        require(worker_start['observer_pid'] == services[0]['child']['child_pid'] and
            _stamp(services[0]['start']['started_at_utc']) <= _stamp(worker_start['started_at_utc']) <=
            _stamp(worker_result['completed_at_utc']) <= _stamp(services[0]['result']['completed_at_utc']),
            'actual worker did not belong to the first admitted authority lifetime')
    require(set(images) == expected_files, 'original native inventory contains missing or unexplained files')
    return {'native_client_processes': len(ACTIONS), 'native_tls_connections': len(clients),
        'authenticated_dispatch_refusals': refusals, 'abandoned_responses': abandoned,
        'controller_namespace_observations': len(isolation),
        'controller_namespace_profile': 'linux_reference' if isolation else 'not_exercised_on_this_platform',
        'independently_protected_deployment_established': False,
        'client_anchor_protected_from_its_own_principal': False}

def summarize(packet, root=SOURCE_ROOT):
    require(type(packet['cases']) is list and len(packet['cases']) == 1, 'one selected AM campaign required')
    case = packet['cases'][0]
    exact(case, {'name', 'commission', 'certificates', 'root_provision_sha256', 'evidence', 'native_boots', 'worker_grants'})
    require(case['name'] == CASE_NAME and case['native_boots'] == ['lifetime-0', 'lifetime-1'], 'selected AM case/lifetimes differ')
    commission = case['commission']; pin = case['root_provision_sha256']
    transport.validate_commission(commission, expected_commission_sha256=transport.commission_digest(commission),
        expected_root_pin=pin, source_root=root)
    require(set(case['certificates']) == {'ca', 'server', 'client', 'other-client', 'foreign-ca', 'foreign-client'},
            'reference public certificate inventory differs')
    for label in ('ca', 'server', 'client'):
        require(bytes.fromhex(case['certificates'][label]).decode('ascii') == commission[label + '_certificate_pem'],
                'original public certificate differs from commission')
    checked = runtime.verify_evidence(case['evidence'], predecessor(str(Path(root).absolute())),
        expected_root_provision_sha256=pin, source_root=root)
    sessions = checked['snapshot']['sessions']; kinds = [e['event']['kind'] for e in case['evidence']['entries']]
    grants = []; challenges = []
    for session in sessions:
        files = {name: bytes.fromhex(raw) for name, raw in session['files_hex'].items()}
        grants.append(load_json_strict(files['grant.json'])['grant_hash'])
        challenges.append(load_json_strict(files['public_challenge.json'])['challenge_commitment_hash'])
    require(len(sessions) == 2 and len(set(challenges)) == 2 and grants == case['worker_grants'] and
        kinds.count('reserve') == kinds.count('launch') == kinds.count('complete') == kinds.count('reopen') == 2 and
        kinds.count('deny') == 1 and len(kinds) == 10 and checked['state'].pending is None and
        checked['state'].status == 'resource_exhausted' and checked['cursor']['epoch'] == 2,
        'selected AM campaign transitions differ')
    observations = verify_transport_images(packet, root)
    return {'cases': [{'name': CASE_NAME, 'completed_sessions': 2, 'root_events': 10,
        'reserved': list(checked['state'].reserved), 'reserved_cost': checked['state'].charged_cost,
        'pending_retained': False, 'denials': 1, 'status': checked['state'].status, 'epoch': 2}],
        'fresh_worker_sessions': 2, 'fresh_live_challenges': 2, 'native_authority_lifetimes': 2,
        'permanent_reservations': 2, 'completed_sessions': 2, 'denied_sessions': 1, 'pending_sessions': 0,
        'old_proof_campaigns_rerun': False, 'old_acceptance_reinterpreted': False,
        'complete_resource_accounting': False, 'independently_protected_deployment_established': False,
        **observations}


class PreparedAuthenticatedAuthority:
    def __init__(self, raw, root=SOURCE_ROOT):
        require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'bounded AM packet bytes required')
        packet = load_json_strict(raw, require_canonical=True)
        exact(packet, {'schema', 'policy', 'base_commit', 'retained_al_execution_sha256',
                      'scope', 'cases', 'native_images', 'claims', 'summary'})
        require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE and
            packet['retained_al_execution_sha256'] == AL_EXECUTION_SHA and packet['scope'] == SCOPE and
            set(packet['claims']) == set(FALSE_CLAIMS) and all(v is False for v in packet['claims'].values()),
            'AM packet scope differs')
        retained_baseline(root)
        _same(packet['summary'], summarize(packet, root), 'AM selected capture summary differs')
        self.packet_bytes = raw

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes, require_canonical=True)


def evidence_images(packet):
    return {CASE_NAME + '.json': canonical(packet['cases'][0]['evidence'])}


def verify_all_native(directory, packet, root=SOURCE_ROOT):
    directory = Path(directory); _no_links(directory)
    expected = _images(packet)
    actual = {}
    for path in directory.rglob('*'):
        _no_links(path)
        if path.is_file():
            actual[_relative(path.relative_to(directory).as_posix())] = path.read_bytes()
    require(actual == expected, 'original native file inventory or bytes differ')
    verify_transport_images(packet, root)
    case = packet['cases'][0]
    checked = runtime.verify_evidence(case['evidence'], predecessor(str(Path(root).absolute())),
        expected_root_provision_sha256=case['root_provision_sha256'], source_root=root)
    for session in checked['snapshot']['sessions']:
        files = {name: bytes.fromhex(raw) for name, raw in session['files_hex'].items()}
        grant = load_json_strict(files['grant.json']); accounting = load_json_strict(files['worker-accounting.json'])
        hashes = verify_native_records(directory / 'workers' / grant['grant_hash'], grant,
            files['sealed_transcript.json'], accounting, source_root=root)
        _same(hashes, session['native_sha256'], 'actual AM worker native records differ from durable completion')
    return {name: sha(raw) for name, raw in actual.items()}
