"""Phase 17AE: a fixed conservative task interpretation and semantic novelty.

The original twenty-two meanings retain their exact bytes and identifiers.  A
fixed palette describes 260 different adapter-family affine behaviours.  It is
defined from the existing bounded program syntax, before any follow-up search;
the current 32-proposal sampler is not asserted to reach every palette entry.

Preparation freshly reconstructs the retained Q/P physical pair.  Twenty-one
captured manifest/registry/program images are authenticated by its fixed package
identities.  Two independently structured existing interpreters recompute the
zero and unit observations; a coefficient characterization separately checks
the adapter-family interpretation.  The universal mathematical statement and
the strengthened acceptance kernel are checked by the separate real Lean gate.
No second candidate, challenge, next context, active store or promotion is made.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from .bootstrap import _validate_program
from .challenge_protocol import execute_reference
from .controller import FAMILIES, _hash
from .finite_kernel import PreparedFiniteKernel, prepare_finite_kernel, FALSE_CLAIMS
from .frontier_meanings import check_task
from .materialized import (MANIFEST, SCHEMA as PACKAGE_SCHEMA, CLAIMS as PACKAGE_CLAIMS,
                           execute_matrix, snapshot, require, sha, safe_relative)

BASE = 'e45af6bc66ed3484b8819ceefbbaf5e4bc8bef6f'
SCHEMA = 'rcp-rclm.phase17ae.task-interpretation-packet.v1'
POLICY = 'phase17ae.fixed-legacy22-plus-bounded-affine260.v1'
MAX_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 512 * 1024
LEGACY_COUNT = 22
PALETTE_COUNT = 260
CATALOG_BOUND = LEGACY_COUNT + PALETTE_COUNT
TASK_PREFIX = 'phase17ae.adapter.affine.'
PROBES = ((0, 0, 0, 0), (1, 0, 0, 0))
SCOPE = {
    'domain': 'fixed conservative extension of the selected Q/P finite task interpretation',
    'legacy_meanings': 'the same thirteen theorem and nine finite vector meanings, unchanged',
    'new_meanings': 'adapter-family affine behaviours with slopes 1..4 and offsets -32..32',
    'separation': 'zero and unit observations determine the adapter affine coefficients',
    'physical_mapping': 'externally anchored extraction, not a universal physical refinement proof',
    'reference_programs': 'bounded mathematical Program projections, not proposed or installed candidates',
    'sampler_coverage': 'no assertion that a current 32-proposal batch reaches the whole palette',
    'semantic_guard': 'failure of the predecessor meaning, independent of declared-frontier membership',
    'family_boundary': 'adapter-family capability novelty, not globally new functions across families',
    'selected_step': 'recertification of the existing first finite step; no second accepted step',
    'resource_interpretation': 'inherited retained reference tariff; AE verification costs unmeasured',
    'historical_campaigns_rerun': False,
    'fresh_workers': 0,
    'fresh_challenges': 0,
    'follow_up_selection_performed': False,
    'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _image(value):
    require(type(value) is str and 0 < len(value) <= MAX_IMAGE_BYTES * 2 and
            len(value) % 2 == 0 and re.fullmatch('[0-9a-f]*', value) is not None,
            'bounded lowercase byte image required')
    return bytes.fromhex(value)


def catalog_descriptor() -> dict:
    """No candidate, state, nonce, challenge, objective or selected count input."""
    return {
        'schema': 'phase17ae.fixed-affine-task-palette.v1',
        'family': 'adapter_policy', 'family_index': 0,
        'legacy_count': LEGACY_COUNT, 'palette_count': PALETTE_COUNT,
        'catalog_bound': CATALOG_BOUND, 'variants': [0, 1, 2, 3],
        'slopes': [1, 2, 3, 4], 'offset_min': -32, 'offset_max': 32,
        'program_parameter_min': -16, 'program_parameter_max': 16,
        'index_formula': '22 + 65 * variant + offset_index',
        'offset_formula': 'offset_index - 32',
        'task_name_formula': TASK_PREFIX + '<variant>.<offset_index>',
        'reference_behaviour': 'map (lambda x: (variant + 1) * x + offset)',
        'formal_input_domain': 'all four-tuples of mathematical integers',
        'probe_inputs': [list(x) for x in PROBES],
        'physical_probe_domain': 'four integers each between -64 and 64',
        'meaning_requires_family': 'adapter_policy',
        'program_identity_required': False,
        'declaration_membership_is_semantic_evidence': False,
        'unknown_indices': 'reject',
        'reference_program_role': 'bounded mathematical projection only',
    }


def affine_task(variant: int, offset_index: int) -> dict:
    """Return one member of the fixed palette, with a bounded reference realizer.

    The four-field reference is a Lean Program projection.  It deliberately has
    no production metadata, nonce, candidate identity or installation receipt.
    """
    require(type(variant) is int and 0 <= variant < 4 and
            type(offset_index) is int and 0 <= offset_index < 65, 'fixed palette coordinates required')
    slope, offset = variant + 1, offset_index - 32
    a = max(-16, min(16, offset))
    b = a - offset
    return {'index': LEGACY_COUNT + 65 * variant + offset_index,
            'task_id': TASK_PREFIX + str(variant) + '.' + str(offset_index),
            'variant': variant, 'slope': slope, 'offset_index': offset_index, 'offset': offset,
            'probe_inputs': [list(x) for x in PROBES],
            'probe_targets': [[slope * x + offset for x in vector] for vector in PROBES],
            'reference_program': {'family': 0, 'variant': variant, 'a': a, 'b': b}}


def fixed_palette() -> list[dict]:
    return [affine_task(variant, offset_index) for variant in range(4) for offset_index in range(65)]


def _input_names(finite: PreparedFiniteKernel, side: str) -> set[str]:
    typed = finite.joint().packet['typed_binding']['predecessor' if side == 'before' else 'candidate']
    return {MANIFEST, 'registry/manifest.json',
            *('registry/programs/' + key + '.json' for key in typed['base'])}


def _complete_snapshot(files: dict, *, expected_package_hash: str) -> None:
    """Check every freshly read byte before retaining the smaller image subset."""
    _hash(expected_package_hash, 'external complete package anchor')
    require(type(files) is dict and MANIFEST in files and
            all(type(raw) is bytes for raw in files.values()), 'immutable complete snapshot required')
    manifest = load_json_strict(files[MANIFEST])
    require(canonical(manifest) == files[MANIFEST] and
            manifest['materialized_package_hash'] == expected_package_hash and
            digest({k: v for k, v in manifest.items() if k != 'materialized_package_hash'}) ==
                expected_package_hash, 'complete snapshot manifest identity differs')
    rows = manifest['files']
    require(set(files) == {MANIFEST, *(row['path'] for row in rows)},
            'complete physical snapshot inventory differs')
    for row in rows:
        raw = files[row['path']]
        require(sha(raw) == row['sha256'] and len(raw) == row['size'],
                'complete physical snapshot bytes differ: ' + row['path'])


def _captured(finite: PreparedFiniteKernel, captured: dict) -> dict:
    """Authenticate the selected images against complete, externally fixed manifests.

    Uncaptured bytes are checked by fresh physical preparation.  This serialized
    validator does not claim that it has re-created those bytes from hashes.
    """
    _exact(captured, {'before', 'after'}, 'captured input')
    bound = finite.packet['bindings']
    joint = finite.joint().packet
    old = joint['typed_binding']['predecessor']
    images, manifests, registries = {}, {}, {}
    for side in ('before', 'after'):
        _exact(captured[side], _input_names(finite, side), side + ' image inventory')
        files = {name: _image(value) for name, value in captured[side].items()}
        manifest = load_json_strict(files[MANIFEST])
        _exact(manifest, {'schema_id', 'kind', 'historical_state_hash',
                         'historical_active_package_hash', 'base_package_hash',
                         'base_parameter_count', 'base_archive_sha256', 'candidate',
                         'files', 'claims', 'materialized_package_hash'}, 'materialized manifest')
        anchor = bound['predecessor_physical_hash' if side == 'before' else 'candidate_physical_hash']
        require(manifest['materialized_package_hash'] == anchor and
                digest({k: v for k, v in manifest.items() if k != 'materialized_package_hash'}) == anchor,
                'physical manifest differs from fixed package identity')
        require(canonical(manifest) == files[MANIFEST] and manifest['schema_id'] == PACKAGE_SCHEMA and
                manifest['kind'] == ('predecessor' if side == 'before' else 'prospective_candidate') and
                manifest['historical_state_hash'] == bound['historical_state_hash'] and
                canonical(manifest['claims']) == canonical(PACKAGE_CLAIMS), 'physical manifest scope differs')
        rows = manifest['files']
        require(type(rows) is list and 0 < len(rows) <= 256, 'bounded manifest file rows required')
        names = []
        for row in rows:
            _exact(row, {'path', 'mode', 'size', 'sha256'}, 'physical file row')
            safe_relative(row['path']); _hash(row['sha256'], 'physical file hash')
            require(row['mode'] == '0644' and type(row['size']) is int and row['size'] >= 0,
                    'physical file mode or size differs')
            names.append(row['path'])
        require(names == sorted(set(names)), 'physical manifest rows must be ordered and unique')
        inventory = {row['path']: row for row in rows}
        for name, raw in files.items():
            if name != MANIFEST:
                require(name in inventory and inventory[name]['sha256'] == sha(raw) and
                        inventory[name]['size'] == len(raw), 'captured image differs: ' + name)
        registry = load_json_strict(files['registry/manifest.json'])
        _exact(registry, {'schema_id', 'inherited_program_hashes', 'candidate_program_hash',
                         'inherited_frontier', 'recursive_frontier', 'candidate_active',
                         'promotion_authorized'}, 'physical registry')
        require(canonical(registry) == files['registry/manifest.json'] and
                registry['schema_id'] == 'runtime.v5.phase17.installed-bounded-programs.v1' and
                registry['candidate_active'] is False and registry['promotion_authorized'] is False,
                'registry byte identity or authority differs')
        require(registry['inherited_program_hashes'] == old['base'] and
                registry['inherited_frontier'] == old['capabilityFrontier'], 'inherited registry differs')
        typed = joint['typed_binding']['predecessor' if side == 'before' else 'candidate']
        keys = list(registry['inherited_program_hashes'])
        if side == 'after':
            require(registry['candidate_program_hash'] == bound['program_hash'] and
                    manifest['candidate']['program_hash'] == bound['program_hash'] and
                    manifest['candidate']['transcript_sha256'] == bound['transcript_sha256'],
                    'different original selected candidate')
            keys.append(bound['program_hash'])
        else:
            require(registry['candidate_program_hash'] is None and manifest['candidate'] is None,
                    'predecessor cannot contain a candidate')
        require(keys == typed['base'] and len(keys) == len(set(keys)), 'registered program order differs')
        programs = []
        for key in keys:
            raw = files['registry/programs/' + key + '.json']
            program = load_json_strict(raw)
            _validate_program(program)
            require(canonical(program) == raw and digest(program) == key, 'program byte identity differs')
            programs.append(program)
        require(canonical(programs) == canonical(joint['task_meanings'][side]['programs']),
                'physical and finite program projections differ')
        images[side], manifests[side], registries[side] = files, manifest, registry
    for field_name in ('historical_active_package_hash', 'base_package_hash',
                       'base_parameter_count', 'base_archive_sha256'):
        require(manifests['before'][field_name] == manifests['after'][field_name],
                'inherited physical identity changed: ' + field_name)
    require(registries['before']['recursive_frontier'] == registries['after']['recursive_frontier'],
            'inherited recursive registry metadata changed')
    base_rows = lambda m: [r for r in m['files'] if r['path'].startswith('base/')]
    require(base_rows(manifests['before']) == base_rows(manifests['after']) and
            len(base_rows(manifests['after'])) == 164, 'frozen base manifest changed')
    require(sum(map(len, images.values())) == 21, 'complete selected image inventory differs')
    return images


def _program_observation(program: dict) -> dict:
    """Recompute public probes; no supplied success bit or desired target is used."""
    _validate_program(program)
    matrix = [execute_matrix(program, list(vector)) for vector in PROBES]
    reference = [execute_reference(program, list(vector)) for vector in PROBES]
    require(matrix == reference, 'independent probe interpreters disagree')
    family = program['family']
    return {'program_hash': digest(program), 'family': family, 'family_index': FAMILIES.index(family),
            'variant': program['variant'], 'a': program['parameter_a'], 'b': program['parameter_b'],
            'probe_outputs': matrix,
            'affine_signature': ([program['variant'] + 1, program['parameter_a'] - program['parameter_b']]
                                 if family == 'adapter_policy' else None)}


def _affine_matches(observation: dict, task: dict) -> bool:
    by_probes = (observation['family'] == 'adapter_policy' and
                 observation['probe_outputs'] == task['probe_targets'])
    by_coefficients = (observation['family'] == 'adapter_policy' and
                       observation['affine_signature'] == [task['slope'], task['offset']])
    require(by_probes == by_coefficients, 'affine probes and coefficient characterization disagree')
    return by_probes


def _observations(meanings: dict, palette: list[dict], images: dict) -> dict:
    result = {}
    tasks = meanings['tasks']
    for side in ('before', 'after'):
        state = meanings[side]
        programs = [_program_observation(program) for program in state['programs']]
        legacy = [check_task(task, state) for task in tasks]
        rows = []
        for task in palette:
            witnesses = [p['program_hash'] for p in programs if _affine_matches(p, task)]
            rows.append({'index': task['index'], 'task_id': task['task_id'],
                         'satisfied': bool(witnesses), 'satisfying_program_hashes': witnesses})
        declared = [i for i, task in enumerate(tasks) if task['task_id'] in state['declared_ids']]
        require(len(declared) == len(state['declared_ids']), 'unknown or repeated legacy declaration')
        checked = [i for i in declared if legacy[i]]
        result[side] = {
            'package_hash': state['package_hash'], 'registry_sha256': sha(images[side]['registry/manifest.json']),
            'program_observations': programs, 'legacy_checks': legacy,
            'declared_indices': declared, 'checked_declared_indices': checked,
            'checked_declared_ids': [tasks[i]['task_id'] for i in checked],
            'affine_checks': rows,
            'affine_solved_indices': [row['index'] for row in rows if row['satisfied']],
            'affine_unsolved_indices': [row['index'] for row in rows if not row['satisfied']],
        }
    return result


def _novelty(catalog: dict, observations: dict, task_index: int) -> dict:
    require(type(task_index) is int and 0 <= task_index < CATALOG_BOUND, 'known task index required')
    def satisfied(side):
        obs = observations[side]
        return (obs['legacy_checks'][task_index] if task_index < LEGACY_COUNT else
                obs['affine_checks'][task_index - LEGACY_COUNT]['satisfied'])
    before, after = satisfied('before'), satisfied('after')
    name = (catalog['legacy_task_ids'][task_index] if task_index < LEGACY_COUNT else
            catalog['tail'][task_index - LEGACY_COUNT]['task_id'])
    return {'task_index': task_index, 'task_id': name,
            'predecessor_satisfied': before, 'candidate_satisfied': after,
            'predecessor_declared': task_index in observations['before']['declared_indices'],
            'candidate_declared': task_index in observations['after']['declared_indices'],
            'predecessor_semantic_failure': not before,
            'strict_semantic_gain': not before and after}


def _derived(finite: PreparedFiniteKernel, captured: dict) -> dict:
    images = _captured(finite, captured)
    meanings = finite.joint().packet['task_meanings']
    palette, descriptor = fixed_palette(), catalog_descriptor()
    legacy_ids = [task['task_id'] for task in meanings['tasks']]
    require(len(legacy_ids) == LEGACY_COUNT and
            not any(name.startswith(TASK_PREFIX) for name in legacy_ids), 'legacy/name separation differs')
    catalog = {'descriptor': descriptor, 'descriptor_sha256': digest(descriptor),
               'legacy_tasks_sha256': digest(meanings['tasks']), 'legacy_task_ids': legacy_ids,
               'tail': palette, 'tail_sha256': digest(palette)}
    catalog['catalog_sha256'] = digest(catalog)
    observations = _observations(meanings, palette, images)
    before, after = observations['before'], observations['after']
    first = _novelty(catalog, observations, LEGACY_COUNT - 1)
    already = _novelty(catalog, observations, 259)
    require(first['strict_semantic_gain'] and not first['predecessor_declared'] and
            first['candidate_declared'], 'selected original first task lost semantic novelty')
    require(before['checked_declared_indices'] == list(range(21)) and
            after['checked_declared_indices'] == list(range(22)), 'original declared frontier differs')
    require(before['affine_solved_indices'] == after['affine_solved_indices'] == [259] and
            not already['predecessor_declared'] and not already['candidate_declared'] and
            not already['predecessor_semantic_failure'], 'already-solvable undeclared control differs')
    guard = {'rule': 'not predecessor meaning.holds; successor satisfaction is separately required',
             'checker_bridge': 'the real Lean gate proves completeness for this fixed catalog',
             'declaration_membership_used_as_failure_evidence': False,
             'selected_original_first_task': first, 'already_solved_undeclared_task': already,
             'new_affine_strict_gains_in_selected_pair': [row['index'] for row in palette
                 if _novelty(catalog, observations, row['index'])['strict_semantic_gain']]}
    summary = {'legacy_tasks': LEGACY_COUNT, 'additional_affine_tasks': PALETTE_COUNT,
               'total_known_tasks': CATALOG_BOUND, 'captured_files': sum(map(len, images.values())),
               'before_programs': len(before['program_observations']),
               'after_programs': len(after['program_observations']),
               'before_frontier': len(before['checked_declared_indices']),
               'after_frontier': len(after['checked_declared_indices']),
               'before_affine_solved': len(before['affine_solved_indices']),
               'after_affine_solved': len(after['affine_solved_indices']),
               'before_affine_unsolved': len(before['affine_unsolved_indices']),
               'after_affine_unsolved': len(after['affine_unsolved_indices']),
               'already_solved_undeclared_index': 259,
               'selected_adapter_signature': [4, 10],
               'selected_first_task_semantically_new': first['strict_semantic_gain'],
               'already_solved_undeclared_task_rejected': not already['predecessor_semantic_failure'],
               'new_affine_strict_gains': len(guard['new_affine_strict_gains_in_selected_pair']),
               'new_accepted_successors': 0, 'fresh_live_evaluations': 0,
               'follow_up_selection_performed': False, 'physical_candidate_active': False}
    return {'catalog': catalog, 'observations': observations, 'semantic_guard': guard, 'summary': summary}


def validate_packet(packet: dict) -> PreparedFiniteKernel:
    _exact(packet, {'schema', 'policy', 'base_commit', 'finite_packet', 'finite_packet_sha256',
                    'captured_inputs', 'catalog', 'observations', 'semantic_guard', 'summary',
                    'scope', 'claims'}, 'task interpretation packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'task interpretation schema, policy or base differs')
    require(canonical(packet['scope']) == canonical(SCOPE) and
            canonical(packet['claims']) == canonical({k: False for k in FALSE_CLAIMS}),
            'task interpretation scope or authority escalation')
    finite = PreparedFiniteKernel(canonical(packet['finite_packet']))
    require(sha(finite.packet_bytes) == packet['finite_packet_sha256'], 'finite input identity differs')
    for key, value in _derived(finite, packet['captured_inputs']).items():
        require(canonical(packet[key]) == canonical(value), 'task interpretation derivation differs: ' + key)
    return finite


@dataclass(frozen=True, slots=True)
class PreparedTaskInterpretation:
    packet_bytes: bytes
    _finite: PreparedFiniteKernel = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable task interpretation required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical task interpretation required')
        object.__setattr__(self, '_finite', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def finite(self) -> PreparedFiniteKernel:
        return self._finite


def novelty_for(prepared: PreparedTaskInterpretation, *, task_index: int,
                expected_predecessor_hash: str, expected_candidate_hash: str) -> dict:
    """Read the semantic guard decision for the selected, anchored physical pair.

    This interface cannot submit an arbitrary state or proposed future program.
    A true semantic gain is one obligation, not an acceptance certificate.
    """
    require(type(prepared) is PreparedTaskInterpretation, 'validated task interpretation required')
    _hash(expected_predecessor_hash, 'external predecessor package anchor')
    _hash(expected_candidate_hash, 'external candidate package anchor')
    checked = PreparedTaskInterpretation(prepared.packet_bytes)
    packet = checked.packet
    bound = checked.finite().packet['bindings']
    require(expected_predecessor_hash == bound['predecessor_physical_hash'] and
            expected_candidate_hash == bound['candidate_physical_hash'], 'selected package anchors differ')
    return _novelty(packet['catalog'], packet['observations'], task_index)


def prepare_task_interpretation(root: Path, packages: Path) -> PreparedTaskInterpretation:
    """Reconstruct the retained finite pair without making any follow-up choice."""
    finite = prepare_finite_kernel(root, packages)
    before, after = snapshot(packages / 'before'), snapshot(packages / 'after')
    bound = finite.packet['bindings']
    for files, key in ((before, 'predecessor_physical_hash'), (after, 'candidate_physical_hash')):
        _complete_snapshot(files, expected_package_hash=bound[key])
    captured = {side: {name: files[name].hex() for name in sorted(_input_names(finite, side))}
                for side, files in (('before', before), ('after', after))}
    derived = _derived(finite, captured)
    result = PreparedTaskInterpretation(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'finite_packet': finite.packet, 'finite_packet_sha256': sha(finite.packet_bytes),
        'captured_inputs': captured, **derived, 'scope': dict(SCOPE),
        'claims': {key: False for key in FALSE_CLAIMS}}))
    require(before == snapshot(packages / 'before') and after == snapshot(packages / 'after'),
            'physical inputs changed during task interpretation preparation')
    return result


def verify_packet_bytes(raw: bytes, recomputed: PreparedTaskInterpretation, *, expected_sha256: str) -> None:
    _hash(expected_sha256, 'external task interpretation packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and
            type(recomputed) is PreparedTaskInterpretation and raw == recomputed.packet_bytes,
            'task interpretation packet differs from anchored independent recomputation')
    PreparedTaskInterpretation(raw)
