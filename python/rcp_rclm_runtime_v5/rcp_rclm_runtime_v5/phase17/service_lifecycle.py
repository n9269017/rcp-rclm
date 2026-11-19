"""AO prepaid service lifetimes with a single retained reference budget owner.

The fixed six dimensions are operational counts/byte allowances, not a common
physical cost unit. A whole lifetime is permanently reserved before its first
process-launch attempt. Launch consumption is durable and once-only. Reopening
an unresolved lifetime refuses: a caller cannot turn a crash into fresh credit
or retry its old lease. Finite request/byte counters are charged before parsing
or forwarding by the trusted supervisor; the resident independently enforces
its prepaid caps. A receipt hash is a binding to separately checked evidence,
not a physical meter attestation.

The provider must protect the commission, ledger, lock, runtime and retained
current cursor. Atomic file replacement, OS synchronization/locking and one
authoritative copy remain assumptions. Copying this entire trusted root can
copy its allowance. Neither the journal nor its verifier establishes global
clone exclusion, physical currentness, independent commissioning, complete
resource accounting or promotion permission.
"""
from __future__ import annotations

import os
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import controller_durable_authority as ak
from . import authority_transport as am
from .resource_ledger import (ResourceError, ResourceExhausted, canonical, digest,
                              exact, nat, require, sha, _no_links)

SCHEMA = 'phase17ao.service-lifecycle-evidence.v1'
COMMISSION_SCHEMA = 'phase17ao.service-lifecycle-commission.v1'
GRANT_SCHEMA = 'phase17ao.service-lifecycle-grant.v1'
EVENT_SCHEMA = 'phase17ao.service-lifecycle-event.v1'
DIMENSIONS = ('service_lifetimes', 'process_launch_attempts',
              'frontend_input_attempts', 'request_bytes', 'response_bytes',
              'authority_tls_connections')
BINDINGS = {'campaign_commission_sha256', 'runtime_sha256',
            'principal_binding_sha256', 'currentness_anchor_sha256'}
MAX_EVENTS = 2048
MAX_BYTES = 32 * 1024 * 1024
ZERO = [0] * len(DIMENSIONS)
DOMAIN = b'RCPRCLM-PHASE17AO-SERVICE-LIFETIME-V1\0'
SCOPE = {
    'accounting': 'nonrefundable operational lifetime allowances; no physical cost conversion',
    'persistence': 'atomic canonical-image replacement and exact readback under one lifetime lock',
    'exclusivity': 'one cooperating owner of the retained root; copied roots can duplicate authority',
    'independently_protected_deployment_established': False,
    'physical_currentness_established': False,
    'global_clone_exclusion_established': False,
    'complete_resource_accounting': False,
    'promotion_authorized': False,
}


def _copy(value):
    return load_json_strict(canonical(value), require_canonical=True)


def _same(left, right, message):
    require(canonical(left) == canonical(right), message)


def _identifier(value):
    require(type(value) is str and 0 < len(value) <= 128 and
            all(32 < ord(ch) < 127 for ch in value), 'bounded printable operation identity required')
    return value


def vector(value):
    require(type(value) in (list, tuple) and len(value) == len(DIMENSIONS),
            'exact six operational dimensions required')
    return [nat(item) for item in value]


def add(left, right):
    return [nat(a + b) for a, b in zip(vector(left), vector(right), strict=True)]


def fits(value, bound):
    return all(a <= b for a, b in zip(vector(value), vector(bound), strict=True))


def commission_digest(value):
    return sha(canonical(value))


def make_commission(*, bindings, lifetime_envelope, total_budget, commissioning_nonce):
    exact(bindings, BINDINGS)
    for value in bindings.values():
        digest(value)
    digest(commissioning_nonce)
    envelope, budget = vector(lifetime_envelope), vector(total_budget)
    require(envelope[0] == 1 and all(item > 0 for item in envelope[1:]),
            'one lifetime and finite positive operational allowances required')
    return {'schema': COMMISSION_SCHEMA, 'dimensions': list(DIMENSIONS),
            'bindings': _copy(bindings), 'lifetime_envelope': envelope,
            'total_budget': budget, 'commissioning_nonce': commissioning_nonce,
            'scope': _copy(SCOPE)}


