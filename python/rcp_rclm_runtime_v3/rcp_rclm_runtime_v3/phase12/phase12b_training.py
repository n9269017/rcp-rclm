from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex

from rcp_rclm_runtime_v3.phase10.sparse_profile import transition_tensor_path
from rcp_rclm_runtime_v3.phase10.training_process import (
    TrainingProcessEvidence,
    run_training_twice,
)
from rcp_rclm_runtime_v3.phase10.training_protocol import (
    TrainingPair,
    TrainingRequest,
)
from rcp_rclm_runtime_v3.phase12.phase12b_lifecycle import Phase12BReference
from rcp_rclm_runtime_v3.phase12.phase12b_tasks import (
    phase12b_new_chain,
    phase12b_training_manifest,
)


def phase12b_training_request(reference: Phase12BReference) -> TrainingRequest:
    proposal = reference.proposal
    program = proposal.program
    if program.training_policy.steps != 1:
        raise ValueError("selected Phase 12B training request requires one step")
    predecessor_path = transition_tensor_path(reference.active_package_root)
    return TrainingRequest(
        transition_id="phase12-generation1-model-weight-training",
        mode="successor",
        predecessor_tensor_sha256=sha256_hex(predecessor_path.read_bytes()),
        training_data_manifest_hash=str(phase12b_training_manifest()["manifest_hash"]),
        pairs=tuple(
            sorted(
                (
                    TrainingPair(current_token_id=current, target_token_id=target)
                    for current, target in phase12b_new_chain()
                ),
                key=lambda pair: (pair.current_token_id, pair.target_token_id),
            )
        ),
        seed=program.training_policy.seed,
        optimizer_steps=program.training_policy.steps,
        learning_rate_numerator=program.training_policy.learning_rate_numerator,
        learning_rate_denominator=program.training_policy.learning_rate_denominator,
    )


@dataclass(frozen=True, slots=True)
class Phase12BTrainingEvidence:
    request: TrainingRequest
    first: TrainingProcessEvidence
    second: TrainingProcessEvidence
    semantic_candidate_tensor_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase12b.training_evidence.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.first.accepted
            and self.second.accepted
            and self.first.candidate_tensor_sha256
            == self.semantic_candidate_tensor_hash
            and self.first.report.to_json() == self.second.report.to_json()
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "request": self.request.to_json(),
            "first": self.first.to_json(),
            "second": self.second.to_json(),
            "semantic_candidate_tensor_hash": self.semantic_candidate_tensor_hash,
            "worker_training_invocations": 2,
            "authoritative_host_recomputation": True,
            "heldout_task_ids_consumed": False,
            "heldout_prompts_consumed": False,
            "heldout_source_consumed": False,
            "heldout_reference_answers_consumed": False,
            "candidate_self_report_authoritative": False,
        }


def run_phase12b_training(
    reference: Phase12BReference,
    output_root: Path,
) -> Phase12BTrainingEvidence:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12B training root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    request = phase12b_training_request(reference)
    predecessor_path = transition_tensor_path(reference.active_package_root)
    first, second = run_training_twice(
        request,
        predecessor_path,
        root / "generation1",
    )
    evidence = Phase12BTrainingEvidence(
        request=request,
        first=first,
        second=second,
        semantic_candidate_tensor_hash=sha256_hex(
            transition_tensor_path(reference.semantic_candidate.root).read_bytes()
        ),
    )
    if not evidence.accepted:
        raise ValueError("Phase 12B untrusted training replay did not close")
    return evidence


__all__ = [
    "Phase12BTrainingEvidence",
    "phase12b_training_request",
    "run_phase12b_training",
]
