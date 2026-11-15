"""Phase 17AH: source-bound finite producer and truthful reference evaluation.

The two sources are the already retained, inactive AF before/after packages.
The unchanged Phase16 producer and Phase17 controller are called directly.
A new, explicit evaluator adapter selects the least missing AE contract and
checks the complete AG finite acceptance predicate.  This is fresh local
reference computation, not a live campaign or physical successor installation.

The caller must retain the request, source and reference-grant identities.
The grant limits a narrow tariff (descriptor admission and two DSL probes per
attempt); its hash does not authenticate an issuer or confer campaign authority.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from . import successor_interface as ag, successor_context as ad, task_interpretation as ae
from .bootstrap import _validate_program, WEIGHTS_SHA256
from .challenge_protocol import execute_reference, reference_grammar
from .controller import (Action, FAMILIES, FIXED_VERIFIER, FrozenSearch, checkpoint,
                         decide, record_evaluation, restore, _hash)
from .controller_continuation import table_of, reference_choice
from .finite_kernel import FALSE_CLAIMS
from .materialized import execute_matrix, require, sha
from .phase16_adapter import bind_phase16_search
from .proposal_provenance import producer_sources, score_table
from .resource_ledger import Policy, TARIFFS, add, cost, _no_links

BASE = '187b13a08dcddb76152a1f66f45872e554d36cb8'
SCHEMA = 'rcp-rclm.phase17ah.producer-domain-packet.v1'
POLICY = 'phase17ah.source-bound-producer-domain.v1'
EVALUATOR = 'phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1'
REQUEST_SCHEMA = 'phase17ah.source-bound-producer-request.v1'
RESULT_SCHEMA = 'phase17ah.source-bound-producer-result.v1'
GRANT_SCHEMA = 'phase17ah.external-reference-grant.v1'
JOURNAL_SCHEMA = 'phase17ah.reference-operation-journal.v1'
JOURNAL_DOMAIN = b'RCPRCLM-PHASE17AH-REFERENCE-OPERATIONS-V1\0'
AG_ROOT = 'artifacts/development/phase17ag/op-109d9740bfb1/gate'
AG_PACKET_SHA = '4f86b74e267c24fc9145f4ae9ce1dad5a385d9fb95e5b1219f8cadd5f62a7c82'
AG_EXECUTION_SHA = 'd32c30f47b9e1d084d0cba479a5365248e62cd4ba9e9d52c0ccaf30a5fc72dad'
AG_SOURCE = '109d9740bfb19ecfaf60c96f8820d3ddbe7c815d'
AG_TREE = 'f60d9f1878b23f8ac3ee9abfd8d1f69ab208c244'
RETAINED_PINS = {AG_ROOT + '/packet.json': AG_PACKET_SHA,
                 AG_ROOT + '/execution.json': AG_EXECUTION_SHA}
MAX_BYTES = 40 * 1024 * 1024
SOURCES = ('af_before', 'af_after')
ATTEMPT_CHARGES = ('candidate', 'vector', 'vector')
UNMEASURED = (
    'inherited source/package/evidence reconstruction and validation',
    'grammar generation, hashing, planner ranking and controller bookkeeping',
    'catalog scans, AG acceptance checks and independent verification calls',
    'journal serialization, filesystem operations, host time and memory',
    'Lean proof compilation, testing, historical work and future campaigns',
)
SCOPE = {
    'sources': 'two retained inactive AF package projections with explicit prospective ModelState lineage',
    'producer': 'direct unchanged Phase16 grammar/ranker and Phase17 controller; measured inherited planner projection',
    'domain': 'exact 32 grammar descriptors and the least missing realized contract from the unchanged 282-task catalog',
    'evaluator': 'new fixed-catalog reference adapter, not the old hidden-challenge evaluator or a live capability claim',
    'public_fields': 'fixed public reference nonce and opaque commitment, not independently witnessed fresh entropy',
    'history': 'fresh recomputed local reference receipts; historical archive root remains unchanged',
    'candidate': 'finite append projection only; no new physical successor package or active-store write',
    'resource_authority': 'externally anchored caller reference grant, with no issuer authentication or campaign authority',
    'tariff': 'one descriptor admission and two bounded DSL probe pairs per attempted candidate',
    'journal': 'fresh preparation persists reservations before calls; serialized verification reconstructs bytes in memory',
    'formal_boundary': 'generic structural Lean statements plus selected generated literal checks; no universal Python refinement',
    'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'old_proof_campaigns_rerun': False,
    'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _same(left, right, message):
    require(canonical(left) == canonical(right), message)


def _nat(value, label, maximum=32):
    require(type(value) is int and 0 <= value <= maximum, 'bounded natural ' + label + ' required')


def _checked_interface(interface):
    require(type(interface) is ag.PreparedSuccessorInterface and sha(interface.packet_bytes) == AG_PACKET_SHA,
            'exact completed AG interface required')
    return interface


@lru_cache(maxsize=1)
def _fixed_interpretation(raw):
    """Only immutable, exactly pinned meaning bytes can enter this pure cache."""
    return ag.FixedInterpretation(raw)


def source_basis(interface, source_id):
    """Derive one of the two immutable selected source projections.

    The second ModelState is a reference adapter input derived from the retained
    AF append.  It is not an activated state, new archive entry or promotion.
    """
    _checked_interface(interface)
    require(type(source_id) is str and source_id in SOURCES, 'selected source identity required')
    second = interface.second_step().packet
    successor = second['successor_packet']
    side = 'before' if source_id == 'af_before' else 'after'
    source = ag._state_from_af(second['finite_projection'][side])
    model = copy.deepcopy(successor['prospective_state'])
    if source_id == 'af_before':
        history = copy.deepcopy(successor['transition'])
        history_hash = successor['prospective_history_hash']
        turn = successor['transition']['next_turn_index']
        nonce = successor['next_context']['view']['public_nonce_hash']
        commitment = successor['next_context']['view']['challenge_commitment_hash']
    else:
        chosen = second['update']['program']
        family = chosen['family']
        require(chosen['generation'] == model['component_generations'][family] + 1,
                'retained AF generation does not extend its reference source')
        model['model_index'] += 1
        model['active_package_hash'] = source['package_hash']
        model['component_generations'][family] += 1
        model['installed_program_hashes'] = sorted(source['keys'])
        model['capability_frontier'] = list(source['named_frontier'])
        turn = successor['transition']['next_turn_index'] + 1
        nonce = digest({'domain': POLICY, 'source': source_id, 'field': 'public_nonce'})
        commitment = digest({'domain': POLICY, 'source': source_id, 'field': 'opaque_commitment'})
        history = {'schema': 'phase17ah.second-prospective-source-link.v1',
            'parent_state_hash': successor['prospective_state_hash'],
            'parent_history_hash': successor['prospective_history_hash'],
            'parent_package_hash': second['update']['parent_package'],
            'package_hash': source['package_hash'], 'program_hash': second['update']['key'],
            'fixed_task': second['update']['task'], 'af_packet_sha256': ag.AF_PACKET_SHA,
            'af_transcript_sha256': second['reference_transcript_sha256'],
            'archive_root_hash': model['archive_root_hash'], 'next_turn_index': turn,
            'prospective_state_hash': digest(model),
            'history_kind': 'prospective_reference_link', 'physical_candidate_active': False,
            'root_authorized': False, 'promotion_authorized': False}
        history_hash = digest(history)
    checked_model = ad._model(model)
    require(checked_model.state_record_hash == digest(model) and
            model['active_package_hash'] == source['package_hash'] and
            model['installed_program_hashes'] == sorted(source['keys']) and
            model['capability_frontier'] == source['named_frontier'] and
            model['archive_root_hash'] == successor['historical_state']['archive_root_hash'],
            'source adapter projection differs from retained package state')
    return {'source_id': source_id, 'source': source, 'source_sha256': digest(source),
        'model_state': model, 'model_state_hash': checked_model.state_record_hash,
        'history': history, 'history_hash': history_hash, 'turn_index': turn,
        'public_nonce_hash': nonce, 'challenge_commitment_hash': commitment,
        'planner_weights_sha256': WEIGHTS_SHA256,
        'planner_projection': copy.deepcopy(successor['projection']['nonzero_weights']),
        'producer_source_files': copy.deepcopy(successor['producer']['source_files']),
        'producer_component_files': copy.deepcopy(successor['producer']['component_files']),
        'physical_candidate_active': False, 'promotion_authorized': False}


def make_request(interface, source_id, *, candidate_credits=32):
    """Recompute the actual grammar and public producer context for this source."""
    _nat(candidate_credits, 'candidate credits')
    basis = source_basis(interface, source_id)
    model = ad._model(basis['model_state'])
    bound = bind_phase16_search(model, turn_index=basis['turn_index'],
        public_nonce_hash=basis['public_nonce_hash'],
        challenge_commitment_hash=basis['challenge_commitment_hash'], candidate_credits=candidate_credits)
    programs = [program.to_json() for program in sorted(bound.programs.values(), key=lambda p: p.program_hash)]
    require(tuple(programs) == reference_grammar(basis['model_state'], basis['turn_index'],
                                              basis['public_nonce_hash']), 'actual grammar/reference disagreement')
    rows = table_of(bound.prefix.frozen)
    independent = score_table(bound.prefix.frozen.view, tuple(programs),
                              tuple(tuple(row) for row in basis['planner_projection']))
    _same(rows, [{'key': row['program_hash'], 'family': row['family_index'],
                 'base_score': row['base_score'], 'ties': row['ties']} for row in independent],
          'captured planner and actual ranker disagree')
    require(len(programs) == 32 and [digest(program) for program in programs] == [row['key'] for row in rows]
            and {(program['family'], program['variant']) for program in programs} ==
                {(family, variant) for family in FAMILIES for variant in range(4)},
            'producer grammar domain is not the exact family/variant cover')
    fixed = interface.second_step().interpretation().packet['catalog']['catalog_sha256']
    producer = {'policy': POLICY, 'source_sha256': basis['source_sha256'],
        'model_state_hash': basis['model_state_hash'], 'history_hash': basis['history_hash'],
        'package_hash': basis['source']['package_hash'], 'planner_weights_sha256': WEIGHTS_SHA256,
        'source_files': basis['producer_source_files'], 'component_files': basis['producer_component_files']}
    binding = {'policy': POLICY, 'evaluator': EVALUATOR, 'source_id': source_id,
        'source_sha256': basis['source_sha256'], 'model_state_hash': basis['model_state_hash'],
        'history_hash': basis['history_hash'], 'fixed_catalog_sha256': fixed,
        'generator': digest(producer), 'search_freeze_hash': bound.prefix.frozen.freeze_hash,
        'candidate_credits': candidate_credits}
    context = {'generator': binding['generator'], 'parent_package': basis['source']['package_hash'],
        'context_hash': digest(binding), 'transcript_hash': basis['history_hash'],
        'credits': candidate_credits, 'offset': int(bound.prefix.frozen.freeze_hash[:16], 16) % 32, 'rows': rows}
    initial_raw = checkpoint(bound.prefix)
    require(restore(initial_raw, expected_prefix_hash=bound.prefix.prefix_hash) == bound.prefix,
            'initial source-bound controller checkpoint differs')
    if source_id == 'af_before':
        retained = interface.second_step().packet['successor_packet']['next_context']
        _same(rows, retained['rows'], 'AF source grammar ranking changed')
        require(bound.prefix.frozen.freeze_hash == retained['freeze_hash'], 'AF source freeze changed')
    return {'schema': REQUEST_SCHEMA, 'policy': POLICY, 'evaluator': EVALUATOR,
        'source_id': source_id, 'source': basis['source'], 'source_sha256': basis['source_sha256'],
        'model_state_hash': basis['model_state_hash'], 'history_hash': basis['history_hash'],
        'fixed_catalog_sha256': fixed, 'programs': programs, 'context': context,
        'context_binding': binding, 'frozen_search': bound.prefix.frozen.to_json(),
        'freeze_hash': bound.prefix.frozen.freeze_hash,
        'initial_checkpoint': load_json_strict(initial_raw), 'initial_prefix_hash': bound.prefix.prefix_hash,
        'grammar_sha256': digest(programs)}


def reference_policy(attempt_limit):
    _nat(attempt_limit, 'reference attempt limit')
    limits = (attempt_limit, 2 * attempt_limit, 8 * attempt_limit, 8 * attempt_limit)
    return Policy(limits, cost(limits))


def make_grant(request, *, resource_attempt_limit=32):
    """Explicit fixture/caller grant; retaining its digest is an external act."""
    _nat(resource_attempt_limit, 'resource attempt limit')
    return {'schema': GRANT_SCHEMA, 'issuer': 'phase17ah.reference-policy-test-authority',
        'source_sha256': request['source_sha256'], 'package_hash': request['source']['package_hash'],
        'history_hash': request['history_hash'], 'context_hash': request['context']['context_hash'],
        'request_sha256': digest(request), 'fixed_catalog_sha256': request['fixed_catalog_sha256'],
        'evaluator': EVALUATOR, 'candidate_limit': request['context']['credits'],
        'policy': reference_policy(resource_attempt_limit).to_json(),
        'authority_kind': 'externally_anchored_reference_grant',
        'issuer_authenticated': False, 'campaign_authority': False, 'promotion_authorized': False}


def _request_shape(request):
    _exact(request, {'schema', 'policy', 'evaluator', 'source_id', 'source', 'source_sha256',
        'model_state_hash', 'history_hash', 'fixed_catalog_sha256', 'programs', 'context',
        'context_binding', 'frozen_search', 'freeze_hash', 'initial_checkpoint',
        'initial_prefix_hash', 'grammar_sha256'}, 'producer request')
    require(request['schema'] == REQUEST_SCHEMA and request['policy'] == POLICY and
            request['evaluator'] == EVALUATOR and type(request['source_id']) is str and
            request['source_id'] in SOURCES, 'producer request identity differs')
    ag._state(request['source']); ag._context(request['context'])
    _nat(request['context']['credits'], 'candidate credits')
    require(type(request['programs']) is list and len(request['programs']) == 32,
            'exact producer descriptor inventory required')
    for program in request['programs']:
        _validate_program(program)
    FrozenSearch.from_json(request['frozen_search'])
    for name in ('source_sha256', 'model_state_hash', 'history_hash', 'fixed_catalog_sha256',
                 'freeze_hash', 'initial_prefix_hash', 'grammar_sha256'):
        _hash(request[name], name)


def _grant_shape(grant):
    _exact(grant, {'schema', 'issuer', 'source_sha256', 'package_hash', 'history_hash',
        'context_hash', 'request_sha256', 'fixed_catalog_sha256', 'evaluator', 'candidate_limit',
        'policy', 'authority_kind', 'issuer_authenticated', 'campaign_authority',
        'promotion_authorized'}, 'reference grant')
    require(grant['schema'] == GRANT_SCHEMA and type(grant['issuer']) is str and
            0 < len(grant['issuer']) <= 256 and grant['evaluator'] == EVALUATOR and
            grant['authority_kind'] == 'externally_anchored_reference_grant' and
            all(grant[key] is False for key in
                ('issuer_authenticated', 'campaign_authority', 'promotion_authorized')),
            'reference grant scope escalation')
    _nat(grant['candidate_limit'], 'grant candidate limit')
    for key in ('source_sha256', 'package_hash', 'history_hash', 'context_hash',
                'request_sha256', 'fixed_catalog_sha256'):
        _hash(grant[key], key)
    require(type(grant['policy']) is dict and type(grant['policy'].get('limits')) is list,
            'literal resource policy required')
    policy = Policy.from_json(grant['policy'])
    maximum = reference_policy(32)
    require(all(x <= y for x, y in zip(policy.limits, maximum.limits, strict=True)) and
            policy.cost_limit <= maximum.cost_limit, 'reference grant exceeds declared maximum profile')
    return policy


def _anchored_inputs(interface, request, grant, expected_source_sha256,
                     expected_request_sha256, expected_authorization_sha256):
    _checked_interface(interface)
    for label, value in (('source anchor', expected_source_sha256),
                         ('request anchor', expected_request_sha256),
                         ('reference grant anchor', expected_authorization_sha256)):
        _hash(value, label)
    request, grant = copy.deepcopy((request, grant))
    _request_shape(request); _grant_shape(grant)
    request, grant = load_json_strict(canonical([request, grant]))
    _request_shape(request); policy = _grant_shape(grant)
    require(digest(request['source']) == request['source_sha256'] == expected_source_sha256 and
            digest(request) == expected_request_sha256 and digest(grant) == expected_authorization_sha256,
            'source, request or reference grant differs from external anchor')
    _same(request, make_request(interface, request['source_id'],
          candidate_credits=request['context']['credits']), 'request differs from actual source-bound producer')
    require(grant['source_sha256'] == request['source_sha256'] and
            grant['package_hash'] == request['source']['package_hash'] and
            grant['history_hash'] == request['history_hash'] and
            grant['context_hash'] == request['context']['context_hash'] and
            grant['request_sha256'] == expected_request_sha256 and
            grant['fixed_catalog_sha256'] == request['fixed_catalog_sha256'] and
            grant['candidate_limit'] == request['context']['credits'], 'reference grant is stale or retargeted')
    return request, grant, policy


def _event(body, index, previous):
    core = {'index': index, 'previous': previous, 'body': body}
    return {**core, 'hash': sha(JOURNAL_DOMAIN + canonical(core))}


class _ReferenceJournal:
    """Persist-before-call in fresh mode; deterministic in-memory verification."""
    def __init__(self, path, request, grant, policy):
        self.rows = []; self.work = []; self.spent = (0, 0, 0, 0); self.stream = None
        self.policy = policy
        if path is not None:
            path = Path(path); _no_links(path)
            require(not path.exists() and path.parent.is_dir(), 'new external AH reference journal required')
            self.stream = path.open('xb')
        self.emit({'kind': 'open', 'schema': JOURNAL_SCHEMA, 'request_sha256': digest(request),
            'authorization_sha256': digest(grant), 'source_sha256': request['source_sha256'],
            'policy': policy.to_json(), 'timing': 'unmeasured; no elapsed-time value asserted'})

    def emit(self, body):
        row = _event(body, len(self.rows), self.rows[-1]['hash'] if self.rows else '0' * 64)
        raw = canonical(row) + b'\n'
        if self.stream is not None:
            require(self.stream.write(raw) == len(raw), 'short AH reference journal write')
            self.stream.flush(); os.fsync(self.stream.fileno())
        self.rows.append(row)
        return row

    def can_attempt(self):
        spent = self.spent
        for kind in ATTEMPT_CHARGES:
            spent = add(spent, TARIFFS[kind])
        return self.policy.fits(spent)

    def perform(self, kind, operation_id, entry, operation):
        spent = add(self.spent, TARIFFS[kind])
        require(self.policy.fits(spent), 'operation has no finite reference reservation')
        reserve = self.emit({'kind': 'reserve', 'operation': kind, 'operation_id': operation_id,
            'input_sha256': sha(canonical(entry)), 'charge': list(TARIFFS[kind]), 'spent_after': list(spent)})
        self.spent = spent
        output = operation()
        require(len(canonical(output)) <= 32768, 'reference result exceeds bound')
        self.emit({'kind': 'result', 'operation_id': operation_id, 'reservation_hash': reserve['hash'],
            'result_sha256': sha(canonical(output)), 'completed': True})
        self.work.append({'kind': kind, 'operation_id': operation_id, 'input': entry, 'output': output})
        return output

    def finish(self, status, examined):
        self.emit({'kind': 'seal', 'status': status, 'examined_candidates': examined,
                   'operation_count': len(self.work), 'spent': list(self.spent), 'charged_cost': cost(self.spent)})

    def close(self):
        if self.stream is not None:
            self.stream.close(); self.stream = None

    def raw(self):
        return b''.join(canonical(row) + b'\n' for row in self.rows)


def _admit(program, key):
    _validate_program(program)
    require(digest(program) == key, 'producer descriptor identity differs')
    return {'program_hash': key, 'descriptor_sha256': sha(canonical(program)),
            'admitted_for_reference_evaluation': True, 'physical_installation': False}


def _probe(program, vector):
    matrix = execute_matrix(program, list(vector))
    independent = execute_reference(program, list(vector))
    require(matrix == independent, 'independent bounded DSL evaluators disagree')
    return matrix


def _missing_contract(fixed, source, program, *, outputs=None, source_holds=None):
    """Internal scan using the adapter's already recomputed probe/meaning cache."""
    require(type(fixed) is ag.FixedInterpretation, 'fixed AE interpretation required')
    _validate_program(program)
    if source_holds is None:
        source_holds = [fixed.check(source, task) for task in range(ae.CATALOG_BOUND)]
    require(type(source_holds) is list and len(source_holds) == ae.CATALOG_BOUND and
            all(type(value) is bool for value in source_holds), 'complete source semantics required')
    if outputs is None:
        outputs = [_probe(program, vector) for vector in ae.PROBES]
    observation = {'program_hash': digest(program), 'family': program['family'],
        'variant': program['variant'], 'probe_outputs': outputs,
        'affine_signature': ([program['variant'] + 1, program['parameter_a'] - program['parameter_b']]
                             if program['family'] == 'adapter_policy' else None)}
    # The selected sources already satisfy every legacy meaning. Appending a
    # descriptor preserves those existential/proof observations; only the fixed
    # affine tail can supply a missing contract in this declared adapter.
    require(all(source_holds[:ae.LEGACY_COUNT]), 'source lacks a retained legacy meaning')
    realized = [bool(value) for value in source_holds]
    for task in ae.fixed_palette():
        realized[task['index']] = realized[task['index']] or ae._affine_matches(observation, task)
    novel = [task for task in range(ae.CATALOG_BOUND) if not source_holds[task] and realized[task]]
    return {'source_holds': list(source_holds), 'candidate_holds': realized,
            'missing_realized_tasks': novel, 'canonical_task': novel[0] if novel else None}


