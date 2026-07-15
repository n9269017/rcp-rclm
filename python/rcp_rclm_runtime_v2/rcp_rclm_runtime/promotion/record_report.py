from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal, cast
from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import FrozenJson, freeze_json, require_schema_id, require_string, require_structural_integer, strict_object, thaw_json
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.records import Phase6ResourceBudgetRecord
from rcp_rclm_runtime.promotion._record_common import *
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_package import Phase7ActivePointerRecord
from rcp_rclm_runtime.promotion.record_policy import Phase7ControllerBudgetRecord, Phase7ControllerPolicyRecord
@dataclass(frozen=True, slots=True)
class Phase7ControllerReport:
    run_id: str
    verdict: ControllerVerdict
    reason_codes: Sequence[Phase7ReasonCode]
    policy: Phase7ControllerPolicyRecord
    budget: Phase7ControllerBudgetRecord
    initial_pointer: Phase7ActivePointerRecord
    final_pointer: Phase7ActivePointerRecord
    attempts: Sequence[Phase7AttemptReport]
    units_consumed: int
    promoted_package_hash: str | None
    ledger_entry_hashes: Sequence[str]
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION
    schema_id: ClassVar[str] = PHASE7_CONTROLLER_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.run_id, 'phase7_controller_report.run_id')
        if self.verdict not in {'promoted', 'exhausted', 'indeterminate'}:
            raise SchemaValidationError('phase7_controller_report.verdict', 'unsupported controller verdict')
        reasons = tuple(self.reason_codes)
        attempts = tuple(self.attempts)
        ledger_hashes = tuple(self.ledger_entry_hashes)
        object.__setattr__(self, 'reason_codes', reasons)
        object.__setattr__(self, 'attempts', attempts)
        object.__setattr__(self, 'ledger_entry_hashes', ledger_hashes)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError('phase7_controller_report.reason_codes', 'reason codes must be unique')
        if self.verdict == 'promoted' and reasons:
            raise SchemaValidationError('phase7_controller_report.reason_codes', 'promoted run cannot contain failure reasons')
        if self.verdict != 'promoted' and (not reasons):
            raise SchemaValidationError('phase7_controller_report.reason_codes', 'nonpromoted run requires a reason')
        if isinstance(self.units_consumed, bool) or not isinstance(self.units_consumed, int) or self.units_consumed < 0:
            raise SchemaValidationError('phase7_controller_report.units_consumed', 'expected a nonnegative integer')
        if self.units_consumed > self.budget.max_attempt_units:
            raise SchemaValidationError('phase7_controller_report.units_consumed', 'controller exceeded its fixed attempt budget')
        expected_units = sum((attempt.controller_units_consumed for attempt in attempts))
        if self.units_consumed != expected_units:
            raise SchemaValidationError('phase7_controller_report.units_consumed', 'unit count does not match attempt reports')
        if len(attempts) > self.budget.max_attempts:
            raise SchemaValidationError('phase7_controller_report.attempts', 'attempt count exceeds the fixed budget')
        if len(ledger_hashes) != len(set(ledger_hashes)):
            raise SchemaValidationError('phase7_controller_report.ledger_entry_hashes', 'ledger entry hashes must be unique')
        for index, value in enumerate(ledger_hashes):
            validate_hash256(value, f'phase7_controller_report.ledger_entry_hashes[{index}]')
        if self.promoted_package_hash is not None:
            validate_hash256(self.promoted_package_hash, 'phase7_controller_report.promoted_package_hash')
        if self.policy.policy_hash != self.initial_pointer.controller_policy_hash:
            raise SchemaValidationError('phase7_controller_report.initial_pointer', 'initial pointer policy binding mismatch')
        if self.policy.policy_hash != self.final_pointer.controller_policy_hash:
            raise SchemaValidationError('phase7_controller_report.final_pointer', 'final pointer policy binding mismatch')
        accepted_attempts = [attempt for attempt in attempts if attempt.verdict == 'accept']
        if self.verdict == 'promoted':
            if len(accepted_attempts) != 1 or accepted_attempts[-1] != attempts[-1]:
                raise SchemaValidationError('phase7_controller_report.attempts', 'promotion requires exactly one final accepted attempt')
            if self.promoted_package_hash is None:
                raise SchemaValidationError('phase7_controller_report.promoted_package_hash', 'promoted run requires a package hash')
            if self.final_pointer.active_package_hash != self.promoted_package_hash:
                raise SchemaValidationError('phase7_controller_report.final_pointer', 'final pointer does not reference the promoted package')
            if self.initial_pointer.active_package_hash == self.final_pointer.active_package_hash:
                raise SchemaValidationError('phase7_controller_report.final_pointer', 'promotion must change the active package')
        else:
            if self.verdict == 'exhausted' and accepted_attempts:
                raise SchemaValidationError('phase7_controller_report', 'exhausted run cannot contain an accepted attempt')
            if len(accepted_attempts) > 1 or self.promoted_package_hash is not None:
                raise SchemaValidationError('phase7_controller_report', 'nonpromoted run cannot contain multiple acceptances or a promoted hash')
            if self.initial_pointer.active_package_hash != self.final_pointer.active_package_hash:
                raise SchemaValidationError('phase7_controller_report.final_pointer', 'nonpromoted run must preserve the active package')
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError('phase7_controller_report.contract_version', f'expected {CONTRACT_VERSION}')

    @property
    def promoted(self) -> bool:
        return self.verdict == 'promoted'

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_controller_report') -> Phase7ControllerReport:
        fields = {'schema_id', 'contract_version', 'run_id', 'verdict', 'promoted', 'reason_codes', 'policy', 'budget', 'initial_pointer', 'final_pointer', 'attempts', 'units_consumed', 'promoted_package_hash', 'ledger_entry_hashes', 'artifact_hashes', 'report_hash'}
        obj = strict_object(value, path, fields)
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        attempts_raw = obj['attempts']
        ledger_raw = obj['ledger_entry_hashes']
        if not isinstance(attempts_raw, list):
            raise SchemaValidationError(f'{path}.attempts', 'expected an array')
        if not isinstance(ledger_raw, list):
            raise SchemaValidationError(f'{path}.ledger_entry_hashes', 'expected an array')
        record = cls(run_id=require_string(obj['run_id'], f'{path}.run_id'), verdict=cast(ControllerVerdict, _literal(obj['verdict'], f'{path}.verdict', {'promoted', 'exhausted', 'indeterminate'})), reason_codes=_parse_reason_array(obj['reason_codes'], f'{path}.reason_codes'), policy=Phase7ControllerPolicyRecord.from_json(obj['policy'], f'{path}.policy'), budget=Phase7ControllerBudgetRecord.from_json(obj['budget'], f'{path}.budget'), initial_pointer=Phase7ActivePointerRecord.from_json(obj['initial_pointer'], f'{path}.initial_pointer'), final_pointer=Phase7ActivePointerRecord.from_json(obj['final_pointer'], f'{path}.final_pointer'), attempts=tuple((Phase7AttemptReport.from_json(item, f'{path}.attempts[{index}]') for index, item in enumerate(attempts_raw))), units_consumed=require_structural_integer(obj['units_consumed'], f'{path}.units_consumed', minimum=0), promoted_package_hash=_optional_hash(obj['promoted_package_hash'], f'{path}.promoted_package_hash'), ledger_entry_hashes=tuple((_required_hash(item, f'{path}.ledger_entry_hashes[{index}]') for index, item in enumerate(ledger_raw))), artifact_hashes=_parse_hash_map(obj['artifact_hashes'], f'{path}.artifact_hashes'), contract_version=require_string(obj['contract_version'], f'{path}.contract_version'))
        if _required_bool(obj['promoted'], f'{path}.promoted') != record.promoted:
            raise SchemaValidationError(f'{path}.promoted', 'promoted flag mismatch')
        if _required_hash(obj['report_hash'], f'{path}.report_hash') != record.report_hash:
            raise SchemaValidationError(f'{path}.report_hash', 'controller report hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'contract_version': self.contract_version, 'run_id': self.run_id, 'verdict': self.verdict, 'promoted': self.promoted, 'reason_codes': [reason.value for reason in self.reason_codes], 'policy': self.policy.to_json(), 'budget': self.budget.to_json(), 'initial_pointer': self.initial_pointer.to_json(), 'final_pointer': self.final_pointer.to_json(), 'attempts': [attempt.to_json() for attempt in self.attempts], 'units_consumed': self.units_consumed, 'promoted_package_hash': self.promoted_package_hash, 'ledger_entry_hashes': list(self.ledger_entry_hashes), 'artifact_hashes': self.artifact_hashes.to_json()}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['report_hash'] = self.report_hash
        return value
