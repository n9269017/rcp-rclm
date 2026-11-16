"""Phase 17AI: an externally anchored authority for controlled AH sessions.

The coordinator owns the actual restored controller checkpoints and issues the
AH reference allowance before calling its evaluator. Its policy and latest
journal head are independent trust inputs. A digest does not establish external
issuer identity, rollback resistance, physical execution or promotion authority.
The reservation covers AH's explicit bounded-reference tariff only; other work
is listed as unmeasured and never represented as zero.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path
import stat

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from . import producer_domain as ah
from .controller import Action, checkpoint, decide, restore, _hash
from .finite_kernel import FALSE_CLAIMS
from .materialized import require, sha
from .resource_ledger import Policy, ResourceError, ResourceExhausted, _no_links, add, cost

BASE = '8903e306229a1caf22315121b519443639537204'
SCHEMA = 'rcp-rclm.phase17ai.controller-authority-packet.v1'
POLICY = 'phase17ai.externally-anchored-controller-authority.v1'
PROFILE_SCHEMA = 'phase17ai.authority-policy.v1'
LEASE_SCHEMA = 'phase17ai.authority-issued-reference-lease.v1'
JOURNAL_SCHEMA = 'phase17ai.controller-authority-journal.v1'
JOURNAL_DOMAIN = b'RCPRCLM-PHASE17AI-CONTROLLER-AUTHORITY-V1\0'
LEASE_DOMAIN = b'RCPRCLM-PHASE17AI-REFERENCE-LEASE-V1\0'
OBJECTIVE = 'phase17ai.fixed-ae-least-newly-realized-meaning.v1'
AH_ROOT = 'artifacts/development/phase17ah/op-817e423cdd0c/gate'
AH_PACKET_SHA = '55d3b9cdc9bf37629fa7c8e7a3d2e821410992703c1038aa30ab9a9cd300dafe'
AH_EXECUTION_SHA = '78338a9b6744ecd1ef7ec84abfe82f55b0335360c3ea1d2708160c368f481fa6'
AH_SOURCE = '817e423cdd0c959c64df0da3428a9f900b18110b'
AH_TREE = 'd11b8948e97d5f348b3855601cacc9f33c4f909b'
RETAINED_PINS = {AH_ROOT + '/packet.json': AH_PACKET_SHA,
                 AH_ROOT + '/execution.json': AH_EXECUTION_SHA}
MAX_BYTES = 64 * 1024 * 1024
MAX_JOURNAL_BYTES = 8 * 1024 * 1024
MAX_EVENT_BYTES = 1024 * 1024
MAX_EVENTS = 32
ZERO = '0' * 64
SOURCE_ROOT = Path(__file__).resolve().parents[4]
CODE_NAMES = ('controller', 'controller_continuation', 'phase16_adapter',
              'challenge_protocol', 'producer_domain', 'successor_interface',
              'task_interpretation', 'finite_kernel', 'resource_ledger',
              'controller_authority')
CODE_PATHS = tuple('python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/' + name + '.py'
                   for name in CODE_NAMES)
SCOPE = {
    'authority': 'explicitly provisioned local single-writer coordinator; external policy and latest head are trust assumptions',
    'authentication': 'exact provenance relative to those independent anchors, not external identity or cryptographic signature authentication',
    'controller': 'actual checkpoints from the unchanged controller in controlled inactive-source AH reference sessions',
    'objective': 'fixed least newly realized AE task under the unchanged 282-task catalog',
    'evaluator': 'pinned actual controller/evaluator/meaning implementation bytes, recomputed AH outcomes',
    'issuance': 'whole-session reference envelope reserved and flushed before the AH evaluator is called',
    'replay': 'independent exact AH session reconstruction and controller checkpoint restoration',
    'resource': 'nonrefundable AH declared reference envelope, not complete host or campaign work accounting',
    'durability': 'trusted filesystem, process locking and independently retained latest journal head; no automatic pending takeover',
    'source_succession': 'two retained AF projections evaluated separately, no newly linked physical two-step execution',
    'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'old_proof_campaigns_rerun': False,
    'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _same(left, right, message):
    require(canonical(left) == canonical(right), message)


def _nat(value, label, maximum=128):
    require(type(value) is int and 0 <= value <= maximum, 'bounded natural ' + label + ' required')
    return value


def _snapshot(value):
    return load_json_strict(canonical(copy.deepcopy(value)))


def _prepared(value):
    require(type(value) is ah.PreparedProducerDomain and sha(value.packet_bytes) == AH_PACKET_SHA,
            'exact completed AH producer-domain evidence required')
    return value


def authority_identity(root=SOURCE_ROOT):
    """Actual code-byte identities selected outside every candidate request."""
    root = Path(root)
    bindings = {}
    for name in CODE_PATHS:
        path = root / name; _no_links(path)
        require(path.is_file(), 'authority implementation source missing: ' + name)
        bindings[name] = sha(path.read_bytes())
    return {'policy': POLICY, 'objective': OBJECTIVE, 'evaluator': ah.EVALUATOR,
            'code_sha256': bindings, 'implementation_sha256': digest(bindings),
            'external_issuer_authenticated': False, 'promotion_authorized': False}


def _identity(identity):
    value = _snapshot(identity)
    _exact(value, {'policy', 'objective', 'evaluator', 'code_sha256', 'implementation_sha256',
                   'external_issuer_authenticated', 'promotion_authorized'}, 'authority identity')
    _same(value, authority_identity(), 'authority code or fixed objective/evaluator differs')
    return value


def _envelope(attempts):
    _nat(attempts, 'authority reference attempts')
    limits = (attempts, 2 * attempts, 8 * attempts, 8 * attempts)
    return Policy(limits, cost(limits))


def _permit(request):
    return {'source_id': request['source_id'], 'source_sha256': request['source_sha256'],
        'model_state_hash': request['model_state_hash'], 'package_hash': request['source']['package_hash'],
        'history_hash': request['history_hash'], 'context_hash': request['context']['context_hash'],
        'request_sha256': digest(request), 'fixed_catalog_sha256': request['fixed_catalog_sha256'],
        'freeze_hash': request['freeze_hash'], 'initial_prefix_hash': request['initial_prefix_hash'],
        'initial_checkpoint_sha256': sha(canonical(request['initial_checkpoint'])),
        'initial_checkpoint': request['initial_checkpoint']}


@lru_cache(maxsize=8)
def _request_image(prepared, source_id, candidate_credits):
    """Cache only the immutable bytes of an exactly pinned pure reconstruction."""
    _prepared(prepared)
    return canonical(ah.make_request(prepared.successor_interface(), source_id,
                                    candidate_credits=candidate_credits))


def make_authority_policy(prepared, identity, *, authority_id, total_attempts=64,
                          session_attempts=32, candidate_credits=32):
    """Provision a reference policy before requesting any candidate evaluation.

    Choosing and retaining this policy is an external authorization act. This
    constructor does not infer it from a candidate, outcome, or successful rank.
    """
    _prepared(prepared); identity = _identity(identity)
    require(type(authority_id) is str and 0 < len(authority_id) <= 128,
            'bounded authority identity required')
    _nat(total_attempts, 'total allowance'); _nat(session_attempts, 'session allowance', 32)
    _nat(candidate_credits, 'controller credits', 32)
    requests = [load_json_strict(_request_image(prepared, source_id, candidate_credits))
                for source_id in ah.SOURCES]
    return {'schema': PROFILE_SCHEMA, 'authority_id': authority_id, 'policy': POLICY,
        'authority_identity_sha256': digest(identity), 'objective': OBJECTIVE,
        'evaluator': ah.EVALUATOR, 'implementation_sha256': identity['implementation_sha256'],
        'fixed_catalog_sha256': requests[0]['fixed_catalog_sha256'],
        'candidate_credits': candidate_credits, 'session_attempts': session_attempts,
        'total_attempts': total_attempts, 'budget': _envelope(total_attempts).to_json(),
        'source_permits': [_permit(request) for request in requests],
        'trust_model': 'independent-policy-and-rollback-resistant-head',
        'external_issuer_authenticated': False, 'campaign_authority_integrated': False,
        'complete_resource_accounting': False, 'promotion_authorized': False}


def _policy(prepared, identity, value, expected_sha256):
    _hash(expected_sha256, 'external authority policy anchor')
    value = _snapshot(value)
    _exact(value, {'schema', 'authority_id', 'policy', 'authority_identity_sha256', 'objective',
        'evaluator', 'implementation_sha256', 'fixed_catalog_sha256', 'candidate_credits',
        'session_attempts', 'total_attempts', 'budget', 'source_permits', 'trust_model',
        'external_issuer_authenticated', 'campaign_authority_integrated',
        'complete_resource_accounting', 'promotion_authorized'}, 'authority policy')
    require(digest(value) == expected_sha256, 'authority policy differs from external anchor')
    wanted = make_authority_policy(prepared, identity, authority_id=value['authority_id'],
        total_attempts=value['total_attempts'], session_attempts=value['session_attempts'],
        candidate_credits=value['candidate_credits'])
    _same(value, wanted, 'authority policy/source/controller provenance differs')
    return value


def _request(prepared, policy, source_id):
    require(type(source_id) is str and source_id in ah.SOURCES, 'authorized source identity required')
    request = load_json_strict(_request_image(prepared, source_id, policy['candidate_credits']))
    permit = next(p for p in policy['source_permits'] if p['source_id'] == source_id)
    _same(_permit(request), permit, 'authority source/controller permit changed')
    restored = restore(canonical(request['initial_checkpoint']),
                       expected_prefix_hash=permit['initial_prefix_hash'])
    require(sha(checkpoint(restored)) == permit['initial_checkpoint_sha256'],
            'actual initial controller checkpoint differs')
    return request


def _issuable(request, policy):
    prefix = restore(canonical(request['initial_checkpoint']),
                     expected_prefix_hash=request['initial_prefix_hash'])
    require(decide(prefix).action == Action.EVALUATE and policy['session_attempts'] > 0,
            'terminal controller or zero work allowance cannot receive a lease')


def _lease(policy, request, serial, previous):
    _nat(serial, 'lease serial', 2); _hash(previous, 'prior authority head')
    grant = ah.make_grant(request, resource_attempt_limit=policy['session_attempts'])
    body = {'schema': LEASE_SCHEMA, 'authority_id': policy['authority_id'],
        'authority_policy_sha256': digest(policy), 'serial': serial, 'previous_head': previous,
        'source_permit': _permit(request), 'objective': policy['objective'],
        'evaluator': policy['evaluator'], 'implementation_sha256': policy['implementation_sha256'],
        'reference_grant': grant, 'reference_grant_sha256': digest(grant),
        'reserved_envelope': _envelope(policy['session_attempts']).to_json()}
    return {**body, 'lease_hash': sha(LEASE_DOMAIN + canonical(body))}


def _event(body, index, previous):
    core = {'index': index, 'previous': previous, 'body': body}
    return {**core, 'hash': sha(JOURNAL_DOMAIN + canonical(core))}


def _parse_line(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_EVENT_BYTES,
            'bounded authority journal record required')
    row = load_json_strict(raw)
    require(canonical(row) == raw, 'canonical authority journal record required')
    _exact(row, {'index', 'previous', 'body', 'hash'}, 'authority journal record')
    return row


def _completed(prepared, policy, lease, session, *, verify_result):
    _exact(session, {'source_id', 'lease', 'request', 'grant', 'result'}, 'authority session')
    _same(session['lease'], lease, 'completion substitutes a lease')
    source_id = lease['source_permit']['source_id']
    require(session['source_id'] == source_id, 'completion substitutes a source')
    request = _request(prepared, policy, source_id)
    _same(session['request'], request, 'completion substitutes a source request')
    _same(session['grant'], lease['reference_grant'], 'completion substitutes the issued grant')
    result = session['result']
    if verify_result:
        ah.verify_session(prepared.successor_interface(), request, lease['reference_grant'], result,
            expected_source_sha256=request['source_sha256'], expected_request_sha256=digest(request),
            expected_authorization_sha256=lease['reference_grant_sha256'])
    restored = restore(canonical(result['final_checkpoint']),
                       expected_prefix_hash=result['final_prefix_hash'])
    require(restored.frozen.freeze_hash == request['freeze_hash'], 'completion changed actual frozen controller')
    final_checkpoint = checkpoint(restored)
    require(canonical(result['final_checkpoint']) == final_checkpoint,
            'completion final controller checkpoint differs')
    spent = tuple(result['resource']['spent'])
    require(_envelope(policy['session_attempts']).fits(spent), 'completion exceeds issued envelope')
    return {'kind': 'complete', 'lease_hash': lease['lease_hash'], 'source_id': source_id,
        'result_sha256': digest(result), 'reference_journal_sha256': result['resource']['journal_sha256'],
        'final_prefix_hash': restored.prefix_hash, 'final_checkpoint_sha256': sha(final_checkpoint),
        'final_checkpoint': result['final_checkpoint'], 'controller_action': result['controller_action'],
        'status': result['status'], 'examined': result['examined'], 'actual_reference_spent': list(spent)}


@dataclass(frozen=True, slots=True)
class AuthorityState:
    head: str
    event_count: int
    reserved: tuple[int, int, int, int]
    serial: int
    status: str
    pending_bytes: bytes | None
    consumed: tuple[str, ...]
    source_state_bytes: bytes
    completed_bytes: tuple[bytes, ...]

    @property
    def pending(self):
        return None if self.pending_bytes is None else load_json_strict(self.pending_bytes)

    @property
    def source_states(self):
        return load_json_strict(self.source_state_bytes)

    def to_json(self):
        return {'head': self.head, 'event_count': self.event_count, 'reserved': list(self.reserved),
            'reserved_cost': cost(self.reserved), 'serial': self.serial, 'status': self.status,
            'pending': self.pending, 'consumed': list(self.consumed), 'source_states': self.source_states,
            'completed': [load_json_strict(raw) for raw in self.completed_bytes]}


def _replay_authority(raw, prepared, identity, *, expected_policy, expected_policy_sha256,
                      expected_head, sessions=(), verify_results):
    """Replay against separately retained policy/head and independently checked results."""
    _prepared(prepared); identity = _identity(identity)
    policy = _policy(prepared, identity, expected_policy, expected_policy_sha256)
    _hash(expected_head, 'external current authority head')
    require(type(raw) is bytes and 0 < len(raw) <= MAX_JOURNAL_BYTES and raw.endswith(b'\n'),
            'authority journal missing, oversized or truncated')
    require(type(verify_results) is bool, 'explicit result-verification mode required')
    session_images = [canonical(_snapshot(session)) for session in sessions]
    require(len(session_images) <= 2, 'at most one issued session per selected source')
    available = {digest(load_json_strict(image)['result']): image for image in session_images}
    require(len(available) == len(session_images), 'duplicate authority completion evidence')
    used_results = set(); head = ZERO; reserved = (0, 0, 0, 0); serial = 0
    pending = None; consumed = []; completed = []; status = 'new'
    states = {p['source_id']: {'prefix_hash': p['initial_prefix_hash'],
        'checkpoint_sha256': p['initial_checkpoint_sha256'], 'checkpoint': p['initial_checkpoint']}
        for p in policy['source_permits']}
    lines = raw.splitlines(keepends=True)
    require(len(lines) <= MAX_EVENTS, 'authority event limit exceeded')
    for index, line in enumerate(lines):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n'), 'authority newline changed')
        row = _parse_line(line[:-1]); body = row['body']
        require(type(row['index']) is int and row['index'] == index and row['previous'] == head,
                'authority record order or previous head differs')
        _same(row, _event(body, index, head), 'authority record hash differs')
        require(type(body) is dict, 'authority event body required')
        kind = body.get('kind')
        if index == 0:
            _exact(body, {'kind', 'schema', 'authority_identity', 'authority_policy', 'policy_sha256'}, 'authority open')
            require(kind == 'open' and body['schema'] == JOURNAL_SCHEMA and
                    body['policy_sha256'] == expected_policy_sha256, 'authority open identity differs')
            _same(body['authority_identity'], identity, 'authority opening code identity differs')
            _same(body['authority_policy'], policy, 'authority opening policy differs')
            status = 'open'
        elif kind in ('reserve', 'deny'):
            _exact(body, {'kind', 'lease', 'reserved_after'} if kind == 'reserve' else {'kind', 'lease'},
                   'authority reservation')
            require(status == 'open' and pending is None, 'authority not open for a fresh lease')
            supplied = body['lease']; source_id = supplied['source_permit']['source_id']
            require(source_id not in consumed, 'source controller revision already consumed')
            request = _request(prepared, policy, source_id)
            _issuable(request, policy)
            wanted = _lease(policy, request, serial, head)
            _same(supplied, wanted, 'lease not issued from exact authority/source/controller state')
            require(states[source_id]['prefix_hash'] == request['initial_prefix_hash'] and
                    states[source_id]['checkpoint_sha256'] == sha(canonical(request['initial_checkpoint'])),
                    'lease uses stale actual controller state')
            proposed = add(reserved, _envelope(policy['session_attempts']).limits)
            fits = Policy.from_json(policy['budget']).fits(proposed)
            if kind == 'reserve':
                require(fits, 'aggregate authority budget exceeded')
                _same(body['reserved_after'], list(proposed), 'aggregate reference reservation differs')
                reserved = proposed; serial += 1; pending = wanted; status = 'pending'
            else:
                require(not fits, 'false authority budget denial')
                status = 'resource_denied'
        elif kind == 'complete':
            require(status == 'pending' and pending is not None, 'completion has no pending issued lease')
            key = body.get('result_sha256'); require(key in available and key not in used_results,
                                                     'missing or duplicate result evidence')
            session = load_json_strict(available[key])
            wanted = _completed(prepared, policy, pending, session, verify_result=verify_results)
            _same(body, wanted, 'authority completion/controller result differs')
            source_id = wanted['source_id']; consumed.append(source_id); used_results.add(key)
            states[source_id] = {'prefix_hash': wanted['final_prefix_hash'],
                'checkpoint_sha256': wanted['final_checkpoint_sha256'], 'checkpoint': wanted['final_checkpoint']}
            completed.append(canonical(wanted)); pending = None; status = 'open'
            # The entire envelope remains charged; unused work is not refunded.
        elif kind == 'failed':
            _exact(body, {'kind', 'lease_hash', 'reason'}, 'failed authority lease')
            require(status == 'pending' and pending is not None and body['lease_hash'] == pending['lease_hash']
                    and body['reason'] in ('interrupted', 'evaluation_or_verification_failed'),
                    'failure does not resolve the exact pending lease')
            status = 'safety_halt'  # Retain pending identity and all charged counters.
        elif kind == 'stop':
            _exact(body, {'kind'}, 'authority stop')
            require(status == 'open' and pending is None, 'cannot stop an unresolved authority lease')
            status = 'external_stop'
        else:
            raise ResourceError('unknown authority event')
        head = row['hash']
    require(head == expected_head, 'authority journal differs from external latest head')
    require(used_results == set(available), 'extra unissued completion evidence')
    return AuthorityState(head, len(lines), reserved, serial, status,
        None if pending is None else canonical(pending), tuple(consumed), canonical(states), tuple(completed))


def replay_authority(raw, prepared, identity, *, expected_policy, expected_policy_sha256,
                     expected_head, sessions=()):
    return _replay_authority(raw, prepared, identity, expected_policy=expected_policy,
        expected_policy_sha256=expected_policy_sha256, expected_head=expected_head,
        sessions=sessions, verify_results=True)


class ControllerAuthority:
    """Local authority with durable precharge and explicit external-head checks.

    ``path=None`` is deterministic evidence reconstruction only. It never claims
    a persisted reservation. Existing files require their independent current
    head plus their completed session evidence; pending work cannot be resumed.
    """
    def __init__(self, path, prepared, identity, *, expected_policy, expected_policy_sha256,
                 expected_head=None, completed_sessions=(), retained_raw=None):
        self.prepared = _prepared(prepared); self._identity_raw = canonical(_identity(identity))
        self._policy_raw = canonical(_policy(prepared, identity, expected_policy, expected_policy_sha256))
        self.policy_sha256 = expected_policy_sha256
        self.path = None if path is None else Path(path).absolute()
        self._file = self._lock = None; self._closed = False; self._poisoned = False
        self._resumed_pending = False; self._execution_started = False
        self._raw = b''; self._state = None
        self._session_images = tuple(canonical(_snapshot(s)) for s in completed_sessions)
        try:
            if self.path is not None:
                require(retained_raw is None, 'disk authority cannot take an alternate journal image')
                _no_links(self.path); require(self.path.parent.is_dir(), 'authority parent directory missing')
                lock = self.path.with_name(self.path.name + '.lock'); _no_links(lock)
                require(not lock.exists() or lock.is_file(), 'authority lock is not a file')
                self._lock = open(lock, 'a+b', buffering=0)
                if self._lock.seek(0, os.SEEK_END) == 0:
                    self._lock.write(b'L')
                self._lock.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                if expected_head is None:
                    require(not self.path.exists(), 'existing authority requires its external latest head')
                    self._file = open(self.path, 'x+b', buffering=0)
                else:
                    require(self.path.is_file(), 'authority journal missing')
                    self._file = open(self.path, 'r+b', buffering=0)
                    retained_raw = self._file.read(MAX_JOURNAL_BYTES + 1)
            if expected_head is None:
                require(retained_raw is None and not self._session_images,
                        'new authority cannot import prior journal or completions')
                self._append_raw(_event({'kind': 'open', 'schema': JOURNAL_SCHEMA,
                    'authority_identity': self.identity, 'authority_policy': self.policy,
                    'policy_sha256': expected_policy_sha256}, 0, ZERO))
            else:
                require(type(retained_raw) is bytes, 'reopening requires original authority bytes')
                self._state = self._replay(retained_raw, expected_head, verify_results=True)
                self._raw = retained_raw
                self._resumed_pending = self._state.pending is not None
        except BaseException:
            self.close(); raise

    @property
    def identity(self):
        return load_json_strict(self._identity_raw)

    @property
    def policy(self):
        return load_json_strict(self._policy_raw)

    @property
    def sessions(self):
        return [load_json_strict(raw) for raw in self._session_images]

    @property
    def state(self):
        self._check(); return self._state

    @property
    def raw(self):
        self._check(); return self._raw

    def _replay(self, raw, head, *, verify_results):
        return _replay_authority(raw, self.prepared, self.identity, expected_policy=self.policy,
            expected_policy_sha256=self.policy_sha256, expected_head=head,
            sessions=self.sessions, verify_results=verify_results)

    def _check(self):
        require(not self._closed and not self._poisoned, 'closed or poisoned authority')
        if self.path is not None:
            _no_links(self.path)
            require(self._file is not None and stat.S_ISREG(self.path.stat().st_mode) and
                    os.path.samestat(os.fstat(self._file.fileno()), self.path.stat()), 'authority file replaced')
            self._file.seek(0)
            require(self._file.read(MAX_JOURNAL_BYTES + 1) == self._raw, 'authority journal changed externally')

    def _current(self, expected_head):
        self._check(); _hash(expected_head, 'independent current authority head')
        require(self._state.head == expected_head, 'stale authority head')

    def _append_raw(self, row):
        line = canonical(row) + b'\n'
        require(len(line) <= MAX_EVENT_BYTES + 1, 'authority event too large')
        data = self._raw + line
        state = self._replay(data, row['hash'], verify_results=False)
        if self._file is not None:
            try:
                self._file.seek(0, os.SEEK_END)
                require(self._file.write(line) == len(line), 'short authority journal write')
                self._file.flush(); os.fsync(self._file.fileno())
            except BaseException:
                self._poisoned = True; raise
        self._raw = data; self._state = state

    def _append(self, body):
        self._check()
        self._append_raw(_event(body, self._state.event_count, self._state.head))

    def reserve(self, source_id, *, expected_head, expected_prefix_hash):
        self._current(expected_head); _hash(expected_prefix_hash, 'external controller prefix anchor')
        require(self._state.status == 'open' and self._state.pending is None,
                'authority not open; unresolved leases cannot be taken over')
        require(source_id in ah.SOURCES and source_id not in self._state.consumed,
                'source controller revision already consumed or unknown')
        require(self._state.source_states[source_id]['prefix_hash'] == expected_prefix_hash,
                'stale controller prefix anchor')
        require(self._state.event_count + 2 <= MAX_EVENTS and
                len(self._raw) + 2 * MAX_EVENT_BYTES <= MAX_JOURNAL_BYTES,
                'authority journal cannot retain a reservation and resolution')
        request = _request(self.prepared, self.policy, source_id)
        _issuable(request, self.policy)
        require(expected_prefix_hash == request['initial_prefix_hash'],
                'controller cannot be reset to issue another session')
        lease = _lease(self.policy, request, self._state.serial, expected_head)
        proposed = add(self._state.reserved, _envelope(self.policy['session_attempts']).limits)
        if not Policy.from_json(self.policy['budget']).fits(proposed):
            self._append({'kind': 'deny', 'lease': lease})
            raise ResourceExhausted('authority denied the complete reference envelope before evaluation')
        self._append({'kind': 'reserve', 'lease': lease, 'reserved_after': list(proposed)})
        self._execution_started = False
        return _snapshot(lease)

    def complete(self, lease, result, *, expected_head):
        self._current(expected_head)
        require(self._state.status == 'pending' and self._state.pending is not None,
                'no issued authority lease awaiting completion')
        require(not self._resumed_pending, 'reopened pending lease cannot be taken over')
        lease, result = _snapshot(lease), _snapshot(result)
        _same(lease, self._state.pending, 'completion has no exact issued pending lease')
        source_id = lease['source_permit']['source_id']
        session = {'source_id': source_id, 'lease': lease,
            'request': _request(self.prepared, self.policy, source_id),
            'grant': lease['reference_grant'], 'result': result}
        body = _completed(self.prepared, self.policy, lease, session, verify_result=True)
        prior = self._session_images
        self._session_images = (*prior, canonical(session))
        try:
            self._append(body)
        except BaseException:
            self._session_images = prior; raise
        return _snapshot(session)

    def execute(self, lease, *, expected_head, journal_path=None):
        """Evaluate only an already persisted exact current lease."""
        self._current(expected_head)
        require(self._state.status == 'pending', 'no pending authority lease for evaluator')
        require(not self._resumed_pending and not self._execution_started,
                'pending evaluator cannot be restarted or taken over')
        lease = _snapshot(lease); _same(lease, self._state.pending, 'unissued evaluator lease')
        request = _request(self.prepared, self.policy, lease['source_permit']['source_id'])
        self._execution_started = True
        result = ah.inspect_session(self.prepared.successor_interface(), request, lease['reference_grant'],
            expected_source_sha256=request['source_sha256'], expected_request_sha256=digest(request),
            expected_authorization_sha256=lease['reference_grant_sha256'], journal_path=journal_path)
        return self.complete(lease, result, expected_head=expected_head)

    def fail(self, *, expected_head, interrupted=False):
        self._current(expected_head); require(type(interrupted) is bool, 'Boolean interruption flag required')
        require(self._state.status == 'pending' and self._state.pending is not None,
                'no pending authority lease to fail')
        self._append({'kind': 'failed', 'lease_hash': self._state.pending['lease_hash'],
                      'reason': 'interrupted' if interrupted else 'evaluation_or_verification_failed'})

    def stop(self, *, expected_head):
        self._current(expected_head); self._append({'kind': 'stop'})

    def close(self):
        if self._file is not None:
            self._file.close(); self._file = None
        if self._lock is not None:
            self._lock.close(); self._lock = None
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


def case_specs():
    return (
        {'name': 'shared_two_sources', 'total_attempts': 64, 'session_attempts': 32, 'credits': 32,
         'sources': ['af_before', 'af_after'], 'finish': 'stop', 'reopen_after_first': True},
        {'name': 'aggregate_denial', 'total_attempts': 32, 'session_attempts': 32, 'credits': 32,
         'sources': ['af_before', 'af_after'], 'finish': 'deny', 'reopen_after_first': False},
        {'name': 'reference_stop', 'total_attempts': 3, 'session_attempts': 3, 'credits': 32,
         'sources': ['af_after'], 'finish': 'stop', 'reopen_after_first': False},
        {'name': 'credit_stop', 'total_attempts': 32, 'session_attempts': 32, 'credits': 4,
         'sources': ['af_after'], 'finish': 'stop', 'reopen_after_first': False},
        {'name': 'interrupted_reservation', 'total_attempts': 32, 'session_attempts': 32, 'credits': 32,
         'sources': ['af_before'], 'finish': 'pending', 'reopen_after_first': False},
    )


def _derive(prepared, identity, journal_directory=None):
    _prepared(prepared); identity = _identity(identity)
    cases = []; images = {}
    for spec in case_specs():
        name = spec['name']; filename = name + '-authority.jsonl'
        policy = make_authority_policy(prepared, identity, authority_id='phase17ai.reference.' + name,
            total_attempts=spec['total_attempts'], session_attempts=spec['session_attempts'],
            candidate_credits=spec['credits'])
        path = None if journal_directory is None else journal_directory / filename
        authority = ControllerAuthority(path, prepared, identity,
            expected_policy=policy, expected_policy_sha256=digest(policy))
        initial_head = authority.state.head; sessions = []; denial = False
        try:
            for index, source_id in enumerate(spec['sources']):
                try:
                    lease = authority.reserve(source_id, expected_head=authority.state.head,
                        expected_prefix_hash=authority.state.source_states[source_id]['prefix_hash'])
                except ResourceExhausted:
                    require(spec['finish'] == 'deny' and index == 1, 'unexpected authority denial')
                    denial = True; break
                if spec['finish'] == 'pending':
                    break
                work_name = name + '-' + source_id + '-operations.jsonl'
                work_path = None if journal_directory is None else journal_directory / work_name
                session = authority.execute(lease, expected_head=authority.state.head, journal_path=work_path)
                sessions.append(session)
                work_raw = bytes.fromhex(session['result']['resource']['journal_hex'])
                if work_path is not None:
                    require(work_path.read_bytes() == work_raw, 'original operation journal changed')
                images[work_name] = {'hex': work_raw.hex(), 'sha256': sha(work_raw)}
                if spec['reopen_after_first'] and index == 0:
                    raw, head = authority.raw, authority.state.head
                    authority.close()
                    authority = ControllerAuthority(path, prepared, identity, expected_policy=policy,
                        expected_policy_sha256=digest(policy), expected_head=head,
                        completed_sessions=sessions, retained_raw=raw if path is None else None)
            if spec['finish'] == 'stop':
                authority.stop(expected_head=authority.state.head)
            require(spec['finish'] != 'deny' or denial, 'selected aggregate denial did not occur')
            if spec['finish'] == 'pending':
                raw, head = authority.raw, authority.state.head; authority.close()
                authority = ControllerAuthority(path, prepared, identity, expected_policy=policy,
                    expected_policy_sha256=digest(policy), expected_head=head,
                    retained_raw=raw if path is None else None)
                before = authority.raw
                refused = False
                try:
                    authority.reserve('af_after', expected_head=authority.state.head,
                        expected_prefix_hash=authority.state.source_states['af_after']['prefix_hash'])
                except ValueError:
                    refused = True
                require(refused and authority.raw == before and authority.state.status == 'pending',
                        'pending authority lease was taken over or silently resolved')
            raw = authority.raw; state = authority.state.to_json()
            if path is not None:
                require(path.read_bytes() == raw, 'original authority journal changed')
            images[filename] = {'hex': raw.hex(), 'sha256': sha(raw)}
            checked = replay_authority(raw, prepared, identity, expected_policy=policy,
                expected_policy_sha256=digest(policy), expected_head=state['head'], sessions=sessions)
            _same(checked.to_json(), state, 'saved authority reconstruction differs')
            cases.append({'name': name, 'authority_policy': policy, 'policy_sha256': digest(policy),
                'initial_head': initial_head, 'journal_name': filename,
                'events': [load_json_strict(line) for line in raw.splitlines()],
                'final_state': state, 'sessions': sessions, 'status': state['status'],
                'budget_denied_before_evaluation': denial,
                'pending_takeover_refused': spec['finish'] == 'pending'})
        finally:
            authority.close()
    main, denied, limited, credit, pending = cases
    require([s['result']['examined'] for s in main['sessions']] == [1, 8] and
            [s['result']['status'] for s in main['sessions']] == ['accepted', 'accepted'] and
            main['final_state']['reserved'] == [64, 128, 512, 512] and
            denied['status'] == 'resource_denied' and len(denied['sessions']) == 1 and
            limited['sessions'][0]['result']['status'] == 'resource_stop' and
            limited['sessions'][0]['result']['examined'] == 3 and
            credit['sessions'][0]['result']['status'] == 'budget_stop' and
            credit['sessions'][0]['result']['examined'] == 4 and pending['status'] == 'pending',
            'selected authority cases differ')
    sessions = [s for case in cases for s in case['sessions']]
    return {'authority_identity': identity, 'cases': cases, 'journal_images': images,
        'summary': {'authority_cases': len(cases), 'source_states': 2,
            'completed_reference_sessions': len(sessions), 'issued_reference_leases':
                sum(case['final_state']['serial'] for case in cases),
            'denied_reference_leases': 1, 'retained_interrupted_reservations': 1,
            'reference_candidate_attempts': sum(s['result']['examined'] for s in sessions),
            'metered_reference_operations': sum(s['result']['resource']['operation_count'] for s in sessions),
            'main_reserved_attempts': 64, 'main_actual_attempts': 9,
            'main_reserved_reference_cost': main['final_state']['reserved_cost'],
            'main_actual_reference_cost': sum(s['result']['resource']['charged_cost'] for s in main['sessions']),
            'fixed_catalog_tasks': 282, 'authority_journal_count': len(cases),
            'operation_journal_count': len(sessions), 'source_specific_controller_checkpoints': True,
            'externally_anchored_local_issuance': True, 'external_issuer_authenticated': False,
            'complete_resource_accounting': False, 'fresh_worker_sessions': 0,
            'fresh_live_challenges': 0, 'new_physical_successors': 0,
            'formal_acceptance_required': True}}


def _execution(raw):
    require(type(raw) is bytes and sha(raw) == AH_EXECUTION_SHA, 'exact completed AH execution required')
    record = load_json_strict(raw, require_canonical=False)
    require(record['source_commit'] == AH_SOURCE and record['source_tree'] == AH_TREE and
            record['completed'] is True and record['producer_domain_coverage_checked'] is True and
            record['source_bound_controller_evaluation_checked'] is True and
            record['proof_mode'] == 'real_pinned_lean_completed_stage_lineage' and
            type(record['source_sha256']) is dict and len(record['source_sha256']) == 555,
            'retained AH source or completion differs')
    return record


def validate_packet(packet):
    _exact(packet, {'schema', 'policy', 'base_commit', 'producer_domain_packet', 'retained_execution_hex',
        'retained_sha256', 'inherited_source_sha256', 'authority_identity', 'cases', 'journal_images',
        'summary', 'scope', 'claims'}, 'controller authority packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'controller authority packet identity differs')
    _same(packet['scope'], SCOPE, 'controller authority scope differs')
    _same(packet['claims'], {key: False for key in FALSE_CLAIMS}, 'controller authority claim escalation')
    _same(packet['retained_sha256'], RETAINED_PINS, 'retained AH pins differ')
    raw = canonical(packet['producer_domain_packet'])
    require(sha(raw) == AH_PACKET_SHA, 'retained AH packet differs')
    prepared = ah.PreparedProducerDomain(raw)
    _exact(packet['retained_execution_hex'], {AH_ROOT + '/execution.json'}, 'retained AH execution')
    execution = _execution(bytes.fromhex(packet['retained_execution_hex'][AH_ROOT + '/execution.json']))
    _same(packet['inherited_source_sha256'], execution['source_sha256'], 'inherited AH source bindings differ')
    identity = _identity(packet['authority_identity'])
    for key, wanted in _derive(prepared, identity).items():
        _same(packet[key], wanted, 'authority derivation differs: ' + key)
    return prepared


@dataclass(frozen=True, slots=True)
class PreparedControllerAuthority:
    packet_bytes: bytes
    _producer: ah.PreparedProducerDomain = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable controller-authority packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical controller-authority packet required')
        object.__setattr__(self, '_producer', validate_packet(packet))

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)

    def producer_domain(self):
        return self._producer

    def second_step(self):
        return self._producer.second_step()

    def finite(self):
        return self._producer.finite()


def authority_journal_images(packet):
    images = packet['journal_images']; require(type(images) is dict, 'authority journal inventory required')
    result = {}
    for name, item in images.items():
        require(type(name) is str and name.endswith('.jsonl') and
                all(c.isascii() and (c.isalnum() or c in '-_.') for c in name) and
                '/' not in name and '\\' not in name, 'portable flat journal filename required')
        _exact(item, {'hex', 'sha256'}, 'journal image')
        require(type(item['hex']) is str and len(item['hex']) <= 2 * MAX_JOURNAL_BYTES,
                'bounded authority journal image required')
        raw = bytes.fromhex(item['hex'])
        require(raw.hex() == item['hex'] and sha(raw) == item['sha256'], 'authority journal image hash differs')
        result[name] = raw
    return result


def _retained(root):
    result = {}
    for name, wanted in RETAINED_PINS.items():
        path = root / name; _no_links(path)
        require(path.is_file(), 'retained AH input missing')
        raw = path.read_bytes(); require(sha(raw) == wanted, 'retained AH input changed: ' + name)
        result[name] = raw
    return result


def prepare_controller_authority(root: Path, packages: Path, *, persist_authority_journals=True):
    require(type(persist_authority_journals) is bool, 'exact authority persistence Boolean required')
    root, packages = Path(root), Path(packages); _no_links(packages)
    require(not packages.exists() and packages.resolve() != root.resolve() and
            root.resolve() not in packages.resolve().parents, 'new external AI package workspace required')
    retained = _retained(root); execution = _execution(retained[AH_ROOT + '/execution.json'])
    for name, wanted in execution['source_sha256'].items():
        path = root / name; _no_links(path)
        require(path.is_file() and sha(path.read_bytes()) == wanted, 'inherited AH source changed: ' + name)
    identity = authority_identity(root); _same(identity, authority_identity(), 'runtime authority root differs')
    inherited = ah.prepare_producer_domain(root, packages / 'inherited', persist_reference_journals=False)
    require(inherited.packet_bytes == retained[AH_ROOT + '/packet.json'],
            'fresh AH source reconstruction differs from completed baseline')
    journals = packages / 'authority-sessions' if persist_authority_journals else None
    if journals is not None:
        journals.mkdir()
    derived = _derive(inherited, identity, journals)
    prepared = PreparedControllerAuthority(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'producer_domain_packet': inherited.packet, 'retained_execution_hex': {
            AH_ROOT + '/execution.json': retained[AH_ROOT + '/execution.json'].hex()},
        'retained_sha256': dict(RETAINED_PINS), 'inherited_source_sha256': execution['source_sha256'],
        **derived, 'scope': dict(SCOPE), 'claims': {key: False for key in FALSE_CLAIMS}}))
    require(retained == _retained(root) and identity == authority_identity(root),
            'retained authority inputs changed during preparation')
    if journals is not None:
        for name, raw in authority_journal_images(prepared.packet).items():
            require((journals / name).read_bytes() == raw, 'original AI journal changed during preparation')
    return prepared


def verify_packet_bytes(raw, recomputed, *, expected_sha256):
    _hash(expected_sha256, 'external authority packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and
            type(recomputed) is PreparedControllerAuthority and raw == recomputed.packet_bytes,
            'authority packet differs from anchored fresh reconstruction')
    PreparedControllerAuthority(raw)


def summary(prepared):
    require(type(prepared) is PreparedControllerAuthority, 'prepared controller authority required')
    return prepared.packet['summary']
