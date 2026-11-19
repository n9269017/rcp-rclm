"""Phase 17AH source-bound producer, evaluator and reference-grant certificates.

The eight inherited modules retain their exact source generation.  The ninth
module checks the captured source-specific grammar and actual reference prefix,
using a constructive offer builder and the same fixed catalog.  Per-row finite
package identities are captured associations, never physical installation or a
proof of general Python/cryptographic refinement.
"""
from __future__ import annotations

from pathlib import Path
import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from . import successor_interface_lean as inherited
from . import producer_domain as runtime
from .materialized import require, sha
from .successor_lean import program, string

MODULES = (*inherited.MODULES, 'ProducerDomain')
POSITIVE = 'ProducerDomainExamples'
NEGATIVES = ('StaleSourceDomain', 'WrongDescriptorBinding', 'IncompleteProducerGrammar',
             'WrongSourceContext', 'FalseMissingContract', 'SkippedCanonicalContract',
             'ForgedPriorVerdict', 'RepeatedControllerRow', 'SkippedControllerChoice',
             'ContinuedAfterCandidatePass', 'SelfAuthorizedGrant', 'RetargetedSourceGrant',
             'InsufficientGrantReceipt', 'MissingReferenceCharge',
             'ReferenceStopCalledExhaustion', 'CreditStopCalledExhaustion')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = inherited.ALLOWED_AXIOMS
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = dict(inherited.PINS)
_read = inherited._read
_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module
negative_location = inherited.negative_location

GENERIC_NAMES = tuple('Phase17ProducerDomain.' + name for name in (
    'domain_parent', 'domain_shape', 'stale_domain_rejected', 'row_descriptor_bound',
    'row_key_bound', 'grammar_slot_covered', 'producer_order_spec', 'producer_order_mem_iff',
    'ordered_grammar_coverage', 'canonical_task_sound', 'canonical_none_iff',
    'canonical_task_first', 'canonical_exists_iff', 'canonical_semantic_gain',
    'no_task_no_semantic_gain', 'offer_descriptor_cannot_substitute',
    'offer_task_cannot_substitute', 'constructed_offer_bound', 'no_contract_refused',
    'evaluation_of_checked', 'evaluation_acceptance', 'truthful_replay_projects', 'truthful_head',
    'forged_verdict_refused', 'truthful_replay_invariant', 'truthful_exhaustion_covers',
    'truthful_terminal_cannot_continue', 'truthful_exhaustion_rejections',
    'grant_cannot_self_authorize', 'stale_grant_refused', 'reservation_appends_exact_charge',
    'refused_reservation_no_charge', 'granted_prefix_within_policy', 'reserved_cost_not_refunded',
    'unauthorized_step_refused', 'retargeted_context_no_receipt', 'insufficient_allowance_no_receipt',
    'authorized_step_spec', 'authorized_step_construct', 'authorized_replay_projects',
    'authorized_replay_within_policy', 'authorized_replay_exact_charges',
    'authorized_evaluated_acceptance', 'authorized_accepted_exact_charges'))
CASE_NAMES = tuple(row['name'] for row in runtime.case_specs())
SELECTED_NAMES = tuple('Phase17ProducerDomainExamples.' + name for name in (
    'retained_source_chain', 'first_domain_bound', 'second_domain_bound',
    'first_domain_coverage', 'second_domain_coverage',
    'first_source_reference_accepted', 'second_source_reference_accepted',
    'first_accepted_charges_reserved', 'second_accepted_charges_reserved',
    'second_source_seven_refusals',
    *('case_' + name for name in CASE_NAMES),
    'source_contexts_differ', 'first_reference_cost', 'second_reference_cost',
    'resource_denial_no_receipt', 'credit_stop_is_not_grammar_exhaustion',
    'reference_stop_is_not_grammar_exhaustion'))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)


def _nat(value):
    require(type(value) is int and value >= 0, 'natural literal required')
    return str(value)


def _bool(value):
    require(type(value) is bool, 'literal Boolean required')
    return 'true' if value else 'false'


def _list(values, emit):
    require(type(values) is list, 'literal list required')
    return '[' + ', '.join(emit(value) for value in values) + ']'


