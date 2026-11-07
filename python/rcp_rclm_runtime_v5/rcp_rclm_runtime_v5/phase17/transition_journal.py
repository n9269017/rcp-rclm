"""Anchored write-ahead challenge consumption. No acceptance or activation event.

Durability is a requested local fsync, not a cross-file atomicity theorem. The
external head and parent binding remain trusted; rolling both back is not
prevented. An interrupted begin is consumed and requires explicit abandonment.
"""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
from rcp_rclm_runtime.canonical.json import load_json_strict
from .resource_ledger import canonical, digest, exact, nat, require, sha, _no_links, ZERO

SCHEMA = 'rcp-rclm.phase17p.transition-journal.v1'
MAX_BYTES = 4 * 1024 * 1024
MAX_EVENT = 8192
MAX_EVENTS = 2048
BINDING_KEYS = {'mode','scope_id','predecessor_state_hash','predecessor_logical_package_hash',
                'predecessor_physical_hash','fixed_verifier_hash'}
BEGIN_KEYS = {'source_sha256','handoff_sha256','challenge_commitment_hash','transcript_sha256',
              'terminal_action','transaction_id'}


def binding(value: dict) -> dict:
    exact(value, BINDING_KEYS)
    require(value['mode'] in ('online_campaign','retained_synthetic_fixture'), 'invalid transaction mode')
    return {k: value[k] if k == 'mode' else digest(value[k]) for k in BINDING_KEYS}


def transaction_id(source_hash: str, physical_parent: str) -> str:
    return sha(b'RCPRCLM-PHASE17P-TRANSACTION-V1\0' + canonical({
        'source_sha256': digest(source_hash), 'predecessor_physical_hash': digest(physical_parent)}))


def event(body: dict, index: int, previous: str) -> dict:
    core = {'index': nat(index), 'previous': digest(previous), 'body': body}
    return {**core, 'hash': sha(b'RCPRCLM-PHASE17P-EVENT-V1\0' + canonical(core))}


@dataclass(frozen=True, slots=True)
class TransitionState:
    head: str
    event_count: int
    status: str
    pending: bytes | None
    completed: tuple[bytes, ...]
    consumed: tuple[str, ...]
    source_hashes: tuple[str, ...]


def replay(raw: bytes, *, expected_head: str, expected_binding: dict) -> TransitionState:
    wanted = binding(expected_binding); digest(expected_head)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and raw.endswith(b'\n'), 'bounded complete journal required')
    lines = raw.splitlines(keepends=True)
    require(0 < len(lines) <= MAX_EVENTS, 'transition event bound exceeded')
    head, status, pending = ZERO, 'new', None
    done, consumed, sources = [], [], []
    for i, line in enumerate(lines):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n') and len(line) <= MAX_EVENT, 'noncanonical journal line')
        row = load_json_strict(line[:-1]); exact(row, {'index','previous','body','hash'})
        require(canonical(row) == line[:-1], 'noncanonical event')
        require(nat(row['index']) == i and digest(row['previous']) == head, 'stale event lineage')
        require(canonical(row) == canonical(event(row['body'], i, head)), 'event digest mismatch')
        b = row['body']; require(type(b) is dict, 'event body required')
        kind = b.get('kind')
        if i == 0:
            exact(b, {'kind','schema','binding'})
            require(kind == 'open' and b['schema'] == SCHEMA and canonical(binding(b['binding'])) == canonical(wanted),
                    'external transition binding differs')
            status = 'open'
        elif kind == 'consume':
            exact(b, {'kind', *BEGIN_KEYS})
            require(status == 'open' and pending is None, 'pending or terminated transition')
            for k in BEGIN_KEYS - {'terminal_action'}: digest(b[k])
            require(b['transaction_id'] == transaction_id(b['source_sha256'], wanted['predecessor_physical_hash']),
                    'transaction identity differs')
            require(b['terminal_action'] in ('await_root_verification','resource_exhausted','search_exhausted',
                                             'external_stop_valid_prefix'), 'unsupported source terminal')
            require(b['challenge_commitment_hash'] not in consumed and b['source_sha256'] not in sources,
                    'challenge or source already consumed')
            consumed.append(b['challenge_commitment_hash']); sources.append(b['source_sha256'])
            pending = canonical(b); status = 'pending'
        elif kind == 'complete':
            exact(b, {'kind','transaction_id','outcome','report_sha256'})
            require(status == 'pending' and pending is not None, 'completion without pending handoff')
            start = load_json_strict(pending)
            require(digest(b['transaction_id']) == start['transaction_id'], 'stale transaction completion')
            digest(b['report_sha256'])
            wanted_outcome = 'blocked_missing_root_witnesses' if start['terminal_action'] == 'await_root_verification' else 'no_candidate'
            require(b['outcome'] == wanted_outcome, 'unsupported acceptance or terminal escalation')
            done.append(canonical({'begin': start, 'completion': b})); pending = None; status = 'open'
        elif kind == 'abort':
            exact(b, {'kind','transaction_id','reason'})
            require(status == 'pending' and pending is not None, 'no pending transition to abandon')
            require(digest(b['transaction_id']) == load_json_strict(pending)['transaction_id'] and
                    b['reason'] in ('staging_failed','interrupted'), 'invalid abandonment')
            # consumed remains unchanged, including interrupted begins.
            pending = None; status = 'safety_halt'
        elif kind == 'stop':
            exact(b, {'kind'})
            require(status == 'open' and pending is None, 'pending work cannot be skipped')
            status = 'external_stop'
        else:
            raise ValueError('unknown transition event; activation is not implemented')
        head = row['hash']
    require(head == expected_head, 'external transition head differs')
    return TransitionState(head, len(lines), status, pending, tuple(done), tuple(consumed), tuple(sources))


