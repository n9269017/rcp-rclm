"""Phase 17Y: selected present-only objective policy and challenge context.

Complete canonical values are reconstructed from the actual retained X/V/U
inputs and the pinned historical transcript.  The independent numerical policy
does not call the production objective selector.  SHA schedules and round
states are untrusted witnesses for Lean; library hashes are consistency checks.
No evaluator, worker, fresh entropy, active store, or promotion API is invoked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import producer_sha256 as previous
from . import producer_preimages as preimages
from .planner_refinement import producer_packet
from .bootstrap import HANDOFF_RECEIPT_HASH, WEIGHTS_SHA256, validate_state
from .controller import CurrentView, FAMILIES, FIXED_VERIFIER, SEMANTICS
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .handoff_source import FIXTURE_PATH, FIXTURE_SHA
from .resource_ledger import _no_links, digest, exact

BASE = '3582c6b591e3f392e6c2d453773b080adc036b65'
SCHEMA = 'rcp-rclm.phase17y.objective-context-packet.v1'
POLICY = 'phase17y.selected-present-only-objective-and-challenge-context.v1'
X_ROOT = 'artifacts/development/phase17x/op-7a7b55bcd9a4'
X_EXECUTION = X_ROOT + '/gate/execution.json'
X_EXECUTION_SHA = '7985aefc6a8edc8d06dd71d901700ba4cb7704b9e999c554ce032575e0c88e6b'
X_PACKET = X_ROOT + '/gate/packet.json'
X_PACKET_SHA = '38df58efe0a378fe8a83dc7e00d5a1c6d98c57f171dd0911ba56a44cca635020'
X_SOURCE = X_ROOT + '/gate/ProducerSha256.lean'
X_SOURCE_SHA = '4b50ff649923a40d235fb7e0eb45a9264b7173fc7c511271ac38bfab75486a5b'
X_AUXILIARY = X_ROOT + '/gate/Phase17XSha256Blocks.lean'
X_AUXILIARY_SHA = '38887a604212c7c54adb762fd9bab8c4572f347277e34f6de59888fd11ad10af'
RETAINED_X_PINS = {
    X_EXECUTION: X_EXECUTION_SHA, X_PACKET: X_PACKET_SHA, X_SOURCE: X_SOURCE_SHA,
    X_AUXILIARY: X_AUXILIARY_SHA,
    X_ROOT + '/operator-validation.json':
        '3c0c76d38771b4880b107252907807dcdb36e7a61ac10c27d9c1d6b84f06c7c5',
}
MAX_BYTES = 40 * 1024 * 1024
MAX_METADATA = (1 << 63) - 1
INPUTS_SHA256 = 'a31f1b36d934c44dc9a7746a2df3772aa2fd52510c93d9585df3322edd98e8eb'
OBJECTIVE_POLICY = 'phase17.inherited-projection-current-objective.v1'
OBJECTIVE_SCHEMA = 'runtime.v5.phase17.objective_decision.v1'
FREEZE_SCHEMA = 'runtime.v5.phase17.objective_freeze.v1'
CHALLENGE_POLICY = 'phase17c.independent-random-vector-spec.v1'
GROUP_COUNTS = {'historical_state': 1, 'objective_feature': 8, 'objective_tie': 8,
                'objective_decision': 1, 'objective_freeze': 1, 'challenge_commitment': 1}
INPUT_FIELDS = {'historical_state_hex', 'objective_hex', 'freeze_hex',
                'public_challenge_hex', 'secret_hex', 'candidate_credits'}
PROFILE = {
    'objective_policy': OBJECTIVE_POLICY, 'objective_schema': OBJECTIVE_SCHEMA,
    'freeze_schema': FREEZE_SCHEMA, 'challenge_policy': CHALLENGE_POLICY,
    'families': list(FAMILIES), 'objective_families': 8,
    'planner_terms_per_family': 84,
    'feature_offset': '(word_index + projection_index * 11) mod 64',
    'feature_value': '(digest_nibble + family_index * 3 + generation + projection_index) mod 9 - 4',
    'objective_score': '20000 - generation * 521 + sum(signed_word * feature_value)',
    'ordering': 'descending (score, complete tie digest, family name)',
    'hash_domain_hex': preimages.PUBLIC_HASH_DOMAIN.hex(),
    'hash_inventory': dict(GROUP_COUNTS), 'hash_record_count': 20,
    'captured_inputs_sha256': INPUTS_SHA256,
    'input_origin': 'exact retained V historical image and original sealed synthetic transcript',
    'formal_target': 'actual imported V state, U planner projection, W current view, and Q objective/challenge binding',
}
SCOPE = {
    'domain': 'selected eight-family objective policy and complete objective, freeze, state and challenge hash inputs',
    'selected_objective_policy_checked': True,
    'selected_objective_challenge_binding_checked': True,
    'selected_sha256_reference_evaluation': True,
    'historical_fixture_only': True,
    'byte_capture_remains_external': True,
    'contextual_digest_authenticity_remains_external': True,
    'secret_generation_and_freshness_remain_external': True,
    'public_nonce_is_supplied_fixture_input': True,
    'temporal_freeze_order_remains_external': True,
    'python_execution_remains_external': True,
    'general_objective_policy_equivalence': False,
    'general_json_parser_equivalence': False,
    'general_sha256_equivalence': False,
    'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True,
    'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('Y selected objective policy and challenge-context reconstruction and proof checking',
              *previous.UNMEASURED[1:])


def _integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label)
    return value


def _decode(value: object) -> dict:
    raw = preimages._hex_bytes(value, preimages.MAX_JSON_BYTES)
    obj = load_json_strict(raw)
    require(type(obj) is dict and preimages.encode_canonical(obj) == raw,
            'complete canonical selected-profile JSON object required')
    return obj


def imported_inputs(x: dict) -> tuple[dict, dict, dict]:
    """Return actual nested W, V and U inputs; callers still validate X's pin."""
    w = x['producer_preimages_packet']
    v = w['program_metadata_packet']
    u = v['planner_refinement_packet']
    return w, v, u