def missing_contract(fixed, source, program):
    """Recompute detached inputs; a caller cannot supply a task or cached verdict."""
    require(type(fixed) is ag.FixedInterpretation, 'fixed AE interpretation required')
    source, program = copy.deepcopy((source, program))
    ag._state(source); _validate_program(program)
    source, program = load_json_strict(canonical([source, program]))
    ag._state(source); _validate_program(program)
    return _missing_contract(fixed, source, program)


def _trial_offer(fixed, request, program, index, seen, task, charges):
    source, context = request['source'], request['context']
    key = digest(program)
    identity = {'schema': 'phase17ah.finite-append-identity.v1',
        'source_sha256': request['source_sha256'], 'context_hash': context['context_hash'],
        'program_hash': key, 'fixed_catalog_sha256': fixed.catalog_sha256, 'fixed_task': task,
        'physical_package_created': False, 'promotion_authorized': False}
    package_hash = digest(identity)
    update = {'key': key, 'program': copy.deepcopy(program), 'task': task,
        'task_name': fixed.task_name(task), 'parent_package': source['package_hash'],
        'candidate_package': package_hash, 'context_hash': context['context_hash'], 'charges': list(charges)}
    proposal = {name: context[name] for name in ('generator', 'parent_package', 'context_hash', 'transcript_hash')}
    proposal.update(choices=[*seen, index], verdicts=[False] * len(seen) + [True],
                    program=key, candidate_package=package_hash)
    evidence = {name: context[name] for name in ('parent_package', 'context_hash', 'transcript_hash')}
    evidence.update(root=source['root'], candidate_package=package_hash,
                    proposal=proposal, charges=list(charges))
    return {'update': update, 'next': ag.apply_update(source, update), 'evidence': evidence}


