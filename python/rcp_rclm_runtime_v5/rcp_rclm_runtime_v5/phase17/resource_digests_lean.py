"""Selected resource-event/work SHA certificates over the actual AA imports.

Unchanged X equations check every selected compression transition. Five bounded
auxiliary modules share repeated transitions while retaining every complete input
chain. The AA dependency is regenerated once and only its exact audits removed.
Whole-journal file checksums and producer-response hashes are outside this scope.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from . import resource_protocol_lean as previous
from . import producer_sha256_lean as arithmetic
from .captured_json_lean import _raw_image
from .materialized import require, sha
from .resource_digests import (
    PreparedResourceDigests, AA_SOURCE_SHA, compression_inventory, validate_packet,
)
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ResourceDigests.lean'
BRIDGE_SHA256 = '6347b5291fa8b97ca57cbadc2e06391e927d3d0a8742cf74818b07363069e6ea'
AA_DEPENDENCY_SHA256 = 'ed28c64ea0aed60f4623fcfe3aca666edb0cb5057f85838a7d088f647454d92d'
DEPENDENCY_LABELS = (*previous.DEPENDENCY_LABELS, 'Phase17AADependency')
BLOCKS_PER_MODULE = 512
NEW_AUXILIARY_LABELS = tuple('Phase17ABSha256Blocks' + str(i) for i in range(5))
AUXILIARY_LABELS = (*previous.AUXILIARY_LABELS, *NEW_AUXILIARY_LABELS)
COMPILED_MODULES = (*previous.COMPILED_MODULES, 'Phase17AADependency', *NEW_AUXILIARY_LABELS)
CASE_IMPORTS = ('Phase17AADependency', *NEW_AUXILIARY_LABELS)
NAMES = tuple('Phase17ResourceDigests.' + name for name in (
    'event_input_bound', 'event_digest_of_checked_input', 'work_digests_of_records',
    'candidate_digest_of_encoding', 'computed_digest_unique',
    'selected_hash_inventory', 'selected_event_preimages',
    'selected_success_event_hashes', 'selected_failed_event_hashes',
    'selected_exhausted_event_hashes', 'selected_interrupted_event_hashes',
    'selected_work_input_digests', 'selected_work_output_digests',
    'selected_work_digests', 'selected_candidate_admission_digests',
    'selected_journal_protocol_and_hashes', 'selected_work_result_binding',
    'selected_learned_acceptance_bound',
))
LABELS = ('ResourceDigests', 'WrongEventIndex', 'WrongEventPrevious', 'WrongEventBody',
          'IncludedEventHash', 'MissingDomainNul', 'WrongDomain', 'WrongEventDigest',
          'WrongWorkInput', 'WrongWorkOutput', 'WrongWorkDigest',
          'WrongAdmissionDescriptor', 'WrongAdmissionDigest', 'MissingEvent',
          'WrongBlockOrder', 'WrongPaddingLength', 'WrongScheduleWord',
          'WrongShaRound', 'WrongFeedForward', 'WrongIncomingState')
FORBIDDEN = previous.FORBIDDEN
MAX_NEW_SOURCE_BYTES = 8 * 1024 * 1024
SHA_NAMESPACE = 'Phase17ResourceDigestSha256'


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked resource digest template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'resource digest template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = previous.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _definition(name: str, typ: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + typ + ' := ' + value + '\n'


def _list(items) -> str:
    return '[' + ', '.join(items) + ']'


def _event_reference(record: dict) -> str:
    require(record['category'] == 'event', 'event record required')
    return 'Phase17ResourceProtocol.' + record['journal'] + 'Event' + str(record['event_index'])


def _record_literal(record: dict) -> str:
    category, index = record['category'], record['index']
    if category == 'event':
        image = _raw_image(bytes.fromhex(record['json_hex']))
        return ('{ json := ' + image + ', preimage := eventDomain ++ (' + image +
                '), digest := ' + _event_reference(record) + '.hash }')
    if category in ('work_input', 'work_output'):
        field = 'input' if category == 'work_input' else 'output'
        reference = 'Phase17ResourceProtocol.workReference' + str(index)
        return ('{ json := ' + reference + '.' + field + 'Image, preimage := ' +
                reference + '.' + field + 'Image, digest := ' + reference + '.' + field + 'Digest }')
    require(category == 'candidate_descriptor', 'known resource digest category required')
    image = _raw_image(bytes.fromhex(record['json_hex']))
    return ('{ json := ' + image + ', preimage := ' + image +
            ', digest := Phase17Evaluation.admissionDigests.getD ' + str(index) + ' "" }')


def _record_definition(index: int, record: dict, name: str | None = None) -> str:
    return _definition(name or ('record' + str(index)), 'Phase17Preimages.HashRecord', _record_literal(record))


def _parts(index: int, path: list[int], name: str | None = None) -> str:
    return _definition(name or ('parts' + str(index)), 'List Phase17Sha256.Block',
        _list(SHA_NAMESPACE + '.block' + str(i) for i in path))


def _hash_certificate(index: int, path: list[int]) -> str:
    record = 'record' + str(index)
    final = SHA_NAMESPACE + '.after' + str(path[-1])
    text = _parts(index, path)
    text += f'''theorem input_valid_{index} : Phase17Sha256.InputValid {record}.preimage := by decide +kernel
theorem partition_{index} : Phase17Sha256.blocks (Phase17Sha256.pad {record}.preimage) = parts{index} := by decide +kernel
theorem chain_{index} : Phase17Sha256.CompressionChain Phase17Sha256.initial parts{index} {final} := by
  exact '''
    text += ''.join('(Phase17Sha256.CompressionChain.cons ' + SHA_NAMESPACE + '.block_step_' + str(i) + ' ' for i in path)
    text += '(Phase17Sha256.CompressionChain.nil ' + final + ')' + ')' * len(path) + '\n'
    text += f'''theorem digest_{index} : Phase17Sha256.digestHex {final} = {record}.digest := by decide +kernel
theorem hash_{index} : Phase17Sha256.HashEvaluated {record} :=
  Phase17Sha256.sha256_of_chain input_valid_{index} partition_{index} chain_{index} digest_{index}

'''
    return text


def _all_hashed(indices) -> str:
    indices = list(indices)
    return ''.join('(Phase17Sha256.AllHashed.cons hash_' + str(i) + ' ' for i in indices) + \
        'Phase17Sha256.AllHashed.nil' + ')' * len(indices)


def _forall2(proofs: list[str]) -> str:
    return ''.join('(List.Forall₂.cons ' + proof + ' ' for proof in proofs) + \
        'List.Forall₂.nil' + ')' * len(proofs)


def _events_hashed(indices) -> str:
    indices = list(indices)
    return ''.join('(EventsHashed.cons event_hashed_' + str(i) + ' ' for i in indices) + \
        'EventsHashed.nil' + ')' * len(indices)


def _works_hashed() -> str:
    return ''.join('(WorksHashed.cons work_hashed_' + str(i) + ' ' for i in range(153)) + \
        'WorksHashed.nil' + ')' * 153


def _positive(packet: dict) -> str:
    records = packet['hash_records']
    _, paths = compression_inventory(records)
    require(len(records) == 631 and len(paths) == 631, 'complete selected resource hash inventory required')
    text = ''.join(_record_definition(i, record) for i, record in enumerate(records))
    text += _definition('selectedEvents', 'List Phase17ResourceProtocol.Event',
        'Phase17ResourceProtocol.successEvents ++ Phase17ResourceProtocol.failedEvents ++ '
        'Phase17ResourceProtocol.exhaustedEvents ++ Phase17ResourceProtocol.interruptedEvents')
    for name, indices in (
        ('eventRecords', range(316)), ('workInputRecords', range(316, 469)),
        ('workOutputRecords', range(469, 622)), ('candidateRecords', range(622, 631)),
        ('allRecords', range(631)),
    ):
        text += _definition(name, 'List Phase17Preimages.HashRecord', _list('record' + str(i) for i in indices))
    text += ''.join(_hash_certificate(i, path) for i, path in enumerate(paths))
    text += 'theorem all_hashed : Phase17Sha256.AllHashed allRecords := ' + _all_hashed(range(631)) + '\n'
    text += '''theorem selected_hash_inventory :
    allRecords.length = 631 ∧ eventRecords.length = 316 ∧
    workInputRecords.length = 153 ∧ workOutputRecords.length = 153 ∧
    candidateRecords.length = 9 ∧ Phase17Sha256.AllHashed allRecords := by
  exact ⟨by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, all_hashed⟩

'''
    for index, record in enumerate(records[:316]):
        event = _event_reference(record)
        text += f'''theorem event_input_{index} : EventInputChecked {event} record{index} := by decide +kernel
theorem event_hashed_{index} : EventDigestChecked {event} :=
  event_digest_of_checked_input {event} record{index} event_input_{index} hash_{index}
'''
    text += 'theorem selected_event_preimages : List.Forall₂ EventInputChecked selectedEvents eventRecords :=\n  '
    text += _forall2(['event_input_' + str(i) for i in range(316)]) + '\n\n'
    offset = 0
    for name, count in (('success', 308), ('failed', 3), ('exhausted', 2), ('interrupted', 3)):
        text += ('theorem selected_' + name + '_event_hashes : EventsHashed Phase17ResourceProtocol.' +
                 name + 'Events :=\n  ' + _events_hashed(range(offset, offset + count)) + '\n\n')
        offset += count
    for name, start, field in (('input', 316, 'input'), ('output', 469, 'output')):
        title = 'workInputRecords' if name == 'input' else 'workOutputRecords'
        text += f'''theorem selected_work_{name}_digests :
    Phase17Sha256.AllHashed {title} ∧
    {title}.map Phase17Preimages.HashRecord.preimage =
      Phase17ResourceProtocol.selectedWorkReferences.map Phase17ResourceProtocol.WorkReference.{field}Image ∧
    {title}.map Phase17Preimages.HashRecord.digest =
      Phase17ResourceProtocol.selectedWorkReferences.map Phase17ResourceProtocol.WorkReference.{field}Digest := by
  exact ⟨''' + _all_hashed(range(start, start + 153)) + ''', rfl, rfl⟩

'''
    for index in range(153):
        text += f'''theorem work_hashed_{index} : WorkDigestsChecked Phase17ResourceProtocol.workReference{index} :=
  work_digests_of_records Phase17ResourceProtocol.workReference{index} record{316 + index} record{469 + index}
    ⟨rfl, rfl⟩ ⟨rfl, rfl⟩ hash_{316 + index} hash_{469 + index}
'''
    text += ('theorem selected_work_digests : WorksHashed Phase17ResourceProtocol.selectedWorkReferences :=\n  ' +
             _works_hashed() + '\n\n')
    for index in range(9):
        text += f'''theorem admission_encoded_{index} :
    Phase17Preimages.encode (Phase17Preimages.descriptorValue Phase17Evaluation.candidateDescriptor{index}.2) =
      some record{622 + index}.preimage := by decide +kernel
theorem admission_hashed_{index} : CandidateDigestChecked Phase17Evaluation.candidateDescriptor{index}
    (Phase17Evaluation.admissionDigests.getD {index} "") :=
  candidate_digest_of_encoding Phase17Evaluation.candidateDescriptor{index} record{622 + index}.preimage
    (Phase17Evaluation.admissionDigests.getD {index} "") admission_encoded_{index} hash_{622 + index}
'''
    text += '''theorem selected_candidate_admission_digests :
    List.Forall₂ CandidateDigestChecked Phase17Evaluation.candidateDescriptors
      Phase17Evaluation.admissionDigests :=
  ''' + _forall2(['admission_hashed_' + str(i) for i in range(9)]) + '\n\n'
    journal_terms = []
    journal_proofs = []
    for name in ('success', 'failed', 'exhausted', 'interrupted'):
        prefix = 'Phase17ResourceProtocol.'
        journal_terms.append('Phase17ResourceProtocol.JournalChecked ' + prefix + 'selectedBinding ' +
            prefix + name + 'Policy ' + prefix + name + 'Raw ' + prefix + name + 'Images ' +
            prefix + name + 'Events ' + prefix + name + 'ExpectedHead ' + prefix + name + 'Final')
        journal_terms.append('EventsHashed ' + prefix + name + 'Events')
        journal_proofs += [prefix + 'selected_' + name + '_replay.1', 'selected_' + name + '_event_hashes']
    text += 'theorem selected_journal_protocol_and_hashes :\n    ' + ' ∧\n    '.join(journal_terms) + ' := by\n'
    text += '  exact ⟨' + ', '.join(journal_proofs) + '⟩\n\n'
    text += '''theorem selected_work_result_binding :
    WorksHashed Phase17ResourceProtocol.selectedWorkReferences ∧
    List.Forall₂ Phase17ResourceProtocol.WorkBound Phase17ResourceProtocol.selectedWorkReferences
      Phase17ResourceProtocol.selectedPairs ∧
    List.Forall₂ Phase17ResourceProtocol.ImportedImageBound Phase17ResourceProtocol.selectedWorkReferences
      Phase17Evaluation.workImages := by
  exact ⟨selected_work_digests, Phase17ResourceProtocol.selected_result_binding,
    Phase17ResourceProtocol.selected_work_schedule_binding.1⟩

theorem selected_learned_acceptance_bound :
    EventsHashed Phase17ResourceProtocol.successEvents ∧
    WorksHashed Phase17ResourceProtocol.selectedWorkReferences ∧
    List.Forall₂ CandidateDigestChecked Phase17Evaluation.candidateDescriptors
      Phase17Evaluation.admissionDigests ∧
    Phase17ResourceProtocol.JournalChecked Phase17ResourceProtocol.selectedBinding
      Phase17ResourceProtocol.successPolicy Phase17ResourceProtocol.successRaw
      Phase17ResourceProtocol.successImages Phase17ResourceProtocol.successEvents
      Phase17ResourceProtocol.successExpectedHead Phase17ResourceProtocol.successFinal ∧
    List.Forall₂ Phase17ResourceProtocol.WorkBound Phase17ResourceProtocol.selectedWorkReferences
      Phase17ResourceProtocol.selectedPairs ∧
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  rcases Phase17ResourceProtocol.selected_learned_acceptance_bound with
    ⟨_, _, _, _, _, _, _, _, _, _, _, accepted⟩
  exact ⟨selected_success_event_hashes, selected_work_digests,
    selected_candidate_admission_digests, Phase17ResourceProtocol.selected_success_replay.1,
    Phase17ResourceProtocol.selected_result_binding, accepted⟩
'''
    return text


def _controls(packet: dict, label: str) -> tuple[str, str, list[str]]:
    records = packet['hash_records']
    blocks, paths = compression_inventory(records)
    zero = string('0' * 64)
    require(label in LABELS[1:], 'known resource digest control required')
    text, conditions = '', []
    if label in ('WrongEventIndex', 'WrongEventPrevious', 'WrongEventBody', 'IncludedEventHash',
                 'MissingDomainNul', 'WrongDomain', 'WrongEventDigest', 'WrongBlockOrder',
                 'WrongPaddingLength'):
        index = 1 if label in ('WrongEventPrevious', 'WrongEventBody') else 0
        record = records[index]
        event = _event_reference(record)
        text += _record_definition(index, record, 'actualRecord')
        conditions += ['EventInputChecked ' + event + ' actualRecord']
        if label == 'WrongEventIndex':
            text += _definition('changedEvent', 'Phase17ResourceProtocol.Event',
                '{ ' + event + ' with index := ' + event + '.index + 1 }')
            return text, 'EventInputChecked changedEvent actualRecord', conditions
        if label == 'WrongEventPrevious':
            text += _definition('changedEvent', 'Phase17ResourceProtocol.Event',
                '{ ' + event + ' with previous := ' + zero + ' }')
            conditions.append(event + '.previous ≠ ' + zero)
            return text, 'EventInputChecked changedEvent actualRecord', conditions
        if label == 'WrongEventBody':
            text += _definition('changedEvent', 'Phase17ResourceProtocol.Event',
                '{ ' + event + ' with body := .seal }')
            conditions.append(event + '.body ≠ .seal')
            return text, 'EventInputChecked changedEvent actualRecord', conditions
        if label == 'IncludedEventHash':
            image = 'Phase17ResourceProtocol.successImage0'
            text += _definition('changedRecord', 'Phase17Preimages.HashRecord',
                '{ actualRecord with json := ' + image + ', preimage := eventDomain ++ ' + image + ' }')
            conditions.append('changedRecord.json ≠ actualRecord.json')
            return text, 'EventInputChecked ' + event + ' changedRecord', conditions
        if label in ('MissingDomainNul', 'WrongDomain'):
            prefix = 'eventDomain.dropLast' if label == 'MissingDomainNul' else 'Phase17Preimages.domain'
            text += _definition('changedRecord', 'Phase17Preimages.HashRecord',
                '{ actualRecord with preimage := ' + prefix + ' ++ actualRecord.json }')
            conditions.append('changedRecord.preimage ≠ actualRecord.preimage')
            return text, 'EventInputChecked ' + event + ' changedRecord', conditions
        if label == 'WrongEventDigest':
            final = SHA_NAMESPACE + '.after' + str(paths[index][-1])
            conditions += ['Phase17Sha256.digestHex ' + final + ' = actualRecord.digest',
                           'actualRecord.digest ≠ ' + zero]
            return text, 'Phase17Sha256.digestHex ' + final + ' = ' + zero, conditions
        if label == 'WrongBlockOrder':
            text += _parts(index, paths[index], 'actualParts')
            conditions += ['1 < actualParts.length',
                'Phase17Sha256.blocks (Phase17Sha256.pad actualRecord.preimage) = actualParts']
            return text, 'Phase17Sha256.blocks (Phase17Sha256.pad actualRecord.preimage) = actualParts.reverse', conditions
        require(label == 'WrongPaddingLength', 'resource padding control required')
        from .producer_sha256 import pad_message
        altered = bytearray(pad_message(bytes.fromhex(record['preimage_hex'])))
        altered[-1] ^= 1
        text += _definition('changedPadded', 'List Nat', arithmetic._nat_list(altered))
        conditions.append('changedPadded.length = (Phase17Sha256.pad actualRecord.preimage).length')
        return text, 'Phase17Sha256.pad actualRecord.preimage = changedPadded', conditions
    if label in ('WrongWorkInput', 'WrongWorkOutput', 'WrongWorkDigest'):
        index = 469 if label == 'WrongWorkOutput' else 316
        field = 'output' if label == 'WrongWorkOutput' else 'input'
        text += _record_definition(index, records[index], 'actualRecord')
        work = 'Phase17ResourceProtocol.workReference0'
        conditions += ['actualRecord.preimage = ' + work + '.' + field + 'Image',
                       'actualRecord.digest = ' + work + '.' + field + 'Digest']
        if label == 'WrongWorkDigest':
            final = SHA_NAMESPACE + '.after' + str(paths[index][-1])
            conditions += ['Phase17Sha256.digestHex ' + final + ' = actualRecord.digest',
                           'actualRecord.digest ≠ ' + zero]
            return text, 'Phase17Sha256.digestHex ' + final + ' = ' + zero, conditions
        raw = bytearray(bytes.fromhex(records[index]['preimage_hex']))
        raw[0] ^= 1
        text += _definition('changedImage', 'List Nat', _raw_image(bytes(raw)))
        conditions.append('changedImage.length = actualRecord.preimage.length')
        return text, 'changedImage = ' + work + '.' + field + 'Image', conditions
    if label in ('WrongAdmissionDescriptor', 'WrongAdmissionDigest'):
        index = 622
        text += _record_definition(index, records[index], 'actualRecord')
        conditions += ['Phase17Preimages.encode (Phase17Preimages.descriptorValue '
                       'Phase17Evaluation.candidateDescriptor0.2) = some actualRecord.preimage']
        if label == 'WrongAdmissionDescriptor':
            conditions.append('Phase17Evaluation.candidateDescriptor0.2 ≠ Phase17Evaluation.candidateDescriptor1.2')
            return text, ('Phase17Preimages.encode (Phase17Preimages.descriptorValue '
                          'Phase17Evaluation.candidateDescriptor1.2) = some actualRecord.preimage'), conditions
        final = SHA_NAMESPACE + '.after' + str(paths[index][-1])
        conditions += ['Phase17Sha256.digestHex ' + final + ' = actualRecord.digest',
                       'actualRecord.digest ≠ ' + zero]
        return text, 'Phase17Sha256.digestHex ' + final + ' = ' + zero, conditions
    if label == 'MissingEvent':
        text += _definition('changedEvents', 'List Phase17ResourceProtocol.Event',
                            'Phase17ResourceProtocol.successEvents.dropLast')
        conditions += ['changedEvents.length = 307', 'Phase17ResourceProtocol.successEvents.length = 308']
        return text, 'changedEvents = Phase17ResourceProtocol.successEvents', conditions
    block = copy.deepcopy(blocks[0])
    original = SHA_NAMESPACE + '.'
    conditions.append('Phase17Sha256.BlockChecked ' + original + 'before0 ' + original +
                      'block0 ' + original + 'trace0 ' + original + 'after0')
    if label == 'WrongScheduleWord':
        block['schedule'][16] ^= 1
    elif label == 'WrongShaRound':
        block['round_states'][0][0] ^= 1
    elif label == 'WrongFeedForward':
        block['output_state'][0] ^= 1
    else:
        require(label == 'WrongIncomingState', 'exhaustive resource digest controls required')
        block['input_state'][0] ^= 1
    text += arithmetic._block_definitions(9000, block)
    conditions.append('before9000 = ' + original + 'before0' if label != 'WrongIncomingState'
                      else 'before9000 ≠ ' + original + 'before0')
    return text, 'Phase17Sha256.BlockChecked before9000 block9000 trace9000 after9000', conditions


def _new_auxiliaries(packet: dict, packet_hash: str) -> dict[str, bytes]:
    blocks, _ = compression_inventory(packet['hash_records'])
    require(len(blocks) == 2134, 'complete selected AB compression inventory required')
    result = {}
    for number, label in enumerate(NEW_AUXILIARY_LABELS):
        start, stop = number * BLOCKS_PER_MODULE, min((number + 1) * BLOCKS_PER_MODULE, len(blocks))
        require(start < stop, 'empty resource digest arithmetic module')
        text = ('import Phase17XSha256Blocks\n\nset_option Elab.async false\n\n'
                'namespace ' + SHA_NAMESPACE + '\nopen Phase17Sha256\n'
                'set_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n')
        text += '-- Fresh AB packet SHA256: ' + packet_hash + '\n'
        for index in range(start, stop):
            text += arithmetic._block_definitions(index, blocks[index]) + arithmetic._block_certificate(index)
        text += '\nend ' + SHA_NAMESPACE + '\n'
        raw = text.encode('utf-8')
        require(len(raw) <= MAX_NEW_SOURCE_BYTES and not re.search(FORBIDDEN, raw),
                'oversized or forbidden resource arithmetic module')
        result[label] = raw
    return result


def _render_packet(packet: dict, packet_hash: str, *, source_root: Path,
                   negative: str | None = None) -> bytes:
    text = ''.join('import ' + label + '\n' for label in CASE_IMPORTS)
    text += '\nset_option Elab.async false\n\n' + template(source_root).decode('utf-8')
    text += ('\nnamespace Phase17ResourceDigests\n'
             'open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17Sha256\n'
             'set_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n')
    text += '-- Fresh AB packet SHA256: ' + packet_hash + '\n'
    if negative is None:
        text += _positive(packet)
    else:
        definitions, proposition, preconditions = _controls(packet, negative)
        text += definitions
        text += ('theorem control_preconditions :\n    ' + ' ∧\n    '.join(preconditions) +
                 ' := by decide +kernel\n\n')
        false_proof = 'by decide +kernel'
        if negative == 'MissingEvent':
            # Keep the complete list-equality proposition, but use its already
            # checked length contradiction instead of deciding 307 equal events.
            false_proof = '''by
  apply decide_eq_false
  intro equality
  have unequal : (307 : Nat) ≠ 308 := by decide +kernel
  exact unequal (control_preconditions.1.symm.trans
    ((congrArg List.length equality).trans control_preconditions.2))'''
        text += ('theorem control_false : decide (' + proposition + ') = false := ' + false_proof + '\n\n'
                 'theorem rejected_control : ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  rw [eq_false h]\n'
                 '  decide +kernel\n')
    text += '\nend Phase17ResourceDigests\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(len(raw) <= MAX_NEW_SOURCE_BYTES and not re.search(FORBIDDEN, raw),
            'oversized or forbidden resource digest proof source')
    return raw


def _dependencies_validated(prepared: PreparedResourceDigests, *, source_root: Path) -> dict[str, bytes]:
    inherited = previous.generated_sources(prepared.resource_protocol(), source_root=source_root)
    require(tuple(inherited) == (*previous.COMPILED_MODULES, *previous.LABELS),
            'exact inherited AA source inventory required')
    source = inherited[previous.LABELS[0]]
    require(sha(source) == AA_SOURCE_SHA, 'regenerated AA certificate differs from exact pinned source')
    expected = {'#print axioms ' + name + '\n' for name in previous.NAMES}
    lines = source.decode('utf-8').splitlines(keepends=True)
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected), 'exact AA dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in source and sha(source) == AA_DEPENDENCY_SHA256,
            'exact stripped AA dependency pin differs')
    result = {name: inherited[name] for name in previous.COMPILED_MODULES}
    result['Phase17AADependency'] = source
    require(tuple(result) == (*previous.COMPILED_MODULES, 'Phase17AADependency'),
            'resource digest dependency order differs')
    return result


def render(prepared: PreparedResourceDigests, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedResourceDigests and negative in (None, *LABELS[1:]),
            'exact resource digest proof input required')
    packet = prepared.packet
    validate_packet(packet)
    return _render_packet(packet, sha(prepared.packet_bytes), source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedResourceDigests, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedResourceDigests, 'exact resource digest proof input required')
    packet = prepared.packet
    validate_packet(packet)
    packet_hash = sha(prepared.packet_bytes)
    dependencies = _dependencies_validated(prepared, source_root=source_root)
    result = {**dependencies, **_new_auxiliaries(packet, packet_hash),
        **{label: _render_packet(packet, packet_hash, source_root=source_root,
            negative=None if label == LABELS[0] else label) for label in LABELS}}
    require(tuple(result) == (*COMPILED_MODULES, *LABELS), 'resource digest full source order differs')
    return result
