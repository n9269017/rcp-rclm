from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.torch_backend.protocol import PilotRequestBinding

PROCESS_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_process_report.v1"
SOURCE_GUARD_SCHEMA_ID: Final[str] = "runtime.pytorch_pilot_source_guard.v1"
SOURCE_GUARD_VERSION: Final[str] = "rcp-rclm-pytorch-pilot-source-guard-v1"

_FORBIDDEN_IMPORT_ROOTS: Final[frozenset[str]] = frozenset(
    {
        "aiohttp",
        "httpx",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "urllib",
    }
)
_FORBIDDEN_RUNTIME_PREFIXES: Final[Sequence[str]] = (
    "rcp_rclm_runtime.checker",
    "rcp_rclm_runtime.generator",
    "rcp_rclm_runtime.lean_bridge",
    "rcp_rclm_runtime.promotion",
    "rcp_rclm_runtime.replay",
)
_FORBIDDEN_CALLS: Final[frozenset[str]] = frozenset(
    {"compile", "eval", "exec", "__import__"}
)
ProcessVerdict = Literal["success", "reject", "indeterminate"]


@dataclass(frozen=True, slots=True)
class PilotSourceFinding:
    code: str
    line: int
    detail: str

    def to_json(self) -> dict[str, object]:
        return {"code": self.code, "line": self.line, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class PilotSourceGuardReport:
    source_path: str
    source_hash: str
    findings: Sequence[PilotSourceFinding]

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def guard_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": SOURCE_GUARD_SCHEMA_ID,
            "guard_version": SOURCE_GUARD_VERSION,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "findings": [item.to_json() for item in self.findings],
            "clean": self.clean,
        }


@dataclass(frozen=True, slots=True)
class PilotProcessReport:
    verdict: ProcessVerdict
    reason_codes: Sequence[str]
    command: Sequence[str]
    return_code: int | None
    timed_out: bool
    stdout_hash: str
    stderr_hash: str
    output_tree_hash: str | None
    proposal_hash: str | None
    source_guard_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "command", tuple(self.command))

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": PROCESS_SCHEMA_ID,
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "command": list(self.command),
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "output_tree_hash": self.output_tree_hash,
            "proposal_hash": self.proposal_hash,
            "source_guard_hash": self.source_guard_hash,
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["report_hash"] = self.report_hash
        return value


@dataclass(frozen=True, slots=True)
class PilotProcessEvidence:
    report: PilotProcessReport
    source_guard: PilotSourceGuardReport
    stdout: bytes
    stderr: bytes
    output_root: Path | None


def guard_proposal_backend_source() -> PilotSourceGuardReport:
    source_path = Path(__file__).with_name("proposal_backend.py").resolve(strict=True)
    source_bytes = source_path.read_bytes()
    try:
        text = source_bytes.decode("utf-8", errors="strict")
        tree = ast.parse(text, filename=source_path.name)
    except (UnicodeDecodeError, SyntaxError) as exc:
        finding = PilotSourceFinding(
            code="PYTORCH_SOURCE_PARSE_FAILED",
            line=getattr(exc, "lineno", None) or 1,
            detail=type(exc).__name__,
        )
        return PilotSourceGuardReport(
            source_path="rcp_rclm_runtime/torch_backend/proposal_backend.py",
            source_hash=sha256_hex(source_bytes),
            findings=(finding,),
        )
    findings: list[PilotSourceFinding] = []
    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
        for module_name in imported:
            root = module_name.split(".", 1)[0]
            if root in _FORBIDDEN_IMPORT_ROOTS:
                findings.append(
                    PilotSourceFinding(
                        "PYTORCH_SOURCE_FORBIDDEN_IMPORT",
                        node.lineno,
                        module_name,
                    )
                )
            if module_name.startswith(_FORBIDDEN_RUNTIME_PREFIXES):
                findings.append(
                    PilotSourceFinding(
                        "PYTORCH_SOURCE_PRIVILEGED_IMPORT",
                        node.lineno,
                        module_name,
                    )
                )
        if isinstance(node, ast.Call):
            called = _call_name(node.func)
            if called in _FORBIDDEN_CALLS:
                findings.append(
                    PilotSourceFinding(
                        "PYTORCH_SOURCE_DYNAMIC_EXECUTION",
                        node.lineno,
                        called,
                    )
                )
            if called in {"os.system", "os.popen"}:
                findings.append(
                    PilotSourceFinding(
                        "PYTORCH_SOURCE_PROCESS_ESCAPE",
                        node.lineno,
                        called,
                    )
                )
    findings.sort(key=lambda item: (item.line, item.code, item.detail))
    return PilotSourceGuardReport(
        source_path="rcp_rclm_runtime/torch_backend/proposal_backend.py",
        source_hash=sha256_hex(source_bytes),
        findings=tuple(findings),
    )