def inspect_session(interface, request, grant, *, expected_source_sha256,
                    expected_request_sha256, expected_authorization_sha256, journal_path=None):
    """Run the real selector against a new, explicitly scoped reference evaluator.

    A trial's prospective final-true proposal is acceptance evidence only when
    the complete recomputed check passes. Actual rejected receipts are kept
    separately and no later candidate is evaluated after a passing receipt.
    """
    request, grant, policy = _anchored_inputs(interface, request, grant, expected_source_sha256,
                                            expected_request_sha256, expected_authorization_sha256)
    fixed = _fixed_interpretation(interface.second_step().interpretation().packet_bytes)
    source = request['source']; context = request['context']
    require(ag._admissible(fixed, source), 'selected reference source is inadmissible')
    source_holds = [fixed.check(source, task) for task in range(ae.CATALOG_BOUND)]
    prefix = restore(canonical(request['initial_checkpoint']), expected_prefix_hash=request['initial_prefix_hash'])
    programs = request['programs']; indices = {digest(program): index for index, program in enumerate(programs)}
    trials, checkpoints, selected = [], [], None
    journal = _ReferenceJournal(journal_path, request, grant, policy)
    try:
        while True:
            decision = decide(prefix)
            checkpoints.append({'prefix_hash': prefix.prefix_hash, 'checkpoint_sha256': sha(checkpoint(prefix)),
                'action': decision.action.value, 'decision_hash': decision.decision_hash,
                'candidate_index': indices.get(decision.candidate_hash)})
            if decision.action != Action.EVALUATE:
                status = {Action.AWAIT_ROOT_VERIFICATION: 'accepted', Action.SEARCH_EXHAUSTED: 'exhausted',
                          Action.RESOURCE_EXHAUSTED: 'budget_stop'}[decision.action]
                break
            seen = [row['index'] for row in trials]
            index = indices[decision.candidate_hash]
            require(index == reference_choice(context['rows'], seen, context['offset']),
                    'actual controller and independent source table choice disagree')
            if not journal.can_attempt():
                journal.emit({'kind': 'denied', 'next_candidate_index': index,
                    'next_charges': list(ATTEMPT_CHARGES), 'spent_unchanged': list(journal.spent),
                    'reason': 'reference_grant_insufficient_for_complete_attempt'})
                status = 'resource_stop'
                break
            program = programs[index]; key = digest(program)
            label = f'ah-{len(trials):02d}'
            journal.perform('candidate', label + '-candidate',
                {'source_sha256': request['source_sha256'], 'context_hash': context['context_hash'],
                 'program_hash': key, 'descriptor_sha256': sha(canonical(program))},
                lambda: _admit(program, key))
            outputs = [journal.perform('vector', label + f'-probe-{probe}',
                {'source_sha256': request['source_sha256'], 'program_hash': key,
                 'descriptor_sha256': sha(canonical(program)), 'input_vector': list(vector)},
                lambda vector=vector: _probe(program, vector)) for probe, vector in enumerate(ae.PROBES)]
            meaning = _missing_contract(fixed, source, program, outputs=outputs, source_holds=source_holds)
            task = meaning['canonical_task']; charges = [row['kind'] for row in journal.work]
            offer = None if task is None else _trial_offer(fixed, request, program, index, seen, task, charges)
            checked = None if offer is None else ag.check_offer(fixed, source, context, charges, offer)
            verdict = checked is not None and checked['passes']
            if offer is not None:
                _same(meaning['candidate_holds'],
                      [fixed.check(offer['next'], task_index) for task_index in range(ae.CATALOG_BOUND)],
                      'probe-derived catalog semantics differ from complete AG interpretation')
            receipt = {'schema': 'phase17ah.truthful-reference-evaluation.v1',
                'source_sha256': request['source_sha256'], 'request_sha256': expected_request_sha256,
                'context_hash': context['context_hash'], 'fixed_catalog_sha256': fixed.catalog_sha256,
                'evaluator': EVALUATOR, 'program_hash': key, 'candidate_index': index,
                'decision_hash': decision.decision_hash, 'prefix_hash': prefix.prefix_hash,
                'canonical_task': task, 'semantics_sha256': digest(meaning),
                'offer_sha256': None if offer is None else digest(offer),
                'check_sha256': None if checked is None else digest(checked),
                'journal_head': journal.rows[-1]['hash'], 'verdict': verdict,
                'live_challenge_opened': False, 'physical_execution_attested': False,
                'formal_acceptance_established': False, 'promotion_authorized': False}
            reasons = [] if verdict else (['no_missing_realized_fixed_contract'] if task is None else
                                          ['finite_acceptance_obligation_refused'])
            updated = record_evaluation(prefix, decision, verdict='candidate_passed' if verdict else 'reject',
                evaluation_hash=digest(receipt), reason_codes=reasons,
                predecessor_state_hash=prefix.frozen.view.predecessor_state_hash,
                challenge_commitment_hash=prefix.frozen.view.challenge_commitment_hash)
            raw = checkpoint(updated)
            require(restore(raw, expected_prefix_hash=updated.prefix_hash) == updated,
                    'actual controller receipt checkpoint does not replay')
            trials.append({'index': index, 'program_hash': key, 'outputs': outputs, **meaning,
                'trial_offer': offer, 'check': checked, 'verdict': verdict, 'receipt': receipt,
                'receipt_hash': digest(receipt), 'prefix_before': prefix.prefix_hash,
                'prefix_after': updated.prefix_hash})
            prefix = updated
            if verdict:
                selected = len(trials) - 1
        require(len(trials) <= context['credits'] and len({row['index'] for row in trials}) == len(trials),
                'reference evaluation exceeded actual controller scope')
        if status == 'exhausted':
            require(len(trials) == 32 and {row['index'] for row in trials} == set(range(32)) and
                    not any(row['verdict'] for row in trials), 'finite producer exhaustion is incomplete')
        journal.finish(status, len(trials))
        raw = journal.raw()
        require(len(raw) <= 4 * 1024 * 1024, 'AH reference journal exceeds bound')
        if journal_path is not None:
            require(Path(journal_path).read_bytes() == raw, 'persisted reference journal differs')
        accepted = None if selected is None else trials[selected]['trial_offer']
        ag_request = None if accepted is None else {'schema': ag.REQUEST_SCHEMA,
            'fixed_catalog_sha256': fixed.catalog_sha256, 'source': source, 'context': context,
            'expected_charges': [row['kind'] for row in journal.work], 'offers': [accepted], 'inspection_budget': 1}
        ag_result = None if ag_request is None else ag.inspect_request(fixed, ag_request,
            expected_source_sha256=request['source_sha256'], expected_request_sha256=digest(ag_request))
        require(ag_result is None or ag_result['status'] == 'accepted', 'accepted reference receipt lacks AG bridge')
        return {'schema': RESULT_SCHEMA, 'source_id': request['source_id'], 'status': status,
            'source_sha256': expected_source_sha256, 'request_sha256': expected_request_sha256,
            'authorization_sha256': expected_authorization_sha256, 'domain_size': 32,
            'fixed_catalog_tasks': ae.CATALOG_BOUND, 'examined': len(trials), 'unexamined': 32 - len(trials),
            'selected_trial': selected, 'trials': trials, 'checkpoints': checkpoints,
            'observations': [{'index': row['index'], 'passed': row['verdict']} for row in trials],
            'final_checkpoint': load_json_strict(checkpoint(prefix)), 'final_prefix_hash': prefix.prefix_hash,
            'controller_action': decide(prefix).action.value,
            'accepted_ag_request': ag_request, 'accepted_ag_result': ag_result,
            'producer_domain_exhausted': status == 'exhausted',
            'all_producer_candidates_truthfully_rejected': status == 'exhausted',
            'global_successor_nonexistence_established': False,
            'resource': {'policy': policy.to_json(), 'operation_count': len(journal.work),
                'charge_sequence': [row['kind'] for row in journal.work], 'spent': list(journal.spent),
                'charged_cost': cost(journal.spent), 'work': journal.work,
                'journal_hex': raw.hex(), 'journal_sha256': sha(raw), 'journal_head': journal.rows[-1]['hash'],
                'journal_events': len(journal.rows), 'timing_measured': False, 'unmeasured': list(UNMEASURED)},
            'issuer_authenticated': False, 'campaign_authority_integrated': False,
            'new_physical_successor_created': False, 'physical_execution_attested': False,
            'promotion_authorized': False}
    finally:
        journal.close()


