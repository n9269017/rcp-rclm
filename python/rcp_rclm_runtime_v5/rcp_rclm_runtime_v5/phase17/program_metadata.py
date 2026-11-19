"""Phase 17V: complete registry JSON images to selected planner program metadata.

Twenty-one complete package files are captured from the reconstructed U fixture.
The thirty-two candidate descriptor images are canonical reconstructions of the
anchored U grammar descriptors, not newly captured worker output. This module
independently decodes and checks their selected metadata and inactive inventory.
SHA computation, physical capture and execution remain external to Lean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import planner_refinement as planner
from .captured_json import decode_captured_json, MAX_JSON_BYTES
from .controller import FAMILIES, CurrentView
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .resource_ledger import _no_links, digest, exact

BASE = '2ed01699fd7930b564d87a79b119b5f359041b9d'
SCHEMA = 'rcp-rclm.phase17v.program-metadata-packet.v1'
POLICY = 'phase17v.complete-registry-json-to-selected-program-metadata.v1'
U_ROOT = 'artifacts/development/phase17u/op-289503c33da4'
U_EXECUTION = U_ROOT + '/gate/execution.json'
U_EXECUTION_SHA = '78461d016e2ca8498d343726dd82e531e4a8f6bf0ee8c84000aa32046d7d5ec5'
U_PACKET = U_ROOT + '/gate/packet.json'
U_PACKET_SHA = 'b5f637e2eb50030a38f193ba888faa157731ceb0cc9505d3f36fea46322c7aae'
U_SOURCE = U_ROOT + '/gate/PlannerRefinement.lean'
U_SOURCE_SHA = '25822cd97b26a6cf506366d14db732ee4e5ec8b8e4d53786fdda8de479950d82'
RETAINED_U_PINS = {
    U_EXECUTION: U_EXECUTION_SHA, U_PACKET: U_PACKET_SHA, U_SOURCE: U_SOURCE_SHA,
    U_ROOT + '/operator-validation.json':
        '729a45b9bab828146651dcf024321465f017728cd143ddb7e66bf290e3c8285b',
}
MAX_BYTES = 30 * 1024 * 1024
MAX_METADATA = (1 << 63) - 1
REGISTRY_PATH = 'registry/manifest.json'
STATE_PATH = 'historical_state.json'
PROGRAM_PREFIX = 'registry/programs/'
PROGRAM_SCHEMA = 'runtime.v4.phase16.mutation_program.v1'
REGISTRY_SCHEMA = 'runtime.v5.phase17.installed-bounded-programs.v1'
STATE_SCHEMA = 'runtime.v4.phase16.model_state.v1'
OPERATIONS = (
    'install_transfer_adapter_motif', 'install_bounded_execution_route',
    'install_content_addressed_memory_motif', 'install_expanding_resource_schedule',
    'install_fair_search_planning_rule', 'install_rejection_conditioned_retrieval_route',
    'install_package_bound_tool_chain', 'install_untrusted_proof_search_policy',
)
PROGRAM_FIELDS = {'schema_id', 'promotion_index', 'family', 'variant', 'generation',
                  'operation_id', 'parameter_a', 'parameter_b', 'public_nonce_hash'}
PROFILE = {
    'json_grammar': 'T canonical unescaped printable ASCII JSON with signed 64-bit integers',
    'registry_path': REGISTRY_PATH, 'historical_state_path': STATE_PATH,
    'program_prefix': PROGRAM_PREFIX, 'program_schema': PROGRAM_SCHEMA,
    'families': list(FAMILIES), 'operations': list(OPERATIONS),
    'inherited_programs': 8, 'before_installed_programs': 8, 'after_installed_programs': 9,
    'package_file_images': 21, 'canonical_grammar_descriptor_images': 32,
    'grammar_image_origin': 'canonical reconstruction of the anchored U grammar descriptors',
    'program_fields': sorted(PROGRAM_FIELDS), 'variants_per_family': 4,
    'parameter_min': -16, 'parameter_max': 16, 'maximum_metadata_integer': MAX_METADATA,
    'family_count_source': 'inherited registry membership; the inactive after candidate is excluded',
    'metadata_target': 'actual imported Phase17Planner.rowInputs and Q selectedBefore/selectedAfter programs and selectedUpdate.program',
}
SCOPE = {
    'domain': 'complete selected registry/state/installed-descriptor images and 32 reconstructed grammar descriptor images',
    'formal_target': 'selected registry-derived counts and decoded descriptor metadata bound to the actual U inputs',
    'selected_program_metadata_interpretation_checked': True,
    'general_program_metadata_interpretation_remains_external': True,
    'grammar_parameter_derivation_remains_external': True,
    'public_hash_computation_remains_external': True,
    'byte_capture_remains_external': True, 'digest_authenticity_remains_external': True,
    'python_execution_remains_external': True, 'general_json_parser_equivalence': False,
    'general_planner_equivalence': False, 'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True,
    'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False, 'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('V registry-image preparation, program metadata reconstruction and proof checking',
              *planner.UNMEASURED[1:])


def _integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label)
    return value


def image_bytes(text: str) -> bytes:
    require(type(text) is str and 0 < len(text) <= 2 * MAX_JSON_BYTES and len(text) % 2 == 0 and
            all(c in '0123456789abcdef' for c in text), 'bounded canonical lowercase JSON image hex required')
    return bytes.fromhex(text)


def decoded_image(text: str) -> object:
    raw = image_bytes(text)
    value = decode_captured_json(raw)
    require(canonical(value) == raw, 'captured metadata JSON is not the exact canonical encoding')
    return value


def decode_program(raw: bytes) -> dict:
    """Decode all nine descriptor fields independently of the production validator."""
    value = decode_captured_json(raw)
    exact(value, PROGRAM_FIELDS)
    require(value['schema_id'] == PROGRAM_SCHEMA, 'program schema differs')
    require(type(value['family']) is str and value['family'] in FAMILIES, 'unknown program family')
    family = FAMILIES.index(value['family'])
    require(value['operation_id'] == OPERATIONS[family], 'program operation/family mismatch')
    _integer(value['promotion_index'], 0, MAX_METADATA, 'program promotion index out of bounds')
    _integer(value['generation'], 1, MAX_METADATA, 'program generation out of bounds')
    _integer(value['variant'], 0, 3, 'program variant out of bounds')
    _integer(value['parameter_a'], -16, 16, 'program parameter A out of bounds')
    _integer(value['parameter_b'], -16, 16, 'program parameter B out of bounds')
    digest(value['public_nonce_hash'])
    require(canonical(value) == raw, 'canonical program descriptor bytes required')
    return value


def _ordered_strings(value: object, label: str, *, hashes: bool = False) -> list[str]:
    require(type(value) is list and len(value) <= 1024 and all(type(item) is str for item in value), label)
    require(value == sorted(set(value)), label + ': sorted unique values required')
    if hashes:
        for item in value:
            digest(item)
    return value


def decode_state(raw: bytes) -> dict:
    state = decode_captured_json(raw)
    exact(state, {'schema_id', 'model_index', 'active_package_hash', 'component_generations',
                  'installed_program_hashes', 'capability_frontier', 'recursive_productivity_frontier',
                  'archive_root_hash', 'fixed_verifier_hash', 'semantics_id'})
    require(state['schema_id'] == STATE_SCHEMA, 'historical state schema differs')
    _integer(state['model_index'], 9, MAX_METADATA, 'historical model index out of bounds')
    exact(state['component_generations'], set(FAMILIES))
    for count in state['component_generations'].values():
        _integer(count, 0, MAX_METADATA, 'historical generation outside metadata bounds')
    for key in ('active_package_hash', 'archive_root_hash', 'fixed_verifier_hash'):
        digest(state[key])
    _ordered_strings(state['installed_program_hashes'], 'installed historical hashes', hashes=True)
    _ordered_strings(state['capability_frontier'], 'historical capability frontier')
    _ordered_strings(state['recursive_productivity_frontier'], 'historical recursive frontier')
    require(type(state['semantics_id']) is str, 'historical semantics identifier required')
    require(canonical(state) == raw, 'canonical historical state bytes required')
    return state


def inherited_counts(programs: dict[str, dict], inherited: list[str]) -> list[int]:
    """Count the manifest's inherited membership, never the after candidate."""
    _ordered_strings(inherited, 'inherited membership', hashes=True)
    counts = [0] * len(FAMILIES)
    generations = [[] for _ in FAMILIES]
    for key in inherited:
        require(key in programs, 'inherited program omitted from complete inventory')
        program = programs[key]
        family = FAMILIES.index(program['family'])
        counts[family] += 1
        generations[family].append(program['generation'])
    require(all(sorted(values) == list(range(1, count + 1))
                for values, count in zip(generations, counts, strict=True)),
            'inherited descriptor generations are not complete consecutive history')
    return counts


