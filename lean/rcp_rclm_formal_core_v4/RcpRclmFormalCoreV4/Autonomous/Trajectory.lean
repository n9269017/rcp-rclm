import RcpRclmFormalCoreV4.Autonomous.Search

namespace RcpRclmFormalCoreV4
namespace Autonomous

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV3

/-- A finite trajectory accepted by the Gate E checker. -/
structure FiniteAutonomousTrajectory
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
    (horizon : Nat) where
  state : Nat → State
  candidate : Nat → RCP.Candidate State Update
  certificate : Nat → CertificatePacket BaseCertificate Task Generator Proposal PackageHash
    Objective Program HistoryHash ChallengeHash RecursiveTask
  initialAdmissible : base.admissible (state 0)
  initialInvariant : base.protectedInvariant (state 0)
  accepted : ∀ t, t < horizon →
    checker.check (state t) (candidate t) (certificate t) = true
  linked : ∀ t, t < horizon → state (t + 1) = (candidate t).next

/-- Forget Gate E evidence while retaining the complete accepted Gate D trajectory. -/
def FiniteAutonomousTrajectory.toLearnedTrajectory
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
    {checker : TrustedAutonomousChecker autonomous learnedChecker}
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon) :
    Learned.FiniteLearnedTrajectory learnedChecker horizon where
  state := trajectory.state
  candidate := trajectory.candidate
  certificate := fun t => (trajectory.certificate t).learned
  initialAdmissible := trajectory.initialAdmissible
  initialInvariant := trajectory.initialInvariant
  accepted := by
    intro t bound
    exact checker.refinesLearned (trajectory.accepted t bound)
  linked := trajectory.linked

/-- Every accepted finite autonomous step has the full Gate E obligation bundle. -/
theorem finite_autonomous_step_sound
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
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon)
    (t : Nat)
    (bound : t < horizon) :
    AutonomousAcceptedStep autonomous
      (trajectory.state t) (trajectory.candidate t) (trajectory.certificate t) := by
  have stateFacts := RCP.finite_trajectory_closure baseChecker
    trajectory.toLearnedTrajectory.toBaseTrajectory t (Nat.le_of_lt bound)
  exact autonomous_accepted_step_sound checker stateFacts.1 stateFacts.2
    (trajectory.accepted t bound)

/-- Gate D strict capability-frontier growth is inherited without weakening. -/
theorem finite_autonomous_frontier_growth
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
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      (learned.frontier (trajectory.state 0)).card + t ≤
        (learned.frontier (trajectory.state t)).card :=
  Learned.finite_learned_frontier_card_growth learnedChecker
    trajectory.toLearnedTrajectory

/-- The initial recursive-productivity frontier is retained at every finite time. -/
theorem finite_recursive_productivity_retained
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
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      autonomous.recursiveFrontier (trajectory.state 0) ⊆
        autonomous.recursiveFrontier (trajectory.state t) := by
  intro t
  induction t with
  | zero =>
      intro _
      exact fun _ member => member
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have stepRetention := recursive_productivity_retained
        (finite_autonomous_step_sound checker trajectory t stepBound)
      rw [trajectory.linked t stepBound]
      exact fun task member => stepRetention (previous member)

/-- Cumulative autonomous search cost. -/
def cumulativeSearchCost
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
    {checker : TrustedAutonomousChecker autonomous learnedChecker}
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon) : Nat → Nat
  | 0 => 0
  | t + 1 => cumulativeSearchCost trajectory t +
      autonomous.searchCost (trajectory.state t) (trajectory.candidate t)

/-- Cumulative declared autonomous search budget. -/
def cumulativeSearchBudget
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
    {checker : TrustedAutonomousChecker autonomous learnedChecker}
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon) : Nat → Nat
  | 0 => 0
  | t + 1 => cumulativeSearchBudget trajectory t +
      autonomous.searchBudget (trajectory.state t) (trajectory.candidate t)

/-- Finite autonomous search consumes no more than the cumulative declared budget. -/
theorem finite_autonomous_resource_bound
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
    {horizon : Nat}
    (trajectory : FiniteAutonomousTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      cumulativeSearchCost trajectory t ≤ cumulativeSearchBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeSearchCost, cumulativeSearchBudget]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have acceptedStep := finite_autonomous_step_sound checker trajectory t stepBound
      have stepBudget := acceptedStep.autonomousObligations.searchWithinBudget
      exact Nat.add_le_add previous stepBudget

end Autonomous
end RcpRclmFormalCoreV4
