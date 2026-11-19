"""AO certificates projected from independently reconstructed service records.

Only PreparedServiceLifecycle's original immutable packet can enter sources().
The semantic validator below is also useful for explicitly synthetic development
tests; that validation is never native capture or physical deployment evidence.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re

from .resource_ledger import canonical, digest, exact, nat, require, sha
from .successor_lean import string
from .controller_continuation_lean import negative_location

MODULES = ('ServiceLifecycle',)
POSITIVE = 'ServiceLifecycleExamples'
DIMENSIONS = ('service_lifetimes', 'process_launch_attempts', 'frontend_input_attempts',
              'request_bytes', 'response_bytes', 'authority_tls_connections')
NEGATIVES = (
    'WrongLifecycleCommission', 'SubstitutedLifecycleSource', 'StaleLifecycleCursor',
    'WrongLifecycleOwner', 'ReplayedLifecycleIdentity', 'SubstitutedLifetimeEnvelope',
    'UnprepaidServiceLaunch', 'RepeatedServiceLaunch', 'PendingLifecycleReopened',
    'InterruptedLifetimeRefunded', 'OverspentLifetimeBudget', 'DeniedLifetimeDebited',
    'LifecycleCloseRefunded', 'RestartReusesReservation', 'UnchargedMalformedInput',
    'UnchargedInputBytes', 'ExceededPrepaidUsage', 'ReplayedServiceUsageEvent',
    'SubstitutedReceiptSource', 'SubstitutedReceiptGrant', 'EarlyLifetimeClose',
    'ReplayedLifetimeOwner', 'WholeLedgerCloneImpossible', 'MissingAccountingPromotes',
    'ServiceCertificatePromotes',
)
LABELS = (*MODULES, POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
GENERIC_NAMES = tuple('Phase17ServiceLifecycle.' + name for name in (
    'usage_reflexive', 'usage_not_refunded', 'usage_zero_bounded',
    'advanced_spec', 'advanced_construct', 'advanced_source_bound', 'advanced_current_cursor',
    'stale_cursor_refused', 'advanced_serial', 'advanced_head', 'reserved_exact',
    'reserved_commission_and_owner', 'reserved_within_budget', 'insufficient_budget_refused',
    'denied_no_new_reservation', 'denied_is_insufficient', 'pending_blocks_reservation',
    'pending_blocks_reopen', 'replayed_lifetime_refused', 'launched_requires_reservation',
    'launched_consumes_exactly', 'launched_once', 'charged_exactly', 'charged_within_envelope',
    'charged_no_refund', 'close_receipt_bound', 'closed_no_refund', 'reopened_no_refund',
    'cumulative_reservation_nondecreasing', 'advance_preserves_budget',
    'reachable_reservations_bounded', 'cloned_complete_ledgers_accept_identically',
    'root_required', 'unknown_accounting_blocks_promotion', 'missing_commission_blocks_promotion',
))
SELECTED_NAMES = tuple('Phase17ServiceLifecycleExamples.' + name for name in (
    'selected_trace', 'selected_first_reservation', 'selected_first_launch',
    'selected_launch_not_reissued', 'selected_restart_charge', 'selected_input_consumption',
    'selected_closing_retains_charges', 'selected_budget_refusal',
    'selected_denial_retains_reservation', 'selected_interrupted_reservation',
    'selected_interrupted_reopen_refused', 'selected_no_promotion',
    'selected_whole_ledger_clone_boundary',
))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)
PROJECTION_FIELDS = {'commission', 'steps', 'budget_refusal',
                     'interrupted_reservation', 'interrupted_reopen'}
STATE_FIELDS = {'current', 'reserved', 'used_lifetime_ids', 'pending', 'closed_grants',
                'owner', 'owner_nonces'}
GRANT_FIELDS = {'identity', 'commission', 'lifetime_id', 'owner', 'epoch',
                'envelope', 'reservation_cursor'}
STEP_FIELDS = {'runtime', 'before', 'expected', 'command', 'next_head', 'after'}
MAX_AMOUNT = 2**63 - 1


def _copy(value):
    from rcp_rclm_runtime.canonical.json import load_json_strict
    return load_json_strict(canonical(value), require_canonical=True)


def _amount(value):
    require(nat(value) <= MAX_AMOUNT, 'finite exact lifecycle quantity required')
    return value


def _identifier(value):
    require(type(value) is str and 0 < len(value) <= 128 and
            all(32 <= ord(character) <= 126 for character in value),
            'bounded printable lifecycle identifier required')
    return value


def _usage(value):
    require(type(value) is list and len(value) == len(DIMENSIONS),
            'exact six-dimensional lifecycle usage required')
    for amount in value:
        _amount(amount)
    return value


def _fits(value, bound):
    return all(left <= right for left, right in zip(value, bound, strict=True))


def _add(left, right):
    return [a + b for a, b in zip(left, right, strict=True)]


def _cursor(value):
    exact(value, {'commission', 'epoch', 'serial', 'head'})
    digest(value['commission']); digest(value['head'])
    _amount(value['epoch']); _amount(value['serial'])
    return value


def _grant(value):
    exact(value, GRANT_FIELDS)
    for field in ('identity', 'commission', 'owner'):
        digest(value[field])
    _identifier(value['lifetime_id']); _amount(value['epoch'])
    _usage(value['envelope']); _cursor(value['reservation_cursor'])
    require(value['reservation_cursor']['commission'] == value['commission'] and
            value['reservation_cursor']['epoch'] == value['epoch'],
            'grant reservation cursor names another commission or epoch')
    return value


def _unique(values, validator, label):
    require(type(values) is list and len(values) <= 2048, 'bounded ' + label + ' required')
    for value in values:
        validator(value)
    require(len(values) == len(set(values)), 'replayed ' + label)


def _state(value):
    exact(value, STATE_FIELDS)
    _cursor(value['current']); _usage(value['reserved'])
    _unique(value['used_lifetime_ids'], _identifier, 'lifetime identities')
    _unique(value['closed_grants'], digest, 'closed grant identities')
    _unique(value['owner_nonces'], digest, 'lifetime owner identities')
    if value['owner'] is not None:
        digest(value['owner'])
        require(value['owner'] in value['owner_nonces'] and value['current']['epoch'] > 0,
                'active owner lacks consumed opening identity')
    pending = value['pending']
    if pending is not None:
        exact(pending, {'grant', 'launched', 'used', 'event_ids'})
        _grant(pending['grant']); _usage(pending['used'])
        require(type(pending['launched']) is bool, 'exact launch-consumption Boolean required')
        _unique(pending['event_ids'], _identifier, 'usage event identities')
        require(_fits(pending['used'], pending['grant']['envelope']), 'pending usage exceeds reservation')
        require(pending['grant']['commission'] == value['current']['commission'] and
                pending['grant']['epoch'] == value['current']['epoch'] and
                pending['grant']['owner'] == value['owner'] and
                pending['grant']['lifetime_id'] in value['used_lifetime_ids'],
                'pending grant lacks exact owner, epoch or lifetime consumption')
        if not pending['launched']:
            require(pending['used'] == [0] * 6 and pending['event_ids'] == [],
                    'unlaunched reservation cannot have consumed work')
    return value


def _receipt(value):
    exact(value, {'commission', 'source', 'grant', 'lifetime_id', 'epoch', 'used'})
    for field in ('commission', 'source', 'grant'):
        digest(value[field])
    _identifier(value['lifetime_id']); _amount(value['epoch']); _usage(value['used'])
    return value


def _command(value):
    require(type(value) is dict and value.get('kind') in
            ('reopen', 'reserve', 'deny', 'launch', 'charge', 'close'), 'known lifecycle operation required')
    kind = value['kind']
    fields = {'kind'} if kind == 'reopen' else {'kind', 'grant'}
    if kind == 'charge': fields |= {'event_id', 'delta'}
    if kind == 'close': fields.add('receipt')
    exact(value, fields)
    if kind != 'reopen': _grant(value['grant'])
    if kind == 'charge': _identifier(value['event_id']); _usage(value['delta'])
    if kind == 'close': _receipt(value['receipt'])
    return value


def _step(value):
    exact(value, STEP_FIELDS)
    exact(value['runtime'], {'source', 'owner'})
    digest(value['runtime']['source']); digest(value['runtime']['owner'])
    _state(value['before']); _cursor(value['expected']); _command(value['command'])
    digest(value['next_head'])
    if value['after'] is not None: _state(value['after'])
    return value


def _advance(commission, step):
    """Semantic replay only. Original native evidence is checked by capture."""
    state, runtime, command = deepcopy(step['before']), step['runtime'], step['command']
    if not (runtime['source'] == commission['source'] and
            state['current']['commission'] == commission['identity'] and
            step['expected'] == state['current'] and step['next_head'] != state['current']['head']):
        return None
    kind = command['kind']; pending = state['pending']
    owned = state['owner'] == runtime['owner'] and state['current']['epoch'] > 0
    if kind == 'reopen':
        if pending is not None or runtime['owner'] in state['owner_nonces']: return None
        state['current']['epoch'] += 1
        state['owner'] = runtime['owner']; state['owner_nonces'].append(runtime['owner'])
    else:
        grant = command['grant']
        if not (owned and grant['commission'] == commission['identity'] and
                grant['owner'] == runtime['owner'] and grant['epoch'] == state['current']['epoch']):
            return None
        if kind in ('reserve', 'deny'):
            if not (pending is None and grant['lifetime_id'] not in state['used_lifetime_ids'] and
                    grant['envelope'] == commission['envelope'] and grant['reservation_cursor'] == state['current']):
                return None
            proposed = _add(state['reserved'], grant['envelope'])
            if _fits(proposed, commission['budget']) != (kind == 'reserve'): return None
            if kind == 'reserve':
                state['reserved'] = proposed
                state['used_lifetime_ids'].append(grant['lifetime_id'])
                state['pending'] = {'grant': deepcopy(grant), 'launched': False, 'used': [0] * 6, 'event_ids': []}
        elif pending is None or pending['grant'] != grant:
            return None
        elif kind == 'launch':
            charged = _add(pending['used'], [1, 1, 0, 0, 0, 0])
            if pending['launched'] or not _fits(charged, grant['envelope']): return None
            pending['launched'] = True; pending['used'] = charged
        elif kind == 'charge':
            delta = command['delta']; charged = _add(pending['used'], delta)
            if not (pending['launched'] and command['event_id'] not in pending['event_ids'] and
                    delta[0] == 0 and any(delta) and _fits(charged, grant['envelope'])): return None
            pending['used'] = charged; pending['event_ids'].append(command['event_id'])
        else:
            expected = {'commission': commission['identity'], 'source': commission['source'],
                'grant': grant['identity'], 'lifetime_id': grant['lifetime_id'],
                'epoch': grant['epoch'], 'used': pending['used']}
            if not pending['launched'] or command['receipt'] != expected: return None
            state['pending'] = None; state['closed_grants'].append(grant['identity'])
    state['current']['serial'] += 1
    state['current']['head'] = step['next_head']
    return state


def validate_projection(value):
    """Check exact selected semantics, not legitimacy of their physical origin."""
    exact(value, PROJECTION_FIELDS)
    commission = value['commission']
    exact(commission, {'identity', 'source', 'envelope', 'budget'})
    digest(commission['identity']); digest(commission['source'])
    _usage(commission['envelope']); _usage(commission['budget'])
    require(commission['envelope'][0] == 1 and all(amount > 0 for amount in commission['envelope']),
            'fixed positive prepaid lifetime envelope required')
    steps = value['steps']
    require(type(steps) is list and 0 < len(steps) <= 2048, 'bounded original lifecycle trace required')
    counts = {kind: 0 for kind in ('reserve', 'launch', 'close', 'deny', 'reopen', 'charge')}
    previous = None
    for step in steps:
        _step(step)
        require(step['after'] is not None and _advance(commission, step) == step['after'],
                'selected lifecycle transition differs from exact native-derived semantics')
        if previous is not None:
            require(step['before'] == previous, 'selected lifecycle trace is not contiguous')
        previous = step['after']; counts[step['command']['kind']] += 1
    require(counts['reserve'] == counts['launch'] == counts['close'] == 2 and counts['deny'] == 1 and
            counts['reopen'] == 2 and counts['charge'] > 0,
            'selected two-lifetime and explicit denial inventory differs')
    first = steps[0]['before']
    require(first['reserved'] == [0] * 6 and first['pending'] is None and
            first['used_lifetime_ids'] == first['closed_grants'] == first['owner_nonces'] == [] and
            first['owner'] is None and first['current']['epoch'] == first['current']['serial'] == 0,
            'selected lifecycle trace lacks exact unconsumed genesis')
    require(previous['pending'] is None and len(previous['closed_grants']) == 2 and
            previous['reserved'] == _add(commission['envelope'], commission['envelope']),
            'selected final state omits permanent lifetime reservations')
    require(any(step['command']['kind'] == 'charge' and step['command']['delta'][2] == 1 and
                step['command']['delta'][3] > 0 for step in steps),
            'selected trace lacks an actual charged input attempt and raw bytes')
    denied = next(step for step in steps if step['command']['kind'] == 'deny')
    refusal = _step(value['budget_refusal'])
    wanted = deepcopy(denied); wanted['command']['kind'] = 'reserve'; wanted['after'] = None
    require(refusal == wanted and _advance(commission, refusal) is None,
            'budget refusal does not match the separately retained durable denial')
    interrupted = _step(value['interrupted_reservation'])
    require(interrupted['command']['kind'] == 'reserve' and interrupted['after'] is not None and
            _advance(commission, interrupted) == interrupted['after'] and
            interrupted['before']['reserved'] == [0] * 6,
            'interrupted isolated control requires an actual fresh permanent reservation')
    reopen = _step(value['interrupted_reopen'])
    require(reopen['command'] == {'kind': 'reopen'} and reopen['before'] == interrupted['after'] and
            reopen['expected'] == reopen['before']['current'] and reopen['after'] is None and
            reopen['runtime']['source'] == commission['source'] and
            reopen['runtime']['owner'] not in reopen['before']['owner_nonces'] and
            _advance(commission, reopen) is None,
            'interrupted reopen must fail because the exact reservation remains pending')
    return _copy(value)


def projection_from_evidence(main_evidence, interrupted_evidence, *, interrupted_reopen_owner=None):
    """Pure mapping of independently verified original lifecycle exports.

    The denied reserve is a counterfactual at the exact actual denial's before
    state; the actual deny remains in the trace and advances its journal cursor.
    Likewise a refused reopen has no installed head. Its proposed head is a
    domain-separated semantic marker, not a claimed native commit. Supplying the
    originally attempted owner binds the selected pending-refusal proposition to
    that retained control; omission is intended for synthetic development data.
    Full capture independently joins these exports to the original service and
    process records before PreparedServiceLifecycle can enter sources().
    """
    from . import service_lifecycle as ledger
    for evidence in (main_evidence, interrupted_evidence):
        ledger.verify_evidence(evidence, expected_commission_sha256=evidence['commission_sha256'])
    require(main_evidence['commission'] == interrupted_evidence['commission'] and
            main_evidence['commission_sha256'] == interrupted_evidence['commission_sha256'],
            'isolated interrupted control must retain the same declared commission')
    native_commission = main_evidence['commission']
    commission = {'identity': main_evidence['commission_sha256'],
        'source': native_commission['bindings']['runtime_sha256'],
        'envelope': list(native_commission['lifetime_envelope']),
        'budget': list(native_commission['total_budget'])}

    def cursor(value):
        return {'commission': value['commission_sha256'], 'epoch': value['epoch'],
                'serial': value['serial'], 'head': value['head']}

    def grant(value):
        return {'identity': value['grant_sha256'], 'commission': value['commission_sha256'],
            'lifetime_id': value['lifetime_id'], 'owner': value['owner_nonce'], 'epoch': value['epoch'],
            'envelope': list(value['envelope']), 'reservation_cursor': cursor(value['reservation_cursor'])}

    def state(value, at):
        pending = value['pending']
        return {'current': cursor(at), 'reserved': list(value['reserved']),
            'used_lifetime_ids': list(value['used_lifetime_ids']),
            'pending': None if pending is None else {'grant': grant(pending['grant']),
                'launched': pending['phase'] == 'launched', 'used': list(pending['used']),
                'event_ids': list(pending['consumed_event_ids'])},
            'closed_grants': [closed['grant']['grant_sha256'] for closed in value['closed']],
            'owner': value['owner_nonce'], 'owner_nonces': list(value['owner_nonces'])}

    def mapped(evidence):
        result = []
        for prior, event in zip(evidence['events'], evidence['events'][1:]):
            before_cursor = {'commission_sha256': evidence['commission_sha256'],
                'epoch': prior['epoch'], 'serial': prior['serial'], 'head': prior['hash']}
            after_cursor = {'commission_sha256': evidence['commission_sha256'],
                'epoch': event['epoch'], 'serial': event['serial'], 'head': event['hash']}
            before = state(prior['after'], before_cursor)
            payload, kind = event['payload'], event['kind']
            owner = payload['owner_nonce'] if kind == 'open' else before['owner']
            if kind == 'open':
                command = {'kind': 'reopen'}
            else:
                command = {'kind': 'close' if kind == 'finish' else kind, 'grant': grant(payload['grant'])}
                if kind == 'charge':
                    command.update(event_id=payload['event_id'], delta=list(payload['delta']))
                if kind == 'finish':
                    original = before['pending']['grant']
                    command['receipt'] = {'commission': commission['identity'], 'source': commission['source'],
                        'grant': original['identity'], 'lifetime_id': original['lifetime_id'],
                        'epoch': original['epoch'], 'used': list(before['pending']['used'])}
            result.append({'runtime': {'source': commission['source'], 'owner': owner},
                'before': before, 'expected': cursor(event['before_cursor']), 'command': command,
                'next_head': event['hash'], 'after': state(event['after'], after_cursor)})
        return result

    steps = mapped(main_evidence)
    denials = [step for step in steps if step['command']['kind'] == 'deny']
    require(len(denials) == 1, 'one actual durable budget denial required')
    refusal = deepcopy(denials[0]); refusal['command']['kind'] = 'reserve'; refusal['after'] = None
    interrupted_steps = mapped(interrupted_evidence)
    require([event['kind'] for event in interrupted_evidence['events']] == ['provision', 'open', 'reserve'],
            'isolated interrupted control must not launch or charge work')
    interrupted = interrupted_steps[-1]
    retained = interrupted['after']
    if interrupted_reopen_owner is None:
        interrupted_reopen_owner = sha(b'phase17ao:semantic-refused-owner\0' + canonical(retained['current']))
    digest(interrupted_reopen_owner)
    next_head = sha(b'phase17ao:uninstalled-reopen-head\0' + canonical(
        {'current': retained['current'], 'owner': interrupted_reopen_owner}))
    reopen = {'runtime': {'source': commission['source'], 'owner': interrupted_reopen_owner},
        'before': deepcopy(retained), 'expected': deepcopy(retained['current']),
        'command': {'kind': 'reopen'}, 'next_head': next_head, 'after': None}
    return validate_projection({'commission': commission, 'steps': steps, 'budget_refusal': refusal,
        'interrupted_reservation': interrupted, 'interrupted_reopen': reopen})


def _prepared(value, root):
    from .service_lifecycle_capture import PreparedServiceLifecycle
    require(type(value) is PreparedServiceLifecycle, 'checked PreparedServiceLifecycle required')
    return PreparedServiceLifecycle(value.packet_bytes, Path(root))


def project(prepared, root):
    checked = _prepared(prepared, root)
    projection = validate_projection(checked.packet['formal_projection'])
    return {'packet_sha256': sha(checked.packet_bytes), **projection}


def _literal_list(values, render):
    return '[' + ', '.join(render(value) for value in values) + ']'


def _usage_literal(value):
    return '⟨' + ', '.join(str(number) for number in value) + '⟩'


def _cursor_literal(value):
    return '⟨' + ', '.join((string(value['commission']), str(value['epoch']),
                          str(value['serial']), string(value['head']))) + '⟩'


def _grant_literal(value):
    return '⟨' + ', '.join((string(value['identity']), string(value['commission']), string(value['lifetime_id']),
        string(value['owner']), str(value['epoch']), _usage_literal(value['envelope']),
        _cursor_literal(value['reservation_cursor']))) + '⟩'


def _state_literal(value):
    pending = value['pending']
    literal = 'none' if pending is None else 'some ⟨' + ', '.join((_grant_literal(pending['grant']),
        str(pending['launched']).lower(), _usage_literal(pending['used']),
        _literal_list(pending['event_ids'], string))) + '⟩'
    owner = 'none' if value['owner'] is None else 'some ' + string(value['owner'])
    return '⟨' + ', '.join((_cursor_literal(value['current']), _usage_literal(value['reserved']),
        _literal_list(value['used_lifetime_ids'], string), literal, _literal_list(value['closed_grants'], string),
        owner, _literal_list(value['owner_nonces'], string))) + '⟩'


def _receipt_literal(value):
    return '⟨' + ', '.join((string(value['commission']), string(value['source']), string(value['grant']),
        string(value['lifetime_id']), str(value['epoch']), _usage_literal(value['used']))) + '⟩'


def _command_literal(value):
    kind = value['kind']
    if kind == 'reopen': return '.reopen'
    result = '.' + kind + ' (' + _grant_literal(value['grant']) + ')'
    if kind == 'charge': result += ' ' + string(value['event_id']) + ' (' + _usage_literal(value['delta']) + ')'
    if kind == 'close': result += ' (' + _receipt_literal(value['receipt']) + ')'
    return '(' + result + ')'


def _step_literal(value):
    after = 'none' if value['after'] is None else 'some ' + _state_literal(value['after'])
    runtime = '⟨' + string(value['runtime']['source']) + ', ' + string(value['runtime']['owner']) + '⟩'
    return '⟨' + ', '.join((runtime, _state_literal(value['before']), _cursor_literal(value['expected']),
        _command_literal(value['command']), string(value['next_head']), after)) + '⟩'


def render_selected(projection, root):
    exact(projection, PROJECTION_FIELDS | {'packet_sha256'})
    digest(projection['packet_sha256'])
    validate_projection({key: projection[key] for key in PROJECTION_FIELDS})
    generic = (Path(root) / 'lean/phase17_bridge/ServiceLifecycle.lean').read_bytes()
    require(generic.startswith(b'import Std\nimport Lean.Elab.Tactic.Omega\n') and
            generic.rstrip().endswith(b'end Phase17ServiceLifecycle'), 'generic service-lifecycle source differs')
    text = generic.decode() + '\n\nnamespace Phase17ServiceLifecycleExamples\nopen Phase17ServiceLifecycle\n'
    text += 'set_option maxRecDepth 65536\nset_option maxHeartbeats 32000000\n'
    text += 'def packetSha256 : String := ' + string(projection['packet_sha256']) + '\n'
    c = projection['commission']
    text += 'def commission : Commission := ⟨' + ', '.join((string(c['identity']), string(c['source']),
        _usage_literal(c['envelope']), _usage_literal(c['budget']))) + '⟩\n'
    selections = {'reopen': [], 'reserve': [], 'launch': [], 'close': [], 'deny': [], 'charge': []}
    for index, step in enumerate(projection['steps']):
        name = 'step' + str(index)
        selections[step['command']['kind']].append(name)
        text += f'def {name} : TraceStep := ' + _step_literal(step) + '\n'
    text += 'def trace : List TraceStep := [' + ', '.join('step' + str(i) for i in range(len(projection['steps']))) + ']\n'
    for alias, kind, index in (('firstOpen', 'reopen', 0), ('firstReserve', 'reserve', 0),
            ('firstLaunch', 'launch', 0), ('firstClose', 'close', 0), ('secondReserve', 'reserve', 1),
            ('secondLaunch', 'launch', 1), ('secondClose', 'close', 1), ('denied', 'deny', 0)):
        text += f'def {alias} : TraceStep := {selections[kind][index]}\n'
    input_index = next(i for i, step in enumerate(projection['steps']) if step['command']['kind'] == 'charge' and
                       step['command']['delta'][2] == 1 and step['command']['delta'][3] > 0)
    text += f'def firstInput : TraceStep := step{input_index}\n'
    for field, name in (('budget_refusal', 'budgetRefusal'), ('interrupted_reservation', 'interruptedReserve'),
                        ('interrupted_reopen', 'interruptedReopen')):
        text += f'def {name} : TraceStep := ' + _step_literal(projection[field]) + '\n'
    text += '''def afterState (step : TraceStep) : State := step.after.getD step.before
def pendingUsage (s : State) : Usage := match s.pending with | none => Usage.zero | some p => p.used
def grantOf (command : Command) : Grant := match command with
  | .reserve g | .deny g | .launch g | .charge g .. | .close g .. => g
  | .reopen => ⟨"", "", "", "", 0, Usage.zero, ⟨"", 0, 0, ""⟩⟩
def chargeEvent (command : Command) : String := match command with | .charge _ eventId _ => eventId | _ => ""
def chargeDelta (command : Command) : Usage := match command with | .charge _ _ delta => delta | _ => Usage.zero
def closeReceipt (command : Command) : Receipt := match command with
  | .close _ receipt => receipt | _ => ⟨"", "", "", "", 0, Usage.zero⟩
def execute (step : TraceStep) : Option State :=
  advance commission step.runtime step.before step.expected step.command step.nextHead
theorem selected_trace : trace.all (stepValid commission) = true := by decide +kernel
theorem selected_first_reservation : execute firstReserve = some (afterState firstReserve) := by decide +kernel
theorem selected_first_launch : execute firstLaunch = some (afterState firstLaunch) := by decide +kernel
theorem selected_launch_not_reissued :
    advance commission firstLaunch.runtime (afterState firstLaunch) (afterState firstLaunch).current
      firstLaunch.command "another-head" = none := by decide +kernel
theorem selected_restart_charge :
    (afterState secondReserve).reserved = (afterState firstReserve).reserved.add commission.envelope := by decide +kernel
theorem selected_input_consumption :
    (chargeDelta firstInput.command).frontendInputAttempts = 1 ∧
    0 < (chargeDelta firstInput.command).requestBytes ∧
    pendingUsage (afterState firstInput) = (pendingUsage firstInput.before).add (chargeDelta firstInput.command) := by decide +kernel
theorem selected_closing_retains_charges :
    (afterState firstClose).reserved = firstClose.before.reserved ∧
    (afterState secondClose).reserved = secondClose.before.reserved := by decide +kernel
theorem selected_budget_refusal : execute budgetRefusal = none := by decide +kernel
theorem selected_denial_retains_reservation :
    execute denied = some (afterState denied) ∧
    (afterState denied).reserved = denied.before.reserved ∧
    (afterState denied).current.serial = denied.before.current.serial + 1 := by decide +kernel
theorem selected_interrupted_reservation :
    execute interruptedReserve = some (afterState interruptedReserve) ∧
    (afterState interruptedReserve).pending ≠ none ∧
    (afterState interruptedReserve).reserved = commission.envelope := by decide +kernel
theorem selected_interrupted_reopen_refused : execute interruptedReopen = none := by decide +kernel
theorem selected_no_promotion : promotionAdmission false false false = false := by decide +kernel
theorem selected_whole_ledger_clone_boundary :
    ∃ first second : State, first = firstReserve.before ∧ second = firstReserve.before ∧
      advance commission firstReserve.runtime first firstReserve.expected firstReserve.command
        firstReserve.nextHead = some (afterState firstReserve) ∧
      advance commission firstReserve.runtime second firstReserve.expected firstReserve.command
        firstReserve.nextHead = some (afterState firstReserve) := by
  apply cloned_complete_ledgers_accept_identically
  exact selected_first_reservation
end Phase17ServiceLifecycleExamples
'''
    return text.encode()


def render_positive():
    return ('import ServiceLifecycle\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(label):
    require(label in NEGATIVES, 'exact service-lifecycle negative required')
    wrong = {
        'WrongLifecycleCommission': 'execute { firstReserve with before := { firstReserve.before with current := { firstReserve.before.current with commission := "untrusted" } } } ≠ none',
        'SubstitutedLifecycleSource': 'execute { firstReserve with runtime := { firstReserve.runtime with source := "untrusted" } } ≠ none',
        'StaleLifecycleCursor': 'execute { firstReserve with expected := { firstReserve.expected with serial := firstReserve.expected.serial + 1 } } ≠ none',
        'WrongLifecycleOwner': 'execute { firstReserve with runtime := { firstReserve.runtime with owner := "untrusted" } } ≠ none',
        'ReplayedLifecycleIdentity': 'execute { firstReserve with before := { firstReserve.before with usedLifetimeIds := firstReserve.before.usedLifetimeIds ++ [(grantOf firstReserve.command).lifetimeId] } } ≠ none',
        'SubstitutedLifetimeEnvelope': 'execute { firstReserve with command := .reserve { grantOf firstReserve.command with envelope := Usage.zero } } ≠ none',
        'UnprepaidServiceLaunch': 'execute { firstReserve with command := firstLaunch.command } ≠ none',
        'RepeatedServiceLaunch': 'advance commission firstLaunch.runtime (afterState firstLaunch) (afterState firstLaunch).current firstLaunch.command "another-head" ≠ none',
        'PendingLifecycleReopened': 'execute interruptedReopen ≠ none',
        'InterruptedLifetimeRefunded': '(afterState interruptedReserve).reserved = Usage.zero',
        'OverspentLifetimeBudget': 'execute budgetRefusal ≠ none',
        'DeniedLifetimeDebited': '(afterState denied).reserved ≠ denied.before.reserved',
        'LifecycleCloseRefunded': '(afterState firstClose).reserved = Usage.zero',
        'RestartReusesReservation': '(afterState secondReserve).reserved = (afterState firstReserve).reserved',
        'UnchargedMalformedInput': '(pendingUsage (afterState firstInput)).frontendInputAttempts = (pendingUsage firstInput.before).frontendInputAttempts',
        'UnchargedInputBytes': '(pendingUsage (afterState firstInput)).requestBytes = (pendingUsage firstInput.before).requestBytes',
        'ExceededPrepaidUsage': 'execute { firstInput with command := .charge (grantOf firstInput.command) "over-budget" { commission.envelope with serviceLifetimes := 0, processLaunchAttempts := commission.envelope.processLaunchAttempts + 1 } } ≠ none',
        'ReplayedServiceUsageEvent': 'execute { firstInput with before := { firstInput.before with pending := firstInput.before.pending.map (fun p => { p with eventIds := p.eventIds ++ [chargeEvent firstInput.command] }) } } ≠ none',
        'SubstitutedReceiptSource': 'execute { firstClose with command := .close (grantOf firstClose.command) { closeReceipt firstClose.command with source := "untrusted" } } ≠ none',
        'SubstitutedReceiptGrant': 'execute { firstClose with command := .close (grantOf firstClose.command) { closeReceipt firstClose.command with grant := "untrusted" } } ≠ none',
        'EarlyLifetimeClose': 'execute { firstLaunch with command := firstClose.command } ≠ none',
        'ReplayedLifetimeOwner': 'execute { firstOpen with before := { firstOpen.before with ownerNonces := [firstOpen.runtime.owner] } } ≠ none',
        'WholeLedgerCloneImpossible': 'execute firstReserve = none',
        'MissingAccountingPromotes': 'promotionAdmission false true true = true',
        'ServiceCertificatePromotes': 'promotionAdmission true true false = true',
    }
    text = '''import ServiceLifecycle
namespace Phase17ServiceLifecycleControl
open Phase17ServiceLifecycle Phase17ServiceLifecycleExamples
set_option maxRecDepth 65536
set_option maxHeartbeats 32000000
'''
    text += 'def wrongClaim : Bool := decide (' + wrong[label] + ')\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17ServiceLifecycleControl\n').encode()


def sources(prepared, root):
    projection = project(prepared, root)
    result = {MODULES[0]: render_selected(projection, root), POSITIVE: render_positive()}
    result.update({label: render_negative(label) for label in NEGATIVES})
    for label, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + label)
    return result


def parse_audits(stdout):
    require(type(stdout) is str, 'exact audit output text required')
    cursor, audits = 0, {}
    for name in NAMES:
        match = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'missing or reordered service-lifecycle audit: ' + name)
        dependencies = [] if match[1] is None else [item.strip() for item in match[1].split(',') if item.strip()]
        require(len(dependencies) == len(set(dependencies)) and set(dependencies) <= ALLOWED_AXIOMS,
                'unapproved service-lifecycle audit dependency')
        audits[name] = dependencies; cursor = match.end()
    require(cursor == len(stdout), 'unexpected service-lifecycle audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    require(raw == render_negative(label), 'negative source differs from exact designated semantic control')
    line, column = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(column) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected service-lifecycle negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': column}
