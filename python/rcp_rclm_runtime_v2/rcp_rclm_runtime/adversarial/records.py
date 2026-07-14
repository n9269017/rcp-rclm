from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final, Literal

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.schema._common import FrozenJson, freeze_json, require_string, thaw_json

ATTACK_CASE_RESULT_SCHEMA_ID: Final[str] = "runtime.phase4_attack_case_result.v2"
ATTACK_SUITE_REPORT_SCHEMA_ID: Final[str] = "runtime.phase4_attack_suite_report.v2"
PHASE_4_SUITE_VERSION: Final[str] = "rcp-rclm-runtime-phase-4-adversarial-v1"
_CASE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9._-]{0,159}$")

AttackVerdict = Literal["accept", "reject", "indeterminate"]


@dataclass(frozen=True, slots=True)
class AdversarialCaseResult:
    case_id: str
    attack_class: str
    expected_verdict: AttackVerdict
    expected_reason_codes: Sequence[str]
    observed_verdict: AttackVerdict
    observed_reason_codes: Sequence[str]
    first_observation_hash: str
    second_observation_hash: str
    deterministic_replay: bool
    evidence: FrozenJson

    schema_id: ClassVar[str] = ATTACK_CASE_RESULT_SCHEMA_ID

    def __post_init__(self) -> None:
        if _CASE_ID_PATTERN.fullmatch(self.case_id) is None:
            raise ValueError(f"invalid adversarial case identifier: {self.case_id}")
        require_string(self.attack_class, "adversarial_case.attack_class")
        if self.expected_verdict not in {"accept", "reject", "indeterminate"}:
            raise ValueError(f"unsupported expected verdict: {self.expected_verdict}")
        if self.observed_verdict not in {"accept", "reject", "indeterminate"}:
            raise ValueError(f"unsupported observed verdict: {self.observed_verdict}")
        expected = tuple(self.expected_reason_codes)
        observed = tuple(self.observed_reason_codes)
        if len(expected) != len(set(expected)):
            raise ValueError("expected reason codes must be unique")
        if len(observed) != len(set(observed)):
            raise ValueError("observed reason codes must be unique")
        object.__setattr__(self, "expected_reason_codes", expected)
        object.__setattr__(self, "observed_reason_codes", observed)
        object.__setattr__(self, "evidence", freeze_json(thaw_json(self.evidence)))
        validate_hash256(
            self.first_observation_hash,
            "adversarial_case.first_observation_hash",
        )
        validate_hash256(
            self.second_observation_hash,
            "adversarial_case.second_observation_hash",
        )
        if not isinstance(self.deterministic_replay, bool):
            raise ValueError("deterministic_replay must be a Boolean")

    @classmethod
    def from_evidence(
        cls,
        *,
        case_id: str,
        attack_class: str,
        expected_verdict: AttackVerdict,
        expected_reason_codes: Sequence[str],
        observed_verdict: AttackVerdict,
        observed_reason_codes: Sequence[str],
        first_observation: object,
        second_observation: object,
        evidence: object,
    ) -> AdversarialCaseResult:
        first_hash = canonical_json_hash(first_observation)
        second_hash = canonical_json_hash(second_observation)
        return cls(
            case_id=case_id,
            attack_class=attack_class,
            expected_verdict=expected_verdict,
            expected_reason_codes=tuple(expected_reason_codes),
            observed_verdict=observed_verdict,
            observed_reason_codes=tuple(observed_reason_codes),
            first_observation_hash=first_hash,
            second_observation_hash=second_hash,
            deterministic_replay=first_hash == second_hash,
            evidence=freeze_json(evidence),
        )

    @property
    def passed(self) -> bool:
        expected_reasons = set(self.expected_reason_codes)
        observed_reasons = set(self.observed_reason_codes)
        return (
            self.deterministic_replay
            and self.observed_verdict == self.expected_verdict
            and expected_reasons.issubset(observed_reasons)
            and self.observed_verdict != "accept"
        )

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "case_id": self.case_id,
            "attack_class": self.attack_class,
            "expected_verdict": self.expected_verdict,
            "expected_reason_codes": list(self.expected_reason_codes),
            "observed_verdict": self.observed_verdict,
            "observed_reason_codes": list(self.observed_reason_codes),
            "first_observation_hash": self.first_observation_hash,
            "second_observation_hash": self.second_observation_hash,
            "deterministic_replay": self.deterministic_replay,
            "passed": self.passed,
            "evidence": thaw_json(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class AdversarialSuiteReport:
    results: Sequence[AdversarialCaseResult]
    suite_version: str = PHASE_4_SUITE_VERSION
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = ATTACK_SUITE_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        results = tuple(self.results)
        case_ids = [item.case_id for item in results]
        if case_ids != sorted(case_ids):
            raise ValueError("adversarial case results must be sorted by case_id")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("adversarial case identifiers must be unique")
        if self.suite_version != PHASE_4_SUITE_VERSION:
            raise ValueError(f"expected suite version {PHASE_4_SUITE_VERSION}")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(f"expected contract version {CONTRACT_VERSION}")
        object.__setattr__(self, "results", results)

    @property
    def case_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for item in self.results if item.passed)

    @property
    def failed_count(self) -> int:
        return self.case_count - self.passed_count

    @property
    def all_passed(self) -> bool:
        return self.case_count > 0 and self.failed_count == 0

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "suite_version": self.suite_version,
            "contract_version": self.contract_version,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "all_passed": self.all_passed,
            "results": [item.to_json() for item in self.results],
        }
