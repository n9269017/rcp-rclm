from __future__ import annotations

import sys

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.generator.grammar import interpret_reference_input
from rcp_rclm_runtime.generator.records import (
    REFERENCE_GENERATOR_MAX_INPUT_BYTES,
    GeneratorReasonCode,
    ReferenceGeneratorInputRecord,
    ReferenceWorkerResponse,
)
from rcp_rclm_runtime.generator.sandbox import (
    install_reference_worker_audit_hook,
    run_reference_worker_sandbox_self_test,
)


def main() -> int:
    raw = sys.stdin.buffer.read(REFERENCE_GENERATOR_MAX_INPUT_BYTES + 1)
    input_hash = sha256_hex(raw)
    install_reference_worker_audit_hook()
    try:
        sandbox = run_reference_worker_sandbox_self_test()
    except Exception as exc:
        sys.stderr.write(f"generator sandbox initialization failed: {type(exc).__name__}\n")
        return 70
    if len(raw) > REFERENCE_GENERATOR_MAX_INPUT_BYTES:
        response = ReferenceWorkerResponse(
            status="reject",
            reason_codes=(GeneratorReasonCode.SCHEMA_MALFORMED,),
            proposal=None,
            sandbox=sandbox,
            input_hash=input_hash,
        )
        sys.stdout.buffer.write(canonical_json_bytes(response.to_json()))
        return 0
    try:
        parsed = load_json_strict(raw, require_canonical=True)
        generator_input = ReferenceGeneratorInputRecord.from_json(parsed)
    except (RuntimeValidationError, TypeError, ValueError):
        response = ReferenceWorkerResponse(
            status="reject",
            reason_codes=(GeneratorReasonCode.SCHEMA_MALFORMED,),
            proposal=None,
            sandbox=sandbox,
            input_hash=input_hash,
        )
        sys.stdout.buffer.write(canonical_json_bytes(response.to_json()))
        return 0
    try:
        proposal, reasons = interpret_reference_input(generator_input)
        response = ReferenceWorkerResponse(
            status="generated" if proposal is not None else "reject",
            reason_codes=reasons,
            proposal=proposal,
            sandbox=sandbox,
            input_hash=input_hash,
        )
    except Exception:
        response = ReferenceWorkerResponse(
            status="indeterminate",
            reason_codes=(GeneratorReasonCode.INTERNAL_ERROR,),
            proposal=None,
            sandbox=sandbox,
            input_hash=input_hash,
        )
    sys.stdout.buffer.write(canonical_json_bytes(response.to_json()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