def project_registry(image: dict, *, side: str, current_view: dict, bindings: dict,
                     inherited: list[str], candidate_program: dict) -> dict:
    """Check every selected registry member and derive predecessor metadata."""
    require(side in ('before', 'after'), 'registry side must be before or after')
    exact(image, {'manifest_hex', 'historical_state_hex', 'programs'})
    manifest = decoded_image(image['manifest_hex'])
    exact(manifest, {'schema_id', 'inherited_program_hashes', 'candidate_program_hash',
                     'inherited_frontier', 'recursive_frontier', 'candidate_active', 'promotion_authorized'})
    require(manifest['schema_id'] == REGISTRY_SCHEMA and manifest['candidate_active'] is False and
            manifest['promotion_authorized'] is False, 'registry candidate must remain inactive and unauthorized')
    state = decode_state(image_bytes(image['historical_state_hex']))
    view = CurrentView.from_json(current_view)
    require(planner.public_hash(state) == view.predecessor_state_hash == bindings['historical_state_hash'],
            'complete historical state differs from anchored predecessor')
    require(state['active_package_hash'] == view.active_package_hash and
            state['fixed_verifier_hash'] == view.fixed_verifier_hash and state['semantics_id'] == view.semantics_id,
            'historical state differs from producer context')
    require(manifest['inherited_program_hashes'] == state['installed_program_hashes'] == inherited and
            len(inherited) == 8, 'inherited inventory differs from actual imported predecessor')
    _ordered_strings(manifest['inherited_frontier'], 'registry inherited frontier')
    _ordered_strings(manifest['recursive_frontier'], 'registry recursive frontier')
    require(manifest['inherited_frontier'] == state['capability_frontier'] and
            manifest['recursive_frontier'] == state['recursive_productivity_frontier'],
            'registry frontiers differ from complete historical state')
    candidate = None if side == 'before' else bindings['program_hash']
    require(manifest['candidate_program_hash'] == candidate and
            bindings['program_hash'] not in inherited, 'inactive candidate identity/substitution differs')
    expected = sorted([*inherited, *([] if candidate is None else [candidate])])
    entries = image['programs']
    require(type(entries) is list and len(entries) == len(expected), 'complete installed registry inventory required')
    keys, programs = [], {}
    for entry in entries:
        exact(entry, {'key', 'image_hex'})
        key = digest(entry['key'])
        program = decode_program(image_bytes(entry['image_hex']))
        require(planner.public_hash(program) == key, 'installed descriptor identity differs from registry key')
        keys.append(key)
        programs[key] = program
    require(keys == expected and len(programs) == len(keys), 'installed registry keys omitted, duplicated or unlisted')
    counts = inherited_counts(programs, inherited)
    require(counts == list(view.family_counts) and
            counts == [state['component_generations'][family] for family in FAMILIES],
            'registry-derived family counts differ from historical state or actual U context')
    if candidate is not None:
        require(canonical(programs[candidate]) == canonical(candidate_program),
                'captured inactive candidate differs from selected Q program')
    return {'manifest': manifest, 'state': state, 'programs': programs, 'family_counts': counts}


