import RcpRclmFormalCoreV2.RCP.Monitors

namespace RcpRclmFormalCoreV2
namespace RCP

/-- An accepted candidate/certificate pair from a particular predecessor state. -/
structure AcceptedSuccessor
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (state : State) where
  candidate : Candidate State Update
  certificate : Certificate
  accepted : checker.check state candidate certificate = true

/--
The explicit availability/generator-completeness assumption required by the
conditional infinite-horizon theorem.
-/
def SuccessorAvailability
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K) : Prop :=
  ∀ state,
    K.admissible state →
    K.protectedInvariant state →
    Nonempty (AcceptedSuccessor checker state)

/-- A state packaged with the two hypotheses required to invoke checker soundness. -/
structure DomainState
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex) where
  state : State
  admissible : K.admissible state
  invariant : K.protectedInvariant state

noncomputable def chooseAcceptedSuccessor
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (availability : SuccessorAvailability checker)
    (state : DomainState K) : AcceptedSuccessor checker state.state :=
  Classical.choice (availability state.state state.admissible state.invariant)

noncomputable def nextDomainState
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (availability : SuccessorAvailability checker)
    (state : DomainState K) : DomainState K := by
  let successor := chooseAcceptedSuccessor checker availability state
  let obligations := accepted_step_sound checker
    state.admissible state.invariant successor.accepted
  exact
    { state := successor.candidate.next
      admissible := obligations.successorAdmissible
      invariant := obligations.invariantPreserved }

noncomputable def infiniteDomainState
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (availability : SuccessorAvailability checker)
    (initial : DomainState K) : Nat → DomainState K
  | 0 => initial
  | n + 1 => nextDomainState checker availability
      (infiniteDomainState checker availability initial n)

noncomputable def infiniteAcceptedSuccessor
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (availability : SuccessorAvailability checker)
    (initial : DomainState K)
    (n : Nat) : AcceptedSuccessor checker
      (infiniteDomainState checker availability initial n).state :=
  chooseAcceptedSuccessor checker availability
    (infiniteDomainState checker availability initial n)

/-- A complete infinite accepted trajectory, with domain closure recorded at every time. -/
structure InfiniteAcceptedTrajectory
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K) where
  state : Nat → State
  candidate : Nat → Candidate State Update
  certificate : Nat → Certificate
  accepted : ∀ n, checker.check (state n) (candidate n) (certificate n) = true
  linked : ∀ n, state (n + 1) = (candidate n).next
  admissible : ∀ n, K.admissible (state n)
  invariant : ∀ n, K.protectedInvariant (state n)

/-- Restrict an infinite accepted trajectory to any finite prefix. -/
def finitePrefixOfInfinite
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    (trajectory : InfiniteAcceptedTrajectory checker)
    (horizon : Nat) : FiniteAcceptedTrajectory checker horizon where
  state := trajectory.state
  candidate := trajectory.candidate
  certificate := trajectory.certificate
  initialAdmissible := trajectory.admissible 0
  initialInvariant := trajectory.invariant 0
  accepted := fun t _ => trajectory.accepted t
  linked := fun t _ => trajectory.linked t

noncomputable def buildInfiniteAcceptedTrajectory
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (availability : SuccessorAvailability checker)
    (initial : DomainState K) : InfiniteAcceptedTrajectory checker where
  state := fun n => (infiniteDomainState checker availability initial n).state
  candidate := fun n =>
    (infiniteAcceptedSuccessor checker availability initial n).candidate
  certificate := fun n =>
    (infiniteAcceptedSuccessor checker availability initial n).certificate
  accepted := fun n =>
    (infiniteAcceptedSuccessor checker availability initial n).accepted
  linked := by
    intro n
    rfl
  admissible := fun n =>
    (infiniteDomainState checker availability initial n).admissible
  invariant := fun n =>
    (infiniteDomainState checker availability initial n).invariant

/--
Reserved infinite-horizon theorem name. The availability assumption remains an
explicit argument and is not derived from checker soundness.
-/
theorem conditional_infinite_trajectory_exists
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (availability : SuccessorAvailability checker)
    (initial : DomainState K) :
    ∃ trajectory : InfiniteAcceptedTrajectory checker,
      trajectory.state 0 = initial.state := by
  exact ⟨buildInfiniteAcceptedTrajectory checker availability initial, rfl⟩

/-- Every finite prefix of an infinite accepted path satisfies endpoint recovery. -/
theorem infinite_endpoint_recovery_prefix_bound
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (laws : RecoveryCompositionLaws K)
    (trajectory : InfiniteAcceptedTrajectory checker)
    (t : Nat) :
    K.stateDistance
        (composedRecovery
          (finitePrefixOfInfinite trajectory t)
          t
          (trajectory.state t))
        (trajectory.state 0) ≤
      cumulativeRecoveryBudget (finitePrefixOfInfinite trajectory t) t := by
  simpa [finitePrefixOfInfinite] using
    (finite_endpoint_recovery_bound checker laws
      (finitePrefixOfInfinite trajectory t) t (Nat.le_refl t))