def _observation(value):
    require(set(value) == {'index', 'passed'}, 'exact controller observation required')
    return '⟨' + _nat(value['index']) + ', ' + _bool(value['passed']) + '⟩'


def _context(name, value):
    return inherited.inherited._context(value).replace('def secondContext :', 'def ' + name + ' :', 1)


def _grant(name, value):
    binding = [('source', value['source_sha256']), ('request', value['request_sha256']),
               ('package', value['package_hash']), ('history', value['history_hash']),
               ('context', value['context_hash']), ('catalog', value['fixed_catalog_sha256']),
               ('evaluator', value['evaluator'])]
    limits = value['policy']['limits']
    require(len(limits) == 4, 'exact grant dimensions required')
    text = 'def ' + name + ' : Grant := {\n  binding := {\n'
    text += ''.join('    ' + key + ' := ' + string(item) + '\n' for key, item in binding)
    text += '  }\n  candidateLimit := ' + _nat(value['candidate_limit']) + '\n'
    for key, item in zip(('referenceCandidateLimit', 'vectorLimit', 'inputLimit', 'outputLimit'), limits, strict=True):
        text += '  ' + key + ' := ' + _nat(item) + '\n'
    return text + '  costLimit := ' + _nat(value['policy']['cost_limit']) + ' }\n'