class TransitionJournal:
    """Single trusted writer; filesystem coordination is not hostile-code isolation."""
    def __init__(self, path: Path, *, expected_binding: dict, expected_head: str | None = None):
        self.path = Path(path).absolute(); _no_links(self.path)
        require(self.path.parent.is_dir(), 'journal parent missing')
        self._binding = canonical(binding(expected_binding))
        self._closed = False; self._poisoned = False
        self._lock = self._file = None; self._raw = b''; self._state = None
        lock = self.path.with_name(self.path.name+'.lock'); _no_links(lock)
        require(not lock.exists() or lock.is_file(), 'regular lock required')
        try:
            self._lock = open(lock, 'a+b', buffering=0)
            if self._lock.seek(0, os.SEEK_END) == 0: self._lock.write(b'L')
            self._lock.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            if expected_head is None:
                require(not self.path.exists(), 'existing journal requires external anchor')
                self._file = open(self.path, 'x+b', buffering=0)
                self._append_raw(event({'kind':'open','schema':SCHEMA,'binding':self.binding},0,ZERO))
            else:
                digest(expected_head); require(self.path.is_file(), 'journal missing')
                self._file = open(self.path,'r+b',buffering=0)
                self._raw = self._file.read(MAX_BYTES+1)
                self._state = replay(self._raw, expected_head=expected_head, expected_binding=self.binding)
        except BaseException:
            self.close(); raise

    @property
    def binding(self): return load_json_strict(self._binding)

    def _check(self):
        require(not self._closed and not self._poisoned and self._file is not None, 'closed or poisoned transition journal')
        _no_links(self.path)
        require(os.path.samestat(os.fstat(self._file.fileno()),self.path.stat()), 'journal replaced')
        self._file.seek(0)
        require(self._file.read(MAX_BYTES+1) == self._raw, 'journal mutated externally')

    @property
    def state(self): self._check(); return self._state

    def journal_bytes(self): self._check(); return self._raw

    def _append_raw(self,row):
        data = canonical(row)+b'\n'
        require(len(data)<=MAX_EVENT and len(self._raw)+len(data)<=MAX_BYTES, 'journal bound exceeded')
        raw = self._raw+data
        state = replay(raw,expected_head=row['hash'],expected_binding=self.binding)
        try:
            self._file.seek(0,os.SEEK_END)
            require(self._file.write(data)==len(data), 'short journal write')
            self._file.flush(); os.fsync(self._file.fileno())
        except BaseException:
            self._poisoned=True; raise
        self._raw,self._state=raw,state

    def _append(self,b):
        self._check(); self._append_raw(event(b,self._state.event_count,self._state.head))

    def consume(self, *, source_sha256: str, handoff_sha256: str, challenge_commitment_hash: str,
                transcript_sha256: str, terminal_action: str) -> str:
        tid=transaction_id(source_sha256,self.binding['predecessor_physical_hash'])
        self._append({'kind':'consume','source_sha256':source_sha256,'handoff_sha256':handoff_sha256,
            'challenge_commitment_hash':challenge_commitment_hash,'transcript_sha256':transcript_sha256,
            'terminal_action':terminal_action,'transaction_id':tid})
        return tid

    def complete(self, *, transaction: str, outcome: str, report_sha256: str):
        self._append({'kind':'complete','transaction_id':transaction,'outcome':outcome,'report_sha256':report_sha256})

    def abort(self, *, interrupted: bool = False):
        require(type(interrupted) is bool,'Boolean interrupted flag required')
        require(self.state.pending is not None,'no pending transition')
        self._append({'kind':'abort','transaction_id':load_json_strict(self.state.pending)['transaction_id'],
                      'reason':'interrupted' if interrupted else 'staging_failed'})

    def stop(self): self._append({'kind':'stop'})

    def close(self):
        if self._closed: return
        self._closed=True
        if self._file is not None: self._file.close()
        if self._lock is not None: self._lock.close()

    def __enter__(self): return self
    def __exit__(self,*_): self.close()
