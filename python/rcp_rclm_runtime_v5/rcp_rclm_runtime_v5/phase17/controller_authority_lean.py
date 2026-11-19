"""Phase17AI certificates for the anchored local issuer and actual AH sessions.

The AH source modules and their selected facts are reused without changing their
meaning. New literals bind the actual provisioned policy, leases, restored
checkpoints, journal heads and reserved envelopes. Hash identity is a retained
binding, not a proof of external issuer identity or physical execution.
"""
from __future__ import annotations

import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from . import producer_domain_lean as inherited
from . import controller_authority as runtime
from .materialized import require, sha
from .successor_lean import program, string

MODULES = (*inherited.MODULES, 'ControllerAuthority')
POSITIVE = 'ControllerAuthorityExamples'
NEGATIVES = ('SelfIssuedLease', 'StaleAuthorityHead', 'WrongSourcePermit',
    'WrongCheckpointPermit', 'WrongObjectiveAuthority', 'WrongEvaluatorAuthority',
    'OverBudgetIssuance', 'OutstandingLeaseIssue', 'ConsumedSourceReissue',
    'UnissuedCompletion', 'WrongLeaseCompletion', 'ForgedControllerCompletion',
    'UnderReservedGrant', 'RefundedReservation', 'ReplayedCompletion',
    'TerminalCheckpointIssue', 'ReopenedPendingCompletion', 'CrossSourceCompletion')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = inherited.ALLOWED_AXIOMS
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = dict(inherited.PINS)
_read = inherited._read
_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module
negative_location = inherited.negative_location

GENERIC_NAMES = tuple('Phase17ControllerAuthority.' + name for name in (
    'issued_spec', 'issued_construct', 'self_policy_refused', 'stale_head_refused',
    'unpermitted_source_refused', 'outstanding_lease_refused', 'consumed_source_refused',
    'insufficient_pool_refused', 'issued_grant_scope', 'issued_semantics_fixed',
    'issued_initial_checkpoint', 'issued_exact_reservation', 'issued_within_pool',
    'issued_cost_not_refunded', 'issued_vector_exact', 'completed_spec',
    'completed_construct', 'unissued_completion_refused', 'completed_exact_retention',
    'completed_cost_not_refunded', 'completed_vector_not_refunded', 'completed_source_consumed',
    'completed_no_replay', 'completed_truthful_controller', 'completed_controller_projection',
    'completed_controller_invariant', 'completed_exact_work',
    'completed_within_issued_envelope', 'completed_actual_cost_bound', 'stop_retains_accounting',
    'pending_stop_refused', 'denied_spec', 'denied_no_new_reservation',
    'denied_is_insufficient', 'reopened_state_retains_charges',
    'reopened_pending_no_completion', 'interrupted_pending_retained',
    'interrupted_issuance_refused', 'interrupted_completion_refused',
    'completed_stale_head_refused', 'completed_stopped', 'reachable_debit_exact',
    'reachable_within_pool', 'reachable_pending_issued', 'reachable_completed_sources',
    'reachable_no_duplicate_sources', 'reachable_actual_cost_reserved',
    'reachable_actual_cost_within_pool'))
CASE_NAMES = tuple(row['name'] for row in runtime.case_specs())
SELECTED_NAMES = tuple('Phase17ControllerAuthorityExamples.' + name for name in (
    *('case_' + name for name in CASE_NAMES), 'main_issued_grants',
    'main_exact_reservation', 'main_actual_reference_work', 'main_unused_envelope_retained',
    'main_checkpoints_updated', 'main_reopen_preserves_budget', 'main_sources_consumed_once',
    'first_completed_acceptance', 'second_completed_acceptance',
    'fixed_policy_meanings', 'aggregate_denial_no_new_lease',
    'reference_stop_is_not_exhaustion', 'credit_stop_is_not_exhaustion',
    'pending_reopen_cannot_complete', 'pending_stop_is_refused'))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)


def _nat(value):
    require(type(value) is int and value >= 0, 'natural literal required')
    return str(value)


