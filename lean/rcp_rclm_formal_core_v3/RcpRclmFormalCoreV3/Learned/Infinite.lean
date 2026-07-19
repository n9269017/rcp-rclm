import RcpRclmFormalCoreV3.Learned.Trajectory

namespace RcpRclmFormalCoreV3
namespace Learned

open RcpRclmFormalCoreV2

/-- An accepted learned successor from a particular predecessor state. -/
structure AcceptedLearnedSuccessor
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (state : State) where
  candidate : RCP.Candidate State Update
  certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
  accepted : checker.check state candidate certificate = true

/--
The explicit Gate D availability premise.  It is not derived from checker soundness,
generator plausibility, or the existence of one finite reference trajectory.
-/
def FrontierExpandingSuccessorAvailability
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker) : Prop :=
  ∀ state,
    base.admissible state →
    base.protectedInvariant state →
    Nonempty (AcceptedLearnedSuccessor checker state)

/-- A Gate D state packaged with the inherited theorem-domain hypotheses. -/
structure LearnedDomainState
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    (base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex) where
  state : State
  admissible : base.admissible state
  invariant : base.protectedInvariant state

noncomputable def chooseAcceptedLearnedSuccessor
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (availability : FrontierExpandingSuccessorAvailability checker)
    (state : LearnedDomainState base) :
    AcceptedLearnedSuccessor checker state.state :=
  Classical.choice (availability state.state state.admissible state.invariant)

noncomputable def nextLearnedDomainState
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (availability : FrontierExpandingSuccessorAvailability checker)
    (state : LearnedDomainState base) : LearnedDomainState base := by
  let successor := chooseAcceptedLearnedSuccessor checker availability state
  let obligations := learned_accepted_step_sound checker
    state.admissible state.invariant successor.accepted
  exact
    { state := successor.candidate.next
      admissible := obligations.baseObligations.successorAdmissible
      invariant := obligations.baseObligations.invariantPreserved }

noncomputable def infiniteLearnedDomainState
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (availability : FrontierExpandingSuccessorAvailability checker)
    (initial : LearnedDomainState base) : Nat → LearnedDomainState base
  | 0 => initial
  | n + 1 =>
      nextLearnedDomainState checker availability
        (infiniteLearnedDomainState checker availability initial n)

noncomputable def infiniteAcceptedLearnedSuccessor
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (availability : FrontierExpandingSuccessorAvailability checker)
    (initial : LearnedDomainState base)
    (n : Nat) :
    AcceptedLearnedSuccessor checker
      (infiniteLearnedDomainState checker availability initial n).state :=
  chooseAcceptedLearnedSuccessor checker availability
    (infiniteLearnedDomainState checker availability initial n)

/-- Infinite learned trajectory with explicit inherited domain closure. -/
structure InfiniteLearnedTrajectory
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker) where
  state : Nat → State
  candidate : Nat → RCP.Candidate State Update
  certificate : Nat →
    CertificatePacket BaseCertificate Task Generator Proposal PackageHash
  accepted : ∀ n, checker.check (state n) (candidate n) (certificate n) = true
  linked : ∀ n, state (n + 1) = (candidate n).next
  admissible : ∀ n, base.admissible (state n)
  invariant : ∀ n, base.protectedInvariant (state n)

noncomputable def buildInfiniteLearnedTrajectory
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (availability : FrontierExpandingSuccessorAvailability checker)
    (initial : LearnedDomainState base) : InfiniteLearnedTrajectory checker where
  state := fun n => (infiniteLearnedDomainState checker availability initial n).state
  candidate := fun n =>
    (infiniteAcceptedLearnedSuccessor checker availability initial n).candidate
  certificate := fun n =>
    (infiniteAcceptedLearnedSuccessor checker availability initial n).certificate
  accepted := fun n =>
    (infiniteAcceptedLearnedSuccessor checker availability initial n).accepted
  linked := by
    intro n
    rfl
  admissible := fun n =>
    (infiniteLearnedDomainState checker availability initial n).admissible
  invariant := fun n =>
    (infiniteLearnedDomainState checker availability initial n).invariant

/-- Gate D conditional infinite learned trajectory theorem. -/
theorem conditional_infinite_learned_frontier_trajectory_exists
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (availability : FrontierExpandingSuccessorAvailability checker)
    (initial : LearnedDomainState base) :
    ∃ trajectory : InfiniteLearnedTrajectory checker,
      trajectory.state 0 = initial.state := by
  exact ⟨buildInfiniteLearnedTrajectory checker availability initial, rfl⟩

/-- Every transition in the conditional infinite trajectory strictly expands the frontier. -/
theorem infinite_learned_frontier_strict
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (trajectory : InfiniteLearnedTrajectory checker)
    (n : Nat) :
    StrictFrontierExpansion learned
      (trajectory.state n) (trajectory.candidate n) := by
  exact
    (learned_accepted_step_sound checker
      (trajectory.admissible n)
      (trajectory.invariant n)
      (trajectory.accepted n)).learnedObligations.strictFrontierExpansion

end Learned
end RcpRclmFormalCoreV3
