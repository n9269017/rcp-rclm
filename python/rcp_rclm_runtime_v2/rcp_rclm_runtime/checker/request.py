from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationReport
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema._common import (
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
)
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord
from rcp_rclm_runtime.checker.evidence import (
    EvaluationEvidenceRecord,
    ProtectedDistinctionRecord,
    ResourceRecord,
    TrustAnchorRecord,
)

CHECKER_REQUEST_SCHEMA_ID = "runtime.phase3_checker_request.v2"


def parse_lean_bridge_report(
    value: object,
    path: str = "lean_bridge_report",
) -> LeanBridgeVerificationReport:
    fields = {
        "schema_id",
        "contract_version",
        "bridge_verdict",
        "reason_codes",
        "case_id",
        "scope",
        "packet_hash",
        "expected_acceptance",
        "lean_rcp_acceptance",
        "lean_rclm_acceptance",
        "differential_match",
        "generated_source_path",
        "generated_source_hash",
        "theorem_surface_hash",
        "project_pin_hash",
        "toolchain_runtime_hash",
        "source_guard_hash",
        "error_detail_hash",
        "compiler_report",
        "compiler_duration_ms",
        "timed_out",
    }
    obj = strict_object(value, path, fields)
    require_schema_id(
        obj["schema_id"],
        f"{path}.schema_id",
        LeanBridgeVerificationReport.schema_id,
    )
    contract_version = require_string(
        obj["contract_version"],
        f"{path}.contract_version",
    )
    reasons_raw = obj["reason_codes"]
    if not isinstance(reasons_raw, list):
        raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
    reasons = tuple(
        require_string(item, f"{path}.reason_codes[{index}]")
        for index, item in enumerate(reasons_raw)
    )
    return LeanBridgeVerificationReport(
        bridge_verdict=_require_choice(
            obj["bridge_verdict"],
            f"{path}.bridge_verdict",
            {"accept", "reject", "indeterminate"},
        ),
        reason_codes=reasons,
        case_id=require_string(obj["case_id"], f"{path}.case_id"),
        scope=require_string(obj["scope"], f"{path}.scope"),
        packet_hash=require_string(obj["packet_hash"], f"{path}.packet_hash"),
        expected_acceptance=_require_bool(
            obj["expected_acceptance"],
            f"{path}.expected_acceptance",
        ),
        lean_rcp_acceptance=_require_optional_bool(
            obj["lean_rcp_acceptance"],
            f"{path}.lean_rcp_acceptance",
        ),
        lean_rclm_acceptance=_require_optional_bool(
            obj["lean_rclm_acceptance"],
            f"{path}.lean_rclm_acceptance",
        ),
        differential_match=_require_bool(
            obj["differential_match"],
            f"{path}.differential_match",
        ),
        generated_source_path=require_string(
            obj["generated_source_path"],
            f"{path}.generated_source_path",
        ),
        generated_source_hash=require_string(
            obj["generated_source_hash"],
            f"{path}.generated_source_hash",
        ),
        theorem_surface_hash=require_string(
            obj["theorem_surface_hash"],
            f"{path}.theorem_surface_hash",
        ),
        project_pin_hash=require_string(
            obj["project_pin_hash"],
            f"{path}.project_pin_hash",
        ),
        toolchain_runtime_hash=require_string(
            obj["toolchain_runtime_hash"],
            f"{path}.toolchain_runtime_hash",
        ),
        source_guard_hash=require_string(
            obj["source_guard_hash"],
            f"{path}.source_guard_hash",
        ),
        error_detail_hash=require_string(
            obj["error_detail_hash"],
            f"{path}.error_detail_hash",
        ),
        compiler_report=LeanVerifierReportRecord.from_json(
            obj["compiler_report"],
            f"{path}.compiler_report",
        ),
        compiler_duration_ms=require_structural_integer(
            obj["compiler_duration_ms"],
            f"{path}.compiler_duration_ms",
            minimum=0,
        ),
        timed_out=_require_bool(obj["timed_out"], f"{path}.timed_out"),
        contract_version=contract_version,
    )


