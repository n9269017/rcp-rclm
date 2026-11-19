"""Fixed online evaluator with bounded reference-work accounting.

The campaign precharges an entire grant before this worker exists. The worker
also enforces each operation locally. Its in-memory metering transcript is
revealed only as a final digest/counter summary after sealing. On worker loss,
that detailed trace may be unavailable; the full campaign grant stays charged.
No candidate-supplied executable, filesystem path, hidden seed, or budget policy
is accepted. Existing Phase 17C challenge semantics and transcript format remain.
"""
from __future__ import annotations

from rcp_rclm_runtime.canonical.json import load_json_strict
from .bootstrap import HistoricalPredecessor
from .campaign_budget import validate_grant
from .challenge_protocol import (
    EvaluatorSession, CLAIMS, PROTOCOL, PROBE_COUNT, digest as object_hash,
    execute_reference, parse_wire, realize_candidate, require, transcript_bytes,
    vector_semantics, verify_transcript, wire_bytes,
)
from .controller import _keys, ControlError
from .resource_ledger import Policy, TARIFFS, add, canonical, cost, sha

WORKER_PROTOCOL = 'runtime.v5.phase17.campaign-worker.v1'
METER_SCHEMA = 'runtime.v5.phase17.online-work-meter.v1'


class WorkMeter:
    """Private in-memory operation trace; durable upper charge is in the parent."""
    def __init__(self, grant: dict, challenge_commitment: str):
        from .resource_ledger import digest
        self.grant = validate_grant(grant)
        self.policy = Policy.from_json(self.grant['envelope'])
        self.commitment = digest(challenge_commitment)
        self.spent = (0, 0, 0, 0)
        self.operation_count = 0
        self.ids: set[str] = set()
        self.status = 'open'
        self.event_count = 0
        self.head = '0' * 64
        self._append({'kind': 'open', 'schema': METER_SCHEMA, 'grant_hash': self.grant['grant_hash'],
                      'challenge_commitment_hash': self.commitment})

    def _append(self, body: dict):
        self.head = sha(b'RCPRCLM-PHASE17O-METER-V1\0' + canonical({
            'previous': self.head, 'index': self.event_count, 'body': body}))
        self.event_count += 1

    def perform(self, kind: str, ident: str, inputs: dict, fixed_operation):
        require(self.status == 'open' and kind in TARIFFS and ident not in self.ids,
                'meter closed, unknown or duplicate operation')
        proposed = add(self.spent, TARIFFS[kind])
        require(self.policy.fits(proposed), 'worker work exceeds reserved grant')
        source = sha(canonical(inputs))
        self.spent = proposed
        self.operation_count += 1
        self.ids.add(ident)
        self._append({'kind': 'reserve', 'operation': kind, 'operation_id': ident,
                      'input_sha256': source, 'spent_after': list(self.spent)})
        try:
            output = fixed_operation()
            raw = canonical(output)
            require(len(raw) <= 4096, 'operation result outside fixed profile')
        except BaseException:
            self.status = 'failed'
            self._append({'kind': 'failed', 'operation_id': ident})
            raise
        self._append({'kind': 'result', 'operation_id': ident, 'output_sha256': sha(raw)})
        return load_json_strict(raw)

    def seal(self):
        require(self.status == 'open', 'meter cannot seal incomplete work')
        self._append({'kind': 'seal'})
        self.status = 'sealed'

    def summary(self) -> dict:
        require(self.status == 'sealed', 'meter evidence cannot be revealed before seal')
        return {'schema': METER_SCHEMA, 'grant_hash': self.grant['grant_hash'],
                'challenge_commitment_hash': self.commitment, 'spent': list(self.spent),
                'charged_cost': cost(self.spent), 'operation_count': self.operation_count,
                'event_count': self.event_count, 'head': self.head, 'status': self.status}


