"""Phase17AJ certificates for a current, separately provisioned witness.

Every selected witness transition is bound to its retained request cursor and
the corresponding unchanged AI issue, completion, denial or stop theorem.
Cryptographic authentication and one authoritative current witness history are
explicit premises; these certificates do not establish physical anti-rollback.
"""
from __future__ import annotations

import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from . import controller_authority_lean as inherited
from . import controller_witness as runtime
from .materialized import require, sha
from .successor_lean import string

MODULES = (*inherited.MODULES, 'AuthorityWitness')
POSITIVE = 'AuthorityWitnessExamples'
NEGATIVES = ('WrongProvision', 'StaleRevision', 'StaleWitnessHead',
    'StaleAuthorityHead', 'ConsumedNonce', 'UnchangedWitnessHead',
    'UnissuedLeaseExecution', 'WrongExecutionOwner', 'ReopenedPendingOwner',
    'ForkedControllerCursor', 'ReplayedReserve', 'ReplayedCompletion',
    'WrongSourceRegistry', 'WrongObjectivePolicy', 'WrongEvaluatorPolicy',
    'RefundedWitnessBudget', 'WrongReadNonce', 'WrongReadHead',
    'UnauthenticatedRead', 'WitnessRollbackImpossibility')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = inherited.ALLOWED_AXIOMS
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = dict(inherited.PINS)
_read = inherited._read
_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module
negative_location = inherited.negative_location

GENERIC_NAMES = tuple('Phase17AuthorityWitness.' + name for name in (
    'accepted_read_exact', 'unauthenticated_read_refused', 'wrong_nonce_read_refused',
    'wrong_head_read_refused', 'read_does_not_supply_owner', 'advanced_spec',
    'advanced_construct', 'authorized_advance_exact', 'unauthenticated_mutation_refused',
    'authorized_advance_recomputes', 'advanced_revision', 'advanced_fixed_provision',
    'advanced_heads', 'advanced_nonce_consumed', 'wrong_provision_refused',
    'stale_revision_refused', 'stale_head_refused', 'reused_nonce_refused',
    'stale_authority_head_refused', 'unchanged_head_refused', 'predecessor_consumed_once',
    'successful_request_cannot_replay', 'reserve_recomputes_issued_lease',
    'reserve_construct', 'execute_requires_owner', 'execute_construct',
    'missing_owner_execution_refused', 'wrong_owner_execution_refused',
    'reserve_semantics_fixed', 'reserve_exact_charge',
    'execution_recomputes_truthful_controller', 'execution_never_refunds', 'reopen_exact',
    'reopened_owner_cannot_execute', 'reopened_pending_retained',
    'perform_preserves_authority_reachability', 'reachable_authority',
    'reachable_nonces_unique', 'reachable_revision_exact', 'reachable_sources_consumed_once',
    'reachable_exact_debit', 'reachable_within_pool',
    'reachable_completed_and_pending_accounted', 'reachable_completed_work_within_pool'))
CASE_NAMES = tuple(row['name'] for row in runtime.case_specs())
SELECTED_NAMES = tuple('Phase17AuthorityWitnessExamples.' + name for name in (
    *('case_' + name for name in CASE_NAMES), 'main_exact_reservation',
    'main_actual_reference_work', 'main_accounted_reservation', 'main_fixed_policy_meanings',
    'main_reopen_retains_completed_state', 'main_consumed_sources_once',
    'main_requests_consumed_once', 'main_revision_exact',
    'first_lease_recomputes_authority', 'second_lease_recomputes_authority',
    'first_completion_recomputes_controller', 'second_completion_recomputes_controller',
    'cloned_controller_cursor_refused', 'old_read_nonce_refused',
    'old_read_after_advance_is_not_current', 'pending_reopen_preserves_charges',
    'pending_reopen_cannot_execute', 'pending_reopen_cannot_issue',
    'pending_reopen_cannot_stop', 'aggregate_denial_preserves_charges',
    'witness_rollback_is_outside_guarantee'))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)
AI = 'Phase17ControllerAuthority.'
EX = 'Phase17ControllerAuthorityExamples.'


def _nat(value):
    require(type(value) is int and value >= 0, 'natural witness literal required')
    return str(value)


