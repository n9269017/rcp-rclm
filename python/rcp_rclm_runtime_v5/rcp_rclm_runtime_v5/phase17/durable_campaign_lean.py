"""AL certificates for the exact durable Phase17O campaign projection.

The immutable prepared packet rechecks every native campaign journal, source
closure, objective authorization, sealed transcript and controller order in
Python. This generator derives states from those bytes, never from a supplied
formal-state field. Lean checks each projected transition, one-use launch,
restart fencing and declared-work accounting. Hashes are retained identities;
no physical execution, independent deployment or complete accounting is inferred.
"""
from __future__ import annotations

from pathlib import Path
import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as object_hash
from rcp_rclm_runtime.canonical.json import load_json_strict
from .resource_ledger import canonical, require, sha, nat, vector, add, ZERO
from . import campaign_budget as budget
from . import durable_campaign as runtime
from .successor_lean import string
from .controller_continuation_lean import negative_location

MODULES = ('DurableCampaign',)
POSITIVE = 'DurableCampaignExamples'
NEGATIVES = (
    'WrongCampaignProvision', 'WrongCampaignPolicy', 'WrongCampaignParent',
    'WrongCampaignObjective', 'WrongCampaignEvaluator', 'WrongCampaignImplementation',
    'WrongCampaignWorker', 'StaleCampaignEpoch', 'StaleCampaignSerial',
    'StaleCampaignHead', 'StaleCampaignJournal', 'StaleCampaignSnapshot',
    'ReplayedCampaignNonce', 'CampaignControllerMayReopen', 'RepeatedCampaignLaunch',
    'CampaignCompletionBeforeLaunch', 'ReopenedCampaignOwner',
    'CampaignOverBudgetReservation', 'RefundedCampaignReservation',
    'ClonedCampaignRootImpossible',
)
LABELS = (*MODULES, POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
GENERIC_NAMES = tuple('Phase17DurableCampaign.' + name for name in (
    'envelope_cost', 'envelope_monotone', 'usage_cost_monotone', 'usage_add_cost',
    'usage_not_refunded', 'committed_spec', 'committed_construct', 'committed_binding',
    'wrong_binding_refused', 'stale_cursor_refused', 'request_cannot_reopen',
    'committed_serial', 'predecessor_cursor_consumed_once', 'reserved_exact',
    'replayed_nonce_refused', 'denied_no_reservation', 'launched_consumed',
    'launch_not_reissued', 'completed_no_refund', 'completed_within_envelope',
    'reopened_retains_charges', 'reopened_owner_cannot_launch',
    'reopened_owner_cannot_complete', 'initial_accounted', 'committed_accounted',
    'reachable_accounted', 'reachable_completed_and_pending_cost',
    'identical_root_copies_accept_identically',
))
SELECTED_NAMES = tuple('Phase17DurableCampaignExamples.' + name for name in (
    'main_reachable', 'interrupted_reachable', 'denial_reachable',
    'main_completed_pending_accounted', 'main_exact_declared_work',
    'interrupted_charge_retained', 'interrupted_owner_revoked',
    'first_launch_consumed', 'first_launch_cannot_repeat',
    'aggregate_denial_no_new_charge', 'root_copy_outside_guarantee',
))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)
CASE_NAMES = ('two_sessions_across_restart', 'interrupted_reservation', 'aggregate_denial')
STATUS = {'open': '.open', 'pending': '.pending', 'resource_exhausted': '.denied'}


def _prepared(value, root):
    from .durable_campaign_capture import PreparedDurableCampaign
    require(type(value) is PreparedDurableCampaign, 'exact prepared durable campaign required')
    # Reconstruct at the selected source tree: an old prepared object cannot
    # survive source mutation merely by retaining a previous validation result.
    return PreparedDurableCampaign(value.packet_bytes, root)


def _same(left, right, message):
    require(canonical(left) == canonical(right), message)


def _nat(value):
    return str(nat(value))


def _usage(value):
    return '⟨' + ', '.join(_nat(item) for item in vector(value)) + '⟩'


