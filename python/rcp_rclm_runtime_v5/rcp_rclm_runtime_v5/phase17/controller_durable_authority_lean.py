"""Phase17AK durable-root certificates with exact inherited AJ transitions.

The selected root publications bind the complete paired journal snapshots to
the unchanged AJ selected witness states. Lean checks serial/epoch/cursor
semantics and the actual AJ transition composition. Root-event and paired-image
digest strings are identities checked by Python; no physical database, lock,
crypto or generic Python refinement theorem is inferred from those strings.
"""
from __future__ import annotations

import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from . import controller_witness_lean as inherited
from .materialized import require, sha
from .successor_lean import string

MODULES = (*inherited.MODULES, 'DurableAuthority')
POSITIVE = 'DurableAuthorityExamples'
NEGATIVES = (
    'WrongDurableProvision', 'WrongStoredDurableProvision', 'StaleDurableEpoch',
    'StaleDurableSerial', 'StaleDurableRootHead', 'StalePairedImage',
    'StaleDurableWitnessHead', 'StaleDurableAuthorityHead', 'UnchangedPairedPublication',
    'UnchangedRootHead', 'UnchangedPairDigest',
    'ControllerMayReopen', 'ForkedDurableCursor', 'OldLifetimeAfterReopen',
    'AcknowledgedBeforeCommit', 'WrongAcknowledgedRequest', 'OldAcknowledgementCurrent',
    'ReopenedDurableOwner', 'RefundedDurableReservation', 'JointRootRollbackImpossible',
)
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = inherited.ALLOWED_AXIOMS
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = dict(inherited.PINS)
_read = inherited._read
_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module
negative_location = inherited.negative_location

GENERIC_NAMES = tuple('Phase17DurableAuthority.' + name for name in (
    'committed_spec', 'committed_construct', 'committed_witness_exact',
    'committed_serial', 'committed_epoch', 'committed_epoch_nondecreasing',
    'committed_identity', 'committed_image', 'committed_image_fields_change', 'committed_witness_revision',
    'wrong_root_refused', 'wrong_stored_root_refused', 'stale_epoch_refused',
    'stale_cursor_refused', 'unchanged_image_refused', 'predecessor_cursor_consumed_once',
    'reopened_epoch_strict', 'reopened_old_handle_refused',
    'reopened_pending_charges_retained', 'reopened_owner_cannot_execute',
    'accepted_receipt_exact', 'wrong_request_receipt_refused', 'precommit_receipt_refused',
    'precommit_crash_retains_root', 'lost_acknowledgement_retains_root',
    'crash_retains_pending_charges', 'reachable_witness',
    'reachable_serial_matches_witness', 'reachable_epoch_bounded_by_commits',
    'reachable_sources_consumed_once', 'reachable_within_authorized_pool',
    'reachable_completed_and_pending_accounted', 'identical_root_copies_accept_identically',
))
CASE_NAMES = inherited.CASE_NAMES
SELECTED_NAMES = tuple('Phase17DurableAuthorityExamples.' + name for name in (
    *('case_' + name for name in CASE_NAMES),
    'main_exact_witness_projection', 'main_exact_reservation', 'main_actual_reference_work',
    'main_completed_and_pending_accounted', 'main_sources_consumed_once',
    'main_serial_and_epoch', 'first_committed_reservation',
    'competing_former_cursor_refused', 'reopened_former_handle_refused',
    'first_reservation_not_acknowledged_before_commit', 'first_committed_receipt_bound',
    'old_receipt_is_not_current', 'pending_reopen_retains_charge',
    'pending_reopen_cannot_execute', 'precommit_crash_keeps_pending_reservation',
    'lost_ack_keeps_committed_reservation', 'aggregate_denial_keeps_charge',
    'joint_root_rollback_is_outside_guarantee', 'root_cloning_is_outside_guarantee',
))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)
AJ = 'Phase17AuthorityWitness.'
EX = 'Phase17AuthorityWitnessExamples.'
AI = 'Phase17ControllerAuthority.'
AIEX = 'Phase17ControllerAuthorityExamples.'


