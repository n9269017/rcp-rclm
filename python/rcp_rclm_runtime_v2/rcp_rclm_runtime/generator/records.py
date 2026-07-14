from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationReport
from rcp_rclm_runtime.schema._common import require_string
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.checker.hardened import Phase4HardenedReport
from rcp_rclm_runtime.generator.protocol import (
    GeneratorReasonCode,
    GeneratorStageResult,
    GeneratorVerdict,
    ProcessVerdict,
    ReferenceProposalRecord,
)

WORKER_SOURCE_FINDING_SCHEMA_ID = "runtime.phase5a_worker_source_finding.v2"
WORKER_SOURCE_GUARD_SCHEMA_ID = "runtime.phase5a_worker_source_guard.v2"
GENERATOR_PROCESS_REPORT_SCHEMA_ID = "runtime.phase5a_generator_process_report.v2"
REFERENCE_LOOP_REPORT_SCHEMA_ID = "runtime.phase5a_reference_loop_report.v2"


@dataclass(frozen=True, slots=True)
class WorkerSourceFinding:
    code: str
    path: str
    line: int
    detail: str

    schema_id: ClassVar[str] = WORKER_SOURCE_FINDING_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.code, "worker_source_finding.code")
        require_string(self.path, "worker_source_finding.path")
        require_string(self.detail, "worker_source_finding.detail")
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 1:
            raise SchemaValidationError(
                "worker_source_finding.line",
                "expected a positive integer",
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class WorkerSourceGuardReport:
    guard_version: str
    file_hashes: FrozenHashMap
    findings: Sequence[WorkerSourceFinding]

    schema_id: ClassVar[str] = WORKER_SOURCE_GUARD_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.guard_version, "worker_source_guard.guard_version")
        object.__setattr__(self, "findings", tuple(self.findings))

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "guard_version": self.guard_version,
            "file_hashes": self.file_hashes.to_json(),
            "findings": [finding.to_json() for finding in self.findings],
            "clean": self.clean,
        }


@dataclass(frozen=True, slots=True)
class GeneratorProcessReport:
    verdict: ProcessVerdict
    reason_codes: Sequence[GeneratorReasonCode]
    input_hash: str
    stdout_hash: str
    stderr_hash: str
    worker_guard_hash: str
    exit_code: int | None
    timed_out: bool
    proposal_hash: str | None

    schema_id: ClassVar[str] = GENERATOR_PROCESS_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.verdict not in {"success", "failure", "indeterminate"}:
            raise SchemaValidationError(
                "generator_process_report.verdict",
                "unsupported process verdict",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "generator_process_report.reason_codes",
                "reason codes must be unique",
            )
        if self.verdict == "success" and self.reason_codes:
            raise SchemaValidationError(
                "generator_process_report.reason_codes",
                "successful process cannot contain failure reasons",
            )
        if self.verdict != "success" and not self.reason_codes:
            raise SchemaValidationError(
                "generator_process_report.reason_codes",
                "non-success process requires a reason code",
            )
        for field_name in (
            "input_hash",
            "stdout_hash",
            "stderr_hash",
            "worker_guard_hash",
        ):
            validate_hash256(
                getattr(self, field_name),
                f"generator_process_report.{field_name}",
            )
        if self.proposal_hash is not None:
            validate_hash256(
                self.proposal_hash,
                "generator_process_report.proposal_hash",
            )
        if self.exit_code is not None and (
            isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int)
        ):
            raise SchemaValidationError(
                "generator_process_report.exit_code",
                "expected integer or null",
            )
        if not isinstance(self.timed_out, bool):
            raise SchemaValidationError(
                "generator_process_report.timed_out",
                "expected a Boolean",
            )
        if self.verdict == "success" and self.proposal_hash is None:
            raise SchemaValidationError(
                "generator_process_report.proposal_hash",
                "successful process requires a proposal hash",
            )
        if self.timed_out and self.verdict != "indeterminate":
            raise SchemaValidationError(
                "generator_process_report.verdict",
                "timeout must be indeterminate",
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "verdict": self.verdict,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "input_hash": self.input_hash,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "worker_guard_hash": self.worker_guard_hash,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "proposal_hash": self.proposal_hash,
        }


@dataclass(frozen=True, slots=True)
class Phase5AReferenceLoopReport:
    transition_id: str
    verdict: GeneratorVerdict
    reason_codes: Sequence[GeneratorReasonCode]
    worker_source_result: GeneratorStageResult
    first_process: GeneratorProcessReport
    second_process: GeneratorProcessReport
    replay_result: GeneratorStageResult
    proposal: ReferenceProposalRecord | None
    proposal_validation_result: GeneratorStageResult
    certificate_construction_result: GeneratorStageResult
    selection_result: GeneratorStageResult
    realization_result: GeneratorStageResult
    lean_bridge_report: LeanBridgeVerificationReport | None
    hardened_checker_report: Phase4HardenedReport | None
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = REFERENCE_LOOP_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase5a_reference_loop_report.transition_id")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(
                "phase5a_reference_loop_report.verdict",
                "unsupported verdict",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase5a_reference_loop_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "phase5a_reference_loop_report.reason_codes",
                "reason codes must be unique",
            )
        if self.verdict == "accept" and self.reason_codes:
            raise SchemaValidationError(
                "phase5a_reference_loop_report.reason_codes",
                "accepting report cannot contain failure reasons",
            )
        if self.verdict != "accept" and not self.reason_codes:
            raise SchemaValidationError(
                "phase5a_reference_loop_report.reason_codes",
                "nonaccepting report requires a reason code",
            )
        if self.verdict == "accept":
            stages = (
                self.worker_source_result,
                self.replay_result,
                self.proposal_validation_result,
                self.certificate_construction_result,
                self.selection_result,
                self.realization_result,
            )
            if any(stage.status != "pass" for stage in stages):
                raise SchemaValidationError(
                    "phase5a_reference_loop_report.verdict",
                    "accept requires every generator stage to pass",
                )
            if self.first_process.verdict != "success" or self.second_process.verdict != "success":
                raise SchemaValidationError(
                    "phase5a_reference_loop_report.verdict",
                    "accept requires two successful generator processes",
                )
            if self.proposal is None:
                raise SchemaValidationError(
                    "phase5a_reference_loop_report.proposal",
                    "accept requires a validated proposal",
                )
            if self.lean_bridge_report is None or not self.lean_bridge_report.accepted:
                raise SchemaValidationError(
                    "phase5a_reference_loop_report.lean_bridge_report",
                    "accept requires an accepting Lean bridge report",
                )
            if self.hardened_checker_report is None or not self.hardened_checker_report.accepted:
                raise SchemaValidationError(
                    "phase5a_reference_loop_report.hardened_checker_report",
                    "accept requires an accepting hardened checker report",
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
            "worker_source_result": self.worker_source_result.to_json(),
            "first_process": self.first_process.to_json(),
            "second_process": self.second_process.to_json(),
            "replay_result": self.replay_result.to_json(),
            "proposal": None if self.proposal is None else self.proposal.to_json(),
            "proposal_validation_result": self.proposal_validation_result.to_json(),
            "certificate_construction_result": self.certificate_construction_result.to_json(),
            "selection_result": self.selection_result.to_json(),
            "realization_result": self.realization_result.to_json(),
            "lean_bridge_report": (
                None if self.lean_bridge_report is None else self.lean_bridge_report.to_json()
            ),
            "hardened_checker_report": (
                None
                if self.hardened_checker_report is None
                else self.hardened_checker_report.to_json()
            ),
            "artifact_hashes": self.artifact_hashes.to_json(),
        }
