"""Phase 17AG: truthful finite successor inspection under unchanged meanings.

The offered domain is an explicit finite list of candidate/evidence pairs.  An
empty search result says nothing about offers outside that list.  Inspection
fuel counts checks, not physical work. No supplied final-result bit replaces
recomputation of the finite Facts fields and semantic novelty. Inherited
proposal verdict prefixes are structurally checked; their historical semantic
truth remains external. The separate pinned Lean gate supplies formal
acceptance and the generic search theorems.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from . import second_step as af
from . import task_interpretation as ae
from .bootstrap import _validate_program
from .controller import FAMILIES, _hash
from .finite_kernel import FALSE_CLAIMS
from .materialized import execute_matrix, require, sha
from .resource_ledger import Policy, TARIFFS, add, cost, _no_links

BASE = 'ef4b009ad1308f1a56d9ef3f8cd9f5bd1ffac8ef'
SCHEMA = 'rcp-rclm.phase17ag.successor-interface-packet.v1'
POLICY = 'phase17ag.fixed-meaning-finite-offer-inspection.v1'
REQUEST_SCHEMA = 'phase17ag.finite-successor-request.v1'
RESULT_SCHEMA = 'phase17ag.finite-successor-result.v1'
AF_ROOT = 'artifacts/development/phase17af/op-88f7b2c7fcae/gate'
AF_PACKET_SHA = 'e05bc39c434454fe2ae34aad7097a96d6adcf4e27a49489071761f9988752d61'
AF_EXECUTION_SHA = '05fe3c1461cb476a94a955a4a024e2a14d29e409b7e4fa395d27e3275ce67226'
AF_SOURCE = '88f7b2c7fcae172c8ac0749de65cf7f80a2a2fad'
AF_TREE = '2e4381c970faab22343bfd4666b7b547def38759'
RETAINED_PINS = {AF_ROOT + '/packet.json': AF_PACKET_SHA,
                 AF_ROOT + '/execution.json': AF_EXECUTION_SHA}
MAX_BYTES = 40 * 1024 * 1024
MAX_OFFERS = 64
MAX_PROGRAMS = 512
OBLIGATIONS = ('before_admissible', 'after_admissible', 'typed', 'update_valid',
               'trusted', 'resources', 'matched', 'expansion', 'semantic_failure')
SCOPE = {
    'domain': 'explicit bounded supplied finite observations and offered candidate/evidence pairs',
    'meanings': 'the exact AE legacy22 plus affine260 catalog, names, root, protected contract and resource policy',
    'success': 'all eight finite Facts fields plus actual source semantic failure; separate Lean acceptance required',
    'refusal': 'a failed check excludes that supplied offer, not all possible successors',
    'exhaustion': 'all supplied offers checked and refused; no completeness claim for production or any wider domain',
    'inspection_fuel': 'maximum number of offer checks, not resource tariff, runtime, campaign budget or OS containment',
    'physical_binding': 'fresh reconstruction of the already accepted AF pair only; generic fixtures are mathematical observations',
    'future_existence': 'conditional on a valid offer being in the supplied pool and sufficient inspection fuel',
    'proposal_history': 'inherited ordered verdict prefix structurally checked; no new semantic attestation of historical verdicts',
    'finite_bound': 'fixed finite catalog bounds strict accepted trajectories; no unbounded recursive productivity',
    'historical_campaigns_rerun': False, 'fresh_workers': 0, 'fresh_live_challenges': 0,
    'new_physical_successors': 0, 'physical_candidate_active': False, 'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _same(a, b, label):
    require(canonical(a) == canonical(b), label)


def _nat(value, label, maximum=2 ** 64 - 1):
    require(type(value) is int and 0 <= value <= maximum, 'bounded natural ' + label + ' required')


def _string(value, label):
    require(type(value) is str and len(value) <= 4096, 'bounded string ' + label + ' required')


def _list(value, label, maximum=4096):
    require(type(value) is list and len(value) <= maximum, 'bounded list ' + label + ' required')


def _strings(value, label, maximum=4096):
    _list(value, label, maximum)
    for item in value:
        _string(item, label)


def _nats(value, label, maximum=4096):
    _list(value, label, maximum)
    for item in value:
        _nat(item, label)


def _charges(value):
    _list(value, 'charges', 10000)
    require(all(type(x) is str and x in TARIFFS for x in value), 'unknown reference charge')


def _state(value):
    _exact(value, {'frozen', 'keys', 'program_keys', 'proofs', 'programs', 'declared',
                   'named_frontier', 'semantic', 'package_hash', 'root'}, 'finite state')
    _list(value['frozen'], 'frozen groups', 32)
    for group in value['frozen']:
        _list(group, 'frozen image', 1024)
        for row in group:
            _exact(row, {'path', 'size', 'sha256'}, 'image row')
            _string(row['path'], 'image path'); _string(row['sha256'], 'image digest')
            _nat(row['size'], 'image size', 2 ** 63 - 1)
    _strings(value['keys'], 'keys', MAX_PROGRAMS)
    _strings(value['program_keys'], 'program keys', MAX_PROGRAMS)
    _list(value['programs'], 'programs', MAX_PROGRAMS)
    require(len(value['program_keys']) == len(value['programs']), 'program pair lengths differ')
    for program in value['programs']:
        _validate_program(program)
    _list(value['proofs'], 'proof observations', 512)
    for row in value['proofs']:
        _strings(row, 'proof observation', 3)
        require(len(row) == 3, 'proof observation triple required')
    _nats(value['declared'], 'declared tasks')
    _strings(value['named_frontier'], 'named frontier')
    require(value['declared'] == sorted(set(value['declared'])) and
            value['named_frontier'] == sorted(set(value['named_frontier'])), 'canonical finite sets required')
    semantic = value['semantic']
    _exact(semantic, {'mass_minus_one_dictionary', 'row_selectors', 'goals'}, 'protected observation')
    _list(semantic['mass_minus_one_dictionary'], 'protected dictionary', 512)
    for row in semantic['mass_minus_one_dictionary']:
        _nats(row, 'protected row', 512)
    _nats(semantic['row_selectors'], 'protected selectors', 512)
    _list(semantic['goals'], 'protected goals', 32)
    for row in semantic['goals']:
        _nats(row, 'goal tokens', 512)
    _string(value['package_hash'], 'package identity'); _string(value['root'], 'root identity')


def _context(value):
    _exact(value, {'generator', 'parent_package', 'context_hash', 'transcript_hash',
                   'credits', 'offset', 'rows'}, 'source context')
    for name in ('generator', 'parent_package', 'context_hash', 'transcript_hash'):
        _string(value[name], name)
    _nat(value['credits'], 'context credits'); _nat(value['offset'], 'context offset')
    _list(value['rows'], 'production rows', 64)
    for row in value['rows']:
        _exact(row, {'key', 'family', 'base_score', 'ties'}, 'production row')
        _string(row['key'], 'production key'); _nat(row['family'], 'family')
        require(type(row['base_score']) is int and abs(row['base_score']) <= 2 ** 63 - 1,
                'bounded production score required')
        _nats(row['ties'], 'production tie values', 64)


def _update(value):
    _exact(value, {'key', 'program', 'task', 'task_name', 'parent_package',
                   'candidate_package', 'context_hash', 'charges'}, 'finite update')
    for key in ('key', 'task_name', 'parent_package', 'candidate_package', 'context_hash'):
        _string(value[key], key)
    _validate_program(value['program']); _nat(value['task'], 'task'); _charges(value['charges'])


def _proposal(value):
    _exact(value, {'generator', 'parent_package', 'context_hash', 'transcript_hash',
                   'choices', 'verdicts', 'program', 'candidate_package'}, 'proposal')
    for key in ('generator', 'parent_package', 'context_hash', 'transcript_hash', 'program', 'candidate_package'):
        _string(value[key], key)
    _nats(value['choices'], 'proposal choices', 64)
    _list(value['verdicts'], 'proposal verdicts', 64)
    require(all(type(x) is bool for x in value['verdicts']), 'literal proposal verdict booleans required')


def _offer(value):
    _exact(value, {'update', 'next', 'evidence'}, 'offered pair')
    _update(value['update']); _state(value['next'])
    evidence = value['evidence']
    _exact(evidence, {'root', 'parent_package', 'candidate_package', 'context_hash',
                      'transcript_hash', 'proposal', 'charges'}, 'evidence')
    for key in ('root', 'parent_package', 'candidate_package', 'context_hash', 'transcript_hash'):
        _string(evidence[key], key)
    _proposal(evidence['proposal']); _charges(evidence['charges'])


@dataclass(frozen=True, slots=True)
class FixedInterpretation:
    """Immutable AE meanings. Candidates have no authority to alter these bytes."""
    interpretation_bytes: bytes
    _prepared: ae.PreparedTaskInterpretation = field(init=False, repr=False, compare=False)
    _configuration_bytes: bytes = field(init=False, repr=False, compare=False)
    _task_bytes: tuple[bytes, ...] = field(init=False, repr=False, compare=False)
    _names: tuple[str, ...] = field(init=False, repr=False, compare=False)
    _catalog_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.interpretation_bytes) is bytes and sha(self.interpretation_bytes) == af.AE_PACKET_SHA,
                'exact preexisting AE interpretation required')
        prepared = ae.PreparedTaskInterpretation(self.interpretation_bytes)
        object.__setattr__(self, '_prepared', prepared)
        packet, finite = prepared.packet, prepared.finite().packet
        tasks = finite['protected_packet']['joint_packet']['task_meanings']['tasks']
        protected = finite['protected_packet']
        cfg = {'root': af.FIXED_VERIFIER, 'policy': finite['resource']['policy'],
               'expected_goals': [[goal['effective_marker'], *task['expected_tokens']]
                    for goal, task in zip(protected['before']['goals'],
                        protected['task_contract']['tasks'], strict=True)]}
        object.__setattr__(self, '_configuration_bytes', canonical(cfg))
        object.__setattr__(self, '_task_bytes', tuple(canonical(task) for task in tasks))
        object.__setattr__(self, '_names', tuple(packet['catalog']['legacy_task_ids']))
        object.__setattr__(self, '_catalog_sha256', packet['catalog']['catalog_sha256'])

    @property
    def catalog_sha256(self):
        return self._catalog_sha256

    def configuration(self):
        return load_json_strict(self._configuration_bytes)

    def task_name(self, task):
        _nat(task, 'task')
        if task < ae.LEGACY_COUNT:
            return self._names[task]
        if task < ae.CATALOG_BOUND:
            return ae.affine_task((task - 22) // 65, (task - 22) % 65)['task_id']
        return ''

    def check(self, state, task):
        """Exact finite observation meaning; no proof-proposition replay here."""
        _nat(task, 'task')
        if task >= ae.CATALOG_BOUND:
            return False
        if task < ae.LEGACY_COUNT:
            meaning = load_json_strict(self._task_bytes[task])
            if meaning['kind'] == 'proof':
                return [meaning['task_id'], meaning['meaning']['source_sha256'], meaning['decode_hash']] in state['proofs']
            return any(program['family'] == meaning['family'] and
                       (meaning['program_hash'] is None or key == meaning['program_hash']) and
                       [execute_matrix(program, vector) for vector in meaning['inputs']] == meaning['targets']
                       for key, program in zip(state['program_keys'], state['programs'], strict=True))
        task_meaning = ae.affine_task((task - 22) // 65, (task - 22) % 65)
        return any(ae._affine_matches(ae._program_observation(program), task_meaning)
                   for program in state['programs'])


def _frontier(fixed, state):
    return [task for task in state['declared'] if fixed.check(state, task)]


def _admissible(fixed, state):
    cfg, semantic = fixed.configuration(), state['semantic']
    rows, selectors, goals = (semantic[name] for name in ('mass_minus_one_dictionary', 'row_selectors', 'goals'))
    return (state['root'] == cfg['root'] and state['root'] != '' and state['package_hash'] != '' and
            len(state['frozen']) == 12 and state['keys'] == state['program_keys'] and
            len(state['keys']) == len(set(state['keys'])) and
            state['named_frontier'] == sorted({fixed.task_name(task) for task in state['declared']}) and
            _frontier(fixed, state) == state['declared'] and len(selectors) == 260 and
            all(index < len(rows) for index in selectors) and all(len(row) == 260 for row in rows) and
            len(goals) == 11 and goals == cfg['expected_goals'])


def apply_update(source, update):
    """The finite append, deliberately without a physical package write."""
    _state(source); _update(update)
    result = copy.deepcopy(source)
    result['keys'].append(update['key']); result['program_keys'].append(update['key'])
    result['programs'].append(copy.deepcopy(update['program']))
    result['declared'] = sorted({*source['declared'], update['task']})
    result['named_frontier'] = sorted({*source['named_frontier'], update['task_name']})
    result['package_hash'] = update['candidate_package']
    return result


def _context_valid(context):
    rows = context['rows']
    return (len(rows) == 32 and context['credits'] <= 32 and context['offset'] < 32 and
            len({row['key'] for row in rows}) == len(rows) and
            all(row['family'] < 8 and len(row['ties']) == 5 for row in rows))


def _choose(context, seen):
    if len(seen) >= 4:
        return next((index for i in range(32) if (index := (context['offset'] + 17 * i) % 32) not in seen), None)
    remaining = [index for index in range(len(context['rows'])) if index not in seen]
    def order(index):
        row = context['rows'][index]
        rejected = sum(context['rows'][previous]['family'] == row['family'] for previous in seen)
        tie = row['ties'][rejected] if rejected < len(row['ties']) else 0
        return row['base_score'] + 797 * rejected, tie, index
    return max(remaining, key=order) if remaining else None


def _produced(context, proposal):
    if not _context_valid(context):
        return False
    if any(proposal[key] != context[key] for key in ('generator', 'parent_package', 'context_hash', 'transcript_hash')):
        return False
    choices = proposal['choices']
    if not choices or len(choices) > context['credits'] or len(set(choices)) != len(choices):
        return False
    seen = []
    for index in choices:
        if _choose(context, seen) != index:
            return False
        seen.append(index)
    return (proposal['verdicts'] == [False] * (len(choices) - 1) + [True] and
            proposal['program'] == context['rows'][choices[-1]]['key'] and
            proposal['candidate_package'] != proposal['parent_package'])


def _check_offer(fixed, source, context, expected_charges, offer):
    cfg = fixed.configuration()
    update, after, evidence = (offer[key] for key in ('update', 'next', 'evidence'))
    proposal = evidence['proposal']
    before_frontier, after_frontier = _frontier(fixed, source), _frontier(fixed, after)
    spent = (0, 0, 0, 0)
    for kind in evidence['charges']:
        spent = add(spent, TARIFFS[kind])
    facts = {
        'before_admissible': _admissible(fixed, source),
        'after_admissible': _admissible(fixed, after),
        'typed': canonical(after) == canonical(apply_update(source, update)),
        'update_valid': (update['parent_package'] == source['package_hash'] and
            update['context_hash'] == context['context_hash'] and update['key'] != '' and
            update['key'] not in source['keys'] and update['task'] not in source['declared'] and
            update['task_name'] not in source['named_frontier'] and
            update['task_name'] == fixed.task_name(update['task']) and update['task_name'] != '' and
            update['candidate_package'] != source['package_hash'] and update['candidate_package'] != '' and
            FAMILIES.index(update['program']['family']) < 8 and update['program']['variant'] < 4),
        'trusted': (evidence['root'] == cfg['root'] and source['root'] == cfg['root'] and
            after['root'] == cfg['root'] and cfg['root'] != '' and
            evidence['parent_package'] == source['package_hash'] and evidence['candidate_package'] == after['package_hash'] and
            evidence['context_hash'] == context['context_hash'] and evidence['transcript_hash'] == context['transcript_hash'] and
            context['parent_package'] == source['package_hash'] and context['generator'] != '' and
            context['context_hash'] != '' and context['transcript_hash'] != '' and _context_valid(context)),
        'resources': (evidence['charges'] == update['charges'] == expected_charges and
                      Policy.from_json(cfg['policy']).fits(spent)),
        'matched': (_produced(context, proposal) and update['parent_package'] == context['parent_package'] and
            update['context_hash'] == context['context_hash'] and update['key'] == proposal['program'] and
            after['package_hash'] == proposal['candidate_package']),
        'expansion': set(before_frontier) <= set(after_frontier) and len(before_frontier) < len(after_frontier),
        'semantic_failure': not fixed.check(source, update['task']),
    }
    return {'offer_sha256': digest(offer), 'obligations': facts,
            'failed_obligations': [name for name in OBLIGATIONS if not facts[name]],
            'passes': all(facts.values()), 'source_holds_task': not facts['semantic_failure'],
            'successor_holds_task': fixed.check(after, update['task']),
            'before_frontier': before_frontier, 'after_frontier': after_frontier,
            'reference_charges': list(spent), 'reference_cost': cost(spent)}


def check_offer(fixed, source, context, expected_charges, offer):
    """Check one detached canonical input bundle and report its offer hash."""
    require(type(fixed) is FixedInterpretation, 'fixed interpretation required')
    source, context, expected_charges, offer = copy.deepcopy((source, context, expected_charges, offer))
    _state(source); _context(context); _charges(expected_charges); _offer(offer)
    source, context, expected_charges, offer = load_json_strict(canonical(
        [source, context, expected_charges, offer]))
    _state(source); _context(context); _charges(expected_charges); _offer(offer)
    return _check_offer(fixed, source, context, expected_charges, offer)


def _request(fixed, request):
    require(type(fixed) is FixedInterpretation, 'fixed interpretation required')
    _exact(request, {'schema', 'fixed_catalog_sha256', 'source', 'context', 'expected_charges',
                     'offers', 'inspection_budget'}, 'successor request')
    require(request['schema'] == REQUEST_SCHEMA and request['fixed_catalog_sha256'] == fixed.catalog_sha256,
            'fixed interpretation identity differs')
    _state(request['source']); _context(request['context']); _charges(request['expected_charges'])
    _list(request['offers'], 'offers', MAX_OFFERS)
    for offer in request['offers']:
        _offer(offer)
    _nat(request['inspection_budget'], 'inspection budget', MAX_OFFERS)


def inspect_request(fixed, request, *, expected_source_sha256, expected_request_sha256):
    """Inspect one detached snapshot under its canonical source/request hashes.

    Validate detached original schema types before canonicalization can turn a
    tuple or custom mapping into a list or dict. Evaluate only the canonical
    snapshot, so NFC normalization agrees with the hash and caller mutations
    after anchoring cannot change either the inspected pool or reported scope.
    """
    _hash(expected_source_sha256, 'external source anchor'); _hash(expected_request_sha256, 'external request anchor')
    request = copy.deepcopy(request)
    _request(fixed, request)
    request = load_json_strict(canonical(request))
    _request(fixed, request)
    require(digest(request['source']) == expected_source_sha256 and digest(request) == expected_request_sha256,
            'request or source differs from externally supplied anchor')
    checks, selected = [], None
    for index, offer in enumerate(request['offers'][:request['inspection_budget']]):
        checked = _check_offer(fixed, request['source'], request['context'], request['expected_charges'], offer)
        checks.append({'index': index, **checked})
        if checked['passes']:
            selected = index
            break
    status = ('accepted' if selected is not None else
              'exhausted' if len(checks) == len(request['offers']) else 'budget_stop')
    return {'schema': RESULT_SCHEMA, 'status': status, 'selected_index': selected,
        'source_sha256': expected_source_sha256, 'request_sha256': expected_request_sha256,
        'fixed_catalog_sha256': fixed.catalog_sha256, 'pool_size': len(request['offers']),
        'inspection_budget': request['inspection_budget'], 'examined': len(checks),
        'unexamined': len(request['offers']) - len(checks), 'checks': checks,
        'source_admissible': _admissible(fixed, request['source']),
        'finite_pool_exhausted': status == 'exhausted',
        'no_passing_offer_in_supplied_pool': status == 'exhausted',
        'guarded_nonexistence_established_in_supplied_pool':
            status == 'exhausted' and _admissible(fixed, request['source']),
        'wider_domain_exhaustion_established': False, 'future_successor_existence_established': False,
        'formal_acceptance_established': False, 'physical_execution_attested': False,
        'resource_accounting_complete': False, 'promotion_authorized': False}


def verify_result(fixed, request, result, *, expected_source_sha256, expected_request_sha256):
    expected = inspect_request(fixed, request, expected_source_sha256=expected_source_sha256,
                               expected_request_sha256=expected_request_sha256)
    _same(result, expected, 'successor result differs from full recomputation')


def _state_from_af(value):
    return {**copy.deepcopy(value), 'program_keys': list(value['keys'])}


def selected_request(prepared):
    require(type(prepared) is af.PreparedSecondStep and sha(prepared.packet_bytes) == AF_PACKET_SHA,
            'exact completed AF selected pair required')
    p = prepared.packet
    update, context = p['update'], p['second_context']
    source = _state_from_af(p['finite_projection']['before'])
    evidence = {'root': source['root'], 'parent_package': update['parent_package'],
        'candidate_package': update['candidate_package'], 'context_hash': context['context_hash'],
        'transcript_hash': context['transcript_hash'], 'proposal': copy.deepcopy(p['proposal']),
        'charges': list(p['resource']['charge_sequence'])}
    return {'schema': REQUEST_SCHEMA, 'fixed_catalog_sha256': p['interpretation_packet']['catalog']['catalog_sha256'],
        'source': source, 'context': copy.deepcopy(context), 'expected_charges': list(p['resource']['charge_sequence']),
        'offers': [{'update': copy.deepcopy(update), 'next': _state_from_af(p['finite_projection']['after']),
                    'evidence': evidence}], 'inspection_budget': 1}


CASE_NAMES = ('selected', 'empty', 'zero_budget', 'refusal', 'refusal_then_selected',
              'budget_before_selected', 'stale_parent', 'wrong_context', 'wrong_candidate',
              'changed_protected', 'omitted_charge', 'wrong_program', 'wrong_task_name',
              'already_solved', 'false_successor', 'source_inadmissible')


def case_requests(prepared):
    """Controlled finite observations, never newly executed physical candidates."""
    selected = selected_request(prepared)
    cases = {name: copy.deepcopy(selected) for name in CASE_NAMES}
    wrong = copy.deepcopy(selected['offers'][0]); wrong['evidence']['root'] = 'wrong-root'
    cases['empty']['offers'] = []; cases['empty']['inspection_budget'] = 0
    cases['zero_budget']['inspection_budget'] = 0
    cases['refusal']['offers'] = [copy.deepcopy(wrong)]
    cases['refusal_then_selected']['offers'].insert(0, copy.deepcopy(wrong))
    cases['refusal_then_selected']['inspection_budget'] = 2
    cases['budget_before_selected']['offers'].insert(0, copy.deepcopy(wrong))
    cases['stale_parent']['offers'][0]['update']['parent_package'] = 'stale-parent'
    cases['wrong_context']['offers'][0]['evidence']['context_hash'] = 'wrong-context'
    cases['wrong_candidate']['offers'][0]['evidence']['candidate_package'] = 'wrong-candidate'
    cases['changed_protected']['offers'][0]['next']['semantic']['goals'][0][0] += 1
    cases['omitted_charge']['offers'][0]['evidence']['charges'] = []
    cases['wrong_program']['offers'][0]['update']['program']['parameter_a'] += 1
    cases['wrong_task_name']['offers'][0]['update']['task_name'] = 'renamed-task'
    for name, task in (('already_solved', 259), ('false_successor', 40)):
        update = cases[name]['offers'][0]['update']
        update['task'] = task; update['task_name'] = ae.affine_task((task - 22) // 65, (task - 22) % 65)['task_id']
        cases[name]['offers'][0]['next'] = apply_update(cases[name]['source'], update)
    cases['source_inadmissible']['source']['proofs'].pop(0)
    cases['source_inadmissible']['offers'][0]['next']['proofs'].pop(0)
    return cases


def _derive(prepared):
    fixed = FixedInterpretation(prepared.interpretation().packet_bytes)
    requests = case_requests(prepared)
    cases = [{'name': name, 'request_sha256': digest(request),
              'result': inspect_request(fixed, request, expected_source_sha256=digest(request['source']),
                                        expected_request_sha256=digest(request))}
             for name, request in requests.items()]
    statuses = {row['name']: row['result']['status'] for row in cases}
    require(statuses['selected'] == statuses['refusal_then_selected'] == 'accepted' and
            statuses['zero_budget'] == statuses['budget_before_selected'] == 'budget_stop' and
            all(statuses[name] == 'exhausted' for name in CASE_NAMES if name not in
                {'selected', 'refusal_then_selected', 'zero_budget', 'budget_before_selected'}),
            'selected finite interface outcome differs')
    return {'selected_request': requests['selected'], 'selected_result': cases[0]['result'], 'cases': cases,
        'summary': {'fixed_catalog_tasks': ae.CATALOG_BOUND, 'checked_facts_fields': 8,
            'semantic_novelty_checks': 1, 'selected_offers': 1, 'selected_inspections': 1,
            'selected_status': 'accepted', 'selected_task': af.SELECTED_TASK,
            'controlled_reference_cases': len(cases), 'controlled_accepted_cases': 2,
            'controlled_exhausted_cases': len(cases) - 4, 'controlled_budget_stops': 2,
            'selected_before_frontier': len(requests['selected']['source']['declared']),
            'remaining_declared_capacity_from_af_before': 260,
            'remaining_declared_capacity_from_af_after': 259,
            'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'new_physical_successors': 0,
            'formal_acceptance_required': True, 'inspection_fuel_is_resource_accounting': False}}


def _execution(raw):
    require(type(raw) is bytes and sha(raw) == AF_EXECUTION_SHA, 'exact retained AF completion required')
    record = load_json_strict(raw, require_canonical=False)
    require(record['source_commit'] == AF_SOURCE and record['source_tree'] == AF_TREE and
            record['second_strict_accepted_step_checked'] is True and
            record['fixed_interpretation_two_step_checked'] is True and record['completed'] is True and
            record['proof_mode'] == 'real_pinned_lean_completed_stage_lineage', 'retained AF result differs')
    require(type(record['source_sha256']) is dict and len(record['source_sha256']) == 535,
            'retained AF source inventory differs')
    return record


def validate_packet(packet):
    _exact(packet, {'schema', 'policy', 'base_commit', 'second_step_packet', 'retained_execution_hex',
        'retained_sha256', 'inherited_source_sha256', 'selected_request', 'selected_result', 'cases',
        'summary', 'scope', 'claims'}, 'successor interface packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'successor interface identity differs')
    _same(packet['scope'], SCOPE, 'successor scope differs')
    _same(packet['claims'], {key: False for key in FALSE_CLAIMS}, 'successor claim escalation')
    _same(packet['retained_sha256'], RETAINED_PINS, 'retained AF pins differ')
    require(sha(canonical(packet['second_step_packet'])) == AF_PACKET_SHA, 'retained AF packet differs')
    _exact(packet['retained_execution_hex'], {AF_ROOT + '/execution.json'}, 'retained execution')
    raw = ae._image(packet['retained_execution_hex'][AF_ROOT + '/execution.json'])
    record = _execution(raw)
    _same(packet['inherited_source_sha256'], record['source_sha256'], 'retained AF source bindings differ')
    prepared = af.PreparedSecondStep(canonical(packet['second_step_packet']))
    for key, value in _derive(prepared).items():
        _same(packet[key], value, 'successor interface derivation differs: ' + key)
    return prepared


@dataclass(frozen=True, slots=True)
class PreparedSuccessorInterface:
    packet_bytes: bytes
    _second: af.PreparedSecondStep = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable successor interface packet required')
        value = load_json_strict(self.packet_bytes)
        require(canonical(value) == self.packet_bytes, 'canonical successor interface packet required')
        object.__setattr__(self, '_second', validate_packet(value))

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)

    def second_step(self):
        return self._second

    def finite(self):
        return self._second.finite()


def _retained(root):
    result = {}
    for name, expected in RETAINED_PINS.items():
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'retained AF record missing or linked')
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained AF record changed: ' + name)
        result[name] = raw
    return result


def prepare_successor_interface(root: Path, packages: Path):
    """Freshly reconstruct the exact AF pair, then inspect only finite offers."""
    _no_links(packages)
    require(not packages.exists() and packages.resolve() != root.resolve() and
            root.resolve() not in packages.resolve().parents, 'new external AG package workspace required')
    retained = _retained(root)
    execution = _execution(retained[AF_ROOT + '/execution.json'])
    for name, expected in execution['source_sha256'].items():
        path = root / name
        require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == expected,
                'inherited AF source changed: ' + name)
    prepared = af.prepare_second_step(root, packages)
    require(prepared.packet_bytes == retained[AF_ROOT + '/packet.json'], 'fresh AF pair differs from completed baseline')
    result = PreparedSuccessorInterface(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'second_step_packet': prepared.packet, 'retained_execution_hex': {
            AF_ROOT + '/execution.json': retained[AF_ROOT + '/execution.json'].hex()},
        'retained_sha256': dict(RETAINED_PINS), 'inherited_source_sha256': execution['source_sha256'],
        **_derive(prepared), 'scope': dict(SCOPE), 'claims': {key: False for key in FALSE_CLAIMS}}))
    require(_retained(root) == retained, 'retained AF inputs changed during preparation')
    return result


def verify_packet_bytes(raw, recomputed, *, expected_sha256):
    _hash(expected_sha256, 'external successor packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and
            type(recomputed) is PreparedSuccessorInterface and raw == recomputed.packet_bytes,
            'successor packet differs from anchored fresh reconstruction')
    PreparedSuccessorInterface(raw)


def summary(prepared):
    require(type(prepared) is PreparedSuccessorInterface, 'prepared successor interface required')
    return prepared.packet['summary']
