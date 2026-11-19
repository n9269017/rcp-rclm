"""Bind all selected evaluator outputs to the imported Y/V/Q definitions.

The complete 144 vector calls, nine outcomes and 153 ordered reference-work
records are checked without replacing imported programs or the opening.  The
raw-descriptor admission hashes and response metadata remain opaque identities;
there is no new SHA computation or physical execution claim in this module.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import objective_context_lean as previous
from .captured_json_lean import _raw_image
from .evaluation_trace import (PreparedEvaluationTrace, Y_SOURCE_SHA,
                               Y_AUXILIARY_SHA, validate_packet)
from .materialized import require, sha
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/EvaluationTrace.lean'
BRIDGE_SHA256 = '837a875e1119ddd16143120ee10a96fe5d111d8940d36eaa951d7e0cd3818918'
DEPENDENCY_LABELS = (*previous.DEPENDENCY_LABELS, 'Phase17YDependency')
AUXILIARY_LABELS = previous.AUXILIARY_LABELS
COMPILED_MODULES = (*previous.COMPILED_MODULES, 'Phase17YDependency')
NAMES = tuple('Phase17Evaluation.' + name for name in (
    'evaluation_sound', 'trivial_target_rejected', 'inherited_solution_rejected',
    'accepted_has_task_meaning', 'selected_imported_opening',
    'selected_program_inventory', 'selected_choice_binding', 'selected_target_outputs',
    'selected_inherited_outputs', 'selected_candidate_outputs',
    'selected_nontriviality_and_novelty', 'selected_outcome_semantics',
    'selected_evaluation_payloads', 'selected_work_images',
    'selected_complete_resource_schedule', 'selected_verdict_prefix',
    'selected_first_success', 'selected_task_meaning', 'selected_learned_acceptance_bound',
))
LABELS = ('EvaluationTrace', 'WrongOpening', 'WrongTargetOutput', 'WrongInheritedOutput',
          'WrongCandidateOutput', 'WrongCandidateFamily', 'WrongInheritedNovelty',
          'TrivialTarget', 'WrongAttemptOrder', 'MissingAttempt', 'WrongVerdict',
          'WrongReason', 'WrongSelectedProgram', 'WrongResourceOrder',
          'WrongWorkInput', 'WrongEvaluationBinding')
FORBIDDEN = previous.FORBIDDEN

# This selected resource repair is applied only after the unchanged X/Y
# generators have checked their historical source pins. It changes the proof
# of one W theorem, with all original definitions and propositions preserved.
W_DEPENDENCY_ORIGINAL_SHA256 = '341f4a756c95cf8acd2b75080b391fabc02ace620f667ea18b344af5df0b9d98'
W_DEPENDENCY_ORIGINAL_BYTES = 919820
W_FREEZE_HELPER_LIMIT = 131072
W_FREEZE_NAMESPACE = 'Phase17ZFreeze'
W_FREEZE_BEGIN = b'\n/- BEGIN phase17z freeze proof factoring. -/\n'
W_FREEZE_END = b'end Phase17ZFreeze\n/- END phase17z freeze proof factoring. -/\n\n'
W_FREEZE_ORIGINAL = b'''theorem selected_freeze_preimage :
    HashInputChecked (freezeValue selectedView Phase17Provenance.selectedContext.rows
      Phase17Metadata.candidateDescriptors) freezeRecord \xe2\x88\xa7
    freezeRecord.digest = Phase17Planner.freezeDigest \xe2\x88\xa7
    Phase17Provenance.selectedContext.rows.length = Phase17Metadata.candidateDescriptors.length \xe2\x88\xa7
    Phase17Metadata.candidateDescriptors.length = 32 := by decide +kernel

'''
W_FREEZE_REPLACEMENT = W_FREEZE_ORIGINAL.replace(
    b':= by decide +kernel\n\n',
    b''':= by
  exact \xe2\x9f\xa8\xe2\x9f\xa8Phase17ZFreeze.record_encoded, Phase17ZFreeze.record_prefixed,
      Phase17ZFreeze.digest_valid\xe2\x9f\xa9, Phase17ZFreeze.digest_bound,
    Phase17ZFreeze.rows_length, Phase17ZFreeze.descriptors_length\xe2\x9f\xa9

''')
W_FREEZE_GENERIC = '''
namespace Phase17ZFreeze
open Phase17Routing

theorem value_object (fuel depth : Nat) (fields : List (String × Value))
    (bytes : List Nat) (depth_ok : ¬ 20 < depth)
    (fields_ok : fields.length ≤ 256 ∧ (fields.map Prod.fst).Pairwise (· < ·))
    (children : encodeFields fuel (depth + 1) fields = some bytes) :
    encodeValue (fuel + 1) depth (.object fields) = some ([123] ++ bytes ++ [125]) := by
  simp only [encodeValue, if_neg depth_ok, if_pos fields_ok, children, Option.bind_eq_bind, Option.bind_some]

theorem value_array (fuel depth : Nat) (values : List Value) (bytes : List Nat)
    (depth_ok : ¬ 20 < depth) (length_ok : values.length ≤ 1024)
    (children : encodeArray fuel (depth + 1) values = some bytes) :
    encodeValue (fuel + 1) depth (.array values) = some ([91] ++ bytes ++ [93]) := by
  simp only [encodeValue, if_neg depth_ok, if_pos length_ok, children, Option.bind_eq_bind, Option.bind_some]

theorem array_singleton (fuel depth : Nat) (value : Value) (bytes : List Nat)
    (child : encodeValue fuel depth value = some bytes) :
    encodeArray (fuel + 1) depth [value] = some bytes := by
  simp only [encodeArray, child, Option.bind_eq_bind, Option.bind_some]

theorem array_cons (fuel depth : Nat) (value : Value) (rest : List Value)
    (head tail : List Nat) (nonempty : rest ≠ [])
    (first : encodeValue fuel depth value = some head)
    (later : encodeArray fuel depth rest = some tail) :
    encodeArray (fuel + 1) depth (value :: rest) = some (head ++ [44] ++ tail) := by
  cases rest with
  | nil => exact False.elim (nonempty rfl)
  | cons next rest =>
      simp only [encodeArray, first, later, Option.bind_eq_bind, Option.bind_some]

theorem fields_singleton (fuel depth : Nat) (key : String) (value : Value)
    (name bytes : List Nat) (key_checked : quoted key = some name)
    (child : encodeValue fuel depth value = some bytes) :
    encodeFields (fuel + 1) depth [(key, value)] = some (name ++ [58] ++ bytes) := by
  simp only [encodeFields, key_checked, child, Option.bind_eq_bind, Option.bind_some]

theorem fields_cons (fuel depth : Nat) (key : String) (value : Value)
    (rest : List (String × Value)) (name head tail : List Nat)
    (nonempty : rest ≠ []) (key_checked : quoted key = some name)
    (first : encodeValue fuel depth value = some head)
    (later : encodeFields fuel depth rest = some tail) :
    encodeFields (fuel + 1) depth ((key, value) :: rest) =
      some (name ++ [58] ++ head ++ [44] ++ tail) := by
  cases rest with
  | nil => exact False.elim (nonempty rfl)
  | cons next rest =>
      simp only [encodeFields, key_checked, first, later, Option.bind_eq_bind, Option.bind_some]

theorem whole_of_value (value : Value) (bytes : List Nat)
    (child : encodeValue 131073 0 value = some bytes) (bounded : bytes.length ≤ 65536) :
    encode value = some bytes := by
  simp only [encode, child, Option.bind_eq_bind, Option.bind_some, if_pos bounded]
'''


def _w_freeze_record(original: bytes) -> tuple[bytes, bytes, dict]:
    """Read bounded byte fragments from the exact historical source itself."""
    require(type(original) is bytes and len(original) == W_DEPENDENCY_ORIGINAL_BYTES and
            sha(original) == W_DEPENDENCY_ORIGINAL_SHA256, 'original W dependency pin differs')
    require(original.count(W_FREEZE_ORIGINAL) == 1 and
            W_FREEZE_BEGIN not in original and W_FREEZE_END not in original and
            W_FREEZE_NAMESPACE.encode() not in original, 'unique original W freeze theorem required')
    records = re.findall(
        rb'^noncomputable def freezeRecord : HashRecord := \{ json := (List\.flatten \[[0-9, \[\]]+\]), '
        rb'preimage := (List\.flatten \[[0-9, \[\]]+\]), digest := "([0-9a-f]{64})" \}$',
        original, flags=re.MULTILINE)
    require(len(records) == 1, 'one complete original freeze record required')

    def image(expression: bytes) -> bytes:
        chunks = json.loads(expression[len(b'List.flatten '):])
        require(type(chunks) is list and 1 <= len(chunks) <= 32 and
                all(type(chunk) is list and 1 <= len(chunk) <= 256 and
                    all(type(byte) is int and 0 <= byte < 128 for byte in chunk) for chunk in chunks),
                'bounded original freeze image chunks required')
        raw = bytes(byte for chunk in chunks for byte in chunk)
        require(_raw_image(raw).encode() == expression, 'original freeze image literal differs')
        return raw

    raw, preimage = image(records[0][0]), image(records[0][1])
    value = json.loads(raw)
    require(type(value) is dict and set(value) == {'candidates', 'schema', 'view'} and
            type(value['candidates']) is list and len(value['candidates']) == 32 and
            value['schema'] == 'runtime.v5.phase17.freeze.v1' and type(value['view']) is dict and
            all(type(row) is dict and set(row) == {'base_score', 'family', 'program_hash', 'variant'}
                for row in value['candidates']), 'selected complete freeze structure differs')
    require(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode() == raw and
            len(raw) == 5221 and len(preimage) == 5247 and
            preimage == b'RCPRCLM-CANONICAL-JSON-V2\0' + raw,
            'selected complete freeze bytes differ')
    return raw, preimage, value


def _w_freeze_helpers(original: bytes) -> bytes:
    _, _, freeze = _w_freeze_record(original)

    def literal(value: object) -> str:
        raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()
        return _raw_image(raw)

    text = W_FREEZE_GENERIC
    for index, candidate in enumerate(freeze['candidates']):
        suffix = str(index)
        text += _definition('candidate' + suffix, 'Value',
            'freezeCandidate (Phase17Provenance.selectedContext.rows[' + suffix +
            "]'(by decide +kernel)) Phase17Metadata.candidateDescriptor" + suffix)
        text += _definition('candidateBytes' + suffix, 'List Nat', literal(candidate))
        text += ('theorem candidate_encoded_' + suffix + ' : encodeValue ' + str(131069 - index) +
                 ' 2 candidate' + suffix + ' = some candidateBytes' + suffix + ' := by decide +kernel\n')
    for index in range(31, -1, -1):
        suffix, later = str(index), str(index + 1)
        text += _definition('values' + suffix, 'List Value',
            '[candidate31]' if index == 31 else 'candidate' + suffix + ' :: values' + later)
        text += _definition('bytes' + suffix, 'List Nat',
            'candidateBytes31' if index == 31 else 'candidateBytes' + suffix + ' ++ [44] ++ bytes' + later)
        text += ('theorem tail_encoded_' + suffix + ' : encodeArray ' + str(131070 - index) +
                 ' 2 values' + suffix + ' = some bytes' + suffix + ' := by\n')
        if index == 31:
            text += '  exact array_singleton 131038 2 candidate31 candidateBytes31 candidate_encoded_31\n'
        else:
            text += ('  exact array_cons ' + str(131069 - index) + ' 2 candidate' + suffix +
                     ' values' + later + ' candidateBytes' + suffix + ' bytes' + later + '\n' +
                     '    (List.cons_ne_nil _ _)\n' +
                     '    candidate_encoded_' + suffix + ' tail_encoded_' + later + '\n')
    text += '''
theorem candidates_bound :
    ((Phase17Provenance.selectedContext.rows.zip Phase17Metadata.candidateDescriptors).map
      (fun pair => freezeCandidate pair.1 pair.2)) = values0 := by rfl

noncomputable def arrayBytes : List Nat := [91] ++ bytes0 ++ [93]
theorem array_encoded : encodeValue 131071 1 (.array values0) = some arrayBytes := by
  exact value_array 131070 1 values0 bytes0 (by decide +kernel)
    (by decide +kernel) tail_encoded_0
'''
    text += _definition('schemaBytes', 'List Nat', literal(freeze['schema']))
    text += _definition('viewBytes', 'List Nat', literal(freeze['view']))
    for key in ('candidates', 'schema', 'view'):
        text += _definition(key + 'Key', 'List Nat', literal(key))
        text += ('theorem ' + key + '_quoted : quoted "' + key + '" = some ' + key +
                 'Key := by decide +kernel\n')
    text += '''
theorem schema_encoded : encodeValue 131070 1 (.string "runtime.v5.phase17.freeze.v1") =
    some schemaBytes := by decide +kernel
theorem view_encoded : encodeValue 131069 1 (viewValue selectedView) =
    some viewBytes := by decide +kernel

noncomputable def fields2 : List (String × Value) := [("view", viewValue selectedView)]
noncomputable def fields1 : List (String × Value) :=
  ("schema", .string "runtime.v5.phase17.freeze.v1") :: fields2
noncomputable def fields0 : List (String × Value) := ("candidates", .array values0) :: fields1
noncomputable def fieldsBytes2 : List Nat := viewKey ++ [58] ++ viewBytes
noncomputable def fieldsBytes1 : List Nat := schemaKey ++ [58] ++ schemaBytes ++ [44] ++ fieldsBytes2
noncomputable def fieldsBytes0 : List Nat := candidatesKey ++ [58] ++ arrayBytes ++ [44] ++ fieldsBytes1
noncomputable def completeBytes : List Nat := [123] ++ fieldsBytes0 ++ [125]

theorem fields_encoded_2 : encodeFields 131070 1 fields2 = some fieldsBytes2 := by
  exact fields_singleton 131069 1 "view" (viewValue selectedView) viewKey viewBytes
    view_quoted view_encoded
theorem fields_encoded_1 : encodeFields 131071 1 fields1 = some fieldsBytes1 := by
  exact fields_cons 131070 1 "schema" (.string "runtime.v5.phase17.freeze.v1") fields2
    schemaKey schemaBytes fieldsBytes2 (List.cons_ne_nil _ _)
    schema_quoted schema_encoded fields_encoded_2
theorem fields_encoded_0 : encodeFields 131072 1 fields0 = some fieldsBytes0 := by
  exact fields_cons 131071 1 "candidates" (.array values0) fields1
    candidatesKey arrayBytes fieldsBytes1 (List.cons_ne_nil _ _)
    candidates_quoted array_encoded fields_encoded_1

theorem freeze_value_bound :
    freezeValue selectedView Phase17Provenance.selectedContext.rows
      Phase17Metadata.candidateDescriptors = .object fields0 := by
  unfold freezeValue
  rw [candidates_bound]
  rfl

theorem value_encoded :
    encodeValue 131073 0 (freezeValue selectedView Phase17Provenance.selectedContext.rows
      Phase17Metadata.candidateDescriptors) = some completeBytes := by
  rw [freeze_value_bound]
  exact value_object 131072 0 fields0 fieldsBytes0 (by decide +kernel)
    (by decide +kernel) fields_encoded_0

theorem complete_image : completeBytes = freezeRecord.json := by decide +kernel
theorem record_encoded :
    encode (freezeValue selectedView Phase17Provenance.selectedContext.rows
      Phase17Metadata.candidateDescriptors) = some freezeRecord.json := by
  rw [← complete_image]
  exact whole_of_value _ _ value_encoded (by decide +kernel)
theorem record_prefixed : freezeRecord.preimage = domain ++ freezeRecord.json := by decide +kernel
theorem digest_valid : Phase17Metadata.digestValid freezeRecord.digest = true := by decide +kernel
theorem digest_bound : freezeRecord.digest = Phase17Planner.freezeDigest := by decide +kernel
theorem rows_length : Phase17Provenance.selectedContext.rows.length =
    Phase17Metadata.candidateDescriptors.length := by decide +kernel
theorem descriptors_length : Phase17Metadata.candidateDescriptors.length = 32 := by decide +kernel

'''
    helper = W_FREEZE_BEGIN + text.encode() + W_FREEZE_END
    require(len(helper) <= W_FREEZE_HELPER_LIMIT and
            helper.count(b'namespace Phase17ZFreeze\n') == 1 and
            helper.count(b'end Phase17ZFreeze\n') == 1 and
            not re.search(FORBIDDEN, helper), 'bounded W freeze helper namespace required')
    return helper


def factor_w_dependency(original: bytes) -> bytes:
    """Change only one pinned W proof body and insert its bounded helper block."""
    helper = _w_freeze_helpers(original)
    replacement = helper + W_FREEZE_REPLACEMENT
    factored = original.replace(W_FREEZE_ORIGINAL, replacement, 1)
    require(factored.count(replacement) == 1 and
            factored.replace(replacement, W_FREEZE_ORIGINAL, 1) == original,
            'exact W proof factoring restoration failed')
    require(W_FREEZE_ORIGINAL.split(b':= by', 1)[0] ==
            W_FREEZE_REPLACEMENT.split(b':= by', 1)[0], 'W theorem proposition changed')
    return factored


def restore_w_dependency(factored: bytes) -> bytes:
    """Reject alterations to either original bytes or the deterministic helpers."""
    require(type(factored) is bytes and
            W_DEPENDENCY_ORIGINAL_BYTES < len(factored) <=
            W_DEPENDENCY_ORIGINAL_BYTES + W_FREEZE_HELPER_LIMIT + len(W_FREEZE_REPLACEMENT),
            'bounded factored W dependency bytes required')
    require(factored.count(W_FREEZE_BEGIN) == 1 and factored.count(W_FREEZE_END) == 1 and
            factored.count(W_FREEZE_REPLACEMENT) == 1, 'unique factored W theorem required')
    first = factored.index(W_FREEZE_BEGIN)
    last = factored.index(W_FREEZE_END) + len(W_FREEZE_END)
    require(first < last and last - first <= W_FREEZE_HELPER_LIMIT and
            factored[last:].startswith(W_FREEZE_REPLACEMENT), 'W helper placement differs')
    original = factored[:first] + W_FREEZE_ORIGINAL + factored[last + len(W_FREEZE_REPLACEMENT):]
    _w_freeze_record(original)
    require(factor_w_dependency(original) == factored, 'deterministic W proof factoring differs')
    return original


def w_dependency_provenance(original: bytes, factored: bytes) -> dict:
    """Deterministic source-change evidence; this does not assert compilation."""
    raw, preimage, freeze = _w_freeze_record(original)
    require(type(factored) is bytes and factor_w_dependency(original) == factored and
            restore_w_dependency(factored) == original, 'W proof provenance pair differs')
    helper = _w_freeze_helpers(original)
    return {
        'schema': 'rcp-rclm.phase17z.w-freeze-proof-refactoring.v1',
        'dependency': 'Phase17WDependency',
        'original_source_sha256': sha(original), 'factored_source_sha256': sha(factored),
        'original_source_bytes': len(original), 'factored_source_bytes': len(factored),
        'helper_namespace': 'Phase17Preimages.' + W_FREEZE_NAMESPACE,
        'helper_sha256': sha(helper), 'helper_bytes': len(helper),
        'helper_byte_limit': W_FREEZE_HELPER_LIMIT,
        'theorem_name': 'Phase17Preimages.selected_freeze_preimage',
        'theorem_statement_sha256': sha(W_FREEZE_ORIGINAL.split(b':= by', 1)[0]),
        'original_proof_sha256': sha(W_FREEZE_ORIGINAL.split(b':= by', 1)[1]),
        'factored_proof_sha256': sha(W_FREEZE_REPLACEMENT.split(b':= by', 1)[1]),
        'original_source_restored_exactly': True,
        'original_definitions_and_data_preserved': True,
        'original_theorem_statements_preserved': True,
        'captured_freeze_json_sha256': sha(raw), 'captured_freeze_json_bytes': len(raw),
        'captured_preimage_bytes': len(preimage), 'candidate_count': len(freeze['candidates']),
        'fresh_compilation_required': True,
    }


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked evaluation trace template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'evaluation trace template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = previous.template_snapshot(root)
    result[BRIDGE_PATH] = sha(template(root))
    return result


def _definition(name: str, kind: str, value: str) -> str:
    return 'noncomputable def ' + name + ' : ' + kind + ' := ' + value + '\n'


def _list(values) -> str:
    return '[' + ', '.join(values) + ']'


def _nats(values) -> str:
    return _list(map(str, values))


def _ints(values) -> str:
    return _list('(' + str(value) + ')' for value in values)


def _matrix(values) -> str:
    return _list(_ints(row) for row in values)


def _bool(value: bool) -> str:
    require(type(value) is bool, 'exact Boolean proof literal required')
    return 'true' if value else 'false'


def _decision(row: dict) -> str:
    return ('{ nontrivial := ' + _bool(row['nontrivial']) +
            ', predecessorPass := ' + _bool(row['predecessor_pass']) +
            ', familyMatches := ' + _bool(row['family_matches']) +
            ', probeMatches := ' + _list(map(_bool, row['probe_matches'])) +
            ', firstMismatch := ' + ('none' if row['first_mismatch'] is None else
                                      'some ' + str(row['first_mismatch'])) +
            ', candidatePass := ' + _bool(row['candidate_pass']) +
            ', passed := ' + _bool(row['passed']) +
            ', verdict := ' + string(row['verdict']) +
            ', reasons := ' + _list(map(string, row['reason_codes'])) + ' }')


def _definitions(packet: dict, *, include_images: bool = True) -> str:
    evaluation = packet['evaluation']
    text = _definition('opening', 'Opening', 'Phase17Objective.opening')
    text += _definition('inheritedDescriptors', 'List DescriptorEntry',
                        'Phase17Metadata.beforeRegistry.inherited')
    text += _definition('inherited', 'List Entry', 'semanticEntries inheritedDescriptors')
    text += _definition('allDescriptors', 'List DescriptorEntry',
                        '(Phase17Metadata.candidateImages.map Prod.fst).zip Phase17Metadata.candidateDescriptors')
    text += _definition('choices', 'List Nat', _nats(evaluation['choices']))
    text += _definition('inheritedWorkOrder', 'List Nat', _nats(evaluation['inherited_work_order']))
    text += _definition('emptyDescriptor', 'Descriptor',
                        '{ promotionIndex := 0, family := 8, variant := 0, generation := 0, a := 0, b := 0, nonce := "" }')
    for index in range(8):
        text += _definition('inheritedDescriptor' + str(index), 'DescriptorEntry',
                            'inheritedDescriptors.getD ' + str(index) + ' ("", emptyDescriptor)')
    text += _definition('workInherited', 'List DescriptorEntry',
                        _list('inheritedDescriptor' + str(i) for i in evaluation['inherited_work_order']))
    for index, row in enumerate(evaluation['candidate_programs']):
        text += _definition('candidateDescriptor' + str(index), 'DescriptorEntry',
            '(' + string(row['key']) + ', Phase17Metadata.candidateDescriptor' + str(row['grammar_index']) + ')')
        text += _definition('candidateProgram' + str(index), 'Program',
                            'Phase17Metadata.semanticProgram candidateDescriptor' + str(index) + '.2')
    text += _definition('candidateDescriptors', 'List DescriptorEntry',
                        _list('candidateDescriptor' + str(i) for i in range(9)))
    text += _definition('candidates', 'List Entry', 'semanticEntries candidateDescriptors')
    text += _definition('expectedTargets', 'Matrix', _matrix(evaluation['target_outputs']))
    for index, rows in enumerate(evaluation['inherited_outputs']):
        text += _definition('inheritedOutput' + str(index), 'Matrix', _matrix(rows))
    text += _definition('expectedInherited', 'List Matrix',
                        _list('inheritedOutput' + str(i) for i in range(8)))
    for index, rows in enumerate(evaluation['candidate_outputs']):
        text += _definition('candidateOutput' + str(index), 'Matrix', _matrix(rows))
    text += _definition('expectedCandidates', 'List Matrix',
                        _list('candidateOutput' + str(i) for i in range(9)))
    for index, row in enumerate(evaluation['outcomes']):
        text += _definition('expectedDecision' + str(index), 'Decision', _decision(row))
        text += _definition('responseMetadata' + str(index), 'ResponseMetadata',
            '{ artifactHash := ' + string(row['artifact_hash']) +
            ', candidateFreezeHash := ' + string(row['candidate_freeze_hash']) +
            ', evaluationHash := ' + string(row['evaluation_hash']) + ' }')
        if include_images:
            text += _definition('responseImage' + str(index), 'List Nat',
                                _raw_image(bytes.fromhex(row['payload_hex'])))
    text += _definition('expectedDecisions', 'List Decision',
                        _list('expectedDecision' + str(i) for i in range(9)))
    text += _definition('evaluationIndices', 'List Nat',
                        _nats(row['evaluation_index'] for row in evaluation['outcomes']))
    text += _definition('responseSequences', 'List Nat',
                        _nats(row['response_sequence'] for row in evaluation['outcomes']))
    text += _definition('reportedChoices', 'List Nat',
                        _nats(row['selected_index'] for row in evaluation['outcomes']))
    text += _definition('reportedKeys', 'List String',
                        _list(string(row['program_hash']) for row in evaluation['outcomes']))
    text += _definition('expectedVerdicts', 'List Bool', _list(map(_bool, evaluation['verdicts'])))
    admission_digests = [json.loads(bytes.fromhex(row['output_hex']))['program_sha256']
                        for row in evaluation['work'] if row['kind'] == 'candidate']
    text += _definition('admissionDigests', 'List String', _list(map(string, admission_digests)))
    if include_images:
        for index, row in enumerate(evaluation['work']):
            text += _definition('workImage' + str(index), 'WorkImage',
                '{ identity := ' + string(row['identity']) + ', kind := .' + row['kind'] +
                ', inputImage := ' + _raw_image(bytes.fromhex(row['input_hex'])) +
                ', outputImage := ' + _raw_image(bytes.fromhex(row['output_hex'])) + ' }')
            if row['role'] == 'target':
                p = str(row['probe_index'])
                view = 'targetWork opening (opening.probes.getD ' + p + ' []) ' + p
            elif row['role'] == 'inherited':
                n_index = row['identity'].split(':')[1]
                p = str(row['probe_index'])
                view = ('inheritedWork inheritedDescriptor' + str(row['program_index']) + ' ' + n_index +
                        ' (opening.probes.getD ' + p + ' []) ' + p)
            elif row['kind'] == 'candidate':
                p = str(row['program_index'])
                view = ('candidateAdmission candidateDescriptor' + p + ' ' + p +
                        ' (admissionDigests.getD ' + p + ' "")')
            else:
                p, j = str(row['program_index']), str(row['probe_index'])
                view = ('candidateWork candidateDescriptor' + p + ' ' + p +
                        ' (opening.probes.getD ' + j + ' []) ' + j)
            text += _definition('workView' + str(index), 'WorkView', view)
        text += _definition('workImages', 'List WorkImage', _list('workImage' + str(i) for i in range(153)))
        text += _definition('selectedWorkViews', 'List WorkView', _list('workView' + str(i) for i in range(153)))
    return text


def _response_proposition(index: int, *, result: str | None = None, challenge: str | None = None) -> str:
    result = result or '(decision opening inherited candidateProgram' + str(index) + ')'
    challenge = challenge or 'Phase17Preimages.selectedView.challengeCommitment'
    return ('Phase17Json.decode responseImage' + str(index) + ' = some\n'
            '      (responseValue responseMetadata' + str(index) + ' ' + str(index) +
            ' candidateDescriptor' + str(index) + '.1\n'
            '        ' + challenge + ' Phase17Preimages.selectedView.predecessorState ' + result + ')')


def _positive(packet: dict) -> str:
    text = _definitions(packet)
    for index in range(153):
        text += ('theorem work_checked_' + str(index) + ' : WorkChecked workImage' + str(index) +
                 ' workView' + str(index) + ' := by decide +kernel\n')
    for index in range(9):
        text += ('theorem response_checked_' + str(index) + ' :\n    ' +
                 _response_proposition(index) + ' := by decide +kernel\n')
    text += 'theorem selected_work_images : List.Forall₂ WorkChecked workImages selectedWorkViews :=\n  '
    text += ''.join('(List.Forall₂.cons work_checked_' + str(i) + ' ' for i in range(153))
    text += 'List.Forall₂.nil' + ')' * 153 + '\n'
    text += 'theorem selected_evaluation_payloads :\n    '
    text += ' ∧\n    '.join(_response_proposition(i) for i in range(9))
    text += ' :=\n  ⟨' + ', '.join('response_checked_' + str(i) for i in range(9)) + '⟩\n'
    text += POSITIVE
    return text


POSITIVE = '''
theorem selected_imported_opening :
    opening = Phase17Objective.opening ∧
    Phase17TaskMeaning.catalog 21 =
      Phase17TaskMeaning.vectorMeaning (Phase17Objective.openingContract opening) ∧
    Phase17Json.decode Phase17Objective.secretImage = some (Phase17Objective.openingValue opening) ∧
    Phase17Objective.record19.digest = Phase17Joint.producerBinding.challenge := by
  refine ⟨rfl, Phase17Objective.opening_bound.2.1, ?_, rfl⟩
  unfold opening
  rw [← Phase17Objective.opening_bound.1]
  exact Phase17Objective.selected_challenge_binding.1

theorem selected_opening_commitment :
    (Phase17Preimages.hashInput
      (Phase17Objective.challengeValue Phase17Objective.selectedView
        Phase17Objective.record17.digest Phase17Objective.record18.digest
        Phase17Objective.credits (Phase17Objective.openingValue opening))).bind
      Phase17Sha256.sha256 = some Phase17Joint.producerBinding.challenge := by
  unfold opening
  rw [← Phase17Objective.opening_bound.1]
  exact Phase17Objective.selected_learned_acceptance_bound.2.2.2.1

theorem selected_program_inventory :
    inherited = Phase17Finite.selectedBefore.programs ∧
    inheritedDescriptors.length = 8 ∧ allDescriptors.length = 32 ∧
    candidateDescriptors.length = 9 ∧ opening.probes.length = 8 ∧
    opening.probes.all (fun probe => decide (probe.length = 4)) = true ∧
    selectPrograms inheritedDescriptors inheritedWorkOrder = some workInherited ∧
    inheritedWorkOrder.Perm (List.range 8) ∧
    workInherited.map (fun entry => entry.2.promotionIndex) = List.range 8 ∧
    admissionDigests.length = candidateDescriptors.length ∧
    admissionDigests.all Phase17Metadata.digestValid = true := by decide +kernel

theorem selected_choice_binding :
    choices = Phase17Provenance.selectedProposal.choices ∧
    choices = Phase17Finite.selectedEvidence.proposal.choices ∧
    selectPrograms allDescriptors choices = some candidateDescriptors ∧
    candidates.map Prod.fst = choiceKeys Phase17Provenance.selectedContext choices ∧
    reportedKeys = candidates.map Prod.fst ∧ reportedChoices = choices ∧
    evaluationIndices = List.range 9 ∧
    responseSequences = (List.range 9).map (fun index => 2 * (index + 1)) ∧
    candidateDescriptor8.1 = Phase17Finite.selectedUpdate.key ∧
    candidateProgram8 = Phase17Finite.selectedUpdate.program := by decide +kernel

theorem selected_target_outputs : targets opening = expectedTargets ∧
    expectedTargets.length = 8 ∧
    expectedTargets.all (fun vector => decide (vector.length = 4)) = true := by decide +kernel

theorem selected_inherited_outputs :
    inherited.map (fun entry => outputs opening entry.2) = expectedInherited ∧
    expectedInherited.length = 8 ∧
    expectedInherited.all (fun rows => decide (rows.length = 8) &&
      rows.all (fun vector => decide (vector.length = 4))) = true := by decide +kernel

theorem selected_candidate_outputs :
    candidates.map (fun entry => outputs opening entry.2) = expectedCandidates ∧
    expectedCandidates.length = 9 ∧
    expectedCandidates.all (fun rows => decide (rows.length = 8) &&
      rows.all (fun vector => decide (vector.length = 4))) = true := by decide +kernel

theorem selected_nontriviality_and_novelty :
    nontrivial opening = true ∧ predecessorPass opening inherited = false ∧
    (inherited.map (fun entry => programMatches opening entry.2)) = List.replicate 8 false ∧
    (Phase17TaskMeaning.catalog 21).check
      { proofs := [], programs := Phase17Finite.selectedBefore.programs } = false := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, ?_⟩
  rw [selected_imported_opening.2.1, ← selected_program_inventory.1, predecessor_check]
  decide +kernel

theorem selected_outcome_semantics :
    candidates.map (fun entry => decision opening inherited entry.2) = expectedDecisions ∧
    expectedDecisions.map Decision.passed = expectedVerdicts ∧
    (expectedDecisions.take 8).all (fun row => !row.familyMatches) = true ∧
    expectedDecision8.familyMatches = true ∧
    expectedDecision8.probeMatches = List.replicate 8 true ∧
    expectedDecision8.firstMismatch = none := by decide +kernel

theorem selected_complete_resource_schedule :
    selectedWorkViews = workViews opening workInherited candidateDescriptors admissionDigests ∧
    workImages.map WorkImage.identity = selectedWorkViews.map WorkView.identity ∧
    (workImages.map WorkImage.identity).Nodup ∧
    workImages.map WorkImage.kind = Phase17Finite.selectedTrace ∧
    selectedWorkViews.map WorkView.kind = Phase17Finite.selectedTrace ∧
    workImages.length = 153 ∧
    (selectedWorkViews.filter (fun work => decide (work.kind = .vector))).length = 144 ∧
    (selectedWorkViews.map (fun work => (array (field work.input "vector")).length)).sum = 576 ∧
    (selectedWorkViews.map (fun work => (array work.output).length)).sum = 576 ∧
    Phase17Resource.counter (selectedWorkViews.map WorkView.kind) 0 = 9 ∧
    Phase17Resource.counter (selectedWorkViews.map WorkView.kind) 1 = 144 ∧
    Phase17Resource.counter (selectedWorkViews.map WorkView.kind) 2 = 576 ∧
    Phase17Resource.counter (selectedWorkViews.map WorkView.kind) 3 = 576 ∧
    Phase17Resource.totalCost (selectedWorkViews.map WorkView.kind) = 4032 := by decide +kernel

theorem selected_verdict_prefix :
    derivedVerdicts opening inherited candidates = Phase17Provenance.selectedProposal.verdicts ∧
    derivedVerdicts opening inherited candidates = Phase17Finite.selectedEvidence.proposal.verdicts ∧
    expectedVerdicts = List.replicate 8 false ++ [true] ∧
    PrefixBound opening inherited candidates Phase17Finite.selectedConfiguration.context
      Phase17Finite.selectedEvidence.proposal := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel,
    Phase17Provenance.selected_provenance, ?_, ?_⟩ <;> decide +kernel

theorem selected_first_success :
    (candidates.take 8).all (fun entry => !passes opening inherited entry.2) = true ∧
    passes opening inherited candidateProgram8 = true ∧
    (candidates.getLast?).map Prod.fst = some Phase17Provenance.selectedProposal.program ∧
    candidateDescriptor8.1 = Phase17Finite.selectedUpdate.key ∧
    candidateProgram8 = Phase17Finite.selectedUpdate.program := by decide +kernel

theorem selected_task_meaning :
    (Phase17TaskMeaning.catalog 21).holds
      { proofs := [], programs := [(Phase17Finite.selectedUpdate.key, Phase17Finite.selectedUpdate.program)] } ∧
    (Phase17TaskMeaning.catalog 21).check
      { proofs := [], programs := Phase17Finite.selectedBefore.programs } = false := by
  constructor
  · rw [selected_imported_opening.2.1]
    exact accepted_has_task_meaning opening inherited _ _ (by decide +kernel)
  · exact selected_nontriviality_and_novelty.2.2.2

theorem selected_learned_acceptance_bound :
    Phase17Sha256.AllHashed Phase17Objective.allRecords ∧
    Phase17Sha256.AllHashed Phase17Sha256.selectedRecords ∧
    (Phase17Preimages.hashInput
      (Phase17Objective.challengeValue Phase17Objective.selectedView
        Phase17Objective.record17.digest Phase17Objective.record18.digest
        Phase17Objective.credits (Phase17Objective.openingValue opening))).bind
      Phase17Sha256.sha256 = some Phase17Joint.producerBinding.challenge ∧
    PrefixBound opening inherited candidates Phase17Finite.selectedConfiguration.context
      Phase17Finite.selectedEvidence.proposal ∧
    List.Forall₂ WorkChecked workImages selectedWorkViews ∧
    selectedWorkViews.map WorkView.kind = Phase17Finite.selectedEvidence.charges ∧
    Phase17TaskMeaning.catalog 21 =
      Phase17TaskMeaning.vectorMeaning (Phase17Objective.openingContract opening) ∧
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  exact ⟨Phase17Objective.all_hashed, Phase17Sha256.all_selected_hashed,
    selected_opening_commitment, selected_verdict_prefix.2.2.2, selected_work_images,
    by decide +kernel, selected_imported_opening.2.1, Phase17Finite.selected_learned_accepted⟩
'''


def _controls(packet: dict, label: str) -> tuple[str, str]:
    images = label in ('WrongReason', 'WrongWorkInput', 'WrongEvaluationBinding', 'WrongResourceOrder')
    text = _definitions(packet, include_images=images)
    if label == 'WrongOpening':
        text += _definition('changedOpening', 'Opening',
                            '{ opening with program := { opening.program with a := opening.program.a + 1 } }')
        return text, 'targets changedOpening = expectedTargets'
    if label == 'WrongTargetOutput':
        return text, 'targets opening = expectedTargets.modify 0 (fun row => row.modify 0 (· + 1))'
    if label == 'WrongInheritedOutput':
        return text, ('outputs opening (Phase17Metadata.semanticProgram inheritedDescriptor0.2) = '
                      'inheritedOutput0.modify 0 (fun row => row.modify 0 (· + 1))')
    if label == 'WrongCandidateOutput':
        return text, 'outputs opening candidateProgram8 = candidateOutput8.modify 0 (fun row => row.modify 0 (· + 1))'
    if label == 'WrongCandidateFamily':
        text += _definition('rotationOpening', 'Opening',
                            '{ opening with program := { family := 2, variant := 0, a := 0, b := 0 } }')
        text += _definition('wrongFamilyProgram', 'Program',
                            '{ family := 5, variant := 0, a := 0, b := 1 }')
        text += '''theorem control_preconditions :
    nontrivial rotationOpening = true ∧ predecessorPass rotationOpening [] = false ∧
    outputs rotationOpening wrongFamilyProgram = targets rotationOpening ∧
    wrongFamilyProgram.family ≠ rotationOpening.program.family := by decide +kernel
'''
        return text, 'passes rotationOpening [] wrongFamilyProgram = true'
    if label == 'WrongInheritedNovelty':
        text += '''theorem control_preconditions :
    nontrivial opening = true ∧ programMatches opening candidateProgram8 = true ∧
    predecessorPass opening (inherited ++ [(candidateDescriptor8.1, candidateProgram8)]) = true := by decide +kernel
'''
        return text, 'passes opening (inherited ++ [(candidateDescriptor8.1, candidateProgram8)]) candidateProgram8 = true'
    if label == 'TrivialTarget':
        text += _definition('identityOpening', 'Opening',
                            '{ opening with program := { family := 0, variant := 0, a := 0, b := 0 } }')
        text += '''theorem control_preconditions :
    nontrivial identityOpening = false ∧ predecessorPass identityOpening [] = false ∧
    programMatches identityOpening identityOpening.program = true := by decide +kernel
'''
        return text, 'passes identityOpening [] identityOpening.program = true'
    if label == 'WrongAttemptOrder':
        text += _definition('swappedCandidates', 'List Entry',
                            '(candidates.drop 1).take 1 ++ candidates.take 1 ++ candidates.drop 2')
        text += '''theorem control_preconditions :
    derivedVerdicts opening inherited swappedCandidates = Phase17Provenance.selectedProposal.verdicts ∧
    swappedCandidates.length = candidates.length := by decide +kernel
'''
        return text, 'swappedCandidates.map Prod.fst = choiceKeys Phase17Provenance.selectedContext choices'
    if label == 'MissingAttempt':
        return text, 'derivedVerdicts opening inherited (candidates.drop 1) = Phase17Provenance.selectedProposal.verdicts'
    if label == 'WrongVerdict':
        return text, 'derivedVerdicts opening inherited candidates = expectedVerdicts.modify 0 Bool.not'
    if label == 'WrongReason':
        return text, _response_proposition(8, result='{ expectedDecision8 with reasons := ["bounded_challenge_rejected"] }')
    if label == 'WrongSelectedProgram':
        return text, 'candidateDescriptor0.1 = Phase17Finite.selectedUpdate.key'
    if label == 'WrongResourceOrder':
        return text, ('(Phase17Resource.Kind.candidate :: ((selectedWorkViews.map WorkView.kind).take 72 ++ '
                      '(selectedWorkViews.map WorkView.kind).drop 73)) = Phase17Finite.selectedTrace')
    if label == 'WrongWorkInput':
        return text, ('Phase17Json.decode workImage0.inputImage = some '
                      '(targetWork opening ((opening.probes.getD 0 []).modify 0 (· + 1)) 0).input')
    if label == 'WrongEvaluationBinding':
        return text, _response_proposition(0, challenge='Phase17Preimages.selectedView.predecessorState')
    raise AssertionError('unknown evaluation-trace negative control')


def _render_packet(packet: dict, packet_sha256: str, *, source_root: Path,
                   negative: str | None = None) -> bytes:
    text = ('import Phase17YDependency\n\nset_option Elab.async false\n\n' + template(source_root).decode() +
            '\nnamespace Phase17Evaluation\n'
            'open Phase17Routing RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
            'set_option maxRecDepth 32768\nset_option maxHeartbeats 64000000\n')
    text += '-- Fresh Z packet SHA256: ' + packet_sha256 + '\n'
    if negative is None:
        text += _positive(packet)
    else:
        definitions, proposition = _controls(packet, negative)
        text += definitions
        text += ('theorem control_false : decide (' + proposition + ') = false := by decide +kernel\n'
                 'theorem rejected_control : ' + proposition + ' := by\n'
                 '  have h : ¬ (' + proposition + ') := of_decide_eq_false control_false\n'
                 '  rw [eq_false h]\n  decide +kernel\n')
    text += '\nend Phase17Evaluation\n'
    if negative is None:
        text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode()
    require(not re.search(FORBIDDEN, raw), 'forbidden evaluation-trace proof token')
    return raw


def _render_validated(prepared: PreparedEvaluationTrace, *, source_root: Path,
                      negative: str | None = None) -> bytes:
    return _render_packet(prepared.packet, sha(prepared.packet_bytes),
                          source_root=source_root, negative=negative)


def _dependencies_validated(prepared: PreparedEvaluationTrace, *, source_root: Path) -> dict[str, bytes]:
    inherited = prepared.objective_context()
    result = previous._dependencies_validated(inherited, source_root=source_root)
    auxiliary = previous._auxiliary_validated(inherited, source_root=source_root)
    require(sha(auxiliary) == Y_AUXILIARY_SHA, 'regenerated Y auxiliary differs from pinned exact source')
    result['Phase17YSha256Blocks'] = auxiliary
    source = previous._render_validated(inherited, source_root=source_root)
    require(sha(source) == Y_SOURCE_SHA, 'regenerated Y certificate differs from pinned exact source')
    expected = {'#print axioms ' + name + '\n' for name in previous.NAMES}
    lines = source.decode().splitlines(keepends=True)
    require({line for line in lines if line.startswith('#print')} == expected and
            sum(line in expected for line in lines) == len(expected), 'exact Y dependency audit removal required')
    source = ''.join(line for line in lines if line not in expected).encode()
    require(b'#print' not in source, 'unexpected Y dependency output')
    result['Phase17YDependency'] = source
    # All original nested source pins above remain mandatory. This final,
    # explicitly reversible Z-local rewrite changes only W's freeze proof.
    result['Phase17WDependency'] = factor_w_dependency(result['Phase17WDependency'])
    require(tuple(result) == COMPILED_MODULES, 'evaluation dependency order differs')
    return result


def render(prepared: PreparedEvaluationTrace, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedEvaluationTrace and negative in (None, *LABELS[1:]),
            'exact evaluation-trace proof input required')
    validate_packet(prepared.packet)
    return _render_validated(prepared, source_root=source_root, negative=negative)


def generated_sources(prepared: PreparedEvaluationTrace, *, source_root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedEvaluationTrace, 'exact evaluation-trace proof input required')
    packet = prepared.packet
    validate_packet(packet)
    return {**_dependencies_validated(prepared, source_root=source_root),
            **{label: _render_packet(packet, sha(prepared.packet_bytes), source_root=source_root,
                                    negative=None if label == LABELS[0] else label) for label in LABELS}}
