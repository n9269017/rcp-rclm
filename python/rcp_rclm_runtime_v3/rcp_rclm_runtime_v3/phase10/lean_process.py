from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.errors import SchemaValidationError

DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS: Final[int] = 600


@dataclass(frozen=True, slots=True)
class PinnedLeanProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def run_pinned_lean_source(
    source_bytes: bytes,
    lean_project_root: Path,
    *,
    temporary_prefix: str,
    source_file_name: str,
    timeout_seconds: int = DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS,
) -> PinnedLeanProcessResult:
    if not temporary_prefix:
        raise SchemaValidationError("lean.process.temporary_prefix", "expected a nonempty prefix")
    if Path(source_file_name).name != source_file_name or not source_file_name.endswith(".lean"):
        raise SchemaValidationError(
            "lean.process.source_file_name",
            "expected a safe Lean source file name",
        )
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise SchemaValidationError(
            "lean.process.timeout_seconds",
            "expected a positive integer timeout",
        )
    lake_executable = shutil.which("lake")
    if lake_executable is None:
        raise SchemaValidationError(
            "lean.process.executable",
            "the pinned lake executable is unavailable on PATH",
        )
    project = lean_project_root.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix=temporary_prefix) as temporary:
        source_path = Path(temporary) / source_file_name
        source_path.write_bytes(source_bytes)
        try:
            completed = subprocess.run(
                [lake_executable, "env", "lean", str(source_path)],
                cwd=project,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise SchemaValidationError(
                "lean.process.timeout",
                f"pinned Lean verification exceeded {timeout_seconds} seconds for {source_file_name}",
            ) from exc
        except OSError as exc:
            raise SchemaValidationError(
                "lean.process.launch",
                f"failed to launch pinned Lean verification: {type(exc).__name__}: {exc}",
            ) from exc
    return PinnedLeanProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


__all__ = [
    "DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS",
    "PinnedLeanProcessResult",
    "run_pinned_lean_source",
]
