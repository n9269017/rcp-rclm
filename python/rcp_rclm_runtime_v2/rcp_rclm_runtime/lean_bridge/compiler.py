from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime._version import (
    FORMAL_SOURCE_COMMIT,
    LEAN_TOOLCHAIN,
    MATHLIB_COMMIT,
)
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.lean_bridge.source_guard import LeanSourceRejected, require_clean_source_bytes
from rcp_rclm_runtime.refinement.theorem_surface import theorem_surface_metadata

FORMAL_PROJECT_RELATIVE_PATH: Final[Path] = Path("lean/rcp_rclm_formal_core_v2")
FORMAL_DOCS_RELATIVE_PATH: Final[Path] = Path("docs/formal_core_v2")
COMPILER_BRIDGE_VERSION: Final[str] = "rcp-rclm-lean-compiler-bridge-v2.0.0"
_EXPECTED_LEAN_VERSION_FRAGMENT: Final[str] = "version 4.31.0"
_EXPECTED_LAKE_LEAN_FRAGMENT: Final[str] = "Lean version 4.31.0"


class LeanCompilerBridgeError(RuntimeValidationError):
    def __init__(self, code: str, path: str, detail: str) -> None:
        super().__init__(code, path, detail)


@dataclass(frozen=True, slots=True)
class PinnedLeanProject:
    repository_root: Path
    root: Path
    toolchain: str
    mathlib_commit: str
    formal_source_commit: str
    formal_source_tree: str
    toolchain_file_hash: str
    manifest_hash: str
    lakefile_hash: str
    theorem_surface_hash: str
    pin_hash: str

    @classmethod
    def discover(
        cls,
        repository_root: Path,
        *,
        verify_git_pin: bool = True,
    ) -> PinnedLeanProject:
        repo_root = repository_root.resolve(strict=True)
        project_root = (repo_root / FORMAL_PROJECT_RELATIVE_PATH).resolve(strict=True)
        if not project_root.is_dir():
            raise LeanCompilerBridgeError(
                "LEAN_PROJECT_MISSING",
                str(project_root),
                "pinned Formal Core v2 project directory is missing",
            )
        toolchain_path = project_root / "lean-toolchain"
        manifest_path = project_root / "lake-manifest.json"
        lakefile_path = project_root / "lakefile.toml"
        for path in (toolchain_path, manifest_path, lakefile_path):
            if not path.is_file():
                raise LeanCompilerBridgeError(
                    "LEAN_PIN_FILE_MISSING",
                    str(path),
                    "required pinned project file is missing",
                )
        toolchain_bytes = toolchain_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
        lakefile_bytes = lakefile_path.read_bytes()
        try:
            toolchain = toolchain_bytes.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise LeanCompilerBridgeError(
                "LEAN_PIN_INVALID_UTF8",
                str(toolchain_path),
                str(exc),
            ) from exc
        if toolchain != LEAN_TOOLCHAIN:
            raise LeanCompilerBridgeError(
                "LEAN_TOOLCHAIN_PIN_MISMATCH",
                str(toolchain_path),
                f"expected {LEAN_TOOLCHAIN}, found {toolchain}",
            )
        try:
            manifest = json.loads(manifest_bytes.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LeanCompilerBridgeError(
                "LEAN_MANIFEST_INVALID",
                str(manifest_path),
                str(exc),
            ) from exc
        if not isinstance(manifest, Mapping):
            raise LeanCompilerBridgeError(
                "LEAN_MANIFEST_INVALID",
                str(manifest_path),
                "manifest root must be an object",
            )
        packages = manifest.get("packages")
        if not isinstance(packages, list):
            raise LeanCompilerBridgeError(
                "LEAN_MANIFEST_INVALID",
                str(manifest_path),
                "manifest packages must be an array",
            )
        mathlib_records = [
            package
            for package in packages
            if isinstance(package, Mapping) and package.get("name") == "mathlib"
        ]
        if len(mathlib_records) != 1:
            raise LeanCompilerBridgeError(
                "MATHLIB_PIN_MISSING",
                str(manifest_path),
                f"expected exactly one mathlib package record, found {len(mathlib_records)}",
            )
        mathlib_commit = mathlib_records[0].get("rev")
        if mathlib_commit != MATHLIB_COMMIT:
            raise LeanCompilerBridgeError(
                "MATHLIB_PIN_MISMATCH",
                str(manifest_path),
                f"expected {MATHLIB_COMMIT}, found {mathlib_commit}",
            )
        formal_source_tree = (
            _verify_formal_source_git_pin(repo_root)
            if verify_git_pin
            else canonical_json_hash(
                {
                    "formal_source_commit": FORMAL_SOURCE_COMMIT,
                    "verification": "unit_test_bypass",
                }
            )
        )
        surface_hash = canonical_json_hash(theorem_surface_metadata())
        pin_payload = {
            "schema_id": "runtime.lean_project_pin.v2",
            "formal_source_commit": FORMAL_SOURCE_COMMIT,
            "formal_source_tree": formal_source_tree,
            "toolchain": toolchain,
            "mathlib_commit": mathlib_commit,
            "toolchain_file_hash": sha256_hex(toolchain_bytes),
            "manifest_hash": sha256_hex(manifest_bytes),
            "lakefile_hash": sha256_hex(lakefile_bytes),
            "theorem_surface_hash": surface_hash,
        }
        return cls(
            repository_root=repo_root,
            root=project_root,
            toolchain=toolchain,
            mathlib_commit=mathlib_commit,
            formal_source_commit=FORMAL_SOURCE_COMMIT,
            formal_source_tree=formal_source_tree,
            toolchain_file_hash=str(pin_payload["toolchain_file_hash"]),
            manifest_hash=str(pin_payload["manifest_hash"]),
            lakefile_hash=str(pin_payload["lakefile_hash"]),
            theorem_surface_hash=surface_hash,
            pin_hash=canonical_json_hash(pin_payload),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.lean_project_pin.v2",
            "project_path": FORMAL_PROJECT_RELATIVE_PATH.as_posix(),
            "formal_source_commit": self.formal_source_commit,
            "formal_source_tree": self.formal_source_tree,
            "toolchain": self.toolchain,
            "mathlib_commit": self.mathlib_commit,
            "toolchain_file_hash": self.toolchain_file_hash,
            "manifest_hash": self.manifest_hash,
            "lakefile_hash": self.lakefile_hash,
            "theorem_surface_hash": self.theorem_surface_hash,
            "pin_hash": self.pin_hash,
        }


@dataclass(frozen=True, slots=True)
class LeanToolchainRuntimeIdentity:
    lake_command: str
    lean_version: str
    lake_version: str
    lean_prefix: str
    platform: str
    environment_path_hash: str
    runtime_hash: str

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.lean_toolchain_runtime_identity.v2",
            "lake_command": self.lake_command,
            "lean_version": self.lean_version,
            "lake_version": self.lake_version,
            "lean_prefix": self.lean_prefix,
            "platform": self.platform,
            "environment_path_hash": self.environment_path_hash,
            "runtime_hash": self.runtime_hash,
        }


