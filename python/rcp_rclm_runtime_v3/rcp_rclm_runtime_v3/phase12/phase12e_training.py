from __future__ import annotations

import ast
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.package import load_package_components
from rcp_rclm_runtime_v3.phase12.phase12e_tasks import (
    PHASE12E_ADAPTER_ROUTE_MAGIC,
    phase12e_adapter_training_manifest,
    selected_phase12e_adapter_spec,
)


if TYPE_CHECKING:
    from rcp_rclm_runtime_v3.phase12.phase12e_lifecycle import Phase12EReference

PHASE12E_TRAINING_SCHEMA_ID: Final[str] = "runtime.v3.phase12e.training_request.v1"
_ALLOWED_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "__future__",
        "argparse",
        "pathlib",
        "struct",
        "torch",
        "warnings",
        "rcp_rclm_runtime",
    }
)
_FORBIDDEN_CALLS: Final[frozenset[str]] = frozenset(
    {"eval", "exec", "compile", "__import__", "open", "breakpoint"}
)


def default_phase12e_worker_source() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "phase12e_training_worker.py"


def phase12e_training_request(reference: Phase12EReference) -> dict[str, object]:
    _, architecture, _, _, adapter = load_package_components(reference.semantic_candidate.root)
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None:
        raise SchemaValidationError("phase12e.training", "selected adapter tensor is missing")
    return {
        "schema_id": PHASE12E_TRAINING_SCHEMA_ID,
        "transition_id": reference.semantic_candidate.update.transition_id,
        "proposal_hash": reference.proposal.report_hash,
        "active_package_hash": reference.phase12d.semantic_candidate.manifest.package_hash,
        "candidate_package_hash": reference.semantic_candidate.manifest.package_hash,
        "training_data_manifest_hash": str(phase12e_adapter_training_manifest(tensor_element_count=record.spec.element_count)["manifest_hash"]),
        "adapter_tensor_name": record.spec.name,
        "adapter_tensor_path": record.spec.path,
        "tensor_element_count": record.spec.element_count,
        "target_raw_values": list(PHASE12E_ADAPTER_ROUTE_MAGIC),
        "optimizer": "sgd",
        "optimizer_steps": 1,
        "seed": reference.proposal.program.training_policy.seed,
        "heldout_material_present": False,
    }


def _inspect_worker_source(path: Path) -> dict[str, object]:
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
        elif isinstance(node, ast.Attribute) and node.attr in {
            "system",
            "popen",
            "socket",
            "urlopen",
            "requests",
        }:
            findings.append(f"forbidden_attribute:{node.attr}:{node.lineno}")
    for root in sorted(imported - _ALLOWED_IMPORTS):
        findings.append(f"forbidden_import:{root}")
    content = {
        "schema_id": "runtime.v3.phase12e.training_worker_source_guard.v1",
        "worker_sha256": sha256_hex(source),
        "imported_roots": sorted(imported),
        "forbidden_findings": sorted(findings),
        "clean": not findings,
    }
    result = dict(content)
    result["guard_hash"] = canonical_json_hash(content)
    return result


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


@dataclass(frozen=True, slots=True)
class Phase12ETrainingProcessEvidence:
    request_hash: str
    worker_source_guard: dict[str, object]
    worker_report: dict[str, object]
    candidate_tensor_sha256: str
    stdout_sha256: str
    stderr_sha256: str
    return_code: int
    timed_out: bool
    output_root: Path

    schema_id: ClassVar[str] = "runtime.v3.phase12e.training_process_evidence.v1"

    @property
    def acceptance_checks(self) -> dict[str, bool]:
        return {
            "not_timed_out": not self.timed_out,
            "return_code_zero": self.return_code == 0,
            "worker_source_guard_clean": self.worker_source_guard.get("clean") is True,
            "worker_report_accepted": self.worker_report.get("accepted") is True,
            "request_hash_matches": self.worker_report.get("request_hash") == self.request_hash,
            "candidate_tensor_hash_matches": (
                self.worker_report.get("candidate_tensor_sha256")
                == self.candidate_tensor_sha256
            ),
            "heldout_material_not_consumed": (
                self.worker_report.get("heldout_material_consumed") is False
            ),
            "stdout_empty": self.stdout_sha256 == sha256_hex(b""),
            "stderr_empty": self.stderr_sha256 == sha256_hex(b""),
        }

    @property
    def accepted(self) -> bool:
        return all(self.acceptance_checks.values())

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "acceptance_checks": self.acceptance_checks,
            "request_hash": self.request_hash,
            "worker_source_guard": dict(self.worker_source_guard),
            "worker_report": dict(self.worker_report),
            "candidate_tensor_sha256": self.candidate_tensor_sha256,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
        }