def _prepared(prepared):
    from .controller_durable_capture import PreparedControllerDurableAuthority
    require(type(prepared) is PreparedControllerDurableAuthority,
            'exact prepared controller durable authority required')
    return prepared


def _same(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def _nat(value):
    require(type(value) is int and value >= 0, 'natural durable authority literal required')
    return str(value)


def _image(event):
    return '⟨' + string(event['hash']) + ', ' + string(event['after']['image_sha256']) + '⟩'


def _cursor(provision, event):
    return {'root_provision_sha256': provision, 'epoch': event['epoch'],
            'serial': event['serial'], 'root_head': event['hash'],
            'image_sha256': event['after']['image_sha256'],
            'witness_cursor': event['after']['witness_cursor']}


def _first_receipt(cases):
    """Bind receipt literals to the captured outer root envelope, not AJ's MAC.

    Exact full-wire authentication and native attribution are verified by the
    immutable Prepared packet. These checks additionally join the selected
    envelope, its request digest, and its publication to the generated theorem.
    """
    case = cases[0]; evidence = case['evidence']; events = evidence['events']
    rows = [wire for wire in case['wire']
            if wire['request']['witness_request']['body']['op'] == 'reserve' and
            wire['response']['commit_applied'] is True and wire['response']['cursor']['serial'] == 2]
    require(len(rows) == 1, 'one captured first-reservation root receipt required')
    wire = rows[0]; request = wire['request']; response = wire['response']
    pin = case['root_provision_sha256']
    before = _cursor(pin, events[1]['event']); after = _cursor(pin, events[2]['event'])
    _same(request['expected_cursor'], before, 'selected receipt does not request the first root cursor')
    _same(response['cursor'], after, 'selected receipt does not acknowledge the first committed reservation')
    require(request['root_provision_sha256'] == response['root_provision_sha256'] == pin,
            'selected receipt changed root provision')
    digest_value = digest(request)
    require(response['request_sha256'] == digest_value,
            'selected receipt does not bind the exact outer root request digest')
    last = load_json_strict(events[2]['witness_journal'].encode().splitlines()[-1])
    _same(request['witness_request'], last['body']['request'],
          'selected root receipt does not name the AJ request that produced its snapshot')
    return digest_value, response


def _receipt_literal(value):
    c = value['cursor']; w = c['witness_cursor']
    cursor = ('⟨' + ', '.join((string(c['root_provision_sha256']), _nat(c['epoch']), _nat(c['serial']),
        '⟨' + string(c['root_head']) + ', ' + string(c['image_sha256']) + '⟩', _nat(w['revision']),
        string(w['witness_head']), string(w['authority_head']))) + '⟩')
    return ('⟨' + string(value['root_provision_sha256']) + ', ' + _nat(c['epoch']) + ', ' + cursor +
            ', ' + string(value['request_sha256']) + '⟩')


def _validate_cases(prepared):
    """Recheck literal-to-byte joins before emitting any trusted proof source."""
    _prepared(prepared)
    witness = prepared.controller_witness()
    prior = witness.packet
    cases = prepared.packet['durable_cases']
    require(tuple(c['name'] for c in cases) == CASE_NAMES, 'durable case inventory differs')
    for ci, case in enumerate(cases):
        aj_case = prior['witness_cases'][ci]
        ev = case['evidence']; provision = ev['root_provision']; pid = ev['root_provision_sha256']
        require(case['ai_case_index'] == aj_case['ai_case_index'] and
                case['root_provision_sha256'] == pid == digest(provision),
                'durable case root provisioning differs')
        _same(provision['witness_provision'], aj_case['provision'], 'durable provision substituted AJ meanings')
        require(provision['witness_provision_sha256'] == aj_case['provision_sha256'],
                'durable provision substituted AJ anchor')
        full_witness = bytes.fromhex(prior['journal_images'][case['name'] + '-witness.jsonl']['hex'])
        full_authority = bytes.fromhex(prior['journal_images'][case['name'] + '-authority.jsonl']['hex'])
        witness_lines = full_witness.splitlines(keepends=True)
        authority_lines = full_authority.splitlines(keepends=True)
        authority_prefixes = {load_json_strict(line[:-1])['hash']: b''.join(authority_lines[:index + 1])
                              for index, line in enumerate(authority_lines)}
        require(len(ev['events']) == len(witness_lines) == len(aj_case['records']) + 1,
                'durable publication and AJ transition inventory differ')
        epoch = 0; previous = None
        for serial, row in enumerate(ev['events']):
            event = row['event']; after = event['after']
            wraw = row['witness_journal'].encode('utf-8'); araw = row['authority_journal'].encode('utf-8')
            require(wraw == b''.join(witness_lines[:serial + 1]),
                    'durable witness bytes are not the exact inherited AJ prefix')
            last = load_json_strict(witness_lines[serial][:-1])
            expected_witness = {'revision': serial, 'witness_head': last['hash'],
                                'authority_head': last['body']['authority_head_after']}
            _same(after['witness_cursor'], expected_witness, 'durable witness cursor differs from inherited AJ')
            require(araw == authority_prefixes[expected_witness['authority_head']],
                    'durable authority bytes are not the exact inherited AI prefix')
            pair = digest({'witness_sha256': sha(wraw), 'authority_sha256': sha(araw)})
            require(after['image_sha256'] == pair, 'durable paired-image identity differs from full bytes')
            if serial:
                record = aj_case['records'][serial - 1]
                require(event['kind'] == record['kind'], 'durable publication kind differs from AJ transition')
                epoch += int(record['kind'] == 'reopen')
                _same(event['before'], previous, 'durable publication substituted predecessor cursor')
            else:
                require(event['kind'] == 'provision' and event['before'] is None,
                        'durable genesis publication differs')
            require(event['serial'] == after['serial'] == serial and
                    event['epoch'] == after['epoch'] == epoch,
                    'durable serial or exclusive lifetime epoch differs')
            previous = _cursor(pid, event)
        _same(ev['final_cursor'], previous, 'durable final root cursor differs')
    require([len(c['evidence']['events']) - 1 for c in cases] == [7, 3, 4],
            'fixed durable transition counts differ')
    return witness, cases


def render_selected(prepared, root):
    witness, cases = _validate_cases(prepared)
    first_digest, first_receipt = _first_receipt(cases)
    _, generic = _split_imports(_read(root, 'DurableAuthority'))
    text = 'import AuthorityWitness\n' + generic
    text += '''
namespace Phase17DurableAuthorityExamples
open Phase17DurableAuthority
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    text += '-- Exact AK packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += '-- Exact inherited AJ packet SHA256: ' + sha(witness.packet_bytes) + '\n'
    text += 'def firstRequestDigest : String := ' + string(first_digest) + '\n'
    text += 'def firstNativeReceipt : Receipt := ' + _receipt_literal(first_receipt) + '\n'
    for ci, case in enumerate(cases):
        evidence = case['evidence']; ai_index = case['ai_case_index']; pid = case['root_provision_sha256']
        ctx = AIEX + 'contexts' + str(ai_index); evaluator = AIEX + 'evaluators' + str(ai_index)
        text += (f'def provision{ci} : RootProvision := '
                 f'⟨{string(pid)}, {EX}provision{ci}⟩\n')
        first = evidence['events'][0]['event']
        text += f'def image{ci}_0 : Image := {_image(first)}\n'
        text += f'def root{ci}_0 : RootState := initialRoot provision{ci} {EX}journal{ci} image{ci}_0\n'
        text += (f'theorem reachable{ci}_0 : Reachable provision{ci} {ctx} {evaluator} '
                 f'{EX}journal{ci} image{ci}_0 root{ci}_0 := .initial\n')
        for serial, row in enumerate(evidence['events'][1:], start=1):
            event = row['event']; prior = f'root{ci}_{serial - 1}'; following = f'root{ci}_{serial}'
            mode = '.reopen' if event['kind'] == 'reopen' else '.mutation'
            image = f'image{ci}_{serial}'; aj_next = EX + f'witness{ci}_{serial}'
            request = EX + f'request{ci}_{serial}'
            text += (f'-- Exact retained witness SHA256: {sha(row["witness_journal"].encode())}\n'
                     f'-- Exact retained authority SHA256: {sha(row["authority_journal"].encode())}\n')
            text += f'def {image} : Image := {_image(event)}\n'
            text += f'def {following} : RootState := installed {prior} {mode} {image} {aj_next}\n'
            text += (f'theorem guard{ci}_{serial} : RootGuard provision{ci} {prior} '
                     f'(handle {prior}) (cursor {prior}) {mode} {request} {image} :=\n'
                     '  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,\n'
                     '    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩\n')
            text += (f'theorem step{ci}_{serial} : commit provision{ci} {ctx} {evaluator} '
                     f'{prior} (handle {prior}) (cursor {prior}) {mode} {request}\n'
                     f'    {aj_next}.head {aj_next}.journal {image} = some {following} :=\n'
                     f'  committed_construct provision{ci} {ctx} {evaluator} {prior} '
                     f'(handle {prior}) (cursor {prior}) {mode} {request}\n'
                     f'    {aj_next}.head {aj_next}.journal {image} {aj_next} '
                     f'guard{ci}_{serial} {EX}step{ci}_{serial}\n')
            text += (f'theorem reachable{ci}_{serial} : Reachable provision{ci} {ctx} {evaluator}\n'
                     f'    {EX}journal{ci} image{ci}_0 {following} :=\n'
                     f'  .commit reachable{ci}_{serial - 1} (handle {prior}) (cursor {prior}) '
                     f'{mode} {request} {aj_next}.head {aj_next}.journal {image} step{ci}_{serial}\n')
        serial = len(evidence['events']) - 1; final = f'root{ci}_{serial}'; epoch = evidence['final_cursor']['epoch']
        text += (f'theorem case_{case["name"]} : Reachable provision{ci} {ctx} {evaluator}\n'
                 f'    {EX}journal{ci} image{ci}_0 {final} ∧ {final}.serial = {_nat(serial)} ∧\n'
                 f'    {final}.epoch = {_nat(epoch)} ∧ {final}.witness = {EX}witness{ci}_{serial} :=\n'
                 f'  ⟨reachable{ci}_{serial}, rfl, rfl, rfl⟩\n')
    text += _selected_tail()
    return text.encode('utf-8')


def _selected_tail():
    return '''
theorem main_exact_witness_projection : root0_7.witness = Phase17AuthorityWitnessExamples.witness0_7 := rfl

theorem main_exact_reservation : Phase17ControllerAuthority.reservedCost root0_7.witness.authority = 7168 :=
  Phase17AuthorityWitnessExamples.main_exact_reservation.2

theorem main_actual_reference_work : Phase17ControllerAuthority.completedCost root0_7.witness.authority = 1008 :=
  Phase17AuthorityWitnessExamples.main_actual_reference_work

theorem main_completed_and_pending_accounted :
    Phase17ControllerAuthority.completedCost root0_7.witness.authority +
      Phase17ControllerAuthority.pendingCost provision0.witness.policy root0_7.witness.authority ≤
      Phase17ControllerAuthority.reservedCost root0_7.witness.authority :=
  reachable_completed_and_pending_accounted provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 Phase17AuthorityWitnessExamples.journal0 image0_0 root0_7 reachable0_7

theorem main_sources_consumed_once : root0_7.witness.authority.consumed.Nodup :=
  reachable_sources_consumed_once provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 Phase17AuthorityWitnessExamples.journal0 image0_0 root0_7 reachable0_7

theorem main_serial_and_epoch : root0_7.serial = 7 ∧ root0_7.epoch = 2 := ⟨rfl, rfl⟩

theorem first_committed_reservation :
    Phase17AuthorityWitness.advance provision0.witness Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 root0_1.witness
      Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal =
      some root0_2.witness := Phase17AuthorityWitnessExamples.step0_2

theorem competing_former_cursor_refused :
    commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      root0_2 (handle root0_2) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
      "competing-head" "competing-journal" ⟨"competing-root", "competing-pair"⟩ = none := by
  apply stale_cursor_refused
  decide +kernel

theorem reopened_former_handle_refused :
    commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      root0_4 (handle root0_3) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5
      root0_5.witness.head root0_5.witness.journal image0_5 = none := by
  apply stale_epoch_refused
  decide +kernel

theorem first_reservation_not_acknowledged_before_commit :
    ¬ ReceiptAccepted root0_1 firstRequestDigest firstNativeReceipt :=
  precommit_receipt_refused provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 root0_1 root0_2 (handle root0_1) (cursor root0_1)
    .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal
    firstRequestDigest image0_2 step0_2

theorem first_committed_receipt_bound :
    ReceiptAccepted root0_2 firstRequestDigest firstNativeReceipt :=
  ⟨by decide +kernel, rfl⟩

theorem old_receipt_is_not_current :
    ¬ ReceiptAccepted root0_3 firstRequestDigest firstNativeReceipt := by
  decide +kernel

theorem pending_reopen_retains_charge :
    root1_3.witness.authority.pending = some Phase17ControllerAuthorityExamples.lease4_0 ∧
    Phase17ControllerAuthority.reservedCost root1_3.witness.authority = 3584 ∧
    root1_3.witness.owner = none ∧ root1_3.epoch = 2 := by decide +kernel

theorem pending_reopen_cannot_execute (owner : String) (result : Phase17ControllerAuthority.Completion) :
    Phase17AuthorityWitness.perform provision1.witness Phase17ControllerAuthorityExamples.contexts4
      Phase17ControllerAuthorityExamples.evaluators4 root1_3.witness (.execute owner result) = none :=
  Phase17AuthorityWitnessExamples.pending_reopen_cannot_execute owner result

theorem precommit_crash_keeps_pending_reservation :
    (crash (begin root1_2 root1_3)).durable = root1_2 ∧
    Phase17ControllerAuthority.reservedCost (crash (begin root1_2 root1_3)).durable.witness.authority = 3584 :=
  ⟨rfl, by decide +kernel⟩

theorem lost_ack_keeps_committed_reservation :
    (crash (afterCommit root1_2)).durable = root1_2 ∧
    Phase17ControllerAuthority.reservedCost (crash (afterCommit root1_2)).durable.witness.authority = 3584 :=
  ⟨rfl, by decide +kernel⟩

theorem aggregate_denial_keeps_charge :
    Phase17ControllerAuthority.reservedCost root2_4.witness.authority = 3584 ∧
    root2_4.witness.authority.halted = true ∧ root2_4.epoch = 1 := by decide +kernel

theorem joint_root_rollback_is_outside_guarantee :
    commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      root0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
      root0_2.witness.head root0_2.witness.journal image0_2 ≠ none := by
  have accepted : commit provision0 Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 root0_1 (handle root0_1) (cursor root0_1)
      .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head
      root0_2.witness.journal image0_2 = some root0_2 := step0_2
  rw [accepted]
  exact Option.some_ne_none _

theorem root_cloning_is_outside_guarantee :
    ∃ first second : RootState, first = root0_1 ∧ second = root0_1 ∧
      commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
        first (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
        root0_2.witness.head root0_2.witness.journal image0_2 = some root0_2 ∧
      commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
        second (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
        root0_2.witness.head root0_2.witness.journal image0_2 = some root0_2 :=
  identical_root_copies_accept_identically provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 root0_1 root0_2 (handle root0_1) (cursor root0_1)
    .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal image0_2 step0_2

end Phase17DurableAuthorityExamples
'''


def render_positive(prepared):
    _prepared(prepared)
    return ('import DurableAuthority\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(prepared, label):
    _prepared(prepared)
    require(label in NEGATIVES, 'exact durable-authority negative required')
    call = 'commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 '
    request = EX + 'request0_2'
    tail = ' .mutation ' + request + ' root0_2.witness.head root0_2.witness.journal image0_2 ≠ none'
    direct = {
        'WrongDurableProvision': call + 'root0_1 { handle root0_1 with identity := "untrusted" } (cursor root0_1)' + tail,
        'WrongStoredDurableProvision': call + '{ root0_1 with identity := "untrusted" } (handle root0_1) (cursor root0_1)' + tail,
        'StaleDurableEpoch': call + 'root0_1 { handle root0_1 with epoch := 0 } (cursor root0_1)' + tail,
        'StaleDurableSerial': call + 'root0_1 (handle root0_1) { cursor root0_1 with serial := 0 }' + tail,
        'StaleDurableRootHead': call + 'root0_1 (handle root0_1) { cursor root0_1 with image := ⟨"stale-root", image0_1.pair⟩ }' + tail,
        'StalePairedImage': call + 'root0_1 (handle root0_1) { cursor root0_1 with image := ⟨image0_1.rootHead, "stale-pair"⟩ }' + tail,
        'StaleDurableWitnessHead': call + 'root0_1 (handle root0_1) { cursor root0_1 with head := "stale-witness" }' + tail,
        'StaleDurableAuthorityHead': call + 'root0_1 (handle root0_1) { cursor root0_1 with journal := "stale-authority" }' + tail,
        'UnchangedPairedPublication': call + 'root0_1 (handle root0_1) (cursor root0_1) .mutation ' + request +
            ' root0_2.witness.head root0_2.witness.journal image0_1 ≠ none',
        'UnchangedRootHead': call + 'root0_1 (handle root0_1) (cursor root0_1) .mutation ' + request +
            ' root0_2.witness.head root0_2.witness.journal ⟨image0_1.rootHead, image0_2.pair⟩ ≠ none',
        'UnchangedPairDigest': call + 'root0_1 (handle root0_1) (cursor root0_1) .mutation ' + request +
            ' root0_2.witness.head root0_2.witness.journal ⟨image0_2.rootHead, image0_1.pair⟩ ≠ none',
        'ControllerMayReopen': call + 'root0_0 (handle root0_0) (cursor root0_0) .mutation ' + EX +
            'request0_1 root0_1.witness.head root0_1.witness.journal image0_1 ≠ none',
        'ForkedDurableCursor': call + 'root0_2 (handle root0_2) (cursor root0_1)' + tail,
        'OldLifetimeAfterReopen': call + 'root0_4 (handle root0_3) (cursor root0_4) .mutation ' + EX +
            'request0_5 root0_5.witness.head root0_5.witness.journal image0_5 ≠ none',
        'AcknowledgedBeforeCommit': 'ReceiptAccepted root0_1 firstRequestDigest firstNativeReceipt',
        'WrongAcknowledgedRequest': 'ReceiptAccepted root0_2 "other-request" firstNativeReceipt',
        'OldAcknowledgementCurrent': 'ReceiptAccepted root0_3 firstRequestDigest firstNativeReceipt',
        'ReopenedDurableOwner': AJ + 'perform provision1.witness ' + AIEX + 'contexts4 ' + AIEX +
            'evaluators4 root1_3.witness (.execute "owner" ' + AIEX + 'completion0_0) ≠ none',
        'RefundedDurableReservation': AI + 'reservedCost root1_3.witness.authority = 0',
        'JointRootRollbackImpossible': call + 'root0_1 (handle root0_1) (cursor root0_1) .mutation ' + request +
            ' root0_2.witness.head root0_2.witness.journal image0_2 = none',
    }
    prefix = '''import DurableAuthority
namespace Phase17DurableAuthorityControl
open Phase17DurableAuthority Phase17DurableAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    proof = ('by\n  simp only [wrongClaim, joint_root_rollback_is_outside_guarantee, decide_false]'
             if label == 'JointRootRollbackImpossible' else 'by decide +kernel')
    text = prefix + 'def wrongClaim : Bool := decide (' + direct[label] + ')\n'
    text += 'theorem actual_rejection : wrongClaim = false := ' + proof + '\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17DurableAuthorityControl\n').encode()


def sources(prepared, root):
    _prepared(prepared)
    prior = inherited.sources(prepared.controller_witness(), root)
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
        require(match is not None, 'missing or reordered durable authority audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved durable authority audit dependency')
        audits[name] = axioms; cursor = match.end()
    require(cursor == len(stdout), 'unexpected durable authority audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected durable authority negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
