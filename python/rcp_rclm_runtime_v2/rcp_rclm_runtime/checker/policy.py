from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal, TypeAlias

from rcp_rclm_runtime._version import CONTRACT_VERSION, FORMAL_SOURCE_COMMIT, LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.mathematics.intervals import PRECISION_SCHEDULE

CheckerScope: TypeAlias = Literal["gate_b_classical", "gate_c_diagonal_quantum"]
ProtectedDistinctionName: TypeAlias = Literal[
    "target_fit",
    "normalization",
    "trace_one",
    "entropy_preserved",
]

PHASE_3_SCHEMA_VERSION: Final[str] = "rcp-rclm-runtime-phase-3-checker-v1"
CHECKER_IMPLEMENTATION_ID: Final[str] = "rcp-rclm-phase-3-selected-reference-checker-v1"

FORMAL_MANIFEST_BLOB: Final[str] = "a2153043eb68e912e7e700600dcd1346ce514dbb"
GATE_C_AUDIT_SHA256: Final[str] = (
    "18b4593e544fa926af7fac20c5623850c929004d944f509d017dba04f6f7f2e5"
)
PHASE_2_PROJECT_PIN_HASH: Final[str] = (
    "32cbf7de4cf65298568432322fb428bceb4cb66269be934de537d0c8991a66d9"
)

CHECKER_POLICY_PAYLOAD: Final[dict[str, object]] = {
    "schema_version": PHASE_3_SCHEMA_VERSION,
    "implementation_id": CHECKER_IMPLEMENTATION_ID,
    "contract_version": CONTRACT_VERSION,
    "formal_source_commit": FORMAL_SOURCE_COMMIT,
    "supported_scopes": [
        "gate_b_classical",
        "gate_c_diagonal_quantum",
    ],
    "residual_indices": ["typed", "packet"],
    "loss_budget": "exact_zero",
    "recovery_budget": "exact_zero",
    "precision_schedule": list(PRECISION_SCHEDULE),
    "candidate_assertions_authoritative": False,
    "model_calls_allowed": 0,
    "network_calls_allowed": 0,
    "checker_input_mutation_allowed": False,
    "generator_dependency_allowed": False,
    "lean_acceptance_required": True,
}
CHECKER_POLICY_HASH: Final[str] = canonical_json_hash(CHECKER_POLICY_PAYLOAD)

LEAN_VERIFIER_POLICY_PAYLOAD: Final[dict[str, object]] = {
    "contract_version": CONTRACT_VERSION,
    "formal_source_commit": FORMAL_SOURCE_COMMIT,
    "lean_toolchain": LEAN_TOOLCHAIN,
    "mathlib_commit": MATHLIB_COMMIT,
    "project_pin_hash": PHASE_2_PROJECT_PIN_HASH,
    "source_guard_required": True,
    "structured_packet_bound_verdict_required": True,
    "rcp_and_rclm_acceptance_required": True,
    "timeout_is_acceptance": False,
}
LEAN_VERIFIER_POLICY_HASH: Final[str] = canonical_json_hash(LEAN_VERIFIER_POLICY_PAYLOAD)

CLAIM_BOUNDARY_PAYLOAD: Final[dict[str, object]] = {
    "selected_gate_b_reference": True,
    "selected_diagonal_gate_c_reference": True,
    "general_noncommuting_quantum": False,
    "candidate_acceptance_licensed": False,
    "promotion_licensed": False,
    "generator_trusted": False,
    "model_free_checker": True,
    "phase_4_adversarial_closure_required": True,
}
CLAIM_BOUNDARY_HASH: Final[str] = canonical_json_hash(CLAIM_BOUNDARY_PAYLOAD)

EVALUATOR_POLICY_PAYLOAD: Final[dict[str, object]] = {
    "policy": "selected-reference-exact-observation-v1",
    "source_of_truth": "state-derived exact distribution or diagonal spectrum",
    "native_float_allowed": False,
    "normalization_repair_allowed": False,
    "unsupported_dense_quantum_allowed": False,
}
EVALUATOR_POLICY_HASH: Final[str] = canonical_json_hash(EVALUATOR_POLICY_PAYLOAD)

RESOURCE_METER_POLICY_PAYLOAD: Final[dict[str, object]] = {
    "policy": "phase-3-pure-checker-resource-meter-v1",
    "model_invocations": 0,
    "network_requests": 0,
    "predecessor_write_attempts": 0,
    "candidate_write_attempts": 0,
    "checker_source_write_attempts": 0,
    "manual_repairs": 0,
    "hidden_oracle_reads": 0,
}
RESOURCE_METER_POLICY_HASH: Final[str] = canonical_json_hash(RESOURCE_METER_POLICY_PAYLOAD)

_CLASSICAL_DISTINCTIONS: Final[Sequence[ProtectedDistinctionName]] = (
    "target_fit",
    "normalization",
)
_QUANTUM_DISTINCTIONS: Final[Sequence[ProtectedDistinctionName]] = (
    "target_fit",
    "trace_one",
    "entropy_preserved",
)


def required_protected_distinctions(scope: CheckerScope) -> Sequence[ProtectedDistinctionName]:
    if scope == "gate_b_classical":
        return _CLASSICAL_DISTINCTIONS
    if scope == "gate_c_diagonal_quantum":
        return _QUANTUM_DISTINCTIONS
    raise ValueError(f"unsupported checker scope: {scope}")
