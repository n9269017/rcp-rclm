"""Phase 17S: captured routing inputs to the original protected task prompts.

The reference interpreter reads complete package route objects and complete
adapter bytes.  A route-hit flag, selected family, or effective marker is never
an input to that interpreter.  Capture, JSON deserialization, cryptographic
identity, and execution of Python remain outside the Lean refinement claim.
The admitted JSON profile excludes Boolean values in numeric route fields;
Python's broader bool/int coercion is not silently claimed to be verified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v4.phase14.tasks import decode_task
from . import sparse_refinement as sparse
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .materialized import snapshot
from .protected_semantics import protected_tasks
from .resource_ledger import _no_links, digest, exact

BASE = '4c58fe4d47e3d8fc8fb2e3aba5c759718fe5b8ae'
SCHEMA = 'rcp-rclm.phase17s.protected-prompt-routing-packet.v1'
POLICY = 'phase17s.captured-package-routing-to-protected-sparse-decoder.v1'
R_ROOT = 'artifacts/development/phase17r/op-0599da3eeb23'
R_EXECUTION = R_ROOT + '/gate/execution.json'
R_EXECUTION_SHA = 'ed6c5d2c2d5e06e8621842c6932888dcfe057975d2640e40fc9e6c438d50dbed'
R_PACKET = R_ROOT + '/gate/packet.json'
R_PACKET_SHA = '505d704bbab6d1f72d22dd36f5f75ea128057ffb48b11000937728abaabb07ad'
R_SOURCE = R_ROOT + '/gate/SparseRefinement.lean'
R_SOURCE_SHA = '335f3fbcf95e9e2f6f8abe6ccc93ac97385cc872954c9454dabdc0209801e808'
RETAINED_R_PINS = {
    R_EXECUTION: R_EXECUTION_SHA, R_PACKET: R_PACKET_SHA,
    R_SOURCE: R_SOURCE_SHA,
    R_ROOT + '/operator-validation.json':
        'ceab7c9ed9f778f92977c451241e448c59eb11c11c28fe46fb500b43eddecc26',
}
MAX_BYTES = 24 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_PROMPT_BYTES = 4096
ADAPTER_BYTES = 5120
ADAPTER_NAME = 'adapter.layers.00.attn_output.B'
ADAPTER_PATH = 'base/model/adapters/tensors/adapter.layers.00.attn_output.B.i16le.bin'
ADAPTER_MANIFEST = 'base/model/adapters/manifest.json'
PACKAGE_MANIFEST = 'base/package_manifest.json'
TENSOR_PATH = 'base/model/tensors/model.layers.00.attn_output.weight.i16le.bin'
ROUTE_FILES = {
    'memory': 'base/memory/memory_manifest.json',
    'retrieval': 'base/retrieval/index_manifest.json',
    'generator': 'base/policies/generator_policy.json',
    'planner': 'base/policies/planner_policy.json',
    'optimizer': 'base/training/optimizer_state.json',
    'resource': 'base/runtime/resource_measurement.json',
}
CAPTURE_PATHS = tuple(sorted((*ROUTE_FILES.values(), ADAPTER_PATH,
                              ADAPTER_MANIFEST, PACKAGE_MANIFEST)))
FAMILIES = ('memory_retrieval', 'generator_planner', 'adapter_optimizer', 'model_weights')
NUMERIC_ROUTE_FIELDS = frozenset({'query_marker_token_id', 'route_marker_token_id',
                                 'slot_token_id', 'offset_bytes', 'commitment_prefix_u16'})
PROFILE = {
    'task_domain': 'eleven original protected prompts and their pinned challenge bindings',
    'hidden_route_selection': 'exactly one of four independently evaluated families',
    'hidden_route_lookup': 'exactly one matching commitment per required route list',
    'legacy_lookup': 'first matching query marker and exact_terminal_byte entry',
    'legacy_order': ['adapter', 'planner', 'memory'],
    'legacy_adapter_magic': [87, 86, 8, 1],
    'legacy_failure_marker': 'marker at the start of the legacy chain',
    'phase14_route_marker': 87,
    'challenge_slot': '180 + unsigned hexadecimal commitment prefix[0:8] mod 64',
    'adapter_name': ADAPTER_NAME, 'adapter_bytes': ADAPTER_BYTES,
    'adapter_word_order': 'signed_int16_little_endian',
    'weight_selection': 'maximum raw score; lowest token id on ties',
    'numeric_route_fields': 'JSON integers; Boolean numeric coercion excluded',
}
SCOPE = {
    'domain': 'captured routing objects and adapter bytes for the selected protected sparse tasks',
    'complete_route_lists_and_array_order_retained': True,
    'original_prompt_bytes_bound': True,
    'byte_capture_and_json_parsing_remain_external': True,
    'python_execution_remains_external': True,
    'cryptographic_identity_and_architecture_selection_remain_external': True,
    'full_transformer_equivalence': False,
    'general_python_json_coercion_equivalence': False,
    'historical_success_reports_are_not_proofs': True,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('S preparation, prompt routing and proof checking', *sparse.UNMEASURED[1:])


def _integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label)
    return value


def _hex(value: object, maximum: int, label: str) -> bytes:
    require(type(value) is str and len(value) % 2 == 0 and len(value) <= 2 * maximum
            and all(c in '0123456789abcdef' for c in value), label)
    return bytes.fromhex(value)


def _json_profile(value: object, depth: int = 0) -> None:
    """Bound the captured AST; numeric route Booleans are outside this profile."""
    require(depth <= 20, 'routing JSON nesting bound exceeded')
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(-(1 << 63) <= value < (1 << 63), 'routing JSON integer bound exceeded')
    elif type(value) is str:
        require(len(value.encode('utf-8')) <= 8192, 'routing JSON string bound exceeded')
    elif type(value) is list:
        require(len(value) <= 1024, 'routing JSON list bound exceeded')
        for item in value:
            _json_profile(item, depth + 1)
    elif type(value) is dict:
        require(len(value) <= 256 and all(type(k) is str for k in value),
                'routing JSON object shape differs')
        for key, item in value.items():
            _json_profile(key, depth + 1)
            require(not (key in NUMERIC_ROUTE_FIELDS and type(item) is bool),
                    'Boolean numeric route field outside admitted profile')
            _json_profile(item, depth + 1)
    else:
        require(False, 'routing JSON contains an unsupported value')


def encode_adapter(raw: bytes) -> dict:
    require(type(raw) is bytes and len(raw) == ADAPTER_BYTES, 'complete immutable adapter bytes required')
    return {'byte_length': ADAPTER_BYTES,
            'nonzero_bytes': [[offset, value] for offset, value in enumerate(raw) if value]}


def decode_adapter(image: dict) -> bytes:
    exact(image, {'byte_length', 'nonzero_bytes'})
    require(type(image['byte_length']) is int and image['byte_length'] == ADAPTER_BYTES,
            'adapter image length differs')
    rows = image['nonzero_bytes']
    require(type(rows) is list and len(rows) <= ADAPTER_BYTES, 'bounded adapter support required')
    raw, previous = bytearray(ADAPTER_BYTES), -1
    for row in rows:
        require(type(row) is list and len(row) == 2, 'exact adapter support pair required')
        offset = _integer(row[0], 0, ADAPTER_BYTES - 1, 'adapter offset outside image')
        value = _integer(row[1], 1, 255, 'adapter support must contain nonzero bytes')
        require(offset > previous, 'adapter offsets must be strictly increasing')
        raw[offset], previous = value, offset
    return bytes(raw)


def signed_words(raw: bytes, offset: object) -> tuple[int, ...] | None:
    """Read four words, retaining the production interpreter's unaligned-offset rule."""
    require(type(raw) is bytes, 'immutable adapter bytes required')
    if type(offset) is not int or offset < 0 or offset + 8 > len(raw):
        return None
    return tuple(sparse.signed16(raw[offset + 2 * i], raw[offset + 2 * i + 1])
                 for i in range(4))