def validate_commission(value, *, expected_commission_sha256):
    digest(expected_commission_sha256)
    exact(value, {'schema', 'dimensions', 'bindings', 'lifetime_envelope',
                  'total_budget', 'commissioning_nonce', 'scope'})
    require(commission_digest(value) == expected_commission_sha256,
            'independently retained lifecycle commission pin differs')
    wanted = make_commission(bindings=value['bindings'],
        lifetime_envelope=value['lifetime_envelope'], total_budget=value['total_budget'],
        commissioning_nonce=value['commissioning_nonce'])
    _same(value, wanted, 'lifecycle commission policy, dimensions or scope differs')
    return wanted


def validate_cursor(value):
    exact(value, {'commission_sha256', 'epoch', 'serial', 'head'})
    digest(value['commission_sha256']); digest(value['head'])
    require(nat(value['epoch']) <= MAX_EVENTS and nat(value['serial']) < MAX_EVENTS,
            'lifecycle cursor exceeds finite event profile')
    return _copy(value)


def _cursor(pin, event):
    return {'commission_sha256': pin, 'epoch': event['epoch'],
            'serial': event['serial'], 'head': event['hash']}


def _initial():
    return {'epoch': 0, 'owner_nonce': None, 'owner_nonces': [],
            'reserved': list(ZERO), 'used_lifetime_ids': [], 'pending': None, 'closed': []}


def make_grant(commission, state, cursor, lifetime_id):
    """reservation_cursor is the exact BEFORE-reservation cursor being consumed."""
    _identifier(lifetime_id); validate_cursor(cursor)
    digest(state['owner_nonce'])
    core = {'schema': GRANT_SCHEMA, 'commission_sha256': commission_digest(commission),
            'lifetime_id': lifetime_id, 'owner_nonce': state['owner_nonce'],
            'epoch': state['epoch'], 'envelope': vector(commission['lifetime_envelope']),
            'reservation_cursor': _copy(cursor)}
    return {**core, 'grant_sha256': sha(DOMAIN + b'GRANT\0' + canonical(core))}


def validate_grant(value):
    exact(value, {'schema', 'commission_sha256', 'lifetime_id', 'owner_nonce', 'epoch',
                  'envelope', 'reservation_cursor', 'grant_sha256'})
    require(value['schema'] == GRANT_SCHEMA, 'lifecycle grant schema differs')
    digest(value['commission_sha256']); digest(value['owner_nonce']); digest(value['grant_sha256'])
    _identifier(value['lifetime_id']); vector(value['envelope']); nat(value['epoch'])
    cursor = validate_cursor(value['reservation_cursor'])
    require(cursor['commission_sha256'] == value['commission_sha256'] and
            cursor['epoch'] == value['epoch'], 'lifecycle grant predecessor binding differs')
    core = {key: item for key, item in value.items() if key != 'grant_sha256'}
    require(value['grant_sha256'] == sha(DOMAIN + b'GRANT\0' + canonical(core)),
            'lifecycle grant identity differs')
    return _copy(value)


def _active(state, grant, *, phase=None):
    grant = validate_grant(grant)
    pending = state['pending']
    require(pending is not None, 'no retained lifecycle reservation')
    _same(pending['grant'], grant, 'stale or substituted lifecycle grant')
    require(grant['epoch'] == state['epoch'] and grant['owner_nonce'] == state['owner_nonce'],
            'lifecycle lease belongs to another owner epoch')
    if phase is not None:
        require(pending['phase'] == phase, 'lifecycle launch phase differs or was already consumed')
    return pending