@dataclass(frozen=True, slots=True)
class Phase3CheckerRequest:
    transition_id: str
    predecessor: RclmStateRecord
    candidate: RclmCandidateRecord
    certificate: RclmCertificatePacketRecord
    trust_anchor: TrustAnchorRecord
    resource_record: ResourceRecord
    protected_distinctions: Sequence[ProtectedDistinctionRecord]
    evaluation_evidence: EvaluationEvidenceRecord
    lean_bridge_report: LeanBridgeVerificationReport
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = CHECKER_REQUEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "checker_request.transition_id")
        object.__setattr__(
            self,
            "protected_distinctions",
            tuple(self.protected_distinctions),
        )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "checker_request.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        ids = [item.distinction_id for item in self.protected_distinctions]
        if ids != sorted(ids):
            raise SchemaValidationError(
                "checker_request.protected_distinctions",
                "protected distinctions must be sorted by distinction_id",
            )
        if len(ids) != len(set(ids)):
            raise SchemaValidationError(
                "checker_request.protected_distinctions",
                "duplicate protected distinction",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "checker_request",
    ) -> Phase3CheckerRequest:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "contract_version",
                "transition_id",
                "predecessor",
                "candidate",
                "certificate",
                "trust_anchor",
                "resource_record",
                "protected_distinctions",
                "evaluation_evidence",
                "lean_bridge_report",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        distinctions_raw = obj["protected_distinctions"]
        if not isinstance(distinctions_raw, list):
            raise SchemaValidationError(
                f"{path}.protected_distinctions",
                "expected an array",
            )
        distinctions = tuple(
            ProtectedDistinctionRecord.from_json(
                item,
                f"{path}.protected_distinctions[{index}]",
            )
            for index, item in enumerate(distinctions_raw)
        )
        return cls(
            transition_id=require_string(
                obj["transition_id"],
                f"{path}.transition_id",
            ),
            predecessor=RclmStateRecord.from_json(
                obj["predecessor"],
                f"{path}.predecessor",
            ),
            candidate=RclmCandidateRecord.from_json(
                obj["candidate"],
                f"{path}.candidate",
            ),
            certificate=RclmCertificatePacketRecord.from_json(
                obj["certificate"],
                f"{path}.certificate",
            ),
            trust_anchor=TrustAnchorRecord.from_json(
                obj["trust_anchor"],
                f"{path}.trust_anchor",
            ),
            resource_record=ResourceRecord.from_json(
                obj["resource_record"],
                f"{path}.resource_record",
            ),
            protected_distinctions=distinctions,
            evaluation_evidence=EvaluationEvidenceRecord.from_json(
                obj["evaluation_evidence"],
                f"{path}.evaluation_evidence",
            ),
            lean_bridge_report=parse_lean_bridge_report(
                obj["lean_bridge_report"],
                f"{path}.lean_bridge_report",
            ),
            contract_version=require_string(
                obj["contract_version"],
                f"{path}.contract_version",
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "predecessor": self.predecessor.to_json(),
            "candidate": self.candidate.to_json(),
            "certificate": self.certificate.to_json(),
            "trust_anchor": self.trust_anchor.to_json(),
            "resource_record": self.resource_record.to_json(),
            "protected_distinctions": [
                item.to_json() for item in self.protected_distinctions
            ],
            "evaluation_evidence": self.evaluation_evidence.to_json(),
            "lean_bridge_report": self.lean_bridge_report.to_json(),
        }


def _require_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, "expected a Boolean")
    return value


def _require_optional_bool(value: object, path: str) -> bool | None:
    if value is None:
        return None
    return _require_bool(value, path)


def _require_choice(value: object, path: str, choices: set[str]) -> str:
    text = require_string(value, path)
    if text not in choices:
        raise SchemaValidationError(path, f"unsupported value: {text}")
    return text
