from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

REFERENCE_PROCESS_POLICY_ID: Final[str] = "rcp-rclm-phase5a-isolated-stdio-v1"
ALLOWED_ENVIRONMENT_KEYS: Final[Sequence[str]] = (
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
        "allowed_environment_keys": list(ALLOWED_ENVIRONMENT_KEYS),
        "generator_file_arguments": [],
        "generator_network_endpoints": [],
        "generator_write_handles": [],
    }
)

__all__ = [
    "ALLOWED_ENVIRONMENT_KEYS",
    "REFERENCE_PROCESS_ENVIRONMENT_HASH",
    "REFERENCE_PROCESS_POLICY_ID",
]
