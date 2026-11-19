"""Phase 17U: exact captured planner bytes to the selected producer score table.

This independent numerical reference decodes the entire signed-int16 image,
then computes every grammar row from public feature/tie digest text.  Hash
preimages and original program descriptors are reconstructed in Python; their
cryptographic computation and metadata interpretation remain external to Lean.
No worker, challenge service, active package, or promotion authority is used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import captured_json as captured
from .bootstrap import WEIGHTS_SHA256, _validate_program
from .challenge_protocol import reference_grammar
from .controller import CurrentView, FAMILIES, RANKING_POLICY
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .resource_ledger import _no_links, digest, exact

BASE = 'db13c5fbaba20151d5d313885cb4e663859f45c1'
SCHEMA = 'rcp-rclm.phase17u.planner-byte-refinement-packet.v1'
POLICY = 'phase17u.exact-planner-bytes-to-public-producer-scores.v1'
T_ROOT = 'artifacts/development/phase17t/op-78919ccb87a0'
T_EXECUTION = T_ROOT + '/gate/execution.json'
T_EXECUTION_SHA = '633dadb4084661d578ee83d357766348cbcf88dde9b371f9a6a1c7eb27224807'
T_PACKET = T_ROOT + '/gate/packet.json'
T_PACKET_SHA = '1c1706cf77fd7cef65f9bbded78ff63796624c27cb1932032c5d7459e70c8410'
T_SOURCE = T_ROOT + '/gate/CapturedJson.lean'
T_SOURCE_SHA = '1f26cd1828a2a84fc408f42e787e3b44d398496ebd3d081bd7c38396884431f7'
RETAINED_T_PINS = {
    T_EXECUTION: T_EXECUTION_SHA, T_PACKET: T_PACKET_SHA, T_SOURCE: T_SOURCE_SHA,
    T_ROOT + '/operator-validation.json':
        '2ff38a77d760aa835534713da85b8a7e1fd2dc4ff663217c459772a62ab93fd7',
}
PLANNER_PATH = 'base/model/phase15_planner/weights.i16le.bin'
WORD_COUNT = 32768
TENSOR_BYTES = 2 * WORD_COUNT
MAX_BYTES = 28 * 1024 * 1024
MAX_METADATA = (1 << 63) - 1
PUBLIC_HASH_DOMAIN = b'RCPRCLM-CANONICAL-JSON-V2\0'
PROFILE = {
    'tensor_path': PLANNER_PATH, 'tensor_bytes': TENSOR_BYTES,
    'word_count': WORD_COUNT, 'element': 'signed_int16_little_endian',
    'projection': 'all nonzero words in ascending word-index order',
    'grammar_rows': 32, 'families': list(FAMILIES), 'variants_per_family': 4,
    'feature_digest': '64 lowercase hexadecimal characters',
    'public_hash_domain_hex': PUBLIC_HASH_DOMAIN.hex(),
    'public_hash_preimage_encoding': 'RCPRCLM-CJSON-V2 with the exact recorded domain prefix',
    'nibble_offset': '(word_index + projection_index * 11) mod 64',
    'feature': '(nibble + family * 3 + variant * 5 + generation + projection_index) mod 9 - 4',
    'base_score': '20000 - family_count * 521 + sum(signed_word * feature)',
    'rejection_pressure': 797,
    'tie': 'first 16 hexadecimal characters of the public tie digest interpreted as a natural number',
    'tie_rejection_counts': [0, 1, 2, 3, 4],
    'ordering': 'descending score, then tie, then lexically ordered program key',
    'ranked_prefix_length': 4, 'enumeration_stride': 17,
    'enumeration_offset': 'first 16 hexadecimal characters of freeze digest mod 32',
    'maximum_metadata_integer': MAX_METADATA,
}
SCOPE = {
    'domain': 'complete captured inherited planner images and the selected 32-row producer table',
    'formal_target': 'signed planner interpretation and equality with the actual imported Q producer context',
    'byte_capture_remains_external': True,
    'digest_authenticity_remains_external': True,
    'public_hash_computation_remains_external': True,
    'program_metadata_interpretation_remains_external': True,
    'python_execution_remains_external': True,
    'general_planner_equivalence': False,
    'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True,
    'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('U planner-image preparation, numerical reconstruction and proof checking',
              *captured.UNMEASURED[1:])


def _integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label)
    return value


def signed16(lo: int, hi: int) -> int:
    """Byte arithmetic independent of struct and the production ranker."""
    _integer(lo, 0, 255, 'planner low byte outside uint8')
    _integer(hi, 0, 255, 'planner high byte outside uint8')
    unsigned = lo + 256 * hi
    return unsigned if hi < 128 else unsigned - 65536


def _raw(raw: bytes) -> None:
    require(type(raw) is bytes and len(raw) == TENSOR_BYTES,
            'exact immutable 65536-byte planner image required')


def word_projection(raw: bytes) -> list[list[int]]:
    """Scan every word, including the zero complement of the sparse support."""
    _raw(raw)
    result = []
    for index in range(WORD_COUNT):
        value = signed16(raw[2 * index], raw[2 * index + 1])
        if value:
            result.append([index, value])
    return result


def encode_planner(raw: bytes) -> dict:
    _raw(raw)
    return {'byte_length': TENSOR_BYTES,
            'nonzero_bytes': [[index, value] for index, value in enumerate(raw) if value],
            'nonzero_words': word_projection(raw)}


def decode_planner(image: dict) -> bytes:
    exact(image, {'byte_length', 'nonzero_bytes', 'nonzero_words'})
    require(type(image['byte_length']) is int and image['byte_length'] == TENSOR_BYTES,
            'planner image byte length differs')
    support = image['nonzero_bytes']
    require(type(support) is list and len(support) <= TENSOR_BYTES,
            'bounded sparse planner byte support required')
    raw = bytearray(TENSOR_BYTES)
    previous = -1
    for row in support:
        require(type(row) is list and len(row) == 2, 'exact planner byte pair required')
        offset = _integer(row[0], 0, TENSOR_BYTES - 1, 'planner byte offset out of bounds')
        value = _integer(row[1], 1, 255, 'planner sparse byte must be nonzero uint8')
        require(offset > previous, 'planner byte offsets must be strictly increasing')
        raw[offset], previous = value, offset
    words = image['nonzero_words']
    require(type(words) is list and len(words) <= WORD_COUNT,
            'bounded sparse planner word support required')
    previous = -1
    for row in words:
        require(type(row) is list and len(row) == 2, 'exact planner word pair required')
        index = _integer(row[0], 0, WORD_COUNT - 1, 'planner word index out of bounds')
        value = _integer(row[1], -32768, 32767, 'planner word outside signed int16')
        require(value != 0 and index > previous, 'planner words must be nonzero and strictly ordered')
        previous = index
    result = bytes(raw)
    require(words == word_projection(result), 'complete planner word projection differs from bytes')
    return result


def hex_nibbles(text: str) -> list[int]:
    """Interpret the complete digest text, without accepting prefixes or uppercase."""
    require(type(text) is str and len(text) == 64 and
            all(character in '0123456789abcdef' for character in text),
            'exact lowercase 64-character public digest required')
    return [ord(character) - 48 if character <= '9' else ord(character) - 87
            for character in text]


def prefix_number(text: str) -> int:
    value = 0
    for nibble in hex_nibbles(text)[:16]:
        value = 16 * value + nibble
    return value


def public_hash(value: object) -> str:
    return sha(PUBLIC_HASH_DOMAIN + canonical(value))


def score_from_projection(projection: list[list[int]], feature_digest: str, *,
                          family: int, variant: int, generation: int, family_count: int) -> int:
    """Exact integer dot product and novelty term; no production score function."""
    _integer(family, 0, 7, 'planner family index out of range')
    _integer(variant, 0, 3, 'planner variant out of range')
    _integer(generation, 1, MAX_METADATA, 'planner generation out of range')
    _integer(family_count, 0, MAX_METADATA, 'planner family count out of range')
    require(type(projection) is list and len(projection) <= WORD_COUNT,
            'bounded planner projection required')
    digits = hex_nibbles(feature_digest)
    total = 20000 - 521 * family_count
    previous = -1
    for projection_index, row in enumerate(projection):
        require(type(row) is list and len(row) == 2, 'exact planner projection pair required')
        word_index = _integer(row[0], 0, WORD_COUNT - 1, 'planner projection index out of range')
        word = _integer(row[1], -32768, 32767, 'planner projection value outside signed range')
        require(word != 0 and word_index > previous, 'canonical complete planner projection required')
        previous = word_index
        digit = digits[(word_index + 11 * projection_index) % 64]
        coefficient = (digit + 3 * family + 5 * variant + generation + projection_index) % 9 - 4
        total += word * coefficient
    return total


def reference_table(raw: bytes, rows: list[dict]) -> list[dict]:
    """Compute all table entries from one complete image and bound public inputs."""
    weights = word_projection(raw)
    require(type(rows) is list and len(rows) == 32, 'complete 32-row planner input required')
    result = []
    keys, pairs = [], []
    for row in rows:
        exact(row, {'program', 'key', 'family', 'family_count', 'feature_preimage',
                    'feature_digest', 'tie_preimages', 'tie_digests'})
        program = row['program']
        _validate_program(program)
        key = digest(row['key'])
        require(key == public_hash(program), 'planner descriptor/key binding differs')
        family = _integer(row['family'], 0, 7, 'planner family index differs')
        require(program['family'] == FAMILIES[family], 'planner program family differs')
        count = _integer(row['family_count'], 0, MAX_METADATA, 'planner family count differs')
        require(program['generation'] == count + 1, 'planner generation/count binding differs')
        require(type(row['tie_digests']) is list and len(row['tie_digests']) == 5,
                'complete five-value planner tie inventory required')
        score = score_from_projection(weights, row['feature_digest'], family=family,
                                      variant=program['variant'], generation=program['generation'],
                                      family_count=count)
        ties = [prefix_number(value) for value in row['tie_digests']]
        result.append({'program_hash': key, 'family_index': family, 'variant': program['variant'],
                       'base_score': score, 'ties': ties})
        keys.append(key)
        pairs.append((family, program['variant']))
    require(keys == sorted(keys) and len(set(keys)) == 32,
            'planner inputs must use unique ordered program keys')
    require(set(pairs) == {(family, variant) for family in range(8) for variant in range(4)},
            'complete planner family/variant coverage required')
    return result


def reference_choice(table: list[dict], seen: list[int], offset: int) -> int | None:
    """Independently select from present-only rows; exhaustion returns no choice."""
    _integer(offset, 0, 31, 'planner enumeration offset out of range')
    require(type(table) is list and len(table) == 32, 'complete producer table required')
    keys = []
    for row in table:
        exact(row, {'program_hash', 'family_index', 'variant', 'base_score', 'ties'})
        keys.append(digest(row['program_hash']))
        _integer(row['family_index'], 0, 7, 'producer family index differs')
        _integer(row['variant'], 0, 3, 'producer variant differs')
        require(type(row['base_score']) is int, 'producer score must be an exact integer')
        require(type(row['ties']) is list and len(row['ties']) == 5 and
                all(type(value) is int and 0 <= value < (1 << 64) for value in row['ties']),
                'producer tie values differ')
    require(keys == sorted(keys) and len(set(keys)) == 32, 'ordered unique producer keys required')
    require(type(seen) is list and len(seen) <= 32 and all(
        type(index) is int and 0 <= index < 32 for index in seen) and len(seen) == len(set(seen)),
        'invalid prior producer choices')
    if len(seen) >= 4:
        for position in range(32):
            candidate = (offset + 17 * position) % 32
            if candidate not in seen:
                return candidate
        return None
    winner, winning_key = None, None
    for index, row in enumerate(table):
        if index in seen:
            continue
        rejections = sum(table[earlier]['family_index'] == row['family_index'] for earlier in seen)
        key = (row['base_score'] + 797 * rejections, row['ties'][rejections], row['program_hash'])
        if winning_key is None or key > winning_key:
            winner, winning_key = index, key
    return winner


def producer_packet(packet: dict) -> dict:
    """The exact already-bound producer context inside the complete T input."""
    return packet['captured_json_packet']['routing_packet']['sparse_packet']['finite_packet'][
        'protected_packet']['joint_packet']['producer_provenance']


def _ranking_inputs(provenance: dict) -> dict:
    """Derive every public hash input from the original fixed context/grammar.

    SHA-256 is reexecuted externally here. Lean receives its complete digest text
    and checks numeric interpretation; this function is not a SHA correctness proof.
    """
    trace = provenance['trace']
    view = CurrentView.from_json(trace['current_view'])
    seed_preimage = {'domain': 'phase17.present_only_ranking_seed.v1', 'view': view.to_json()}
    seed_digest = public_hash(seed_preimage)
    programs = reference_grammar({'active_package_hash': view.active_package_hash,
        'component_generations': dict(zip(FAMILIES, view.family_counts, strict=True))},
        view.turn_index, view.public_nonce_hash)
    rows = []
    for program in programs:
        key = public_hash(program)
        family = FAMILIES.index(program['family'])
        count = view.family_counts[family]
        feature_preimage = {'domain': 'phase16.inherited_planner_feature_projection.v1',
            'planner_weights_sha256': WEIGHTS_SHA256, 'active_package_hash': view.active_package_hash,
            'program': program, 'seed': seed_digest, 'challenge_stream': 'phase17-present-only-v1'}
        tie_preimages = [{'policy_id': RANKING_POLICY, 'program_hash': key,
            'active_package_hash': view.active_package_hash, 'family_count': count,
            'rejection_count': rejected} for rejected in range(5)]
        rows.append({'program': program, 'key': key, 'family': family, 'family_count': count,
            'feature_preimage': feature_preimage, 'feature_digest': public_hash(feature_preimage),
            'tie_preimages': tie_preimages, 'tie_digests': [public_hash(value) for value in tie_preimages]})
    # The fixed source context determines the expected freeze. Numeric equality
    # with these rows is independently required below, on BOTH byte images.
    freeze_preimage = {'schema': 'runtime.v5.phase17.freeze.v1', 'view': view.to_json(),
        'candidates': [{'program_hash': row['program_hash'], 'family': FAMILIES[row['family_index']],
            'variant': row['variant'], 'base_score': row['base_score']} for row in trace['table']]}
    freeze_digest = public_hash(freeze_preimage)
    require(freeze_digest == trace['search_freeze_hash'], 'original search freeze differs')
    return {'current_view': view.to_json(), 'seed_preimage': seed_preimage, 'seed_digest': seed_digest,
            'rows': rows, 'freeze_preimage': freeze_preimage, 'freeze_digest': freeze_digest,
            'offset': prefix_number(freeze_digest) % 32}


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_T_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES,
                'missing/oversized retained T input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained T input changed: ' + name)
        result[name] = raw
    return result


def validate_packet(packet: dict) -> captured.PreparedCapturedJson:
    exact(packet, {'schema', 'policy', 'base_commit', 'captured_json_packet', 'captured_json_packet_sha256',
                   'bindings', 'retained_t', 'profile', 'scope', 'claims', 'before', 'after',
                   'tensor_sha256', 'ranking', 'before_table', 'after_table', 'selected_choices'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'planner refinement schema/policy differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'planner refinement profile/scope differs')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported planner root/closure claim')
    require(canonical(packet['retained_t']) == canonical(RETAINED_T_PINS), 'retained T anchors changed')
    raw_t = canonical(packet['captured_json_packet'])
    require(sha(raw_t) == packet['captured_json_packet_sha256'] == T_PACKET_SHA,
            'same-candidate T packet changed')
    require(canonical(packet['bindings']) == canonical(packet['captured_json_packet']['bindings']),
            'planner package/task binding differs')
    provenance = producer_packet(packet)
    record = next(row for row in provenance['producer']['component_files'] if row['path'] == PLANNER_PATH)
    require(record == {'path': PLANNER_PATH, 'size': TENSOR_BYTES, 'sha256': WEIGHTS_SHA256},
            'planner component binding differs from original producer')
    exact(packet['tensor_sha256'], {'before', 'after'})
    images = {side: decode_planner(packet[side]) for side in ('before', 'after')}
    for side, raw in images.items():
        require(sha(raw) == digest(packet['tensor_sha256'][side]) == WEIGHTS_SHA256,
                'captured planner image differs from original producer: ' + side)
        require(encode_planner(raw) == packet[side], 'planner image round trip differs')
    ranking = _ranking_inputs(provenance)
    require(canonical(packet['ranking']) == canonical(ranking), 'public planner hash/descriptor inputs differ')
    for side, raw in images.items():
        rows = reference_table(raw, ranking['rows'])
        require(canonical(packet[side + '_table']) == canonical(rows) == canonical(provenance['trace']['table']),
                'complete planner score table differs from original producer: ' + side)
    require(type(ranking['offset']) is int and ranking['offset'] == provenance['trace']['enumeration_offset'],
            'planner enumeration offset differs')
    choices = [step['selected_index'] for step in provenance['trace']['steps']]
    require(canonical(packet['selected_choices']) == canonical(choices), 'ordered producer trace differs')
    seen = []
    for choice in choices:
        require(reference_choice(packet['before_table'], seen, ranking['offset']) == choice,
                'byte-derived table does not select original producer prefix')
        seen.append(choice)
    # Only complete valid U inputs invoke the inherited deep validator. This
    # ordering avoids rechecking the large T packet for malformed U controls.
    return captured.PreparedCapturedJson(raw_t)


@dataclass(frozen=True, slots=True)
class PreparedPlannerRefinement:
    packet_bytes: bytes
    _captured: captured.PreparedCapturedJson = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable planner refinement packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical planner refinement packet required')
        object.__setattr__(self, '_captured', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def captured_json(self) -> captured.PreparedCapturedJson:
        return self._captured


def prepare_planner_refinement(root: Path, packages: Path) -> PreparedPlannerRefinement:
    """Freshly reconstruct both physical images and T inputs, without workers or Lean."""
    retained = read_retained(root)
    previous = captured.prepare_captured_json(root, packages)
    require(previous.packet_bytes == retained[T_PACKET], 'fresh JSON input differs from completed T')
    t_packet = previous.packet
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'captured_json_packet': t_packet, 'captured_json_packet_sha256': sha(previous.packet_bytes),
              'bindings': t_packet['bindings'], 'retained_t': dict(RETAINED_T_PINS),
              'profile': dict(PROFILE), 'scope': dict(SCOPE),
              'claims': {name: False for name in FALSE_CLAIMS}}
    raw_images = {}
    for side in ('before', 'after'):
        path = packages / side / PLANNER_PATH
        _no_links(path)
        require(path.is_file() and path.stat().st_size == TENSOR_BYTES, 'complete physical planner image missing')
        raw_images[side] = path.read_bytes()
        packet[side] = encode_planner(raw_images[side])
    packet['tensor_sha256'] = {side: sha(raw) for side, raw in raw_images.items()}
    provenance = producer_packet(packet)
    packet['ranking'] = _ranking_inputs(provenance)
    for side, raw in raw_images.items():
        packet[side + '_table'] = reference_table(raw, packet['ranking']['rows'])
    packet['selected_choices'] = [step['selected_index'] for step in provenance['trace']['steps']]
    prepared = PreparedPlannerRefinement(canonical(packet))
    require(all((packages / side / PLANNER_PATH).read_bytes() == raw for side, raw in raw_images.items()),
            'physical planner image changed during capture')
    require(retained == read_retained(root), 'retained T inputs changed during planner preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedPlannerRefinement, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external planner packet anchor differs')
    require(type(recomputed) is PreparedPlannerRefinement and raw == recomputed.packet_bytes,
            'planner packet differs from independent reconstruction')
    PreparedPlannerRefinement(raw)


def summary(prepared: PreparedPlannerRefinement) -> dict:
    require(type(prepared) is PreparedPlannerRefinement, 'validated planner refinement packet required')
    packet = prepared.packet
    return {'packages': 2, 'tensor_bytes_per_package': TENSOR_BYTES,
            'word_count_per_package': WORD_COUNT,
            'nonzero_words_per_package': {side: len(packet[side]['nonzero_words']) for side in ('before', 'after')},
            'nonzero_bytes_per_package': {side: len(packet[side]['nonzero_bytes']) for side in ('before', 'after')},
            'source_path': PLANNER_PATH, 'source_file_sha256': packet['tensor_sha256'],
            'grammar_rows_per_package': len(packet['ranking']['rows']),
            'feature_digests': len(packet['ranking']['rows']),
            'tie_digests': sum(len(row['tie_digests']) for row in packet['ranking']['rows']),
            'selected_proposals': len(packet['selected_choices']),
            'selected_choices': packet['selected_choices'],
            'enumeration_offset': packet['ranking']['offset'],
            'captured_json_packet_sha256': T_PACKET_SHA}
