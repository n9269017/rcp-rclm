"""AN broker certificates from the independently validated original packet.

The projection is derived by the native validator from real commission, broker
intent, AM request, pending-anchor and accounting records. It is not accepted as
a controller-supplied formal state. OS isolation and legitimate commissioning
remain native/external premises, and missing accounting never becomes zero cost.
"""
from __future__ import annotations

from pathlib import Path
import re

from rcp_rclm_runtime.canonical.json import load_json_strict
from .resource_ledger import canonical, digest, exact, nat, require, sha
from .successor_lean import string
from .controller_continuation_lean import negative_location

MODULES = ('ProtectedAuthority',)
POSITIVE = 'ProtectedAuthorityExamples'
NEGATIVES = (
    'WrongBrokerCommission', 'WrongBrokerRoot', 'SubstitutedBrokerImplementation',
    'SubstitutedControllerImplementation', 'SubstitutedBrokerObjective',
    'SubstitutedBrokerEvaluator', 'SubstitutedAccountingPolicy',
    'AdministrativeBrokerOperation', 'PendingBrokerMutationRetried',
    'ReplayedBrokerNonce', 'UncertainBrokerOutcomeCleared',
    'ReconciliationLaunchesWorker', 'IncompleteAccountingAdmitted',
    'TransportSuccessPromotes', 'ClonedBrokerImpossible', 'WrongBrokerCursorIssued',
    'ZeroBrokerCredits', 'ExceededBrokerCreditLimit', 'ExhaustedBrokerIntentCapacity',
    'ReplayedReadIntent', 'ReplayedReconcileIntent',
)
LABELS = (*MODULES, POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
GENERIC_NAMES = tuple('Phase17ProtectedAuthority.' + name for name in (
    'dispatch_spec', 'dispatch_construct', 'dispatch_fixed_binding',
    'dispatch_pinned_authority', 'wrong_commission_refused', 'wrong_root_refused',
    'wrong_runtime_refused', 'administrative_operation_refused', 'run_requires_idle',
    'pending_run_refused', 'replayed_run_refused', 'dispatch_credit_limit',
    'dispatch_intent_capacity', 'over_credit_refused', 'zero_credit_refused',
    'intent_capacity_refused', 'replayed_intent_refused', 'begin_retains_exact_pending',
    'begin_blocks_repeat', 'uncertain_outcome_retained', 'terminal_outcome_cleared',
    'reconcile_issues_read', 'reconcile_never_launches', 'ready_exact_inventory',
    'ready_entries_complete', 'unknown_observation_incomplete',
    'unknown_upper_bound_incomplete', 'incomplete_entry_blocks_coverage',
    'accepted_requires_coverage', 'accepted_requires_budget', 'accepted_requires_root',
    'incomplete_coverage_blocks_promotion', 'transport_alone_cannot_promote',
    'identical_brokers_dispatch_identically',
))
SELECTED_NAMES = tuple('Phase17ProtectedAuthorityExamples.' + name for name in (
    'selected_dispatch', 'selected_authority_pin', 'selected_write_ahead',
    'selected_pending_blocks_repeat', 'selected_reconcile_read',
    'selected_reconcile_no_launch', 'selected_unknown_coverage',
    'selected_no_promotion_admission', 'selected_root_authorization_required',
    'cloned_broker_outside_guarantee',
))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)
COMMISSION_FIELDS = ('identity', 'authority_commission', 'root', 'broker_source',
                     'controller_source', 'objective', 'evaluator', 'accounting_policy')
LIMIT_FIELDS = ('max_credits', 'max_intents')
RUNTIME_FIELDS = COMMISSION_FIELDS[3:]
PROJECTION_FIELDS = {'commission', 'runtime', 'first_state', 'run_intent', 'first_issued',
                     'pending_state', 'reconcile_intent', 'required_categories', 'coverage', 'budget'}


def _copy(value):
    return load_json_strict(canonical(value), require_canonical=True)


def _cursor(value):
    exact(value, {'epoch', 'serial', 'head'})
    nat(value['epoch']); nat(value['serial']); digest(value['head'])
    return _copy(value)


def _mutation(value):
    exact(value, {'current', 'nonce', 'credits'})
    _cursor(value['current']); digest(value['nonce'])
    require(nat(value['credits']) <= 32, 'bounded mutation credits required')
    return _copy(value)


