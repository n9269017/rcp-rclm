import RcpRclmFormalCoreV2.RCP.Checker

namespace RcpRclmFormalCoreV2
namespace RCP

/-- A finite trajectory whose transitions are all accepted by the trusted checker. -/
structure FiniteAcceptedTrajectory
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (horizon : Nat) where
  state : Nat → State
  candidate : Nat → Candidate State Update
  certificate : Nat → Certificate
  initialAdmissible : K.admissible (state 0)
  initialInvariant : K.protectedInvariant (state 0)
  accepted : ∀ t, t < horizon →
    checker.check (state t) (candidate t) (certificate t) = true
  linked : ∀ t, t < horizon → state (t + 1) = (candidate t).next

/-- Every state in a finite accepted trajectory remains admissible and invariant-preserving. -/
theorem finite_trajectory_closure
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      K.admissible (trajectory.state t) ∧
      K.protectedInvariant (trajectory.state t) := by
  intro t
  induction t with
  | zero =>
      intro _
      exact ⟨trajectory.initialAdmissible, trajectory.initialInvariant⟩
  | succ t inductionHypothesis =>
      intro bound
      have previousBound : t ≤ horizon :=
        Nat.le_trans (Nat.le_succ t) bound
      have previousState := inductionHypothesis previousBound
      have stepIndexBound : t < horizon := Nat.lt_of_succ_le bound
      have obligations := accepted_step_sound checker
        previousState.1 previousState.2
        (trajectory.accepted t stepIndexBound)
      rw [trajectory.linked t stepIndexBound]
      exact ⟨obligations.successorAdmissible, obligations.invariantPreserved⟩

/-- Every accepted transition in a finite trajectory satisfies the one-step obligations. -/
theorem finite_trajectory_step_sound
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon)
    (t : Nat)
    (stepIndexBound : t < horizon) :
    StepObligations K
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t) := by
  have stateFacts := finite_trajectory_closure checker trajectory t
    (Nat.le_of_lt stepIndexBound)
  exact accepted_step_sound checker stateFacts.1 stateFacts.2
    (trajectory.accepted t stepIndexBound)

/--
Transport a protected distinction through the first `steps` updates of a finite
trajectory. The definition is meaningful for every natural number; the theorems
below use it only when `steps ≤ horizon`.
-/
def transportedDistinction
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    Nat → Protected → Protected
  | 0, distinction => distinction
  | t + 1, distinction =>
      K.transportProtected
        (trajectory.state t)
        (trajectory.candidate t)
        (transportedDistinction trajectory t distinction)

/-- Sum of the declared protected-information loss budgets for the first `steps` updates. -/
def cumulativeLossBudget
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeLossBudget trajectory t +
        K.lossBudget (trajectory.state t) (trajectory.candidate t)

/-- Actual certified local recovery error at transition `t`. -/
def localRecoveryError
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon)
    (t : Nat) : ℝ :=
  K.stateDistance
    (K.recover
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.candidate t).next)
    (trajectory.state t)

/-- Sum of the actual certified local recovery errors for the first `steps` updates. -/
def cumulativeRecoveryError
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeRecoveryError trajectory t + localRecoveryError trajectory t

/-- Sum of the declared recovery budgets for the first `steps` updates. -/
def cumulativeRecoveryBudget
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeRecoveryBudget trajectory t +
        K.recoveryBudget (trajectory.state t) (trajectory.candidate t)

/--
Compose the candidate-tied recovery maps in rollback order.  For `steps = t`,
this is `R₀ ∘ R₁ ∘ ... ∘ Rₜ₋₁`, so it maps an endpoint state at time `t`
back into the common abstract state type used by the Gate A kernel.
-/
def composedRecovery
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → State → State
  | 0, endpoint => endpoint
  | t + 1, endpoint =>
      composedRecovery trajectory t
        (K.recover
          (trajectory.state t)
          (trajectory.candidate t)
          endpoint)

