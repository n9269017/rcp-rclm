from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.kernel_checks import (
    _containment_result,
    _domain_result,
    _invariant_result,
    _recovery_result,
    _typed_successor,
    core_packet_accepted,
)
from rcp_rclm_runtime.checker.metric_checks import (
    _evaluation_match,
    _monitor_result,
    _progress_result,
    _protected_nonloss_result,
    _strict_witness_result,
    compute_metric_bounds,
)
from rcp_rclm_runtime.checker.policy import CheckerScope
from rcp_rclm_runtime.checker.records import (
    ComponentResultRecord,
    EvaluationEvidenceRecord,
    MetricBoundsRecord,
    ProtectedDistinctionRecord,
    ResidualResultRecord,
)
from rcp_rclm_runtime.checker.reference import scope_from_core_state


@dataclass(frozen=True, slots=True)
class MathematicalComputation:
    scope: CheckerScope
    typed_successor_result: ComponentResultRecord
    residuals: Sequence[ResidualResultRecord]
    residual_result: ComponentResultRecord
    metric_bounds: MetricBoundsRecord
    evaluation_result: ComponentResultRecord
    protected_nonloss_result: ComponentResultRecord
    recovery_result: ComponentResultRecord
    progress_result: ComponentResultRecord
    strict_witness_result: ComponentResultRecord
    invariant_result: ComponentResultRecord
    containment_result: ComponentResultRecord
    domain_result: ComponentResultRecord
    monitor_result: ComponentResultRecord


def compute_mathematical_obligations(
    predecessor: RclmStateRecord,
    candidate: RclmCandidateRecord,
    certificate_name: str,
    distinctions: Sequence[ProtectedDistinctionRecord],
    evaluation: EvaluationEvidenceRecord,
    precision_bits: int,
) -> MathematicalComputation:
    scope = scope_from_core_state(predecessor.core)
    typed_result, typed_ok = _typed_successor(predecessor, candidate)
    packet_ok = core_packet_accepted(predecessor, candidate, certificate_name)
    residuals = (
        ResidualResultRecord(
            index="typed",
            value=Rational(-1 if typed_ok else 1),
            upper_nonpositive=typed_ok,
        ),
        ResidualResultRecord(
            index="packet",
            value=Rational(-1 if packet_ok else 1),
            upper_nonpositive=packet_ok,
        ),
    )
    residual_ok = all(item.upper_nonpositive for item in residuals)
    residual_result = ComponentResultRecord.from_evidence(
        "pass" if residual_ok else "fail",
        () if residual_ok else (ReasonCode.RESIDUAL_POSITIVE,),
        {
            "required_indices": ["typed", "packet"],
            "all_upper_nonpositive": residual_ok,
        },
    )
    metrics = compute_metric_bounds(
        predecessor,
        candidate,
        precision_bits=precision_bits,
    )
    evaluation_result = _evaluation_match(predecessor, candidate, evaluation)
    progress_result = _progress_result(metrics.progress_delta)
    strict_result = _strict_witness_result(
        predecessor,
        candidate,
        certificate_name,
        metrics.progress_delta,
    )
    nonloss_result = _protected_nonloss_result(scope, distinctions, metrics)
    recovery_result = _recovery_result(predecessor, candidate)
    invariant_result = _invariant_result(candidate)
    containment_result = _containment_result(typed_ok, candidate)
    domain_result = _domain_result(predecessor, candidate)
    monitor_result = _monitor_result(
        scope,
        certificate_name,
        metrics,
        progress_result,
    )
    return MathematicalComputation(
        scope=scope,
        typed_successor_result=typed_result,
        residuals=residuals,
        residual_result=residual_result,
        metric_bounds=metrics,
        evaluation_result=evaluation_result,
        protected_nonloss_result=nonloss_result,
        recovery_result=recovery_result,
        invariant_result=invariant_result,
        containment_result=containment_result,
        progress_result=progress_result,
        strict_witness_result=strict_result,
        domain_result=domain_result,
        monitor_result=monitor_result,
    )
