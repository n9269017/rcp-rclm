import RcpRclmFormalCoreV3.Learned.Kernel

namespace RcpRclmFormalCoreV3
namespace Learned

open RcpRclmFormalCoreV2

/-- Phase 9 name for the finite Gate D capability frontier. -/
abbrev CapabilityFrontier (Task : Type*) := Finset Task

/--
Phase 9 executable-contract name for the complete learned package state.  This is an
abbreviation of the already proved Gate D package-state object, not a second state model.
-/
abbrev LearnedRCLMState
    (BaseState ModelArchitecture ModelWeights Generator Planner TrainingPolicy
      RetrievalPolicy Memory Tokenizer VerificationPolicy ResourcePolicy SelfModel
      Task : Type*)
    [DecidableEq Task] :=
  PackageState BaseState ModelArchitecture ModelWeights Generator Planner TrainingPolicy
    RetrievalPolicy Memory Tokenizer VerificationPolicy ResourcePolicy SelfModel Task

/-- Phase 9 executable-contract name for typed learned package updates. -/
abbrev LearnedRCLMUpdate
    (BaseUpdate WeightUpdate ArchitectureUpdate GeneratorUpdate PlannerUpdate
      TrainingPolicyUpdate RetrievalUpdate MemoryUpdate TokenizerUpdate
      SelfModelUpdate : Type*) :=
  PackageUpdate BaseUpdate WeightUpdate ArchitectureUpdate GeneratorUpdate PlannerUpdate
    TrainingPolicyUpdate RetrievalUpdate MemoryUpdate TokenizerUpdate SelfModelUpdate

/-- Phase 9 executable-contract name for learned certificate packets. -/
abbrev LearnedCertificatePacket
    (BaseCertificate Task Generator Proposal PackageHash : Type*)
    [DecidableEq Task] :=
  CertificatePacket BaseCertificate Task Generator Proposal PackageHash

/-- A task paired with an actual proof of the selected solve relation. -/
structure CertifiedTask
    (State Task : Type*)
    (solves : State → Task → Prop) where
  state : State
  task : Task
  certified : solves state task

/-- Complete predecessor-frontier retention across a candidate transition. -/
def FrontierRetention
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : State)
    (candidate : RCP.Candidate State Update) : Prop :=
  learned.frontier state ⊆ learned.frontier candidate.next

/-- Phase 9 name for strict finite frontier expansion. -/
abbrev FrontierExpansion
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : State)
    (candidate : RCP.Candidate State Update) :=
  StrictFrontierExpansion learned state candidate

/--
The exact self-hosted generator binding frozen by Phase 9.  The generator and package
names in a certificate are accepted only when they are the active predecessor bindings,
the proposal was produced by that generator, and the proposal binds the actual candidate.
-/
def SelfHostedGenerator
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
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash) : Prop :=
  certificate.generator = learned.activeGenerator state ∧
    learned.generatorBound state certificate.generator ∧
    learned.proposalProducedBy certificate.generator state certificate.proposal ∧
    learned.proposalBindsCandidate state certificate.proposal candidate ∧
    certificate.generatorPackageHash = learned.activePackageHash state ∧
    learned.packageHashBound state certificate.generator certificate.generatorPackageHash

/-- Phase 9 correspondence name for the learned kernel refinement. -/
abbrev LearnedKernelRefinement
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    (base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex) :=
  FrontierKernel
    (Task := Task) (Generator := Generator) (Proposal := Proposal)
    (PackageHash := PackageHash) base

/-- Phase 9 correspondence name for learned checker refinement. -/
abbrev LearnedCheckerRefinement
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : LearnedKernelRefinement
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (baseChecker : RCP.TrustedChecker base) :=
  TrustedLearnedChecker learned baseChecker

/-- Every frontier member yields a certified-task object. -/
def certifiedTaskOfFrontierMember
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
    CertifiedTask State Task learned.solves :=
  { state := state
    task := task
    certified := learned.frontierSound member }

/-- Accepted Gate D steps retain the complete predecessor frontier. -/
theorem learned_accepted_step_frontier_retention
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate :
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash}
    (accepted : LearnedAcceptedStep learned state candidate certificate) :
    FrontierRetention learned state candidate :=
  accepted.learnedObligations.strictFrontierExpansion.1

/-- Accepted Gate D steps strictly expand the frontier. -/
theorem learned_accepted_step_frontier_expansion
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate :
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash}
    (accepted : LearnedAcceptedStep learned state candidate certificate) :
    FrontierExpansion learned state candidate :=
  accepted.learnedObligations.strictFrontierExpansion

/-- Accepted Gate D steps satisfy the complete active-generator and package binding. -/
theorem learned_accepted_step_self_hosted_generator
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate :
      CertificatePacket BaseCertificate Task Generator Proposal PackageHash}
    (accepted : LearnedAcceptedStep learned state candidate certificate) :
    SelfHostedGenerator learned state candidate certificate := by
  exact
    ⟨accepted.learnedObligations.generatorIsActive,
      accepted.learnedObligations.generatorBound,
      accepted.learnedObligations.proposalProduced,
      accepted.learnedObligations.proposalBindsCandidate,
      accepted.learnedObligations.packageHashIsActive,
      accepted.learnedObligations.packageHashBound⟩

end Learned
end RcpRclmFormalCoreV3
