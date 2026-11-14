"""Phase17AC controlled comparisons of the unchanged present-only controller.

The generic Lean theorems quantify over structural ranking contexts. This
collector independently interprets that projection and compares selected,
explicitly synthetic executions with the production Python controller. It does
not authenticate evaluator receipts, derive physical ranks, or run a campaign.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from .controller import (Action, CurrentView, FAMILIES, FrozenSearch, RankedCandidate,
                         RANKING_POLICY, SearchPrefix, checkpoint, decide,
                         exhaustion_record, halt, record_evaluation, restore)

BASE = '3d1f1a663f2087c4e80dc18c0b208818ce2d2d3f'
SCHEMA = 'rcp-rclm.phase17ac.controller-continuation-packet.v1'
POLICY = 'phase17ac.generic-present-prefix-and-finite-exhaustion.v1'
CONTROLLER = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller.py'
CONTROLLER_SHA = 'a6d6dadf7fbe33a28017d4b6b2d690ea0ff8fd68133aa2423c5a8b7bf4b1ed0a'
PROVENANCE = 'lean/phase17_bridge/ProposalProvenance.lean'
PROVENANCE_SHA = '3cae873ff4dba673c926ac4ecf214d349c2ec6a635bf0ead44547bebc76056a4'
FALSE_CLAIMS = (
    'root_transition_verified', 'full_learned_step_instantiated',
    'full_autonomous_step_instantiated', 'complete_learned_kernel_constructed',
    'physical_projection_formally_verified', 'physical_execution_attested',
    'full_goal_interpretation_supplied', 'full_information_interpretation_supplied',
    'full_frontier_recertified', 'recursive_productivity_recertified',
    'complete_resource_accounting', 'campaign_budget_authority_integrated',
    'os_resource_containment', 'historical_cost_recovered',
    'promotion_authorized', 'promotion_performed', 'active_store_written',
    'live_capability_gain_demonstrated', 'phase17_exit_closed', 'gate_e_closed',
    'egc0_started', 'github_hosted_ci_passed', 'cross_platform_validation',
    'phase18_independent_replay',
)
SCOPE = {
    'domain': '32-candidate present-only controller with arbitrary natural initial credits',
    'generic_theorems': 'structural Lean model using the unchanged Phase17Provenance.choose',
    'python_correspondence': 'controlled finite comparisons, not a universal Python refinement theorem',
    'ranking_inputs': 'synthetic tables; no claim of learned planner or physical tensor execution',
    'receipt_authentication': 'external to Lean protocol projection',
    'evaluator_truth': 'external; fixture verdicts are not measured capability',
    'noninterference': 'same present projection gives same decision; host input provenance remains external',
    'search_resume': 'validated logical prefix; not a compiler process memory snapshot',
    'compilation_resume': 'separately attributed completed-stage lineage under the AC runner contract',
    'trusted_import_cache_assumption': True,
    'old_proof_campaigns_rerun': False,
    'fresh_workers': 0,
    'fresh_challenges': 0,
    'promotion_api': False,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_preexisting_sources(root: Path) -> dict:
    result = {}
    for name, expected in ((CONTROLLER, CONTROLLER_SHA), (PROVENANCE, PROVENANCE_SHA)):
        path = root / name
        require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
                'missing or linked controller input: ' + name)
        raw = path.read_bytes().replace(b'\r\n', b'\n')
        require(sha(raw) == expected, 'preexisting controller input changed: ' + name)
        result[name] = expected
    return result


def table_of(frozen: FrozenSearch) -> list[dict]:
    rows = []
    for candidate in frozen.candidates:
        family = FAMILIES.index(candidate.family)
        ties = [int(digest({'policy_id': RANKING_POLICY,
                           'program_hash': candidate.program_hash,
                           'active_package_hash': frozen.view.active_package_hash,
                           'family_count': frozen.view.family_counts[family],
                           'rejection_count': count})[:16], 16) for count in range(5)]
        rows.append({'key': candidate.program_hash, 'family': family,
                     'base_score': candidate.base_score, 'ties': ties})
    return rows


def reference_choice(rows: list[dict], seen: list[int], offset: int) -> int | None:
    """Ordered-table interpreter, independent of production _candidate.

    This has the same Nat-index tie order as Lean: FrozenSearch sorts unique
    hexadecimal program keys, so index order agrees with Python's string tie.
    """
    require(len(rows) == 32 and type(offset) is int and 0 <= offset < 32, 'context shape')
    available = set(range(32)).difference(seen)
    if len(seen) < 4:
        if not available:
            return None
        counts = [sum(rows[index]['family'] == family for index in seen) for family in range(8)]
        ranked = sorted(available, key=lambda index: (
            rows[index]['base_score'] + 797 * counts[rows[index]['family']],
            rows[index]['ties'][counts[rows[index]['family']]], index))
        return ranked[-1]
    # Sorted positions implement the complete permutation, not a next-index shortcut.
    positions = {(offset + 17 * step) % 32: step for step in range(32)}
    return min(available, key=positions.__getitem__) if available else None


def reference_decision(context: dict, prefix: dict) -> tuple[str, int | None]:
    observations = prefix['observations']
    if prefix['stop'] is not None:
        return {'external': Action.EXTERNAL_STOP.value, 'safety': Action.SAFETY_HALT.value}[prefix['stop']], None
    if observations and observations[-1]['passed']:
        return Action.AWAIT_ROOT_VERIFICATION.value, None
    if len(observations) == 32:
        return Action.SEARCH_EXHAUSTED.value, None
    if len(observations) >= prefix['initial_credits']:
        return Action.RESOURCE_EXHAUSTED.value, None
    index = reference_choice(context['rows'], [o['index'] for o in observations], context['offset'])
    require(index is not None, 'ongoing projection has no candidate')
    return Action.EVALUATE.value, index


def reference_replay(context: dict, credits: int, observations: list[dict], stop: str | None = None) -> dict:
    require(type(credits) is int and credits >= 0, 'natural credits required')
    require(type(observations) is list and len(observations) <= 32, 'bounded observations required')
    require(stop in (None, 'external', 'safety'), 'stop reason')
    prefix = {'initial_credits': credits, 'observations': [], 'stop': None}
    for observation in observations:
        require(type(observation) is dict and set(observation) == {'index', 'passed'} and
                type(observation['index']) is int and type(observation['passed']) is bool,
                'observation shape')
        action, index = reference_decision(context, prefix)
        require(action == Action.EVALUATE.value and index == observation['index'],
                'observation differs from the next present-only choice')
        prefix['observations'].append(dict(observation))
    if stop is not None:
        require(reference_decision(context, prefix)[0] == Action.EVALUATE.value,
                'cannot overwrite a terminal cause')
        prefix['stop'] = stop
    return prefix


def project(prefix: SearchPrefix) -> dict:
    indices = {candidate.program_hash: i for i, candidate in enumerate(prefix.frozen.candidates)}
    return {'initial_credits': prefix.initial_credits,
            'observations': [{'index': indices[o.program_hash], 'passed': o.verdict == 'candidate_passed'}
                             for o in prefix.observations],
            'stop': {None: None, Action.EXTERNAL_STOP.value: 'external', Action.SAFETY_HALT.value: 'safety'}[prefix.stop]}


def fixture(seed: int) -> FrozenSearch:
    """Public deterministic test data; no entropy, real model, or hidden challenge."""
    require(type(seed) is int and 0 <= seed < 4096, 'fixture seed bound')
    view = CurrentView(digest(['AC-state', seed % 4]), digest(['AC-package', seed % 4]),
                       digest(['AC-synthetic-commitment', seed]), digest(['AC-public-nonce', seed]),
                       seed % 7, tuple((seed + i * 3) % 11 for i in range(8)))
    patterns = (lambda i, v: 0,
                lambda i, v: (i * 521 - v * 797),
                lambda i, v: -(i * 2001 + v * 701),
                lambda i, v: ((i + v) % 3) * 100000 - i * 200)
    candidates = tuple(RankedCandidate(digest(['AC-program', family, variant]), family, variant,
                                       patterns[seed % 4](i, variant))
                       for i, family in enumerate(FAMILIES) for variant in range(4))
    return FrozenSearch(view, candidates)


@lru_cache(maxsize=1)
def offset_fixtures() -> tuple[FrozenSearch, ...]:
    found = {}
    for seed in range(4096):
        frozen = fixture(seed)
        found.setdefault(int(frozen.freeze_hash[:16], 16) % 32, frozen)
        if len(found) == 32:
            return tuple(found[i] for i in range(32))
    raise ValueError('controlled offset-coverage fixture bound exhausted')


def case_specs() -> tuple[dict, ...]:
    result = [{'name': f'exhaust_offset_{i:02d}', 'context': i, 'credits': 40,
               'verdicts': [False] * 32, 'stop': None} for i in range(32)]
    result += [{'name': f'pass_last_credit_{i:02d}', 'context': 0, 'credits': i,
                'verdicts': [False] * (i - 1) + [True], 'stop': None} for i in range(1, 33)]
    result += [{'name': f'credit_boundary_{n}', 'context': 1, 'credits': n,
                'verdicts': [False] * min(n, 32), 'stop': None} for n in (0, 1, 3, 4, 5, 31, 32, 40, 100)]
    result += [{'name': f'{stop}_at_{n}', 'context': 2, 'credits': 40,
                'verdicts': [False] * n, 'stop': stop}
               for stop in ('external', 'safety') for n in (0, 1, 3, 4, 5, 31)]
    result += [{'name': 'ongoing_fallback', 'context': 3, 'credits': 40,
                'verdicts': [False] * 4, 'stop': None}]
    return tuple(result)


def _observe(prefix: SearchPrefix, passed: bool) -> SearchPrefix:
    decision = decide(prefix)
    return record_evaluation(prefix, decision,
        verdict='candidate_passed' if passed else 'reject',
        evaluation_hash=digest(['AC-controlled-receipt', prefix.prefix_hash, passed]),
        reason_codes=() if passed else ('controlled_fixture_rejection',),
        predecessor_state_hash=prefix.frozen.view.predecessor_state_hash,
        challenge_commitment_hash=prefix.frozen.view.challenge_commitment_hash)


def run_case(spec: dict, frozen: FrozenSearch, context: dict) -> dict:
    prefix = SearchPrefix(frozen, spec['credits'])
    checkpoints = []
    for position in range(len(spec['verdicts']) + 1):
        projection = project(prefix)
        expected = reference_replay(context, spec['credits'], projection['observations'])
        require(expected == projection, 'production/reference prefix differs')
        observed = decide(prefix)
        indices = {candidate.program_hash: i for i, candidate in enumerate(frozen.candidates)}
        projected_action = (observed.action.value, indices.get(observed.candidate_hash))
        require(projected_action == reference_decision(context, projection), 'production/reference decision differs')
        restored = restore(checkpoint(prefix), expected_prefix_hash=prefix.prefix_hash)
        require(restored == prefix and decide(restored) == observed, 'checkpoint roundtrip differs')
        checkpoints.append({'length': position, 'prefix_hash': prefix.prefix_hash,
                            'checkpoint_sha256': sha(checkpoint(prefix)),
                            'action': projected_action[0], 'candidate_index': projected_action[1]})
        if position < len(spec['verdicts']):
            prefix = _observe(restored, spec['verdicts'][position])
    if spec['stop'] is not None:
        prefix = halt(prefix, safety=spec['stop'] == 'safety')
    projected = project(prefix)
    require(projected == reference_replay(context, spec['credits'], projected['observations'], spec['stop']),
            'terminal stop projection differs')
    action, candidate_index = reference_decision(context, projected)
    require(decide(prefix).action.value == action, 'terminal action differs')
    if action == Action.SEARCH_EXHAUSTED.value:
        exhausted = exhaustion_record(prefix)
        require(set(exhausted['rejected_program_hashes']) == set(exhausted['legal_program_hashes']) and
                len(exhausted['rejected_program_hashes']) == 32, 'incomplete exhaustion')
    require(restore(checkpoint(prefix), expected_prefix_hash=prefix.prefix_hash) == prefix,
            'final stopped checkpoint differs')
    return {'name': spec['name'], 'context': spec['context'], 'prefix': projected,
            'action': action, 'candidate_index': candidate_index, 'checkpoint_trace': checkpoints,
            'final_checkpoint_sha256': sha(checkpoint(prefix)), 'final_prefix_hash': prefix.prefix_hash}


@dataclass(frozen=True)
class PreparedContinuation:
    packet_bytes: bytes

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)


def prepare(root: Path) -> PreparedContinuation:
    pins = verify_preexisting_sources(root)
    freezes = offset_fixtures()
    contexts = [{'offset': i, 'rows': table_of(frozen), 'frozen_search': frozen.to_json(),
                 'freeze_hash': frozen.freeze_hash, 'context_credits_metadata': 0}
                for i, frozen in enumerate(freezes)]
    cases = [run_case(spec, freezes[spec['context']], contexts[spec['context']]) for spec in case_specs()]
    packet = {'schema': SCHEMA, 'policy': POLICY, 'baseline': BASE, 'scope': SCOPE,
              'claims': {name: False for name in FALSE_CLAIMS}, 'preexisting_sources': pins,
              'contexts': contexts, 'cases': cases,
              'summary': {'context_count': len(contexts), 'case_count': len(cases),
                          'covered_offsets': list(range(32)),
                          'candidate_pass_positions': list(range(1, 33)),
                          'checkpoint_roundtrips': sum(len(c['checkpoint_trace']) + 1 for c in cases),
                          'controlled_evaluations': sum(len(c['prefix']['observations']) for c in cases),
                          'actions_observed': sorted({c['action'] for c in cases}),
                          'initial_credit_values': sorted({c['prefix']['initial_credits'] for c in cases}),
                          'fresh_workers': 0, 'fresh_live_challenges': 0}}
    return PreparedContinuation(canonical(packet))


def verify_packet(raw: bytes, prepared: PreparedContinuation, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and len(raw) <= 4 * 1024 * 1024 and sha(raw) == expected_sha256,
            'continuation packet checksum or bound differs')
    load_json_strict(raw)
    require(raw == prepared.packet_bytes, 'continuation packet differs from actual-controller reconstruction')