/-- A finite composition of nonexpansive recovery maps remains nonexpansive. -/
theorem composedRecovery_nonexpansive
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (laws : RecoveryCompositionLaws K)
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t x y,
      K.stateDistance
          (composedRecovery trajectory t x)
          (composedRecovery trajectory t y) ≤
        K.stateDistance x y := by
  intro t
  induction t with
  | zero =>
      intro x y
      exact le_rfl
  | succ t inductionHypothesis =>
      intro x y
      calc
        K.stateDistance
            (composedRecovery trajectory (t + 1) x)
            (composedRecovery trajectory (t + 1) y) =
          K.stateDistance
            (composedRecovery trajectory t
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                x))
            (composedRecovery trajectory t
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                y)) := by rfl
        _ ≤ K.stateDistance
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                x)
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                y) := inductionHypothesis _ _
        _ ≤ K.stateDistance x y :=
          laws.recoverNonexpansive _ _ _ _

/-- Progress is monotone between any two in-horizon states of an accepted trajectory. -/
theorem finite_progress_monotone
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon)
    (start finish : Nat)
    (startLeFinish : start ≤ finish)
    (finishBound : finish ≤ horizon) :
    K.progress (trajectory.state start) ≤
      K.progress (trajectory.state finish) := by
  exact Nat.le_induction
    (m := start)
    (P := fun finish _ =>
      finish ≤ horizon →
        K.progress (trajectory.state start) ≤
          K.progress (trajectory.state finish))
    (by
      intro _
      exact le_rfl)
    (by
      intro t _ inductionHypothesis successorBound
      have stepBound : t < horizon := Nat.lt_of_succ_le successorBound
      have prefixBound : t ≤ horizon := Nat.le_of_lt stepBound
      have prefixProgress := inductionHypothesis prefixBound
      have obligations :=
        finite_trajectory_step_sound checker trajectory t stepBound
      have stepProgress :
          K.progress (trajectory.state t) ≤
            K.progress (trajectory.state (t + 1)) := by
        rw [trajectory.linked t stepBound]
        exact obligations.progressNondecreasing
      exact le_trans prefixProgress stepProgress)
    finish startLeFinish finishBound

/--
The protected value at the initial state is bounded by the transported endpoint
value plus the sum of all declared per-step loss budgets.
-/
theorem finite_composed_nonloss_bound
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon → ∀ distinction,
      K.protectedValue (trajectory.state 0) distinction ≤
        K.protectedValue (trajectory.state t)
            (transportedDistinction trajectory t distinction) +
          cumulativeLossBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _ distinction
      simp [transportedDistinction, cumulativeLossBudget]
  | succ t inductionHypothesis =>
      intro bound distinction
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_of_lt stepBound
      have previous := inductionHypothesis previousBound distinction
      have obligations :=
        finite_trajectory_step_sound checker trajectory t stepBound
      have stepNonLoss :=
        obligations.protectedNonLoss
          (transportedDistinction trajectory t distinction)
      have stepNonLossAtState :
          K.protectedValue (trajectory.state t)
              (transportedDistinction trajectory t distinction) ≤
            K.protectedValue (trajectory.state (t + 1))
                (K.transportProtected
                  (trajectory.state t)
                  (trajectory.candidate t)
                  (transportedDistinction trajectory t distinction)) +
              K.lossBudget (trajectory.state t) (trajectory.candidate t) := by
        rw [trajectory.linked t stepBound]
        exact stepNonLoss
      calc
        K.protectedValue (trajectory.state 0) distinction
            ≤ K.protectedValue (trajectory.state t)
                (transportedDistinction trajectory t distinction) +
              cumulativeLossBudget trajectory t := previous
        _ ≤ (K.protectedValue (trajectory.state (t + 1))
                (K.transportProtected
                  (trajectory.state t)
                  (trajectory.candidate t)
                  (transportedDistinction trajectory t distinction)) +
              K.lossBudget (trajectory.state t) (trajectory.candidate t)) +
            cumulativeLossBudget trajectory t :=
          add_le_add_left stepNonLossAtState
            (cumulativeLossBudget trajectory t)
        _ = K.protectedValue (trajectory.state (t + 1))
                (transportedDistinction trajectory (t + 1) distinction) +
              cumulativeLossBudget trajectory (t + 1) := by
          simp only [transportedDistinction, cumulativeLossBudget]
          ac_rfl