def _transition(commission, before, cursor, kind, payload):
    state = _copy(before)
    if kind == 'provision':
        exact(payload, {'commission_sha256'})
        require(cursor is None and state == _initial() and
                payload['commission_sha256'] == commission_digest(commission),
                'lifecycle genesis differs')
    elif kind == 'open':
        exact(payload, {'owner_nonce'}); digest(payload['owner_nonce'])
        require(state['pending'] is None, 'unresolved lifetime forbids automatic reopen or retry')
        require(payload['owner_nonce'] not in state['owner_nonces'], 'lifecycle owner nonce replay')
        state['epoch'] += 1
        require(state['epoch'] <= MAX_EVENTS, 'lifecycle epoch capacity exhausted')
        state['owner_nonce'] = payload['owner_nonce']
        state['owner_nonces'].append(payload['owner_nonce'])
    elif kind in ('reserve', 'deny'):
        exact(payload, {'grant'})
        grant = validate_grant(payload['grant'])
        require(state['owner_nonce'] is not None and state['pending'] is None,
                'lifecycle owner missing or reservation unresolved')
        require(grant['lifetime_id'] not in state['used_lifetime_ids'], 'lifetime identity already consumed')
        _same(grant, make_grant(commission, state, cursor, grant['lifetime_id']),
              'reservation is not the exact commissioned grant')
        proposed = add(state['reserved'], commission['lifetime_envelope'])
        allowed = fits(proposed, commission['total_budget'])
        require(allowed == (kind == 'reserve'), 'false lifecycle budget decision')
        if allowed:
            state['reserved'] = proposed
            state['used_lifetime_ids'].append(grant['lifetime_id'])
            state['pending'] = {'grant': grant, 'phase': 'reserved', 'used': list(ZERO),
                                'consumed_event_ids': []}
    elif kind == 'launch':
        exact(payload, {'grant'})
        pending = _active(state, payload['grant'], phase='reserved')
        pending['phase'] = 'launched'
        pending['used'] = [1, 1, 0, 0, 0, 0]
        require(fits(pending['used'], pending['grant']['envelope']), 'launch exceeds lifetime envelope')
    elif kind == 'charge':
        exact(payload, {'grant', 'delta', 'event_id', 'evidence_sha256'})
        pending = _active(state, payload['grant'], phase='launched')
        event_id = _identifier(payload['event_id'])
        require(event_id not in pending['consumed_event_ids'], 'lifecycle usage event replay')
        delta = vector(payload['delta'])
        require(delta[0] == 0 and any(delta), 'ordinary charge cannot mint or repeat lifetime launch')
        if payload['evidence_sha256'] is not None:
            digest(payload['evidence_sha256'])
        used = add(pending['used'], delta)
        require(fits(used, pending['grant']['envelope']), 'service usage exceeds prepaid lifetime allowance')
        pending['used'] = used
        pending['consumed_event_ids'].append(event_id)
    elif kind == 'finish':
        exact(payload, {'grant', 'outcome', 'evidence_sha256'})
        pending = _active(state, payload['grant'], phase='launched')
        require(payload['outcome'] in ('completed', 'failed'), 'unsupported lifecycle terminal outcome')
        digest(payload['evidence_sha256'])
        state['closed'].append({'grant': _copy(pending['grant']), 'outcome': payload['outcome'],
            'used': list(pending['used']), 'consumed_event_ids': list(pending['consumed_event_ids']),
            'evidence_sha256': payload['evidence_sha256']})
        state['pending'] = None
    else:
        raise ResourceError('unknown service lifecycle transition')
    require(fits(state['reserved'], commission['total_budget']), 'cumulative lifecycle budget exceeded')
    return state


def _event(pin, before_cursor, kind, payload, after):
    core = {'schema': EVENT_SCHEMA, 'commission_sha256': pin,
            'serial': 0 if before_cursor is None else before_cursor['serial'] + 1,
            'epoch': after['epoch'], 'kind': kind,
            'before_cursor': _copy(before_cursor), 'payload': _copy(payload), 'after': _copy(after)}
    return {**core, 'hash': sha(DOMAIN + b'EVENT\0' + canonical(core))}