def _strings(values):
    require(type(values) is list and all(type(item) is str for item in values),
            'exact string list required for campaign projection')
    return '[' + ', '.join(string(item) for item in values) + ']'


def _binding(provision):
    context = provision['context']
    return {
        'campaign': context['campaign_id'], 'parentState': context['predecessor_state_hash'],
        'parentPackage': context['predecessor_package_hash'], 'verifier': context['fixed_verifier_hash'],
        'policy': object_hash(provision['policy']),
        'implementation': provision['implementation']['implementation_sha256'],
        'objectivePolicy': provision['objective_policy'],
        'evaluatorProtocol': provision['evaluator_protocol'],
        'workerProtocol': provision['worker_protocol'],
        'accountingProfile': provision['accounting_profile'],
    }


def _provision_literal(provision, pin):
    binding = '⟨' + ', '.join(string(value) for value in _binding(provision).values()) + '⟩'
    policy = provision['policy']
    return ('⟨' + string(pin) + ', ' + binding + ', ' + _nat(provision['context']['installed_count']) +
            ', ⟨' + _usage(policy['limits']) + ', ' + _nat(policy['cost_limit']) + '⟩⟩')


def _pending_projection(pending):
    if pending is None:
        return None
    permit = pending['permit']
    require(pending['stage'] in ('reserved', 'launch_consumed'), 'unknown campaign launch projection')
    owner = pending['owner_epoch']
    if owner is not None:
        nat(owner)
    return {'grant': permit['grant']['grant_hash'], 'freeze': permit['freeze']['freeze_hash'],
            'credits': nat(permit['grant']['candidate_credits']),
            'reservation_epoch': nat(permit['reservation_epoch']), 'owner_epoch': owner,
            'launched': pending['stage'] == 'launch_consumed'}


def _state_projection(entry, provision):
    event, snapshot = entry['event'], entry['snapshot']
    _, journal = runtime._journal(snapshot, provision)
    require(journal.status in STATUS, 'unsupported campaign state projection')
    completed = (0, 0, 0, 0)
    for encoded in journal.completed:
        value = load_json_strict(encoded)
        completed = add(completed, value['completion']['worker_spent'])
    require(len(snapshot['sessions']) == len(journal.completed), 'completed campaign projection differs')
    pending = _pending_projection(snapshot['pending'])
    require((pending is None) == (journal.pending is None), 'durable pending and campaign journal differ')
    if pending is not None:
        require(pending['grant'] == journal.pending_grant['grant_hash'] and
                pending['freeze'] == journal.pending_grant['objective_freeze_hash'] and
                pending['credits'] == journal.pending_grant['candidate_credits'],
                'pending authorization projection differs')
    return {'provision': event['root_provision_sha256'], 'epoch': nat(event['epoch']),
            'serial': nat(event['serial']), 'head': event['root_head'],
            'journal': event['journal_sha256'], 'image': event['snapshot_sha256'],
            'reserved': list(journal.reserved), 'session_count': journal.session_count,
            'pending': pending, 'nonces': list(snapshot['nonces']), 'freezes': list(journal.freezes),
            'completed_work': list(completed), 'completed_count': len(journal.completed),
            'status': journal.status}


def _pending_literal(value):
    if value is None:
        return 'none'
    owner = 'none' if value['owner_epoch'] is None else 'some ' + _nat(value['owner_epoch'])
    return ('some ⟨' + string(value['grant']) + ', ' + string(value['freeze']) + ', ' +
            _nat(value['credits']) + ', ' + _nat(value['reservation_epoch']) + ', ' + owner +
            ', ' + ('true' if value['launched'] else 'false') + '⟩')


def _state_literal(value):
    return '⟨' + ', '.join((string(value['provision']), _nat(value['epoch']), _nat(value['serial']),
        string(value['head']), string(value['journal']), string(value['image']), _usage(value['reserved']),
        _nat(value['session_count']), _pending_literal(value['pending']), _strings(value['nonces']),
        _strings(value['freezes']), _usage(value['completed_work']), _nat(value['completed_count']),
        STATUS[value['status']])) + '⟩'


