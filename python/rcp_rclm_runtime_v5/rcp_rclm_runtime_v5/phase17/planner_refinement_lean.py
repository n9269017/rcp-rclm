"""Render complete planner-byte projection into Q's actual producer context.

The positive proof reads all 32,768 words in bounded kernel-checked blocks,
then checks each of the 32 complete score/tie rows separately and composes
their proofs into the complete table.  The expected table is
the actual imported Q context, not a separately supplied success observation.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from . import captured_json_lean
from .materialized import require, sha
from .planner_refinement import (
    PreparedPlannerRefinement, T_SOURCE_SHA, decode_planner, encode_planner,
    score_from_projection, validate_packet,
)
from .sparse_refinement_lean import _image
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/PlannerByteRefinement.lean'
BRIDGE_SHA256 = 'dbc53efad0add69b098e08d37223b0ad8da0b41a1cbc2553ec684047950da7b1'
DEPENDENCY_LABELS = ('Phase17QDependency', 'Phase17RDependency',
                     'Phase17SDependency', 'Phase17TDependency')
NAMES = tuple('Phase17Planner.' + name for name in (
    'hex_digit_bound', 'word_projection_sound', 'nonzero_word_covered',
    'projection_from_blocks', 'table_from_projection', 'context_reconstruction',
    'selected_byte_images', 'selected_complete_word_projection',
    'selected_all_score_terms', 'selected_all_tie_prefixes', 'selected_rows_bound',
    'selected_context_bound', 'selected_produced_trace',
    'selected_learned_acceptance_bound', 'selected_decoder_edges',
))
LABELS = (
    'PlannerRefinement', 'ChangedPlannerByte', 'SwappedPlannerEndian',
    'OmittedPlannerWord', 'InjectedPlannerWord', 'InvalidPlannerByte',
    'ChangedFeatureDigest', 'ChangedFamilyCount', 'ChangedProgramGeneration',
    'ChangedTieDigest', 'ChangedFreezeDigest', 'NonHexDigestSuffix', 'ChangedRowKey',
)


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked planner refinement template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'planner refinement template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = captured_json_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _nat(value: int) -> str:
    require(type(value) is int and 0 <= value < 2 ** 64, 'bounded planner natural literal')
    return str(value)


def _integer(value: int) -> str:
    require(type(value) is int and -(2 ** 63) <= value < 2 ** 63,
            'bounded planner integer literal')
    return '(' + str(value) + ')' if value < 0 else str(value)


def _projection(rows: list[list[int]]) -> str:
    return '[' + ', '.join('(' + _nat(index) + ', ' + _integer(value) + ')'
                           for index, value in rows) + ']'


def _row(row: dict) -> str:
    return ('{ key := ' + string(row['key']) + ', family := ' + _nat(row['family']) +
            ', variant := ' + _nat(row['program']['variant']) +
            ', generation := ' + _nat(row['program']['generation']) +
            ', familyCount := ' + _nat(row['family_count']) +
            ', featureDigest := ' + string(row['feature_digest']) +
            ', tieDigests := [' + ', '.join(map(string, row['tie_digests'])) + '] }')


def _changed_digit(text: str, index: int) -> str:
    alphabet = '0123456789abcdef'
    digit = alphabet[(alphabet.index(text[index]) + 1) % 16]
    return text[:index] + digit + text[index + 1:]


def _control_definitions(packet: dict, negative: str) -> tuple[str, str]:
    """Mutate actual bytes or public numeric inputs; keep the Q target fixed."""
    image = copy.deepcopy(packet['before'])
    projection = packet['before']['nonzero_words']
    declarations = 'def expectedProjection : List (Nat × Int) := ' + _projection(projection) + '\n'
    if negative in ('ChangedPlannerByte', 'SwappedPlannerEndian',
                    'OmittedPlannerWord', 'InjectedPlannerWord', 'InvalidPlannerByte'):
        word_index = projection[0][0]
        if negative == 'ChangedPlannerByte':
            image['nonzero_bytes'][0][1] = 254 if image['nonzero_bytes'][0][1] == 255 else image['nonzero_bytes'][0][1] + 1
        elif negative == 'SwappedPlannerEndian':
            raw = decode_planner(image)
            word_index = next(index for index in range(32768) if raw[2 * index] != raw[2 * index + 1])
            changed = bytearray(raw)
            for index in range(32768):
                changed[2 * index], changed[2 * index + 1] = raw[2 * index + 1], raw[2 * index]
            image = encode_planner(bytes(changed))
        elif negative == 'OmittedPlannerWord':
            image['nonzero_bytes'] = [entry for entry in image['nonzero_bytes']
                                      if entry[0] not in (2 * word_index, 2 * word_index + 1)]
        elif negative == 'InjectedPlannerWord':
            word_index = 32767
            require(all(entry[0] < 2 * word_index for entry in image['nonzero_bytes']),
                    'planner zero-complement control location changed')
            image['nonzero_bytes'].append([2 * word_index, 1])
        else:
            image['nonzero_bytes'][0][1] = 256
        declarations += 'def controlImage : PlannerImage := ' + _image(image) + '\n'
        if negative == 'InvalidPlannerByte':
            proposition = '(entries controlImage.support).all (fun entry => decide (entry.2 < 256)) = true'
        else:
            block = word_index // 256
            proposition = ('decodedBlock controlImage ' + str(block) +
                           ' = expectedBlock expectedProjection ' + str(block))
        return declarations, proposition
    if negative == 'ChangedFreezeDigest':
        declarations += 'def controlFreeze : String := ' + string(
            _changed_digit(packet['ranking']['freeze_digest'], 15)) + '\n'
        return declarations, 'decodedOffset controlFreeze = some Phase17Provenance.selectedContext.offset'
    row = copy.deepcopy(packet['ranking']['rows'][0])
    if negative == 'ChangedFeatureDigest':
        baseline = packet['before_table'][0]['base_score']
        for position in range(64):
            changed = _changed_digit(row['feature_digest'], position)
            value = score_from_projection(projection, changed, family=row['family'],
                variant=row['program']['variant'], generation=row['program']['generation'],
                family_count=row['family_count'])
            if value != baseline:
                row['feature_digest'] = changed
                break
        else:
            require(False, 'planner feature control did not change the numerical score')
    elif negative == 'ChangedFamilyCount':
        row['family_count'] += 1
    elif negative == 'ChangedProgramGeneration':
        row['program']['generation'] += 1
    elif negative == 'ChangedTieDigest':
        row['tie_digests'][0] = _changed_digit(row['tie_digests'][0], 0)
    elif negative == 'NonHexDigestSuffix':
        row['feature_digest'] = row['feature_digest'][:-1] + 'g'
    elif negative == 'ChangedRowKey':
        row['key'] = _changed_digit(row['key'], 0)
    else:
        require(False, 'unknown planner negative control')
    declarations += 'def controlRow : RowInput := ' + _row(row) + '\n'
    target = ('Phase17Provenance.selectedContext.rows.getD 0 '
              '{ key := "", family := 8, baseScore := 0, ties := [] }')
    return declarations, 'projectedRow expectedProjection controlRow = some (' + target + ')'


def _definitions(prepared: PreparedPlannerRefinement) -> str:
    packet = prepared.packet
    text = 'noncomputable def beforeImage : PlannerImage := ' + _image(packet['before']) + '\n'
    text += 'noncomputable def afterImage : PlannerImage := ' + _image(packet['after']) + '\n'
    text += 'noncomputable def expectedProjection : List (Nat × Int) := ' + _projection(packet['before']['nonzero_words']) + '\n'
    text += 'noncomputable def rowInputs : List RowInput := [\n  ' + ',\n  '.join(
        _row(row) for row in packet['ranking']['rows']) + '\n]\n'
    text += 'noncomputable def freezeDigest : String := ' + string(packet['ranking']['freeze_digest']) + '\n'
    text += 'noncomputable def selectedChoices : List Nat := [' + ', '.join(map(_nat, packet['selected_choices'])) + ']\n'
    return text


def _block_certificates() -> str:
    declarations = []
    for block in range(128):
        declarations.append('private theorem checked_block_' + str(block).zfill(3) +
            ' : decodedBlock beforeImage ' + str(block) + ' = expectedBlock expectedProjection ' +
            str(block) + ' := by decide +kernel\n')
    declarations.append('private theorem checked_blocks (block : Nat) (bounded : block < 128) :\n'
        '    decodedBlock beforeImage block = expectedBlock expectedProjection block := by\n'
        '  interval_cases block\n')
    for block in range(128):
        declarations.append('  · exact checked_block_' + str(block).zfill(3) + '\n')
    return '\n'.join(declarations)


def _row_certificates() -> str:
    declarations = [
        'private noncomputable def inputAt (index : Nat) : RowInput := rowInputs.getD index '
        '{ key := "", family := 0, variant := 0, generation := 0, familyCount := 0, '
        'featureDigest := "", tieDigests := [] }\n',
        'private noncomputable def targetAt (index : Nat) : Phase17Provenance.RankedProgram := '
        'Phase17Provenance.selectedContext.rows.getD index '
        '{ key := "", family := 0, baseScore := 0, ties := [] }\n',
    ]
    for row in range(32):
        declarations.append('private theorem checked_row_' + str(row).zfill(3) +
            ' : RowChecked expectedProjection (inputAt ' + str(row) + ') (targetAt ' +
            str(row) + ') := by\n  unfold RowChecked\n  decide +kernel\n')
    declarations.append('private theorem checked_rows :\n'
        '    List.Forall₂ (RowChecked expectedProjection) rowInputs '
        'Phase17Provenance.selectedContext.rows := by\n')
    for row in range(32):
        declarations.append('  refine List.Forall₂.cons checked_row_' + str(row).zfill(3) + ' ?_\n')
    declarations.append('  exact List.Forall₂.nil\n')
    return '\n'.join(declarations)


POSITIVE = r'''
theorem selected_byte_images :
    Canonical beforeImage ∧ Canonical afterImage ∧ beforeImage = afterImage := by
  unfold Canonical
  decide +kernel

__BLOCK_CERTIFICATES__

theorem selected_complete_word_projection :
    decodedProjection beforeImage = expectedProjection ∧
    decodedProjection afterImage = expectedProjection ∧ expectedProjection.length = 84 := by
  have before : decodedProjection beforeImage = expectedProjection :=
    projection_from_blocks beforeImage expectedProjection checked_blocks (by decide +kernel)
  rw [← selected_byte_images.2.2]
  exact ⟨before, before, by decide +kernel⟩

__ROW_CERTIFICATES__

theorem selected_all_score_terms :
    rowInputs.length = 32 ∧
    rowInputs.map (fun row => (hexDigits row.featureDigest).map
      (fun digits => (scoreTerms expectedProjection row digits).length)) =
      List.replicate 32 (some 84) ∧
    rowInputs.map (fun row => (hexDigits row.featureDigest).map
      (baseScore expectedProjection row)) =
      Phase17Provenance.selectedContext.rows.map (fun row => some row.baseScore) := by
  have assembled := checked_rows_compose expectedProjection rowInputs
    Phase17Provenance.selectedContext.rows checked_rows
  have rowLength : rowInputs.length = 32 := by decide +kernel
  have projectionLength : expectedProjection.length = 84 := by decide +kernel
  refine ⟨rowLength, ?_, assembled.2.1⟩
  simpa only [rowLength, projectionLength] using assembled.1

theorem selected_all_tie_prefixes :
    rowInputs.map (fun row => row.tieDigests.mapM prefix16) =
      Phase17Provenance.selectedContext.rows.map (fun row => some row.ties) ∧
    rowInputs.map (fun row => row.tieDigests.length) = List.replicate 32 5 ∧
    decodedOffset freezeDigest = some Phase17Provenance.selectedContext.offset := by
  have assembled := checked_rows_compose expectedProjection rowInputs
    Phase17Provenance.selectedContext.rows checked_rows
  refine ⟨assembled.2.2.1, ?_, by decide +kernel⟩
  simpa only [selected_all_score_terms.1] using assembled.2.2.2.1

theorem selected_rows_bound :
    decodedRows beforeImage rowInputs = some Phase17Provenance.selectedContext.rows ∧
    decodedRows afterImage rowInputs = some Phase17Provenance.selectedContext.rows := by
  have before : decodedRows beforeImage rowInputs = some Phase17Provenance.selectedContext.rows := by
    rw [table_from_projection beforeImage expectedProjection rowInputs
      selected_complete_word_projection.1]
    exact (checked_rows_compose expectedProjection rowInputs
      Phase17Provenance.selectedContext.rows checked_rows).2.2.2.2
  rw [← selected_byte_images.2.2]
  exact ⟨before, before⟩

theorem selected_context_bound :
    decodedContext Phase17Provenance.selectedContext beforeImage rowInputs freezeDigest =
      some Phase17Finite.selectedConfiguration.context ∧
    decodedContext Phase17Provenance.selectedContext afterImage rowInputs freezeDigest =
      some Phase17Finite.selectedConfiguration.context := by
  exact ⟨context_reconstruction _ _ _ _ selected_rows_bound.1 selected_all_tie_prefixes.2.2,
    context_reconstruction _ _ _ _ selected_rows_bound.2 selected_all_tie_prefixes.2.2⟩

/-- The whole selected proposal prefix uses the context reconstructed from
    the byte-derived table. Supplied digest preimages remain external inputs. -/
theorem selected_produced_trace :
    ∃ context : Phase17Provenance.Context,
      decodedContext Phase17Provenance.selectedContext beforeImage rowInputs freezeDigest = some context ∧
      context = Phase17Finite.selectedConfiguration.context ∧
      Phase17Provenance.Produced context Phase17Provenance.selectedProposal ∧
      selectedChoices = Phase17Provenance.selectedProposal.choices ∧
      Phase17Provenance.follows context [] selectedChoices = true := by
  refine ⟨Phase17Provenance.selectedContext, selected_context_bound.1, rfl,
    Phase17Provenance.selected_provenance, ?_, ?_⟩ <;> decide +kernel

/-- The selected finite acceptance carries both the producer numerical binding
    and T's captured JSON-to-package binding. This is not a physical or general
    autonomous-transition acceptance statement. -/
theorem selected_learned_acceptance_bound :
    ∃ context : Phase17Provenance.Context,
      decodedContext Phase17Provenance.selectedContext beforeImage rowInputs freezeDigest = some context ∧
      decodedContext Phase17Provenance.selectedContext afterImage rowInputs freezeDigest = some context ∧
      context = Phase17Finite.selectedConfiguration.context ∧
      Phase17Provenance.Produced context Phase17Finite.selectedEvidence.proposal ∧
      Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
        Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
        (Phase17Finite.packet Phase17Finite.selectedConfiguration
          Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
      Phase17Json.ImagesBound Phase17Json.beforeImages Phase17Routing.beforePackage ∧
      Phase17Json.ImagesBound Phase17Json.afterImages Phase17Routing.afterPackage ∧
      Phase17Json.decodePackage Phase17Json.beforeImages Phase17Routing.beforePackage.adapterImage =
        some Phase17Routing.beforePackage ∧
      Phase17Json.decodePackage Phase17Json.afterImages Phase17Routing.afterPackage.adapterImage =
        some Phase17Routing.afterPackage ∧
      Phase17Routing.RoutedGoalBinding Phase17Routing.beforePackage Phase17Sparse.beforeImage
        Phase17Routing.originalTasks Phase17Sparse.selectedTargets ∧
      Phase17Routing.RoutedGoalBinding Phase17Routing.afterPackage Phase17Sparse.afterImage
        Phase17Routing.originalTasks Phase17Sparse.selectedTargets := by
  exact ⟨Phase17Provenance.selectedContext, selected_context_bound.1, selected_context_bound.2,
    rfl, Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted,
    Phase17Json.selected_before_decode, Phase17Json.selected_after_decode,
    Phase17Json.selected_package_reconstruction.1, Phase17Json.selected_package_reconstruction.2,
    Phase17Routing.selected_routed_goals.1, Phase17Routing.selected_routed_goals.2⟩

theorem selected_decoder_edges :
    signed16 0 128 = -32768 ∧ signed16 255 127 = 32767 ∧
    signed16 255 255 = -1 ∧ signed16 1 0 = 1 ∧ signed16 0 1 = 256 ∧
    hexDigit 48 = some 0 ∧ hexDigit 57 = some 9 ∧ hexDigit 97 = some 10 ∧
    hexDigit 102 = some 15 ∧ hexDigit 65 = none ∧ hexDigit 103 = none ∧
    prefix16 "0000000000000000000000000000000000000000000000000000000000000000" = some 0 ∧
    prefix16 "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" = some 18446744073709551615 ∧
    decodedOffset "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" = some 31 ∧
    prefix16 "000000000000000000000000000000000000000000000000000000000000000g" = none ∧
    prefix16 "0" = none := by decide +kernel
'''


def _render_validated(prepared: PreparedPlannerRefinement, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import Phase17TDependency\n\nset_option Elab.async false\n\n' +
            template(source_root).decode('utf-8'))
    text += '\nnamespace Phase17Planner\nopen Phase17Sparse RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 32000000\n'
    text += '-- Fresh U packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    if negative is None:
        text += _definitions(prepared)
        text += POSITIVE.replace('__BLOCK_CERTIFICATES__', _block_certificates()).replace(
            '__ROW_CERTIFICATES__', _row_certificates())
    else:
        definitions, proposition = _control_definitions(prepared.packet, negative)
        text += definitions
        text += ('theorem control_false :\n'
                 '    decide (' + proposition + ') = false := by\n'
                 '  with_unfolding_all rfl\n\n'
                 'theorem rejected_control :\n'
                 '    ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  simp only [h]\n'
                 '  decide +kernel\n')
    text += '\nend Phase17Planner\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw),
            'forbidden planner refinement proof token')
    return raw


def _dependencies_validated(prepared: PreparedPlannerRefinement, *, source_root: Path) -> dict[str, bytes]:
    captured = prepared.captured_json()
    result = captured_json_lean._dependencies_validated(captured, source_root=source_root)
    source = captured_json_lean._render_validated(captured, source_root=source_root)
    require(sha(source) == T_SOURCE_SHA, 'freshly generated T dependency differs from its exact pinned source')
    lines = source.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in captured_json_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected),
            'exact T dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in source, 'unexpected T dependency output')
    result['Phase17TDependency'] = source
    require(tuple(result) == DEPENDENCY_LABELS, 'planner dependency order differs')
    return result


def render(prepared: PreparedPlannerRefinement, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedPlannerRefinement and negative in (None, *LABELS[1:]),
            'exact planner refinement proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedPlannerRefinement, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedPlannerRefinement, 'exact planner refinement proof input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label)
               for label in LABELS}}
