"""Phase 17N: precharged, single-writer accounting for a declared work profile.

This is NOT OS resource containment or complete campaign resource accounting.
Tariffs count candidate admissions and four-value reference-interpreter calls.
No CPU/GPU time, energy, RSS, storage, or uninstrumented work is silently zeroed.
A hash chain needs an external expected head: hashes do not attest execution or
prevent rollback when the caller also accepts a rolled-back anchor.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import time
from typing import Callable

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict

SCHEMA = "runtime.v5.phase17.resource-ledger.v1"
PROFILE = "phase17n.bounded-vector-reference-work.v1"
DIMENSIONS = ("candidate_attempts", "vector_calls", "input_values", "output_values")
WEIGHTS = (64, 16, 1, 1)
TARIFFS = {"candidate": (1, 0, 0, 0), "vector": (0, 1, 4, 4)}
MAX_NAT = (1 << 63) - 1
MAX_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 4096
MAX_EVENT_BYTES = 4096
ZERO = "0" * 64
BINDING_FIELDS = {"predecessor_package_hash", "candidate_package_hash", "transcript_sha256", "fixed_verifier_hash"}

class ResourceError(ValueError):
    """Malformed, stale, ambiguous, or unsupported resource evidence."""

class ResourceExhausted(ResourceError):
    """Declared budget exhausted; not a complete-search certificate."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ResourceError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def nat(value: object) -> int:
    require(type(value) is int and 0 <= value <= MAX_NAT, "bounded nonnegative integer required")
    return value


def digest(value: object) -> str:
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "canonical digest required")
    return value


def exact(value: object, keys: set[str]) -> dict:
    require(type(value) is dict and set(value) == keys, "exact record fields required")
    return value


def vector(value: object) -> tuple[int, int, int, int]:
    require(type(value) in (list, tuple) and len(value) == 4, "four resource dimensions required")
    return tuple(nat(x) for x in value)


def cost(values: object) -> int:
    return nat(sum(w * x for w, x in zip(WEIGHTS, vector(values), strict=True)))


def add(a: object, b: object) -> tuple[int, int, int, int]:
    return tuple(nat(x + y) for x, y in zip(vector(a), vector(b), strict=True))


def canonical(value: object) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ResourceError("invalid canonical resource value") from exc


def parse(raw: bytes) -> dict:
    require(type(raw) is bytes and 0 < len(raw) <= MAX_EVENT_BYTES, "invalid resource record length")
    try:
        result = load_json_strict(raw)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ResourceError("invalid canonical resource record") from exc
    require(type(result) is dict and canonical(result) == raw, "noncanonical resource record")
    return result


def binding(value: object) -> dict:
    return {k: digest(v) for k, v in exact(value, BINDING_FIELDS).items()}


@dataclass(frozen=True, slots=True)
class Policy:
    limits: tuple[int, int, int, int]
    cost_limit: int

    def __post_init__(self):
        object.__setattr__(self, "limits", vector(self.limits))
        nat(self.cost_limit)
        cost(self.limits)  # Reject profiles outside the bounded arithmetic model.

    def to_json(self) -> dict:
        return {"profile": PROFILE, "dimensions": list(DIMENSIONS), "weights": list(WEIGHTS),
                "limits": list(self.limits), "cost_limit": self.cost_limit}

    @classmethod
    def from_json(cls, value: object) -> "Policy":
        d = exact(value, {"profile", "dimensions", "weights", "limits", "cost_limit"})
        require(d["profile"] == PROFILE and d["dimensions"] == list(DIMENSIONS), "wrong resource profile")
        require(type(d["weights"]) is list and tuple(nat(x) for x in d["weights"]) == WEIGHTS,
                "resource conversion weights changed")
        return cls(vector(d["limits"]), nat(d["cost_limit"]))

    def fits(self, spent: object) -> bool:
        v = vector(spent)
        return all(x <= y for x, y in zip(v, self.limits, strict=True)) and cost(v) <= self.cost_limit


def full_grammar_policy(installed_count: int, *, candidate_limit: int = 32) -> Policy:
    """Declared before replay; depends on inherited inventory, not winning rank."""
    require(nat(installed_count) <= 1024 and nat(candidate_limit) <= 32, "profile inventory exceeds bounds")
    calls = (1 + installed_count + candidate_limit) * 8
    limits = (candidate_limit, calls, 4 * calls, 4 * calls)
    return Policy(limits, cost(limits))


def event(body: dict, index: int, previous: str) -> dict:
    core = {"index": nat(index), "previous": digest(previous), "body": body}
    return {**core, "hash": sha(b"RCPRCLM-PHASE17N-EVENT-V1\0" + canonical(core))}


def operation(body: dict) -> tuple[str, str, str, tuple[int, int, int, int]]:
    op = body["operation"]
    require(type(op) is str and op in TARIFFS, "unknown metered operation")
    ident = body["operation_id"]
    require(type(ident) is str and re.fullmatch(r"[A-Za-z0-9:_-]{1,96}", ident) is not None,
            "invalid operation identity")
    source = digest(body["input_sha256"])
    charge = vector(body["charge"])
    require(charge == TARIFFS[op], "operation tariff changed")
    return op, ident, source, charge


