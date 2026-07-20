from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.mathematics.intervals import (
    IntervalEvidence,
    log_rational_interval,
    sum_intervals,
)
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID, VOCAB_SIZE
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import exact_dyadic_distribution

PRECISION_BITS: Final[int] = 256
TARGET_CORRECT_MASS: Final[int] = 4_096
TARGET_OTHER_MASS: Final[int] = 1

_LOG_CACHE: dict[Rational, IntervalEvidence] = {}


def _log(value: Rational) -> IntervalEvidence:
    existing = _LOG_CACHE.get(value)
    if existing is not None:
        return existing
    result = log_rational_interval(value, PRECISION_BITS)
    _LOG_CACHE[value] = result
    return result


def _target_distribution(target_token_id: int) -> Sequence[Rational]:
    total = TARGET_CORRECT_MASS + TARGET_OTHER_MASS * (VOCAB_SIZE - 1)
    return tuple(
        Rational(TARGET_CORRECT_MASS if token == target_token_id else TARGET_OTHER_MASS, total)
        for token in range(VOCAB_SIZE)
    )


def _entropy(distribution: Sequence[Rational]) -> IntervalEvidence:
    terms = [
        -(IntervalEvidence.exact(probability, PRECISION_BITS) * _log(probability))
        for probability in distribution
    ]
    return sum_intervals(terms, PRECISION_BITS)


def _kl(
    distribution: Sequence[Rational],
    target: Sequence[Rational],
) -> IntervalEvidence:
    terms = []
    for probability, target_probability in zip(distribution, target, strict=True):
        log_ratio = _log(probability) - _log(target_probability)
        terms.append(IntervalEvidence.exact(probability, PRECISION_BITS) * log_ratio)
    return sum_intervals(terms, PRECISION_BITS)


@dataclass(frozen=True, slots=True)
class TokenInformationEvidence:
    position: int
    current_token_id: int
    target_token_id: int
    score_vector_hash: str
    density_hash: str
    correct_probability: Rational
    entropy_interval: IntervalEvidence
    kl_qre_interval: IntervalEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase10.token_information_evidence.v1"

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "position": self.position,
            "current_token_id": self.current_token_id,
            "target_token_id": self.target_token_id,
            "score_vector_hash": self.score_vector_hash,
            "density_hash": self.density_hash,
            "correct_probability": self.correct_probability.to_json(),
            "shannon_entropy_interval": self.entropy_interval.to_json(),
            "von_neumann_entropy_interval": self.entropy_interval.to_json(),
            "kl_interval": self.kl_qre_interval.to_json(),
            "diagonal_qre_interval": self.kl_qre_interval.to_json(),
            "density_semantics": "diagonal_token_distribution_v1",
        }


@dataclass(frozen=True, slots=True)
class PromptInformationEvidence:
    task_id: str
    model_identity_hash: str
    prompt_hash: str
    steps: Sequence[TokenInformationEvidence]
    entropy_sum_interval: IntervalEvidence
    kl_qre_sum_interval: IntervalEvidence

    schema_id: ClassVar[str] = "runtime.v3.phase10.prompt_information_evidence.v1"

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "model_identity_hash": self.model_identity_hash,
            "prompt_hash": self.prompt_hash,
            "steps": [step.to_json() for step in self.steps],
            "entropy_sum_interval": self.entropy_sum_interval.to_json(),
            "kl_sum_interval": self.kl_qre_sum_interval.to_json(),
            "diagonal_qre_sum_interval": self.kl_qre_sum_interval.to_json(),
        }


def prompt_information_evidence(
    package_root: Path,
    task: LeanCompletionTask,
) -> PromptInformationEvidence:
    manifest = load_package_manifest(package_root.resolve(strict=True))
    target_tokens = [*task.expected_completion.encode("ascii"), EOS_TOKEN_ID]
    current = task.marker
    steps: list[TokenInformationEvidence] = []
    entropy_values: list[IntervalEvidence] = []
    kl_values: list[IntervalEvidence] = []
    for position, target_token in enumerate(target_tokens):
        scores, distribution = exact_dyadic_distribution(package_root, current)
        target_distribution = _target_distribution(target_token)
        entropy = _entropy(distribution)
        kl_qre = _kl(distribution, target_distribution)
        density_json = [probability.to_json() for probability in distribution]
        step = TokenInformationEvidence(
            position=position,
            current_token_id=current,
            target_token_id=target_token,
            score_vector_hash=canonical_json_hash(list(scores)),
            density_hash=canonical_json_hash(density_json),
            correct_probability=distribution[target_token],
            entropy_interval=entropy,
            kl_qre_interval=kl_qre,
        )
        steps.append(step)
        entropy_values.append(entropy)
        kl_values.append(kl_qre)
        current = target_token
    return PromptInformationEvidence(
        task_id=task.task_id,
        model_identity_hash=manifest.model_identity_hash,
        prompt_hash=sha256_hex(task.model_prompt),
        steps=tuple(steps),
        entropy_sum_interval=sum_intervals(entropy_values, PRECISION_BITS),
        kl_qre_sum_interval=sum_intervals(kl_values, PRECISION_BITS),
    )


