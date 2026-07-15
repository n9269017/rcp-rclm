from __future__ import annotations
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Literal, TypeAlias, cast
from rcp_rclm_runtime.canonical.hashing import validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
PHASE7_STAGE_SCHEMA_ID = "runtime.phase7_stage_result.v2"
PHASE7_POLICY_SCHEMA_ID = "runtime.phase7_controller_policy.v2"
PHASE7_BUDGET_SCHEMA_ID = "runtime.phase7_controller_budget.v2"
PHASE7_ATTEMPT_SCHEMA_ID = "runtime.phase7_attempt_report.v2"
PHASE7_PACKAGE_SCHEMA_ID = "runtime.phase7_immutable_package_manifest.v2"
PHASE7_LEDGER_SCHEMA_ID = "runtime.phase7_ledger_entry.v2"
PHASE7_ACTIVE_POINTER_SCHEMA_ID = "runtime.phase7_active_pointer.v2"
PHASE7_CONTROLLER_REPORT_SCHEMA_ID = "runtime.phase7_controller_report.v2"
StageStatus: TypeAlias = Literal["pass", "fail", "indeterminate", "not_evaluated"]
AttemptVerdict: TypeAlias = Literal["accept", "reject", "indeterminate"]
ControllerVerdict: TypeAlias = Literal["promoted", "exhausted", "indeterminate"]
PackageStatus: TypeAlias = Literal["root", "promoted"]
LedgerEvent: TypeAlias = Literal["bootstrap", "promotion", "rejection", "indeterminate"]
class Phase7ReasonCode(StrEnum):
    SCHEMA_MALFORMED = 'PHASE7_SCHEMA_MALFORMED'
    STORE_LOCKED = 'PHASE7_STORE_LOCKED'
    ACTIVE_STORE_INVALID = 'PHASE7_ACTIVE_STORE_INVALID'
    ACTIVE_PACKAGE_MISMATCH = 'PHASE7_ACTIVE_PACKAGE_MISMATCH'
    BUDGET_EXHAUSTED = 'PHASE7_BUDGET_EXHAUSTED'
    GENERATOR_FAILED = 'PHASE7_GENERATOR_FAILED'
    GENERATOR_REPLAY_MISMATCH = 'PHASE7_GENERATOR_REPLAY_MISMATCH'
    PROPOSAL_INVALID = 'PHASE7_PROPOSAL_INVALID'
    SELECTION_FAILED = 'PHASE7_SELECTION_FAILED'
    REALIZATION_FAILED = 'PHASE7_REALIZATION_FAILED'
    EVALUATION_FAILED = 'PHASE7_EVALUATION_FAILED'
    CERTIFICATE_FAILED = 'PHASE7_CERTIFICATE_FAILED'
    LEAN_REJECTED = 'PHASE7_LEAN_REJECTED'
    CHECKER_REJECTED = 'PHASE7_CHECKER_REJECTED'
    CANDIDATE_MUTATED = 'PHASE7_CANDIDATE_MUTATED'
    MANUAL_REPAIR_DETECTED = 'PHASE7_MANUAL_REPAIR_DETECTED'
    PROMOTION_FAILED = 'PHASE7_PROMOTION_FAILED'
    ROLLBACK_FAILED = 'PHASE7_ROLLBACK_FAILED'
    LEDGER_FAILED = 'PHASE7_LEDGER_FAILED'
    INTERNAL_ERROR = 'PHASE7_INTERNAL_ERROR'

_ATTEMPT_STAGE_ORDER: Sequence[str] = ("generator", "proposal_validation", "selection", "realization", "objective_evaluation", "certificate_construction", "lean_bridge", "hardened_checker", "fallback_rollback")
def _parse_reason_array(value: object, path: str) -> Sequence[Phase7ReasonCode]:
    if not isinstance(value, list):
        raise SchemaValidationError(path, 'expected an array')
    reasons: list[Phase7ReasonCode] = []
    for index, item in enumerate(value):
        text = require_string(item, f'{path}[{index}]')
        try:
            reasons.append(Phase7ReasonCode(text))
        except ValueError as exc:
            raise SchemaValidationError(f'{path}[{index}]', f'unknown Phase 7 reason code: {text}') from exc
    return tuple(reasons)
def _parse_hash_map(value: object, path: str) -> FrozenHashMap:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, 'expected an object')
    mapping: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = require_string(raw_key, f'{path}.key')
        mapping[key] = _required_hash(raw_value, f'{path}.{key}')
    return FrozenHashMap.from_mapping(mapping, path)
def _required_hash(value: object, path: str) -> str:
    return validate_hash256(require_string(value, path), path)
def _optional_hash(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _required_hash(value, path)
def _required_bool(value: object, path: str) -> bool:
    _require_bool(value, path)
    return cast(bool, value)
def _require_bool(value: object, path: str) -> None:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, 'expected a Boolean')
def _literal(value: object, path: str, allowed: set[str]) -> str:
    text = require_string(value, path)
    if text not in allowed:
        raise SchemaValidationError(path, f'unsupported value: {text}')
    return text
def _require_exact(value: str, expected: str, path: str) -> None:
    if value != expected:
        raise SchemaValidationError(path, f'expected {expected}')

__all__ = [
    "PHASE7_STAGE_SCHEMA_ID",
    "PHASE7_POLICY_SCHEMA_ID",
    "PHASE7_BUDGET_SCHEMA_ID",
    "PHASE7_ATTEMPT_SCHEMA_ID",
    "PHASE7_PACKAGE_SCHEMA_ID",
    "PHASE7_LEDGER_SCHEMA_ID",
    "PHASE7_ACTIVE_POINTER_SCHEMA_ID",
    "PHASE7_CONTROLLER_REPORT_SCHEMA_ID",
    "StageStatus",
    "AttemptVerdict",
    "ControllerVerdict",
    "PackageStatus",
    "LedgerEvent",
    "Phase7ReasonCode",
    "_ATTEMPT_STAGE_ORDER",
    "_parse_reason_array",
    "_parse_hash_map",
    "_required_hash",
    "_optional_hash",
    "_required_bool",
    "_require_bool",
    "_literal",
    "_require_exact",
]
