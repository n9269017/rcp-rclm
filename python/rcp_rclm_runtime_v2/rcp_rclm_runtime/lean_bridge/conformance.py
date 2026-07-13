from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime._version import CONTRACT_VERSION, FORMAL_SOURCE_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.lean_bridge.packet import reference_packets
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationReport,
    LeanReferenceVerifier,
)


@dataclass(frozen=True, slots=True)
class DifferentialConformanceSuiteReport:
    reports: Sequence[LeanBridgeVerificationReport]
    contract_version: str = CONTRACT_VERSION
    formal_source_commit: str = FORMAL_SOURCE_COMMIT

    schema_id: ClassVar[str] = "runtime.lean_differential_conformance_suite.v2"

    def __post_init__(self) -> None:
        object.__setattr__(self, "reports", tuple(self.reports))

    @property
    def case_count(self) -> int:
        return len(self.reports)

    @property
    def accepting_case_count(self) -> int:
        return sum(1 for report in self.reports if report.expected_acceptance)

    @property
    def rejecting_case_count(self) -> int:
        return sum(1 for report in self.reports if not report.expected_acceptance)

    @property
    def all_bridge_reports_accepted(self) -> bool:
        return all(report.accepted for report in self.reports)

    @property
    def all_differential_matches(self) -> bool:
        return all(report.differential_match for report in self.reports)

    @property
    def ok(self) -> bool:
        return (
            self.case_count == 10
            and self.accepting_case_count == 4
            and self.rejecting_case_count == 6
            and self.all_bridge_reports_accepted
            and self.all_differential_matches
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "formal_source_commit": self.formal_source_commit,
            "case_count": self.case_count,
            "accepting_case_count": self.accepting_case_count,
            "rejecting_case_count": self.rejecting_case_count,
            "all_bridge_reports_accepted": self.all_bridge_reports_accepted,
            "all_differential_matches": self.all_differential_matches,
            "ok": self.ok,
            "case_report_hashes": {
                report.case_id: report.report_hash
                for report in sorted(self.reports, key=lambda item: item.case_id)
            },
            "reports": [
                report.to_json()
                for report in sorted(self.reports, key=lambda item: item.case_id)
            ],
        }


def run_reference_conformance(
    verifier: LeanReferenceVerifier,
) -> DifferentialConformanceSuiteReport:
    reports = tuple(verifier.verify(packet) for packet in reference_packets())
    return DifferentialConformanceSuiteReport(reports=reports)