def verify_evidence(evidence, *, expected_commission_sha256, expected_cursor=None):
    """Pure replay of retained images; never invokes a process or claims currentness."""
    exact(evidence, {'schema', 'commission', 'commission_sha256', 'events', 'final_cursor', 'scope'})
    require(evidence['schema'] == SCHEMA and evidence['commission_sha256'] == expected_commission_sha256,
            'lifecycle evidence schema or external commission pin differs')
    _same(evidence['scope'], SCOPE, 'lifecycle evidence broadens reference scope')
    commission = validate_commission(evidence['commission'],
        expected_commission_sha256=expected_commission_sha256)
    events = evidence['events']
    require(type(events) is list and 0 < len(events) <= MAX_EVENTS,
            'bounded complete lifecycle event history required')
    require(len(canonical(evidence)) <= MAX_BYTES, 'lifecycle evidence exceeds finite byte profile')
    state, cursor = _initial(), None
    for serial, event in enumerate(events):
        exact(event, {'schema', 'commission_sha256', 'serial', 'epoch', 'kind',
                      'before_cursor', 'payload', 'after', 'hash'})
        require((serial == 0) == (event['kind'] == 'provision'), 'lifecycle genesis position differs')
        after = _transition(commission, state, cursor, event['kind'], event['payload'])
        wanted = _event(expected_commission_sha256, cursor, event['kind'], event['payload'], after)
        _same(event, wanted, 'lifecycle record is not the exact append-only transition')
        state, cursor = after, _cursor(expected_commission_sha256, event)
    _same(evidence['final_cursor'], cursor, 'lifecycle final cursor differs')
    if expected_cursor is not None:
        validate_cursor(expected_cursor)
        _same(cursor, expected_cursor, 'independently retained lifecycle head differs')
    return {'commission': commission, 'cursor': cursor, 'state': state,
            'summary': {'epochs': state['epoch'], 'events': len(events),
                        'reserved': list(state['reserved']),
                        'lifetimes_reserved': len(state['used_lifetime_ids']),
                        'lifetimes_closed': len(state['closed']),
                        'budget_denials': sum(event['kind'] == 'deny' for event in events),
                        'pending_retained': state['pending'] is not None,
                        'scope': _copy(SCOPE)}}


def _read(path):
    path = Path(path).absolute(); _no_links(path)
    require(path.is_file() and 0 < path.stat().st_size <= MAX_BYTES,
            'provisioned bounded lifecycle ledger required')
    raw = path.read_bytes()
    return raw, load_json_strict(raw, require_canonical=True)


def read_evidence(path, *, expected_commission_sha256=None, expected_cursor=None):
    """Read retained evidence even if an interrupted reservation forbids reopening."""
    _, evidence = _read(path)
    pin = evidence['commission_sha256'] if expected_commission_sha256 is None else expected_commission_sha256
    verify_evidence(evidence, expected_commission_sha256=pin, expected_cursor=expected_cursor)
    return evidence


def provision(path, commission, *, expected_commission_sha256):
    commission = validate_commission(commission, expected_commission_sha256=expected_commission_sha256)
    path = Path(path).absolute(); _no_links(path)
    lock_path = path.with_name(path.name + '.lock')
    require(path.parent.is_dir() and not path.exists() and not lock_path.exists(),
            'new lifecycle ledger and existing protected parent required')
    after = _transition(commission, _initial(), None, 'provision',
                        {'commission_sha256': expected_commission_sha256})
    event = _event(expected_commission_sha256, None, 'provision',
                   {'commission_sha256': expected_commission_sha256}, after)
    evidence = {'schema': SCHEMA, 'commission': commission,
        'commission_sha256': expected_commission_sha256, 'events': [event],
        'final_cursor': _cursor(expected_commission_sha256, event), 'scope': _copy(SCOPE)}
    verify_evidence(evidence, expected_commission_sha256=expected_commission_sha256)
    ak._write_new(lock_path, b'L'); os.chmod(lock_path, 0o600)
    ak._write_new(path, canonical(evidence)); os.chmod(path, 0o600)
    ak._directory_sync(path.parent)
    return read_evidence(path, expected_commission_sha256=expected_commission_sha256)


