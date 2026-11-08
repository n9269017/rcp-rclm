"""Phase 17Q: a same-candidate finite-observation certificate input.

This increment reconstructs the retained P *fixture*, not P's live campaign.
Physical packages and protected observations are read afresh.  The N journal
is retained historical reference-work evidence whose schedule/results are
recomputed; it is not a measurement of the cost of this new verification.
No active store, worker, challenge source, or promotion API is used here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from .campaign_transaction import load_predecessor
from .handoff_source import checked_handoff, unhex, FIXTURE_SHA
from .joint_evidence import PreparedJoint
from .materialized import materialize_package, verify_package, snapshot
from .metered_evaluation import (prepare_work, verify_profile, selected_binding,
                                 validate_work_results)
from .protected_semantics import (PreparedProtectedSemantics,
                                  prepare_protected_semantics, observation_projection)
from .resource_ledger import (canonical, require, sha, digest, exact, Policy,
                              full_grammar_policy, replay as resource_replay, _no_links)
from .transition_journal import replay as transition_replay

BASE = '85ea17f46ff594b9a4a67ab51678b5656461f6b2'
SCHEMA = 'rcp-rclm.phase17q.finite-observation-packet.v1'
POLICY = 'phase17q.same-staged-fixture-finite-observation-kernel.v1'
MAX_BYTES = 16 * 1024 * 1024
P_ROOT = 'artifacts/development/phase17p/op-fb904e168e85/gate'
P_FIXTURE = P_ROOT + '/profile/fixture'
TRANSACTION = '6467827fa82103d213b86778dd1e05dab9989f6bf4b8df0cec321e82ba88c965'
P_DOSSIER = P_FIXTURE + '/staging/transactions/' + TRANSACTION
N_ROOT = 'artifacts/development/phase17n/op-2a7186e3590f/gate'
P_EXECUTION = P_ROOT + '/execution.json'
P_EXECUTION_SHA = '7230e2565d1380702e2573552224affa02d1396950fc631b86e32234872ec400'
P_HEAD = '606fbdbf4d16e675802509ed44af42ad97ef36bc1f083c7e29995f4c9d488e78'
JOINT_SHA = '035c570a3e4b7f1ed2fd43085d9cd6357b2596a169eebcd621c0ff5d0fe274ac'
RETAINED_PINS = {
    P_EXECUTION: P_EXECUTION_SHA,
    P_FIXTURE + '/source.json': '4be76d208a6d2f33e48b99239c358905825538df9b4b89b78138db3d54bd57f5',
    P_FIXTURE + '/staging/binding.json': '03a20957d3561e294ce3a61e49f97089a2d06e88da0f7a2ab3bbf5a9d6d5e0f3',
    P_FIXTURE + '/staging/expected-head.txt': '38bc7c1e0bbd00df6116d4da46400cbaa254390388f42a47e7f6eb001493ce65',
    P_FIXTURE + '/staging/journal.jsonl': 'e7ef375e164b4449f69f872db507be7301c94c472291909bdff02034bdf1a873',
    P_DOSSIER + '/joint-evidence.json': JOINT_SHA,
    P_DOSSIER + '/assessment.json': '4f2c777393d74150b3ddd75e0486707d124a4b4ffa5d2ae872ae6fb8359fbfd5',
    N_ROOT + '/profile.json': '76c680f3d9b71a78a1afabad1e52b2113a9c65cf8fa14d1126d327b85d57e864',
    N_ROOT + '/resource-journal.jsonl': 'aa20e37afa57295bb094c5ad7cd093cfb922f189dc0f0d1ef060a6d696f794b5',
}
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
    'domain': 'finite observations of the pinned historical synthetic staged package',
    'physical_mapping': 'externally checked extraction, not a universal Lean refinement proof',
    'resource_interpretation': 'retained N bounded reference-work tariff; not Q execution costs',
    'protected_interpretation': 'eleven inherited byte-token goals and fixed diagonal KL targets',
    'frontier_interpretation': 'selected theorem observations and bounded vector contracts',
    'recovery_interpretation': 'candidate-tied inverse of the finite observation append, not active filesystem rollback',
    'historical_campaigns_rerun': False,
    'fresh_workers': 0,
    'fresh_challenges': 0,
    'promotion_api': False,
}
UNMEASURED = (
    'Q preparation and proof checking', 'bootstrap and archive validation',
    'physical staging and observation', 'hashing and canonical parsing',
    'Python overhead and journal I/O', 'CPU time', 'accelerator time',
    'memory', 'storage', 'energy', 'active promotion and rollback',
)


def read_retained(root: Path) -> dict[str, bytes]:
    """External fixed anchors, never a caller-selected report or proof path."""
    result = {}
    for relative, expected in RETAINED_PINS.items():
        path = root / relative
        _no_links(path)
        require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'missing/oversized retained evidence: ' + relative)
        raw = path.read_bytes()
        require(sha(raw) == expected, 'retained evidence changed: ' + relative)
        result[relative] = raw
    return result


def _decode_retained(value: object) -> dict[str, bytes]:
    exact(value, set(RETAINED_PINS))
    out = {}
    for name, expected in RETAINED_PINS.items():
        raw = unhex(value[name])
        require(sha(raw) == expected, 'retained input anchor differs: ' + name)
        out[name] = raw
    return out


def _staging(retained: dict[str, bytes], bindings: dict) -> dict:
    binding = load_json_strict(retained[P_FIXTURE + '/staging/binding.json'])
    require(retained[P_FIXTURE + '/staging/expected-head.txt'] == (P_HEAD + '\n').encode(), 'P head differs')
    state = transition_replay(retained[P_FIXTURE + '/staging/journal.jsonl'],
                              expected_head=P_HEAD, expected_binding=binding)
    require(state.status == 'open' and state.pending is None and len(state.completed) == 1, 'P fixture is unresolved')
    completed = load_json_strict(state.completed[0])
    assessment_raw = retained[P_DOSSIER + '/assessment.json']
    assessment = load_json_strict(assessment_raw)
    require(completed['completion']['report_sha256'] == sha(assessment_raw), 'P dossier is not journal-bound')
    require(completed['begin']['transaction_id'] == TRANSACTION and
            completed['completion']['outcome'] == 'blocked_missing_root_witnesses', 'P outcome changed')
    require(binding['mode'] == 'retained_synthetic_fixture' and
            binding['predecessor_physical_hash'] == bindings['predecessor_physical_hash'] and
            binding['predecessor_state_hash'] == bindings['historical_state_hash'] and
            binding['scope_id'] == bindings['transcript_sha256'] == FIXTURE_SHA,
            'staged parent or transcript differs')
    require(state.consumed == (bindings['challenge_commitment_hash'],) and
            state.source_hashes == (RETAINED_PINS[P_FIXTURE + '/source.json'],), 'P consumption binding differs')
    require(assessment['candidate_physical_hash'] == bindings['candidate_physical_hash'] and
            assessment['root_acceptance_evaluated'] is False and
            assessment['physical_candidate_staged'] is True, 'P candidate/authority differs')
    return {'transaction_id': TRANSACTION, 'journal_head': P_HEAD,
            'source_kind': 'retained_synthetic_fixture',
            'source_sha256': RETAINED_PINS[P_FIXTURE + '/source.json'],
            'outcome': 'blocked_missing_root_witnesses', 'root_acceptance_evaluated': False}


def _resource(retained: dict[str, bytes], bindings: dict) -> dict:
    profile = load_json_strict(retained[N_ROOT + '/profile.json'], require_canonical=False)
    policy = Policy.from_json(profile['policy'])
    require(policy == full_grammar_policy(8), 'fixed work budget differs')
    anchors = selected_binding()
    require(anchors['predecessor_package_hash'] == bindings['predecessor_physical_hash'] and
            anchors['candidate_package_hash'] == bindings['candidate_physical_hash'] and
            anchors['transcript_sha256'] == bindings['transcript_sha256'], 'resource candidate differs')
    raw = retained[N_ROOT + '/resource-journal.jsonl']
    checked = resource_replay(raw, expected_head=profile['journal_head'], policy=policy, expected_binding=anchors)
    require(checked.status == 'sealed' and checked.pending_hash is None, 'resource journal unresolved')
    require(list(checked.spent) == profile['spent'] == [9, 144, 576, 576] and
            checked.charged_cost == profile['charged_cost'] == 4032 and
            list(checked.charges) == profile['charge_sequence'] and
            sha(raw) == profile['journal_sha256'], 'resource profile differs from recomputed accounting')
    return {'origin': 'retained_phase17n_reference_profile', 'policy': policy.to_json(),
            'binding': anchors, 'journal_head': checked.head, 'journal_sha256': sha(raw),
            'charge_sequence': list(checked.charges), 'spent': list(checked.spent),
            'charged_cost': checked.charged_cost, 'operation_count': len(checked.operation_ids),
            'historical_physical_cost_recovered': False, 'Q_execution_cost_measured': False}


def validate_packet(p: dict) -> PreparedProtectedSemantics:
    exact(p, {'schema', 'policy', 'base_commit', 'protected_packet', 'protected_packet_sha256',
              'bindings', 'retained_hex', 'retained_sha256', 'staging', 'resource', 'scope',
              'unmeasured', 'claims'})
    require(p['schema'] == SCHEMA and p['policy'] == POLICY and p['base_commit'] == BASE, 'finite kernel policy differs')
    require(canonical(p['scope']) == canonical(SCOPE) and p['unmeasured'] == list(UNMEASURED), 'scope escalation')
    require(canonical(p['claims']) == canonical({k: False for k in FALSE_CLAIMS}), 'unsupported authority/closure claim')
    retained = _decode_retained(p['retained_hex'])
    require(canonical(p['retained_sha256']) == canonical(RETAINED_PINS), 'retained manifest differs')
    require(canonical(p['staging']) == canonical(_staging(retained, p['bindings'])), 'staging projection differs')
    require(canonical(p['resource']) == canonical(_resource(retained, p['bindings'])), 'resource projection differs')
    protected = PreparedProtectedSemantics(canonical(p['protected_packet']))
    require(p['protected_packet_sha256'] == sha(protected.packet_bytes) and
            canonical(p['bindings']) == canonical(protected.packet['bindings']), 'protected binding differs')
    require(canonical(protected.packet['joint_packet']) == retained[P_DOSSIER + '/joint-evidence.json'],
            'fresh same-candidate capsule differs from the staged P fixture')
    return protected


@dataclass(frozen=True, slots=True)
class PreparedFiniteKernel:
    packet_bytes: bytes
    _protected: PreparedProtectedSemantics = field(init=False, repr=False, compare=False)
    _joint: PreparedJoint = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES, 'bounded immutable finite packet required')
        value = load_json_strict(self.packet_bytes)
        require(canonical(value) == self.packet_bytes, 'canonical finite packet required')
        protected = validate_packet(value)
        object.__setattr__(self, '_protected', protected)
        object.__setattr__(self, '_joint', PreparedJoint(canonical(protected.packet['joint_packet'])))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def protected(self) -> PreparedProtectedSemantics:
        return self._protected

    def joint(self) -> PreparedJoint:
        return self._joint


def prepare_finite_kernel(root: Path, packages: Path) -> PreparedFiniteKernel:
    """Fresh physical extraction plus retained-input replay. No worker/prover."""
    _no_links(packages)
    require(not packages.exists(), 'new physical package directory required')
    require(packages.resolve() != root.resolve() and root.resolve() not in packages.resolve().parents,
            'physical package directory must be outside the source checkout')
    retained = read_retained(root)
    parent = load_predecessor(root)
    source = retained[P_FIXTURE + '/source.json']
    handoff = checked_handoff(parent, source, expected_source_hash=RETAINED_PINS[P_FIXTURE + '/source.json'])
    require(handoff.record['source_kind'] == 'retained_synthetic_fixture' and
            handoff.record['terminal_action'] == 'await_root_verification', 'selected fixture has no staged candidate')
    bundle = root / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
    capture = root / 'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
    packages.mkdir(parents=True)
    before = materialize_package(packages / 'before', parent, bundle)
    after = materialize_package(packages / 'after', parent, bundle,
                                transcript=handoff.transcript, expected_transcript_hash=FIXTURE_SHA)
    snapshots = snapshot(before.root), snapshot(after.root)
    protected = prepare_protected_semantics(before, after, parent, bundle=bundle, capture=capture,
                 source_root=root, transcript=handoff.transcript, expected_transcript_hash=FIXTURE_SHA)
    # Verify every retained operation, its order, and output against independently
    # derived work. This recomputation is outside the historical tariff.
    profile = load_json_strict(retained[N_ROOT + '/profile.json'], require_canonical=False)
    work = prepare_work(parent, handoff.transcript, expected_hash=FIXTURE_SHA)
    verified = verify_profile(retained[N_ROOT + '/resource-journal.jsonl'],
        expected_head=profile['journal_head'], policy=Policy.from_json(profile['policy']),
        expected_binding=selected_binding(), expected_work=work)
    outputs = {task.identity: task.execute() for task in work}
    verdicts = validate_work_results(parent, handoff.transcript, outputs)
    require(verdicts == profile['verdicts'] and len(work) == len(verified.operation_ids) == 153,
            'retained work schedule or output verification differs')
    p = protected.packet
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE,
              'protected_packet': p, 'protected_packet_sha256': sha(protected.packet_bytes),
              'bindings': p['bindings'], 'retained_hex': {k: v.hex() for k, v in retained.items()},
              'retained_sha256': dict(RETAINED_PINS), 'staging': _staging(retained, p['bindings']),
              'resource': _resource(retained, p['bindings']), 'scope': dict(SCOPE),
              'unmeasured': list(UNMEASURED), 'claims': {k: False for k in FALSE_CLAIMS}}
    result = PreparedFiniteKernel(canonical(packet))
    require(snapshots == (snapshot(before.root), snapshot(after.root)), 'physical packages changed during Q preparation')
    for receipt, raw, anchor in ((before, None, None), (after, handoff.transcript, FIXTURE_SHA)):
        verify_package(receipt.root, parent, bundle, expected_package_hash=receipt.package_hash,
                       transcript=raw, expected_transcript_hash=anchor)
    require(retained == read_retained(root), 'retained evidence changed during Q preparation')
    return result


def verify_packet_bytes(raw: bytes, recomputed: PreparedFiniteKernel, *, expected_sha256: str) -> None:
    require(type(raw) is bytes and sha(raw) == digest(expected_sha256), 'external finite packet anchor differs')
    require(type(recomputed) is PreparedFiniteKernel and raw == recomputed.packet_bytes,
            'finite packet differs from independent physical recomputation')
    PreparedFiniteKernel(raw)
