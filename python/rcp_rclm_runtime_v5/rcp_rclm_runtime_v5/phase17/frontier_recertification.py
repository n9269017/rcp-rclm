"""Re-execute the selected package's complete 21-task capability frontier.

Uses actual inherited quantized decoder/package files, not stored success flags.
The 13 Lean-backed obligations are PREPARED here, never accepted without the
separate pinned Lean execution gate. Eight Phase16 tasks keep their original
bounded integer semantics. Recursive-productivity recertification is separate.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest, load_package_components
from rcp_rclm_runtime_v4.phase14.tasks import base_task_suite, decode_task
from rcp_rclm_runtime_v4.phase14.challenges import challenges_from_answer_store as challenges14
from rcp_rclm_runtime_v4.phase15.challenges import challenges_from_answer_store as challenges15
from rcp_rclm_runtime_v4.phase15.decoder import decode_plan, NAME_BY_TOKEN
from rcp_rclm_runtime_v5.phase17.bootstrap import (
    HistoricalPredecessor, _read_pinned_archive, _member, validate_selected_lineage,
    CAPTURE_SHA256, CAPTURE_HASH, M9_BUNDLE_SHA256, SELECTED_CAMPAIGN_HASH,
)
from rcp_rclm_runtime_v5.phase17.challenge_protocol import execute_reference
from rcp_rclm_runtime_v5.phase17.materialized import (
    PackageReceipt, require, verify_package, sha, execute_installed,
)


@dataclass(frozen=True)
class PreparedFrontier:
    report_bytes: bytes
    sources: tuple[tuple[str, bytes], ...]

    @property
    def report(self) -> dict:
        return load_json_strict(self.report_bytes)


def _named_source(source: str, task_id: str) -> tuple[str, bytes]:
    name = 'phase17_' + sha(task_id.encode())[:24]
    require(source.count('example ') == 1, 'expected one selected theorem')
    source = source.replace('example ', 'theorem '+name+' ', 1)
    # Only known templates plus grammar-checked completions enter this path.
    require(not re.search(r'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', source),
            'forbidden generated proof token')
    source += '\n#print axioms '+name+'\n'
    return name, source.encode('utf-8')


def _integer_token(name: str) -> int:
    require(name.startswith('INT_'), 'integer token required')
    token = name[4:]
    require(re.fullmatch(r'(?:NEG)?\d+', token) is not None, 'invalid integer token')
    return -int(token[3:]) if token.startswith('NEG') else int(token)


def _dynamic_source(challenge, decode) -> tuple[str, int]:
    names = [NAME_BY_TOKEN[t] for t in decode.tokens]
    require(decode.stopped_on_eos and tuple(decode.tokens) == challenge.expected_plan_tokens,
            'actual planner failed retained dynamic obligation')
    if challenge.domain == 'lean_multistep':
        a, b = _integer_token(names[1]), _integer_token(names[2])
        require(0 <= a < b <= 8, 'bad decoded Lean parameters')
        return ('import Mathlib\n\n'
                f'example (x : Nat) : x + {challenge.parameter_a} < x + {challenge.parameter_b} := by\n'
                f'  have h : {a} < {b} := by omega\n'
                '  exact Nat.add_lt_add_left h x\n'), 0
    a, b = _integer_token(names[1]), _integer_token(names[3])
    # Execute the decoded candidate plan; compare against independent task parameters.
    cases = 0
    for x in range(-32, 33):
        actual = a*x+b
        require(actual == challenge.parameter_a*x+challenge.parameter_b, 'decoded affine program failed')
        cases += 1
    return ('import Mathlib\n\n'
            f'def phase17Affine (x : Int) : Int := ({a}) * x + ({b})\n'
            f'example (x : Int) : phase17Affine x = ({challenge.parameter_a}) * x + ({challenge.parameter_b}) := by\n'
            '  rfl\n'), cases


def prepare_frontier(package: PackageReceipt, parent: HistoricalPredecessor, *,
                     bundle: Path, capture: Path, transcript: bytes | None = None,
                     expected_transcript_hash: str | None = None) -> PreparedFrontier:
    """Measure before AND after executing all old tasks; no historical pass reuse."""
    verified = verify_package(package.root, parent, bundle, expected_package_hash=package.package_hash,
                              transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    require(verified.manifest_bytes == package.manifest_bytes, 'package receipt substitution')
    base = package.root/'base'
    model = load_package_manifest(base)
    # load_package_components actually checks all tensor/tokenizer/adapter manifests
    # and bytes. The inference path remains the inherited selected sparse profile.
    load_package_components(base)
    with _read_pinned_archive(bundle, M9_BUNDLE_SHA256) as archive:
        a14 = load_json_strict(_member(archive, 'campaign/phase14_reference/campaign/answer_store_private.json', 65536),
                              require_canonical=False)
        a15 = load_json_strict(_member(archive, 'campaign/answer_store_private.json', 65536), require_canonical=False)
    pairs = [(task, None) for task in base_task_suite()]
    pairs.extend((challenge.task, challenge) for challenge in challenges14(a14))
    require(len(pairs) == 11, 'eleven inherited task obligations required')
    rows, sources = [], []
    for task, challenge in pairs:
        result = decode_task(base, task, challenge=challenge)
        require(result.route_hit and result.stopped_on_eos and
                result.completion_text == task.expected_completion, 'inherited model completion failed: '+task.task_id)
        name, source = _named_source(task.render_source(result.completion_text), task.task_id)
        sources.append((name, source))
        rows.append({'task_id': task.task_id, 'method': 'inherited_quantized_profile_then_lean',
                     'evaluation_passed': True, 'decode_hash': result.result_hash,
                     'completion_sha256': sha(result.completion_text.encode()),
                     'proof_name': name, 'source_sha256': sha(source), 'lean_required': True,
                     'fresh_lean_checked': False})
    for challenge in challenges15(a15):
        decoded = decode_plan(base, challenge.domain, challenge.parameter_a, challenge.parameter_b)
        source, cases = _dynamic_source(challenge, decoded)
        name, raw = _named_source(source, challenge.task_id)
        sources.append((name, raw))
        rows.append({'task_id': challenge.task_id, 'method': 'inherited_plan_decoder_then_lean',
                     'evaluation_passed': True, 'decode_hash': decoded.report_hash,
                     'decoded_tokens': list(decoded.tokens), 'exhaustive_integer_cases': cases,
                     'proof_name': name, 'source_sha256': sha(raw), 'lean_required': True,
                     'fresh_lean_checked': False})
    with _read_pinned_archive(capture, CAPTURE_SHA256) as archive:
        obj = load_json_strict(_member(archive, 'phase16_capture.json', 64*1024*1024), require_canonical=False)
    require(digest({k:v for k,v in obj.items() if k != 'report_hash'}) == CAPTURE_HASH == obj['report_hash'],
            'capture identity mismatch')
    matches = [c for c in obj['campaigns'] if c['report_hash'] == SELECTED_CAMPAIGN_HASH]
    require(len(matches) == 1, 'selected campaign missing')
    chosen = matches[0]
    require(validate_selected_lineage(chosen) == parent.accepted_programs, 'selected lineage changed')
    for transition in chosen['transitions']:
        program = transition['accepted_program']
        challenge = transition['retained_private_challenge']
        vector = challenge['public_input_vector']
        actual = execute_installed(package, digest(program), vector)
        expected = execute_reference(program, vector)
        require(actual == expected, 'installed executor/reference disagreement')
        execution = {'schema_id':'runtime.v4.phase16.program_execution.v1',
                     'family':program['family'], 'variant':program['variant'],
                     'generation':program['generation'], 'operation_id':program['operation_id'],
                     'output_vector':actual, 'program_hash':digest(program)}
        require(digest(execution) == challenge['target_output_hash'], 'retained capability output mismatch')
        rows.append({'task_id':challenge['capability_id'], 'method':'materialized_registry_integer_execution',
                     'evaluation_passed':True, 'program_hash':digest(program),
                     'execution_hash':digest(execution), 'input_vector':vector, 'output_vector':actual,
                     'lean_required':False, 'fresh_lean_checked':False,
                     'scope':'original finite Phase16 challenge, not all-input equivalence'})
    ids = [r['task_id'] for r in rows]
    require(len(ids) == len(set(ids)) == 21 and sorted(ids) == list(parent.state['capability_frontier']),
            'frontier omission, addition, or duplication')
    verify_package(package.root, parent, bundle, expected_package_hash=package.package_hash,
                   transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    report = {'schema_id':'runtime.v5.phase17.prepared-capability-frontier.v1',
              'materialized_package_hash':package.package_hash, 'model_identity_hash':model.model_identity_hash,
              'base_parameter_count':model.parameter_count, 'capability_count':len(rows),
              'task_reports':sorted(rows,key=lambda r:r['task_id']),
              'lean_obligation_count':len(sources), 'python_evaluation_passed':True,
              'complete_capability_coverage':True, 'package_unchanged':True,
              'fresh_lean_verified':False, 'full_frontier_recertified':False,
              'recursive_productivity_recertified':False, 'root_transition_verified':False,
              'full_transformer_inference':False, 'promotion_authorized':False,
              'phase17_exit_closed':False, 'gate_e_closed':False, 'egc0_started':False}
    report['report_hash'] = digest(report)
    return PreparedFrontier(canonical(report), tuple(sorted(sources)))


def evaluate_candidate_package(package: PackageReceipt, parent: HistoricalPredecessor, *,
                               bundle: Path, transcript: bytes, expected_transcript_hash: str) -> dict:
    """Evaluate the PHYSICAL prospective registry delta on all eight sealed probes.

    Exact deterministic realization of the already-frozen descriptor, not new
    generation after answer disclosure. No package selection from observed scores.
    """
    from rcp_rclm_runtime_v5.phase17.challenge_protocol import verify_transcript, _secret_from_entropy, vector_semantics
    receipt = verify_package(package.root,parent,bundle,expected_package_hash=package.package_hash,
                             transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    replay = verify_transcript(parent,transcript,expected_transcript_hash=expected_transcript_hash)
    require(replay.terminal_action == 'await_root_verification','no candidate to evaluate')
    sealed = load_json_strict(transcript)['events']
    opening = sealed[-1]['response']['payload']['opening']
    family = sealed[0]['request']['objective']['objective_family']
    hidden = _secret_from_entropy(bytes.fromhex(opening['entropy_hex']),family)
    candidate_hash = replay.selected_candidate_hash
    checks = []
    for vector in hidden['probes']:
        actual = execute_installed(receipt,candidate_hash,vector)
        expected = vector_semantics(family,hidden['target_variant'],hidden['target_a'],hidden['target_b'],vector)
        require(actual == expected,'materialized candidate differs from sealed evaluation')
        checks.append({'input':vector,'output':actual,'expected':expected})
    verify_package(package.root,parent,bundle,expected_package_hash=package.package_hash,
                   transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    return {'schema_id':'runtime.v5.phase17.materialized-candidate-evaluation.v1',
            'materialized_package_hash':package.package_hash,'transcript_sha256':expected_transcript_hash,
            'program_hash':candidate_hash,'probe_count':len(checks),'probe_checks':checks,
            'physical_candidate_matches_frozen_descriptor':True,'bounded_evaluation_passed':True,
            'full_model_intelligence_gain_claimed':False,'promotion_authorized':False}
