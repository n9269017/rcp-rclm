"""Phase 17L: one immutable transaction for typed, task and producer evidence.

A valid capsule is not an accepted root transition. It carries independently
recomputed subpackets; the new real proof checks must then validate their joint
certificate. Hash equality is integrity relative to an external anchor, not
execution attestation or a proof of the physical observation mapping.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from .bootstrap import HistoricalPredecessor
from .materialized import PackageReceipt, require, sha, snapshot, verify_package
from .learned_state_binding import (PreparedLearnedBinding, prepare_learned_binding,
                                  GROUPS, CLAIMS, hash_value)
from .frontier_meanings import PreparedMeanings, prepare_meanings, HISTORICAL_CATALOG_SHA256
from .proposal_provenance import PreparedProvenance, prepare_provenance, producer_sources

SCHEMA = 'runtime.v5.phase17.same-candidate-composition.v1'
POLICY = 'phase17.same-parent-candidate-transcript-program-objective-challenge.v1'
MAX_BYTES = 2 * 1024 * 1024
KINDS = ('typed_binding', 'task_meanings', 'producer_provenance')
SCOPE = {
    'physical_observation_refinement_formally_verified': False,
    'full_base_obligations_instantiated': False,
    'goal_information_resource_witnesses_supplied': False,
    'root_acceptance_evaluated': False,
    'authorization_issued': False,
    'historical_capability_reports_reassigned': False,
    'same_candidate_subcertificates_required': True,
    'phase17h_plan_proofs_rerun': False,
    'selected_finite_vector_task_scope_only': True,
}
REMAINING = (
    'concrete_compatible_base_RCP_RCLM_obligations',
    'physical_observation_refinement_to_composed_kernel',
    'concrete_goal_drift_and_budget',
    'complete_resource_measurement_budget_and_enforcement',
    'full_information_semantics_and_nonregression',
    'autonomous_recursive_productivity_and_history_obligations',
    'durable_fresh_challenge_consumption',
    'active_atomic_promotion_and_rollback',
)


def shared_bindings(typed: PreparedLearnedBinding, tasks: PreparedMeanings,
                    provenance: PreparedProvenance) -> dict:
    """Reject independently valid subpackets from different transactions.

    This function proves no physical facts on its own. Production construction
    uses prepare_joint, which independently measures and replays the same input.
    """
    require(type(typed) is PreparedLearnedBinding and type(tasks) is PreparedMeanings
            and type(provenance) is PreparedProvenance, 'exact prepared subpacket types required')
    i, j, k = typed.packet, tasks.packet, provenance.packet
    b = i['bindings']; t = k['trace']; producer = k['producer']; c = k['candidate']
    require(canonical(b) == canonical(j['bindings']), 'typed/task transaction mismatch')
    require(t['terminal'] == 'await_root_verification' and c is not None,
            'joint certificate requires a passing ordered proposal')
    expected = {
        'historical_state_hash': producer['predecessor_state_hash'],
        'predecessor_physical_hash': producer['physical_package_hash'],
        'candidate_physical_hash': c['physical_package_hash'],
        'transcript_sha256': k['transcript_sha256'],
        'program_hash': c['program_hash'],
        'objective_hash': t['objective_hash'],
        'challenge_commitment_hash': t['current_view']['challenge_commitment_hash'],
    }
    require(canonical(b) == canonical(expected), 'task/producer transaction mismatch')
    require(c['parent_physical_hash'] == b['predecessor_physical_hash'] and
            c['transcript_sha256'] == b['transcript_sha256'], 'candidate ancestry mismatch')
    for ik, jk in (('predecessor', 'before'), ('candidate', 'after')):
        state, observation = i[ik], j[jk]
        require(state['package_hash'] == observation['package_hash'], 'observation package mismatch')
        require(state['base'] == [digest(p) for p in observation['programs']],
                'typed/task program inventory mismatch')
        require(state['capabilityFrontier'] == observation['declared_ids'],
                'typed/task frontier declaration mismatch')
    require(i['new_capability'] == j['new_task_id'] and i['new_program'] == t['selected_program_hash'] and
            digest(j['after']['programs'][-1]) == t['steps'][-1]['program_hash'],
            'selected program/task mismatch')
    require(sha(canonical(j['tasks'][:21])) == HISTORICAL_CATALOG_SHA256, 'historical task scope changed')
    return dict(b)


@dataclass(frozen=True)
class PreparedJoint:
    packet_bytes: bytes

    def __post_init__(self) -> None:
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable joint capsule required')
        validate_packet(load_json_strict(self.packet_bytes))

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)

    def components(self) -> tuple[PreparedLearnedBinding, PreparedMeanings, PreparedProvenance]:
        p = self.packet
        return (PreparedLearnedBinding(canonical(p['typed_binding'])),
                PreparedMeanings(canonical(p['task_meanings'])),
                PreparedProvenance(canonical(p['producer_provenance'])))


def validate_packet(p: dict) -> None:
    require(type(p) is dict and set(p) == {'schema_id', 'policy', *KINDS, 'bindings',
            'component_sha256', 'scope', 'claims', 'remaining_witness_classes'}, 'exact joint fields required')
    require(p['schema_id'] == SCHEMA and p['policy'] == POLICY, 'joint policy mismatch')
    i = PreparedLearnedBinding(canonical(p['typed_binding']))
    j = PreparedMeanings(canonical(p['task_meanings']))
    k = PreparedProvenance(canonical(p['producer_provenance']))
    require(canonical(p['bindings']) == canonical(shared_bindings(i, j, k)), 'joint shared bindings differ')
    hashes = {n: sha(canonical(p[n])) for n in KINDS}
    require(p['component_sha256'] == hashes, 'subpacket byte identity mismatch')
    require(canonical(p['scope']) == canonical(SCOPE), 'joint scope escalation')
    require(p['remaining_witness_classes'] == list(REMAINING), 'missing witnesses concealed')
    require(type(p['claims']) is dict and set(p['claims']) == set(CLAIMS) and
            all(v is False for v in p['claims'].values()), 'joint closure/authorization claim rejected')


def join_prepared(typed: PreparedLearnedBinding, tasks: PreparedMeanings,
                  provenance: PreparedProvenance) -> PreparedJoint:
    """Compatibility check, not a physical verifier or report-based acceptance."""
    b = shared_bindings(typed, tasks, provenance)
    parts = dict(zip(KINDS, (typed.packet, tasks.packet, provenance.packet), strict=True))
    return PreparedJoint(canonical({'schema_id': SCHEMA, 'policy': POLICY, **parts,
        'bindings': b, 'component_sha256': {n: sha(canonical(v)) for n, v in parts.items()},
        'scope': dict(SCOPE), 'claims': {k: False for k in CLAIMS},
        'remaining_witness_classes': list(REMAINING)}))


def prepare_joint(before: PackageReceipt, after: PackageReceipt, parent: HistoricalPredecessor, *,
                  bundle: Path, capture: Path, source_root: Path, transcript: bytes,
                  expected_transcript_hash: str) -> PreparedJoint:
    """Measure once-selected packages, then independently reconstruct all layers.

    No old execution report, pass vector, proof path or candidate-provided verdict
    is accepted. Prior reports are never relabeled for the changed transcript.
    The caller supplies an external transcript anchor, not a self-hash alone.
    """
    hash_value(expected_transcript_hash, 'external transcript anchor required')
    require(type(transcript) is bytes and sha(transcript) == expected_transcript_hash,
            'anchored transcript mismatch')
    require(before.root.resolve() != after.root.resolve(), 'same package directory')
    pf, cf = snapshot(before.root), snapshot(after.root)
    pins = producer_sources(source_root)
    provenance = prepare_provenance(before, after, parent, bundle=bundle, source_root=source_root,
                                   transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    tasks = prepare_meanings(before, after, parent, bundle=bundle, capture=capture,
                             transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    typed, operational = prepare_learned_binding(before, after, parent, bundle=bundle, capture=capture,
                             transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    require(typed.packet['operational_packet_sha256'] == sha(operational.packet_bytes),
            'fresh operational computation binding differs')
    result = join_prepared(typed, tasks, provenance)
    require(snapshot(before.root) == pf and snapshot(after.root) == cf and
            producer_sources(source_root) == pins, 'input/source changed during joint verification')
    verify_package(before.root, parent, bundle, expected_package_hash=before.package_hash)
    verify_package(after.root, parent, bundle, expected_package_hash=after.package_hash,
                   transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    return result


def verify_joint_bytes(raw: bytes, independently_prepared: PreparedJoint, *, expected_sha256: str) -> None:
    hash_value(expected_sha256, 'external joint anchor required')
    require(type(independently_prepared) is PreparedJoint and type(raw) is bytes and
            sha(raw) == expected_sha256 and raw == independently_prepared.packet_bytes,
            'joint capsule differs from anchored independent recomputation')
    PreparedJoint(raw)
