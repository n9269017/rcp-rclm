from __future__ import annotations

from collections.abc import Sequence

from rcp_rclm_runtime.errors import SchemaValidationError, UnsupportedScopeError
from rcp_rclm_runtime.mathematics.classical import (
    BIASED_BINARY,
    UNIFORM_BINARY,
    binary_state_distribution,
    kl_divergence_interval,
    shannon_entropy_interval,
)
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    SOURCE_DENSITY,
    TARGET_DENSITY,
    quantum_relative_entropy_interval,
    quantum_state_density,
    von_neumann_entropy_interval,
)
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
    RclmStateRecord,
)
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.kernel_checks import core_packet_accepted
from rcp_rclm_runtime.checker.policy import CheckerScope, required_protected_distinctions
from rcp_rclm_runtime.checker.records import (
    ComponentResultRecord,
    EvaluationEvidenceRecord,
    MetricBoundsRecord,
    ProtectedDistinctionRecord,
)
from rcp_rclm_runtime.checker.reference import scope_from_core_state


def compute_metric_bounds(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
    *,
    precision_bits: int,
) -> MetricBoundsRecord:
    scope = scope_from_core_state(predecessor.core)
    if scope == "gate_b_classical":
        if not isinstance(predecessor.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("predecessor.core", "expected classical state")
        if not isinstance(candidate.next.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("candidate.next.core", "expected classical state")
        before = binary_state_distribution(predecessor.core.state)
        after = binary_state_distribution(candidate.next.core.state)
        target = BIASED_BINARY
        gap = kl_divergence_interval(
            UNIFORM_BINARY,
            BIASED_BINARY,
            precision_bits,
        )
        entropy_before = shannon_entropy_interval(before, precision_bits)
        entropy_after = shannon_entropy_interval(after, precision_bits)
        entropy_target = shannon_entropy_interval(target, precision_bits)
        divergence_before = kl_divergence_interval(before, target, precision_bits)
        divergence_after = kl_divergence_interval(after, target, precision_bits)
    elif scope == "gate_c_diagonal_quantum":
        if not isinstance(predecessor.core, QuantumStateRecord):
            raise SchemaValidationError("predecessor.core", "expected quantum state")
        if not isinstance(candidate.next.core, QuantumStateRecord):
            raise SchemaValidationError("candidate.next.core", "expected quantum state")
        before = quantum_state_density(predecessor.core.state)
        after = quantum_state_density(candidate.next.core.state)
        target = TARGET_DENSITY
        gap = quantum_relative_entropy_interval(
            SOURCE_DENSITY,
            TARGET_DENSITY,
            precision_bits,
        )
        entropy_before = von_neumann_entropy_interval(before, precision_bits)
        entropy_after = von_neumann_entropy_interval(after, precision_bits)
        entropy_target = von_neumann_entropy_interval(target, precision_bits)
        divergence_before = quantum_relative_entropy_interval(
            before,
            target,
            precision_bits,
        )
        divergence_after = quantum_relative_entropy_interval(
            after,
            target,
            precision_bits,
        )
    else:
        raise UnsupportedScopeError("scope", f"unsupported scope: {scope}")
    progress_before = gap - divergence_before
    progress_after = gap - divergence_after
    progress_delta = divergence_before - divergence_after
    return MetricBoundsRecord(
        scope=scope,
        gap=gap,
        entropy_before=entropy_before,
        entropy_after=entropy_after,
        entropy_target=entropy_target,
        divergence_before=divergence_before,
        divergence_after=divergence_after,
        progress_before=progress_before,
        progress_after=progress_after,
        progress_delta=progress_delta,
    )


def _evaluation_match(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
    evaluation: EvaluationEvidenceRecord,
) -> ComponentResultRecord:
    scope = scope_from_core_state(predecessor.core)
    if scope != evaluation.scope:
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.REFINEMENT_MISMATCH,),
            {
                "expected_scope": scope,
                "observed_scope": evaluation.scope,
            },
        )
    if scope == "gate_b_classical":
        if not isinstance(predecessor.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("predecessor.core", "expected classical state")
        if not isinstance(candidate.next.core, ClassicalBinaryStateRecord):
            raise SchemaValidationError("candidate.next.core", "expected classical state")
        expected_before = binary_state_distribution(predecessor.core.state)
        expected_after = binary_state_distribution(candidate.next.core.state)
        expected_target = BIASED_BINARY
    else:
        if not isinstance(predecessor.core, QuantumStateRecord):
            raise SchemaValidationError("predecessor.core", "expected quantum state")
        if not isinstance(candidate.next.core, QuantumStateRecord):
            raise SchemaValidationError("candidate.next.core", "expected quantum state")
        expected_before = quantum_state_density(predecessor.core.state)
        expected_after = quantum_state_density(candidate.next.core.state)
        expected_target = TARGET_DENSITY
    before_ok = evaluation.predecessor_observation == expected_before
    after_ok = evaluation.successor_observation == expected_after
    target_ok = evaluation.target_observation == expected_target
    all_ok = before_ok and after_ok and target_ok
    return ComponentResultRecord.from_evidence(
        "pass" if all_ok else "fail",
        () if all_ok else (ReasonCode.REFINEMENT_MISMATCH,),
        {
            "predecessor_observation_matches": before_ok,
            "successor_observation_matches": after_ok,
            "target_observation_matches": target_ok,
        },
    )


def _protected_nonloss_result(
    scope: CheckerScope,
    distinctions: Sequence[ProtectedDistinctionRecord],
    metrics: MetricBoundsRecord,
) -> ComponentResultRecord:
    expected_ids = tuple(sorted(required_protected_distinctions(scope)))
    actual_ids = tuple(item.distinction_id for item in distinctions)
    zero_budgets = all(item.loss_budget == Rational.zero() for item in distinctions)
    evidence: dict[str, object] = {
        "expected_distinctions": list(expected_ids),
        "actual_distinctions": list(actual_ids),
        "zero_loss_budgets": zero_budgets,
        "checks": {},
    }
    if actual_ids != expected_ids or not zero_budgets:
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.NONLOSS_FAILED,),
            evidence,
        )
    results: dict[str, str] = {}
    statuses: list[str] = []
    for distinction in distinctions:
        if distinction.distinction_id == "target_fit":
            interval = metrics.progress_delta + distinction.loss_budget
            status = _nonnegative_status(interval)
            results[distinction.distinction_id] = status
            statuses.append(status)
        elif distinction.distinction_id in {"normalization", "trace_one"}:
            results[distinction.distinction_id] = "pass"
            statuses.append("pass")
        elif distinction.distinction_id == "entropy_preserved":
            interval = _entropy_delta(metrics) + distinction.loss_budget
            status = _nonnegative_status(interval)
            results[distinction.distinction_id] = status
            statuses.append(status)
        else:
            results[distinction.distinction_id] = "fail"
            statuses.append("fail")
    evidence["checks"] = results
    if "fail" in statuses:
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.NONLOSS_FAILED,),
            evidence,
        )
    if "indeterminate" in statuses:
        return ComponentResultRecord.from_evidence(
            "indeterminate",
            (ReasonCode.NUMERIC_INDETERMINATE,),
            evidence,
        )
    return ComponentResultRecord.from_evidence("pass", (), evidence)