class ServiceLifecycleLedger:
    """Trusted supervisor's lifetime-held budget owner; no child is launched here.

    The entire finite envelope and consume_launch must be committed before the
    first Popen. The supervisor records planned launch/input attempts before
    forwarding them. Quantities known only from original native observations
    (including response bytes, TLS connections and nested worker launches) may
    be reconciled afterwards within that already prepaid envelope; the resident
    must enforce its commissioned limits before issuing or emitting work. Such
    reconciliation never refunds allowance. Finishing requires the supervisor
    to have checked its original terminal evidence; this module binds its digest
    but cannot attest the external process itself. close only releases ownership
    and never synthesizes terminal evidence.
    """
    def __init__(self, path, *, expected_commission_sha256, owner_nonce, expected_cursor=None):
        self.path = Path(path).absolute(); _no_links(self.path)
        self.pin = digest(expected_commission_sha256)
        self._lock = None; self._closed = self._poisoned = False
        self._raw = self._evidence = self._checked = None
        try:
            lock_path = self.path.with_name(self.path.name + '.lock')
            require(self.path.is_file() and lock_path.is_file(),
                    'provisioned lifecycle ledger and owner lock required')
            self._lock = ak._LifetimeLock(lock_path)
            self._raw, self._evidence = _read(self.path)
            self._checked = verify_evidence(self._evidence,
                expected_commission_sha256=self.pin, expected_cursor=expected_cursor)
            self._commit('open', {'owner_nonce': digest(owner_nonce)}, expected_cursor=self._checked['cursor'])
        except BaseException:
            self.close()
            raise

    def _check(self):
        require(not self._closed and not self._poisoned and self._lock is not None,
                'lifecycle owner closed or poisoned')
        self._lock.check()
        raw, _ = _read(self.path)
        require(raw == self._raw, 'lifecycle ledger changed outside its owner')

    def _commit(self, kind, payload, *, expected_cursor):
        self._check(); validate_cursor(expected_cursor)
        _same(expected_cursor, self._checked['cursor'], 'stale lifecycle compare-and-publish cursor')
        require(len(self._evidence['events']) < MAX_EVENTS, 'lifecycle event capacity exhausted')
        after = _transition(self._checked['commission'], self._checked['state'],
                            self._checked['cursor'], kind, payload)
        event = _event(self.pin, self._checked['cursor'], kind, payload, after)
        wanted = _copy(self._evidence)
        wanted['events'].append(event)
        wanted['final_cursor'] = _cursor(self.pin, event)
        checked = verify_evidence(wanted, expected_commission_sha256=self.pin)
        raw = canonical(wanted)
        try:
            self._check()
            am._replace(self.path, wanted)
            actual, _ = _read(self.path)
            require(actual == raw, 'lifecycle committed readback differs')
            self._lock.check()
            self._raw, self._evidence, self._checked = raw, wanted, checked
        except BaseException:
            self._poisoned = True
            raise
        return _copy(event)

    @property
    def cursor(self):
        self._check(); return _copy(self._checked['cursor'])

    @property
    def state(self):
        self._check(); return _copy(self._checked['state'])

    @property
    def commission(self):
        self._check(); return _copy(self._checked['commission'])

    def export_evidence(self):
        self._check()
        verify_evidence(self._evidence, expected_commission_sha256=self.pin)
        return _copy(self._evidence)

    def reserve(self, lifetime_id, *, expected_cursor):
        self._check(); validate_cursor(expected_cursor)
        _same(expected_cursor, self._checked['cursor'], 'stale lifecycle reservation cursor')
        grant = make_grant(self._checked['commission'], self._checked['state'],
                           self._checked['cursor'], lifetime_id)
        proposed = add(self._checked['state']['reserved'], self._checked['commission']['lifetime_envelope'])
        allowed = fits(proposed, self._checked['commission']['total_budget'])
        self._commit('reserve' if allowed else 'deny', {'grant': grant}, expected_cursor=expected_cursor)
        if not allowed:
            raise ResourceExhausted('prepaid service lifetime budget exhausted before process launch')
        return grant

    def consume_launch(self, grant, *, expected_cursor):
        return self._commit('launch', {'grant': _copy(grant)}, expected_cursor=expected_cursor)

    def charge(self, grant, delta, *, event_id, expected_cursor, evidence_sha256=None):
        return self._commit('charge', {'grant': _copy(grant), 'delta': vector(delta),
            'event_id': event_id, 'evidence_sha256': evidence_sha256}, expected_cursor=expected_cursor)

    def charge_input(self, grant, raw, *, event_id, expected_cursor):
        """Commit the raw attempt and byte count BEFORE any protocol parser runs."""
        require(type(raw) is bytes, 'original raw frontend bytes required')
        return self.charge(grant, [0, 0, 1, len(raw), 0, 0], event_id=event_id,
                           expected_cursor=expected_cursor, evidence_sha256=sha(raw))

    def finish(self, grant, *, expected_cursor, evidence_sha256, outcome='completed'):
        return self._commit('finish', {'grant': _copy(grant), 'outcome': outcome,
            'evidence_sha256': evidence_sha256}, expected_cursor=expected_cursor)

    def close(self):
        if self._lock is not None:
            self._lock.close(); self._lock = None
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
