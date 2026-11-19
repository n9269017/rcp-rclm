"""Phase 17T: captured canonical ASCII JSON images to the protected S values.

The independent reference below is an iterative token/stack decoder.  It does
not delegate parsing to Python's JSON library.  It admits the bounded canonical
ASCII subset used by all eight selected JSON images in each S package.  General
Unicode JSON, escape syntax, floating point, physical capture, digest
authenticity, and execution of Python are outside the new Lean claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import prompt_routing as routing
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .resource_ledger import _no_links, digest, exact

BASE = '54793ebc6077129b999913064d906a33291a81ca'
SCHEMA = 'rcp-rclm.phase17t.captured-json-packet.v1'
POLICY = 'phase17t.canonical-ascii-json-to-protected-routing.v1'
S_ROOT = 'artifacts/development/phase17s/op-34ab34deffc7'
S_EXECUTION = S_ROOT + '/gate/execution.json'
S_EXECUTION_SHA = 'be8616400ffb8c66d1749478cbe9aa79e0d0729db6514d8b6c64206e4d8182c7'
S_PACKET = S_ROOT + '/gate/packet.json'
S_PACKET_SHA = '52bf7cfbfc6aae0582f7bba35c281f01394c358a16f228c55a22dd044c2d8fda'
S_SOURCE = S_ROOT + '/gate/PromptRouting.lean'
S_SOURCE_SHA = '98d8862773919f435d2cbc1d4a1dee3fd416f76ef46a7deabfbd1e485a4ef455'
RETAINED_S_PINS = {
    S_EXECUTION: S_EXECUTION_SHA, S_PACKET: S_PACKET_SHA, S_SOURCE: S_SOURCE_SHA,
    S_ROOT + '/operator-validation.json':
        '76d29044730e8b1057530bf46c343a4d572eec51bd928abc1e5296fd5b5f0a41',
}
MAX_BYTES = 24 * 1024 * 1024
MAX_JSON_BYTES = 65536
MAX_DEPTH = 20
MAX_ARRAY_LENGTH = 1024
MAX_OBJECT_FIELDS = 256
MAX_STRING_BYTES = 8192
MIN_INTEGER = -(1 << 63)
MAX_INTEGER = (1 << 63) - 1
JSON_FIELDS = (
    ('memory', routing.ROUTE_FILES['memory']),
    ('retrieval', routing.ROUTE_FILES['retrieval']),
    ('generator', routing.ROUTE_FILES['generator']),
    ('planner', routing.ROUTE_FILES['planner']),
    ('optimizer', routing.ROUTE_FILES['optimizer']),
    ('resource', routing.ROUTE_FILES['resource']),
    ('packageManifest', routing.PACKAGE_MANIFEST),
    ('adapterManifest', routing.ADAPTER_MANIFEST),
)
PROFILE = {
    'grammar': 'canonical unescaped printable ASCII JSON with signed 64-bit integers',
    'strings': 'bytes 32 through 126 except double quote and backslash; no escape syntax',
    'object_keys': 'strictly increasing ASCII lexical order; duplicate keys rejected',
    'arrays': 'complete ordered values; no trailing comma',
    'numbers': 'base-ten integers; no plus, leading zero, negative zero, fraction or exponent',
    'literals': ['null', 'false', 'true'],
    'whitespace': 'none outside strings; no BOM or trailing newline',
    'max_json_bytes': MAX_JSON_BYTES, 'max_depth': MAX_DEPTH,
    'depth_convention': 'root value depth zero; contained values and object keys add one',
    'max_array_length': MAX_ARRAY_LENGTH, 'max_object_fields': MAX_OBJECT_FIELDS,
    'max_string_bytes': MAX_STRING_BYTES,
    'integer_min': MIN_INTEGER, 'integer_max': MAX_INTEGER,
    'json_fields': [{'field': field, 'path': path} for field, path in JSON_FIELDS],
}
SCOPE = {
    'domain': 'eight complete captured JSON images per selected S package',
    'formal_target': 'decode exact image bytes into the existing S routing values',
    'byte_capture_remains_external': True,
    'digest_authenticity_remains_external': True,
    'python_execution_remains_external': True,
    'general_json_parser_equivalence': False,
    'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True,
    'historical_success_reports_are_not_proofs': True,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('T captured JSON preparation, decoding and proof checking', *routing.UNMEASURED[1:])


def _tokens(raw: bytes):
    """Tokenize the admitted raw grammar without JSON-library interpretation."""
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte in b'[]{}:,':
            yield chr(byte), None
            index += 1
        elif byte == 34:
            end = raw.find(b'"', index + 1)
            require(end >= 0, 'unterminated captured JSON string')
            body = raw[index + 1:end]
            require(len(body) <= MAX_STRING_BYTES, 'captured JSON string bound exceeded')
            require(all(32 <= value <= 126 and value != 92 for value in body),
                    'captured JSON string outside unescaped printable ASCII profile')
            yield 'string', body.decode('ascii')
            index = end + 1
        elif byte == 45 or 48 <= byte <= 57:
            start = index
            negative = byte == 45
            if negative:
                index += 1
                require(index < len(raw) and 49 <= raw[index] <= 57,
                        'captured JSON negative integer must have a nonzero leading digit')
            elif byte == 48:
                require(index + 1 == len(raw) or not 48 <= raw[index + 1] <= 57,
                        'captured JSON integer has a leading zero')
            while index < len(raw) and 48 <= raw[index] <= 57:
                index += 1
            require(index - start <= 19 + int(negative), 'captured JSON integer digit bound exceeded')
            value = int(raw[start:index])
            require(MIN_INTEGER <= value <= MAX_INTEGER, 'captured JSON integer outside signed 64-bit range')
            yield 'scalar', value
        else:
            matched = False
            for spelling, value in ((b'null', None), (b'false', False), (b'true', True)):
                if raw.startswith(spelling, index):
                    yield 'scalar', value
                    index += len(spelling)
                    matched = True
                    break
            require(matched, 'unexpected captured JSON byte or noncanonical whitespace')


def decode_captured_json(raw: bytes) -> object:
    """Decode one bounded document using explicit container states.

    Container depth is measured from root zero.  Object keys have the same
    depth as their values.  A depth-20 empty container is legal; a contained
    value or key at depth 21 is not.  The Lean decoder is separately recursive.
    """
    require(type(raw) is bytes and 0 < len(raw) <= MAX_JSON_BYTES,
            'bounded immutable captured JSON bytes required')
    missing = object()
    result = missing
    stack = []

    def expecting_value() -> bool:
        if not stack:
            return result is missing
        top = stack[-1]
        return top['state'] == 'value' or (top['kind'] == 'array' and top['state'] == 'first')

    def accept(value: object) -> None:
        nonlocal result
        require(len(stack) <= MAX_DEPTH, 'captured JSON nesting bound exceeded')
        require(expecting_value(), 'unexpected captured JSON value')
        if not stack:
            result = value
        else:
            top = stack[-1]
            if top['kind'] == 'array':
                require(len(top['items']) < MAX_ARRAY_LENGTH, 'captured JSON array bound exceeded')
                top['items'].append(value)
            else:
                top['items'][top['key']] = value
                top['key'] = None
            top['state'] = 'end'

    for kind, value in _tokens(raw):
        if kind in ('[', '{'):
            require(expecting_value(), 'unexpected captured JSON container')
            require(len(stack) <= MAX_DEPTH, 'captured JSON nesting bound exceeded')
            stack.append({'kind': 'array' if kind == '[' else 'object',
                          'items': [] if kind == '[' else {},
                          'state': 'first', 'key': None, 'previous': None})
        elif kind in (']', '}'):
            require(bool(stack), 'unmatched captured JSON closing delimiter')
            top = stack[-1]
            require(top['kind'] == ('array' if kind == ']' else 'object')
                    and top['state'] in ('first', 'end'),
                    'mismatched delimiter or incomplete captured JSON container')
            stack.pop()
            accept(top['items'])
        elif kind == ',':
            require(bool(stack) and stack[-1]['state'] == 'end', 'unexpected captured JSON comma')
            stack[-1]['state'] = 'value' if stack[-1]['kind'] == 'array' else 'key'
        elif kind == ':':
            require(bool(stack) and stack[-1]['kind'] == 'object'
                    and stack[-1]['state'] == 'colon', 'unexpected captured JSON colon')
            stack[-1]['state'] = 'value'
        elif (kind == 'string' and stack and stack[-1]['kind'] == 'object'
              and stack[-1]['state'] in ('first', 'key')):
            top = stack[-1]
            require(len(stack) <= MAX_DEPTH, 'captured JSON key nesting bound exceeded')
            require(len(top['items']) < MAX_OBJECT_FIELDS, 'captured JSON object bound exceeded')
            require(top['previous'] is None or top['previous'] < value,
                    'captured JSON object keys must be strictly increasing and unique')
            top['key'], top['previous'], top['state'] = value, value, 'colon'
        else:
            accept(value)
    require(not stack and result is not missing, 'incomplete captured JSON document')
    return result


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_S_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES,
                'missing/oversized retained S input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained S input changed: ' + name)
        result[name] = raw
    return result


def document_bytes(packet: dict, side: str) -> dict[str, bytes]:
    """Get raw JSON images from the complete nested S capture, in field order."""
    require(side in ('before', 'after'), 'captured JSON package side differs')
    rows = packet['routing_packet'][side]['files']
    require(type(rows) is list and len(rows) == len(routing.CAPTURE_PATHS),
            'captured S file inventory differs')
    files = {}
    for row, path in zip(rows, routing.CAPTURE_PATHS, strict=True):
        exact(row, {'path', 'size', 'sha256', 'hex'})
        require(row['path'] == path, 'captured S file path/order differs')
        files[path] = row
    result = {}
    for field_name, path in JSON_FIELDS:
        row = files[path]
        hex_value = row['hex']
        require(type(hex_value) is str and 0 < len(hex_value) <= 2 * MAX_JSON_BYTES
                and len(hex_value) % 2 == 0 and all(c in '0123456789abcdef' for c in hex_value),
                'bounded canonical captured JSON hexadecimal bytes required')
        raw = bytes.fromhex(hex_value)
        require(type(row['size']) is int and row['size'] == len(raw)
                and sha(raw) == digest(row['sha256']), 'captured JSON image identity differs')
        result[field_name] = raw
    return result


def _documents(packet: dict) -> dict[str, list[dict]]:
    result = {}
    for side in ('before', 'after'):
        images = document_bytes(packet, side)
        route_objects = packet['routing_packet'][side]['route_objects']
        rows = []
        for field_name, path in JSON_FIELDS:
            raw = images[field_name]
            value = decode_captured_json(raw)
            require(type(value) is dict, 'captured routing JSON root must be an object')
            # This cross-check concerns the unchanged production parser in the
            # admitted ASCII profile; it is not a proof of that implementation.
            production = load_json_strict(raw)
            require(canonical(value) == raw == canonical(production),
                    'independent/production captured JSON interpretation differs')
            if field_name in routing.ROUTE_FILES:
                require(canonical(value) == canonical(route_objects[field_name]),
                        'decoded captured JSON differs from the S routing value')
            rows.append({'field': field_name, 'path': path, 'size': len(raw), 'sha256': sha(raw)})
        result[side] = rows
    return result


def validate_packet(packet: dict) -> routing.PreparedPromptRouting:
    exact(packet, {'schema', 'policy', 'base_commit', 'routing_packet', 'routing_packet_sha256',
                   'bindings', 'retained_s', 'profile', 'documents', 'scope', 'claims'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'captured JSON policy differs')
    require(canonical(packet['profile']) == canonical(PROFILE)
            and canonical(packet['scope']) == canonical(SCOPE), 'captured JSON profile/scope differs')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported captured JSON root/closure claim')
    require(canonical(packet['retained_s']) == canonical(RETAINED_S_PINS), 'retained S anchors changed')
    raw = canonical(packet['routing_packet'])
    require(sha(raw) == packet['routing_packet_sha256'] == S_PACKET_SHA, 'same-candidate S packet changed')
    require(canonical(packet['bindings']) == canonical(packet['routing_packet']['bindings']),
            'captured JSON package/task binding differs')
    require(canonical(packet['documents']) == canonical(_documents(packet)),
            'captured JSON document inventory differs')
    # Validate the complete inherited protected packet once per prepared value.
    # Prior success reports cannot replace this input reconstruction or Lean.
    return routing.PreparedPromptRouting(raw)


@dataclass(frozen=True, slots=True)
class PreparedCapturedJson:
    packet_bytes: bytes
    _routing: routing.PreparedPromptRouting = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable captured JSON packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical captured JSON packet required')
        object.__setattr__(self, '_routing', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def routing(self) -> routing.PreparedPromptRouting:
        return self._routing


def prepare_captured_json(root: Path, packages: Path) -> PreparedCapturedJson:
    """Reconstruct selected packages and every inherited input; no workers/Lean."""
    retained = read_retained(root)
    previous = routing.prepare_prompt_routing(root, packages)
    require(previous.packet_bytes == retained[S_PACKET], 'fresh routing input differs from completed S')
    packet_s = previous.packet
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'routing_packet': packet_s, 'routing_packet_sha256': sha(previous.packet_bytes),
              'bindings': packet_s['bindings'], 'retained_s': dict(RETAINED_S_PINS),
              'profile': dict(PROFILE), 'scope': dict(SCOPE),
              'claims': {name: False for name in FALSE_CLAIMS}}
    packet['documents'] = _documents(packet)
    prepared = PreparedCapturedJson(canonical(packet))
    require(retained == read_retained(root), 'retained S inputs changed during captured JSON preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedCapturedJson, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external captured JSON packet anchor differs')
    require(type(recomputed) is PreparedCapturedJson and raw == recomputed.packet_bytes,
            'captured JSON packet differs from independent reconstruction')
    PreparedCapturedJson(raw)


def summary(prepared: PreparedCapturedJson) -> dict:
    require(type(prepared) is PreparedCapturedJson, 'validated captured JSON packet required')
    packet = prepared.packet
    return {
        'documents_per_package': len(JSON_FIELDS), 'packages': 2,
        'total_document_checks': 2 * len(JSON_FIELDS),
        'json_bytes_per_package': {side: sum(row['size'] for row in packet['documents'][side])
                                   for side in ('before', 'after')},
        'source_file_sha256': {side: {row['path']: row['sha256'] for row in packet['documents'][side]}
                               for side in ('before', 'after')},
        'json_fields': [name for name, _ in JSON_FIELDS],
        'original_protected_tasks': len(packet['routing_packet']['tasks']),
        'routing_packet_sha256': S_PACKET_SHA,
        'decoder_profile': PROFILE['grammar'],
    }
