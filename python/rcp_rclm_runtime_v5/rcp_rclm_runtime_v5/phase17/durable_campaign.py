"""Phase17AL: atomic, nonrefundable authorization of fixed live campaign work.

This is a local reference service, conditional on a protected, current, unique
root and trusted service code. It does not deploy that protection. The service
owns its fixed worker launch; a caller cannot supply a grant, evaluator, path,
next-state verdict, refund or retry. Independently running the older worker is
outside this admitted execution path and is not prevented by this protocol.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import stat

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as object_hash
from . import campaign_budget as budget
from . import controller_durable_authority as ak
from .campaign_transaction import context_for, check_controller, audit_campaign, FALSE_CLAIMS as OLD_FALSE_CLAIMS, UNMEASURED
from .challenge_protocol import PROTOCOL, digest, realize_candidate, reference_grammar
from .controller import Action, checkpoint, decide, record_evaluation
from .controller_authority import FALSE_CLAIMS
from .metered_worker import WORKER_PROTOCOL, verify_metered_transcript
from .objectives import OBJECTIVE_POLICY, select_bootstrap_objective, freeze_bootstrap_objective
from .phase16_adapter import bind_phase16_search
from .resource_ledger import (Policy, PROFILE, ResourceError, ResourceExhausted, ZERO,
    add, canonical, cost, exact, nat, require, sha, digest as hash_value, _no_links)

BASE = '961beaaeeb1fe4461aa27fbec0af08469bd5c2aa'
SCHEMA = 'phase17al.durable-campaign-evidence.v1'
PROVISION_SCHEMA = 'phase17al.durable-campaign-provision.v1'
EVENT_SCHEMA = 'phase17al.durable-campaign-event.v1'
PERMIT_SCHEMA = 'phase17al.durable-campaign-permit.v1'
DOMAIN = b'RCPRCLM-PHASE17AL-DURABLE-CAMPAIGN-V1\0'
SOURCE_ROOT = Path(__file__).resolve().parents[4]
MAX_BYTES = 128 * 1024 * 1024
MAX_EVENTS = 128
SESSION_FILES = frozenset({'grant.json', 'objective.json', 'objective_freeze.json',
    'public_challenge.json', 'sealed_transcript.json', 'worker-accounting.json',
    'controller_checkpoint.json', 'session.json'})
NATIVE_FILES = frozenset({'start.json', 'child.json', 'stdin.jsonl', 'stdout.jsonl',
                         'stderr.txt', 'result.json'})
CURSOR_FIELDS = {'root_provision_sha256', 'epoch', 'serial', 'root_head',
                 'journal_sha256', 'snapshot_sha256'}
SCOPE = {
    'deployment': 'local_reference_only',
    'authority': 'independently pinned provision and one trusted atomic campaign root',
    'worker': 'service-owned fixed Phase17O evaluator; one committed reservation and launch consumption per admitted worker',
    'authentication': 'no new public-key or hostile-client response authentication; protected service transport remains external',
    'currentness': 'one trusted SQLite root with a cooperative lifetime lock; whole-root rollback and cloning remain external',
    'storage': 'SQLite DELETE rollback journal with synchronous=EXTRA; correctness and physical persistence remain backend/OS assumptions',
    'source': 'fixed historical Phase16 predecessor; no promoted successor lineage',
    'accounting': 'nonrefundable Phase17O bounded-vector reference tariff only',
    'external_issuer_authenticated': False,
    'independently_protected_deployment_established': False,
    'global_authority_exclusivity_established': False,
    'complete_resource_accounting': False,
    'physical_execution_attested': False,
    'promotion_authorized': False,
    'unmeasured': list(UNMEASURED),
}


def _same(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def _copy(value):
    return load_json_strict(canonical(value))


def _hex(value, label):
    require(type(value) is str and len(value) % 2 == 0 and len(value) <= MAX_BYTES * 2,
            label + ' requires bounded hex bytes')
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ResourceError(label + ' has invalid hex bytes') from exc
    require(raw.hex() == value, label + ' requires canonical lower-case hex')
    return raw


def implementation_identity(source_root=SOURCE_ROOT):
    """Pin project source bytes; interpreter/stdlib/OS remain trusted premises."""
    root = Path(source_root).absolute()
    paths = []
    for version in (2, 3, 4, 5):
        package = root / 'python' / ('rcp_rclm_runtime_v' + str(version))
        package = package / ('rcp_rclm_runtime' if version == 2 else 'rcp_rclm_runtime_v' + str(version))
        require(package.is_dir(), 'campaign runtime source package missing')
        paths.extend(p for p in package.rglob('*.py'))
    paths.extend(root / name for name in ('scripts/phase17_campaign_worker.py',
                                         'scripts/phase17_durable_campaign_service.py'))
    require(0 < len(paths) <= 512, 'campaign source inventory exceeds profile')
    bindings = {}
    for path in sorted(paths):
        _no_links(path)
        require(path.is_file(), 'campaign implementation source missing')
        bindings[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    return {'code_sha256': bindings, 'implementation_sha256': object_hash(bindings)}


def make_provision(source_root, parent, policy, authority_id, nonce):
    require(type(policy) is Policy, 'exact provisioned policy required')
    require(type(authority_id) is str and 0 < len(authority_id) <= 128,
            'bounded campaign authority identity required')
    hash_value(nonce)
    campaign_id = sha(DOMAIN + b'CAMPAIGN\0' + canonical({'authority_id': authority_id, 'nonce': nonce}))
    return {'schema': PROVISION_SCHEMA, 'authority_id': authority_id,
        'provisioning_nonce': nonce, 'context': context_for(parent, campaign_id),
        'policy': policy.to_json(), 'implementation': implementation_identity(source_root),
        'objective_policy': OBJECTIVE_POLICY, 'worker_protocol': WORKER_PROTOCOL,
        'evaluator_protocol': PROTOCOL, 'accounting_profile': PROFILE, 'scope': _copy(SCOPE)}


def _provision(value, parent, source_root, expected_pin):
    hash_value(expected_pin)
    value = _copy(value)
    exact(value, {'schema', 'authority_id', 'provisioning_nonce', 'context', 'policy',
        'implementation', 'objective_policy', 'worker_protocol', 'evaluator_protocol',
        'accounting_profile', 'scope'})
    require(object_hash(value) == expected_pin, 'campaign provision differs from independent pin')
    wanted = make_provision(source_root, parent, Policy.from_json(value['policy']),
                            value['authority_id'], value['provisioning_nonce'])
    _same(value, wanted, 'campaign provision source, parent, policy or scope differs')
    return value


def _cursor(pin, event):
    return {'root_provision_sha256': pin, 'epoch': event['epoch'], 'serial': event['serial'],
            'root_head': event['root_head'], 'journal_sha256': event['journal_sha256'],
            'snapshot_sha256': event['snapshot_sha256']}


def _validate_cursor(value):
    exact(value, CURSOR_FIELDS)
    for key in CURSOR_FIELDS - {'epoch', 'serial'}:
        hash_value(value[key])
    nat(value['epoch']); nat(value['serial'])
    return _copy(value)


def _journal(snapshot, provision):
    raw = _hex(snapshot['journal_hex'], 'campaign journal')
    require(raw.endswith(b'\n'), 'campaign journal must end with newline')
    lines = raw.splitlines()
    require(lines, 'campaign journal missing')
    head = load_json_strict(lines[-1])['hash']
    state = budget.replay(raw, expected_head=head, policy=Policy.from_json(provision['policy']),
                          expected_context=provision['context'])
    return raw, state


def _append_journal(snapshot, provision, body):
    raw, state = _journal(snapshot, provision)
    event = budget.event(body, state.event_count, state.head)
    result = raw + canonical(event) + b'\n'
    budget.replay(result, expected_head=event['hash'], policy=Policy.from_json(provision['policy']),
                  expected_context=provision['context'])
    return result.hex()


def _initial(provision):
    row = budget.event({'kind': 'open', 'schema': budget.SCHEMA,
        'context': provision['context'], 'policy': provision['policy']}, 0, ZERO)
    return {'journal_hex': (canonical(row) + b'\n').hex(), 'pending': None,
            'nonces': [], 'sessions': []}


def _connect(path):
    # AK's constructor supplies missing-file refusal, trusted_schema=OFF,
    # foreign keys, rollback-journal checking and quick_check. AL strengthens
    # synchronization to EXTRA, including directory sync after journal unlink.
    connection = ak._connect(path)
    try:
        connection.execute('PRAGMA synchronous=EXTRA')
        require(connection.execute('PRAGMA synchronous').fetchone()[0] == 3 and
                connection.execute('PRAGMA journal_mode').fetchone()[0] == 'delete',
                'campaign root EXTRA synchronization policy differs')
        return connection
    except BaseException:
        connection.close()
        raise


def _request(value, cursor, snapshot, provision):
    exact(value, {'expected_cursor', 'request_nonce', 'credits'})
    _same(_validate_cursor(value['expected_cursor']), cursor, 'stale or substituted campaign cursor')
    hash_value(value['request_nonce'])
    require(value['request_nonce'] not in snapshot['nonces'], 'campaign request nonce replayed')
    require(nat(value['credits']) <= 32, 'candidate credits exceed fixed grammar')
    raw, state = _journal(snapshot, provision)
    require(state.status == 'open' and snapshot['pending'] is None,
            'campaign has unresolved work or is terminated')
    require(state.event_count + 2 <= budget.MAX_EVENTS and
            len(raw) + 2 * budget.MAX_EVENT_BYTES <= budget.MAX_BYTES,
            'campaign journal capacity exhausted before admission')
    return state


def _permit(parent, provision, cursor, request, state):
    objective = select_bootstrap_objective(parent, turn_index=state.session_count,
                                          public_nonce_hash=request['request_nonce'])
    freeze = freeze_bootstrap_objective(objective, parent, turn_index=state.session_count,
                                       public_nonce_hash=request['request_nonce'])
    grant = budget.make_grant(provision['context'], state.session_count, state.head,
                              freeze['freeze_hash'], request['credits'])
    core = {'schema': PERMIT_SCHEMA, 'root_provision_sha256': cursor['root_provision_sha256'],
        'grant': grant, 'objective': objective.to_json(), 'freeze': freeze,
        'request_nonce': request['request_nonce'], 'reservation_epoch': cursor['epoch'],
        'reservation_cursor': _copy(cursor)}
    return {**core, 'permit_sha256': sha(DOMAIN + b'PERMIT\0' + canonical(core))}


def _session_files(session):
    exact(session, {'files_hex', 'native_sha256', 'permit_sha256', 'launch_cursor', 'owner_epoch'})
    exact(session['files_hex'], set(SESSION_FILES))
    exact(session['native_sha256'], set(NATIVE_FILES))
    for name, digest_value in session['native_sha256'].items():
        require(type(name) is str and name not in ('', '.', '..') and
                '/' not in name and '\\' not in name, 'native binding must name a direct file')
        hash_value(digest_value)
    return {name: _hex(raw, 'session ' + name) for name, raw in session['files_hex'].items()}


def _next_snapshot(previous, provision, parent, cursor, *, kind, epoch, request, session):
    if kind == 'provision':
        require(previous is None and cursor is None and epoch == 0 and request is None and session is None,
                'invalid initial campaign transition')
        return _initial(provision)
    require(previous is not None and cursor is not None, 'campaign predecessor missing')
    exact(previous, {'journal_hex', 'pending', 'nonces', 'sessions'})
    result = _copy(previous)
    if kind == 'reopen':
        require(epoch == cursor['epoch'] + 1 and request is None and session is None,
                'reopen must advance the durable epoch')
        if result['pending'] is not None:
            result['pending']['owner_epoch'] = None
        return result
    require(epoch == cursor['epoch'] and epoch > 0, 'mutation must use the open authority epoch')
    if kind in ('reserve', 'deny'):
        require(session is None, 'reservation cannot supply a completion')
        state = _request(request, cursor, previous, provision)
        permit = _permit(parent, provision, cursor, request, state)
        grant = permit['grant']
        proposed = add(state.reserved, Policy.from_json(grant['envelope']).limits)
        fits = Policy.from_json(provision['policy']).fits(proposed)
        require(fits == (kind == 'reserve'), 'false campaign reservation or denial')
        body = {'kind': kind, 'grant': grant}
        if fits:
            body['reserved_after'] = list(proposed)
            result['pending'] = {'permit': permit, 'stage': 'reserved', 'owner_epoch': epoch}
        result['journal_hex'] = _append_journal(previous, provision, body)
        result['nonces'].append(request['request_nonce'])
        return result
    require(request is None, 'backend transition cannot supply a controller request')
    pending = previous['pending']
    require(type(pending) is dict and pending['owner_epoch'] == epoch,
            'pending campaign work has no current live owner')
    if kind == 'launch':
        require(session is None and pending['stage'] == 'reserved', 'campaign launch already consumed')
        result['pending']['stage'] = 'launch_consumed'
        return result
    require(kind == 'complete' and pending['stage'] == 'launch_consumed',
            'campaign completion requires a consumed current launch')
    files = _session_files(session)
    permit = pending['permit']; grant = permit['grant']
    require(session['owner_epoch'] == epoch and type(session['owner_epoch']) is int and
            session['permit_sha256'] == permit['permit_sha256'], 'completion substitutes live permit owner')
    _same(_validate_cursor(session['launch_cursor']), cursor, 'completion does not bind consumed launch')
    require(files['grant.json'] == canonical(grant) and
            files['objective.json'] == canonical(permit['objective']) and
            files['objective_freeze.json'] == canonical(permit['freeze']),
            'completion substitutes grant or objective authorization')
    accounting = load_json_strict(files['worker-accounting.json'])
    checked = verify_metered_transcript(parent, grant, files['sealed_transcript.json'], accounting)
    require(check_controller(parent, files['sealed_transcript.json']) == files['controller_checkpoint.json'],
            'completion substitutes actual controller checkpoint')
    result['journal_hex'] = _append_journal(previous, provision,
        {'kind': 'complete', 'grant_hash': grant['grant_hash'], **checked})
    result['pending'] = None
    result['sessions'].append(_copy(session))
    raw, state = _journal(result, provision)
    session_map = {}
    for retained in result['sessions']:
        retained_files = _session_files(retained)
        retained_grant = load_json_strict(retained_files['grant.json'])
        require(retained_grant['grant_hash'] not in session_map, 'duplicate completed worker grant')
        session_map[retained_grant['grant_hash']] = retained_files
    audit_campaign(parent, raw, expected_head=state.head, policy=Policy.from_json(provision['policy']),
                   expected_context=provision['context'], sessions=session_map)
    return result


def _event(pin, snapshot, *, previous, kind, epoch, boot_nonce, request, session):
    core = {'schema': EVENT_SCHEMA, 'kind': kind,
        'serial': 0 if previous is None else previous['serial'] + 1,
        'epoch': epoch, 'previous_root_head': ZERO if previous is None else previous['root_head'],
        'root_provision_sha256': pin, 'boot_nonce': boot_nonce,
        'request': _copy(request), 'session_sha256': None if session is None else object_hash(session),
        'journal_sha256': sha(_hex(snapshot['journal_hex'], 'campaign journal')),
        'snapshot_sha256': object_hash(snapshot)}
    return {**core, 'root_head': sha(DOMAIN + b'EVENT\0' + canonical(core))}


def verify_evidence(evidence, parent, *, expected_root_provision_sha256, source_root=SOURCE_ROOT):
    exact(evidence, {'schema', 'provision', 'root_provision_sha256', 'entries', 'final_cursor', 'scope'})
    require(evidence['schema'] == SCHEMA and
            evidence['root_provision_sha256'] == expected_root_provision_sha256,
            'campaign evidence schema or independent pin differs')
    _same(evidence['scope'], SCOPE, 'campaign scope escalation')
    provision = _provision(evidence['provision'], parent, source_root, expected_root_provision_sha256)
    entries = evidence['entries']
    require(type(entries) is list and 0 < len(entries) <= MAX_EVENTS, 'campaign root history capacity')
    previous = cursor = None
    boots = set()
    for index, entry in enumerate(entries):
        exact(entry, {'event', 'snapshot'})
        event, supplied = entry['event'], entry['snapshot']
        exact(event, {'schema', 'kind', 'serial', 'epoch', 'previous_root_head',
            'root_provision_sha256', 'boot_nonce', 'request', 'session_sha256',
            'journal_sha256', 'snapshot_sha256', 'root_head'})
        exact(supplied, {'journal_hex', 'pending', 'nonces', 'sessions'})
        require(type(event['serial']) is int and event['serial'] == index, 'campaign root serial differs')
        nat(event['epoch'])
        kind = event['kind']
        if kind == 'reopen':
            nonce = hash_value(event['boot_nonce'])
            require(nonce not in boots, 'campaign boot nonce replayed')
            boots.add(nonce)
        else:
            require(event['boot_nonce'] is None, 'non-reopen supplied a boot nonce')
        session = supplied['sessions'][-1] if kind == 'complete' and supplied['sessions'] else None
        wanted = _next_snapshot(previous, provision, parent, cursor, kind=kind,
            epoch=event['epoch'], request=event['request'], session=session)
        _same(supplied, wanted, 'campaign snapshot does not follow its exact accepted transition')
        expected_event = _event(expected_root_provision_sha256, wanted, previous=cursor,
            kind=kind, epoch=event['epoch'], boot_nonce=event['boot_nonce'],
            request=event['request'], session=session)
        _same(event, expected_event, 'campaign root hash or image binding differs')
        previous, cursor = wanted, _cursor(expected_root_provision_sha256, event)
    _same(_validate_cursor(evidence['final_cursor']), cursor, 'final campaign cursor differs')
    _, state = _journal(previous, provision)
    return {'cursor': cursor, 'snapshot': previous, 'state': state, 'provision': provision}


def provision_root(root_directory, source_root, parent, policy, *, authority_id, nonce):
    root = Path(root_directory).absolute(); _no_links(root)
    require(not root.exists(), 'campaign provisioning cannot overwrite or initialize an existing root')
    provision = make_provision(source_root, parent, policy, authority_id, nonce)
    pin = object_hash(provision)
    snapshot = _initial(provision)
    event = _event(pin, snapshot, previous=None, kind='provision', epoch=0,
                   boot_nonce=None, request=None, session=None)
    root.mkdir(mode=0o700, parents=True)
    ak._write_new(root / 'authority.lock', b'L')
    ak._write_new(root / 'authority.sqlite3', b'')
    os.chmod(root / 'authority.lock', 0o600); os.chmod(root / 'authority.sqlite3', 0o600)
    connection = _connect(root / 'authority.sqlite3')
    try:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), image BLOB NOT NULL)')
        connection.execute('CREATE TABLE snapshots (serial INTEGER PRIMARY KEY, event BLOB NOT NULL, image BLOB NOT NULL)')
        connection.execute('INSERT INTO metadata VALUES (1,?)', (canonical(provision),))
        connection.execute('INSERT INTO snapshots VALUES (0,?,?)', (canonical(event), canonical(snapshot)))
        connection.commit()
        require(connection.execute('SELECT serial,event,image FROM snapshots').fetchall() ==
                [(0, canonical(event), canonical(snapshot))], 'provisioned campaign commit readback differs')
        ak._directory_sync(root)
        return {'root_provision_sha256': pin, 'cursor': _cursor(pin, event)}
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def _fault(stage):
    """Controlled fault-injection boundary; the runtime supplies no bypass."""


class DurableCampaignAuthority:
    def __init__(self, root_directory, parent, *, expected_root_provision_sha256,
                 source_root=SOURCE_ROOT, boot_nonce):
        self.root_directory = Path(root_directory).absolute(); _no_links(self.root_directory)
        self.source_root = Path(source_root).absolute()
        self.parent = parent
        self.root_provision_sha256 = hash_value(expected_root_provision_sha256)
        hash_value(boot_nonce)
        self._closed = self._poisoned = False
        self._lock = self._connection = None
        self._rows = []
        self._provision_bytes = None
        try:
            require(self.root_directory.is_dir(), 'provisioned campaign root missing')
            self._lock = ak._LifetimeLock(self.root_directory / 'authority.lock')
            db = self.root_directory / 'authority.sqlite3'
            self._database_stat = db.stat()
            self._connection = _connect(db)
            rows = self._connection.execute('SELECT singleton,image FROM metadata').fetchall()
            require(len(rows) == 1 and rows[0][0] == 1 and type(rows[0][1]) is bytes,
                    'exact campaign provision database image required')
            self._provision_bytes = rows[0][1]
            provision = load_json_strict(self._provision_bytes)
            require(canonical(provision) == self._provision_bytes, 'campaign provision is not canonical')
            self._rows = self._read_rows()
            checked = verify_evidence(self._evidence(), parent,
                expected_root_provision_sha256=self.root_provision_sha256, source_root=self.source_root)
            self._provision = checked['provision']; self._snapshot = checked['snapshot']
            self._cursor = checked['cursor']; self._state = checked['state']
            require(boot_nonce not in [load_json_strict(r[1])['boot_nonce'] for r in self._rows],
                    'campaign boot nonce replayed')
            self._commit('reopen', boot_nonce=boot_nonce)
        except BaseException:
            self.close(); raise

    def _read_rows(self):
        rows = self._connection.execute('SELECT serial,event,image FROM snapshots ORDER BY serial').fetchall()
        require(0 < len(rows) <= MAX_EVENTS and [r[0] for r in rows] == list(range(len(rows))) and
                all(type(r[1]) is bytes and type(r[2]) is bytes for r in rows),
                'campaign database snapshot sequence differs')
        require(sum(len(r[1]) + len(r[2]) for r in rows) <= MAX_BYTES, 'campaign database images exceed profile')
        return rows

    def _evidence(self):
        entries = []
        for _, event_raw, image_raw in self._rows:
            event, snapshot = load_json_strict(event_raw), load_json_strict(image_raw)
            require(canonical(event) == event_raw and canonical(snapshot) == image_raw,
                    'noncanonical campaign database image')
            entries.append({'event': event, 'snapshot': snapshot})
        return {'schema': SCHEMA, 'provision': load_json_strict(self._provision_bytes),
            'root_provision_sha256': self.root_provision_sha256, 'entries': entries,
            'final_cursor': _cursor(self.root_provision_sha256, entries[-1]['event']), 'scope': _copy(SCOPE)}

    def _check(self):
        require(not self._closed and not self._poisoned and self._connection is not None,
                'campaign authority closed or poisoned')
        self._lock.check()
        db = self.root_directory / 'authority.sqlite3'; _no_links(db)
        require(stat.S_ISREG(db.stat().st_mode) and os.path.samestat(self._database_stat, db.stat()),
                'campaign root database replaced')
        require(self._connection.execute('SELECT singleton,image FROM metadata').fetchall() ==
                [(1, self._provision_bytes)], 'campaign provision changed externally')
        require(self._connection.execute('PRAGMA synchronous').fetchone()[0] == 3 and
                self._connection.execute('PRAGMA journal_mode').fetchone()[0] == 'delete',
                'campaign synchronization policy changed')
        require(self._read_rows() == self._rows, 'campaign root changed outside this lifetime')

    @property
    def provision(self):
        self._check(); return _copy(self._provision)

    @property
    def cursor(self):
        self._check(); return _copy(self._cursor)

    @property
    def snapshot(self):
        self._check(); return _copy(self._snapshot)

    @property
    def state(self):
        self._check(); return self._state

    def export_evidence(self):
        self._check()
        evidence = self._evidence()
        verify_evidence(evidence, self.parent, expected_root_provision_sha256=self.root_provision_sha256,
                        source_root=self.source_root)
        return evidence

    def _commit(self, kind, *, boot_nonce=None, request=None, session=None):
        self._check()
        require(len(self._rows) < MAX_EVENTS, 'campaign root event capacity exhausted')
        epoch = self._cursor['epoch'] + 1 if kind == 'reopen' else self._cursor['epoch']
        snapshot = _next_snapshot(self._snapshot, self._provision, self.parent, self._cursor,
            kind=kind, epoch=epoch, request=request, session=session)
        event = _event(self.root_provision_sha256, snapshot, previous=self._cursor,
            kind=kind, epoch=epoch, boot_nonce=boot_nonce, request=request, session=session)
        event_raw, image_raw = canonical(event), canonical(snapshot)
        require(sum(len(r[1]) + len(r[2]) for r in self._rows) + len(event_raw) + len(image_raw) <= MAX_BYTES,
                'campaign root byte capacity exhausted')
        connection = self._connection
        try:
            connection.execute('BEGIN IMMEDIATE')
            require(self._read_rows() == self._rows and
                    connection.execute('SELECT singleton,image FROM metadata').fetchall() == [(1, self._provision_bytes)],
                    'campaign compare-and-publish predecessor changed')
            connection.execute('INSERT INTO snapshots VALUES (?,?,?)', (event['serial'], event_raw, image_raw))
            _fault('before_commit'); _fault(kind + ':before_commit')
            connection.commit()
            _fault('after_commit'); _fault(kind + ':after_commit')
            wanted = self._rows + [(event['serial'], event_raw, image_raw)]
            require(self._read_rows() == wanted, 'campaign committed readback differs')
            self._rows = wanted; self._snapshot = snapshot
            self._cursor = _cursor(self.root_provision_sha256, event)
            _, self._state = _journal(snapshot, self._provision)
        except BaseException:
            self._poisoned = True
            if connection.in_transaction:
                connection.rollback()
            raise

    def _reserve(self, expected_cursor, request_nonce, credits):
        self._check()
        # Reserve enough root transitions for consumption and completion before
        # authorizing work; a later capacity fault still retains the full charge.
        require(len(self._rows) + 3 <= MAX_EVENTS, 'campaign root lacks admission capacity')
        request = {'expected_cursor': _copy(expected_cursor), 'request_nonce': request_nonce, 'credits': credits}
        state = _request(request, self._cursor, self._snapshot, self._provision)
        permit = _permit(self.parent, self._provision, self._cursor, request, state)
        proposed = add(state.reserved, Policy.from_json(permit['grant']['envelope']).limits)
        kind = 'reserve' if Policy.from_json(self._provision['policy']).fits(proposed) else 'deny'
        self._commit(kind, request=request)
        if kind == 'deny':
            raise ResourceExhausted('durable campaign denied the full envelope before worker launch')
        return _copy(permit)

    def _consume_launch(self):
        self._check()
        require(self.source_root.resolve() == SOURCE_ROOT.resolve(),
                'live campaign must pin the actually executing source root')
        _same(implementation_identity(self.source_root), self._provision['implementation'],
              'fixed campaign source changed before worker launch')
        self._commit('launch')
        _fault('after_launch_consumption')
        return _copy(self._snapshot['pending']['permit'])

    def _complete(self, session):
        self._check()
        self._commit('complete', session=_copy(session))
        return load_json_strict(bytes.fromhex(self._snapshot['journal_hex']).splitlines()[-1])['body']

    def run_session(self, *, expected_cursor, request_nonce, credits):
        permit = self._reserve(expected_cursor, request_nonce, credits)
        self._consume_launch()
        launch_cursor = self.cursor
        grant = permit['grant']; objective = permit['objective']; freeze = permit['freeze']
        reservation_head = self._state.head
        native_directory = self.root_directory / 'worker-native' / grant['grant_hash']
        _fault('before_worker_launch')
        from .durable_campaign_native import RecordedCampaignEvaluatorClient, verify_native_records
        try:
            with RecordedCampaignEvaluatorClient(grant, native_directory=native_directory) as worker:
                public = worker.request('open', objective=objective, freeze=freeze,
                                        candidate_credits=credits)['public_challenge']
                binding = bind_phase16_search(self.parent.phase16_state(), turn_index=grant['session_index'],
                    challenge_commitment_hash=public['challenge_commitment_hash'],
                    public_nonce_hash=request_nonce, candidate_credits=credits)
                actual = [q.to_json() for q in sorted(binding.programs.values(), key=lambda q: q.program_hash)]
                require(actual == list(reference_grammar(self.parent.state, grant['session_index'], request_nonce)) and
                        digest(actual) == public['grammar_hash'], 'live campaign grammar disagreement')
                prefix = binding.prefix
                while decide(prefix).action == Action.EVALUATE:
                    step = decide(prefix)
                    artifact = realize_candidate(binding.programs[step.candidate_hash].to_json(), freeze)
                    receipt = worker.request('freeze_candidate', artifact_hash=artifact['artifact_hash'],
                                             program_hash=artifact['program_hash'])['receipt']
                    report = worker.request('evaluate', artifact=artifact,
                                             candidate_freeze_hash=receipt['candidate_freeze_hash'])
                    require(report['event'] == 'candidate_evaluated' and
                        report['program_hash'] == step.candidate_hash and report['artifact_hash'] == artifact['artifact_hash'] and
                        report['candidate_freeze_hash'] == receipt['candidate_freeze_hash'] and
                        report['evaluation_index'] == len(prefix.observations) and
                        report['evaluation_hash'] == digest({k: v for k, v in report.items() if k != 'evaluation_hash'}),
                        'live campaign evaluation receipt differs')
                    prefix = record_evaluation(prefix, step, verdict=report['verdict'],
                        evaluation_hash=report['evaluation_hash'], reason_codes=report['reason_codes'],
                        predecessor_state_hash=report['predecessor_state_hash'],
                        challenge_commitment_hash=report['challenge_commitment_hash'])
                worker.request('seal', terminal_action=decide(prefix).action.value)
                transcript, accounting = worker.transcript(), worker.accounting
                worker_pid = worker.process.pid
                require(worker.process.returncode == 0, 'authorized campaign worker did not exit cleanly')
            native = worker.evidence()
            require(type(native) is dict and native and all(type(raw) is bytes for raw in native.values()),
                    'original completed native worker evidence required')
            _same(verify_native_records(native_directory, grant, transcript, accounting,
                                       source_root=self.source_root),
                  {name: sha(raw) for name, raw in native.items()},
                  'original native worker records differ from completed semantics')
            checked_checkpoint = check_controller(self.parent, transcript)
            require(checked_checkpoint == checkpoint(prefix), 'actual live controller transcript differs')
            checked = verify_metered_transcript(self.parent, grant, transcript, accounting)
            completion = {'kind': 'complete', 'grant_hash': grant['grant_hash'], **checked}
            completed_journal = _append_journal(self._snapshot, self._provision, completion)
            completed_head = load_json_strict(bytes.fromhex(completed_journal).splitlines()[-1])['hash']
            files = {'grant.json': canonical(grant), 'objective.json': canonical(objective),
                'objective_freeze.json': canonical(freeze), 'public_challenge.json': canonical(public),
                'sealed_transcript.json': transcript, 'worker-accounting.json': canonical(accounting),
                'controller_checkpoint.json': checked_checkpoint,
                'session.json': canonical({'schema': 'rcp-rclm.phase17o.session.v1',
                    'session_index': grant['session_index'], 'grant_hash': grant['grant_hash'],
                    'campaign_head_before': grant['previous_campaign_head'], 'reservation_head': reservation_head,
                    'campaign_head_after': completed_head, 'completion': completion,
                    'reserved': grant['envelope']['limits'], 'worker_spent': accounting['spent'],
                    'controller_pid': os.getpid(), 'worker_pid': worker_pid,
                    'separate_process': worker_pid != os.getpid(), 'worker_exited_cleanly': True,
                    'fresh_live_challenge': True, 'automatic_retries': 0,
                    'claims': dict(OLD_FALSE_CLAIMS), 'unmeasured': list(UNMEASURED)})}
            session = {'files_hex': {name: raw.hex() for name, raw in files.items()},
                'native_sha256': {name: sha(raw) for name, raw in native.items()},
                'permit_sha256': permit['permit_sha256'], 'launch_cursor': launch_cursor,
                'owner_epoch': launch_cursor['epoch']}
            self._complete(session)
            files['durable-session.json'] = canonical({'schema': 'phase17al.authorized-session.v1',
                'permit': permit, 'launch_cursor': launch_cursor, 'completion_cursor': self.cursor,
                'native_sha256': session['native_sha256'], 'scope': _copy(SCOPE)})
            return files
        except BaseException:
            # Do not synthesize a failed/completed/refunded state from missing
            # process evidence. A fresh lifetime retains the unresolved charge.
            self._poisoned = True
            raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._connection is not None:
            if self._connection.in_transaction:
                self._connection.rollback()
            self._connection.close(); self._connection = None
        if self._lock is not None:
            self._lock.close(); self._lock = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
