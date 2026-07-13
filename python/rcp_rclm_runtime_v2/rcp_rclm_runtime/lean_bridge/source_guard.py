from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.errors import RuntimeValidationError

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

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))

    @property
    def clean(self) -> bool:
        return not self.findings

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.lean_source_guard_report.v2",
            "source_hash": self.source_hash,
            "byte_count": self.byte_count,
            "clean": self.clean,
            "findings": [finding.to_json() for finding in self.findings],
        }


class LeanSourceRejected(RuntimeValidationError):
    __slots__ = ("report",)

    def __init__(self, report: SourceGuardReport) -> None:
        summary = ", ".join(
            f"{finding.token}@{finding.line}:{finding.column}"
            for finding in report.findings
        )
        super().__init__(
            "LEAN_SOURCE_FORBIDDEN_TOKEN",
            "generated_lean_source",
            summary,
        )
        self.report = report


def scan_source_bytes(source: bytes) -> SourceGuardReport:
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        finding = SourceGuardFinding(
            code="LEAN_SOURCE_INVALID_UTF8",
            token="invalid_utf8",
            line=1,
            column=1,
        )
        return SourceGuardReport(
            source_hash=sha256_hex(source),
            byte_count=len(source),
            findings=(finding,),
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
        source_hash=sha256_hex(source),
        byte_count=len(source),
        findings=tuple(findings),
    )


def scan_source_text(source: str) -> SourceGuardReport:
    return scan_source_bytes(source.encode("utf-8"))


def scan_source_file(path: Path) -> SourceGuardReport:
    return scan_source_bytes(path.read_bytes())


def require_clean_source_bytes(source: bytes) -> SourceGuardReport:
    report = scan_source_bytes(source)
    if not report.clean:
        raise LeanSourceRejected(report)
    return report


def require_clean_source_file(path: Path) -> SourceGuardReport:
    report = scan_source_file(path)
    if not report.clean:
        raise LeanSourceRejected(report)
    return report


def _line_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_newline = text.rfind("\n", 0, offset)
    column = offset + 1 if last_newline < 0 else offset - last_newline
    return line, column