@dataclass(frozen=True, slots=True)
class Replay:
    head: str
    event_count: int
    spent: tuple[int, int, int, int]
    status: str
    pending_hash: str | None
    operation_ids: tuple[str, ...]
    charges: tuple[str, ...]

    @property
    def charged_cost(self) -> int:
        return cost(self.spent)


def replay(raw: bytes, *, expected_head: str, policy: Policy, expected_binding: dict) -> Replay:
    """Recompute charges and state. The expected head/policy/binding are external."""
    require(type(policy) is Policy, "exact frozen policy required")
    wanted = binding(expected_binding)
    digest(expected_head)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and raw.endswith(b"\n"),
            "missing, truncated, or oversized resource journal")
    lines = raw.splitlines(keepends=True)
    require(0 < len(lines) <= MAX_EVENTS, "resource journal event bound exceeded")
    head, spent, status, pending = ZERO, (0, 0, 0, 0), "new", None
    ids: list[str] = []
    charges: list[str] = []
    for index, line in enumerate(lines):
        require(line.endswith(b"\n") and not line.endswith(b"\r\n"), "noncanonical journal newline")
        row = exact(parse(line[:-1]), {"index", "previous", "body", "hash"})
        require(nat(row["index"]) == index and digest(row["previous"]) == head, "broken event order or lineage")
        require(row == event(row["body"], index, head), "event hash mismatch")
        body = row["body"]
        require(type(body) is dict and type(body.get("kind")) is str, "resource event kind required")
        kind = body["kind"]
        if index == 0:
            exact(body, {"kind", "schema", "binding", "policy"})
            require(kind == "open" and body["schema"] == SCHEMA, "resource header required")
            require(binding(body["binding"]) == wanted and Policy.from_json(body["policy"]) == policy,
                    "external binding or policy differs")
            status = "open"
        elif kind in ("reserve", "exhausted"):
            require(status == "open" and pending is None, "reservation after stop or during pending work")
            keys = {"kind", "operation", "operation_id", "input_sha256", "charge"}
            exact(body, keys | ({"spent_after"} if kind == "reserve" else {"reason"}))
            op, ident, _, charge = operation(body)
            require(ident not in ids, "duplicate operation identity")
            proposed = add(spent, charge)
            if kind == "reserve":
                require(policy.fits(proposed), "reservation exceeds declared envelope")
                require(vector(body["spent_after"]) == proposed, "forged cumulative usage")
                spent = proposed
                ids.append(ident)
                charges.append(op)
                pending = row["hash"]
                status = "pending"
            else:
                require(not policy.fits(proposed) and body["reason"] == "declared_budget", "false exhaustion")
                status = "resource_exhausted"
        elif kind == "result":
            exact(body, {"kind", "reservation_hash", "ok", "result_sha256", "error_code", "elapsed_ns"})
            require(status == "pending" and digest(body["reservation_hash"]) == pending, "stale/unreserved result")
            require(type(body["ok"]) is bool, "Boolean result required")
            nat(body["elapsed_ns"])
            if body["ok"]:
                digest(body["result_sha256"])
                require(body["error_code"] is None, "successful result has error")
                status = "open"
            else:
                require(body["result_sha256"] is None and body["error_code"] in ("operation_failed", "interrupted"),
                        "invalid failure record")
                status = "safety_halt"
            pending = None
            # Deliberately do not refund any previously reserved dimension.
        elif kind in ("seal", "stop"):
            exact(body, {"kind"})
            require(status == "open" and pending is None, "cannot seal incomplete/failed work")
            status = "sealed" if kind == "seal" else "external_stop"
        else:
            raise ResourceError("unknown resource event")
        head = row["hash"]
    require(head == expected_head, "external resource head differs")
    return Replay(head, len(lines), spent, status, pending, tuple(ids), tuple(charges))


def _no_links(path: Path) -> None:
    for item in (path, *path.parents):
        require(not item.is_symlink() and not (hasattr(item, "is_junction") and item.is_junction()), "linked resource path")