def unique_route(value: object, commitment: str, key: str = 'phase14_routes') -> dict | None:
    if type(value) is not dict or type(value.get(key)) is not list:
        return None
    matches = [row for row in value[key]
               if type(row) is dict and row.get('challenge_commitment_hash') == commitment]
    return matches[0] if len(matches) == 1 else None


def legacy_route(value: object, marker: int, key: str) -> int | None:
    """First match matters: a malformed first match cannot expose a later route."""
    if type(value) is not dict or type(value.get(key)) is not list:
        return None
    for row in value[key]:
        if (type(row) is dict and type(row.get('query_marker_token_id')) is int
                and row['query_marker_token_id'] == marker
                and row.get('match_mode') == 'exact_terminal_byte'):
            target = row.get('route_marker_token_id')
            return target if type(target) is int else None
    return None


def legacy_chain(objects: dict, adapter: bytes, marker: int) -> tuple[int, bool]:
    current = marker
    if current == 87:
        if signed_words(adapter, 0) != (87, 86, 8, 1):
            return marker, False
        current = 86
    if current == 86:
        target = legacy_route(objects['planner'], current, 'routes')
        if target is None:
            return marker, False
        current = target
    if current == 85:
        target = legacy_route(objects['retrieval'], current, 'entries')
        if target is None:
            return marker, False
        current = target
    return current, True


