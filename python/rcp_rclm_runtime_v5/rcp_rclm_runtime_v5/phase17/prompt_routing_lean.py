"""Render the captured protected prompts and package objects into Lean routing.

The route interpreter receives the complete captured route lists and adapter
image. No Python-selected hit, family or effective marker is a Lean input.
The completed Q and R certificates are regenerated exactly and compiled as two
same-run dependencies by the S checker; only S's named audits are new S audits.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import sparse_refinement_lean
from .materialized import require, sha
from .prompt_routing import (PreparedPromptRouting, validate_packet, R_SOURCE_SHA,
                             ADAPTER_MANIFEST, PACKAGE_MANIFEST)

BRIDGE_PATH = 'lean/phase17_bridge/ProtectedRouting.lean'
BRIDGE_SHA256 = 'afc654851772188b36608cf5c2fc9cda0b5c3c7148afcbd035894e5971eff1ec'
DEPENDENCY_LABELS = ('Phase17QDependency', 'Phase17RDependency')
NAMES = tuple('Phase17Routing.' + name for name in (
    'unique_route_sound', 'duplicate_route_rejected', 'legacy_failure_restores_start',
    'unique_family_sound', 'routed_goal_binding_sound',
    'selected_adapter_images', 'selected_manifest_selection', 'selected_original_prompts',
    'selected_hidden_families', 'selected_legacy_chain', 'selected_routing',
    'selected_routed_goals', 'selected_information_contexts',
    'selected_learned_acceptance_bound', 'selected_edge_controls',
))
LABELS = ('PromptRouting', 'MissingRoute', 'MalformedRoute', 'DuplicateCommitment',
          'AmbiguousFamily', 'ChangedAdapterByte', 'AdapterOutOfBounds',
          'WrongPromptTerminal', 'WrongTaskBinding', 'WrongTensorManifest',
          'WrongLegacyRoute')


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked protected routing template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'protected routing template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = sparse_refinement_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _string(value: str) -> str:
    require(type(value) is str, 'literal string required')
    escapes = {'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r', '\t': '\\t'}
    return '"' + ''.join(escapes.get(c, '\\u{' + format(ord(c), 'x') + '}'
                                      if ord(c) < 32 else c) for c in value) + '"'


def _value(value: object) -> str:
    if value is None:
        return '.null'
    if type(value) is bool:
        return '(.boolean ' + str(value).lower() + ')'
    if type(value) is int:
        return '(.integer (' + str(value) + '))'
    if type(value) is str:
        return '(.string ' + _string(value) + ')'
    if type(value) is list:
        return '(.array [' + ', '.join(map(_value, value)) + '])'
    require(type(value) is dict and all(type(k) is str for k in value),
            'complete typed JSON object required')
    return '(.object [' + ', '.join('(' + _string(key) + ', ' + _value(item) + ')'
                                    for key, item in value.items()) + '])'


def _list(value: list) -> str:
    return sparse_refinement_lean._list(value)


def _image(value: dict) -> str:
    return sparse_refinement_lean._image(value)


def _package_inputs(capture: dict) -> dict:
    files = {row['path']: bytes.fromhex(row['hex']) for row in capture['files']}
    return {**copy.deepcopy(capture['route_objects']),
            'packageManifest': load_json_strict(files[PACKAGE_MANIFEST]),
            'adapterManifest': load_json_strict(files[ADAPTER_MANIFEST]),
            'adapterImage': copy.deepcopy(capture['adapter_image'])}


def _package(name: str, package: dict) -> str:
    fields = ('memory', 'retrieval', 'generator', 'planner', 'optimizer', 'resource',
              'packageManifest', 'adapterManifest')
    text = 'def ' + name + ' : Package := {\n'
    text += '\n'.join('  ' + key + ' := ' + _value(package[key]) for key in fields)
    return text + '\n  adapterImage := ' + _image(package['adapterImage']) + '\n}\n'


def _task(task: dict) -> str:
    challenge = task['challenge']
    rendered = 'none' if challenge is None else ('some { taskId := ' + _string(challenge['task_id']) +
              ', commitment := ' + _string(challenge['commitment_hash']) +
              ', slot := ' + str(challenge['slot_token_id']) + ' }')
    return '{ taskId := ' + _string(task['task_id']) + ', prompt := ' + \
        _list(list(bytes.fromhex(task['prompt_hex']))) + ', challenge := ' + rendered + ' }'


def _definitions(prepared: PreparedPromptRouting, negative: str | None) -> str:
    packet = prepared.packet
    before = _package_inputs(packet['before'])
    after = _package_inputs(packet['after'])
    tasks = copy.deepcopy(packet['tasks'])
    if negative == 'MissingRoute':
        after['retrieval']['entries'] = []
    elif negative == 'MalformedRoute':
        after['retrieval']['entries'][0]['route_marker_token_id'] = '84'
    elif negative == 'DuplicateCommitment':
        after['memory']['phase14_routes'].append(copy.deepcopy(after['memory']['phase14_routes'][0]))
    elif negative == 'AmbiguousFamily':
        row = copy.deepcopy(after['memory']['phase14_routes'][0])
        after['generator']['phase14_routes'].append(copy.deepcopy(row))
        after['planner']['phase14_routes'].append(row)
    elif negative == 'ChangedAdapterByte':
        require(after['adapterImage']['nonzero_bytes'][0] == [0, 87], 'adapter control byte differs')
        after['adapterImage']['nonzero_bytes'][0][1] = 88
    elif negative == 'AdapterOutOfBounds':
        after['optimizer']['phase14_routes'][0]['offset_bytes'] = 5120
    elif negative == 'WrongPromptTerminal':
        raw = bytearray.fromhex(tasks[0]['prompt_hex'])
        raw[-1] = 0
        tasks[0]['prompt_hex'] = bytes(raw).hex()
    elif negative == 'WrongTaskBinding':
        task = next(row for row in tasks if row['challenge'] is not None)
        task['challenge']['task_id'] = 'different-task'
    elif negative == 'WrongTensorManifest':
        after['packageManifest']['tensor_manifest_hash'] = '0' * 64
    elif negative == 'WrongLegacyRoute':
        after['planner']['routes'][0]['route_marker_token_id'] = 86
    text = _package('beforePackage', before) + _package('afterPackage', after)
    text += 'def originalTasks : List Task := [\n  ' + ',\n  '.join(map(_task, tasks)) + '\n]\n'
    text += 'def expectedOriginalMarkers : List Nat := ' + _list([t['original_marker'] for t in packet['tasks']]) + '\n'
    text += 'def expectedAdapterHash : String := ' + _string(packet['before']['adapter_sha256']) + '\n'
    text += 'def expectedTensorManifestHash : String := ' + _string(packet['before']['tensor_manifest_hash']) + '\n'
    return text


POSITIVE = r'''
theorem selected_adapter_images :
    CanonicalAdapter beforePackage.adapterImage ∧ CanonicalAdapter afterPackage.adapterImage ∧
    beforePackage.adapterImage = afterPackage.adapterImage := by
  unfold CanonicalAdapter
  decide +kernel

theorem selected_manifest_selection :
    selectedAdapterShape beforePackage = true ∧ selectedAdapterShape afterPackage = true ∧
    selectedAdapterHash beforePackage = some expectedAdapterHash ∧
    selectedAdapterHash afterPackage = some expectedAdapterHash ∧
    tensorManifestHash beforePackage = some expectedTensorManifestHash ∧
    tensorManifestHash afterPackage = some expectedTensorManifestHash := by decide +kernel

theorem selected_original_prompts :
    originalTasks.length = 11 ∧ originalTasks.all promptBound = true ∧
    originalTasks.map (fun task => task.prompt.getLast?.getD 0) = expectedOriginalMarkers := by decide +kernel

theorem selected_hidden_families :
    originalTasks.map (fun task => (route beforePackage Phase17Sparse.beforeImage task).family) =
      [none, none, none, none, none, none, none, some .memoryRetrieval, some .modelWeights,
        some .adapterOptimizer, some .generatorPlanner] ∧
    originalTasks.map (fun task => (route afterPackage Phase17Sparse.afterImage task).family) =
      [none, none, none, none, none, none, none, some .memoryRetrieval, some .modelWeights,
        some .adapterOptimizer, some .generatorPlanner] := by decide +kernel

theorem selected_legacy_chain :
    legacyChain beforePackage 87 = ⟨84, true⟩ ∧ legacyChain beforePackage 86 = ⟨84, true⟩ ∧
    legacyChain beforePackage 85 = ⟨84, true⟩ ∧ legacyChain afterPackage 87 = ⟨84, true⟩ ∧
    legacyChain afterPackage 86 = ⟨84, true⟩ ∧ legacyChain afterPackage 85 = ⟨84, true⟩ := by decide +kernel

theorem selected_routing :
    RoutingBinding beforePackage Phase17Sparse.beforeImage originalTasks Phase17Sparse.selectedMarkers ∧
    RoutingBinding afterPackage Phase17Sparse.afterImage originalTasks Phase17Sparse.selectedMarkers := by
  unfold RoutingBinding
  decide +kernel

theorem selected_routed_goals :
    RoutedGoalBinding beforePackage Phase17Sparse.beforeImage originalTasks Phase17Sparse.selectedTargets ∧
    RoutedGoalBinding afterPackage Phase17Sparse.afterImage originalTasks Phase17Sparse.selectedTargets := by
  exact ⟨routed_goal_binding_sound _ _ _ _ _ selected_routing.1 Phase17Sparse.selected_goal_decode.1,
    routed_goal_binding_sound _ _ _ _ _ selected_routing.2 Phase17Sparse.selected_goal_decode.2⟩

theorem selected_information_contexts :
    routedPositions beforePackage Phase17Sparse.beforeImage originalTasks Phase17Sparse.selectedTargets =
      Phase17Protected.boundContract.positions ∧
    routedPositions afterPackage Phase17Sparse.afterImage originalTasks Phase17Sparse.selectedTargets =
      Phase17Protected.boundContract.positions := by decide +kernel

/-- The selected finite-model step now carries original-prompt routing, decoded
    goals and teacher-forced information positions. Capturing those literals and
    executing the external runtime remain outside this theorem. -/
theorem selected_learned_acceptance_bound :
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
    Phase17Sparse.CapturedProjection Phase17Sparse.beforeImage Phase17Protected.observedBefore
      Phase17Sparse.selectedMarkers Phase17Sparse.selectedTargets ∧
    Phase17Sparse.CapturedProjection Phase17Sparse.afterImage Phase17Protected.observedAfter
      Phase17Sparse.selectedMarkers Phase17Sparse.selectedTargets ∧
    RoutedGoalBinding beforePackage Phase17Sparse.beforeImage originalTasks Phase17Sparse.selectedTargets ∧
    RoutedGoalBinding afterPackage Phase17Sparse.afterImage originalTasks Phase17Sparse.selectedTargets ∧
    (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedBefore =
      Phase17Sparse.decodedInformationSum Phase17Sparse.beforeImage
        (routedPositions beforePackage Phase17Sparse.beforeImage originalTasks Phase17Sparse.selectedTargets) ∧
    (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedAfter =
      Phase17Sparse.decodedInformationSum Phase17Sparse.afterImage
        (routedPositions afterPackage Phase17Sparse.afterImage originalTasks Phase17Sparse.selectedTargets) := by
  refine ⟨Phase17Sparse.selected_learned_acceptance_bound.1,
    Phase17Sparse.selected_learned_acceptance_bound.2.1,
    Phase17Sparse.selected_learned_acceptance_bound.2.2,
    selected_routed_goals.1, selected_routed_goals.2, ?_, ?_⟩
  · rw [selected_information_contexts.1]
    exact Phase17Sparse.selected_information_transport.1
  · rw [selected_information_contexts.2]
    exact Phase17Sparse.selected_information_transport.2.1

theorem selected_edge_controls :
    marker? (.boolean true) = none ∧ marker? (.string "84") = none ∧
    marker? (.integer (-1)) = none ∧ marker? (.integer 256) = none ∧
    (uniqueRoute [.object [("challenge_commitment_hash", .string "duplicate")],
      .object [("challenge_commitment_hash", .string "duplicate")]] "duplicate").isNone = true ∧
    uniqueFamily [.memoryRetrieval, .generatorPlanner] = none ∧
    legacyLookup (.object [("entries", .array [
      .object [("query_marker_token_id", .integer 85), ("match_mode", .string "exact_terminal_byte"),
        ("route_marker_token_id", .integer 84)],
      .object [("query_marker_token_id", .integer 85), ("match_mode", .string "exact_terminal_byte"),
        ("route_marker_token_id", .integer 1)]])]) "entries" 85 = some 84 ∧
    fourWords afterPackage.adapterImage 5120 = none ∧
    promptBound ⟨"empty", [], none⟩ = false ∧
    legacyChain { afterPackage with planner := .null } 87 = ⟨87, false⟩ := by decide +kernel
'''


def _render_validated(prepared: PreparedPromptRouting, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import Phase17RDependency\n\nset_option Elab.async false\n\n' +
            template(source_root).decode('utf-8'))
    text += '\nnamespace Phase17Routing\nopen RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 32000000\n'
    text += '-- Fresh S packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += _definitions(prepared, negative)
    if negative is None:
        text += POSITIVE
    else:
        text += ('theorem rejected_control :\n'
                 '    RoutingBinding afterPackage Phase17Sparse.afterImage originalTasks Phase17Sparse.selectedMarkers := by\n'
                 '  unfold RoutingBinding\n  decide +kernel\n')
    text += '\nend Phase17Routing\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw),
            'forbidden protected routing proof token')
    return raw


def _dependencies_validated(prepared: PreparedPromptRouting, *, source_root: Path) -> dict[str, bytes]:
    sparse = prepared.sparse()
    q = sparse_refinement_lean._common_source_validated(sparse, source_root=source_root)
    r = sparse_refinement_lean._render_validated(sparse, source_root=source_root)
    require(sha(r) == R_SOURCE_SHA, 'freshly generated R dependency differs from its exact pinned source')
    lines = r.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in sparse_refinement_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected),
            'exact R dependency audit removal required')
    r = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in r, 'unexpected R dependency output')
    return dict(zip(DEPENDENCY_LABELS, (q, r), strict=True))


def render(prepared: PreparedPromptRouting, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedPromptRouting and negative in (None, *LABELS[1:]),
            'exact protected routing proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedPromptRouting, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedPromptRouting, 'exact protected routing input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label)
               for label in LABELS}}
