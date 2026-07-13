from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Sequence
from typing import ClassVar, Final, Literal, Mapping, TypeAlias

from rcp_rclm_runtime._version import CONTRACT_VERSION, LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
)

VerdictName: TypeAlias = Literal["accept", "reject", "indeterminate"]
LeanVerdictName: TypeAlias = Literal["accept", "reject"]

CHECK_VERDICT_SCHEMA_ID: Final[str] = "runtime.check_verdict.v2"
LEAN_VERIFIER_REPORT_SCHEMA_ID: Final[str] = "runtime.lean_verifier_report.v2"


class ReasonCode(StrEnum):
    SCHEMA_UNKNOWN = "SCHEMA_UNKNOWN"
    SCHEMA_MALFORMED = "SCHEMA_MALFORMED"
    CANONICALIZATION_FAILED = "CANONICALIZATION_FAILED"
    HASH_MISMATCH = "HASH_MISMATCH"
    PARENT_LINK_MISMATCH = "PARENT_LINK_MISMATCH"
    TRUST_ANCHOR_CHANGED = "TRUST_ANCHOR_CHANGED"
    UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    TYPED_SUCCESSOR_FAILED = "TYPED_SUCCESSOR_FAILED"
    RESIDUAL_POSITIVE = "RESIDUAL_POSITIVE"
    NONLOSS_FAILED = "NONLOSS_FAILED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    INVARIANT_FAILED = "INVARIANT_FAILED"
    PROGRESS_REGRESSION = "PROGRESS_REGRESSION"
    STRICT_WITNESS_FAILED = "STRICT_WITNESS_FAILED"
    TRUST_INVALID = "TRUST_INVALID"
    RESOURCE_INVALID = "RESOURCE_INVALID"
    CONTAINMENT_FAILED = "CONTAINMENT_FAILED"
    SUCCESSOR_DOMAIN_FAILED = "SUCCESSOR_DOMAIN_FAILED"
    REFINEMENT_MISMATCH = "REFINEMENT_MISMATCH"
    MONITOR_FAILED = "MONITOR_FAILED"
    NUMERIC_INDETERMINATE = "NUMERIC_INDETERMINATE"
    LEAN_SOURCE_FORBIDDEN_TOKEN = "LEAN_SOURCE_FORBIDDEN_TOKEN"
    LEAN_VERIFIER_FAILED = "LEAN_VERIFIER_FAILED"
    PROVENANCE_FAILED = "PROVENANCE_FAILED"
    MANUAL_REPAIR_DETECTED = "MANUAL_REPAIR_DETECTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class FrozenHashMap:
    entries: Sequence[tuple[str, str]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))
        keys = [key for key, _ in self.entries]
        if keys != sorted(keys):
            raise SchemaValidationError("hash_map", "hash map entries must be key-sorted")
        if len(keys) != len(set(keys)):
            raise SchemaValidationError("hash_map", "duplicate hash map key")
        for key, value in self.entries:
            require_string(key, "hash_map.key")
            validate_hash256(value, f"hash_map.{key}")

    @classmethod
    def from_mapping(cls, value: Mapping[str, str], path: str) -> FrozenHashMap:
        entries: list[tuple[str, str]] = []
        for key, hash_value in value.items():
            require_string(key, f"{path}.key")
            validate_hash256(hash_value, f"{path}.{key}")
            entries.append((key, hash_value))
        return cls(tuple(sorted(entries)))

    def to_json(self) -> dict[str, str]:
        return dict(self.entries)


