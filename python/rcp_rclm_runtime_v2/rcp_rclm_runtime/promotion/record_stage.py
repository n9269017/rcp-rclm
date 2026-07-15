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
@dataclass(frozen=True, slots=True)
class Phase7StageResult:
    stage: str
    status: StageStatus
    reason_codes: Sequence[Phase7ReasonCode]
    evidence: FrozenJson
    schema_id: ClassVar[str] = PHASE7_STAGE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.stage, 'phase7_stage.stage')
        if self.status not in {'pass', 'fail', 'indeterminate', 'not_evaluated'}:
            raise SchemaValidationError('phase7_stage.status', 'unsupported stage status')
        reasons = tuple(self.reason_codes)
        object.__setattr__(self, 'reason_codes', reasons)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError('phase7_stage.reason_codes', 'reason codes must be unique')
        if self.status in {'pass', 'not_evaluated'} and reasons:
            raise SchemaValidationError('phase7_stage.reason_codes', 'passing and not-evaluated stages cannot contain reasons')
        if self.status in {'fail', 'indeterminate'} and (not reasons):
            raise SchemaValidationError('phase7_stage.reason_codes', 'failed and indeterminate stages require a reason')
        object.__setattr__(self, 'evidence', freeze_json(thaw_json(self.evidence)))

    @classmethod
    def build(cls, stage: str, status: StageStatus, reason_codes: Sequence[Phase7ReasonCode], evidence: object) -> Phase7StageResult:
        return cls(stage, status, tuple(reason_codes), freeze_json(evidence))

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(thaw_json(self.evidence))

    @classmethod
    def from_json(cls, value: object, path: str='phase7_stage') -> Phase7StageResult:
        obj = strict_object(value, path, {'schema_id', 'stage', 'status', 'reason_codes', 'evidence', 'evidence_hash'})
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        reasons = _parse_reason_array(obj['reason_codes'], f'{path}.reason_codes')
        status = _literal(obj['status'], f'{path}.status', {'pass', 'fail', 'indeterminate', 'not_evaluated'})
        record = cls(stage=require_string(obj['stage'], f'{path}.stage'), status=cast(StageStatus, status), reason_codes=reasons, evidence=freeze_json(obj['evidence'], f'{path}.evidence'))
        declared_hash = _required_hash(obj['evidence_hash'], f'{path}.evidence_hash')
        if declared_hash != record.evidence_hash:
            raise SchemaValidationError(f'{path}.evidence_hash', 'evidence hash mismatch')
        return record

    def to_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'stage': self.stage, 'status': self.status, 'reason_codes': [reason.value for reason in self.reason_codes], 'evidence': thaw_json(self.evidence), 'evidence_hash': self.evidence_hash}
