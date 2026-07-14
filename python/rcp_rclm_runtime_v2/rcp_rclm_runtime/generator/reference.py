from __future__ import annotations

from typing import Final, Literal

from rcp_rclm_runtime.canonical.hashing import (
    canonical_json_hash,
    file_record_from_bytes,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.schema.package import PackageManifestRecord
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    RclmStateRecord,
)
from rcp_rclm_runtime.checker.policy import (
    CHECKER_POLICY_HASH,
    CLAIM_BOUNDARY_HASH,
    LEAN_VERIFIER_POLICY_HASH,
)
from rcp_rclm_runtime.checker.records import ResourceRecord, TrustAnchorRecord
from rcp_rclm_runtime.checker.reference import (
    canonical_rclm_state,
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.generator.grammar import (
    reference_budget,
    reference_objective,
    reference_policy,
)
from rcp_rclm_runtime.generator.process import REFERENCE_PROCESS_ENVIRONMENT_HASH
from rcp_rclm_runtime.generator.protocol import (
    GeneratorPredecessorViewRecord,
    ReferenceGeneratorInputRecord,
)

ReferenceSeedState = Literal["initial", "target"]
REFERENCE_CONTROLLER_BUDGET_UNITS: Final[int] = 1
REFERENCE_CONTROLLER_CONSUMED_UNITS: Final[int] = 1


def reference_transition_id(state: ReferenceSeedState) -> str:
    if state == "initial":
        return "phase5a.gate_b_classical.initial.improve"
    return "phase5a.gate_b_classical.target.stabilize"


def reference_controller_trust_anchor() -> TrustAnchorRecord:
    return reference_trust_anchor()


def reference_controller_resource_record() -> ResourceRecord:
    return reference_resource_record(
        budget_units=REFERENCE_CONTROLLER_BUDGET_UNITS,
        consumed_units=REFERENCE_CONTROLLER_CONSUMED_UNITS,
        environment_hash=REFERENCE_PROCESS_ENVIRONMENT_HASH,
    )


def reference_generator_input(
    state: ReferenceSeedState,
) -> ReferenceGeneratorInputRecord:
    transition_id = reference_transition_id(state)
    predecessor = canonical_rclm_state(ClassicalBinaryStateRecord(state))
    trust_anchor = reference_controller_trust_anchor()
    resource_record = reference_controller_resource_record()
    predecessor_manifest = _predecessor_manifest(
        transition_id,
        predecessor,
        trust_anchor,
        resource_record,
    )
    predecessor_view = GeneratorPredecessorViewRecord(
        package_id=predecessor_manifest.package_id,
        manifest_hash=predecessor_manifest.content_hash(),
        semantic_tree_hash=predecessor_manifest.semantic_tree_hash,
        state_hash=canonical_json_hash(predecessor.to_json()),
        state=predecessor,
    )
    return ReferenceGeneratorInputRecord(
        transition_id=transition_id,
        predecessor=predecessor_view,
        policy=reference_policy(),
        objective=reference_objective(),
        budget=reference_budget(),
    )


def _predecessor_manifest(
    transition_id: str,
    predecessor: RclmStateRecord,
    trust_anchor: TrustAnchorRecord,
    resource_record: ResourceRecord,
) -> PackageManifestRecord:
    predecessor_json = predecessor.to_json()
    predecessor_files = (
        file_record_from_bytes(
            "state/predecessor.json",
            "0644",
            canonical_json_bytes(predecessor_json),
        ),
    )
    return PackageManifestRecord(
        package_id=f"{transition_id}.predecessor",
        parent_package_id=None,
        parent_manifest_hash=None,
        semantic_tree_hash=semantic_tree_hash(predecessor_files),
        candidate_hash=canonical_json_hash(predecessor_json),
        certificate_packet_hash=canonical_json_hash(
            {
                "schema_id": "runtime.phase4_root_certificate.v2",
                "transition_id": transition_id,
            }
        ),
        checker_policy_hash=CHECKER_POLICY_HASH,
        lean_verifier_policy_hash=LEAN_VERIFIER_POLICY_HASH,
        trust_anchor_hash=canonical_json_hash(trust_anchor.to_json()),
        resource_record_hash=canonical_json_hash(resource_record.to_json()),
        claim_boundary_hash=CLAIM_BOUNDARY_HASH,
    )
