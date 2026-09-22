from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_CHALLENGE_POLICY_ID,
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_FAMILY_STRIDE,
    PHASE16_FIXED_VERIFIER_HASH,
    UPDATE_FAMILIES,
    UpdateFamily,
)
from rcp_rclm_runtime_v4.phase16.grammar import execute_program, output_hash
from rcp_rclm_runtime_v4.phase16.ranking import ranked_programs
from rcp_rclm_runtime_v4.phase16.records import ModelState, MutationProgram
from rcp_rclm_runtime_v4.phase16.scheduler import fair_order


def _input_vector(value_hash: str) -> tuple[int, int, int, int]:
    values = []
    for index in range(4):
        start = index * 8
        values.append(int(value_hash[start : start + 8], 16) % 33 - 16)
    return tuple(values)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class HiddenChallenge:
    promotion_index: int
    predecessor_freeze_hash: str
    generated_after_predecessor_freeze: bool
    public_nonce_hash: str
    public_input_vector: Sequence[int]
    target_family: UpdateFamily
    target_program_hash: str
    target_output_hash: str
    commitment_hash: str
    challenge_stream: str
    seed: str

    schema_id: ClassVar[str] = "runtime.v4.phase16.hidden_challenge.v1"

    def __post_init__(self) -> None:
        if self.promotion_index < 0:
            raise SchemaValidationError(
                "phase16.challenge.promotion_index",
                "expected nonnegative integer",
            )
        for field, value in (
            ("predecessor_freeze_hash", self.predecessor_freeze_hash),
            ("public_nonce_hash", self.public_nonce_hash),
            ("target_program_hash", self.target_program_hash),
            ("target_output_hash", self.target_output_hash),
            ("commitment_hash", self.commitment_hash),
        ):
            validate_hash256(value, f"phase16.challenge.{field}")
        if not self.generated_after_predecessor_freeze:
            raise SchemaValidationError(
                "phase16.challenge.generated_after_predecessor_freeze",
                "challenge must be generated after predecessor freeze",
            )
        if self.target_family not in UPDATE_FAMILIES:
            raise SchemaValidationError(
                "phase16.challenge.target_family",
                "unsupported update family",
            )
        vector = tuple(self.public_input_vector)
        if len(vector) != 4 or any(
            isinstance(item, bool) or not isinstance(item, int) for item in vector
        ):
            raise SchemaValidationError(
                "phase16.challenge.public_input_vector",
                "four integers required",
            )
        object.__setattr__(self, "public_input_vector", vector)
        if not self.challenge_stream or not self.seed:
            raise SchemaValidationError(
                "phase16.challenge",
                "seed and challenge stream are required",
            )
        if self.commitment_hash != canonical_json_hash(self.private_commitment_payload()):
            raise SchemaValidationError(
                "phase16.challenge.commitment_hash",
                "private challenge commitment mismatch",
            )

    @property
    def challenge_id(self) -> str:
        return f"phase16.hidden.{self.commitment_hash[:20]}"

    @property
    def capability_id(self) -> str:
        return (
            f"phase16.dynamic.{self.target_family}."
            f"{self.commitment_hash[:20]}"
        )

    def public_input(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.v4.phase16.public_challenge_input.v1",
            "input_vector": list(self.public_input_vector),
            "commitment_hash": self.commitment_hash,
            "challenge_id": self.challenge_id,
            "generated_after_predecessor_freeze": True,
            "answer_visible_to_candidate": False,
            "candidate_controlled_memory_contains_answer": False,
        }

    def public_json(self) -> dict[str, object]:
        return {
            "schema_id": "runtime.v4.phase16.public_hidden_challenge.v1",
            "challenge_id": self.challenge_id,
            "promotion_index": self.promotion_index,
            "predecessor_freeze_hash": self.predecessor_freeze_hash,
            "generated_after_predecessor_freeze": True,
            "public_nonce_hash": self.public_nonce_hash,
            "public_input": self.public_input(),
            "commitment_hash": self.commitment_hash,
            "challenge_policy_id": PHASE16_CHALLENGE_POLICY_ID,
            "target_program_visible_before_candidate_freeze": False,
            "target_output_visible_before_candidate_freeze": False,
        }

    def private_commitment_payload(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "promotion_index": self.promotion_index,
            "predecessor_freeze_hash": self.predecessor_freeze_hash,
            "generated_after_predecessor_freeze": True,
            "public_nonce_hash": self.public_nonce_hash,
            "public_input_vector": list(self.public_input_vector),
            "target_family": self.target_family,
            "target_program_hash": self.target_program_hash,
            "target_output_hash": self.target_output_hash,
            "challenge_stream": self.challenge_stream,
            "seed": self.seed,
            "challenge_policy_id": PHASE16_CHALLENGE_POLICY_ID,
        }

    def retained_private_json(self) -> dict[str, object]:
        value = self.private_commitment_payload()
        value["commitment_hash"] = self.commitment_hash
        value["challenge_id"] = self.challenge_id
        value["capability_id"] = self.capability_id
        value["released_only_after_campaign_transaction"] = True
        return value