def greedy_weight_token(tensor: bytes, current: int) -> int:
    require(type(tensor) is bytes and len(tensor) == sparse.TENSOR_BYTES,
            'complete captured transition tensor required')
    _integer(current, 0, 259, 'weight route query outside vocabulary')
    best, highest = 0, None
    for target in range(260):
        offset = 2 * (320 * target + current)
        word = sparse.signed16(tensor[offset], tensor[offset + 1])
        require(word % 2048 == 0, 'weight route score is nonintegral')
        score = word // 2048
        if highest is None or score > highest:
            best, highest = target, score
    return best


def _pair_hit(left: dict | None, right: dict | None, slot: int) -> bool:
    return bool(left and right and all(type(row.get('slot_token_id')) is int
                and row['slot_token_id'] == slot
                and type(row.get('route_marker_token_id')) is int
                and row['route_marker_token_id'] == 87 for row in (left, right)))


def route_reference(objects: dict, adapter: bytes, tensor: bytes, *,
                    adapter_sha256: str, tensor_manifest_hash: str,
                    task_id: str, prompt: bytes, challenge: dict | None) -> dict:
    """Interpret original prompt data; no selected route or expected output input."""
    exact(objects, set(ROUTE_FILES))
    require(all(type(value) is dict for value in objects.values()), 'routing source objects required')
    _json_profile(objects)
    require(type(prompt) is bytes and 0 < len(prompt) <= MAX_PROMPT_BYTES,
            'nonempty bounded original prompt bytes required')
    require(type(task_id) is str and 0 < len(task_id) <= 180, 'task identity required')
    digest(adapter_sha256); digest(tensor_manifest_hash)
    require(type(adapter) is bytes and len(adapter) == ADAPTER_BYTES, 'complete adapter image required')
    original, marker, hit, family = prompt[-1], prompt[-1], True, None
    if challenge is not None:
        exact(challenge, {'task_id', 'commitment_hash', 'slot_token_id'})
        commitment = digest(challenge['commitment_hash'])
        slot = _integer(challenge['slot_token_id'], 180, 243, 'challenge slot outside profile')
        require(challenge['task_id'] == task_id and original == slot
                and slot == 180 + int(commitment[:8], 16) % 64,
                'original prompt/challenge identity or slot binding differs')
        memory = unique_route(objects['memory'], commitment)
        retrieval = unique_route(objects['retrieval'], commitment)
        generator = unique_route(objects['generator'], commitment)
        planner = unique_route(objects['planner'], commitment)
        adapter_route = unique_route(objects['optimizer'], commitment)
        adapter_hit = False
        if adapter_route is not None:
            prefix = adapter_route.get('commitment_prefix_u16')
            offset = adapter_route.get('offset_bytes')
            observed = signed_words(adapter, offset)
            # The production function uses the stored prefix. It does not
            # rederive it from the commitment or consult its unused slot field.
            adapter_hit = (type(prefix) is int and observed is not None
                           and observed == (slot, 87, prefix, 1)
                           and adapter_route.get('tensor_sha256') == adapter_sha256)
        weight = unique_route(objects['resource'], commitment, 'phase14_weight_routes')
        selected = greedy_weight_token(tensor, slot)
        weight_hit = bool(weight and type(weight.get('slot_token_id')) is int
                          and weight['slot_token_id'] == slot
                          and type(weight.get('route_marker_token_id')) is int
                          and weight['route_marker_token_id'] == 87
                          and weight.get('tensor_manifest_hash') == tensor_manifest_hash
                          and selected == 87)
        hits = [name for name, present in zip(FAMILIES,
                (_pair_hit(memory, retrieval, slot), _pair_hit(generator, planner, slot),
                 adapter_hit, weight_hit), strict=True) if present]
        hit = len(hits) == 1
        family = hits[0] if hit else None
        marker = 87 if hit else original
    marker, legacy_hit = legacy_chain(objects, adapter, marker)
    if challenge is not None or original in (85, 86, 87):
        hit = hit and legacy_hit
    _integer(marker, 0, 255, 'effective prompt marker is not a byte')
    return {'task_id': task_id, 'original_marker': original, 'effective_marker': marker,
            'route_hit': hit, 'selected_route_family': family}


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_R_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES,
                'missing/oversized retained R input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained R input changed: ' + name)
        result[name] = raw
    return result