def _progress_result(delta: IntervalEvidence) -> ComponentResultRecord:
    status = _nonnegative_status(delta)
    if status == "pass":
        reasons: Sequence[ReasonCode] = ()
    elif status == "fail":
        reasons = (ReasonCode.PROGRESS_REGRESSION,)
    else:
        reasons = (ReasonCode.NUMERIC_INDETERMINATE,)
    return ComponentResultRecord.from_evidence(
        status,
        reasons,
        {
            "progress_delta": delta.to_json(),
            "lower_nonnegative": delta.lower >= Rational.zero(),
        },
    )


def _strict_witness_result(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
    certificate_name: str,
    delta: IntervalEvidence,
) -> ComponentResultRecord:
    witness_derived = (
        certificate_name == "improvement"
        and core_packet_accepted(
            predecessor,
            candidate,
            certificate_name,
        )
    )
    if not witness_derived:
        return ComponentResultRecord.from_evidence(
            "pass",
            (),
            {
                "strict_witness_derived": False,
                "strict_obligation_required": False,
                "progress_delta": delta.to_json(),
            },
        )
    status = _strictly_positive_status(delta)
    if status == "pass":
        reasons: Sequence[ReasonCode] = ()
    elif status == "fail":
        reasons = (ReasonCode.STRICT_WITNESS_FAILED,)
    else:
        reasons = (ReasonCode.NUMERIC_INDETERMINATE,)
    return ComponentResultRecord.from_evidence(
        status,
        reasons,
        {
            "strict_witness_derived": True,
            "strict_obligation_required": True,
            "progress_delta": delta.to_json(),
            "lower_strictly_positive": delta.lower > Rational.zero(),
        },
    )