def _state(value):
    exact(value, {'commission', 'root', 'current', 'pending', 'consumed'})
    digest(value['commission']); digest(value['root']); _cursor(value['current'])
    if value['pending'] is not None:
        _mutation(value['pending'])
    require(type(value['consumed']) is list and len(value['consumed']) <= 4096,
            'bounded original broker nonce history required')
    for nonce in value['consumed']:
        digest(nonce)
    require(len(set(value['consumed'])) == len(value['consumed']), 'broker nonce history contains replay')
    return _copy(value)


def _intent(value):
    exact(value, {'operation', 'nonce', 'credits'})
    require(value['operation'] in ('read', 'run', 'reconcile'), 'controller operation required')
    digest(value['nonce']); require(nat(value['credits']) <= 32, 'bounded intent credits required')
    require(value['operation'] == 'run' or value['credits'] == 0, 'read intent credits must be zero')
    return _copy(value)


def validate_projection(value):
    """Validate a native-derived semantic projection; this is not capture evidence.

    ``PreparedProtectedAuthority`` independently recomputes this entire value
    from the packet's original records before ``project`` can emit it.
    """
    exact(value, PROJECTION_FIELDS)
    c, b = value['commission'], value['runtime']
    exact(c, set(COMMISSION_FIELDS) | set(LIMIT_FIELDS)); exact(b, set(RUNTIME_FIELDS))
    for field in COMMISSION_FIELDS:
        digest(c[field])
    require(0 < nat(c['max_credits']) <= 32 and 0 < nat(c['max_intents']) <= 128,
            'fixed commissioned admission limits differ')
    for field in RUNTIME_FIELDS:
        require(b[field] == c[field], 'runtime differs from commissioned fixed binding: ' + field)
    s, pending = _state(value['first_state']), _state(value['pending_state'])
    q, reconcile = _intent(value['run_intent']), _intent(value['reconcile_intent'])
    require(s['commission'] == c['identity'] and s['root'] == c['root'], 'broker commission/root join differs')
    require(s['pending'] is None and q['operation'] == 'run' and q['nonce'] not in s['consumed'],
            'selected run must be an originally admitted idle mutation')
    require(0 < q['credits'] <= c['max_credits'] and len(s['consumed']) < c['max_intents'],
            'selected run exceeds fixed credit or intent capacity')
    require(len(pending['consumed']) < c['max_intents'], 'selected reconciliation has no remaining intent capacity')
    expected = {'authority_commission': c['authority_commission'], 'root': c['root'],
                'current': s['current'], 'operation': 'run', 'nonce': q['nonce'], 'credits': q['credits']}
    exact(value['first_issued'], set(expected))
    require(value['first_issued'] == expected, 'original AM request does not match broker issuance')
    expected_pending = {**s, 'pending': {'current': s['current'], 'nonce': q['nonce'], 'credits': q['credits']},
                        'consumed': s['consumed'] + [q['nonce']]}
    require(pending == expected_pending, 'write-ahead broker record does not retain exact mutation and consumption')
    require(reconcile['operation'] == 'reconcile' and reconcile['nonce'] not in pending['consumed'],
            'selected read-only reconciliation intent differs')
    # The required inventory is sourced from the trusted accounting module. The
    # packet does not choose a shorter list to call its own accounting complete.
    from .authority_accounting import CATEGORIES
    required, entries = value['required_categories'], value['coverage']
    require(type(required) is list and required == list(CATEGORIES), 'fixed accounting category inventory differs')
    require(type(entries) is list and len(entries) == len(required), 'exact accounting coverage rows required')
    unknown = False
    for category, entry in zip(required, entries, strict=True):
        exact(entry, {'category', 'observed', 'upper_bound', 'meter'})
        require(entry['category'] == category, 'accounting categories omitted, duplicated or reordered')
        for key in ('observed', 'upper_bound'):
            if entry[key] is None:
                unknown = True
            else:
                nat(entry[key])
        if entry['meter'] == '':
            unknown = True
        else:
            digest(entry['meter'])
        if entry['observed'] is not None and entry['upper_bound'] is not None:
            require(entry['observed'] <= entry['upper_bound'], 'accounting observation exceeds declared bound')
    nat(value['budget'])
    require(unknown, 'reference packet cannot claim complete campaign accounting')
    return _copy(value)


def _prepared(value, root):
    from .protected_authority_capture import PreparedProtectedAuthority
    require(type(value) is PreparedProtectedAuthority, 'checked PreparedProtectedAuthority required')
    # Reconstruct from immutable packet bytes at the exact source. Holding a
    # mutable object's earlier validation result is not a trust boundary.
    return PreparedProtectedAuthority(value.packet_bytes, Path(root))


def project(prepared, root):
    checked = _prepared(prepared, root)
    projection = validate_projection(checked.packet['formal_projection'])
    return {'packet_sha256': sha(checked.packet_bytes), **projection}