def _tasks(tasks: object, sparse_packet: dict) -> None:
    contract = sparse_packet['finite_packet']['protected_packet']['task_contract']['tasks']
    require(type(tasks) is list and len(tasks) == len(contract) == 11, 'eleven original protected tasks required')
    for task, pinned in zip(tasks, contract, strict=True):
        exact(task, {'task_id', 'prompt_hex', 'prompt_sha256', 'original_marker', 'expected_tokens', 'challenge'})
        prompt = _hex(task['prompt_hex'], MAX_PROMPT_BYTES, 'canonical prompt bytes required')
        require(prompt and task['task_id'] == pinned['task_id'] and
                sha(prompt) == task['prompt_sha256'] == pinned['prompt_sha256'],
                'original protected prompt identity differs')
        require(type(task['original_marker']) is int and
                task['original_marker'] == pinned['original_marker'] == prompt[-1],
                'original marker is not the final prompt byte')
        require(canonical(task['expected_tokens']) == canonical(pinned['expected_tokens']),
                'original protected completion changed')
        if pinned['challenge_commitment'] is None:
            require(task['challenge'] is None, 'legacy task assigned a hidden challenge')
        else:
            challenge = task['challenge']
            exact(challenge, {'task_id', 'commitment_hash', 'slot_token_id'})
            require(challenge['task_id'] == task['task_id'] and
                    challenge['commitment_hash'] == pinned['challenge_commitment'],
                    'hidden challenge identity differs')
            slot = _integer(challenge['slot_token_id'], 180, 243, 'challenge slot outside profile')
            require(slot == prompt[-1] == 180 + int(digest(challenge['commitment_hash'])[:8], 16) % 64,
                    'hidden commitment slot derivation differs')


def _typed_rows(sparse_packet: dict, side: str) -> dict[str, dict]:
    joint = sparse_packet['finite_packet']['protected_packet']['joint_packet']
    state = joint['typed_binding']['predecessor' if side == 'before' else 'candidate']
    rows = [row for value in state.values() if type(value) is list
            for row in value if type(row) is dict and set(row) == {'path', 'size', 'sha256'}]
    require(len(rows) == len({row['path'] for row in rows}) == 164, 'R typed physical inventory differs')
    return {row['path']: row for row in rows}


