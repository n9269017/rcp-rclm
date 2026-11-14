"""Phase 17AD: an inactive successor's next present-state context.

The selected packet reopens the exact Q/P fixture and measures its physical
candidate.  A prospective Phase 16 ModelState is an adapter input, not an active
store record.  Its archive root remains the historical archive root; a separate
reference history binds the prospective transition.  No challenge is opened,
candidate evaluated, root authorization issued, or package promoted here.

The general context function accepts only this validated immutable projection
and independently supplied public fields.  It never authenticates their source
or freshness.  The selected fixture uses explicitly synthetic public fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import struct

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime_v4.phase16.records import ModelState
from .bootstrap import SELECTED_STATE_HASH, WEIGHTS_SHA256, validate_state, _validate_program
from .campaign_transaction import load_predecessor
from .challenge_protocol import reference_grammar
from .controller import (Action, FAMILIES, FIXED_VERIFIER, SEMANTICS, checkpoint,
                         decide, restore, _hash, _integer)
from .controller_continuation import table_of, reference_choice
from .finite_kernel import (PreparedFiniteKernel, prepare_finite_kernel, FALSE_CLAIMS,
                            P_FIXTURE, P_HEAD, TRANSACTION, RETAINED_PINS)
from .handoff_source import checked_handoff, FIXTURE_SHA
from .materialized import (MANIFEST, SCHEMA as PACKAGE_SCHEMA, CLAIMS as PACKAGE_CLAIMS,
                           snapshot, verify_package, require, sha, safe_relative)
from .phase16_adapter import bind_phase16_search
from .proposal_provenance import producer_sources, score_table

BASE = '99600c67e9e7d0c71d7de5cf09f0d3b5d786ad1a'
SCHEMA = 'rcp-rclm.phase17ad.successor-context-packet.v1'
POLICY = 'phase17ad.inactive-successor-present-context.v1'
OBJECTIVE_POLICY = 'phase17ad.current-snapshot-inherited-projection-objective.v1'
MAX_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 512 * 1024
PLANNER = 'base/model/phase15_planner/weights.i16le.bin'
SELECTED_NONCE = digest({'domain': POLICY, 'fixture': 'public-next-turn-nonce'})
SELECTED_COMMITMENT = digest({'domain': POLICY, 'fixture': 'synthetic-opaque-next-commitment'})
SELECTED_CREDITS = 32
SCOPE = {
    'domain': 'prospective next context of the inactive pinned Q/P candidate',
    'state_role': 'reference adapter input; not an activated or promoted ModelState',
    'archive_root': 'unchanged historical archive root; no new archive execution claimed',
    'history': 'parent-linked prospective reference identity, not an authenticated live ledger',
    'objective': 'new present-snapshot policy over eight families and inherited planner bytes',
    'ranking': 'unchanged Phase16 grammar/ranker compared with an independent integer projection',
    'public_fields': 'explicit synthetic next nonce and opaque commitment; no challenge opened',
    'formal_boundary': 'selected literals and conditional state-indexed finite kernel, not physical equivalence',
    'expected_charges': 'a separately supplied per-state witness; no next-turn cost witness invented',
    'historical_campaigns_rerun': False,
    'fresh_workers': 0,
    'fresh_challenges': 0,
    'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _image(value):
    require(type(value) is str and len(value) <= MAX_IMAGE_BYTES * 2 and
            len(value) % 2 == 0 and re.fullmatch('[0-9a-f]*', value) is not None,
            'bounded lowercase byte image required')
    return bytes.fromhex(value)


def _model(state: dict) -> ModelState:
    validate_state(state)
    result = ModelState(**{k: v for k, v in state.items() if k != 'schema_id'})
    require(canonical(result.to_json()) == canonical(state), 'model-state interpretation differs')
    return result


def _input_names(finite: PreparedFiniteKernel, side: str) -> set[str]:
    joint = finite.joint().packet
    typed = joint['typed_binding']['predecessor' if side == 'before' else 'candidate']
    return {MANIFEST, 'historical_state.json', 'registry/manifest.json',
            *(row['path'] for row in joint['producer_provenance']['producer']['component_files']),
            *('registry/programs/' + key + '.json' for key in typed['base'])}


def _captured(finite: PreparedFiniteKernel, captured: dict) -> tuple[dict, dict, tuple]:
    """Check images against externally anchored complete package manifests.

    Uncaptured package bytes are covered by fresh physical reconstruction in
    prepare_successor_context, not fabricated by this serialized-data verifier.
    """
    _exact(captured, {'before', 'after'}, 'captured input')
    bound = finite.packet['bindings']
    joint = finite.joint().packet
    images = {}
    manifests = {}
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
                canonical(manifest['claims']) == canonical(PACKAGE_CLAIMS), 'physical manifest scope differs')
        rows = manifest['files']
        require(type(rows) is list and 0 < len(rows) <= 256, 'bounded manifest file rows')
        names = []
        for row in rows:
            _exact(row, {'path', 'mode', 'size', 'sha256'}, 'physical file row')
            safe_relative(row['path']); _hash(row['sha256'], 'physical file hash')
            require(row['mode'] == '0644' and type(row['size']) is int and row['size'] >= 0,
                    'physical file mode/size differs')
            names.append(row['path'])
        require(names == sorted(set(names)), 'physical manifest rows must be ordered and unique')
        inventory = {row['path']: row for row in rows}
        for name, raw in files.items():
            if name == MANIFEST:
                continue
            require(name in inventory and inventory[name]['sha256'] == sha(raw) and
                    inventory[name]['size'] == len(raw), 'captured image differs: ' + name)
        registry = load_json_strict(files['registry/manifest.json'])
        _exact(registry, {'schema_id', 'inherited_program_hashes', 'candidate_program_hash',
                         'inherited_frontier', 'recursive_frontier', 'candidate_active',
                         'promotion_authorized'}, 'physical registry')
        require(registry['schema_id'] == 'runtime.v5.phase17.installed-bounded-programs.v1' and
                registry['candidate_active'] is False and registry['promotion_authorized'] is False,
                'candidate registry claims activation')
        typed = joint['typed_binding']['predecessor' if side == 'before' else 'candidate']
        tasks = joint['task_meanings'][side]
        keys = list(registry['inherited_program_hashes'])
        if side == 'after':
            require(registry['candidate_program_hash'] == bound['program_hash'], 'different added program')
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
            require(canonical(program) == raw and digest(program) == key, 'descriptor byte identity differs')
            programs.append(program)
        require(canonical(programs) == canonical(tasks['programs']), 'physical and finite programs differ')
        images[side] = files
        manifests[side] = manifest
    before, after = images['before'], images['after']
    require(before['historical_state.json'] == after['historical_state.json'],
            'historical state image differs')
    state = validate_state(load_json_strict(before['historical_state.json']))
    require(canonical(state) == before['historical_state.json'] and
            digest(state) == SELECTED_STATE_HASH == bound['historical_state_hash'],
            'historical state canonical identity differs')
    old_keys = joint['typed_binding']['predecessor']['base']
    require(state['installed_program_hashes'] == old_keys and
            state['capability_frontier'] == joint['typed_binding']['predecessor']['capabilityFrontier'],
            'historical inventory differs from finite predecessor')
    for side in ('before', 'after'):
        registry = load_json_strict(images[side]['registry/manifest.json'])
        require(registry['inherited_program_hashes'] == old_keys and
                registry['inherited_frontier'] == state['capability_frontier'] and
                registry['recursive_frontier'] == state['recursive_productivity_frontier'],
                'inherited registry metadata differs')
        manifest = manifests[side]
        require(manifest['historical_state_hash'] == SELECTED_STATE_HASH and
                manifest['historical_active_package_hash'] == state['active_package_hash'],
                'historical manifest parent differs')
    base_rows = lambda m: [r for r in m['files'] if r['path'].startswith('base/')]
    require(base_rows(manifests['before']) == base_rows(manifests['after']) and
            len(base_rows(manifests['after'])) == 164, 'frozen base manifest changed')
    for row in joint['producer_provenance']['producer']['component_files']:
        name = row['path']
        require(before[name] == after[name] and sha(after[name]) == row['sha256'] and
                len(after[name]) == row['size'], 'successor producer component changed')
    require(before[PLANNER] == after[PLANNER] and len(after[PLANNER]) == 65536 and
            sha(after[PLANNER]) == WEIGHTS_SHA256, 'complete inherited planner image differs')
    weights = struct.unpack('<32768h', after[PLANNER])
    projection = tuple((index, value) for index, value in enumerate(weights) if value)
    require(len(projection) == 84, 'inherited nonzero projection shape differs')
    return state, images, projection


def _basis(finite: PreparedFiniteKernel, captured: dict) -> tuple[dict, tuple]:
    state, images, weights = _captured(finite, captured)
    p = finite.packet
    joint = finite.joint().packet
    bound = p['bindings']; trace = joint['producer_provenance']['trace']
    raw = images['after']['registry/programs/' + bound['program_hash'] + '.json']
    program = load_json_strict(raw)
    require(program == trace['steps'][-1]['program'] and program['promotion_index'] ==
            trace['current_view']['turn_index'], 'added program is not selected prior-turn program')
    family = program['family']
    require(program['generation'] == state['component_generations'][family] + 1,
            'added generation does not extend predecessor')
    generations = dict(state['component_generations']); generations[family] += 1
    prospective = dict(state)
    prospective.update(model_index=state['model_index'] + 1,
                       active_package_hash=bound['candidate_physical_hash'],
                       component_generations=generations,
                       installed_program_hashes=sorted(state['installed_program_hashes'] + [bound['program_hash']]),
                       capability_frontier=joint['typed_binding']['candidate']['capabilityFrontier'])
    # This is deliberately unchanged: no new accepted archive has been created.
    require(prospective['archive_root_hash'] == state['archive_root_hash'], 'archive anchor changed')
    model = _model(prospective)
    transition = {'schema': 'rcp-rclm.phase17ad.prospective-history.v1',
                  'parent_state_hash': SELECTED_STATE_HASH,
                  'parent_archive_root_hash': state['archive_root_hash'],
                  'parent_physical_package_hash': bound['predecessor_physical_hash'],
                  'candidate_physical_package_hash': bound['candidate_physical_hash'],
                  'program_hash': bound['program_hash'],
                  'transcript_sha256': bound['transcript_sha256'],
                  'transaction_id': TRANSACTION, 'staging_journal_head': P_HEAD,
                  'finite_packet_sha256': sha(finite.packet_bytes),
                  'prior_turn_index': trace['current_view']['turn_index'],
                  'next_turn_index': trace['current_view']['turn_index'] + 1,
                  'prospective_state_hash': model.state_record_hash,
                  'physical_candidate_active': False, 'root_authorized': False,
                  'history_kind': 'prospective_reference_link'}
    history_hash = digest(transition)
    old_producer = joint['producer_provenance']['producer']
    producer = {'policy': POLICY, 'producer_kind': old_producer['producer_kind'],
                'physical_package_hash': bound['candidate_physical_hash'],
                'prospective_state_hash': model.state_record_hash,
                'prospective_history_hash': history_hash,
                'planner_weights_sha256': WEIGHTS_SHA256,
                'component_files': old_producer['component_files'],
                'source_files': old_producer['source_files'],
                'self_hosted_generator_execution_demonstrated': False,
                'physical_execution_attested': False}
    producer['generator_id'] = digest(producer)
    basis = {'transition': transition, 'prospective_history_hash': history_hash,
             'historical_state': state, 'prospective_state': prospective,
             'prospective_state_hash': model.state_record_hash,
             'producer': producer,
             'projection': {'planner_image_sha256': WEIGHTS_SHA256,
                            'planner_word_count': 32768,
                            'nonzero_weights': [list(item) for item in weights],
                            'before_program_hashes': joint['typed_binding']['predecessor']['base'],
                            'after_program_hashes': joint['typed_binding']['candidate']['base'],
                            'before_frontier': joint['typed_binding']['predecessor']['capabilityFrontier'],
                            'after_frontier': joint['typed_binding']['candidate']['capabilityFrontier'],
                            'added_family': family, 'added_generation': program['generation']}}
    return basis, weights


def _objective(state: dict, history_hash: str, weights: tuple, *, turn: int, nonce: str) -> dict:
    rows = []
    for family_index, family in enumerate(FAMILIES):
        generation = state['component_generations'][family]
        features = {'domain': OBJECTIVE_POLICY, 'prospective_state_hash': digest(state),
                    'prospective_history_hash': history_hash,
                    'package_hash': state['active_package_hash'],
                    'planner_weights_sha256': WEIGHTS_SHA256, 'turn_index': turn,
                    'public_nonce_hash': nonce, 'objective_family': family,
                    'capability_frontier': state['capability_frontier'],
                    'recursive_productivity_frontier': state['recursive_productivity_frontier']}
        feature_hash = digest(features)
        terms = [weight * ((int(feature_hash[(index + j * 11) % 64], 16) +
                           family_index * 3 + generation + j) % 9 - 4)
                 for j, (index, weight) in enumerate(weights)]
        inherited_score = sum(terms)
        tie = digest({'policy_id': OBJECTIVE_POLICY, 'feature_hash': feature_hash, 'family': family})
        rows.append({'family': family, 'generation': generation, 'feature_hash': feature_hash,
                     'terms': terms, 'inherited_projection_score': inherited_score,
                     'score': 20000 - generation * 521 + inherited_score, 'tie_break': tie})
    rows.sort(key=lambda row: (row['score'], row['tie_break'], row['family']), reverse=True)
    result = {'schema': 'rcp-rclm.phase17ad.current-objective.v1', 'policy': OBJECTIVE_POLICY,
              'prospective_state_hash': digest(state), 'prospective_history_hash': history_hash,
              'package_hash': state['active_package_hash'], 'turn_index': turn,
              'public_nonce_hash': nonce, 'planner_weights_sha256': WEIGHTS_SHA256,
              'ranked_objectives': rows, 'objective_family': rows[0]['family'],
              'goal': 'extend_verified_capability_frontier',
              'fixed_verifier_hash': FIXED_VERIFIER, 'semantics_id': SEMANTICS,
              'physical_candidate_active': False, 'promotion_authorized': False}
    return {**result, 'decision_hash': digest(result)}


def _context(basis: dict, weights: tuple, *, turn_index: int, public_nonce_hash: str,
             challenge_commitment_hash: str, candidate_credits: int) -> dict:
    """No future horizon, challenge opening, winner, or stopping time is an input."""
    _integer(turn_index, 'turn_index'); _hash(public_nonce_hash, 'public nonce')
    _hash(challenge_commitment_hash, 'opaque challenge commitment')
    _integer(candidate_credits, 'candidate_credits')
    require(turn_index == basis['transition']['next_turn_index'], 'successor turn index differs')
    require(candidate_credits <= 32, 'finite root provenance permits at most 32 credits')
    state = basis['prospective_state']; model = _model(state)
    bound = bind_phase16_search(model, turn_index=turn_index,
                               challenge_commitment_hash=challenge_commitment_hash,
                               public_nonce_hash=public_nonce_hash, candidate_credits=candidate_credits)
    programs = tuple(p.to_json() for p in sorted(bound.programs.values(), key=lambda p: p.program_hash))
    require(programs == reference_grammar(state, turn_index, public_nonce_hash),
            'successor grammar interpretation differs')
    independent = score_table(bound.prefix.frozen.view, programs, weights)
    table = table_of(bound.prefix.frozen)
    reference_table = [{'key': r['program_hash'], 'family': r['family_index'],
                        'base_score': r['base_score'], 'ties': r['ties']} for r in independent]
    require(table == reference_table, 'physical successor ranking interpretation differs')
    freeze = bound.prefix.frozen.freeze_hash
    offset = int(freeze[:16], 16) % 32
    decision = decide(bound.prefix)
    index = reference_choice(table, [], offset) if candidate_credits else None
    require(decision.action == (Action.EVALUATE if candidate_credits else Action.RESOURCE_EXHAUSTED) and
            decision.candidate_hash == (None if index is None else table[index]['key']),
            'successor initial controller decision differs')
    raw = checkpoint(bound.prefix)
    require(restore(raw, expected_prefix_hash=bound.prefix.prefix_hash) == bound.prefix,
            'successor initial checkpoint failed replay')
    objective = _objective(state, basis['prospective_history_hash'], weights,
                           turn=turn_index, nonce=public_nonce_hash)
    objective_freeze = {'schema': 'rcp-rclm.phase17ad.current-objective-freeze.v1',
                        'objective_decision_hash': objective['decision_hash'],
                        'prospective_state_hash': model.state_record_hash,
                        'prospective_history_hash': basis['prospective_history_hash'],
                        'package_hash': state['active_package_hash'],
                        'turn_index': turn_index, 'public_nonce_hash': public_nonce_hash,
                        'fixed_verifier_hash': FIXED_VERIFIER, 'semantics_id': SEMANTICS,
                        'challenge_bound': False, 'promotion_authorized': False}
    objective_freeze['freeze_hash'] = digest(objective_freeze)
    context_binding = {'policy': POLICY, 'prospective_state_hash': model.state_record_hash,
                       'prospective_history_hash': basis['prospective_history_hash'],
                       'generator_id': basis['producer']['generator_id'],
                       'objective_freeze_hash': objective_freeze['freeze_hash'],
                       'search_freeze_hash': freeze, 'candidate_credits': candidate_credits}
    context = {'view': bound.prefix.frozen.view.to_json(), 'rows': table, 'offset': offset,
               'programs': list(programs), 'grammar_hash': digest(list(programs)),
               'public_ranking_seed': bound.public_ranking_seed,
               'frozen_search': bound.prefix.frozen.to_json(), 'freeze_hash': freeze,
               'initial_checkpoint': load_json_strict(raw), 'initial_prefix_hash': bound.prefix.prefix_hash,
               'initial_action': decision.action.value, 'initial_candidate_hash': decision.candidate_hash,
               'initial_candidate_index': index, 'initial_decision_hash': decision.decision_hash,
               'context_binding': context_binding,
               'provenance_context': {'generator': basis['producer']['generator_id'],
                                      'parent_package': state['active_package_hash'],
                                      'context_hash': digest(context_binding),
                                      'transcript_hash': basis['prospective_history_hash'],
                                      'credits': candidate_credits, 'offset': offset, 'rows': table}}
    return {'objective': objective, 'objective_freeze': objective_freeze, 'next_context': context}


def _derived(finite: PreparedFiniteKernel, captured: dict) -> dict:
    basis, weights = _basis(finite, captured)
    turn = basis['transition']['next_turn_index']
    require(SELECTED_COMMITMENT != finite.packet['bindings']['challenge_commitment_hash'],
            'selected public commitment accidentally reuses previous challenge')
    context = _context(basis, weights, turn_index=turn,
                       public_nonce_hash=SELECTED_NONCE,
                       challenge_commitment_hash=SELECTED_COMMITMENT,
                       candidate_credits=SELECTED_CREDITS)
    projection = basis['projection']
    summary = {'before_programs': len(projection['before_program_hashes']),
               'after_programs': len(projection['after_program_hashes']),
               'before_frontier': len(projection['before_frontier']),
               'after_frontier': len(projection['after_frontier']),
               'candidate_rows': len(context['next_context']['rows']),
               'objective_families': len(context['objective']['ranked_objectives']),
               'planner_nonzero_terms': len(weights), 'planner_total_words': 32768,
               'prior_turn_index': basis['transition']['prior_turn_index'],
               'next_turn_index': turn,
               'next_initial_action': context['next_context']['initial_action'],
               'next_initial_candidate_index': context['next_context']['initial_candidate_index'],
               'new_evaluations': 0, 'new_accepted_successors': 0,
               'physical_candidate_active': False}
    return {**basis, **context, 'summary': summary}


def validate_packet(packet: dict) -> PreparedFiniteKernel:
    _exact(packet, {'schema', 'policy', 'base_commit', 'finite_packet', 'finite_packet_sha256',
                    'captured_inputs', 'transition', 'prospective_history_hash', 'historical_state',
                    'prospective_state', 'prospective_state_hash', 'producer', 'projection',
                    'objective', 'objective_freeze', 'next_context', 'summary', 'scope', 'claims'}, 'successor packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'successor schema/policy/base differs')
    require(canonical(packet['scope']) == canonical(SCOPE) and
            canonical(packet['claims']) == canonical({k: False for k in FALSE_CLAIMS}),
            'successor scope or authority escalation')
    finite = PreparedFiniteKernel(canonical(packet['finite_packet']))
    require(sha(finite.packet_bytes) == packet['finite_packet_sha256'], 'finite input identity differs')
    expected = _derived(finite, packet['captured_inputs'])
    for key, value in expected.items():
        require(canonical(packet[key]) == canonical(value), 'successor derivation differs: ' + key)
    return finite


@dataclass(frozen=True, slots=True)
class PreparedSuccessorContext:
    packet_bytes: bytes
    _finite: PreparedFiniteKernel = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable successor context required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical successor context required')
        object.__setattr__(self, '_finite', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def finite(self) -> PreparedFiniteKernel:
        return self._finite


def context_for(prepared: PreparedSuccessorContext, *, expected_state_hash: str,
                expected_history_hash: str, turn_index: int, public_nonce_hash: str,
                challenge_commitment_hash: str, candidate_credits: int) -> dict:
    """Construct a reference context for an externally selected public request.

    The exact immutable selected projection and its separately supplied state
    and reference-history anchors are required.  This interface does not accept
    an arbitrary ModelState, activation flag, challenge opening, or target count.
    The commitment is an opaque public input, not authenticated fresh entropy.
    """
    require(type(prepared) is PreparedSuccessorContext, 'validated successor projection required')
    _hash(expected_state_hash, 'external state anchor'); _hash(expected_history_hash, 'external history anchor')
    checked = PreparedSuccessorContext(prepared.packet_bytes)
    finite = checked.finite()
    basis, weights = _basis(finite, checked.packet['captured_inputs'])
    require(expected_state_hash == basis['prospective_state_hash'] and
            expected_history_hash == basis['prospective_history_hash'], 'stale successor state/history anchor')
    require(challenge_commitment_hash != finite.packet['bindings']['challenge_commitment_hash'],
            'previous consumed challenge commitment cannot identify this reference turn')
    return _context(basis, weights, turn_index=turn_index, public_nonce_hash=public_nonce_hash,
                    challenge_commitment_hash=challenge_commitment_hash, candidate_credits=candidate_credits)


def prepare_successor_context(root: Path, packages: Path) -> PreparedSuccessorContext:
    """Independently reconstruct both physical packages; do not run a campaign."""
    source_before = producer_sources(root)
    finite = prepare_finite_kernel(root, packages)
    before, after = snapshot(packages / 'before'), snapshot(packages / 'after')
    captured = {side: {name: files[name].hex() for name in sorted(_input_names(finite, side))}
                for side, files in (('before', before), ('after', after))}
    derived = _derived(finite, captured)
    require(source_before == derived['producer']['source_files'], 'producer implementation binding changed')
    result = PreparedSuccessorContext(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'finite_packet': finite.packet, 'finite_packet_sha256': sha(finite.packet_bytes),
        'captured_inputs': captured, **derived, 'scope': dict(SCOPE),
        'claims': {k: False for k in FALSE_CLAIMS}}))
    parent = load_predecessor(root)
    handoff_raw = bytes.fromhex(finite.packet['retained_hex'][P_FIXTURE + '/source.json'])
    handoff = checked_handoff(parent, handoff_raw,
                              expected_source_hash=RETAINED_PINS[P_FIXTURE + '/source.json'])
    bundle = root / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
    for side, transcript, anchor in (('before', None, None), ('after', handoff.transcript, FIXTURE_SHA)):
        key = 'predecessor_physical_hash' if side == 'before' else 'candidate_physical_hash'
        verify_package(packages / side, parent, bundle,
                       expected_package_hash=finite.packet['bindings'][key],
                       transcript=transcript, expected_transcript_hash=anchor)
    require(before == snapshot(packages / 'before') and after == snapshot(packages / 'after') and
            source_before == producer_sources(root), 'physical inputs or implementation changed during AD preparation')
    return result


def verify_packet_bytes(raw: bytes, recomputed: PreparedSuccessorContext, *, expected_sha256: str) -> None:
    _hash(expected_sha256, 'external successor packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and
            type(recomputed) is PreparedSuccessorContext and raw == recomputed.packet_bytes,
            'successor packet differs from anchored independent recomputation')
    PreparedSuccessorContext(raw)