@dataclass(frozen=True, slots=True)
class LeanCompilationResult:
    command: Sequence[str]
    source_name: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    duration_ms: int
    timed_out: bool
    source_hash: str
    toolchain_identity: LeanToolchainRuntimeIdentity
    project_pin_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "command", tuple(self.command))

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def stdout_hash(self) -> str:
        return sha256_hex(self.stdout)

    @property
    def stderr_hash(self) -> str:
        return sha256_hex(self.stderr)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.lean_compilation_result.v2",
            "compiler_bridge_version": COMPILER_BRIDGE_VERSION,
            "command": list(self.command),
            "source_name": self.source_name,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "succeeded": self.succeeded,
            "source_hash": self.source_hash,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "project_pin_hash": self.project_pin_hash,
            "toolchain_identity": self.toolchain_identity.to_json(),
        }


def _native_elan_lake_candidates(
    environment: Mapping[str, str],
) -> Sequence[Path]:
    configured = environment.get("ELAN_HOME")
    if configured is None:
        elan_home = Path.home() / ".elan"
    else:
        elan_home = Path(configured)
        if not elan_home.is_absolute():
            raise LeanCompilerBridgeError(
                "ELAN_HOME_INVALID",
                "ELAN_HOME",
                "ELAN_HOME must be an absolute path",
            )
    return (
        elan_home / "bin" / "lake.exe",
        elan_home / "bin" / "lake",
    )


