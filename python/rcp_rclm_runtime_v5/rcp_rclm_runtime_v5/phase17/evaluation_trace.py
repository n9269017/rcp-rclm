"""Phase 17Z: selected evaluator outputs and the actual producer verdict prefix.

The independent integer interpreter reconstructs all 144 four-vector calls in
the retained reference profile.  Outcomes follow from the retained Y opening,
all eight inherited programs and all nine attempted candidate descriptors.
Stored verdicts are comparison targets, never inputs to this calculation.
Journal hashes and physical capture remain external to Lean.  No worker,
challenge service, fresh entropy, campaign or promotion API is invoked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import objective_context as previous
from . import program_metadata as metadata
from .controller import FAMILIES
from .finite_kernel import FALSE_CLAIMS, canonical, require, sha
from .handoff_source import FIXTURE_PATH, FIXTURE_SHA
from .planner_refinement import producer_packet
from .resource_ledger import (_no_links, digest, exact, parse, Policy,
                              replay as resource_replay)

BASE = '06914d358d155916d8cd9760532ee60b022d3ff5'
SCHEMA = 'rcp-rclm.phase17z.evaluation-trace-packet.v1'
POLICY = 'phase17z.selected-evaluator-computation-and-producer-verdict-prefix.v1'
Y_ROOT = 'artifacts/development/phase17y/op-d3ff154c0d0d'
Y_EXECUTION = Y_ROOT + '/gate/execution.json'
Y_EXECUTION_SHA = 'c7d39f24054a482dddf5ba5610e832690b8a5afcae523e8e4ee30d3823ebfb6e'
Y_PACKET = Y_ROOT + '/gate/packet.json'
Y_PACKET_SHA = '61c4ec7ce0c8f2b566a7262f313b185993129fd67851f8a56fdc7a501ad1b22f'
Y_SOURCE = Y_ROOT + '/gate/ObjectiveContext.lean'
Y_SOURCE_SHA = '581e4e72ebc2f7806bc916abd8230ea09867b3af195aeb7c891e6336e9ff163f'
Y_AUXILIARY = Y_ROOT + '/gate/Phase17YSha256Blocks.lean'
Y_AUXILIARY_SHA = '1ae7a4a8f7005503f21a36e1bc7cc734e44167b57c8afee5024aa219446bdf3b'
RETAINED_Y_PINS = {
    Y_EXECUTION: Y_EXECUTION_SHA, Y_PACKET: Y_PACKET_SHA, Y_SOURCE: Y_SOURCE_SHA,
    Y_AUXILIARY: Y_AUXILIARY_SHA,
    Y_ROOT + '/operator-validation.json':
        '06643982662856fd08b4a133219507b5d9f48ac029b0dd0aa5287ee45aff9ebe',
}
MAX_BYTES = 40 * 1024 * 1024
TRANSCRIPT_BYTES = 40527
JOURNAL_PATH = 'artifacts/development/phase17n/op-2a7186e3590f/gate/resource-journal.jsonl'
PROFILE_PATH = 'artifacts/development/phase17n/op-2a7186e3590f/gate/profile.json'
REJECTION_REASON = 'bounded_challenge_rejected'
PROFILE = {
    'families': list(FAMILIES), 'variants_per_family': 4,
    'parameter_min': -16, 'parameter_max': 16, 'probe_value_min': -32,
    'probe_value_max': 32, 'probe_count': 8, 'vector_width': 4,
    'inherited_programs': 8, 'candidate_attempts': 9,
    'target_vector_calls': 8, 'inherited_vector_calls': 64,
    'candidate_vector_calls': 72, 'vector_calls': 144,
    'candidate_admissions': 9, 'operations': 153,
    'input_values': 576, 'output_values': 576,
    'outcome_rule': 'nontrivial and not predecessor_pass and family_matches and all_probe_outputs_match',
    'rejection_reason': REJECTION_REASON,
    'work_order': 'target probes; inherited programs in historical promotion order and all probes; each candidate admission then all probes in Q choice order',
    'output_policy': 'all eight probes for every program, without success-dependent short circuit',
    'input_origin': 'actual retained Y opening, V descriptors, Q producer prefix and N reference journal',
    'formal_target': 'actual imported Y opening and Q task, programs, choices, verdicts and resource kinds',
}
SCOPE = {
    'domain': 'selected 144 vector outputs, nine evaluator outcomes and the actual Q producer verdict prefix',
    'evaluator_outputs_from_opening_checked': True,
    'producer_verdict_prefix_checked': True,
    'selected_resource_kind_schedule_checked': True,
    'selected_objective_policy_checked': True,
    'selected_objective_challenge_binding_checked': True,
    'historical_fixture_only': True,
    'all_eight_rejected_candidates_have_wrong_family': True,
    'byte_capture_remains_external': True,
    'contextual_digest_authenticity_remains_external': True,
    'response_and_resource_journal_hash_computation_remains_external': True,
    'secret_generation_and_freshness_remain_external': True,
    'challenge_secrecy_remains_external': True,
    'evaluator_independence_remains_external': True,
    'temporal_freeze_order_remains_external': True,
    'python_execution_remains_external': True,
    'general_evaluator_equivalence': False,
    'general_json_parser_equivalence': False,
    'general_sha256_equivalence': False,
    'full_transformer_equivalence': False,
    'trusted_import_cache_assumption': True,
    'historical_success_reports_are_not_proofs': True,
    'old_proof_campaigns_rerun': False,
    'fresh_workers': 0, 'fresh_challenges': 0, 'promotion_api': False,
}
UNMEASURED = ('Z selected evaluator reconstruction and proof checking', *previous.UNMEASURED[1:])


def _integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label)
    return value


def _vector(value: object, *, probe: bool = False) -> list[int]:
    require(type(value) is list and len(value) == 4, 'complete four-integer vector required')
    low, high = (-32, 32) if probe else (-(1 << 63), (1 << 63) - 1)
    for number in value:
        _integer(number, low, high, 'bounded exact integer vector component required')
    return value


def program_parameters(program: dict) -> dict:
    """Use V's independently checked descriptor grammar, retaining all fields."""
    decoded = metadata.decode_program(canonical(program))
    return {'family': FAMILIES.index(decoded['family']), 'variant': decoded['variant'],
            'a': decoded['parameter_a'], 'b': decoded['parameter_b']}


