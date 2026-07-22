from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase13.constants import (
    ATTACK_REASON_BY_ID,
    PHASE13A_ATTACK_SUITE_VERSION,
    PHASE13A_CONTRACT_HASH,
    PHASE13A_CONTRACT_VERSION,
    PHASE13A_REPLAY_PROFILE,
)


def _ordered_unique(values: Sequence[str], path: str) -> Sequence[str]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value for value in result):
        raise SchemaValidationError(path, "entries must be nonempty strings")
    if len(result) != len(set(result)):
        raise SchemaValidationError(path, "entries must be unique")
    expected = tuple(sorted(result, key=lambda value: value.encode("utf-8")))
    if result != expected:
        raise SchemaValidationError(path, "entries must be sorted by UTF-8 bytes")
    return result


@dataclass(frozen=True, slots=True)
class ReplayInvocationCounters:
    training_invocations: int = 0
    generator_invocations: int = 0
    planner_invocations: int = 0

    schema_id: ClassVar[str] = "runtime.v3.phase13a.replay_invocation_counters.v1"

    def __post_init__(self) -> None:
        for name in ("training_invocations", "generator_invocations", "planner_invocations"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value != 0:
                raise SchemaValidationError(f"phase13a.counters.{name}", "replay invocation count must be zero")

    @property
    def accepted(self) -> bool:
        return True

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "training_invocations": self.training_invocations,
            "generator_invocations": self.generator_invocations,
            "planner_invocations": self.planner_invocations,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class RetainedFileRecord:
    path: str
    size: int
    sha256: str

    schema_id: ClassVar[str] = "runtime.v3.phase13a.retained_file.v1"

    def __post_init__(self) -> None:
        if not self.path or self.path.startswith("/") or ".." in self.path.split("/"):
            raise SchemaValidationError("phase13a.retained_file.path", "expected a safe relative path")
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise SchemaValidationError("phase13a.retained_file.size", "expected a nonnegative integer")
        validate_hash256(self.sha256, "phase13a.retained_file.sha256")

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "path": self.path,
            "size": self.size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class RetainedEvidenceManifest:
    files: Sequence[RetainedFileRecord]
    missing_declared_paths: Sequence[str]
    excluded_forbidden_paths: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase13a.retained_evidence_manifest.v1"

    def __post_init__(self) -> None:
        files = tuple(self.files)
        paths = tuple(item.path for item in files)
        if paths != tuple(sorted(paths, key=lambda value: value.encode("utf-8"))):
            raise SchemaValidationError("phase13a.manifest.files", "files must be path sorted")
        if len(paths) != len(set(paths)):
            raise SchemaValidationError("phase13a.manifest.files", "duplicate path")
        object.__setattr__(self, "files", files)
        object.__setattr__(
            self,
            "missing_declared_paths",
            _ordered_unique(self.missing_declared_paths, "phase13a.manifest.missing_declared_paths"),
        )
        object.__setattr__(
            self,
            "excluded_forbidden_paths",
            _ordered_unique(self.excluded_forbidden_paths, "phase13a.manifest.excluded_forbidden_paths"),
        )

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "files": [item.to_json() for item in self.files],
            "missing_declared_paths": list(self.missing_declared_paths),
            "excluded_forbidden_paths": list(self.excluded_forbidden_paths),
        }