def _nat(value):
    return str(nat(value))


def _cursor_literal(value):
    return '⟨' + ', '.join((_nat(value['epoch']), _nat(value['serial']), string(value['head']))) + '⟩'


def _mutation_literal(value):
    return '⟨' + ', '.join((_cursor_literal(value['current']), string(value['nonce']), _nat(value['credits']))) + '⟩'


def _state_literal(value):
    pending = 'none' if value['pending'] is None else 'some ' + _mutation_literal(value['pending'])
    consumed = '[' + ', '.join(string(nonce) for nonce in value['consumed']) + ']'
    return '⟨' + ', '.join((string(value['commission']), string(value['root']),
        _cursor_literal(value['current']), pending, consumed)) + '⟩'


def _intent_literal(value):
    return '⟨' + ', '.join((string(value['operation']), string(value['nonce']), _nat(value['credits']))) + '⟩'


def _issued_literal(value):
    return '⟨' + ', '.join((string(value['authority_commission']), string(value['root']),
        _cursor_literal(value['current']), string(value['operation']), string(value['nonce']), _nat(value['credits']))) + '⟩'


def _coverage_literal(entries):
    def optional(value):
        return 'none' if value is None else 'some ' + _nat(value)
    return '[' + ', '.join('⟨' + ', '.join((string(e['category']), optional(e['observed']),
        optional(e['upper_bound']), string(e['meter']))) + '⟩' for e in entries) + ']'


def render_selected(projection, root):
    exact(projection, PROJECTION_FIELDS | {'packet_sha256'})
    digest(projection['packet_sha256'])
    validate_projection({key: projection[key] for key in PROJECTION_FIELDS})
    generic = (Path(root) / 'lean/phase17_bridge/ProtectedAuthority.lean').read_bytes()
    require(generic.startswith(b'import Std\nimport Lean.Elab.Tactic.Omega\n') and
            generic.rstrip().endswith(b'end Phase17ProtectedAuthority'), 'generic protected-authority source differs')
    text = generic.decode() + '\n\nnamespace Phase17ProtectedAuthorityExamples\nopen Phase17ProtectedAuthority\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 16000000\n'
    text += 'def packetSha256 : String := ' + string(projection['packet_sha256']) + '\n'
    text += 'def commission : Commission := ⟨' + ', '.join(string(projection['commission'][name])
        for name in COMMISSION_FIELDS) + ', ' + ', '.join(_nat(projection['commission'][name])
        for name in LIMIT_FIELDS) + '⟩\n'
    text += 'def runtime : RuntimeBinding := ⟨' + ', '.join(string(projection['runtime'][name])
        for name in RUNTIME_FIELDS) + '⟩\n'
    for field, name in (('first_state', 'firstState'), ('pending_state', 'pendingState')):
        text += f'def {name} : State := ' + _state_literal(projection[field]) + '\n'
    for field, name in (('run_intent', 'runIntent'), ('reconcile_intent', 'reconcileIntent')):
        text += f'def {name} : Intent := ' + _intent_literal(projection[field]) + '\n'
    text += 'def firstIssued : Issued := ' + _issued_literal(projection['first_issued']) + '\n'
    text += 'def requiredCategories : List String := [' + ', '.join(string(v) for v in projection['required_categories']) + ']\n'
    text += 'def coverage : List Coverage := ' + _coverage_literal(projection['coverage']) + '\n'
    text += 'def budget : Nat := ' + _nat(projection['budget']) + '\n'
    text += '''theorem selected_dispatch :
    dispatch commission runtime firstState runIntent = some firstIssued := by decide +kernel
theorem selected_authority_pin :
    firstIssued.authorityCommission = commission.authorityCommission ∧
    firstIssued.root = commission.root ∧ firstIssued.current = firstState.current := by decide +kernel
theorem selected_write_ahead :
    beginMutation commission runtime firstState runIntent = some pendingState := by decide +kernel
theorem selected_pending_blocks_repeat :
    dispatch commission runtime pendingState runIntent = none := by decide +kernel
theorem selected_reconcile_read :
    (dispatch commission runtime pendingState reconcileIntent).map Issued.operation = some "read" := by decide +kernel
theorem selected_reconcile_no_launch :
    (dispatch commission runtime pendingState reconcileIntent).map launchCount = some 0 := by decide +kernel
theorem selected_unknown_coverage : coverageReady requiredCategories coverage = false := by decide +kernel
theorem selected_no_promotion_admission :
    promotionAdmission requiredCategories coverage budget true = false := by decide +kernel
theorem selected_root_authorization_required :
    promotionAdmission requiredCategories coverage budget false = false := by decide +kernel
theorem cloned_broker_outside_guarantee :
    ∃ first second : State, first = firstState ∧ second = firstState ∧
      dispatch commission runtime first runIntent = some (issued commission firstState runIntent) ∧
      dispatch commission runtime second runIntent = some (issued commission firstState runIntent) := by
  apply identical_brokers_dispatch_identically
  exact selected_dispatch
end Phase17ProtectedAuthorityExamples
'''
    return text.encode()