@dataclass(frozen=True, slots=True)
class Phase10InformationReport:
    protected_predecessor: PromptInformationEvidence
    protected_candidate: PromptInformationEvidence
    heldout_predecessor: PromptInformationEvidence
    heldout_candidate: PromptInformationEvidence
    protected_budget: Rational

    schema_id: ClassVar[str] = "runtime.v3.phase10.information_report.v1"

    @property
    def protected_density_unchanged(self) -> bool:
        predecessor_steps = tuple(self.protected_predecessor.steps)
        candidate_steps = tuple(self.protected_candidate.steps)
        if (
            self.protected_predecessor.task_id != self.protected_candidate.task_id
            or self.protected_predecessor.prompt_hash != self.protected_candidate.prompt_hash
            or len(predecessor_steps) != len(candidate_steps)
        ):
            return False
        return all(
            predecessor.position == candidate.position
            and predecessor.current_token_id == candidate.current_token_id
            and predecessor.target_token_id == candidate.target_token_id
            and predecessor.score_vector_hash == candidate.score_vector_hash
            and predecessor.density_hash == candidate.density_hash
            for predecessor, candidate in zip(
                predecessor_steps, candidate_steps, strict=True
            )
        )

    @property
    def protected_regression_interval(self) -> IntervalEvidence:
        if self.protected_density_unchanged:
            return IntervalEvidence.exact(Rational.zero(), PRECISION_BITS)
        return (
            self.protected_candidate.kl_qre_sum_interval
            - self.protected_predecessor.kl_qre_sum_interval
        )

    @property
    def heldout_improvement_interval(self) -> IntervalEvidence:
        return (
            self.heldout_predecessor.kl_qre_sum_interval
            - self.heldout_candidate.kl_qre_sum_interval
        )

    @property
    def protected_nonregression(self) -> bool:
        return self.protected_regression_interval.upper <= self.protected_budget

    @property
    def strict_information_witness(self) -> bool:
        return self.heldout_improvement_interval.strictly_positive()

    @property
    def accepted(self) -> bool:
        return self.protected_nonregression and self.strict_information_witness

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "protected_predecessor": self.protected_predecessor.to_json(),
            "protected_candidate": self.protected_candidate.to_json(),
            "heldout_predecessor": self.heldout_predecessor.to_json(),
            "heldout_candidate": self.heldout_candidate.to_json(),
            "protected_budget": self.protected_budget.to_json(),
            "protected_density_unchanged": self.protected_density_unchanged,
            "protected_regression_interval": self.protected_regression_interval.to_json(),
            "heldout_improvement_interval": self.heldout_improvement_interval.to_json(),
            "protected_nonregression": self.protected_nonregression,
            "strict_information_witness": self.strict_information_witness,
            "accepted": self.accepted,
            "qre_equals_kl_by_diagonal_construction": True,
            "von_neumann_equals_shannon_by_diagonal_construction": True,
        }


def build_information_report(
    predecessor_root: Path,
    candidate_root: Path,
    protected_task: LeanCompletionTask,
    heldout_task: LeanCompletionTask,
) -> Phase10InformationReport:
    return Phase10InformationReport(
        protected_predecessor=prompt_information_evidence(predecessor_root, protected_task),
        protected_candidate=prompt_information_evidence(candidate_root, protected_task),
        heldout_predecessor=prompt_information_evidence(predecessor_root, heldout_task),
        heldout_candidate=prompt_information_evidence(candidate_root, heldout_task),
        protected_budget=Rational.zero(),
    )


__all__ = [
    "Phase10InformationReport",
    "PromptInformationEvidence",
    "TokenInformationEvidence",
    "build_information_report",
    "prompt_information_evidence",
]
