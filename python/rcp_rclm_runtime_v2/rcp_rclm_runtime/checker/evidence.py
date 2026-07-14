from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Final, Literal, TypeAlias

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationReport
from rcp_rclm_runtime.mathematics.classical import DistributionRecord
from rcp_rclm_runtime.mathematics.diagonal_quantum import DiagonalDensityRecord
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema._common import (
    FrozenJson,
    freeze_json,
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
    thaw_json,
)
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.schema.verdict import (
    FrozenHashMap,
    LeanVerifierReportRecord,
    ReasonCode,
)
from rcp_rclm_runtime.checker.policy import (
    CheckerScope,
    ProtectedDistinctionName,
)

TRUST_ANCHOR_SCHEMA_ID: Final[str] = "runtime.phase3_trust_anchor.v2"
RESOURCE_RECORD_SCHEMA_ID: Final[str] = "runtime.phase3_resource_record.v2"
PROTECTED_DISTINCTION_SCHEMA_ID: Final[str] = "runtime.phase3_protected_distinction.v2"
EVALUATION_EVIDENCE_SCHEMA_ID: Final[str] = "runtime.phase3_evaluation_evidence.v2"
CHECKER_REQUEST_SCHEMA_ID: Final[str] = "runtime.phase3_checker_request.v2"
COMPONENT_RESULT_SCHEMA_ID: Final[str] = "runtime.phase3_component_result.v2"
RESIDUAL_RESULT_SCHEMA_ID: Final[str] = "runtime.phase3_residual_result.v2"
METRIC_BOUNDS_SCHEMA_ID: Final[str] = "runtime.phase3_metric_bounds.v2"
CHECKER_REPORT_SCHEMA_ID: Final[str] = "runtime.phase3_checker_report.v2"

_COMMIT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
GateStatus: TypeAlias = Literal["pass", "fail", "indeterminate", "not_evaluated"]
ResidualIndex: TypeAlias = Literal["typed", "packet"]
ObservationRecord: TypeAlias = DistributionRecord | DiagonalDensityRecord


@dataclass(frozen=True, slots=True)
class TrustAnchorRecord:
    formal_source_commit: str
    lean_toolchain: str
    mathlib_commit: str
    formal_manifest_blob: str
    gate_c_audit_sha256: str
    checker_policy_hash: str
    lean_verifier_policy_hash: str
    claim_boundary_hash: str

    schema_id: ClassVar[str] = TRUST_ANCHOR_SCHEMA_ID

    def __post_init__(self) -> None:
        for field_name in ("formal_source_commit", "mathlib_commit", "formal_manifest_blob"):
            value = getattr(self, field_name)
            if _COMMIT_PATTERN.fullmatch(value) is None:
                raise SchemaValidationError(
                    f"trust_anchor.{field_name}",
                    "expected a lowercase 40-character Git object ID",
                )
        require_string(self.lean_toolchain, "trust_anchor.lean_toolchain")
        validate_hash256(self.gate_c_audit_sha256, "trust_anchor.gate_c_audit_sha256")
        for field_name in (
            "checker_policy_hash",
            "lean_verifier_policy_hash",
            "claim_boundary_hash",
        ):
            validate_hash256(getattr(self, field_name), f"trust_anchor.{field_name}")

    @classmethod
    def from_json(cls, value: object, path: str = "trust_anchor") -> TrustAnchorRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "formal_source_commit",
                "lean_toolchain",
                "mathlib_commit",
                "formal_manifest_blob",
                "gate_c_audit_sha256",
                "checker_policy_hash",
                "lean_verifier_policy_hash",
                "claim_boundary_hash",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            formal_source_commit=require_string(
                obj["formal_source_commit"], f"{path}.formal_source_commit"
            ),
            lean_toolchain=require_string(obj["lean_toolchain"], f"{path}.lean_toolchain"),
            mathlib_commit=require_string(obj["mathlib_commit"], f"{path}.mathlib_commit"),
            formal_manifest_blob=require_string(
                obj["formal_manifest_blob"], f"{path}.formal_manifest_blob"
            ),
            gate_c_audit_sha256=require_string(
                obj["gate_c_audit_sha256"], f"{path}.gate_c_audit_sha256"
            ),
            checker_policy_hash=require_string(
                obj["checker_policy_hash"], f"{path}.checker_policy_hash"
            ),
            lean_verifier_policy_hash=require_string(
                obj["lean_verifier_policy_hash"], f"{path}.lean_verifier_policy_hash"
            ),
            claim_boundary_hash=require_string(
                obj["claim_boundary_hash"], f"{path}.claim_boundary_hash"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "formal_source_commit": self.formal_source_commit,
            "lean_toolchain": self.lean_toolchain,
            "mathlib_commit": self.mathlib_commit,
            "formal_manifest_blob": self.formal_manifest_blob,
            "gate_c_audit_sha256": self.gate_c_audit_sha256,
            "checker_policy_hash": self.checker_policy_hash,
            "lean_verifier_policy_hash": self.lean_verifier_policy_hash,
            "claim_boundary_hash": self.claim_boundary_hash,
        }