def metadata_rows(candidate_images: list[dict], counts: list[int], ranking: dict) -> list[dict]:
    """Reconstruct every U RowInput field using decoded descriptor metadata."""
    require(type(candidate_images) is list and len(candidate_images) == 32, 'complete 32 descriptor images required')
    require(type(counts) is list and len(counts) == 8, 'exact family count vector required')
    for count in counts:
        _integer(count, 0, MAX_METADATA, 'derived family count invalid')
    rows = ranking['rows']
    require(type(rows) is list and len(rows) == 32, 'complete actual U rows required')
    view = CurrentView.from_json(ranking['current_view'])
    result, keys, pairs = [], [], []
    for entry, row in zip(candidate_images, rows, strict=True):
        exact(entry, {'key', 'image_hex'})
        key = digest(entry['key'])
        program = decode_program(image_bytes(entry['image_hex']))
        family = FAMILIES.index(program['family'])
        count = counts[family]
        require(program['generation'] == count + 1 and
                program['promotion_index'] == view.turn_index and program['public_nonce_hash'] == view.public_nonce_hash,
                'descriptor generation, turn or nonce differs from selected current view')
        require(key == row['key'] == planner.public_hash(program) and
                canonical(program) == canonical(row['program']), 'decoded descriptor differs from actual U grammar row')
        require(row['family'] == family and type(row['family']) is int and
                row['family_count'] == count and type(row['family_count']) is int,
                'decoded family metadata differs from actual U inputs')
        digest(row['feature_digest'])
        require(type(row['tie_digests']) is list and len(row['tie_digests']) == 5,
                'exact external tie digest inventory required')
        for value in row['tie_digests']:
            digest(value)
        result.append({'key': key, 'family': family, 'variant': program['variant'],
                       'generation': program['generation'], 'familyCount': count,
                       'featureDigest': row['feature_digest'], 'tieDigests': row['tie_digests']})
        keys.append(key)
        pairs.append((family, program['variant']))
    require(keys == sorted(set(keys)) and len(keys) == 32, 'canonical unique descriptor ordering required')
    require(set(pairs) == {(family, variant) for family in range(8) for variant in range(4)},
            'complete descriptor family and variant coverage required')
    return result


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_U_PINS.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained U input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained U input changed: ' + name)
        result[name] = raw
    return result


