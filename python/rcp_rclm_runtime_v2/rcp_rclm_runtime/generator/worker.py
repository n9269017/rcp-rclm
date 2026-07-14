from __future__ import annotations

import sys

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.generator.grammar import generate_reference_proposal
from rcp_rclm_runtime.generator.protocol import ReferenceGeneratorInputRecord


def main() -> int:
    data = sys.stdin.buffer.read()
    try:
        value = load_json_strict(data, require_canonical=True)
        request = ReferenceGeneratorInputRecord.from_json(value)
        proposal = generate_reference_proposal(request)
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        error = {
            "schema_id": "runtime.phase5a_generator_worker_error.v2",
            "error_type": type(exc).__name__,
            "error_detail_hash": sha256_hex(str(exc).encode("utf-8")),
        }
        sys.stderr.buffer.write(canonical_json_bytes(error) + b"\n")
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(proposal.to_json()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
