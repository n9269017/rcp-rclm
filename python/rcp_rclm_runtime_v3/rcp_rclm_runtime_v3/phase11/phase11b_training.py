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
from rcp_rclm_runtime_v3.phase10.training_protocol import TrainingPair, TrainingRequest
from rcp_rclm_runtime_v3.phase11.phase11b_candidate import CandidateKind
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import Phase11BReference
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import (
    phase11b_alpha_pairs,
    phase11b_beta_pairs,
    phase11b_training_manifest,
)
from rcp_rclm_runtime_v3.phase11.records import GeneratorInvocationReport


def phase11b_training_request(
    reference: Phase11BReference,
    invocation: GeneratorInvocationReport,
    kind: CandidateKind,
) -> TrainingRequest:
    pairs = phase11b_alpha_pairs() if kind == "alpha_rejected" else phase11b_beta_pairs()
    selection_id = (
        "training_partition_alpha"
        if kind == "alpha_rejected"
        else "training_partition_beta"
    )
    program = invocation.program
    if program.training_policy.steps != 1:
        raise ValueError("selected Phase 11B training request requires one step")
    predecessor_path = transition_tensor_path(reference.active.active_package_root)
    return TrainingRequest(
        transition_id=f"phase11b-{kind}-model-programmed-training",
        mode="successor",
        predecessor_tensor_sha256=sha256_hex(predecessor_path.read_bytes()),
        training_data_manifest_hash=str(
            phase11b_training_manifest(selection_id)["manifest_hash"]
        ),
        pairs=tuple(
            sorted(
                (
                    TrainingPair(current_token_id=current, target_token_id=target)
                    for current, target in pairs
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
class Phase11BTrainingEvidence:
    alpha_request: TrainingRequest
    alpha_first: TrainingProcessEvidence
    alpha_second: TrainingProcessEvidence
    beta_request: TrainingRequest
    beta_first: TrainingProcessEvidence
    beta_second: TrainingProcessEvidence
    semantic_alpha_tensor_hash: str
    semantic_beta_tensor_hash: str

    schema_id: ClassVar[str] = "runtime.v3.phase11b.training_evidence.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.alpha_first.accepted
            and self.alpha_second.accepted
            and self.beta_first.accepted
            and self.beta_second.accepted
            and self.alpha_first.candidate_tensor_sha256
            == self.semantic_alpha_tensor_hash
            and self.beta_first.candidate_tensor_sha256
            == self.semantic_beta_tensor_hash
            and self.alpha_first.report.to_json() == self.alpha_second.report.to_json()
            and self.beta_first.report.to_json() == self.beta_second.report.to_json()
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "alpha_request": self.alpha_request.to_json(),
            "alpha_first": self.alpha_first.to_json(),
            "alpha_second": self.alpha_second.to_json(),
            "beta_request": self.beta_request.to_json(),
            "beta_first": self.beta_first.to_json(),
            "beta_second": self.beta_second.to_json(),
            "semantic_alpha_tensor_hash": self.semantic_alpha_tensor_hash,
            "semantic_beta_tensor_hash": self.semantic_beta_tensor_hash,
            "worker_training_invocations": 4,
            "authoritative_host_recomputation": True,
            "heldout_task_ids_consumed": False,
            "heldout_prompts_consumed": False,
            "heldout_source_consumed": False,
            "heldout_reference_answers_consumed": False,
            "candidate_self_report_authoritative": False,
        }


def run_phase11b_training(
    reference: Phase11BReference,
    output_root: Path,
) -> Phase11BTrainingEvidence:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 11B training root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    predecessor_tensor_path = transition_tensor_path(reference.active.active_package_root)
    alpha_request = phase11b_training_request(
        reference,
        reference.alpha_invocation,
        "alpha_rejected",
    )
    alpha_first, alpha_second = run_training_twice(
        alpha_request,
        predecessor_tensor_path,
        root / "alpha",
    )
    beta_request = phase11b_training_request(
        reference,
        reference.beta_invocation,
        "beta_promoted",
    )
    beta_first, beta_second = run_training_twice(
        beta_request,
        predecessor_tensor_path,
        root / "beta",
    )
    evidence = Phase11BTrainingEvidence(
        alpha_request=alpha_request,
        alpha_first=alpha_first,
        alpha_second=alpha_second,
        beta_request=beta_request,
        beta_first=beta_first,
        beta_second=beta_second,
        semantic_alpha_tensor_hash=sha256_hex(
            transition_tensor_path(reference.alpha_candidate.root).read_bytes()
        ),
        semantic_beta_tensor_hash=sha256_hex(
            transition_tensor_path(reference.beta_candidate.root).read_bytes()
        ),
    )
    if not evidence.accepted:
        raise ValueError("Phase 11B untrusted training replay did not close")
    return evidence


__all__ = [
    "Phase11BTrainingEvidence",
    "phase11b_training_request",
    "run_phase11b_training",
]
