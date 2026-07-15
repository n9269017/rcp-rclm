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
class Phase7ImmutablePackageManifestRecord:
    package_id: str
    status: PackageStatus
    parent_package_hash: str | None
    predecessor_package_tree_hash: str
    predecessor_manifest_hash: str
    predecessor_payload_tree_hash: str
    state_hash: str
    source_candidate_package_tree_hash: str | None
    source_candidate_manifest_hash: str | None
    source_candidate_payload_tree_hash: str | None
    evidence_tree_hash: str
    accepted_attempt_report_hash: str | None
    controller_policy_hash: str
    substantive_component_kinds: Sequence[str]
    contract_version: str = CONTRACT_VERSION
    schema_id: ClassVar[str] = PHASE7_PACKAGE_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.package_id, 'phase7_package.package_id')
        if self.status not in {'root', 'promoted'}:
            raise SchemaValidationError('phase7_package.status', 'unsupported package status')
        if self.parent_package_hash is not None:
            validate_hash256(self.parent_package_hash, 'phase7_package.parent_package_hash')
        for name, value in (('predecessor_package_tree_hash', self.predecessor_package_tree_hash), ('predecessor_manifest_hash', self.predecessor_manifest_hash), ('predecessor_payload_tree_hash', self.predecessor_payload_tree_hash), ('state_hash', self.state_hash), ('evidence_tree_hash', self.evidence_tree_hash), ('controller_policy_hash', self.controller_policy_hash)):
            validate_hash256(value, f'phase7_package.{name}')
        for name, value in (('source_candidate_package_tree_hash', self.source_candidate_package_tree_hash), ('source_candidate_manifest_hash', self.source_candidate_manifest_hash), ('source_candidate_payload_tree_hash', self.source_candidate_payload_tree_hash), ('accepted_attempt_report_hash', self.accepted_attempt_report_hash)):
            if value is not None:
                validate_hash256(value, f'phase7_package.{name}')
        components = tuple(self.substantive_component_kinds)
        object.__setattr__(self, 'substantive_component_kinds', components)
        if components != tuple(sorted(set(components))):
            raise SchemaValidationError('phase7_package.substantive_component_kinds', 'component kinds must be unique and sorted')
        candidate_values = (self.source_candidate_package_tree_hash, self.source_candidate_manifest_hash, self.source_candidate_payload_tree_hash, self.accepted_attempt_report_hash)
        if self.status == 'root':
            if self.parent_package_hash is not None or any((value is not None for value in candidate_values)):
                raise SchemaValidationError('phase7_package', 'root package cannot contain parent or promotion bindings')
            if components:
                raise SchemaValidationError('phase7_package.substantive_component_kinds', 'root package has no promoted component')
        else:
            if self.parent_package_hash is None or any((value is None for value in candidate_values)):
                raise SchemaValidationError('phase7_package', 'promoted package requires parent, candidate, and accepted-attempt bindings')
            if not components:
                raise SchemaValidationError('phase7_package.substantive_component_kinds', 'promoted package requires a substantive component')
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError('phase7_package.contract_version', f'expected {CONTRACT_VERSION}')

    @property
    def package_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_package') -> Phase7ImmutablePackageManifestRecord:
        fields = {'schema_id', 'contract_version', 'package_id', 'status', 'parent_package_hash', 'predecessor_package_tree_hash', 'predecessor_manifest_hash', 'predecessor_payload_tree_hash', 'state_hash', 'source_candidate_package_tree_hash', 'source_candidate_manifest_hash', 'source_candidate_payload_tree_hash', 'evidence_tree_hash', 'accepted_attempt_report_hash', 'controller_policy_hash', 'substantive_component_kinds', 'package_hash'}
        obj = strict_object(value, path, fields)
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        components_raw = obj['substantive_component_kinds']
        if not isinstance(components_raw, list):
            raise SchemaValidationError(f'{path}.substantive_component_kinds', 'expected an array')
        record = cls(package_id=require_string(obj['package_id'], f'{path}.package_id'), status=cast(PackageStatus, _literal(obj['status'], f'{path}.status', {'root', 'promoted'})), parent_package_hash=_optional_hash(obj['parent_package_hash'], f'{path}.parent_package_hash'), predecessor_package_tree_hash=_required_hash(obj['predecessor_package_tree_hash'], f'{path}.predecessor_package_tree_hash'), predecessor_manifest_hash=_required_hash(obj['predecessor_manifest_hash'], f'{path}.predecessor_manifest_hash'), predecessor_payload_tree_hash=_required_hash(obj['predecessor_payload_tree_hash'], f'{path}.predecessor_payload_tree_hash'), state_hash=_required_hash(obj['state_hash'], f'{path}.state_hash'), source_candidate_package_tree_hash=_optional_hash(obj['source_candidate_package_tree_hash'], f'{path}.source_candidate_package_tree_hash'), source_candidate_manifest_hash=_optional_hash(obj['source_candidate_manifest_hash'], f'{path}.source_candidate_manifest_hash'), source_candidate_payload_tree_hash=_optional_hash(obj['source_candidate_payload_tree_hash'], f'{path}.source_candidate_payload_tree_hash'), evidence_tree_hash=_required_hash(obj['evidence_tree_hash'], f'{path}.evidence_tree_hash'), accepted_attempt_report_hash=_optional_hash(obj['accepted_attempt_report_hash'], f'{path}.accepted_attempt_report_hash'), controller_policy_hash=_required_hash(obj['controller_policy_hash'], f'{path}.controller_policy_hash'), substantive_component_kinds=tuple((require_string(item, f'{path}.substantive_component_kinds[{index}]') for index, item in enumerate(components_raw))), contract_version=require_string(obj['contract_version'], f'{path}.contract_version'))
        if _required_hash(obj['package_hash'], f'{path}.package_hash') != record.package_hash:
            raise SchemaValidationError(f'{path}.package_hash', 'package hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'contract_version': self.contract_version, 'package_id': self.package_id, 'status': self.status, 'parent_package_hash': self.parent_package_hash, 'predecessor_package_tree_hash': self.predecessor_package_tree_hash, 'predecessor_manifest_hash': self.predecessor_manifest_hash, 'predecessor_payload_tree_hash': self.predecessor_payload_tree_hash, 'state_hash': self.state_hash, 'source_candidate_package_tree_hash': self.source_candidate_package_tree_hash, 'source_candidate_manifest_hash': self.source_candidate_manifest_hash, 'source_candidate_payload_tree_hash': self.source_candidate_payload_tree_hash, 'evidence_tree_hash': self.evidence_tree_hash, 'accepted_attempt_report_hash': self.accepted_attempt_report_hash, 'controller_policy_hash': self.controller_policy_hash, 'substantive_component_kinds': list(self.substantive_component_kinds)}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['package_hash'] = self.package_hash
        return value
@dataclass(frozen=True, slots=True)
class Phase7LedgerEntryRecord:
    sequence_number: int
    event: LedgerEvent
    previous_entry_hash: str | None
    active_package_hash_before: str
    active_package_hash_after: str
    attempt_report_hash: str | None
    controller_policy_hash: str
    run_id: str
    reason_codes: Sequence[Phase7ReasonCode]
    contract_version: str = CONTRACT_VERSION
    schema_id: ClassVar[str] = PHASE7_LEDGER_SCHEMA_ID

    def __post_init__(self) -> None:
        if isinstance(self.sequence_number, bool) or not isinstance(self.sequence_number, int) or self.sequence_number < 0:
            raise SchemaValidationError('phase7_ledger.sequence_number', 'expected a nonnegative integer')
        if self.event not in {'bootstrap', 'promotion', 'rejection', 'indeterminate'}:
            raise SchemaValidationError('phase7_ledger.event', 'unsupported ledger event')
        if self.previous_entry_hash is not None:
            validate_hash256(self.previous_entry_hash, 'phase7_ledger.previous_entry_hash')
        validate_hash256(self.active_package_hash_before, 'phase7_ledger.active_package_hash_before')
        validate_hash256(self.active_package_hash_after, 'phase7_ledger.active_package_hash_after')
        if self.attempt_report_hash is not None:
            validate_hash256(self.attempt_report_hash, 'phase7_ledger.attempt_report_hash')
        validate_hash256(self.controller_policy_hash, 'phase7_ledger.controller_policy_hash')
        require_string(self.run_id, 'phase7_ledger.run_id')
        reasons = tuple(self.reason_codes)
        object.__setattr__(self, 'reason_codes', reasons)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError('phase7_ledger.reason_codes', 'reason codes must be unique')
        if self.event == 'bootstrap':
            if self.sequence_number != 0 or self.previous_entry_hash is not None:
                raise SchemaValidationError('phase7_ledger', 'bootstrap entry must start the ledger')
            if self.attempt_report_hash is not None or reasons:
                raise SchemaValidationError('phase7_ledger', 'bootstrap entry cannot contain attempt or rejection evidence')
        else:
            if self.sequence_number < 1 or self.previous_entry_hash is None:
                raise SchemaValidationError('phase7_ledger', 'non-bootstrap entry requires a predecessor ledger entry')
            if self.attempt_report_hash is None:
                raise SchemaValidationError('phase7_ledger.attempt_report_hash', 'controller event requires an attempt report')
        if self.event == 'promotion':
            if self.active_package_hash_before == self.active_package_hash_after:
                raise SchemaValidationError('phase7_ledger.active_package_hash_after', 'promotion must change the active package hash')
            if reasons:
                raise SchemaValidationError('phase7_ledger.reason_codes', 'promotion cannot contain failure reasons')
        if self.event in {'rejection', 'indeterminate'}:
            if self.active_package_hash_before != self.active_package_hash_after:
                raise SchemaValidationError('phase7_ledger.active_package_hash_after', 'nonpromotion event must preserve the active package')
            if not reasons:
                raise SchemaValidationError('phase7_ledger.reason_codes', 'nonpromotion event requires a reason')
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError('phase7_ledger.contract_version', f'expected {CONTRACT_VERSION}')

    @property
    def entry_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_ledger') -> Phase7LedgerEntryRecord:
        fields = {'schema_id', 'contract_version', 'sequence_number', 'event', 'previous_entry_hash', 'active_package_hash_before', 'active_package_hash_after', 'attempt_report_hash', 'controller_policy_hash', 'run_id', 'reason_codes', 'entry_hash'}
        obj = strict_object(value, path, fields)
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        record = cls(sequence_number=require_structural_integer(obj['sequence_number'], f'{path}.sequence_number', minimum=0), event=cast(LedgerEvent, _literal(obj['event'], f'{path}.event', {'bootstrap', 'promotion', 'rejection', 'indeterminate'})), previous_entry_hash=_optional_hash(obj['previous_entry_hash'], f'{path}.previous_entry_hash'), active_package_hash_before=_required_hash(obj['active_package_hash_before'], f'{path}.active_package_hash_before'), active_package_hash_after=_required_hash(obj['active_package_hash_after'], f'{path}.active_package_hash_after'), attempt_report_hash=_optional_hash(obj['attempt_report_hash'], f'{path}.attempt_report_hash'), controller_policy_hash=_required_hash(obj['controller_policy_hash'], f'{path}.controller_policy_hash'), run_id=require_string(obj['run_id'], f'{path}.run_id'), reason_codes=_parse_reason_array(obj['reason_codes'], f'{path}.reason_codes'), contract_version=require_string(obj['contract_version'], f'{path}.contract_version'))
        if _required_hash(obj['entry_hash'], f'{path}.entry_hash') != record.entry_hash:
            raise SchemaValidationError(f'{path}.entry_hash', 'ledger entry hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'contract_version': self.contract_version, 'sequence_number': self.sequence_number, 'event': self.event, 'previous_entry_hash': self.previous_entry_hash, 'active_package_hash_before': self.active_package_hash_before, 'active_package_hash_after': self.active_package_hash_after, 'attempt_report_hash': self.attempt_report_hash, 'controller_policy_hash': self.controller_policy_hash, 'run_id': self.run_id, 'reason_codes': [reason.value for reason in self.reason_codes]}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['entry_hash'] = self.entry_hash
        return value
@dataclass(frozen=True, slots=True)
class Phase7ActivePointerRecord:
    active_package_hash: str
    active_package_id: str
    predecessor_manifest_hash: str
    predecessor_payload_tree_hash: str
    state_hash: str
    ledger_head_hash: str
    ledger_sequence_number: int
    controller_policy_hash: str
    contract_version: str = CONTRACT_VERSION
    schema_id: ClassVar[str] = PHASE7_ACTIVE_POINTER_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.active_package_id, 'phase7_active_pointer.active_package_id')
        for name, value in (('active_package_hash', self.active_package_hash), ('predecessor_manifest_hash', self.predecessor_manifest_hash), ('predecessor_payload_tree_hash', self.predecessor_payload_tree_hash), ('state_hash', self.state_hash), ('ledger_head_hash', self.ledger_head_hash), ('controller_policy_hash', self.controller_policy_hash)):
            validate_hash256(value, f'phase7_active_pointer.{name}')
        if isinstance(self.ledger_sequence_number, bool) or not isinstance(self.ledger_sequence_number, int) or self.ledger_sequence_number < 0:
            raise SchemaValidationError('phase7_active_pointer.ledger_sequence_number', 'expected a nonnegative integer')
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError('phase7_active_pointer.contract_version', f'expected {CONTRACT_VERSION}')

    @property
    def pointer_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_active_pointer') -> Phase7ActivePointerRecord:
        fields = {'schema_id', 'contract_version', 'active_package_hash', 'active_package_id', 'predecessor_manifest_hash', 'predecessor_payload_tree_hash', 'state_hash', 'ledger_head_hash', 'ledger_sequence_number', 'controller_policy_hash', 'pointer_hash'}
        obj = strict_object(value, path, fields)
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        record = cls(active_package_hash=_required_hash(obj['active_package_hash'], f'{path}.active_package_hash'), active_package_id=require_string(obj['active_package_id'], f'{path}.active_package_id'), predecessor_manifest_hash=_required_hash(obj['predecessor_manifest_hash'], f'{path}.predecessor_manifest_hash'), predecessor_payload_tree_hash=_required_hash(obj['predecessor_payload_tree_hash'], f'{path}.predecessor_payload_tree_hash'), state_hash=_required_hash(obj['state_hash'], f'{path}.state_hash'), ledger_head_hash=_required_hash(obj['ledger_head_hash'], f'{path}.ledger_head_hash'), ledger_sequence_number=require_structural_integer(obj['ledger_sequence_number'], f'{path}.ledger_sequence_number', minimum=0), controller_policy_hash=_required_hash(obj['controller_policy_hash'], f'{path}.controller_policy_hash'), contract_version=require_string(obj['contract_version'], f'{path}.contract_version'))
        if _required_hash(obj['pointer_hash'], f'{path}.pointer_hash') != record.pointer_hash:
            raise SchemaValidationError(f'{path}.pointer_hash', 'active-pointer hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'contract_version': self.contract_version, 'active_package_hash': self.active_package_hash, 'active_package_id': self.active_package_id, 'predecessor_manifest_hash': self.predecessor_manifest_hash, 'predecessor_payload_tree_hash': self.predecessor_payload_tree_hash, 'state_hash': self.state_hash, 'ledger_head_hash': self.ledger_head_hash, 'ledger_sequence_number': self.ledger_sequence_number, 'controller_policy_hash': self.controller_policy_hash}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['pointer_hash'] = self.pointer_hash
        return value
