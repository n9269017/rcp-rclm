"""Phase17AK: a durable, exclusive reference root for the unchanged AJ witness.

The separately provisioned root stores complete AJ/AI journal pairs in one
SQLite transaction and owns the current restart anchor.  A process holds a
nonblocking lifetime lock, and every publication compares the root epoch and
cursor again inside the transaction.  Native work uses a disk AJ witness;
path-free replay is used only to check retained images.  A response is released
only after commit and exact readback.  A new lifetime increments the epoch,
performs AJ.reopen, and never recovers an old execution owner.

The provider must protect this root directory, provisioning pin, and key and
must present one authoritative durable database.  SQLite/OS durability and
locking, authentication security, external issuer legitimacy, and resistance
to rolling back or cloning the entire trusted root are explicit assumptions.
This reference backend does not establish those physical properties, general
Python-to-Lean refinement, live campaign authority, or complete work accounting.
All inherited broader Phase17 flags remain false.  Uncommitted staging images
are retained as attempts, never accepted as a replacement root or completion.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import sqlite3
import stat

from . import controller_witness as aj
from .materialized import require, sha
from .resource_ledger import _no_links
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest

BASE = '0ad2290b81d7b4a314b10dd0bcfa28725be4a452'
SCHEMA = 'rcp-rclm.phase17ak.durable-authority-evidence.v1'
PROVISION_SCHEMA = 'phase17ak.durable-root-provision.v1'
EVENT_SCHEMA = 'phase17ak.durable-root-event.v1'
REQUEST_SCHEMA = 'phase17ak.durable-root-request.v1'
RESPONSE_SCHEMA = 'phase17ak.durable-root-response.v1'
POLICY = 'phase17ak.transactional-reference-root.v1'
BACKEND_POLICY = 'sqlite-full-sync-single-root-lifetime-lock.v1'
DOMAIN = b'RCPRCLM-PHASE17AK-DURABLE-ROOT-V1\0'
EVENT_DOMAIN = DOMAIN + b'EVENT\0'
REQUEST_DOMAIN = DOMAIN + b'REQUEST\0'
RESPONSE_DOMAIN = DOMAIN + b'RESPONSE\0'
CODE_PATH = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller_durable_authority.py'
SOURCE_ROOT = Path(__file__).resolve().parents[4]
MAX_ROOT_EVENTS = aj.MAX_EVENTS
FALSE_CLAIMS = aj.FALSE_CLAIMS
SCOPE = {
    'authority': 'independently pinned root provision and current complete AJ/AI snapshot in one trusted SQLite database',
    'persistence': 'SQLite DELETE journal, FULL synchronization, successful commit and exact readback; physical durability remains a backend assumption',
    'exclusivity': 'one cooperating process holding the nonblocking root-directory lifetime lock plus per-transaction epoch/cursor CAS',
    'restart': 'root snapshot supplies current head; fresh execution directory and AJ reopen revoke all prior execution ownership',
    'execution': 'unchanged disk-backed AJ/AI/AH reference execution; no path-free result substituted for observed execution',
    'authentication': 'domain-separated HMAC relative to separately provisioned key; fixture key is public and shared-key holders can forge responses',
    'resource': 'unchanged declared reference tariff only; root transactions, replay, synchronization, transport and host costs excluded',
    'external_issuer_authenticated': False,
    'physical_durability_verified': False,
    'global_clone_exclusion_established': False,
    'joint_root_rollback_resistance_established': False,
    'complete_resource_accounting': False,
    'fresh_worker_sessions': 0,
    'fresh_live_challenges': 0,
    'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _same(left, right, label):
    require(canonical(left) == canonical(right), label)


def _snapshot(value):
    return load_json_strict(canonical(value))


def _nat(value, label):
    require(type(value) is int and 0 <= value <= MAX_ROOT_EVENTS, 'bounded natural ' + label + ' required')
    return value


def durable_identity(root=SOURCE_ROOT):
    root = Path(root)
    bound = dict(aj.witness_identity(root)['code_sha256'])
    _no_links(root / CODE_PATH)
    bound[CODE_PATH] = sha((root / CODE_PATH).read_bytes())
    return {'policy': POLICY, 'backend_policy': BACKEND_POLICY, 'code_sha256': bound,
            'implementation_sha256': digest(bound), 'external_issuer_authenticated': False,
            'promotion_authorized': False}


def make_root_provision(prepared, provision, key, *, expected_provision_sha256,
                        authority_id, provisioning_nonce):
    """An administrator fixes this pin outside candidate/controller requests.

    Key bytes are never included in the public provision or evidence.  Passing
    a random private key is supported but is not evidence of external trust.
    """
    provision = aj._provision(prepared, provision, key, expected_provision_sha256)
    require(type(authority_id) is str and 0 < len(authority_id) <= 128,
            'bounded durable root authority identity required')
    aj._hash(provisioning_nonce, 'independent root provisioning nonce')
    return {'schema': PROVISION_SCHEMA, 'authority_id': authority_id,
            'provisioning_nonce': provisioning_nonce,
            'witness_provision': provision, 'witness_provision_sha256': expected_provision_sha256,
            'durable_identity': durable_identity(), 'backend_policy': BACKEND_POLICY,
            'key_commitment': sha(aj._key(key)),
            'public_reference_fixture_key': key == aj.PUBLIC_FIXTURE_KEY,
            'external_issuer_authenticated': False, 'complete_resource_accounting': False,
            'promotion_authorized': False}


def _provision(prepared, value, key, expected):
    aj._hash(expected, 'independent durable root provisioning pin')
    value = _snapshot(value)
    _exact(value, {'schema', 'authority_id', 'provisioning_nonce', 'witness_provision',
        'witness_provision_sha256', 'durable_identity', 'backend_policy', 'key_commitment',
        'public_reference_fixture_key', 'external_issuer_authenticated',
        'complete_resource_accounting', 'promotion_authorized'}, 'durable root provision')
    require(digest(value) == expected, 'durable root provision differs from independent pin')
    wanted = make_root_provision(prepared, value['witness_provision'], key,
        expected_provision_sha256=value['witness_provision_sha256'],
        authority_id=value['authority_id'], provisioning_nonce=value['provisioning_nonce'])
    _same(value, wanted, 'durable root source, policy, key or witness provision differs')
    return value


def _image(witness_raw, authority_raw):
    require(type(witness_raw) is bytes and 0 < len(witness_raw) <= aj.MAX_LEDGER_BYTES,
            'bounded complete witness image required')
    require(type(authority_raw) is bytes and 0 < len(authority_raw) <= aj.ai.MAX_JOURNAL_BYTES,
            'bounded complete authority image required')
    return {'witness_sha256': sha(witness_raw), 'authority_sha256': sha(authority_raw),
            'witness_bytes': len(witness_raw), 'authority_bytes': len(authority_raw)}


def _image_digest(image):
    return digest({name: image[name] for name in ('witness_sha256', 'authority_sha256')})


def _cursor(provision_sha256, event):
    return {'root_provision_sha256': provision_sha256, 'epoch': event['epoch'],
            'serial': event['serial'], 'root_head': event['hash'],
            'image_sha256': event['after']['image_sha256'],
            'witness_cursor': _snapshot(event['after']['witness_cursor'])}


def _validate_cursor(value):
    _exact(value, {'root_provision_sha256', 'epoch', 'serial', 'root_head',
                  'image_sha256', 'witness_cursor'}, 'durable root cursor')
    _nat(value['epoch'], 'root epoch'); _nat(value['serial'], 'root serial')
    for name in ('root_provision_sha256', 'root_head', 'image_sha256'):
        aj._hash(value[name], name)
    inner = value['witness_cursor']
    _exact(inner, {'revision', 'witness_head', 'authority_head'}, 'witness cursor')
    _nat(inner['revision'], 'witness revision')
    aj._hash(inner['witness_head'], 'witness head'); aj._hash(inner['authority_head'], 'authority head')
    return value


def _event(provision_sha256, witness, authority_raw, *, before, epoch, kind, boot_nonce):
    raw = witness.raw
    image = _image(raw, authority_raw)
    serial = 0 if before is None else before['serial'] + 1
    _nat(serial, 'root serial'); _nat(epoch, 'root epoch')
    request_sha = None if before is None else digest(witness.records[-1]['body']['request'])
    core = {'schema': EVENT_SCHEMA, 'root_provision_sha256': provision_sha256,
            'serial': serial, 'epoch': epoch, 'kind': kind,
            'boot_nonce': boot_nonce, 'previous_root_head': aj.ai.ZERO if before is None else before['root_head'],
            'request_sha256': request_sha, 'before': _snapshot(before),
            'after': {'epoch': epoch, 'serial': serial, 'image_sha256': _image_digest(image),
                      'witness_cursor': witness.cursor}, 'image': image}
    return {**core, 'hash': sha(EVENT_DOMAIN + canonical(core))}


def _entry(event, witness_raw, authority_raw):
    return {'event': _snapshot(event), 'witness_journal': witness_raw.decode('utf-8'),
            'authority_journal': authority_raw.decode('utf-8')}


@dataclass(frozen=True, slots=True)
class _VerifiedImage:
    raw: bytes
    cursor_bytes: bytes
    last_record_bytes: bytes
    record_count: int

    @property
    def cursor(self):
        return load_json_strict(self.cursor_bytes)

    @property
    def records(self):
        # The event constructor needs only the exact last request, while the
        # separately retained count/prefix check proves extension length.
        return [load_json_strict(self.last_record_bytes)]


@lru_cache(maxsize=64)
def _verified_image(prepared, provision_bytes, key, provision_pin, raw, authority, expected_head):
    """Cache only complete immutable, independently replayed journal images.

    The active root provision/source identities are checked before each lookup.
    This cache never holds live ownership or confers a native execution credit.
    """
    reconstructed = aj.replay_witness(raw, prepared, load_json_strict(provision_bytes), key,
        expected_provision_sha256=provision_pin, expected_head=expected_head)
    try:
        require(reconstructed._ai.raw == authority, 'durable AJ/AI journal pair differs')
        records = reconstructed.records
        return _VerifiedImage(raw, canonical(reconstructed.cursor), canonical(records[-1]), len(records))
    finally:
        reconstructed.close()


def verify_evidence(evidence, prepared, key, *, expected_root_provision_sha256):
    """Purely reconstruct exact accepted images; never execute a native worker.

    This verifies recorded semantics and bytes.  It does not prove that a
    submitted history is the physically current root, or manufacture observed
    commit/locking evidence from a reconstructed history.
    """
    _exact(evidence, {'schema', 'root_provision', 'root_provision_sha256', 'events',
                      'final_cursor', 'scope'}, 'durable root evidence')
    require(evidence['schema'] == SCHEMA and evidence['root_provision_sha256'] == expected_root_provision_sha256,
            'durable root evidence schema or independent pin differs')
    _same(evidence['scope'], SCOPE, 'durable root evidence scope differs')
    provision = _provision(prepared, evidence['root_provision'], key, expected_root_provision_sha256)
    entries = evidence['events']
    require(type(entries) is list and 0 < len(entries) <= MAX_ROOT_EVENTS,
            'complete bounded durable root event history required')
    previous = None; previous_witness = b''; previous_authority = b''; boot = None
    for serial, entry in enumerate(entries):
        _exact(entry, {'event', 'witness_journal', 'authority_journal'}, 'durable root image entry')
        require(type(entry['witness_journal']) is str and type(entry['authority_journal']) is str,
                'exact UTF8 retained journal images required')
        raw = entry['witness_journal'].encode('utf-8'); authority = entry['authority_journal'].encode('utf-8')
        event = entry['event']
        _exact(event, {'schema', 'root_provision_sha256', 'serial', 'epoch', 'kind', 'boot_nonce', 'previous_root_head',
            'request_sha256', 'before', 'after', 'image', 'hash'}, 'durable root event')
        _exact(event['after'], {'epoch', 'serial', 'image_sha256', 'witness_cursor'}, 'root event after')
        _exact(event['image'], {'witness_sha256', 'authority_sha256', 'witness_bytes', 'authority_bytes'},
               'root image binding')
        image = _image(raw, authority)
        _same(event['image'], image, 'durable journal image bytes differ')
        _nat(event['serial'], 'root serial'); _nat(event['epoch'], 'root epoch')
        require(event['serial'] == serial and event['schema'] == EVENT_SCHEMA and
                event['root_provision_sha256'] == expected_root_provision_sha256,
                'durable root event order, provisioning identity or schema differs')
        aj._hash(event['hash'], 'root event hash')
        cursor = _validate_cursor(_cursor(expected_root_provision_sha256, event))
        reconstructed = _verified_image(prepared, canonical(provision['witness_provision']), key,
            provision['witness_provision_sha256'], raw, authority, cursor['witness_cursor']['witness_head'])
        if previous is None:
            require(reconstructed.record_count == 1 and event['kind'] == 'provision' and
                    event['epoch'] == 0 and event['boot_nonce'] is None,
                    'durable root genesis differs')
        else:
            require(raw.startswith(previous_witness) and reconstructed.record_count == serial + 1,
                    'root snapshot is not one exact AJ extension')
            require(authority.startswith(previous_authority), 'root snapshot rolls back authority bytes')
            kind = reconstructed.records[-1]['body']['kind']
            require(kind == event['kind'] and kind in ('reopen', 'reserve', 'execute', 'deny', 'stop'),
                    'root event substitutes witness operation')
            if kind == 'reopen':
                aj._hash(event['boot_nonce'], 'root boot nonce')
                require(event['epoch'] == previous['epoch'] + 1 and
                        reconstructed.records[-1]['body']['request']['body']['nonce'] == event['boot_nonce'],
                        'root reopening did not advance epoch with its exact nonce')
                boot = event['boot_nonce']
            else:
                require(boot is not None and event['epoch'] == previous['epoch'] and event['boot_nonce'] == boot,
                        'root operation crosses its exclusive epoch')
        expected_event = _event(expected_root_provision_sha256, reconstructed, authority,
            before=previous, epoch=event['epoch'], kind=event['kind'], boot_nonce=event['boot_nonce'])
        _same(event, expected_event, 'root event is not the exact committed transition')
        previous = cursor; previous_witness = raw; previous_authority = authority
    _same(evidence['final_cursor'], previous, 'durable root final cursor differs')
    return {'root_provision_sha256': expected_root_provision_sha256, 'cursor': previous,
            'event_count': len(entries), 'epochs': previous['epoch'],
            'witness_journal_sha256': sha(previous_witness), 'authority_journal_sha256': sha(previous_authority),
            'native_execution_repeated': False, 'physical_currentness_established': False}


def _mac(key, domain, value):
    return hmac.new(aj._key(key), domain + canonical(value), hashlib.sha256).hexdigest()


def make_request(root_provision_sha256, key, witness_request, *, expected_cursor=None):
    aj._hash(root_provision_sha256, 'durable request root pin')
    if expected_cursor is not None:
        _validate_cursor(expected_cursor)
    core = {'schema': REQUEST_SCHEMA, 'root_provision_sha256': root_provision_sha256,
            'expected_cursor': _snapshot(expected_cursor), 'witness_request': _snapshot(witness_request)}
    return {**core, 'mac': _mac(key, REQUEST_DOMAIN, core)}


def _request(value, key, root_pin, witness_pin):
    value = _snapshot(value)
    _exact(value, {'schema', 'root_provision_sha256', 'expected_cursor', 'witness_request', 'mac'},
           'durable root request')
    require(value['schema'] == REQUEST_SCHEMA and value['root_provision_sha256'] == root_pin,
            'durable request names another root')
    aj._hash(value['mac'], 'root request MAC')
    core = {name: value[name] for name in ('schema', 'root_provision_sha256', 'expected_cursor', 'witness_request')}
    require(hmac.compare_digest(value['mac'], _mac(key, REQUEST_DOMAIN, core)), 'durable request MAC differs')
    inner = aj._request(value['witness_request'], witness_pin, key)
    if inner['body']['op'] == 'read':
        require(value['expected_cursor'] is None, 'root read cannot choose a stored root cursor')
    else:
        _validate_cursor(value['expected_cursor'])
        require(value['expected_cursor']['root_provision_sha256'] == root_pin,
                'root cursor provision differs')
    return value


def verify_reply(reply, supplied_request, *, key, expected_root_provision_sha256):
    _exact(reply, {'schema', 'root_provision_sha256', 'request_sha256', 'nonce', 'cursor',
                  'commit_applied', 'witness_response', 'mac'}, 'durable root response')
    witness_pin = supplied_request['witness_request']['provision_sha256']
    supplied_request = _request(supplied_request, key, expected_root_provision_sha256, witness_pin)
    require(reply['schema'] == RESPONSE_SCHEMA and
            reply['root_provision_sha256'] == expected_root_provision_sha256 and
            reply['request_sha256'] == digest(supplied_request) and
            reply['nonce'] == supplied_request['witness_request']['body']['nonce'],
            'durable response is not bound to this root and fresh request')
    aj._hash(reply['mac'], 'root response MAC')
    core = {name: value for name, value in reply.items() if name != 'mac'}
    require(hmac.compare_digest(reply['mac'], _mac(key, RESPONSE_DOMAIN, core)), 'durable response MAC differs')
    cursor = _validate_cursor(reply['cursor'])
    require(cursor['root_provision_sha256'] == expected_root_provision_sha256 and type(reply['commit_applied']) is bool,
            'durable response cursor or publication flag differs')
    payload = aj.verify_reply(reply['witness_response'], supplied_request['witness_request'],
        expected_provision_sha256=witness_pin, key=key)
    inner_cursor = {name: payload['state'][name] for name in ('revision', 'witness_head', 'authority_head')}
    _same(cursor['witness_cursor'], inner_cursor, 'root response does not bind its exact AJ state')
    advancing = payload['ok'] and payload['outcome'] != 'read'
    require(reply['commit_applied'] == advancing, 'durable response publication flag contradicts AJ result')
    if advancing:
        before = supplied_request['expected_cursor']
        require(cursor['epoch'] == before['epoch'] and cursor['serial'] == before['serial'] + 1 and
                cursor['root_head'] != before['root_head'] and cursor['image_sha256'] != before['image_sha256'],
                'durable acknowledgement does not advance the requested current root')
    return {'cursor': _snapshot(cursor), 'commit_applied': reply['commit_applied'], 'witness': payload}


class _LifetimeLock:
    def __init__(self, path):
        self.path = Path(path); self.stream = None
        _no_links(self.path)
        require(self.path.is_file(), 'provisioned durable root lock missing')
        self.stream = open(self.path, 'r+b', buffering=0)
        try:
            require(self.stream.read() == b'L', 'durable root lock bytes differ')
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.check()
        except BaseException:
            self.close(); raise

    def check(self):
        _no_links(self.path)
        require(self.stream is not None and stat.S_ISREG(self.path.stat().st_mode) and
                os.path.samestat(os.fstat(self.stream.fileno()), self.path.stat()),
                'durable root lifetime lock replaced')

    def close(self):
        if self.stream is not None:
            self.stream.close(); self.stream = None


def _connect(path):
    _no_links(path)
    require(path.is_file(), 'provisioned durable root database missing; opening cannot initialize it')
    connection = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.execute('PRAGMA foreign_keys=ON')
        mode = connection.execute('PRAGMA journal_mode').fetchone()[0]
        connection.execute('PRAGMA synchronous=FULL')
        require(mode == 'delete' and connection.execute('PRAGMA synchronous').fetchone()[0] == 2,
                'durable root backend synchronization policy differs')
        require(connection.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'durable root database corrupt')
        return connection
    except BaseException:
        connection.close(); raise


def _write_new(path, data):
    _no_links(path)
    with open(path, 'xb', buffering=0) as stream:
        require(stream.write(data) == len(data), 'short new durable authority image write')
        stream.flush(); os.fsync(stream.fileno())


def _directory_sync(path):
    # POSIX supplies directory fsync.  Windows directory durability remains an
    # explicit SQLite/OS premise; opening a directory as a file is unsupported.
    if os.name != 'nt':
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def provision_root(root_directory, prepared, provision, key, *, expected_provision_sha256,
                   authority_id, provisioning_nonce):
    root = Path(root_directory).absolute(); _no_links(root)
    require(not root.exists(), 'durable root provisioning cannot overwrite or reinitialize a root')
    value = make_root_provision(prepared, provision, key,
        expected_provision_sha256=expected_provision_sha256,
        authority_id=authority_id, provisioning_nonce=provisioning_nonce)
    pin = digest(value)
    root.mkdir(mode=0o700, parents=True)
    _write_new(root / 'authority.lock', b'L')
    _write_new(root / 'authority.sqlite3', b'')
    os.chmod(root / 'authority.lock', 0o600); os.chmod(root / 'authority.sqlite3', 0o600)
    connection = _connect(root / 'authority.sqlite3')
    witness = None
    try:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), image BLOB NOT NULL)')
        connection.execute('CREATE TABLE snapshots (serial INTEGER PRIMARY KEY, event BLOB NOT NULL, witness BLOB NOT NULL, authority BLOB NOT NULL)')
        witness = aj.WitnessAuthority(None, prepared, provision, key,
            expected_provision_sha256=expected_provision_sha256)
        event = _event(pin, witness, witness._ai.raw, before=None, epoch=0, kind='provision', boot_nonce=None)
        connection.execute('INSERT INTO metadata VALUES (1,?)', (canonical(value),))
        connection.execute('INSERT INTO snapshots VALUES (0,?,?,?)',
                           (canonical(event), witness.raw, witness._ai.raw))
        connection.commit()
        rows = connection.execute('SELECT serial,event,witness,authority FROM snapshots ORDER BY serial').fetchall()
        require(rows == [(0, canonical(event), witness.raw, witness._ai.raw)], 'new root committed readback differs')
        _directory_sync(root)
        return {'root_provision_sha256': pin, 'cursor': _cursor(pin, event)}
    finally:
        if witness is not None:
            witness.close()
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def _fault(stage):
    """Named failure boundaries for controlled tests, with no runtime bypass."""


class DurableAuthority:
    """One exclusive native witness lifetime under an independently pinned root.

    The execution directory must be new.  It is populated only from the accepted
    root image, so a controller cannot choose a stale local restart anchor.
    Neither close nor any exception removes attempted/native evidence.
    """
    def __init__(self, root_directory, prepared, key, *, expected_root_provision_sha256,
                 execution_directory, boot_nonce):
        self.root = Path(root_directory).absolute(); _no_links(self.root)
        self.execution_directory = Path(execution_directory).absolute()
        _no_links(self.execution_directory)
        require(self.root.is_dir() and not self.execution_directory.exists(),
                'existing provisioned root and fresh execution directory required')
        require(self.root not in self.execution_directory.parents and
                self.execution_directory not in self.root.parents and self.root != self.execution_directory,
                'trusted durable root and untrusted execution directories must be separate')
        aj._hash(boot_nonce, 'new authority lifetime nonce')
        self.prepared = prepared; self.key = aj._key(key)
        self.root_provision_sha256 = expected_root_provision_sha256
        self._closed = self._poisoned = False
        self._lock = self._connection = self._witness = None
        self._rows = []; self._provision_bytes = None; self._cursor = None
        self._boot_nonce = boot_nonce; self._epoch = None
        try:
            self._lock = _LifetimeLock(self.root / 'authority.lock')
            self._database_path = self.root / 'authority.sqlite3'
            self._database_stat = self._database_path.stat()
            self._connection = _connect(self._database_path)
            schema = self._connection.execute("SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            require(schema == [('metadata', 'table'), ('snapshots', 'table')], 'durable root database schema differs')
            meta = self._connection.execute('SELECT singleton,image FROM metadata').fetchall()
            require(len(meta) == 1 and meta[0][0] == 1 and type(meta[0][1]) is bytes,
                    'exact root provision database image required')
            self._provision_bytes = meta[0][1]
            value = load_json_strict(self._provision_bytes)
            require(canonical(value) == self._provision_bytes, 'root provision image is not canonical')
            _provision(prepared, value, key, expected_root_provision_sha256)
            self._rows = self._read_rows()
            evidence = self._evidence()
            checked = verify_evidence(evidence, prepared, key,
                                      expected_root_provision_sha256=expected_root_provision_sha256)
            self._cursor = checked['cursor']; self._epoch = self._cursor['epoch'] + 1
            last = self._rows[-1]
            self.execution_directory.mkdir(mode=0o700, parents=True)
            _write_new(self.execution_directory / 'witness.jsonl', last[2])
            _write_new(self.execution_directory / 'authority.jsonl', last[3])
            _write_new(self.execution_directory / 'root-start.json', canonical({
                'schema': 'phase17ak.authority-start.v1', 'root_provision_sha256': expected_root_provision_sha256,
                'previous_cursor': self._cursor, 'epoch': self._epoch, 'boot_nonce': boot_nonce}))
            self._witness = aj.WitnessAuthority(self.execution_directory, prepared,
                value['witness_provision'], key, expected_provision_sha256=value['witness_provision_sha256'],
                expected_head=self._cursor['witness_cursor']['witness_head'])
            self._witness.reopen(boot_nonce)
            self._commit(kind='reopen', epoch=self._epoch)
        except BaseException:
            self._poisoned = True; self.close(); raise

    @property
    def provision(self):
        return load_json_strict(self._provision_bytes)

    @property
    def witness_provision(self):
        return self.provision['witness_provision']

    @property
    def cursor(self):
        self._check()
        return _snapshot(self._cursor)

    def _read_rows(self):
        rows = self._connection.execute('SELECT serial,event,witness,authority FROM snapshots ORDER BY serial').fetchall()
        require(0 < len(rows) <= MAX_ROOT_EVENTS and all(type(row[0]) is int and
                all(type(value) is bytes for value in row[1:]) for row in rows),
                'invalid durable snapshot history')
        require(all(row[0] == index for index, row in enumerate(rows)),
                'durable SQL snapshot slot differs from its ordered serial')
        require(all(canonical(load_json_strict(row[1])) == row[1] and
                    0 < len(row[2]) <= aj.MAX_LEDGER_BYTES and
                    0 < len(row[3]) <= aj.ai.MAX_JOURNAL_BYTES for row in rows),
                'noncanonical or oversized durable snapshot image')
        return rows

    def _evidence(self):
        events = [_entry(load_json_strict(row[1]), row[2], row[3]) for row in self._rows]
        return {'schema': SCHEMA, 'root_provision': self.provision,
                'root_provision_sha256': self.root_provision_sha256, 'events': events,
                'final_cursor': _cursor(self.root_provision_sha256, events[-1]['event']),
                'scope': _snapshot(SCOPE)}

    def _check(self):
        require(not self._closed and not self._poisoned, 'closed or poisoned durable authority')
        self._lock.check(); _no_links(self._database_path)
        require(stat.S_ISREG(self._database_path.stat().st_mode) and
                os.path.samestat(self._database_stat, self._database_path.stat()),
                'durable root database replaced')
        require(self._connection.execute('SELECT singleton,image FROM metadata').fetchall() == [(1, self._provision_bytes)],
                'durable root provision changed externally')
        require(self._read_rows() == self._rows, 'durable root epoch, cursor or history changed externally')
        if self._cursor is not None and self._epoch is not None:
            require(self._cursor['epoch'] == self._epoch, 'stale durable authority lifetime')

    def _commit(self, *, kind, epoch):
        # _check's lifetime comparison is deferred for the opening epoch change.
        require(not self._closed and not self._poisoned, 'closed or poisoned durable authority')
        self._lock.check()
        before = _snapshot(self._cursor)
        raw, authority = self._witness.raw, self._witness._ai.raw
        event = _event(self.root_provision_sha256, self._witness, authority,
                      before=before, epoch=epoch, kind=kind, boot_nonce=self._boot_nonce)
        candidate = (*self._rows, (event['serial'], canonical(event), raw, authority))
        require(len(candidate) <= MAX_ROOT_EVENTS, 'durable root event bound exhausted')
        # AJ replay verifies the exact state transition and complete image pair;
        # full root validation also prevents accidental epoch or head changes.
        proposed = {'schema': SCHEMA, 'root_provision': self.provision,
            'root_provision_sha256': self.root_provision_sha256,
            'events': [_entry(load_json_strict(row[1]), row[2], row[3]) for row in candidate],
            'final_cursor': _cursor(self.root_provision_sha256, event), 'scope': _snapshot(SCOPE)}
        verify_evidence(proposed, self.prepared, self.key,
                        expected_root_provision_sha256=self.root_provision_sha256)
        try:
            _fault('before_commit')
            self._connection.execute('BEGIN IMMEDIATE')
            require(self._read_rows() == self._rows and
                    self._connection.execute('SELECT singleton,image FROM metadata').fetchall() == [(1, self._provision_bytes)],
                    'durable root compare-and-swap rejected a stale epoch or cursor')
            current = _cursor(self.root_provision_sha256, load_json_strict(self._rows[-1][1]))
            _same(current, before, 'durable root CAS predecessor differs')
            require(epoch == before['epoch'] + 1 if kind == 'reopen' else epoch == before['epoch'],
                    'durable publication has the wrong exclusive epoch')
            self._connection.execute('INSERT INTO snapshots VALUES (?,?,?,?)', candidate[-1])
            _fault('after_insert')
            self._connection.commit()
            _fault('after_commit')
            require(self._read_rows() == list(candidate), 'committed durable root readback differs')
            self._rows = list(candidate); self._cursor = proposed['final_cursor']
            _directory_sync(self.root)
            _fault('after_readback')
        except BaseException:
            self._poisoned = True
            if self._connection.in_transaction:
                self._connection.rollback()
            raise

    def dispatch(self, supplied):
        self._check()
        value = _request(supplied, self.key, self.root_provision_sha256,
                         self.provision['witness_provision_sha256'])
        inner = value['witness_request']; op = inner['body']['op']
        require(op != 'reopen', 'controller cannot acquire a new root epoch')
        if op != 'read':
            _same(value['expected_cursor'], self._cursor, 'stale durable root request cursor')
        try:
            witness_response = self._witness.dispatch(inner)
            payload = aj.verify_reply(witness_response, inner,
                expected_provision_sha256=self.provision['witness_provision_sha256'], key=self.key)
            advancing = bool(payload['ok'] and payload['outcome'] != 'read')
            if advancing:
                self._commit(kind=self._witness.records[-1]['body']['kind'], epoch=self._epoch)
            self._check()
            _same(self._cursor['witness_cursor'], self._witness.cursor,
                  'acknowledgement would expose uncommitted witness state')
            core = {'schema': RESPONSE_SCHEMA, 'root_provision_sha256': self.root_provision_sha256,
                    'request_sha256': digest(value), 'nonce': inner['body']['nonce'],
                    'cursor': _snapshot(self._cursor), 'commit_applied': advancing,
                    'witness_response': witness_response}
            reply = {**core, 'mac': _mac(self.key, RESPONSE_DOMAIN, core)}
            verify_reply(reply, value, key=self.key, expected_root_provision_sha256=self.root_provision_sha256)
            _fault('before_reply')
            return reply
        except BaseException:
            self._poisoned = True
            raise

    def export_evidence(self):
        self._check()
        evidence = self._evidence()
        verify_evidence(evidence, self.prepared, self.key,
                        expected_root_provision_sha256=self.root_provision_sha256)
        return evidence

    def close(self):
        if self._witness is not None:
            self._witness.close(); self._witness = None
        if self._connection is not None:
            if self._connection.in_transaction:
                self._connection.rollback()
            self._connection.close(); self._connection = None
        if self._lock is not None:
            self._lock.close(); self._lock = None
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()