def _resolve_lake_command(
    lake_command: str | None,
    environment: Mapping[str, str],
) -> str:
    if lake_command is not None:
        return lake_command
    discovered = shutil.which("lake", path=environment.get("PATH"))
    if discovered is not None:
        return discovered
    for candidate in _native_elan_lake_candidates(environment):
        if candidate.is_file():
            return str(candidate)
    raise LeanCompilerBridgeError(
        "LAKE_NOT_FOUND",
        "lake",
        "Lake executable was not found on PATH or in the native Elan home",
    )


class LeanCompiler:
    def __init__(
        self,
        project: PinnedLeanProject,
        lake_command: str | None = None,
        timeout_seconds: int = 120,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
            raise LeanCompilerBridgeError(
                "LEAN_TIMEOUT_INVALID",
                "timeout_seconds",
                "timeout must be an integer",
            )
        if timeout_seconds < 1 or timeout_seconds > 3600:
            raise LeanCompilerBridgeError(
                "LEAN_TIMEOUT_INVALID",
                "timeout_seconds",
                "timeout must be between 1 and 3600 seconds",
            )
        self._environment = dict(os.environ if environment is None else environment)
        resolved_lake = _resolve_lake_command(lake_command, self._environment)
        self._project = project
        self._lake_command = resolved_lake
        self._timeout_seconds = timeout_seconds
        self._environment["ELAN_TOOLCHAIN"] = LEAN_TOOLCHAIN
        self._runtime_identity_cache: LeanToolchainRuntimeIdentity | None = None

    @property
    def project(self) -> PinnedLeanProject:
        return self._project

    def runtime_identity(self) -> LeanToolchainRuntimeIdentity:
        if self._runtime_identity_cache is not None:
            return self._runtime_identity_cache
        lean_version = self._run_identity_command(
            (self._lake_command, "env", "lean", "--version"),
            "Lean",
        )
        if _EXPECTED_LEAN_VERSION_FRAGMENT not in lean_version:
            raise LeanCompilerBridgeError(
                "LEAN_RUNTIME_VERSION_MISMATCH",
                "Lean",
                f"expected {_EXPECTED_LEAN_VERSION_FRAGMENT!r} in {lean_version!r}",
            )
        lake_version = self._run_identity_command(
            (self._lake_command, "--version"),
            "Lake",
        )
        if _EXPECTED_LAKE_LEAN_FRAGMENT not in lake_version:
            raise LeanCompilerBridgeError(
                "LAKE_RUNTIME_VERSION_MISMATCH",
                "Lake",
                f"expected {_EXPECTED_LAKE_LEAN_FRAGMENT!r} in {lake_version!r}",
            )
        lean_prefix = self._run_identity_command(
            (self._lake_command, "env", "lean", "--print-prefix"),
            "LeanPrefix",
        )
        path_value = self._environment.get("PATH", "")
        payload = {
            "schema_id": "runtime.lean_toolchain_runtime_identity.v2",
            "lake_command": self._lake_command,
            "lean_version": lean_version,
            "lake_version": lake_version,
            "lean_prefix": lean_prefix,
            "platform": os.name,
            "environment_path_hash": sha256_hex(path_value.encode("utf-8")),
            "project_pin_hash": self._project.pin_hash,
        }
        runtime_hash = canonical_json_hash(payload)
        identity = LeanToolchainRuntimeIdentity(
            lake_command=self._lake_command,
            lean_version=lean_version,
            lake_version=lake_version,
            lean_prefix=lean_prefix,
            platform=os.name,
            environment_path_hash=str(payload["environment_path_hash"]),
            runtime_hash=runtime_hash,
        )
        self._runtime_identity_cache = identity
        return identity

    def compile_source(
        self,
        source: bytes,
        *,
        source_name: str = "generated/RuntimeBridgeCertificate.lean",
    ) -> LeanCompilationResult:
        if not source_name or not source_name.endswith(".lean"):
            raise LeanCompilerBridgeError(
                "LEAN_SOURCE_NAME_INVALID",
                "source_name",
                "generated source name must be a nonempty .lean path",
            )
        try:
            guard_report = require_clean_source_bytes(source)
        except LeanSourceRejected as exc:
            raise LeanCompilerBridgeError(
                "LEAN_SOURCE_GUARD_REJECTED",
                source_name,
                str(exc),
            ) from exc
        identity = self.runtime_identity()
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-lean-bridge-") as temp_dir:
            source_path = Path(temp_dir) / "RuntimeBridgeCertificate.lean"
            source_path.write_bytes(source)
            command = (
                self._lake_command,
                "env",
                "lean",
                str(source_path),
            )
            started = time.monotonic_ns()
            try:
                process = subprocess.run(
                    command,
                    cwd=self._project.root,
                    env=self._environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self._timeout_seconds,
                    check=False,
                )
                exit_code = process.returncode
                stdout = process.stdout
                stderr = process.stderr
                timed_out = False
            except subprocess.TimeoutExpired as exc:
                exit_code = 124
                stdout = _timeout_stream(exc.stdout)
                stderr = _timeout_stream(exc.stderr)
                timed_out = True
            duration_ms = max(0, (time.monotonic_ns() - started) // 1_000_000)
        return LeanCompilationResult(
            command=command,
            source_name=source_name,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
            source_hash=guard_report.source_hash,
            toolchain_identity=identity,
            project_pin_hash=self._project.pin_hash,
        )

    def _run_identity_command(self, command: Sequence[str], label: str) -> str:
        try:
            process = subprocess.run(
                tuple(command),
                cwd=self._project.root,
                env=self._environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LeanCompilerBridgeError(
                "LEAN_IDENTITY_TIMEOUT",
                label,
                f"identity command timed out: {tuple(command)}",
            ) from exc
        if process.returncode != 0:
            detail = process.stderr.decode("utf-8", errors="replace").strip()
            raise LeanCompilerBridgeError(
                "LEAN_IDENTITY_FAILED",
                label,
                detail or f"identity command exited with {process.returncode}",
            )
        try:
            text = process.stdout.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise LeanCompilerBridgeError(
                "LEAN_IDENTITY_INVALID_UTF8",
                label,
                str(exc),
            ) from exc
        if not text:
            raise LeanCompilerBridgeError(
                "LEAN_IDENTITY_EMPTY",
                label,
                "identity command returned empty stdout",
            )
        return text


def _verify_formal_source_git_pin(repository_root: Path) -> str:
    if not (repository_root / ".git").exists():
        raise LeanCompilerBridgeError(
            "FORMAL_SOURCE_GIT_MISSING",
            str(repository_root),
            "repository root must contain Git metadata for formal-source pin verification",
        )
    _run_git(
        repository_root,
        ("cat-file", "-e", f"{FORMAL_SOURCE_COMMIT}^{{commit}}"),
        "FORMAL_SOURCE_COMMIT_MISSING",
    )
    changed = _run_git(
        repository_root,
        (
            "diff",
            "--name-only",
            FORMAL_SOURCE_COMMIT,
            "--",
            FORMAL_PROJECT_RELATIVE_PATH.as_posix(),
            FORMAL_DOCS_RELATIVE_PATH.as_posix(),
        ),
        "FORMAL_SOURCE_DIFF_FAILED",
    )
    if changed:
        raise LeanCompilerBridgeError(
            "FORMAL_SOURCE_DRIFT",
            str(repository_root),
            "formal source differs from the pinned commit: " + ", ".join(changed.splitlines()),
        )
    dirty = _run_git(
        repository_root,
        (
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            FORMAL_PROJECT_RELATIVE_PATH.as_posix(),
            FORMAL_DOCS_RELATIVE_PATH.as_posix(),
        ),
        "FORMAL_SOURCE_STATUS_FAILED",
    )
    if dirty:
        raise LeanCompilerBridgeError(
            "FORMAL_SOURCE_WORKTREE_DIRTY",
            str(repository_root),
            "formal source worktree is dirty: " + ", ".join(dirty.splitlines()),
        )
    return _run_git(
        repository_root,
        ("rev-parse", f"{FORMAL_SOURCE_COMMIT}^{{tree}}"),
        "FORMAL_SOURCE_TREE_FAILED",
    )


def _run_git(
    repository_root: Path,
    arguments: Sequence[str],
    error_code: str,
) -> str:
    process = subprocess.run(
        ("git", "-C", str(repository_root), *tuple(arguments)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise LeanCompilerBridgeError(
            error_code,
            str(repository_root),
            detail or f"git command exited with {process.returncode}",
        )
    try:
        return process.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise LeanCompilerBridgeError(
            "FORMAL_SOURCE_GIT_INVALID_UTF8",
            str(repository_root),
            str(exc),
        ) from exc


def _timeout_stream(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")