def render_selected(prepared, root):
    require(type(prepared) is runtime.PreparedProducerDomain, 'exact prepared producer domain required')
    packet = prepared.packet
    cases = packet['cases']
    require(tuple(case['name'] for case in cases) == CASE_NAMES, 'producer case inventory differs')
    before = prepared.second_step().packet['finite_projection']['before']
    after = prepared.second_step().packet['finite_projection']['after']
    for case in cases:
        expected = before if case['request']['source_id'] == 'af_before' else after
        require(case['request']['source'] == {**expected, 'program_keys': expected['keys']},
                'AH formal source differs from retained AF projection')
    _, generic = _split_imports(_read(root, 'ProducerDomain'))
    text = 'import TruthfulSuccessorInterface\n' + generic
    text += '''
namespace Phase17ProducerDomainExamples
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
open Phase17TaskInterpretation Phase17TruthfulSuccessor Phase17ProducerDomain
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000

def fixed : Phase17Finite.Configuration := Phase17SecondStep.fixed
def source0 : State := Phase17SecondStep.observedBefore
def source1 : State := Phase17SecondStep.observedAfter

theorem retained_source_chain : source0 = Phase17Finite.selectedAfter ∧
    source1 = Phase17SecondStep.secondCandidate.next :=
  ⟨Phase17SecondStep.second_before_matches, rfl⟩

def cumulativeCharges (prior : List Nat) : List Phase17Resource.Kind :=
  (List.replicate (prior.length + 1) (trialCharges 2)).flatten

def chargesAt (prior : List Nat) (_index : Nat) (_source : State) : List Phase17Resource.Kind :=
  cumulativeCharges prior
'''
    text += '-- Complete AH input packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    fixed_python = runtime.ag.FixedInterpretation(prepared.second_step().interpretation().packet_bytes)
    case_details = []
    for ci, case in enumerate(cases):
        req, result = case['request'], case['result']
        sid = 0 if req['source_id'] == 'af_before' else 1
        source = 'source' + str(sid)
        context, domain, build, evaluator, grant = ('context' + str(ci), 'domain' + str(ci),
            'builder' + str(ci), 'evaluator' + str(ci), 'grant' + str(ci))
        text += _context(context, req['context'])
        programs = '[' + ', '.join('(' + string(digest(p)) + ', ' + program(p) + ')'
                                  for p in req['programs']) + ']'
        text += 'def ' + domain + ' : Domain := ⟨' + context + ', ' + programs + '⟩\n'
        text += 'def contexts' + str(ci) + ' (_source : State) : Phase17Provenance.Context := ' + context + '\n'
        identities = []
        source_holds = [fixed_python.check(req['source'], task)
                        for task in range(runtime.ae.CATALOG_BOUND)]
        for index, descriptor in enumerate(req['programs']):
            meaning = runtime._missing_contract(fixed_python, req['source'], descriptor,
                                                source_holds=source_holds)
            task = meaning['canonical_task']
            identity = '' if task is None else runtime._trial_offer(
                fixed_python, req, descriptor, index, [], task, [])['update']['candidate_package']
            identities.append(identity)
        text += '-- Identity table is a finite constructor association, not an evaluator history.\n'
        text += 'def identities' + str(ci) + ' : List String := ' + _list(identities, string) + '\n'
        text += ('def ' + build + ' (prior : List Nat) (index task : Nat) : Offer :=\n'
            '  constructOffer fixed ' + source + ' ' + domain + ' (identities' + str(ci) + '.getD index "")\n'
            '    prior index task (cumulativeCharges prior)\n')
        text += ('def ' + evaluator + ' : List Nat → Nat → Bool :=\n'
            '  evaluate fixed contexts' + str(ci) + ' chargesAt ' + source + ' ' + domain + ' ' + build + '\n')
        text += _grant(grant, case['grant'])
        text += ('theorem domain_bound' + str(ci) + ' : DomainBound ' + source + ' ' + domain + ' := by\n'
                 '  refine ⟨rfl, ?_, rfl, rfl, ?_, ?_⟩\n')
        if ci == 0:
            text += '  · exact Phase17SecondStep.second_context_valid\n'
        elif ci == 1:
            text += ('  · unfold Phase17Provenance.ContextValid\n'
                     '    refine ⟨rfl, by decide, by decide, ?_, ?_⟩\n'
                     '    · decide +kernel\n    · decide +kernel\n')
        else:
            text += ('  · rcases domain_bound1.2.1 with ⟨length, _, offset, keys, rows⟩\n'
                     '    exact ⟨length, by decide, offset, keys, rows⟩\n')
        text += ('  · intro index\n    fin_cases index <;> decide +kernel\n'
                 '  · intro family variant\n    fin_cases family <;> fin_cases variant\n')
        for family in runtime.FAMILIES:
            for variant in range(4):
                matching = [index for index, descriptor in enumerate(req['programs'])
                            if descriptor['family'] == family and descriptor['variant'] == variant]
                require(len(matching) == 1, 'unique actual grammar slot witness required')
                text += '    · exact ⟨⟨' + _nat(matching[0]) + ', by decide⟩, rfl, rfl⟩\n'
        observations = result['observations']
        text += ('def observations' + str(ci) + ' : List Phase17Controller.Observation := ' +
                 _list(observations, _observation) + '\n')
        case_steps = []
        for ti in range(len(observations) + 1):
            prefix = observations[:ti]
            charges = ['candidate', 'vector', 'vector'] * ti
            state = f'state{ci}_{ti}'
            text += ('def ' + state + ' : ExecutionState :=\n'
                '  ⟨⟨' + _nat(req['context']['credits']) + ', ' + _list(prefix, _observation) + ', none⟩, ' +
                inherited.inherited._kinds(charges) + '⟩\n')
        for ti, trial in enumerate(result['trials']):
            index, task = trial['index'], trial['canonical_task']
            choice = f'choice{ci}_{ti}'
            expected = 'none' if task is None else 'some ' + _nat(task)
            canonical_expr = ('canonicalTask fixed ' + source + ' (Phase17Provenance.rowAt ' + context + ' ' +
                _nat(index) + ').key (rowProgram ' + domain + ' ' + _nat(index) + ')')
            text += 'theorem ' + choice + ' : ' + canonical_expr + ' = ' + expected + ' := by decide +kernel\n'
            prior = [row['index'] for row in result['trials'][:ti]]
            prior_literal = _list(prior, _nat)
            eval_lemma = f'evaluation{ci}_{ti}'
            if task is None:
                text += ('theorem ' + eval_lemma + ' (prior : List Nat) : ' + evaluator + ' prior ' +
                    _nat(index) + ' = false :=\n'
                    '  no_contract_refused fixed contexts' + str(ci) + ' chargesAt ' + source + ' ' + domain +
                    ' ' + build + ' prior ' + _nat(index) + ' ' + choice + '\n')
            else:
                offer = trial['trial_offer']
                expected_offer = runtime._trial_offer(fixed_python, req, req['programs'][index],
                    index, prior, task, ['candidate', 'vector', 'vector'] * (ti + 1))
                require(offer == expected_offer and trial['verdict'] is True,
                        'selected formal offer is not the constructive observed trial')
                check_name = f'check{ci}_{ti}'
                offered = build + ' ' + prior_literal + ' ' + _nat(index) + ' ' + _nat(task)
                text += ('theorem ' + check_name + ' : check fixed contexts' + str(ci) +
                    ' (chargesAt ' + prior_literal + ' ' + _nat(index) + ') ' + source + ' (' + offered +
                    ') = true := by decide +kernel\n')
                text += ('theorem ' + eval_lemma + ' : ' + evaluator + ' ' + prior_literal + ' ' +
                    _nat(index) + ' = true := by\n'
                    '  have requestBound : RequestBound contexts' + str(ci) + ' ' + source + ' ' + domain +
                    ' := ⟨rfl, domain_bound' + str(ci) + '⟩\n'
                    '  have offerBound : OfferBound fixed ' + source + ' ' + domain + ' ' + _nat(index) +
                    ' ' + _nat(task) + ' (' + offered + ') :=\n'
                    '    constructed_offer_bound fixed ' + source + ' ' + domain + ' _ ' + prior_literal +
                    ' ' + _nat(index) + ' ' + _nat(task) + ' _ (by decide) ' + choice + '\n'
                    '  exact evaluation_of_checked fixed contexts' + str(ci) + ' chargesAt ' + source + ' ' + domain +
                    ' ' + build + ' ' + prior_literal + ' ' + _nat(index) + ' ' + _nat(task) + '\n'
                    '    ' + choice + ' requestBound offerBound ' + check_name + '\n')
            step_name = f'step{ci}_{ti}'
            text += ('theorem ' + step_name + ' : authorizedStep ' + grant + ' ' + grant + ' ' + grant + '.binding\n'
                '    ' + context + ' ' + evaluator + ' 2 state' + str(ci) + '_' + str(ti) + ' ' +
                _observation(observations[ti]) + ' = some state' + str(ci) + '_' + str(ti + 1) + ' := by\n'
                '  apply authorized_step_construct\n'
                '  · decide +kernel\n'
                '  · decide +kernel\n'
                '  · exact (' + eval_lemma + ((' ' + prior_literal) if task is None else '') + ').symm\n'
                '  · decide +kernel\n')
            case_steps.append(step_name)
        final = f'state{ci}_{len(observations)}'
        name = 'case_' + case['name']
        text += ('theorem ' + name + ' : authorizedReplay ' + grant + ' ' + grant + ' ' + grant + '.binding\n'
            '    ' + context + ' ' + evaluator + ' 2 state' + str(ci) + '_0 observations' + str(ci) +
            ' = some ' + final + ' := by\n'
            '  have finalAllowed : admissibleExecution ' + grant + ' ' + grant + ' ' + grant + '.binding ' +
            context + ' ' + final + ' := by decide +kernel\n'
            '  simp only [observations' + str(ci) + ', authorizedReplay, ' +
            ', '.join([*case_steps, *(['Option.bind_some'] if case_steps else []), 'finalAllowed', 'if_true']) + ']\n')
        action = {'await_root_verification': '.awaitRoot', 'resource_exhausted': '.resourceExhausted',
                  'search_exhausted': '.searchExhausted'}.get(result['controller_action'])
        if action is None:
            require(result['controller_action'] == 'evaluate', 'unexpected selected controller action')
            action = '(.evaluate ' + _nat(result['checkpoints'][-1]['candidate_index']) + ')'
        text += ('theorem terminal' + str(ci) + ' : Phase17Controller.decision ' + context + ' ' + final +
            '.controller = some ' + action + ' := by decide +kernel\n')
        case_details.append((ci, source, context, domain, build, evaluator, grant, final))
    text += '''
theorem first_domain_bound : DomainBound source0 domain0 := domain_bound0
theorem second_domain_bound : DomainBound source1 domain1 := domain_bound1

theorem first_domain_coverage : (producerOrder context0).Nodup ∧
    (producerOrder context0).length = 32 ∧ (producerOrder context0).toFinset = Finset.range 32 :=
  producer_order_spec context0 (domain_shape source0 domain0 first_domain_bound)

theorem second_domain_coverage : (producerOrder context1).Nodup ∧
    (producerOrder context1).length = 32 ∧ (producerOrder context1).toFinset = Finset.range 32 :=
  producer_order_spec context1 (domain_shape source1 domain1 second_domain_bound)

theorem first_source_reference_accepted :
    Accepted fixed contexts0 (chargesAt [] 30) source0 (builder0 [] 30 41) :=
  check_sound fixed contexts0 (chargesAt [] 30) Phase17SecondStep.selected_catalog_complete
    source0 (builder0 [] 30 41) check0_0

theorem second_source_reference_accepted :
    Accepted fixed contexts1 (chargesAt [19, 5, 18, 27, 13, 30, 15] 0) source1
      (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) :=
  check_sound fixed contexts1 (chargesAt [19, 5, 18, 27, 13, 30, 15] 0)
    Phase17SecondStep.selected_catalog_complete source1
    (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) check1_7

theorem first_accepted_charges_reserved :
    (builder0 [] 30 41).evidence.charges = state0_1.spent ∧
    (builder0 [] 30 41).update.charges = state0_1.spent ∧
    Phase17Resource.Fits grant0.policy state0_1.spent := by decide +kernel

theorem second_accepted_charges_reserved :
    (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56).evidence.charges = state1_8.spent ∧
    (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56).update.charges = state1_8.spent ∧
    Phase17Resource.Fits grant1.policy state1_8.spent := by decide +kernel

theorem second_source_seven_refusals :
    evaluator1 [] 19 = false ∧ evaluator1 [19] 5 = false ∧
    evaluator1 [19, 5] 18 = false ∧ evaluator1 [19, 5, 18] 27 = false ∧
    evaluator1 [19, 5, 18, 27] 13 = false ∧ evaluator1 [19, 5, 18, 27, 13] 30 = false ∧
    evaluator1 [19, 5, 18, 27, 13, 30] 15 = false :=
  ⟨evaluation1_0 _, evaluation1_1 _, evaluation1_2 _, evaluation1_3 _,
    evaluation1_4 _, evaluation1_5 _, evaluation1_6 _⟩

theorem source_contexts_differ : source0.packageHash ≠ source1.packageHash ∧
    context0.parentPackage ≠ context1.parentPackage ∧ context0.contextHash ≠ context1.contextHash := by
  decide +kernel

theorem first_reference_cost : Phase17Resource.totalCost state0_1.spent = 112 ∧
    Phase17Resource.Fits grant0.policy state0_1.spent := by decide +kernel

theorem second_reference_cost : Phase17Resource.totalCost state1_8.spent = 896 ∧
    Phase17Resource.Fits grant1.policy state1_8.spent := by decide +kernel

theorem resource_denial_no_receipt :
    authorizedStep grant4 grant4 grant4.binding context4 evaluator4 2 state4_3 ⟨27, false⟩ = none :=
  insufficient_allowance_no_receipt grant4 grant4 grant4.binding context4 evaluator4 2
    state4_3 ⟨27, false⟩ (by decide +kernel)

theorem credit_stop_is_not_grammar_exhaustion :
    Phase17Controller.decision context2 state2_4.controller = some .resourceExhausted ∧
      state2_4.controller.observations.length < 32 := ⟨terminal2, by decide⟩

theorem reference_stop_is_not_grammar_exhaustion :
    Phase17Controller.decision context4 state4_3.controller = some (.evaluate 27) ∧
      state4_3.controller.observations.length < 32 := ⟨terminal4, by decide⟩

end Phase17ProducerDomainExamples
'''
    return text.encode('utf-8')


