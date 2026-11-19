"""Phase 17R: exact captured tensor bytes to the protected sparse semantics.

The selected input is the historical staged fixture used by Q.  A fresh physical
reconstruction supplies every byte.  The sparse encoding has a checked complete
round trip; it is not a list of caller-selected scores.  The new Lean certificate
checks the byte interpretation.  OS reads, Python execution, prompt routing and
the full transformer remain outside that formal refinement claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from .finite_kernel import (PreparedFiniteKernel, prepare_finite_kernel,
                            FALSE_CLAIMS, canonical, require, sha)
from .resource_ledger import _no_links, exact, digest

BASE = '54de3a0841bb747207e2721566e38f6582b8874b'
SCHEMA = 'rcp-rclm.phase17r.sparse-byte-refinement-packet.v1'
POLICY = 'phase17r.exact-captured-int16-sparse-profile.v1'
WIDTH, VOCAB, DIVISOR, CLIP, EOS, MAX_TOKENS = 320, 260, 2048, 15, 258, 16
TENSOR_BYTES = 2 * WIDTH * WIDTH
MAX_BYTES = 20 * 1024 * 1024
Q_ROOT = 'artifacts/development/phase17q/op-5d5d0e2fe033'
Q_EXECUTION = Q_ROOT + '/gate/execution.json'
Q_EXECUTION_SHA = 'cfc8ea42284efe018cdf6abb675db1969d5a2e35b052314197fdcac1004e55a1'
Q_PACKET = Q_ROOT + '/gate/packet.json'
Q_PACKET_SHA = 'b6dd8df26fb7efc25c6fed6cc7832bf65a42b933fd2d1276346695bd8451c9e5'
Q_SOURCE = Q_ROOT + '/gate/FiniteKernel.lean'
Q_SOURCE_SHA = '7da29c3aebf34671927e13ff781853b792e61ebda46b1744686a2548e42baf80'
RETAINED_Q_PINS = {
    Q_EXECUTION: Q_EXECUTION_SHA,
    Q_PACKET: Q_PACKET_SHA,
    Q_SOURCE: Q_SOURCE_SHA,
    Q_ROOT + '/operator-validation.json':
        '2512a13dd8600755eec122240d88a831987e62101bd761c53efa5181eb0bb26b',
}
PROFILE = {
    'tensor_bytes': TENSOR_BYTES, 'width': WIDTH, 'vocabulary': VOCAB,
    'element': 'signed_int16_little_endian',
    'word_index': 'target * 320 + current', 'score_divisor': DIVISOR,
    'require_integral_scores': True, 'clip': CLIP,
    'mass': '2 ** (clip(score) - min(clipped_row))',
    'greedy': 'maximum RAW score; lowest token id on ties',
    'eos': EOS, 'other_non_byte_tokens_stop_unsuccessfully': True,
    'maximum_tokens': MAX_TOKENS,
}
SCOPE = {
    'domain': 'captured bytes of the selected inherited sparse transition tensor',
    'complete_image_round_trip': True,
    'score_domain': 'all 260 by 260 conditional score cells in each package',
    'goal_domain': 'eleven protected continuations from independently bound effective markers',
    'byte_capture_and_python_execution_remain_trusted': True,
    'prompt_routing_remains_external': True,
    'full_transformer_equivalence': False,
    'historical_success_reports_are_not_proofs': True,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = (
    'R preparation, byte extraction and proof checking',
    'bootstrap and archive validation', 'physical staging and observation',
    'hashing and canonical parsing', 'Python overhead and journal I/O',
    'CPU time', 'accelerator time', 'memory', 'storage', 'energy',
    'active promotion and rollback',
)


def _int(value: object, lo: int, hi: int, label: str) -> int:
    require(type(value) is int and lo <= value <= hi, label)
    return value


def signed16(lo: int, hi: int) -> int:
    """Explicit byte arithmetic, independently checked against struct in tests."""
    _int(lo, 0, 255, 'low byte outside uint8')
    _int(hi, 0, 255, 'high byte outside uint8')
    unsigned = lo + 256 * hi
    return unsigned - 65536 if unsigned >= 32768 else unsigned


def _raw(raw: bytes) -> None:
    require(type(raw) is bytes and len(raw) == TENSOR_BYTES,
            'exact immutable 204800-byte tensor required')


def encode_tensor(raw: bytes) -> dict:
    _raw(raw)
    return {'byte_length': TENSOR_BYTES,
            'nonzero_bytes': [[offset, value] for offset, value in enumerate(raw) if value]}


def decode_tensor(image: dict) -> bytes:
    exact(image, {'byte_length', 'nonzero_bytes'})
    require(type(image['byte_length']) is int and image['byte_length'] == TENSOR_BYTES,
            'tensor byte length differs')
    rows = image['nonzero_bytes']
    require(type(rows) is list and len(rows) <= TENSOR_BYTES, 'bounded sparse byte inventory required')
    result = bytearray(TENSOR_BYTES)
    previous = -1
    for row in rows:
        require(type(row) is list and len(row) == 2, 'exact sparse byte pair required')
        offset = _int(row[0], 0, TENSOR_BYTES - 1, 'sparse byte offset out of bounds')
        value = _int(row[1], 1, 255, 'canonical nonzero byte required')
        require(offset > previous, 'sparse byte offsets must be strictly increasing')
        result[offset] = value
        previous = offset
    return bytes(result)


def _score_row(raw: bytes, current: int) -> list[int]:
    row = []
    for target in range(VOCAB):
        offset = 2 * (target * WIDTH + current)
        value = signed16(raw[offset], raw[offset + 1])
        require(value % DIVISOR == 0, 'nonintegral sparse score')
        row.append(value // DIVISOR)
    return row


def scores_from_tensor(raw: bytes) -> list[list[int]]:
    _raw(raw)
    return [_score_row(raw, current) for current in range(VOCAB)]


def masses_from_scores(row: list[int]) -> list[int]:
    require(type(row) is list and len(row) == VOCAB, 'complete score row required')
    for value in row:
        _int(value, -16, 15, 'signed integral score outside int16 profile')
    clipped = [max(-CLIP, min(CLIP, value)) for value in row]
    minimum = min(clipped)
    return [1 << (value - minimum) for value in clipped]


def decode_greedy(raw: bytes, marker: int, max_tokens: int = MAX_TOKENS) -> dict:
    """Bounded raw-score greedy interpreter; tokens include the stopping token.

    Distribution clipping does not change the raw-score tie-breaking rule.
    No supplied goal, target, probability row or success flag is an input.
    """
    _raw(raw)
    current = _int(marker, 0, VOCAB - 1, 'initial token outside vocabulary')
    _int(max_tokens, 1, MAX_TOKENS, 'greedy token bound differs')
    tokens, steps = [], []
    for _ in range(max_tokens):
        row = _score_row(raw, current)
        selected = min(range(VOCAB), key=lambda token: (-row[token], token))
        ordered = sorted(row, reverse=True)
        tokens.append(selected)
        steps.append({'current': current, 'selected': selected,
                      'score': row[selected], 'runner_up': ordered[1]})
        if selected == EOS:
            return {'tokens': tokens, 'stopped_on_eos': True, 'termination': 'eos', 'steps': steps}
        if selected >= 256:
            return {'tokens': tokens, 'stopped_on_eos': False, 'termination': 'non_byte_token', 'steps': steps}
        current = selected
    return {'tokens': tokens, 'stopped_on_eos': False, 'termination': 'token_limit', 'steps': steps}


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_Q_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES,
                'missing/oversized retained Q input: ' + name)
        data = path.read_bytes()
        require(sha(data) == expected, 'retained Q input changed: ' + name)
        result[name] = data
    return result


def validate_packet(p: dict) -> PreparedFiniteKernel:
    exact(p, {'schema', 'policy', 'base_commit', 'finite_packet', 'finite_packet_sha256',
              'bindings', 'retained_q', 'profile', 'before', 'after', 'markers', 'targets',
              'tensor_sha256', 'scope', 'claims'})
    require(p['schema'] == SCHEMA and p['policy'] == POLICY and p['base_commit'] == BASE,
            'sparse refinement policy differs')
    require(canonical(p['profile']) == canonical(PROFILE) and
            canonical(p['scope']) == canonical(SCOPE), 'sparse interpretation or scope changed')
    require(canonical(p['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported full-root/physical/closure claim')
    require(canonical(p['retained_q']) == canonical(RETAINED_Q_PINS), 'retained Q anchors changed')
    finite_raw = canonical(p['finite_packet'])
    require(p['finite_packet_sha256'] == Q_PACKET_SHA == sha(finite_raw),
            'same-candidate Q packet changed')
    # Refuse malformed new fields before the expensive inherited semantic
    # reconstruction. The complete Q validation still runs before any return.
    require(canonical(p['bindings']) == canonical(p['finite_packet']['bindings']),
            'sparse candidate/parent binding differs')
    semantic = p['finite_packet']['protected_packet']
    markers, targets = [], []
    for measured, task in zip(semantic['before']['goals'], semantic['task_contract']['tasks'], strict=True):
        require(measured['task_id'] == task['task_id'], 'task order changed')
        markers.append(measured['effective_marker'])
        targets.append(list(task['expected_tokens']))
    require(canonical(p['markers']) == canonical(markers) and
            canonical(p['targets']) == canonical(targets) and
            len(markers) == 11 and sum(map(len, targets)) == 28,
            'protected marker/target interpretation differs')
    require(canonical(p['tensor_sha256']) == canonical({side: semantic[side]['tensor_sha256']
                                                       for side in ('before', 'after')}),
            'tensor identity changed')
    for side in ('before', 'after'):
        observation = semantic[side]
        raw = decode_tensor(p[side])
        require(raw == bytes.fromhex(observation['tensor_hex']) and
                sha(raw) == observation['tensor_sha256'], 'complete tensor byte round trip differs')
        require(encode_tensor(raw) == p[side], 'noncanonical sparse byte image')
        rows = scores_from_tensor(raw)
        # Every conditional cell is checked, including contexts not present in
        # the eleven selected goals.  The before/after images are decoded apart.
        for current, row in enumerate(rows):
            index = observation['row_selectors'][current]
            require(row == observation['score_dictionary'][index], 'byte-derived score row differs')
            masses = masses_from_scores(row)
            require([mass - 1 for mass in masses] == observation['mass_minus_one_dictionary'][index] and
                    sum(masses) == observation['row_totals'][index], 'byte-derived normalization differs')
        for index, (marker, target) in enumerate(zip(markers, targets, strict=True)):
            measured = observation['goals'][index]
            require(measured['effective_marker'] == marker and measured['tokens'] == target,
                    'independently observed goal differs')
            decoded = decode_greedy(raw, marker)
            require(decoded['stopped_on_eos'] is True and decoded['tokens'] == target,
                    'captured tensor does not execute protected continuation')
    return PreparedFiniteKernel(finite_raw)


@dataclass(frozen=True, slots=True)
class PreparedSparseRefinement:
    packet_bytes: bytes
    _finite: PreparedFiniteKernel = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable sparse refinement packet required')
        value = load_json_strict(self.packet_bytes)
        require(canonical(value) == self.packet_bytes, 'canonical sparse refinement packet required')
        object.__setattr__(self, '_finite', validate_packet(value))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def finite(self) -> PreparedFiniteKernel:
        return self._finite


def prepare_sparse_refinement(root: Path, packages: Path) -> PreparedSparseRefinement:
    """Fresh captured inputs, without workers, challenges or compiler runs."""
    retained = read_retained(root)
    finite = prepare_finite_kernel(root, packages)
    require(finite.packet_bytes == retained[Q_PACKET], 'fresh finite input differs from completed Q')
    observations = finite.protected().packet
    markers = [goal['effective_marker'] for goal in observations['before']['goals']]
    targets = [list(task['expected_tokens']) for task in observations['task_contract']['tasks']]
    p = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
         'finite_packet': finite.packet, 'finite_packet_sha256': sha(finite.packet_bytes),
         'bindings': finite.packet['bindings'], 'retained_q': dict(RETAINED_Q_PINS),
         'profile': dict(PROFILE), 'markers': markers, 'targets': targets,
         'tensor_sha256': {side: observations[side]['tensor_sha256'] for side in ('before', 'after')},
         'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS}}
    for side in ('before', 'after'):
        p[side] = encode_tensor(bytes.fromhex(observations[side]['tensor_hex']))
    prepared = PreparedSparseRefinement(canonical(p))
    require(retained == read_retained(root), 'retained Q inputs changed during R preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedSparseRefinement, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external refinement packet anchor differs')
    require(type(recomputed) is PreparedSparseRefinement and raw == recomputed.packet_bytes,
            'refinement packet differs from fresh captured-byte reconstruction')
    PreparedSparseRefinement(raw)
