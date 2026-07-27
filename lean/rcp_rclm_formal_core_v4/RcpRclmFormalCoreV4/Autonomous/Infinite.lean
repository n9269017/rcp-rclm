import RcpRclmFormalCoreV4.Autonomous.Trajectory

namespace RcpRclmFormalCoreV4
namespace Autonomous

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV3

/-- An active state packaged with the inherited admissibility and invariant hypotheses. -/
structure AutonomousDomainState
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    (base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex) where
  state : State
  admissible : base.admissible state
  invariant : base.protectedInvariant state

/-- A deterministic bounded-search output from one active state. -/
structure AcceptedAutonomousSuccessor
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (state : State) where
  attempt : SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
    Objective Program HistoryHash ChallengeHash RecursiveTask
  found : firstAccepted checker state
    (improver.enumerate state (improver.history state)) = some attempt

/--
Executable Gate E availability: deterministic bounded search returns an accepted output at
every admissible invariant-preserving state.  Unlike Gate D availability, the successor is
identified by the declared search procedure rather than supplied as a bare existential.
-/
def ConstructiveSuccessorAvailability
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask)) : Prop :=
  ∀ state,
    base.admissible state →
    base.protectedInvariant state →
    Nonempty (AcceptedAutonomousSuccessor checker improver state)

/-- Relative candidate existence in the frozen enumeration discharges constructive availability. -/
theorem constructive_successor_availability_on_declared_class
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (acceptedCandidateExists : ∀ state,
      base.admissible state →
      base.protectedInvariant state →
      ∃ attempt ∈ improver.enumerate state (improver.history state),
        checker.check state attempt.candidate attempt.certificate = true) :
    ConstructiveSuccessorAvailability checker improver := by
  intro state stateAdmissible stateInvariant
  rcases bounded_search_complete checker state
    (improver.enumerate state (improver.history state))
    (acceptedCandidateExists state stateAdmissible stateInvariant) with
    ⟨attempt, found⟩
  exact ⟨⟨attempt, found⟩⟩

noncomputable def chooseAutonomousSuccessor
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (availability : ConstructiveSuccessorAvailability checker improver)
    (state : AutonomousDomainState base) :
    AcceptedAutonomousSuccessor checker improver state.state :=
  Classical.choice (availability state.state state.admissible state.invariant)

noncomputable def nextAutonomousDomainState
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (availability : ConstructiveSuccessorAvailability checker improver)
    (state : AutonomousDomainState base) : AutonomousDomainState base := by
  let successor := chooseAutonomousSuccessor checker improver availability state
  have accepted : checker.check state.state successor.attempt.candidate
      successor.attempt.certificate = true :=
    firstAccepted_sound checker state.state successor.found
  let obligations := autonomous_accepted_step_sound checker
    state.admissible state.invariant accepted
  exact
    { state := successor.attempt.candidate.next
      admissible := obligations.learnedStep.baseObligations.successorAdmissible
      invariant := obligations.learnedStep.baseObligations.invariantPreserved }

noncomputable def infiniteAutonomousDomainState
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (availability : ConstructiveSuccessorAvailability checker improver)
    (initial : AutonomousDomainState base) : Nat → AutonomousDomainState base
  | 0 => initial
  | n + 1 => nextAutonomousDomainState checker improver availability
      (infiniteAutonomousDomainState checker improver availability initial n)

noncomputable def infiniteAutonomousSuccessor
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (availability : ConstructiveSuccessorAvailability checker improver)
    (initial : AutonomousDomainState base)
    (n : Nat) : AcceptedAutonomousSuccessor checker improver
      (infiniteAutonomousDomainState checker improver availability initial n).state :=
  chooseAutonomousSuccessor checker improver availability
    (infiniteAutonomousDomainState checker improver availability initial n)

/-- Infinite trajectory whose every transition is selected by the bounded autonomous search. -/
structure InfiniteAutonomousTrajectory
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker) where
  state : Nat → State
  attempt : Nat → SearchAttempt State Update BaseCertificate Task Generator Proposal
    PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask
  accepted : ∀ n,
    checker.check (state n) (attempt n).candidate (attempt n).certificate = true
  linked : ∀ n, state (n + 1) = (attempt n).candidate.next
  admissible : ∀ n, base.admissible (state n)
  invariant : ∀ n, base.protectedInvariant (state n)

noncomputable def buildInfiniteAutonomousTrajectory
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (availability : ConstructiveSuccessorAvailability checker improver)
    (initial : AutonomousDomainState base) : InfiniteAutonomousTrajectory checker where
  state := fun n =>
    (infiniteAutonomousDomainState checker improver availability initial n).state
  attempt := fun n =>
    (infiniteAutonomousSuccessor checker improver availability initial n).attempt
  accepted := fun n => firstAccepted_sound checker
    (infiniteAutonomousDomainState checker improver availability initial n).state
    (infiniteAutonomousSuccessor checker improver availability initial n).found
  linked := by
    intro n
    rfl
  admissible := fun n =>
    (infiniteAutonomousDomainState checker improver availability initial n).admissible
  invariant := fun n =>
    (infiniteAutonomousDomainState checker improver availability initial n).invariant

/-- Gate E conditional infinite autonomous RCLM trajectory theorem. -/
theorem conditional_infinite_autonomous_rclm_trajectory_exists
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    (improver : AutonomousImprover State HistoryHash
      (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
        Objective Program HistoryHash ChallengeHash RecursiveTask))
    (availability : ConstructiveSuccessorAvailability checker improver)
    (initial : AutonomousDomainState base) :
    ∃ trajectory : InfiniteAutonomousTrajectory checker,
      trajectory.state 0 = initial.state := by
  exact ⟨buildInfiniteAutonomousTrajectory checker improver availability initial, rfl⟩

end Autonomous
end RcpRclmFormalCoreV4