def run_pytorch_proposal_process(
    request: PilotRequestBinding,
    predecessor_payload_root: Path,
    output_root: Path,
) -> PilotProcessEvidence:
    source_guard = guard_proposal_backend_source()
    if not source_guard.clean:
        report = _report(
            verdict="reject",
            reasons=("PYTORCH_WORKER_SOURCE_REJECTED",),
            command=(),
            return_code=None,
            timed_out=False,
            stdout=b"",
            stderr=b"",
            output_root=None,
            proposal_hash=None,
            source_guard=source_guard,
        )
        return PilotProcessEvidence(report, source_guard, b"", b"", None)
    resolved_predecessor = predecessor_payload_root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"proposal output already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-pytorch-process-", dir=resolved_output.parent
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        request_path = temporary_root / "request.json"
        request_path.write_bytes(canonical_json_bytes(request.to_json()))
        worker_path = Path(__file__).with_name("proposal_backend.py").resolve(strict=True)
        command = (
            sys.executable,
            "-I",
            "-B",
            str(worker_path),
            "propose",
            "--request",
            str(request_path),
            "--predecessor-root",
            str(resolved_predecessor),
            "--output-root",
            str(resolved_output),
        )
        environment = _worker_environment()
        try:
            completed = subprocess.run(
                command,
                cwd=temporary_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=max(5, request.policy.time_budget_millis // 1000 + 30),
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            report = _report(
                verdict="indeterminate",
                reasons=("PYTORCH_PROCESS_TIMEOUT",),
                command=command,
                return_code=None,
                timed_out=True,
                stdout=stdout,
                stderr=stderr,
                output_root=None,
                proposal_hash=None,
                source_guard=source_guard,
            )
            return PilotProcessEvidence(report, source_guard, stdout, stderr, None)
    stdout = completed.stdout
    stderr = completed.stderr
    proposal_hash: str | None = None
    output_tree_hash: str | None = None
    reasons: Sequence[str] = ()
    verdict: ProcessVerdict = "success"
    published_root: Path | None = resolved_output
    if completed.returncode != 0:
        verdict = "indeterminate" if completed.returncode == 3 else "reject"
        reasons = ("PYTORCH_PROCESS_FAILED",)
        published_root = None
    else:
        try:
            result = load_json_strict(stdout.rstrip(b"\r\n"), require_canonical=True)
            if not isinstance(result, dict) or result.get("verdict") != "success":
                raise SchemaValidationError("pytorch_process.stdout", "non-success result")
            proposal_value = load_json_strict(
                (resolved_output / "proposal.json").read_bytes(), require_canonical=True
            )
            if not isinstance(proposal_value, dict):
                raise SchemaValidationError("pytorch_process.proposal", "expected object")
            raw_proposal_hash = proposal_value.get("proposal_hash")
            if not isinstance(raw_proposal_hash, str):
                raise SchemaValidationError(
                    "pytorch_process.proposal_hash", "expected string"
                )
            proposal_hash = raw_proposal_hash
            output_tree_hash = semantic_tree_hash(build_tree_records(resolved_output))
        except (OSError, SchemaValidationError, ValueError) as exc:
            verdict = "reject"
            reasons = ("PYTORCH_OUTPUT_INVALID", type(exc).__name__)
            published_root = None
    report = PilotProcessReport(
        verdict=verdict,
        reason_codes=reasons,
        command=command,
        return_code=completed.returncode,
        timed_out=False,
        stdout_hash=sha256_hex(stdout),
        stderr_hash=sha256_hex(stderr),
        output_tree_hash=output_tree_hash,
        proposal_hash=proposal_hash,
        source_guard_hash=source_guard.guard_hash,
    )
    return PilotProcessEvidence(report, source_guard, stdout, stderr, published_root)


def _report(
    *,
    verdict: ProcessVerdict,
    reasons: Sequence[str],
    command: Sequence[str],
    return_code: int | None,
    timed_out: bool,
    stdout: bytes,
    stderr: bytes,
    output_root: Path | None,
    proposal_hash: str | None,
    source_guard: PilotSourceGuardReport,
) -> PilotProcessReport:
    output_tree_hash = (
        None
        if output_root is None
        else semantic_tree_hash(build_tree_records(output_root))
    )
    return PilotProcessReport(
        verdict=verdict,
        reason_codes=tuple(reasons),
        command=tuple(command),
        return_code=return_code,
        timed_out=timed_out,
        stdout_hash=sha256_hex(stdout),
        stderr_hash=sha256_hex(stderr),
        output_tree_hash=output_tree_hash,
        proposal_hash=proposal_hash,
        source_guard_hash=source_guard.guard_hash,
    )


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _worker_environment() -> dict[str, str]:
    retained = {
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LD_LIBRARY_PATH",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
    environment = {
        key: value for key, value in os.environ.items() if key.upper() in retained
    }
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    return environment


__all__ = [
    "PilotProcessEvidence",
    "PilotProcessReport",
    "PilotSourceFinding",
    "PilotSourceGuardReport",
    "guard_proposal_backend_source",
    "run_pytorch_proposal_process",
]