def _command_projection(before, after, provision):
    event, snapshot = after['event'], after['snapshot']
    kind = event['kind']
    if kind == 'reopen':
        return {'kind': kind, 'mode': '.backend', 'literal': '.reopen'}
    if kind in ('reserve', 'deny'):
        request = event['request']
        raw, _ = runtime._journal(snapshot, provision)
        body = load_json_strict(raw.splitlines()[-1])['body']
        grant = budget.validate_grant(body['grant'])
        require(body['kind'] == kind and grant['candidate_credits'] == request['credits'],
                'campaign admission body projection differs')
        result = {'kind': kind, 'mode': '.request', 'nonce': request['request_nonce'],
                  'freeze': grant['objective_freeze_hash'], 'grant': grant['grant_hash'],
                  'credits': nat(grant['candidate_credits'])}
        result['literal'] = ('.' + kind + ' ' + string(result['nonce']) + ' ' + string(result['freeze']) +
                             ' ' + string(result['grant']) + ' ' + _nat(result['credits']))
        return result
    pending = before['snapshot']['pending']
    require(type(pending) is dict, 'campaign backend transition has no predecessor grant')
    grant = pending['permit']['grant']['grant_hash']
    if kind == 'launch':
        return {'kind': kind, 'mode': '.backend', 'grant': grant, 'literal': '.launch ' + string(grant)}
    require(kind == 'complete', 'unknown campaign transition projection')
    raw, journal = runtime._journal(snapshot, provision)
    body = load_json_strict(raw.splitlines()[-1])['body']
    require(body['kind'] == 'complete' and body['grant_hash'] == grant,
            'campaign completion body projection differs')
    actual = nat(body['candidate_evaluations'])
    expected = budget.full_grammar_policy(provision['context']['installed_count'], candidate_limit=actual)
    _same(body['worker_spent'], list(expected.limits), 'actual declared campaign work projection differs')
    session = snapshot['sessions'][-1]
    files = runtime._session_files(session)
    require(sha(files['sealed_transcript.json']) == body['transcript_sha256'] and
            len(snapshot['sessions']) == len(journal.completed), 'completion transcript projection differs')
    return {'kind': kind, 'mode': '.backend', 'grant': grant, 'transcript': body['transcript_sha256'],
            'actual': actual, 'literal': '.complete ' + string(grant) + ' ' +
            string(body['transcript_sha256']) + ' ' + _nat(actual)}


def project(prepared, root):
    """Derive every Lean state from revalidated native campaign evidence bytes."""
    checked = _prepared(prepared, root)
    packet = checked.packet
    require([case['name'] for case in packet['cases']] == list(CASE_NAMES),
            'exact durable campaign case order required')
    cases = []
    for case in packet['cases']:
        evidence = case['evidence']; provision = evidence['provision']; pin = case['root_provision_sha256']
        require(evidence['root_provision_sha256'] == pin == object_hash(provision),
                'campaign provision projection differs')
        entries = evidence['entries']
        states = [_state_projection(entry, provision) for entry in entries]
        commands = [_command_projection(entries[index - 1], entries[index], provision)
                    for index in range(1, len(entries))]
        require([state['serial'] for state in states] == list(range(len(states))),
                'campaign projection serials differ')
        require(entries[0]['event']['kind'] == 'provision', 'campaign projection must begin at provision')
        cases.append({'name': case['name'], 'provision': provision, 'pin': pin,
                      'states': states, 'commands': commands})
    require([case['states'][-1]['completed_count'] for case in cases] == [2, 0, 1],
            'selected completion projection differs')
    return {'packet_sha256': sha(checked.packet_bytes), 'cases': cases}


def _first(case, kind):
    indices = [index + 1 for index, command in enumerate(case['commands']) if command['kind'] == kind]
    require(indices, 'selected campaign transition missing: ' + kind)
    return indices[0]