def _files(rows: object, anchors: dict[str, dict]) -> dict[str, bytes]:
    require(type(rows) is list and len(rows) == len(CAPTURE_PATHS), 'complete routing file inventory required')
    result = {}
    for row, wanted in zip(rows, CAPTURE_PATHS, strict=True):
        exact(row, {'path', 'size', 'sha256', 'hex'})
        require(row['path'] == wanted and wanted in anchors, 'routing source path/order differs')
        raw = _hex(row['hex'], MAX_FILE_BYTES, 'bounded canonical routing file bytes required')
        require(type(row['size']) is int and row['size'] == len(raw) == anchors[wanted]['size']
                and sha(raw) == row['sha256'] == anchors[wanted]['sha256'],
                'routing bytes do not match the R physical package')
        result[wanted] = raw
    return result


def capture_metadata(files: dict[str, bytes]) -> tuple[dict, bytes, str, str]:
    """Decode every captured JSON object; retain arrays, duplicates and order."""
    exact(files, set(CAPTURE_PATHS))
    decoded = {}
    for name in (*ROUTE_FILES.values(), ADAPTER_MANIFEST, PACKAGE_MANIFEST):
        obj = load_json_strict(files[name])
        require(type(obj) is dict and canonical(obj) == files[name], 'canonical complete routing object required')
        _json_profile(obj)
        decoded[name] = obj
    objects = {key: decoded[path] for key, path in ROUTE_FILES.items()}
    manifest = decoded[ADAPTER_MANIFEST]
    require(type(manifest.get('records')) is list, 'adapter record inventory missing')
    record = next((row for row in manifest['records'] if type(row) is dict
                   and type(row.get('spec')) is dict and row['spec'].get('name') == ADAPTER_NAME), None)
    require(record is not None, 'selected adapter record missing')
    spec = record['spec']
    require(spec.get('path') == ADAPTER_PATH[5:] and spec.get('byte_order') == 'little'
            and spec.get('dtype') == 'int16' and spec.get('role') == 'adapter_b'
            and canonical(spec.get('shape')) == canonical([320, 8])
            and type(spec.get('size_bytes')) is int and spec['size_bytes'] == ADAPTER_BYTES,
            'selected adapter specification differs')
    raw = files[ADAPTER_PATH]
    require(len(raw) == ADAPTER_BYTES and sha(raw) == record.get('sha256'), 'selected adapter record/bytes differ')
    package = decoded[PACKAGE_MANIFEST]
    return objects, raw, digest(record['sha256']), digest(package.get('tensor_manifest_hash'))


def _reference_observations(capture: dict, tensor: bytes, tasks: list[dict]) -> list[dict]:
    return [route_reference(capture['route_objects'], decode_adapter(capture['adapter_image']), tensor,
                adapter_sha256=capture['adapter_sha256'], tensor_manifest_hash=capture['tensor_manifest_hash'],
                task_id=task['task_id'], prompt=bytes.fromhex(task['prompt_hex']), challenge=task['challenge'])
            for task in tasks]


