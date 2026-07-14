from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime.generator.records import WorkerSandboxRecord

REFERENCE_WORKER_AUDIT_POLICY_VERSION: Final[str] = (
    "rcp-rclm-phase5-reference-worker-audit-v1"
)

_DENIED_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "os.chdir",
        "os.chmod",
        "os.chown",
        "os.link",
        "os.mkdir",
        "os.remove",
        "os.rename",
        "os.replace",
        "os.rmdir",
        "os.symlink",
        "os.system",
        "shutil.copyfile",
        "shutil.copymode",
        "shutil.copystat",
        "shutil.move",
        "subprocess.Popen",
    }
)


def audit_denial_reason(event: str, args: Sequence[object]) -> str | None:
    if event == "open":
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else None
        if isinstance(mode, str) and any(token in mode for token in ("w", "a", "x", "+")):
            return "filesystem_write_denied"
        if isinstance(flags, int):
            write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            if flags & write_flags:
                return "filesystem_write_denied"
    if event in _DENIED_EVENTS:
        return "mutation_or_subprocess_denied"
    if event.startswith("socket."):
        return "network_denied"
    return None


def enforce_reference_worker_audit(event: str, args: Sequence[object]) -> None:
    reason = audit_denial_reason(event, args)
    if reason is not None:
        raise PermissionError(f"{REFERENCE_WORKER_AUDIT_POLICY_VERSION}:{reason}:{event}")


def install_reference_worker_audit_hook() -> None:
    sys.addaudithook(enforce_reference_worker_audit)


def run_reference_worker_sandbox_self_test() -> WorkerSandboxRecord:
    _require_denied("open", ("probe", "wb", os.O_WRONLY | os.O_CREAT))
    _require_denied("socket.__new__", ())
    _require_denied("subprocess.Popen", ())
    return WorkerSandboxRecord(
        audit_policy_version=REFERENCE_WORKER_AUDIT_POLICY_VERSION,
        file_write_probe="denied",
        network_probe="denied",
        subprocess_probe="denied",
        checker_input_present=False,
        trust_anchor_present=False,
        previous_manifest_history_present=False,
        promotion_ledger_present=False,
        reference_answer_present=False,
    )


def _require_denied(event: str, args: Sequence[object]) -> None:
    try:
        enforce_reference_worker_audit(event, args)
    except PermissionError:
        return
    raise RuntimeError(f"sandbox self-test failed to deny audit event {event}")
