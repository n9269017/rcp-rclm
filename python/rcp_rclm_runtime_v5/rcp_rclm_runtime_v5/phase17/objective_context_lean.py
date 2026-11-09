"""Bind the complete selected objective computation to imported X/W/V/U/Q data.

Each SHA witness is checked by the unchanged X reference. The small new
arithmetic module shares repeated transitions without dropping ordered blocks.
The policy certificate derives all eight rows from the actual imported planner
projection, then checks complete decision/freeze/challenge images and identities.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from . import producer_sha256_lean as previous
from .captured_json_lean import _raw_image
from .materialized import require, sha
from .objective_context import PreparedObjectiveContext, X_SOURCE_SHA, X_AUXILIARY_SHA, validate_packet
from .prompt_routing_lean import _value
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ObjectiveContext.lean'
BRIDGE_SHA256 = '4f75390520ddb9e2647d04da5e706923a418bc2d8ec09a60e43d6abd31d3bd60'
DEPENDENCY_LABELS = (*previous.DEPENDENCY_LABELS, 'Phase17XDependency')
AUXILIARY_LABELS = ('Phase17XSha256Blocks', 'Phase17YSha256Blocks')
COMPILED_MODULES = (*previous.DEPENDENCY_LABELS, 'Phase17XSha256Blocks',
                    'Phase17XDependency', 'Phase17YSha256Blocks')
NAMES = tuple('Phase17Objective.' + name for name in (
    'terms_length', 'rank_score_bound', 'captured_digest_bound',
    'selected_imported_context', 'selected_historical_state_digest',
    'selected_feature_inputs', 'selected_feature_digests', 'selected_tie_inputs',
    'selected_tie_digests', 'selected_numeric_terms', 'selected_objective_order',
    'selected_objective_decision', 'selected_objective_freeze',
    'selected_challenge_binding', 'selected_learned_acceptance_bound',
))
LABELS = ('ObjectiveContext', 'WrongHistoricalState', 'WrongFeatureContext',
          'WrongPlannerProjection', 'WrongGeneration', 'WrongScoreTerm',
          'WrongObjectiveOrder', 'WrongObjectiveWinner', 'WrongDecisionBinding',
          'WrongFreezeBinding', 'WrongChallengeOpening', 'WrongChallengeCredits',
          'MissingDomainNul', 'WrongShaRound')
FORBIDDEN = previous.FORBIDDEN


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked objective context template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'objective context template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = previous.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _definition(name: str, kind: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + kind + ' := ' + value + '\n'


def _nats(values) -> str:
    return '[' + ', '.join(map(str, values)) + ']'


def _ints(values) -> str:
    return '[' + ', '.join('(' + str(x) + ')' for x in values) + ']'


def _rank(row: dict) -> str:
    return ('{ family := ' + string(row['family']) + ', generation := ' + str(row['generation']) +
            ', projectionScore := (' + str(row['projection_score']) + '), score := (' +
            str(row['score']) + '), tie := ' + string(row['tie_digest']) + ' }')


def _compression_inventory(packet: dict) -> tuple[list[dict], list[list[int]]]:
    unique, blocks, paths = {}, [], []
    for record in packet['hash_records']:
        path = []
        for block in record['blocks']:
            key = previous._block_key(block)
            if key not in unique:
                unique[key] = len(blocks)
                blocks.append(block)
            else:
                require(block == blocks[unique[key]], 'repeated Y compression witness differs')
            path.append(unique[key])
        paths.append(path)
    require(len(blocks) == 304 and sum(map(len, paths)) == 440,
            'complete selected Y compression inventory required')
    return blocks, paths


def _record(record: dict, index: int) -> str:
    if index == 0:
        image = 'Phase17Metadata.beforeImages.historical'
        return ('{ json := ' + image + ', preimage := Phase17Preimages.domain ++ ' + image +
                ', digest := Phase17Preimages.selectedView.predecessorState }')
    expected = ('Phase17Joint.producerBinding.objective' if index == 17 else
                'Phase17Preimages.selectedView.challengeCommitment' if index == 19 else
                string(record['digest']))
    return ('{ json := ' + _raw_image(bytes.fromhex(record['json_hex'])) +
            ', preimage := ' + _raw_image(bytes.fromhex(record['preimage_hex'])) +
            ', digest := ' + expected + ' }')


def _definitions(packet: dict) -> str:
    inputs = packet['inputs']
    objective = json.loads(bytes.fromhex(inputs['objective_hex']))
    public = json.loads(bytes.fromhex(inputs['public_challenge_hex']))
    secret = json.loads(bytes.fromhex(inputs['secret_hex']))
    text = _definition('selectedView', 'Phase17Preimages.View', 'Phase17Preimages.selectedView')
    text += _definition('selectedState', 'Phase17Metadata.HistoricalState', 'Phase17Metadata.beforeHistorical')
    text += _definition('selectedProjection', 'List (Nat × Int)', 'Phase17Planner.expectedProjection')
    text += _definition('plannerHash', 'String', 'Phase17Preimages.plannerHash')
    text += _definition('bootstrapHash', 'String', string(objective['bootstrap_report_hash']))
    text += _definition('grammarHash', 'String', string(public['grammar_hash']))
    text += _definition('credits', 'Nat', 'Phase17Provenance.selectedContext.credits')
    for name, field in (('objectiveImage', 'objective_hex'), ('freezeImage', 'freeze_hex'),
                        ('publicImage', 'public_challenge_hex'), ('secretImage', 'secret_hex')):
        text += _definition(name, 'List Nat', _raw_image(bytes.fromhex(inputs[field])))
    text += _definition('secret', 'Value', _value(secret))
    family = packet['profile']['families'].index(secret['objective_family'])
    text += _definition('opening', 'Opening', '{ entropy := ' + string(secret['entropy_hex']) +
        ', program := { family := ' + str(family) + ', variant := ' + str(secret['target_variant']) +
        ', a := (' + str(secret['target_a']) + '), b := (' + str(secret['target_b']) + ') }, probes := [' +
        ', '.join(_ints(probe) for probe in secret['probes']) + '] }')
    for index, record in enumerate(packet['hash_records']):
        text += _definition('record' + str(index), 'Phase17Preimages.HashRecord', _record(record, index))
    text += _definition('allRecords', 'List Phase17Preimages.HashRecord',
                        '[' + ', '.join('record' + str(i) for i in range(20)) + ']')
    text += _definition('featureRecords', 'List Phase17Preimages.HashRecord',
                        '[' + ', '.join('record' + str(i) for i in range(1, 9)) + ']')
    text += _definition('tieRecords', 'List Phase17Preimages.HashRecord',
                        '[' + ', '.join('record' + str(i) for i in range(9, 17)) + ']')
    for index, row in enumerate(packet['objective_rows']):
        text += _definition('row' + str(index), 'Rank', _rank(row))
        text += _definition('expectedTerms' + str(index), 'List Int', _ints(row['terms']))
    text += _definition('rows', 'List Rank', '[' + ', '.join('row' + str(i) for i in range(8)) + ']')
    text += _definition('expectedOrder', 'List Rank',
                        '[' + ', '.join('row' + str(i) for i in packet['ranked_indices']) + ']')
    return text


def _hash_certificate(index: int, path: list[int]) -> str:
    final = 'Phase17ObjectiveSha256.after' + str(path[-1])
    text = _definition('parts' + str(index), 'List Phase17Sha256.Block',
                       '[' + ', '.join('Phase17ObjectiveSha256.block' + str(i) for i in path) + ']')
    text += f'''theorem valid_{index} : Phase17Sha256.InputValid record{index}.preimage := by decide +kernel
theorem partition_{index} : Phase17Sha256.blocks (Phase17Sha256.pad record{index}.preimage) = parts{index} := by decide +kernel
theorem chain_{index} : Phase17Sha256.CompressionChain Phase17Sha256.initial parts{index} {final} := by
  exact '''
    text += ''.join('(Phase17Sha256.CompressionChain.cons Phase17ObjectiveSha256.block_step_' + str(i) + ' ' for i in path)
    text += '(Phase17Sha256.CompressionChain.nil ' + final + ')' + ')' * len(path) + '\n'
    text += f'''theorem digest_{index} : Phase17Sha256.digestHex {final} = record{index}.digest := by decide +kernel
theorem hash_{index} : Phase17Sha256.HashEvaluated record{index} :=
  Phase17Sha256.sha256_of_chain valid_{index} partition_{index} chain_{index} digest_{index}
'''
    return text


def _all_hashed(indices) -> str:
    indices = list(indices)
    return ''.join('(Phase17Sha256.AllHashed.cons hash_' + str(i) + ' ' for i in indices) + 'Phase17Sha256.AllHashed.nil' + ')' * len(indices)


def _row_certificates() -> str:
    text = ''
    for family in range(8):
        f, t = family + 1, family + 9
        text += f'''theorem feature_input_{family} :
    Phase17Preimages.HashInputChecked (featureValue selectedView selectedState plannerHash {family}) record{f} := by decide +kernel
theorem tie_input_{family} :
    Phase17Preimages.HashInputChecked (tieValue {family} record{f}.digest) record{t} := by decide +kernel
theorem terms_{family} :
    (Phase17Planner.hexDigits record{f}.digest).map
      (terms selectedProjection {family} (selectedState.generations.getD {family} 0)) = some expectedTerms{family} ∧
    expectedTerms{family}.length = 84 ∧ expectedTerms{family}.sum = row{family}.projectionScore ∧
    rank selectedProjection {family} (selectedState.generations.getD {family} 0)
      record{f}.digest record{t}.digest = some row{family} := by decide +kernel
'''
    return text


def _positive(packet: dict) -> str:
    _, paths = _compression_inventory(packet)
    text = _definitions(packet)
    for index, path in enumerate(paths):
        text += _hash_certificate(index, path)
    text += 'theorem all_hashed : Phase17Sha256.AllHashed allRecords := ' + _all_hashed(range(20)) + '\n'
    text += _row_certificates()
    features = ' ∧\n    '.join(f'Phase17Preimages.HashInputChecked (featureValue selectedView selectedState plannerHash {i}) record{i+1}' for i in range(8))
    ties = ' ∧\n    '.join(f'Phase17Preimages.HashInputChecked (tieValue {i} record{i+1}.digest) record{i+9}' for i in range(8))
    text += 'theorem selected_feature_inputs :\n    ' + features + ' := ⟨' + ', '.join(f'feature_input_{i}' for i in range(8)) + '⟩\n'
    text += 'theorem selected_tie_inputs :\n    ' + ties + ' := ⟨' + ', '.join(f'tie_input_{i}' for i in range(8)) + '⟩\n'
    text += '''theorem selected_feature_digests :
    Phase17Sha256.digestRecords featureRecords = some (featureRecords.map Phase17Preimages.HashRecord.digest) :=
  Phase17Sha256.digest_records_sound _ ''' + _all_hashed(range(1, 9)) + '\n'
    text += '''theorem selected_tie_digests :
    Phase17Sha256.digestRecords tieRecords = some (tieRecords.map Phase17Preimages.HashRecord.digest) :=
  Phase17Sha256.digest_records_sound _ ''' + _all_hashed(range(9, 17)) + '\n'
    text += POSITIVE
    return text


POSITIVE = '''
theorem selected_imported_context :
    selectedView = Phase17Preimages.selectedView ∧
    selectedState = Phase17Metadata.beforeHistorical ∧
    selectedState = Phase17Metadata.afterHistorical ∧
    Phase17Metadata.beforeImages.historical = Phase17Metadata.afterImages.historical ∧
    selectedView.predecessorState = Phase17Joint.producerBinding.historicalState ∧
    selectedView.challengeCommitment = Phase17Joint.producerBinding.challenge ∧
    selectedState.generations = selectedView.context.familyCounts ∧
    Phase17Planner.decodedProjection Phase17Planner.beforeImage = selectedProjection ∧
    Phase17Planner.decodedProjection Phase17Planner.afterImage = selectedProjection ∧
    selectedProjection.length = 84 ∧ credits = 32 ∧
    allRecords.length = 20 ∧
    (allRecords.map (fun record => record.preimage.length)).sum = 27051 ∧
    Phase17Metadata.decodeHistorical Phase17Metadata.beforeImages.historical = some selectedState ∧
    Phase17Metadata.decodeHistorical Phase17Metadata.afterImages.historical = some selectedState ∧
    selectedState.activePackage = selectedView.context.activePackage ∧
    selectedState.fixedVerifier = selectedView.context.fixedVerifier ∧
    selectedState.semantics = selectedView.context.semantics := by
  refine ⟨rfl, rfl, by decide +kernel, by decide +kernel, rfl, rfl, by decide +kernel,
    Phase17Planner.selected_complete_word_projection.1,
    Phase17Planner.selected_complete_word_projection.2.1,
    Phase17Planner.selected_complete_word_projection.2.2,
    by decide +kernel, by decide +kernel, by decide +kernel,
    Phase17Metadata.before_historical_decode, ?_,
    by decide +kernel, by decide +kernel, by decide +kernel⟩
  exact Phase17Metadata.after_historical_decode

theorem selected_historical_state_digest :
    Phase17Sha256.sha256 (Phase17Preimages.domain ++ Phase17Metadata.beforeImages.historical) =
      some Phase17Joint.producerBinding.historicalState ∧
    Phase17Sha256.sha256 (Phase17Preimages.domain ++ Phase17Metadata.afterImages.historical) =
      some Phase17Preimages.selectedView.predecessorState := by
  constructor
  · exact hash_0
  · rw [← selected_imported_context.2.2.2.1]
    exact hash_0

theorem selected_numeric_terms :
    ranks selectedProjection selectedState.generations
      (featureRecords.map Phase17Preimages.HashRecord.digest)
      (tieRecords.map Phase17Preimages.HashRecord.digest) = some rows ∧
    (List.range 8).map (fun family =>
      (Phase17Planner.hexDigits ((featureRecords.getD family record1).digest)).map
        (fun digits => (terms selectedProjection family
          (selectedState.generations.getD family 0) digits).length)) =
      List.replicate 8 (some 84) ∧
    rows.length = 8 := by decide +kernel

theorem selected_objective_order :
    ordered rows = expectedOrder ∧ winner rows = "tool_policy" ∧
    (expectedOrder.map Rank.family) = ["tool_policy", "architecture_policy", "adapter_policy",
      "retrieval_policy", "planner_policy", "verification_automation_policy", "optimizer_policy", "memory_policy"] ∧
    expectedOrder.Pairwise (fun left right => precedes left right = true) ∧
    (rows.map Rank.family) = Phase17Metadata.families := by decide +kernel

theorem decision_input :
    Phase17Preimages.HashInputChecked (decisionValue selectedView plannerHash bootstrapHash rows) record17 ∧
    record17.json = objectiveImage ∧
    Phase17Json.decode objectiveImage = some (decisionValue selectedView plannerHash bootstrapHash rows) := by decide +kernel

theorem selected_objective_decision :
    Phase17Preimages.HashInputChecked (decisionValue selectedView plannerHash bootstrapHash rows) record17 ∧
    Phase17Json.decode objectiveImage = some (decisionValue selectedView plannerHash bootstrapHash rows) ∧
    (Phase17Preimages.hashInput (decisionValue selectedView plannerHash bootstrapHash rows)).bind
      Phase17Sha256.sha256 = some Phase17Joint.producerBinding.objective := by
  exact ⟨decision_input.1, decision_input.2.2,
    Phase17Sha256.preimage_digest_bound _ _ decision_input.1 hash_17⟩

theorem freeze_input :
    Phase17Preimages.HashInputChecked (freezeValue selectedView record17.digest) record18 ∧
    Phase17Preimages.encode (frozenValue selectedView record17.digest record18.digest) = some freezeImage ∧
    Phase17Json.decode freezeImage = some (frozenValue selectedView record17.digest record18.digest) := by decide +kernel

theorem selected_objective_freeze :
    Phase17Preimages.HashInputChecked (freezeValue selectedView record17.digest) record18 ∧
    Phase17Json.decode freezeImage = some (frozenValue selectedView record17.digest record18.digest) ∧
    (Phase17Preimages.hashInput (freezeValue selectedView record17.digest)).bind
      Phase17Sha256.sha256 = some record18.digest := by
  exact ⟨freeze_input.1, freeze_input.2.2,
    Phase17Sha256.preimage_digest_bound _ _ freeze_input.1 hash_18⟩

theorem challenge_input :
    Phase17Preimages.HashInputChecked
      (challengeValue selectedView record17.digest record18.digest credits secret) record19 ∧
    Phase17Json.decode secretImage = some secret ∧
    Phase17Preimages.encode secret = some secretImage ∧
    Phase17Routing.field secret "objective_family" = .string (winner rows) ∧
    Phase17Json.decode publicImage = some
      (publicValue selectedView record18.digest grammarHash (winner rows) credits) := by decide +kernel

theorem opening_bound :
    secret = openingValue opening ∧
    Phase17TaskMeaning.catalog 21 = Phase17TaskMeaning.vectorMeaning (openingContract opening) ∧
    opening.probes.length = 8 ∧
    opening.probes.all (fun probe => decide (probe.length = 4 ∧ probe.all (fun x => decide (-32 ≤ x ∧ x ≤ 32)) = true)) = true := by
  exact ⟨by decide +kernel, rfl, by decide +kernel, by decide +kernel⟩

theorem selected_challenge_binding :
    Phase17Json.decode secretImage = some secret ∧
    Phase17Routing.field secret "objective_family" = .string (winner rows) ∧
    Phase17Json.decode publicImage = some
      (publicValue selectedView record18.digest grammarHash (winner rows) credits) ∧
    (Phase17Preimages.hashInput
      (challengeValue selectedView record17.digest record18.digest credits secret)).bind
      Phase17Sha256.sha256 = some Phase17Preimages.selectedView.challengeCommitment ∧
    record19.digest = Phase17Joint.producerBinding.challenge ∧
    credits = Phase17Provenance.selectedContext.credits ∧
    secret = openingValue opening ∧
    Phase17TaskMeaning.catalog 21 = Phase17TaskMeaning.vectorMeaning (openingContract opening) := by
  exact ⟨challenge_input.2.1, challenge_input.2.2.2.1, challenge_input.2.2.2.2,
    Phase17Sha256.preimage_digest_bound _ _ challenge_input.1 hash_19, rfl, rfl,
    opening_bound.1, opening_bound.2.1⟩

theorem selected_learned_acceptance_bound :
    Phase17Sha256.AllHashed allRecords ∧
    ranks selectedProjection selectedState.generations
      (featureRecords.map Phase17Preimages.HashRecord.digest)
      (tieRecords.map Phase17Preimages.HashRecord.digest) = some rows ∧
    (Phase17Preimages.hashInput (decisionValue selectedView plannerHash bootstrapHash rows)).bind
      Phase17Sha256.sha256 = some Phase17Joint.producerBinding.objective ∧
    (Phase17Preimages.hashInput
      (challengeValue selectedView record17.digest record18.digest credits secret)).bind
      Phase17Sha256.sha256 = some Phase17Joint.producerBinding.challenge ∧
    Phase17Sha256.AllHashed Phase17Sha256.selectedRecords ∧
    Phase17TaskMeaning.catalog 21 = Phase17TaskMeaning.vectorMeaning (openingContract opening) ∧
    Phase17Provenance.Produced Phase17Finite.selectedConfiguration.context Phase17Finite.selectedEvidence.proposal ∧
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  exact ⟨all_hashed, selected_numeric_terms.1, selected_objective_decision.2.2,
    selected_challenge_binding.2.2.2.1, Phase17Sha256.all_selected_hashed, opening_bound.2.1,
    Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted⟩
'''


def _controls(packet: dict, label: str) -> tuple[str, str]:
    text = _definitions(packet)
    if label == 'WrongHistoricalState':
        raw = bytearray(bytes.fromhex(packet['inputs']['historical_state_hex']))
        raw[1] ^= 1
        text += _definition('changedImage', 'List Nat', _raw_image(bytes(raw)))
        return text, 'changedImage = Phase17Metadata.beforeImages.historical'
    if label == 'WrongFeatureContext':
        text += _definition('changedView', 'Phase17Preimages.View',
            '{ selectedView with context := { selectedView.context with nonce := "' + '0'*64 + '" } }')
        return text, 'Phase17Preimages.HashInputChecked (featureValue changedView selectedState plannerHash 0) record1'
    if label == 'WrongPlannerProjection':
        text += _definition('changedProjection', 'List (Nat × Int)',
            'selectedProjection.modify 0 (fun pair => (pair.1, pair.2 + 1))')
        return text, '(Phase17Planner.hexDigits record1.digest).map (terms changedProjection 0 1) = some expectedTerms0'
    if label == 'WrongGeneration':
        return text, 'rank selectedProjection 0 2 record1.digest record9.digest = some row0'
    if label == 'WrongScoreTerm':
        return text, '(Phase17Planner.hexDigits record1.digest).map (terms selectedProjection 0 1) = some (expectedTerms0.modify 0 (· + 1))'
    if label == 'WrongObjectiveOrder':
        return text, 'ordered rows = expectedOrder.reverse'
    if label == 'WrongObjectiveWinner':
        return text, 'winner rows = "adapter_policy"'
    if label == 'WrongDecisionBinding':
        return text, 'record17.digest = Phase17Preimages.selectedView.predecessorState'
    if label == 'WrongFreezeBinding':
        return text, 'Phase17Preimages.HashInputChecked (freezeValue selectedView record0.digest) record18'
    if label == 'WrongChallengeOpening':
        secret = json.loads(bytes.fromhex(packet['inputs']['secret_hex']))
        secret['target_a'] += 1
        text += _definition('changedSecret', 'Value', _value(secret))
        return text, 'Phase17Preimages.HashInputChecked (challengeValue selectedView record17.digest record18.digest credits changedSecret) record19'
    if label == 'WrongChallengeCredits':
        return text, 'Phase17Preimages.HashInputChecked (challengeValue selectedView record17.digest record18.digest (credits + 1) secret) record19'
    if label == 'MissingDomainNul':
        return text, 'record1.preimage = Phase17Preimages.domain.dropLast ++ record1.json'
    if label == 'WrongShaRound':
        block = copy.deepcopy(packet['hash_records'][0]['blocks'][0])
        block['round_states'][0][0] ^= 1
        text += 'open Phase17Sha256\n' + previous._block_definitions(1000, block)
        return text, 'Phase17Sha256.BlockChecked before1000 block1000 trace1000 after1000'
    raise AssertionError('unknown objective-context negative control')


def _auxiliary_validated(prepared: PreparedObjectiveContext, *, source_root: Path) -> bytes:
    blocks, _ = _compression_inventory(prepared.packet)
    text = ('import Phase17XSha256Blocks\n\nset_option Elab.async false\n'
            'namespace Phase17ObjectiveSha256\nopen Phase17Sha256\n'
            'set_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n')
    text += '-- Fresh Y packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    for index, block in enumerate(blocks):
        text += previous._block_definitions(index, block) + previous._block_certificate(index)
    text += '\nend Phase17ObjectiveSha256\n'
    raw = text.encode()
    require(not re.search(FORBIDDEN, raw), 'forbidden objective SHA proof token')
    return raw


def _render_validated(prepared: PreparedObjectiveContext, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    text = ('import Phase17XDependency\nimport Phase17YSha256Blocks\n\nset_option Elab.async false\n\n' +
            template(source_root).decode() + '\nnamespace Phase17Objective\n'
            'open Phase17Routing RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
            'set_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n')
    text += '-- Fresh Y packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    if negative is None:
        text += _positive(prepared.packet)
    else:
        definitions, proposition = _controls(prepared.packet, negative)
        text += definitions
        text += ('theorem control_false : decide (' + proposition + ') = false := by decide +kernel\n'
                 'theorem rejected_control : ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  simp only [h]\n  decide +kernel\n')
    text += '\nend Phase17Objective\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode()
    require(not re.search(FORBIDDEN, raw), 'forbidden objective-context proof token')
    return raw


def _dependencies_validated(prepared: PreparedObjectiveContext, *, source_root: Path) -> dict[str, bytes]:
    inherited = prepared.producer_sha256()
    result = previous._dependencies_validated(inherited, source_root=source_root)
    auxiliary = previous._auxiliary_validated(inherited, source_root=source_root)
    require(sha(auxiliary) == X_AUXILIARY_SHA, 'regenerated X auxiliary differs from pinned exact source')
    result['Phase17XSha256Blocks'] = auxiliary
    source = previous._render_validated(inherited, source_root=source_root)
    require(sha(source) == X_SOURCE_SHA, 'regenerated X certificate differs from pinned exact source')
    expected = {'#print axioms ' + name + '\n' for name in previous.NAMES}
    lines = source.decode().splitlines(keepends=True)
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected), 'exact X dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode()
    require(b'#print' not in source, 'unexpected X dependency output')
    result['Phase17XDependency'] = source
    require(tuple(result) == COMPILED_MODULES[:-1], 'objective dependency order differs')
    return result


def render(prepared: PreparedObjectiveContext, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedObjectiveContext and negative in (None, *LABELS[1:]),
            'exact objective-context proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedObjectiveContext, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedObjectiveContext, 'exact objective-context proof input required')
    validate_packet(prepared.packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            AUXILIARY_LABELS[1]: _auxiliary_validated(prepared, source_root=source_root),
            **{label: _render_validated(prepared, source_root=source_root,
                                      negative=None if label == LABELS[0] else label) for label in LABELS}}
