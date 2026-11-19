"""Fresh metered reference execution of an already sealed bounded-DSL transcript.

This profile performs all eight probes (no success-dependent short circuit).
It is not a new online search, hidden challenge, or replay of historical CPU cost.
Bootstrap/validation, journaling, Python overhead, and formal proof checking are
outside this declared work tariff and are NOT represented as zero-cost work.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bootstrap import HistoricalPredecessor, _validate_program
from .challenge_protocol import execute_reference, vector_semantics, verify_transcript
from .controller import FIXED_VERIFIER
from .resource_ledger import (Ledger, Policy, ResourceError, Replay, canonical, parse,
                              binding, digest, full_grammar_policy, replay, require, sha)
from rcp_rclm_runtime.canonical.json import load_json_strict

PARENT_PACKAGE = "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535"
CANDIDATE_PACKAGE = "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
TRANSCRIPT = "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f"
# Scoped accounting has no authority to declare a full accepted transition.
FALSE_CLAIMS = (
    "complete_resource_accounting", "os_resource_containment", "historical_cost_recovered",
    "physical_execution_attested", "root_transition_verified", "promotion_authorized",
    "promotion_performed", "phase17_exit_closed", "gate_e_closed", "egc0_started",
    "live_capability_gain_demonstrated", "recursive_productivity_recertified",
    "full_frontier_recertified", "full_learned_step_instantiated")


@dataclass(frozen=True, slots=True)
class Work:
    kind: str
    identity: str
    input_bytes: bytes

    @property
    def input_hash(self) -> str:
        return sha(self.input_bytes)

    def execute(self) -> bytes:
        value = load_json_strict(self.input_bytes)
        if self.kind == "candidate":
            return canonical({"program_sha256": sha(canonical(value["program"]))})
        if value["role"] == "target":
            f, v, a, b = value["parameters"]
            result = vector_semantics(f, v, a, b, value["vector"])
        else:
            result = execute_reference(value["program"], value["vector"])
        require(type(result) is list and len(result) == 4 and all(type(x) is int for x in result),
                "fixed interpreter result shape changed")
        return canonical(result)


def prepare_work(parent: HistoricalPredecessor, transcript: bytes, *, expected_hash: str) -> tuple[Work, ...]:
    """Authenticate the sealed history before deriving the deterministic profile."""
    require(type(parent) is HistoricalPredecessor, "anchored predecessor required")
    digest(expected_hash)
    verify_transcript(parent, transcript, expected_transcript_hash=expected_hash)
    d = load_json_strict(transcript)
    events = d["events"]
    secret = events[-1]["response"]["payload"]["opening"]
    probes = secret["probes"]
    require(len(probes) == 8, "eight-probe policy required")
    work: list[Work] = []
    for j, v in enumerate(probes):
        work.append(Work("vector", f"target:{j}", canonical({"role": "target", "vector": v,
            "parameters": [secret["objective_family"], secret["target_variant"], secret["target_a"], secret["target_b"]]})))
    for i, raw in enumerate(parent.accepted_programs):
        program = load_json_strict(raw)
        _validate_program(program)
        for j, v in enumerate(probes):
            work.append(Work("vector", f"inherited:{i}:{j}", canonical({"role": "inherited", "program": program, "vector": v})))
    for i, ev in enumerate(events[2:-1:2]):
        require(ev["request"]["op"] == "evaluate", "evaluation sequence differs")
        program = ev["request"]["artifact"]["program"]
        _validate_program(program)
        work.append(Work("candidate", f"candidate:{i}", canonical({"program": program})))
        for j, v in enumerate(probes):
            work.append(Work("vector", f"candidate:{i}:probe:{j}", canonical({"role": "candidate", "program": program, "vector": v})))
    return tuple(work)


def selected_binding() -> dict:
    return {"predecessor_package_hash": PARENT_PACKAGE, "candidate_package_hash": CANDIDATE_PACKAGE,
            "transcript_sha256": TRANSCRIPT, "fixed_verifier_hash": FIXED_VERIFIER}


def validate_work_results(parent: HistoricalPredecessor, transcript: bytes, outputs: dict[str, bytes]) -> list[str]:
    """Recompute truth from the newly executed outputs, not stored verdict bits."""
    events = load_json_strict(transcript)["events"]
    secret = events[-1]["response"]["payload"]["opening"]
    expected = [load_json_strict(outputs[f"target:{j}"]) for j in range(8)]
    family = secret["objective_family"]
    nontrivial = any(a != b for a, b in zip(expected, secret["probes"], strict=True))
    inherited_pass = any(load_json_strict(raw)["family"] == family and
        all(load_json_strict(outputs[f"inherited:{i}:{j}"]) == expected[j] for j in range(8))
        for i, raw in enumerate(parent.accepted_programs))
    verdicts = []
    for i, ev in enumerate(events[2:-1:2]):
        program = ev["request"]["artifact"]["program"]
        candidate_pass = program["family"] == family and all(
            load_json_strict(outputs[f"candidate:{i}:probe:{j}"]) == expected[j] for j in range(8))
        verdict = "candidate_passed" if nontrivial and not inherited_pass and candidate_pass else "reject"
        require(ev["response"]["payload"]["verdict"] == verdict, "fresh metered result disagrees with sealed verdict")
        verdicts.append(verdict)
    return verdicts


def verify_profile(raw: bytes, *, expected_head: str, policy: Policy, expected_binding: dict,
                   expected_work: tuple[Work, ...]) -> Replay:
    """Independent accounting pass plus fixed-interpreter output recomputation.

    Recomputing outputs is validation work outside the measured execution profile;
    this does not attest the original process or satisfy Phase 18 independence.
    """
    result = replay(raw, expected_head=expected_head, policy=policy, expected_binding=expected_binding)
    require(result.status == "sealed" and result.pending_hash is None, "complete sealed profile required")
    records = [parse(line) for line in raw.splitlines()]
    require(len(records) == 2 * len(expected_work) + 2, "omitted/extra profile operation")
    for i, task in enumerate(expected_work):
        reserve = records[1 + i * 2]["body"]
        completed = records[2 + i * 2]["body"]
        require((reserve["operation"], reserve["operation_id"], reserve["input_sha256"]) ==
                (task.kind, task.identity, task.input_hash), "profile schedule/input substitution")
        require(completed["ok"] is True and completed["result_sha256"] == sha(task.execute()),
                "profile output differs from fixed reference")
    return result


def run_selected_profile(parent: HistoricalPredecessor, transcript: bytes, *, journal: Path) -> dict:
    require(sha(transcript) == TRANSCRIPT, "selected synthetic transcript differs")
    work = prepare_work(parent, transcript, expected_hash=TRANSCRIPT)
    policy = full_grammar_policy(len(parent.accepted_programs))
    anchors = selected_binding()
    outputs = {}
    with Ledger(journal, policy=policy, expected_binding=anchors) as ledger:
        for task in work:
            outputs[task.identity] = ledger.perform(task.kind, task.identity, task.input_hash, task.execute)
        verdicts = validate_work_results(parent, transcript, outputs)
        ledger.seal()
        head = ledger.state.head
        raw = ledger.journal_bytes()
    checked = verify_profile(raw, expected_head=head, policy=policy, expected_binding=anchors, expected_work=work)
    return {"schema": "runtime.v5.phase17.metered-vector-profile.v1", "binding": anchors,
            "policy": policy.to_json(), "journal_head": head, "journal_sha256": sha(raw),
            "spent": list(checked.spent), "charged_cost": checked.charged_cost,
            "charge_sequence": list(checked.charges), "event_count": checked.event_count,
            "status": checked.status, "operation_count": len(checked.operation_ids),
            "candidate_attempts": checked.spent[0], "vector_calls": checked.spent[1],
            "verdicts": verdicts, "sealed_accounting_recomputed": True, "synthetic_fixture": True,
            "fresh_execution_profile": True, "historical_transcript_rewritten": False,
            "unmeasured": ["cpu_time", "accelerator_time", "memory", "storage", "energy",
                           "bootstrap_and_validation", "journal_io", "python_runtime_overhead", "formal_verification"],
            "claims": {k: False for k in FALSE_CLAIMS}}