def _run_worker(
    request: dict[str, object],
    output_root: Path,
    *,
    worker_source: Path,
    timeout_seconds: int = 180,
) -> Phase12ETrainingProcessEvidence:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12E training output already exists: {root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    guard = _inspect_worker_source(worker_source)
    if guard["clean"] is not True:
        raise SchemaValidationError("phase12e.training_worker", "worker source guard rejected")
    request_hash = canonical_json_hash(request)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12e-worker-", dir=root.parent) as temporary:
        work = Path(temporary)
        request_path = work / "request.json"
        worker_path = work / "worker.py"
        tensor_path = work / "candidate.i16le.bin"
        report_path = work / "training_report.json"
        request_path.write_bytes(canonical_json_bytes(request))
        shutil.copyfile(worker_source.resolve(strict=True), worker_path)
        command = [
            sys.executable,
            "-I",
            "-B",
            worker_path.name,
            "--request",
            request_path.name,
            "--tensor-out",
            tensor_path.name,
            "--report-out",
            report_path.name,
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
                "Phase 12E training worker failed: "
                f"timed_out={timed_out}, return_code={return_code}, "
                f"stderr_sha256={sha256_hex(stderr)}"
            )
        if not tensor_path.is_file() or not report_path.is_file():
            raise SchemaValidationError("phase12e.training_output", "worker output is incomplete")
        candidate = tensor_path.read_bytes()
        report_value = load_json_strict(report_path.read_bytes(), require_canonical=True)
        if not isinstance(report_value, dict):
            raise SchemaValidationError("phase12e.training_report", "expected an object")
        element_count = request["tensor_element_count"]
        if isinstance(element_count, bool) or not isinstance(element_count, int):
            raise SchemaValidationError("phase12e.training_request", "element count is invalid")
        expected_values = list(PHASE12E_ADAPTER_ROUTE_MAGIC) + [0] * (element_count - 4)
        expected = struct.pack("<" + "h" * element_count, *expected_values)
        if candidate != expected:
            raise SchemaValidationError(
                "phase12e.training_output",
                "worker tensor differs from host exact recomputation",
            )
        staged = work / "output"
        staged.mkdir()
        (staged / "candidate.i16le.bin").write_bytes(candidate)
        (staged / "training_report.json").write_bytes(report_path.read_bytes())
        os.replace(staged, root)
    evidence = Phase12ETrainingProcessEvidence(
        request_hash=request_hash,
        worker_source_guard=guard,
        worker_report=report_value,
        candidate_tensor_sha256=sha256_hex(candidate),
        stdout_sha256=sha256_hex(stdout),
        stderr_sha256=sha256_hex(stderr),
        return_code=return_code,
        timed_out=timed_out,
        output_root=root,
    )
    if not evidence.accepted:
        failed = sorted(
            name for name, accepted in evidence.acceptance_checks.items() if not accepted
        )
        diagnostic = {
            "failed_checks": failed,
            "evidence": evidence.to_json(),
            "stdout_utf8": stdout.decode("utf-8", errors="replace")[-4096:],
            "stderr_utf8": stderr.decode("utf-8", errors="replace")[-4096:],
        }
        raise ValueError(
            "Phase 12E training process evidence did not accept: "
            + canonical_json_bytes(diagnostic).decode("utf-8")
        )
    return evidence


@dataclass(frozen=True, slots=True)
class Phase12ETrainingEvidence:
    request: dict[str, object]
    first: Phase12ETrainingProcessEvidence
    second: Phase12ETrainingProcessEvidence
    semantic_candidate_tensor_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase12e.training_evidence.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.first.accepted
            and self.second.accepted
            and self.first.candidate_tensor_sha256 == self.second.candidate_tensor_sha256
            and self.first.worker_report == self.second.worker_report
            and self.first.candidate_tensor_sha256 == self.semantic_candidate_tensor_hash
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "request": dict(self.request),
            "request_hash": canonical_json_hash(self.request),
            "first": self.first.to_json(),
            "second": self.second.to_json(),
            "semantic_candidate_tensor_hash": self.semantic_candidate_tensor_hash,
            "worker_training_invocations": 2,
            "optimizer_steps_per_invocation": 1,
            "authoritative_host_recomputation": True,
            "heldout_task_ids_consumed": False,
            "heldout_prompts_consumed": False,
            "heldout_source_consumed": False,
            "heldout_reference_answers_consumed": False,
            "candidate_self_report_authoritative": False,
        }


def run_phase12e_training_request(
    request: dict[str, object],
    semantic_candidate_tensor_hash: str,
    output_root: Path,
    *,
    worker_source: Path | None = None,
) -> Phase12ETrainingEvidence:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12E training root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    worker = (worker_source or default_phase12e_worker_source()).resolve(strict=True)
    first = _run_worker(request, root / "first", worker_source=worker)
    second = _run_worker(request, root / "second", worker_source=worker)
    evidence = Phase12ETrainingEvidence(
        request=request,
        first=first,
        second=second,
        semantic_candidate_tensor_hash=semantic_candidate_tensor_hash,
    )
    if not evidence.accepted:
        raise ValueError("Phase 12E duplicate untrusted training replay did not close")
    return evidence


def run_phase12e_training(
    reference: "Phase12EReference",
    output_root: Path,
    *,
    worker_source: Path | None = None,
) -> Phase12ETrainingEvidence:
    request = phase12e_training_request(reference)
    _, architecture, _, _, adapter = load_package_components(reference.semantic_candidate.root)
    selected = selected_phase12e_adapter_spec(architecture)
    record = next((item for item in adapter.records if item.spec.name == selected.name), None)
    if record is None:
        raise SchemaValidationError("phase12e.training", "selected candidate adapter is missing")
    return run_phase12e_training_request(
        request,
        record.sha256,
        output_root,
        worker_source=worker_source,
    )


__all__ = [
    "Phase12ETrainingEvidence",
    "Phase12ETrainingProcessEvidence",
    "default_phase12e_worker_source",
    "phase12e_training_request",
    "run_phase12e_training",
    "run_phase12e_training_request",
]