def execute_vector(program: dict, probe: list[int]) -> list[int]:
    """Integer semantics independent of challenge_protocol and metered_evaluation."""
    exact(program, {'family', 'variant', 'a', 'b'})
    family = _integer(program['family'], 0, 7, 'fixed vector family required')
    v = _integer(program['variant'], 0, 3, 'fixed vector variant required') + 1
    a = _integer(program['a'], -16, 16, 'bounded vector parameter A required')
    b = _integer(program['b'], -16, 16, 'bounded vector parameter B required')
    xs = _vector(probe, probe=True)
    if family == 0:
        return [v * x + a - b for x in xs]
    if family == 1:
        return [xs[(i + v + 1) % 4] + a * (i + 1) + b for i in range(4)]
    if family == 2:
        return [xs[(i + v) % 4] + (a if i == 0 else 0) for i in range(4)]
    if family == 3:
        total = sum(xs)
        return [total + a + v * (i + 1) * (i + 2) // 2 - b * (i + 1) for i in range(4)]
    if family == 4:
        return [xs[0] + a, xs[1] * v, xs[2] - b, xs[3] + xs[0] * v]
    if family == 5:
        return [xs[(i * v + abs(b)) % 4] for i in range(4)]
    if family == 6:
        return [xs[0] + xs[1] + a, xs[1] - xs[2] + b, xs[2] * v, xs[3] + a - b]
    return sorted(x + a * v - b for x in xs)


def _outputs(value: object, *, probes: bool = False) -> list[list[int]]:
    require(type(value) is list and len(value) == 8, 'all eight vector outputs required')
    return [_vector(row, probe=probes) for row in value]


def match_outputs(family: int, target_family: int, outputs: list, targets: list) -> dict:
    _integer(family, 0, 7, 'bounded candidate family required')
    _integer(target_family, 0, 7, 'bounded target family required')
    _outputs(outputs); _outputs(targets)
    matches = [left == right for left, right in zip(outputs, targets, strict=True)]
    first = next((i for i, matches_probe in enumerate(matches) if not matches_probe), None)
    return {'family_matches': family == target_family, 'probe_matches': matches,
            'first_mismatch': first, 'passes': family == target_family and all(matches)}


def verdict_from_outputs(target_family: int, probes: list, targets: list,
                         inherited_families: list[int], inherited_outputs: list,
                         candidate_family: int, candidate_outputs: list) -> dict:
    """Derive the full policy, including nontriviality and predecessor novelty."""
    _outputs(probes, probes=True); _outputs(targets)
    require(type(inherited_families) is list and type(inherited_outputs) is list and
            len(inherited_families) == len(inherited_outputs) == 8,
            'complete eight-program inherited evaluator inventory required')
    inherited = [match_outputs(family, target_family, output, targets)
                 for family, output in zip(inherited_families, inherited_outputs, strict=True)]
    candidate = match_outputs(candidate_family, target_family, candidate_outputs, targets)
    nontrivial = any(target != probe for target, probe in zip(targets, probes, strict=True))
    predecessor_pass = any(row['passes'] for row in inherited)
    passed = nontrivial and not predecessor_pass and candidate['passes']
    return {'nontrivial': nontrivial, 'predecessor_pass': predecessor_pass,
            'family_matches': candidate['family_matches'], 'probe_matches': candidate['probe_matches'],
            'first_mismatch': candidate['first_mismatch'], 'candidate_pass': candidate['passes'],
            'passed': passed, 'verdict': 'candidate_passed' if passed else 'reject',
            'reason_codes': [] if passed else [REJECTION_REASON]}


def imported_inputs(y: dict) -> tuple[dict, dict, dict, dict, dict]:
    """Actual retained V, U, Q, joint and producer inputs, not a substitute model."""
    _, v, u = previous.imported_inputs(y['producer_sha256_packet'])
    q = u['captured_json_packet']['routing_packet']['sparse_packet']['finite_packet']
    joint = q['protected_packet']['joint_packet']
    return v, u, q, joint, producer_packet(u)


def inputs_from_transcript(y: dict, transcript: bytes) -> dict:
    require(type(transcript) is bytes and len(transcript) == TRANSCRIPT_BYTES and
            sha(transcript) == FIXTURE_SHA == y['bindings']['transcript_sha256'],
            'exact original selected transcript required')
    data = load_json_strict(transcript)
    exact(data, {'events', 'schema_id'})
    require(canonical(data) == transcript and type(data['events']) is list and len(data['events']) == 20,
            'complete canonical selected transcript required')
    require(canonical(previous.inputs_from_transcript(y['producer_sha256_packet'], transcript)) ==
            canonical(y['inputs']), 'transcript differs from actual retained Y inputs')
    return {'transcript_hex': transcript.hex()}


def _work(kind: str, identity: str, role: str, program_index: int | None,
          probe_index: int | None, value: dict, output: object) -> dict:
    source, result = canonical(value), canonical(output)
    return {'kind': kind, 'identity': identity, 'role': role, 'program_index': program_index,
            'probe_index': probe_index, 'input_hex': source.hex(), 'output_hex': result.hex(),
            'input_sha256': sha(source), 'output_sha256': sha(result)}


def _resource(work: list[dict], q: dict) -> dict:
    resource = q['resource']
    raw = bytes.fromhex(q['retained_hex'][JOURNAL_PATH])
    require(sha(raw) == q['retained_sha256'][JOURNAL_PATH] == resource['journal_sha256'],
            'retained Q resource journal anchor differs')
    checked = resource_replay(raw, expected_head=resource['journal_head'],
        policy=Policy.from_json(resource['policy']), expected_binding=resource['binding'])
    require(checked.status == 'sealed' and checked.pending_hash is None,
            'complete retained reference journal required')
    records = [parse(line) for line in raw.splitlines()]
    require(len(work) == len(checked.operation_ids) == 153 and len(records) == 308,
            'complete 153-operation reference work inventory required')
    for i, task in enumerate(work):
        reserve, result = records[2 * i + 1]['body'], records[2 * i + 2]['body']
        require((reserve['operation'], reserve['operation_id'], reserve['input_sha256']) ==
                (task['kind'], task['identity'], task['input_sha256']),
                'derived reference work order or input differs from retained N journal')
        require(result['ok'] is True and result['result_sha256'] == task['output_sha256'],
                'independent vector output differs from retained N journal')
    require([task['kind'] for task in work] == resource['charge_sequence'] == list(checked.charges) and
            [task['identity'] for task in work] == list(checked.operation_ids) and
            list(checked.spent) == resource['spent'] == [9, 144, 576, 576] and
            checked.charged_cost == resource['charged_cost'] == 4032 and
            resource['operation_count'] == 153,
            'actual Q resource operation sequence or declared tariff differs')
    return {**resource, 'operation_ids': list(checked.operation_ids), 'journal_events': len(records)}


def derive_evaluation(y: dict, inputs: dict) -> dict:
    """Reconstruct outputs without consulting recorded verdicts or worker code."""
    exact(inputs, {'transcript_hex'})
    raw = metadata.image_bytes(inputs['transcript_hex'])
    require(inputs_from_transcript(y, raw) == inputs, 'selected transcript projection differs')
    events = load_json_strict(raw)['events']
    v, u, q, joint, producer = imported_inputs(y)
    opening = previous._decode(y['inputs']['secret_hex'])
    probes = _outputs(opening['probes'], probes=True)
    target_program = {'family': FAMILIES.index(opening['objective_family']),
                      'variant': opening['target_variant'], 'a': opening['target_a'], 'b': opening['target_b']}
    targets = [execute_vector(target_program, probe) for probe in probes]
    before = v['registry_images']['before']['programs']
    inherited = [{'key': entry['key'], 'program': metadata.decode_program(bytes.fromhex(entry['image_hex']))}
                 for entry in before]
    require(len(inherited) == 8 and
            canonical([row['program'] for row in inherited]) == canonical(joint['task_meanings']['before']['programs']),
            'complete inherited order differs from actual Q predecessor programs')
    inherited_parameters = [program_parameters(row['program']) for row in inherited]
    inherited_outputs = [[execute_vector(program, probe) for probe in probes] for program in inherited_parameters]
    # Q and V enumerate installed programs by key; N ran them in historical
    # promotion order. Preserve this real permutation rather than relabel work.
    inherited_work_order = sorted(range(8), key=lambda i: inherited[i]['program']['promotion_index'])
    require([inherited[i]['program']['promotion_index'] for i in inherited_work_order] == list(range(8)),
            'complete inherited historical promotion order required')
    inherited_checks = [match_outputs(program['family'], target_program['family'], output, targets)
        for program, output in zip(inherited_parameters, inherited_outputs, strict=True)]
    trace = producer['trace']
    steps, choices = trace['steps'], u['selected_choices']
    require(type(steps) is list and type(choices) is list and len(steps) == len(choices) == 9,
            'complete nine-attempt selected producer prefix required')
    candidates, candidate_outputs, outcomes = [], [], []
    work = [_work('vector', f'target:{j}', 'target', None, j,
        {'role': 'target', 'vector': probe, 'parameters': [opening['objective_family'],
            target_program['variant'], target_program['a'], target_program['b']]}, targets[j])
        for j, probe in enumerate(probes)]
    for work_index, program_index in enumerate(inherited_work_order):
        row = inherited[program_index]
        work.extend(_work('vector', f'inherited:{work_index}:{j}', 'inherited', program_index, j,
            {'role': 'inherited', 'program': row['program'], 'vector': probe}, inherited_outputs[program_index][j])
            for j, probe in enumerate(probes))
    for i, (step, choice) in enumerate(zip(steps, choices, strict=True)):
        _integer(choice, 0, 31, 'selected grammar index outside fixed inventory')
        descriptor = v['candidate_images'][choice]
        program = metadata.decode_program(bytes.fromhex(descriptor['image_hex']))
        freeze_event, evaluation_event = events[2 * i + 1:2 * i + 3]
        require(freeze_event['request']['op'] == 'freeze_candidate' and
                evaluation_event['request']['op'] == 'evaluate', 'candidate event order differs')
        artifact = evaluation_event['request']['artifact']
        report = evaluation_event['response']['payload']
        key = digest(descriptor['key'])
        require(step['selected_index'] == choice and
                key == step['program_hash'] == artifact['program_hash'] == report['program_hash'] and
                canonical(program) == canonical(step['program']) == canonical(artifact['program']),
                'attempted program differs from actual V descriptor and Q selected choice')
        candidate = {'key': key, 'grammar_index': choice, 'program': program}
        parameters = program_parameters(program)
        outputs = [execute_vector(parameters, probe) for probe in probes]
        outcome = verdict_from_outputs(target_program['family'], probes, targets,
            [row['family'] for row in inherited_parameters], inherited_outputs, parameters['family'], outputs)
        require(outcome['verdict'] == report['verdict'] == step['verdict'] and
                outcome['reason_codes'] == report['reason_codes'] == step['reason_codes'],
                'independent evaluator result differs from retained report or Q verdict prefix')
        require(type(report['evaluation_index']) is int and report['evaluation_index'] == i and
                report['event'] == 'candidate_evaluated' and
                report['challenge_commitment_hash'] == y['bindings']['challenge_commitment_hash'] and
                report['predecessor_state_hash'] == y['bindings']['historical_state_hash'],
                'evaluation report context or index differs from retained Y/Q context')
        for name in ('artifact_hash', 'candidate_freeze_hash', 'evaluation_hash'):
            require(digest(report[name]) == step[name], 'evaluation report differs from actual Q producer binding')
        require(report['artifact_hash'] == artifact['artifact_hash'] and
                report['candidate_freeze_hash'] == evaluation_event['request']['candidate_freeze_hash'] ==
                freeze_event['response']['payload']['receipt']['candidate_freeze_hash'],
                'evaluation differs from the preceding candidate freeze')
        outcomes.append({'evaluation_index': i, 'program_hash': key, 'selected_index': choice,
            'response_sequence': evaluation_event['response']['sequence'],
            'payload_hex': canonical(report).hex(),
            **outcome, **{name: report[name] for name in ('artifact_hash', 'candidate_freeze_hash',
                'evaluation_hash', 'challenge_commitment_hash', 'predecessor_state_hash')}})
        candidates.append(candidate); candidate_outputs.append(outputs)
        work.append(_work('candidate', f'candidate:{i}', 'candidate', i, None,
            {'program': program}, {'program_sha256': sha(canonical(program))}))
        work.extend(_work('vector', f'candidate:{i}:probe:{j}', 'candidate', i, j,
            {'role': 'candidate', 'program': program, 'vector': probe}, outputs[j])
            for j, probe in enumerate(probes))
    verdicts = [row['passed'] for row in outcomes]
    require(verdicts == [False] * 8 + [True], 'selected complete rejection prefix and first success differ')
    seal = events[-1]['response']['payload']
    require(trace['terminal'] == seal['terminal_action'] == 'await_root_verification' and
            seal['candidate_evaluations'] == 9 and seal['complete_bounded_coverage'] is False and
            trace['selected_program_hash'] == seal['selected_candidate_hash'] == candidates[-1]['key'] ==
            y['bindings']['program_hash'], 'selected terminal candidate differs from actual Q/Y binding')
    meanings = joint['task_meanings']
    task = next(row for row in meanings['tasks'] if row['task_id'] == meanings['new_task_id'])
    require(task['kind'] == 'vectors' and task['program_hash'] is None and
            task['family'] == opening['objective_family'] and task['inputs'] == probes and task['targets'] == targets,
            'opening-derived outputs differ from actual Q task contract')
    profile = load_json_strict(bytes.fromhex(q['retained_hex'][PROFILE_PATH]), require_canonical=False)
    require(profile['verdicts'] == [row['verdict'] for row in outcomes],
            'selected outcomes differ from retained N reference profile')
    return {'opening': opening, 'target_program': target_program, 'inherited_programs': inherited,
            'candidate_programs': candidates, 'target_outputs': targets, 'inherited_outputs': inherited_outputs,
            'candidate_outputs': candidate_outputs, 'inherited_checks': inherited_checks,
            'inherited_work_order': inherited_work_order,
            'outcomes': outcomes, 'choices': choices, 'verdicts': verdicts, 'work': work,
            'resource': _resource(work, q), 'terminal': trace['terminal'],
            'selected_program_hash': candidates[-1]['key'], 'final_prefix_hash': trace['final_prefix_hash']}


def packet_from_inputs(y: dict, inputs: dict) -> dict:
    return {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
            'objective_context_packet': y, 'objective_context_packet_sha256': Y_PACKET_SHA,
            'bindings': y['bindings'], 'retained_y': dict(RETAINED_Y_PINS),
            'profile': dict(PROFILE), 'scope': dict(SCOPE), 'claims': {key: False for key in FALSE_CLAIMS},
            'inputs': inputs, 'evaluation': derive_evaluation(y, inputs)}


def validate_packet(packet: dict) -> previous.PreparedObjectiveContext:
    exact(packet, {'schema', 'policy', 'base_commit', 'objective_context_packet', 'objective_context_packet_sha256',
        'bindings', 'retained_y', 'profile', 'scope', 'claims', 'inputs', 'evaluation'})
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'evaluation trace schema/policy/base differs')
    require(canonical(packet['profile']) == canonical(PROFILE) and canonical(packet['scope']) == canonical(SCOPE),
            'evaluation trace profile/scope differs')
    require(canonical(packet['claims']) == canonical({key: False for key in FALSE_CLAIMS}),
            'unsupported evaluation trace authority or closure claim')
    require(canonical(packet['retained_y']) == canonical(RETAINED_Y_PINS), 'retained Y anchors differ')
    y = packet['objective_context_packet']
    raw_y = canonical(y)
    require(sha(raw_y) == packet['objective_context_packet_sha256'] == Y_PACKET_SHA,
            'actual imported Y packet differs')
    require(canonical(packet['bindings']) == canonical(y['bindings']), 'evaluation package/program binding differs')
    expected = derive_evaluation(y, packet['inputs'])
    require(canonical(packet['evaluation']) == canonical(expected),
            'complete evaluator outputs, verdict prefix or resource work differs')
    return previous.PreparedObjectiveContext(raw_y)


