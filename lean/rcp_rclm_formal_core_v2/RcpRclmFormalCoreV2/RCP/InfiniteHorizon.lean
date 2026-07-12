import RcpRclmFormalCoreV2.RCP.Trajectory

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

end RCP
end RcpRclmFormalCoreV2