def _projection(packet: dict) -> dict:
    u = packet['planner_refinement_packet']
    joint = u['captured_json_packet']['routing_packet']['sparse_packet']['finite_packet']['protected_packet']['joint_packet']
    typed = joint['typed_binding']
    producer = planner.producer_packet(u)
    selected = [step['program'] for step in producer['trace']['steps']
                if step['program_hash'] == packet['bindings']['program_hash']]
    require(len(selected) == 1 and typed['new_program'] == packet['bindings']['program_hash'] ==
            producer['trace']['selected_program_hash'], 'selected program identity differs from actual Q context')
    require(typed['candidate']['base'] == [*typed['predecessor']['base'], typed['new_program']],
            'selected Q base extension differs')
    exact(packet['registry_images'], {'before', 'after'})
    projections = {}
    for side in ('before', 'after'):
        projections[side] = project_registry(packet['registry_images'][side], side=side,
            current_view=u['ranking']['current_view'], bindings=packet['bindings'],
            inherited=typed['predecessor']['base'], candidate_program=selected[0])
        require(projections[side]['state']['capability_frontier'] == typed['predecessor']['capabilityFrontier'],
                'decoded registry frontier differs from actual Q predecessor')
    before, after = projections['before'], projections['after']
    before_programs = [before['programs'][key] for key in typed['predecessor']['base']]
    after_programs = [after['programs'][key] for key in typed['candidate']['base']]
    require(canonical(before_programs) == canonical(joint['task_meanings']['before']['programs']) and
            canonical(after_programs) == canonical(joint['task_meanings']['after']['programs']) and
            canonical(selected[0]) == canonical(joint['task_meanings']['after']['programs'][-1]),
            'complete decoded registry programs differ from actual Q semantic program inventories')
    require(packet['registry_images']['before']['historical_state_hex'] ==
            packet['registry_images']['after']['historical_state_hex'],
            'after package must retain the complete predecessor state image')
    for key, program in before['programs'].items():
        require(canonical(after['programs'][key]) == canonical(program), 'inherited installed program changed after staging')
    rows = metadata_rows(packet['candidate_images'], before['family_counts'], u['ranking'])
    require(metadata_rows(packet['candidate_images'], after['family_counts'], u['ranking']) == rows,
            'candidate staging changed predecessor metadata context')
    selected_images = [entry for entry in packet['candidate_images'] if entry['key'] == typed['new_program']]
    require(len(selected_images) == 1 and
            canonical(decode_program(image_bytes(selected_images[0]['image_hex']))) == canonical(selected[0]),
            'decoded selected grammar program differs from actual Q selected update')
    return {'registries': projections, 'rows': rows, 'selected_program': selected[0]}