def inputs_from_transcript(x: dict, transcript: bytes) -> dict:
    require(type(transcript) is bytes and sha(transcript) == FIXTURE_SHA == x['bindings']['transcript_sha256'],
            'original selected transcript anchor differs')
    data = load_json_strict(transcript)
    exact(data, {'events', 'schema_id'})
    require(canonical(data) == transcript and type(data['events']) is list and len(data['events']) == 20,
            'complete canonical selected transcript required')
    first, last = data['events'][0], data['events'][-1]
    require(first['request']['op'] == 'open' and last['request']['op'] == 'seal',
            'selected transcript opening/seal order differs')
    _, v, _ = imported_inputs(x)
    before = v['registry_images']['before']['historical_state_hex']
    require(before == v['registry_images']['after']['historical_state_hex'],
            'before/after historical state images differ')
    return {
        'historical_state_hex': before,
        'objective_hex': preimages.encode_canonical(first['request']['objective']).hex(),
        'freeze_hex': preimages.encode_canonical(first['request']['freeze']).hex(),
        'public_challenge_hex': preimages.encode_canonical(first['response']['payload']['public_challenge']).hex(),
        'secret_hex': preimages.encode_canonical(last['response']['payload']['opening']).hex(),
        'candidate_credits': first['request']['candidate_credits'],
    }


def feature_value(state: dict, view: dict, family: int) -> dict:
    _integer(family, 0, 7, 'objective family index outside fixed domain')
    return {'domain': OBJECTIVE_POLICY, 'active_package_hash': state['active_package_hash'],
            'predecessor_state_hash': view['predecessor_state_hash'],
            'planner_weights_sha256': WEIGHTS_SHA256, 'turn_index': view['turn_index'],
            'public_nonce_hash': view['public_nonce_hash'], 'objective_family': FAMILIES[family],
            'capability_frontier': state['capability_frontier'],
            'recursive_productivity_frontier': state['recursive_productivity_frontier']}