def render_selected(projection, root):
    generic = (Path(root) / 'lean/phase17_bridge/DurableCampaign.lean').read_bytes()
    require(generic.startswith(b'import Std\nimport Lean.Elab.Tactic.Omega\n') and
            generic.rstrip().endswith(b'end Phase17DurableCampaign'), 'generic durable campaign source differs')
    text = generic.decode() + '\n\nnamespace Phase17DurableCampaignExamples\nopen Phase17DurableCampaign\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 16000000\n'
    text += 'def packetSha256 : String := ' + string(projection['packet_sha256']) + '\n'
    cases = projection['cases']
    for ci, case in enumerate(cases):
        text += f'def provision{ci} : Provision := {_provision_literal(case["provision"], case["pin"])}\n'
        for index, state in enumerate(case['states']):
            text += f'def state{ci}_{index} : State := {_state_literal(state)}\n'
            if index == 0:
                text += (f'theorem initial{ci} : state{ci}_0 = initial provision{ci} state{ci}_0.head '
                         f'state{ci}_0.journal state{ci}_0.image := rfl\n'
                         f'theorem reachable{ci}_0 : Reachable provision{ci} state{ci}_0.head '
                         f'state{ci}_0.journal state{ci}_0.image state{ci}_0 := by\n'
                         f'  exact .initial\n')
                continue
            command = case['commands'][index - 1]
            text += f'def command{ci}_{index} : Command := {command["literal"]}\n'
            call = (f'commit provision{ci} provision{ci}.binding state{ci}_{index - 1} '
                    f'(cursor state{ci}_{index - 1}) {command["mode"]} command{ci}_{index} '
                    f'state{ci}_{index}.head state{ci}_{index}.journal state{ci}_{index}.image')
            text += f'theorem step{ci}_{index} : {call} = some state{ci}_{index} := by decide +kernel\n'
            text += (f'theorem reachable{ci}_{index} : Reachable provision{ci} state{ci}_0.head '
                     f'state{ci}_0.journal state{ci}_0.image state{ci}_{index} :=\n'
                     f'  .step reachable{ci}_{index - 1} provision{ci}.binding (cursor state{ci}_{index - 1}) '
                     f'{command["mode"]} command{ci}_{index} state{ci}_{index}.head state{ci}_{index}.journal '
                     f'state{ci}_{index}.image step{ci}_{index}\n')
    finals = [len(case['states']) - 1 for case in cases]
    for ci, name in enumerate(('main', 'interrupted', 'denial')):
        text += f'def {name}Final : State := state{ci}_{finals[ci]}\n'
        text += (f'theorem {name}_reachable : Reachable provision{ci} state{ci}_0.head '
                 f'state{ci}_0.journal state{ci}_0.image {name}Final := reachable{ci}_{finals[ci]}\n')
    reserve = _first(cases[0], 'reserve'); launch = _first(cases[0], 'launch')
    pending_reserve = _first(cases[1], 'reserve'); deny = _first(cases[2], 'deny')
    for name, value in (
        ('firstBeforeReserve', f'state0_{reserve - 1}'), ('firstReserved', f'state0_{reserve}'),
        ('firstBeforeLaunch', f'state0_{launch - 1}'), ('firstLaunched', f'state0_{launch}'),
        ('interruptedReserved', f'state1_{pending_reserve}'), ('beforeDenial', f'state2_{deny - 1}'),
        ('afterDenial', f'state2_{deny}')):
        text += f'def {name} : State := {value}\n'
    rc = cases[0]['commands'][reserve - 1]; pc = cases[1]['commands'][pending_reserve - 1]
    dc = cases[2]['commands'][deny - 1]
    for name, value in (('firstNonce', rc['nonce']), ('firstFreeze', rc['freeze']),
                        ('firstGrant', rc['grant']), ('interruptedGrant', pc['grant'])):
        text += f'def {name} : String := {string(value)}\n'
    text += 'def firstCredits : Nat := ' + _nat(rc['credits']) + '\n'
    text += 'def firstReservation : Command := .reserve firstNonce firstFreeze firstGrant firstCredits\n'
    text += (f'theorem firstReservationStep : commit provision0 provision0.binding firstBeforeReserve '
             f'(cursor firstBeforeReserve) .request firstReservation firstReserved.head firstReserved.journal '
             f'firstReserved.image = some firstReserved := step0_{reserve}\n'
             f'theorem firstLaunchStep : commit provision0 provision0.binding firstBeforeLaunch '
             f'(cursor firstBeforeLaunch) .backend (.launch firstGrant) firstLaunched.head firstLaunched.journal '
             f'firstLaunched.image = some firstLaunched := step0_{launch}\n')
    text += '''theorem main_completed_pending_accounted :
    mainFinal.completedWork.cost + (pendingUsage provision0 mainFinal.pending).cost ≤ mainFinal.reserved.cost ∧
      mainFinal.reserved.cost ≤ provision0.budget.costLimit :=
  reachable_completed_and_pending_cost provision0 state0_0.head state0_0.journal state0_0.image mainFinal main_reachable
'''
    text += ('theorem main_exact_declared_work : mainFinal.completedWork = ' +
             _usage(cases[0]['states'][-1]['completed_work']) +
             ' ∧ mainFinal.completedCount = 2 := by decide +kernel\n')
    text += '''theorem interrupted_charge_retained : interruptedFinal.reserved = interruptedReserved.reserved ∧
    0 < interruptedFinal.reserved.cost := by decide +kernel
theorem interrupted_owner_revoked : interruptedFinal.pending.map Pending.ownerEpoch = some none := by decide +kernel
theorem first_launch_consumed :
    ∃ pending, firstBeforeLaunch.pending = some pending ∧ pending.grant = firstGrant ∧
      pending.ownerEpoch = some firstBeforeLaunch.epoch ∧ pending.launched = false ∧
      firstLaunched.pending = some { pending with launched := true } ∧
      firstLaunched.reserved = firstBeforeLaunch.reserved :=
  launched_consumed provision0 provision0.binding firstBeforeLaunch firstLaunched (cursor firstBeforeLaunch)
    firstGrant firstLaunched.head firstLaunched.journal firstLaunched.image firstLaunchStep
theorem first_launch_cannot_repeat :
    commit provision0 provision0.binding firstLaunched (cursor firstLaunched) .backend (.launch firstGrant)
      "new-head" firstLaunched.journal "new-image" = none :=
  launch_not_reissued provision0 provision0.binding firstBeforeLaunch firstLaunched (cursor firstBeforeLaunch)
    firstGrant firstLaunched.head firstLaunched.journal firstLaunched.image
    "new-head" firstLaunched.journal "new-image" firstLaunchStep
'''
    text += (f'theorem aggregate_denial_no_new_charge : afterDenial.reserved = beforeDenial.reserved ∧ '
             f'afterDenial.sessionCount = beforeDenial.sessionCount ∧\n'
             f'    ¬ Fits provision2.budget (beforeDenial.reserved.add (envelope provision2.installed {dc["credits"]})) :=\n'
             f'  denied_no_reservation provision2 provision2.binding beforeDenial afterDenial (cursor beforeDenial) '
             f'{string(dc["nonce"])} {string(dc["freeze"])} {string(dc["grant"])} {dc["credits"]} '
             f'afterDenial.head afterDenial.journal afterDenial.image step2_{deny}\n')
    text += '''theorem root_copy_outside_guarantee :
    ∃ first second : State, first = firstBeforeReserve ∧ second = firstBeforeReserve ∧
      commit provision0 provision0.binding first (cursor firstBeforeReserve) .request firstReservation
        firstReserved.head firstReserved.journal firstReserved.image = some firstReserved ∧
      commit provision0 provision0.binding second (cursor firstBeforeReserve) .request firstReservation
        firstReserved.head firstReserved.journal firstReserved.image = some firstReserved :=
  identical_root_copies_accept_identically provision0 provision0.binding firstBeforeReserve firstReserved
    (cursor firstBeforeReserve) .request firstReservation firstReserved.head firstReserved.journal
    firstReserved.image firstReservationStep
end Phase17DurableCampaignExamples
'''
    return text.encode()


