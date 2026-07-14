from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.generator.protocol import (
    GeneratorReasonCode,
    ReferenceGeneratorInputRecord,
    ReferenceProposalRecord,
)
from rcp_rclm_runtime.generator.records import (
    GeneratorProcessReport,
    WorkerSourceFinding,
    WorkerSourceGuardReport,
)

REFERENCE_PACKAGE_MODULE: Final[str] = "rcp_rclm_runtime.generator"
REFERENCE_WORKER_MODULE: Final[str] = "rcp_rclm_runtime.generator.worker"
REFERENCE_GRAMMAR_MODULE: Final[str] = "rcp_rclm_runtime.generator.grammar"
REFERENCE_PROTOCOL_MODULE: Final[str] = "rcp_rclm_runtime.generator.protocol"
WORKER_SOURCE_GUARD_VERSION: Final[str] = "rcp-rclm-phase5a-worker-source-guard-v1"
REFERENCE_PROCESS_POLICY_ID: Final[str] = "rcp-rclm-phase5a-isolated-stdio-v1"
_BANNED_IMPORT_ROOTS: Final[frozenset[str]] = frozenset(
    {
        "ctypes",
        "ftplib",
        "http",
        "importlib",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "tempfile",
        "urllib",
        "webbrowser",
    }
)
_BANNED_CALL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
        "input",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
    }
)
_BANNED_CALL_ATTRIBUTES: Final[frozenset[str]] = frozenset(
    {
        "connect",
        "create_connection",
        "open",
        "popen",
        "run",
        "system",
        "write_bytes",
        "write_text",
    }
)
_BANNED_ATTRIBUTE_READS: Final[frozenset[str]] = frozenset(
    {
        "argv",
        "executable",
        "meta_path",
        "modules",
        "path",
        "path_hooks",
    }
)
_ALLOWED_RECORD_GETATTR_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "budget_units_used",
        "formal_source_commit",
        "grammar_id",
        "implementation_id",
        "manifest_hash",
        "max_budget_units",
        "max_proof_length",
        "max_proposals",
        "max_word_depth",
        "objective_hash",
        "policy_hash",
        "policy_version",
        "predecessor_manifest_hash",
        "process_timeout_seconds",
        "proof_length",
        "request_hash",
        "semantic_tree_hash",
        "state_hash",
        "word_depth",
    }
)
_ALLOWED_RUNTIME_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "rcp_rclm_runtime._version",
        "rcp_rclm_runtime.canonical.hashing",
        "rcp_rclm_runtime.canonical.json",
        "rcp_rclm_runtime.errors",
        "rcp_rclm_runtime.generator.grammar",
        "rcp_rclm_runtime.generator.protocol",
        "rcp_rclm_runtime.schema._common",
        "rcp_rclm_runtime.schema.state",
    }
)
_ALLOWED_ENVIRONMENT_KEYS: Final[Sequence[str]] = (
    "COMSPEC",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)
REFERENCE_PROCESS_ENVIRONMENT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.phase5a_process_environment_policy.v2",
        "policy_id": REFERENCE_PROCESS_POLICY_ID,
        "input_channel": "stdin",
        "output_channel": "stdout",
        "working_directory": "fresh_empty_temporary_directory",
        "python_isolated_mode": True,
        "python_bytecode_writes": False,
        "python_utf8_mode": True,
        "hash_order_independent_canonical_output": True,
        "allowed_environment_keys": list(_ALLOWED_ENVIRONMENT_KEYS),
        "generator_file_arguments": [],
        "generator_network_endpoints": [],
        "generator_write_handles": [],
    }
)


@dataclass(frozen=True, slots=True)
class GeneratorProcessEvidence:
    input_bytes: bytes
    stdout: bytes
    stderr: bytes
    source_guard: WorkerSourceGuardReport
    proposal: ReferenceProposalRecord | None
    report: GeneratorProcessReport


def guard_reference_worker_source() -> WorkerSourceGuardReport:
    findings: list[WorkerSourceFinding] = []
    file_hashes: dict[str, str] = {}
    for module_name in (
        REFERENCE_PACKAGE_MODULE,
        REFERENCE_WORKER_MODULE,
        REFERENCE_GRAMMAR_MODULE,
        REFERENCE_PROTOCOL_MODULE,
    ):
        relative_path, source = _module_source(module_name)
        file_hashes[relative_path] = sha256_hex(source)
        findings.extend(scan_generator_source_bytes(relative_path, source))
    findings.sort(key=lambda item: (item.path, item.line, item.code, item.detail))
    return WorkerSourceGuardReport(
        guard_version=WORKER_SOURCE_GUARD_VERSION,
        file_hashes=FrozenHashMap.from_mapping(
            file_hashes,
            "worker_source_guard.file_hashes",
        ),
        findings=tuple(findings),
    )


