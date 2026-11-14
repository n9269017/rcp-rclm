"""Fixed Phase17O worker; no caller-selected code, path, entropy, or trust anchor."""
from __future__ import annotations
from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 5)]
    from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
    from rcp_rclm_runtime_v5.phase17.metered_worker import MeteredEvaluatorSession, WORKER_PROTOCOL
    from rcp_rclm_runtime_v5.phase17.challenge_protocol import parse_wire, wire_bytes, MAX_WIRE_BYTES, MAX_EVENTS, require
    from rcp_rclm_runtime_v5.phase17.controller import _keys
    try:
        # The parent has persisted the full grant before this process launch.
        # Bootstrap work is deliberately outside the abstract vector tariff.
        parent = reopen_phase16(
            capture_archive=root / 'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
            closure_archive=root / ('artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/'
                                    'runtime-v4-phase16-final-closure-31153935872-1.zip'),
            phase15_bundle=root / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip')
        def read():
            line = sys.stdin.buffer.readline(MAX_WIRE_BYTES + 2)
            require(line.endswith(b'\n') and len(line) <= MAX_WIRE_BYTES + 1, 'invalid frame')
            return parse_wire(line[:-1])
        def emit(value):
            sys.stdout.buffer.write(wire_bytes(value) + b'\n')
            sys.stdout.buffer.flush()
        first = read()
        _keys(first, {'protocol', 'grant'}, 'worker admission')
        require(first['protocol'] == WORKER_PROTOCOL, 'worker protocol')
        session = MeteredEvaluatorSession(parent, first['grant'])
        grant_hash = session.grant['grant_hash']
        emit({'protocol': WORKER_PROTOCOL, 'event': 'grant_received', 'grant_hash': grant_hash})
        for _ in range(MAX_EVENTS):
            response = session.handle(read())
            emit({'protocol': WORKER_PROTOCOL, 'grant_hash': grant_hash, 'response': response,
                  'accounting': session.meter.summary() if session.sealed else None})
            if session.sealed:
                return 0
        return 4
    except Exception:
        # Hidden entropy, private probes, local paths and detailed failures stay out.
        sys.stdout.buffer.write(b'{"error":"campaign_evaluator_fail_closed"}\n')
        sys.stdout.buffer.flush()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