def tie_value(family: int, feature_digest: str) -> dict:
    _integer(family, 0, 7, 'objective family index outside fixed domain')
    return {'policy_id': OBJECTIVE_POLICY, 'feature_hash': digest(feature_digest),
            'family': FAMILIES[family]}


def score_terms(projection: list, family: int, generation: int, feature_digest: str) -> list[int]:
    """Independent integer objective score; no production objective selector."""
    _integer(family, 0, 7, 'objective family index outside fixed domain')
    _integer(generation, 0, MAX_METADATA, 'bounded objective generation required')
    digest(feature_digest)
    require(type(projection) is list and len(projection) == 84,
            'complete 84-entry inherited planner projection required')
    terms, indices = [], []
    for j, entry in enumerate(projection):
        require(type(entry) is list and len(entry) == 2, 'exact planner index/word pair required')
        index = _integer(entry[0], 0, 32767, 'planner word index outside image')
        weight = _integer(entry[1], -32768, 32767, 'planner signed word outside int16')
        require(weight != 0 and (not indices or index > indices[-1]),
                'planner support must be nonzero, ordered, and unique')
        indices.append(index)
        char = feature_digest[(index + j * 11) % 64]
        nibble = ord(char) - (48 if char <= '9' else 87)
        feature = (nibble + family * 3 + generation + j) % 9 - 4
        terms.append(weight * feature)
    return terms


def rank_indices(rows: list[dict]) -> list[int]:
    require(type(rows) is list and len(rows) == 8, 'all eight objective rows required')
    for index, row in enumerate(rows):
        require(type(row) is dict and type(row.get('family_index')) is int and
                row['family_index'] == index and row.get('family') == FAMILIES[index],
                'objective rows must follow the complete fixed family order')
        _integer(row.get('score'), -(1 << 63), MAX_METADATA, 'bounded objective score required')
        digest(row.get('tie_digest'))
    return sorted(range(8), key=lambda i: (rows[i]['score'], rows[i]['tie_digest'], rows[i]['family']), reverse=True)


def _hash_record(category: str, index: int, value: dict, expected: str | None = None,
                 *, with_trace: bool = True) -> dict:
    raw = preimages.encode_canonical(value)
    image = preimages.PUBLIC_HASH_DOMAIN + raw
    output = previous.sha256_hex(image)
    require(output == sha(image), 'independent objective SHA-256 disagrees with hashlib')
    if expected is not None:
        require(output == digest(expected), 'selected objective context digest differs from imported binding')
    record = {'category': category, 'index': index, 'json_hex': raw.hex(),
              'preimage_hex': image.hex(), 'digest': output}
    if with_trace:
        record['blocks'] = previous.compression_trace(image)
    return record