def verify_session(interface, request, grant, result, *, expected_source_sha256,
                   expected_request_sha256, expected_authorization_sha256):
    expected = inspect_session(interface, request, grant, expected_source_sha256=expected_source_sha256,
        expected_request_sha256=expected_request_sha256,
        expected_authorization_sha256=expected_authorization_sha256)
    _same(result, expected, 'source-bound result differs from complete recomputation')


def case_specs():
    return ({'name': 'first_source', 'source_id': 'af_before', 'credits': 32, 'resource_attempts': 32},
            {'name': 'second_source', 'source_id': 'af_after', 'credits': 32, 'resource_attempts': 32},
            {'name': 'second_source_credit_stop', 'source_id': 'af_after', 'credits': 4, 'resource_attempts': 32},
            {'name': 'second_source_zero_credit', 'source_id': 'af_after', 'credits': 0, 'resource_attempts': 32},
            {'name': 'second_source_resource_stop', 'source_id': 'af_after', 'credits': 32, 'resource_attempts': 3})


def _derive(interface, journal_directory=None):
    sources = [source_basis(interface, source_id) for source_id in SOURCES]
    cases = []
    for spec in case_specs():
        request = make_request(interface, spec['source_id'], candidate_credits=spec['credits'])
        grant = make_grant(request, resource_attempt_limit=spec['resource_attempts'])
        result = inspect_session(interface, request, grant,
            expected_source_sha256=request['source_sha256'], expected_request_sha256=digest(request),
            expected_authorization_sha256=digest(grant),
            journal_path=None if journal_directory is None else journal_directory / (spec['name'] + '.jsonl'))
        cases.append({'name': spec['name'], 'request': request, 'grant': grant, 'result': result})
    first, second, credit, zero, resource = (case['result'] for case in cases)
    require((first['status'], first['examined'], first['trials'][-1]['canonical_task']) == ('accepted', 1, 41)
            and (second['status'], second['examined'], second['trials'][-1]['canonical_task']) == ('accepted', 8, 56)
            and (credit['status'], credit['examined']) == ('budget_stop', 4)
            and (zero['status'], zero['examined']) == ('budget_stop', 0)
            and (resource['status'], resource['examined']) == ('resource_stop', 3),
            'fixed source-bound reference cases differ')
    require(first['trials'][0]['program_hash'] == ag.af.SELECTED_PROGRAM,
            'source-bound producer no longer includes selected AF initial choice')
    return {'sources': sources, 'cases': cases, 'summary': {
        'source_states': 2, 'producer_descriptors_per_source': 32, 'fixed_catalog_tasks': ae.CATALOG_BOUND,
        'reference_sessions': len(cases), 'accepted_reference_sessions': 2,
        'credit_stopped_reference_sessions': 2, 'resource_stopped_reference_sessions': 1,
        'first_source_selected_task': 41, 'second_source_selected_task': 56,
        'first_source_inspections': 1, 'second_source_inspections': 8,
        'second_source_truthful_rejections': 7,
        'reference_candidate_attempts': sum(case['result']['examined'] for case in cases),
        'metered_reference_operations': sum(case['result']['resource']['operation_count'] for case in cases),
        'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'new_physical_successors': 0,
        'formal_acceptance_required': True, 'full_grammar_reference_cost_limit': reference_policy(32).cost_limit,
        'reference_grant_is_campaign_authority': False}}


