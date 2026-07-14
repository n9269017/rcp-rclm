from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final, Mapping

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.generator.records import (
    GeneratorProcessObservation,
    GeneratorReasonCode,
    GeneratorReplayReport,
    ReferenceGeneratorInputRecord,
    ReferenceWorkerResponse,
)

_WORKER_MODULE: Final[str] = "rcp_rclm_runtime.generator.worker"
_ENVIRONMENT_KEYS: Final[tuple[str, ...]] = (
    "COMSPEC",
    "LANG",
    "LC_ALL",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
)


def run_reference_generator_process(
    generator_input: ReferenceGeneratorInputRecord,
    *,
    python_executable: str | None = None,
) -> GeneratorProcessObservation:
    input_bytes = canonical_json_bytes(generator_input.to_json())
    input_hash = sha256_hex(input_bytes)
    executable = python_executable or sys.executable
    command = (executable, "-I", "-B", "-m", _WORKER_MODULE)
    command_hash = canonical_json_hash(
        {
            "schema_id": "runtime.phase5_generator_command.v2",
            "argv": ["<python>", "-I", "-B", "-m", _WORKER_MODULE],
        }
    )
    environment = _minimal_environment()
    environment_key_hash = canonical_json_hash(
        {
            "schema_id": "runtime.phase5_generator_environment_keys.v2",
            "keys": sorted(environment),
        }
    )
    try:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase5-generator-") as temp_dir:
            completed = subprocess.run(
                command,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(temp_dir),
                env=environment,
                timeout=generator_input.resource_budget.timeout_seconds,
                check=False,
                close_fds=True,
            )
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_bytes(exc.stdout)
        stderr = _timeout_bytes(exc.stderr)
        return GeneratorProcessObservation(
            status="indeterminate",
            reason_codes=(GeneratorReasonCode.PROCESS_TIMEOUT,),
            exit_code=124,
            timed_out=True,
            input_hash=input_hash,
            stdout_hash=sha256_hex(stdout),
            stderr_hash=sha256_hex(stderr),
            command_hash=command_hash,
            environment_key_hash=environment_key_hash,
            response=None,
        )
    stdout = completed.stdout
    stderr = completed.stderr
    normalized_exit_code = completed.returncode if 0 <= completed.returncode <= 255 else 255
    if completed.returncode != 0:
        return GeneratorProcessObservation(
            status="reject",
            reason_codes=(GeneratorReasonCode.PROCESS_FAILED,),
            exit_code=normalized_exit_code,
            timed_out=False,
            input_hash=input_hash,
            stdout_hash=sha256_hex(stdout),
            stderr_hash=sha256_hex(stderr),
            command_hash=command_hash,
            environment_key_hash=environment_key_hash,
            response=None,
        )
    try:
        parsed = load_json_strict(stdout, require_canonical=True)
        response = ReferenceWorkerResponse.from_json(parsed)
    except (RuntimeValidationError, TypeError, ValueError):
        return GeneratorProcessObservation(
            status="reject",
            reason_codes=(GeneratorReasonCode.OUTPUT_INVALID,),
            exit_code=normalized_exit_code,
            timed_out=False,
            input_hash=input_hash,
            stdout_hash=sha256_hex(stdout),
            stderr_hash=sha256_hex(stderr),
            command_hash=command_hash,
            environment_key_hash=environment_key_hash,
            response=None,
        )
    if response.input_hash != input_hash:
        return GeneratorProcessObservation(
            status="reject",
            reason_codes=(GeneratorReasonCode.OUTPUT_INVALID,),
            exit_code=normalized_exit_code,
            timed_out=False,
            input_hash=input_hash,
            stdout_hash=sha256_hex(stdout),
            stderr_hash=sha256_hex(stderr),
            command_hash=command_hash,
            environment_key_hash=environment_key_hash,
            response=response,
        )
    return GeneratorProcessObservation(
        status=response.status,
        reason_codes=response.reason_codes,
        exit_code=normalized_exit_code,
        timed_out=False,
        input_hash=input_hash,
        stdout_hash=sha256_hex(stdout),
        stderr_hash=sha256_hex(stderr),
        command_hash=command_hash,
        environment_key_hash=environment_key_hash,
        response=response,
    )


def run_reference_generator_replay(
    generator_input: ReferenceGeneratorInputRecord,
    *,
    python_executable: str | None = None,
) -> GeneratorReplayReport:
    first = run_reference_generator_process(
        generator_input,
        python_executable=python_executable,
    )
    second = run_reference_generator_process(
        generator_input,
        python_executable=python_executable,
    )
    deterministic = (
        first.stdout_hash == second.stdout_hash
        and first.status == second.status
        and first.reason_codes == second.reason_codes
        and (
            (first.response is None and second.response is None)
            or (
                first.response is not None
                and second.response is not None
                and first.response.response_hash == second.response.response_hash
            )
        )
    )
    if not deterministic:
        return GeneratorReplayReport(
            status="reject",
            reason_codes=(GeneratorReasonCode.REPLAY_MISMATCH,),
            first=first,
            second=second,
            proposal=None,
        )
    if first.status == "generated":
        proposal = None if first.response is None else first.response.proposal
        if proposal is None:
            return GeneratorReplayReport(
                status="reject",
                reason_codes=(GeneratorReasonCode.OUTPUT_INVALID,),
                first=first,
                second=second,
                proposal=None,
            )
        return GeneratorReplayReport(
            status="generated",
            reason_codes=(),
            first=first,
            second=second,
            proposal=proposal,
        )
    return GeneratorReplayReport(
        status=first.status,
        reason_codes=(
            first.reason_codes
            if first.reason_codes
            else (GeneratorReasonCode.PROCESS_FAILED,)
        ),
        first=first,
        second=second,
        proposal=None,
    )


def _minimal_environment() -> Mapping[str, str]:
    environment = {
        key: os.environ[key]
        for key in _ENVIRONMENT_KEYS
        if key in os.environ
    }
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _timeout_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")