@dataclass(frozen=True, slots=True)
class ReplaySourceFinding:
    code: str
    path: str
    line: int
    detail: str

    def __post_init__(self) -> None:
        if not self.code or not self.path or not self.detail:
            raise SchemaValidationError("phase13a.source_finding", "fields must be nonempty")
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 1:
            raise SchemaValidationError("phase13a.source_finding.line", "expected a positive integer")

    def to_json(self) -> dict[str, object]:
        return {"code": self.code, "path": self.path, "line": self.line, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ReplaySourceGuardReport:
    file_hashes: Mapping[str, str]
    findings: Sequence[ReplaySourceFinding]

    schema_id: ClassVar[str] = "runtime.v3.phase13a.replay_source_guard.v1"

    def __post_init__(self) -> None:
        hashes = dict(self.file_hashes)
        if tuple(hashes) != tuple(sorted(hashes, key=lambda value: value.encode("utf-8"))):
            raise SchemaValidationError("phase13a.source_guard.file_hashes", "keys must be sorted")
        for path, digest in hashes.items():
            if not path:
                raise SchemaValidationError("phase13a.source_guard.file_hashes", "path must be nonempty")
            validate_hash256(digest, f"phase13a.source_guard.file_hashes.{path}")
        findings = tuple(self.findings)
        expected = tuple(sorted(findings, key=lambda item: (item.path, item.line, item.code, item.detail)))
        if findings != expected:
            raise SchemaValidationError("phase13a.source_guard.findings", "findings must be sorted")
        object.__setattr__(self, "file_hashes", hashes)
        object.__setattr__(self, "findings", findings)

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "file_hashes": dict(self.file_hashes),
            "findings": [item.to_json() for item in self.findings],
            "clean": self.clean,
        }


@dataclass(frozen=True, slots=True)
class AdversarialAttackResult:
    attack_id: str
    expected_reason_code: str
    first_reason_codes: Sequence[str]
    second_reason_codes: Sequence[str]
    first_observation_hash: str
    second_observation_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase13a.attack_result.v1"

    def __post_init__(self) -> None:
        expected = ATTACK_REASON_BY_ID.get(self.attack_id)
        if expected is None or expected != self.expected_reason_code:
            raise SchemaValidationError("phase13a.attack.attack_id", "unknown attack or reason-code mismatch")
        for name in ("first_observation_hash", "second_observation_hash"):
            validate_hash256(getattr(self, name), f"phase13a.attack.{name}")
        first = _ordered_unique(self.first_reason_codes, "phase13a.attack.first_reason_codes")
        second = _ordered_unique(self.second_reason_codes, "phase13a.attack.second_reason_codes")
        object.__setattr__(self, "first_reason_codes", first)
        object.__setattr__(self, "second_reason_codes", second)

    @property
    def deterministic(self) -> bool:
        return (
            self.first_observation_hash == self.second_observation_hash
            and self.first_reason_codes == self.second_reason_codes
        )

    @property
    def passed(self) -> bool:
        return self.deterministic and self.expected_reason_code in self.first_reason_codes

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attack_id": self.attack_id,
            "expected_reason_code": self.expected_reason_code,
            "first_reason_codes": list(self.first_reason_codes),
            "second_reason_codes": list(self.second_reason_codes),
            "first_observation_hash": self.first_observation_hash,
            "second_observation_hash": self.second_observation_hash,
            "deterministic": self.deterministic,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class AdversarialAttackSuiteReport:
    results: Sequence[AdversarialAttackResult]
    suite_version: str = PHASE13A_ATTACK_SUITE_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase13a.attack_suite.v1"

    def __post_init__(self) -> None:
        results = tuple(self.results)
        ids = tuple(item.attack_id for item in results)
        if ids != tuple(sorted(ids, key=lambda value: value.encode("utf-8"))):
            raise SchemaValidationError("phase13a.attack_suite.results", "results must be attack-id sorted")
        if len(ids) != len(set(ids)):
            raise SchemaValidationError("phase13a.attack_suite.results", "duplicate attack id")
        if set(ids) != set(ATTACK_REASON_BY_ID):
            raise SchemaValidationError("phase13a.attack_suite.results", "suite must cover every frozen attack")
        if self.suite_version != PHASE13A_ATTACK_SUITE_VERSION:
            raise SchemaValidationError("phase13a.attack_suite.version", "suite version mismatch")
        object.__setattr__(self, "results", results)

    @property
    def all_passed(self) -> bool:
        return all(item.passed for item in self.results)

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "suite_version": self.suite_version,
            "case_count": len(self.results),
            "passed_count": sum(item.passed for item in self.results),
            "failed_count": sum(not item.passed for item in self.results),
            "all_passed": self.all_passed,
            "results": [item.to_json() for item in self.results],
        }