def _execution(raw):
    require(type(raw) is bytes and sha(raw) == AG_EXECUTION_SHA, 'exact retained AG completion required')
    record = load_json_strict(raw, require_canonical=False)
    require(record['source_commit'] == AG_SOURCE and record['source_tree'] == AG_TREE and
            record['truthful_successor_interface_checked'] is True and
            record['finite_successor_stop_conditions_checked'] is True and record['completed'] is True and
            record['proof_mode'] == 'real_pinned_lean_completed_stage_lineage', 'retained AG result differs')
    require(type(record['source_sha256']) is dict and len(record['source_sha256']) == 545,
            'retained AG source inventory differs')
    return record


def validate_packet(packet):
    _exact(packet, {'schema', 'policy', 'base_commit', 'successor_interface_packet', 'retained_execution_hex',
        'retained_sha256', 'inherited_source_sha256', 'sources', 'cases', 'summary', 'scope', 'claims'},
        'producer domain packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'producer domain packet identity differs')
    _same(packet['scope'], SCOPE, 'producer domain scope differs')
    _same(packet['claims'], {key: False for key in FALSE_CLAIMS}, 'producer domain claim escalation')
    _same(packet['retained_sha256'], RETAINED_PINS, 'retained AG pins differ')
    raw = canonical(packet['successor_interface_packet'])
    require(sha(raw) == AG_PACKET_SHA, 'retained AG packet differs')
    interface = ag.PreparedSuccessorInterface(raw)
    _exact(packet['retained_execution_hex'], {AG_ROOT + '/execution.json'}, 'retained execution')
    record = _execution(ae._image(packet['retained_execution_hex'][AG_ROOT + '/execution.json']))
    _same(packet['inherited_source_sha256'], record['source_sha256'], 'retained AG source bindings differ')
    for key, value in _derive(interface).items():
        _same(packet[key], value, 'producer domain derivation differs: ' + key)
    return interface


@dataclass(frozen=True, slots=True)
class PreparedProducerDomain:
    packet_bytes: bytes
    _interface: ag.PreparedSuccessorInterface = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable producer domain packet required')
        value = load_json_strict(self.packet_bytes)
        require(canonical(value) == self.packet_bytes, 'canonical producer domain packet required')
        object.__setattr__(self, '_interface', validate_packet(value))

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)

    def successor_interface(self):
        return self._interface

    def second_step(self):
        return self._interface.second_step()

    def finite(self):
        return self._interface.finite()