class MeteredEvaluatorSession(EvaluatorSession):
    """Same sealed evaluator responses; exhaustive fixed-work evaluation order."""
    def __init__(self, predecessor: HistoricalPredecessor, grant: dict):
        super().__init__(predecessor)
        self.grant = validate_grant(grant)
        ctx = self.grant['context']
        require(ctx['predecessor_state_hash'] == object_hash(predecessor.state) and
                ctx['predecessor_package_hash'] == predecessor.state['active_package_hash'] and
                ctx['installed_count'] == len(predecessor.accepted_programs), 'grant predecessor mismatch')
        self.meter: WorkMeter | None = None
        self.expected: list[list[int]] = []
        self.predecessor_pass = False
        self.nontrivial = False

    def _open(self, request: dict, *, replay_entropy: bytes | None = None) -> dict:
        objective, freeze = self._validate_open(request)
        require(freeze['freeze_hash'] == self.grant['objective_freeze_hash'] and
                freeze['turn_index'] == self.grant['session_index'] and
                request['candidate_credits'] == self.grant['candidate_credits'], 'request not bound to grant')
        # The inherited implementation checks freeze BEFORE its only entropy draw.
        payload = super()._open(request, replay_entropy=replay_entropy)
        self.meter = WorkMeter(self.grant, self.public['challenge_commitment_hash'])
        secret = self.secret
        for i, probe in enumerate(secret['probes']):
            inputs = {'role': 'target', 'family': secret['objective_family'],
                      'variant': secret['target_variant'], 'a': secret['target_a'],
                      'b': secret['target_b'], 'probe': probe}
            self.expected.append(self.meter.perform('vector', f'target:{i}', inputs,
                lambda x=probe: vector_semantics(secret['objective_family'], secret['target_variant'],
                                                 secret['target_a'], secret['target_b'], x)))
        self.nontrivial = any(x != y for x, y in zip(secret['probes'], self.expected, strict=True))
        # All inherited programs and all probes, even for unrelated families.
        # Fixed work counts do not reveal hidden per-probe success shortcuts.
        for j, raw in enumerate(self.parent.accepted_programs):
            program = load_json_strict(raw)
            outputs = [self.meter.perform('vector', f'inherited:{j}:{i}',
                {'role': 'inherited', 'program': program, 'probe': probe},
                lambda p=program, x=probe: execute_reference(p, x))
                for i, probe in enumerate(secret['probes'])]
            if program['family'] == secret['objective_family'] and outputs == self.expected:
                self.predecessor_pass = True
        return payload

    def _handle(self, request: dict, *, replay_entropy: bytes | None = None) -> dict:
        request = parse_wire(wire_bytes(request))
        if request.get('op') != 'evaluate':
            response = super()._handle(request, replay_entropy=replay_entropy)
            if request.get('op') == 'seal':
                require(self.meter is not None, 'missing work meter')
                self.meter.seal()
            return response
        # Mirror the inherited candidate-freeze checks before invoking any work.
        require(not self.sealed and self.opened and self.meter is not None, 'evaluator not open')
        require(request.get('protocol') == PROTOCOL, 'protocol mismatch')
        _keys(request, {'protocol', 'op', 'candidate_freeze_hash', 'artifact'}, 'evaluate')
        require(self.pending is not None, 'candidate must be frozen before evaluation')
        require(request['candidate_freeze_hash'] == self.pending['candidate_freeze_hash'], 'stale candidate freeze')
        h = self.pending['program_hash']
        artifact = realize_candidate(self.programs[h], self.freeze)
        require(type(request['artifact']) is dict and wire_bytes(request['artifact']) == wire_bytes(artifact),
                'candidate mutated after freeze')
        index = len(self.considered)
        self.meter.perform('candidate', f'admit:{index}', {'artifact_hash': artifact['artifact_hash'],
            'program_hash': h}, lambda: {'admitted': True})
        outputs = [self.meter.perform('vector', f'candidate:{index}:{i}',
                    {'role': 'candidate', 'program': self.programs[h], 'probe': probe},
                    lambda x=probe: execute_reference(self.programs[h], x))
                   for i, probe in enumerate(self.secret['probes'])]
        passed = (self.nontrivial and not self.predecessor_pass and
                  self.programs[h]['family'] == self.secret['objective_family'] and outputs == self.expected)
        payload = {'event': 'candidate_evaluated', 'program_hash': h,
                   'artifact_hash': artifact['artifact_hash'],
                   'candidate_freeze_hash': self.pending['candidate_freeze_hash'],
                   'predecessor_state_hash': self.freeze['predecessor_state_hash'],
                   'challenge_commitment_hash': self.public['challenge_commitment_hash'],
                   'evaluation_index': index, 'verdict': 'candidate_passed' if passed else 'reject',
                   'reason_codes': [] if passed else ['bounded_challenge_rejected'], 'claims': dict(CLAIMS)}
        payload['evaluation_hash'] = object_hash(payload)
        self.considered.append(h)
        self.pending = None
        if passed:
            self.passed = h
        response = {'protocol': PROTOCOL, 'sequence': len(self.events), 'request_hash': object_hash(request),
                    'previous_response_hash': self.previous, 'payload': payload}
        response['response_hash'] = object_hash(response)
        response = parse_wire(wire_bytes(response))
        self.previous = response['response_hash']
        self.events.append({'request': request, 'response': response})
        return parse_wire(wire_bytes(response))


def verify_metered_transcript(predecessor: HistoricalPredecessor, grant: dict,
                              transcript: bytes, accounting: dict) -> dict:
    """Recompute every old evaluator response and every fixed metered operation.

    This is deterministic post-seal checking, NOT physical-execution attestation,
    original-worker-independent Phase 18 closure, or a new hidden test campaign.
    """
    grant = validate_grant(grant)
    anchor = sha(transcript)
    verified = verify_transcript(predecessor, transcript, expected_transcript_hash=anchor)
    events = load_json_strict(transcript)['events']
    entropy = bytes.fromhex(events[-1]['response']['payload']['opening']['entropy_hex'])
    session = MeteredEvaluatorSession(predecessor, grant)
    for index, item in enumerate(events):
        response = session._handle(item['request'], replay_entropy=entropy if index == 0 else None)
        require(wire_bytes(response) == wire_bytes(item['response']), 'metered evaluator transcript mismatch')
    actual = session.meter.summary()
    require(type(accounting) is dict and canonical(accounting) == canonical(actual), 'worker accounting mismatch')
    require(transcript_bytes(session.events) == transcript, 'transcript format changed')
    return {'transcript_sha256': anchor, 'challenge_commitment_hash': session.public['challenge_commitment_hash'],
            'meter_head': actual['head'], 'worker_spent': actual['spent'],
            'terminal_action': verified.terminal_action, 'candidate_evaluations': verified.candidate_evaluations}