def _strings(values):
    require(type(values) is list and all(type(v) is str for v in values), 'string list required')
    return '[' + ', '.join(string(v) for v in values) + ']'


def _permit(name, item, policy):
    raw = item['initial_checkpoint']
    require(raw['initial_credits'] == policy['candidate_credits'] and
            raw['observations'] == [] and raw['stop'] is None and
            sha(canonical(raw)) == item['initial_checkpoint_sha256'],
            'authority initial checkpoint is not the exact fresh restored prefix')
    fields = {'source': item['source_sha256'], 'request': item['request_sha256'],
        'package': item['package_hash'], 'history': item['history_hash'],
        'context': item['context_hash'], 'catalog': item['fixed_catalog_sha256'],
        'evaluator': policy['evaluator']}
    text = 'def ' + name + ' : Permit := {\n  name := ' + string(item['source_id']) + '\n  binding := {\n'
    text += ''.join('    ' + key + ' := ' + string(value) + '\n' for key, value in fields.items())
    text += '  }\n  model := ' + string(item['model_state_hash']) + '\n'
    text += '  prefixHash := ' + string(item['initial_prefix_hash']) + '\n'
    text += '  initial := Phase17Controller.initial ' + _nat(policy['candidate_credits']) + '\n'
    text += '  checkpoint := ' + string(item['initial_checkpoint_sha256']) + '\n'
    text += '  frozen := ' + string(item['freeze_hash']) + '\n'
    text += '  objective := ' + string(policy['objective']) + '\n'
    return text + '  evaluatorCode := ' + string(policy['implementation_sha256']) + ' }\n'


def _policy(name, value, policy_sha, permits):
    require(digest(value) == policy_sha, 'selected authority policy anchor differs')
    text = 'def ' + name + ' : AuthorityPolicy := {\n'
    for key, item in (('authority', value['authority_id']), ('policy', policy_sha),
        ('catalog', value['fixed_catalog_sha256']), ('objective', value['objective']),
        ('evaluator', value['evaluator']), ('evaluatorCode', value['implementation_sha256'])):
        text += '  ' + key + ' := ' + string(item) + '\n'
    text += '  candidateCredits := ' + _nat(value['candidate_credits']) + '\n'
    text += '  sessionAttempts := ' + _nat(value['session_attempts']) + '\n'
    text += '  poolAttempts := ' + _nat(value['total_attempts']) + '\n'
    return text + '  sources := [' + ', '.join(permits) + '] }\n'


def _unselected_evaluator(name, request, producer):
    """Instantiate the actual AH evaluator for a permitted but unused source.

    Selected AH cases cover both main source sessions. A four-credit policy also
    permits the before-source without executing it, so its complete evaluator
    definition is supplied rather than pretending its context has 32 credits.
    No extra execution or existence is asserted for that unused permit.
    """
    source = 'Phase17ProducerDomainExamples.source' + ('0' if request['source_id'] == 'af_before' else '1')
    context = name + 'Context'; domain = name + 'Domain'; builder = name + 'Builder'
    text = inherited._context(context, request['context'])
    programs = '[' + ', '.join('(' + string(digest(p)) + ', ' + program(p) + ')'
                              for p in request['programs']) + ']'
    text += 'def ' + domain + ' : Domain := ⟨' + context + ', ' + programs + '⟩\n'
    fixed = runtime.ah.ag.FixedInterpretation(producer.second_step().interpretation().packet_bytes)
    source_holds = [fixed.check(request['source'], i) for i in range(runtime.ah.ae.CATALOG_BOUND)]
    identities = []
    for index, descriptor in enumerate(request['programs']):
        task = runtime.ah._missing_contract(fixed, request['source'], descriptor,
                                            source_holds=source_holds)['canonical_task']
        identity = '' if task is None else runtime.ah._trial_offer(fixed, request, descriptor,
                          index, [], task, [])['update']['candidate_package']
        identities.append(identity)
    text += 'def ' + name + 'Identities : List String := ' + _strings(identities) + '\n'
    text += 'def ' + name + 'Contexts (_source : Phase17Finite.State) := ' + context + '\n'
    text += ('def ' + builder + ' (prior : List Nat) (index task : Nat) : Phase17TruthfulSuccessor.Offer :=\n'
        '  constructOffer Phase17ProducerDomainExamples.fixed ' + source + ' ' + domain + ' (' + name + 'Identities.getD index "")\n'
        '    prior index task (Phase17ProducerDomainExamples.cumulativeCharges prior)\n')
    text += ('def ' + name + 'Evaluator : List Nat → Nat → Bool :=\n'
        '  evaluate Phase17ProducerDomainExamples.fixed ' + name + 'Contexts Phase17ProducerDomainExamples.chargesAt ' + source + ' ' + domain + ' ' + builder + '\n')
    return text, context, name + 'Evaluator'


