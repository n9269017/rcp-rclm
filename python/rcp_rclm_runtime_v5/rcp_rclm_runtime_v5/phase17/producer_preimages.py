"""Phase 17W: selected producer preimages and seeded grammar interpretation.

The reference independently encodes the complete selected canonical JSON hash
inputs and derives all fixed-grammar descriptor parameters from complete supplied
seed digests. Python recomputes SHA-256 as external preparation consistency work;
the Lean result does not certify SHA-256, digest authenticity, physical capture,
or execution of Python. No worker, challenge, promotion or historical campaign
is invoked here. The exact completed V packet remains the input anchor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import program_metadata as metadata
from .controller import CurrentView, FAMILIES, RANKING_POLICY
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .resource_ledger import _no_links, digest, exact

BASE = '62338d94237f2b913bb2bd6ccd7367388678b92b'
SCHEMA = 'rcp-rclm.phase17w.producer-preimages-packet.v1'
POLICY = 'phase17w.selected-canonical-producer-preimages-and-seeded-grammar.v1'
V_ROOT = 'artifacts/development/phase17v/op-40e2a0fa5d4e'
V_EXECUTION = V_ROOT + '/gate/execution.json'
V_EXECUTION_SHA = '12194ab7d50b27e85d4e42b9b610c7b9fb0b46807a08ddeb88f59f7251a5b3ab'
V_PACKET = V_ROOT + '/gate/packet.json'
V_PACKET_SHA = 'f239d1b713117e5ae02182ddb8ce3c7e55a3580683767b938056c7dff5ca2161'
V_SOURCE = V_ROOT + '/gate/ProgramMetadata.lean'
V_SOURCE_SHA = 'efb57b5c15137d0d255e2f66e9e6bb4d9bfa8289b11f23c6e9d6b320c8b87216'
RETAINED_V_PINS = {
    V_EXECUTION: V_EXECUTION_SHA, V_PACKET: V_PACKET_SHA, V_SOURCE: V_SOURCE_SHA,
    V_ROOT + '/operator-validation.json':
        '53b0c637ac6e101b3a50bb750bf3127e3986639f7fb6b4f7674604fbfa5308aa',
}
MAX_BYTES = 32 * 1024 * 1024
MAX_JSON_BYTES = 65536
MAX_DEPTH = 20
MAX_ARRAY = 1024
MAX_OBJECT = 256
MAX_STRING = 8192
MAX_METADATA = (1 << 63) - 1
PUBLIC_HASH_DOMAIN = b'RCPRCLM-CANONICAL-JSON-V2\0'
GRAMMAR_DOMAIN = 'phase16.legal_mutation_program.v1'
RANKING_SEED_DOMAIN = 'phase17.present_only_ranking_seed.v1'
FEATURE_DOMAIN = 'phase16.inherited_planner_feature_projection.v1'
CHALLENGE_STREAM = 'phase17-present-only-v1'
FREEZE_SCHEMA = 'runtime.v5.phase17.freeze.v1'
PROFILE = {
    'json_grammar': 'bounded canonical unescaped printable ASCII JSON with signed 64-bit integers',
    'canonical_object_order': 'strict ascending ASCII keys; no duplicate keys',
    'hash_domain_hex': PUBLIC_HASH_DOMAIN.hex(),
    'grammar_seed_domain': GRAMMAR_DOMAIN,
    'ranking_seed_domain': RANKING_SEED_DOMAIN,
    'feature_domain': FEATURE_DOMAIN,
    'ranking_policy': RANKING_POLICY,
    'challenge_stream': CHALLENGE_STREAM,
    'freeze_schema': FREEZE_SCHEMA,
    'families': list(FAMILIES), 'operations': list(metadata.OPERATIONS),
    'variants_per_family': 4, 'grammar_rows': 32,
    'seed_digest_format': 'exactly 64 lowercase hexadecimal characters',
    'parameter_window_start': '(offset * 2) mod 56',
    'parameter_window_nibbles': 8,
    'parameter_value': 'big-endian 8-nibble unsigned integer mod 33 minus 16',
    'parameter_a_offset': 'family_index + variant',
    'parameter_b_offset': 'family_index + variant + 7',
    'parameter_min': -16, 'parameter_max': 16,
    'tie_rejection_counts': [0, 1, 2, 3, 4],
    'preimage_inventory': {'ranking_seed': 1, 'grammar_seed': 32, 'program': 32,
                          'feature': 32, 'tie': 160, 'freeze': 1},
    'preimage_count': 258,
    'preimage_origin': 'canonical reconstruction from the pinned V packet and its actual U/Q producer context',
    'formal_target': 'actual imported V candidate descriptor images and U producer inputs with selected Q acceptance',
}
SCOPE = {
    'domain': '258 complete selected producer hash preimages and 32 seeded grammar descriptors',
    'selected_grammar_parameter_derivation_checked': True,
    'selected_hash_preimages_checked': True,
    'general_grammar_parameter_derivation_remains_external': True,
    'public_hash_computation_remains_external': True,
    'sha256_computation_remains_external': True,
    'byte_capture_remains_external': True,
    'digest_authenticity_remains_external': True,
    'python_execution_remains_external': True,
    'general_json_parser_equivalence': False,
    'general_planner_equivalence': False,
    'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True,
    'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('W canonical producer-preimage reconstruction, seeded grammar interpretation and proof checking',
              *metadata.UNMEASURED[1:])


def _integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label)
    return value


def _ascii_string(value: object) -> bytes:
    require(type(value) is str and len(value) <= MAX_STRING and
            all(32 <= ord(char) <= 126 and char not in ('"', '\\') for char in value),
            'bounded unescaped printable ASCII string required')
    return b'"' + value.encode('ascii') + b'"'


def _encode(value: object, depth: int) -> bytes:
    require(depth <= MAX_DEPTH, 'canonical value nesting exceeds profile')
    if value is None:
        return b'null'
    if type(value) is bool:
        return b'true' if value else b'false'
    if type(value) is int:
        _integer(value, -(1 << 63), MAX_METADATA, 'canonical integer outside signed 64-bit range')
        return str(value).encode('ascii')
    if type(value) is str:
        return _ascii_string(value)
    if type(value) is list:
        require(len(value) <= MAX_ARRAY, 'canonical array exceeds profile')
        return b'[' + b','.join(_encode(item, depth + 1) for item in value) + b']'
    if type(value) is dict:
        require(len(value) <= MAX_OBJECT and all(type(key) is str for key in value),
                'bounded canonical string-keyed object required')
        fields = [(_ascii_string(key), _encode(value[key], depth + 1)) for key in sorted(value)]
        return b'{' + b','.join(key + b':' + item for key, item in fields) + b'}'
    raise ValueError('value is outside the selected canonical JSON profile')


def encode_canonical(value: object) -> bytes:
    """Independent selected-profile encoder, with no json.dumps or hash routine."""
    raw = _encode(value, 0)
    require(len(raw) <= MAX_JSON_BYTES, 'complete canonical JSON image exceeds profile')
    return raw


def hash_preimage(value: object) -> bytes:
    """The domain prefix includes its terminating NUL byte exactly once."""
    return PUBLIC_HASH_DOMAIN + encode_canonical(value)


def _hex_bytes(value: object, maximum: int) -> bytes:
    require(type(value) is str and 0 < len(value) <= maximum * 2 and len(value) % 2 == 0 and
            all(char in '0123456789abcdef' for char in value), 'bounded lowercase complete image hex required')
    return bytes.fromhex(value)


def signed_parameter(seed: str, offset: int) -> int:
    """Read all digest digits, then the declared eight-nibble window."""
    digest(seed)
    _integer(offset, 0, MAX_METADATA, 'seed parameter offset must be a bounded natural')
    digits = [ord(char) - (48 if char <= '9' else 87) for char in seed]
    start = (2 * offset) % 56
    value = 0
    for nibble in digits[start:start + 8]:
        value = 16 * value + nibble
    return value % 33 - 16


def _view(value: dict) -> dict:
    return CurrentView.from_json(value).to_json()


def grammar_seed_value(view: dict, family: int, variant: int) -> dict:
    context = _view(view)
    _integer(family, 0, 7, 'grammar family index out of bounds')
    _integer(variant, 0, 3, 'grammar variant out of bounds')
    generation = context['family_counts'][family] + 1
    _integer(generation, 1, MAX_METADATA, 'grammar generation out of bounds')
    return {'domain': GRAMMAR_DOMAIN, 'active_package_hash': context['active_package_hash'],
            'promotion_index': context['turn_index'], 'family': FAMILIES[family],
            'variant': variant, 'generation': generation, 'public_nonce_hash': context['public_nonce_hash']}


def grammar_descriptor(view: dict, family: int, variant: int, seed: str) -> dict:
    seed_value = grammar_seed_value(view, family, variant)
    digest(seed)
    return {'schema_id': metadata.PROGRAM_SCHEMA, 'promotion_index': seed_value['promotion_index'],
            'family': FAMILIES[family], 'variant': variant, 'generation': seed_value['generation'],
            'operation_id': metadata.OPERATIONS[family],
            'parameter_a': signed_parameter(seed, family + variant),
            'parameter_b': signed_parameter(seed, family + variant + 7),
            'public_nonce_hash': seed_value['public_nonce_hash']}


def ranking_seed_value(view: dict) -> dict:
    return {'domain': RANKING_SEED_DOMAIN, 'view': _view(view)}


def feature_value(view: dict, program: dict, seed: str) -> dict:
    context = _view(view)
    digest(seed)
    metadata.decode_program(encode_canonical(program))
    return {'domain': FEATURE_DOMAIN, 'planner_weights_sha256': metadata.planner.WEIGHTS_SHA256,
            'active_package_hash': context['active_package_hash'], 'program': program,
            'seed': seed, 'challenge_stream': CHALLENGE_STREAM}


def tie_value(view: dict, key: str, family: int, rejected: int) -> dict:
    context = _view(view)
    digest(key)
    _integer(family, 0, 7, 'tie family index out of bounds')
    _integer(rejected, 0, 4, 'tie rejection count out of bounds')
    return {'policy_id': RANKING_POLICY, 'program_hash': key,
            'active_package_hash': context['active_package_hash'],
            'family_count': context['family_counts'][family], 'rejection_count': rejected}


def freeze_value(view: dict, table: list[dict]) -> dict:
    context = _view(view)
    require(type(table) is list and len(table) == 32, 'complete producer table required for freeze')
    candidates = []
    for row in table:
        exact(row, {'program_hash', 'family_index', 'variant', 'base_score', 'ties'})
        digest(row['program_hash'])
        family = _integer(row['family_index'], 0, 7, 'freeze family index out of bounds')
        variant = _integer(row['variant'], 0, 3, 'freeze variant out of bounds')
        score = _integer(row['base_score'], -(1 << 63), MAX_METADATA, 'freeze score out of bounds')
        candidates.append({'program_hash': row['program_hash'], 'family': FAMILIES[family],
                           'variant': variant, 'base_score': score})
    keys = [row['program_hash'] for row in candidates]
    require(keys == sorted(set(keys)) and len(keys) == 32, 'freeze candidate keys must be ordered and unique')
    require({(row['family'], row['variant']) for row in candidates} ==
            {(family, variant) for family in FAMILIES for variant in range(4)},
            'freeze must cover the complete family/variant domain')
    return {'schema': FREEZE_SCHEMA, 'view': context, 'candidates': candidates}


def _record(value: object, expected_digest: str | None = None) -> dict:
    raw = encode_canonical(value)
    preimage = PUBLIC_HASH_DOMAIN + raw
    computed = sha(preimage)
    if expected_digest is not None:
        require(computed == digest(expected_digest), 'external SHA consistency differs from anchored producer digest')
    return {'json_hex': raw.hex(), 'preimage_hex': preimage.hex(), 'digest': computed}


def _check_record(record: dict, expected: dict) -> None:
    exact(record, {'json_hex', 'preimage_hex', 'digest'})
    raw = _hex_bytes(record['json_hex'], MAX_JSON_BYTES)
    preimage = _hex_bytes(record['preimage_hex'], MAX_JSON_BYTES + len(PUBLIC_HASH_DOMAIN))
    digest(record['digest'])
    require(preimage == PUBLIC_HASH_DOMAIN + raw, 'hash domain or complete JSON preimage differs')
    require(record['json_hex'] == expected['json_hex'], 'canonical JSON preimage fields or encoding differ')
    require(record['preimage_hex'] == expected['preimage_hex'], 'complete prefixed preimage differs')
    require(record['digest'] == expected['digest'] == sha(preimage), 'supplied external producer digest differs')


def producer_inputs(v: dict) -> dict:
    """Reconstruct all preimages and seeded descriptors from the exact V/U inputs.

    This is pure reference preparation. The hash outputs are supplied to Lean;
    checking their SHA-256 computation is outside the W theorem.
    """
    u = v['planner_refinement_packet']
    ranking = u['ranking']
    view = _view(ranking['current_view'])
    seed = _record(ranking_seed_value(view), ranking['seed_digest'])
    require(encode_canonical(ranking_seed_value(view)) == canonical(ranking['seed_preimage']),
            'constructed ranking seed differs from actual U preimage')
    require(type(ranking['rows']) is list and len(ranking['rows']) == 32 and
            type(v['candidate_images']) is list and len(v['candidate_images']) == 32,
            'complete actual V/U grammar inventory required')
    rows, pairs = [], []
    for row, image in zip(ranking['rows'], v['candidate_images'], strict=True):
        program = metadata.decode_program(metadata.image_bytes(image['image_hex']))
        family = FAMILIES.index(program['family'])
        variant = program['variant']
        count = view['family_counts'][family]
        key = digest(row['key'])
        require(image['key'] == key and row['family'] == family and row['family_count'] == count and
                type(row['family']) is int and type(row['family_count']) is int,
                'actual V program key/family/count differs from actual U row')
        seed_value = grammar_seed_value(view, family, variant)
        grammar_seed = _record(seed_value)
        derived = grammar_descriptor(view, family, variant, grammar_seed['digest'])
        require(encode_canonical(derived) == metadata.image_bytes(image['image_hex']) == canonical(row['program']),
                'seed-derived descriptor differs from actual imported V image or U program')
        program_record = _record(derived, key)
        feature = feature_value(view, derived, seed['digest'])
        require(encode_canonical(feature) == canonical(row['feature_preimage']),
                'constructed feature differs from actual U preimage')
        require(type(row['tie_preimages']) is list and len(row['tie_preimages']) == 5 and
                type(row['tie_digests']) is list and len(row['tie_digests']) == 5,
                'complete ordered actual U tie input inventory required')
        ties = []
        for rejected in range(5):
            tie = tie_value(view, key, family, rejected)
            require(encode_canonical(tie) == canonical(row['tie_preimages'][rejected]),
                    'constructed tie differs from actual U preimage')
            ties.append(_record(tie, row['tie_digests'][rejected]))
        rows.append({'key': key, 'grammar_seed': grammar_seed, 'program': program_record,
                     'feature': _record(feature, row['feature_digest']), 'ties': ties})
        pairs.append((family, variant))
    keys = [row['key'] for row in rows]
    require(keys == sorted(set(keys)) and len(keys) == 32 and
            set(pairs) == {(family, variant) for family in range(8) for variant in range(4)},
            'complete ordered eight-family four-variant domain required')
    frozen = freeze_value(view, u['before_table'])
    require(encode_canonical(frozen) == canonical(ranking['freeze_preimage']),
            'constructed freeze differs from actual U preimage')
    return {'current_view': view, 'ranking_seed': seed, 'rows': rows,
            'freeze': _record(frozen, ranking['freeze_digest'])}


def validate_producer(producer: dict, v: dict) -> dict:
    exact(producer, {'current_view', 'ranking_seed', 'rows', 'freeze'})
    require(canonical(producer['current_view']) == canonical(v['planner_refinement_packet']['ranking']['current_view']),
            'producer current view differs from actual V/U context')
    _view(producer['current_view'])
    require(type(producer['rows']) is list and len(producer['rows']) == 32,
            'complete 32-row preimage inventory required')
    expected = producer_inputs(v)
    _check_record(producer['ranking_seed'], expected['ranking_seed'])
    for row, target in zip(producer['rows'], expected['rows'], strict=True):
        exact(row, {'key', 'grammar_seed', 'program', 'feature', 'ties'})
        require(digest(row['key']) == target['key'], 'preimage row key or order differs from imported V/U')
        require(type(row['ties']) is list and len(row['ties']) == 5, 'all five ordered tie preimages required')
        for kind in ('grammar_seed', 'program', 'feature'):
            _check_record(row[kind], target[kind])
        for value, target_value in zip(row['ties'], target['ties'], strict=True):
            _check_record(value, target_value)
    _check_record(producer['freeze'], expected['freeze'])
    return expected


def validate_packet(packet: dict) -> metadata.PreparedProgramMetadata:
    exact(packet, {'schema', 'policy', 'base_commit', 'program_metadata_packet', 'program_metadata_packet_sha256',
                   'bindings', 'retained_v', 'profile', 'scope', 'claims', 'producer'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'producer preimage schema/policy differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'producer preimage profile/scope differs')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported producer preimage root/closure claim')
    require(canonical(packet['retained_v']) == canonical(RETAINED_V_PINS), 'retained V anchors changed')
    raw_v = canonical(packet['program_metadata_packet'])
    require(sha(raw_v) == packet['program_metadata_packet_sha256'] == V_PACKET_SHA, 'same-candidate V packet changed')
    require(canonical(packet['bindings']) == canonical(packet['program_metadata_packet']['bindings']),
            'producer preimage package/program binding differs')
    validate_producer(packet['producer'], packet['program_metadata_packet'])
    # Reject invalid W additions before the inherited, more expensive validation.
    return metadata.PreparedProgramMetadata(raw_v)


@dataclass(frozen=True, slots=True)
class PreparedProducerPreimages:
    packet_bytes: bytes
    _metadata: metadata.PreparedProgramMetadata = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable producer preimage packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical producer preimage packet required')
        object.__setattr__(self, '_metadata', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def program_metadata(self) -> metadata.PreparedProgramMetadata:
        return self._metadata


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_V_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained V input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained V input changed: ' + name)
        result[name] = raw
    return result


def prepare_producer_preimages(root: Path, packages: Path) -> PreparedProducerPreimages:
    """Reconstruct complete V inputs and all 258 preimages without campaigns."""
    retained = read_retained(root)
    previous = metadata.prepare_program_metadata(root, packages)
    require(previous.packet_bytes == retained[V_PACKET], 'fresh program metadata differs from completed V')
    v = previous.packet
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'program_metadata_packet': v, 'program_metadata_packet_sha256': sha(previous.packet_bytes),
              'bindings': v['bindings'], 'retained_v': dict(RETAINED_V_PINS),
              'profile': dict(PROFILE), 'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS},
              'producer': producer_inputs(v)}
    prepared = PreparedProducerPreimages(canonical(packet))
    require(retained == read_retained(root), 'retained V inputs changed during producer preimage preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedProducerPreimages, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external producer preimage packet anchor differs')
    require(type(recomputed) is PreparedProducerPreimages and raw == recomputed.packet_bytes,
            'producer preimage packet differs from independent reconstruction')
    PreparedProducerPreimages(raw)


def preimage_groups(producer: dict) -> dict[str, list[dict]]:
    return {'ranking_seed': [producer['ranking_seed']],
            'grammar_seed': [row['grammar_seed'] for row in producer['rows']],
            'program': [row['program'] for row in producer['rows']],
            'feature': [row['feature'] for row in producer['rows']],
            'tie': [value for row in producer['rows'] for value in row['ties']],
            'freeze': [producer['freeze']]}


def summary(prepared: PreparedProducerPreimages) -> dict:
    require(type(prepared) is PreparedProducerPreimages, 'validated producer preimage packet required')
    packet = prepared.packet
    producer = validate_producer(packet['producer'], packet['program_metadata_packet'])
    groups = preimage_groups(producer)
    counts = {kind: {'images': len(values),
                     'json_bytes': sum(len(bytes.fromhex(value['json_hex'])) for value in values),
                     'prefixed_bytes': sum(len(bytes.fromhex(value['preimage_hex'])) for value in values)}
              for kind, values in groups.items()}
    return {'preimage_groups': counts,
            'complete_json_images': sum(value['images'] for value in counts.values()),
            'complete_json_bytes': sum(value['json_bytes'] for value in counts.values()),
            'complete_prefixed_bytes': sum(value['prefixed_bytes'] for value in counts.values()),
            'domain_prefix_bytes_per_image': len(PUBLIC_HASH_DOMAIN),
            'canonical_grammar_descriptors': len(producer['rows']),
            'derived_parameters': 2 * len(producer['rows']),
            'seed_digest_nibbles': 64, 'parameter_window_nibbles': 8,
            'families': len(FAMILIES), 'variants_per_family': 4,
            'tie_rejection_counts': list(range(5)),
            'preimage_origin': PROFILE['preimage_origin'],
            'selected_program_hash': packet['bindings']['program_hash'],
            'program_metadata_packet_sha256': V_PACKET_SHA,
            'sha256_is_external_preparation_consistency_check': True,
            'sha256_formally_checked': False,
            'fresh_worker_output_captured': False,
            'candidate_active': False, 'promotion_authorized': False}