def _same(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def render_selected(prepared, root):
    require(type(prepared) is runtime.PreparedControllerWitness, 'exact prepared controller witness required')
    packet = prepared.packet; cases = packet['witness_cases']; authority = prepared.controller_authority()
    require(tuple(row['name'] for row in cases) == CASE_NAMES, 'selected witness case inventory differs')
    _, generic = _split_imports(_read(root, 'AuthorityWitness'))
    text = 'import ControllerAuthority\n' + generic
    text += '''
namespace Phase17AuthorityWitnessExamples
open Phase17AuthorityWitness
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    text += '-- Exact AJ witness packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    for ci, case in enumerate(cases):
        ai_index = case['ai_case_index']; ai_case = authority.packet['cases'][ai_index]
        require(ai_case['name'] == case['name'] and digest(case['provision']) == case['provision_sha256'],
                'witness provision or inherited case differs')
        provision = case['provision']; policy = EX + 'policy' + str(ai_index)
        contexts = EX + 'contexts' + str(ai_index); evaluators = EX + 'evaluators' + str(ai_index)
        _same(provision['authority_policy'], ai_case['authority_policy'], 'witness policy is not the exact AI policy')
        require(provision['authority_policy_sha256'] == ai_case['policy_sha256'] and
                provision['ai_packet_sha256'] == sha(authority.packet_bytes) and
                provision['witness_identity'] == packet['witness_identity'],
                'witness provision does not bind the exact authority or code')
        initial_journal = ai_case['events'][0]['hash']
        text += f'def provision{ci} : Provision := {{\n'
        for key, value in (('identity', case['provision_sha256']), ('witness', provision['witness_id']),
                ('credential', provision['key_commitment']),
                ('implementation', provision['witness_identity']['implementation_sha256']),
                ('genesis', case['initial_witness_head'])):
            text += '  ' + key + ' := ' + string(value) + '\n'
        text += '  policy := ' + policy + ' }\n'
        text += (f'theorem provision_valid{ci} : ProvisionValid provision{ci} :=\n'
                 f'  ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,\n'
                 f'    by decide +kernel, {EX}policy_valid{ai_index}⟩\n')
        text += f'def journal{ci} : String := {string(initial_journal)}\n'
        text += f'def witness{ci}_0 : WitnessState := initial provision{ci} journal{ci}\n'
        text += (f'theorem reachable{ci}_0 : Reachable provision{ci} {contexts} {evaluators}\n'
                 f'    journal{ci} witness{ci}_0 := .initial\n')
        ai_step = 0; session = 0; current_ai = EX + f'state{ai_index}_0'
        current = f'witness{ci}_0'; current_head = case['initial_witness_head']; current_journal = initial_journal
        for index, record in enumerate(case['records'], start=1):
            kind = record['kind']; request = f'request{ci}_{index}'; following = f'witness{ci}_{index}'
            require(record['revision_before'] == index - 1 and record['revision_after'] == index and
                    record['witness_head_before'] == current_head and
                    record['authority_head_before'] == current_journal and
                    record['ai_state_before']['head'] == current_journal and
                    record['ai_state_after']['head'] == record['authority_head_after'],
                    'witness transition cursor or authority projection differs')
            owner = string(record['owner_commitment']) if record['owner_commitment'] is not None else None
            if kind == 'reopen':
                require(record['authority_head_after'] == current_journal and record['owner_commitment'] is None,
                        'reopen changed the authority journal or supplied execution ownership')
                _same(record['ai_state_after'], record['ai_state_before'], 'reopen changed persistent authority state')
                command = '.reopen'; next_ai = '(' + AI + 'reopen ' + current_ai + ')'
                transition = 'by rfl'
            else:
                ai_step += 1; ai_event = ai_case['events'][ai_step]; body = ai_event['body']
                expected_kind = 'complete' if kind == 'execute' else kind
                require(body['kind'] == expected_kind and ai_event['previous'] == current_journal and
                        ai_event['hash'] == record['authority_head_after'],
                        'witness did not perform the exact retained AI transition')
                next_ai = EX + f'state{ai_index}_{ai_step}'
                if kind == 'reserve':
                    require(record['owner_commitment'] is not None and
                            record['source_id'] == body['lease']['source_permit']['source_id'],
                            'reserved witness owner or source differs')
                    source = EX + f'permit{ai_index}_{runtime.ai.ah.SOURCES.index(record["source_id"])}'
                    command = '.reserve ' + owner + ' ' + source
                    transition = ('by\n  apply reserve_construct\n  · decide +kernel\n  · rfl\n'
                                  f'  · exact {EX}issue{ai_index}_{session}')
                elif kind == 'execute':
                    require(record['session_index'] == session and record['owner_commitment'] is not None,
                            'completed witness session index or owner differs')
                    _same(case['sessions'][session], ai_case['sessions'][session],
                          'witness completion differs from the exact checked AI session')
                    completion = EX + f'completion{ai_index}_{session}'
                    command = '.execute ' + owner + ' ' + completion
                    transition = ('by\n  apply execute_construct\n  · decide +kernel\n  · rfl\n'
                                  f'  · exact {EX}complete{ai_index}_{session}')
                    session += 1
                elif kind == 'deny':
                    source = EX + f'permit{ai_index}_{runtime.ai.ah.SOURCES.index(record["source_id"])}'
                    command = '.deny ' + source
                    transition = (f'by\n  change {AI}deny {policy} {policy} {string(current_journal)}\n'
                        f'    {string(current_journal)} {current_ai} {source} = some {next_ai}\n'
                        f'  exact {EX}deny{ai_index}')
                elif kind == 'stop':
                    command = '.stop'; transition = f'by exact {EX}stop{ai_index}'
                else:
                    raise ValueError('unsupported witnessed transition')
            text += (f'-- Retained AI state projection SHA256: {digest(record["ai_state_after"])}\n'
                f'def {request} : Request := {{\n  provision := provision{ci}.identity\n'
                f'  revision := {_nat(record["revision_before"])}\n'
                f'  head := {string(record["witness_head_before"])}\n'
                f'  journal := {string(record["authority_head_before"])}\n'
                f'  nonce := {string(record["nonce"])}\n  command := {command} }}\n')
            next_head = string(record['witness_head_after']); next_journal = string(record['authority_head_after'])
            text += f'def {following} : WitnessState := updated {current} {request} {next_head} {next_journal} {next_ai}\n'
            text += (f'theorem guard{ci}_{index} : AdvanceGuard provision{ci} {current} {request}\n'
                f'    {next_head} {next_journal} :=\n'
                f'  ⟨rfl, rfl, provision_valid{ci}, rfl, rfl, by decide +kernel, by decide +kernel,\n'
                '    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩\n')
            text += (f'theorem performed{ci}_{index} : perform provision{ci} {contexts} {evaluators}\n'
                     f'    {current} {request}.command = some {next_ai} := {transition}\n')
            text += (f'theorem step{ci}_{index} : advance provision{ci} {contexts} {evaluators}\n'
                f'    {current} {request} {next_head} {next_journal} = some {following} :=\n'
                f'  advanced_construct provision{ci} {contexts} {evaluators} {current} {request}\n'
                f'    {next_head} {next_journal} {next_ai} guard{ci}_{index} performed{ci}_{index}\n')
            text += (f'theorem reachable{ci}_{index} : Reachable provision{ci} {contexts} {evaluators}\n'
                f'    journal{ci} {following} :=\n'
                f'  .advance reachable{ci}_{index - 1} {request} {next_head} {next_journal} step{ci}_{index}\n')
            current = following; current_ai = next_ai
            current_head = record['witness_head_after']; current_journal = record['authority_head_after']
        require(ai_step == len(ai_case['events']) - 1 and session == len(case['sessions']),
                'witness trace did not cover its exact inherited AI event/session prefix')
        _same(case['final_state']['authority_state'], ai_case['final_state'], 'witness final authority projection differs')
        require(case['final_state']['revision'] == len(case['records']) and
                case['final_state']['witness_head'] == current_head and
                case['final_state']['authority_head'] == current_journal,
                'witness final cursor differs from selected transitions')
        text += (f'theorem case_{case["name"]} : Reachable provision{ci} {contexts} {evaluators}\n'
            f'    journal{ci} {current} ∧ {current}.revision = {_nat(len(case["records"]))} ∧\n'
            f'    {current}.authority = {current_ai} := ⟨reachable{ci}_{len(case["records"])}, rfl, rfl⟩\n')
    require([len(case['records']) for case in cases] == [7, 3, 4], 'selected witness transition count differs')
    text += _selected_tail()
    return text.encode('utf-8')


def _selected_tail():
    return '''
theorem main_exact_reservation : Phase17ControllerAuthority.reservedVector witness0_7.authority = [64, 128, 512, 512] ∧
    Phase17ControllerAuthority.reservedCost witness0_7.authority = 7168 :=
  Phase17ControllerAuthorityExamples.main_exact_reservation

theorem main_actual_reference_work : Phase17ControllerAuthority.completedCost witness0_7.authority = 1008 := by decide +kernel

theorem main_accounted_reservation :
    Phase17ControllerAuthority.completedCost witness0_7.authority +
      Phase17ControllerAuthority.pendingCost provision0.policy witness0_7.authority ≤
      Phase17ControllerAuthority.reservedCost witness0_7.authority :=
  reachable_completed_and_pending_accounted provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem main_fixed_policy_meanings : provision0.policy = Phase17ControllerAuthorityExamples.policy0 ∧
    Phase17ControllerAuthorityExamples.permit0_0.objective = provision0.policy.objective ∧
    Phase17ControllerAuthorityExamples.permit0_1.objective = provision0.policy.objective ∧
    Phase17ControllerAuthorityExamples.permit0_0.evaluatorCode = provision0.policy.evaluatorCode ∧
    Phase17ControllerAuthorityExamples.permit0_1.evaluatorCode = provision0.policy.evaluatorCode := by decide +kernel

theorem main_reopen_retains_completed_state : witness0_4.authority =
    Phase17ControllerAuthority.reopen witness0_3.authority ∧ witness0_4.owner = none ∧
    witness0_4.journal = witness0_3.journal ∧
    Phase17ControllerAuthority.reservedCost witness0_4.authority = 3584 :=
  ⟨rfl, rfl, rfl, by decide +kernel⟩

theorem main_consumed_sources_once : witness0_7.authority.consumed.Nodup :=
  reachable_sources_consumed_once provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem main_requests_consumed_once : witness0_7.nonces.Nodup :=
  reachable_nonces_unique provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem main_revision_exact : witness0_7.revision = witness0_7.nonces.length :=
  reachable_revision_exact provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem first_lease_recomputes_authority :
    perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_1 request0_2.command = some Phase17ControllerAuthorityExamples.state0_1 := performed0_2

theorem second_lease_recomputes_authority :
    perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_4 request0_5.command = some Phase17ControllerAuthorityExamples.state0_3 := performed0_5

theorem first_completion_recomputes_controller :
    Phase17ControllerAuthority.CompletionValid provision0.policy Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 witness0_2.authority Phase17ControllerAuthorityExamples.completion0_0 := by
  apply execution_recomputes_truthful_controller
  exact performed0_3

theorem second_completion_recomputes_controller :
    Phase17ControllerAuthority.CompletionValid provision0.policy Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 witness0_5.authority Phase17ControllerAuthorityExamples.completion0_1 := by
  apply execution_recomputes_truthful_controller
  exact performed0_6

def clonedRequest : Request := { request0_2 with
  nonce := "fresh-competing-nonce"
  command := .reserve "different-controller-owner" Phase17ControllerAuthorityExamples.permit0_1 }

theorem cloned_controller_cursor_refused :
    advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_2 clonedRequest "competing-head" "competing-journal" = none := by
  apply stale_revision_refused
  decide +kernel

theorem old_read_nonce_refused (authentic : ReadResponse → Prop) :
    ¬ ReadAccepted authentic provision0 "fresh-read" witness0_1 (readResponse witness0_1 "old-read") := by
  apply wrong_nonce_read_refused
  decide +kernel

theorem old_read_after_advance_is_not_current (authentic : ReadResponse → Prop) :
    ¬ ReadAccepted authentic provision0 "same-read" witness0_2 (readResponse witness0_1 "same-read") := by
  apply wrong_head_read_refused
  decide +kernel

theorem pending_reopen_preserves_charges :
    witness1_3.authority.pending = some Phase17ControllerAuthorityExamples.lease4_0 ∧
    Phase17ControllerAuthority.reservedCost witness1_3.authority = 3584 ∧
    witness1_3.authority.liveLease = none ∧ witness1_3.owner = none ∧
    witness1_3.journal = witness1_2.journal := by decide +kernel

theorem pending_reopen_cannot_execute (owner : String) (result : Phase17ControllerAuthority.Completion) :
    perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
      witness1_3 (.execute owner result) = none :=
  missing_owner_execution_refused provision1 Phase17ControllerAuthorityExamples.contexts4
    Phase17ControllerAuthorityExamples.evaluators4 witness1_3 owner result rfl

theorem pending_reopen_cannot_issue :
    perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
      witness1_3 (.reserve "new-owner" Phase17ControllerAuthorityExamples.permit4_1) = none := by decide +kernel

theorem pending_reopen_cannot_stop :
    perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
      witness1_3 .stop = none := by decide +kernel

theorem aggregate_denial_preserves_charges :
    witness2_4.authority.nextSerial = 1 ∧ Phase17ControllerAuthority.reservedCost witness2_4.authority = 3584 ∧
    witness2_4.authority.pending = none ∧ witness2_4.authority.halted = true :=
  Phase17ControllerAuthorityExamples.aggregate_denial_no_new_lease

/-- Restoring the witness itself to a former trusted state re-enables that
    state's valid request. The controller-snapshot result cannot rule this out. -/
theorem witness_rollback_is_outside_guarantee :
    advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_1 request0_2 witness0_2.head witness0_2.journal ≠ none := by
  have accepted : advance provision0 Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 witness0_1 request0_2
      witness0_2.head witness0_2.journal = some witness0_2 := step0_2
  rw [accepted]
  exact Option.some_ne_none _

end Phase17AuthorityWitnessExamples
'''


def render_positive(prepared):
    require(type(prepared) is runtime.PreparedControllerWitness, 'exact prepared witness audit required')
    return ('import AuthorityWitness\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(prepared, label):
    require(type(prepared) is runtime.PreparedControllerWitness and label in NEGATIVES,
            'exact controller-witness negative required')
    advance = 'advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 '
    perform = 'perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 '
    request = 'request0_2'; nexts = ' witness0_2.head witness0_2.journal'
    direct = {
        'WrongProvision': advance + 'witness0_1 { request0_2 with provision := "untrusted" }' + nexts + ' ≠ none',
        'StaleRevision': advance + 'witness0_1 { request0_2 with revision := 0 }' + nexts + ' ≠ none',
        'StaleWitnessHead': advance + 'witness0_1 { request0_2 with head := "stale" }' + nexts + ' ≠ none',
        'StaleAuthorityHead': advance + 'witness0_1 { request0_2 with journal := "stale" }' + nexts + ' ≠ none',
        'ConsumedNonce': advance + 'witness0_1 { request0_2 with nonce := request0_1.nonce }' + nexts + ' ≠ none',
        'UnchangedWitnessHead': advance + 'witness0_1 request0_2 witness0_1.head witness0_2.journal ≠ none',
        'UnissuedLeaseExecution': perform + 'witness0_1 (.execute "owner" Phase17ControllerAuthorityExamples.completion0_0) ≠ none',
        'WrongExecutionOwner': perform + 'witness0_2 (.execute "wrong-owner" Phase17ControllerAuthorityExamples.completion0_0) ≠ none',
        'ReopenedPendingOwner': 'perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 witness1_3 (.execute "owner" Phase17ControllerAuthorityExamples.completion0_0) ≠ none',
        'ForkedControllerCursor': advance + 'witness0_2 clonedRequest "competing-head" "competing-journal" ≠ none',
        'ReplayedReserve': advance + 'witness0_2 request0_2 "replayed-head" "replayed-journal" ≠ none',
        'ReplayedCompletion': advance + 'witness0_3 request0_3 "replayed-head" "replayed-journal" ≠ none',
        'WrongSourceRegistry': perform + 'witness0_1 (.reserve "owner" { Phase17ControllerAuthorityExamples.permit0_0 with checkpoint := "foreign-checkpoint" }) ≠ none',
        'WrongObjectivePolicy': perform + 'witness0_1 (.reserve "owner" { Phase17ControllerAuthorityExamples.permit0_0 with objective := "self-objective" }) ≠ none',
        'WrongEvaluatorPolicy': perform + 'witness0_1 (.reserve "owner" { Phase17ControllerAuthorityExamples.permit0_0 with evaluatorCode := "self-evaluator" }) ≠ none',
        'RefundedWitnessBudget': 'Phase17ControllerAuthority.reservedCost witness0_7.authority = 1008',
        'WrongReadNonce': 'ReadAccepted (fun _ => True) provision0 "fresh-read" witness0_1 (readResponse witness0_1 "old-read")',
        'WrongReadHead': 'ReadAccepted (fun _ => True) provision0 "same-read" witness0_2 (readResponse witness0_1 "same-read")',
        'UnauthenticatedRead': 'ReadAccepted (fun _ => False) provision0 "fresh-read" witness0_1 (readResponse witness0_1 "fresh-read")',
        'WitnessRollbackImpossibility': advance + 'witness0_1 ' + request + nexts + ' = none',
    }
    prefix = '''import AuthorityWitness
namespace Phase17AuthorityWitnessControl
open Phase17AuthorityWitness Phase17AuthorityWitnessExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    proof = ('by\n  simp only [wrongClaim, witness_rollback_is_outside_guarantee, decide_false]'
             if label == 'WitnessRollbackImpossibility' else 'by decide +kernel')
    text = prefix + 'def wrongClaim : Bool := decide (' + direct[label] + ')\n'
    text += 'theorem actual_rejection : wrongClaim = false := ' + proof + '\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17AuthorityWitnessControl\n').encode()


def sources(prepared, root):
    require(type(prepared) is runtime.PreparedControllerWitness, 'exact prepared controller witness required')
    prior = inherited.sources(prepared.controller_authority(), root)
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
        require(match is not None, 'missing or reordered controller witness audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved controller witness audit dependency')
        audits[name] = axioms; cursor = match.end()
    require(cursor == len(stdout), 'unexpected controller witness audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected controller witness negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
