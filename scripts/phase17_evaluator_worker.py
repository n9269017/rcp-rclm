"""Dedicated Phase 17C evaluator process; a bounded JSON protocol, not a sandbox.

Only fixed repository code and a bounded DSL are executed. No command, path,
Python source, seed, winning candidate, or trust override is accepted from stdin.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 5)]
    from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
    from rcp_rclm_runtime_v5.phase17.challenge_protocol import (
        EvaluatorSession, MAX_WIRE_BYTES, MAX_EVENTS, parse_wire, wire_bytes,
    )
    try:
        predecessor = reopen_phase16(
            capture_archive=root / 'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
            closure_archive=root / ('artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/'
                                    'runtime-v4-phase16-final-closure-31153935872-1.zip'),
            phase15_bundle=root / ('artifacts/private_phase16/bootstrap/'
                                   'runtime-v4-phase15-bundle-30969783629-1.zip'))
        session = EvaluatorSession(predecessor)
        for _ in range(MAX_EVENTS):
            line = sys.stdin.buffer.readline(MAX_WIRE_BYTES + 2)
            if not line:
                return 0 if session.sealed else 3
            if not line.endswith(b'\n') or len(line) > MAX_WIRE_BYTES + 1:
                raise ValueError('invalid frame')
            response = session.handle(parse_wire(line[:-1]))
            sys.stdout.buffer.write(wire_bytes(response) + b'\n')
            sys.stdout.buffer.flush()
            if session.sealed:
                return 0
        return 4
    except Exception:
        # Never interpolate exception text: private payloads/paths stay out of
        # pre-reveal protocol errors. Details can be tested in-process offline.
        sys.stdout.buffer.write(b'{"error":"evaluator_fail_closed"}\n')
        sys.stdout.buffer.flush()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