def render_selected(prepared, root):
    require(type(prepared) is runtime.PreparedControllerAuthority, 'exact prepared controller authority required')
    packet = prepared.packet; cases = packet['cases']; producer = prepared.producer_domain()
    old = producer.packet['cases']
    require(tuple(case['name'] for case in cases) == CASE_NAMES, 'authority case inventory differs')
    _, generic = _split_imports(_read(root, 'ControllerAuthority'))
    text = 'import ProducerDomain\n' + generic
    text += '''
namespace Phase17ControllerAuthorityExamples
open Phase17ProducerDomain Phase17ControllerAuthority
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    text += '-- Exact AI authority packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    projections = []
    for ci, case in enumerate(cases):
        policy = case['authority_policy']; policy_name = 'policy' + str(ci)
        permits = []
        contexts = []; evaluators = []
        for pi, item in enumerate(policy['source_permits']):
            name = f'permit{ci}_{pi}'; permits.append(name)
            text += _permit(name, item, policy)
            request = runtime._request(producer, policy, item['source_id'])
            matches = [i for i, original in enumerate(old) if canonical(original['request']) == canonical(request)]
            if matches:
                chosen = matches[0]; contexts.append('Phase17ProducerDomainExamples.context' + str(chosen))
                evaluators.append('Phase17ProducerDomainExamples.evaluator' + str(chosen))
            else:
                extra, context, evaluator = _unselected_evaluator(f'unselected{ci}_{pi}', request, producer)
                text += extra; contexts.append(context); evaluators.append(evaluator)
        require([p['source_id'] for p in policy['source_permits']] == list(runtime.ah.SOURCES),
                'exact authority source permit ordering required')
        text += _policy(policy_name, policy, case['policy_sha256'], permits)
        text += 'theorem policy_valid' + str(ci) + ' : PolicyValid ' + policy_name + ' := by decide +kernel\n'
        text += ('def contexts' + str(ci) + ' (source : Permit) : Phase17Provenance.Context :=\n'
                 '  if source.name = "af_before" then ' + contexts[0] + ' else ' + contexts[1] + '\n')
        text += ('def evaluators' + str(ci) + ' (source : Permit) : List Nat → Nat → Bool :=\n'
                 '  if source.name = "af_before" then ' + evaluators[0] + ' else ' + evaluators[1] + '\n')
        text += f'def state{ci}_0 : AuthorityState := Phase17ControllerAuthority.initial\n'
        text += f'theorem reachable{ci}_0 : Reachable {policy_name} contexts{ci} evaluators{ci} state{ci}_0 := .initial\n'
        current = f'state{ci}_0'; reach = f'reachable{ci}_0'; step = 0; session_index = 0
        completions = []
        for event in case['events'][1:]:
            body = event['body']; kind = body['kind']; head = string(event['previous'])
            if ci == 0 and kind == 'reserve' and session_index == 1:
                reopened = f'state{ci}_reopened'
                text += f'def {reopened} : AuthorityState := reopen {current}\n'
                text += f'theorem reachable{ci}_reopened : Reachable {policy_name} contexts{ci} evaluators{ci} {reopened} := .reopen {reach}\n'
                current, reach = reopened, f'reachable{ci}_reopened'
            step += 1; following = f'state{ci}_{step}'; next_reach = f'reachable{ci}_{step}'
            if kind == 'reserve':
                lease = body['lease']; source_id = lease['source_permit']['source_id']
                pi = runtime.ah.SOURCES.index(source_id); permit = permits[pi]
                require(lease['serial'] == len(completions) and
                        lease['authority_policy_sha256'] == case['policy_sha256'] and
                        lease['authority_id'] == policy['authority_id'] and
                        lease['objective'] == policy['objective'] and
                        lease['evaluator'] == policy['evaluator'] and
                        lease['implementation_sha256'] == policy['implementation_sha256'] and
                        lease['source_permit'] == policy['source_permits'][pi],
                        'authority lease issuer or source binding differs')
                lease_name = f'lease{ci}_{session_index}'
                text += f'def {lease_name} : Lease := issuedLease {policy_name} {permit} {_nat(lease["serial"])}\n'
                text += inherited._grant(f'capturedGrant{ci}_{session_index}', lease['reference_grant'])
                text += f'theorem grant_bound{ci}_{session_index} : {lease_name}.grant = capturedGrant{ci}_{session_index} := by decide +kernel\n'
                text += (f'def {following} : AuthorityState := {{ {current} with\n'
                    f'  nextSerial := {current}.nextSerial + 1\n'
                    f'  reservedAttempts := {current}.reservedAttempts + {policy_name}.sessionAttempts\n'
                    f'  pending := some {lease_name}\n  liveLease := some {lease_name} }}\n')
                text += (f'theorem issue{ci}_{session_index} : issue {policy_name} {policy_name} {head} {head}\n'
                    f'    {current} {permit} = some {following} := by decide +kernel\n')
                text += (f'theorem {next_reach} : Reachable {policy_name} contexts{ci} evaluators{ci} {following} :=\n'
                    f'  .issue {reach} {policy_name} {head} {head} {permit} issue{ci}_{session_index}\n')
                current, reach = following, next_reach
            elif kind == 'complete':
                session = case['sessions'][session_index]
                require(session['lease'] == lease and digest(session['result']) == body['result_sha256'],
                        'actual completion differs from issued session')
                matches = [i for i, original in enumerate(old) if all(canonical(session[key]) ==
                    canonical(original[key]) for key in ('request', 'grant', 'result'))]
                require(len(matches) == 1, 'selected authority result must equal one complete checked AH case')
                oi = matches[0]; result = session['result']; count = result['examined']
                completion = f'completion{ci}_{session_index}'; completions.append(completion)
                text += (f'def {completion} : Completion := {{\n  lease := {lease_name}\n'
                    f'  observations := Phase17ProducerDomainExamples.observations{oi}\n'
                    f'  execution := Phase17ProducerDomainExamples.state{oi}_{count}\n'
                    f'  checkpoint := {string(body["final_checkpoint_sha256"])} }}\n')
                text += (f'theorem valid_completion{ci}_{session_index} : CompletionValid {policy_name}\n'
                    f'    contexts{ci} evaluators{ci} {current} {completion} := by\n'
                    '  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,\n'
                    '    by decide +kernel, by decide +kernel, by decide +kernel, ?_, ?_,\n'
                    '    by decide +kernel, by decide +kernel⟩\n'
                    f'  · exact Phase17ProducerDomainExamples.case_{old[oi]["name"]}\n'
                    f'  · change SessionStopped {lease_name} Phase17ProducerDomainExamples.context{oi} Phase17ProducerDomainExamples.state{oi}_{count}\n'
                    '')
                if result['controller_action'] == 'evaluate':
                    text += (f'    simpa only [SessionStopped, Phase17ProducerDomainExamples.terminal{oi}] using\n'
                             f'      (show reserveTrial {lease_name}.grant Phase17ProducerDomainExamples.state{oi}_{count}.spent 2 = none from by decide +kernel)\n')
                else:
                    text += f'    simp only [SessionStopped, Phase17ProducerDomainExamples.terminal{oi}]\n'
                text += (f'def {following} : AuthorityState := {{ {current} with\n  pending := none\n  liveLease := none\n'
                    f'  consumed := {current}.consumed ++ [{completion}.lease.source.name]\n'
                    f'  completed := {current}.completed ++ [{completion}] }}\n')
                text += (f'theorem complete{ci}_{session_index} : complete {policy_name} contexts{ci} evaluators{ci}\n'
                    f'    {head} {head} {current} {completion} = some {following} :=\n'
                    f'  completed_construct {policy_name} contexts{ci} evaluators{ci} {head} {current}\n'
                    f'    {completion} valid_completion{ci}_{session_index}\n')
                text += (f'theorem {next_reach} : Reachable {policy_name} contexts{ci} evaluators{ci} {following} :=\n'
                    f'  .complete {reach} {head} {head} {completion} complete{ci}_{session_index}\n')
                current, reach = following, next_reach; session_index += 1
            elif kind in ('stop', 'deny'):
                text += f'def {following} : AuthorityState := interrupt {current}\n'
                if kind == 'stop':
                    text += f'theorem stop{ci} : stop {current} = some {following} := by decide +kernel\n'
                else:
                    source_id = body['lease']['source_permit']['source_id']; pi = runtime.ah.SOURCES.index(source_id)
                    text += (f'theorem deny{ci} : deny {policy_name} {policy_name} {head} {head}\n'
                        f'    {current} {permits[pi]} = some {following} := by decide +kernel\n')
                text += (f'theorem {next_reach} : Reachable {policy_name} contexts{ci} evaluators{ci} {following} :=\n'
                    f'  .interrupt {reach}\n')
                current, reach = following, next_reach
            else:
                raise ValueError('unhandled selected authority event')
        final = case['final_state']
        require(final['reserved'] == [final['serial'] * policy['session_attempts'] * m for m in (1, 2, 8, 8)],
                'captured final reservation does not equal all issued envelopes')
        vector = '[' + ', '.join(_nat(v) for v in final['reserved']) + ']'
        consumed = _strings(final['consumed'])
        text += (f'theorem case_{case["name"]} : Reachable {policy_name} contexts{ci} evaluators{ci} {current} ∧\n'
            f'    reservedVector {current} = {vector} ∧ reservedCost {current} = {_nat(final["reserved_cost"])} ∧\n'
            f'    {current}.nextSerial = {_nat(final["serial"])} ∧ {current}.consumed = {consumed} :=\n'
            f'  ⟨{reach}, by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩\n')
        projections.append((current, reach))
    text += '''