@dataclass(frozen=True, slots=True)
class Phase13AReplayBoundaryReport:
    retained_manifest: RetainedEvidenceManifest
    source_guard: ReplaySourceGuardReport
    counters: ReplayInvocationCounters
    forbidden_modules_loaded: Sequence[str]
    forbidden_paths_present: Sequence[str]
    phase12_required_paths_present: Sequence[str]
    phase12_required_paths_missing: Sequence[str]
    attack_suite: AdversarialAttackSuiteReport
    contract_hash: str = PHASE13A_CONTRACT_HASH
    contract_version: str = PHASE13A_CONTRACT_VERSION
    replay_profile: str = PHASE13A_REPLAY_PROFILE

    schema_id: ClassVar[str] = "runtime.v3.phase13a.replay_boundary_report.v1"

    def __post_init__(self) -> None:
        validate_hash256(self.contract_hash, "phase13a.report.contract_hash")
        if self.contract_hash != PHASE13A_CONTRACT_HASH:
            raise SchemaValidationError("phase13a.report.contract_hash", "contract hash mismatch")
        if self.contract_version != PHASE13A_CONTRACT_VERSION:
            raise SchemaValidationError("phase13a.report.contract_version", "contract version mismatch")
        if self.replay_profile != PHASE13A_REPLAY_PROFILE:
            raise SchemaValidationError("phase13a.report.replay_profile", "replay profile mismatch")
        for name in (
            "forbidden_modules_loaded",
            "forbidden_paths_present",
            "phase12_required_paths_present",
            "phase12_required_paths_missing",
        ):
            object.__setattr__(self, name, _ordered_unique(getattr(self, name), f"phase13a.report.{name}"))

    @property
    def phase12_dependency_complete(self) -> bool:
        return not self.phase12_required_paths_missing

    @property
    def replay_boundary_closed(self) -> bool:
        return (
            self.source_guard.clean
            and self.counters.accepted
            and not self.forbidden_modules_loaded
            and not self.forbidden_paths_present
            and self.attack_suite.all_passed
        )

    @property
    def phase13a_slice_closed(self) -> bool:
        return self.replay_boundary_closed

    @property
    def phase13_exit_closed(self) -> bool:
        return False

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "contract_hash": self.contract_hash,
            "replay_profile": self.replay_profile,
            "retained_manifest": self.retained_manifest.to_json(),
            "retained_manifest_hash": self.retained_manifest.manifest_hash,
            "source_guard": self.source_guard.to_json(),
            "source_guard_hash": self.source_guard.report_hash,
            "counters": self.counters.to_json(),
            "forbidden_modules_loaded": list(self.forbidden_modules_loaded),
            "forbidden_paths_present": list(self.forbidden_paths_present),
            "phase12_required_paths_present": list(self.phase12_required_paths_present),
            "phase12_required_paths_missing": list(self.phase12_required_paths_missing),
            "phase12_dependency_complete": self.phase12_dependency_complete,
            "attack_suite": self.attack_suite.to_json(),
            "attack_suite_hash": self.attack_suite.report_hash,
            "replay_boundary_closed": self.replay_boundary_closed,
            "phase13a_slice_closed": self.phase13a_slice_closed,
            "phase13_exit_closed": self.phase13_exit_closed,
        }


__all__ = [
    "AdversarialAttackResult",
    "AdversarialAttackSuiteReport",
    "Phase13AReplayBoundaryReport",
    "ReplayInvocationCounters",
    "ReplaySourceFinding",
    "ReplaySourceGuardReport",
    "RetainedEvidenceManifest",
    "RetainedFileRecord",
]