def _retained(root):
    result = {}
    for name, expected in RETAINED_PINS.items():
        path = root / name; _no_links(path)
        require(path.is_file(), 'retained AG input missing')
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained AG input changed: ' + name)
        result[name] = raw
    return result


def prepare_producer_domain(root: Path, packages: Path, *, persist_reference_journals=True):
    """Reconstruct retained packages and the five reference sessions.

    Fresh preparation persists reservations before the selected calls. Saved
    evidence reconstruction must explicitly select ``False`` to reconstruct
    the same journal bytes in memory without creating new durable journals.
    This mode does not remove the inherited package-reconstruction workspace.
    """
    require(type(persist_reference_journals) is bool,
            'persist_reference_journals requires an exact bool')
    _no_links(packages)
    require(not packages.exists() and packages.resolve() != root.resolve() and
            root.resolve() not in packages.resolve().parents, 'new external AH package workspace required')
    retained = _retained(root); execution = _execution(retained[AG_ROOT + '/execution.json'])
    for name, expected in execution['source_sha256'].items():
        path = root / name; _no_links(path)
        require(path.is_file() and sha(path.read_bytes()) == expected, 'inherited AG source changed: ' + name)
    producer_before = producer_sources(root)
    interface = ag.prepare_successor_interface(root, packages / 'inherited')
    require(interface.packet_bytes == retained[AG_ROOT + '/packet.json'],
            'fresh AG reconstruction differs from completed baseline')
    journals = packages / 'reference-sessions' if persist_reference_journals else None
    if journals is not None:
        journals.mkdir()
    derived = _derive(interface, journals)
    result = PreparedProducerDomain(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'successor_interface_packet': interface.packet, 'retained_execution_hex': {
            AG_ROOT + '/execution.json': retained[AG_ROOT + '/execution.json'].hex()},
        'retained_sha256': dict(RETAINED_PINS), 'inherited_source_sha256': execution['source_sha256'],
        **derived, 'scope': dict(SCOPE), 'claims': {key: False for key in FALSE_CLAIMS}}))
    require(retained == _retained(root) and producer_before == producer_sources(root),
            'retained source inputs changed during producer-domain preparation')
    if journals is not None:
        for case in result.packet['cases']:
            require((journals / (case['name'] + '.jsonl')).read_bytes() ==
                    bytes.fromhex(case['result']['resource']['journal_hex']), 'AH journal changed during preparation')
    return result


def verify_packet_bytes(raw, recomputed, *, expected_sha256):
    _hash(expected_sha256, 'external producer domain packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and
            type(recomputed) is PreparedProducerDomain and raw == recomputed.packet_bytes,
            'producer domain packet differs from anchored fresh reconstruction')
    PreparedProducerDomain(raw)


def summary(prepared):
    require(type(prepared) is PreparedProducerDomain, 'prepared producer domain required')
    return prepared.packet['summary']