theorem main_issued_grants : lease0_0.grant = Phase17ProducerDomainExamples.grant0 ∧ lease0_1.grant = Phase17ProducerDomainExamples.grant1 := by decide +kernel

theorem main_exact_reservation : reservedVector state0_5 = [64, 128, 512, 512] ∧
    reservedCost state0_5 = 7168 := by decide +kernel

theorem main_actual_reference_work :
    Phase17Resource.totalCost completion0_0.execution.spent +
      Phase17Resource.totalCost completion0_1.execution.spent = 1008 := by decide +kernel

theorem main_unused_envelope_retained :
    Phase17Resource.totalCost completion0_0.execution.spent +
      Phase17Resource.totalCost completion0_1.execution.spent < reservedCost state0_5 := by decide +kernel

theorem main_checkpoints_updated : state0_5.completed = [completion0_0, completion0_1] ∧
    completion0_0.execution.controller = Phase17ProducerDomainExamples.state0_1.controller ∧
    completion0_1.execution.controller = Phase17ProducerDomainExamples.state1_8.controller := by decide +kernel

theorem main_reopen_preserves_budget : reservedCost state0_reopened = 3584 ∧
    state0_reopened.consumed = ["af_before"] ∧ state0_reopened.pending = none := by decide +kernel

theorem main_sources_consumed_once : state0_5.consumed.Nodup :=
  reachable_no_duplicate_sources policy0 contexts0 evaluators0 state0_5 reachable0_5

