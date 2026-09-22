from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.bootstrap import Phase16BootstrapReport
from rcp_rclm_runtime_v4.phase16.campaign import validate_phase16_campaign
from rcp_rclm_runtime_v4.phase16.constants import PHASE16_ATTACK_SCHEMA_ID


@dataclass(frozen=True, slots=True)
class Phase16AttackCase:
    attack_id: str
    rejected: bool
    reason_class: str

    schema_id: ClassVar[str] = "runtime.v4.phase16.attack_case.v1"

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attack_id": self.attack_id,
            "rejected": self.rejected,
            "reason_class": self.reason_class,
            "case_hash": canonical_json_hash(
                {
                    "schema_id": self.schema_id,
                    "attack_id": self.attack_id,
                    "rejected": self.rejected,
                    "reason_class": self.reason_class,
                }
            ),
        }


@dataclass(frozen=True, slots=True)
class Phase16AttackSuiteReport:
    source_head: str
    reference_campaign_hash: str
    cases: Sequence[Phase16AttackCase]

    schema_id: ClassVar[str] = PHASE16_ATTACK_SCHEMA_ID

    @property
    def accepted(self) -> bool:
        return (
            len(self.cases) == 12
            and len({case.attack_id for case in self.cases}) == 12
            and all(case.rejected for case in self.cases)
        )

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "reference_campaign_hash": self.reference_campaign_hash,
            "cases": [case.to_json() for case in self.cases],
            "attack_count": len(self.cases),
            "rejected_count": sum(case.rejected for case in self.cases),
            "accepted": self.accepted,
            "phase16_exit_closed": False,
            "gate_e_closed": False,
            "next_phase": 16,
        }

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase16AttackSuiteReport:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("phase16.attacks", "expected object")
        raw_cases = value.get("cases")
        if not isinstance(raw_cases, Sequence) or isinstance(
            raw_cases, (str, bytes, bytearray)
        ):
            raise SchemaValidationError("phase16.attacks.cases", "expected array")
        cases = []
        for item in raw_cases:
            if not isinstance(item, Mapping):
                raise SchemaValidationError("phase16.attacks.cases", "case is not object")
            cases.append(
                Phase16AttackCase(
                    attack_id=str(item.get("attack_id")),
                    rejected=item.get("rejected") is True,
                    reason_class=str(item.get("reason_class")),
                )
            )
        report = cls(
            source_head=str(value.get("source_head")),
            reference_campaign_hash=str(value.get("reference_campaign_hash")),
            cases=tuple(cases),
        )
        if value.get("report_hash") != report.report_hash:
            raise SchemaValidationError("phase16.attacks.report_hash", "hash mismatch")
        if value.get("accepted") is not report.accepted or not report.accepted:
            raise SchemaValidationError("phase16.attacks.accepted", "attack suite failed")
        return report


def _retag(campaign: dict[str, object]) -> dict[str, object]:
    payload = dict(campaign)
    payload.pop("report_hash", None)
    campaign["report_hash"] = canonical_json_hash(payload)
    return campaign


def _mutated(
    reference: Mapping[str, object],
    transform: Callable[[dict[str, object]], None],
) -> dict[str, object]:
    candidate = deepcopy(dict(reference))
    transform(candidate)
    return _retag(candidate)


def _rejected(
    attack_id: str,
    action: Callable[[], object],
) -> Phase16AttackCase:
    try:
        action()
    except Exception as error:
        return Phase16AttackCase(
            attack_id=attack_id,
            rejected=True,
            reason_class=type(error).__name__,
        )
    return Phase16AttackCase(
        attack_id=attack_id,
        rejected=False,
        reason_class="UNEXPECTED_ACCEPT",
    )


def run_phase16_attacks(
    *,
    reference_campaign: Mapping[str, object],
    bootstrap: Phase16BootstrapReport,
    source_head: str,
) -> Phase16AttackSuiteReport:
    validate_phase16_campaign(reference_campaign, bootstrap=bootstrap)

    def validate(candidate: Mapping[str, object]) -> object:
        return validate_phase16_campaign(candidate, bootstrap=bootstrap)

    transforms: tuple[tuple[str, Callable[[dict[str, object]], None]], ...] = (
        (
            "host_authored_success_schedule",
            lambda value: value.__setitem__(
                "host_authored_success_schedule_present", True
            ),
        ),
        (
            "fair_order_substitution",
            lambda value: value["transitions"][0]["fair_search_certificate"][
                "fair_order_hashes"
            ].reverse(),
        ),
        (
            "archive_poisoning",
            lambda value: value["archive"]["records"][0]["payload"].__setitem__(
                "answer_visible", True
            ),
        ),
        (
            "candidate_self_reported_success",
            lambda value: value["transitions"][0]["search_attempts"][-1].__setitem__(
                "candidate_self_report_authoritative", True
            ),
        ),
        (
            "verifier_substitution",
            lambda value: value.__setitem__("fixed_verifier_hash", "0" * 64),
        ),
        (
            "semantic_regime_substitution",
            lambda value: value.__setitem__("semantics_id", "noncommuting-unverified"),
        ),
        (
            "capability_frontier_regression",
            lambda value: value["final_state"]["capability_frontier"].pop(0),
        ),
        (
            "recursive_productivity_forgery",
            lambda value: value["final_state"][
                "recursive_productivity_frontier"
            ].append("recursive.forged"),
        ),
        (
            "resource_laundering",
            lambda value: value["transitions"][0]["fair_search_certificate"][
                "resource_envelope_limits"
            ].__setitem__(0, 1),
        ),
        (
            "manual_repair_concealment",
            lambda value: value.__setitem__("manual_repairs", 1),
        ),
        (
            "lineage_substitution",
            lambda value: value["transitions"][1].__setitem__(
                "predecessor_state_hash", "f" * 64
            ),
        ),
        (
            "search_exhaustion_forgery",
            lambda value: value["exhaustion_probe"].__setitem__(
                "considered_program_count", 1
            ),
        ),
    )
    cases = tuple(
        _rejected(
            attack_id,
            lambda transform=transform: validate(
                _mutated(reference_campaign, transform)
            ),
        )
        for attack_id, transform in transforms
    )
    report = Phase16AttackSuiteReport(
        source_head=source_head,
        reference_campaign_hash=str(reference_campaign["report_hash"]),
        cases=cases,
    )
    if not report.accepted:
        raise SchemaValidationError("phase16.attacks", "selected attack suite failed")
    return report


__all__ = [
    "Phase16AttackCase",
    "Phase16AttackSuiteReport",
    "run_phase16_attacks",
]