def run_reference_generator_process(
    request: ReferenceGeneratorInputRecord,
) -> GeneratorProcessEvidence:
    input_bytes = canonical_json_bytes(request.to_json())
    source_guard = guard_reference_worker_source()
    if not source_guard.clean:
        empty_hash = sha256_hex(b"")
        report = GeneratorProcessReport(
            verdict="failure",
            reason_codes=(GeneratorReasonCode.WORKER_SOURCE_REJECTED,),
            input_hash=request.input_hash,
            stdout_hash=empty_hash,
            stderr_hash=empty_hash,
            worker_guard_hash=source_guard.report_hash,
            exit_code=None,
            timed_out=False,
            proposal_hash=None,
        )
        return GeneratorProcessEvidence(
            input_bytes=input_bytes,
            stdout=b"",
            stderr=b"",
            source_guard=source_guard,
            proposal=None,
            report=report,
        )

    environment = _sanitized_environment(os.environ)
    command = (
        sys.executable,
        "-I",
        "-B",
        "-X",
        "utf8",
        "-m",
        REFERENCE_WORKER_MODULE,
    )
    stdout = b""
    stderr = b""
    exit_code: int | None = None
    timed_out = False
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase5a-") as temporary_directory:
        try:
            completed = subprocess.run(
                command,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=temporary_directory,
                env=environment,
                check=False,
                timeout=request.budget.process_timeout_seconds,
                close_fds=True,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = _timeout_bytes(exc.stdout)
            stderr = _timeout_bytes(exc.stderr)

    proposal: ReferenceProposalRecord | None = None
    reasons: list[GeneratorReasonCode] = []
    if timed_out:
        verdict = "indeterminate"
        reasons.append(GeneratorReasonCode.PROCESS_TIMEOUT)
    elif exit_code != 0:
        verdict = "failure"
        reasons.append(GeneratorReasonCode.PROCESS_FAILED)
    else:
        try:
            parsed = load_json_strict(stdout, require_canonical=True)
            proposal = ReferenceProposalRecord.from_json(parsed)
        except (RuntimeValidationError, TypeError, ValueError):
            verdict = "failure"
            reasons.append(GeneratorReasonCode.OUTPUT_MALFORMED)
        else:
            verdict = "success"

    report = GeneratorProcessReport(
        verdict=verdict,
        reason_codes=tuple(reasons),
        input_hash=request.input_hash,
        stdout_hash=sha256_hex(stdout),
        stderr_hash=sha256_hex(stderr),
        worker_guard_hash=source_guard.report_hash,
        exit_code=exit_code,
        timed_out=timed_out,
        proposal_hash=None if proposal is None else proposal.proposal_hash,
    )
    return GeneratorProcessEvidence(
        input_bytes=input_bytes,
        stdout=stdout,
        stderr=stderr,
        source_guard=source_guard,
        proposal=proposal,
        report=report,
    )


def _module_source(module_name: str) -> tuple[str, bytes]:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"generator module is not importable: {module_name}")
    path = Path(spec.origin).resolve(strict=True)
    if not path.is_file():
        raise RuntimeError(f"generator module source is not a regular file: {module_name}")
    module_path = "/".join(module_name.split("."))
    relative = (
        f"{module_path}/__init__.py"
        if path.name == "__init__.py"
        else f"{module_path}.py"
    )
    return relative, path.read_bytes()


def scan_generator_source_bytes(
    path: str,
    source: bytes,
) -> Sequence[WorkerSourceFinding]:
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return (
            WorkerSourceFinding(
                code="GENERATOR_SOURCE_INVALID_UTF8",
                path=path,
                line=1,
                detail=str(exc),
            ),
        )
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        return (
            WorkerSourceFinding(
                code="GENERATOR_SOURCE_SYNTAX_ERROR",
                path=path,
                line=exc.lineno or 1,
                detail=exc.msg,
            ),
        )
    findings: list[WorkerSourceFinding] = []
    for node in ast.walk(tree):
        imported_roots: set[str] = set()
        imported_modules: set[str] = set()
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
            imported_modules.add(node.module)
        for root in sorted(imported_roots & _BANNED_IMPORT_ROOTS):
            findings.append(
                WorkerSourceFinding(
                    code="GENERATOR_FORBIDDEN_IMPORT",
                    path=path,
                    line=node.lineno,
                    detail=root,
                )
            )
        for module_name in sorted(imported_modules):
            if (
                module_name.startswith("rcp_rclm_runtime.")
                and module_name not in _ALLOWED_RUNTIME_IMPORTS
            ):
                findings.append(
                    WorkerSourceFinding(
                        code="GENERATOR_PRIVILEGED_IMPORT",
                        path=path,
                        line=node.lineno,
                        detail=module_name,
                    )
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if (
                node.func.id in _BANNED_CALL_NAMES
                and not _allowed_record_getattr(node)
            ):
                findings.append(
                    WorkerSourceFinding(
                        code="GENERATOR_FORBIDDEN_CALL",
                        path=path,
                        line=node.lineno,
                        detail=node.func.id,
                    )
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _BANNED_CALL_ATTRIBUTES:
                findings.append(
                    WorkerSourceFinding(
                        code="GENERATOR_FORBIDDEN_ATTRIBUTE_CALL",
                        path=path,
                        line=node.lineno,
                        detail=node.func.attr,
                    )
                )
        if isinstance(node, ast.Attribute) and node.attr in _BANNED_ATTRIBUTE_READS:
            findings.append(
                WorkerSourceFinding(
                    code="GENERATOR_FORBIDDEN_ATTRIBUTE_READ",
                    path=path,
                    line=node.lineno,
                    detail=node.attr,
                )
            )
    return tuple(findings)


def _allowed_record_getattr(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "getattr":
        return False
    if len(node.args) != 2 or node.keywords:
        return False
    owner, field = node.args
    return (
        isinstance(owner, ast.Name)
        and owner.id == "self"
        and isinstance(field, ast.Constant)
        and isinstance(field.value, str)
        and field.value in _ALLOWED_RECORD_GETATTR_FIELDS
    )


def _sanitized_environment(source: Mapping[str, str]) -> dict[str, str]:
    environment = {
        key: source[key]
        for key in _ALLOWED_ENVIRONMENT_KEYS
        if key in source and source[key]
    }
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    return environment


def _timeout_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")