theorem first_completed_acceptance :
    Phase17TruthfulSuccessor.Accepted Phase17ProducerDomainExamples.fixed Phase17ProducerDomainExamples.contexts0 (Phase17ProducerDomainExamples.chargesAt [] 30)
      Phase17ProducerDomainExamples.source0 (Phase17ProducerDomainExamples.builder0 [] 30 41) := Phase17ProducerDomainExamples.first_source_reference_accepted

theorem second_completed_acceptance :
    Phase17TruthfulSuccessor.Accepted Phase17ProducerDomainExamples.fixed Phase17ProducerDomainExamples.contexts1
      (Phase17ProducerDomainExamples.chargesAt [19, 5, 18, 27, 13, 30, 15] 0) Phase17ProducerDomainExamples.source1
      (Phase17ProducerDomainExamples.builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) := Phase17ProducerDomainExamples.second_source_reference_accepted

theorem fixed_policy_meanings : permit0_0.binding.catalog = policy0.catalog ∧
    permit0_1.binding.catalog = policy0.catalog ∧ permit0_0.objective = policy0.objective ∧
    permit0_1.objective = policy0.objective ∧ permit0_0.evaluatorCode = policy0.evaluatorCode ∧
    permit0_1.evaluatorCode = policy0.evaluatorCode := by decide +kernel