def derive_objective(x: dict, inputs: dict, *, with_traces: bool = True) -> dict:
    """Derive every selected row, complete JSON value, and hash from fixed inputs.

    The supplied objective/freeze are comparison targets only. Their rows and
    claimed winner do not enter the feature construction or ordering.
    """
    exact(inputs, INPUT_FIELDS)
    w, v, u = imported_inputs(x)
    view = CurrentView.from_json(w['producer']['current_view']).to_json()
    state = validate_state(_decode(inputs['historical_state_hex']))
    require(inputs['historical_state_hex'] == v['registry_images']['before']['historical_state_hex'] ==
            v['registry_images']['after']['historical_state_hex'],
            'historical state image differs from actual imported V inputs')
    require(state['active_package_hash'] == view['active_package_hash'] and
            state['fixed_verifier_hash'] == view['fixed_verifier_hash'] == FIXED_VERIFIER and
            state['semantics_id'] == view['semantics_id'] == SEMANTICS and
            [state['component_generations'][family] for family in FAMILIES] == view['family_counts'],
            'historical state does not supply actual imported current context')
    _integer(view['turn_index'], 0, MAX_METADATA, 'bounded current turn required')
    credits = _integer(inputs['candidate_credits'], 0, 32, 'bounded candidate credits required')
    trace = producer_packet(u)['trace']
    require(credits == trace['initial_credits'], 'candidate credits differ from actual imported Q context')
    supplied_objective, supplied_freeze = _decode(inputs['objective_hex']), _decode(inputs['freeze_hex'])
    public, secret = _decode(inputs['public_challenge_hex']), _decode(inputs['secret_hex'])
    exact(secret, {'entropy_hex', 'objective_family', 'target_variant', 'target_a', 'target_b', 'probes'})
    digest(secret['entropy_hex'])
    require(secret['objective_family'] in FAMILIES, 'unknown supplied opening family')
    _integer(secret['target_variant'], 0, 3, 'opening target variant outside fixed domain')
    for key in ('target_a', 'target_b'):
        _integer(secret[key], -16, 16, 'opening parameter outside declared domain')
    require(type(secret['probes']) is list and len(secret['probes']) == 8, 'eight complete opening probes required')
    for probe in secret['probes']:
        require(type(probe) is list and len(probe) == 4, 'complete four-integer opening vector required')
        for value in probe:
            _integer(value, -32, 32, 'opening probe value outside declared domain')
    require(u['before']['nonzero_words'] == u['after']['nonzero_words'],
            'before/after planner projection differs')
    projection = u['before']['nonzero_words']
    state_record = _hash_record('historical_state', 0, state, view['predecessor_state_hash'], with_trace=with_traces)
    require(state_record['digest'] == x['bindings']['historical_state_hash'],
            'historical state digest differs from actual Q binding')
    features, ties, rows = [], [], []
    for family in range(8):
        generation = _integer(state['component_generations'][FAMILIES[family]], 0, MAX_METADATA,
                              'bounded historical family generation required')
        feature = _hash_record('objective_feature', family, feature_value(state, view, family), with_trace=with_traces)
        tie = _hash_record('objective_tie', family, tie_value(family, feature['digest']), with_trace=with_traces)
        terms = score_terms(projection, family, generation, feature['digest'])
        projection_score = sum(terms)
        rows.append({'family_index': family, 'family': FAMILIES[family], 'generation': generation,
                     'projection_score': projection_score, 'score': 20000 - generation * 521 + projection_score,
                     'feature_digest': feature['digest'], 'tie_digest': tie['digest'], 'terms': terms})
        features.append(feature)
        ties.append(tie)
    order = rank_indices(rows)
    ranked = [{'family': rows[index]['family'], 'generation': rows[index]['generation'],
               'inherited_projection_score': rows[index]['projection_score'], 'score': rows[index]['score'],
               'tie_break': rows[index]['tie_digest']} for index in order]
    objective = {'schema_id': OBJECTIVE_SCHEMA, 'policy_id': OBJECTIVE_POLICY,
                 'bootstrap_report_hash': HANDOFF_RECEIPT_HASH,
                 'predecessor_state_hash': state_record['digest'], 'active_package_hash': state['active_package_hash'],
                 'planner_weights_sha256': WEIGHTS_SHA256, 'turn_index': view['turn_index'],
                 'public_nonce_hash': view['public_nonce_hash'], 'ranked_objectives': ranked,
                 'objective_family': ranked[0]['family'], 'goal': 'extend_verified_capability_frontier',
                 'fixed_verifier_hash': FIXED_VERIFIER, 'semantics_id': SEMANTICS, 'promotion_authorized': False}
    require(canonical(supplied_objective) == canonical(objective),
            'complete captured objective differs from independently derived policy')
    objective_record = _hash_record('objective_decision', 0, objective, x['bindings']['objective_hash'],
                                   with_trace=with_traces)
    freeze_body = {'schema_id': FREEZE_SCHEMA, 'objective_decision_hash': objective_record['digest'],
                   'predecessor_state_hash': state_record['digest'], 'active_package_hash': state['active_package_hash'],
                   'turn_index': view['turn_index'], 'public_nonce_hash': view['public_nonce_hash'],
                   'fixed_verifier_hash': FIXED_VERIFIER, 'semantics_id': SEMANTICS,
                   'challenge_bound': False, 'promotion_authorized': False}
    freeze_record = _hash_record('objective_freeze', 0, freeze_body, supplied_freeze.get('freeze_hash'),
                                with_trace=with_traces)
    freeze = {**freeze_body, 'freeze_hash': freeze_record['digest']}
    require(canonical(supplied_freeze) == canonical(freeze), 'complete captured objective freeze differs')
    require(secret['objective_family'] == objective['objective_family'], 'sealed opening objective family differs')
    challenge_value = {'policy': CHALLENGE_POLICY, 'freeze': freeze, 'credits': credits, 'secret': secret}
    challenge_record = _hash_record('challenge_commitment', 0, challenge_value,
                                   view['challenge_commitment_hash'], with_trace=with_traces)
    require(challenge_record['digest'] == x['bindings']['challenge_commitment_hash'],
            'challenge digest differs from actual Q binding')
    exact(public, {'policy_id', 'objective_freeze_hash', 'predecessor_state_hash', 'active_package_hash',
                   'turn_index', 'public_nonce_hash', 'objective_family', 'candidate_credits', 'probe_count',
                   'grammar_hash', 'challenge_commitment_hash', 'domain', 'successor_availability_assumed'})
    expected_public = {'policy_id': CHALLENGE_POLICY, 'objective_freeze_hash': freeze_record['digest'],
                       'predecessor_state_hash': state_record['digest'], 'active_package_hash': state['active_package_hash'],
                       'turn_index': view['turn_index'], 'public_nonce_hash': view['public_nonce_hash'],
                       'objective_family': objective['objective_family'], 'candidate_credits': credits, 'probe_count': 8,
                       'grammar_hash': digest(trace['grammar_hash']),
                       'challenge_commitment_hash': challenge_record['digest'],
                       'domain': 'bounded_four_integer_vector_dsl', 'successor_availability_assumed': False}
    require(canonical(public) == canonical(expected_public), 'captured public challenge/context binding differs')
    return {'objective_rows': rows, 'ranked_indices': order,
            'hash_records': [state_record, *features, *ties, objective_record, freeze_record, challenge_record]}