def render_positive():
    return ('import ProtectedAuthority\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(label):
    require(label in NEGATIVES, 'exact protected-authority negative required')
    call = 'dispatch commission runtime '
    wrong = {
        'WrongBrokerCommission': call + '{ firstState with commission := "untrusted" } runIntent ≠ none',
        'WrongBrokerRoot': call + '{ firstState with root := "untrusted" } runIntent ≠ none',
        'SubstitutedBrokerImplementation': 'dispatch commission { runtime with brokerSource := "untrusted" } firstState runIntent ≠ none',
        'SubstitutedControllerImplementation': 'dispatch commission { runtime with controllerSource := "untrusted" } firstState runIntent ≠ none',
        'SubstitutedBrokerObjective': 'dispatch commission { runtime with objective := "untrusted" } firstState runIntent ≠ none',
        'SubstitutedBrokerEvaluator': 'dispatch commission { runtime with evaluator := "untrusted" } firstState runIntent ≠ none',
        'SubstitutedAccountingPolicy': 'dispatch commission { runtime with accountingPolicy := "untrusted" } firstState runIntent ≠ none',
        'AdministrativeBrokerOperation': call + 'firstState { runIntent with operation := "reopen" } ≠ none',
        'PendingBrokerMutationRetried': call + 'pendingState runIntent ≠ none',
        'ReplayedBrokerNonce': call + '{ firstState with consumed := firstState.consumed ++ [runIntent.nonce] } runIntent ≠ none',
        'UncertainBrokerOutcomeCleared': 'reconcilePending pendingState false = none',
        'ReconciliationLaunchesWorker': '(dispatch commission runtime pendingState reconcileIntent).map launchCount = some 1',
        'IncompleteAccountingAdmitted': 'promotionAdmission requiredCategories coverage budget true = true',
        'TransportSuccessPromotes': 'promotionAdmission requiredCategories coverage budget false = true',
        'ClonedBrokerImpossible': call + 'firstState runIntent = none',
        'WrongBrokerCursorIssued': call + 'firstState runIntent = some { firstIssued with current := { firstIssued.current with head := "stale" } }',
        'ZeroBrokerCredits': call + 'firstState { runIntent with credits := 0 } ≠ none',
        'ExceededBrokerCreditLimit': call + 'firstState { runIntent with credits := commission.maxCredits + 1 } ≠ none',
        'ExhaustedBrokerIntentCapacity': call + '{ firstState with consumed := List.replicate commission.maxIntents "used" } runIntent ≠ none',
        'ReplayedReadIntent': call + '{ firstState with consumed := firstState.consumed ++ [reconcileIntent.nonce] } { reconcileIntent with operation := "read" } ≠ none',
        'ReplayedReconcileIntent': call + '{ pendingState with consumed := pendingState.consumed ++ [reconcileIntent.nonce] } reconcileIntent ≠ none',
    }
    text = '''import ProtectedAuthority
namespace Phase17ProtectedAuthorityControl
open Phase17ProtectedAuthority Phase17ProtectedAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    text += 'def wrongClaim : Bool := decide (' + wrong[label] + ')\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17ProtectedAuthorityControl\n').encode()


def sources(prepared, root):
    projection = project(prepared, root)
    result = {MODULES[0]: render_selected(projection, root), POSITIVE: render_positive()}
    result.update({name: render_negative(name) for name in NEGATIVES})
    for name, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + name)
    return result


def parse_audits(stdout):
    require(type(stdout) is str, 'exact audit output text required')
    cursor, audits = 0, {}
    for name in NAMES:
        match = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'missing or reordered protected-authority audit: ' + name)
        dependencies = [] if match[1] is None else [item.strip() for item in match[1].split(',') if item.strip()]
        require(len(dependencies) == len(set(dependencies)) and set(dependencies) <= ALLOWED_AXIOMS,
                'unapproved protected-authority audit dependency')
        audits[name] = dependencies; cursor = match.end()
    require(cursor == len(stdout), 'unexpected protected-authority audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected protected-authority negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
