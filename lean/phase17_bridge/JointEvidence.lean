/- This template is appended after the pinned, regenerated typed/task/provenance
   source bodies. It does not import a historical successful result as evidence.
   All remaining base, goal, resource and information premises stay explicit. -/
namespace Phase17Joint

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/-- One kernel receives both adapters, rather than two unrelated kernels. -/
def compose
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView) :=
  Phase17Provenance.attachProvenance
    (Phase17TaskMeaning.attachTaskSemantics other observeTasks declared catalog)
    context candidateView

theorem composed_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    {s : State} {task : Nat}
    (member : task ∈ (compose other observeTasks declared catalog context candidateView).frontier s) :
    (catalog task).holds (observeTasks s) :=
  (compose other observeTasks declared catalog context candidateView).frontierSound member

theorem composed_provenance_bound
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (p : Phase17Provenance.Proposal)
    (valid : Phase17Provenance.ContextValid (context s))
    (produced : Phase17Provenance.Produced (context s) p) :
    (compose other observeTasks declared catalog context candidateView).generatorBound s (context s).generator ∧
    (compose other observeTasks declared catalog context candidateView).proposalProducedBy
      (context s).generator s p :=
  ⟨⟨rfl, valid⟩, ⟨rfl, produced⟩⟩

/-- Composition does not replace open semantic/resource fields with constants. -/
theorem remaining_semantics_unchanged
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView) :
    (compose other observeTasks declared catalog context candidateView).goalDrift = other.goalDrift ∧
    (compose other observeTasks declared catalog context candidateView).goalDriftBudget = other.goalDriftBudget ∧
    (compose other observeTasks declared catalog context candidateView).resourceUsed = other.resourceUsed ∧
    (compose other observeTasks declared catalog context candidateView).resourceBudget = other.resourceBudget ∧
    (compose other observeTasks declared catalog context candidateView).informationValue = other.informationValue ∧
    (compose other observeTasks declared catalog context candidateView).informationBudget = other.informationBudget :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩

def certificate
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (p : Phase17Provenance.Proposal) (baseCertificate : BaseCertificate) :
    Learned.CertificatePacket BaseCertificate Nat String Phase17Provenance.Proposal String :=
  { base := baseCertificate
    protectedFrontier := (compose other observeTasks declared catalog context candidateView).frontier s
    generator := (context s).generator
    proposal := p
    generatorPackageHash := (context s).parentPackage }

/-- Actual LearnedAcceptedStep constructor, CONDITIONAL on all remaining premises.
    It is not instantiated for a physical transition by this development gate. -/
theorem assemble_learned_step
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (candidate : RCP.Candidate State Update)
    (p : Phase17Provenance.Proposal) (baseCertificate : BaseCertificate)
    (valid : Phase17Provenance.ContextValid (context s))
    (produced : Phase17Provenance.Produced (context s) p)
    (matched : Phase17Provenance.CandidateMatches (context s) p (candidateView candidate))
    (expansion : Learned.StrictFrontierExpansion
      (compose other observeTasks declared catalog context candidateView) s candidate)
    (baseProof : RCP.StepObligations base s candidate baseCertificate)
    (goal : other.goalDrift s candidate ≤ other.goalDriftBudget s candidate)
    (resources : other.resourceUsed s candidate ≤ other.resourceBudget s candidate)
    (information : other.informationValue candidate.next ≤
      other.informationValue s + other.informationBudget s candidate) :
    Learned.LearnedAcceptedStep
      (compose other observeTasks declared catalog context candidateView) s candidate
      (certificate other observeTasks declared catalog context candidateView s p baseCertificate) := by
  exact {
    baseObligations := baseProof
    learnedObligations := {
      protectedFrontierCertified := by intro task h; exact h
      protectedFrontierRetained := expansion.1
      strictFrontierExpansion := expansion
      generatorIsActive := rfl
      generatorBound := ⟨rfl, valid⟩
      proposalProduced := ⟨rfl, produced⟩
      proposalBindsCandidate := matched
      packageHashIsActive := rfl
      packageHashBound := ⟨rfl, rfl, valid⟩
      goalDriftWithinBudget := goal
      resourceWithinBudget := resources
      informationNonRegression := information } }

structure Binding where
  historicalState : String
  predecessor : String
  candidate : String
  transcript : String
  program : String
  objective : String
  challenge : String
  deriving DecidableEq

end Phase17Joint