def generate_hidden_challenge(
    *,
    state: ModelState,
    programs: Sequence[MutationProgram],
    promotion_index: int,
    predecessor_freeze_hash: str,
    public_nonce_hash: str,
    seed: str,
    challenge_stream: str,
    verified_family_counts: Mapping[str, int],
) -> HiddenChallenge:
    validate_hash256(predecessor_freeze_hash, "phase16.challenge.predecessor_freeze_hash")
    validate_hash256(public_nonce_hash, "phase16.challenge.public_nonce_hash")
    if not programs:
        raise SchemaValidationError("phase16.challenge.programs", "legal grammar is empty")
    family_offset_hash = canonical_json_hash(
        {
            "policy_id": PHASE16_CHALLENGE_POLICY_ID,
            "seed": seed,
            "challenge_stream": challenge_stream,
        }
    )
    offset = int(family_offset_hash[:16], 16) % len(UPDATE_FAMILIES)
    family = UPDATE_FAMILIES[
        (offset + promotion_index * PHASE16_FAMILY_STRIDE) % len(UPDATE_FAMILIES)
    ]
    considered: list[str] = []
    rejected_families: list[str] = []
    learned_trace: list[MutationProgram] = []
    for _ in range(4):
        remaining = tuple(
            program for program in programs if program.program_hash not in considered
        )
        ranked = ranked_programs(
            remaining,
            active_package_hash=state.active_package_hash,
            verified_family_counts=verified_family_counts,
            rejected_families=tuple(rejected_families),
            seed=seed,
            challenge_stream=challenge_stream,
        )
        candidate = ranked[0]
        learned_trace.append(candidate)
        considered.append(candidate.program_hash)
        rejected_families.append(candidate.family)
    offset_hash = canonical_json_hash(
        {
            "domain": "phase16.fair_order_offset.v1",
            "active_package_hash": state.active_package_hash,
            "promotion_index": promotion_index,
            "seed": seed,
            "challenge_stream": challenge_stream,
        }
    )
    fair_candidates = tuple(
        program
        for program in fair_order(programs, offset_hash)
        if program.program_hash not in considered and program.family == family
    )
    learned_family_candidates = tuple(
        program for program in learned_trace if program.family == family
    )
    if fair_candidates:
        target_program = fair_candidates[0]
    elif learned_family_candidates:
        target_program = learned_family_candidates[-1]
    else:
        family_programs = tuple(
            program for program in programs if program.family == family
        )
        if not family_programs:
            raise SchemaValidationError(
                "phase16.challenge.family_programs",
                "selected family has no legal mutation",
            )
        target_program = family_programs[0]
    input_hash = canonical_json_hash(
        {
            "domain": "phase16.post_freeze_public_input.v1",
            "seed": seed,
            "challenge_stream": challenge_stream,
            "promotion_index": promotion_index,
            "predecessor_freeze_hash": predecessor_freeze_hash,
            "public_nonce_hash": public_nonce_hash,
        }
    )
    vector = _input_vector(input_hash)
    public_input = {"input_vector": list(vector)}
    target_result_hash = output_hash(target_program, public_input)
    payload = {
        "schema_id": HiddenChallenge.schema_id,
        "promotion_index": promotion_index,
        "predecessor_freeze_hash": predecessor_freeze_hash,
        "generated_after_predecessor_freeze": True,
        "public_nonce_hash": public_nonce_hash,
        "public_input_vector": list(vector),
        "target_family": family,
        "target_program_hash": target_program.program_hash,
        "target_output_hash": target_result_hash,
        "challenge_stream": challenge_stream,
        "seed": seed,
        "challenge_policy_id": PHASE16_CHALLENGE_POLICY_ID,
    }
    return HiddenChallenge(
        promotion_index=promotion_index,
        predecessor_freeze_hash=predecessor_freeze_hash,
        generated_after_predecessor_freeze=True,
        public_nonce_hash=public_nonce_hash,
        public_input_vector=vector,
        target_family=family,
        target_program_hash=target_program.program_hash,
        target_output_hash=target_result_hash,
        commitment_hash=canonical_json_hash(payload),
        challenge_stream=challenge_stream,
        seed=seed,
    )


def evaluate_hidden_candidate(
    *,
    challenge: HiddenChallenge,
    state: ModelState,
    program: MutationProgram,
) -> dict[str, object]:
    candidate_freeze_hash = canonical_json_hash(
        {
            "domain": "phase16.candidate_freeze.v1",
            "predecessor_state_hash": state.state_record_hash,
            "challenge_commitment_hash": challenge.commitment_hash,
            "program_hash": program.program_hash,
        }
    )
    execution = execute_program(program, challenge.public_input())
    observed_output_hash = canonical_json_hash(execution)
    predecessor_failed = challenge.target_program_hash not in state.installed_program_hashes
    candidate_passed = (
        program.program_hash == challenge.target_program_hash
        and observed_output_hash == challenge.target_output_hash
    )
    accepted = predecessor_failed and candidate_passed
    reason_codes = [] if accepted else ["INDEPENDENT_HIDDEN_CHALLENGE_FAILED"]
    report: dict[str, object] = {
        "schema_id": "runtime.v4.phase16.independent_evaluation.v1",
        "challenge_id": challenge.challenge_id,
        "challenge_commitment_hash": challenge.commitment_hash,
        "candidate_freeze_hash": candidate_freeze_hash,
        "program_hash": program.program_hash,
        "observed_output_hash": observed_output_hash,
        "predecessor_failed_hidden_challenge": predecessor_failed,
        "candidate_passed_hidden_challenge": candidate_passed,
        "predecessor_frontier_recertified": True,
        "answer_retrieved_from_candidate_memory": False,
        "candidate_self_report_authoritative": False,
        "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
        "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
        "accepted": accepted,
        "reason_codes": reason_codes,
    }
    report["report_hash"] = canonical_json_hash(report)
    return report


__all__ = [
    "HiddenChallenge",
    "evaluate_hidden_candidate",
    "generate_hidden_challenge",
]
