from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.training_protocol import (
    TrainingReport,
    TrainingRequest,
    expected_trained_tensor,
)

_ALLOWED_IMPORTS = frozenset(
    {"argparse", "hashlib", "json", "struct", "pathlib", "torch", "__future__"}
)
_FORBIDDEN_CALLS = frozenset(
    {"eval", "exec", "compile", "__import__", "open", "breakpoint"}
)


@dataclass(frozen=True, slots=True)
class WorkerSourceGuard:
    worker_sha256: str
    imported_roots: Sequence[str]
    forbidden_findings: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v3.phase10.worker_source_guard.v1"

    @property
    def clean(self) -> bool:
        return not self.forbidden_findings

    @property
    def guard_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "worker_sha256": self.worker_sha256,
            "imported_roots": list(self.imported_roots),
            "forbidden_findings": list(self.forbidden_findings),
            "clean": self.clean,
        }


@dataclass(frozen=True, slots=True)
class TrainingProcessEvidence:
    request_hash: str
    report: TrainingReport
    source_guard: WorkerSourceGuard
    stdout_sha256: str
    stderr_sha256: str
    return_code: int
    timed_out: bool
    candidate_tensor_sha256: str
    output_root: Path

    schema_id: ClassVar[str] = "runtime.v3.phase10.training_process_evidence.v1"

    @property
    def accepted(self) -> bool:
        return (
            not self.timed_out
            and self.return_code == 0
            and self.source_guard.clean
            and self.report.request_hash == self.request_hash
            and self.report.candidate_tensor_sha256 == self.candidate_tensor_sha256
        )

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "request_hash": self.request_hash,
            "training_report": self.report.to_json(),
            "training_report_hash": self.report.report_hash,
            "source_guard": self.source_guard.to_json(),
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "candidate_tensor_sha256": self.candidate_tensor_sha256,
            "accepted": self.accepted,
        }


def default_worker_source() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "phase10_training_worker.py"


def inspect_worker_source(path: Path) -> WorkerSourceGuard:
    source = path.resolve(strict=True).read_bytes()
    tree = ast.parse(source.decode("utf-8"), filename=path.name)
    imported: set[str] = set()
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _FORBIDDEN_CALLS:
                findings.append(f"forbidden_call:{node.func.id}:{node.lineno}")
        elif isinstance(node, ast.Attribute):
            if node.attr in {"system", "popen", "socket", "urlopen", "requests"}:
                findings.append(f"forbidden_attribute:{node.attr}:{node.lineno}")
    for root in sorted(imported - _ALLOWED_IMPORTS):
        findings.append(f"forbidden_import:{root}")
    return WorkerSourceGuard(
        worker_sha256=sha256_hex(source),
        imported_roots=tuple(sorted(imported)),
        forbidden_findings=tuple(sorted(findings)),
    )


def _worker_environment() -> dict[str, str]:
    allowed = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "TMP",
        "TEMP",
        "HOME",
        "USERPROFILE",
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
    }
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "PYTHONHASHSEED": "0",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    return environment


def run_training_process(
    request: TrainingRequest,
    predecessor_tensor_path: Path,
    output_root: Path,
    *,
    worker_source: Path | None = None,
    timeout_seconds: int = 180,
) -> TrainingProcessEvidence:
    predecessor_path = predecessor_tensor_path.resolve(strict=True)
    predecessor = predecessor_path.read_bytes()
    if sha256_hex(predecessor) != request.predecessor_tensor_sha256:
        raise SchemaValidationError("phase10.training_process", "predecessor tensor binding mismatch")
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"training output already exists: {resolved_output}")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    worker = (worker_source or default_worker_source()).resolve(strict=True)
    guard = inspect_worker_source(worker)
    if not guard.clean:
        raise SchemaValidationError("phase10.training_worker", "worker source guard rejected")

    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase10-worker-",
        dir=resolved_output.parent,
    ) as temporary:
        work = Path(temporary)
        request_path = work / "request.json"
        tensor_path = work / "predecessor.i16le.bin"
        worker_path = work / "worker.py"
        staged_output = work / "output"
        request_path.write_bytes(canonical_json_bytes(request.to_json()))
        tensor_path.write_bytes(predecessor)
        shutil.copyfile(worker, worker_path)
        command = [
            sys.executable,
            "-I",
            "-B",
            worker_path.name,
            "--request",
            request_path.name,
            "--predecessor-tensor",
            tensor_path.name,
            "--output",
            staged_output.name,
        ]
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=work,
                env=_worker_environment(),
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            return_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            return_code = -1
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
        if timed_out or return_code != 0:
            raise RuntimeError(
                f"Phase 10 training worker failed: timed_out={timed_out}, "
                f"return_code={return_code}, stderr_sha256={sha256_hex(stderr)}"
            )
        observed_names = {entry.name for entry in staged_output.iterdir()}
        if observed_names != {
            "model.layers.00.attn_output.weight.i16le.bin",
            "training_report.json",
        }:
            raise SchemaValidationError("phase10.training_output", "unexpected output file set")
        candidate_path = staged_output / "model.layers.00.attn_output.weight.i16le.bin"
        candidate = candidate_path.read_bytes()
        expected = expected_trained_tensor(predecessor, request)
        if candidate != expected:
            raise SchemaValidationError(
                "phase10.training_output", "worker tensor differs from host exact recomputation"
            )
        report = TrainingReport.from_json(
            load_json_strict(
                (staged_output / "training_report.json").read_bytes(),
                require_canonical=True,
            )
        )
        if report.request_hash != request.request_hash:
            raise SchemaValidationError("phase10.training_report", "request hash mismatch")
        os.replace(staged_output, resolved_output)
    return TrainingProcessEvidence(
        request_hash=request.request_hash,
        report=report,
        source_guard=guard,
        stdout_sha256=sha256_hex(stdout),
        stderr_sha256=sha256_hex(stderr),
        return_code=return_code,
        timed_out=timed_out,
        candidate_tensor_sha256=sha256_hex(candidate),
        output_root=resolved_output,
    )


def run_training_twice(
    request: TrainingRequest,
    predecessor_tensor_path: Path,
    output_root: Path,
    *,
    worker_source: Path | None = None,
) -> tuple[TrainingProcessEvidence, TrainingProcessEvidence]:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"training replay root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    first = run_training_process(
        request,
        predecessor_tensor_path,
        root / "first",
        worker_source=worker_source,
    )
    second = run_training_process(
        request,
        predecessor_tensor_path,
        root / "second",
        worker_source=worker_source,
    )
    first_tensor = (
        first.output_root / "model.layers.00.attn_output.weight.i16le.bin"
    ).read_bytes()
    second_tensor = (
        second.output_root / "model.layers.00.attn_output.weight.i16le.bin"
    ).read_bytes()
    if first_tensor != second_tensor or first.report.to_json() != second.report.to_json():
        raise SchemaValidationError("phase10.training_replay", "fresh worker runs differ")
    return first, second


__all__ = [
    "TrainingProcessEvidence",
    "WorkerSourceGuard",
    "default_worker_source",
    "inspect_worker_source",
    "run_training_process",
    "run_training_twice",
]
