"""Fixed-worker pipe client. Process separation is NOT a hostile-code sandbox."""
from __future__ import annotations
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading

from rcp_rclm_runtime_v5.phase17.challenge_protocol import (
    PROTOCOL, MAX_WIRE_BYTES, CLAIMS, digest, parse_wire, wire_bytes, require,
    transcript_bytes,
)
from rcp_rclm_runtime_v5.phase17.controller import ControlError, _keys


def worker_environment() -> dict[str, str]:
    # No arbitrary inherited API credentials, PYTHONPATH or evaluator seeds.
    allowed = ('SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'LANG', 'LC_ALL')
    return {k: v for k, v in os.environ.items() if k.upper() in allowed}


class EvaluatorClient:
    def __init__(self, *, response_timeout: float = 30.0):
        require(type(response_timeout) in (int, float) and 0 < response_timeout <= 120,
                'response timeout outside bounded profile')
        self.timeout = response_timeout
        self.events: list[dict] = []
        self.previous = '0' * 64
        self.closed = False
        self.sealed = False
        self._directory = tempfile.TemporaryDirectory(prefix='rcp-phase17c-worker-')
        root = Path(__file__).resolve().parents[4]
        self._stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(
                [sys.executable, '-I', '-S', '-B', '-u', str(root / 'scripts/phase17_evaluator_worker.py')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                cwd=self._directory.name, env=worker_environment(), shell=False,
                close_fds=True,
            )
        except Exception:
            self._stderr.close()
            self._directory.cleanup()
            raise
        self._responses: queue.Queue = queue.Queue(maxsize=2)
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self) -> None:
        try:
            while True:
                line = self.process.stdout.readline(MAX_WIRE_BYTES + 2)
                if not line:
                    self._responses.put(None, timeout=1)
                    return
                self._responses.put(line, timeout=1)
                if len(line) > MAX_WIRE_BYTES + 1:
                    return
        except (OSError, ValueError, queue.Full):
            return

    def request(self, op: str, **fields) -> dict:
        require(not self.closed and not self.sealed, 'closed/sealed evaluator client')
        request = parse_wire(wire_bytes({'protocol': PROTOCOL, 'op': op, **fields}))
        try:
            self.process.stdin.write(wire_bytes(request) + b'\n')
            self.process.stdin.flush()
            raw = self._responses.get(timeout=self.timeout)
            require(type(raw) is bytes and raw.endswith(b'\n') and len(raw) <= MAX_WIRE_BYTES + 1,
                    'evaluator stopped or returned an invalid frame')
            response = parse_wire(raw[:-1])
            _keys(response, {'protocol', 'sequence', 'request_hash', 'previous_response_hash',
                             'payload', 'response_hash'}, 'evaluator response')
            require(response['protocol'] == PROTOCOL and type(response['sequence']) is int and
                    response['sequence'] == len(self.events) and
                    response['request_hash'] == digest(request) and
                    response['previous_response_hash'] == self.previous and
                    response['response_hash'] == digest({k: v for k, v in response.items() if k != 'response_hash'}),
                    'evaluator response binding mismatch')
            require(type(response['payload']) is dict and
                    wire_bytes(response['payload'].get('claims')) == wire_bytes(CLAIMS),
                    'evaluator authority escalation')
            self.events.append({'request': request, 'response': response})
            self.previous = response['response_hash']
            if op == 'seal':
                require(response['payload'].get('event') == 'session_sealed', 'seal not acknowledged')
                self.sealed = True
                self.process.stdin.close()
                require(self.process.wait(timeout=self.timeout) == 0, 'evaluator abnormal termination')
            return parse_wire(wire_bytes(response['payload']))
        except (OSError, ValueError, TypeError, KeyError, queue.Empty, subprocess.TimeoutExpired) as exc:
            self.close()
            raise ControlError('evaluator transport/protocol failed closed') from exc

    def transcript(self) -> bytes:
        require(self.sealed, 'unsealed transcript cannot reveal a completed transaction')
        return transcript_bytes(self.events)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=10)
        self._reader.join(timeout=2)
        for pipe in (self.process.stdin, self.process.stdout):
            if pipe is not None and not pipe.closed:
                try:
                    pipe.close()
                except OSError:
                    pass  # A killed worker can leave a buffered broken pipe.
        self._stderr.close()
        self._directory.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