@dataclass(frozen=True, slots=True)
class ResourceRecord:
    budget_units: int
    consumed_units: int
    precision_bits: int
    model_invocations: int
    network_requests: int
    predecessor_write_attempts: int
    candidate_write_attempts: int
    checker_source_write_attempts: int
    manual_repair_count: int
    hidden_oracle_reads: int
    environment_hash: str
    meter_policy_hash: str

    schema_id: ClassVar[str] = RESOURCE_RECORD_SCHEMA_ID

    def __post_init__(self) -> None:
        for field_name in (
            "budget_units",
            "consumed_units",
            "precision_bits",
            "model_invocations",
            "network_requests",
            "predecessor_write_attempts",
            "candidate_write_attempts",
            "checker_source_write_attempts",
            "manual_repair_count",
            "hidden_oracle_reads",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchemaValidationError(
                    f"resource_record.{field_name}",
                    "expected a nonnegative integer",
                )
        if self.precision_bits < 128 or self.precision_bits > 4096:
            raise SchemaValidationError(
                "resource_record.precision_bits",
                "precision_bits must be between 128 and 4096",
            )
        validate_hash256(self.environment_hash, "resource_record.environment_hash")
        validate_hash256(self.meter_policy_hash, "resource_record.meter_policy_hash")

    @classmethod
    def from_json(cls, value: object, path: str = "resource_record") -> ResourceRecord:
        fields = {
            "schema_id",
            "budget_units",
            "consumed_units",
            "precision_bits",
            "model_invocations",
            "network_requests",
            "predecessor_write_attempts",
            "candidate_write_attempts",
            "checker_source_write_attempts",
            "manual_repair_count",
            "hidden_oracle_reads",
            "environment_hash",
            "meter_policy_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        integer_fields = {
            name: require_structural_integer(obj[name], f"{path}.{name}", minimum=0)
            for name in fields
            if name
            not in {
                "schema_id",
                "environment_hash",
                "meter_policy_hash",
            }
        }
        return cls(
            budget_units=integer_fields["budget_units"],
            consumed_units=integer_fields["consumed_units"],
            precision_bits=integer_fields["precision_bits"],
            model_invocations=integer_fields["model_invocations"],
            network_requests=integer_fields["network_requests"],
            predecessor_write_attempts=integer_fields["predecessor_write_attempts"],
            candidate_write_attempts=integer_fields["candidate_write_attempts"],
            checker_source_write_attempts=integer_fields["checker_source_write_attempts"],
            manual_repair_count=integer_fields["manual_repair_count"],
            hidden_oracle_reads=integer_fields["hidden_oracle_reads"],
            environment_hash=require_string(
                obj["environment_hash"], f"{path}.environment_hash"
            ),
            meter_policy_hash=require_string(
                obj["meter_policy_hash"], f"{path}.meter_policy_hash"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "budget_units": self.budget_units,
            "consumed_units": self.consumed_units,
            "precision_bits": self.precision_bits,
            "model_invocations": self.model_invocations,
            "network_requests": self.network_requests,
            "predecessor_write_attempts": self.predecessor_write_attempts,
            "candidate_write_attempts": self.candidate_write_attempts,
            "checker_source_write_attempts": self.checker_source_write_attempts,
            "manual_repair_count": self.manual_repair_count,
            "hidden_oracle_reads": self.hidden_oracle_reads,
            "environment_hash": self.environment_hash,
            "meter_policy_hash": self.meter_policy_hash,
        }


@dataclass(frozen=True, slots=True)
class ProtectedDistinctionRecord:
    distinction_id: ProtectedDistinctionName
    loss_budget: Rational

    schema_id: ClassVar[str] = PROTECTED_DISTINCTION_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.distinction_id not in {
            "target_fit",
            "normalization",
            "trace_one",
            "entropy_preserved",
        }:
            raise SchemaValidationError(
                "protected_distinction.distinction_id",
                f"unsupported protected distinction: {self.distinction_id}",
            )
        if not self.loss_budget.is_nonnegative():
            raise SchemaValidationError(
                "protected_distinction.loss_budget",
                "loss budget must be nonnegative",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "protected_distinction",
    ) -> ProtectedDistinctionRecord:
        obj = strict_object(value, path, {"schema_id", "distinction_id", "loss_budget"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        distinction_id = require_string(obj["distinction_id"], f"{path}.distinction_id")
        if distinction_id not in {
            "target_fit",
            "normalization",
            "trace_one",
            "entropy_preserved",
        }:
            raise SchemaValidationError(
                f"{path}.distinction_id",
                f"unsupported protected distinction: {distinction_id}",
            )
        return cls(
            distinction_id=distinction_id,
            loss_budget=Rational.from_json(obj["loss_budget"], f"{path}.loss_budget"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "distinction_id": self.distinction_id,
            "loss_budget": self.loss_budget.to_json(),
        }


@dataclass(frozen=True, slots=True)
class EvaluationEvidenceRecord:
    scope: CheckerScope
    predecessor_observation: ObservationRecord
    successor_observation: ObservationRecord
    target_observation: ObservationRecord
    evaluator_policy_hash: str

    schema_id: ClassVar[str] = EVALUATION_EVIDENCE_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.scope == "gate_b_classical":
            expected_type = DistributionRecord
        elif self.scope == "gate_c_diagonal_quantum":
            expected_type = DiagonalDensityRecord
        else:
            raise SchemaValidationError(
                "evaluation_evidence.scope",
                f"unsupported scope: {self.scope}",
            )
        for field_name in (
            "predecessor_observation",
            "successor_observation",
            "target_observation",
        ):
            if not isinstance(getattr(self, field_name), expected_type):
                raise SchemaValidationError(
                    f"evaluation_evidence.{field_name}",
                    f"scope {self.scope} requires {expected_type.__name__}",
                )
        validate_hash256(
            self.evaluator_policy_hash,
            "evaluation_evidence.evaluator_policy_hash",
        )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "evaluation_evidence",
    ) -> EvaluationEvidenceRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "scope",
                "predecessor_observation",
                "successor_observation",
                "target_observation",
                "evaluator_policy_hash",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        scope = require_string(obj["scope"], f"{path}.scope")
        if scope == "gate_b_classical":
            parser = DistributionRecord.from_json
        elif scope == "gate_c_diagonal_quantum":
            parser = DiagonalDensityRecord.from_json
        else:
            raise SchemaValidationError(f"{path}.scope", f"unsupported scope: {scope}")
        return cls(
            scope=scope,
            predecessor_observation=parser(
                obj["predecessor_observation"],
                f"{path}.predecessor_observation",
            ),
            successor_observation=parser(
                obj["successor_observation"],
                f"{path}.successor_observation",
            ),
            target_observation=parser(
                obj["target_observation"],
                f"{path}.target_observation",
            ),
            evaluator_policy_hash=require_string(
                obj["evaluator_policy_hash"],
                f"{path}.evaluator_policy_hash",
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "scope": self.scope,
            "predecessor_observation": self.predecessor_observation.to_json(),
            "successor_observation": self.successor_observation.to_json(),
            "target_observation": self.target_observation.to_json(),
            "evaluator_policy_hash": self.evaluator_policy_hash,
        }
