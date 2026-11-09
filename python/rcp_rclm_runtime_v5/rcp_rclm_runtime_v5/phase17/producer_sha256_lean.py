"""Kernel-checked SHA-256 witnesses for all actual imported W hash records.

Literal schedules and round states are untrusted intermediate values. Generic
soundness theorems derive compression, complete block chaining, and the final
SHA-256 result from their locally checked recurrences. Shared transitions are
proved once and reused without omitting any complete selected message.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from . import producer_preimages_lean
from .materialized import require, sha
from .producer_sha256 import (
    PreparedProducerSha256, W_SOURCE_SHA, compression_trace, validate_packet,
)
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ProducerSha256.lean'
BRIDGE_SHA256 = 'ffdaf6f2e291702a7688c231220525fd45ef6f775503c6557a37c364188d0d9e'
DEPENDENCY_LABELS = (*producer_preimages_lean.DEPENDENCY_LABELS, 'Phase17WDependency')
AUXILIARY_LABELS = ('Phase17XSha256Blocks',)
BRIDGE_MARKER = '/-- The actual imported W input record now has its complete digest evaluated. -/'
NAMES = tuple('Phase17Sha256.' + name for name in (
    'schedule_checked_sound', 'rounds_checked_sound', 'block_checked_sound',
    'compression_chain_sound', 'preimage_digest_bound', 'selected_standard_vectors',
    'selected_padding_edges', 'selected_hash_inventory', 'selected_ranking_digest',
    'selected_grammar_digests', 'selected_program_digests', 'selected_feature_digests',
    'selected_tie_digests', 'selected_freeze_digest', 'selected_learned_acceptance_bound',
))
LABELS = (
    'ProducerSha256', 'WrongInputByte', 'MissingDomainNul', 'WrongPaddingLength',
    'WrongWordEndian', 'WrongScheduleWord', 'WrongRoundState', 'WrongInitialState',
    'WrongFeedForward', 'WrongBlockOrder', 'TruncatedBlockChain', 'WrongDigest',
    'WrongWBinding',
)
FORBIDDEN = rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b'


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked producer SHA-256 template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'producer SHA-256 template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = producer_preimages_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _definition(name: str, kind: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + kind + ' := ' + value + '\n'


def _nat_list(values) -> str:
    return '[' + ', '.join(map(str, values)) + ']'


def _reference(record: dict) -> str:
    category, index = record['category'], record['index']
    if category == 'ranking_seed':
        return 'Phase17Preimages.rankingSeedRecord'
    if category == 'freeze':
        return 'Phase17Preimages.freezeRecord'
    if category == 'tie':
        return ('(Phase17Preimages.record' + str(index // 5) + '.ties.getD ' + str(index % 5) +
                ' { json := [], preimage := [], digest := "" })')
    field = {'grammar_seed': 'grammarSeed', 'program': 'program', 'feature': 'feature'}[category]
    return 'Phase17Preimages.record' + str(index) + '.' + field


def _trace_literal(block: dict) -> str:
    return ('{ schedule := ' + _nat_list(block['schedule']) +
            ', roundStates := [' + ', '.join(_nat_list(state) for state in block['round_states']) +
            '], finalState := ' + _nat_list(block['round_states'][-1]) + ' }')


def _block_key(block: dict) -> tuple:
    return tuple(block['input_state']), block['block_hex']


def _block_definitions(index: int, block: dict) -> str:
    text = _definition('block' + str(index), 'Block', _nat_list(bytes.fromhex(block['block_hex'])))
    text += _definition('before' + str(index), 'State', _nat_list(block['input_state']))
    text += _definition('after' + str(index), 'State', _nat_list(block['output_state']))
    text += _definition('trace' + str(index), 'BlockTrace', _trace_literal(block))
    return text


def _block_certificate(index: int) -> str:
    return f'''theorem block_checked_{index} :
    BlockChecked before{index} block{index} trace{index} after{index} := by
  decide +kernel

theorem block_step_{index} : compress before{index} block{index} = after{index} :=
  block_checked_sound _ _ _ _ block_checked_{index}

'''


def _record_certificates(index: int, record: dict, ids: list[int], *, reference: str | None = None) -> str:
    name = 'selectedRecord' + str(index)
    if reference is None:
        reference = _reference(record)
    text = _definition(name, 'Phase17Preimages.HashRecord', reference)
    text += _definition('parts' + str(index), 'List Block',
                        '[' + ', '.join('block' + str(number) for number in ids) + ']')
    final = 'after' + str(ids[-1])
    text += f'''theorem input_checked_{index} : InputValid {name}.preimage := by decide +kernel

theorem partition_checked_{index} :
    blocks (pad {name}.preimage) = parts{index} ∧
    parts{index}.flatten = pad {name}.preimage ∧
    (pad {name}.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_{index} : CompressionChain initial parts{index} {final} := by
  exact '''
    text += ''.join('(CompressionChain.cons block_step_' + str(number) + ' ' for number in ids)
    text += '(CompressionChain.nil ' + final + ')' + ')' * len(ids) + '\n\n'
    text += f'''theorem digest_checked_{index} : digestHex {final} = {name}.digest := by decide +kernel

theorem hash_checked_{index} : HashEvaluated {name} :=
  sha256_of_chain input_checked_{index} partition_checked_{index}.1
    chain_checked_{index} digest_checked_{index}

'''
    return text


def _all_hashed(indices) -> str:
    indices = list(indices)
    return ''.join('(AllHashed.cons hash_checked_' + str(index) + ' ' for index in indices) + 'AllHashed.nil' + ')' * len(indices)


STANDARD_VECTORS = (
    (b'', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    (b'abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'),
    (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
     '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'),
)


def _compression_inventory(packet: dict) -> tuple[list[dict], list[dict], list[list[int]]]:
    records = packet['hash_records']
    require(len(records) == 258, 'complete selected W hash inventory required')
    all_records = list(records)
    for raw, digest in STANDARD_VECTORS:
        all_records.append({'category': 'standard', 'index': len(all_records) - len(records),
                            'preimage_hex': raw.hex(), 'digest': digest, 'blocks': compression_trace(raw)})
    unique: dict[tuple, int] = {}
    blocks: list[dict] = []
    paths: list[list[int]] = []
    for record in all_records:
        path = []
        for block in record['blocks']:
            key = _block_key(block)
            if key not in unique:
                unique[key] = len(blocks)
                blocks.append(block)
            else:
                previous = blocks[unique[key]]
                require(all(previous[field] == block[field] for field in
                            ('schedule', 'round_states', 'output_state')),
                        'duplicate compression input has inconsistent witness')
            path.append(unique[key])
        paths.append(path)
    return all_records, blocks, paths


def _positive(packet: dict) -> str:
    records = packet['hash_records']
    all_records, _, paths = _compression_inventory(packet)
    text = '-- Every complete selected message keeps its own ordered block chain.\n'
    for index, (record, ids) in enumerate(zip(all_records, paths, strict=True)):
        reference = None
        if index >= len(records):
            reference = ('{ json := [], preimage := ' + _nat_list(bytes.fromhex(record['preimage_hex'])) +
                         ', digest := ' + string(record['digest']) + ' }')
        text += _record_certificates(index, record, ids, reference=reference)
    text += _definition('selectedRecords', 'List Phase17Preimages.HashRecord',
                        '[' + ', '.join('selectedRecord' + str(index) for index in range(len(records))) + ']')
    text += 'theorem all_selected_hashed : AllHashed selectedRecords := ' + _all_hashed(range(258)) + '\n\n'
    text += '''theorem selected_hash_inventory :
    selectedRecords.length = 258 ∧
    (selectedRecords.map (fun record => record.preimage.length)).sum = 98349 ∧
    (selectedRecords.map (fun record => (blocks (pad record.preimage)).length)).sum = 1652 ∧
    digestRecords selectedRecords = some (selectedRecords.map Phase17Preimages.HashRecord.digest) := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, ?_⟩
  exact digest_records_sound selectedRecords all_selected_hashed

'''
    groups = [('ranking_seed', 'ranking', 'selected_ranking_digest'),
              ('grammar_seed', 'grammar', 'selected_grammar_digests'),
              ('program', 'program', 'selected_program_digests'),
              ('feature', 'feature', 'selected_feature_digests'),
              ('tie', 'tie', 'selected_tie_digests'), ('freeze', 'freeze', 'selected_freeze_digest')]
    for category, name, theorem in groups:
        indices = [index for index, record in enumerate(records) if record['category'] == category]
        text += _definition(name + 'Records', 'List Phase17Preimages.HashRecord',
                            '[' + ', '.join('selectedRecord' + str(index) for index in indices) + ']')
        text += f'''theorem {theorem} :
    digestRecords {name}Records = some ({name}Records.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ ''' + _all_hashed(indices) + '\n\n'
    text += '''theorem selected_standard_vectors :
    sha256 [] = some "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" ∧
    sha256 [97, 98, 99] = some "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" ∧
    sha256 (Phase17Preimages.ascii "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") =
      some "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1" := by
  exact ⟨hash_checked_258, hash_checked_259, hash_checked_260⟩

'''
    text += PADDING_EDGES
    text += ACCEPTANCE
    return text


PADDING_EDGES = '''theorem selected_padding_edges :
    (pad []).length = 64 ∧
    (pad (List.replicate 55 0)).length = 64 ∧
    (pad (List.replicate 56 0)).length = 128 ∧
    (pad (List.replicate 63 0)).length = 128 ∧
    (pad (List.replicate 64 0)).length = 128 ∧
    be64 440 = [0, 0, 0, 0, 0, 0, 1, 184] ∧
    be64 448 = [0, 0, 0, 0, 0, 0, 1, 192] ∧
    be64 18446744073709551615 = [255, 255, 255, 255, 255, 255, 255, 255] ∧
    word [1, 2, 3, 4] = 16909060 ∧
    ror 2147483649 1 = 3221225472 ∧
    u32 4294967296 = 0 ∧
    sha256 [256] = none ∧
    constants.length = 64 ∧ initial.length = 8 := by decide +kernel

'''


ACCEPTANCE = '''theorem selected_learned_acceptance_bound :
    AllHashed selectedRecords ∧
    (Phase17Preimages.hashInput
      (Phase17Preimages.rankingSeedValue Phase17Preimages.selectedView)).bind sha256 =
        some Phase17Preimages.rankingSeedRecord.digest ∧
    (Phase17Preimages.hashInput
      (Phase17Preimages.freezeValue Phase17Preimages.selectedView Phase17Provenance.selectedContext.rows
        Phase17Metadata.candidateDescriptors)).bind sha256 = some Phase17Preimages.freezeRecord.digest ∧
    Phase17Preimages.derivedDescriptors = some Phase17Metadata.candidateDescriptors ∧
    Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.beforeImage
      Phase17Preimages.freezeRecord.digest Phase17Preimages.selectedView.context Phase17Metadata.beforeImages
      Phase17Preimages.derivedPublicRows Phase17Preimages.derivedImages =
        some Phase17Finite.selectedConfiguration.context ∧
    Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.afterImage
      Phase17Preimages.freezeRecord.digest Phase17Preimages.selectedView.context Phase17Metadata.afterImages
      Phase17Preimages.derivedPublicRows Phase17Preimages.derivedImages =
        some Phase17Finite.selectedConfiguration.context ∧
    Phase17Provenance.Produced Phase17Finite.selectedConfiguration.context Phase17Finite.selectedEvidence.proposal ∧
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  exact ⟨all_selected_hashed,
    preimage_digest_bound _ _ Phase17Preimages.selected_ranking_seed_preimage.1 hash_checked_0,
    preimage_digest_bound _ _ Phase17Preimages.selected_freeze_preimage.1 hash_checked_257,
    Phase17Preimages.selected_descriptors_bound.1,
    Phase17Preimages.selected_context_bound.1, Phase17Preimages.selected_context_bound.2,
    Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted⟩
'''


def _controls(packet: dict, negative: str) -> tuple[str, str]:
    record = packet['hash_records'][0]
    block = copy.deepcopy(record['blocks'][0])
    raw = bytes.fromhex(record['preimage_hex'])
    text = _definition('actualRecord', 'Phase17Preimages.HashRecord', _reference(record))
    text += _definition('actualParts', 'List Block',
                        '[' + ', '.join(_nat_list(bytes.fromhex(value['block_hex'])) for value in record['blocks']) + ']')
    if negative in ('WrongInputByte', 'MissingDomainNul'):
        changed = bytes([raw[0] ^ 1]) + raw[1:] if negative == 'WrongInputByte' else raw[:25] + raw[26:]
        text += _definition('changedInput', 'List Nat', _nat_list(changed))
        return text, 'changedInput = actualRecord.preimage'
    if negative == 'WrongPaddingLength':
        text += _definition('wrongLengthField', 'List Nat', _nat_list((len(raw)*8+8).to_bytes(8, 'big')))
        return text, 'be64 (actualRecord.preimage.length * 8) = wrongLengthField'
    if negative == 'WrongWordEndian':
        data = bytes.fromhex(block['block_hex'])
        wrong = [int.from_bytes(data[offset:offset+4], 'little') for offset in range(0,64,4)]
        text += _definition('wrongWords', 'List Nat', _nat_list(wrong))
        text += _definition('firstBlock', 'Block', _nat_list(data))
        return text, 'readWords firstBlock = wrongWords'
    if negative == 'WrongBlockOrder':
        parts = list(record['blocks']); parts[0], parts[1] = parts[1], parts[0]
        text += _definition('wrongParts', 'List Block',
                            '[' + ', '.join(_nat_list(bytes.fromhex(value['block_hex'])) for value in parts) + ']')
        return text, 'blocks (pad actualRecord.preimage) = wrongParts'
    if negative == 'TruncatedBlockChain':
        return text, 'blocks (pad actualRecord.preimage) = actualParts.dropLast'
    if negative in ('WrongDigest', 'WrongWBinding'):
        final = record['blocks'][-1]['output_state']
        text += _definition('finalState', 'State', _nat_list(final))
        if negative == 'WrongDigest':
            changed = ('0' if record['digest'][0] != '0' else '1') + record['digest'][1:]
            return text, 'digestHex finalState = ' + string(changed)
        return text, 'digestHex finalState = Phase17Preimages.record0.grammarSeed.digest'
    if negative == 'WrongScheduleWord':
        block['schedule'][20] ^= 1
    elif negative == 'WrongRoundState':
        block['round_states'][0][0] ^= 1
    elif negative == 'WrongInitialState':
        block['input_state'][0] ^= 1
    elif negative == 'WrongFeedForward':
        block['output_state'][0] ^= 1
    else:
        raise AssertionError('unknown producer SHA-256 negative control')
    # The fresh auxiliary already owns block0..block695. These deliberately
    # corrupted local witnesses use a separate name, so rejection must arise
    # from the false recurrence rather than from a duplicate declaration.
    text += _block_definitions(1000, block)
    return text, 'BlockChecked before1000 block1000 trace1000 after1000'


def _template_parts(source_root: Path) -> tuple[str, str]:
    text = template(source_root).decode('utf-8')
    require(text.count(BRIDGE_MARKER) == 1, 'exact SHA-256 template bridge boundary required')
    core, bridge = text.split(BRIDGE_MARKER, 1)
    return core + 'end Phase17Sha256\n', 'namespace Phase17Sha256\n' + BRIDGE_MARKER + bridge


def _auxiliary_validated(prepared: PreparedProducerSha256, *, source_root: Path) -> bytes:
    core, _ = _template_parts(source_root)
    text = 'import Lean\n\nset_option Elab.async false\n\n' + core
    text += '\nnamespace Phase17Sha256\nset_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n'
    text += '-- Fresh X packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    _, blocks, _ = _compression_inventory(prepared.packet)
    require(len(blocks) == 696, 'complete selected and standard-vector compression inventory required')
    for index, block in enumerate(blocks):
        text += _block_definitions(index, block)
        text += _block_certificate(index)
    text += '\nend Phase17Sha256\n'
    raw = text.encode('utf-8')
    require(not re.search(FORBIDDEN, raw), 'forbidden producer SHA-256 proof token')
    return raw


def _render_validated(prepared: PreparedProducerSha256, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    _, bridge = _template_parts(source_root)
    text = ('import Phase17WDependency\nimport Phase17XSha256Blocks\n\n'
            'set_option Elab.async false\n\n' + bridge)
    text += '\nnamespace Phase17Sha256\nopen RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n'
    text += '-- Fresh X packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    if negative is None:
        text += _positive(prepared.packet)
    else:
        definitions, proposition = _controls(prepared.packet, negative)
        text += definitions
        text += ('theorem control_false : decide (' + proposition + ') = false := by decide +kernel\n\n'
                 'theorem rejected_control : ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  simp only [h]\n'
                 '  decide +kernel\n')
    text += '\nend Phase17Sha256\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(FORBIDDEN, raw), 'forbidden producer SHA-256 proof token')
    return raw


def _dependencies_validated(prepared: PreparedProducerSha256, *, source_root: Path) -> dict[str, bytes]:
    previous = prepared.producer_preimages()
    result = producer_preimages_lean._dependencies_validated(previous, source_root=source_root)
    source = producer_preimages_lean._render_validated(previous, source_root=source_root)
    require(sha(source) == W_SOURCE_SHA, 'freshly generated W dependency differs from its exact pinned source')
    lines = source.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in producer_preimages_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected), 'exact W dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in source, 'unexpected W dependency output')
    result['Phase17WDependency'] = source
    require(tuple(result) == DEPENDENCY_LABELS, 'producer SHA-256 dependency order differs')
    return result


def render(prepared: PreparedProducerSha256, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedProducerSha256 and negative in (None, *LABELS[1:]),
            'exact producer SHA-256 proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedProducerSha256, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedProducerSha256, 'exact producer SHA-256 proof input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            AUXILIARY_LABELS[0]: _auxiliary_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label) for label in LABELS}}