@dataclass(frozen=True, slots=True)
class PreparedEvaluationTrace:
    packet_bytes: bytes
    _previous: previous.PreparedObjectiveContext = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable evaluation trace packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical evaluation trace packet required')
        object.__setattr__(self, '_previous', validate_packet(packet))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def objective_context(self) -> previous.PreparedObjectiveContext:
        return self._previous


def read_retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in {**RETAINED_Y_PINS, FIXTURE_PATH: FIXTURE_SHA}.items():
        path = root / name
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained Z input: ' + name)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained Z input changed: ' + name)
        result[name] = raw
    return result


def prepare_evaluation_trace(root: Path, packages: Path) -> PreparedEvaluationTrace:
    """Freshly reconstruct inherited inputs and selected work without campaigns."""
    retained = read_retained(root)
    inherited = previous.prepare_objective_context(root, packages)
    require(inherited.packet_bytes == retained[Y_PACKET], 'fresh objective inputs differ from completed Y')
    y = inherited.packet
    inputs = inputs_from_transcript(y, retained[FIXTURE_PATH])
    prepared = PreparedEvaluationTrace(canonical(packet_from_inputs(y, inputs)))
    require(retained == read_retained(root), 'retained Y/fixture inputs changed during evaluation preparation')
    return prepared


