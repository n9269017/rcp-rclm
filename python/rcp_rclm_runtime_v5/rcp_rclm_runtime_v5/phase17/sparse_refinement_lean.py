"""Render exact Phase 17R byte semantics and newly checked Q dependencies.

The complete sparse byte support comes from a checked round trip of every byte,
not a caller's score table. Expected score/mass observations remain fixed by the
separately anchored Q packet and are checked against the independent Lean
decoder. Only this module's named R audits count as new R audit outputs.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from . import finite_kernel_lean
from .materialized import require, sha
from .sparse_refinement import (PreparedSparseRefinement, validate_packet,
                                decode_tensor, encode_tensor, Q_SOURCE_SHA)

BRIDGE_PATH = 'lean/phase17_bridge/SparseByteRefinement.lean'
BRIDGE_SHA256 = 'cc312ee118b7939e0bf61a12df8611c5e8cfae3e78ae94890ad6f49668a04202'
COMMON_LABEL = 'Phase17QDependency'
NAMES = tuple('Phase17Sparse.' + name for name in (
    'signed16_range', 'clipped_score_range', 'dyadic_weight_positive',
    'row_probability_normalized', 'mass_binding_sound',
    'distribution_binding_sound', 'information_binding_sound',
    'selected_byte_images', 'selected_score_projection', 'selected_mass_projection',
    'selected_goal_decode', 'selected_information_transport',
    'selected_learned_acceptance_bound', 'selected_codec_edges', 'selected_decoder_edges',
))
LABELS = ('SparseRefinement', 'ChangedTensorByte', 'TransposedTensor',
          'AlteredProbability', 'WrongMarker', 'MissingEOS', 'InvalidByteRange',
          'WrongSignedBoundary', 'WrongGreedyTie')


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked sparse refinement template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'sparse refinement template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = finite_kernel_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _list(value: list) -> str:
    return '[' + ', '.join(_list(x) if type(x) is list else str(x) for x in value) + ']'


def _tree(rows: list[list[int]]) -> str:
    if not rows:
        return '.empty'
    middle = len(rows) // 2
    offset, value = rows[middle]
    return '(.node ' + _tree(rows[:middle]) + ' ' + str(offset) + ' ' + str(value) + ' ' + _tree(rows[middle + 1:]) + ')'


def _image(value: dict) -> str:
    return '{ byteLength := ' + str(value['byte_length']) + ', support := ' + _tree(value['nonzero_bytes']) + ' }'


def _common_source_validated(prepared: PreparedSparseRefinement, *, source_root: Path) -> bytes:
    raw = finite_kernel_lean.render(prepared.finite(), source_root=source_root)
    require(sha(raw) == Q_SOURCE_SHA, 'freshly generated Q dependency differs from its exact pinned source')
    lines = raw.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in finite_kernel_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected,
            'exact Q dependency audit removal required')
    result = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in result, 'unexpected Q dependency output')
    return result


def common_source(prepared: PreparedSparseRefinement, *, source_root: Path) -> bytes:
    require(type(prepared) is PreparedSparseRefinement, 'exact sparse refinement input required')
    validate_packet(prepared.packet)
    return _common_source_validated(prepared, source_root=source_root)


def _definitions(prepared: PreparedSparseRefinement, negative: str | None) -> tuple[str, int]:
    p = prepared.packet
    q = prepared.finite().protected().packet
    before, after = copy.deepcopy(p['before']), copy.deepcopy(p['after'])
    current = after['nonzero_bytes'][0][0] // 2 % 320
    require(current < 260, 'control must touch interpreted tensor region')
    markers, targets = copy.deepcopy(p['markers']), copy.deepcopy(p['targets'])
    if negative == 'ChangedTensorByte':
        after['nonzero_bytes'][0][1] -= 8
    elif negative == 'TransposedTensor':
        raw = decode_tensor(after)
        changed = bytearray(len(raw))
        for target in range(320):
            for context in range(320):
                src = 2 * (target * 320 + context)
                dst = 2 * (context * 320 + target)
                changed[dst:dst + 2] = raw[src:src + 2]
        after = encode_tensor(bytes(changed))
    elif negative == 'InvalidByteRange':
        after['nonzero_bytes'][0][1] = 256
    elif negative == 'WrongMarker':
        markers[0] = 0
    elif negative == 'MissingEOS':
        targets[0] = targets[0][:-1]
    text = 'def beforeImage : TensorImage := ' + _image(before) + '\n'
    text += 'def afterImage : TensorImage := ' + _image(after) + '\n'
    text += 'def expectedScores : List (List Int) := ' + _list(q['before']['score_dictionary']) + '\n'
    text += 'def expectedSelectors : List Nat := ' + _list(q['before']['row_selectors']) + '\n'
    text += 'def selectedMarkers : List Nat := ' + _list(markers) + '\n'
    text += 'def selectedTargets : List (List Nat) := ' + _list(targets) + '\n'
    return text, current


POSITIVE = r'''
theorem selected_byte_images :
    Canonical beforeImage ∧ Canonical afterImage ∧ beforeImage = afterImage := by
  unfold Canonical
  decide +kernel

__ROW_CERTIFICATES__

theorem selected_score_projection :
    ScoreBinding beforeImage expectedScores expectedSelectors ∧
    ScoreBinding afterImage expectedScores expectedSelectors ∧
    IntegralScores beforeImage ∧ IntegralScores afterImage := by
  have allRows := score_binding_from_rows beforeImage expectedScores expectedSelectors checked_rows
  rw [← selected_byte_images.2.2]
  exact ⟨allRows.1, allRows.1, allRows.2, allRows.2⟩

theorem selected_mass_projection :
    (∀ current < 260, Phase17Protected.rowAt Phase17Protected.observedBefore current =
      decodedRow beforeImage current) ∧
    (∀ current < 260, Phase17Protected.rowAt Phase17Protected.observedAfter current =
      decodedRow afterImage current) := by
  have beforeRows : Phase17Protected.observedBefore.rows = expectedScores.map massMinusOne := by decide +kernel
  have afterRows : Phase17Protected.observedAfter.rows = expectedScores.map massMinusOne := by decide +kernel
  have beforeSelectors : Phase17Protected.observedBefore.selectors = expectedSelectors := by decide +kernel
  have afterSelectors : Phase17Protected.observedAfter.selectors = expectedSelectors := by decide +kernel
  exact ⟨mass_binding_sound beforeImage expectedScores expectedSelectors
      Phase17Protected.observedBefore selected_score_projection.1 beforeRows beforeSelectors,
    mass_binding_sound afterImage expectedScores expectedSelectors
      Phase17Protected.observedAfter selected_score_projection.2.1 afterRows afterSelectors⟩

theorem selected_goal_decode :
    GoalBinding beforeImage selectedMarkers selectedTargets ∧
    GoalBinding afterImage selectedMarkers selectedTargets := by
  have before : GoalBinding beforeImage selectedMarkers selectedTargets := by
    unfold GoalBinding
    decide +kernel
  rw [← selected_byte_images.2.2]
  exact ⟨before, before⟩

theorem selected_information_transport :
    (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedBefore =
      decodedInformationSum beforeImage Phase17Protected.boundContract.positions ∧
    (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedAfter =
      decodedInformationSum afterImage Phase17Protected.boundContract.positions ∧
    decodedInformationSum afterImage Phase17Protected.boundContract.positions =
      decodedInformationSum beforeImage Phase17Protected.boundContract.positions := by
  have positions : ∀ position ∈ Phase17Protected.boundContract.positions, position.1 < 260 := by decide +kernel
  exact ⟨information_binding_sound beforeImage Phase17Protected.observedBefore
      selected_mass_projection.1 _ positions,
    information_binding_sound afterImage Phase17Protected.observedAfter
      selected_mass_projection.2 _ positions,
    congrArg (fun image => decodedInformationSum image Phase17Protected.boundContract.positions)
      selected_byte_images.2.2.symm⟩

/-- The existing selected finite-model acceptance now carries concrete decoded
    byte/probability/goal bindings. It is still not physical root acceptance. -/
theorem selected_learned_acceptance_bound :
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
    CapturedProjection beforeImage Phase17Protected.observedBefore selectedMarkers selectedTargets ∧
    CapturedProjection afterImage Phase17Protected.observedAfter selectedMarkers selectedTargets := by
  refine ⟨Phase17Finite.selected_learned_accepted, ?_, ?_⟩
  · exact ⟨selected_byte_images.1, selected_score_projection.2.2.1,
      selected_mass_projection.1, by decide +kernel, selected_goal_decode.1⟩
  · exact ⟨selected_byte_images.2.1, selected_score_projection.2.2.2,
      selected_mass_projection.2, by decide +kernel, selected_goal_decode.2⟩

theorem selected_codec_edges :
    signed16 0 128 = -32768 ∧ signed16 255 127 = 32767 ∧
    signed16 255 255 = -1 ∧ signed16 0 248 = -2048 ∧
    (-2049 : Int) / 2048 = -2 ∧ (-2049 : Int) % 2048 ≠ 0 ∧
    (-2048 : Int) / 2048 = -1 ∧ (-2048 : Int) % 2048 = 0 ∧
    clip (-16) = -15 ∧ clip 16 = 15 ∧
    massMinusOne [-16, -15] = [0, 0] ∧
    massMinusOne [-16, 15] = [0, 1073741823] := by decide +kernel

theorem selected_decoder_edges :
    greedyToken ([7, 7, 3] ++ List.replicate 257 0) = 0 ∧
    greedyToken ([1, 5, 5, 0] ++ List.replicate 256 0) = 1 ∧
    greedyToken ([-16, -15] ++ List.replicate 258 (-16)) = 1 ∧
    decodeWith (fun _ => List.replicate 258 0 ++ [1, 0]) 16 42 = ⟨[258], .eos⟩ ∧
    decodeWith (fun _ => List.replicate 256 0 ++ [1, 0, 0, 0]) 16 42 = ⟨[256], .nonByte⟩ ∧
    decodeWith (fun _ => 1 :: List.replicate 259 0) 2 42 = ⟨[0, 0], .limit⟩ := by decide +kernel
'''


def _row_certificates() -> str:
    declarations = []
    for current in range(260):
        declarations.append(
            'private theorem checked_row_' + str(current).zfill(3) +
            ' : RowFacts beforeImage expectedScores expectedSelectors ' + str(current) +
            ' := by\n  unfold RowFacts\n  decide +kernel\n')
    declarations.append('private theorem checked_rows (current : Nat) (bounded : current < 260) :\n'
                        '    RowFacts beforeImage expectedScores expectedSelectors current := by\n'
                        '  interval_cases current\n')
    for current in range(260):
        declarations.append('  · exact checked_row_' + str(current).zfill(3) + '\n')
    return '\n'.join(declarations)


def _render_validated(prepared: PreparedSparseRefinement, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import ' + COMMON_LABEL + '\n\nset_option Elab.async false\n\n' +
            template(source_root).decode('utf-8'))
    text += '\nnamespace Phase17Sparse\nopen RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 32000000\n'
    text += '-- Fresh R packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    declarations, current = _definitions(prepared, negative)
    text += declarations
    if negative is None:
        text += POSITIVE.replace('__ROW_CERTIFICATES__', _row_certificates())
    elif negative in ('ChangedTensorByte', 'TransposedTensor'):
        text += ('theorem rejected_control : decodedRow afterImage ' + str(current) +
                 ' = Phase17Protected.rowAt Phase17Protected.observedAfter ' + str(current) + ' := by decide\n')
    elif negative == 'AlteredProbability':
        q = prepared.finite().protected().packet['after']
        row = list(q['mass_minus_one_dictionary'][q['row_selectors'][0]])
        row[0] += 1
        text += 'def changedProbabilityRow : List Nat := ' + _list(row) + '\n'
        text += 'theorem rejected_control : decodedRow afterImage 0 = changedProbabilityRow := by decide\n'
    elif negative in ('WrongMarker', 'MissingEOS'):
        text += ('theorem rejected_control : GoalBinding afterImage selectedMarkers selectedTargets := by\n'
                 '  unfold GoalBinding\n  decide\n')
    elif negative == 'InvalidByteRange':
        text += 'theorem rejected_control : Canonical afterImage := by\n  unfold Canonical\n  decide\n'
    elif negative == 'WrongSignedBoundary':
        text += 'theorem rejected_control : signed16 0 128 = 32768 := by decide\n'
    elif negative == 'WrongGreedyTie':
        text += ('theorem rejected_control : greedyToken ([7, 7, 3] ++ List.replicate 257 0) = 1 '
                 ':= by decide\n')
    text += '\nend Phase17Sparse\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw),
            'forbidden sparse proof token')
    return raw


def render(prepared: PreparedSparseRefinement, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedSparseRefinement and negative in (None, *LABELS[1:]),
            'exact sparse refinement proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedSparseRefinement, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedSparseRefinement, 'exact sparse refinement input required')
    # Validate this one immutable input once for the entire source inventory.
    # Every case is rendered from that same object; no per-case packet override
    # or unvalidated external input is accepted by this batching path.
    validate_packet(prepared.packet)
    return {COMMON_LABEL: _common_source_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label)
               for label in LABELS}}
