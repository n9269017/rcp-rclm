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
from rcp_rclm_runtime.promotion.record_stage import Phase7StageResult
@dataclass(frozen=True, slots=True)
class Phase7AttemptReport:
    run_id: str
    attempt_index: int
    transition_id: str
    verdict: AttemptVerdict
    reason_codes: Sequence[Phase7ReasonCode]
    controller_units_consumed: int
    active_pointer_hash_before: str
    active_pointer_hash_after: str
    generator_input_hash: str
    proposal_hash: str | None
    selection_hash: str | None
    phase6_report_hash: str | None
    candidate_package_tree_hash: str | None
    evaluation_hash: str | None
    certificate_hash: str | None
    lean_report_hash: str | None
    checker_report_hash: str | None
    fallback_rollback_verified: bool
    manual_repair_count: int
    stages: Sequence[Phase7StageResult]
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION
    schema_id: ClassVar[str] = PHASE7_ATTEMPT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.run_id, 'phase7_attempt.run_id')
        require_string(self.transition_id, 'phase7_attempt.transition_id')
        if isinstance(self.attempt_index, bool) or not isinstance(self.attempt_index, int) or self.attempt_index < 0:
            raise SchemaValidationError('phase7_attempt.attempt_index', 'expected a nonnegative integer')
        if isinstance(self.controller_units_consumed, bool) or not isinstance(self.controller_units_consumed, int) or self.controller_units_consumed < 1:
            raise SchemaValidationError('phase7_attempt.controller_units_consumed', 'expected a positive integer')
        if self.verdict not in {'accept', 'reject', 'indeterminate'}:
            raise SchemaValidationError('phase7_attempt.verdict', 'unsupported attempt verdict')
        reasons = tuple(self.reason_codes)
        object.__setattr__(self, 'reason_codes', reasons)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError('phase7_attempt.reason_codes', 'reason codes must be unique')
        if self.verdict == 'accept' and reasons:
            raise SchemaValidationError('phase7_attempt.reason_codes', 'accepted attempt cannot contain failure reasons')
        if self.verdict != 'accept' and (not reasons):
            raise SchemaValidationError('phase7_attempt.reason_codes', 'nonaccepting attempt requires a reason')
        for name, value in (('active_pointer_hash_before', self.active_pointer_hash_before), ('active_pointer_hash_after', self.active_pointer_hash_after), ('generator_input_hash', self.generator_input_hash)):
            validate_hash256(value, f'phase7_attempt.{name}')
        for name, value in (('proposal_hash', self.proposal_hash), ('selection_hash', self.selection_hash), ('phase6_report_hash', self.phase6_report_hash), ('candidate_package_tree_hash', self.candidate_package_tree_hash), ('evaluation_hash', self.evaluation_hash), ('certificate_hash', self.certificate_hash), ('lean_report_hash', self.lean_report_hash), ('checker_report_hash', self.checker_report_hash)):
            if value is not None:
                validate_hash256(value, f'phase7_attempt.{name}')
        _require_bool(self.fallback_rollback_verified, 'phase7_attempt.fallback_rollback_verified')
        if isinstance(self.manual_repair_count, bool) or not isinstance(self.manual_repair_count, int):
            raise SchemaValidationError('phase7_attempt.manual_repair_count', 'expected an integer')
        if self.manual_repair_count != 0:
            raise SchemaValidationError('phase7_attempt.manual_repair_count', 'manual repair is forbidden')
        stages = tuple(self.stages)
        object.__setattr__(self, 'stages', stages)
        stage_names = [stage.stage for stage in stages]
        if stage_names != list(_ATTEMPT_STAGE_ORDER):
            raise SchemaValidationError('phase7_attempt.stages', 'attempt stages must match the frozen controller order')
        if self.verdict == 'accept' and self.active_pointer_hash_before != self.active_pointer_hash_after:
            raise SchemaValidationError('phase7_attempt.active_pointer_hash_after', 'accepted candidate verification cannot mutate the active pointer')
        if self.verdict == 'accept' and (not self.fallback_rollback_verified):
            raise SchemaValidationError('phase7_attempt.fallback_rollback_verified', 'accepted attempt requires a verified fallback rollback path')
        if self.verdict == 'accept':
            required_hashes = (self.proposal_hash, self.selection_hash, self.phase6_report_hash, self.candidate_package_tree_hash, self.evaluation_hash, self.certificate_hash, self.lean_report_hash, self.checker_report_hash)
            if any((value is None for value in required_hashes)):
                raise SchemaValidationError('phase7_attempt', 'accepted attempt requires every verification artifact hash')
            if any((stage.status != 'pass' for stage in stages)):
                raise SchemaValidationError('phase7_attempt.stages', 'accepted attempt requires every stage to pass')
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError('phase7_attempt.contract_version', f'expected {CONTRACT_VERSION}')

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_attempt') -> Phase7AttemptReport:
        fields = {'schema_id', 'contract_version', 'run_id', 'attempt_index', 'transition_id', 'verdict', 'reason_codes', 'controller_units_consumed', 'active_pointer_hash_before', 'active_pointer_hash_after', 'generator_input_hash', 'proposal_hash', 'selection_hash', 'phase6_report_hash', 'candidate_package_tree_hash', 'evaluation_hash', 'certificate_hash', 'lean_report_hash', 'checker_report_hash', 'fallback_rollback_verified', 'manual_repair_count', 'stages', 'artifact_hashes', 'report_hash'}
        obj = strict_object(value, path, fields)
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        stages_raw = obj['stages']
        if not isinstance(stages_raw, list):
            raise SchemaValidationError(f'{path}.stages', 'expected an array')
        record = cls(run_id=require_string(obj['run_id'], f'{path}.run_id'), attempt_index=require_structural_integer(obj['attempt_index'], f'{path}.attempt_index', minimum=0), transition_id=require_string(obj['transition_id'], f'{path}.transition_id'), verdict=cast(AttemptVerdict, _literal(obj['verdict'], f'{path}.verdict', {'accept', 'reject', 'indeterminate'})), reason_codes=_parse_reason_array(obj['reason_codes'], f'{path}.reason_codes'), controller_units_consumed=require_structural_integer(obj['controller_units_consumed'], f'{path}.controller_units_consumed', minimum=1), active_pointer_hash_before=_required_hash(obj['active_pointer_hash_before'], f'{path}.active_pointer_hash_before'), active_pointer_hash_after=_required_hash(obj['active_pointer_hash_after'], f'{path}.active_pointer_hash_after'), generator_input_hash=_required_hash(obj['generator_input_hash'], f'{path}.generator_input_hash'), proposal_hash=_optional_hash(obj['proposal_hash'], f'{path}.proposal_hash'), selection_hash=_optional_hash(obj['selection_hash'], f'{path}.selection_hash'), phase6_report_hash=_optional_hash(obj['phase6_report_hash'], f'{path}.phase6_report_hash'), candidate_package_tree_hash=_optional_hash(obj['candidate_package_tree_hash'], f'{path}.candidate_package_tree_hash'), evaluation_hash=_optional_hash(obj['evaluation_hash'], f'{path}.evaluation_hash'), certificate_hash=_optional_hash(obj['certificate_hash'], f'{path}.certificate_hash'), lean_report_hash=_optional_hash(obj['lean_report_hash'], f'{path}.lean_report_hash'), checker_report_hash=_optional_hash(obj['checker_report_hash'], f'{path}.checker_report_hash'), fallback_rollback_verified=_required_bool(obj['fallback_rollback_verified'], f'{path}.fallback_rollback_verified'), manual_repair_count=require_structural_integer(obj['manual_repair_count'], f'{path}.manual_repair_count', minimum=0), stages=tuple((Phase7StageResult.from_json(item, f'{path}.stages[{index}]') for index, item in enumerate(stages_raw))), artifact_hashes=_parse_hash_map(obj['artifact_hashes'], f'{path}.artifact_hashes'), contract_version=require_string(obj['contract_version'], f'{path}.contract_version'))
        if _required_hash(obj['report_hash'], f'{path}.report_hash') != record.report_hash:
            raise SchemaValidationError(f'{path}.report_hash', 'attempt report hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'contract_version': self.contract_version, 'run_id': self.run_id, 'attempt_index': self.attempt_index, 'transition_id': self.transition_id, 'verdict': self.verdict, 'reason_codes': [reason.value for reason in self.reason_codes], 'controller_units_consumed': self.controller_units_consumed, 'active_pointer_hash_before': self.active_pointer_hash_before, 'active_pointer_hash_after': self.active_pointer_hash_after, 'generator_input_hash': self.generator_input_hash, 'proposal_hash': self.proposal_hash, 'selection_hash': self.selection_hash, 'phase6_report_hash': self.phase6_report_hash, 'candidate_package_tree_hash': self.candidate_package_tree_hash, 'evaluation_hash': self.evaluation_hash, 'certificate_hash': self.certificate_hash, 'lean_report_hash': self.lean_report_hash, 'checker_report_hash': self.checker_report_hash, 'fallback_rollback_verified': self.fallback_rollback_verified, 'manual_repair_count': self.manual_repair_count, 'stages': [stage.to_json() for stage in self.stages], 'artifact_hashes': self.artifact_hashes.to_json()}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['report_hash'] = self.report_hash
        return value
