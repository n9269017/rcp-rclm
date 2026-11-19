"""Concrete protected sparse-output goals and diagonal information observations.

This is a deliberately bounded interpretation of the inherited byte-token
profile, NOT the full RCLM semantic kernel. All 260 conditional distributions
are measured twice and compared with the unchanged production implementation.
The eleven protected task definitions are reopened from their original pinned
sources/archive. No caller-selected target distribution or numeric pass report
is an input. The full model, Phase15 planner and vector-task probability meanings
are not inferred from this profile. Nothing in this module authorizes promotion.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import struct

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence, sum_intervals
from rcp_rclm_runtime_v3.phase10.sparse_profile import exact_dyadic_distribution, transition_tensor_path
from rcp_rclm_runtime_v3.phase10.information import _entropy, _kl, _target_distribution, PRECISION_BITS
from rcp_rclm_runtime_v3.phase10.package import load_package_components
from rcp_rclm_runtime_v4.phase14.tasks import base_task_suite, decode_task
from rcp_rclm_runtime_v4.phase14.challenges import challenges_from_answer_store
from .bootstrap import HistoricalPredecessor, M9_BUNDLE_SHA256, _read_pinned_archive, _member
from .materialized import PackageReceipt, require, sha, snapshot, verify_package
from .joint_evidence import PreparedJoint, prepare_joint, CLAIMS
from .learned_state_binding import hash_value
from .proposal_provenance import _blob

SCHEMA = 'runtime.v5.phase17.protected-sparse-semantics.v1'
POLICY = 'phase17.protected-byte-token-goal-and-diagonal-kl.v1'
VOCAB = 260
WIDTH = 320
DIVISOR = 2048
CLIP = 15
EOS = 258
MAX_BYTES = 8 * 1024 * 1024
TENSOR = 'base/model/tensors/model.layers.00.attn_output.weight.i16le.bin'
PROFILE = {
    'profile': 'sparse_last_token_transition_v1',
    'vocabulary': VOCAB, 'width': WIDTH, 'score_divisor': DIVISOR,
    'logit_clip': CLIP, 'target_correct_mass': 4096, 'target_other_mass': 1,
    'probability': '2^(clipped_score-minimum)/sum_masses',
    'information': 'sum of original teacher-forced KL(p||q), natural logarithms',
    'density': 'existing root diagonal density; von Neumann=Shannon; QRE=KL',
    'goal': 'count of changed protected (effective marker, completion, EOS) observations',
    'goal_budget': 0, 'information_budget': 0,
    'covered_probability_tasks': 'eleven inherited byte-token theorem-completion tasks',
    'not_covered': ['full transformer semantics', 'Phase15 planner probability interpretation',
                    'vector-task probability interpretation', 'general goal preservation',
                    'full autonomous acceptance', 'complete resource accounting'],
}
# Filled from reviewed existing source identities, not from caller-provided code.
SOURCE_PINS = {'python/rcp_rclm_runtime_v2/rcp_rclm_runtime/mathematics/intervals.py': '0f1d9e9e24f4186a20f6f0ae545d368c464a82fe', 'python/rcp_rclm_runtime_v2/rcp_rclm_runtime/mathematics/rational.py': '9f74af0f31189253da3b71b6eda6097ed9dd8558', 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/constants.py': '363cd0c808d959f1efc8f7bbf98e33e4b06b0257', 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/information.py': '146343ec8e0589fb5c9782880b8305c571af0fef', 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/learned_data.py': 'a525bbd8a4ed8b354eb10418aeacee19265cd01c', 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/package.py': '977b5bd604646330a139af44b608fd6bb2d5c692', 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/sparse_profile.py': 'cb78f7439634948d912c3ecef067c4af138a8abc', 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/tensors.py': '89762217478436013fb14fcf9c74909814599f42', 'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/challenges.py': 'e80a2c79f8343d94967ae5f2c9e071059f6a483f', 'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/tasks.py': '93c9cf0c9ab04c8f1128073f5cd1b09392fd9654'}


def semantic_sources(root: Path) -> list[dict]:
    rows = []
    require(bool(SOURCE_PINS), 'semantic source anchors missing')
    for name, wanted in sorted(SOURCE_PINS.items()):
        p = root / name
        require(p.is_file() and not any(x.is_symlink() for x in (p, *p.parents)), 'missing/linked semantic source')
        raw = p.read_bytes().replace(b'\r\n', b'\n')
        require(_blob(raw) == wanted, 'semantic source differs: ' + name)
        rows.append({'path': name, 'git_blob': wanted, 'sha256': sha(raw), 'size': len(raw)})
    return rows


def _keys(value, names, label):
    require(type(value) is dict and set(value) == set(names), label + ': exact fields required')


def _ints(value, count, lo, hi, label):
    require(type(value) is list and len(value) == count and
            all(type(x) is int and lo <= x <= hi for x in value), label + ': bounded integer vector required')


def masses_from_scores(scores: list[int]) -> list[int]:
    """Independent normalization; the existing implementation is checked separately."""
    _ints(scores, VOCAB, -16, 15, 'raw score row')
    clipped = []
    for value in scores:
        clipped.append(-CLIP if value < -CLIP else CLIP if value > CLIP else value)
    low = min(clipped)
    return [2 ** (value - low) for value in clipped]


def scores_from_tensor(raw: bytes) -> list[list[int]]:
    require(type(raw) is bytes and len(raw) == 2 * WIDTH * WIDTH, 'exact inherited tensor bytes required')
    tensor = tuple(v[0] for v in struct.iter_unpack('<h', raw))
    rows = []
    for current in range(VOCAB):
        row = []
        for target in range(VOCAB):
            value = tensor[target * WIDTH + current]
            require(value % DIVISOR == 0, 'nonintegral frozen score')
            row.append(value // DIVISOR)
        rows.append(row)
    return rows


def pack_rows(rows: list[list[int]]) -> tuple[list[list[int]], list[int]]:
    require(type(rows) is list and len(rows) == VOCAB, 'complete conditional domain required')
    dictionary, selectors, seen = [], [], {}
    for row in rows:
        _ints(row, VOCAB, -16, 15, 'conditional row')
        key = tuple(row)
        if key not in seen:
            seen[key] = len(dictionary); dictionary.append(list(row))
        selectors.append(seen[key])
    return dictionary, selectors


def protected_tasks(bundle: Path):
    with _read_pinned_archive(bundle, M9_BUNDLE_SHA256) as z:
        store = load_json_strict(_member(z, 'campaign/phase14_reference/campaign/answer_store_private.json', 65536),
                                 require_canonical=False)
    pairs = [(t, None) for t in base_task_suite()]
    pairs += [(c.task, c) for c in challenges_from_answer_store(store)]
    require(len(pairs) == len({t.task_id for t, _ in pairs}) == 11, 'eleven original tasks required')
    return tuple(sorted(pairs, key=lambda pair: pair[0].task_id.encode('utf-8')))


def task_contract(pairs) -> dict:
    rows = []
    for t, challenge in pairs:
        expected = [*t.expected_completion.encode('ascii'), EOS]
        rows.append({'task_id': t.task_id, 'prompt_sha256': sha(t.model_prompt),
                     'original_marker': t.marker, 'expected_tokens': expected,
                     'challenge_commitment': None if challenge is None else challenge.commitment_hash})
    return {'schema_id': 'runtime.v5.phase17.protected-sparse-task-contract.v1',
            'tasks': rows, 'source': 'original phase10-14 definitions and pinned Phase15 bundle',
            'target_correct_mass': 4096, 'target_other_mass': 1, 'horizon_input': False}


def observe(package: PackageReceipt, pairs) -> dict:
    """Fresh observation of ONE physical package; never copy the other package."""
    base = package.root / 'base'
    components = load_package_components(base)
    path = transition_tensor_path(base)
    require(path.resolve().relative_to(package.root.resolve()).as_posix() == TENSOR, 'unexpected transition tensor path')
    raw = path.read_bytes()
    source_rows = scores_from_tensor(raw)
    dictionary, selectors = pack_rows(source_rows)
    masses = [masses_from_scores(row) for row in dictionary]
    for current, row in enumerate(source_rows):
        actual_scores, distribution = exact_dyadic_distribution(base, current)
        expected = masses[selectors[current]]; total = sum(expected)
        require(list(actual_scores) == row and len(distribution) == VOCAB, 'production score disagreement')
        require(all(p.fraction == Fraction(w, total) for p, w in zip(distribution, expected, strict=True)),
                'production probability disagreement')
    goals = []
    for task, challenge in pairs:
        result = decode_task(base, task, challenge=challenge)
        require(result.route_hit and result.stopped_on_eos, 'protected route/termination failure')
        actual = [*result.decode.completion_token_ids, EOS]
        require(actual == [*task.expected_completion.encode('ascii'), EOS], 'protected output does not meet original target')
        goals.append({'task_id': task.task_id, 'effective_marker': result.effective_marker_token_id,
                      'tokens': actual, 'route_evidence_hash': result.route_evidence_hash,
                      'decode_hash': result.result_hash})
    require(path.read_bytes() == raw, 'tensor changed during observation')
    return {'package_hash': package.package_hash, 'model_identity_hash': components[0].model_identity_hash,
            'tensor_sha256': sha(raw), 'tensor_size': len(raw), 'tensor_path': TENSOR, 'tensor_hex': raw.hex(),
            'score_dictionary': dictionary, 'row_selectors': selectors,
            'mass_minus_one_dictionary': [[w - 1 for w in row] for row in masses],
            'row_totals': [sum(row) for row in masses], 'goals': goals,
            'production_rows_compared': VOCAB}


def observation_projection(o: dict) -> dict:
    return {'mass_minus_one_dictionary': o['mass_minus_one_dictionary'],
            'row_selectors': o['row_selectors'],
            'goals': [[r['effective_marker'], *r['tokens']] for r in o['goals']]}


def information_positions(o: dict, contract: dict) -> list[list[int]]:
    positions = []
    require(len(o['goals']) == len(contract['tasks']) == 11, 'missing protected goal')
    for measured, task in zip(o['goals'], contract['tasks'], strict=True):
        require(measured['task_id'] == task['task_id'], 'goal/task order differs')
        current = measured['effective_marker']
        for target in task['expected_tokens']:
            positions.append([current, target]); current = target
    return positions


def goal_drift(before: dict, after: dict) -> int:
    a, b = observation_projection(before)['goals'], observation_projection(after)['goals']
    require(len(a) == len(b) == 11, 'goal domain changed')
    return sum(left != right for left, right in zip(a, b, strict=True))


def information_summary(o: dict, positions: list[list[int]]) -> dict:
    """Certified interval diagnostics; formal equality uses full exact masses.

    Neither a rounded entropy estimate nor equal entropy alone authorizes the
    probability-retention claim. Fixed p and q give exact preservation without
    subtracting overlapping interval approximations and calling the result zero.
    """
    cache, entropy, divergence = {}, [], []
    for current, target in positions:
        index = o['row_selectors'][current]
        key = (index, target)
        if key not in cache:
            weights = [w + 1 for w in o['mass_minus_one_dictionary'][index]]
            total = sum(weights); p = tuple(Rational(w, total) for w in weights)
            cache[key] = (_entropy(p), _kl(p, _target_distribution(target)))
        h, d = cache[key]; entropy.append(h); divergence.append(d)
    return {'position_count': len(positions), 'unique_row_target_queries': len(cache),
            'shannon_sum_interval': sum_intervals(entropy, PRECISION_BITS).to_json(),
            'diagonal_kl_sum_interval': sum_intervals(divergence, PRECISION_BITS).to_json(),
            'von_neumann_equals_shannon_by_diagonal_construction': True,
            'qre_equals_kl_by_diagonal_construction': True,
            'numeric_intervals_are_not_new_lean_proofs': True}


def _check_observation(o: dict, contract: dict, expected_package: str):
    _keys(o, ('package_hash','model_identity_hash','tensor_sha256','tensor_size','tensor_path',
              'score_dictionary','row_selectors','mass_minus_one_dictionary','row_totals','goals','tensor_hex',
              'production_rows_compared'), 'observation')
    require(o['package_hash'] == expected_package and o['tensor_path'] == TENSOR and
            type(o['tensor_size']) is int and o['tensor_size'] == 2*WIDTH*WIDTH and
            type(o['production_rows_compared']) is int and o['production_rows_compared'] == VOCAB, 'observation identity/coverage')
    for field in ('package_hash','model_identity_hash','tensor_sha256'): hash_value(o[field], field)
    encoded = o['tensor_hex']
    require(type(encoded) is str and len(encoded) == 4*WIDTH*WIDTH and
            all(c in '0123456789abcdef' for c in encoded), 'exact canonical tensor encoding required')
    raw = bytes.fromhex(encoded)
    require(sha(raw) == o['tensor_sha256'], 'tensor bytes/digest disagreement')
    rows = o['score_dictionary']; require(type(rows) is list and 1 <= len(rows) <= VOCAB, 'bounded score dictionary')
    for row in rows: _ints(row, VOCAB, -16, 15, 'score row')
    _ints(o['row_selectors'], VOCAB, 0, len(rows)-1, 'row selectors')
    expanded = [rows[i] for i in o['row_selectors']]
    require(expanded == scores_from_tensor(raw), 'score data not decoded from bound tensor')
    require(pack_rows(expanded) == (rows, o['row_selectors']), 'noncanonical/unused/duplicate dictionary rows')
    masses = [masses_from_scores(row) for row in rows]
    minus = o['mass_minus_one_dictionary']
    require(type(minus) is list and len(minus) == len(rows), 'mass dictionary shape')
    for row in minus: _ints(row, VOCAB, 0, (1 << 30)-1, 'mass row')
    require(minus == [[w-1 for w in row] for row in masses], 'mass normalization disagrees with measured scores')
    _ints(o['row_totals'], len(rows), VOCAB, VOCAB*(1 << 30), 'row totals')
    require(o['row_totals'] == [sum(row) for row in masses], 'wrong normalizing denominator')
    goals = o['goals']; require(type(goals) is list and len(goals) == 11, 'eleven goals required')
    for row, task in zip(goals, contract['tasks'], strict=True):
        _keys(row, ('task_id','effective_marker','tokens','route_evidence_hash','decode_hash'), 'goal')
        require(row['task_id'] == task['task_id'], 'goal identity/order mismatch')
        require(type(row['effective_marker']) is int and 0 <= row['effective_marker'] < VOCAB, 'effective marker type')
        _ints(row['tokens'], len(task['expected_tokens']), 0, VOCAB-1, 'goal tokens')
        require(row['tokens'] == task['expected_tokens'], 'protected goal target changed')
        for h in ('route_evidence_hash','decode_hash'): hash_value(row[h], h)


def validate_packet(p: dict):
    _keys(p, ('schema_id','policy','profile','source_bindings','joint_packet','joint_packet_sha256','bindings',
              'task_contract','task_contract_sha256','before','after','information_positions',
              'before_information','after_information','selected_goal_drift','probabilities_equal',
              'scope','claims'), 'protected semantics')
    require(p['schema_id'] == SCHEMA and p['policy'] == POLICY and canonical(p['profile']) == canonical(PROFILE), 'semantic policy substituted')
    joint = PreparedJoint(canonical(p['joint_packet']))
    require(p['joint_packet_sha256'] == sha(joint.packet_bytes) and p['bindings'] == joint.packet['bindings'], 'joint evidence binding mismatch')
    contract = p['task_contract']
    _keys(contract, ('schema_id','tasks','source','target_correct_mass','target_other_mass','horizon_input'), 'contract')
    require(p['task_contract_sha256'] == CONTRACT_SHA256 and sha(canonical(contract)) == CONTRACT_SHA256, 'historical protected task contract changed')
    require(p['source_bindings'] == SOURCE_ROWS and canonical(p['source_bindings']) == canonical(SOURCE_ROWS), 'semantic implementation bindings changed')
    before, after = p['before'], p['after']
    _check_observation(before,contract,p['bindings']['predecessor_physical_hash'])
    _check_observation(after,contract,p['bindings']['candidate_physical_hash'])
    for obs, side, task_side in [(before,'predecessor','before'),(after,'candidate','after')]:
        file_rows = joint.packet['typed_binding'][side]['modelWeights']
        entries = [r for r in file_rows if r['path'] == TENSOR]
        require(len(entries) == 1 and entries[0]['sha256'] == obs['tensor_sha256'] and
                entries[0]['size'] == obs['tensor_size'], 'tensor not bound to joint physical package')
        proof_rows = {r['task_id']: r for r in joint.packet['task_meanings'][task_side]['proof_observations']}
        require(all(g['task_id'] in proof_rows and g['decode_hash'] == proof_rows[g['task_id']]['decode_hash']
                    for g in obs['goals']), 'goal observation not bound to joint decoder evidence')
    # The raw data, not just its hash, is compared. Equal entropy is insufficient.
    require(observation_projection(before) == observation_projection(after), 'protected probability/goal observation changed')
    require(before['score_dictionary'] == after['score_dictionary'] and before['tensor_sha256'] == after['tensor_sha256'], 'inherited score/tensor changed')
    expected_positions = information_positions(before, contract)
    require(type(p['information_positions']) is list and len(p['information_positions']) == len(expected_positions), 'position coverage')
    for pair in p['information_positions']: _ints(pair, 2, 0, VOCAB-1, 'information position')
    require(p['information_positions'] == expected_positions and
            p['information_positions'] == information_positions(after,contract), 'target or context substitution')
    for name, observation in [('before_information',before),('after_information',after)]:
        require(canonical(p[name]) == canonical(information_summary(observation, expected_positions)), 'numeric report differs from exact observations')
    require(type(p['selected_goal_drift']) is int and p['selected_goal_drift'] == goal_drift(before,after) == 0 and
            p['probabilities_equal'] is True, 'false preservation flag')
    require(canonical(p['scope']) == canonical(SCOPE) and canonical(p['claims']) == canonical({k:False for k in CLAIMS}), 'unsupported completion/authority claim')


SCOPE = {'protected_sparse_observations_only': True, 'full_goal_interpretation_supplied': False,
         'full_information_interpretation_supplied': False, 'physical_projection_formally_verified': False,
         'complete_learned_step_instantiated': False, 'resource_fields_unchanged': True,
         'historical_success_reports_accepted_as_input': False, 'promotion_api': False}
CONTRACT_SHA256 = 'af34fb682a920122318f001bf2b76e826244f38202d0377f99f65515e4a14e28'
SOURCE_ROWS = [{'path': 'python/rcp_rclm_runtime_v2/rcp_rclm_runtime/mathematics/intervals.py', 'git_blob': '0f1d9e9e24f4186a20f6f0ae545d368c464a82fe', 'sha256': 'f5ad340271f6cde73f8cd350c4252d9accea364e0161a37ebe8687343edb5d1c', 'size': 8856}, {'path': 'python/rcp_rclm_runtime_v2/rcp_rclm_runtime/mathematics/rational.py', 'git_blob': '9f74af0f31189253da3b71b6eda6097ed9dd8558', 'sha256': 'dc8d5a4f1f3934a86f64cde059b4909e0b5bec1d3bedf145f767634a4883abde', 'size': 8240}, {'path': 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/constants.py', 'git_blob': '363cd0c808d959f1efc8f7bbf98e33e4b06b0257', 'sha256': 'a2254372ee5b0268085a919d428accd9b82826f48beea3efdcd95cbe346d0b43', 'size': 4155}, {'path': 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/information.py', 'git_blob': '146343ec8e0589fb5c9782880b8305c571af0fef', 'sha256': '75ca2571d564715d8d75ee3b07c83f042cbc5bfab3f3b1803cc20739942d3fe9', 'size': 10260}, {'path': 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/learned_data.py', 'git_blob': 'a525bbd8a4ed8b354eb10418aeacee19265cd01c', 'sha256': 'cbd602b233c2bbc24b23ed30a4b5dcef28f6081e34964c2cc92f96402044bade', 'size': 9685}, {'path': 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/package.py', 'git_blob': '977b5bd604646330a139af44b608fd6bb2d5c692', 'sha256': '4dde7fcc5418474fb517785fc6e77e09918ddaf717d0630e934e10a900604d6d', 'size': 22403}, {'path': 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/sparse_profile.py', 'git_blob': 'cb78f7439634948d912c3ecef067c4af138a8abc', 'sha256': 'ccc4215a9fbe3520078da7179271513da6b90cd5fd8568bcf5f29858380d44a1', 'size': 13139}, {'path': 'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/tensors.py', 'git_blob': '89762217478436013fb14fcf9c74909814599f42', 'sha256': '73131f0996ef03104ece560442f94a90851a8dbf0bba93bd87ef92d33cc6c8df', 'size': 15922}, {'path': 'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/challenges.py', 'git_blob': 'e80a2c79f8343d94967ae5f2c9e071059f6a483f', 'sha256': '4ebcacf07ea4000267bafd6ba0de9f89f55718c7bd09f252745d4f383920d014', 'size': 11000}, {'path': 'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/tasks.py', 'git_blob': '93c9cf0c9ab04c8f1128073f5cd1b09392fd9654', 'sha256': '73ed9cc123142f5cc03828f8be98b0fa523867b986a587ed55aee36d405d2d5a', 'size': 25439}]


@dataclass(frozen=True)
class PreparedProtectedSemantics:
    packet_bytes: bytes

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES, 'bounded immutable semantic packet required')
        p = load_json_strict(self.packet_bytes)
        require(canonical(p) == self.packet_bytes, 'noncanonical semantic packet')
        validate_packet(p)

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)


def prepare_protected_semantics(before: PackageReceipt, after: PackageReceipt, parent: HistoricalPredecessor, *,
                                bundle: Path, capture: Path, source_root: Path,
                                transcript: bytes, expected_transcript_hash: str) -> PreparedProtectedSemantics:
    sources = semantic_sources(source_root)
    start_before, start_after = snapshot(before.root), snapshot(after.root)
    joint = prepare_joint(before,after,parent,bundle=bundle,capture=capture,source_root=source_root,
                          transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    pairs = protected_tasks(bundle); contract = task_contract(pairs)
    require(sha(canonical(contract)) == CONTRACT_SHA256, 'original task definition changed')
    b, a = observe(before,pairs), observe(after,pairs)
    positions = information_positions(b,contract)
    p = {'schema_id': SCHEMA, 'policy': POLICY, 'profile': PROFILE, 'source_bindings': sources,
         'joint_packet': joint.packet, 'joint_packet_sha256': sha(joint.packet_bytes), 'bindings': joint.packet['bindings'],
         'task_contract': contract, 'task_contract_sha256': CONTRACT_SHA256,
         'before': b, 'after': a, 'information_positions': positions,
         'before_information': information_summary(b,positions), 'after_information': information_summary(a,positions),
         'selected_goal_drift': goal_drift(b,a), 'probabilities_equal': observation_projection(b) == observation_projection(a),
         'scope': SCOPE, 'claims': {k:False for k in CLAIMS}}
    require(start_before == snapshot(before.root) and start_after == snapshot(after.root), 'physical package changed')
    require(sources == semantic_sources(source_root), 'semantic source changed')
    for receipt, raw, anchor in [(before,None,None),(after,transcript,expected_transcript_hash)]:
        verify_package(receipt.root,parent,bundle,expected_package_hash=receipt.package_hash,
                       transcript=raw,expected_transcript_hash=anchor)
    return PreparedProtectedSemantics(canonical(p))


def verify_protected_bytes(raw: bytes, recomputed: PreparedProtectedSemantics, *, expected_sha256: str):
    require(type(raw) is bytes and sha(raw) == hash_value(expected_sha256,'external packet anchor'), 'packet anchor differs')
    require(type(recomputed) is PreparedProtectedSemantics and raw == recomputed.packet_bytes, 'packet is not independently recomputed evidence')
    return PreparedProtectedSemantics(raw)
