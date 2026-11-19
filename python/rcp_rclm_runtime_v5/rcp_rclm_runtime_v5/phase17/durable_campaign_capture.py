"""Fresh admitted AL campaign work and process-free evidence reconstruction.

Live entropy is generated only by the unchanged fixed worker. Public case
nonces specify present context, never a future result or hidden challenge seed.
Every selected lifetime is retained once; a failed attempt is not replaced in
place or credited by reconstructed bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import lru_cache
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import durable_campaign as runtime
from .campaign_transaction import load_predecessor
from .controller_durable_authority import FALSE_CLAIMS
from .durable_campaign_native import verify_native_records, FILES as WORKER_FILES, _hash, _pid, _stamp
from .resource_ledger import Policy, ResourceError, ResourceExhausted, canonical, cost, exact, full_grammar_policy, require, sha, _no_links

BASE = runtime.BASE
SOURCE_ROOT = Path(__file__).resolve().parents[4]
SCHEMA = 'rcp-rclm.phase17al.durable-campaign-packet.v1'
POLICY = 'phase17al.fixed-live-campaign-local-reference.v1'
PROTOCOL = 'phase17al.reference-authority-stdio.v1'
NATIVE_SCHEMA = 'phase17al.authority-native.v1'
AK_EXECUTION = 'artifacts/development/phase17ak/op-b91832856069/gate/execution.json'
AK_EXECUTION_SHA = '200a218f58066f6ac8b63be8be96e659b09bb2f4dc2fcb941462bb92ac0c3781'
MAX_BYTES = 128 * 1024 * 1024
MAX_FRAME = 1024 * 1024
SERVICE = 'scripts/phase17_durable_campaign_service.py'
SERVICE_FILES = ('start.json', 'child.json', 'stdin.jsonl', 'stdout.jsonl', 'stderr.txt', 'result.json', 'export.json')
CASE_NAMES = ('two_sessions_across_restart', 'interrupted_reservation', 'aggregate_denial')


def _false_claims(value):
    return (type(value) is dict and set(value) == set(FALSE_CLAIMS) and
            all(value[name] is False for name in FALSE_CLAIMS))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _nonce(case, purpose):
    return sha(('Phase17AL/' + case + '/' + purpose).encode())


def _write(path, raw):
    path = Path(path); _no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        require(stream.write(raw) == len(raw), 'short AL capture write')
        stream.flush(); os.fsync(stream.fileno())


@lru_cache(maxsize=2)
def predecessor(root):
    return load_predecessor(Path(root))


def retained_baseline(root):
    raw = (Path(root) / AK_EXECUTION).read_bytes()
    require(sha(raw) == AK_EXECUTION_SHA, 'exact completed AK execution required')
    # Pinned historical execution manifests use the stage runner's pretty JSON,
    # distinct from protocol CJSON. The exact raw hash is checked first.
    record = load_json_strict(raw, require_canonical=False)
    require(record['completed'] is True and record['source_commit'] == 'b9183285606921f70f6dec1a99b397f3d1b919a6'
            and record['source_tree'] == 'e03ff894cdaf5731836b3b1e07dab55778a29ecd'
            and record['durable_authority_commit_checked'] is True and
            record['exclusive_authority_epoch_checked'] is True and
            _false_claims(record['claims']), 'completed AK scope differs')
    for name, digest in record['source_sha256'].items():
        require(sha((Path(root) / name).read_bytes()) == digest, 'inherited AK source changed: ' + name)
    return record


def serve(root, argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--root-pin', required=True)
    parser.add_argument('--boot-nonce', required=True)
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--allow-reference-reservation-test', action='store_true')
    args = parser.parse_args(argv)
    parent = predecessor(str(root))
    with runtime.DurableCampaignAuthority(args.directory, parent,
            expected_root_provision_sha256=args.root_pin, source_root=root,
            boot_nonce=args.boot_nonce) as authority:
        def emit(value):
            raw = canonical(value) + b'\n'
            require(len(raw) <= MAX_FRAME, 'authority response outside bounded protocol')
            require(sys.stdout.buffer.write(raw) == len(raw), 'short authority response')
            sys.stdout.buffer.flush()
        for _ in range(64):
            line = sys.stdin.buffer.readline(MAX_FRAME + 1)
            require(line.endswith(b'\n') and len(line) <= MAX_FRAME, 'bounded authority frame required')
            request = load_json_strict(line[:-1], require_canonical=True)
            require(type(request) is dict, 'authority request object required')
            before = authority.cursor
            finish = False
            try:
                op = request.get('op')
                fields = {'protocol', 'op'}
                if op in ('run', 'reserve_reference_test'):
                    fields |= {'expected_cursor', 'request_nonce', 'credits'}
                exact(request, fields)
                require(request['protocol'] == PROTOCOL, 'authority protocol differs')
                if op == 'read':
                    result = {'status': authority.state.status,
                              'reserved': list(authority.state.reserved),
                              'sessions': len(authority.state.completed)}
                elif op == 'run':
                    files = authority.run_session(expected_cursor=request['expected_cursor'],
                        request_nonce=request['request_nonce'], credits=request['credits'])
                    result = {'session_sha256': {name: sha(raw) for name, raw in files.items()}}
                elif op == 'reserve_reference_test':
                    require(args.allow_reference_reservation_test,
                            'reservation-only command is not a campaign controller operation')
                    permit = authority._reserve(request['expected_cursor'], request['request_nonce'], request['credits'])
                    result = {'permit_sha256': permit['permit_sha256'], 'worker_launched': False}
                elif op == 'finish':
                    exported = authority.export_evidence()
                    raw = canonical(exported)
                    _write(args.export, raw)
                    result = {'export_sha256': sha(raw)}
                    finish = True
                else:
                    raise ResourceError('unknown authority operation')
                accepted, reason = True, None
            except (ResourceError, ValueError, TypeError, KeyError) as error:
                # A failed worker/ambiguous commit poisons the handle; cursor()
                # below then fails and this lifetime cannot receive acceptance.
                accepted, result = False, None
                reason = 'aggregate_budget_denied' if isinstance(error, ResourceExhausted) else 'protocol_or_authority_refused'
            after = authority.cursor
            emit({'protocol': PROTOCOL, 'request_sha256': sha(canonical(request)),
                  'accepted': accepted, 'reason': reason, 'before': before, 'after': after,
                  'committed': canonical(before) != canonical(after), 'result': result})
            if finish:
                return 0
    raise ResourceError('authority request capacity exhausted')


class NativeTransport:
    def __init__(self, root, directory, native, export, *, pin, boot_nonce, reservation_test=False):
        self.root, self.directory, self.native, self.export = map(Path, (root, directory, native, export))
        _no_links(self.native); require(not self.native.exists(), 'fresh authority observation required')
        self.native.mkdir(parents=True)
        self._closed = False; self._reader_error = None; self._timed_out = False
        self._queue = queue.Queue(); self._calls = []
        self._input = (self.native / 'stdin.jsonl').open('xb', buffering=0)
        self._output = (self.native / 'stdout.jsonl').open('xb', buffering=0)
        self._error = (self.native / 'stderr.txt').open('xb', buffering=0)
        command = [sys.executable, '-I', '-S', '-B', '-u', str(self.root / SERVICE),
                   '--directory', str(self.directory), '--root-pin', pin,
                   '--boot-nonce', boot_nonce, '--export', str(self.export)]
        if reservation_test:
            command.append('--allow-reference-reservation-test')
        self.start = {'schema': NATIVE_SCHEMA, 'invocation_id': uuid.uuid4().hex,
            'started_at_utc': _now(), 'observer_pid': os.getpid(), 'command': command,
            'python_sha256': sha(Path(sys.executable).read_bytes()),
            'service_sha256': sha((self.root / SERVICE).read_bytes()),
            'capture_sha256': sha(Path(__file__).read_bytes()), 'root_provision_sha256': pin,
            'boot_nonce': boot_nonce, 'reservation_test': reservation_test,
            'physical_execution_attested': False}
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
                    line = self.process.stdout.readline(MAX_FRAME + 1)
                    if not line:
                        self._queue.put(None); return
                    require(line.endswith(b'\n') and len(line) <= MAX_FRAME, 'authority native framing differs')
                    self._output.write(line); self._queue.put(line)
            except BaseException as error:
                self._reader_error = str(error); self._queue.put(None)
        self._thread = threading.Thread(target=read, daemon=True); self._thread.start()

    def call(self, op, **fields):
        request = {'protocol': PROTOCOL, 'op': op, **fields}
        raw = canonical(request) + b'\n'
        require(len(raw) <= MAX_FRAME, 'authority request exceeds bound')
        require(self.process.stdin.write(raw) == len(raw), 'short authority input')
        self.process.stdin.flush(); self._input.write(raw)
        try:
            line = self._queue.get(timeout=600)
        except queue.Empty:
            self._timed_out = True; self.process.kill()
            raise ResourceError('authority request timed out')
        require(line is not None and self._reader_error is None, 'authority ended without completed reply')
        reply = load_json_strict(line[:-1], require_canonical=True)
        require(reply['protocol'] == PROTOCOL and reply['request_sha256'] == sha(canonical(request)),
                'authority reply request binding differs')
        self._calls.append((request, reply))
        return reply

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.process.stdin.close()
        except (OSError, BrokenPipeError):
            pass
        try:
            code = self.process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            self._timed_out = True; self.process.kill(); code = self.process.wait()
        self._thread.join(timeout=10)
        self.process.stdout.close(); self._input.close(); self._output.close(); self._error.close()
        exported = None
        if code == 0 and not self._timed_out and not self._thread.is_alive():
            raw = self.export.read_bytes()
            require(len(raw) <= MAX_BYTES, 'authority export outside profile')
            load_json_strict(raw, require_canonical=True)
            _write(self.native / 'export.json', raw)
            exported = sha(raw)
        result = {'schema': NATIVE_SCHEMA, 'invocation_id': self.start['invocation_id'],
            'child_pid': self.process.pid, 'completed_at_utc': _now(),
            'elapsed_ns': time.monotonic_ns() - self.started_ns,
            'returncode': code, 'native_wait_completed': True,
            'timed_out': self._timed_out, 'reader_finished': not self._thread.is_alive(),
            'reader_error': self._reader_error, 'export_sha256': exported,
            'stream_sha256': {name: sha((self.native / name).read_bytes())
                for name in ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')}}
        _write(self.native / 'result.json', canonical(result))
        require(code == 0 and not self._timed_out and result['reader_finished'] and self._reader_error is None,
                'authority native lifetime did not complete')
        require((self.native / 'stderr.txt').read_bytes() == b'', 'authority native diagnostic stream not empty')


def _policies(parent):
    one = full_grammar_policy(len(parent.accepted_programs), candidate_limit=2)
    two = Policy(tuple(2 * value for value in one.limits), 2 * one.cost_limit)
    return (two, one, one)


def _run(transport, nonce, *, expected=None, op='run', accepted=True, committed=True, **extra):
    cursor = transport.call('read')['after'] if expected is None else expected
    result = transport.call(op, expected_cursor=cursor, request_nonce=nonce, credits=2, **extra)
    require(result['accepted'] is accepted and result['committed'] is committed,
            'selected authority request outcome differs')
    return result


def prepare_durable_campaign(root, physical):
    root, physical = Path(root).absolute(), Path(physical).absolute()
    require(not physical.exists(), 'new AL physical workspace required')
    physical.mkdir(parents=True)
    retained_baseline(root); parent = predecessor(str(root))
    cases, boots = [], []
    native_root = physical / 'campaign-native'
    for case, policy in zip(CASE_NAMES, _policies(parent), strict=True):
        directory = physical / 'roots' / case
        pin = runtime.provision_root(directory, root, parent, policy,
            authority_id='phase17al.reference.' + case, nonce=_nonce(case, 'provision'))['root_provision_sha256']
        names = []
        count = 2 if case != 'aggregate_denial' else 1
        for index in range(count):
            name = case + '-lifetime-' + str(index)
            names.append(name)
            export = physical / 'exports' / (name + '.json')
            transport = NativeTransport(root, directory, native_root / 'authority' / name, export,
                pin=pin, boot_nonce=_nonce(case, 'boot-' + str(index)),
                reservation_test=case == 'interrupted_reservation')
            try:
                initial = transport.call('read')['after']
                if case == 'two_sessions_across_restart':
                    completed = _run(transport, _nonce(case, 'request-' + str(index)), expected=initial)
                    if index == 0:
                        _run(transport, _nonce(case, 'stale'), expected=initial, accepted=False, committed=False)
                        _run(transport, _nonce(case, 'request-0'), accepted=False, committed=False)
                        _run(transport, _nonce(case, 'substitute'), accepted=False, committed=False,
                             evaluator='caller-selected-code')
                elif case == 'interrupted_reservation':
                    if index == 0:
                        _run(transport, _nonce(case, 'pending'), expected=initial, op='reserve_reference_test')
                    else:
                        _run(transport, _nonce(case, 'retry'), expected=initial, accepted=False, committed=False)
                else:
                    _run(transport, _nonce(case, 'first'), expected=initial)
                    _run(transport, _nonce(case, 'denied'), accepted=False, committed=True)
                finished = transport.call('finish')
                require(finished['accepted'] is True and finished['committed'] is False, 'authority export refused')
            finally:
                transport.close()
            boots.append({'name': name, 'case': case, 'root_provision_sha256': pin,
                          'export_sha256': sha(export.read_bytes()), 'initial_cursor': initial,
                          'final_cursor': finished['after']})
        evidence = load_json_strict(export.read_bytes(), require_canonical=True)
        checked = runtime.verify_evidence(evidence, parent, expected_root_provision_sha256=pin, source_root=root)
        worker_grants = []
        for session in checked['snapshot']['sessions']:
            grant = load_json_strict(bytes.fromhex(session['files_hex']['grant.json']))
            grant_hash = grant['grant_hash']; worker_grants.append(grant_hash)
            origin = directory / 'worker-native' / grant_hash
            target = native_root / 'workers' / case / grant_hash
            require(not target.exists(), 'worker capture collision')
            target.mkdir(parents=True)
            for path in origin.iterdir():
                _no_links(path); require(path.is_file(), 'unexpected worker native entry')
                _write(target / path.name, path.read_bytes())
        cases.append({'name': case, 'root_provision_sha256': pin, 'evidence': evidence,
                      'native_boots': names, 'worker_grants': worker_grants})
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'retained_ak_execution_sha256': AK_EXECUTION_SHA, 'scope': runtime.SCOPE,
        'cases': cases, 'native_boots': boots, 'claims': {name: False for name in FALSE_CLAIMS}}
    packet['summary'] = summarize(packet, root)
    prepared = PreparedDurableCampaign(canonical(packet), root)
    verify_all_native(native_root, packet, root)
    return prepared


def summarize(packet, root=SOURCE_ROOT):
    parent = predecessor(str(Path(root).absolute()))
    require([case['name'] for case in packet['cases']] == list(CASE_NAMES), 'AL selected case inventory differs')
    results, challenges = [], []
    for case in packet['cases']:
        exact(case, {'name', 'root_provision_sha256', 'evidence', 'native_boots', 'worker_grants'})
        checked = runtime.verify_evidence(case['evidence'], parent,
            expected_root_provision_sha256=case['root_provision_sha256'], source_root=root)
        state = checked['state']; sessions = checked['snapshot']['sessions']
        grants = []
        for session in sessions:
            files = {name: bytes.fromhex(raw) for name, raw in session['files_hex'].items()}
            grant = load_json_strict(files['grant.json']); grants.append(grant['grant_hash'])
            public = load_json_strict(files['public_challenge.json'])
            challenges.append(public['challenge_commitment_hash'])
        require(case['worker_grants'] == grants, 'selected campaign worker inventory differs')
        kinds = [entry['event']['kind'] for entry in case['evidence']['entries']]
        results.append({'name': case['name'], 'completed_sessions': len(sessions),
            'reserved': list(state.reserved), 'reserved_cost': state.charged_cost,
            'status': state.status, 'pending_retained': state.pending is not None,
            'root_events': len(kinds), 'launch_consumptions': kinds.count('launch'),
            'denials': kinds.count('deny'), 'epoch': checked['cursor']['epoch']})
    require([row['completed_sessions'] for row in results] == [2, 0, 1] and
            [row['launch_consumptions'] for row in results] == [2, 0, 1] and
            [row['denials'] for row in results] == [0, 0, 1] and
            [row['pending_retained'] for row in results] == [False, True, False] and
            [row['epoch'] for row in results] == [2, 2, 1] and
            [row['status'] for row in results] == ['open', 'pending', 'resource_exhausted'],
            'selected AL live campaign outcomes differ')
    require(len(challenges) == 3 and len(set(challenges)) == 3, 'fresh worker challenge bindings repeated')
    expected_names = [case + '-lifetime-' + str(index) for case in CASE_NAMES
                      for index in range(1 if case == 'aggregate_denial' else 2)]
    require(type(packet['native_boots']) is list and
            [boot['name'] for boot in packet['native_boots']] == expected_names,
            'five original authority lifetimes required in exact order')
    for boot in packet['native_boots']:
        exact(boot, {'name', 'case', 'root_provision_sha256', 'export_sha256', 'initial_cursor', 'final_cursor'})
        require(boot['case'] in CASE_NAMES and boot['name'].startswith(boot['case'] + '-lifetime-'),
                'native authority case binding differs')
        _hash(boot['root_provision_sha256']); _hash(boot['export_sha256'])
        runtime._validate_cursor(boot['initial_cursor']); runtime._validate_cursor(boot['final_cursor'])
    for case in packet['cases']:
        require(case['native_boots'] == [boot['name'] for boot in packet['native_boots'] if boot['case'] == case['name']],
                'case native lifetime inventory differs')
    return {'cases': results, 'fresh_worker_sessions': 3, 'fresh_live_challenges': 3,
        'native_authority_lifetimes': 5, 'permanent_reservations': 4,
        'completed_sessions': 3, 'denied_sessions': 1, 'pending_sessions': 1,
        'old_proof_campaigns_rerun': False, 'old_acceptance_reinterpreted': False,
        'complete_resource_accounting': False, 'independently_protected_deployment_established': False}


class PreparedDurableCampaign:
    def __init__(self, raw, root=SOURCE_ROOT):
        require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'bounded AL packet bytes required')
        packet = load_json_strict(raw, require_canonical=True)
        exact(packet, {'schema', 'policy', 'base_commit', 'retained_ak_execution_sha256',
                       'scope', 'cases', 'native_boots', 'claims', 'summary'})
        require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE and
                packet['retained_ak_execution_sha256'] == AK_EXECUTION_SHA and
                canonical(packet['scope']) == canonical(runtime.SCOPE) and
                _false_claims(packet['claims']), 'AL packet scope differs')
        require(canonical(packet['summary']) == canonical(summarize(packet, root)), 'AL selected summary differs')
        self.packet_bytes = raw

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)


def evidence_images(packet):
    return {case['name'] + '.json': canonical(case['evidence']) for case in packet['cases']}


def _verify_exchange(request, reply, exported, *, reservation_test):
    """Bind each original wire outcome to its exact committed root interval."""
    exact(reply, {'protocol', 'request_sha256', 'accepted', 'reason', 'before', 'after', 'committed', 'result'})
    before, after = reply['before'], reply['after']
    entries = exported['entries']
    require(0 <= before['serial'] <= after['serial'] < len(entries), 'native publication interval differs')
    previous = entries[before['serial']]['snapshot']
    rows = entries[before['serial'] + 1:after['serial'] + 1]
    op = request.get('op')
    if op in ('read', 'finish'):
        exact(request, {'protocol', 'op'})
        require(reply['accepted'] is True and not rows and reply['reason'] is None,
                'read/export reply changed authoritative state')
        if op == 'read':
            _, state = runtime._journal(previous, exported['provision'])
            require(canonical(reply['result']) == canonical({'status': state.status, 'reserved': list(state.reserved),
                    'sessions': len(state.completed)}), 'native read state differs')
        else:
            require(after == exported['final_cursor'] and reply['result'] ==
                    {'export_sha256': sha(canonical(exported))}, 'native export reply differs')
        return
    wanted_keys = {'protocol', 'op', 'expected_cursor', 'request_nonce', 'credits'}
    if not rows:
        require(reply['accepted'] is False and reply['result'] is None and
                reply['reason'] == 'protocol_or_authority_refused', 'native protocol refusal differs')
        refused = (set(request) != wanted_keys or request.get('protocol') != PROTOCOL or
            op not in ('run', 'reserve_reference_test') or (op == 'reserve_reference_test' and not reservation_test))
        if not refused:
            try:
                runtime._request({name: request[name] for name in
                    ('expected_cursor', 'request_nonce', 'credits')}, before, previous, exported['provision'])
            except (ResourceError, ValueError, TypeError, KeyError):
                refused = True
        require(refused, 'native refusal has no matching protocol/authority rejection')
        return
    exact(request, wanted_keys)
    require(request['protocol'] == PROTOCOL and canonical(request['expected_cursor']) == canonical(before),
            'native mutation request cursor differs')
    body = {name: request[name] for name in ('expected_cursor', 'request_nonce', 'credits')}
    require(canonical(rows[0]['event']['request']) == canonical(body), 'native request differs from committed admission')
    kinds = [row['event']['kind'] for row in rows]
    if kinds == ['deny']:
        require(op == 'run' and reply['accepted'] is False and reply['result'] is None and
                reply['reason'] == 'aggregate_budget_denied', 'native aggregate denial differs')
        return
    require(reply['accepted'] is True and reply['reason'] is None, 'native committed request lacks acceptance')
    permit = rows[0]['snapshot']['pending']['permit']
    if kinds == ['reserve']:
        require(op == 'reserve_reference_test' and reservation_test and canonical(reply['result']) ==
                canonical({'permit_sha256': permit['permit_sha256'], 'worker_launched': False}),
                'native reservation fixture differs')
        return
    require(op == 'run' and kinds == ['reserve', 'launch', 'complete'], 'native worker publication order differs')
    session = rows[-1]['snapshot']['sessions'][-1]
    files = {name: bytes.fromhex(value) for name, value in session['files_hex'].items()}
    files['durable-session.json'] = canonical({'schema': 'phase17al.authorized-session.v1',
        'permit': permit, 'launch_cursor': runtime._cursor(exported['root_provision_sha256'], rows[1]['event']),
        'completion_cursor': after, 'native_sha256': session['native_sha256'], 'scope': runtime.SCOPE})
    require(reply['result'] == {'session_sha256': {name: sha(raw) for name, raw in files.items()}},
            'native completed session file bindings differ')


def verify_all_native(directory, packet, root=SOURCE_ROOT):
    directory, root = Path(directory), Path(root)
    parent = predecessor(str(root.absolute()))
    hashes, invocations, python_hashes, lifetime_pids = {}, set(), set(), {}
    cases = {case['name']: case for case in packet['cases']}
    expected_files = set()
    prior_exports = {}
    for boot in packet['native_boots']:
        folder = directory / 'authority' / boot['name']
        require(folder.is_dir() and {p.name for p in folder.iterdir()} == set(SERVICE_FILES),
                'exact authority native inventory required')
        raw = {name: (folder / name).read_bytes() for name in SERVICE_FILES}
        require(all(len(value) <= MAX_BYTES for value in raw.values()), 'authority record exceeds bound')
        start, child, result = [load_json_strict(raw[name], require_canonical=True)
                                for name in ('start.json', 'child.json', 'result.json')]
        exact(start, {'schema', 'invocation_id', 'started_at_utc', 'observer_pid', 'command',
            'python_sha256', 'service_sha256', 'capture_sha256', 'root_provision_sha256',
            'boot_nonce', 'reservation_test', 'physical_execution_attested'})
        exact(child, {'schema', 'invocation_id', 'child_pid', 'observer_pid', 'observed_at_utc'})
        exact(result, {'schema', 'invocation_id', 'child_pid', 'completed_at_utc', 'elapsed_ns',
            'returncode', 'native_wait_completed', 'timed_out', 'reader_finished', 'reader_error',
            'export_sha256', 'stream_sha256'})
        for value in (start, child, result):
            _hash(value['invocation_id'], 32)
        for key in ('python_sha256', 'service_sha256', 'capture_sha256', 'root_provision_sha256', 'boot_nonce'):
            _hash(start[key])
        _hash(result['export_sha256'])
        exact(result['stream_sha256'], {'stdin.jsonl', 'stdout.jsonl', 'stderr.txt'})
        for value in result['stream_sha256'].values():
            _hash(value)
        require(_stamp(start['started_at_utc']) <= _stamp(child['observed_at_utc']) <=
                _stamp(result['completed_at_utc']), 'native authority timestamps out of order')
        for value in (start['observer_pid'], child['observer_pid'], child['child_pid'], result['child_pid']):
            _pid(value)
        require(type(result['elapsed_ns']) is int and result['elapsed_ns'] >= 0 and
                type(start['reservation_test']) is bool and
                start['reservation_test'] is (boot['case'] == 'interrupted_reservation'),
                'native authority observation types or fixture dispatch differ')
        require(start['schema'] == child['schema'] == result['schema'] == NATIVE_SCHEMA and
                start['invocation_id'] == child['invocation_id'] == result['invocation_id'] and
                start['invocation_id'] not in invocations, 'authority native identity differs')
        invocations.add(start['invocation_id']); python_hashes.add(start['python_sha256'])
        require(type(child['child_pid']) is int and child['child_pid'] > 0 and
                child['child_pid'] == result['child_pid'] and child['observer_pid'] == start['observer_pid'] and
                child['child_pid'] != child['observer_pid'], 'authority native process binding differs')
        require(type(result['returncode']) is int and result['returncode'] == 0 and
                result['native_wait_completed'] is True and result['reader_finished'] is True and
                result['timed_out'] is False and result['reader_error'] is None and raw['stderr.txt'] == b'',
                'authority native wait incomplete or diagnostics present')
        require(start['service_sha256'] == sha((root / SERVICE).read_bytes()) and
                start['capture_sha256'] == sha(Path(__file__).read_bytes()) and
                start['root_provision_sha256'] == boot['root_provision_sha256'] and
                start['physical_execution_attested'] is False, 'authority native source or scope differs')
        command = start['command']
        require(type(command) is list and len(command) in (14, 15) and
                all(type(arg) is str and arg for arg in command) and
                command[1:5] == ['-I', '-S', '-B', '-u'] and
                command[5].replace('\\', '/').endswith('/' + SERVICE) and
                command[6] == '--directory' and command[8:10] == ['--root-pin', boot['root_provision_sha256']] and
                command[10:12] == ['--boot-nonce', start['boot_nonce']] and command[12] == '--export' and
                (command[14:] == ['--allow-reference-reservation-test'] if start['reservation_test'] else len(command) == 14),
                'authority native command differs')
        require(result['stream_sha256'] == {name: sha(raw[name]) for name in
            ('stdin.jsonl', 'stdout.jsonl', 'stderr.txt')} and
            result['export_sha256'] == boot['export_sha256'] == sha(raw['export.json']),
            'authority native stream/export identities differ')
        exported = load_json_strict(raw['export.json'], require_canonical=True)
        runtime.verify_evidence(exported, parent, expected_root_provision_sha256=boot['root_provision_sha256'], source_root=root)
        case = cases[boot['case']]
        require(exported['entries'] == case['evidence']['entries'][:len(exported['entries'])],
                'native authority export does not match final case prefix')
        previous = prior_exports.get(boot['case'])
        if previous is not None:
            require(exported['entries'][:len(previous)] == previous, 'restart discarded authoritative prefix')
        prior_exports[boot['case']] = exported['entries']
        reopen_index = 1 if previous is None else len(previous)
        require(reopen_index < len(exported['entries']), 'authority lifetime lacks reopening event')
        reopening = exported['entries'][reopen_index]['event']
        require(reopening['kind'] == 'reopen' and reopening['boot_nonce'] == start['boot_nonce'] and
                runtime._cursor(boot['root_provision_sha256'], reopening) == boot['initial_cursor'],
                'authority process is not bound to this exact reopening epoch')
        lifetime_key = (boot['root_provision_sha256'], boot['initial_cursor']['epoch'])
        require(lifetime_key not in lifetime_pids, 'multiple native owners for one captured authority epoch')
        lifetime_pids[lifetime_key] = child['child_pid']
        requests = [load_json_strict(line, require_canonical=True) for line in raw['stdin.jsonl'].splitlines()]
        replies = [load_json_strict(line, require_canonical=True) for line in raw['stdout.jsonl'].splitlines()]
        require(raw['stdin.jsonl'] == b''.join(canonical(row) + b'\n' for row in requests) and
                raw['stdout.jsonl'] == b''.join(canonical(row) + b'\n' for row in replies),
                'authority original stream framing differs')
        require(len(requests) == len(replies) and len(requests) >= 2 and
                requests[0]['op'] == 'read' and requests[-1]['op'] == 'finish', 'authority exchange inventory differs')
        current = boot['initial_cursor']
        cursors = {canonical(runtime._cursor(boot['root_provision_sha256'], row['event'])) for row in exported['entries']}
        for request, reply in zip(requests, replies, strict=True):
            require(reply['protocol'] == PROTOCOL and reply['request_sha256'] == sha(canonical(request)) and
                    canonical(reply['before']) == canonical(current) and
                    canonical(reply['after']) in cursors and
                    type(reply['accepted']) is bool and type(reply['committed']) is bool and
                    reply['committed'] == (canonical(reply['before']) != canonical(reply['after'])),
                    'authority original request/response cursor binding differs')
            _verify_exchange(request, reply, exported, reservation_test=start['reservation_test'])
            current = reply['after']
        require(current == boot['final_cursor'] == exported['final_cursor'] and
                replies[-1]['result'] == {'export_sha256': sha(raw['export.json'])},
                'authority final native export binding differs')
        for name, value in raw.items():
            relative = (folder / name).relative_to(directory).as_posix()
            expected_files.add(relative); hashes[relative] = sha(value)
    require(len(invocations) == 5 and len(python_hashes) == 1, 'authority native lifetime/interpreter inventory differs')
    for case in packet['cases']:
        require(prior_exports[case['name']] == case['evidence']['entries'], 'final case export omitted')
        for session in case['evidence']['entries'][-1]['snapshot']['sessions']:
            files = {name: bytes.fromhex(value) for name, value in session['files_hex'].items()}
            grant = load_json_strict(files['grant.json'])
            folder = directory / 'workers' / case['name'] / grant['grant_hash']
            verified = verify_native_records(folder, grant, files['sealed_transcript.json'],
                load_json_strict(files['worker-accounting.json']), source_root=root)
            require(verified == session['native_sha256'], 'original worker evidence differs from root completion')
            start = load_json_strict((folder / 'start.json').read_bytes())
            child = load_json_strict((folder / 'child.json').read_bytes())
            session_report = load_json_strict(files['session.json'])
            authority_pid = lifetime_pids.get((case['root_provision_sha256'], session['owner_epoch']))
            require(authority_pid is not None and start['observer_pid'] == authority_pid and
                    session_report['controller_pid'] == authority_pid and
                    session_report['worker_pid'] == child['child_pid'],
                    'native worker and session do not belong to the authorized authority lifetime')
            require(start['invocation_id'] not in invocations and start['python_sha256'] in python_hashes,
                    'worker native invocation/interpreter differs')
            invocations.add(start['invocation_id'])
            for name, digest in verified.items():
                relative = (folder / name).relative_to(directory).as_posix()
                expected_files.add(relative); hashes[relative] = digest
    actual_files = set()
    for path in directory.rglob('*'):
        _no_links(path)
        if path.is_file():
            actual_files.add(path.relative_to(directory).as_posix())
    require(actual_files == expected_files and len(invocations) == 8, 'extra/missing native observations')
    return hashes
