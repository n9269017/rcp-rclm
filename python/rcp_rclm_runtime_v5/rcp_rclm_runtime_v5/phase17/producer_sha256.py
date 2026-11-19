"""Phase 17X: selected SHA-256 evaluation of W's complete producer preimages.

This independent, integer-only SHA-256 reference follows FIPS 180-4 sections
4.1.2, 4.2.2, 5.1.1, 5.2.1, 5.3.3 and 6.2. It does not call hashlib or the
production producer. hashlib is used separately to detect preparation mistakes.
The Lean certificate checks the selected computation; physical capture, digest
authenticity, and execution of Python remain external. No campaign is run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import producer_preimages as preimages
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .resource_ledger import _no_links, digest, exact

BASE = '812510fa3e68212d8b0551c6facd23a6f3a90119'
SCHEMA = 'rcp-rclm.phase17x.producer-sha256-packet.v1'
POLICY = 'phase17x.selected-fips180-4-producer-sha256.v1'
W_ROOT = 'artifacts/development/phase17w/op-a6603870a4f3'
W_EXECUTION = W_ROOT + '/gate/execution.json'
W_EXECUTION_SHA = '3e28aa871593cf5b6de14ee2c5a4108ddf471d49a82d8d2b890167d9c8b9de2f'
W_PACKET = W_ROOT + '/gate/packet.json'
W_PACKET_SHA = '0aa054dadb40655a373887197fbe5bd2ec41b62ad435db8f9d3695e650cb9947'
W_SOURCE = W_ROOT + '/gate/ProducerPreimages.lean'
W_SOURCE_SHA = '1708667cbcffd5cf66b64fd3bca8fcae5a75d32cbc6dfdc71d900830e65e8181'
RETAINED_W_PINS = {
    W_EXECUTION: W_EXECUTION_SHA, W_PACKET: W_PACKET_SHA, W_SOURCE: W_SOURCE_SHA,
    W_ROOT + '/operator-validation.json':
        'd0aeae4b64d33e5d29002ed910ecf5b69693c1249e5c84ef10516271a1bf6cc2',
}
MAX_BYTES = 32 * 1024 * 1024
MAX_IMAGE_BYTES = preimages.MAX_JSON_BYTES + len(preimages.PUBLIC_HASH_DOMAIN)
WORD_MASK = (1 << 32) - 1
INITIAL_STATE = (
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
)
ROUND_CONSTANTS = (
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
)
GROUP_COUNTS = {'ranking_seed': 1, 'grammar_seed': 32, 'program': 32,
                'feature': 32, 'tie': 160, 'freeze': 1}
PROFILE = {
    'algorithm': 'SHA-256', 'standard': 'FIPS PUB 180-4 (August 2015)',
    'word_bits': 32, 'block_bytes': 64, 'rounds_per_block': 64,
    'digest_bytes': 32, 'digest_text': '64 lowercase hexadecimal characters',
    'word_byte_order': 'big-endian', 'length_field_bits': 64,
    'message_length_units': 'bits',
    'padding': '0x80 then zeros to byte offset 56 mod 64, then 64-bit big-endian bit length',
    'initial_state': list(INITIAL_STATE), 'round_constants': list(ROUND_CONSTANTS),
    'arithmetic': 'unsigned 32-bit words with additions reduced modulo 2^32',
    'preimage_inventory': GROUP_COUNTS, 'preimage_count': 258,
    'preimage_order': list(GROUP_COUNTS),
    'preimage_origin': 'exact complete W HashRecord preimages; no re-encoding or prefix substitution',
    'formal_target': 'actual imported W records, supplied digests and selected V/U/Q producer composition',
    'trace': 'all padded blocks with incoming state, complete 64-word schedule, all 64 round states and outgoing state',
}
SCOPE = {
    'domain': '258 complete selected producer SHA-256 computations',
    'selected_sha256_computation_checked': True,
    'selected_producer_digests_checked': True,
    'general_sha256_equivalence': False,
    'sha256_collision_resistance_remains_external': True,
    'general_grammar_parameter_derivation_remains_external': True,
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
UNMEASURED = ('X selected producer SHA-256 reference reconstruction and proof checking',
              *preimages.UNMEASURED[1:])


def _word(value: object) -> int:
    require(type(value) is int and 0 <= value <= WORD_MASK, 'unsigned 32-bit word required')
    return value


def rotate_right(value: int, count: int) -> int:
    _word(value)
    require(type(count) is int and 0 <= count < 32, '32-bit rotation count required')
    return ((value >> count) | (value << (32 - count))) & WORD_MASK


def pad_message(raw: bytes) -> bytes:
    require(type(raw) is bytes and len(raw) <= MAX_IMAGE_BYTES, 'bounded immutable SHA-256 input required')
    bit_length = len(raw) * 8
    require(bit_length < (1 << 64), 'SHA-256 bit length must fit the 64-bit field')
    zeros = (55 - len(raw)) % 64
    return raw + b'\x80' + bytes(zeros) + bit_length.to_bytes(8, 'big')


def message_schedule(block: bytes) -> tuple[int, ...]:
    require(type(block) is bytes and len(block) == 64, 'complete 64-byte SHA-256 block required')
    words = [int.from_bytes(block[offset:offset + 4], 'big') for offset in range(0, 64, 4)]
    for index in range(16, 64):
        x, y = words[index - 15], words[index - 2]
        s0 = rotate_right(x, 7) ^ rotate_right(x, 18) ^ (x >> 3)
        s1 = rotate_right(y, 17) ^ rotate_right(y, 19) ^ (y >> 10)
        words.append((words[index - 16] + s0 + words[index - 7] + s1) & WORD_MASK)
    return tuple(words)


def compression_rounds(state: tuple[int, ...], schedule: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    require(type(state) is tuple and len(state) == 8, 'eight-word immutable SHA-256 chaining state required')
    require(type(schedule) is tuple and len(schedule) == 64, 'complete immutable SHA-256 schedule required')
    for value in (*state, *schedule):
        _word(value)
    a, b, c, d, e, f, g, h = state
    rounds = []
    for constant, word in zip(ROUND_CONSTANTS, schedule, strict=True):
        big1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25)
        choice = (e & f) ^ ((~e & WORD_MASK) & g)
        temporary1 = (h + big1 + choice + constant + word) & WORD_MASK
        big0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22)
        majority = (a & b) ^ (a & c) ^ (b & c)
        temporary2 = (big0 + majority) & WORD_MASK
        a, b, c, d, e, f, g, h = ((temporary1 + temporary2) & WORD_MASK,
                                 a, b, c, (d + temporary1) & WORD_MASK, e, f, g)
        rounds.append((a, b, c, d, e, f, g, h))
    return tuple(rounds)


def compress_block(state: tuple[int, ...], block: bytes) -> tuple[int, ...]:
    rounds = compression_rounds(state, message_schedule(block))
    return tuple((old + current) & WORD_MASK for old, current in
                 zip(state, rounds[-1], strict=True))


def sha256_bytes(raw: bytes) -> bytes:
    """Return the complete FIPS-style SHA-256 result without a library hash call."""
    padded = pad_message(raw)
    state = INITIAL_STATE
    for offset in range(0, len(padded), 64):
        state = compress_block(state, padded[offset:offset + 64])
    return b''.join(word.to_bytes(4, 'big') for word in state)


def sha256_hex(raw: bytes) -> str:
    return sha256_bytes(raw).hex()


def compression_trace(raw: bytes) -> list[dict]:
    """Expose every selected padded block and intermediate reference state."""
    padded = pad_message(raw)
    state = INITIAL_STATE
    blocks = []
    for index, offset in enumerate(range(0, len(padded), 64)):
        block = padded[offset:offset + 64]
        schedule = message_schedule(block)
        rounds = compression_rounds(state, schedule)
        output = tuple((old + current) & WORD_MASK for old, current in zip(state, rounds[-1], strict=True))
        blocks.append({'index': index, 'block_hex': block.hex(),
                       'input_state': list(state), 'schedule': list(schedule),
                       'round_states': [list(state) for state in rounds], 'output_state': list(output)})
        state = output
    return blocks


def validate_trace(raw: bytes, blocks: list[dict], expected_digest: str) -> None:
    padded = pad_message(raw)
    require(type(blocks) is list and len(blocks) == len(padded) // 64,
            'complete SHA-256 compression trace required')
    state = INITIAL_STATE
    for index, record in enumerate(blocks):
        exact(record, {'index', 'block_hex', 'input_state', 'schedule', 'round_states', 'output_state'})
        block = padded[index * 64:(index + 1) * 64]
        require(type(record['index']) is int and record['index'] == index and
                record['block_hex'] == block.hex(), 'SHA-256 block order or complete padded bytes differ')
        for key, count in (('input_state', 8), ('schedule', 64), ('output_state', 8)):
            require(type(record[key]) is list and len(record[key]) == count,
                    'complete SHA-256 trace word array required')
            for value in record[key]:
                _word(value)
        require(tuple(record['input_state']) == state, 'SHA-256 initial state or block chaining differs')
        require(tuple(record['schedule']) == message_schedule(block), 'SHA-256 complete message schedule differs')
        require(type(record['round_states']) is list and len(record['round_states']) == 64,
                'all 64 SHA-256 round states required')
        for round_state in record['round_states']:
            require(type(round_state) is list and len(round_state) == 8, 'eight exact SHA-256 round state words required')
            for word in round_state:
                _word(word)
        rounds = compression_rounds(state, tuple(record['schedule']))
        require(tuple(tuple(words) for words in record['round_states']) == rounds, 'SHA-256 round transition differs')
        output = tuple((old + current) & WORD_MASK for old, current in zip(state, rounds[-1], strict=True))
        require(tuple(record['output_state']) == output, 'SHA-256 compression output differs')
        state = output
    require(b''.join(word.to_bytes(4, 'big') for word in state).hex() == digest(expected_digest),
            'SHA-256 final big-endian digest differs')


def selected_records(w: dict) -> list[dict]:
    """Flatten the exact W records in declared group/index order."""
    groups = preimages.preimage_groups(w['producer'])
    require(list(groups) == list(GROUP_COUNTS), 'selected SHA-256 group order differs')
    records = []
    for category, count in GROUP_COUNTS.items():
        require(type(groups[category]) is list and len(groups[category]) == count,
                'selected SHA-256 inventory differs')
        for index, record in enumerate(groups[category]):
            exact(record, {'json_hex', 'preimage_hex', 'digest'})
            raw = preimages._hex_bytes(record['preimage_hex'], MAX_IMAGE_BYTES)
            output = sha256_hex(raw)
            require(output == digest(record['digest']) == sha(raw),
                    'independent SHA-256 differs from W digest or hashlib')
            records.append({'category': category, 'index': index,
                            'preimage_hex': raw.hex(), 'digest': output, 'blocks': compression_trace(raw)})
    return records


def validate_hash_records(records: list[dict], w: dict) -> None:
    require(type(records) is list and len(records) == 258, 'complete 258-record SHA-256 inventory required')
    expected_groups = preimages.preimage_groups(w['producer'])
    position = 0
    for category, count in GROUP_COUNTS.items():
        require(type(expected_groups[category]) is list and len(expected_groups[category]) == count,
                'anchored W group inventory differs')
        for index, target in enumerate(expected_groups[category]):
            record = records[position]
            position += 1
            exact(record, {'category', 'index', 'preimage_hex', 'digest', 'blocks'})
            require(record['category'] == category and type(record['index']) is int and record['index'] == index,
                    'SHA-256 group/index/order differs from complete W inventory')
            require(record['preimage_hex'] == target['preimage_hex'] and record['digest'] == target['digest'],
                    'SHA-256 preimage or digest differs from actual W record')
            raw = preimages._hex_bytes(record['preimage_hex'], MAX_IMAGE_BYTES)
            validate_trace(raw, record['blocks'], record['digest'])
            require(sha256_hex(raw) == digest(record['digest']) == sha(raw),
                    'selected SHA-256 result differs from its complete input')


def validate_packet(packet: dict) -> preimages.PreparedProducerPreimages:
    exact(packet, {'schema', 'policy', 'base_commit', 'producer_preimages_packet',
                   'producer_preimages_packet_sha256', 'bindings', 'retained_w',
                   'profile', 'scope', 'claims', 'hash_records'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'producer SHA-256 schema/policy differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'producer SHA-256 profile/scope differs')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported producer SHA-256 root/closure claim')
    require(canonical(packet['retained_w']) == canonical(RETAINED_W_PINS), 'retained W anchors changed')
    raw_w = canonical(packet['producer_preimages_packet'])
    require(sha(raw_w) == packet['producer_preimages_packet_sha256'] == W_PACKET_SHA,
            'same-candidate W packet changed')
    require(canonical(packet['bindings']) == canonical(packet['producer_preimages_packet']['bindings']),
            'producer SHA-256 package/program binding differs')
    validate_hash_records(packet['hash_records'], packet['producer_preimages_packet'])
    return preimages.PreparedProducerPreimages(raw_w)


@dataclass(frozen=True, slots=True)
class PreparedProducerSha256:
    packet_bytes: bytes
    _preimages: preimages.PreparedProducerPreimages = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable producer SHA-256 packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical producer SHA-256 packet required')
        object.__setattr__(self, '_preimages', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def producer_preimages(self) -> preimages.PreparedProducerPreimages:
        return self._preimages


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_W_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained W input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained W input changed: ' + name)
        result[name] = raw
    return result


def prepare_producer_sha256(root: Path, packages: Path) -> PreparedProducerSha256:
    """Reconstruct W and evaluate all selected SHA-256 inputs without campaigns."""
    retained = read_retained(root)
    previous = preimages.prepare_producer_preimages(root, packages)
    require(previous.packet_bytes == retained[W_PACKET], 'fresh producer preimages differ from completed W')
    w = previous.packet
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'producer_preimages_packet': w, 'producer_preimages_packet_sha256': sha(previous.packet_bytes),
              'bindings': w['bindings'], 'retained_w': dict(RETAINED_W_PINS),
              'profile': dict(PROFILE), 'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS},
              'hash_records': selected_records(w)}
    prepared = PreparedProducerSha256(canonical(packet))
    require(retained == read_retained(root), 'retained W inputs changed during SHA-256 preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedProducerSha256, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external producer SHA-256 packet anchor differs')
    require(type(recomputed) is PreparedProducerSha256 and raw == recomputed.packet_bytes,
            'producer SHA-256 packet differs from independent reconstruction')
    PreparedProducerSha256(raw)


def summary(prepared: PreparedProducerSha256) -> dict:
    require(type(prepared) is PreparedProducerSha256, 'validated producer SHA-256 packet required')
    packet = prepared.packet
    records = packet['hash_records']
    groups = {}
    for category, count in GROUP_COUNTS.items():
        values = [record for record in records if record['category'] == category]
        lengths = [len(bytes.fromhex(value['preimage_hex'])) for value in values]
        groups[category] = {'images': count, 'preimage_bytes': sum(lengths),
                            'padded_bytes': sum(len(pad_message(bytes(length))) for length in lengths),
                            'compression_blocks': sum(len(pad_message(bytes(length))) // 64 for length in lengths)}
    blocks = sum(value['compression_blocks'] for value in groups.values())
    return {'algorithm': PROFILE['algorithm'], 'standard': PROFILE['standard'],
            'hash_groups': groups, 'complete_preimages': len(records),
            'complete_preimage_bytes': sum(value['preimage_bytes'] for value in groups.values()),
            'complete_padded_bytes': sum(value['padded_bytes'] for value in groups.values()),
            'compression_blocks': blocks, 'compression_rounds': 64 * blocks,
            'message_schedule_words': 64 * blocks, 'digest_bytes': 32 * len(records),
            'selected_program_hash': packet['bindings']['program_hash'],
            'producer_preimages_packet_sha256': W_PACKET_SHA,
            'python_reference_matches_hashlib': True,
            'selected_sha256_formal_claim': 'equality in the declared Lean SHA-256 reference semantics',
            'digest_authenticity_remains_external': True,
            'fresh_worker_output_captured': False, 'candidate_active': False, 'promotion_authorized': False}