def _capture_check(capture: dict, sparse_packet: dict, side: str, tasks: list[dict]) -> None:
    exact(capture, {'package_hash', 'files', 'route_objects', 'adapter_image', 'adapter_sha256',
                    'tensor_manifest_hash', 'observations'})
    expected_hash = sparse_packet['bindings']['predecessor_physical_hash' if side == 'before'
                                               else 'candidate_physical_hash']
    require(capture['package_hash'] == expected_hash, 'routing capture belongs to another physical package')
    files = _files(capture['files'], _typed_rows(sparse_packet, side))
    objects, adapter, adapter_sha, tensor_manifest = capture_metadata(files)
    require(canonical(capture['route_objects']) == canonical(objects), 'routing object differs from captured JSON')
    require(decode_adapter(capture['adapter_image']) == adapter
            and encode_adapter(adapter) == capture['adapter_image'], 'complete adapter byte round trip differs')
    require(capture['adapter_sha256'] == adapter_sha and capture['tensor_manifest_hash'] == tensor_manifest,
            'routing manifest identity differs')
    tensor = sparse.decode_tensor(sparse_packet[side])
    observations = _reference_observations(capture, tensor, tasks)
    require(canonical(capture['observations']) == canonical(observations), 'routing observations were not independently derived')
    goals = sparse_packet['finite_packet']['protected_packet'][side]['goals']
    require(len(observations) == len(goals) == 11, 'routing/goal domain differs')
    for row, goal in zip(observations, goals, strict=True):
        require(row['route_hit'] is True and row['task_id'] == goal['task_id']
                and row['effective_marker'] == goal['effective_marker'],
                'original prompt does not derive the R protected marker')


def validate_packet(packet: dict) -> sparse.PreparedSparseRefinement:
    exact(packet, {'schema', 'policy', 'base_commit', 'sparse_packet', 'sparse_packet_sha256',
                   'bindings', 'retained_r', 'profile', 'tasks', 'before', 'after', 'scope', 'claims'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'prompt routing policy differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and
            canonical(packet['scope']) == canonical(SCOPE), 'prompt routing scope/profile changed')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}), 'unsupported root/closure claim')
    require(canonical(packet['retained_r']) == canonical(RETAINED_R_PINS), 'retained R anchors changed')
    raw = canonical(packet['sparse_packet'])
    require(sha(raw) == packet['sparse_packet_sha256'] == R_PACKET_SHA, 'same-candidate R packet changed')
    require(canonical(packet['bindings']) == canonical(packet['sparse_packet']['bindings']), 'routing candidate binding differs')
    _tasks(packet['tasks'], packet['sparse_packet'])
    for side in ('before', 'after'):
        _capture_check(packet[side], packet['sparse_packet'], side, packet['tasks'])
    require(canonical(packet['before']['observations']) == canonical(packet['after']['observations']),
            'protected routed task interpretation changed')
    # The full inherited validation remains mandatory. New-field checks above
    # fail quickly before its more expensive finite/byte reconstruction.
    return sparse.PreparedSparseRefinement(raw)


@dataclass(frozen=True, slots=True)
class PreparedPromptRouting:
    packet_bytes: bytes
    _sparse: sparse.PreparedSparseRefinement = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable routing packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical routing packet required')
        object.__setattr__(self, '_sparse', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def sparse(self) -> sparse.PreparedSparseRefinement:
        return self._sparse


def _capture(root: Path, sparse_packet: dict, side: str, tasks: list[dict], pairs) -> dict:
    raw_files = {}
    for name in CAPTURE_PATHS:
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_FILE_BYTES, 'missing/oversized routing input')
        raw_files[name] = path.read_bytes()
    objects, adapter, adapter_sha, tensor_manifest = capture_metadata(raw_files)
    package_hash = sparse_packet['bindings']['predecessor_physical_hash' if side == 'before'
                                               else 'candidate_physical_hash']
    capture = {'package_hash': package_hash,
        'files': [{'path': name, 'size': len(raw), 'sha256': sha(raw), 'hex': raw.hex()}
                  for name, raw in sorted(raw_files.items())],
        'route_objects': objects, 'adapter_image': encode_adapter(adapter),
        'adapter_sha256': adapter_sha, 'tensor_manifest_hash': tensor_manifest}
    tensor_path = root / TENSOR_PATH
    _no_links(tensor_path)
    tensor = tensor_path.read_bytes()
    require(tensor == sparse.decode_tensor(sparse_packet[side]), 'physical transition tensor differs from R')
    capture['observations'] = _reference_observations(capture, tensor, tasks)
    goals = sparse_packet['finite_packet']['protected_packet'][side]['goals']
    for row, goal, (task, challenge) in zip(capture['observations'], goals, pairs, strict=True):
        actual = decode_task(root / 'base', task, challenge=challenge)
        measured = {'task_id': actual.task_id, 'original_marker': actual.original_marker_token_id,
                    'effective_marker': actual.effective_marker_token_id, 'route_hit': actual.route_hit,
                    'selected_route_family': actual.selected_route_family}
        require(canonical(measured) == canonical(row), 'production/reference routing disagreement')
        require(actual.result_hash == goal['decode_hash'] and actual.route_evidence_hash == goal['route_evidence_hash'],
                'fresh production route/decode evidence differs from R')
        require(actual.route_hit and actual.stopped_on_eos and
                [*actual.decode.completion_token_ids, sparse.EOS] == goal['tokens'],
                'routed original task does not execute the R protected continuation')
    require(all((root / name).read_bytes() == raw for name, raw in raw_files.items())
            and tensor_path.read_bytes() == tensor, 'physical routing inputs changed during capture')
    return capture


