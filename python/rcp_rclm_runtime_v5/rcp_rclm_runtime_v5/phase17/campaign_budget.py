"""Phase 17O: externally anchored, single-writer campaign reservation authority.

A session's full bounded-vector envelope is durably charged BEFORE worker launch.
Unused and failed reservations are never refunded. This is a trusted local
coordinator, not an OS sandbox, an anti-rollback service, or physical metering.
A pathname and a hash do not create new budget authority. Creation is explicit;
reopening requires the operator's independent context, policy, and expected head.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

from rcp_rclm_runtime.canonical.json import load_json_strict
from .controller import FIXED_VERIFIER
from .resource_ledger import (
    Policy, ResourceError, ResourceExhausted, ZERO, add, canonical, cost, digest,
    exact, full_grammar_policy, nat, require, sha, vector, _no_links,
)

SCHEMA = 'runtime.v5.phase17.campaign-reservations.v1'
GRANT_SCHEMA = 'runtime.v5.phase17.worker-grant.v1'
MAX_BYTES = 8 * 1024 * 1024
MAX_EVENTS = 2048
MAX_EVENT_BYTES = 16384
CONTEXT_FIELDS = {'campaign_id', 'predecessor_state_hash', 'predecessor_package_hash',
                  'fixed_verifier_hash', 'installed_count'}


def context(value: object) -> dict:
    obj = exact(value, CONTEXT_FIELDS)
    result = {k: digest(obj[k]) for k in CONTEXT_FIELDS - {'installed_count'}}
    count = nat(obj['installed_count'])
    require(count <= 1024, 'installed inventory exceeds declared profile')
    require(result['fixed_verifier_hash'] == FIXED_VERIFIER, 'fixed verifier changed')
    result['installed_count'] = count
    return result


def parse(raw: bytes) -> dict:
    require(type(raw) is bytes and 0 < len(raw) <= MAX_EVENT_BYTES, 'campaign record size')
    try:
        value = load_json_strict(raw)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ResourceError('invalid canonical campaign record') from exc
    require(type(value) is dict and canonical(value) == raw, 'noncanonical campaign record')
    return value


def make_grant(ctx: dict, session_index: int, previous: str, freeze_hash: str,
               candidate_credits: int) -> dict:
    ctx = context(ctx)
    require(nat(candidate_credits) <= 32, 'candidate credits exceed fixed grammar')
    envelope = full_grammar_policy(ctx['installed_count'], candidate_limit=candidate_credits)
    core = {'schema': GRANT_SCHEMA, 'context': ctx, 'session_index': nat(session_index),
            'previous_campaign_head': digest(previous), 'objective_freeze_hash': digest(freeze_hash),
            'candidate_credits': candidate_credits, 'envelope': envelope.to_json()}
    return {**core, 'grant_hash': sha(b'RCPRCLM-PHASE17O-GRANT-V1\0' + canonical(core))}


def validate_grant(value: object) -> dict:
    obj = exact(value, {'schema', 'context', 'session_index', 'previous_campaign_head',
                       'objective_freeze_hash', 'candidate_credits', 'envelope', 'grant_hash'})
    wanted = make_grant(obj['context'], obj['session_index'], obj['previous_campaign_head'],
                        obj['objective_freeze_hash'], obj['candidate_credits'])
    # Compare canonical bytes, not Python equality (True must not equal 1).
    require(canonical(obj) == canonical(wanted), 'worker grant content/hash mismatch')
    return wanted


def event(body: dict, index: int, previous: str) -> dict:
    core = {'index': nat(index), 'previous': digest(previous), 'body': body}
    return {**core, 'hash': sha(b'RCPRCLM-PHASE17O-CAMPAIGN-V1\0' + canonical(core))}


@dataclass(frozen=True, slots=True)
class CampaignState:
    head: str
    event_count: int
    reserved: tuple[int, int, int, int]
    session_count: int
    status: str
    pending: bytes | None
    completed: tuple[bytes, ...]
    freezes: tuple[str, ...]

    @property
    def charged_cost(self) -> int:
        return cost(self.reserved)

    @property
    def pending_grant(self) -> dict | None:
        return None if self.pending is None else load_json_strict(self.pending)


def replay(raw: bytes, *, expected_head: str, policy: Policy, expected_context: dict) -> CampaignState:
    require(type(policy) is Policy, 'exact external campaign policy required')
    ctx = context(expected_context)
    digest(expected_head)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and raw.endswith(b'\n'),
            'campaign journal missing, oversized or truncated')
    lines = raw.splitlines(keepends=True)
    require(0 < len(lines) <= MAX_EVENTS, 'campaign event capacity exceeded')
    head, reserved, status, pending = ZERO, (0, 0, 0, 0), 'new', None
    session_count = 0
    freezes: list[str] = []
    completed: list[bytes] = []
    challenges: set[str] = set()
    for index, line in enumerate(lines):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n'), 'campaign newline changed')
        row = exact(parse(line[:-1]), {'index', 'previous', 'body', 'hash'})
        require(nat(row['index']) == index and digest(row['previous']) == head, 'campaign event order')
        body = row['body']
        require(type(body) is dict, 'campaign body required')
        require(canonical(row) == canonical(event(body, index, head)), 'campaign event hash mismatch')
        kind = body.get('kind')
        if index == 0:
            exact(body, {'kind', 'schema', 'context', 'policy'})
            require(kind == 'open' and body['schema'] == SCHEMA and context(body['context']) == ctx,
                    'wrong campaign context')
            require(Policy.from_json(body['policy']) == policy, 'external campaign policy differs')
            status = 'open'
        elif kind in ('reserve', 'deny'):
            exact(body, {'kind', 'grant', 'reserved_after'} if kind == 'reserve' else {'kind', 'grant'})
            require(status == 'open' and pending is None, 'campaign not accepting a session')
            grant = validate_grant(body['grant'])
            require(grant['context'] == ctx and grant['session_index'] == session_count and
                    grant['previous_campaign_head'] == head, 'wrong campaign grant lineage')
            require(grant['objective_freeze_hash'] not in freezes, 'objective freeze already consumed')
            envelope = Policy.from_json(grant['envelope'])
            proposed = add(reserved, envelope.limits)
            if kind == 'reserve':
                require(policy.fits(proposed), 'aggregate campaign budget exceeded')
                require(vector(body['reserved_after']) == proposed, 'forged aggregate reservation')
                reserved = proposed
                session_count += 1
                freezes.append(grant['objective_freeze_hash'])
                pending = canonical(grant)
                status = 'pending'
            else:
                require(not policy.fits(proposed), 'false campaign exhaustion')
                status = 'resource_exhausted'
        elif kind == 'complete':
            exact(body, {'kind', 'grant_hash', 'transcript_sha256', 'challenge_commitment_hash',
                         'meter_head', 'worker_spent', 'terminal_action', 'candidate_evaluations'})
            require(status == 'pending' and pending is not None, 'completion without reservation')
            grant = load_json_strict(pending)
            require(digest(body['grant_hash']) == grant['grant_hash'], 'stale grant completion')
            for key in ('transcript_sha256', 'challenge_commitment_hash', 'meter_head'):
                digest(body[key])
            require(body['challenge_commitment_hash'] not in challenges, 'challenge already consumed')
            n = nat(body['candidate_evaluations'])
            require(n <= grant['candidate_credits'], 'too many candidate evaluations')
            calls = 8 * (1 + ctx['installed_count'] + n)
            require(vector(body['worker_spent']) == (n, calls, calls * 4, calls * 4),
                    'worker operation inventory differs')
            require(Policy.from_json(grant['envelope']).fits(body['worker_spent']), 'worker exceeds grant')
            terminal = body['terminal_action']
            require(terminal in ('await_root_verification', 'search_exhausted', 'resource_exhausted',
                                 'external_stop_valid_prefix', 'fail_closed_safety_halt'), 'unknown terminal')
            require(terminal != 'search_exhausted' or n == 32, 'incomplete search exhaustion')
            require(terminal != 'await_root_verification' or n > 0, 'candidate pass without evaluation')
            completed.append(canonical({'grant': grant, 'completion': body}))
            challenges.add(body['challenge_commitment_hash'])
            pending, status = None, 'open'
            # Deliberately no refund, even if a worker stopped early.
        elif kind == 'failed':
            exact(body, {'kind', 'grant_hash', 'reason'})
            require(status == 'pending' and pending is not None and
                    digest(body['grant_hash']) == load_json_strict(pending)['grant_hash'], 'stale failure')
            require(body['reason'] in ('worker_or_verification_failed', 'interrupted'), 'unsupported failure')
            pending, status = None, 'safety_halt'
        elif kind == 'stop':
            exact(body, {'kind'})
            require(status == 'open' and pending is None, 'cannot stop unresolved campaign')
            status = 'external_stop'
        else:
            raise ResourceError('unknown campaign event')
        head = row['hash']
    require(head == expected_head, 'external campaign head differs')
    return CampaignState(head, len(lines), reserved, session_count, status, pending,
                         tuple(completed), tuple(freezes))


class CampaignAuthority:
    """One external budget authority across worker lifetimes, not promotion turns.

    The parent directory and rollback-resistant expected head are external trust
    assumptions. Do not create a new authority to bypass a consumed budget.
    Successful close/reopen preserves charges; an unresolved grant must halt.
    """
    def __init__(self, path: Path, *, policy: Policy, expected_context: dict,
                 expected_head: str | None = None):
        self.path = Path(path).absolute()
        _no_links(self.path)
        require(self.path.parent.is_dir(), 'campaign parent directory must exist')
        require(type(policy) is Policy, 'exact policy required')
        self.policy = policy
        self._context = canonical(context(expected_context))
        self._raw = b''
        self._state = None
        self._closed = False
        self._poisoned = False
        self._file = None
        self._lock = None
        lock = self.path.with_name(self.path.name + '.lock')
        _no_links(lock)
        require(not lock.exists() or lock.is_file(), 'campaign lock is not a file')
        try:
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
                require(not self.path.exists(), 'existing campaign requires an external head')
                self._file = open(self.path, 'x+b', buffering=0)
                self._append_raw(event({'kind': 'open', 'schema': SCHEMA, 'context': self.context,
                                        'policy': policy.to_json()}, 0, ZERO))
            else:
                digest(expected_head)
                require(self.path.is_file(), 'campaign journal missing')
                self._file = open(self.path, 'r+b', buffering=0)
                raw = self._file.read(MAX_BYTES + 1)
                self._state = replay(raw, expected_head=expected_head, policy=policy,
                                     expected_context=self.context)
                self._raw = raw
        except BaseException:
            self.close()
            raise

    @property
    def context(self) -> dict:
        return load_json_strict(self._context)

    @property
    def state(self) -> CampaignState:
        self._check()
        return self._state

    def _check(self) -> None:
        require(not self._closed and not self._poisoned and self._file is not None,
                'closed or poisoned campaign authority')
        _no_links(self.path)
        require(stat.S_ISREG(self.path.stat().st_mode) and
                os.path.samestat(os.fstat(self._file.fileno()), self.path.stat()), 'campaign file replaced')
        self._file.seek(0)
        require(self._file.read(MAX_BYTES + 1) == self._raw, 'campaign changed externally')

    def _append_raw(self, row: dict) -> None:
        line = canonical(row) + b'\n'
        require(len(line) <= MAX_EVENT_BYTES + 1, 'campaign event too large')
        data = self._raw + line
        state = replay(data, expected_head=row['hash'], policy=self.policy, expected_context=self.context)
        try:
            self._file.seek(0, os.SEEK_END)
            require(self._file.write(line) == len(line), 'short campaign write')
            self._file.flush()
            os.fsync(self._file.fileno())
        except BaseException:
            self._poisoned = True
            raise
        self._state, self._raw = state, data

    def _append(self, body: dict) -> None:
        self._check()
        self._append_raw(event(body, self._state.event_count, self._state.head))

    def reserve(self, *, objective_freeze_hash: str, candidate_credits: int) -> dict:
        self._check()
        require(self._state.status == 'open', 'campaign not open; no automatic pending recovery')
        # Ensure space for a resolution record before authorizing any work.
        require(self._state.event_count + 2 <= MAX_EVENTS and len(self._raw) + 2 * MAX_EVENT_BYTES <= MAX_BYTES,
                'campaign journal capacity exhausted before admission')
        grant = make_grant(self.context, self._state.session_count, self._state.head,
                           objective_freeze_hash, candidate_credits)
        proposed = add(self._state.reserved, Policy.from_json(grant['envelope']).limits)
        if not self.policy.fits(proposed):
            self._append({'kind': 'deny', 'grant': grant})
            raise ResourceExhausted('campaign grant denied before worker launch')
        self._append({'kind': 'reserve', 'grant': grant, 'reserved_after': list(proposed)})
        return validate_grant(grant)

    def complete(self, predecessor, *, transcript: bytes, accounting: dict) -> dict:
        self._check()
        require(self._state.status == 'pending', 'no pending grant to complete')
        from .metered_worker import verify_metered_transcript
        grant = self._state.pending_grant
        checked = verify_metered_transcript(predecessor, grant, transcript, accounting)
        from .campaign_transaction import check_controller
        check_controller(predecessor, transcript)
        body = {'kind': 'complete', 'grant_hash': grant['grant_hash'], **checked}
        self._append(body)
        return body

    def fail(self, *, interrupted: bool = False) -> None:
        require(type(interrupted) is bool, 'Boolean interruption flag required')
        grant = self.state.pending_grant
        require(grant is not None, 'no pending grant to fail')
        self._append({'kind': 'failed', 'grant_hash': grant['grant_hash'],
                      'reason': 'interrupted' if interrupted else 'worker_or_verification_failed'})

    def stop(self) -> None:
        self._append({'kind': 'stop'})

    def journal_bytes(self) -> bytes:
        self._check()
        return self._raw

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._file is not None:
            self._file.close()
        if self._lock is not None:
            self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
