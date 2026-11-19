"""Render complete registry and grammar descriptor bytes into U's actual inputs.

Every image is independently decoded by the imported canonical JSON reference.
The per-image proofs compose into full registry inventories, the actual Q DSL
programs, all 32 actual U RowInput records, and its selected producer context.
Only public key/feature/tie/freeze strings remain supplied hash inputs.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from . import planner_refinement_lean
from .captured_json_lean import _raw_image
from .controller import FAMILIES
from .materialized import require, sha
from .program_metadata import PreparedProgramMetadata, U_SOURCE_SHA, validate_packet
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ProgramMetadata.lean'
BRIDGE_SHA256 = '26881978fb207e8cabc341aef469143832459a246491e42b21a20d9ebd4f0d9d'
DEPENDENCY_LABELS = (*planner_refinement_lean.DEPENDENCY_LABELS, 'Phase17UDependency')
NAMES = tuple('Phase17Metadata.' + name for name in (
    'program_decode_unique', 'registry_counts_sound', 'registry_inventory_sound',
    'metadata_rows_compose', 'metadata_context_transport',
    'selected_registry_images', 'selected_registry_inventory', 'selected_inherited_counts',
    'selected_candidate_separation', 'selected_descriptor_decodes', 'selected_metadata_bound',
    'selected_candidate_bound', 'selected_context_bound', 'selected_learned_acceptance_bound',
    'selected_decoder_edges',
))
LABELS = (
    'ProgramMetadata', 'WrongProgramFamily', 'WrongOperationId', 'BooleanProgramGeneration',
    'ProgramVariantOutOfBounds', 'ProgramParameterOutOfBounds', 'WrongProgramGeneration',
    'WrongPublicNonce', 'MissingInheritedProgram', 'DuplicateRegistryProgram',
    'ActiveCandidate', 'WrongHistoricalGeneration', 'ChangedMetadataKey',
)


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked program metadata template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'program metadata template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = planner_refinement_lean.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _nat(value: int) -> str:
    require(type(value) is int and 0 <= value < 2 ** 63, 'bounded metadata natural literal')
    return str(value)


def _int(value: int) -> str:
    require(type(value) is int and -(2 ** 63) <= value < 2 ** 63, 'bounded metadata integer literal')
    return '(' + str(value) + ')' if value < 0 else str(value)


def _strings(values: list[str]) -> str:
    return '[' + ', '.join(map(string, values)) + ']'


def _nats(values: list[int]) -> str:
    return '[' + ', '.join(map(_nat, values)) + ']'


def _option_string(value: str | None) -> str:
    return 'none' if value is None else '(some ' + string(value) + ')'


def _decoded(hex_image: str) -> dict:
    return json.loads(bytes.fromhex(hex_image))


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _descriptor(value: dict) -> str:
    return ('{ promotionIndex := ' + _nat(value['promotion_index']) +
            ', family := ' + _nat(FAMILIES.index(value['family'])) +
            ', variant := ' + _nat(value['variant']) +
            ', generation := ' + _nat(value['generation']) +
            ', a := ' + _int(value['parameter_a']) + ', b := ' + _int(value['parameter_b']) +
            ', nonce := ' + string(value['public_nonce_hash']) + ' }')


def _manifest(value: dict) -> str:
    return ('{ inheritedKeys := ' + _strings(value['inherited_program_hashes']) +
            ', candidateKey := ' + _option_string(value['candidate_program_hash']) +
            ', inheritedFrontier := ' + _strings(value['inherited_frontier']) +
            ', recursiveFrontier := ' + _strings(value['recursive_frontier']) + ' }')


def _state(value: dict) -> str:
    return ('{ activePackage := ' + string(value['active_package_hash']) +
            ', archiveRoot := ' + string(value['archive_root_hash']) +
            ', frontier := ' + _strings(value['capability_frontier']) +
            ', generations := ' + _nats([value['component_generations'][name] for name in FAMILIES]) +
            ', fixedVerifier := ' + string(value['fixed_verifier_hash']) +
            ', installedKeys := ' + _strings(value['installed_program_hashes']) +
            ', modelIndex := ' + _nat(value['model_index']) +
            ', recursiveFrontier := ' + _strings(value['recursive_productivity_frontier']) +
            ', semantics := ' + string(value['semantics_id']) + ' }')


def _public_context(value: dict) -> str:
    return ('{ activePackage := ' + string(value['active_package_hash']) +
            ', fixedVerifier := ' + string(value['fixed_verifier_hash']) +
            ', semantics := ' + string(value['semantics_id']) +
            ', turnIndex := ' + _nat(value['turn_index']) +
            ', nonce := ' + string(value['public_nonce_hash']) +
            ', familyCounts := ' + _nats(value['family_counts']) + ' }')


def _public_row(row: dict, *, key: str | None = None) -> str:
    return ('{ key := ' + string(row['key'] if key is None else key) +
            ', featureDigest := ' + string(row['feature_digest']) +
            ', tieDigests := ' + _strings(row['tie_digests']) + ' }')


def _definition(name: str, kind: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + kind + ' := ' + value + '\n'


def _registry_definitions(packet: dict, side: str, *, prefix: str | None = None) -> str:
    prefix = side if prefix is None else prefix
    image = packet['registry_images'][side]
    manifest = _decoded(image['manifest_hex'])
    text = _definition(prefix + 'ManifestImage', 'List Nat', _raw_image(bytes.fromhex(image['manifest_hex'])))
    text += _definition(prefix + 'HistoricalImage', 'List Nat', _raw_image(bytes.fromhex(image['historical_state_hex'])))
    text += _definition(prefix + 'Manifest', 'Manifest', _manifest(manifest))
    text += _definition(prefix + 'Historical', 'HistoricalState', _state(_decoded(image['historical_state_hex'])))
    pairs, decoded = [], []
    for index, entry in enumerate(image['programs']):
        raw_name, decoded_name = f'{prefix}ProgramImage{index}', f'{prefix}Descriptor{index}'
        text += _definition(raw_name, 'List Nat', _raw_image(bytes.fromhex(entry['image_hex'])))
        text += _definition(decoded_name, 'Descriptor', _descriptor(_decoded(entry['image_hex'])))
        pairs.append('(' + string(entry['key']) + ', ' + raw_name + ')')
        decoded.append('(' + string(entry['key']) + ', ' + decoded_name + ')')
    text += _definition(prefix + 'ProgramImages', 'List (String × List Nat)', '[' + ', '.join(pairs) + ']')
    text += _definition(prefix + 'Programs', 'List InstalledProgram', '[' + ', '.join(decoded) + ']')
    text += _definition(prefix + 'Images', 'RegistryImages',
                        '{ manifest := ' + prefix + 'ManifestImage, historical := ' + prefix +
                        'HistoricalImage, programs := ' + prefix + 'ProgramImages }')
    inherited = [decoded[index] for index, entry in enumerate(image['programs'])
                 if entry['key'] in manifest['inherited_program_hashes']]
    selected = [decoded[index] for index, entry in enumerate(image['programs'])
                if entry['key'] == manifest['candidate_program_hash']]
    staged = 'none' if not selected else '(some ' + selected[0] + ')'
    counts = [sum(_decoded(entry['image_hex'])['family'] == family for entry in image['programs']
                  if entry['key'] in manifest['inherited_program_hashes']) for family in FAMILIES]
    text += _definition(prefix + 'Registry', 'RegistryProjection',
                        '{ inherited := [' + ', '.join(inherited) + '], staged := ' + staged +
                        ', counts := ' + _nats(counts) + ' }')
    return text


def _definitions(prepared: PreparedProgramMetadata) -> str:
    packet = prepared.packet
    ranking = packet['planner_refinement_packet']['ranking']
    text = _definition('publicContext', 'PublicContext', _public_context(ranking['current_view']))
    text += _definition('declaredCounts', 'List Nat', _nats(ranking['current_view']['family_counts']))
    text += _registry_definitions(packet, 'before')
    text += _registry_definitions(packet, 'after')
    for index, (entry, row) in enumerate(zip(packet['candidate_images'], ranking['rows'], strict=True)):
        text += _definition(f'candidateImage{index}', 'List Nat', _raw_image(bytes.fromhex(entry['image_hex'])))
        text += _definition(f'candidateDescriptor{index}', 'Descriptor', _descriptor(_decoded(entry['image_hex'])))
        text += _definition(f'publicRow{index}', 'PublicRow', _public_row(row))
    text += _definition('candidateImages', 'List (String × List Nat)', '[' + ', '.join(
        '(' + string(entry['key']) + ', candidateImage' + str(index) + ')'
        for index, entry in enumerate(packet['candidate_images'])) + ']')
    text += _definition('candidateDescriptors', 'List Descriptor',
                        '[' + ', '.join(f'candidateDescriptor{i}' for i in range(32)) + ']')
    text += _definition('publicRows', 'List PublicRow', '[' + ', '.join(f'publicRow{i}' for i in range(32)) + ']')
    text += _definition('emptyRow', 'Phase17Planner.RowInput',
                        '{ key := "", family := 0, variant := 0, generation := 0, familyCount := 0, featureDigest := "", tieDigests := [] }')
    return text


def _registry_certificates(packet: dict, side: str, *, prefix: str | None = None,
                           with_registry: bool = True) -> str:
    prefix = side if prefix is None else prefix
    text = f'''theorem {prefix}_manifest_decode :
    decodeManifest {prefix}ManifestImage = some {prefix}Manifest := by decide +kernel

theorem {prefix}_historical_decode :
    decodeHistorical {prefix}HistoricalImage = some {prefix}Historical := by decide +kernel

'''
    names = []
    for index, _ in enumerate(packet['registry_images'][side]['programs']):
        name = f'{prefix}_program_decode_{index}'
        names.append(name)
        text += f'''theorem {name} :
    decodeProgram {prefix}ProgramImage{index} = some {prefix}Descriptor{index} := by decide +kernel

'''
    text += f'''theorem {prefix}_programs_decode :
    decodePrograms {prefix}ProgramImages = some {prefix}Programs := by
  simp [decodePrograms, {prefix}ProgramImages, {prefix}Programs, {', '.join(names)}]

'''
    if with_registry:
        text += f'''theorem {prefix}_registry_decode :
    decodeRegistry {prefix}Images publicContext = some {prefix}Registry := by
  rw [registry_from_decodes {prefix}Images publicContext {prefix}Manifest {prefix}Historical
    {prefix}Programs {prefix}_manifest_decode {prefix}_historical_decode {prefix}_programs_decode]
  decide +kernel

'''
    return text


def _candidate_certificates(packet: dict) -> str:
    text = ''
    for index, entry in enumerate(packet['candidate_images']):
        text += f'''theorem candidate_decode_{index} :
    decodeProgram candidateImage{index} = some candidateDescriptor{index} := by decide +kernel

theorem row_check_{index} :
    metadataRow publicContext declaredCounts publicRow{index}
      ({string(entry['key'])}, candidateImage{index}) =
        some (Phase17Planner.rowInputs.getD {index} emptyRow) := by
  simp only [metadataRow, publicRow{index}, candidate_decode_{index}]
  decide +kernel

'''
    text += '''theorem checked_metadata_rows :
    List.Forall₂ (fun pair target => metadataRow publicContext declaredCounts pair.1 pair.2 = some target)
      (publicRows.zip candidateImages) Phase17Planner.rowInputs := by
  exact ''' + ''.join(f'(List.Forall₂.cons row_check_{index} ' for index in range(32)) + 'List.Forall₂.nil' + ')' * 32 + '\n\n'
    text += '''theorem complete_metadata_rows :
    metadataRows publicContext declaredCounts publicRows candidateImages = some Phase17Planner.rowInputs := by
  exact metadata_rows_compose publicContext declaredCounts publicRows candidateImages
    Phase17Planner.rowInputs (by decide +kernel) checked_metadata_rows

'''
    return text


POSITIVE = '''
theorem selected_registry_images :
    decodeManifest beforeImages.manifest = some beforeManifest ∧
    decodeManifest afterImages.manifest = some afterManifest ∧
    decodeHistorical beforeImages.historical = some beforeHistorical ∧
    decodeHistorical afterImages.historical = some afterHistorical ∧
    decodePrograms beforeImages.programs = some beforePrograms ∧
    decodePrograms afterImages.programs = some afterPrograms ∧
    beforeImages.programs.length = 8 ∧ afterImages.programs.length = 9 := by
  exact ⟨before_manifest_decode, after_manifest_decode, before_historical_decode,
    after_historical_decode, before_programs_decode, after_programs_decode,
    by decide +kernel, by decide +kernel⟩

/-- This is equality with the actual finite kernel's program observations. The
    after interpretation uses inherited order followed by its staged candidate. -/
theorem selected_registry_inventory :
    decodeRegistry beforeImages publicContext = some beforeRegistry ∧
    decodeRegistry afterImages publicContext = some afterRegistry ∧
    beforeRegistry.inherited.map (fun entry => (entry.1, semanticProgram entry.2)) =
      Phase17Finite.selectedBefore.programs ∧
    (afterRegistry.inherited ++ afterRegistry.staged.toList).map
      (fun entry => (entry.1, semanticProgram entry.2)) = Phase17Finite.selectedAfter.programs := by
  exact ⟨before_registry_decode, after_registry_decode, by decide +kernel, by decide +kernel⟩

theorem selected_inherited_counts :
    beforeRegistry.counts = declaredCounts ∧ afterRegistry.counts = declaredCounts ∧
    declaredCounts = beforeHistorical.generations ∧ declaredCounts = afterHistorical.generations ∧
    declaredCounts = publicContext.familyCounts ∧
    beforeRegistry.inherited = afterRegistry.inherited ∧
    completeGenerations beforeRegistry.inherited = true ∧
    completeGenerations afterRegistry.inherited = true := by decide +kernel

theorem selected_candidate_separation :
    beforeRegistry.staged = none ∧ afterRegistry.staged.isSome = true ∧
    beforeManifest.candidateKey = none ∧
    afterManifest.candidateKey = some Phase17Finite.selectedUpdate.key ∧
    afterRegistry.inherited.length = 8 ∧ afterPrograms.length = 9 ∧
    (afterRegistry.inherited.map Prod.fst).contains Phase17Finite.selectedUpdate.key = false ∧
    (Phase17Json.decode afterManifestImage).map (fun value => Phase17Routing.field value "candidate_active") =
      some (.boolean false) ∧
    (Phase17Json.decode afterManifestImage).map (fun value => Phase17Routing.field value "promotion_authorized") =
      some (.boolean false) := by decide +kernel

theorem selected_descriptor_decodes :
    candidateImages.mapM (fun image => decodeProgram image.2) = some candidateDescriptors ∧
    candidateDescriptors.length = 32 ∧
    (List.range 8).all (fun family => (List.range 4).all (fun variant => decide
      ((candidateDescriptors.filter (fun program =>
        program.family == family && program.variant == variant)).length = 1))) = true := by
  constructor
  · simp [candidateImages, candidateDescriptors, __CANDIDATE_DECODES__]
  · decide +kernel

theorem selected_metadata_bound :
    metadataRows publicContext beforeRegistry.counts publicRows candidateImages =
      some Phase17Planner.rowInputs ∧
    metadataRows publicContext afterRegistry.counts publicRows candidateImages =
      some Phase17Planner.rowInputs := by
  rw [selected_inherited_counts.1, selected_inherited_counts.2.1]
  exact ⟨complete_metadata_rows, complete_metadata_rows⟩

theorem selected_candidate_bound :
    afterRegistry.staged.map (fun entry => (entry.1, semanticProgram entry.2)) =
      some (Phase17Finite.selectedUpdate.key, Phase17Finite.selectedUpdate.program) ∧
    afterRegistry.staged.map Prod.fst = some Phase17Provenance.selectedProposal.program ∧
    (candidateImages.getD __SELECTED_INDEX__ ("", [])).1 = Phase17Finite.selectedUpdate.key ∧
    (decodeProgram (candidateImages.getD __SELECTED_INDEX__ ("", [])).2).map semanticProgram =
      some Phase17Finite.selectedUpdate.program := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, ?_⟩
  change (decodeProgram candidateImage__SELECTED_INDEX__).map semanticProgram = _
  rw [candidate_decode___SELECTED_INDEX__]
  decide +kernel

/-- The selected producer context now consumes the JSON-derived metadata. -/
theorem selected_context_bound :
    reconstructedContext Phase17Provenance.selectedContext Phase17Planner.beforeImage
      Phase17Planner.freezeDigest publicContext beforeImages publicRows candidateImages =
        some Phase17Finite.selectedConfiguration.context ∧
    reconstructedContext Phase17Provenance.selectedContext Phase17Planner.afterImage
      Phase17Planner.freezeDigest publicContext afterImages publicRows candidateImages =
        some Phase17Finite.selectedConfiguration.context := by
  rw [metadata_context_transport _ _ _ _ _ _ _ beforeRegistry Phase17Planner.rowInputs
    before_registry_decode selected_metadata_bound.1]
  rw [metadata_context_transport _ _ _ _ _ _ _ afterRegistry Phase17Planner.rowInputs
    after_registry_decode selected_metadata_bound.2]
  exact Phase17Planner.selected_context_bound

theorem selected_learned_acceptance_bound :
    ∃ context : Phase17Provenance.Context,
      reconstructedContext Phase17Provenance.selectedContext Phase17Planner.beforeImage
        Phase17Planner.freezeDigest publicContext beforeImages publicRows candidateImages = some context ∧
      reconstructedContext Phase17Provenance.selectedContext Phase17Planner.afterImage
        Phase17Planner.freezeDigest publicContext afterImages publicRows candidateImages = some context ∧
      context = Phase17Finite.selectedConfiguration.context ∧
      beforeRegistry.inherited.map (fun entry => (entry.1, semanticProgram entry.2)) =
        Phase17Finite.selectedBefore.programs ∧
      (afterRegistry.inherited ++ afterRegistry.staged.toList).map
        (fun entry => (entry.1, semanticProgram entry.2)) = Phase17Finite.selectedAfter.programs ∧
      Phase17Provenance.Produced context Phase17Finite.selectedEvidence.proposal ∧
      Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
        Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
        (Phase17Finite.packet Phase17Finite.selectedConfiguration
          Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
      Phase17Json.decodePackage Phase17Json.beforeImages Phase17Routing.beforePackage.adapterImage =
        some Phase17Routing.beforePackage ∧
      Phase17Json.decodePackage Phase17Json.afterImages Phase17Routing.afterPackage.adapterImage =
        some Phase17Routing.afterPackage := by
  exact ⟨Phase17Provenance.selectedContext, selected_context_bound.1, selected_context_bound.2,
    rfl, selected_registry_inventory.2.2.1, selected_registry_inventory.2.2.2,
    Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted,
    Phase17Json.selected_package_reconstruction.1, Phase17Json.selected_package_reconstruction.2⟩

theorem selected_decoder_edges :
    natural (.boolean true) = none ∧ natural (.integer (-1)) = none ∧
    natural (.integer 0) = some 0 ∧ natural (.integer 9223372036854775807) = some 9223372036854775807 ∧
    natural (.integer 9223372036854775808) = none ∧ familyIndex "unknown" = none ∧
    familyIndex "adapter_policy" = some 0 ∧ familyIndex "verification_automation_policy" = some 7 ∧
    candidateKey (.boolean false) = none ∧ candidateKey .null = some none ∧
    candidateKey (.string "not-a-digest") = none ∧
    decodeProgram [] = none ∧ descriptorValue (.object []) = none ∧
    decodeManifest [] = none ∧ decodeHistorical [] = none := by decide +kernel
'''


def _changed_key(key: str) -> str:
    return ('0' if key[0] != '0' else '1') + key[1:]


def _control_definitions(packet: dict, negative: str) -> tuple[str, str]:
    ranking = packet['planner_refinement_packet']['ranking']
    text = _definition('publicContext', 'PublicContext', _public_context(ranking['current_view']))
    text += _definition('declaredCounts', 'List Nat', _nats(ranking['current_view']['family_counts']))
    if negative in ('MissingInheritedProgram', 'DuplicateRegistryProgram'):
        text += _registry_definitions(packet, 'before')
        changed = copy.deepcopy(packet)
        entries = changed['registry_images']['before']['programs']
        if negative == 'MissingInheritedProgram':
            del entries[0]
        else:
            entries.insert(0, copy.deepcopy(entries[0]))
        # Only the input inventory changes; the original imported inventory is
        # the expected target and is not reconstructed from the mutated data.
        text += _registry_definitions(changed, 'before', prefix='changed')
        text += _registry_certificates(changed, 'before', prefix='changed', with_registry=False)
        text += '''theorem changed_registry_rejected :
    decodeRegistry changedImages publicContext = none := by
  rw [registry_from_decodes changedImages publicContext changedManifest changedHistorical
    changedPrograms changed_manifest_decode changed_historical_decode changed_programs_decode]
  decide +kernel

'''
        return text, 'decodeRegistry changedImages publicContext = some beforeRegistry'
    if negative == 'ActiveCandidate':
        image = packet['registry_images']['after']['manifest_hex']
        target = _decoded(image)
        changed = copy.deepcopy(target)
        changed['candidate_active'] = True
        text += _definition('changedImage', 'List Nat', _raw_image(_canonical(changed)))
        text += _definition('targetManifest', 'Manifest', _manifest(target))
        return text, 'decodeManifest changedImage = some targetManifest'
    if negative == 'WrongHistoricalGeneration':
        text += _registry_definitions(packet, 'before')
        state = _decoded(packet['registry_images']['before']['historical_state_hex'])
        state['component_generations'][FAMILIES[0]] += 1
        text += _definition('changedImage', 'List Nat', _raw_image(_canonical(state)))
        return text, ('((decodeHistorical changedImage).bind (fun state => '
                      'projectRegistry beforeManifest state beforePrograms publicContext)) = some beforeRegistry')
    entry = copy.deepcopy(packet['candidate_images'][0])
    program = _decoded(entry['image_hex'])
    original = copy.deepcopy(program)
    row = ranking['rows'][0]
    if negative == 'WrongProgramFamily':
        program['family'] = 'unknown_policy'
    elif negative == 'WrongOperationId':
        program['operation_id'] = 'install_unknown_operation'
    elif negative == 'BooleanProgramGeneration':
        program['generation'] = True
    elif negative == 'ProgramVariantOutOfBounds':
        program['variant'] = 4
    elif negative == 'ProgramParameterOutOfBounds':
        program['parameter_a'] = 17
    elif negative == 'WrongProgramGeneration':
        program['generation'] += 1
    elif negative == 'WrongPublicNonce':
        program['public_nonce_hash'] = '0' * 64
    elif negative == 'ChangedMetadataKey':
        entry['key'] = _changed_key(entry['key'])
    else:
        raise AssertionError('unknown program metadata negative control')
    text += _definition('changedImage', 'List Nat', _raw_image(_canonical(program)))
    if negative in ('WrongProgramFamily', 'WrongOperationId', 'BooleanProgramGeneration',
                    'ProgramVariantOutOfBounds', 'ProgramParameterOutOfBounds'):
        text += _definition('targetDescriptor', 'Descriptor', _descriptor(original))
        return text, 'decodeProgram changedImage = some targetDescriptor'
    text += _definition('changedPublic', 'PublicRow', _public_row(row, key=entry['key']))
    text += _definition('emptyRow', 'Phase17Planner.RowInput',
                        '{ key := "", family := 0, variant := 0, generation := 0, familyCount := 0, featureDigest := "", tieDigests := [] }')
    return text, ('metadataRow publicContext declaredCounts changedPublic (' + string(entry['key']) +
                  ', changedImage) = some (Phase17Planner.rowInputs.getD 0 emptyRow)')


def _render_validated(prepared: PreparedProgramMetadata, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import Phase17UDependency\n\nset_option Elab.async false\n\n' +
            template(source_root).decode('utf-8'))
    text += '\nnamespace Phase17Metadata\nopen RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 32000000\n'
    text += '-- Fresh V packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    if negative is None:
        packet = prepared.packet
        selected = [i for i, entry in enumerate(packet['candidate_images'])
                    if entry['key'] == packet['bindings']['program_hash']]
        require(len(selected) == 1, 'exact selected V descriptor required')
        text += _definitions(prepared)
        text += _registry_certificates(packet, 'before')
        text += _registry_certificates(packet, 'after')
        text += _candidate_certificates(packet)
        text += POSITIVE.replace('__CANDIDATE_DECODES__', ', '.join(f'candidate_decode_{i}' for i in range(32))).replace(
            '__SELECTED_INDEX__', str(selected[0]))
    else:
        definitions, proposition = _control_definitions(prepared.packet, negative)
        text += definitions
        false_proof = ('  apply decide_eq_false\n'
                       '  intro accepted\n'
                       '  rw [changed_registry_rejected] at accepted\n'
                       '  cases accepted\n'
                       if negative in ('MissingInheritedProgram', 'DuplicateRegistryProgram') else
                       '  with_unfolding_all rfl\n')
        text += ('theorem control_false :\n'
                 '    decide (' + proposition + ') = false := by\n'
                 + false_proof + '\n'
                 'theorem rejected_control :\n'
                 '    ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  simp only [h]\n'
                 '  decide +kernel\n')
    text += '\nend Phase17Metadata\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw),
            'forbidden program metadata proof token')
    return raw


def _dependencies_validated(prepared: PreparedProgramMetadata, *, source_root: Path) -> dict[str, bytes]:
    planner = prepared.planner_refinement()
    result = planner_refinement_lean._dependencies_validated(planner, source_root=source_root)
    source = planner_refinement_lean._render_validated(planner, source_root=source_root)
    require(sha(source) == U_SOURCE_SHA, 'freshly generated U dependency differs from its exact pinned source')
    lines = source.decode('utf-8').splitlines(keepends=True)
    expected = {'#print axioms ' + name + '\n' for name in planner_refinement_lean.NAMES}
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected),
            'exact U dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode('utf-8')
    require(b'#print' not in source, 'unexpected U dependency output')
    result['Phase17UDependency'] = source
    require(tuple(result) == DEPENDENCY_LABELS, 'metadata dependency order differs')
    return result


def render(prepared: PreparedProgramMetadata, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedProgramMetadata and negative in (None, *LABELS[1:]),
            'exact program metadata proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedProgramMetadata, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedProgramMetadata, 'exact program metadata proof input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label)
               for label in LABELS}}
