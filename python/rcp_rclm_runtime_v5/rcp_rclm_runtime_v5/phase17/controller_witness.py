"""Phase17AJ: an independently anchored reference witness for AI authority.

The witness owns the AI policy and journal. A controller supplies no next-state
verdict. Requests and replies are nonce-bound MAC messages relative to a trusted
bootstrap key; the selected fixture deliberately uses a public reference key.
Legitimate external provisioning, secrecy of a real deployment key, persistent
current-head authority, and host/cryptographic refinement remain assumptions.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import sys
import time

from . import controller_authority as ai
from .materialized import require, sha
from .resource_ledger import ResourceError, ResourceExhausted, _no_links
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest

BASE = 'e8d3c035f1ebbb6a725db2a49583185e10016490'
AI_ROOT = 'artifacts/development/phase17ai/op-cb5401cf6b98/gate'
AI_PACKET_SHA = '3534a0a4559a3fa963f9aa172b9d5357450a60534eaf537153efe634aca762c0'
AI_EXECUTION_SHA = 'e8ef5c0cdc23a0cad79280525394b3415207f51a151815a2aedb46c7281378bd'
AI_SOURCE = 'cb5401cf6b989a44da55780ccea431a13f88266d'
AI_TREE = '1aa5db8af9b282443e157c6bbd251818d86f82a1'
RETAINED_PINS = {AI_ROOT + '/packet.json': AI_PACKET_SHA, AI_ROOT + '/execution.json': AI_EXECUTION_SHA}
SCHEMA = 'rcp-rclm.phase17aj.controller-witness-packet.v1'
POLICY = 'phase17aj.independently-anchored-reference-witness.v1'
PROVISION_SCHEMA = 'phase17aj.witness-provision.v1'
REQUEST_SCHEMA = 'phase17aj.witness-request.v1'
RESPONSE_SCHEMA = 'phase17aj.witness-response.v1'
LEDGER_SCHEMA = 'phase17aj.witness-ledger.v1'
DOMAIN = b'RCPRCLM-PHASE17AJ-WITNESS-V1\0'
REQUEST_DOMAIN = DOMAIN + b'REQUEST\0'
RESPONSE_DOMAIN = DOMAIN + b'RESPONSE\0'
MAX_BYTES = 96 * 1024 * 1024
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_WIRE_BYTES = 8 * 1024 * 1024
MAX_EVENTS = 64
SOURCE_ROOT = Path(__file__).resolve().parents[4]
CODE_PATH = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller_witness.py'
PUBLIC_FIXTURE_KEY = hashlib.sha256(b'Phase17AJ public deterministic reference MAC key; NOT a deployment secret').digest()
FALSE_CLAIMS = ai.FALSE_CLAIMS
SCOPE = {
    'witness': 'separately launched reference process owning the AI policy and journal; independently pinned provisioning and current head',
    'authentication': 'HMAC-SHA256 request/reply binding under a trusted caller/verifier and current witness; every shared-key holder can forge either direction, so no hostile-key-holder resistance, nonrepudiation or external provisioning is established; selected fixture key is public',
    'freshness': 'trusted caller/verifier supplies nonrepeating request nonces and uses the authenticated snapshot cursor for compare-and-advance; a read alone does not promise continuing currentness',
    'currentness': 'exact compare-and-advance in one trusted witness history; an authenticated old read is not current after a later advance',
    'restart': 'explicit independently retained expected witness head required; pending work retains full charges and loses execution ownership',
    'controller': 'actual unchanged AI/AH reference controller and evaluator for separately provisioned inactive AF sources',
    'resource': 'AI declared nonrefundable reference tariff; witness work, transport, hashing, persistence and host costs remain outside it',
    'durability': 'trusted filesystem and one cooperating writer; two-file mismatch fails closed without automatic repair',
    'external_issuer_authenticated': False, 'witness_machine_rollback_resistance_established': False,
    'complete_resource_accounting': False, 'fresh_worker_sessions': 0, 'fresh_live_challenges': 0,
    'old_proof_campaigns_rerun': False, 'promotion_api': False,
}


def _same(a, b, message):
    require(canonical(a) == canonical(b), message)


def _snapshot(value):
    return load_json_strict(canonical(copy.deepcopy(value)))


def _exact(value, names, label):
    require(type(value) is dict and set(value) == set(names), 'exact ' + label + ' fields required')


def _hash(value, label):
    ai._hash(value, label)
    return value


def _prepared(value):
    require(type(value) is ai.PreparedControllerAuthority and sha(value.packet_bytes) == AI_PACKET_SHA,
            'exact completed AI authority packet required')
    return value


def witness_identity(root=SOURCE_ROOT):
    root = Path(root); _no_links(root / CODE_PATH)
    bound = {**ai.authority_identity(root)['code_sha256'], CODE_PATH: sha((root / CODE_PATH).read_bytes())}
    return {'policy': POLICY, 'code_sha256': bound, 'implementation_sha256': digest(bound),
            'external_issuer_authenticated': False, 'promotion_authorized': False}


def _key(key):
    require(type(key) is bytes and len(key) == 32, 'exact 32-byte independently provisioned MAC key required')
    return key


def make_provision(prepared, *, case_name, witness_id, key, identity=None):
    _prepared(prepared); _key(key)
    identity = witness_identity() if identity is None else _snapshot(identity)
    _same(identity, witness_identity(), 'witness implementation differs')
    cases = {c['name']: c for c in prepared.packet['cases']}
    require(case_name in cases, 'selected AI case required')
    require(type(witness_id) is str and 0 < len(witness_id) <= 128, 'bounded witness identity required')
    case = cases[case_name]
    return {'schema': PROVISION_SCHEMA, 'witness_id': witness_id, 'reference_case': case_name,
        'ai_packet_sha256': AI_PACKET_SHA, 'authority_identity': prepared.packet['authority_identity'],
        'authority_policy': case['authority_policy'], 'authority_policy_sha256': case['policy_sha256'],
        'witness_identity': identity, 'key_commitment': sha(key),
        'authentication': 'HMAC-SHA256-relative-to-independent-bootstrap-key',
        'public_reference_fixture_key': key == PUBLIC_FIXTURE_KEY,
        'external_issuer_authenticated': False, 'complete_resource_accounting': False}


def _provision(prepared, value, key, expected_sha256):
    _hash(expected_sha256, 'independent witness provisioning anchor')
    value = _snapshot(value)
    require(digest(value) == expected_sha256, 'witness provision differs from independent anchor')
    _exact(value, {'schema', 'witness_id', 'reference_case', 'ai_packet_sha256', 'authority_identity',
        'authority_policy', 'authority_policy_sha256', 'witness_identity', 'key_commitment',
        'authentication', 'public_reference_fixture_key', 'external_issuer_authenticated',
        'complete_resource_accounting'}, 'witness provision')
    _same(value, make_provision(prepared, case_name=value['reference_case'], witness_id=value['witness_id'],
        key=key), 'witness policy, key, source or implementation differs')
    return value


def _mac(key, domain, body):
    return hmac.new(_key(key), domain + canonical(body), hashlib.sha256).hexdigest()


def request(provision_sha256, key, *, op, nonce, cursor=None, source_id=None,
            owner_commitment=None, owner_token=None, lease_hash=None):
    _hash(provision_sha256, 'provision'); _hash(nonce, 'fresh request nonce')
    body = {'op': op, 'nonce': nonce, 'cursor': _snapshot(cursor), 'source_id': source_id,
            'owner_commitment': owner_commitment, 'owner_token': owner_token, 'lease_hash': lease_hash}
    core = {'schema': REQUEST_SCHEMA, 'provision_sha256': provision_sha256, 'body': body}
    return {**core, 'mac': _mac(key, REQUEST_DOMAIN, core)}


def _request(value, provision_sha256, key):
    value = _snapshot(value)
    _exact(value, {'schema', 'provision_sha256', 'body', 'mac'}, 'witness request')
    core = {k: value[k] for k in ('schema', 'provision_sha256', 'body')}
    require(value['schema'] == REQUEST_SCHEMA and value['provision_sha256'] == provision_sha256,
            'wrong witness provisioning identity')
    _hash(value['mac'], 'request MAC')
    require(hmac.compare_digest(value['mac'], _mac(key, REQUEST_DOMAIN, core)), 'request MAC differs')
    body = value['body']
    _exact(body, {'op', 'nonce', 'cursor', 'source_id', 'owner_commitment', 'owner_token', 'lease_hash'},
           'witness command')
    _hash(body['nonce'], 'fresh request nonce')
    require(body['op'] in ('read', 'reserve', 'execute', 'stop', 'reopen'), 'unsupported witness operation')
    return value


def _reply(key, provision_sha256, supplied_request, payload):
    core = {'schema': RESPONSE_SCHEMA, 'provision_sha256': provision_sha256,
            'request_sha256': digest(supplied_request), 'nonce': supplied_request['body']['nonce'],
            'payload': _snapshot(payload)}
    return {**core, 'mac': _mac(key, RESPONSE_DOMAIN, core)}


def verify_reply(reply, supplied_request, *, expected_provision_sha256, key):
    supplied_request = _request(supplied_request, expected_provision_sha256, key)
    reply = _snapshot(reply)
    _exact(reply, {'schema', 'provision_sha256', 'request_sha256', 'nonce', 'payload', 'mac'}, 'witness reply')
    core = {k: reply[k] for k in ('schema', 'provision_sha256', 'request_sha256', 'nonce', 'payload')}
    require(reply['schema'] == RESPONSE_SCHEMA and reply['provision_sha256'] == expected_provision_sha256 and
            reply['request_sha256'] == digest(supplied_request) and reply['nonce'] == supplied_request['body']['nonce'],
            'reply is not bound to this provision and fresh request')
    _hash(reply['mac'], 'reply MAC')
    require(hmac.compare_digest(reply['mac'], _mac(key, RESPONSE_DOMAIN, core)), 'reply MAC differs')
    return _snapshot(reply['payload'])


def _event(body, index, previous):
    core = {'index': index, 'previous': previous, 'body': body}
    return {**core, 'hash': sha(DOMAIN + canonical(core))}


def _write_new(path, raw):
    _no_links(path)
    with open(path, 'xb', buffering=0) as stream:
        require(stream.write(raw) == len(raw), 'short witness provisioning write')
        stream.flush(); os.fsync(stream.fileno())


class WitnessAuthority:
    """One authoritative witness history, with no caller-supplied state transition.

    A path-free instance is deterministic reconstruction. Disk reopening requires
    an independently supplied exact witness head. Any inner/outer journal split
    is retained and refused; it is never repaired from a caller's preferred copy.
    """
    def __init__(self, directory, prepared, provision, key, *, expected_provision_sha256,
                 expected_head=None, retained_ledger=None, retained_authority=None):
        self.prepared = _prepared(prepared); self.key = _key(key)
        self._provision_bytes = canonical(_provision(prepared, provision, key, expected_provision_sha256))
        self.provision_sha256 = expected_provision_sha256
        self.directory = None if directory is None else Path(directory).absolute()
        self._closed = self._poisoned = False; self._live_owner = None
        self._raw = b''; self._rows = []; self._used = []; self._file = None
        self._ai = None; self._last_session = None
        try:
            if expected_head is not None:
                _hash(expected_head, 'independent current witness head')
                if self.directory is not None:
                    require(retained_ledger is None and retained_authority is None,
                            'disk witness cannot import alternative journal images')
                    for name in ('witness.jsonl', 'authority.jsonl'):
                        _no_links(self.directory / name)
                    retained_ledger = (self.directory / 'witness.jsonl').read_bytes()
                    retained_authority = (self.directory / 'authority.jsonl').read_bytes()
                require(type(retained_ledger) is bytes and type(retained_authority) is bytes,
                        'reopening requires complete original witness and authority bytes')
                reconstructed = replay_witness(retained_ledger, prepared, self.provision, key,
                    expected_provision_sha256=expected_provision_sha256, expected_head=expected_head)
                require(reconstructed._ai.raw == retained_authority,
                        'witness/authority journal split; preserve without automatic repair')
                self._raw, self._rows, self._used = reconstructed._raw, reconstructed._rows, reconstructed._used
                sessions = reconstructed._ai.sessions; ai_head = reconstructed._ai.state.head
                reconstructed.close()
                self._ai = ai.ControllerAuthority(None if self.directory is None else self.directory / 'authority.jsonl',
                    prepared.producer_domain(), self.provision['authority_identity'],
                    expected_policy=self.provision['authority_policy'],
                    expected_policy_sha256=self.provision['authority_policy_sha256'],
                    expected_head=ai_head, completed_sessions=sessions,
                    retained_raw=retained_authority if self.directory is None else None)
                if self.directory is not None:
                    self._file = open(self.directory / 'witness.jsonl', 'r+b', buffering=0)
            else:
                require(retained_ledger is None and retained_authority is None,
                        'new witness cannot select an existing history')
                if self.directory is not None:
                    require(self.directory.is_dir() and not (self.directory / 'witness.jsonl').exists(),
                            'new witness requires an uninitialized provisioned directory')
                    self._file = open(self.directory / 'witness.jsonl', 'x+b', buffering=0)
                self._ai = ai.ControllerAuthority(None if self.directory is None else self.directory / 'authority.jsonl',
                    prepared.producer_domain(), self.provision['authority_identity'],
                    expected_policy=self.provision['authority_policy'],
                    expected_policy_sha256=self.provision['authority_policy_sha256'])
                self._append({'kind': 'open', 'schema': LEDGER_SCHEMA,
                    'provision_sha256': self.provision_sha256, 'authority_head_after': self._ai.state.head,
                    'authority_state_after': self._ai.state.to_json()})
        except BaseException:
            self.close(); raise

    @property
    def provision(self):
        return load_json_strict(self._provision_bytes)

    @property
    def raw(self):
        self._check(); return self._raw

    @property
    def state(self):
        self._check()
        return {'revision': len(self._rows) - 1, 'witness_head': self._rows[-1]['hash'],
                'authority_head': self._ai.state.head, 'authority_state': self._ai.state.to_json(),
                'provision_sha256': self.provision_sha256}

    @property
    def cursor(self):
        state = self.state
        return {k: state[k] for k in ('revision', 'witness_head', 'authority_head')}

    @property
    def records(self):
        self._check()
        return [_snapshot(row) for row in self._rows]

    def _check(self):
        require(not self._closed and not self._poisoned, 'closed or poisoned witness')
        self._ai._check()
        if self._file is not None:
            _no_links(self.directory / 'witness.jsonl')
            require(os.path.samestat(os.fstat(self._file.fileno()), (self.directory / 'witness.jsonl').stat()),
                    'witness journal replaced')
            self._file.seek(0)
            require(self._file.read(MAX_LEDGER_BYTES + 1) == self._raw, 'witness journal changed externally')

    def _append(self, body):
        require(len(self._rows) < MAX_EVENTS, 'witness event bound exceeded')
        previous = self._rows[-1]['hash'] if self._rows else ai.ZERO
        row = _event(body, len(self._rows), previous)
        require(row['hash'] != previous and bool(row['hash']), 'witness publication must advance its local head')
        line = canonical(row) + b'\n'
        require(len(self._raw) + len(line) <= MAX_LEDGER_BYTES, 'witness byte bound exceeded')
        if self._file is not None:
            try:
                self._file.seek(0, os.SEEK_END)
                require(self._file.write(line) == len(line), 'short witness journal write')
                self._file.flush(); os.fsync(self._file.fileno())
            except BaseException:
                self._poisoned = True; raise
        self._raw += line; self._rows.append(row)

    def _reference_result(self, source_id):
        case = next(c for c in self.prepared.packet['cases'] if c['name'] == self.provision['reference_case'])
        return next(s['result'] for s in case['sessions'] if s['source_id'] == source_id)

    def _advance(self, supplied, *, stored_session=None, allow_reopen=False):
        self._check(); supplied = _request(supplied, self.provision_sha256, self.key); body = supplied['body']
        before = self.state; op = body['op']; nonce = body['nonce']
        require(op != 'read', 'read is not an advancing command')
        _same(body['cursor'], self.cursor, 'stale witness revision or head')
        require(nonce not in self._used, 'witness request nonce already consumed')
        require(len(self._rows) + 1 <= MAX_EVENTS and len(self._raw) + 2 * MAX_WIRE_BYTES <= MAX_LEDGER_BYTES,
                'witness cannot retain a complete operation')
        session = None; lease = None; denied = False
        if op == 'reserve':
            require(body['owner_token'] is None and body['lease_hash'] is None,
                    'reservation cannot supply an execution token or issued lease')
            _hash(body['owner_commitment'], 'live execution-owner commitment')
            require(body['source_id'] in ai.ah.SOURCES, 'unauthorized source')
            try:
                lease = self._ai.reserve(body['source_id'], expected_head=before['authority_head'],
                    expected_prefix_hash=self._ai.state.source_states[body['source_id']]['prefix_hash'])
                self._live_owner = body['owner_commitment']
            except ResourceExhausted:
                denied = True; self._live_owner = None
        elif op == 'execute':
            require(body['source_id'] is None and body['owner_commitment'] is None,
                    'execution cannot substitute source or owner commitment')
            _hash(body['owner_token'], 'live execution-owner token'); _hash(body['lease_hash'], 'issued lease')
            require(self._live_owner is not None and sha(bytes.fromhex(body['owner_token'])) == self._live_owner,
                    'execution owner absent, wrong or lost on reopening')
            require(self._ai.state.pending is not None and body['lease_hash'] == self._ai.state.pending['lease_hash'],
                    'execution does not name the current issued lease')
            lease = self._ai.state.pending
            if stored_session is not None:
                _same(stored_session['lease'], lease, 'saved witness completion substitutes lease')
                session = self._ai.complete(lease, stored_session['result'], expected_head=before['authority_head'])
                _same(session, stored_session, 'saved witness completion differs')
            elif self.directory is None:
                session = self._ai.complete(lease, self._reference_result(lease['source_permit']['source_id']),
                                            expected_head=before['authority_head'])
            else:
                name = 'work-' + str(self._ai.state.serial - 1) + '.jsonl'
                session = self._ai.execute(lease, expected_head=before['authority_head'],
                                          journal_path=self.directory / name)
            self._live_owner = None; self._last_session = _snapshot(session)
        elif op in ('stop', 'reopen'):
            require(all(body[k] is None for k in ('source_id', 'owner_commitment', 'owner_token', 'lease_hash')),
                    'administrative witness command has extraneous authority')
            if op == 'stop':
                self._ai.stop(expected_head=before['authority_head']); self._live_owner = None
            else:
                require(allow_reopen, 'controller cannot issue witness reopen')
                raw, sessions, head = self._ai.raw, self._ai.sessions, self._ai.state.head
                self._ai.close()
                self._ai = ai.ControllerAuthority(None if self.directory is None else self.directory / 'authority.jsonl',
                    self.prepared.producer_domain(), self.provision['authority_identity'],
                    expected_policy=self.provision['authority_policy'],
                    expected_policy_sha256=self.provision['authority_policy_sha256'], expected_head=head,
                    completed_sessions=sessions, retained_raw=raw if self.directory is None else None)
                self._live_owner = None
        else:
            raise ResourceError('unsupported witness advancement')
        try:
            after = self._ai.state
            require(after.head == before['authority_head'] if op == 'reopen' else
                    after.head != before['authority_head'], 'AI journal head does not match the witness operation')
            self._append({'kind': 'deny' if denied else op, 'request': supplied,
                'revision_before': before['revision'], 'witness_head_before': before['witness_head'],
                'authority_head_before': before['authority_head'],
                'authority_head_after': after.head, 'authority_state_after': after.to_json(),
                'session': session})
        except BaseException:
            self._poisoned = True; raise
        self._used.append(nonce)
        return {'ok': True, 'outcome': 'denied' if denied else op,
                'state': self.state, 'lease': lease if not denied else None, 'session': session}

    def reopen(self, nonce):
        supplied = request(self.provision_sha256, self.key, op='reopen', nonce=nonce, cursor=self.cursor)
        return self._advance(supplied, allow_reopen=True)

    def dispatch(self, supplied):
        self._check(); supplied = _request(supplied, self.provision_sha256, self.key)
        body = supplied['body']
        try:
            require(body['op'] != 'reopen', 'controller cannot issue witness reopen')
            if body['op'] == 'read':
                require(all(body[k] is None for k in ('cursor', 'source_id', 'owner_commitment', 'owner_token', 'lease_hash')),
                        'read cannot confer or select authority')
                payload = {'ok': True, 'outcome': 'read', 'state': self.state, 'lease': None, 'session': None}
            else:
                payload = self._advance(supplied)
        except (ValueError, StopIteration):
            if self._poisoned:
                raise
            payload = {'ok': False, 'outcome': 'refused', 'state': self.state, 'lease': None, 'session': None}
        return _reply(self.key, self.provision_sha256, supplied, payload)

    def close(self):
        if self._file is not None:
            self._file.close(); self._file = None
        if self._ai is not None:
            self._ai.close()
        self._closed = True


def replay_witness(raw, prepared, provision, key, *, expected_provision_sha256, expected_head):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_LEDGER_BYTES and raw.endswith(b'\n'),
            'complete bounded witness ledger required')
    lines = raw.splitlines(keepends=True)
    require(len(lines) <= MAX_EVENTS and all(line.endswith(b'\n') and not line.endswith(b'\r\n') for line in lines),
            'witness newline or event inventory differs')
    rows = [load_json_strict(line[:-1]) for line in lines]
    for index, (line, row) in enumerate(zip(lines, rows, strict=True)):
        _exact(row, {'index', 'previous', 'body', 'hash'}, 'witness ledger record')
        require(type(row['index']) is int and row['index'] == index and canonical(row) + b'\n' == line,
                'witness record is not canonical and ordered')
        _same(row, _event(row['body'], index, rows[index - 1]['hash'] if index else ai.ZERO), 'witness hash chain differs')
    require(rows[-1]['hash'] == expected_head, 'witness ledger differs from independent current head')
    result = WitnessAuthority(None, prepared, provision, key, expected_provision_sha256=expected_provision_sha256)
    try:
        _same(result._rows[0], rows[0], 'witness initial provision or authority differs')
        for row in rows[1:]:
            body = row['body']
            _exact(body, {'kind', 'request', 'revision_before', 'witness_head_before',
                'authority_head_before', 'authority_head_after', 'authority_state_after', 'session'},
                'advancing witness event')
            result._advance(body['request'], stored_session=body['session'], allow_reopen=body['kind'] == 'reopen')
            _same(result._rows[-1], row, 'witness event is not the exact recomputed transition')
        require(result.raw == raw, 'witness replay differs')
        return result
    except BaseException:
        result.close(); raise


def provision_directory(directory, prepared, provision, key, *, expected_provision_sha256):
    directory = Path(directory); _no_links(directory)
    require(not directory.exists(), 'witness provisioning cannot overwrite an existing authority')
    provision = _provision(prepared, provision, key, expected_provision_sha256)
    directory.mkdir(parents=True)
    _write_new(directory / 'provision.json', canonical(provision))
    _write_new(directory / 'fixture-key.bin' if provision['public_reference_fixture_key'] else directory / 'bootstrap-key.bin', key)
    witness = WitnessAuthority(directory, prepared, provision, key, expected_provision_sha256=expected_provision_sha256)
    head = witness.state['witness_head']; witness.close()
    return head


class _NativeTransport:
    def __init__(self, root, directory, native_directory, *, provision_sha256, expected_head, boot_nonce):
        import queue
        import threading
        import uuid
        self.directory = Path(directory); self.native = Path(native_directory)
        self.native.mkdir(parents=True); self._closed = False; self._response_timed_out = False
        self._stdin = open(self.native / 'stdin.bin', 'xb', buffering=0)
        self._stdout = open(self.native / 'stdout.bin', 'xb', buffering=0)
        self._stderr = open(self.native / 'stderr.bin', 'xb', buffering=0)
        self._queue = queue.Queue(); self._thread_error = None
        root = Path(root).absolute()
        argv = [sys.executable, '-B', '-m', 'rcp_rclm_runtime_v5.phase17.controller_witness',
                '--serve', '--root', str(root), '--directory', str(self.directory),
                '--provision-sha256', provision_sha256, '--expected-head', expected_head,
                '--boot-nonce', boot_nonce]
        self.started = datetime.now(timezone.utc).isoformat(); self.t0 = time.monotonic_ns()
        self.start = {'schema': 'phase17aj.witness-native-start.v1', 'invocation_id': uuid.uuid4().hex,
            'argv': argv, 'source_root': str(root), 'witness_directory': str(self.directory),
            'provision_sha256': provision_sha256, 'expected_head': expected_head, 'boot_nonce': boot_nonce,
            'ai_packet_sha256': AI_PACKET_SHA, 'witness_identity': witness_identity(root),
            'started_at_utc': self.started}
        _write_new(self.native / 'start.json', canonical(self.start))
        environment = os.environ.copy()
        environment['PYTHONPATH'] = os.pathsep.join(str(root / 'python' / ('rcp_rclm_runtime_v' + str(v)))
                                                  for v in (2, 3, 4, 5))
        environment['PYTHONDONTWRITEBYTECODE'] = '1'; environment['PYTHONUTF8'] = '1'
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self._stderr, env=environment, cwd=root)
        self.pid = self.process.pid

        def reader():
            try:
                while True:
                    line = self.process.stdout.readline(MAX_WIRE_BYTES + 1)
                    if not line:
                        self._queue.put(None); return
                    require(len(line) <= MAX_WIRE_BYTES and line.endswith(b'\n'), 'witness response exceeds framing bound')
                    self._stdout.write(line); self._queue.put(line)
            except BaseException as exc:
                self._thread_error = str(exc); self._queue.put(None)
        self._thread = threading.Thread(target=reader, daemon=True); self._thread.start()

    def call(self, supplied):
        import queue
        raw = canonical(supplied) + b'\n'
        require(len(raw) <= MAX_WIRE_BYTES, 'witness request exceeds framing bound')
        self._stdin.write(raw)
        self.process.stdin.write(raw); self.process.stdin.flush()
        try:
            line = self._queue.get(timeout=600)
        except queue.Empty:
            self._response_timed_out = True
            self.process.kill()
            raise ResourceError('witness response timed out')
        require(line is not None and self._thread_error is None, 'witness ended without a complete response')
        value = load_json_strict(line[:-1]); require(canonical(value) + b'\n' == line, 'noncanonical witness response')
        return value

    def close(self):
        if self._closed:
            return
        self._closed = True; timed_out = self._response_timed_out
        try:
            self.process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            code = self.process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            timed_out = True; self.process.kill(); code = self.process.wait()
        self._thread.join(timeout=30)
        if not self._thread.is_alive():
            self.process.stdout.close()
        for stream in (self._stdin, self._stdout, self._stderr):
            stream.flush(); os.fsync(stream.fileno()); stream.close()
        records = {name: {'bytes': (self.native / name).stat().st_size,
                         'sha256': sha((self.native / name).read_bytes())}
                   for name in ('stdin.bin', 'stdout.bin', 'stderr.bin')}
        record = {'schema': 'phase17aj.witness-native-result.v1', 'invocation_id': self.start['invocation_id'],
            'pid': self.pid, 'started_at_utc': self.started, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
            'elapsed_ns': time.monotonic_ns() - self.t0, 'returncode': code,
            'timed_out': timed_out, 'native_wait_completed': True,
            'reader_finished': not self._thread.is_alive(), 'reader_error': self._thread_error,
            'start_sha256': sha((self.native / 'start.json').read_bytes()), 'streams': records}
        _write_new(self.native / 'native-result.json', canonical(record))
        require(code == 0 and not timed_out and not self._thread.is_alive() and self._thread_error is None and
                records['stderr.bin']['bytes'] == 0, 'witness process did not complete cleanly')


def _serve(root, directory, provision_sha256, expected_head, boot_nonce):
    root, directory = Path(root), Path(directory)
    require(root.resolve() == SOURCE_ROOT.resolve(), 'witness source root differs from imported code')
    for name in ('provision.json', 'witness.jsonl', 'authority.jsonl'):
        _no_links(directory / name)
    provision = load_json_strict((directory / 'provision.json').read_bytes())
    name = 'fixture-key.bin' if provision.get('public_reference_fixture_key') is True else 'bootstrap-key.bin'
    _no_links(directory / name); key = (directory / name).read_bytes()
    raw = (root / AI_ROOT / 'packet.json').read_bytes()
    require(sha(raw) == AI_PACKET_SHA, 'witness retained AI packet differs')
    prepared = ai.PreparedControllerAuthority(raw)
    witness = WitnessAuthority(directory, prepared, provision, key,
        expected_provision_sha256=provision_sha256, expected_head=expected_head)
    try:
        witness.reopen(boot_nonce)
        while True:
            line = sys.stdin.buffer.readline(MAX_WIRE_BYTES + 1)
            if not line:
                break
            require(len(line) <= MAX_WIRE_BYTES and line.endswith(b'\n') and not line.endswith(b'\r\n'),
                    'bounded canonical witness request frame required')
            supplied = load_json_strict(line[:-1])
            require(canonical(supplied) + b'\n' == line, 'canonical request frame required')
            response = witness.dispatch(supplied)
            sys.stdout.buffer.write(canonical(response) + b'\n'); sys.stdout.buffer.flush()
    finally:
        witness.close()


def case_specs():
    return (
        {'name': 'shared_two_sources', 'ai_case_index': 0, 'boots': 2},
        {'name': 'interrupted_reservation', 'ai_case_index': 4, 'boots': 2},
        {'name': 'aggregate_denial', 'ai_case_index': 1, 'boots': 1},
    )


def _nonce(case, label):
    return sha(DOMAIN + b'PUBLIC-REFERENCE-NONCE\0' + (case + ':' + label).encode())


def _case_records(rows):
    result = []; completed = 0
    for previous, row in zip(rows, rows[1:]):
        body = row['body']; request_body = body['request']['body']; kind = body['kind']
        commitment = request_body['owner_commitment']
        source_id = request_body['source_id']; session_index = None
        if kind == 'execute':
            commitment = sha(bytes.fromhex(request_body['owner_token']))
            source_id = body['session']['source_id']; session_index = completed; completed += 1
        result.append({'kind': kind, 'revision_before': body['revision_before'], 'revision_after': row['index'],
            'witness_head_before': row['previous'], 'witness_head_after': row['hash'],
            'authority_head_before': body['authority_head_before'], 'authority_head_after': body['authority_head_after'],
            'nonce': request_body['nonce'], 'owner_commitment': commitment, 'source_id': source_id,
            'session_index': session_index,
            'ai_state_before': previous['body']['authority_state_after'],
            'ai_state_after': body['authority_state_after']})
    return result


def _derive(prepared, identity, packages=None):
    _prepared(prepared); _same(identity, witness_identity(), 'current witness implementation differs')
    cases = []; images = {}; native_boots = []
    for spec in case_specs():
        name = spec['name']; key = PUBLIC_FIXTURE_KEY
        provision = make_provision(prepared, case_name=name, witness_id='phase17aj.reference.' + name,
                                   key=key, identity=identity)
        provision_sha = digest(provision)
        directory = None if packages is None else packages / 'witness-authorities' / name
        if directory is None:
            witness = WitnessAuthority(None, prepared, provision, key, expected_provision_sha256=provision_sha)
            initial_head = witness.state['witness_head']
        else:
            initial_head = provision_directory(directory, prepared, provision, key,
                                               expected_provision_sha256=provision_sha)
            witness = None
        transport = None; head = initial_head; wire = []; sessions = []; refusals = []
        boot_number = 0; request_number = 0; boot = None; current = None

        def start_boot():
            nonlocal transport, witness, boot, boot_number, head
            boot_name = name + '-' + str(boot_number); boot_nonce = _nonce(name, 'boot-' + str(boot_number))
            if directory is None:
                if boot_number:
                    raw, authority_raw = witness.raw, witness._ai.raw; witness.close()
                    witness = WitnessAuthority(None, prepared, provision, key,
                        expected_provision_sha256=provision_sha, expected_head=head,
                        retained_ledger=raw, retained_authority=authority_raw)
                witness.reopen(boot_nonce)
            else:
                transport = _NativeTransport(SOURCE_ROOT, directory, packages / 'witness-native' / boot_name,
                    provision_sha256=provision_sha, expected_head=head, boot_nonce=boot_nonce)
            boot = {'name': boot_name, 'case': name, 'expected_head': head, 'boot_nonce': boot_nonce,
                    'provision_sha256': provision_sha, 'request_sha256': [], 'response_sha256': []}
            native_boots.append(boot); boot_number += 1

        def close_boot():
            nonlocal transport
            if transport is not None:
                transport.close(); transport = None

        def call(op, *, cursor=None, source_id=None, owner=None, lease_hash=None, nonce=None):
            nonlocal current, head, request_number
            nonce = _nonce(name, 'request-' + str(request_number)) if nonce is None else nonce
            request_number += 1
            supplied = request(provision_sha, key, op=op, nonce=nonce, cursor=cursor,
                source_id=source_id, owner_commitment=sha(bytes.fromhex(owner)) if op == 'reserve' else None,
                owner_token=owner if op == 'execute' else None, lease_hash=lease_hash)
            response = witness.dispatch(supplied) if directory is None else transport.call(supplied)
            payload = verify_reply(response, supplied, expected_provision_sha256=provision_sha, key=key)
            wire.append({'boot': boot['name'], 'request': supplied, 'response': response})
            boot['request_sha256'].append(sha(canonical(supplied) + b'\n'))
            boot['response_sha256'].append(sha(canonical(response) + b'\n'))
            current = payload['state']; head = current['witness_head']
            return supplied, response, payload

        def cursor():
            return {k: current[k] for k in ('revision', 'witness_head', 'authority_head')}

        def ok(payload, outcome):
            require(payload['ok'] is True and payload['outcome'] == outcome, 'selected witness operation did not succeed')

        def refused(payload, label):
            require(payload['ok'] is False and payload['outcome'] == 'refused', 'selected witness refusal missing')
            refusals.append(label)

        owner1, owner2, stranger = (_nonce(name, x) for x in ('owner-1', 'owner-2', 'stranger'))
        try:
            start_boot()
            first_read, old_reply, payload = call('read'); ok(payload, 'read'); old_cursor = cursor()
            _, _, payload = call('reserve', cursor=old_cursor, source_id='af_before', owner=owner1)
            ok(payload, 'reserve'); first_lease = payload['lease']; reserved_cursor = cursor()
            _, _, payload = call('reserve', cursor=old_cursor, source_id='af_after', owner=stranger)
            refused(payload, 'cloned-stale-controller-reservation')
            _, _, payload = call('execute', cursor=cursor(), owner=stranger, lease_hash=first_lease['lease_hash'])
            refused(payload, 'foreign-execution-owner')
            replay_request = request(provision_sha, key, op='read', nonce=_nonce(name, 'different-fresh-read'))
            replay_refused = False
            try:
                verify_reply(old_reply, replay_request, expected_provision_sha256=provision_sha, key=key)
            except ValueError:
                replay_refused = True
            require(replay_refused, 'old authenticated read accepted for a different request')
            if name == 'interrupted_reservation':
                close_boot(); start_boot(); _, _, payload = call('read'); ok(payload, 'read')
                _, _, payload = call('execute', cursor=cursor(), owner=owner1, lease_hash=first_lease['lease_hash'])
                refused(payload, 'reopened-pending-owner-takeover')
                _, _, payload = call('reserve', cursor=cursor(), source_id='af_after', owner=owner2)
                refused(payload, 'reopened-pending-new-reservation')
                _, _, payload = call('stop', cursor=cursor()); refused(payload, 'reopened-pending-stop')
            else:
                _, _, payload = call('execute', cursor=cursor(), owner=owner1, lease_hash=first_lease['lease_hash'])
                ok(payload, 'execute'); sessions.append(payload['session'])
                if name == 'shared_two_sources':
                    close_boot(); start_boot(); _, _, payload = call('read'); ok(payload, 'read')
                    _, _, payload = call('execute', cursor=reserved_cursor, owner=owner1, lease_hash=first_lease['lease_hash'])
                    refused(payload, 'completed-lease-replay-after-restart')
                _, _, payload = call('reserve', cursor=cursor(), source_id='af_after', owner=owner2)
                if name == 'aggregate_denial':
                    ok(payload, 'denied')
                else:
                    ok(payload, 'reserve'); lease = payload['lease']
                    _, _, payload = call('execute', cursor=cursor(), owner=owner2, lease_hash=lease['lease_hash'])
                    ok(payload, 'execute'); sessions.append(payload['session'])
                    _, _, payload = call('stop', cursor=cursor()); ok(payload, 'stop')
            close_boot()
            if directory is None:
                ledger_raw, authority_raw = witness.raw, witness._ai.raw
            else:
                ledger_raw, authority_raw = (directory / 'witness.jsonl').read_bytes(), (directory / 'authority.jsonl').read_bytes()
            checked = replay_witness(ledger_raw, prepared, provision, key,
                expected_provision_sha256=provision_sha, expected_head=head)
            try:
                _same(checked.state, current, 'original witness result differs from saved reconstruction')
                require(checked._ai.raw == authority_raw, 'original inner authority journal differs')
                rows = checked.records
            finally:
                checked.close()
            raw_images = {name + '-witness.jsonl': ledger_raw, name + '-authority.jsonl': authority_raw,
                          name + '-rpc.jsonl': b''.join(canonical(row) + b'\n' for row in wire)}
            for index, session in enumerate(sessions):
                work = bytes.fromhex(session['result']['resource']['journal_hex'])
                if directory is not None:
                    require((directory / ('work-' + str(index) + '.jsonl')).read_bytes() == work,
                            'original witness operation journal differs')
                raw_images[name + '-work-' + str(index) + '.jsonl'] = work
            for filename, raw in raw_images.items():
                images[filename] = {'hex': raw.hex(), 'sha256': sha(raw)}
                if packages is not None:
                    _write_new(packages / 'witness-sessions' / filename, raw)
            cases.append({'name': name, 'ai_case_index': spec['ai_case_index'], 'provision': provision,
                'provision_sha256': provision_sha, 'initial_witness_head': initial_head,
                'records': _case_records(rows), 'final_state': current, 'sessions': sessions,
                'refusals': refusals, 'old_read_reply_refused_for_fresh_nonce': replay_refused,
                'native_boot_names': [b['name'] for b in native_boots if b['case'] == name]})
        finally:
            close_boot()
            if witness is not None:
                witness.close()
    sessions = [s for case in cases for s in case['sessions']]
    main, pending, denied = cases
    require(main['final_state']['authority_state']['status'] == 'external_stop' and
            pending['final_state']['authority_state']['status'] == 'pending' and
            denied['final_state']['authority_state']['status'] == 'resource_denied',
            'selected witness final statuses differ')
    require([s['result']['examined'] for s in main['sessions']] == [1, 8] and len(sessions) == 3,
            'selected witness actual reference results differ')
    return {'witness_identity': identity, 'witness_cases': cases, 'journal_images': images,
        'native_boots': native_boots,
        'summary': {'witness_cases': 3, 'required_reference_witness_lifetimes': 5,
            'completed_reference_sessions': 3, 'issued_reference_leases': 4,
            'denied_reference_leases': 1, 'retained_interrupted_reservations': 1,
            'reference_candidate_attempts': sum(s['result']['examined'] for s in sessions),
            'metered_reference_operations': sum(s['result']['resource']['operation_count'] for s in sessions),
            'source_states': 2, 'fixed_catalog_tasks': 282,
            'main_reserved_reference_cost': main['final_state']['authority_state']['reserved_cost'],
            'main_actual_reference_cost': sum(s['result']['resource']['charged_cost'] for s in main['sessions']),
            'nonce_bound_responses_checked': True, 'independent_current_head_required_on_reopen': True,
            'pending_reopen_takeover_refused': True, 'public_reference_fixture_key': True,
            'external_issuer_authenticated': False, 'witness_machine_rollback_resistance_established': False,
            'complete_resource_accounting': False, 'fresh_worker_sessions': 0, 'fresh_live_challenges': 0,
            'new_physical_successors': 0, 'formal_acceptance_required': True}}


def witness_journal_images(packet):
    result = {}
    for name, value in packet['journal_images'].items():
        require(type(name) is str and name.endswith('.jsonl') and
                all(c.isascii() and (c.isalnum() or c in '-_.') for c in name) and '/' not in name and '\\' not in name,
                'flat portable witness journal filename required')
        _exact(value, {'hex', 'sha256'}, 'witness journal image')
        require(type(value['hex']) is str and len(value['hex']) <= 2 * MAX_LEDGER_BYTES, 'bounded witness image required')
        raw = bytes.fromhex(value['hex'])
        require(raw and raw.hex() == value['hex'] and sha(raw) == value['sha256'], 'witness image checksum differs')
        result[name] = raw
    return result


def verify_witness_native_records(directory, prepared_or_packet):
    directory = Path(directory); _no_links(directory)
    packet = prepared_or_packet.packet if type(prepared_or_packet) is PreparedControllerWitness else prepared_or_packet
    require(type(packet) is dict and packet['schema'] == SCHEMA and packet['base_commit'] == BASE,
            'exact AJ packet required for native evidence')
    images = witness_journal_images(packet)
    wires = [load_json_strict(line) for name, raw in images.items() if name.endswith('-rpc.jsonl')
             for line in raw.splitlines()]
    expected = {boot['name'] + '/' + name for boot in packet['native_boots']
                for name in ('start.json', 'native-result.json', 'stdin.bin', 'stdout.bin', 'stderr.bin')}
    actual = set(); actual_directories = set()
    for path in directory.rglob('*'):
        _no_links(path)
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
        elif path.is_dir():
            actual_directories.add(path.relative_to(directory).as_posix())
        else:
            raise ResourceError('nonregular witness native entry')
    require(actual == expected and actual_directories == {boot['name'] for boot in packet['native_boots']},
            'exact original witness native inventory differs')
    for boot in packet['native_boots']:
        here = directory / boot['name']
        start_raw = (here / 'start.json').read_bytes(); result_raw = (here / 'native-result.json').read_bytes()
        start, result = load_json_strict(start_raw), load_json_strict(result_raw)
        require(canonical(start) == start_raw and canonical(result) == result_raw, 'native metadata is not canonical')
        _exact(start, {'schema', 'invocation_id', 'argv', 'source_root', 'witness_directory',
            'provision_sha256', 'expected_head', 'boot_nonce', 'ai_packet_sha256', 'witness_identity',
            'started_at_utc'}, 'native witness start')
        _exact(result, {'schema', 'invocation_id', 'pid', 'started_at_utc', 'finished_at_utc',
            'elapsed_ns', 'returncode', 'timed_out', 'native_wait_completed', 'reader_finished',
            'reader_error', 'start_sha256', 'streams'}, 'native witness completion')
        require(type(start['invocation_id']) is str and len(start['invocation_id']) == 32 and
                all(c in '0123456789abcdef' for c in start['invocation_id']), 'native invocation identity differs')
        require(start['schema'] == 'phase17aj.witness-native-start.v1' and
                result['schema'] == 'phase17aj.witness-native-result.v1' and
                start['invocation_id'] == result['invocation_id'] and result['start_sha256'] == sha(start_raw),
                'witness native producer identity differs')
        for field in ('provision_sha256', 'expected_head', 'boot_nonce'):
            require(start[field] == boot[field], 'witness native provisioning or head anchor differs')
        _same(start['witness_identity'], packet['witness_identity'], 'witness native code binding differs')
        require(start['ai_packet_sha256'] == AI_PACKET_SHA, 'witness native AI input differs')
        require(type(result['pid']) is int and result['pid'] > 0 and type(result['returncode']) is int and
                result['returncode'] == 0 and result['timed_out'] is False and result['native_wait_completed'] is True and
                result['reader_finished'] is True and result['reader_error'] is None,
                'witness process has no clean observed native completion')
        require(start['started_at_utc'] == result['started_at_utc'] and
                datetime.fromisoformat(result['finished_at_utc']) >= datetime.fromisoformat(result['started_at_utc']) and
                type(result['elapsed_ns']) is int and result['elapsed_ns'] >= 0, 'witness native time record differs')
        argv = start['argv']
        require(type(argv) is list and len(argv) == 15 and all(type(item) is str and item for item in argv) and
                argv[1:4] == ['-B', '-m', 'rcp_rclm_runtime_v5.phase17.controller_witness'] and
                argv[4:] == ['--serve', '--root', start['source_root'], '--directory', start['witness_directory'],
                             '--provision-sha256', boot['provision_sha256'], '--expected-head', boot['expected_head'],
                             '--boot-nonce', boot['boot_nonce']], 'witness native command differs')
        selected = [row for row in wires if row['boot'] == boot['name']]
        wanted_in = b''.join(canonical(row['request']) + b'\n' for row in selected)
        wanted_out = b''.join(canonical(row['response']) + b'\n' for row in selected)
        require([sha(canonical(row['request']) + b'\n') for row in selected] == boot['request_sha256'] and
                [sha(canonical(row['response']) + b'\n') for row in selected] == boot['response_sha256'],
                'native witness request/reply inventory differs')
        require((here / 'stdin.bin').read_bytes() == wanted_in and (here / 'stdout.bin').read_bytes() == wanted_out and
                (here / 'stderr.bin').read_bytes() == b'', 'native witness streams differ from exact semantic wire images')
        _exact(result['streams'], {'stdin.bin', 'stdout.bin', 'stderr.bin'}, 'native witness streams')
        for name, expected_image in result['streams'].items():
            raw = (here / name).read_bytes()
            _same(expected_image, {'bytes': len(raw), 'sha256': sha(raw)}, 'native witness stream checksum differs')
    return {name: sha((directory / name).read_bytes()) for name in sorted(expected)}


def _execution(raw):
    require(type(raw) is bytes and sha(raw) == AI_EXECUTION_SHA, 'exact completed AI execution required')
    result = load_json_strict(raw, require_canonical=False)
    require(result['source_commit'] == AI_SOURCE and result['source_tree'] == AI_TREE and
            result['completed'] is True and result['authority_bound_controller_state_checked'] is True and
            result['authority_issued_reference_grants_checked'] is True and
            result['proof_mode'] == 'real_pinned_lean_completed_stage_lineage' and len(result['source_sha256']) == 565,
            'completed AI source or authority result differs')
    return result


def validate_packet(packet):
    _exact(packet, {'schema', 'policy', 'base_commit', 'controller_authority_packet', 'retained_execution_hex',
        'retained_sha256', 'inherited_source_sha256', 'witness_identity', 'witness_cases', 'journal_images',
        'native_boots', 'summary', 'scope', 'claims'}, 'controller witness packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'controller witness packet identity differs')
    _same(packet['scope'], SCOPE, 'controller witness scope differs')
    _same(packet['claims'], {name: False for name in FALSE_CLAIMS}, 'controller witness claim escalation')
    _same(packet['retained_sha256'], RETAINED_PINS, 'retained AI pins differ')
    raw = canonical(packet['controller_authority_packet']); require(sha(raw) == AI_PACKET_SHA, 'retained AI packet differs')
    prepared = ai.PreparedControllerAuthority(raw)
    _exact(packet['retained_execution_hex'], {AI_ROOT + '/execution.json'}, 'retained AI execution')
    execution = _execution(bytes.fromhex(packet['retained_execution_hex'][AI_ROOT + '/execution.json']))
    _same(packet['inherited_source_sha256'], execution['source_sha256'], 'inherited AI source bindings differ')
    for key, wanted in _derive(prepared, witness_identity()).items():
        _same(packet[key], wanted, 'witness derivation differs: ' + key)
    return prepared


@dataclass(frozen=True, slots=True)
class PreparedControllerWitness:
    packet_bytes: bytes
    _authority: ai.PreparedControllerAuthority = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable controller witness packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical witness packet required')
        object.__setattr__(self, '_authority', validate_packet(packet))

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)

    def controller_authority(self):
        return self._authority

    def authority(self):
        return self._authority

    def producer_domain(self):
        return self._authority.producer_domain()

    def second_step(self):
        return self._authority.second_step()

    def finite(self):
        return self._authority.finite()


def prepare_controller_witness(root: Path, packages: Path, *, persist_witness_journals=True):
    require(type(persist_witness_journals) is bool, 'exact witness persistence Boolean required')
    root, packages = Path(root), Path(packages); _no_links(packages)
    require(not packages.exists() and packages.resolve() != root.resolve() and
            root.resolve() not in packages.resolve().parents, 'new external AJ package workspace required')
    retained = {}
    for name, expected in RETAINED_PINS.items():
        _no_links(root / name); raw = (root / name).read_bytes()
        require(sha(raw) == expected, 'retained AI input differs: ' + name); retained[name] = raw
    execution = _execution(retained[AI_ROOT + '/execution.json'])
    for name, expected in execution['source_sha256'].items():
        _no_links(root / name); require(sha((root / name).read_bytes()) == expected, 'inherited AI source differs: ' + name)
    identity = witness_identity(root); _same(identity, witness_identity(), 'runtime witness root differs')
    inherited = ai.prepare_controller_authority(root, packages / 'inherited', persist_authority_journals=False)
    require(inherited.packet_bytes == retained[AI_ROOT + '/packet.json'], 'reconstructed AI source differs from baseline')
    if persist_witness_journals:
        (packages / 'witness-sessions').mkdir(); (packages / 'witness-native').mkdir()
    derived = _derive(inherited, identity, packages if persist_witness_journals else None)
    prepared = PreparedControllerWitness(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'controller_authority_packet': inherited.packet,
        'retained_execution_hex': {AI_ROOT + '/execution.json': retained[AI_ROOT + '/execution.json'].hex()},
        'retained_sha256': dict(RETAINED_PINS), 'inherited_source_sha256': execution['source_sha256'],
        **derived, 'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS}}))
    require(identity == witness_identity(root), 'witness source changed during preparation')
    for name, raw in retained.items():
        require((root / name).read_bytes() == raw, 'retained AI bytes changed during preparation')
    if persist_witness_journals:
        for name, raw in witness_journal_images(prepared.packet).items():
            require((packages / 'witness-sessions' / name).read_bytes() == raw, 'original witness journal changed')
        verify_witness_native_records(packages / 'witness-native', prepared)
    return prepared


def verify_packet_bytes(raw, recomputed, *, expected_sha256):
    _hash(expected_sha256, 'independent witness packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and type(recomputed) is PreparedControllerWitness and
            raw == recomputed.packet_bytes, 'witness packet differs from anchored fresh reconstruction')
    PreparedControllerWitness(raw)


def summary(prepared):
    require(type(prepared) is PreparedControllerWitness, 'prepared controller witness required')
    return prepared.packet['summary']


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--provision-sha256', required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--boot-nonce', required=True)
    args = parser.parse_args()
    _serve(args.root, args.directory, args.provision_sha256, args.expected_head, args.boot_nonce)

