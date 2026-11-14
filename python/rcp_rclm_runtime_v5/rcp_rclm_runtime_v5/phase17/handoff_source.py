"""Phase 17P: recomputed, immutable inputs for inactive successor staging.

An O completion is evidence for an evaluation, not root acceptance. A canonical
capsule retains ALL completed sessions under an external campaign head. The
separate pinned historical fixture path never claims a live worker or campaign.
Neither capsule hashes nor this module attest physical execution.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from rcp_rclm_runtime.canonical.json import load_json_strict
from .bootstrap import HistoricalPredecessor
from .campaign_transaction import audit_campaign, check_controller, context_for
from .challenge_protocol import digest as object_hash, verify_transcript
from .resource_ledger import Policy, canonical, digest, exact, nat, require, sha

SCHEMA = 'rcp-rclm.phase17p.handoff-source.v1'
FIXTURE_SHA = '16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f'
FIXTURE_PATH = 'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json'
MAX_SOURCE_BYTES = 16 * 1024 * 1024
SESSION_NAMES = {'grant.json','objective.json','objective_freeze.json','public_challenge.json',
                 'sealed_transcript.json','worker-accounting.json','controller_checkpoint.json','session.json'}
KINDS = ('online_campaign', 'retained_synthetic_fixture')


def parse(raw: bytes) -> dict:
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SOURCE_BYTES, 'bounded immutable handoff bytes required')
    p = load_json_strict(raw)
    require(type(p) is dict and canonical(p) == raw, 'canonical handoff object required')
    return p


def unhex(value: object) -> bytes:
    require(type(value) is str and len(value) <= 2 * MAX_SOURCE_BYTES, 'bounded hex bytes required')
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError('malformed hex bytes') from exc
    require(raw.hex() == value, 'noncanonical hex bytes')
    return raw


@dataclass(frozen=True, slots=True)
class Handoff:
    source_bytes: bytes
    record_bytes: bytes
    transcript: bytes

    @property
    def record(self) -> dict:
        return load_json_strict(self.record_bytes)

    @property
    def source_hash(self) -> str:
        return sha(self.source_bytes)


def campaign_capsule(*, journal: bytes, expected_head: str, policy: Policy,
                     expected_context: dict, sessions: dict[str, dict[str, bytes]],
                     selected_grant_hash: str) -> bytes:
    """Serialize inputs, not authorize them. checked_handoff does all checks."""
    require(type(journal) is bytes and type(policy) is Policy and type(sessions) is dict,
            'exact campaign inputs required')
    require(len(sessions) <= 32, 'handoff session inventory bound exceeded')
    encoded = {}
    for key, files in sessions.items():
        digest(key); exact(files, SESSION_NAMES)
        require(all(type(v) is bytes for v in files.values()), 'immutable session bytes required')
        encoded[key] = {name: raw.hex() for name, raw in files.items()}
    raw = canonical({'schema': SCHEMA, 'kind': 'online_campaign', 'journal_hex': journal.hex(),
        'campaign_head': digest(expected_head), 'policy': policy.to_json(), 'context': expected_context,
        'selected_grant_hash': digest(selected_grant_hash), 'sessions_hex': encoded})
    parse(raw)
    return raw


def fixture_capsule(root: Path) -> bytes:
    """Development fixture only; may not enter an online-mode transition journal."""
    raw = (root / FIXTURE_PATH).read_bytes()
    require(sha(raw) == FIXTURE_SHA, 'original synthetic transcript changed')
    return canonical({'schema': SCHEMA, 'kind': 'retained_synthetic_fixture', 'transcript_hex': raw.hex()})


def checked_handoff(parent: HistoricalPredecessor, raw: bytes, *, expected_source_hash: str) -> Handoff:
    require(type(parent) is HistoricalPredecessor, 'exact historical predecessor required')
    parent.validate()
    require(sha(raw) == digest(expected_source_hash), 'external source snapshot anchor differs')
    p = parse(raw)
    require(p.get('schema') == SCHEMA and p.get('kind') in KINDS, 'unknown handoff source kind')
    campaign_head = grant_hash = None
    reserved = worker_spent = None
    if p['kind'] == 'online_campaign':
        exact(p, {'schema','kind','journal_hex','campaign_head','policy','context','selected_grant_hash','sessions_hex'})
        require(type(p['sessions_hex']) is dict and 0 < len(p['sessions_hex']) <= 32, 'bounded session inventory required')
        sessions = {}
        for key, encoded in p['sessions_hex'].items():
            digest(key); exact(encoded, SESSION_NAMES)
            sessions[key] = {name: unhex(v) for name,v in encoded.items()}
        ctx = p['context']; require(type(ctx) is dict, 'campaign context required')
        require(canonical(ctx) == canonical(context_for(parent, ctx['campaign_id'])), 'historical campaign parent differs')
        audit = audit_campaign(parent, unhex(p['journal_hex']), expected_head=p['campaign_head'],
                               policy=Policy.from_json(p['policy']), expected_context=ctx, sessions=sessions)
        require(not audit['pending_grant_retained'] and audit['status'] in ('open','resource_exhausted','external_stop'),
                'unresolved or safety-halted campaign cannot hand off')
        grant_hash = digest(p['selected_grant_hash'])
        require(grant_hash in sessions, 'selected completed grant missing')
        selected = sessions[grant_hash]
        transcript = selected['sealed_transcript.json']
        meta = load_json_strict(selected['session.json'])
        campaign_head = digest(p['campaign_head'])
        reserved, worker_spent = meta['reserved'], meta['worker_spent']
        scope = ctx['campaign_id']
    else:
        exact(p, {'schema','kind','transcript_hex'})
        transcript = unhex(p['transcript_hex'])
        require(sha(transcript) == FIXTURE_SHA, 'only the named historical fixture is admitted in fixture mode')
        scope = FIXTURE_SHA
    # This is additional producer recomputation, not trust in evaluator verdicts.
    transcript_hash = sha(transcript)
    checked = verify_transcript(parent, transcript, expected_transcript_hash=transcript_hash)
    cp = check_controller(parent, transcript)
    events = load_json_strict(transcript)['events']
    public = events[0]['response']['payload']['public_challenge']
    record = {'schema': 'rcp-rclm.phase17p.checked-handoff.v1', 'source_kind': p['kind'],
        'scope_id': scope, 'source_sha256': expected_source_hash,
        'predecessor_state_hash': object_hash(parent.state),
        'predecessor_logical_package_hash': parent.state['active_package_hash'],
        'fixed_verifier_hash': parent.state['fixed_verifier_hash'],
        'campaign_head': campaign_head, 'grant_hash': grant_hash,
        'transcript_sha256': transcript_hash,
        'challenge_commitment_hash': public['challenge_commitment_hash'],
        'objective_freeze_hash': events[0]['request']['freeze']['freeze_hash'],
        'controller_checkpoint_sha256': sha(cp), 'terminal_action': checked.terminal_action,
        'candidate_evaluations': checked.candidate_evaluations,
        'selected_candidate_hash': checked.selected_candidate_hash,
        'session_reserved': reserved, 'worker_spent': worker_spent,
        'root_acceptance_evaluated': False, 'promotion_authorized': False}
    return Handoff(raw, canonical(record), transcript)
