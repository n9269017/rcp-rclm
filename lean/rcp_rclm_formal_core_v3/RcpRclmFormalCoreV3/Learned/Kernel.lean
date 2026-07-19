import Mathlib.Data.Finset.Card
import RcpRclmFormalCoreV2.RCP
import RcpRclmFormalCoreV3.Learned.Types

namespace RcpRclmFormalCoreV3
namespace Learned

open RcpRclmFormalCoreV2

/--
The learned capability-frontier refinement layered over an existing RCP/RCLM kernel.
The base kernel remains authoritative for typed successor, protected non-loss,
recovery, progress, trust, resources, reality containment, and domain closure.
Gate D adds a finite certified task frontier and explicit generator/package bindings.
-/
structure FrontierKernel
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    (base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex) where
  frontier : State → Finset Task
  solves : State → Task → Prop
  frontierSound : ∀ {state task}, task ∈ frontier state → solves state task

  activeGenerator : State → Generator
  activePackageHash : State → PackageHash
  generatorBound : State → Generator → Prop
  proposalProducedBy : Generator → State → Proposal → Prop
  proposalBindsCandidate :
    State → Proposal → RCP.Candidate State Update → Prop
  packageHashBound : State → Generator → PackageHash → Prop

  goalDrift : State → RCP.Candidate State Update → Nat
  goalDriftBudget : State → RCP.Candidate State Update → Nat
  resourceUsed : State → RCP.Candidate State Update → Nat
  resourceBudget : State → RCP.Candidate State Update → Nat

  informationValue : State → ℝ
  informationBudget : State → RCP.Candidate State Update → ℝ
  informationBudget_nonnegative : ∀ state candidate,
    0 ≤ informationBudget state candidate

/--
For finite frontiers, strict expansion is represented by inclusion together with
strict cardinal growth.  This is equivalent to proper inclusion and makes the
quantitative `|F_N| ≥ |F_0| + N` theorem direct.
-/
def StrictFrontierExpansion
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : State)
    (candidate : RCP.Candidate State Update) : Prop :=
  learned.frontier state ⊆ learned.frontier candidate.next ∧
    (learned.frontier state).card < (learned.frontier candidate.next).card

/-- Gate D obligations not already supplied by the base RCP/RCLM kernel. -/
structure SpecificObligations
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate :
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash) : Prop where
  protectedFrontierCertified :
    certificate.protectedFrontier ⊆ learned.frontier state
  protectedFrontierRetained :
    certificate.protectedFrontier ⊆ learned.frontier candidate.next
  strictFrontierExpansion : StrictFrontierExpansion learned state candidate

  generatorIsActive : certificate.generator = learned.activeGenerator state
  generatorBound : learned.generatorBound state certificate.generator
  proposalProduced :
    learned.proposalProducedBy certificate.generator state certificate.proposal
  proposalBindsCandidate :
    learned.proposalBindsCandidate state certificate.proposal candidate
  packageHashIsActive :
    certificate.generatorPackageHash = learned.activePackageHash state
  packageHashBound : learned.packageHashBound
    state certificate.generator certificate.generatorPackageHash

  goalDriftWithinBudget :
    learned.goalDrift state candidate ≤ learned.goalDriftBudget state candidate
  resourceWithinBudget :
    learned.resourceUsed state candidate ≤ learned.resourceBudget state candidate
  informationNonRegression :
    learned.informationValue candidate.next ≤
      learned.informationValue state + learned.informationBudget state candidate

/--
The complete Gate D one-step result: all inherited RCP/RCLM obligations plus the
learned capability-frontier and self-hosted generator obligations.
-/
structure LearnedAcceptedStep
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate :
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash) : Prop where
  baseObligations : RCP.StepObligations base state candidate certificate.base
  learnedObligations : SpecificObligations learned state candidate certificate

/--
A learned checker is a Boolean checker that refines an already trusted base checker.
The generator is not trusted: accepted packets must both refine base-checker
acceptance and satisfy the additional Gate D proof obligations.
-/
structure TrustedLearnedChecker
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (baseChecker : RCP.TrustedChecker base) where
  check : State → RCP.Candidate State Update →
    CertificatePacket BaseCertificate Task Generator Proposal PackageHash → Bool
  refinesBase : ∀ {state candidate certificate},
    check state candidate certificate = true →
      baseChecker.check state candidate certificate.base = true
  learnedSound : ∀ {state candidate certificate},
    base.admissible state →
    base.protectedInvariant state →
    check state candidate certificate = true →
      SpecificObligations learned state candidate certificate

/-- Gate D one-step checker soundness. -/
theorem learned_accepted_step_sound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {baseChecker : RCP.TrustedChecker base}
    (checker : TrustedLearnedChecker learned baseChecker)
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate :
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash}
    (stateAdmissible : base.admissible state)
    (stateInvariant : base.protectedInvariant state)
    (accepted : checker.check state candidate certificate = true) :
    LearnedAcceptedStep learned state candidate certificate := by
  have baseAccepted :
      baseChecker.check state candidate certificate.base = true :=
    checker.refinesBase accepted
  exact
    { baseObligations :=
        baseChecker.sound stateAdmissible stateInvariant baseAccepted
      learnedObligations :=
        checker.learnedSound stateAdmissible stateInvariant accepted }

/-- Every certified frontier member is a solved task. -/
theorem frontier_member_solved
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    {state : State}
    {task : Task}
    (member : task ∈ learned.frontier state) :
    learned.solves state task :=
  learned.frontierSound member

end Learned
end RcpRclmFormalCoreV3