def render_positive(prepared):
    require(type(prepared) is runtime.PreparedProducerDomain, 'exact prepared producer domain required')
    return ('import ProducerDomain\n' + '\n'.join('#print axioms ' + n for n in NAMES) + '\n').encode()


def render_negative(prepared, label):
    require(type(prepared) is runtime.PreparedProducerDomain and label in NEGATIVES,
            'exact producer domain negative required')
    direct = {
        'StaleSourceDomain': 'DomainBound source1 domain0',
        'WrongDescriptorBinding': 'OfferBound fixed source0 domain0 30 41 (builder0 [] 31 41)',
        'IncompleteProducerGrammar': 'DomainBound source0 { domain0 with programs := domain0.programs.take 31 }',
        'WrongSourceContext': 'RequestBound contexts0 source0 domain1',
        'RepeatedControllerRow': 'Phase17Controller.replay context1 (Phase17Controller.initial 32) [⟨19, false⟩, ⟨19, false⟩] ≠ none',
        'SkippedControllerChoice': 'Phase17Controller.advance context1 (Phase17Controller.initial 32) ⟨5, false⟩ ≠ none',
        'SelfAuthorizedGrant': 'Authorized grant0 { grant0 with costLimit := 3585 } grant0.binding',
        'RetargetedSourceGrant': 'Authorized grant0 grant0 grant1.binding',
    }
    prefix = '''import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    if label in direct:
        assertion, proof = 'decide (' + direct[label] + ')', 'by decide +kernel'
    elif label == 'FalseMissingContract':
        assertion = 'decide (canonicalTask fixed source1 (Phase17Provenance.rowAt context1 19).key (rowProgram domain1 19) = some 40)'
        proof = 'by simp only [wrongClaim, choice1_0]; decide +kernel'
    elif label == 'SkippedCanonicalContract':
        assertion = 'decide (canonicalTask fixed source1 (Phase17Provenance.rowAt context1 0).key (rowProgram domain1 0) = some 57)'
        proof = 'by simp only [wrongClaim, choice1_7]; decide +kernel'
    elif label == 'ForgedPriorVerdict':
        assertion = 'decide (truthfulReplay context1 evaluator1 (Phase17Controller.initial 32) [⟨19, true⟩] ≠ none)'
        proof = 'by simp only [wrongClaim, truthfulReplay, Phase17Controller.initial, Phase17Controller.seen, List.map_nil, evaluation1_0, Bool.true_eq_false, if_false]; decide +kernel'
    elif label == 'ContinuedAfterCandidatePass':
        assertion = 'decide (Phase17Controller.advance context1 state1_8.controller ⟨0, false⟩ ≠ none)'
        proof = 'by simp only [wrongClaim, Phase17Controller.advance, terminal1]; decide +kernel'
    elif label == 'InsufficientGrantReceipt':
        assertion = 'decide (authorizedStep grant4 grant4 grant4.binding context4 evaluator4 2 state4_3 ⟨27, false⟩ ≠ none)'
        proof = 'by simp only [wrongClaim, resource_denial_no_receipt]; decide +kernel'
    elif label == 'MissingReferenceCharge':
        assertion = 'decide (authorizedReplay grant1 grant1 grant1.binding context1 evaluator1 2 state1_0 observations1 = some { state1_8 with spent := [] })'
        proof = 'by simp only [wrongClaim, case_second_source]; decide +kernel'
    elif label == 'ReferenceStopCalledExhaustion':
        assertion = 'decide (Phase17Controller.decision context4 state4_3.controller = some .searchExhausted)'
        proof = 'by simp only [wrongClaim, terminal4]; decide +kernel'
    else:
        require(label == 'CreditStopCalledExhaustion', 'unhandled producer negative')
        assertion = 'decide (Phase17Controller.decision context2 state2_4.controller = some .searchExhausted)'
        proof = 'by simp only [wrongClaim, terminal2]; decide +kernel'
    text = prefix + 'def wrongClaim : Bool := ' + assertion + '\n'
    text += 'theorem actual_rejection : wrongClaim = false := ' + proof + '\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17ProducerDomainControl\n').encode()


def sources(prepared, root):
    require(type(prepared) is runtime.PreparedProducerDomain, 'exact prepared producer domain required')
    prior = inherited.sources(prepared.successor_interface(), root)
    result = {name: prior[name] for name in inherited.MODULES}
    result[MODULES[-1]] = render_selected(prepared, root)
    result[POSITIVE] = render_positive(prepared)
    result.update({name: render_negative(prepared, name) for name in NEGATIVES})
    for name, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + name)
    return result


def parse_audits(stdout):
    cursor, audits = 0, {}
    for name in NAMES:
        match = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'missing or reordered producer domain audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved producer domain axiom')
        audits[name] = axioms
        cursor = match.end()
    require(cursor == len(stdout), 'unexpected producer domain audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected producer domain negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
