"""Phase 17C bounded challenge/evaluation protocol, never promotion authority.

The reference grammar/interpreter is deliberately separate from Phase 16's
candidate executor. The domain is the existing four-integer-vector DSL, NOT
full-tensor inference or general empirical capability. Runtime entropy belongs
to the evaluator process and is sampled only after validated objective freeze.
A sealed transcript permits deterministic checking; a digest is not a signature.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v5.phase17.bootstrap import (
    HistoricalPredecessor, OPERATIONS, _validate_program,
)
from rcp_rclm_runtime_v5.phase17.controller import (
    Action, ControlError, FAMILIES, FIXED_VERIFIER, SEMANTICS, _hash, _integer, _keys,
)
from rcp_rclm_runtime_v5.phase17.objectives import (
    ObjectiveDecision, freeze_bootstrap_objective,
)

POLICY = "phase17c.independent-random-vector-spec.v1"
PROTOCOL = "runtime.v5.phase17.challenge-protocol.v1"
MAX_WIRE_BYTES = 128 * 1024
MAX_TRANSCRIPT_BYTES = 2 * 1024 * 1024
MAX_EVENTS = 66  # open + (freeze/evaluate)*32 + seal
PROBE_COUNT = 8
CLAIMS = {
    "promotion_authorized": False,
    "phase17_exit_closed": False,
    "gate_e_closed": False,
    "egc0_started": False,
    "fresh_lean_verification": False,
    "full_frontier_recertified": False,
    "os_security_sandbox": False,
    "phase18_independent_replay": False,
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ControlError(reason)


def wire_bytes(obj: dict) -> bytes:
    try:
        data = canonical_json_bytes(obj)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ControlError("invalid protocol value") from exc
    require(len(data) <= MAX_WIRE_BYTES, "protocol message exceeds bound")
    return data


def parse_wire(data: bytes) -> dict:
    require(type(data) is bytes and 0 < len(data) <= MAX_WIRE_BYTES, "invalid wire length")
    try:
        obj = load_json_strict(data)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ControlError("invalid canonical protocol JSON") from exc
    require(type(obj) is dict and canonical_json_bytes(obj) == data, "noncanonical protocol object")
    return obj


def reference_grammar(state: dict, turn_index: int, nonce: str) -> tuple[dict, ...]:
    """Independent re-expression of the fixed Phase 16 8x4 grammar."""
    _integer(turn_index, "turn_index")
    _hash(nonce, "nonce")
    programs = []
    for index, family in enumerate(FAMILIES):
        generation = state["component_generations"][family] + 1
        for variant in range(4):
            seed = digest({"domain": "phase16.legal_mutation_program.v1",
                           "active_package_hash": state["active_package_hash"],
                           "promotion_index": turn_index, "family": family,
                           "variant": variant, "generation": generation,
                           "public_nonce_hash": nonce})
            values = [int(seed[(offset * 2) % 56:(offset * 2) % 56 + 8], 16) % 33 - 16
                      for offset in (index + variant, index + variant + 7)]
            programs.append({"schema_id": "runtime.v4.phase16.mutation_program.v1",
                             "promotion_index": turn_index, "family": family,
                             "variant": variant, "generation": generation,
                             "operation_id": OPERATIONS[family],
                             "parameter_a": values[0], "parameter_b": values[1],
                             "public_nonce_hash": nonce})
    return tuple(sorted(programs, key=digest))


def vector_semantics(family: str, variant: int, a: int, b: int,
                     vector: list[int]) -> list[int]:
    """Reference integer semantics; no eval, executable source or import payload."""
    require(family in FAMILIES and type(variant) is int and 0 <= variant < 4,
            "invalid bounded operation")
    require(type(a) is int and type(b) is int and -16 <= a <= 16 and -16 <= b <= 16,
            "invalid bounded parameters")
    require(type(vector) is list and len(vector) == 4 and
            all(type(x) is int and -64 <= x <= 64 for x in vector), "invalid probe vector")
    v = variant + 1
    x0, x1, x2, x3 = vector
    if family == "adapter_policy":
        return [v * x + a - b for x in vector]
    if family == "architecture_policy":
        return [vector[(i + v + 1) % 4] + a * (i + 1) + b for i in range(4)]
    if family == "memory_policy":
        result = [vector[(i + v) % 4] for i in range(4)]
        result[0] += a
        return result
    if family == "optimizer_policy":
        return [sum(vector) + a + v * (i + 1) * (i + 2) // 2 - b * (i + 1)
                for i in range(4)]
    if family == "planner_policy":
        return [x0 + a, x1 * v, x2 - b, x3 + x0 * v]
    if family == "retrieval_policy":
        return [vector[(i * v + abs(b)) % 4] for i in range(4)]
    if family == "tool_policy":
        return [x0 + x1 + a, x1 - x2 + b, x2 * v, x3 + a - b]
    return sorted(x + a * v - b for x in vector)


def execute_reference(program: dict, vector: list[int]) -> list[int]:
    _validate_program(program)
    return vector_semantics(program["family"], program["variant"],
                            program["parameter_a"], program["parameter_b"], vector)


def realize_candidate(program: dict, freeze: dict) -> dict:
    """Immutable bounded-DSL delta descriptor, not installation in an active model."""
    _validate_program(program)
    payload = {"schema_id": "runtime.v5.phase17.bounded_candidate.v1",
               "predecessor_state_hash": freeze["predecessor_state_hash"],
               "predecessor_package_hash": freeze["active_package_hash"],
               "objective_freeze_hash": freeze["freeze_hash"],
               "program": program, "program_hash": digest(program),
               "fixed_verifier_hash": FIXED_VERIFIER, "semantics_id": SEMANTICS,
               "installed": False, "promotion_authorized": False}
    # Serialize now to detach all caller-owned dictionaries.
    payload = parse_wire(wire_bytes(payload))
    payload["artifact_hash"] = digest(payload)
    return payload


def _secret_from_entropy(entropy: bytes, family: str) -> dict:
    """No candidate list, winning-program index, future horizon or evaluator hint."""
    require(type(entropy) is bytes and len(entropy) == 32, "32-byte evaluator entropy required")
    def word(label: str) -> int:
        return int.from_bytes(hashlib.sha256(POLICY.encode() + b"\x00" + entropy +
                                            b"\x00" + label.encode()).digest(), "big")
    # Fixed mapping from uniformly random bytes; modulo bias is declared and
    # immaterial to protocol tests. No claim of a uniform 33-element sampler.
    return {"entropy_hex": entropy.hex(), "objective_family": family,
            "target_variant": word("variant") % 4,
            "target_a": word("a") % 33 - 16, "target_b": word("b") % 33 - 16,
            "probes": [[word(f"probe:{i}:{j}") % 65 - 32 for j in range(4)]
                       for i in range(PROBE_COUNT)]}


def _outcomes(secret: dict, program: dict, installed: tuple[bytes, ...]) -> tuple[str, list[str]]:
    family = secret["objective_family"]
    expected = [vector_semantics(family, secret["target_variant"], secret["target_a"],
                                 secret["target_b"], x) for x in secret["probes"]]
    nontrivial = any(y != x for y, x in zip(expected, secret["probes"], strict=True))
    inherited = [load_json_strict(raw) for raw in installed]
    predecessor_pass = any(p["family"] == family and
        all(execute_reference(p, x) == y for x, y in zip(secret["probes"], expected, strict=True))
        for p in inherited)
    candidate_pass = program["family"] == family and all(
        execute_reference(program, x) == y for x, y in zip(secret["probes"], expected, strict=True))
    if nontrivial and not predecessor_pass and candidate_pass:
        return "candidate_passed", []
    # Do not expose hidden vectors, expected outputs, scores, target parameters,
    # program identity or even the precise rejection cause before sealing.
    return "reject", ["bounded_challenge_rejected"]


@dataclass(frozen=True, slots=True)
class TranscriptVerification:
    transcript_hash: str
    candidate_evaluations: int
    terminal_action: str
    selected_candidate_hash: str | None


class EvaluatorSession:
    """Trusted data interpreter with a single open/search/seal lifecycle.

    Call this in the dedicated worker. Direct in-process use is for tests and
    offline recomputation, NOT a claim of evaluator isolation.
    """
    def __init__(self, predecessor: HistoricalPredecessor):
        require(type(predecessor) is HistoricalPredecessor, "historical predecessor required")
        predecessor.validate()
        self.parent = predecessor
        self.events: list[dict] = []
        self.opened = False
        self.sealed = False
        self.pending: dict | None = None
        self.considered: list[str] = []
        self.passed: str | None = None
        self.previous = "0" * 64
        self.secret: dict | None = None
        self.public: dict | None = None
        self.programs: dict[str, dict] = {}
        self.budget = 0
        self.freeze: dict | None = None

    def _validate_open(self, request: dict) -> tuple[dict, dict]:
        _keys(request, {"protocol", "op", "objective", "freeze", "candidate_credits"}, "open")
        credits = _integer(request["candidate_credits"], "candidate_credits")
        require(credits <= 32, "credits exceed current grammar")
        decision = ObjectiveDecision(wire_bytes(request["objective"]))
        obj = decision.to_json()
        expected = freeze_bootstrap_objective(decision, self.parent,
                      turn_index=obj["turn_index"], public_nonce_hash=obj["public_nonce_hash"])
        require(type(request["freeze"]) is dict and
                wire_bytes(request["freeze"]) == wire_bytes(expected), "objective freeze mismatch")
        return obj, expected

    def _open(self, request: dict, *, replay_entropy: bytes | None = None) -> dict:
        require(not self.opened, "session already open")
        objective, freeze = self._validate_open(request)
        # Validation above precedes the ONLY live entropy draw. The wire
        # protocol cannot supply replay_entropy; offline verifier calls below.
        entropy = secrets.token_bytes(32) if replay_entropy is None else replay_entropy
        secret = _secret_from_entropy(entropy, objective["objective_family"])
        programs = reference_grammar(self.parent.state, freeze["turn_index"], freeze["public_nonce_hash"])
        self.programs = {digest(p): p for p in programs}
        self.budget = request["candidate_credits"]
        self.freeze = freeze
        self.secret = secret
        self.opened = True
        self.public = {"policy_id": POLICY, "objective_freeze_hash": freeze["freeze_hash"],
                       "predecessor_state_hash": freeze["predecessor_state_hash"],
                       "active_package_hash": freeze["active_package_hash"],
                       "turn_index": freeze["turn_index"], "public_nonce_hash": freeze["public_nonce_hash"],
                       "objective_family": objective["objective_family"],
                       "candidate_credits": self.budget, "probe_count": PROBE_COUNT,
                       "grammar_hash": digest(list(programs)),
                       "challenge_commitment_hash": digest({"policy": POLICY, "freeze": freeze,
                                                             "credits": self.budget, "secret": secret}),
                       "domain": "bounded_four_integer_vector_dsl",
                       "successor_availability_assumed": False}
        return {"event": "challenge_committed", "public_challenge": self.public, "claims": dict(CLAIMS)}

    def terminal(self) -> str | None:
        if self.passed is not None:
            return Action.AWAIT_ROOT_VERIFICATION.value
        if len(self.considered) == 32:
            return Action.SEARCH_EXHAUSTED.value
        if len(self.considered) == self.budget:
            return Action.RESOURCE_EXHAUSTED.value
        return None

    def handle(self, request: dict) -> dict:
        return self._handle(request)

    def _handle(self, request: dict, *, replay_entropy: bytes | None = None) -> dict:
        request = parse_wire(wire_bytes(request))
        require(not self.sealed, "sealed session cannot be reused")
        require(request.get("protocol") == PROTOCOL, "protocol mismatch")
        op = request.get("op")
        if op == "open":
            payload = self._open(request, replay_entropy=replay_entropy)
        else:
            require(self.opened, "validated objective freeze required first")
            if op == "freeze_candidate":
                _keys(request, {"protocol", "op", "artifact_hash", "program_hash"}, "candidate freeze")
                require(self.pending is None and self.terminal() is None, "search not accepting a candidate")
                _hash(request["artifact_hash"], "artifact_hash")
                h = _hash(request["program_hash"], "program_hash")
                require(h in self.programs and h not in self.considered, "illegal or repeated candidate")
                expected = realize_candidate(self.programs[h], self.freeze)
                require(expected["artifact_hash"] == request["artifact_hash"], "candidate artifact substitution")
                pending = {"program_hash": h, "artifact_hash": request["artifact_hash"],
                           "challenge_commitment_hash": self.public["challenge_commitment_hash"],
                           "objective_freeze_hash": self.freeze["freeze_hash"],
                           "previous_response_hash": self.previous,
                           "evaluation_index": len(self.considered)}
                pending["candidate_freeze_hash"] = digest(pending)
                self.pending = pending
                payload = {"event": "candidate_frozen", "receipt": pending, "claims": dict(CLAIMS)}
            elif op == "evaluate":
                _keys(request, {"protocol", "op", "candidate_freeze_hash", "artifact"}, "evaluate")
                require(self.pending is not None, "candidate must be frozen before evaluation")
                require(request["candidate_freeze_hash"] == self.pending["candidate_freeze_hash"],
                        "stale candidate freeze")
                h = self.pending["program_hash"]
                expected = realize_candidate(self.programs[h], self.freeze)
                require(type(request["artifact"]) is dict and
                        wire_bytes(request["artifact"]) == wire_bytes(expected), "candidate mutated after freeze")
                verdict, reasons = _outcomes(self.secret, self.programs[h], self.parent.accepted_programs)
                payload = {"event": "candidate_evaluated", "program_hash": h,
                           "artifact_hash": expected["artifact_hash"],
                           "candidate_freeze_hash": self.pending["candidate_freeze_hash"],
                           "predecessor_state_hash": self.freeze["predecessor_state_hash"],
                           "challenge_commitment_hash": self.public["challenge_commitment_hash"],
                           "evaluation_index": len(self.considered), "verdict": verdict,
                           "reason_codes": reasons, "claims": dict(CLAIMS)}
                payload["evaluation_hash"] = digest(payload)
                self.considered.append(h)
                self.pending = None
                if verdict == "candidate_passed":
                    self.passed = h
            elif op == "seal":
                _keys(request, {"protocol", "op", "terminal_action"}, "seal")
                require(self.pending is None, "unfinished candidate cannot be sealed")
                action = request["terminal_action"]
                expected = self.terminal()
                require(action == expected if expected is not None else
                        action in (Action.EXTERNAL_STOP.value, Action.SAFETY_HALT.value),
                        "terminal cause not supported by retained observations")
                self.sealed = True
                payload = {"event": "session_sealed", "terminal_action": action,
                           "candidate_evaluations": len(self.considered),
                           "selected_candidate_hash": self.passed, "opening": self.secret,
                           "complete_bounded_coverage": len(self.considered) == 32,
                           "claims": dict(CLAIMS)}
            else:
                raise ControlError("unsupported protocol operation")
        response = {"protocol": PROTOCOL, "sequence": len(self.events),
                    "request_hash": digest(request), "previous_response_hash": self.previous,
                    "payload": payload}
        response["response_hash"] = digest(response)
        # Snapshots detach public messages from evaluator state.
        response = parse_wire(wire_bytes(response))
        self.previous = response["response_hash"]
        self.events.append({"request": request, "response": response})
        return parse_wire(wire_bytes(response))


def transcript_bytes(events: list[dict]) -> bytes:
    return canonical_json_bytes({"schema_id": "runtime.v5.phase17.sealed_transcript.v1", "events": events})


def verify_transcript(predecessor: HistoricalPredecessor, data: bytes, *,
                      expected_transcript_hash: str) -> TranscriptVerification:
    """Recompute sealed finite DSL observations; not author authentication or Lean."""
    _hash(expected_transcript_hash, "external transcript anchor")
    require(type(data) is bytes and len(data) <= MAX_TRANSCRIPT_BYTES, "transcript size bound")
    require(hashlib.sha256(data).hexdigest() == expected_transcript_hash, "transcript anchor mismatch")
    try:
        obj = load_json_strict(data)
        _keys(obj, {"schema_id", "events"}, "transcript")
        require(canonical_json_bytes(obj) == data, "transcript must be canonical")
        require(obj["schema_id"] == "runtime.v5.phase17.sealed_transcript.v1", "transcript schema")
        events = obj["events"]
        require(type(events) is list and 2 <= len(events) <= MAX_EVENTS, "transcript event bound")
        last = events[-1]["response"]["payload"]
        require(last["event"] == "session_sealed", "transcript must end at seal")
        entropy_hex = last["opening"]["entropy_hex"]
        require(type(entropy_hex) is str and len(entropy_hex) == 64 and
                entropy_hex == bytes.fromhex(entropy_hex).hex(), "invalid opening")
        session = EvaluatorSession(predecessor)
        for i, event in enumerate(events):
            _keys(event, {"request", "response"}, "event")
            expected = session._handle(event["request"], replay_entropy=bytes.fromhex(entropy_hex) if i == 0 else None)
            require(type(event["response"]) is dict and
                    wire_bytes(event["response"]) == wire_bytes(expected), "transcript recomputation mismatch")
        require(session.sealed, "missing terminal seal")
        return TranscriptVerification(expected_transcript_hash, len(session.considered),
                                      last["terminal_action"], session.passed)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        if isinstance(exc, ControlError):
            raise
        raise ControlError("malformed transcript") from exc