class Ledger:
    """Local single-writer journal, write-ahead reservations, no implicit recovery.

    Lock is advisory: this is not protection from hostile code with the same OS
    account. Restoring a pending operation requires explicit abandonment; its
    charge remains and the session halts. Existing bytes are never truncated.
    """
    def __init__(self, path: Path, *, policy: Policy, expected_binding: dict,
                 expected_head: str | None = None):
        self.path = Path(path).absolute()
        _no_links(self.path)
        require(self.path.parent.is_dir(), "resource journal parent must exist")
        require(type(policy) is Policy, "exact policy required")
        self.policy = policy
        self._binding_bytes = canonical(binding(expected_binding))
        self._poisoned = False
        self._closed = False
        self._lock = None
        self._file = None
        self._raw = b""
        self._state = None
        lock_path = self.path.with_name(self.path.name + ".lock")
        _no_links(lock_path)
        require(not lock_path.exists() or lock_path.is_file(), "resource lock must be a regular file")
        try:
            self._lock = open(lock_path, "a+b", buffering=0)
            if self._lock.seek(0, os.SEEK_END) == 0:
                self._lock.write(b"L")
            self._lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            if expected_head is None:
                require(not self.path.exists(), "existing journal requires external head")
                self._file = open(self.path, "x+b", buffering=0)
                first = event({"kind": "open", "schema": SCHEMA, "binding": self.binding,
                               "policy": self.policy.to_json()}, 0, ZERO)
                self._append_raw(first)
            else:
                digest(expected_head)
                require(self.path.is_file(), "resource journal missing")
                self._file = open(self.path, "r+b", buffering=0)
                raw = self._file.read(MAX_BYTES + 1)
                self._state = replay(raw, expected_head=expected_head, policy=policy, expected_binding=self.binding)
                self._raw = raw
        except BaseException:
            self.close()
            raise

    @property
    def binding(self) -> dict:
        return load_json_strict(self._binding_bytes)

    @property
    def state(self) -> Replay:
        self._check()
        return self._state

    def _check(self) -> None:
        require(not self._closed and not self._poisoned, "closed or poisoned resource ledger")
        require(self._file is not None, "resource file absent")
        _no_links(self.path)
        require(os.path.samestat(os.fstat(self._file.fileno()), self.path.stat()), "resource file replaced")
        self._file.seek(0)
        require(self._file.read(MAX_BYTES + 1) == self._raw, "resource journal changed externally")

    def _append_raw(self, row: dict) -> None:
        data = canonical(row) + b"\n"
        require(len(data) <= MAX_EVENT_BYTES + 1 and len(self._raw) + len(data) <= MAX_BYTES, "journal capacity exceeded")
        combined = self._raw + data
        next_state = replay(combined, expected_head=row["hash"], policy=self.policy, expected_binding=self.binding)
        try:
            self._file.seek(0, os.SEEK_END)
            written = self._file.write(data)
            require(written == len(data), "short resource journal write")
            self._file.flush()
            os.fsync(self._file.fileno())
        except BaseException:
            self._poisoned = True
            raise
        self._raw, self._state = combined, next_state

    def _append(self, body: dict) -> None:
        self._check()
        self._append_raw(event(body, self._state.event_count, self._state.head))

    def reserve(self, operation_kind: str, operation_id: str, input_sha256: str) -> str:
        self._check()
        require(self._state.status == "open", "resource session not open")
        require(type(operation_kind) is str and operation_kind in TARIFFS, "unknown metered operation")
        body = {"operation": operation_kind, "operation_id": operation_id,
                "input_sha256": input_sha256, "charge": list(TARIFFS[operation_kind])}
        _, ident, _, charge = operation(body)
        require(ident not in self._state.operation_ids, "duplicate operation identity")
        proposed = add(self._state.spent, charge)
        if not self.policy.fits(proposed):
            self._append({"kind": "exhausted", **body, "reason": "declared_budget"})
            raise ResourceExhausted("declared work envelope exhausted before execution")
        self._append({"kind": "reserve", **body, "spent_after": list(proposed)})
        return self._state.head

    def finish(self, reservation_hash: str, *, result: bytes | None,
               elapsed_ns: int, error_code: str | None = None) -> None:
        self._check()
        require(self._state.status == "pending" and reservation_hash == self._state.pending_hash, "stale reservation")
        require(result is None or type(result) is bytes and len(result) <= 32768, "bounded result bytes required")
        nat(elapsed_ns)
        self._append({"kind": "result", "reservation_hash": digest(reservation_hash),
                      "ok": error_code is None, "result_sha256": None if result is None else sha(result),
                      "error_code": error_code, "elapsed_ns": elapsed_ns})

    def perform(self, operation_kind: str, operation_id: str, input_sha256: str,
                trusted_operation: Callable[[], bytes]) -> bytes:
        """Trusted wrapper only. Candidate-supplied callbacks are not admitted."""
        require(callable(trusted_operation), "operation callable required")
        reservation = self.reserve(operation_kind, operation_id, input_sha256)
        started = time.monotonic_ns()
        try:
            raw = trusted_operation()
            require(type(raw) is bytes and len(raw) <= 32768, "operation returned invalid bytes")
            elapsed = time.monotonic_ns() - started
            nat(elapsed)
        except BaseException:
            self.finish(reservation, result=None, elapsed_ns=max(0, time.monotonic_ns() - started),
                        error_code="operation_failed")
            raise
        self.finish(reservation, result=raw, elapsed_ns=elapsed)
        return raw

    def abandon_interrupted(self) -> None:
        self._check()
        require(self._state.status == "pending", "no interrupted reservation")
        self.finish(self._state.pending_hash, result=None, elapsed_ns=0, error_code="interrupted")

    def seal(self) -> None:
        self._append({"kind": "seal"})

    def stop(self) -> None:
        self._append({"kind": "stop"})

    def journal_bytes(self) -> bytes:
        self._check()
        return self._raw

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._file is not None:
            self._file.close()
        if self._lock is not None:
            self._lock.close()  # OS releases advisory lock, including on process death.

    def __enter__(self) -> "Ledger":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
