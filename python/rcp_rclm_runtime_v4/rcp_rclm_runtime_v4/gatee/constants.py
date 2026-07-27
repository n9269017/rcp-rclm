from __future__ import annotations

from typing import Final

CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v4-gate-e-v1"
REPORT_SCHEMA_ID: Final[str] = "runtime.v4.gatee.autonomous_search_report.v1"
ROUTE_HINT_SCHEMA_ID: Final[str] = "runtime.v4.gatee.route_hint_policy.v1"
FRONTIER_SCHEMA_ID: Final[str] = "runtime.v4.gatee.frontier_snapshot.v1"
ATTEMPT_SCHEMA_ID: Final[str] = "runtime.v4.gatee.search_attempt.v1"
EXHAUSTION_SCHEMA_ID: Final[str] = "runtime.v4.gatee.search_exhaustion_certificate.v1"

FORBIDDEN_ROUTE_HINT_FIELDS: Final[tuple[str, ...]] = (
    "accepted_program_bytes_present",
    "expected_candidate_hash_present",
    "expected_final_model_identity_present",
    "expected_new_capability_present",
    "host_selected_objective_present",
    "next_successful_transition_index_present",
    "required_successful_component_set_present",
)

RESULT_PROMOTED: Final[str] = "promoted"
RESULT_EXHAUSTED: Final[str] = "exhausted"
RESULT_KINDS: Final[frozenset[str]] = frozenset({RESULT_PROMOTED, RESULT_EXHAUSTED})
