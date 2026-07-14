from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, RuntimeValidationError, SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.schema.verdict import FrozenHashMap, ReasonCode
from rcp_rclm_runtime.checker.aggregate import check_transition
from rcp_rclm_runtime.checker.integrity import (
    PACKAGE_INTEGRITY_SCHEMA_ID,
    PackageIntegrityRecord,
    check_package_integrity,
)
from rcp_rclm_runtime.checker.records import (
    ComponentResultRecord,
    Phase3CheckerReport,
    Phase3CheckerRequest,
)

HARDENED_CHECKER_REQUEST_SCHEMA_ID = "runtime.phase4_hardened_checker_request.v2"
HARDENED_CHECKER_REPORT_SCHEMA_ID = "runtime.phase4_hardened_checker_report.v2"


@dataclass(frozen=True, slots=True)
class Phase4HardenedRequest:
    checker_request: Phase3CheckerRequest
    package_integrity: PackageIntegrityRecord
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = HARDENED_CHECKER_REQUEST_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "hardened_checker_request.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "hardened_checker_request",
    ) -> Phase4HardenedRequest:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "contract_version",
                "checker_request",
                "package_integrity",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            checker_request=Phase3CheckerRequest.from_json(
                obj["checker_request"],
                f"{path}.checker_request",
            ),
            package_integrity=PackageIntegrityRecord.from_json(
                obj["package_integrity"],
                f"{path}.package_integrity",
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
            "checker_request": self.checker_request.to_json(),
            "package_integrity": self.package_integrity.to_json(),
        }


@dataclass(frozen=True, slots=True)
class Phase4HardenedReport:
    transition_id: str
    verdict: Literal["accept", "reject", "indeterminate"]
    reason_codes: Sequence[ReasonCode]
    integrity_result: ComponentResultRecord
    checker_report: Phase3CheckerReport | None
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = HARDENED_CHECKER_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "hardened_checker_report.transition_id")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(
                "hardened_checker_report.verdict",
                f"unsupported verdict: {self.verdict}",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "hardened_checker_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "hardened_checker_report.reason_codes",
                "reason codes must be unique",
            )
        if self.verdict == "accept" and self.reason_codes:
            raise SchemaValidationError(
                "hardened_checker_report.reason_codes",
                "accept verdict cannot contain failure reasons",
            )
        if self.verdict != "accept" and not self.reason_codes:
            raise SchemaValidationError(
                "hardened_checker_report.reason_codes",
                "nonaccepting verdict requires a reason code",
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
            "integrity_result": self.integrity_result.to_json(),
            "checker_report": (
                None if self.checker_report is None else self.checker_report.to_json()
            ),
            "artifact_hashes": self.artifact_hashes.to_json(),
        }


def check_hardened_transition(
    request: Phase4HardenedRequest,
) -> Phase4HardenedReport:
    input_hash_before = canonical_json_hash(request.to_json())
    try:
        integrity_result = check_package_integrity(
            request.checker_request,
            request.package_integrity,
        )
        checker_report = check_transition(request.checker_request)
        reasons = _ordered_reasons(
            integrity_result.reason_codes,
            checker_report.reason_codes,
        )
        if integrity_result.status == "fail" or checker_report.verdict == "reject":
            verdict: Literal["accept", "reject", "indeterminate"] = "reject"
        elif (
            integrity_result.status == "indeterminate"
            or checker_report.verdict == "indeterminate"
        ):
            verdict = "indeterminate"
        else:
            verdict = "accept"
        artifact_hashes = FrozenHashMap.from_mapping(
            {
                "hardened_request": input_hash_before,
                "phase3_request": canonical_json_hash(
                    request.checker_request.to_json()
                ),
                "package_integrity": canonical_json_hash(
                    request.package_integrity.to_json()
                ),
                "phase3_report": checker_report.report_hash,
            },
            "hardened_checker_report.artifact_hashes",
        )
        report = Phase4HardenedReport(
            transition_id=request.checker_request.transition_id,
            verdict=verdict,
            reason_codes=reasons,
            integrity_result=integrity_result,
            checker_report=checker_report,
            artifact_hashes=artifact_hashes,
        )
    except Exception as exc:
        report = _error_report(
            transition_id=request.checker_request.transition_id,
            reason=ReasonCode.INTERNAL_ERROR,
            detail=exc,
            artifact_hashes={"hardened_request": input_hash_before},
        )
    input_hash_after = canonical_json_hash(request.to_json())
    if input_hash_after != input_hash_before:
        return _error_report(
            transition_id=request.checker_request.transition_id,
            reason=ReasonCode.INTERNAL_ERROR,
            detail=RuntimeError("hardened checker input mutation detected"),
            artifact_hashes={
                "hardened_request_before": input_hash_before,
                "hardened_request_after": input_hash_after,
            },
        )
    return report


def check_hardened_transition_bytes(
    data: bytes,
    *,
    require_canonical: bool = True,
) -> Phase4HardenedReport:
    raw_hash = sha256_hex(data)
    try:
        value = load_json_strict(data, require_canonical=require_canonical)
    except CanonicalizationError as exc:
        return _error_report(
            transition_id="unparsed",
            reason=ReasonCode.CANONICALIZATION_FAILED,
            detail=exc,
            artifact_hashes={"raw_input": raw_hash},
        )
    try:
        request = Phase4HardenedRequest.from_json(value)
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        return _error_report(
            transition_id=_transition_id_from_untrusted(value),
            reason=ReasonCode.SCHEMA_MALFORMED,
            detail=exc,
            artifact_hashes={
                "raw_input": raw_hash,
                "parsed_input": canonical_json_hash(value),
            },
        )
    return check_hardened_transition(request)


def _ordered_reasons(
    *groups: Sequence[ReasonCode],
) -> Sequence[ReasonCode]:
    return tuple(dict.fromkeys(reason for group in groups for reason in group))


def _error_report(
    *,
    transition_id: str,
    reason: ReasonCode,
    detail: Exception,
    artifact_hashes: Mapping[str, str],
) -> Phase4HardenedReport:
    detail_hash = sha256_hex(str(detail).encode("utf-8"))
    hashes = dict(artifact_hashes)
    hashes["error_detail"] = detail_hash
    integrity_result = ComponentResultRecord.from_evidence(
        "fail",
        (reason,),
        {
            "error_type": type(detail).__name__,
            "error_detail_hash": detail_hash,
        },
    )
    return Phase4HardenedReport(
        transition_id=transition_id,
        verdict="reject",
        reason_codes=(reason,),
        integrity_result=integrity_result,
        checker_report=None,
        artifact_hashes=FrozenHashMap.from_mapping(
            hashes,
            "hardened_checker_report.artifact_hashes",
        ),
    )


def _transition_id_from_untrusted(value: object) -> str:
    if not isinstance(value, Mapping):
        return "unparsed"
    checker_request = value.get("checker_request")
    if not isinstance(checker_request, Mapping):
        return "unparsed"
    transition_id = checker_request.get("transition_id")
    if isinstance(transition_id, str) and transition_id:
        return transition_id
    return "unparsed"
