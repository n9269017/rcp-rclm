import Mathlib.Tactic.Ring
import RcpRclmFormalCoreV2.RCP
import RcpRclmFormalCoreV3.Learned.Kernel

namespace RcpRclmFormalCoreV3
namespace Learned

open RcpRclmFormalCoreV2

/-- A finite trajectory accepted by a trusted Gate D checker. -/
structure FiniteLearnedTrajectory
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    (horizon : Nat) where
  state : Nat → State
  candidate : Nat → RCP.Candidate State Update
  certificate : Nat →
    CertificatePacket BaseCertificate Task Generator Proposal PackageHash
  initialAdmissible : base.admissible (state 0)
  initialInvariant : base.protectedInvariant (state 0)
  accepted : ∀ t, t < horizon →
    checker.check (state t) (candidate t) (certificate t) = true
  linked : ∀ t, t < horizon → state (t + 1) = (candidate t).next

/-- Forget Gate D evidence and obtain an ordinary finite accepted base trajectory. -/
def FiniteLearnedTrajectory.toBaseTrajectory
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    RCP.FiniteAcceptedTrajectory baseChecker horizon where
  state := trajectory.state
  candidate := trajectory.candidate
  certificate := fun t => (trajectory.certificate t).base
  initialAdmissible := trajectory.initialAdmissible
  initialInvariant := trajectory.initialInvariant
  accepted := by
    intro t bound
    exact checker.refinesBase (trajectory.accepted t bound)
  linked := trajectory.linked

/-- Every accepted learned transition has the complete Gate D obligation bundle. -/
theorem finite_learned_step_sound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon)
    (t : Nat)
    (bound : t < horizon) :
    LearnedAcceptedStep learned
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t) := by
  have stateFacts :=
    RCP.finite_trajectory_closure baseChecker trajectory.toBaseTrajectory t
      (Nat.le_of_lt bound)
  exact learned_accepted_step_sound checker
    stateFacts.1 stateFacts.2 (trajectory.accepted t bound)

/-- Every adjacent accepted learned step strictly expands the certified frontier. -/
theorem finite_learned_frontier_chain
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon)
    (t : Nat)
    (bound : t < horizon) :
    learned.frontier (trajectory.state t) ⊆
        learned.frontier (trajectory.state (t + 1)) ∧
      (learned.frontier (trajectory.state t)).card <
        (learned.frontier (trajectory.state (t + 1))).card := by
  have expansion :=
    (finite_learned_step_sound checker trajectory t bound).learnedObligations.strictFrontierExpansion
  rw [trajectory.linked t bound]
  exact expansion

/-- The initial certified frontier is retained at every finite time. -/
theorem finite_learned_frontier_retained
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      learned.frontier (trajectory.state 0) ⊆
        learned.frontier (trajectory.state t) := by
  intro t
  induction t with
  | zero =>
      intro _
      exact fun _ member => member
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have stepSubset :=
        (finite_learned_frontier_chain checker trajectory t stepBound).1
      exact fun task member => stepSubset (previous member)

/-- Every accepted learned step adds at least one frontier element. -/
theorem finite_learned_frontier_card_growth
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      (learned.frontier (trajectory.state 0)).card + t ≤
        (learned.frontier (trajectory.state t)).card := by
  intro t
  induction t with
  | zero =>
      intro _
      simp
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have stepCard :=
        (finite_learned_frontier_chain checker trajectory t stepBound).2
      have lifted :
          (learned.frontier (trajectory.state 0)).card + (t + 1) ≤
            (learned.frontier (trajectory.state t)).card + 1 := by
        simpa [Nat.add_assoc] using Nat.add_le_add_right previous 1
      exact le_trans lifted (Nat.succ_le_of_lt stepCard)

/-- Final-frontier form of the Gate D finite strict-growth theorem. -/
theorem finite_learned_final_frontier_growth
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    (learned.frontier (trajectory.state 0)).card + horizon ≤
      (learned.frontier (trajectory.state horizon)).card :=
  finite_learned_frontier_card_growth checker trajectory horizon (Nat.le_refl horizon)

/-- Cumulative Gate D resource use. -/
def cumulativeResourceUsed
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) : Nat → Nat
  | 0 => 0
  | t + 1 =>
      cumulativeResourceUsed trajectory t +
        learned.resourceUsed (trajectory.state t) (trajectory.candidate t)

/-- Cumulative Gate D resource budget. -/
def cumulativeResourceBudget
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) : Nat → Nat
  | 0 => 0
  | t + 1 =>
      cumulativeResourceBudget trajectory t +
        learned.resourceBudget (trajectory.state t) (trajectory.candidate t)

