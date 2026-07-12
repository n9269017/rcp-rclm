import Mathlib.Topology.Algebra.InfiniteSum.Real
import RcpRclmFormalCoreV2.RCP.InfiniteHorizon

open scoped BigOperators

namespace RcpRclmFormalCoreV2
namespace RCP

/-- Recursive Lyapunov error accumulation is the corresponding finite range sum. -/
theorem cumulativeLyapunovError_eq_sum_range
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t,
      cumulativeLyapunovError monitors trajectory t =
        ∑ i ∈ Finset.range t,
          monitors.lyapunovError
            (trajectory.state i)
            (trajectory.candidate i)
            (trajectory.certificate i) := by
  intro t
  induction t with
  | zero =>
      simp [cumulativeLyapunovError]
  | succ t inductionHypothesis =>
      simp [cumulativeLyapunovError, Finset.sum_range_succ,
        inductionHypothesis]

/-- Recursive ambiguity error accumulation is the corresponding finite range sum. -/
theorem cumulativeAmbiguityError_eq_sum_range
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t,
      cumulativeAmbiguityError monitors trajectory t =
        ∑ i ∈ Finset.range t,
          monitors.ambiguityError
            (trajectory.state i)
            (trajectory.candidate i)
            (trajectory.certificate i) := by
  intro t
  induction t with
  | zero =>
      simp [cumulativeAmbiguityError]
  | succ t inductionHypothesis =>
      simp [cumulativeAmbiguityError, Finset.sum_range_succ,
        inductionHypothesis]

/-- Recursive relevance error accumulation is the corresponding finite range sum. -/
theorem cumulativeRelevanceError_eq_sum_range
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t,
      cumulativeRelevanceError monitors trajectory t =
        ∑ i ∈ Finset.range t,
          monitors.relevanceError
            (trajectory.state i)
            (trajectory.candidate i)
            (trajectory.certificate i) := by
  intro t
  induction t with
  | zero =>
      simp [cumulativeRelevanceError]
  | succ t inductionHypothesis =>
      simp [cumulativeRelevanceError, Finset.sum_range_succ,
        inductionHypothesis]

/--
Standard analytic summability assumptions for the three nonnegative Paper I
error sequences along an infinite accepted trajectory.
-/
structure SummableMonitorBudgets
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker) : Prop where
  lyapunov : Summable fun t =>
    monitors.lyapunovError
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)
  ambiguity : Summable fun t =>
    monitors.ambiguityError
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)
  relevance : Summable fun t =>
    monitors.relevanceError
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)

/--
Summability of the nonnegative error sequences canonically supplies uniform
caps on all finite partial budgets.
-/
noncomputable def SummableMonitorBudgets.toUniformMonitorBudgetCaps
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {monitors : PreservationMonitors K (Relevance := Relevance)}
    {trajectory : InfiniteAcceptedTrajectory checker}
    (budgets : SummableMonitorBudgets monitors trajectory) :
    UniformMonitorBudgetCaps monitors trajectory where
  lyapunovCap := ∑' t,
    monitors.lyapunovError
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)
  ambiguityCap := ∑' t,
    monitors.ambiguityError
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)
  relevanceCap := ∑' t,
    monitors.relevanceError
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)
  lyapunovBound := by
    intro t
    rw [cumulativeLyapunovError_eq_sum_range]
    exact sum_le_hasSum (Finset.range t)
      (fun i _ => monitors.lyapunovError_nonnegative
        (trajectory.state i)
        (trajectory.candidate i)
        (trajectory.certificate i))
      budgets.lyapunov.hasSum
  ambiguityBound := by
    intro t
    rw [cumulativeAmbiguityError_eq_sum_range]
    exact sum_le_hasSum (Finset.range t)
      (fun i _ => monitors.ambiguityError_nonnegative
        (trajectory.state i)
        (trajectory.candidate i)
        (trajectory.certificate i))
      budgets.ambiguity.hasSum
  relevanceBound := by
    intro t
    rw [cumulativeRelevanceError_eq_sum_range]
    exact sum_le_hasSum (Finset.range t)
      (fun i _ => monitors.relevanceError_nonnegative
        (trajectory.state i)
        (trajectory.candidate i)
        (trajectory.certificate i))
      budgets.relevance.hasSum

/--
Paper I's standard summability premise implies all uniform finite-prefix monitor
conclusions already proved from `UniformMonitorBudgetCaps`.
-/
theorem infinite_monitor_bounds_of_summable
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (budgets : SummableMonitorBudgets monitors trajectory)
    (t : Nat)
    (relevance : Relevance) :
    let caps := budgets.toUniformMonitorBudgetCaps
    (monitors.lyapunovValue (trajectory.state t) +
        cumulativeMotionCharge monitors (finitePrefixOfInfinite trajectory t) t ≤
      monitors.lyapunovValue (trajectory.state 0) + caps.lyapunovCap) ∧
    (cumulativeUnsupportedCollapse monitors
        (finitePrefixOfInfinite trajectory t) t ≤ caps.ambiguityCap) ∧
    (monitors.relevanceValue (trajectory.state 0) relevance ≤
      monitors.relevanceValue (trajectory.state t)
          (transportedRelevance monitors
            (finitePrefixOfInfinite trajectory t) t relevance) +
        caps.relevanceCap) := by
  dsimp
  exact infinite_monitor_uniform_bounds
    checker monitors trajectory budgets.toUniformMonitorBudgetCaps t relevance

/-- Summable Lyapunov error implies a uniform bound on accumulated motion charge. -/
theorem infinite_cumulative_motion_bounded_of_summable
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (budgets : SummableMonitorBudgets monitors trajectory)
    (t : Nat) :
    cumulativeMotionCharge monitors (finitePrefixOfInfinite trajectory t) t ≤
      monitors.lyapunovValue (trajectory.state 0) +
        budgets.toUniformMonitorBudgetCaps.lyapunovCap :=
  infinite_cumulative_motion_bounded
    checker monitors trajectory budgets.toUniformMonitorBudgetCaps t

end RCP
end RcpRclmFormalCoreV2