theorem aggregate_denial_no_new_lease : state1_3.nextSerial = 1 ∧
    reservedCost state1_3 = 3584 ∧ state1_3.pending = none ∧ state1_3.halted = true := by decide +kernel

theorem reference_stop_is_not_exhaustion :
    Phase17Controller.decision Phase17ProducerDomainExamples.context4 completion2_0.execution.controller = some (.evaluate 27) ∧
    reservedCost state2_3 = 336 := ⟨Phase17ProducerDomainExamples.terminal4, by decide +kernel⟩

theorem credit_stop_is_not_exhaustion :
    Phase17Controller.decision Phase17ProducerDomainExamples.context2 completion3_0.execution.controller = some .resourceExhausted ∧
    completion3_0.execution.controller.observations.length = 4 := ⟨Phase17ProducerDomainExamples.terminal2, by decide +kernel⟩

theorem pending_reopen_cannot_complete :
    (reopen state4_1).pending = some lease4_0 ∧ reservedCost (reopen state4_1) = 3584 ∧
    (reopen state4_1).liveLease = none := by decide +kernel

theorem pending_stop_is_refused : stop state4_1 = none := by decide +kernel

end Phase17ControllerAuthorityExamples
'''
    return text.encode('utf-8')


def render_positive(prepared):
    require(type(prepared) is runtime.PreparedControllerAuthority, 'exact prepared controller authority required')
    return ('import ControllerAuthority\n' + '\n'.join('#print axioms ' + n for n in NAMES) + '\n').encode()


def render_negative(prepared, label):
    require(type(prepared) is runtime.PreparedControllerAuthority and label in NEGATIVES,
            'exact controller-authority negative required')
    direct = {
        'SelfIssuedLease': 'issue policy0 { policy0 with poolAttempts := 96 } "head" "head" state0_0 permit0_0 ≠ none',
        'StaleAuthorityHead': 'issue policy0 policy0 "old" "current" state0_0 permit0_0 ≠ none',
        'WrongSourcePermit': 'issue policy0 policy0 "head" "head" state0_0 { permit0_0 with binding := permit0_1.binding } ≠ none',
        'WrongCheckpointPermit': 'issue policy0 policy0 "head" "head" state0_0 { permit0_0 with checkpoint := "replacement" } ≠ none',
        'WrongObjectiveAuthority': 'issue policy0 policy0 "head" "head" state0_0 { permit0_0 with objective := "candidate-objective" } ≠ none',
        'WrongEvaluatorAuthority': 'issue policy0 policy0 "head" "head" state0_0 { permit0_0 with evaluatorCode := "candidate-evaluator" } ≠ none',
        'OverBudgetIssuance': 'issue policy1 policy1 "head" "head" state1_2 permit1_1 ≠ none',
        'OutstandingLeaseIssue': 'issue policy0 policy0 "head" "head" state0_1 permit0_1 ≠ none',
        'ConsumedSourceReissue': 'issue policy0 policy0 "head" "head" state0_2 permit0_0 ≠ none',
        'UnissuedCompletion': 'complete policy0 contexts0 evaluators0 "head" "head" state0_0 completion0_0 ≠ none',
        'WrongLeaseCompletion': 'complete policy0 contexts0 evaluators0 "head" "head" state0_1 { completion0_0 with lease := { lease0_0 with serial := 1 } } ≠ none',
        'UnderReservedGrant': '(issuedGrant policy0 permit0_0).costLimit = 112',
        'RefundedReservation': 'reservedCost state0_5 = 1008',
        'ReplayedCompletion': 'complete policy0 contexts0 evaluators0 "head" "head" state0_2 completion0_0 ≠ none',
        'TerminalCheckpointIssue': 'issue zeroPolicy zeroPolicy "head" "head" state0_0 zeroPermit ≠ none',
        'ReopenedPendingCompletion': 'complete policy0 contexts0 evaluators0 "head" "head" (reopen state0_1) completion0_0 ≠ none',
        'CrossSourceCompletion': 'complete policy0 contexts0 evaluators0 "head" "head" state0_1 { completion0_0 with lease := { lease0_0 with source := permit0_1 } } ≠ none',
    }
    prefix = '''import ControllerAuthority