def validate_hash_records(records: list[dict], expected: list[dict]) -> None:
    require(type(records) is list and len(records) == len(expected) == 20,
            'complete 20-record objective context hash inventory required')
    for record, target in zip(records, expected, strict=True):
        exact(record, {'category', 'index', 'json_hex', 'preimage_hex', 'digest', 'blocks'})
        require(type(record['index']) is int and
                canonical({key: value for key, value in record.items() if key != 'blocks'}) == canonical(target),
                'objective hash input, category/order, or target digest differs')
        raw = preimages._hex_bytes(record['preimage_hex'], previous.MAX_IMAGE_BYTES)
        previous.validate_trace(raw, record['blocks'], record['digest'])


def validate_packet(packet: dict) -> previous.PreparedProducerSha256:
    exact(packet, {'schema', 'policy', 'base_commit', 'producer_sha256_packet', 'producer_sha256_packet_sha256',
                   'bindings', 'retained_x', 'profile', 'scope', 'claims', 'inputs', 'objective_rows',
                   'ranked_indices', 'hash_records'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'objective context schema/policy/base differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'objective context profile/scope differs')
    require(canonical(packet['claims']) == canonical({key: False for key in FALSE_CLAIMS}),
            'unsupported objective context root/closure claim')
    require(canonical(packet['retained_x']) == canonical(RETAINED_X_PINS), 'retained X anchors differ')
    raw_x = canonical(packet['producer_sha256_packet'])
    require(sha(raw_x) == packet['producer_sha256_packet_sha256'] == X_PACKET_SHA,
            'actual imported X packet differs')
    x = packet['producer_sha256_packet']
    require(canonical(packet['bindings']) == canonical(x['bindings']), 'objective package/program binding differs')
    require(sha(canonical(packet['inputs'])) == INPUTS_SHA256,
            'captured inputs differ from the exact retained fixture projection')
    expected = derive_objective(x, packet['inputs'], with_traces=False)
    require(canonical(packet['objective_rows']) == canonical(expected['objective_rows']),
            'complete objective row arithmetic differs')
    require(canonical(packet['ranked_indices']) == canonical(expected['ranked_indices']),
            'complete objective ranking/order differs')
    validate_hash_records(packet['hash_records'], expected['hash_records'])
    return previous.PreparedProducerSha256(raw_x)


@dataclass(frozen=True, slots=True)
class PreparedObjectiveContext:
    packet_bytes: bytes
    _previous: previous.PreparedProducerSha256 = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable objective context packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical objective context packet required')
        object.__setattr__(self, '_previous', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def producer_sha256(self) -> previous.PreparedProducerSha256:
        return self._previous


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in {**RETAINED_X_PINS, FIXTURE_PATH: FIXTURE_SHA}.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained Y input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained Y input changed: ' + name)
        result[name] = raw
    return result


def packet_from_inputs(x: dict, inputs: dict) -> dict:
    """Assemble independently derived data; this is not formal acceptance."""
    return {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
            'producer_sha256_packet': x, 'producer_sha256_packet_sha256': X_PACKET_SHA,
            'bindings': x['bindings'], 'retained_x': dict(RETAINED_X_PINS),
            'profile': dict(PROFILE), 'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS},
            'inputs': inputs, **derive_objective(x, inputs)}


def prepare_objective_context(root: Path, packages: Path) -> PreparedObjectiveContext:
    """Reconstruct the selected historical inputs without workers or campaigns."""
    retained = read_retained(root)
    inherited = previous.prepare_producer_sha256(root, packages)
    require(inherited.packet_bytes == retained[X_PACKET], 'fresh producer SHA inputs differ from completed X')
    x = inherited.packet
    inputs = inputs_from_transcript(x, retained[FIXTURE_PATH])
    prepared = PreparedObjectiveContext(canonical(packet_from_inputs(x, inputs)))
    require(retained == read_retained(root), 'retained X/fixture inputs changed during objective preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedObjectiveContext, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external objective context packet anchor differs')
    require(type(recomputed) is PreparedObjectiveContext and raw == recomputed.packet_bytes,
            'objective context packet differs from independent reconstruction')
    PreparedObjectiveContext(raw)


def summary(prepared: PreparedObjectiveContext) -> dict:
    require(type(prepared) is PreparedObjectiveContext, 'validated objective context packet required')
    p = prepared.packet
    groups = {}
    keys = set()
    for category, count in GROUP_COUNTS.items():
        records = [record for record in p['hash_records'] if record['category'] == category]
        lengths = [len(bytes.fromhex(record['preimage_hex'])) for record in records]
        groups[category] = {'images': count, 'preimage_bytes': sum(lengths),
                            'compression_blocks': sum(len(record['blocks']) for record in records)}
        for record in records:
            keys.update((tuple(block['input_state']), block['block_hex']) for block in record['blocks'])
    blocks = sum(group['compression_blocks'] for group in groups.values())
    return {'hash_groups': groups, 'complete_preimages': len(p['hash_records']),
            'complete_preimage_bytes': sum(group['preimage_bytes'] for group in groups.values()),
            'compression_blocks': blocks, 'distinct_compression_transitions': len(keys),
            'compression_rounds': blocks * 64, 'objective_families': 8, 'objective_terms': 8 * 84,
            'ranked_indices': p['ranked_indices'], 'selected_family': p['objective_rows'][p['ranked_indices'][0]]['family'],
            'objective_hash': p['bindings']['objective_hash'],
            'challenge_commitment_hash': p['bindings']['challenge_commitment_hash'],
            'producer_sha256_packet_sha256': X_PACKET_SHA,
            'python_reference_matches_hashlib': True,
            'fresh_worker_output_captured': False, 'candidate_active': False, 'promotion_authorized': False}
