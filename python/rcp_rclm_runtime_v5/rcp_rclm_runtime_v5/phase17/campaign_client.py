"""Transport to one fixed metered worker. Grants come from the external authority.

This client alone is not a budget authorization: use run_campaign_session, which
persists the reservation before constructing it. Separate processes and a reduced
environment are not protection against hostile code running as the same OS user.
"""
from __future__ import annotations
import queue
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

from .campaign_budget import validate_grant
from .challenge_client import worker_environment
from .challenge_protocol import (
    CLAIMS, PROTOCOL, MAX_WIRE_BYTES, digest, parse_wire, wire_bytes, require, transcript_bytes,
)
from .controller import ControlError, _keys
from .metered_worker import WORKER_PROTOCOL


class CampaignEvaluatorClient:
    def __init__(self, grant: dict, *, response_timeout: float = 30.0):
        require(type(response_timeout) in (int, float) and 0 < response_timeout <= 120,
                'response timeout outside bounded profile')
        self.grant = validate_grant(grant)
        self.timeout = response_timeout
        self.events: list[dict] = []
        self.previous = '0' * 64
        self.closed = False
        self.sealed = False
        self.accounting = None
        self.process = None
        self._reader = None
        self._directory = tempfile.TemporaryDirectory(prefix='rcp-phase17o-worker-')
        self._stderr = tempfile.TemporaryFile()
        self._responses: queue.Queue = queue.Queue(maxsize=2)
        root = Path(__file__).resolve().parents[4]
        try:
            self.process = subprocess.Popen(
                [sys.executable, '-I', '-S', '-B', '-u', str(root / 'scripts/phase17_campaign_worker.py')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                cwd=self._directory.name, env=worker_environment(), shell=False, close_fds=True)
            self._reader = threading.Thread(target=self._read, daemon=True)
            self._reader.start()
            self._write({'protocol': WORKER_PROTOCOL, 'grant': self.grant})
            ack = self._receive()
            _keys(ack, {'protocol', 'event', 'grant_hash'}, 'grant acknowledgment')
            require(ack == {'protocol': WORKER_PROTOCOL, 'event': 'grant_received',
                            'grant_hash': self.grant['grant_hash']}, 'worker grant substitution')
        except BaseException:
            self.close()
            raise

    def _write(self, value: dict):
        self.process.stdin.write(wire_bytes(value) + b'\n')
        self.process.stdin.flush()

    def _read(self):
        try:
            while True:
                raw = self.process.stdout.readline(MAX_WIRE_BYTES + 2)
                self._responses.put(raw if raw else None, timeout=1)
                if not raw or len(raw) > MAX_WIRE_BYTES + 1:
                    return
        except (OSError, ValueError, queue.Full):
            return

    def _receive(self) -> dict:
        raw = self._responses.get(timeout=self.timeout)
        require(type(raw) is bytes and raw.endswith(b'\n') and len(raw) <= MAX_WIRE_BYTES + 1,
                'worker stopped or invalid frame')
        return parse_wire(raw[:-1])

    def request(self, op: str, **fields) -> dict:
        require(not self.closed and not self.sealed, 'closed/sealed metered worker')
        request = parse_wire(wire_bytes({'protocol': PROTOCOL, 'op': op, **fields}))
        try:
            self._write(request)
            outer = self._receive()
            _keys(outer, {'protocol', 'grant_hash', 'response', 'accounting'}, 'metered response')
            require(outer['protocol'] == WORKER_PROTOCOL and outer['grant_hash'] == self.grant['grant_hash'],
                    'worker response grant mismatch')
            response = outer['response']
            _keys(response, {'protocol', 'sequence', 'request_hash', 'previous_response_hash',
                             'payload', 'response_hash'}, 'evaluator response')
            require(response['protocol'] == PROTOCOL and type(response['sequence']) is int and
                    response['sequence'] == len(self.events) and response['request_hash'] == digest(request) and
                    response['previous_response_hash'] == self.previous and
                    response['response_hash'] == digest({k: v for k, v in response.items() if k != 'response_hash'}),
                    'evaluator response binding mismatch')
            require(type(response['payload']) is dict and
                    wire_bytes(response['payload'].get('claims')) == wire_bytes(CLAIMS), 'worker authority escalation')
            require((type(outer['accounting']) is dict if op == 'seal' else outer['accounting'] is None),
                    'accounting revealed early or missing after seal')
            self.events.append({'request': request, 'response': response})
            self.previous = response['response_hash']
            if op == 'seal':
                require(response['payload'].get('event') == 'session_sealed', 'seal not acknowledged')
                self.process.stdin.close()
                require(self.process.wait(timeout=self.timeout) == 0, 'worker abnormal termination')
                self.accounting = parse_wire(wire_bytes(outer['accounting']))
                self.sealed = True
            return parse_wire(wire_bytes(response['payload']))
        except (OSError, ValueError, TypeError, KeyError, queue.Empty, subprocess.TimeoutExpired) as exc:
            self.close()
            raise ControlError('metered evaluator transport/protocol failed closed') from exc

    def transcript(self) -> bytes:
        require(self.sealed, 'worker transcript not sealed')
        return transcript_bytes(self.events)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=10)
            if self._reader is not None:
                self._reader.join(timeout=2)
            for pipe in (self.process.stdin, self.process.stdout):
                if pipe is not None and not pipe.closed:
                    try:
                        pipe.close()
                    except OSError:
                        pass
        self._stderr.close()
        self._directory.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
