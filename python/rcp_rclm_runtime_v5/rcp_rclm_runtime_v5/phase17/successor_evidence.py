"""Recompute a prospective extension and compile explicit root-premise evidence.

The exported packet is NOT an acceptance/promotion certificate. In particular,
retaining 19 recursive task labels does not reexecute their operational meanings.
Only the unchanged bounded registry profile and exact historical bootstrap are
supported. No active state or successor identity is installed by this module.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime_v5.phase17.bootstrap import HistoricalPredecessor, WEIGHTS_SHA256, _validate_program
from rcp_rclm_runtime_v5.phase17.controller import ControlError, FAMILIES
from rcp_rclm_runtime_v5.phase17.challenge_protocol import verify_transcript, reference_grammar, execute_reference
from rcp_rclm_runtime_v5.phase17.materialized import (
    PackageReceipt, MANIFEST, require, sha, snapshot, verify_package, execute_installed,
)
from rcp_rclm_runtime_v5.phase17.frontier_recertification import prepare_frontier, evaluate_candidate_package
from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective

SCHEMA = 'runtime.v5.phase17.successor-premise-packet.v1'
BASE_FIELDS = ('typedSuccessor', 'residualsNonpositive', 'protectedNonLoss',
               'constructiveRecovery', 'invariantPreserved', 'progressNondecreasing',
               'strictProgressWhenWitness', 'trustValid', 'resourceValid',
               'realityContained', 'successorAdmissible')
LEARNED_FIELDS = ('protectedFrontierCertified', 'protectedFrontierRetained',
                  'strictFrontierExpansion', 'generatorIsActive', 'generatorBound',
                  'proposalProduced', 'proposalBindsCandidate', 'packageHashIsActive',
                  'packageHashBound', 'goalDriftWithinBudget', 'resourceWithinBudget',
                  'informationNonRegression')
AUTONOMOUS_FIELDS = ('objectiveSelectedEndogenously', 'programProducedEndogenously',
                     'hiddenChallengeFresh', 'historyIsBound', 'routeHintsAbsent',
                     'programCandidateBinding', 'programCertificateBinding',
                     'protectedRecursiveFrontierCertified', 'protectedRecursiveFrontierRetained',
                     'recursiveFrontierRetained', 'recursiveWitnessValid', 'searchWithinBudget')
FALSE_CLAIMS = ('root_transition_verified', 'recursive_productivity_recertified',
                'full_frontier_recertified', 'promotion_authorized', 'promotion_performed',
                'phase17_exit_closed', 'gate_e_closed', 'egc0_started',
                'live_capability_gain_demonstrated', 'complete_resource_accounting')


@dataclass(frozen=True)
class PreparedSuccessor:
    packet_bytes: bytes

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    @property
    def packet_hash(self) -> str:
        return digest(self.packet)


def _rows(files: dict[str, bytes]) -> list[dict]:
    return [{'path': n, 'sha256': sha(b), 'size': len(b)} for n, b in sorted(files.items())]


def projection_delta(before: dict[str, bytes], after: dict[str, bytes], candidate_hash: str) -> dict:
    """Exact byte comparison, not merely equality of candidate-authored manifests."""
    candidate_path = 'registry/programs/' + candidate_hash + '.json'
    require(set(after) - set(before) == {candidate_path}, 'not one exact program-file addition')
    protected = set(before) - {MANIFEST, 'registry/manifest.json'}
    require(set(before) - set(after) == set(), 'predecessor file removed')
    require(all(before[n] == after[n] for n in protected), 'protected bytes changed')
    old_registry = load_json_strict(before['registry/manifest.json'])
    new_registry = load_json_strict(after['registry/manifest.json'])
    expected_registry = {**old_registry, 'candidate_program_hash': candidate_hash}
    require(canonical(new_registry) == canonical(expected_registry), 'unauthorized registry change')
    require(old_registry['candidate_program_hash'] is None and new_registry['candidate_active'] is False,
            'active candidate or chained bootstrap unsupported')
    # Removing the additional program and restoring the two metadata files must
    # reconstruct the predecessor exactly. This is a projection, not active rollback.
    recovered = {k: v for k, v in after.items() if k != candidate_path}
    for n in (MANIFEST, 'registry/manifest.json'):
        recovered[n] = before[n]
    require(recovered == before, 'exact package projection recovery failed')
    return {'protected_before': _rows({n: before[n] for n in protected}),
            'protected_after': _rows({n: after[n] for n in protected}),
            'added_path': candidate_path, 'exact_projection_recovery': True,
            'active_store_rollback_performed': False}


def _recursive_matrix(parent: HistoricalPredecessor, candidate: PackageReceipt,
                      frontier: dict, objective: dict, grammar: tuple[dict, ...]) -> list[dict]:
    """Account for EVERY inherited label; do not infer ability from mere membership."""
    # The actual planner bytes used by the authenticated objective must also be
    # physically present in the candidate. Only the fixed nonzero projection is used.
    matches = [r for r in load_json_strict(candidate.manifest_bytes)['files']
               if r['sha256'] == WEIGHTS_SHA256]
    require(len(matches) == 1 and sha((candidate.root / matches[0]['path']).read_bytes()) == WEIGHTS_SHA256,
            'physical objective-planner bytes missing')
    plans = [r for r in frontier['task_reports'] if r['method'] == 'inherited_plan_decoder_then_lean']
    require(len(plans) == 2 and all(len(r['decoded_tokens']) > 1 for r in plans), 'multi-token plans absent')
    for program in grammar:
        _validate_program(program)
    require(len(grammar) == len({digest(p) for p in grammar}) == 32, 'recursive grammar incomplete')
    require({p['family'] for p in grammar} == set(FAMILIES), 'grammar family omitted')
    probes = {
        'recursive.generate_valid_program': {
            'method': 'fixed_current_view_32_program_enumeration',
            'grammar_hash': digest(list(grammar)), 'program_count': 32},
        'recursive.choose_update_family': {
            'method': 'authenticated_inherited_planner_projection',
            'objective_hash': digest(objective), 'planner_sha256': WEIGHTS_SHA256},
        'recursive.generate_multi_token_plan': {
            'method': 'two_actual_inherited_planner_decodes',
            'decode_hashes': [r['decode_hash'] for r in plans]},
    }
    ids = parent.state['recursive_productivity_frontier']
    require(len(ids) == len(set(ids)) == 19 and set(probes) <= set(ids), 'unexpected historical recursive frontier')
    return [{'task_id': task,
             'status': 'selected_profile_probe_passed' if task in probes else 'operational_recertification_pending',
             'probe': probes.get(task),
             'inherited_label_retained': True,
             'full_task_semantics_recertified': False}
            for task in ids]


def obligation_ledger() -> list[dict]:
    """The complete root field inventory. Support is never proof of all premises."""
    support = {
        ('base', 'typedSuccessor'): 'exact_prospective_package_delta_only; no active typed successor',
        ('base', 'protectedNonLoss'): 'exact retained file bytes; no complete information-semantics refinement',
        ('base', 'constructiveRecovery'): 'exact physical predecessor projection; no active-store rollback',
        ('learned', 'protectedFrontierRetained'): 'fresh 21-task Python candidate checks; Lean gate separate',
        ('learned', 'strictFrontierExpansion'): 'one new finite-probe capability in a PROSPECTIVE frontier',
        ('learned', 'proposalBindsCandidate'): 'anchored transcript and independently reconstructed physical program',
        ('autonomous', 'objectiveSelectedEndogenously'): 'current package-conditioned objective recomputed',
        ('autonomous', 'programCandidateBinding'): 'frozen descriptor matched to physical installed bytes',
        ('autonomous', 'protectedRecursiveFrontierCertified'): 'historical labels bound; operational semantics pending',
        ('autonomous', 'protectedRecursiveFrontierRetained'): 'finite label inclusion; operational semantics pending',
        ('autonomous', 'recursiveFrontierRetained'): 'finite label inclusion plus three scoped probes; not all 19 abilities',
        ('autonomous', 'searchWithinBudget'): 'candidate credits only; not complete runtime resource accounting',
    }
    return [{'layer': layer, 'field': field, 'complete_root_premise_discharged': False,
             'support': support.get((layer, field), 'no complete concrete witness in this increment')}
            for layer, fields in (('base', BASE_FIELDS), ('learned', LEARNED_FIELDS),
                                   ('autonomous', AUTONOMOUS_FIELDS)) for field in fields]


def prepare_successor(predecessor: PackageReceipt, candidate: PackageReceipt,
                      parent: HistoricalPredecessor, *, bundle: Path, capture: Path,
                      transcript: bytes, expected_transcript_hash: str) -> PreparedSuccessor:
    """Production entry: recompute facts. No external pass-report or proof is trusted."""
    parent.validate()
    replay = verify_transcript(parent, transcript, expected_transcript_hash=expected_transcript_hash)
    require(replay.terminal_action == 'await_root_verification' and replay.selected_candidate_hash is not None,
            'no passing candidate; exhaustion/partial stops cannot form successor evidence')
    checked_parent = verify_package(predecessor.root, parent, bundle, expected_package_hash=predecessor.package_hash)
    checked_candidate = verify_package(candidate.root, parent, bundle, expected_package_hash=candidate.package_hash,
                                      transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    require(checked_parent.manifest_bytes == predecessor.manifest_bytes and
            checked_candidate.manifest_bytes == candidate.manifest_bytes, 'package receipt substitution')
    require(predecessor.package_hash != candidate.package_hash, 'no package change')
    original, proposed = snapshot(predecessor.root), snapshot(candidate.root)
    delta = projection_delta(original, proposed, replay.selected_candidate_hash)
    frontier = prepare_frontier(candidate, parent, bundle=bundle, capture=capture,
                                transcript=transcript, expected_transcript_hash=expected_transcript_hash).report
    evaluation = evaluate_candidate_package(candidate, parent, bundle=bundle, transcript=transcript,
                                            expected_transcript_hash=expected_transcript_hash)
    events = load_json_strict(transcript)['events']
    opening = events[0]['request']
    old_objective = opening['objective']
    objective = select_bootstrap_objective(parent, turn_index=old_objective['turn_index'],
                                           public_nonce_hash=old_objective['public_nonce_hash']).to_json()
    require(canonical(objective) == canonical(old_objective), 'objective changed')
    grammar = reference_grammar(parent.state, objective['turn_index'], objective['public_nonce_hash'])
    candidate_program = load_json_strict(proposed[delta['added_path']])
    require(candidate_program in grammar, 'candidate outside unchanged grammar')
    rows = evaluation['probe_checks']
    require(len(rows) == 8, 'eight sealed probes required')
    inherited = [load_json_strict(p) for p in parent.accepted_programs]
    family_programs = [p for p in inherited if p['family'] == candidate_program['family']]
    require(family_programs, 'inherited family support missing')
    for p in family_programs:
        actual = [execute_installed(predecessor, digest(p), r['input']) for r in rows]
        require(actual == [execute_reference(p, r['input']) for r in rows], 'predecessor interpreter mismatch')
        require(actual != [r['expected'] for r in rows], 'predecessor already solves finite target')
    support = _recursive_matrix(parent, candidate, frontier, objective, grammar)
    public = events[0]['response']['payload']['public_challenge']
    challenge_hash = public['challenge_commitment_hash']
    old_ids = parent.state['capability_frontier']
    new_id = 'phase17.dynamic.' + challenge_hash
    require(new_id not in old_ids, 'not a new capability identifier')
    program_ids = parent.state['installed_program_hashes']
    packet = {
        'schema_id': SCHEMA,
        'scope': 'prospective_single_historical_registry_extension; not root acceptance',
        'bindings': {'historical_state_hash': parent.receipt['selected_state_hash'] if 'selected_state_hash' in parent.receipt else
                     load_json_strict(predecessor.manifest_bytes)['historical_state_hash'],
                     'predecessor_physical_hash': predecessor.package_hash, 'candidate_physical_hash': candidate.package_hash,
                     'transcript_sha256': expected_transcript_hash, 'program_hash': replay.selected_candidate_hash,
                     'objective_hash': digest(objective), 'challenge_commitment_hash': challenge_hash},
        'projection': delta,
        'candidate_program': candidate_program, 'inherited_family_programs': family_programs,
        'current_grammar': list(grammar),
        'capabilities_before': old_ids, 'capabilities_after': sorted([*old_ids, new_id]), 'new_capability': new_id,
        'programs_before': program_ids, 'programs_after': sorted([*program_ids, replay.selected_candidate_hash]),
        'recursive_before': parent.state['recursive_productivity_frontier'],
        'recursive_after': parent.state['recursive_productivity_frontier'],
        'recursive_support': support, 'strict_recursive_expansion_claimed': False,
        'search_used': replay.candidate_evaluations, 'search_budget': opening['candidate_credits'],
        'frontier': frontier, 'candidate_evaluation': evaluation,
        'root_obligation_ledger': obligation_ledger(),
        'trusted_refinement_assumptions': ['Python parsers, hashing, measurement and DSL execution',
            'external transcript anchor integrity, not authentication or evidence of entropy quality',
            'proof literal extraction correctly describes the measured artifacts'],
        'claims': {k: False for k in FALSE_CLAIMS},
    }
    require(snapshot(predecessor.root) == original and snapshot(candidate.root) == proposed, 'package changed during verification')
    return PreparedSuccessor(canonical(packet))


def verify_packet_bytes(data: bytes, expected: PreparedSuccessor, *, expected_sha256: str) -> None:
    require(type(data) is bytes and len(data) <= 2 * 1024 * 1024, 'packet byte bound')
    require(re.fullmatch('[0-9a-f]{64}', expected_sha256) is not None and sha(data) == expected_sha256,
            'packet external hash mismatch')
    require(data == expected.packet_bytes, 'packet differs from independently recomputed evidence')