def render_positive():
    return ('import DurableCampaign\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(label):
    require(label in NEGATIVES, 'exact durable campaign negative required')
    tail = ' .request firstReservation firstReserved.head firstReserved.journal firstReserved.image ≠ none'
    call = 'commit provision0 provision0.binding '
    wrong = {
        'WrongCampaignProvision': call + '{ firstBeforeReserve with provision := "untrusted" } (cursor firstBeforeReserve)' + tail,
        'WrongCampaignPolicy': 'commit provision0 { provision0.binding with policy := "untrusted" } firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'WrongCampaignParent': 'commit provision0 { provision0.binding with parentPackage := "untrusted" } firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'WrongCampaignObjective': 'commit provision0 { provision0.binding with objectivePolicy := "untrusted" } firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'WrongCampaignEvaluator': 'commit provision0 { provision0.binding with evaluatorProtocol := "untrusted" } firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'WrongCampaignImplementation': 'commit provision0 { provision0.binding with implementation := "untrusted" } firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'WrongCampaignWorker': 'commit provision0 { provision0.binding with workerProtocol := "untrusted" } firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'StaleCampaignEpoch': call + 'firstBeforeReserve { cursor firstBeforeReserve with epoch := 0 }' + tail,
        'StaleCampaignSerial': call + 'firstBeforeReserve { cursor firstBeforeReserve with serial := 0 }' + tail,
        'StaleCampaignHead': call + 'firstBeforeReserve { cursor firstBeforeReserve with head := "stale" }' + tail,
        'StaleCampaignJournal': call + 'firstBeforeReserve { cursor firstBeforeReserve with journal := "stale" }' + tail,
        'StaleCampaignSnapshot': call + 'firstBeforeReserve { cursor firstBeforeReserve with image := "stale" }' + tail,
        'ReplayedCampaignNonce': call + '{ firstBeforeReserve with nonces := [firstNonce] } (cursor firstBeforeReserve)' + tail,
        'CampaignControllerMayReopen': call + 'firstBeforeReserve (cursor firstBeforeReserve) .request .reopen "new-head" firstBeforeReserve.journal "new-image" ≠ none',
        'RepeatedCampaignLaunch': call + 'firstLaunched (cursor firstLaunched) .backend (.launch firstGrant) "new-head" firstLaunched.journal "new-image" ≠ none',
        'CampaignCompletionBeforeLaunch': call + 'firstReserved (cursor firstReserved) .backend (.complete firstGrant "transcript" 0) "new-head" "new-journal" "new-image" ≠ none',
        'ReopenedCampaignOwner': 'commit provision1 provision1.binding interruptedFinal (cursor interruptedFinal) .backend (.launch interruptedGrant) "new-head" interruptedFinal.journal "new-image" ≠ none',
        'CampaignOverBudgetReservation': 'commit { provision0 with budget := ⟨Usage.zero, 0⟩ } provision0.binding firstBeforeReserve (cursor firstBeforeReserve)' + tail,
        'RefundedCampaignReservation': 'interruptedFinal.reserved.cost = 0',
        'ClonedCampaignRootImpossible': call + 'firstBeforeReserve (cursor firstBeforeReserve) .request firstReservation firstReserved.head firstReserved.journal firstReserved.image = none',
    }
    text = '''import DurableCampaign
namespace Phase17DurableCampaignControl
open Phase17DurableCampaign Phase17DurableCampaignExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    text += 'def wrongClaim : Bool := decide (' + wrong[label] + ')\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17DurableCampaignControl\n').encode()


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
        require(match is not None, 'missing or reordered durable campaign audit: ' + name)
        axioms = [] if match[1] is None else [item.strip() for item in match[1].split(',') if item.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved durable campaign audit dependency')
        audits[name] = axioms; cursor = match.end()
    require(cursor == len(stdout), 'unexpected durable campaign audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected durable campaign negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
