"""Phase 17AF: one concrete, inactive second step under AE's fixed meanings.

The public AD context and its initial production choice were already committed.
No nonce search, hidden challenge, worker, active-store write or promotion is
performed. Fresh package bytes and a precharged reference-work journal supply
the selected finite inputs; acceptance requires the separate pinned Lean gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from . import successor_context as ad
from . import task_interpretation as ae
from .bootstrap import _validate_program, _read_pinned_archive, _member, M9_BUNDLE_SHA256
from .challenge_protocol import execute_reference
from .conservative_extension import registry_from_files
from .controller import Action, FIXED_VERIFIER, checkpoint, decide, record_evaluation, restore, _hash
from .finite_kernel import PreparedFiniteKernel, FALSE_CLAIMS
from .frontier_meanings import check_task
from .frontier_recertification import _named_source, _dynamic_source, challenges15, decode_plan
from .learned_state_binding import GROUPS, state_projection
from .materialized import (MANIFEST, PackageReceipt, execute_installed, execute_matrix,
                           snapshot, require, sha, safe_relative)
from .protected_semantics import observe, observation_projection, protected_tasks
from .resource_ledger import Policy, TARIFFS, add, cost, _no_links

BASE = 'b964bb738890047fea021a50aeb1160eb502e3d4'
SCHEMA = 'rcp-rclm.phase17af.second-step-packet.v1'
POLICY = 'phase17af.saved-ad-initial-choice-fixed-ae-interpretation.v1'
PACKAGE_SCHEMA = 'rcp-rclm.phase17af.inactive-second-package.v1'
JOURNAL_SCHEMA = 'rcp-rclm.phase17af.reference-work-journal.v1'
JOURNAL_DOMAIN = b'RCPRCLM-PHASE17AF-REFERENCE-WORK-V1\0'
MAX_BYTES = 40 * 1024 * 1024
AD_ROOT = 'artifacts/development/phase17ad/op-1feb4d24e918/gate'
AE_ROOT = 'artifacts/development/phase17ae/op-87a74e2e2e9d/gate'
AD_PACKET_SHA = 'b81bc075bd469b36a7f25a186a54a169e82140a8ef278a43099a12f820438a45'
AE_PACKET_SHA = 'f1dbb5409f39ee8b24860366876b47075855372398347274a369ccdd31ef6bb4'
AD_EXECUTION_SHA = 'fe6d0665f2837765cb49e70de4edd204abcc9cfa75575cc1f43d52d84d144d66'
AE_EXECUTION_SHA = 'fd33a192084c848f396a6b45fa12dc30c2d0aed2508d25e36e7cf0b3cd1ad03f'
RETAINED_PINS = {AD_ROOT + '/packet.json': AD_PACKET_SHA, AE_ROOT + '/packet.json': AE_PACKET_SHA,
                 AD_ROOT + '/execution.json': AD_EXECUTION_SHA, AE_ROOT + '/execution.json': AE_EXECUTION_SHA}
SELECTED_PROGRAM = 'c7e8b8e3c29edc92452562acebcfc5c9574a2f7e94d07d7ef3f4068f4010f823'
SELECTED_TASK = 41
SELECTED_NAME = 'phase17ae.adapter.affine.0.19'
SELECTED_INDEX = 30
UNMEASURED = (
    'full 32-program generation and ranking', 'package preparation, copying and hashing',
    'independent reference-interpreter comparisons and all validation/recomputation',
    'protected model and proof-source observations', 'journal persistence and filesystem work',
    'Lean compilation, proof verification and Python tests',
    'wall time, CPU/GPU time, energy, RSS and storage; no absent measurement is zeroed',
)
SCOPE = {
    'domain': 'one public inactive prospective second finite step from the selected AE successor',
    'selection': 'unchanged committed AD initial production choice; no nonce or challenge search',
    'interpretation': 'unchanged AE fixed 282-task catalog and semantic novelty guard',
    'objective': 'original AD retrieval_policy description retained; no objective/controller integration claim',
    'public_fields': 'the AD synthetic nonce and opaque commitment, not a newly opened live challenge',
    'history': 'AD context transcript_hash is its prospective-history anchor; AF reference_transcript_sha256 separately binds completed reference work',
    'resources': 'one candidate admission and 38 installed matrix calls; original four-dimension tariff',
    'physical_mapping': 'freshly checked bytes and serialized projection, not universal physical refinement',
    'formal_acceptance': 'requires the separate real pinned Lean gate; preparation is not acceptance',
    'historical_campaigns_rerun': False, 'fresh_workers': 0, 'fresh_live_challenges': 0,
    'physical_candidate_active': False, 'promotion_api': False,
}


def _exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), 'exact ' + label + ' fields required')


def _same(left, right, message):
    require(canonical(left) == canonical(right), message)


def _images(value):
    require(type(value) is dict and len(value) <= 32, 'bounded captured image inventory required')
    result = {}
    for name, image in value.items():
        safe_relative(name)
        result[name] = ae._image(image)
    return result


def _retained(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in RETAINED_PINS.items():
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'retained AD/AE record missing or linked')
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained AD/AE input differs: ' + name)
        result[name] = raw
    return result


def _selection(successor: ad.PreparedSuccessorContext, interpretation: ae.PreparedTaskInterpretation) -> dict:
    require(successor.finite().packet_bytes == interpretation.finite().packet_bytes,
            'AD and AE selected finite packets differ')
    s, a = successor.packet, interpretation.packet
    context = s['next_context']
    prefix = restore(canonical(context['initial_checkpoint']), expected_prefix_hash=context['initial_prefix_hash'])
    decision = decide(prefix)
    require(decision.action == Action.EVALUATE and decision.candidate_hash == SELECTED_PROGRAM and
            context['initial_candidate_index'] == SELECTED_INDEX and
            context['rows'][SELECTED_INDEX]['key'] == SELECTED_PROGRAM,
            'saved AD initial production choice differs')
    programs = [p for p in context['programs'] if digest(p) == decision.candidate_hash]
    require(len(programs) == 1, 'selected production program missing or duplicated')
    program = programs[0]; _validate_program(program)
    require(program['family'] == 'adapter_policy' and program['variant'] == 0 and
            program['parameter_a'] == -6 and program['parameter_b'] == 7 and
            program['generation'] == 2 and program['promotion_index'] == 1,
            'saved production adapter differs')
    task = ae.affine_task(0, 19)
    require(task['index'] == SELECTED_TASK and task['task_id'] == SELECTED_NAME and
            a['observations']['after']['affine_solved_indices'] == [259] and
            SELECTED_TASK not in a['observations']['after']['checked_declared_indices'],
            'fixed selected contract is not semantically new')
    require(context['provenance_context']['parent_package'] ==
            interpretation.finite().packet['bindings']['candidate_physical_hash'],
            'AD next context is not parented at the AE selected successor')
    return {'program': program, 'program_hash': SELECTED_PROGRAM, 'index': SELECTED_INDEX,
            'task': task, 'decision_hash': decision.decision_hash}


def _after_metadata(successor, interpretation, before: dict[str, bytes]) -> tuple[dict, dict]:
    selected = _selection(successor, interpretation)
    first = interpretation.finite().packet
    joint = first['protected_packet']['joint_packet']
    _same({name: raw.hex() for name, raw in before.items()}, interpretation.packet['captured_inputs']['after'],
          'second predecessor images differ from fixed AE successor')
    old = load_json_strict(before[MANIFEST]); registry = load_json_strict(before['registry/manifest.json'])
    keys = joint['typed_binding']['candidate']['base']
    registry.update(inherited_program_hashes=list(keys), candidate_program_hash=SELECTED_PROGRAM,
                    inherited_frontier=list(joint['typed_binding']['candidate']['capabilityFrontier']))
    new_rows = {row['path']: dict(row) for row in old['files']}
    replacements = {'registry/manifest.json': canonical(registry),
                    'registry/programs/' + SELECTED_PROGRAM + '.json': canonical(selected['program'])}
    require('registry/programs/' + SELECTED_PROGRAM + '.json' not in new_rows, 'candidate shadows old program')
    for name, raw in replacements.items():
        new_rows[name] = {'path': name, 'mode': '0644', 'size': len(raw), 'sha256': sha(raw)}
    manifest = {'schema_id': PACKAGE_SCHEMA, 'kind': 'inactive_second_prospective_candidate',
        'parent_package_hash': old['materialized_package_hash'], 'parent_manifest_sha256': sha(before[MANIFEST]),
        'historical_state_hash': old['historical_state_hash'], 'ad_packet_sha256': AD_PACKET_SHA,
        'ae_packet_sha256': AE_PACKET_SHA, 'program_hash': SELECTED_PROGRAM,
        'fixed_task_index': SELECTED_TASK, 'fixed_task_name': SELECTED_NAME,
        'files': [new_rows[name] for name in sorted(new_rows)],
        'candidate_active': False, 'promotion_authorized': False, 'claims': {k: False for k in FALSE_CLAIMS}}
    manifest['materialized_package_hash'] = digest(manifest)
    require(manifest['materialized_package_hash'] != old['materialized_package_hash'], 'second package did not change')
    replacements[MANIFEST] = canonical(manifest)
    return replacements, manifest


def _captured(successor, interpretation, captures):
    _exact(captures, {'before', 'after'}, 'second physical input')
    before, after = _images(captures['before']), _images(captures['after'])
    changes, manifest = _after_metadata(successor, interpretation, before)
    _same({name: raw.hex() for name, raw in {**before, **changes}.items()}, captures['after'],
          'second candidate captured bytes differ from exact inactive append')
    require(len(before) == 11 and len(after) == 12, 'second captured input count differs')
    return {'before': before, 'after': after}, manifest


def _intent(successor, interpretation, manifest):
    c = successor.packet['next_context']
    return {'schema': 'rcp-rclm.phase17af.public-second-selection-intent.v1', 'policy': POLICY,
        'ad_packet_sha256': AD_PACKET_SHA, 'ae_packet_sha256': AE_PACKET_SHA,
        'ad_execution_sha256': AD_EXECUTION_SHA, 'ae_execution_sha256': AE_EXECUTION_SHA,
        'predecessor_package_hash': manifest['parent_package_hash'],
        'candidate_package_hash': manifest['materialized_package_hash'],
        'prospective_state_hash': successor.packet['prospective_state_hash'],
        'prospective_history_hash': successor.packet['prospective_history_hash'],
        'context_hash': c['provenance_context']['context_hash'], 'search_freeze_hash': c['freeze_hash'],
        'initial_prefix_hash': c['initial_prefix_hash'], 'selected_index': SELECTED_INDEX,
        'selected_program': SELECTED_PROGRAM, 'fixed_task_index': SELECTED_TASK, 'fixed_task_name': SELECTED_NAME,
        'original_ad_objective_family': successor.packet['objective']['objective_family'],
        'live_challenge_opened': False, 'objective_integration_claimed': False, 'promotion_authorized': False}


def _programs(images):
    return [(key, load_json_strict(raw)) for key, raw in registry_from_files(images).entries]


def _work(captures, intent):
    result = [{'kind': 'candidate', 'operation_id': 'af-candidate-0000',
        'input': {'schema': 'phase17af.candidate-admission-input.v1', 'selection_intent_sha256': sha(canonical(intent)),
                  'program_hash': SELECTED_PROGRAM, 'task_index': SELECTED_TASK},
        'output': {'schema': 'phase17af.candidate-admission-result.v1', 'admitted_for_reference_evaluation': True,
                   'program_hash': SELECTED_PROGRAM, 'task_index': SELECTED_TASK, 'root_authorized': False}}]
    for side in ('before', 'after'):
        package_hash = load_json_strict(captures[side][MANIFEST])['materialized_package_hash']
        for index, (key, program) in enumerate(_programs(captures[side])):
            for probe, vector in enumerate(ae.PROBES):
                matrix, reference = execute_matrix(program, list(vector)), execute_reference(program, list(vector))
                require(matrix == reference, 'independent second-step interpreters disagree')
                result.append({'kind': 'vector', 'operation_id': f'af-{side}-{index:02d}-{probe}',
                    'input': {'schema': 'phase17af.installed-vector-input.v1', 'side': side,
                              'package_hash': package_hash, 'program_hash': key,
                              'descriptor_sha256': sha(captures[side]['registry/programs/' + key + '.json']),
                              'input_vector': list(vector)},
                    'output': matrix})
    require(len(result) == 39 and len({row['operation_id'] for row in result}) == 39, 'exact second work inventory required')
    return result


def _event(body, index, previous):
    core = {'index': index, 'previous': previous, 'body': body}
    return {**core, 'hash': sha(JOURNAL_DOMAIN + canonical(core))}


def _journal_rows(work, policy, intent):
    rows = []; spent = (0, 0, 0, 0)
    def emit(body):
        row = _event(body, len(rows), rows[-1]['hash'] if rows else '0' * 64)
        rows.append(row)
        return row
    emit({'kind': 'open', 'schema': JOURNAL_SCHEMA, 'selection_intent_sha256': sha(canonical(intent)),
          'policy': policy.to_json(), 'timing': 'unmeasured; no elapsed-time value asserted'})
    for task in work:
        spent = add(spent, TARIFFS[task['kind']]); require(policy.fits(spent), 'second reference work exceeds original policy')
        reserve = emit({'kind': 'reserve', 'operation': task['kind'], 'operation_id': task['operation_id'],
            'input_sha256': sha(canonical(task['input'])), 'charge': list(TARIFFS[task['kind']]), 'spent_after': list(spent)})
        emit({'kind': 'result', 'operation_id': task['operation_id'], 'reservation_hash': reserve['hash'],
              'result_sha256': sha(canonical(task['output'])), 'completed': True})
    emit({'kind': 'seal', 'operation_count': len(work), 'spent': list(spent), 'charged_cost': cost(spent),
          'status': 'completed_declared_reference_work'})
    return rows, spent


def _journal_bytes(rows):
    return b''.join(canonical(row) + b'\n' for row in rows)


def _execute_work(path, work, policy, intent, receipts):
    """Persist each reservation before the fixed trusted installed-byte call."""
    require(not path.exists() and not path.is_symlink(), 'new reference-work journal required')
    rows, spent = _journal_rows(work, policy, intent)
    actual = []
    with path.open('xb') as stream:
        def persist(row):
            data = canonical(row) + b'\n'
            written = stream.write(data)
            require(type(written) is int and written == len(data), 'short reference-work journal write')
            stream.flush(); os.fsync(stream.fileno())
        persist(rows[0])
        for i, task in enumerate(work):
            persist(rows[1 + 2 * i])
            if task['kind'] == 'candidate':
                # Reopen the actual installed candidate after its reservation;
                # earlier planning checks are outside this narrow tariff.
                receipt = receipts['after']
                raw = (receipt.root / ('registry/programs/' + SELECTED_PROGRAM + '.json')).read_bytes()
                program = load_json_strict(raw); _validate_program(program)
                registry = load_json_strict((receipts['before'].root / 'registry/manifest.json').read_bytes())
                old_keys = registry['inherited_program_hashes'] + [registry['candidate_program_hash']]
                require(digest(program) == SELECTED_PROGRAM and canonical(program) == raw and
                        SELECTED_PROGRAM not in old_keys and program['family'] == 'adapter_policy' and
                        program['variant'] == 0 and program['parameter_a'] - program['parameter_b'] == -13 and
                        receipt.package_hash == intent['candidate_package_hash'],
                        'installed candidate admission differs')
                result = {'schema': 'phase17af.candidate-admission-result.v1',
                    'admitted_for_reference_evaluation': True, 'program_hash': SELECTED_PROGRAM,
                    'task_index': SELECTED_TASK, 'root_authorized': False}
            else:
                entry = task['input']
                result = execute_installed(receipts[entry['side']], entry['program_hash'], entry['input_vector'])
            _same(result, task['output'], 'actual installed reference-work output differs')
            # This hash is computed from the returned output, not a supplied pass bit.
            result_row = _event({'kind': 'result', 'operation_id': task['operation_id'],
                'reservation_hash': rows[1 + 2 * i]['hash'], 'result_sha256': sha(canonical(result)),
                'completed': True}, 2 + 2 * i, rows[1 + 2 * i]['hash'])
            _same(result_row, rows[2 + 2 * i], 'actual operation receipt differs')
            persist(result_row); actual.append(result)
        persist(rows[-1])
    require(path.read_bytes() == _journal_bytes(rows), 'persisted reference-work journal differs')
    return rows, spent


def _fresh_proofs(receipt, bundle, protected):
    rows = []
    goals = {row['task_id']: row for row in protected['goals']}
    for task, _ in protected_tasks(bundle):
        goal = goals[task.task_id]
        require(goal['tokens'][-1] == 258 and all(0 <= x < 128 for x in goal['tokens'][:-1]),
                'protected source tokens differ')
        completion = bytes(goal['tokens'][:-1]).decode('ascii')
        name, source = _named_source(task.render_source(completion), task.task_id)
        rows.append({'task_id': task.task_id, 'source_sha256': sha(source), 'decode_hash': goal['decode_hash']})
    with _read_pinned_archive(bundle, M9_BUNDLE_SHA256) as archive:
        store = load_json_strict(_member(archive, 'campaign/answer_store_private.json', 65536), require_canonical=False)
    for challenge in challenges15(store):
        decoded = decode_plan(receipt.root / 'base', challenge.domain, challenge.parameter_a, challenge.parameter_b)
        source, _ = _dynamic_source(challenge, decoded)
        _, raw = _named_source(source, challenge.task_id)
        rows.append({'task_id': challenge.task_id, 'source_sha256': sha(raw), 'decode_hash': decoded.report_hash})
    require(len(rows) == 13, 'thirteen fixed proof observations required')
    return sorted(rows, key=lambda row: row['task_id'])


def _projection(images, manifest, interpretation, observations, proof_rows):
    finite = interpretation.finite().packet
    joint = finite['protected_packet']['joint_packet']; old = joint['typed_binding']['candidate']
    result, availability = {}, {}
    for side in ('before', 'after'):
        files = images[side]; m = load_json_strict(files[MANIFEST])
        index = {row['path']: row for row in m['files']}
        # Reconstruct each component's rows from this package's manifest; the
        # source of its grouping is the already checked immutable interpretation.
        frozen = [[{'path': row['path'], 'size': index[row['path']]['size'], 'sha256': index[row['path']]['sha256']}
                   for row in old[group]] for group in GROUPS]
        pairs = _programs(files); programs = [p for _, p in pairs]
        declared = list(range(22)) + ([] if side == 'before' else [SELECTED_TASK])
        names = list(old['capabilityFrontier']) + ([] if side == 'before' else [SELECTED_NAME])
        state = {'proof_observations': proof_rows[side], 'programs': programs,
                 'declared_ids': sorted(names), 'package_hash': m['materialized_package_hash']}
        legacy = [check_task(task, state) for task in joint['task_meanings']['tasks']]
        probes = [ae._program_observation(program) for program in programs]
        rows = [{'index': task['index'], 'task_id': task['task_id'],
                 'witnesses': [p['program_hash'] for p in probes if ae._affine_matches(p, task)]}
                for task in interpretation.packet['catalog']['tail']]
        solved = [row['index'] for row in rows if row['witnesses']]
        require(all(legacy) and solved == ([259] if side == 'before' else [41, 259]),
                'fixed-catalog preservation or semantic gain differs')
        result[side] = {'frozen': frozen, 'keys': [key for key, _ in pairs],
            'proofs': [[p['task_id'], p['source_sha256'], p['decode_hash']] for p in proof_rows[side]],
            'programs': programs, 'declared': declared, 'named_frontier': sorted(names),
            'semantic': observation_projection(observations[side]),
            'package_hash': m['materialized_package_hash'], 'root': FIXED_VERIFIER}
        availability[side] = {'legacy_checks': legacy, 'affine_rows': rows, 'affine_solved_indices': solved,
                              'checked_declared_indices': declared, 'program_observations': probes}
    return result, availability


def _derived(successor, interpretation, captures, protected, proof_rows, journal_hex):
    selected = _selection(successor, interpretation)
    images, manifest = _captured(successor, interpretation, captures)
    finite = interpretation.finite().packet
    old_semantic = finite['protected_packet']['after']
    old_proofs = finite['protected_packet']['joint_packet']['task_meanings']['after']['proof_observations']
    _exact(protected, {'before', 'after'}, 'protected observation')
    _exact(proof_rows, {'before', 'after'}, 'proof observation')
    for side in ('before', 'after'):
        _same(protected[side], {**old_semantic, 'package_hash': load_json_strict(images[side][MANIFEST])['materialized_package_hash']},
              'independently observed protected model data changed')
        _same(proof_rows[side], old_proofs, 'independently observed proof-source binding changed')
    projection, availability = _projection(images, manifest, interpretation, protected, proof_rows)
    intent = _intent(successor, interpretation, manifest)
    work = _work(images, intent); policy = Policy.from_json(finite['resource']['policy'])
    rows, spent = _journal_rows(work, policy, intent)
    require(type(journal_hex) is str and len(journal_hex) <= 2 * 1024 * 1024 and
            re.fullmatch('[0-9a-f]+', journal_hex) and len(journal_hex) % 2 == 0 and
            bytes.fromhex(journal_hex) == _journal_bytes(rows), 'reference-work sequence, results or journal binding differ')
    require(list(spent) == [1, 38, 152, 152] and cost(spent) == 976, 'reference-work counters differ')
    context = successor.packet['next_context']; provenance = context['provenance_context']
    charges = [row['kind'] for row in work]
    proposal = {'generator': provenance['generator'], 'parent_package': provenance['parent_package'],
        'context_hash': provenance['context_hash'], 'transcript_hash': provenance['transcript_hash'],
        'choices': [SELECTED_INDEX], 'verdicts': [True], 'program': SELECTED_PROGRAM,
        'candidate_package': manifest['materialized_package_hash']}
    evaluation = {'schema': 'phase17af.fixed-affine-reference-evaluation.v1',
        'selection_intent_sha256': sha(canonical(intent)), 'journal_head': rows[-1]['hash'],
        'work_results_sha256': sha(canonical([task['output'] for task in work])),
        'task_index': SELECTED_TASK, 'task_id': SELECTED_NAME, 'predecessor_holds': False,
        'candidate_holds': True, 'old_meanings_preserved': True, 'physical_candidate_active': False,
        'root_authorized': False, 'formal_acceptance_established': False}
    prefix = restore(canonical(context['initial_checkpoint']), expected_prefix_hash=context['initial_prefix_hash'])
    final = record_evaluation(prefix, decide(prefix), verdict='candidate_passed', evaluation_hash=digest(evaluation),
        reason_codes=(), predecessor_state_hash=prefix.frozen.view.predecessor_state_hash,
        challenge_commitment_hash=prefix.frozen.view.challenge_commitment_hash)
    final_raw = checkpoint(final)
    require(restore(final_raw, expected_prefix_hash=final.prefix_hash) == final and
            decide(final).action == Action.AWAIT_ROOT_VERIFICATION and len(final.observations) == 1,
            'second production controller prefix differs')
    transcript = {'schema': 'phase17af.public-reference-transcript.v1', 'intent': intent,
        'initial_checkpoint_sha256': sha(canonical(context['initial_checkpoint'])),
        'initial_decision_hash': selected['decision_hash'], 'evaluation': evaluation,
        'evaluation_hash': digest(evaluation), 'final_checkpoint': load_json_strict(final_raw),
        'final_prefix_hash': final.prefix_hash, 'terminal_action': decide(final).action.value,
        'proposal': proposal, 'live_challenge_opened': False, 'promotion_authorized': False}
    resource = {'profile': 'phase17af.installed-matrix-reference-work.v1', 'policy': policy.to_json(),
        'charge_sequence': charges, 'spent': list(spent), 'charged_cost': cost(spent),
        'operation_count': len(work), 'vector_calls': 38, 'candidate_admissions': 1,
        'work': work, 'journal_sha256': sha(_journal_bytes(rows)), 'journal_head': rows[-1]['hash'],
        'journal_event_count': len(rows), 'selection_intent_sha256': sha(canonical(intent)),
        'timing_measured': False, 'unmeasured': list(UNMEASURED)}
    update = {'key': SELECTED_PROGRAM, 'program': selected['program'], 'task': SELECTED_TASK,
        'task_name': SELECTED_NAME, 'parent_package': manifest['parent_package_hash'],
        'candidate_package': manifest['materialized_package_hash'], 'context_hash': provenance['context_hash'],
        'charges': charges}
    summary = {'first_frontier': 21, 'second_before_frontier': 22, 'second_after_frontier': 23,
        'second_before_programs': 9, 'second_after_programs': 10, 'fixed_catalog_tasks': 282,
        'selected_task_index': SELECTED_TASK, 'selected_affine_signature': [1, -13],
        'before_affine_solved': 1, 'after_affine_solved': 2, 'after_affine_unsolved': 258,
        'production_candidates': 32, 'selected_production_index': SELECTED_INDEX,
        'candidate_evaluations': 1, 'rejected_candidates': 0, 'captured_files': 23,
        'metered_operations': 39, 'charged_cost': 976, 'fresh_worker_sessions': 0,
        'fresh_live_challenges': 0, 'physical_candidate_active': False, 'formal_acceptance_required': True}
    return {'selection_intent': intent, 'second_context': provenance, 'proposal': proposal,
        'update': update, 'finite_projection': projection, 'availability': availability,
        'reference_transcript': transcript, 'reference_transcript_sha256': sha(canonical(transcript)),
        'resource': resource, 'summary': summary}


def validate_packet(packet):
    _exact(packet, {'schema', 'policy', 'base_commit', 'successor_packet', 'interpretation_packet',
        'retained_execution_hex', 'retained_sha256', 'captured_inputs', 'protected_observations',
        'proof_observations', 'reference_journal_hex', 'selection_intent', 'second_context', 'proposal',
        'update', 'finite_projection', 'availability', 'reference_transcript', 'reference_transcript_sha256', 'resource', 'summary',
        'scope', 'claims'}, 'second-step packet')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'second-step schema, policy or continuation baseline differs')
    _same(packet['scope'], SCOPE, 'second-step scope differs')
    _same(packet['claims'], {k: False for k in FALSE_CLAIMS}, 'second-step authority escalation')
    _same(packet['retained_sha256'], RETAINED_PINS, 'retained AD/AE anchors differ')
    for name, value, expected in (('AD', packet['successor_packet'], AD_PACKET_SHA),
                                  ('AE', packet['interpretation_packet'], AE_PACKET_SHA)):
        require(sha(canonical(value)) == expected, 'fixed ' + name + ' packet differs')
    _exact(packet['retained_execution_hex'], {AD_ROOT + '/execution.json', AE_ROOT + '/execution.json'}, 'retained executions')
    for name, image in packet['retained_execution_hex'].items():
        raw = ae._image(image)
        require(sha(raw) == RETAINED_PINS[name], 'retained completed execution differs')
    successor = ad.PreparedSuccessorContext(canonical(packet['successor_packet']))
    interpretation = ae.PreparedTaskInterpretation(canonical(packet['interpretation_packet']))
    expected = _derived(successor, interpretation, packet['captured_inputs'], packet['protected_observations'],
                        packet['proof_observations'], packet['reference_journal_hex'])
    for key, value in expected.items():
        _same(packet[key], value, 'second-step derivation differs: ' + key)
    return successor, interpretation


@dataclass(frozen=True, slots=True)
class PreparedSecondStep:
    packet_bytes: bytes
    _successor: ad.PreparedSuccessorContext = field(init=False, repr=False, compare=False)
    _interpretation: ae.PreparedTaskInterpretation = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable second-step packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical second-step packet required')
        successor, interpretation = validate_packet(packet)
        object.__setattr__(self, '_successor', successor); object.__setattr__(self, '_interpretation', interpretation)

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)

    def finite(self) -> PreparedFiniteKernel:
        return self._interpretation.finite()

    def successor_context(self) -> ad.PreparedSuccessorContext:
        return self._successor

    def interpretation(self) -> ae.PreparedTaskInterpretation:
        return self._interpretation


def prepare_second_step(root: Path, packages: Path) -> PreparedSecondStep:
    """Reconstruct first packages once, then materialize and observe the second."""
    _no_links(packages)
    require(not packages.exists() and root.resolve() not in packages.resolve().parents and
            root.resolve() != packages.resolve(), 'new external second-step workspace required')
    retained = _retained(root)
    successor = ad.prepare_successor_context(root, packages / 'first')
    require(successor.packet_bytes == retained[AD_ROOT + '/packet.json'], 'fresh AD context differs from committed one')
    finite = successor.finite()
    first_images = {side: snapshot(packages / 'first' / side) for side in ('before', 'after')}
    captured_ae = {side: {name: files[name].hex() for name in sorted(ae._input_names(finite, side))}
                  for side, files in first_images.items()}
    for side, key in (('before', 'predecessor_physical_hash'), ('after', 'candidate_physical_hash')):
        ae._complete_snapshot(first_images[side], expected_package_hash=finite.packet['bindings'][key])
    interpretation = ae.PreparedTaskInterpretation(canonical({'schema': ae.SCHEMA, 'policy': ae.POLICY,
        'base_commit': ae.BASE, 'finite_packet': finite.packet, 'finite_packet_sha256': sha(finite.packet_bytes),
        'captured_inputs': captured_ae, **ae._derived(finite, captured_ae), 'scope': dict(ae.SCOPE),
        'claims': {k: False for k in FALSE_CLAIMS}}))
    require(interpretation.packet_bytes == retained[AE_ROOT + '/packet.json'], 'fresh AE interpretation differs')
    before = first_images['after']; before_small = _images(captured_ae['after'])
    changes, manifest = _after_metadata(successor, interpretation, before_small)
    after = {**before, **changes}
    destination = packages / 'second'
    require(not destination.exists() and not destination.is_symlink(), 'new inactive second package required')
    destination.mkdir()
    for name, raw in after.items():
        safe_relative(name); path = destination / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    require(snapshot(destination) == after, 'fresh second package differs from full expected bytes')
    ae._complete_snapshot(after, expected_package_hash=manifest['materialized_package_hash'])
    captures = {'before': {name: raw.hex() for name, raw in before_small.items()},
                'after': {name: raw.hex() for name, raw in {**before_small, **changes}.items()}}
    images, _ = _captured(successor, interpretation, captures)
    intent = _intent(successor, interpretation, manifest)
    work = _work(images, intent); policy = Policy.from_json(finite.packet['resource']['policy'])
    receipts = {'before': PackageReceipt(packages / 'first/after', before[MANIFEST]),
                'after': PackageReceipt(destination, after[MANIFEST])}
    rows, _ = _execute_work(packages / 'reference-work.jsonl', work, policy, intent, receipts)
    bundle = root / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
    pairs = protected_tasks(bundle)
    protected = {side: observe(receipt, pairs) for side, receipt in receipts.items()}
    proofs = {side: _fresh_proofs(receipt, bundle, protected[side]) for side, receipt in receipts.items()}
    # Independently measure all typed file groups and registry order from both
    # complete physical packages before retaining the smaller serialized images.
    old_names = finite.joint().packet['typed_binding']['candidate']['capabilityFrontier']
    physical_projections = {side: state_projection(snapshot(receipt.root), receipt.package_hash,
        old_names + ([] if side == 'before' else [SELECTED_NAME])) for side, receipt in receipts.items()}
    journal_hex = _journal_bytes(rows).hex()
    derived = _derived(successor, interpretation, captures, protected, proofs, journal_hex)
    for side in ('before', 'after'):
        typed = physical_projections[side]; projected = derived['finite_projection'][side]
        _same([typed[group] for group in GROUPS], projected['frozen'], 'fresh typed component images differ')
        _same(typed['base'], projected['keys'], 'fresh physical registry order differs')
        _same(typed['capabilityFrontier'], projected['named_frontier'], 'fresh physical frontier differs')
    result = PreparedSecondStep(canonical({'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
        'successor_packet': successor.packet, 'interpretation_packet': interpretation.packet,
        'retained_execution_hex': {name: raw.hex() for name, raw in retained.items() if name.endswith('/execution.json')},
        'retained_sha256': dict(RETAINED_PINS), 'captured_inputs': captures,
        'protected_observations': protected, 'proof_observations': proofs,
        'reference_journal_hex': journal_hex, **derived, 'scope': dict(SCOPE),
        'claims': {k: False for k in FALSE_CLAIMS}}))
    require(snapshot(packages / 'first/before') == first_images['before'] and
            snapshot(packages / 'first/after') == before and snapshot(destination) == after and
            (packages / 'reference-work.jsonl').read_bytes() == _journal_bytes(rows) and retained == _retained(root),
            'second-step source, package or work bytes changed during preparation')
    return result


def verify_packet_bytes(raw: bytes, recomputed: PreparedSecondStep, *, expected_sha256: str) -> None:
    _hash(expected_sha256, 'external second-step packet anchor')
    require(type(raw) is bytes and sha(raw) == expected_sha256 and type(recomputed) is PreparedSecondStep and
            raw == recomputed.packet_bytes, 'second-step packet differs from anchored fresh reconstruction')
    PreparedSecondStep(raw)


def summary(prepared: PreparedSecondStep) -> dict:
    require(type(prepared) is PreparedSecondStep, 'validated second-step input required')
    return prepared.packet['summary']
