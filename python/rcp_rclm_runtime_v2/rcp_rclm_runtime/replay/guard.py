from __future__ import annotations

import ast
import importlib.util
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema.verdict import FrozenHashMap

REPLAY_SOURCE_GUARD_VERSION: Final[str] = "rcp-rclm-phase8-replay-source-guard-v1"
_REPLAY_MODULES: Final[Sequence[str]] = (
    "rcp_rclm_runtime.replay",
    "rcp_rclm_runtime.replay.bundle",
    "rcp_rclm_runtime.replay.guard",
    "rcp_rclm_runtime.replay.records",
    "rcp_rclm_runtime.replay.reference",
    "rcp_rclm_runtime.replay.reproduce",
    "rcp_rclm_runtime.generator.environment",
    "rcp_rclm_runtime.generator.reference",
    "rcp_rclm_runtime.promotion",
    "rcp_rclm_runtime.promotion.policy",
    "rcp_rclm_runtime.successor",
    "rcp_rclm_runtime.successor.budget",
)
_FORBIDDEN_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "rcp_rclm_runtime.generator.process",
        "rcp_rclm_runtime.generator.worker",
        "random",
        "secrets",
        "socket",
        "subprocess",
        "torch",
    }
)
_FORBIDDEN_CALL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "run_reference_generator_process",
        "generate_reference_proposal",
    }
)


@dataclass(frozen=True, slots=True)
class ReplaySourceFinding:
    code: str
    path: str
    line: int
    detail: str

    def __post_init__(self) -> None:
        if not self.code or not self.path or not self.detail:
            raise SchemaValidationError("phase8_replay_source_finding", "fields must be nonempty")
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 1:
            raise SchemaValidationError("phase8_replay_source_finding.line", "expected a positive integer")

    def to_json(self) -> dict[str, object]:
        return {
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ReplaySourceGuardReport:
    file_hashes: FrozenHashMap
    findings: Sequence[ReplaySourceFinding]
    guard_version: str = REPLAY_SOURCE_GUARD_VERSION

    def __post_init__(self) -> None:
        findings = tuple(self.findings)
        object.__setattr__(self, "findings", findings)
        expected = tuple(sorted(findings, key=lambda item: (item.path, item.line, item.code, item.detail)))
        if findings != expected:
            raise SchemaValidationError("phase8_replay_source_guard.findings", "findings must be sorted")
        if self.guard_version != REPLAY_SOURCE_GUARD_VERSION:
            raise SchemaValidationError(
                "phase8_replay_source_guard.guard_version",
                f"expected {REPLAY_SOURCE_GUARD_VERSION}",
            )

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.phase8_replay_source_guard.v2",
            "guard_version": self.guard_version,
            "file_hashes": self.file_hashes.to_json(),
            "findings": [finding.to_json() for finding in self.findings],
            "clean": self.clean,
        }


def guard_independent_replay_source() -> ReplaySourceGuardReport:
    findings: list[ReplaySourceFinding] = []
    file_hashes: dict[str, str] = {}
    for module_name in _REPLAY_MODULES:
        relative_path, source = _module_source(module_name)
        file_hashes[relative_path] = sha256_hex(source)
        findings.extend(scan_replay_source_bytes(relative_path, source))
    findings.sort(key=lambda item: (item.path, item.line, item.code, item.detail))
    return ReplaySourceGuardReport(
        file_hashes=FrozenHashMap.from_mapping(
            file_hashes,
            "phase8_replay_source_guard.file_hashes",
        ),
        findings=tuple(findings),
    )


def scan_replay_source_bytes(path: str, source: bytes) -> Sequence[ReplaySourceFinding]:
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return (
            ReplaySourceFinding(
                code="REPLAY_SOURCE_INVALID_UTF8",
                path=path,
                line=1,
                detail=str(exc),
            ),
        )
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        return (
            ReplaySourceFinding(
                code="REPLAY_SOURCE_SYNTAX_ERROR",
                path=path,
                line=exc.lineno or 1,
                detail=exc.msg,
            ),
        )
    findings: list[ReplaySourceFinding] = []
    for node in ast.walk(tree):
        imported: set[str] = set()
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        for name in sorted(imported):
            if _is_forbidden_import(name):
                findings.append(
                    ReplaySourceFinding(
                        code="REPLAY_FORBIDDEN_IMPORT",
                        path=path,
                        line=node.lineno,
                        detail=name,
                    )
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _FORBIDDEN_CALL_NAMES:
                findings.append(
                    ReplaySourceFinding(
                        code="REPLAY_GENERATOR_INVOCATION",
                        path=path,
                        line=node.lineno,
                        detail=node.func.id,
                    )
                )
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_CALL_NAMES:
            findings.append(
                ReplaySourceFinding(
                    code="REPLAY_GENERATOR_INVOCATION",
                    path=path,
                    line=node.lineno,
                    detail=node.attr,
                )
            )
    return tuple(findings)


def _is_forbidden_import(name: str) -> bool:
    return any(name == forbidden or name.startswith(f"{forbidden}.") for forbidden in _FORBIDDEN_IMPORTS)


def _module_source(module_name: str) -> tuple[str, bytes]:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"replay module is not importable: {module_name}")
    path = Path(spec.origin).resolve(strict=True)
    if not path.is_file():
        raise RuntimeError(f"replay module source is not a regular file: {module_name}")
    module_path = "/".join(module_name.split("."))
    relative = (
        f"{module_path}/__init__.py"
        if path.name == "__init__.py"
        else f"{module_path}.py"
    )
    return relative, path.read_bytes()


__all__ = [
    "REPLAY_SOURCE_GUARD_VERSION",
    "ReplaySourceFinding",
    "ReplaySourceGuardReport",
    "guard_independent_replay_source",
    "scan_replay_source_bytes",
]