namespace Phase17ControllerAuthorityControl
open Phase17ProducerDomain Phase17ControllerAuthority Phase17ControllerAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    if label == 'TerminalCheckpointIssue':
        prefix += '''def zeroPermit : Permit := { permit0_0 with initial := Phase17Controller.initial 0 }
def zeroPolicy : AuthorityPolicy := { policy0 with candidateCredits := 0, sources := [zeroPermit] }
'''
    if label == 'ForgedControllerCompletion':
        assertion = 'decide (complete policy0 contexts0 evaluators0 "head" "head" state0_1 { completion0_0 with execution := Phase17ProducerDomainExamples.state0_0 } ≠ none)'
        proof = '''by
  unfold wrongClaim
  have invalid : ¬ CompletionValid policy0 contexts0 evaluators0 state0_1
      { completion0_0 with execution := Phase17ProducerDomainExamples.state0_0 } := by
    intro valid
    have run := valid.2.2.2.2.2.2.2.1
    change authorizedReplay Phase17ProducerDomainExamples.grant0 Phase17ProducerDomainExamples.grant0 Phase17ProducerDomainExamples.grant0.binding Phase17ProducerDomainExamples.context0 Phase17ProducerDomainExamples.evaluator0 2
      Phase17ProducerDomainExamples.state0_0 Phase17ProducerDomainExamples.observations0 = some Phase17ProducerDomainExamples.state0_0 at run
    rw [Phase17ProducerDomainExamples.case_first_source] at run
    have different : Phase17ProducerDomainExamples.state0_1 ≠ Phase17ProducerDomainExamples.state0_0 := by decide +kernel
    exact different (Option.some.inj run)
  simp only [complete, invalid, and_false, if_false, ne_eq, not_true_eq_false, decide_false]
'''
    else:
        assertion = 'decide (' + direct[label] + ')'
        proof = ('by simp [wrongClaim, reopened_pending_no_completion]'
                 if label == 'ReopenedPendingCompletion' else 'by decide +kernel')
    text = prefix + 'def wrongClaim : Bool := ' + assertion + '\n'
    text += 'theorem actual_rejection : wrongClaim = false := ' + proof + '\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17ControllerAuthorityControl\n').encode()


def sources(prepared, root):
    require(type(prepared) is runtime.PreparedControllerAuthority, 'exact prepared controller authority required')
    prior = inherited.sources(prepared.producer_domain(), root)
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
        require(match is not None, 'missing or reordered controller authority audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved controller authority axiom')
        audits[name] = axioms; cursor = match.end()
    require(cursor == len(stdout), 'unexpected controller authority audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected controller authority negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
