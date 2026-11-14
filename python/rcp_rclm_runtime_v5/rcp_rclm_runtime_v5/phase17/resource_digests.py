"""Phase 17AB: selected resource-event and work-image SHA-256 computations.

Reconstruct the exact hash inputs consumed by the imported AA event protocol,
AA work references and Z candidate admissions. Complete inputs, padding and
compression witnesses use the unchanged X integer SHA-256 equations. Hashlib
is only an independent preparation comparison. No ledger is opened for writing
and no work, challenge, compiler or promotion is run by this collector.

Whole-journal file checksums and producer-response hashes remain outside the
new formal inventory; the retained AA records keep their original attribution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import resource_protocol as previous
from . import producer_sha256 as reference
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .resource_ledger import _no_links

BASE = 'a0093cb8c25ec2ceefb0e5ad53f4719e30cb330d'
SCHEMA = 'rcp-rclm.phase17ab.resource-digests-packet.v1'
POLICY = 'phase17ab.selected-resource-event-and-work-sha256.v1'
AA_ROOT = 'artifacts/development/phase17aa/op-fd7895e86037'
AA_EXECUTION = AA_ROOT + '/gate/execution.json'
AA_EXECUTION_SHA = '82f322b12d6fef96dd7b6602badd7352c79909f459522b06378891ef72d349ff'
AA_PACKET = AA_ROOT + '/gate/packet.json'
AA_PACKET_SHA = 'cb46c31c5a2e7a1714f6aee0cf57751de1cf56c514bd4b4fbb36a0a6d8bd3ec5'
AA_SOURCE = AA_ROOT + '/gate/ResourceProtocol.lean'
AA_SOURCE_SHA = '7db8a00c44524830760dc2197d6e30b725abafa055620de3a4217fa646f4c862'
RETAINED_AA_PINS = {
    AA_EXECUTION: AA_EXECUTION_SHA, AA_PACKET: AA_PACKET_SHA, AA_SOURCE: AA_SOURCE_SHA,
    AA_ROOT + '/operator-validation.json':
        '52cab715cf453b9b85677b81c229c39f136cadf7281eac036cf975569f24ddd7',
}
MAX_BYTES = 64 * 1024 * 1024
MAX_INPUT_BYTES = 4096
EVENT_DOMAIN = b'RCPRCLM-PHASE17N-EVENT-V1\0'
GROUP_COUNTS = {'event': 316, 'work_input': 153, 'work_output': 153, 'candidate_descriptor': 9}
GROUP_BYTES = {'event': 109566, 'work_input': 51906, 'work_output': 2816, 'candidate_descriptor': 2698}
GROUP_BLOCKS = {'event': 1919, 'work_input': 881, 'work_output': 162, 'candidate_descriptor': 46}
RECORD_FIELDS = {'category', 'index', 'identity', 'journal', 'event_index',
                 'json_hex', 'preimage_hex', 'digest', 'blocks'}
PROFILE = {
    'algorithm': 'SHA-256', 'standard': 'FIPS PUB 180-4 (August 2015)',
    'word_bits': 32, 'block_bytes': 64, 'rounds_per_block': 64,
    'digest_text': '64 lowercase hexadecimal characters',
    'group_order': list(GROUP_COUNTS), 'group_counts': dict(GROUP_COUNTS),
    'group_input_bytes': dict(GROUP_BYTES), 'group_padded_blocks': dict(GROUP_BLOCKS),
    'journal_order': ['success', 'failed', 'exhausted', 'interrupted'],
    'journal_event_counts': [308, 3, 2, 3], 'event_domain_hex': EVENT_DOMAIN.hex(),
    'event_core_fields': ['body', 'index', 'previous'],
    'event_hash_field_excluded': True, 'event_lf_excluded': True,
    'input_count': 631, 'input_bytes': 166986, 'padded_block_occurrences': 3008,
    'distinct_compression_transitions': 2134, 'maximum_input_bytes': MAX_INPUT_BYTES,
    'preimage_origin': 'actual AA events and work references; actual Z candidate descriptors and admission digests',
    'formal_target': 'selected event digests, work input/output digests and candidate raw-descriptor digests',
    'whole_journal_file_checksums_in_new_inventory': False,
    'producer_response_hashes_in_new_inventory': False,
}
SCOPE = {
    'domain': '631 complete selected resource-event, work-image and candidate-descriptor hash inputs',
    'resource_event_hashes_checked': True, 'resource_work_digests_checked': True,
    'selected_candidate_admission_digests_checked': True,
    'resource_journal_protocol_checked': True, 'resource_journal_work_binding_checked': True,
    'evaluator_outputs_from_opening_checked': True, 'producer_verdict_prefix_checked': True,
    'whole_journal_file_hash_computation_remains_external': True,
    'producer_response_hash_computation_remains_external': True,
    'byte_capture_remains_external': True, 'contextual_digest_authenticity_remains_external': True,
    'sha256_collision_resistance_remains_external': True,
    'physical_journal_persistence_remains_external': True, 'physical_locking_remains_external': True,
    'external_head_authenticity_remains_external': True, 'python_execution_remains_external': True,
    'secret_generation_and_freshness_remain_external': True, 'challenge_secrecy_remains_external': True,
    'evaluator_independence_remains_external': True, 'temporal_freeze_order_remains_external': True,
    'objective_policy_succession_remains_external': True,
    'historical_fixture_only': True, 'interruption_fixture_is_simulation': True,
    'general_resource_ledger_equivalence': False, 'general_evaluator_equivalence': False,
    'general_json_parser_equivalence': False, 'general_sha256_equivalence': False,
    'general_planner_equivalence': False, 'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True, 'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False, 'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('AB selected resource-event/work digest reconstruction and proof checking',
              *previous.UNMEASURED[1:])


def detached(value):
    return load_json_strict(canonical(value))


def image_bytes(value: object) -> bytes:
    return previous.image_bytes(value, bound=MAX_INPUT_BYTES)


def event_preimage(event: dict) -> tuple[bytes, bytes]:
    """Canonical event core, including index/previous/body, excluding hash/LF."""
    previous.exact(event, {'index', 'previous', 'body', 'hash'})
    previous.natural(event['index'])
    previous.digest(event['previous']); previous.digest(event['hash'])
    require(type(event['body']) is dict, 'exact event body object required')
    core = canonical({'body': event['body'], 'index': event['index'], 'previous': event['previous']})
    raw = EVENT_DOMAIN + core
    require(0 < len(core) and len(raw) <= MAX_INPUT_BYTES, 'bounded complete event preimage required')
    return core, raw


def _target(category: str, index: int, identity: str, image: bytes, raw: bytes,
            expected: str, *, journal=None, event_index=None) -> dict:
    require(type(image) is bytes and type(raw) is bytes and
            0 < len(image) <= MAX_INPUT_BYTES and 0 < len(raw) <= MAX_INPUT_BYTES,
            'bounded complete selected digest input required')
    require(type(identity) is str and identity, 'selected digest identity required')
    require(sha(raw) == previous.digest(expected), 'selected input differs from captured digest')
    return {'category': category, 'index': index, 'identity': identity, 'journal': journal,
            'event_index': event_index, 'json_hex': image.hex(), 'preimage_hex': raw.hex(),
            'digest': expected}


def selected_inputs(aa: dict) -> list[dict]:
    """Reconstruct all inputs from the exact imported packet, not supplied traces."""
    require(type(aa) is dict and sha(canonical(aa)) == AA_PACKET_SHA,
            'actual imported AA packet differs')
    protocol, z = aa['protocol'], aa['evaluation_trace_packet']['evaluation']
    require([j['name'] for j in protocol['journals']] == PROFILE['journal_order'] and
            [len(j['events']) for j in protocol['journals']] == PROFILE['journal_event_counts'],
            'complete imported AA journal/event inventory differs')
    rows = []
    index = 0
    for journal in protocol['journals']:
        for event_index, event in enumerate(journal['events']):
            require(event['index'] == event_index, 'captured resource index differs from its position')
            image, raw = event_preimage(event)
            rows.append(_target('event', index, journal['name'] + ':' + str(event_index),
                image, raw, event['hash'], journal=journal['name'], event_index=event_index))
            index += 1
    work = z['work']
    require(len(work) == 153 and len(protocol['work']) == 153,
            'complete selected AA/Z work inventory required')
    for category, field in (('work_input', 'input'), ('work_output', 'output')):
        for index, (task, bound) in enumerate(zip(work, protocol['work'], strict=True)):
            require(task['identity'] == bound['identity'] and task['kind'] == bound['kind'] and
                    task[field + '_sha256'] == bound[field + '_sha256'],
                    'actual AA work reference differs from Z work image')
            raw = image_bytes(task[field + '_hex'])
            rows.append(_target(category, index, task['identity'], raw, raw, task[field + '_sha256']))
    admissions = [task for task in work if task['kind'] == 'candidate']
    require(len(admissions) == len(z['candidate_programs']) == 9,
            'complete candidate raw-descriptor inventory required')
    for index, (task, candidate) in enumerate(zip(admissions, z['candidate_programs'], strict=True)):
        source, result = load_json_strict(image_bytes(task['input_hex'])), load_json_strict(image_bytes(task['output_hex']))
        previous.exact(source, {'program'}); previous.exact(result, {'program_sha256'})
        require(task['identity'] == 'candidate:' + str(index) and
                canonical(source['program']) == canonical(candidate['program']),
                'candidate raw descriptor differs from actual Z admission')
        raw = canonical(candidate['program'])
        rows.append(_target('candidate_descriptor', index, task['identity'], raw, raw, result['program_sha256']))
    for category, count in GROUP_COUNTS.items():
        selected = [row for row in rows if row['category'] == category]
        require(len(selected) == count and [row['index'] for row in selected] == list(range(count)) and
                sum(len(bytes.fromhex(row['preimage_hex'])) for row in selected) == GROUP_BYTES[category],
                'complete selected digest group inventory differs')
    require(len(rows) == 631, 'complete 631-input digest inventory required')
    return rows


def compression_inventory(records: list[dict]) -> tuple[list[dict], list[list[int]]]:
    """Deduplicate exact incoming-state/block transitions, preserving all paths."""
    keys, unique, paths = {}, [], []
    for record in records:
        path = []
        for block in record['blocks']:
            key = (tuple(block['input_state']), block['block_hex'])
            if key not in keys:
                keys[key] = len(unique)
                unique.append(block)
            else:
                require(block == unique[keys[key]], 'shared compression witness differs')
            path.append(keys[key])
        paths.append(path)
    return unique, paths


def selected_records(aa: dict) -> list[dict]:
    records = []
    for target in selected_inputs(aa):
        raw = image_bytes(target['preimage_hex'])
        require(reference.sha256_hex(raw) == target['digest'],
                'independent SHA-256 differs from actual selected digest')
        records.append({**target, 'blocks': reference.compression_trace(raw)})
    _inventory_counts(records)
    return records


def _inventory_counts(records: list[dict]) -> None:
    blocks, paths = compression_inventory(records)
    require(len(blocks) == 2134 and sum(map(len, paths)) == 3008,
            'complete selected AB compression inventory differs')
    for category in GROUP_COUNTS:
        require(sum(len(row['blocks']) for row in records if row['category'] == category) == GROUP_BLOCKS[category],
                'selected digest group padded-block inventory differs')


def validate_record(record: dict, target: dict) -> None:
    """Reject rehashed substitutions before accepting any arithmetic witness."""
    previous.exact(record, RECORD_FIELDS)
    require(type(record['index']) is int and record['index'] >= 0,
            'exact nonnegative digest group index required')
    require(record['event_index'] is None or type(record['event_index']) is int and record['event_index'] >= 0,
            'exact event position required')
    supplied = {name: record[name] for name in RECORD_FIELDS if name != 'blocks'}
    require(canonical(supplied) == canonical(target),
            'selected digest input identity, order, preimage or captured digest differs')
    raw = image_bytes(record['preimage_hex'])
    require(sha(raw) == record['digest'], 'library SHA-256 differs from actual selected digest')
    reference.validate_trace(raw, record['blocks'], record['digest'])


def validate_hash_records(records: list[dict], aa: dict) -> None:
    require(type(records) is list and len(records) == 631, 'complete ordered 631-record SHA inventory required')
    targets = selected_inputs(aa)
    for record, target in zip(records, targets, strict=True):
        validate_record(record, target)
    _inventory_counts(records)


def packet_from_inputs(aa: dict) -> dict:
    records = selected_records(aa)
    return {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'resource_protocol_packet': detached(aa), 'resource_protocol_packet_sha256': AA_PACKET_SHA,
        'bindings': detached(aa['bindings']), 'retained_aa': dict(RETAINED_AA_PINS),
        'profile': detached(PROFILE), 'scope': detached(SCOPE),
        'claims': {name: False for name in FALSE_CLAIMS}, 'hash_records': records}


def validate_packet(packet: dict) -> previous.PreparedResourceProtocol:
    previous.exact(packet, {'schema', 'policy', 'base_commit', 'resource_protocol_packet',
        'resource_protocol_packet_sha256', 'bindings', 'retained_aa', 'profile', 'scope', 'claims', 'hash_records'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'resource digest schema/policy/base differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'resource digest profile/scope differs')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported resource digest authority or closure claim')
    require(canonical(packet['retained_aa']) == canonical(RETAINED_AA_PINS), 'retained AA anchors differ')
    aa = packet['resource_protocol_packet']; raw_aa = canonical(aa)
    require(sha(raw_aa) == packet['resource_protocol_packet_sha256'] == AA_PACKET_SHA,
            'actual imported AA packet differs')
    require(canonical(packet['bindings']) == canonical(aa['bindings']),
            'resource digest package/program binding differs')
    validate_hash_records(packet['hash_records'], aa)
    return previous.PreparedResourceProtocol(raw_aa)


@dataclass(frozen=True, slots=True)
class PreparedResourceDigests:
    packet_bytes: bytes
    _previous: previous.PreparedResourceProtocol = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable resource digest packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical resource digest packet required')
        object.__setattr__(self, '_previous', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def resource_protocol(self) -> previous.PreparedResourceProtocol:
        return self._previous


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_AA_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= previous.MAX_BYTES,
                'missing/oversized retained AB input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained AB input changed: ' + name)
        result[name] = raw
    return result


def prepare_resource_digests(root: Path, packages: Path) -> PreparedResourceDigests:
    retained = read_retained(root)
    inherited = previous.prepare_resource_protocol(root, packages)
    require(inherited.packet_bytes == retained[AA_PACKET], 'fresh selected resource protocol differs from completed AA')
    prepared = PreparedResourceDigests(canonical(packet_from_inputs(inherited.packet)))
    require(retained == read_retained(root), 'retained AA inputs changed during digest preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedResourceDigests, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == previous.digest(expected_sha256),
            'external resource digest packet anchor differs')
    require(type(recomputed) is PreparedResourceDigests and raw == recomputed.packet_bytes,
            'resource digest packet differs from independent reconstruction')
    PreparedResourceDigests(raw)


def summary(prepared: PreparedResourceDigests) -> dict:
    require(type(prepared) is PreparedResourceDigests, 'validated resource digest packet required')
    packet = prepared.packet
    rows = packet['hash_records']; blocks, paths = compression_inventory(rows)
    return {'inputs': len(rows), 'input_bytes': sum(len(bytes.fromhex(r['preimage_hex'])) for r in rows),
        'groups': dict(GROUP_COUNTS), 'group_input_bytes': dict(GROUP_BYTES),
        'padded_block_occurrences': sum(map(len, paths)), 'distinct_compression_transitions': len(blocks),
        'event_domain_hex': EVENT_DOMAIN.hex(), 'events': 316, 'work_operations': 153,
        'candidate_descriptors': 9, 'resource_protocol_packet_sha256': AA_PACKET_SHA,
        'retained_aa': dict(RETAINED_AA_PINS), 'bindings': detached(packet['bindings']),
        'whole_journal_file_hash_computation_remains_external': True,
        'producer_response_hash_computation_remains_external': True,
        'fresh_worker_output_captured': False, 'candidate_active': False, 'promotion_authorized': False}