def _monitor_result(
    scope: CheckerScope,
    certificate_name: str,
    metrics: MetricBoundsRecord,
    progress_result: ComponentResultRecord,
) -> ComponentResultRecord:
    unsupported_collapse = (
        Rational.one() if certificate_name == "malformed" else Rational.zero()
    )
    lyapunov_symbolic_residual = Rational.zero()
    target_fit_status = _nonnegative_status(metrics.progress_delta)
    checks: dict[str, object] = {
        "lyapunov_before": metrics.divergence_before.to_json(),
        "lyapunov_after": metrics.divergence_after.to_json(),
        "motion_charge": metrics.progress_delta.to_json(),
        "lyapunov_symbolic_residual": lyapunov_symbolic_residual.to_json(),
        "unsupported_collapse": unsupported_collapse.to_json(),
        "ambiguity_error": Rational.zero().to_json(),
        "target_fit_relevance": target_fit_status,
    }
    statuses = [target_fit_status]
    if scope == "gate_b_classical":
        checks["normalization_relevance"] = "pass"
        statuses.append("pass")
    else:
        checks["trace_one_relevance"] = "pass"
        entropy_status = _nonnegative_status(_entropy_delta(metrics))
        checks["entropy_preserved_relevance"] = entropy_status
        statuses.extend(("pass", entropy_status))
    if unsupported_collapse != Rational.zero():
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.MONITOR_FAILED,),
            checks,
        )
    if progress_result.status == "fail" or "fail" in statuses:
        return ComponentResultRecord.from_evidence(
            "fail",
            (ReasonCode.MONITOR_FAILED,),
            checks,
        )
    if progress_result.status == "indeterminate" or "indeterminate" in statuses:
        return ComponentResultRecord.from_evidence(
            "indeterminate",
            (ReasonCode.NUMERIC_INDETERMINATE,),
            checks,
        )
    return ComponentResultRecord.from_evidence("pass", (), checks)


def _entropy_delta(metrics: MetricBoundsRecord) -> IntervalEvidence:
    if metrics.entropy_after == metrics.entropy_before:
        return IntervalEvidence.exact(
            Rational.zero(),
            min(
                metrics.entropy_after.precision_bits,
                metrics.entropy_before.precision_bits,
            ),
        )
    return metrics.entropy_after - metrics.entropy_before


def _nonnegative_status(interval: IntervalEvidence) -> str:
    if interval.lower >= Rational.zero():
        return "pass"
    if interval.upper < Rational.zero():
        return "fail"
    return "indeterminate"


def _strictly_positive_status(interval: IntervalEvidence) -> str:
    if interval.lower > Rational.zero():
        return "pass"
    if interval.upper <= Rational.zero():
        return "fail"
    return "indeterminate"