@dataclass(frozen=True, slots=True)
class CheckVerdictRecord:
    verdict: VerdictName
    reason_codes: Sequence[ReasonCode]
    input_hashes: FrozenHashMap
    evidence_hashes: FrozenHashMap
    checker_implementation_hash: str
    lean_verifier_report_hash: str
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = CHECK_VERDICT_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError("check_verdict.verdict", f"unknown verdict: {self.verdict}")
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "check_verdict.contract_version", f"expected {CONTRACT_VERSION}"
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError("check_verdict.reason_codes", "reason codes must be unique")
        if self.verdict == "accept" and self.reason_codes:
            raise SchemaValidationError(
                "check_verdict.reason_codes", "accept verdict must have no failure reason codes"
            )
        if self.verdict != "accept" and not self.reason_codes:
            raise SchemaValidationError(
                "check_verdict.reason_codes", "nonaccepting verdict requires at least one reason code"
            )
        validate_hash256(
            self.checker_implementation_hash,
            "check_verdict.checker_implementation_hash",
        )
        validate_hash256(
            self.lean_verifier_report_hash,
            "check_verdict.lean_verifier_report_hash",
        )

    @classmethod
    def from_json(cls, value: object, path: str = "check_verdict") -> CheckVerdictRecord:
        fields = {
            "schema_id",
            "contract_version",
            "verdict",
            "reason_codes",
            "input_hashes",
            "evidence_hashes",
            "checker_implementation_hash",
            "lean_verifier_report_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        contract_version = require_string(obj["contract_version"], f"{path}.contract_version")
        verdict = require_string(obj["verdict"], f"{path}.verdict")
        if verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(f"{path}.verdict", f"unknown verdict: {verdict}")
        reasons_raw = obj["reason_codes"]
        if not isinstance(reasons_raw, list):
            raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
        reasons: list[ReasonCode] = []
        for index, reason_raw in enumerate(reasons_raw):
            reason_text = require_string(reason_raw, f"{path}.reason_codes[{index}]")
            try:
                reasons.append(ReasonCode(reason_text))
            except ValueError as exc:
                raise SchemaValidationError(
                    f"{path}.reason_codes[{index}]", f"unknown reason code: {reason_text}"
                ) from exc
        input_hashes_raw = obj["input_hashes"]
        evidence_hashes_raw = obj["evidence_hashes"]
        if not isinstance(input_hashes_raw, Mapping):
            raise SchemaValidationError(f"{path}.input_hashes", "expected an object")
        if not isinstance(evidence_hashes_raw, Mapping):
            raise SchemaValidationError(f"{path}.evidence_hashes", "expected an object")
        input_hashes = FrozenHashMap.from_mapping(
            _string_hash_mapping(input_hashes_raw, f"{path}.input_hashes"),
            f"{path}.input_hashes",
        )
        evidence_hashes = FrozenHashMap.from_mapping(
            _string_hash_mapping(evidence_hashes_raw, f"{path}.evidence_hashes"),
            f"{path}.evidence_hashes",
        )
        checker_hash = require_string(
            obj["checker_implementation_hash"],
            f"{path}.checker_implementation_hash",
        )
        verifier_hash = require_string(
            obj["lean_verifier_report_hash"],
            f"{path}.lean_verifier_report_hash",
        )
        return cls(
            verdict=verdict,
            reason_codes=tuple(reasons),
            input_hashes=input_hashes,
            evidence_hashes=evidence_hashes,
            checker_implementation_hash=checker_hash,
            lean_verifier_report_hash=verifier_hash,
            contract_version=contract_version,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "verdict": self.verdict,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "input_hashes": self.input_hashes.to_json(),
            "evidence_hashes": self.evidence_hashes.to_json(),
            "checker_implementation_hash": self.checker_implementation_hash,
            "lean_verifier_report_hash": self.lean_verifier_report_hash,
        }


@dataclass(frozen=True, slots=True)
class LeanVerifierReportRecord:
    verdict: LeanVerdictName
    source_hash: str
    exit_code: int
    stdout_hash: str
    stderr_hash: str
    forbidden_tokens: Sequence[str] = ()
    toolchain: str = LEAN_TOOLCHAIN
    mathlib_commit: str = MATHLIB_COMMIT

    schema_id: ClassVar[str] = LEAN_VERIFIER_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "forbidden_tokens", tuple(self.forbidden_tokens))
        if self.verdict not in {"accept", "reject"}:
            raise SchemaValidationError("lean_report.verdict", f"unknown verdict: {self.verdict}")
        if self.toolchain != LEAN_TOOLCHAIN:
            raise SchemaValidationError("lean_report.toolchain", f"expected {LEAN_TOOLCHAIN}")
        if self.mathlib_commit != MATHLIB_COMMIT:
            raise SchemaValidationError("lean_report.mathlib_commit", f"expected {MATHLIB_COMMIT}")
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise SchemaValidationError("lean_report.exit_code", "expected an integer")
        for field_name in ("source_hash", "stdout_hash", "stderr_hash"):
            validate_hash256(getattr(self, field_name), f"lean_report.{field_name}")
        if self.forbidden_tokens:
            raise SchemaValidationError(
                "lean_report.forbidden_tokens",
                "serialized verifier report requires the pre-compilation source guard to be clean",
            )
        if self.verdict == "accept" and self.exit_code != 0:
            raise SchemaValidationError(
                "lean_report.exit_code", "accept verdict requires zero compiler exit code"
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "lean_verifier_report",
    ) -> LeanVerifierReportRecord:
        fields = {
            "schema_id",
            "verdict",
            "source_hash",
            "toolchain",
            "mathlib_commit",
            "exit_code",
            "stdout_hash",
            "stderr_hash",
            "forbidden_tokens",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        verdict = require_string(obj["verdict"], f"{path}.verdict")
        if verdict not in {"accept", "reject"}:
            raise SchemaValidationError(f"{path}.verdict", f"unknown verdict: {verdict}")
        forbidden = obj["forbidden_tokens"]
        if not isinstance(forbidden, list):
            raise SchemaValidationError(f"{path}.forbidden_tokens", "expected an array")
        forbidden_tokens = tuple(
            require_string(item, f"{path}.forbidden_tokens[{index}]")
            for index, item in enumerate(forbidden)
        )
        return cls(
            verdict=verdict,
            source_hash=require_string(obj["source_hash"], f"{path}.source_hash"),
            toolchain=require_string(obj["toolchain"], f"{path}.toolchain"),
            mathlib_commit=require_string(obj["mathlib_commit"], f"{path}.mathlib_commit"),
            exit_code=require_structural_integer(obj["exit_code"], f"{path}.exit_code"),
            stdout_hash=require_string(obj["stdout_hash"], f"{path}.stdout_hash"),
            stderr_hash=require_string(obj["stderr_hash"], f"{path}.stderr_hash"),
            forbidden_tokens=forbidden_tokens,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "verdict": self.verdict,
            "source_hash": self.source_hash,
            "toolchain": self.toolchain,
            "mathlib_commit": self.mathlib_commit,
            "exit_code": self.exit_code,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "forbidden_tokens": list(self.forbidden_tokens),
        }


def _string_hash_mapping(value: Mapping[object, object], path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, hash_value in value.items():
        if not isinstance(key, str) or not isinstance(hash_value, str):
            raise SchemaValidationError(path, "hash map keys and values must be strings")
        result[key] = hash_value
    return result
