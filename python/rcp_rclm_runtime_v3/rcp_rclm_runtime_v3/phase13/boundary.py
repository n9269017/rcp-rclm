from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import sha256_hex

from rcp_rclm_runtime_v3.phase13.constants import (
    FORBIDDEN_REPLAY_MODULE_PREFIXES,
    FORBIDDEN_REPLAY_PATH_SUFFIXES,
    PHASE12_COMPLETE_REQUIRED_PATHS,
    PHASE13A_RETAINED_SOURCE_PATHS,
)
from rcp_rclm_runtime_v3.phase13.records import (
    ReplaySourceFinding,
    ReplaySourceGuardReport,
    RetainedEvidenceManifest,
    RetainedFileRecord,
)

_REPLAY_SOURCE_FILES = (
    "constants.py",
    "records.py",
    "attacks.py",
    "boundary.py",
    "reference.py",
)
_FORBIDDEN_IMPORTS = (
    "importlib",
    "random",
    "secrets",
    "socket",
    "subprocess",
    "torch",
    "rcp_rclm_runtime_v3.phase10.training_process",
    "rcp_rclm_runtime_v3.phase11.phase11b_training",
    "rcp_rclm_runtime_v3.phase12.phase12b_training",
    "rcp_rclm_runtime_v3.phase12.phase12e_training",
)
_FORBIDDEN_CALLS = (
    "eval",
    "exec",
    "__import__",
    "run_training_twice",
    "generate_phase12e_proposal",
    "generate_phase12d_proposal",
)


def _is_forbidden_relative_path(path: str) -> bool:
    return any(path.endswith(suffix) for suffix in FORBIDDEN_REPLAY_PATH_SUFFIXES)


def build_retained_evidence_manifest(repo_root: Path, output_root: Path) -> RetainedEvidenceManifest:
    repo = repo_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 13 retained-evidence root already exists: {output}")
    output.mkdir(parents=True, exist_ok=False)
    files: list[RetainedFileRecord] = []
    missing: list[str] = []
    excluded: list[str] = []
    for relative in sorted(PHASE13A_RETAINED_SOURCE_PATHS, key=lambda value: value.encode("utf-8")):
        if _is_forbidden_relative_path(relative):
            excluded.append(relative)
            continue
        source = repo / relative
        if not source.is_file():
            missing.append(relative)
            continue
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        content = destination.read_bytes()
        files.append(RetainedFileRecord(path=relative, size=len(content), sha256=sha256_hex(content)))
    return RetainedEvidenceManifest(
        files=tuple(files),
        missing_declared_paths=tuple(sorted(missing, key=lambda value: value.encode("utf-8"))),
        excluded_forbidden_paths=tuple(sorted(excluded, key=lambda value: value.encode("utf-8"))),
    )


def phase12_dependency_paths(repo_root: Path) -> tuple[Sequence[str], Sequence[str]]:
    repo = repo_root.resolve(strict=True)
    present = tuple(
        relative
        for relative in PHASE12_COMPLETE_REQUIRED_PATHS
        if (repo / relative).is_file()
    )
    missing = tuple(
        relative
        for relative in PHASE12_COMPLETE_REQUIRED_PATHS
        if not (repo / relative).is_file()
    )
    return (
        tuple(sorted(present, key=lambda value: value.encode("utf-8"))),
        tuple(sorted(missing, key=lambda value: value.encode("utf-8"))),
    )


def forbidden_modules_loaded() -> Sequence[str]:
    return tuple(
        sorted(
            (
                name
                for name in sys.modules
                if any(name == prefix or name.startswith(f"{prefix}.") for prefix in FORBIDDEN_REPLAY_MODULE_PREFIXES)
            ),
            key=lambda value: value.encode("utf-8"),
        )
    )


def forbidden_paths_present(bundle_root: Path) -> Sequence[str]:
    root = bundle_root.resolve(strict=True)
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file() and _is_forbidden_relative_path(path.relative_to(root).as_posix())
            ),
            key=lambda value: value.encode("utf-8"),
        )
    )


def guard_phase13_replay_source() -> ReplaySourceGuardReport:
    package_root = Path(__file__).resolve(strict=True).parent
    findings: list[ReplaySourceFinding] = []
    hashes: dict[str, str] = {}
    for file_name in _REPLAY_SOURCE_FILES:
        path = package_root / file_name
        source = path.read_bytes()
        relative = f"rcp_rclm_runtime_v3/phase13/{file_name}"
        hashes[relative] = sha256_hex(source)
        text = source.decode("utf-8", errors="strict")
        tree = ast.parse(text, filename=relative)
        for node in ast.walk(tree):
            imports: set[str] = set()
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module)
            for imported in sorted(imports):
                if any(imported == item or imported.startswith(f"{item}.") for item in _FORBIDDEN_IMPORTS):
                    findings.append(
                        ReplaySourceFinding(
                            code="PHASE13_REPLAY_FORBIDDEN_IMPORT",
                            path=relative,
                            line=node.lineno,
                            detail=imported,
                        )
                    )
            call_name: str | None = None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
            if call_name in _FORBIDDEN_CALLS:
                findings.append(
                    ReplaySourceFinding(
                        code="PHASE13_REPLAY_FORBIDDEN_CALL",
                        path=relative,
                        line=node.lineno,
                        detail=str(call_name),
                    )
                )
    findings.sort(key=lambda item: (item.path, item.line, item.code, item.detail))
    return ReplaySourceGuardReport(
        file_hashes={key: hashes[key] for key in sorted(hashes, key=lambda value: value.encode("utf-8"))},
        findings=tuple(findings),
    )


__all__ = [
    "build_retained_evidence_manifest",
    "forbidden_modules_loaded",
    "forbidden_paths_present",
    "guard_phase13_replay_source",
    "phase12_dependency_paths",
]