/-- Cumulative resource use is bounded by the cumulative declared budget. -/
theorem finite_learned_resource_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      cumulativeResourceUsed trajectory t ≤ cumulativeResourceBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeResourceUsed, cumulativeResourceBudget]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have local :=
        (finite_learned_step_sound checker trajectory t stepBound).learnedObligations.resourceWithinBudget
      exact Nat.add_le_add previous local

/-- Cumulative goal drift and its budget. -/
def cumulativeGoalDrift
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) : Nat → Nat
  | 0 => 0
  | t + 1 =>
      cumulativeGoalDrift trajectory t +
        learned.goalDrift (trajectory.state t) (trajectory.candidate t)

def cumulativeGoalDriftBudget
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) : Nat → Nat
  | 0 => 0
  | t + 1 =>
      cumulativeGoalDriftBudget trajectory t +
        learned.goalDriftBudget (trajectory.state t) (trajectory.candidate t)

theorem finite_learned_goal_drift_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      cumulativeGoalDrift trajectory t ≤ cumulativeGoalDriftBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeGoalDrift, cumulativeGoalDriftBudget]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have local :=
        (finite_learned_step_sound checker trajectory t stepBound).learnedObligations.goalDriftWithinBudget
      exact Nat.add_le_add previous local

/-- Cumulative information-regression budget. -/
def cumulativeInformationBudget
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeInformationBudget trajectory t +
        learned.informationBudget (trajectory.state t) (trajectory.candidate t)

/-- Selected information value cannot regress beyond accumulated certified budgets. -/
theorem finite_learned_information_nonregression
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      learned.informationValue (trajectory.state t) ≤
        learned.informationValue (trajectory.state 0) +
          cumulativeInformationBudget trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeInformationBudget]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previous := inductionHypothesis (Nat.le_of_lt stepBound)
      have local :=
        (finite_learned_step_sound checker trajectory t stepBound).learnedObligations.informationNonRegression
      rw [trajectory.linked t stepBound]
      calc
        learned.informationValue (trajectory.candidate t).next
            ≤ learned.informationValue (trajectory.state t) +
                learned.informationBudget
                  (trajectory.state t) (trajectory.candidate t) := local
        _ ≤ (learned.informationValue (trajectory.state 0) +
                cumulativeInformationBudget trajectory t) +
              learned.informationBudget
                (trajectory.state t) (trajectory.candidate t) :=
          add_le_add_right previous _
        _ = learned.informationValue (trajectory.state 0) +
              cumulativeInformationBudget trajectory (t + 1) := by
          simp only [cumulativeInformationBudget]
          ring

/-- Existing Gate A protected-loss theorem, inherited unchanged by Gate D. -/
theorem finite_learned_composed_nonloss_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon → ∀ distinction,
      base.protectedValue (trajectory.state 0) distinction ≤
        base.protectedValue (trajectory.state t)
            (RCP.transportedDistinction trajectory.toBaseTrajectory t distinction) +
          RCP.cumulativeLossBudget trajectory.toBaseTrajectory t :=
  RCP.finite_composed_nonloss_bound baseChecker trajectory.toBaseTrajectory

/-- Existing Gate A endpoint-recovery theorem, inherited unchanged by Gate D. -/
theorem finite_learned_endpoint_recovery_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    (laws : RCP.RecoveryCompositionLaws base)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      base.stateDistance
          (RCP.composedRecovery trajectory.toBaseTrajectory t (trajectory.state t))
          (trajectory.state 0) ≤
        RCP.cumulativeRecoveryBudget trajectory.toBaseTrajectory t :=
  RCP.finite_endpoint_recovery_bound baseChecker laws trajectory.toBaseTrajectory

/-- Existing Gate A Lyapunov/motion theorem, inherited unchanged by Gate D. -/
theorem finite_learned_lyapunov_motion_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Relevance : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    {checker : TrustedLearnedChecker learned baseChecker}
    (monitors : RCP.PreservationMonitors base (Relevance := Relevance))
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      monitors.lyapunovValue (trajectory.state t) +
          RCP.cumulativeMotionCharge monitors trajectory.toBaseTrajectory t ≤
        monitors.lyapunovValue (trajectory.state 0) +
          RCP.cumulativeLyapunovError monitors trajectory.toBaseTrajectory t :=
  RCP.finite_lyapunov_motion_bound baseChecker monitors trajectory.toBaseTrajectory

/-- Every accepted learned step retains the inherited trust proposition. -/
theorem finite_learned_trust_valid
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {horizon : Nat}
    (trajectory : FiniteLearnedTrajectory checker horizon)
    (t : Nat)
    (bound : t < horizon) :
    base.trustValid
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t).base :=
  (finite_learned_step_sound checker trajectory t bound).baseObligations.trustValid

end Learned
end RcpRclmFormalCoreV3
