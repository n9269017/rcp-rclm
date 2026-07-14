from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final, Literal, TypeAlias

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.schema._common import FrozenJson, freeze_json, require_string, thaw_json
from rcp_rclm_runtime.schema.verdict import FrozenHashMap, ReasonCode
from rcp_rclm_runtime.checker.policy import CheckerScope

COMPONENT_RESULT_SCHEMA_ID: Final[str] = "runtime.phase3_component_result.v2"
RESIDUAL_RESULT_SCHEMA_ID: Final[str] = "runtime.phase3_residual_result.v2"
METRIC_BOUNDS_SCHEMA_ID: Final[str] = "runtime.phase3_metric_bounds.v2"
CHECKER_REPORT_SCHEMA_ID: Final[str] = "runtime.phase3_checker_report.v2"

GateStatus: TypeAlias = Literal["pass", "fail", "indeterminate", "not_evaluated"]
ResidualIndex: TypeAlias = Literal["typed", "packet"]


@dataclass(frozen=True, slots=True)
class ComponentResultRecord:
    status: GateStatus
    reason_codes: Sequence[ReasonCode]
    evidence: FrozenJson

    schema_id: ClassVar[str] = COMPONENT_RESULT_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "evidence", freeze_json(thaw_json(self.evidence)))
        if self.status not in {"pass", "fail", "indeterminate", "not_evaluated"}:
            raise SchemaValidationError(
                "component_result.status",
                f"unsupported component status: {self.status}",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "component_result.reason_codes",
                "reason codes must be unique",
            )
        if self.status == "pass" and self.reason_codes:
            raise SchemaValidationError(
                "component_result.reason_codes",
                "passing component cannot contain failure reasons",
            )
        if self.status in {"fail", "indeterminate"} and not self.reason_codes:
            raise SchemaValidationError(
                "component_result.reason_codes",
                "nonpassing evaluated component requires a reason code",
            )
        if self.status == "not_evaluated" and self.reason_codes:
            raise SchemaValidationError(
                "component_result.reason_codes",
                "not-evaluated component cannot contain reason codes",
            )

    @classmethod
    def from_evidence(
        cls,
        status: GateStatus,
        reason_codes: Sequence[ReasonCode],
        evidence: object,
    ) -> ComponentResultRecord:
        return cls(status, tuple(reason_codes), freeze_json(evidence))

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "status": self.status,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "evidence": thaw_json(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class ResidualResultRecord:
    index: ResidualIndex
    value: Rational
    upper_nonpositive: bool

    schema_id: ClassVar[str] = RESIDUAL_RESULT_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.index not in {"typed", "packet"}:
            raise SchemaValidationError(
                "residual_result.index",
                f"unsupported residual index: {self.index}",
            )
        if not isinstance(self.upper_nonpositive, bool):
            raise SchemaValidationError(
                "residual_result.upper_nonpositive",
                "expected a Boolean",
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "index": self.index,
            "value": self.value.to_json(),
            "upper_nonpositive": self.upper_nonpositive,
        }


@dataclass(frozen=True, slots=True)
class MetricBoundsRecord:
    scope: CheckerScope
    gap: IntervalEvidence
    entropy_before: IntervalEvidence
    entropy_after: IntervalEvidence
    entropy_target: IntervalEvidence
    divergence_before: IntervalEvidence
    divergence_after: IntervalEvidence
    progress_before: IntervalEvidence
    progress_after: IntervalEvidence
    progress_delta: IntervalEvidence

    schema_id: ClassVar[str] = METRIC_BOUNDS_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.scope not in {"gate_b_classical", "gate_c_diagonal_quantum"}:
            raise SchemaValidationError(
                "metric_bounds.scope",
                f"unsupported scope: {self.scope}",
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "scope": self.scope,
            "gap": self.gap.to_json(),
            "entropy_before": self.entropy_before.to_json(),
            "entropy_after": self.entropy_after.to_json(),
            "entropy_target": self.entropy_target.to_json(),
            "divergence_before": self.divergence_before.to_json(),
            "divergence_after": self.divergence_after.to_json(),
            "progress_before": self.progress_before.to_json(),
            "progress_after": self.progress_after.to_json(),
            "progress_delta": self.progress_delta.to_json(),
        }


@dataclass(frozen=True, slots=True)
class Phase3CheckerReport:
    transition_id: str
    verdict: Literal["accept", "reject", "indeterminate"]
    reason_codes: Sequence[ReasonCode]
    structural_result: ComponentResultRecord
    typed_successor_result: ComponentResultRecord
    computed_residuals: Sequence[ResidualResultRecord]
    residual_result: ComponentResultRecord
    metric_bounds: MetricBoundsRecord | None
    evaluation_result: ComponentResultRecord
    protected_nonloss_result: ComponentResultRecord
    recovery_result: ComponentResultRecord
    progress_result: ComponentResultRecord
    strict_witness_result: ComponentResultRecord
    trust_result: ComponentResultRecord
    resource_result: ComponentResultRecord
    domain_result: ComponentResultRecord
    refinement_result: ComponentResultRecord
    monitor_result: ComponentResultRecord
    lean_bridge_result: ComponentResultRecord
    artifact_hashes: FrozenHashMap
    checker_policy_hash: str
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = CHECKER_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "checker_report.transition_id")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "computed_residuals", tuple(self.computed_residuals))
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(
                "checker_report.verdict",
                f"unsupported verdict: {self.verdict}",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "checker_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "checker_report.reason_codes",
                "reason codes must be unique",
            )
        if self.verdict == "accept" and self.reason_codes:
            raise SchemaValidationError(
                "checker_report.reason_codes",
                "accept verdict cannot contain failure reasons",
            )
        if self.verdict != "accept" and not self.reason_codes:
            raise SchemaValidationError(
                "checker_report.reason_codes",
                "nonaccepting verdict requires a reason code",
            )
        validate_hash256(
            self.checker_policy_hash,
            "checker_report.checker_policy_hash",
        )

    @property
    def accepted(self) -> bool:
        return self.verdict == "accept"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "verdict": self.verdict,
            "accepted": self.accepted,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "structural_result": self.structural_result.to_json(),
            "typed_successor_result": self.typed_successor_result.to_json(),
            "computed_residuals": [
                item.to_json() for item in self.computed_residuals
            ],
            "residual_result": self.residual_result.to_json(),
            "metric_bounds": (
                None if self.metric_bounds is None else self.metric_bounds.to_json()
            ),
            "evaluation_result": self.evaluation_result.to_json(),
            "protected_nonloss_result": self.protected_nonloss_result.to_json(),
            "recovery_result": self.recovery_result.to_json(),
            "progress_result": self.progress_result.to_json(),
            "strict_witness_result": self.strict_witness_result.to_json(),
            "trust_result": self.trust_result.to_json(),
            "resource_result": self.resource_result.to_json(),
            "domain_result": self.domain_result.to_json(),
            "refinement_result": self.refinement_result.to_json(),
            "monitor_result": self.monitor_result.to_json(),
            "lean_bridge_result": self.lean_bridge_result.to_json(),
            "artifact_hashes": self.artifact_hashes.to_json(),
            "checker_policy_hash": self.checker_policy_hash,
        }
