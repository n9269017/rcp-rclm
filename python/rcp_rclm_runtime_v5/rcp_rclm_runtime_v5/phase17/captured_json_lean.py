"""Emit exact captured JSON image certificates over the imported S values.

All eight complete raw images from each selected package become Lean inputs.
The target values are S's actual imported fields.  No new parsed value is
supplied as an alternative authority for a successful decoder result.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import prompt_routing_lean
from .captured_json import (PreparedCapturedJson, JSON_FIELDS, S_SOURCE_SHA,
                            document_bytes, validate_packet)
from .materialized import require, sha

BRIDGE_PATH = 'lean/phase17_bridge/CapturedJson.lean'
BRIDGE_SHA256 = '388e2b92ef1442067167e871508e1c10ca6770d7f1907b6bd90124ff729e9d0d'
DEPENDENCY_LABELS = ('Phase17QDependency', 'Phase17RDependency', 'Phase17SDependency')
NAMES = tuple('Phase17Json.' + name for name in (
    'decode_unique', 'decode_byte_domain', 'decode_consumes_all',
    'images_binding_sound', 'decoded_package_unique',
    'selected_image_inventory', 'selected_before_decode', 'selected_after_decode',
    'selected_package_reconstruction', 'selected_original_prompt_routing',
    'selected_routed_goals', 'selected_information_contexts',
    'selected_learned_acceptance_bound', 'selected_canonical_edge_cases',
    'selected_rejection_controls',
))
LABELS = ('CapturedJson', 'ChangedJsonByte', 'TruncatedJson', 'TrailingJsonByte',
          'DuplicateJsonKey', 'UnsortedJsonKeys', 'NonCanonicalInteger',
          'BooleanIntegerSubstitution', 'EscapedJsonString', 'NonAsciiJsonByte',
          'WrongJsonDocument', 'LeadingJsonWhitespace', 'OutOfByteRange')


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked captured JSON template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'captured JSON template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = prompt_routing_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _raw_image(raw: bytes) -> str:
    require(type(raw) is bytes and raw and all(byte < 128 for byte in raw),
            'complete ASCII JSON image literal required')
    # Bounded literal chunks avoid a single deeply nested syntax expression.
    # The enclosing captured-data definition needs no executable code; kernel
    # reduction still sees and checks every byte in its complete body.
    chunks = (raw[offset:offset + 256] for offset in range(0, len(raw), 256))
    return 'List.flatten [' + ', '.join(
        '[' + ', '.join(map(str, chunk)) + ']' for chunk in chunks) + ']'


def _images(name: str, images: dict[str, bytes]) -> str:
    require(tuple(images) == tuple(field for field, _ in JSON_FIELDS),
            'complete ordered JSON image inventory required')
    return 'noncomputable def ' + name + ' : PackageImages := {\n' + '\n'.join(
        '  ' + field + ' := ' + _raw_image(images[field]) for field, _ in JSON_FIELDS) + '\n}\n'


def _control_image(images: dict[str, bytes], negative: str) -> list[int]:
    """Mutate bytes only; the acceptance target remains the actual S memory AST."""
    raw = images['memory']
    require(b'"candidate_self_report_authoritative":false' in raw
            and b'"entry_count":1' in raw, 'selected control anchors changed')
    if negative == 'ChangedJsonByte':
        raw = raw.replace(b'"candidate_self_report_authoritative":false',
                          b'"candidate_self_report_authoritative":true', 1)
    elif negative == 'TruncatedJson':
        raw = raw[:-1]
    elif negative == 'TrailingJsonByte':
        raw += b'0'
    elif negative == 'DuplicateJsonKey':
        raw = b'{"candidate_self_report_authoritative":false,' + raw[1:]
    elif negative == 'UnsortedJsonKeys':
        # Reorder existing fields without changing their values or duplicating
        # keys. This use of JSON is only a deliberately invalid control maker.
        pairs = list(json.loads(raw).items())
        pairs[0], pairs[1] = pairs[1], pairs[0]
        raw = json.dumps(dict(pairs), ensure_ascii=True, separators=(',', ':')).encode('ascii')
    elif negative == 'NonCanonicalInteger':
        raw = raw.replace(b'"entry_count":1', b'"entry_count":01', 1)
    elif negative == 'BooleanIntegerSubstitution':
        raw = raw.replace(b'"entry_count":1', b'"entry_count":true', 1)
    elif negative == 'EscapedJsonString':
        raw = raw.replace(b'"candidate_self_report_authoritative"',
                          b'"candidate_self_report_authoritativ\\u0065"', 1)
    elif negative == 'NonAsciiJsonByte':
        raw = raw[:2] + b'\x80' + raw[3:]
    elif negative == 'WrongJsonDocument':
        raw = images['retrieval']
    elif negative == 'LeadingJsonWhitespace':
        raw = b' ' + raw
    elif negative == 'OutOfByteRange':
        return [256, *raw[1:]]
    else:
        require(False, 'unknown captured JSON negative control')
    return list(raw)


def _definitions(prepared: PreparedCapturedJson, negative: str | None) -> str:
    packet = prepared.packet
    before = document_bytes(packet, 'before')
    if negative is not None:
        raw = _control_image(before, negative)
        return 'def controlImage : List Nat := [' + ', '.join(map(str, raw)) + ']\n'
    after = document_bytes(packet, 'after')
    text = _images('beforeImages', before) + _images('afterImages', after)
    sizes = [len(before[field]) for field, _ in JSON_FIELDS]
    text += 'def expectedLengths : List Nat := [' + ', '.join(map(str, sizes)) + ']\n'
    text += 'def imageLengths (images : PackageImages) : List Nat := [' + ', '.join(
        'images.' + field + '.length' for field, _ in JSON_FIELDS) + ']\n'
    # Each distinct complete before-image is decoded against the exact field
    # imported from S. The after-image transport additionally checks equality
    # of both complete image collections and both imported package values.
    for field, _ in JSON_FIELDS:
        text += ('theorem before_' + field + '_decoded : decode beforeImages.' + field +
                 ' = some Phase17Routing.beforePackage.' + field + ' := by decide +kernel\n')
    return text


POSITIVE = r'''
theorem selected_image_inventory :
    imageLengths beforeImages = expectedLengths ∧ imageLengths afterImages = expectedLengths ∧
    expectedLengths.length = 8 ∧ expectedLengths.foldl Nat.add 0 = 51505 := by decide +kernel

theorem selected_before_decode : ImagesBound beforeImages Phase17Routing.beforePackage := by
  exact ⟨before_memory_decoded, before_retrieval_decoded, before_generator_decoded,
    before_planner_decoded, before_optimizer_decoded, before_resource_decoded,
    before_packageManifest_decoded, before_adapterManifest_decoded⟩

theorem selected_after_decode : ImagesBound afterImages Phase17Routing.afterPackage := by
  have sameImages : afterImages = beforeImages := by rfl
  have samePackages : Phase17Routing.afterPackage = Phase17Routing.beforePackage := by rfl
  rw [sameImages, samePackages]
  exact selected_before_decode

theorem selected_package_reconstruction :
    decodePackage beforeImages Phase17Routing.beforePackage.adapterImage = some Phase17Routing.beforePackage ∧
    decodePackage afterImages Phase17Routing.afterPackage.adapterImage = some Phase17Routing.afterPackage := by
  exact ⟨images_binding_sound _ _ selected_before_decode,
    images_binding_sound _ _ selected_after_decode⟩

theorem selected_original_prompt_routing :
    (∃ package, decodePackage beforeImages Phase17Routing.beforePackage.adapterImage = some package ∧
      RoutingBinding package Phase17Sparse.beforeImage Phase17Routing.originalTasks Phase17Sparse.selectedMarkers) ∧
    (∃ package, decodePackage afterImages Phase17Routing.afterPackage.adapterImage = some package ∧
      RoutingBinding package Phase17Sparse.afterImage Phase17Routing.originalTasks Phase17Sparse.selectedMarkers) := by
  exact ⟨⟨Phase17Routing.beforePackage, selected_package_reconstruction.1,
      Phase17Routing.selected_routing.1⟩,
    ⟨Phase17Routing.afterPackage, selected_package_reconstruction.2,
      Phase17Routing.selected_routing.2⟩⟩

theorem selected_routed_goals :
    (∃ package, decodePackage beforeImages Phase17Routing.beforePackage.adapterImage = some package ∧
      RoutedGoalBinding package Phase17Sparse.beforeImage Phase17Routing.originalTasks Phase17Sparse.selectedTargets) ∧
    (∃ package, decodePackage afterImages Phase17Routing.afterPackage.adapterImage = some package ∧
      RoutedGoalBinding package Phase17Sparse.afterImage Phase17Routing.originalTasks Phase17Sparse.selectedTargets) := by
  exact ⟨⟨Phase17Routing.beforePackage, selected_package_reconstruction.1,
      Phase17Routing.selected_routed_goals.1⟩,
    ⟨Phase17Routing.afterPackage, selected_package_reconstruction.2,
      Phase17Routing.selected_routed_goals.2⟩⟩

theorem selected_information_contexts :
    (decodePackage beforeImages Phase17Routing.beforePackage.adapterImage).map
      (fun package => routedPositions package Phase17Sparse.beforeImage
        Phase17Routing.originalTasks Phase17Sparse.selectedTargets) =
      some Phase17Protected.boundContract.positions ∧
    (decodePackage afterImages Phase17Routing.afterPackage.adapterImage).map
      (fun package => routedPositions package Phase17Sparse.afterImage
        Phase17Routing.originalTasks Phase17Sparse.selectedTargets) =
      some Phase17Protected.boundContract.positions := by
  constructor
  · rw [selected_package_reconstruction.1]
    exact congrArg some Phase17Routing.selected_information_contexts.1
  · rw [selected_package_reconstruction.2]
    exact congrArg some Phase17Routing.selected_information_contexts.2

/-- The parsed packages carry the original prompt semantics into the selected
    Q/R/S acceptance statement. Capture and external execution are unchanged
    obligations, and this is still the declared selected finite model. -/
theorem selected_learned_acceptance_bound :
    ∃ before after : Package,
      decodePackage beforeImages Phase17Routing.beforePackage.adapterImage = some before ∧
      decodePackage afterImages Phase17Routing.afterPackage.adapterImage = some after ∧
      ImagesBound beforeImages before ∧ ImagesBound afterImages after ∧
      Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
        Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
        (Phase17Finite.packet Phase17Finite.selectedConfiguration
          Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
      Phase17Sparse.CapturedProjection Phase17Sparse.beforeImage Phase17Protected.observedBefore
        Phase17Sparse.selectedMarkers Phase17Sparse.selectedTargets ∧
      Phase17Sparse.CapturedProjection Phase17Sparse.afterImage Phase17Protected.observedAfter
        Phase17Sparse.selectedMarkers Phase17Sparse.selectedTargets ∧
      RoutedGoalBinding before Phase17Sparse.beforeImage Phase17Routing.originalTasks Phase17Sparse.selectedTargets ∧
      RoutedGoalBinding after Phase17Sparse.afterImage Phase17Routing.originalTasks Phase17Sparse.selectedTargets ∧
      (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedBefore =
        Phase17Sparse.decodedInformationSum Phase17Sparse.beforeImage
          (routedPositions before Phase17Sparse.beforeImage Phase17Routing.originalTasks Phase17Sparse.selectedTargets) ∧
      (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedAfter =
        Phase17Sparse.decodedInformationSum Phase17Sparse.afterImage
          (routedPositions after Phase17Sparse.afterImage Phase17Routing.originalTasks Phase17Sparse.selectedTargets) := by
  refine ⟨Phase17Routing.beforePackage, Phase17Routing.afterPackage,
    selected_package_reconstruction.1, selected_package_reconstruction.2,
    selected_before_decode, selected_after_decode, ?_⟩
  exact Phase17Routing.selected_learned_acceptance_bound

theorem selected_canonical_edge_cases :
    decode [110,117,108,108] = some .null ∧
    decode [116,114,117,101] = some (.boolean true) ∧
    decode [102,97,108,115,101] = some (.boolean false) ∧
    decode [48] = some (.integer 0) ∧ decode [45,49] = some (.integer (-1)) ∧
    decode [34,32,97,32,34] = some (.string " a ") ∧
    decode [91,93] = some (.array []) ∧ decode [123,125] = some (.object []) ∧
    decode ([91,123,34,97,34,58,49,125,93]) = some (.array [.object [("a", .integer 1)]]) ∧
    decode (("-9223372036854775808" : String).toList.map Char.toNat) = some (.integer (-9223372036854775808)) ∧
    decode (("9223372036854775807" : String).toList.map Char.toNat) = some (.integer 9223372036854775807) ∧
    (decode (List.replicate 20 91 ++ [48] ++ List.replicate 20 93)).isSome = true := by decide +kernel

theorem selected_rejection_controls :
    decode [] = none ∧ decode [32,48] = none ∧ decode [48,32] = none ∧
    decode [48,48] = none ∧ decode [45,48] = none ∧ decode [43,49] = none ∧
    decode [49,46,48] = none ∧ decode [49,101,50] = none ∧
    decode [34,92,110,34] = none ∧ decode [34,128,34] = none ∧ decode [256] = none ∧
    decode [91,48,44,93] = none ∧ decode [123,34,97,34,58,48,44,125] = none ∧
    decode [123,34,97,34,58,48,44,34,97,34,58,49,125] = none ∧
    decode [123,34,98,34,58,48,44,34,97,34,58,49,125] = none ∧
    decode (("9223372036854775808" : String).toList.map Char.toNat) = none ∧
    decode (("-9223372036854775809" : String).toList.map Char.toNat) = none ∧
    decode (List.replicate 21 91 ++ [48] ++ List.replicate 21 93) = none := by decide +kernel
'''


def _render_validated(prepared: PreparedCapturedJson, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import Phase17SDependency\n\nset_option Elab.async false\n\n' +
            template(source_root).decode('utf-8'))
    text += '\nnamespace Phase17Json\nopen Phase17Routing RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 32000000\n'
    text += '-- Fresh T packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += _definitions(prepared, negative)
    if negative is None:
        text += POSITIVE
    else:
        # The Boolean witness is checked by definitional equality in the
        # kernel. Its failure is an rfl error, which the strict negative-output
        # checker rejects; an unchanged valid image cannot be counted as a
        # negative merely because a false witness failed to compile.
        text += ('theorem control_false :\n'
                 '    decide (decode controlImage = some Phase17Routing.beforePackage.memory) = false := by\n'
                 '  with_unfolding_all rfl\n\n'
                 'theorem rejected_control :\n'
                 '    decode controlImage = some Phase17Routing.beforePackage.memory := by\n'
                 '  have h : ¬ (decode controlImage = some Phase17Routing.beforePackage.memory) :=\n'
                 '    of_decide_eq_false control_false\n'
                 '  simp only [h]\n'
                 '  decide +kernel\n')
    text += '\nend Phase17Json\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw),
            'forbidden captured JSON proof token')
    return raw


def _dependencies_validated(prepared: PreparedCapturedJson, *, source_root: Path) -> dict[str, bytes]:
    routing = prepared.routing()
    result = prompt_routing_lean._dependencies_validated(routing, source_root=source_root)
    source = prompt_routing_lean._render_validated(routing, source_root=source_root)
    require(sha(source) == S_SOURCE_SHA, 'freshly generated S dependency differs from its exact pinned source')
    lines = source.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in prompt_routing_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected),
            'exact S dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in source, 'unexpected S dependency output')
    result['Phase17SDependency'] = source
    require(tuple(result) == DEPENDENCY_LABELS, 'captured JSON dependency order differs')
    return result


def render(prepared: PreparedCapturedJson, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedCapturedJson and negative in (None, *LABELS[1:]),
            'exact captured JSON proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedCapturedJson, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedCapturedJson, 'exact captured JSON proof input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label)
               for label in LABELS}}