def validate_packet(packet: dict) -> planner.PreparedPlannerRefinement:
    exact(packet, {'schema', 'policy', 'base_commit', 'planner_refinement_packet', 'planner_refinement_packet_sha256',
                   'bindings', 'retained_u', 'profile', 'scope', 'claims', 'registry_images', 'candidate_images'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'program metadata schema/policy differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'program metadata profile/scope differs')
    require(canonical(packet['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported program metadata root/closure claim')
    require(canonical(packet['retained_u']) == canonical(RETAINED_U_PINS), 'retained U anchors changed')
    raw_u = canonical(packet['planner_refinement_packet'])
    require(sha(raw_u) == packet['planner_refinement_packet_sha256'] == U_PACKET_SHA, 'same-candidate U packet changed')
    require(canonical(packet['bindings']) == canonical(packet['planner_refinement_packet']['bindings']),
            'registry package/program binding differs')
    _projection(packet)
    # Reject malformed V additions before invoking the expensive inherited validator.
    return planner.PreparedPlannerRefinement(raw_u)


@dataclass(frozen=True, slots=True)
class PreparedProgramMetadata:
    packet_bytes: bytes
    _planner: planner.PreparedPlannerRefinement = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable program metadata packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical program metadata packet required')
        object.__setattr__(self, '_planner', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def planner_refinement(self) -> planner.PreparedPlannerRefinement:
        return self._planner


def capture_registry(package: Path) -> tuple[dict, dict[str, bytes]]:
    """Read every registry file, rejecting unlisted files, nesting and symlinks."""
    _no_links(package)
    directory = package / 'registry'
    _no_links(directory)
    require(directory.is_dir(), 'complete registry directory missing')
    paths = {}
    for path in sorted(directory.rglob('*')):
        _no_links(path)
        relative = path.relative_to(package).as_posix()
        if path.is_dir():
            require(relative == 'registry/programs', 'unexpected nested registry directory')
        else:
            require(path.is_file() and path.stat().st_nlink == 1 and 0 < path.stat().st_size <= MAX_JSON_BYTES,
                    'registry image must be bounded independent regular file')
            paths[relative] = path
    require(REGISTRY_PATH in paths, 'complete registry manifest missing')
    state = package / STATE_PATH
    _no_links(state)
    require(state.is_file() and state.stat().st_nlink == 1 and 0 < state.stat().st_size <= MAX_JSON_BYTES,
            'complete historical state image missing')
    paths[STATE_PATH] = state
    files = {name: path.read_bytes() for name, path in paths.items()}
    entries = []
    for name, raw in sorted(files.items()):
        if name in (REGISTRY_PATH, STATE_PATH):
            continue
        require(name.startswith(PROGRAM_PREFIX) and name.endswith('.json'), 'unlisted registry file')
        key = name[len(PROGRAM_PREFIX):-5]
        digest(key)
        require(name == PROGRAM_PREFIX + key + '.json', 'noncanonical registry descriptor path')
        entries.append({'key': key, 'image_hex': raw.hex()})
    require(all(path.read_bytes() == files[name] for name, path in paths.items()), 'registry files changed during capture')
    return {'manifest_hex': files[REGISTRY_PATH].hex(), 'historical_state_hex': files[STATE_PATH].hex(),
            'programs': entries}, files


def prepare_program_metadata(root: Path, packages: Path) -> PreparedProgramMetadata:
    """Reconstruct U and capture the selected complete registries, without campaigns."""
    retained = read_retained(root)
    previous = planner.prepare_planner_refinement(root, packages)
    require(previous.packet_bytes == retained[U_PACKET], 'fresh planner input differs from completed U')
    u = previous.packet
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'planner_refinement_packet': u, 'planner_refinement_packet_sha256': sha(previous.packet_bytes),
              'bindings': u['bindings'], 'retained_u': dict(RETAINED_U_PINS),
              'profile': dict(PROFILE), 'scope': dict(SCOPE), 'claims': {name: False for name in FALSE_CLAIMS},
              'registry_images': {}, 'candidate_images': [
                  {'key': row['key'], 'image_hex': canonical(row['program']).hex()} for row in u['ranking']['rows']]}
    captures = {}
    for side in ('before', 'after'):
        packet['registry_images'][side], captures[side] = capture_registry(packages / side)
    prepared = PreparedProgramMetadata(canonical(packet))
    for side in ('before', 'after'):
        image, files = capture_registry(packages / side)
        require(files == captures[side] and image == packet['registry_images'][side], 'complete registry capture changed')
    require(retained == read_retained(root), 'retained U inputs changed during metadata preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedProgramMetadata, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external metadata packet anchor differs')
    require(type(recomputed) is PreparedProgramMetadata and raw == recomputed.packet_bytes,
            'program metadata packet differs from independent reconstruction')
    PreparedProgramMetadata(raw)


def summary(prepared: PreparedProgramMetadata) -> dict:
    require(type(prepared) is PreparedProgramMetadata, 'validated program metadata packet required')
    packet = prepared.packet
    projection = _projection(packet)
    inventories = {}
    for side, image in packet['registry_images'].items():
        files = {REGISTRY_PATH: image_bytes(image['manifest_hex']), STATE_PATH: image_bytes(image['historical_state_hex'])}
        files.update({PROGRAM_PREFIX + row['key'] + '.json': image_bytes(row['image_hex']) for row in image['programs']})
        inventories[side] = {name: {'size': len(raw), 'sha256': sha(raw)} for name, raw in sorted(files.items())}
    return {'packages': 2, 'package_file_images': sum(len(files) for files in inventories.values()),
            'package_file_bytes': sum(row['size'] for files in inventories.values() for row in files.values()),
            'source_file_inventory': inventories, 'canonical_grammar_descriptor_images': len(packet['candidate_images']),
            'canonical_grammar_descriptor_bytes': sum(len(image_bytes(row['image_hex'])) for row in packet['candidate_images']),
            'grammar_image_origin': PROFILE['grammar_image_origin'],
            'inherited_programs_per_package': 8, 'installed_programs': {'before': 8, 'after': 9},
            'inherited_family_counts': projection['registries']['before']['family_counts'],
            'candidate_excluded_from_family_counts': True, 'candidate_active': False, 'promotion_authorized': False,
            'metadata_rows': len(projection['rows']), 'descriptor_fields_per_image': len(PROGRAM_FIELDS),
            'selected_program_hash': packet['bindings']['program_hash'],
            'planner_refinement_packet_sha256': U_PACKET_SHA}