/-- Every finite prefix of an infinite accepted path satisfies the Lyapunov bound. -/
theorem infinite_lyapunov_motion_prefix_bound
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (t : Nat) :
    monitors.lyapunovValue (trajectory.state t) +
        cumulativeMotionCharge monitors (finitePrefixOfInfinite trajectory t) t ≤
      monitors.lyapunovValue (trajectory.state 0) +
        cumulativeLyapunovError monitors (finitePrefixOfInfinite trajectory t) t := by
  simpa [finitePrefixOfInfinite] using
    (finite_lyapunov_motion_bound checker monitors
      (finitePrefixOfInfinite trajectory t) t (Nat.le_refl t))

/-- Every finite prefix of an infinite accepted path satisfies the ambiguity bound. -/
theorem infinite_ambiguity_collapse_prefix_bound
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (t : Nat) :
    cumulativeUnsupportedCollapse monitors (finitePrefixOfInfinite trajectory t) t ≤
      cumulativeAmbiguityError monitors (finitePrefixOfInfinite trajectory t) t := by
  exact finite_ambiguity_collapse_bound checker monitors
    (finitePrefixOfInfinite trajectory t) t (Nat.le_refl t)

/-- Every finite prefix preserves transported self-model relevance within budget. -/
theorem infinite_self_model_relevance_prefix_bound
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (t : Nat)
    (relevance : Relevance) :
    monitors.relevanceValue (trajectory.state 0) relevance ≤
      monitors.relevanceValue (trajectory.state t)
          (transportedRelevance monitors
            (finitePrefixOfInfinite trajectory t) t relevance) +
        cumulativeRelevanceError monitors
          (finitePrefixOfInfinite trajectory t) t := by
  simpa [finitePrefixOfInfinite] using
    (finite_self_model_relevance_bound checker monitors
      (finitePrefixOfInfinite trajectory t) t (Nat.le_refl t) relevance)

/--
Uniform caps on all finite partial error budgets of an infinite accepted path.
For nonnegative series, a concrete standard `Summable` proof may be used to
construct these caps.  Gate A keeps the bounded-partial-sum premise explicit
rather than silently assuming analytic convergence.
-/
structure UniformMonitorBudgetCaps
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker) where
  lyapunovCap : ℝ
  ambiguityCap : ℝ
  relevanceCap : ℝ
  lyapunovBound : ∀ t,
    cumulativeLyapunovError monitors (finitePrefixOfInfinite trajectory t) t ≤
      lyapunovCap
  ambiguityBound : ∀ t,
    cumulativeAmbiguityError monitors (finitePrefixOfInfinite trajectory t) t ≤
      ambiguityCap
  relevanceBound : ∀ t,
    cumulativeRelevanceError monitors (finitePrefixOfInfinite trajectory t) t ≤
      relevanceCap

/--
Bounded partial error budgets yield uniform finite-prefix Lyapunov, ambiguity,
and transported self-model-relevance bounds along the infinite accepted path.
-/
theorem infinite_monitor_uniform_bounds
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (caps : UniformMonitorBudgetCaps monitors trajectory)
    (t : Nat)
    (relevance : Relevance) :
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
  have lyapunovPrefix :=
    infinite_lyapunov_motion_prefix_bound checker monitors trajectory t
  have lyapunovCapped := le_trans lyapunovPrefix
    (add_le_add_right (caps.lyapunovBound t)
      (monitors.lyapunovValue (trajectory.state 0)))
  have ambiguityCapped := le_trans
    (infinite_ambiguity_collapse_prefix_bound checker monitors trajectory t)
    (caps.ambiguityBound t)
  have relevancePrefix :=
    infinite_self_model_relevance_prefix_bound
      checker monitors trajectory t relevance
  have relevanceCapped := le_trans relevancePrefix
    (add_le_add_right (caps.relevanceBound t)
      (monitors.relevanceValue (trajectory.state t)
        (transportedRelevance monitors
          (finitePrefixOfInfinite trajectory t) t relevance)))
  exact ⟨lyapunovCapped, ambiguityCapped, relevanceCapped⟩

/-- The accumulated nonnegative motion charge is uniformly bounded on every prefix. -/
theorem infinite_cumulative_motion_bounded
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : InfiniteAcceptedTrajectory checker)
    (caps : UniformMonitorBudgetCaps monitors trajectory)
    (t : Nat) :
    cumulativeMotionCharge monitors (finitePrefixOfInfinite trajectory t) t ≤
      monitors.lyapunovValue (trajectory.state 0) + caps.lyapunovCap := by
  have motionBelowChargedValue :
      cumulativeMotionCharge monitors (finitePrefixOfInfinite trajectory t) t ≤
        monitors.lyapunovValue (trajectory.state t) +
          cumulativeMotionCharge monitors
            (finitePrefixOfInfinite trajectory t) t := by
    have lifted := add_le_add_left
      (monitors.lyapunovValue_nonnegative (trajectory.state t))
      (cumulativeMotionCharge monitors (finitePrefixOfInfinite trajectory t) t)
    simpa using lifted
  have prefixBound :=
    infinite_lyapunov_motion_prefix_bound checker monitors trajectory t
  have cappedPrefix := le_trans prefixBound
    (add_le_add_right (caps.lyapunovBound t)
      (monitors.lyapunovValue (trajectory.state 0)))
  exact le_trans motionBelowChargedValue cappedPrefix

end RCP
end RcpRclmFormalCoreV2
