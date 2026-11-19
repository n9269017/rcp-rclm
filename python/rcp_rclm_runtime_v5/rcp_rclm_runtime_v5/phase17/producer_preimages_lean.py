"""Render all selected producer preimages into actual imported V/U inputs.

Complete JSON and domain-prefixed input images are checked independently of
their supplied digest strings. Every seeded descriptor is constructed in Lean,
then bound to the imported V descriptor and image. No SHA-256 theorem is claimed.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from . import program_metadata_lean
from .captured_json_lean import _raw_image
from .controller import FAMILIES
from .materialized import require, sha
from .producer_preimages import PreparedProducerPreimages, V_SOURCE_SHA, validate_packet
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ProducerPreimages.lean'
BRIDGE_SHA256 = '2afd34f75745591ed871f9d91ed0e39384506177b8459419bf03ea9c9df38930'
DEPENDENCY_LABELS = (*program_metadata_lean.DEPENDENCY_LABELS, 'Phase17VDependency')
NAMES = tuple('Phase17Preimages.' + name for name in (
    'parameter_range', 'preimage_encoding_bound', 'row_certificates_compose',
    'selected_context_projection', 'selected_ranking_seed_preimage',
    'selected_grammar_seed_preimages', 'selected_program_preimages',
    'selected_feature_preimages', 'selected_tie_preimages', 'selected_freeze_preimage',
    'selected_parameters', 'selected_descriptors_bound', 'selected_context_bound',
    'selected_learned_acceptance_bound', 'selected_encoding_edges',
))
LABELS = (
    'ProducerPreimages', 'WrongHashDomain', 'MissingDomainNul', 'WrongGrammarSeedContext',
    'WrongSeedWindow', 'WrongSeedDigest', 'ChangedProgramPreimage', 'WrongFeatureSeed',
    'WrongTieCount', 'WrongFreezeCandidate', 'NoncanonicalObjectOrder',
    'TruncatedPreimage', 'WrongDescriptorBinding',
)


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked producer preimages template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'producer preimages template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = program_metadata_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _definition(name: str, kind: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + kind + ' := ' + value + '\n'


def _record(value: dict) -> str:
    return ('{ json := ' + _raw_image(bytes.fromhex(value['json_hex'])) +
            ', preimage := ' + _raw_image(bytes.fromhex(value['preimage_hex'])) +
            ', digest := ' + string(value['digest']) + ' }')


def _row(value: dict) -> str:
    return ('{ key := ' + string(value['key']) + ', grammarSeed := ' + _record(value['grammar_seed']) +
            ', program := ' + _record(value['program']) + ', feature := ' + _record(value['feature']) +
            ', ties := [' + ', '.join(map(_record, value['ties'])) + '] }')


def _target(index: int) -> str:
    return ('{ descriptor := Phase17Metadata.candidateDescriptor' + str(index) +
            ', rowPublic := Phase17Metadata.publicRow' + str(index) +
            ', image := Phase17Metadata.candidateImage' + str(index) + ' }')


def _context_definitions(packet: dict) -> str:
    producer = packet['producer']
    text = _definition('selectedView', 'View',
        '{ context := Phase17Metadata.publicContext, predecessorState := ' +
        'Phase17Joint.producerBinding.historicalState, challengeCommitment := ' +
        'Phase17Joint.producerBinding.challenge }')
    planner = packet['program_metadata_packet']['planner_refinement_packet']
    text += _definition('plannerHash', 'String',
        '((Phase17LearnedBinding.observedBefore.package.planner.find? (fun file => '
        'file.path == "base/model/phase15_planner/weights.i16le.bin")).map '
        'Phase17LearnedBinding.FileRef.digest).getD ""')
    # Earlier selected Lean modules do not export the ranking-seed scalar.
    # Its syntax and uses are checked; authenticity remains supplied, alongside
    # authenticity of the imported digest records and SHA-256 computation.
    text += _definition('suppliedRankingSeed', 'String', string(planner['ranking']['seed_digest']))
    return text


def _definitions(packet: dict) -> str:
    producer = packet['producer']
    text = _context_definitions(packet)
    text += _definition('rankingSeedRecord', 'HashRecord', _record(producer['ranking_seed']))
    text += _definition('freezeRecord', 'HashRecord', _record(producer['freeze']))
    for index, row in enumerate(producer['rows']):
        text += _definition('record' + str(index), 'RowRecords', _row(row))
        text += _definition('target' + str(index), 'RowTarget', _target(index))
    text += _definition('rowRecords', 'List RowRecords', '[' + ', '.join(f'record{i}' for i in range(32)) + ']')
    text += _definition('rowTargets', 'List RowTarget', '[' + ', '.join(f'target{i}' for i in range(32)) + ']')
    text += '''
noncomputable def derivedImages : List (String × List Nat) :=
  rowRecords.map (fun record => (record.program.digest, record.program.json))

noncomputable def derivedPublicRows : List Phase17Metadata.PublicRow :=
  rowRecords.map (fun record =>
    { key := record.program.digest, featureDigest := record.feature.digest,
      tieDigests := record.ties.map HashRecord.digest })

noncomputable def derivedDescriptors : Option (List Phase17Metadata.Descriptor) :=
  (rowRecords.zip rowTargets).mapM (fun pair =>
    derivedDescriptor selectedView pair.2.descriptor.family pair.2.descriptor.variant
      pair.1.grammarSeed.digest)

'''
    return text


def _row_certificates() -> str:
    text = ''
    for index in range(32):
        text += f'''theorem row_checked_{index} :
    RowChecked selectedView plannerHash rankingSeedRecord.digest record{index} target{index} := by
  decide +kernel

theorem descriptor_checked_{index} :
    derivedDescriptor selectedView target{index}.descriptor.family target{index}.descriptor.variant
      record{index}.grammarSeed.digest = some target{index}.descriptor := row_checked_{index}.2.1

'''
    text += '''theorem all_rows_checked :
    List.Forall₂ (RowChecked selectedView plannerHash rankingSeedRecord.digest) rowRecords rowTargets := by
  exact ''' + ''.join(f'(List.Forall₂.cons row_checked_{index} ' for index in range(32)) + 'List.Forall₂.nil' + ')' * 32 + '\n\n'
    return text


PROJECTIONS = '''
/-- Transport checked row projections without reducing the complete captured
    byte lists again when composing the selected certificate. -/
theorem ties_project (view : View) (target : RowTarget) (records : List HashRecord)
    (checked : TiesChecked view target records) :
    records.map HashRecord.digest = target.rowPublic.tieDigests := by
  apply List.ext_getElem
  · simp only [List.length_map, checked.1, checked.2.1]
  · intro index leftBound rightBound
    have bound : index < records.length := by simpa only [List.length_map] using leftBound
    have member : (records[index], index) ∈ records.zipIdx := by
      apply List.mk_mem_zipIdx_iff_getElem?.mpr
      exact List.getElem?_eq_getElem bound
    have allTies : ∀ pair ∈ records.zipIdx,
        decide (TieChecked view target pair.2 pair.1) = true :=
      List.all_eq_true.mp checked.2.2
    have tieDecision : decide (TieChecked view target index records[index]) = true :=
      allTies (records[index], index) member
    have tie : TieChecked view target index records[index] := of_decide_eq_true tieDecision
    simpa only [List.getElem_map, List.getD_eq_getElem?_getD,
      List.getElem?_eq_getElem rightBound, Option.getD_some] using tie.2

theorem descriptors_project (view : View) (plannerHash rankingSeed : String)
    (records : List RowRecords) (targets : List RowTarget)
    (checked : List.Forall₂ (RowChecked view plannerHash rankingSeed) records targets) :
    (records.zip targets).mapM (fun pair =>
      derivedDescriptor view pair.2.descriptor.family pair.2.descriptor.variant
        pair.1.grammarSeed.digest) = some (targets.map RowTarget.descriptor) := by
  induction checked with
  | nil => rfl
  | cons head tail ih =>
      simp only [List.zip_cons_cons, List.mapM_cons, head.2.1, ih, List.map_cons]
      rfl

theorem images_project (view : View) (plannerHash rankingSeed : String)
    (records : List RowRecords) (targets : List RowTarget)
    (checked : List.Forall₂ (RowChecked view plannerHash rankingSeed) records targets) :
    records.map (fun record => (record.program.digest, record.program.json)) =
      targets.map (fun target => (target.rowPublic.key, target.image)) := by
  induction checked with
  | nil => rfl
  | cons head tail ih =>
      simp only [List.map_cons, head.2.2.2.1, head.2.2.2.2.2.1, ih]

theorem public_row_project (view : View) (plannerHash rankingSeed : String)
    (record : RowRecords) (target : RowTarget)
    (checked : RowChecked view plannerHash rankingSeed record target) :
    ({ key := record.program.digest, featureDigest := record.feature.digest,
       tieDigests := record.ties.map HashRecord.digest } : Phase17Metadata.PublicRow) =
      target.rowPublic := by
  rw [checked.2.2.2.2.2.1, checked.2.2.2.2.2.2.2.1,
    ties_project view target record.ties checked.2.2.2.2.2.2.2.2]

theorem public_rows_project (view : View) (plannerHash rankingSeed : String)
    (records : List RowRecords) (targets : List RowTarget)
    (checked : List.Forall₂ (RowChecked view plannerHash rankingSeed) records targets) :
    records.map (fun record =>
      ({ key := record.program.digest, featureDigest := record.feature.digest,
         tieDigests := record.ties.map HashRecord.digest } : Phase17Metadata.PublicRow)) =
      targets.map RowTarget.rowPublic := by
  induction checked with
  | nil => rfl
  | cons head tail ih =>
      simp only [List.map_cons, public_row_project _ _ _ _ _ head, ih]

'''


POSITIVE = '''
theorem selected_context_projection :
    selectedView.context = Phase17Metadata.publicContext ∧
    selectedView.predecessorState = Phase17Joint.producerBinding.historicalState ∧
    selectedView.challengeCommitment = Phase17Joint.producerBinding.challenge ∧
    ((Phase17LearnedBinding.observedBefore.package.planner.find? (fun file =>
      file.path == "base/model/phase15_planner/weights.i16le.bin")).map
      (fun file => (file.size, file.digest))) = some (65536, plannerHash) ∧
    ((Phase17LearnedBinding.observedAfter.package.planner.find? (fun file =>
      file.path == "base/model/phase15_planner/weights.i16le.bin")).map
      (fun file => (file.size, file.digest))) = some (65536, plannerHash) ∧
    selectedView.context.familyCounts = Phase17Metadata.beforeRegistry.counts ∧
    selectedView.context.familyCounts = Phase17Metadata.afterRegistry.counts ∧
    (rowTargets.map RowTarget.descriptor) = Phase17Metadata.candidateDescriptors ∧
    (rowTargets.map RowTarget.rowPublic) = Phase17Metadata.publicRows ∧
    rowTargets.length = 32 ∧ rowRecords.length = 32 ∧
    Phase17Provenance.selectedContext.rows.length = 32 ∧
    Phase17Planner.rowInputs.length = 32 := by
  refine ⟨rfl, rfl, rfl, ?_, ?_, ?_, ?_, rfl, rfl, rfl, rfl, rfl, rfl⟩
  all_goals decide +kernel

theorem selected_ranking_seed_preimage :
    HashInputChecked (rankingSeedValue selectedView) rankingSeedRecord ∧
    rankingSeedRecord.digest = suppliedRankingSeed := by decide +kernel

theorem selected_grammar_seed_preimages :
    List.Forall₂ (fun record target =>
      HashInputChecked (grammarSeedValue selectedView target.descriptor.family
        target.descriptor.variant) record.grammarSeed) rowRecords rowTargets := by
  exact project_rows all_rows_checked (fun _ _ checked => checked.1)

theorem selected_program_preimages :
    List.Forall₂ (fun record target =>
      HashInputChecked (descriptorValue target.descriptor) record.program ∧
      record.program.json = target.image ∧ record.program.digest = target.rowPublic.key)
      rowRecords rowTargets := by
  exact project_rows all_rows_checked (fun _ _ checked =>
    ⟨checked.2.2.1, checked.2.2.2.1, checked.2.2.2.2.2.1⟩)

theorem selected_feature_preimages :
    List.Forall₂ (fun record target =>
      HashInputChecked (featureValue selectedView plannerHash rankingSeedRecord.digest
        target.descriptor) record.feature ∧ record.feature.digest = target.rowPublic.featureDigest)
      rowRecords rowTargets := by
  exact project_rows all_rows_checked (fun _ _ checked =>
    ⟨checked.2.2.2.2.2.2.1, checked.2.2.2.2.2.2.2.1⟩)

theorem selected_tie_preimages :
    List.Forall₂ (fun record target => TiesChecked selectedView target record.ties)
      rowRecords rowTargets := by
  exact project_rows all_rows_checked (fun _ _ checked => checked.2.2.2.2.2.2.2.2)

theorem selected_freeze_preimage :
    HashInputChecked (freezeValue selectedView Phase17Provenance.selectedContext.rows
      Phase17Metadata.candidateDescriptors) freezeRecord ∧
    freezeRecord.digest = Phase17Planner.freezeDigest ∧
    Phase17Provenance.selectedContext.rows.length = Phase17Metadata.candidateDescriptors.length ∧
    Phase17Metadata.candidateDescriptors.length = 32 := by decide +kernel

theorem selected_parameters :
    List.Forall₂ (fun record target =>
      derivedDescriptor selectedView target.descriptor.family target.descriptor.variant
        record.grammarSeed.digest = some target.descriptor) rowRecords rowTargets ∧
    completeRows selectedView plannerHash rankingSeedRecord.digest rowRecords rowTargets = true := by
  exact ⟨project_rows all_rows_checked (fun _ _ checked => checked.2.1),
    row_certificates_compose _ _ _ _ _ all_rows_checked⟩

theorem selected_descriptors_bound :
    derivedDescriptors = some Phase17Metadata.candidateDescriptors ∧
    derivedImages = Phase17Metadata.candidateImages ∧
    derivedPublicRows = Phase17Metadata.publicRows := by
  exact ⟨descriptors_project _ _ _ _ _ all_rows_checked,
    images_project _ _ _ _ _ all_rows_checked,
    public_rows_project _ _ _ _ _ all_rows_checked⟩

/-- The reconstruction consumes the W records, whose complete encodings and
    seeded descriptor interpretation have been checked above. Hash output
    correctness remains a supplied premise of this selected reference chain. -/
theorem selected_context_bound :
    Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.beforeImage
      freezeRecord.digest selectedView.context Phase17Metadata.beforeImages derivedPublicRows derivedImages =
        some Phase17Finite.selectedConfiguration.context ∧
    Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.afterImage
      freezeRecord.digest selectedView.context Phase17Metadata.afterImages derivedPublicRows derivedImages =
        some Phase17Finite.selectedConfiguration.context := by
  rw [selected_descriptors_bound.2.1, selected_descriptors_bound.2.2,
    selected_freeze_preimage.2.1, selected_context_projection.1]
  exact Phase17Metadata.selected_context_bound

theorem selected_learned_acceptance_bound :
    ∃ context : Phase17Provenance.Context,
      completeRows selectedView plannerHash rankingSeedRecord.digest rowRecords rowTargets = true ∧
      HashInputChecked (rankingSeedValue selectedView) rankingSeedRecord ∧
      HashInputChecked (freezeValue selectedView Phase17Provenance.selectedContext.rows
        Phase17Metadata.candidateDescriptors) freezeRecord ∧
      derivedDescriptors = some Phase17Metadata.candidateDescriptors ∧
      Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.beforeImage
        freezeRecord.digest selectedView.context Phase17Metadata.beforeImages derivedPublicRows derivedImages = some context ∧
      Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.afterImage
        freezeRecord.digest selectedView.context Phase17Metadata.afterImages derivedPublicRows derivedImages = some context ∧
      context = Phase17Finite.selectedConfiguration.context ∧
      Phase17Provenance.Produced context Phase17Finite.selectedEvidence.proposal ∧
      Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
        Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
        (Phase17Finite.packet Phase17Finite.selectedConfiguration
          Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  exact ⟨Phase17Provenance.selectedContext, selected_parameters.2,
    selected_ranking_seed_preimage.1, selected_freeze_preimage.1,
    selected_descriptors_bound.1, selected_context_bound.1, selected_context_bound.2,
    rfl, Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted⟩

theorem selected_encoding_edges :
    encode .null = some [110, 117, 108, 108] ∧
    encode (.boolean true) = some [116, 114, 117, 101] ∧
    encode (.integer (-1)) = some [45, 49] ∧
    encode (.integer (-9223372036854775808)) = some (ascii "-9223372036854775808") ∧
    encode (.integer 9223372036854775807) = some (ascii "9223372036854775807") ∧
    encode (.integer 9223372036854775808) = none ∧
    encode (.integer (-9223372036854775809)) = none ∧
    encode (.array []) = some [91, 93] ∧ encode (.object []) = some [123, 125] ∧
    encode (.object [("b", .null), ("a", .null)]) = none ∧
    encode (.object [("a", .null), ("a", .null)]) = none ∧
    quoted "é" = none ∧ quoted (String.ofList [Char.ofNat 34]) = none ∧
    quoted (String.ofList [Char.ofNat 92]) = none ∧
    parameter "0000000000000000000000000000000000000000000000000000000000000000" 0 = some (-16) ∧
    parameter "0000002000000000000000000000000000000000000000000000000000000000" 0 = some 16 ∧
    parameter "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" 0 = some (-13) ∧
    parameter "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" 0 =
      parameter "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" 28 ∧
    window "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" 27 = some 1737075661 ∧
    parameter "000000000000000000000000000000000000000000000000000000000000000g" 0 = none ∧
    parameter "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" 0 = none ∧
    parameter "0" 0 = none ∧
    parameter "0000000000000000000000000000000000000000000000000000000000000000" 9223372036854775808 = none ∧
    domain.length = 26 ∧ domain.getLast? = some 0 := by decide +kernel
'''


def _mutated_record(record: dict, value: object) -> dict:
    result = copy.deepcopy(record)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    result['json_hex'] = raw.hex()
    result['preimage_hex'] = (b'RCPRCLM-CANONICAL-JSON-V2\0' + raw).hex()
    return result


def _controls(packet: dict, negative: str) -> tuple[str, str]:
    producer = packet['producer']
    text = _context_definitions(packet)
    row = copy.deepcopy(producer['rows'][0])
    descriptor = json.loads(bytes.fromhex(row['program']['json_hex']))
    family = FAMILIES.index(descriptor['family'])
    variant = descriptor['variant']
    text += _definition('target', 'RowTarget', _target(0))
    if negative in ('WrongHashDomain', 'MissingDomainNul', 'TruncatedPreimage'):
        record = copy.deepcopy(producer['ranking_seed'])
        raw = bytes.fromhex(record['preimage_hex'])
        if negative == 'WrongHashDomain':
            raw = b'X' + raw[1:]
        elif negative == 'MissingDomainNul':
            raw = raw[:25] + raw[26:]
        else:
            raw = raw[:-1]
        record['preimage_hex'] = raw.hex()
        text += _definition('changed', 'HashRecord', _record(record))
        return text, 'HashInputChecked (rankingSeedValue selectedView) changed'
    if negative == 'WrongSeedWindow':
        from .producer_preimages import signed_parameter
        offset = family + variant
        seed = row['grammar_seed']['digest']
        different = next(index for index in range(28)
                         if signed_parameter(seed, index) != descriptor['parameter_a'])
        require(different != offset, 'wrong-window control must differ from declared offset')
        return text, ('parameter ' + string(seed) + ' ' + str(different) +
                      ' = some target.descriptor.a')
    if negative == 'WrongSeedDigest':
        from .producer_preimages import signed_parameter
        seed = row['grammar_seed']['digest']
        offset = family + variant
        start = (offset * 2) % 56
        changed = next(seed[:start] + nibble + seed[start+1:] for nibble in '0123456789abcdef'
                       if signed_parameter(seed[:start] + nibble + seed[start+1:], offset) != descriptor['parameter_a'])
        return text, ('derivedDescriptor selectedView ' + str(family) + ' ' + str(variant) +
                      ' ' + string(changed) + ' = some target.descriptor')
    if negative == 'WrongDescriptorBinding':
        text += _definition('changed', 'HashRecord', _record(row['program']))
        return text, 'changed.json = Phase17Metadata.candidateImage1'
    if negative == 'NoncanonicalObjectOrder':
        return text, ('encode (.object [("z", .integer 0), ("a", .integer 1)]) = '
                      'some (ascii ' + string('{"z":0,"a":1}') + ')')
    if negative == 'WrongFreezeCandidate':
        value = json.loads(bytes.fromhex(producer['freeze']['json_hex']))
        value['candidates'][0]['base_score'] += 1
        text += _definition('changed', 'HashRecord', _record(_mutated_record(producer['freeze'], value)))
        return text, ('HashInputChecked (freezeValue selectedView Phase17Provenance.selectedContext.rows '
                      'Phase17Metadata.candidateDescriptors) changed')
    if negative == 'WrongGrammarSeedContext':
        value = json.loads(bytes.fromhex(row['grammar_seed']['json_hex']))
        value['promotion_index'] += 1
        text += _definition('changed', 'HashRecord', _record(_mutated_record(row['grammar_seed'], value)))
        return text, ('HashInputChecked (grammarSeedValue selectedView target.descriptor.family '
                      'target.descriptor.variant) changed')
    if negative == 'ChangedProgramPreimage':
        descriptor['parameter_a'] += 1
        text += _definition('changed', 'HashRecord', _record(_mutated_record(row['program'], descriptor)))
        return text, 'HashInputChecked (descriptorValue target.descriptor) changed'
    if negative == 'WrongFeatureSeed':
        value = json.loads(bytes.fromhex(row['feature']['json_hex']))
        value['seed'] = ('0' if value['seed'][0] != '0' else '1') + value['seed'][1:]
        text += _definition('changed', 'HashRecord', _record(_mutated_record(row['feature'], value)))
        return text, 'HashInputChecked (featureValue selectedView plannerHash suppliedRankingSeed target.descriptor) changed'
    if negative == 'WrongTieCount':
        value = json.loads(bytes.fromhex(row['ties'][0]['json_hex']))
        value['family_count'] += 1
        text += _definition('changed', 'HashRecord', _record(_mutated_record(row['ties'][0], value)))
        return text, 'TieChecked selectedView target 0 changed'
    raise AssertionError('unknown producer preimages negative control')


def _render_validated(prepared: PreparedProducerPreimages, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import Phase17VDependency\n\nset_option Elab.async false\n\n' +
            template(source_root).decode('utf-8'))
    text += '\nnamespace Phase17Preimages\nopen RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 32000000\n'
    text += '-- Fresh W packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    packet = prepared.packet
    if negative is None:
        text += _definitions(packet)
        text += PROJECTIONS
        text += _row_certificates()
        text += POSITIVE
    else:
        definitions, proposition = _controls(packet, negative)
        text += definitions
        text += ('theorem control_false :\n'
                 '    decide (' + proposition + ') = false := by\n'
                 + ('  decide +kernel\n\n' if negative == 'WrongFreezeCandidate' else
                    '  with_unfolding_all rfl\n\n') +
                 'theorem rejected_control :\n'
                 '    ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  simp only [h]\n'
                 '  decide +kernel\n')
    text += '\nend Phase17Preimages\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw),
            'forbidden producer preimages proof token')
    return raw


def _dependencies_validated(prepared: PreparedProducerPreimages, *, source_root: Path) -> dict[str, bytes]:
    metadata = prepared.program_metadata()
    result = program_metadata_lean._dependencies_validated(metadata, source_root=source_root)
    source = program_metadata_lean._render_validated(metadata, source_root=source_root)
    require(sha(source) == V_SOURCE_SHA, 'freshly generated V dependency differs from its exact pinned source')
    lines = source.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in program_metadata_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected),
            'exact V dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in source, 'unexpected V dependency output')
    result['Phase17VDependency'] = source
    require(tuple(result) == DEPENDENCY_LABELS, 'producer preimages dependency order differs')
    return result


def render(prepared: PreparedProducerPreimages, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedProducerPreimages and negative in (None, *LABELS[1:]),
            'exact producer preimages proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedProducerPreimages, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedProducerPreimages, 'exact producer preimages proof input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label)
               for label in LABELS}}
