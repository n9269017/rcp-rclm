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

end RCP
end RcpRclmFormalCoreV2
