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
class Phase7ControllerPolicyRecord:
    policy_id: str
    scope: Literal['gate_b_classical_reference']
    generator_backend: Literal['phase5a_reference_process']
    selector_backend: Literal['phase6_reference_selector']
    realizer_backend: Literal['phase6_isolated_realizer']
    evaluator_backend: Literal['phase3_reference_evaluator']
    checker_backend: Literal['phase4_hardened_checker']
    require_two_run_generator_replay: bool
    require_public_package_verification: bool
    require_lean_acceptance: bool
    require_checker_acceptance: bool
    allow_manual_repair: bool
    allow_candidate_mutation: bool
    contract_version: str = CONTRACT_VERSION
    schema_id: ClassVar[str] = PHASE7_POLICY_SCHEMA_ID

    def __post_init__(self) -> None:
        for name, value in (('policy_id', self.policy_id), ('scope', self.scope), ('generator_backend', self.generator_backend), ('selector_backend', self.selector_backend), ('realizer_backend', self.realizer_backend), ('evaluator_backend', self.evaluator_backend), ('checker_backend', self.checker_backend)):
            require_string(value, f'phase7_policy.{name}')
        _require_exact(self.scope, 'gate_b_classical_reference', 'phase7_policy.scope')
        _require_exact(self.generator_backend, 'phase5a_reference_process', 'phase7_policy.generator_backend')
        _require_exact(self.selector_backend, 'phase6_reference_selector', 'phase7_policy.selector_backend')
        _require_exact(self.realizer_backend, 'phase6_isolated_realizer', 'phase7_policy.realizer_backend')
        _require_exact(self.evaluator_backend, 'phase3_reference_evaluator', 'phase7_policy.evaluator_backend')
        _require_exact(self.checker_backend, 'phase4_hardened_checker', 'phase7_policy.checker_backend')
        for name in ('require_two_run_generator_replay', 'require_public_package_verification', 'require_lean_acceptance', 'require_checker_acceptance', 'allow_manual_repair', 'allow_candidate_mutation'):
            _require_bool(getattr(self, name), f'phase7_policy.{name}')
        if not self.require_two_run_generator_replay:
            raise SchemaValidationError('phase7_policy.require_two_run_generator_replay', 'two-run generator replay is mandatory')
        if not self.require_public_package_verification:
            raise SchemaValidationError('phase7_policy.require_public_package_verification', 'public package verification is mandatory')
        if not self.require_lean_acceptance or not self.require_checker_acceptance:
            raise SchemaValidationError('phase7_policy', 'Lean and hardened-checker acceptance are mandatory')
        if self.allow_manual_repair or self.allow_candidate_mutation:
            raise SchemaValidationError('phase7_policy', 'manual repair and candidate mutation are forbidden')
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError('phase7_policy.contract_version', f'expected {CONTRACT_VERSION}')

    @property
    def policy_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_policy') -> Phase7ControllerPolicyRecord:
        fields = {'schema_id', 'contract_version', 'policy_id', 'scope', 'generator_backend', 'selector_backend', 'realizer_backend', 'evaluator_backend', 'checker_backend', 'require_two_run_generator_replay', 'require_public_package_verification', 'require_lean_acceptance', 'require_checker_acceptance', 'allow_manual_repair', 'allow_candidate_mutation', 'policy_hash'}
        obj = strict_object(value, path, fields)
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        record = cls(policy_id=require_string(obj['policy_id'], f'{path}.policy_id'), scope=cast(Literal['gate_b_classical_reference'], _literal(obj['scope'], f'{path}.scope', {'gate_b_classical_reference'})), generator_backend=cast(Literal['phase5a_reference_process'], _literal(obj['generator_backend'], f'{path}.generator_backend', {'phase5a_reference_process'})), selector_backend=cast(Literal['phase6_reference_selector'], _literal(obj['selector_backend'], f'{path}.selector_backend', {'phase6_reference_selector'})), realizer_backend=cast(Literal['phase6_isolated_realizer'], _literal(obj['realizer_backend'], f'{path}.realizer_backend', {'phase6_isolated_realizer'})), evaluator_backend=cast(Literal['phase3_reference_evaluator'], _literal(obj['evaluator_backend'], f'{path}.evaluator_backend', {'phase3_reference_evaluator'})), checker_backend=cast(Literal['phase4_hardened_checker'], _literal(obj['checker_backend'], f'{path}.checker_backend', {'phase4_hardened_checker'})), require_two_run_generator_replay=_required_bool(obj['require_two_run_generator_replay'], f'{path}.require_two_run_generator_replay'), require_public_package_verification=_required_bool(obj['require_public_package_verification'], f'{path}.require_public_package_verification'), require_lean_acceptance=_required_bool(obj['require_lean_acceptance'], f'{path}.require_lean_acceptance'), require_checker_acceptance=_required_bool(obj['require_checker_acceptance'], f'{path}.require_checker_acceptance'), allow_manual_repair=_required_bool(obj['allow_manual_repair'], f'{path}.allow_manual_repair'), allow_candidate_mutation=_required_bool(obj['allow_candidate_mutation'], f'{path}.allow_candidate_mutation'), contract_version=require_string(obj['contract_version'], f'{path}.contract_version'))
        if _required_hash(obj['policy_hash'], f'{path}.policy_hash') != record.policy_hash:
            raise SchemaValidationError(f'{path}.policy_hash', 'policy hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'contract_version': self.contract_version, 'policy_id': self.policy_id, 'scope': self.scope, 'generator_backend': self.generator_backend, 'selector_backend': self.selector_backend, 'realizer_backend': self.realizer_backend, 'evaluator_backend': self.evaluator_backend, 'checker_backend': self.checker_backend, 'require_two_run_generator_replay': self.require_two_run_generator_replay, 'require_public_package_verification': self.require_public_package_verification, 'require_lean_acceptance': self.require_lean_acceptance, 'require_checker_acceptance': self.require_checker_acceptance, 'allow_manual_repair': self.allow_manual_repair, 'allow_candidate_mutation': self.allow_candidate_mutation}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['policy_hash'] = self.policy_hash
        return value
@dataclass(frozen=True, slots=True)
class Phase7ControllerBudgetRecord:
    max_attempts: int
    max_attempt_units: int
    attempt_unit_cost: int
    max_promotions: int
    phase6_budget: Phase6ResourceBudgetRecord
    schema_id: ClassVar[str] = PHASE7_BUDGET_SCHEMA_ID

    def __post_init__(self) -> None:
        for name, value in (('max_attempts', self.max_attempts), ('max_attempt_units', self.max_attempt_units), ('attempt_unit_cost', self.attempt_unit_cost), ('max_promotions', self.max_promotions)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise SchemaValidationError(f'phase7_budget.{name}', 'expected a positive integer')
        if self.max_attempt_units < self.attempt_unit_cost:
            raise SchemaValidationError('phase7_budget.max_attempt_units', 'budget must fund at least one attempt')
        if self.max_promotions != 1:
            raise SchemaValidationError('phase7_budget.max_promotions', 'one controller run may promote at most one package')

    @property
    def budget_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str='phase7_budget') -> Phase7ControllerBudgetRecord:
        obj = strict_object(value, path, {'schema_id', 'max_attempts', 'max_attempt_units', 'attempt_unit_cost', 'max_promotions', 'phase6_budget', 'budget_hash'})
        require_schema_id(obj['schema_id'], f'{path}.schema_id', cls.schema_id)
        record = cls(max_attempts=require_structural_integer(obj['max_attempts'], f'{path}.max_attempts', minimum=1), max_attempt_units=require_structural_integer(obj['max_attempt_units'], f'{path}.max_attempt_units', minimum=1), attempt_unit_cost=require_structural_integer(obj['attempt_unit_cost'], f'{path}.attempt_unit_cost', minimum=1), max_promotions=require_structural_integer(obj['max_promotions'], f'{path}.max_promotions', minimum=1), phase6_budget=Phase6ResourceBudgetRecord.from_json(obj['phase6_budget'], f'{path}.phase6_budget'))
        if _required_hash(obj['budget_hash'], f'{path}.budget_hash') != record.budget_hash:
            raise SchemaValidationError(f'{path}.budget_hash', 'budget hash mismatch')
        return record

    def _content_json(self) -> dict[str, object]:
        return {'schema_id': self.schema_id, 'max_attempts': self.max_attempts, 'max_attempt_units': self.max_attempt_units, 'attempt_unit_cost': self.attempt_unit_cost, 'max_promotions': self.max_promotions, 'phase6_budget': self.phase6_budget.to_json()}

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value['budget_hash'] = self.budget_hash
        return value
