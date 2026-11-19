"""Phase 17AA: retained resource-journal admission, completion and stop protocol.

An independent bounded replay derives every state from the complete four N
journals. Existing replay results and profile reports are comparison targets.
The successful reservations/results bind the actual 153 Z work images. Hashes
are recomputed here, but SHA computation, capture, locking, persistence and
physical execution remain external to the new Lean protocol certificate.
No ledger is opened for writing and no operation, worker or challenge is run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import evaluation_trace as previous
from . import resource_ledger as existing
from .controller import FIXED_VERIFIER
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha

BASE = 'd4d9cde8da7d2dc48c15a9dfc70f6c14d72bee55'
SCHEMA = 'rcp-rclm.phase17aa.resource-protocol-packet.v1'
POLICY = 'phase17aa.selected-resource-journal-protocol-and-work-binding.v1'
Z_ROOT = 'artifacts/development/phase17z/op-5df2585d1f4b'
Z_EXECUTION = Z_ROOT + '/gate/execution.json'
Z_EXECUTION_SHA = '047d02c257ec5db357c379d9060d0df6e224d9030bd1f8e613681142b0e2c672'
Z_PACKET = Z_ROOT + '/gate/packet.json'
Z_PACKET_SHA = 'db767e3f3134dc3a021629eda42ba2214426b1f072e28ebe9cc8b24dc759553f'
Z_SOURCE = Z_ROOT + '/gate/EvaluationTrace.lean'
Z_SOURCE_SHA = 'c3fa8765b14b214b1c3b49f9aada2a0cd25ccac31742ea4084c7ff902d0a0394'
RETAINED_Z_PINS = {
    Z_EXECUTION: Z_EXECUTION_SHA, Z_PACKET: Z_PACKET_SHA, Z_SOURCE: Z_SOURCE_SHA,
    Z_ROOT + '/operator-validation.json':
        'fc1636a68f380bce4f2982364a1571880e7784a85436801c6585818fb073599b',
}
N_ROOT = 'artifacts/development/phase17n/op-2a7186e3590f/gate'
JOURNALS = (
    ('success', 'resource-journal.jsonl', 'profile.json',
     '13eaa10744643e58a5cf44c433a8d0417f8183721199fb2fec2578effa47aa7a'),
    ('failed', 'failed-work.jsonl', 'failed-profile.json',
     'e14bc07a30a2e4685b39db9ef86532836ea1e1f2d35032671870516c2fc477a7'),
    ('exhausted', 'exhausted-work.jsonl', 'exhausted-profile.json',
     '2f9591786536c02efd2bdea4374d7be861388540c6dd605defa13a015886b047'),
    ('interrupted', 'interrupted-work.jsonl', 'interrupted-profile.json',
     '09814728ac0594ec021d656282e3d9718b77db2190ab009853b97e196f3862b1'),
)
RETAINED_N_PINS = {
    N_ROOT + '/resource-journal.jsonl': 'aa20e37afa57295bb094c5ad7cd093cfb922f189dc0f0d1ef060a6d696f794b5',
    N_ROOT + '/profile.json': '76c680f3d9b71a78a1afabad1e52b2113a9c65cf8fa14d1126d327b85d57e864',
    N_ROOT + '/failed-work.jsonl': '9d2bf36745ef767122f5079693f1abdf67bac9a700b9a3e2690eb262b89d8de7',
    N_ROOT + '/failed-profile.json': '2cf04cd261f364c45d31213033eea6ffc53ee27a757dc682e06f9620c8342654',
    N_ROOT + '/exhausted-work.jsonl': 'd17580dbce0cb462a6c4a8c47172e7e163a4e0b57f2adb7788e536940d437892',
    N_ROOT + '/exhausted-profile.json': 'f8d22b3a5109a72d5424fb538d1e3d68dfc693944b574c1db78a616eed29687b',
    N_ROOT + '/interrupted-work.jsonl': 'fc3ac44217ca1e232eeadc8d4a9d39ebeb82985b40d67c7efb0d1ffe59c569cd',
    N_ROOT + '/interrupted-profile.json': '1f305cd896ad33ae046cabcbccabda21aae68e25191f172803ec1a3d81f879b2',
}
MAX_BYTES = 40 * 1024 * 1024
MAX_JOURNAL_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 4096
MAX_EVENT_BYTES = 4096
MAX_NAT = (1 << 63) - 1
ZERO = '0' * 64
EVENT_DOMAIN = b'RCPRCLM-PHASE17N-EVENT-V1\0'
LEDGER_SCHEMA = 'runtime.v5.phase17.resource-ledger.v1'
LEDGER_PROFILE = 'phase17n.bounded-vector-reference-work.v1'
DIMENSIONS = ('candidate_attempts', 'vector_calls', 'input_values', 'output_values')
WEIGHTS = (64, 16, 1, 1)
TARIFFS = {'candidate': (1, 0, 0, 0), 'vector': (0, 1, 4, 4)}
BINDING_FIELDS = {'predecessor_package_hash', 'candidate_package_hash', 'transcript_sha256', 'fixed_verifier_hash'}
PROFILE = {
    'journals': ['success', 'failed', 'exhausted', 'interrupted'],
    'event_counts': [308, 3, 2, 3], 'journal_bytes': [120790, 1541, 1186, 1533],
    'total_events': 316, 'total_journal_bytes': 125050,
    'selected_operations': 153, 'selected_candidate_admissions': 9,
    'selected_vector_calls': 144, 'dimensions': list(DIMENSIONS), 'weights': list(WEIGHTS),
    'maximum_natural': MAX_NAT, 'event_sha_domain_hex': EVENT_DOMAIN.hex(),
    'input_origin': 'four exact retained N journals and completed Z selected work images',
    'formal_target': 'bounded journal transition protocol, complete selected trace and actual Z work linkage',
}
SCOPE = {
    'domain': 'four retained resource journals and their selected Z work binding',
    'resource_journal_protocol_checked': True, 'resource_journal_work_binding_checked': True,
    'evaluator_outputs_from_opening_checked': True, 'producer_verdict_prefix_checked': True,
    'selected_resource_kind_schedule_checked': True, 'selected_objective_policy_checked': True,
    'selected_objective_challenge_binding_checked': True, 'historical_fixture_only': True,
    'byte_capture_remains_external': True, 'contextual_digest_authenticity_remains_external': True,
    'response_and_resource_journal_hash_computation_remains_external': True,
    'physical_journal_persistence_remains_external': True,
    'physical_locking_remains_external': True,
    'external_head_authenticity_remains_external': True, 'python_execution_remains_external': True,
    'secret_generation_and_freshness_remain_external': True, 'challenge_secrecy_remains_external': True,
    'evaluator_independence_remains_external': True, 'temporal_freeze_order_remains_external': True,
    'interruption_fixture_is_simulation': True, 'general_resource_ledger_equivalence': False,
    'general_evaluator_equivalence': False, 'general_json_parser_equivalence': False,
    'general_sha256_equivalence': False, 'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True, 'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False, 'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('AA selected resource-journal reconstruction and proof checking', *previous.UNMEASURED[1:])


def exact(value: object, keys: set[str]) -> dict:
    require(type(value) is dict and set(value) == keys, 'exact resource protocol fields required')
    return value


def natural(value: object) -> int:
    require(type(value) is int and 0 <= value <= MAX_NAT, 'bounded exact natural required')
    return value


def digest(value: object) -> str:
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None,
            'canonical resource digest required')
    return value


def vector(value: object) -> list[int]:
    require(type(value) is list and len(value) == 4, 'four exact resource dimensions required')
    return [natural(x) for x in value]


def weighted(values: object) -> int:
    return natural(sum(w * x for w, x in zip(WEIGHTS, vector(values), strict=True)))


def checked_policy(value: object) -> dict:
    p = exact(value, {'profile', 'dimensions', 'weights', 'limits', 'cost_limit'})
    require(p['profile'] == LEDGER_PROFILE and type(p['dimensions']) is list and
            p['dimensions'] == list(DIMENSIONS), 'fixed resource profile/dimensions required')
    require(type(p['weights']) is list and len(p['weights']) == 4 and
            [natural(x) for x in p['weights']] == list(WEIGHTS), 'fixed resource weights required')
    vector(p['limits']); weighted(p['limits']); natural(p['cost_limit'])
    return load_json_strict(canonical(p))


def checked_binding(value: object) -> dict:
    return {key: digest(item) for key, item in exact(value, BINDING_FIELDS).items()}


def fits(policy: dict, values: list[int]) -> bool:
    # Match the existing dimension-first check. If every dimension fits, the
    # validated policy's weighted limit already bounds the conversion arithmetic.
    return all(x <= y for x, y in zip(values, policy['limits'], strict=True)) and weighted(values) <= policy['cost_limit']


def image_bytes(value: object, bound: int = MAX_JOURNAL_BYTES) -> bytes:
    require(type(value) is str and 0 < len(value) <= 2 * bound and len(value) % 2 == 0 and
            re.fullmatch(r'[0-9a-f]+', value) is not None, 'bounded canonical lowercase byte image required')
    return bytes.fromhex(value)


def replay_journal(raw: bytes, *, expected_head: str, policy: dict, expected_binding: dict) -> dict:
    """Independent read-only replay; no production ledger transition is called."""
    wanted_policy, wanted_binding = checked_policy(policy), checked_binding(expected_binding)
    digest(expected_head)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_JOURNAL_BYTES and raw.endswith(b'\n'),
            'complete bounded immutable journal bytes required')
    lines = raw.splitlines(keepends=True)
    require(0 < len(lines) <= MAX_EVENTS, 'resource event count bound exceeded')
    head, spent, status, pending = ZERO, [0, 0, 0, 0], 'new', None
    identities: list[str] = []
    charges: list[str] = []
    events, images, states = [], [], []
    for index, line in enumerate(lines):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n') and
                0 < len(line) - 1 <= MAX_EVENT_BYTES, 'complete bounded LF-only event required')
        row = exact(load_json_strict(line[:-1]), {'index', 'previous', 'body', 'hash'})
        require(natural(row['index']) == index and digest(row['previous']) == head,
                'resource event index or previous hash differs')
        digest(row['hash'])
        require(row['hash'] == sha(EVENT_DOMAIN + canonical({
            'index': index, 'previous': head, 'body': row['body']})), 'resource event hash differs')
        body = row['body']
        require(type(body) is dict and type(body.get('kind')) is str, 'resource event kind required')
        kind = body['kind']
        if index == 0:
            exact(body, {'kind', 'schema', 'binding', 'policy'})
            require(kind == 'open' and body['schema'] == LEDGER_SCHEMA, 'initial resource open required')
            require(checked_binding(body['binding']) == wanted_binding and
                    checked_policy(body['policy']) == wanted_policy, 'external policy or package binding differs')
            status = 'open'
        elif kind in ('reserve', 'exhausted'):
            exact(body, {'kind', 'operation', 'operation_id', 'input_sha256', 'charge'} |
                  ({'spent_after'} if kind == 'reserve' else {'reason'}))
            require(status == 'open' and pending is None, 'reservation requires open nonpending state')
            op, ident = body['operation'], body['operation_id']
            require(type(op) is str and op in TARIFFS, 'known operation kind required')
            require(type(ident) is str and re.fullmatch(r'[A-Za-z0-9:_-]{1,96}', ident) is not None,
                    'bounded ASCII operation identity required')
            require(ident not in identities, 'duplicate operation identity')
            digest(body['input_sha256'])
            charge = vector(body['charge'])
            require(charge == list(TARIFFS[op]), 'exact operation tariff required')
            proposed = [natural(a + b) for a, b in zip(spent, charge, strict=True)]
            can_reserve = fits(wanted_policy, proposed)
            if kind == 'reserve':
                require(can_reserve and vector(body['spent_after']) == proposed,
                        'reservation exceeds policy or falsifies cumulative spent')
                spent = proposed
                identities.append(ident); charges.append(op)
                pending, status = row['hash'], 'pending'
            else:
                require(not can_reserve and body['reason'] == 'declared_budget', 'false declared exhaustion')
                status = 'resource_exhausted'
        elif kind == 'result':
            exact(body, {'kind', 'reservation_hash', 'ok', 'result_sha256', 'error_code', 'elapsed_ns'})
            require(status == 'pending' and digest(body['reservation_hash']) == pending,
                    'result lacks matching pending reservation')
            require(type(body['ok']) is bool, 'exact Boolean completion required')
            natural(body['elapsed_ns'])
            if body['ok']:
                digest(body['result_sha256'])
                require(body['error_code'] is None, 'successful result contains error')
                status = 'open'
            else:
                require(body['result_sha256'] is None and
                        body['error_code'] in ('operation_failed', 'interrupted'), 'invalid failure result shape')
                status = 'safety_halt'
            pending = None
        elif kind in ('seal', 'stop'):
            exact(body, {'kind'})
            require(status == 'open' and pending is None, 'completion requires open nonpending state')
            status = 'sealed' if kind == 'seal' else 'external_stop'
        else:
            require(False, 'unknown or repeated resource event')
        head = row['hash']
        events.append(row); images.append(line[:-1].hex())
        states.append({'head': head, 'event_count': index + 1, 'spent': list(spent),
            'charged_cost': weighted(spent), 'status': status, 'pending_hash': pending,
            'operation_ids': list(identities), 'charges': list(charges)})
    require(head == expected_head, 'external retained resource head differs')
    return {'events': events, 'event_images': images, 'states': states, 'result': states[-1]}


def _compare_existing(raw: bytes, head: str, policy: dict, binding: dict, result: dict) -> None:
    reference = existing.replay(raw, expected_head=head,
        policy=existing.Policy.from_json(policy), expected_binding=binding)
    target = {'head': reference.head, 'event_count': reference.event_count,
        'spent': list(reference.spent), 'charged_cost': reference.charged_cost,
        'status': reference.status, 'pending_hash': reference.pending_hash,
        'operation_ids': list(reference.operation_ids), 'charges': list(reference.charges)}
    require(canonical(result) == canonical(target), 'independent resource replay disagrees with existing replay')


def inputs_from_retained(retained: dict[str, bytes]) -> dict:
    result = []
    for name, journal_name, profile_name, _ in JOURNALS:
        raw, profile = retained[N_ROOT + '/' + journal_name], retained[N_ROOT + '/' + profile_name]
        require(type(raw) is bytes and sha(raw) == RETAINED_N_PINS[N_ROOT + '/' + journal_name] and
                type(profile) is bytes and sha(profile) == RETAINED_N_PINS[N_ROOT + '/' + profile_name],
                'retained N journal or comparison report differs')
        result.append({'name': name, 'raw_hex': raw.hex(), 'profile_hex': profile.hex()})
    return {'journals': result}


def _small_policy(limits: list[int], cost_limit: int) -> dict:
    return {'profile': LEDGER_PROFILE, 'dimensions': list(DIMENSIONS), 'weights': list(WEIGHTS),
            'limits': limits, 'cost_limit': cost_limit}


def derive_protocol(z: dict, inputs: dict) -> dict:
    """Derive protocol states first; stored reports never supply replay outcomes."""
    exact(inputs, {'journals'})
    rows = inputs['journals']
    require(type(rows) is list and len(rows) == len(JOURNALS), 'four complete retained resource journals required')
    resource = z['evaluation']['resource']
    binding = checked_binding(resource['binding'])
    require(binding == {'predecessor_package_hash': z['bindings']['predecessor_physical_hash'],
        'candidate_package_hash': z['bindings']['candidate_physical_hash'],
        'transcript_sha256': z['bindings']['transcript_sha256'], 'fixed_verifier_hash': FIXED_VERIFIER},
        'same-candidate predecessor/verifier/transcript binding differs')
    journals = []
    for index, (row, (name, journal_name, profile_name, head)) in enumerate(zip(rows, JOURNALS, strict=True)):
        exact(row, {'name', 'raw_hex', 'profile_hex'})
        require(row['name'] == name, 'retained resource journal order differs')
        raw, report_raw = image_bytes(row['raw_hex']), image_bytes(row['profile_hex'])
        path, profile_path = N_ROOT + '/' + journal_name, N_ROOT + '/' + profile_name
        require(sha(raw) == RETAINED_N_PINS[path] and sha(report_raw) == RETAINED_N_PINS[profile_path],
                'retained resource bytes or comparison profile changed')
        policy = resource['policy'] if name == 'success' else _small_policy(
            [0, 0, 0, 0] if name == 'exhausted' else [0, 1, 4, 4], 0 if name == 'exhausted' else 24)
        replayed = replay_journal(raw, expected_head=head, policy=policy, expected_binding=binding)
        _compare_existing(raw, head, policy, binding, replayed['result'])
        report = load_json_strict(report_raw, require_canonical=False)
        require(type(report) is dict and report['journal_sha256'] == sha(raw) and
                report['journal_head'] == head and canonical(report['spent']) == canonical(replayed['result']['spent']) and
                report['status'] == replayed['result']['status'], 'retained profile differs from independent replay')
        if name != 'exhausted':
            require(type(report['charged_cost']) is int and report['charged_cost'] == replayed['result']['charged_cost'],
                    'retained profile charge differs from independent replay')
        require(len(raw) == PROFILE['journal_bytes'][index] and
                len(replayed['events']) == PROFILE['event_counts'][index], 'complete retained journal inventory differs')
        journals.append({'name': name, 'path': path, 'raw_hex': raw.hex(), 'expected_head': head,
            'binding': dict(binding), 'policy': checked_policy(policy), 'comparison_profile': report, **replayed})
    success = journals[0]
    work = []
    require(len(z['evaluation']['work']) == 153 and len(success['events']) == 308,
            'complete selected Z work and resource event inventory required')
    for index, task in enumerate(z['evaluation']['work']):
        source, output = image_bytes(task['input_hex']), image_bytes(task['output_hex'])
        require(sha(source) == task['input_sha256'] and sha(output) == task['output_sha256'],
                'selected Z work byte digest differs')
        reserve, result = success['events'][1 + 2 * index]['body'], success['events'][2 + 2 * index]['body']
        require(reserve['kind'] == 'reserve' and reserve['operation_id'] == task['identity'] and
                reserve['operation'] == task['kind'] and reserve['input_sha256'] == task['input_sha256'] and
                result['kind'] == 'result' and result['ok'] is True and result['result_sha256'] == task['output_sha256'],
                'selected resource reservation/result differs from actual Z work')
        work.append({key: task[key] for key in ('identity', 'kind', 'input_sha256', 'output_sha256')})
    result = success['result']
    require(result['status'] == 'sealed' and result['pending_hash'] is None and
            result['spent'] == resource['spent'] == [9, 144, 576, 576] and
            result['charged_cost'] == resource['charged_cost'] == 4032 and
            result['charges'] == resource['charge_sequence'] == [row['kind'] for row in work] and
            result['operation_ids'] == resource['operation_ids'] == [row['identity'] for row in work] and
            result['head'] == resource['journal_head'] and sha(bytes.fromhex(success['raw_hex'])) == resource['journal_sha256'],
            'complete selected journal outcome differs from actual Z resource premise')
    return {'journals': journals, 'work': work, 'selected_work_bound': True}


def packet_from_inputs(z: dict, inputs: dict) -> dict:
    return {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'evaluation_trace_packet': z, 'evaluation_trace_packet_sha256': Z_PACKET_SHA,
        'bindings': z['bindings'], 'retained_z': dict(RETAINED_Z_PINS), 'retained_n': dict(RETAINED_N_PINS),
        'profile': dict(PROFILE), 'scope': dict(SCOPE), 'claims': {key: False for key in FALSE_CLAIMS},
        'inputs': inputs, 'protocol': derive_protocol(z, inputs)}


def validate_packet(packet: dict) -> previous.PreparedEvaluationTrace:
    exact(packet, {'schema', 'policy', 'base_commit', 'evaluation_trace_packet', 'evaluation_trace_packet_sha256',
        'bindings', 'retained_z', 'retained_n', 'profile', 'scope', 'claims', 'inputs', 'protocol'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'resource protocol schema/policy/base differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'resource protocol profile/scope differs')
    require(canonical(packet['claims']) == canonical({key: False for key in FALSE_CLAIMS}),
            'unsupported resource protocol authority or closure claim')
    require(canonical(packet['retained_z']) == canonical(RETAINED_Z_PINS) and
            canonical(packet['retained_n']) == canonical(RETAINED_N_PINS), 'retained Z/N anchors differ')
    z = packet['evaluation_trace_packet']; raw_z = canonical(z)
    require(sha(raw_z) == packet['evaluation_trace_packet_sha256'] == Z_PACKET_SHA,
            'actual imported Z packet differs')
    require(canonical(packet['bindings']) == canonical(z['bindings']), 'resource protocol package/program binding differs')
    expected = derive_protocol(z, packet['inputs'])
    require(canonical(packet['protocol']) == canonical(expected),
            'complete resource events, cumulative states or selected work binding differs')
    return previous.PreparedEvaluationTrace(raw_z)


@dataclass(frozen=True, slots=True)
class PreparedResourceProtocol:
    packet_bytes: bytes
    _previous: previous.PreparedEvaluationTrace = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable resource protocol packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical resource protocol packet required')
        object.__setattr__(self, '_previous', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def evaluation_trace(self) -> previous.PreparedEvaluationTrace:
        return self._previous


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in {**RETAINED_Z_PINS, **RETAINED_N_PINS}.items():
        path = root / name
        existing._no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained AA input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained AA input changed: ' + name)
        result[name] = raw
    return result


def prepare_resource_protocol(root: Path, packages: Path) -> PreparedResourceProtocol:
    retained = read_retained(root)
    inherited = previous.prepare_evaluation_trace(root, packages)
    require(inherited.packet_bytes == retained[Z_PACKET], 'fresh selected evaluation differs from completed Z')
    prepared = PreparedResourceProtocol(canonical(packet_from_inputs(inherited.packet, inputs_from_retained(retained))))
    require(retained == read_retained(root), 'retained Z/N bytes changed during resource protocol preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedResourceProtocol, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external resource protocol packet anchor differs')
    require(type(recomputed) is PreparedResourceProtocol and raw == recomputed.packet_bytes,
            'resource protocol packet differs from independent reconstruction')
    PreparedResourceProtocol(raw)


def summary(prepared: PreparedResourceProtocol) -> dict:
    require(type(prepared) is PreparedResourceProtocol, 'validated resource protocol packet required')
    packet = prepared.packet; protocol = packet['protocol']; journals = protocol['journals']
    success = journals[0]['result']
    return {'journals': len(journals), 'journal_names': [row['name'] for row in journals],
        'event_counts': [len(row['events']) for row in journals],
        'journal_bytes': [len(bytes.fromhex(row['raw_hex'])) for row in journals],
        'events': sum(len(row['events']) for row in journals),
        'total_journal_bytes': sum(len(bytes.fromhex(row['raw_hex'])) for row in journals),
        'json_images': sum(len(row['event_images']) for row in journals),
        'json_image_bytes': sum(len(bytes.fromhex(image)) for row in journals for image in row['event_images']),
        'states_checked': sum(len(row['states']) for row in journals),
        'selected_operations': len(protocol['work']), 'candidate_admissions': success['spent'][0],
        'vector_calls': success['spent'][1], 'input_values': success['spent'][2], 'output_values': success['spent'][3],
        'declared_spent': success['spent'], 'declared_cost': success['charged_cost'],
        'statuses': [row['result']['status'] for row in journals],
        'spent_by_journal': [row['result']['spent'] for row in journals],
        'charged_costs': [row['result']['charged_cost'] for row in journals],
        'resource_journal_sha256': RETAINED_N_PINS[N_ROOT + '/resource-journal.jsonl'],
        'evaluation_trace_packet_sha256': Z_PACKET_SHA, 'retained_z': dict(RETAINED_Z_PINS),
        'bindings': dict(packet['bindings']), 'fresh_worker_output_captured': False,
        'candidate_active': False, 'promotion_authorized': False}