/--
The sum of actual certified local recovery errors is bounded by the sum of the
per-step recovery budgets. This aggregate theorem remains useful independently
of the stronger endpoint rollback theorem below.
-/
theorem finite_composed_recovery_bound
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      cumulativeRecoveryError trajectory t ≤
        cumulativeRecoveryBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeRecoveryError, cumulativeRecoveryBudget]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_of_lt stepBound
      have previous := inductionHypothesis previousBound
      have localBound :=
        (finite_trajectory_step_sound checker trajectory t stepBound).constructiveRecovery
      have combined := add_le_add previous localBound
      simpa [cumulativeRecoveryError, cumulativeRecoveryBudget,
        localRecoveryError, ConstructiveRecovery] using combined

/--
The composed rollback map recovers the initial state from every accepted finite
endpoint within the sum of the declared one-step recovery budgets.

Unlike `finite_composed_recovery_bound`, this theorem is an actual endpoint
statement.  Its metric and nonexpansiveness assumptions are explicit in
`RecoveryCompositionLaws`; checker soundness alone is not used to infer them.
-/
theorem finite_endpoint_recovery_bound
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (laws : RecoveryCompositionLaws K)
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      K.stateDistance
          (composedRecovery trajectory t (trajectory.state t))
          (trajectory.state 0) ≤
        cumulativeRecoveryBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simpa [composedRecovery, cumulativeRecoveryBudget] using
        (le_of_eq (laws.selfDistanceZero (trajectory.state 0)))
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_of_lt stepBound
      have previous := inductionHypothesis previousBound
      have localBound :
          K.stateDistance
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.state (t + 1)))
              (trajectory.state t) ≤
            K.recoveryBudget
              (trajectory.state t)
              (trajectory.candidate t) := by
        simpa [trajectory.linked t stepBound, ConstructiveRecovery] using
          (finite_trajectory_step_sound checker trajectory t stepBound).constructiveRecovery
      have prefixNonexpansive :
          K.stateDistance
              (composedRecovery trajectory t
                (K.recover
                  (trajectory.state t)
                  (trajectory.candidate t)
                  (trajectory.state (t + 1))))
              (composedRecovery trajectory t (trajectory.state t)) ≤
            K.stateDistance
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.state (t + 1)))
              (trajectory.state t) :=
        composedRecovery_nonexpansive laws trajectory t _ _
      calc
        K.stateDistance
            (composedRecovery trajectory (t + 1)
              (trajectory.state (t + 1)))
            (trajectory.state 0) =
          K.stateDistance
            (composedRecovery trajectory t
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.state (t + 1))))
            (trajectory.state 0) := by rfl
        _ ≤ K.stateDistance
              (composedRecovery trajectory t
                (K.recover
                  (trajectory.state t)
                  (trajectory.candidate t)
                  (trajectory.state (t + 1))))
              (composedRecovery trajectory t (trajectory.state t)) +
            K.stateDistance
              (composedRecovery trajectory t (trajectory.state t))
              (trajectory.state 0) :=
          laws.triangle _ _ _
        _ ≤ K.stateDistance
              (K.recover
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.state (t + 1)))
              (trajectory.state t) +
            cumulativeRecoveryBudget trajectory t :=
          add_le_add prefixNonexpansive previous
        _ ≤ K.recoveryBudget
              (trajectory.state t)
              (trajectory.candidate t) +
            cumulativeRecoveryBudget trajectory t :=
          add_le_add_left localBound _
        _ = cumulativeRecoveryBudget trajectory (t + 1) := by
          simp only [cumulativeRecoveryBudget]
          ac_rfl

end RCP
end RcpRclmFormalCoreV2
