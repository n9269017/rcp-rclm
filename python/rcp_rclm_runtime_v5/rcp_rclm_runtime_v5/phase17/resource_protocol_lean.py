"""Generate kernel-checked, per-event resource-journal replay certificates.

The retained Z generator is invoked once. Its twelve-module extension preserves
all earlier source bytes, including the single guarded W proof refactoring.
Journal and work digest computation remains outside the new Lean statement.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import evaluation_trace_lean as previous
from .captured_json_lean import _raw_image
from .materialized import require, sha
from .resource_protocol import PreparedResourceProtocol, Z_SOURCE_SHA, validate_packet
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ResourceProtocol.lean'
BRIDGE_SHA256 = '174505cec65f20cc02c76680da543886edcc707d393bb2c893c5a9e14b076e0f'
DEPENDENCY_LABELS = (*previous.DEPENDENCY_LABELS, 'Phase17ZDependency')
AUXILIARY_LABELS = previous.AUXILIARY_LABELS
COMPILED_MODULES = (*previous.COMPILED_MODULES, 'Phase17ZDependency')
Z_DEPENDENCY_SHA256 = '019ae5470de1422af1a5680d27d7d611f63218020514f10045b8585fe7502467'
NAMES = tuple('Phase17ResourceProtocol.' + name for name in (
    'reserve_charges_before_result', 'result_never_refunds', 'result_requires_pending',
    'terminal_state_rejects_events', 'step_counters_sound', 'replay_counters_sound',
    'replay_spending_monotone', 'replay_within_policy', 'sealed_has_no_pending',
    'selected_event_decodings', 'selected_success_replay', 'selected_failed_replay',
    'selected_exhausted_replay', 'selected_interrupted_replay',
    'selected_header_and_scope_binding', 'selected_work_schedule_binding',
    'selected_result_binding', 'selected_counters_and_budget',
    'selected_failure_no_refund', 'selected_learned_acceptance_bound',
))
LABELS = ('ResourceProtocol', 'WrongHeaderBinding', 'WrongPolicyWeights',
          'WrongEventIndex', 'WrongPreviousHash', 'DuplicateOperation',
          'WrongTariff', 'WrongSpentAfter', 'OverBudgetReservation',
          'DimensionOverrun', 'ResultWithoutReservation', 'WrongReservationHash',
          'WrongResultShape', 'ResumeAfterFailure', 'SealPending', 'WrongWorkOrder',
          'MissingWork', 'WrongInputDigest', 'WrongOutputDigest', 'RefundFailedResult',
          'FalseExhaustion', 'ArithmeticOverflow', 'WrongFinalHead')
FORBIDDEN = previous.FORBIDDEN


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked resource protocol template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'resource protocol template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = previous.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _list(items) -> str:
    return '[' + ', '.join(items) + ']'


def _definition(name: str, typ: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + typ + ' := ' + value + '\n'


def _packed_image(raw: bytes, *, line: bool = False) -> str:
    """An exact AA-local byte image stored as one bounded little-endian Nat.

    The count preserves leading zero bytes when the storage integer is read
    most-significant-first. Hex literals avoid Python's decimal digit ceiling
    for a permitted 4096-byte image. This storage integer is not a journal
    field: all protocol integers retain their separate 63-bit bounds. An
    independent repeated mod/div readback checks the emitted literal.
    """
    require(type(raw) is bytes and type(line) is bool and
            0 < len(raw) <= (4097 if line else 4096), 'bounded exact ASCII image required')
    printable = raw[:-1] if line else raw
    require(printable and all(32 <= byte <= 126 for byte in printable) and
            (not line or raw.endswith(b'\n')), 'printable ASCII image or single-LF line required')
    literal = '0x' + format(int.from_bytes(raw, 'little'), 'x')
    remaining = int(literal, 16)
    decoded = []
    for _ in raw:
        decoded.append(remaining % 256)
        remaining //= 256
    require(remaining == 0 and bytes(decoded) == raw, 'packed proof literal round-trip differs')
    return 'bytesLE ' + str(len(raw)) + ' ' + literal


def _usage(values: list[int]) -> str:
    require(type(values) is list and len(values) == 4 and all(type(n) is int for n in values),
            'exact four-dimensional usage required')
    return '⟨' + ', '.join(map(str, values)) + '⟩'


def _policy(value: dict) -> str:
    return '⟨' + _usage(value['limits']) + ', ' + str(value['cost_limit']) + '⟩'


def _binding(value: dict) -> str:
    return '⟨' + ', '.join(string(value[k]) for k in (
        'predecessor_package_hash', 'candidate_package_hash', 'transcript_sha256',
        'fixed_verifier_hash')) + '⟩'


def _optional(value: str | None) -> str:
    return 'none' if value is None else '(some ' + string(value) + ')'


def _operation(body: dict) -> str:
    return '⟨.' + body['operation'] + ', ' + string(body['operation_id']) + ', ' + \
        string(body['input_sha256']) + ', ' + _usage(body['charge']) + '⟩'


def _body(value: dict) -> str:
    kind = value['kind']
    if kind == 'open':
        return '.open (' + _binding(value['binding']) + ') (' + _policy(value['policy']) + ')'
    if kind == 'reserve':
        return '.reserve (' + _operation(value) + ') (' + _usage(value['spent_after']) + ')'
    if kind == 'exhausted':
        return '.exhausted (' + _operation(value) + ') ' + string(value['reason'])
    if kind == 'result':
        return '.result ' + string(value['reservation_hash']) + ' ' + \
            ('true' if value['ok'] else 'false') + ' ' + _optional(value['result_sha256']) + \
            ' ' + _optional(value['error_code']) + ' ' + str(value['elapsed_ns'])
    require(kind in ('seal', 'stop'), 'known typed event required')
    return '.' + kind


def _event(value: dict) -> str:
    return '⟨' + str(value['index']) + ', ' + string(value['previous']) + ', ' + \
        string(value['hash']) + ', (' + _body(value['body']) + ')⟩'


def _state(value: dict) -> str:
    status = {'new': 'new', 'open': 'open', 'pending': 'pending', 'sealed': 'sealed',
              'resource_exhausted': 'resourceExhausted', 'safety_halt': 'safetyHalt',
              'external_stop': 'externalStop'}[value['status']]
    return '⟨' + string(value['head']) + ', ' + str(value['event_count']) + ', ' + \
        _usage(value['spent']) + ', .' + status + ', ' + _optional(value['pending_hash']) + \
        ', ' + _list(map(string, value['operation_ids'])) + ', ' + \
        _list('.' + k for k in value['charges']) + '⟩'


def _forall2(proofs: list[str]) -> str:
    return ''.join('List.Forall₂.cons ' + proof + ' (' for proof in proofs) + \
        'List.Forall₂.nil' + ')' * len(proofs)


def _runs(proofs: list[str], final: str) -> str:
    return ''.join('Runs.cons ' + proof + ' (' for proof in proofs) + \
        'Runs.nil ' + final + ')' * len(proofs)


def _definitions(packet: dict, *, include_images: bool) -> str:
    text = '''noncomputable def selectedBinding : Binding :=
  ⟨Phase17Finite.selectedEvidence.parentPackage,
    Phase17Finite.selectedEvidence.candidatePackage,
    Phase17Finite.selectedEvidence.transcriptHash, Phase17Finite.selectedEvidence.root⟩
'''
    for journal in packet['protocol']['journals']:
        name = journal['name']
        text += _definition(name + 'Policy', 'Policy', _policy(journal['policy']))
        text += _definition(name + 'ExpectedHead', 'String', string(journal['expected_head']))
        text += _definition(name + 'State0', 'State', 'initial')
        for index, (event, state) in enumerate(zip(journal['events'], journal['states'], strict=True)):
            text += _definition(name + 'Event' + str(index), 'Event', _event(event))
            text += _definition(name + 'State' + str(index + 1), 'State', _state(state))
        count = len(journal['events'])
        text += _definition(name + 'Events', 'List Event',
                            _list(name + 'Event' + str(i) for i in range(count)))
        text += _definition(name + 'Final', 'State', name + 'State' + str(count))
        if include_images:
            lines = bytes.fromhex(journal['raw_hex']).splitlines(keepends=True)
            require(len(lines) == count and all(line.endswith(b'\n') for line in lines),
                    'exact full journal framing required')
            for index, (image, line) in enumerate(zip(journal['event_images'], lines, strict=True)):
                raw = bytes.fromhex(image)
                require(line == raw + b'\n', 'complete event image/LF framing differs')
                text += _definition(name + 'Image' + str(index), 'List Nat', _packed_image(raw))
                text += _definition(name + 'Line' + str(index), 'List Nat', _packed_image(line, line=True))
            text += _definition(name + 'Images', 'List (List Nat)',
                                _list(name + 'Image' + str(i) for i in range(count)))
            text += _definition(name + 'Lines', 'List (List Nat)',
                                _list(name + 'Line' + str(i) for i in range(count)))
            text += _definition(name + 'LineLengths', 'List Nat', _list(str(len(line)) for line in lines))
            text += _definition(name + 'Raw', 'List Nat', name + 'Lines.flatten')
    pairs = []
    for index, work in enumerate(packet['protocol']['work']):
        imported = 'Phase17Evaluation.workImage' + str(index)
        text += _definition('workReference' + str(index), 'WorkReference',
            '⟨' + imported + '.identity, ' + imported + '.kind, ' + imported + '.inputImage, ' +
            imported + '.outputImage, ' + string(work['input_sha256']) + ', ' +
            string(work['output_sha256']) + '⟩')
        pairs.append('(successEvent' + str(1 + 2 * index) + ', successEvent' + str(2 + 2 * index) + ')')
    text += _definition('selectedWorkReferences', 'List WorkReference',
                        _list('workReference' + str(i) for i in range(len(pairs))))
    text += _definition('selectedPairs', 'List (Event × Event)', _list(pairs))
    text += '''abbrev ImportedImageBound (reference : WorkReference)
    (image : Phase17Evaluation.WorkImage) : Prop :=
  reference.identity = image.identity ∧ reference.kind = image.kind ∧
  reference.inputImage = image.inputImage ∧ reference.outputImage = image.outputImage
'''
    return text


def _journal_proofs(journal: dict) -> str:
    name, count = journal['name'], len(journal['events'])
    text = ''
    for index in range(count):
        suffix = str(index)
        text += ('theorem ' + name + '_decode' + suffix + ' : EventImageChecked ' +
                 name + 'Image' + suffix + ' ' + name + 'Event' + suffix + ' := by decide +kernel\n')
        text += ('theorem ' + name + '_line' + suffix + ' : ' + name + 'Line' + suffix +
                 ' = ' + name + 'Image' + suffix + ' ++ [10] := by decide +kernel\n')
        line_length = len(bytes.fromhex(journal['event_images'][index])) + 1
        text += ('theorem ' + name + '_line_length' + suffix + ' : ' + name + 'Line' + suffix +
                 '.length = ' + str(line_length) + ' := by decide +kernel\n')
        text += ('theorem ' + name + '_step' + suffix + ' : Step selectedBinding ' + name +
                 'Policy ' + name + 'State' + suffix + ' ' + name + 'Event' + suffix + ' ' +
                 name + 'State' + str(index + 1) + ' := by\n' +
                 '  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, rfl⟩ <;> decide +kernel\n')
    text += ('theorem ' + name + '_decoded : List.Forall₂ EventImageChecked ' + name +
             'Images ' + name + 'Events :=\n  ' +
             _forall2([name + '_decode' + str(i) for i in range(count)]) + '\n')
    text += ('theorem ' + name + '_framed : ' + name + 'Raw = framed ' + name + 'Images :=\n' +
             '  framed_of_lines (lines := ' + name + 'Lines) (images := ' + name + 'Images) (' +
             _forall2([name + '_line' + str(i) for i in range(count)]) + ')\n')
    text += ('theorem ' + name + '_runs : Runs selectedBinding ' + name + 'Policy initial ' +
             name + 'Events ' + name + 'Final :=\n  ' +
             _runs([name + '_step' + str(i) for i in range(count)], name + 'Final') + '\n')
    size = len(bytes.fromhex(journal['raw_hex']))
    text += ('theorem ' + name + '_raw_bounds : ' + name + 'Raw.length = ' + str(size) +
             ' ∧ 0 < ' + name + 'Raw.length ∧ ' + name + 'Raw.length ≤ 4194304 := by\n' +
             '  have length_eq : ' + name + 'Raw.length = ' + name + 'LineLengths.sum :=\n' +
             '    flatten_length_of_lines (lines := ' + name + 'Lines) (lengths := ' + name + 'LineLengths) (' +
             _forall2([name + '_line_length' + str(i) for i in range(count)]) + ')\n' +
             '  refine ⟨length_eq.trans (by decide +kernel), ?_⟩\n' +
             '  rw [length_eq]\n  decide +kernel\n')
    text += ('theorem ' + name + '_journal : JournalChecked selectedBinding ' + name +
             'Policy ' + name + 'Raw ' + name + 'Images ' + name + 'Events ' + name +
             'ExpectedHead ' + name + 'Final :=\n' +
             '  ⟨' + name + '_raw_bounds.2.1, ' + name + '_raw_bounds.2.2, ' + name + '_framed, ' +
             name + '_decoded, ' + name + '_runs, by decide +kernel⟩\n')
    return text


def _positive(packet: dict) -> str:
    text = '''def bytesLE (count packed : Nat) : List Nat :=
  match count with
  | 0 => []
  | n + 1 => (packed % 256) :: bytesLE n (packed / 256)
termination_by structural count

'''
    text += _definitions(packet, include_images=True)
    for journal in packet['protocol']['journals']:
        text += _journal_proofs(journal)
    for index in range(len(packet['protocol']['work'])):
        suffix = str(index)
        text += ('theorem imported_image' + suffix + ' : ImportedImageBound workReference' + suffix +
                 ' Phase17Evaluation.workImage' + suffix + ' := ⟨rfl, rfl, rfl, rfl⟩\n')
        text += ('theorem result_binding' + suffix + ' : WorkBound workReference' + suffix +
                 ' (successEvent' + str(1 + 2 * index) + ', successEvent' + str(2 + 2 * index) +
                 ') := by decide +kernel\n')
    text += '''theorem selected_event_decodings :
    List.Forall₂ EventImageChecked successImages successEvents ∧
    List.Forall₂ EventImageChecked failedImages failedEvents ∧
    List.Forall₂ EventImageChecked exhaustedImages exhaustedEvents ∧
    List.Forall₂ EventImageChecked interruptedImages interruptedEvents ∧
    successRaw = framed successImages ∧ failedRaw = framed failedImages ∧
    exhaustedRaw = framed exhaustedImages ∧ interruptedRaw = framed interruptedImages ∧
    successRaw.length = 120790 ∧ failedRaw.length = 1541 ∧
    exhaustedRaw.length = 1186 ∧ interruptedRaw.length = 1533 ∧
    successEvents.length = 308 ∧ failedEvents.length = 3 ∧
    exhaustedEvents.length = 2 ∧ interruptedEvents.length = 3 := by
  exact ⟨success_decoded, failed_decoded, exhausted_decoded, interrupted_decoded,
    success_framed, failed_framed, exhausted_framed, interrupted_framed,
    success_raw_bounds.1, failed_raw_bounds.1, exhausted_raw_bounds.1,
    interrupted_raw_bounds.1, by decide +kernel⟩

theorem selected_success_replay :
    JournalChecked selectedBinding successPolicy successRaw successImages successEvents
      successExpectedHead successFinal ∧ successFinal.status = .sealed ∧
    successFinal.pending = none := ⟨success_journal, by decide +kernel⟩

theorem selected_failed_replay :
    JournalChecked selectedBinding failedPolicy failedRaw failedImages failedEvents
      failedExpectedHead failedFinal ∧ failedFinal.status = .safetyHalt ∧
    failedFinal.pending = none := ⟨failed_journal, by decide +kernel⟩

theorem selected_exhausted_replay :
    JournalChecked selectedBinding exhaustedPolicy exhaustedRaw exhaustedImages exhaustedEvents
      exhaustedExpectedHead exhaustedFinal ∧ exhaustedFinal.status = .resourceExhausted ∧
    exhaustedFinal.pending = none := ⟨exhausted_journal, by decide +kernel⟩

theorem selected_interrupted_replay :
    JournalChecked selectedBinding interruptedPolicy interruptedRaw interruptedImages interruptedEvents
      interruptedExpectedHead interruptedFinal ∧ interruptedFinal.status = .safetyHalt ∧
    interruptedFinal.pending = none := ⟨interrupted_journal, by decide +kernel⟩

theorem selected_header_and_scope_binding :
    selectedBinding.predecessor = Phase17Finite.selectedEvidence.parentPackage ∧
    selectedBinding.candidate = Phase17Finite.selectedEvidence.candidatePackage ∧
    selectedBinding.transcript = Phase17Finite.selectedEvidence.transcriptHash ∧
    selectedBinding.verifier = Phase17Finite.selectedEvidence.root ∧
    selectedBinding.predecessor = Phase17Finite.selectedCandidate.update.parentPackage ∧
    selectedBinding.candidate = Phase17Finite.selectedCandidate.update.candidatePackage ∧
    successEvent0.body = .open selectedBinding successPolicy ∧
    failedEvent0.body = .open selectedBinding failedPolicy ∧
    exhaustedEvent0.body = .open selectedBinding exhaustedPolicy ∧
    interruptedEvent0.body = .open selectedBinding interruptedPolicy ∧
    successPolicy.limits.candidates = Phase17Finite.selectedPolicy.limits 0 ∧
    successPolicy.limits.vectors = Phase17Finite.selectedPolicy.limits 1 ∧
    successPolicy.limits.inputs = Phase17Finite.selectedPolicy.limits 2 ∧
    successPolicy.limits.outputs = Phase17Finite.selectedPolicy.limits 3 ∧
    successPolicy.costLimit = Phase17Finite.selectedPolicy.costLimit := by decide +kernel

theorem selected_work_schedule_binding :
    List.Forall₂ ImportedImageBound selectedWorkReferences Phase17Evaluation.workImages ∧
    successEvents = successEvent0 :: (pairEvents selectedPairs ++ [successEvent307]) ∧
    selectedWorkReferences.length = 153 ∧
    selectedWorkReferences.map WorkReference.kind = Phase17Finite.selectedEvidence.charges ∧
    selectedWorkReferences.map WorkReference.identity =
      Phase17Evaluation.workImages.map Phase17Evaluation.WorkImage.identity ∧
    (selectedWorkReferences.map WorkReference.identity).Nodup := by
  refine ⟨'''
    text += _forall2(['imported_image' + str(i) for i in range(153)])
    text += ''', rfl, by decide +kernel, by decide +kernel, rfl, ?_⟩
  decide +kernel

theorem selected_result_binding : List.Forall₂ WorkBound selectedWorkReferences selectedPairs :=
  ''' + _forall2(['result_binding' + str(i) for i in range(153)]) + '''

theorem selected_counters_and_budget :
    CountersSound successFinal ∧ successPolicy.Fits successFinal.spent ∧
    successFinal.charges = Phase17Finite.selectedEvidence.charges ∧
    successFinal.spent = tally Phase17Finite.selectedTrace ∧
    successFinal.spent.cost = Phase17Resource.totalCost Phase17Finite.selectedTrace ∧
    Phase17Resource.Fits Phase17Finite.selectedPolicy successFinal.charges ∧
    successFinal.spent = ⟨9, 144, 576, 576⟩ ∧ successFinal.spent.cost = 4032 := by
  refine ⟨replay_counters_sound (by decide +kernel) success_runs,
    replay_within_policy (by decide +kernel) success_runs, ?_⟩
  unfold Phase17Resource.Fits
  decide +kernel

theorem selected_failure_no_refund :
    failedFinal.spent = failedState2.spent ∧ failedFinal.charges = failedState2.charges ∧
    failedFinal.operationIds = failedState2.operationIds ∧
    interruptedFinal.spent = interruptedState2.spent ∧
    interruptedFinal.charges = interruptedState2.charges ∧
    interruptedFinal.operationIds = interruptedState2.operationIds ∧
    failedFinal.spent = ⟨0, 1, 4, 4⟩ ∧ interruptedFinal.spent = ⟨0, 1, 4, 4⟩ ∧
    failedFinal.spent.cost = 24 ∧ interruptedFinal.spent.cost = 24 ∧
    exhaustedFinal.spent = Usage.zero ∧ exhaustedFinal.charges = [] ∧
    exhaustedFinal.operationIds = [] := by
  have failure := result_never_refunds (e := failedEvent2) (by rfl) failed_step2
  have interruption := result_never_refunds (e := interruptedEvent2) (by rfl) interrupted_step2
  exact ⟨failure.1, failure.2.1, failure.2.2,
    interruption.1, interruption.2.1, interruption.2.2, by decide +kernel⟩

theorem selected_learned_acceptance_bound :
    JournalChecked selectedBinding successPolicy successRaw successImages successEvents
      successExpectedHead successFinal ∧
    List.Forall₂ ImportedImageBound selectedWorkReferences Phase17Evaluation.workImages ∧
    List.Forall₂ WorkBound selectedWorkReferences selectedPairs ∧
    successFinal.charges = Phase17Finite.selectedEvidence.charges ∧
    Phase17Sha256.AllHashed Phase17Objective.allRecords ∧
    Phase17Sha256.AllHashed Phase17Sha256.selectedRecords ∧
    (Phase17Preimages.hashInput
      (Phase17Objective.challengeValue Phase17Objective.selectedView
        Phase17Objective.record17.digest Phase17Objective.record18.digest
        Phase17Objective.credits (Phase17Objective.openingValue Phase17Evaluation.opening))).bind
      Phase17Sha256.sha256 = some Phase17Joint.producerBinding.challenge ∧
    Phase17Evaluation.PrefixBound Phase17Evaluation.opening Phase17Evaluation.inherited
      Phase17Evaluation.candidates Phase17Finite.selectedConfiguration.context
      Phase17Finite.selectedEvidence.proposal ∧
    List.Forall₂ Phase17Evaluation.WorkChecked Phase17Evaluation.workImages
      Phase17Evaluation.selectedWorkViews ∧
    Phase17Evaluation.selectedWorkViews.map Phase17Evaluation.WorkView.kind =
      Phase17Finite.selectedEvidence.charges ∧
    Phase17TaskMeaning.catalog 21 = Phase17TaskMeaning.vectorMeaning
      (Phase17Objective.openingContract Phase17Evaluation.opening) ∧
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  exact ⟨selected_success_replay.1, selected_work_schedule_binding.1,
    selected_result_binding, selected_counters_and_budget.2.2.1,
    Phase17Evaluation.selected_learned_acceptance_bound⟩
'''
    return text


def _controls(packet: dict, label: str) -> tuple[str, str]:
    require(label in LABELS[1:], 'known resource protocol control required')
    text = _definitions(packet, include_images=False)
    journals = {row['name']: row for row in packet['protocol']['journals']}
    first = journals['success']['events'][1]['body']
    first_op = _operation(first)
    text += _definition('firstOperation', 'Operation', first_op)
    step = lambda state, event, policy='successPolicy', binding='selectedBinding': (
        'Step ' + binding + ' ' + policy + ' ' + state + ' ' + event +
        ' (next ' + state + ' ' + event + ')')
    preconditions = ['Step selectedBinding successPolicy successState1 successEvent1 successState2']
    if label == 'WrongHeaderBinding':
        text += _definition('alteredBinding', 'Binding',
                            '{ selectedBinding with predecessor := zeroHead }')
        preconditions += ['alteredBinding.Valid', 'alteredBinding ≠ selectedBinding']
        proposition = step('initial', 'successEvent0', binding='alteredBinding')
    elif label == 'WrongPolicyWeights':
        raw = bytes.fromhex(journals['success']['event_images'][0])
        old, new = b'"weights":[64,16,1,1]', b'"weights":[65,16,1,1]'
        require(raw.count(old) == 1, 'unique actual policy-weight control anchor required')
        text += _definition('originalHeaderImage', 'List Nat', _raw_image(raw))
        text += _definition('alteredHeaderImage', 'List Nat', _raw_image(raw.replace(old, new, 1)))
        preconditions += ['EventImageChecked originalHeaderImage successEvent0',
                          'Phase17Json.decode alteredHeaderImage ≠ none',
                          'alteredHeaderImage ≠ originalHeaderImage']
        proposition = 'EventImageChecked alteredHeaderImage successEvent0'
    elif label == 'WrongEventIndex':
        text += _definition('alteredEvent', 'Event', '{ successEvent1 with index := 2 }')
        preconditions += ['alteredEvent.previous = successState1.head']
        proposition = step('successState1', 'alteredEvent')
    elif label == 'WrongPreviousHash':
        text += _definition('alteredEvent', 'Event', '{ successEvent1 with previous := zeroHead }')
        preconditions += ['alteredEvent.index = successState1.count',
                          'digestValid alteredEvent.previous = true',
                          'alteredEvent.previous ≠ successState1.head']
        proposition = step('successState1', 'alteredEvent')
    elif label == 'DuplicateOperation':
        second = dict(journals['success']['events'][3]['body'])
        second['operation_id'] = first['operation_id']
        text += _definition('alteredOperation', 'Operation', _operation(second))
        text += _definition('alteredEvent', 'Event',
            '{ successEvent3 with body := .reserve alteredOperation (' + _usage(second['spent_after']) + ') }')
        preconditions += ['alteredOperation.Valid', 'alteredOperation.identity ∈ successState3.operationIds',
                          'successPolicy.Fits (successState3.spent.add alteredOperation.amount)']
        proposition = step('successState3', 'alteredEvent')
    elif label == 'WrongTariff':
        text += _definition('alteredOperation', 'Operation',
                            '{ firstOperation with amount := ⟨0, 1, 4, 3⟩ }')
        text += _definition('alteredEvent', 'Event',
            '{ successEvent1 with body := .reserve alteredOperation (successState1.spent.add alteredOperation.amount) }')
        preconditions += ['alteredOperation.amount.Bounded',
                          'successPolicy.Fits (successState1.spent.add alteredOperation.amount)',
                          'alteredOperation.amount ≠ charge alteredOperation.kind']
        proposition = step('successState1', 'alteredEvent')
    elif label == 'WrongSpentAfter':
        text += _definition('alteredEvent', 'Event',
                            '{ successEvent1 with body := .reserve firstOperation Usage.zero }')
        preconditions += ['firstOperation.Valid', 'successState2.spent ≠ Usage.zero']
        proposition = step('successState1', 'alteredEvent')
    elif label == 'OverBudgetReservation':
        text += _definition('alteredPolicy', 'Policy', '{ successPolicy with costLimit := 0 }')
        preconditions += ['alteredPolicy.Valid', 'successState2.spent.LE alteredPolicy.limits',
                          'alteredPolicy.costLimit < successState2.spent.cost']
        proposition = step('successState1', 'successEvent1', policy='alteredPolicy')
    elif label == 'DimensionOverrun':
        text += _definition('alteredPolicy', 'Policy',
                            '{ successPolicy with limits := ⟨32, 328, 1312, 3⟩ }')
        preconditions += ['alteredPolicy.Valid', 'successState2.spent.cost ≤ alteredPolicy.costLimit',
                          'alteredPolicy.limits.outputs < successState2.spent.outputs']
        proposition = step('successState1', 'successEvent1', policy='alteredPolicy')
    elif label == 'ResultWithoutReservation':
        text += _definition('alteredEvent', 'Event',
                            '{ successEvent2 with index := 1, previous := successState1.head }')
        preconditions += ['successState1.status = .open', 'successState1.pending = none']
        proposition = step('successState1', 'alteredEvent')
    elif label == 'WrongReservationHash':
        result = dict(journals['success']['events'][2]['body'])
        result['reservation_hash'] = '0' * 64
        text += _definition('alteredEvent', 'Event',
                            '{ successEvent2 with body := (' + _body(result) + ') }')
        preconditions += ['successState2.status = .pending',
                          'successState2.pending ≠ some zeroHead']
        proposition = step('successState2', 'alteredEvent')
    elif label == 'WrongResultShape':
        result = dict(journals['success']['events'][2]['body'])
        result['result_sha256'] = None
        text += _definition('alteredEvent', 'Event',
                            '{ successEvent2 with body := (' + _body(result) + ') }')
        preconditions += ['successState2.pending = some successEvent1.hash',
                          'resultShape true none none = false']
        proposition = step('successState2', 'alteredEvent')
    elif label == 'ResumeAfterFailure':
        text += _definition('alteredEvent', 'Event',
            '⟨failedFinal.count, failedFinal.head, successEvent0.hash, .seal⟩')
        preconditions += ['Terminal failedFinal', 'failedFinal.pending = none']
        proposition = step('failedFinal', 'alteredEvent', policy='failedPolicy')
    elif label == 'SealPending':
        text += _definition('alteredEvent', 'Event', '{ successEvent2 with body := .seal }')
        preconditions += ['successState2.status = .pending', 'successState2.pending = some successEvent1.hash']
        proposition = step('successState2', 'alteredEvent')
    elif label == 'WrongWorkOrder':
        text += _definition('alteredWork', 'List WorkReference',
                            'workReference1 :: workReference0 :: selectedWorkReferences.drop 2')
        preconditions += ['alteredWork.length = selectedWorkReferences.length',
                          'alteredWork.map WorkReference.kind = selectedWorkReferences.map WorkReference.kind',
                          'workReference0.identity ≠ workReference1.identity']
        proposition = 'List.Forall₂ WorkBound alteredWork selectedPairs'
    elif label == 'MissingWork':
        text += _definition('alteredWork', 'List WorkReference', 'selectedWorkReferences.take 152')
        for index in range(152):
            text += ('theorem missing_prefix_pair' + str(index) + ' : WorkBound workReference' + str(index) +
                     ' (successEvent' + str(1 + 2 * index) + ', successEvent' + str(2 + 2 * index) +
                     ') := by decide +kernel\n')
        preconditions += ['alteredWork.length + 1 = selectedWorkReferences.length',
                          'List.Forall₂ WorkBound alteredWork (selectedPairs.take 152)']
        proposition = 'List.Forall₂ WorkBound alteredWork selectedPairs'
    elif label in ('WrongInputDigest', 'WrongOutputDigest'):
        field = 'inputDigest' if label == 'WrongInputDigest' else 'outputDigest'
        text += _definition('alteredReference', 'WorkReference',
                            '{ workReference0 with ' + field + ' := zeroHead }')
        preconditions += ['WorkBound workReference0 (successEvent1, successEvent2)',
                          'digestValid alteredReference.' + field + ' = true',
                          'alteredReference.' + field + ' ≠ workReference0.' + field]
        proposition = 'WorkBound alteredReference (successEvent1, successEvent2)'
    elif label == 'RefundFailedResult':
        text += _definition('alteredState', 'State', '{ failedFinal with spent := Usage.zero }')
        preconditions += ['Step selectedBinding failedPolicy failedState2 failedEvent2 failedFinal',
                          'failedFinal.spent.cost = 24', 'alteredState.spent.cost = 0']
        proposition = 'Step selectedBinding failedPolicy failedState2 failedEvent2 alteredState'
    elif label == 'FalseExhaustion':
        text += _definition('alteredEvent', 'Event',
            '{ successEvent1 with body := .exhausted firstOperation "declared_budget" }')
        preconditions += ['successPolicy.Fits (successState1.spent.add firstOperation.amount)']
        proposition = step('successState1', 'alteredEvent')
    elif label == 'ArithmeticOverflow':
        result = dict(journals['success']['events'][2]['body'])
        result['elapsed_ns'] = 1 << 63
        text += _definition('alteredEvent', 'Event',
                            '{ successEvent2 with body := (' + _body(result) + ') }')
        # A separate local guard witness checks dimension-first exhaustion:
        # its weighted proposed cost may exceed MAX although every component
        # and the policy are bounded. This is not a reachable-history claim.
        text += _definition('boundaryPolicy', 'Policy',
                            '⟨⟨144115188075855871, 0, 0, 0⟩, 9223372036854775744⟩')
        text += _definition('boundaryState', 'State',
                            '{ successState1 with spent := boundaryPolicy.limits }')
        text += _definition('boundaryOperation', 'Operation',
                            '{ firstOperation with kind := .candidate, amount := charge .candidate }')
        text += _definition('boundaryEvent', 'Event',
            '{ successEvent1 with body := .exhausted boundaryOperation "declared_budget" }')
        preconditions += ['boundaryPolicy.Valid',
            '(boundaryState.spent.add boundaryOperation.amount).Bounded',
            'maxNatural < (boundaryState.spent.add boundaryOperation.amount).cost',
            step('boundaryState', 'boundaryEvent', policy='boundaryPolicy')]
        proposition = step('successState2', 'alteredEvent')
    else:
        require(label == 'WrongFinalHead', 'exhaustive resource control inventory required')
        preconditions += ['successFinal.head = successExpectedHead', 'successExpectedHead ≠ zeroHead']
        proposition = 'successFinal.head = zeroHead'
    text += 'theorem control_preconditions : ' + ' ∧\n    '.join('(' + p + ')' for p in preconditions)
    if label == 'MissingWork':
        text += (' := by\n  exact ⟨by decide +kernel, by decide +kernel, ' +
                 _forall2(['missing_prefix_pair' + str(i) for i in range(152)]) + '⟩\n')
    else:
        text += ' := by decide +kernel\n'
    return text, proposition


def _render_packet(packet: dict, packet_sha256: str, *, source_root: Path,
                   negative: str | None = None) -> bytes:
    text = ('import Phase17ZDependency\n\nset_option Elab.async false\n\n' + template(source_root).decode() +
            '\nnamespace Phase17ResourceProtocol\n'
            'open Phase17Routing RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
            'set_option maxRecDepth 131072\nset_option maxHeartbeats 64000000\n'
            '-- Fresh AA packet SHA256: ' + packet_sha256 + '\n')
    if negative is None:
        text += _positive(packet)
    else:
        definitions, proposition = _controls(packet, negative)
        text += definitions
        false_proof = 'by decide +kernel\n'
        if negative == 'MissingWork':
            false_proof = ('by\n  apply decide_eq_false\n  intro accepted\n' +
                           '  have different : alteredWork.length ≠ selectedPairs.length := by decide +kernel\n' +
                           '  exact different (List.Forall₂.length_eq accepted)\n')
        text += 'theorem control_false : decide (' + proposition + ') = false := ' + false_proof
        text += ('theorem rejected_control : ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  rw [eq_false h]\n  decide +kernel\n')
    text += '\nend Phase17ResourceProtocol\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode()
    require(not re.search(FORBIDDEN, raw), 'forbidden resource protocol proof token')
    return raw


def render(prepared: PreparedResourceProtocol, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedResourceProtocol and negative in (None, *LABELS[1:]),
            'exact resource-protocol proof input required')
    validate_packet(prepared.packet)
    return _render_packet(prepared.packet, sha(prepared.packet_bytes),
                          source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedResourceProtocol, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedResourceProtocol, 'exact resource-protocol proof input required')
    packet = prepared.packet
    validate_packet(packet)
    dependencies = _dependencies_validated(prepared, source_root=source_root)
    return {**dependencies, **{label: _render_packet(packet, sha(prepared.packet_bytes),
        source_root=source_root, negative=None if label == LABELS[0] else label) for label in LABELS}}


def _dependencies_validated(prepared: PreparedResourceProtocol, *, source_root: Path) -> dict[str, bytes]:
    # Exactly one call: the inherited generator checks its pins and applies W's
    # original guarded proof factoring once. AA never refactors that source.
    inherited = previous.generated_sources(prepared.evaluation_trace(), source_root=source_root)
    require(tuple(inherited) == (*previous.COMPILED_MODULES, *previous.LABELS),
            'exact inherited Z source inventory required')
    source = inherited[previous.LABELS[0]]
    require(sha(source) == Z_SOURCE_SHA, 'regenerated Z certificate differs from pinned exact source')
    expected = {'#print axioms ' + name + '\n' for name in previous.NAMES}
    lines = source.decode().splitlines(keepends=True)
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected), 'exact Z dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode()
    require(b'#print' not in source and sha(source) == Z_DEPENDENCY_SHA256,
            'exact stripped Z dependency pin differs')
    result = {name: inherited[name] for name in previous.COMPILED_MODULES}
    result['Phase17ZDependency'] = source
    require(tuple(result) == COMPILED_MODULES, 'resource protocol dependency order differs')
    return result
