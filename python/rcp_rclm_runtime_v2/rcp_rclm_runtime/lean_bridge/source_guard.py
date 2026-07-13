from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.errors import RuntimeValidationError

SOURCE_GUARD_VERSION: Final[str] = "rcp-rclm-lean-source-guard-v2.0.0"
_DEFAULT_SOURCE_PATH: Final[str] = "generated_lean_source"
_FORBIDDEN_PROOF_TOKEN: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])(sorryAx|sorry|admit)(?![A-Za-z0-9_])"
)
_LOCAL_AXIOM_DECLARATION: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*(?:private[ \t]+)?axiom[ \t]+",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class SourceGuardFinding:
    code: str
    token: str
    line: int
    column: int

    def to_json(self) -> dict[str, object]:
        return {
            "code": self.code,
            "token": self.token,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True, slots=True)
class SourceGuardReport:
    source_hash: str
    byte_count: int
    findings: Sequence[SourceGuardFinding]
    source_path: str = _DEFAULT_SOURCE_PATH
    gate_version: str = SOURCE_GUARD_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))
        _validate_source_path(self.source_path)
        if self.gate_version != SOURCE_GUARD_VERSION:
            raise RuntimeValidationError(
                "LEAN_SOURCE_GUARD_VERSION_MISMATCH",
                "gate_version",
                f"expected {SOURCE_GUARD_VERSION}, found {self.gate_version}",
            )
        if isinstance(self.byte_count, bool) or not isinstance(self.byte_count, int):
            raise RuntimeValidationError(
                "LEAN_SOURCE_BYTE_COUNT_INVALID",
                "byte_count",
                "byte count must be an integer",
            )
        if self.byte_count < 0:
            raise RuntimeValidationError(
                "LEAN_SOURCE_BYTE_COUNT_INVALID",
                "byte_count",
                "byte count must be nonnegative",
            )

    @property
    def clean(self) -> bool:
        return not self.findings

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.lean_source_guard_report.v2",
            "gate_version": self.gate_version,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "byte_count": self.byte_count,
            "clean": self.clean,
            "findings": [finding.to_json() for finding in self.findings],
        }


class LeanSourceRejected(RuntimeValidationError):
    __slots__ = ("report",)

    def __init__(self, report: SourceGuardReport) -> None:
        findings = ", ".join(
            f"{finding.token}@{finding.line}:{finding.column}"
            for finding in report.findings
        )
        detail = (
            f"gate_version={report.gate_version}; "
            f"source_sha256={report.source_hash}; findings={findings}"
        )
        super().__init__(
            "LEAN_SOURCE_FORBIDDEN_TOKEN",
            report.source_path,
            detail,
        )
        self.report = report


def scan_source_bytes(
    source: bytes,
    *,
    source_path: str | None = None,
) -> SourceGuardReport:
    source_hash = sha256_hex(source)
    resolved_source_path = (
        f"generated/sha256-{source_hash}.lean"
        if source_path is None
        else source_path
    )
    _validate_source_path(resolved_source_path)
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        finding = SourceGuardFinding(
            code="LEAN_SOURCE_INVALID_UTF8",
            token="invalid_utf8",
            line=1,
            column=1,
        )
        return SourceGuardReport(
            source_hash=source_hash,
            byte_count=len(source),
            findings=(finding,),
            source_path=resolved_source_path,
        )

    findings: list[SourceGuardFinding] = []
    for match in _FORBIDDEN_PROOF_TOKEN.finditer(text):
        line, column = _line_column(text, match.start())
        findings.append(
            SourceGuardFinding(
                code="LEAN_SOURCE_FORBIDDEN_TOKEN",
                token=match.group(1),
                line=line,
                column=column,
            )
        )
    for match in _LOCAL_AXIOM_DECLARATION.finditer(text):
        line, column = _line_column(text, match.start())
        findings.append(
            SourceGuardFinding(
                code="LEAN_SOURCE_LOCAL_AXIOM",
                token="axiom",
                line=line,
                column=column,
            )
        )
    findings.sort(key=lambda item: (item.line, item.column, item.code, item.token))
    return SourceGuardReport(
        source_hash=source_hash,
        byte_count=len(source),
        findings=tuple(findings),
        source_path=resolved_source_path,
    )


def scan_source_text(
    source: str,
    *,
    source_path: str | None = None,
) -> SourceGuardReport:
    return scan_source_bytes(source.encode("utf-8"), source_path=source_path)


def scan_source_file(path: Path) -> SourceGuardReport:
    return scan_source_bytes(path.read_bytes(), source_path=path.as_posix())


def require_clean_source_bytes(
    source: bytes,
    *,
    source_path: str | None = None,
) -> SourceGuardReport:
    report = scan_source_bytes(source, source_path=source_path)
    if not report.clean:
        raise LeanSourceRejected(report)
    return report


def require_clean_source_file(path: Path) -> SourceGuardReport:
    report = scan_source_file(path)
    if not report.clean:
        raise LeanSourceRejected(report)
    return report


def _validate_source_path(source_path: str) -> None:
    if not isinstance(source_path, str) or not source_path:
        raise RuntimeValidationError(
            "LEAN_SOURCE_PATH_INVALID",
            "source_path",
            "source path must be a nonempty string",
        )
    if "\x00" in source_path:
        raise RuntimeValidationError(
            "LEAN_SOURCE_PATH_INVALID",
            "source_path",
            "source path must not contain a NUL byte",
        )


def _line_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_newline = text.rfind("\n", 0, offset)
    column = offset + 1 if last_newline < 0 else offset - last_newline
    return line, column