def prepare_prompt_routing(root: Path, packages: Path) -> PreparedPromptRouting:
    """Independently capture both packages; no worker, challenge service, or Lean run."""
    retained = read_retained(root)
    previous = sparse.prepare_sparse_refinement(root, packages)
    require(previous.packet_bytes == retained[R_PACKET], 'fresh sparse input differs from completed R')
    packet_r = previous.packet
    before, after = packages / 'before', packages / 'after'
    snapshots = snapshot(before), snapshot(after)
    bundle = root / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
    pairs = protected_tasks(bundle)
    tasks = [{'task_id': task.task_id, 'prompt_hex': task.model_prompt.hex(),
              'prompt_sha256': sha(task.model_prompt), 'original_marker': task.marker,
              'expected_tokens': [*task.expected_completion.encode('ascii'), sparse.EOS],
              'challenge': None if challenge is None else {'task_id': challenge.task_id,
                  'commitment_hash': challenge.commitment_hash, 'slot_token_id': challenge.slot_token_id}}
             for task, challenge in pairs]
    _tasks(tasks, packet_r)
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'sparse_packet': packet_r, 'sparse_packet_sha256': sha(previous.packet_bytes),
              'bindings': packet_r['bindings'], 'retained_r': dict(RETAINED_R_PINS),
              'profile': dict(PROFILE), 'tasks': tasks,
              'before': _capture(before, packet_r, 'before', tasks, pairs),
              'after': _capture(after, packet_r, 'after', tasks, pairs),
              'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS}}
    prepared = PreparedPromptRouting(canonical(packet))
    require(snapshots == (snapshot(before), snapshot(after)), 'physical packages changed during S preparation')
    require(retained == read_retained(root), 'retained R inputs changed during S preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedPromptRouting, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external routing packet anchor differs')
    require(type(recomputed) is PreparedPromptRouting and raw == recomputed.packet_bytes,
            'routing packet differs from independent physical reconstruction')
    PreparedPromptRouting(raw)


def summary(prepared: PreparedPromptRouting) -> dict:
    require(type(prepared) is PreparedPromptRouting, 'validated routing packet required')
    packet = prepared.packet
    rows = packet['before']['observations']
    return {'task_count': len(packet['tasks']),
            'hidden_challenge_count': sum(task['challenge'] is not None for task in packet['tasks']),
            'legacy_chain_tasks': sum(row['original_marker'] != row['effective_marker'] for row in rows),
            'route_family_counts': {family: sum(row['selected_route_family'] == family for row in rows)
                                    for family in FAMILIES},
            'captured_files_per_package': len(CAPTURE_PATHS),
            'adapter_bytes_per_package': ADAPTER_BYTES,
            'source_file_sha256': {side: {row['path']: row['sha256'] for row in packet[side]['files']}
                                   for side in ('before', 'after')},
            'original_markers': [row['original_marker'] for row in rows],
            'effective_markers': [row['effective_marker'] for row in rows]}