def verify_packet_bytes(raw: bytes, recomputed: PreparedEvaluationTrace, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external evaluation trace packet anchor differs')
    require(type(recomputed) is PreparedEvaluationTrace and raw == recomputed.packet_bytes,
            'evaluation trace packet differs from independent reconstruction')
    PreparedEvaluationTrace(raw)


def summary(prepared: PreparedEvaluationTrace) -> dict:
    require(type(prepared) is PreparedEvaluationTrace, 'validated evaluation trace packet required')
    evaluation = prepared.packet['evaluation']
    work, outcomes = evaluation['work'], evaluation['outcomes']
    vector_work = [row for row in work if row['kind'] == 'vector']
    input_bytes = sum(len(bytes.fromhex(row['input_hex'])) for row in work)
    output_bytes = sum(len(bytes.fromhex(row['output_hex'])) for row in work)
    payload_bytes = sum(len(bytes.fromhex(row['payload_hex'])) for row in outcomes)
    return {'target_vector_calls': len(evaluation['target_outputs']),
            'inherited_vector_calls': sum(map(len, evaluation['inherited_outputs'])),
            'candidate_vector_calls': sum(map(len, evaluation['candidate_outputs'])),
            'vector_calls': len(vector_work), 'candidate_attempts': len(outcomes), 'operations': len(work),
            'input_values': 4 * len(vector_work), 'output_values': sum(
                len(load_json_strict(bytes.fromhex(row['output_hex']))) for row in vector_work),
            'declared_spent': evaluation['resource']['spent'], 'declared_cost': evaluation['resource']['charged_cost'],
            'rejections': sum(not row['passed'] for row in outcomes),
            'passes': sum(row['passed'] for row in outcomes),
            'nontrivial': outcomes[0]['nontrivial'], 'predecessor_pass': outcomes[0]['predecessor_pass'],
            'rejected_candidate_family_matches': [row['family_matches'] for row in outcomes[:-1]],
            'choices': evaluation['choices'], 'verdicts': evaluation['verdicts'],
            'selected_program_hash': evaluation['selected_program_hash'], 'terminal': evaluation['terminal'],
            'resource_journal_sha256': evaluation['resource']['journal_sha256'],
            'objective_context_packet_sha256': Y_PACKET_SHA,
            'transcript_sha256': FIXTURE_SHA, 'transcript_bytes': TRANSCRIPT_BYTES,
            'work_input_bytes': input_bytes, 'work_output_bytes': output_bytes,
            'evaluation_payload_bytes': payload_bytes, 'json_images': 2 * len(work) + len(outcomes),
            'json_image_bytes': input_bytes + output_bytes + payload_bytes,
            'fresh_worker_output_captured': False, 'candidate_active': False, 'promotion_authorized': False}
