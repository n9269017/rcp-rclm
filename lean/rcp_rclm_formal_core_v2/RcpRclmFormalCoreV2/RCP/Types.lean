import Mathlib.Data.Real.Basic

namespace RcpRclmFormalCoreV2
namespace RCP

/-- A proposed typed update together with its claimed successor state. -/
structure Candidate (State Update : Type*) where
  update : Update
  next : State

/--
Abstract data required by the conditional successor theorem.

Every field is theorem-relevant. In particular, protected values, residuals,
recovery, trust, resources, and reality containment are supplied by an
instantiation rather than replaced by constants or booleans set true by
construction. `protectedValue_nonconstant` prevents the theorem kernel itself
from being instantiated with a globally constant distinguishability quantity.
-/
structure Kernel
    (State Update Certificate Protected ResidualIndex : Type*) where
  apply : State → Update → State
  admissible : State → Prop
  protectedInvariant : State → Prop

  protectedValue : State → Protected → ℝ
  protectedValue_nonconstant :
    ∃ state₁ distinction₁ state₂ distinction₂,
      protectedValue state₁ distinction₁ ≠
        protectedValue state₂ distinction₂
  transportProtected : State → Candidate State Update → Protected → Protected
  lossBudget : State → Candidate State Update → ℝ
  lossBudget_nonnegative : ∀ s candidate, 0 ≤ lossBudget s candidate

  stateDistance : State → State → ℝ
  stateDistance_nonnegative : ∀ x y, 0 ≤ stateDistance x y
  recover : State → Candidate State Update → State → State
  recoveryBudget : State → Candidate State Update → ℝ
  recoveryBudget_nonnegative : ∀ s candidate, 0 ≤ recoveryBudget s candidate

  progress : State → ℝ
  strictWitness : State → Candidate State Update → Certificate → Prop

  residual : State → Candidate State Update → Certificate → ResidualIndex → ℝ
  trustValid : State → Candidate State Update → Certificate → Prop
  resourceValid : State → Candidate State Update → Certificate → Prop
  realityContained : State → Candidate State Update → Certificate → Prop

/-- The candidate's claimed successor agrees with the typed update semantics. -/
def TypedSuccessor
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex)
    (state : State)
    (candidate : Candidate State Update) : Prop :=
  candidate.next = K.apply state candidate.update

end RCP
end RcpRclmFormalCoreV2
