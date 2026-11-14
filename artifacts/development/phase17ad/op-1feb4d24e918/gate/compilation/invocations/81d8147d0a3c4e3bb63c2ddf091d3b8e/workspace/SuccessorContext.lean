import ControllerContinuation
import FiniteObservationKernel

/-
Phase 17AD: one finite-observation kernel with state-indexed transaction context.

The immutable root, task catalog/name interpretation, protected contract and
resource policy are inherited from Q. Only the current source state's producer
context and expected charge sequence vary. Providers are mathematical inputs:
they neither authenticate their own values nor establish physical execution,
fresh hidden challenges, a next accepted candidate, or autonomous acceptance.

The transport theorem constructs the actual immutable-root LearnedAcceptedStep
for a SINGLE kernel at every source state for which the existing finite Facts
are supplied. The two-step theorem requires separate facts at both linked states;
it does not infer the existence of a second successful search.
-/
namespace Phase17SuccessorContext

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

abbrev State := Phase17Finite.State
abbrev Update := Phase17Finite.Update
abbrev Evidence := Phase17Finite.Evidence
abbrev Contexts := State → Phase17Provenance.Context
abbrev Charges := State → List Phase17Resource.Kind
abbrev Candidate := RCP.Candidate State Update

def configurationAt (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) : Phase17Finite.Configuration :=
  { fixed with context := contexts s, expectedCharges := charges s }

theorem configuration_semantics_fixed (fixed : Phase17Finite.Configuration)
    (contexts : Contexts) (charges : Charges) (s : State) :
    (configurationAt fixed contexts charges s).root = fixed.root ∧
    (configurationAt fixed contexts charges s).catalog = fixed.catalog ∧
    (configurationAt fixed contexts charges s).taskName = fixed.taskName ∧
    (configurationAt fixed contexts charges s).contract = fixed.contract ∧
    (configurationAt fixed contexts charges s).policy = fixed.policy :=
  ⟨rfl, rfl, rfl, rfl, rfl⟩

private def rejectedState : State :=
  ⟨[], [], [], [], ∅, ∅, ⟨[], [], []⟩, "", ""⟩

private def rejectedUpdate : Update :=
  ⟨"", ⟨0, 0, 0, 0⟩, 0, "", "", "", "", []⟩

private def rejectedEvidence : Evidence :=
  ⟨"", "", "", "", "", ⟨"", "", "", "", [], [], "", ""⟩, []⟩

/-- The existing nonconstant protected quantity, nonconstant residual and all
    fixed semantic fields are preserved. The new structural predicate remains
    non-universal for every provider, because an empty update key is rejected. -/
noncomputable def base (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) :
    RCP.Kernel State Update Evidence Phase17Finite.Protected Phase17Finite.ResidualIndex :=
  { Phase17Finite.base fixed with
    trustValid := fun s c e =>
      Phase17Finite.trustValid (configurationAt fixed contexts charges s) s c e
    resourceValid := fun s c e =>
      Phase17Finite.resourceValid (configurationAt fixed contexts charges s) c e
    realityContained := fun s c e =>
      Phase17Finite.realityContained (configurationAt fixed contexts charges s) s c e
    realityContained_not_universal := by
      refine ⟨rejectedState, ⟨rejectedUpdate, rejectedState⟩, rejectedEvidence, ?_⟩
      intro h
      have invalid := h.2.1.2.2.1
      exact invalid rfl }

/-- This is an actual FrontierKernel over the new base, not a second per-step
    kernel or an unspecified compatible semantic-kernel parameter. -/
noncomputable def learned (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) :
    Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String)
      (base fixed contexts charges) where
  frontier := (Phase17Finite.learned fixed).frontier
  solves := (Phase17Finite.learned fixed).solves
  frontierSound := (Phase17Finite.learned fixed).frontierSound
  activeGenerator := fun s => (contexts s).generator
  activePackageHash := (Phase17Finite.learned fixed).activePackageHash
  generatorBound := fun s g => g = (contexts s).generator ∧
    (contexts s).parentPackage = s.packageHash ∧ Phase17Provenance.ContextValid (contexts s)
  proposalProducedBy := fun g s p => g = (contexts s).generator ∧
    (contexts s).parentPackage = s.packageHash ∧ Phase17Provenance.Produced (contexts s) p
  proposalBindsCandidate := fun s p c => (contexts s).parentPackage = s.packageHash ∧
    Phase17Provenance.CandidateMatches (contexts s) p (Phase17Finite.candidateView c)
  packageHashBound := fun s g hash => g = (contexts s).generator ∧ hash = s.packageHash ∧
    (contexts s).parentPackage = s.packageHash ∧ Phase17Provenance.ContextValid (contexts s)
  goalDrift := (Phase17Finite.learned fixed).goalDrift
  goalDriftBudget := (Phase17Finite.learned fixed).goalDriftBudget
  resourceUsed := (Phase17Finite.learned fixed).resourceUsed
  resourceBudget := (Phase17Finite.learned fixed).resourceBudget
  informationValue := (Phase17Finite.learned fixed).informationValue
  informationBudget := (Phase17Finite.learned fixed).informationBudget
  informationBudget_nonnegative := (Phase17Finite.learned fixed).informationBudget_nonnegative

def packet (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (e : Evidence) :
    Learned.CertificatePacket Evidence Nat String Phase17Provenance.Proposal String :=
  Phase17Finite.packet (configurationAt fixed contexts charges s) s e

theorem base_semantics_fixed (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) :
    (base fixed contexts charges).apply = (Phase17Finite.base fixed).apply ∧
    (base fixed contexts charges).admissible = (Phase17Finite.base fixed).admissible ∧
    (base fixed contexts charges).protectedInvariant = (Phase17Finite.base fixed).protectedInvariant ∧
    (base fixed contexts charges).protectedValue = (Phase17Finite.base fixed).protectedValue ∧
    (base fixed contexts charges).transportProtected = (Phase17Finite.base fixed).transportProtected ∧
    (base fixed contexts charges).lossBudget = (Phase17Finite.base fixed).lossBudget ∧
    (base fixed contexts charges).stateDistance = (Phase17Finite.base fixed).stateDistance ∧
    (base fixed contexts charges).recover = (Phase17Finite.base fixed).recover ∧
    (base fixed contexts charges).recoveryBudget = (Phase17Finite.base fixed).recoveryBudget ∧
    (base fixed contexts charges).progress = (Phase17Finite.base fixed).progress ∧
    (base fixed contexts charges).strictWitness = (Phase17Finite.base fixed).strictWitness ∧
    (base fixed contexts charges).residual = (Phase17Finite.base fixed).residual :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

theorem learned_semantics_fixed (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) :
    (learned fixed contexts charges).frontier = (Phase17Finite.learned fixed).frontier ∧
    (learned fixed contexts charges).solves = (Phase17Finite.learned fixed).solves ∧
    (learned fixed contexts charges).activePackageHash = (Phase17Finite.learned fixed).activePackageHash ∧
    (learned fixed contexts charges).goalDrift = (Phase17Finite.learned fixed).goalDrift ∧
    (learned fixed contexts charges).goalDriftBudget = (Phase17Finite.learned fixed).goalDriftBudget ∧
    (learned fixed contexts charges).resourceUsed = (Phase17Finite.learned fixed).resourceUsed ∧
    (learned fixed contexts charges).resourceBudget = (Phase17Finite.learned fixed).resourceBudget ∧
    (learned fixed contexts charges).informationValue = (Phase17Finite.learned fixed).informationValue ∧
    (learned fixed contexts charges).informationBudget = (Phase17Finite.learned fixed).informationBudget :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

theorem packet_uses_source_context (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (e : Evidence) :
    (packet fixed contexts charges s e).generator = (contexts s).generator ∧
    (packet fixed contexts charges s e).generatorPackageHash = s.packageHash ∧
    (packet fixed contexts charges s e).protectedFrontier =
      (learned fixed contexts charges).frontier s ∧
    (packet fixed contexts charges s e).proposal = e.proposal ∧
    (packet fixed contexts charges s e).base = e :=
  ⟨rfl, rfl, rfl, rfl, rfl⟩

/-- At a specified source state the dynamic base has exactly Q's original
    eleven obligations with that source's context and charge list. -/
theorem base_obligations_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence) :
    RCP.StepObligations (base fixed contexts charges) s c e ↔
      RCP.StepObligations (Phase17Finite.base (configurationAt fixed contexts charges s)) s c e := by
  constructor <;> intro h <;>
    exact {
      typedSuccessor := h.typedSuccessor
      residualsNonpositive := h.residualsNonpositive
      protectedNonLoss := h.protectedNonLoss
      constructiveRecovery := h.constructiveRecovery
      invariantPreserved := h.invariantPreserved
      progressNondecreasing := h.progressNondecreasing
      strictProgressWhenWitness := h.strictProgressWhenWitness
      trustValid := h.trustValid
      resourceValid := h.resourceValid
      realityContained := h.realityContained
      successorAdmissible := h.successorAdmissible }

theorem learned_obligations_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence) :
    Learned.SpecificObligations (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) ↔
      Learned.SpecificObligations (Phase17Finite.learned (configurationAt fixed contexts charges s))
        s c (Phase17Finite.packet (configurationAt fixed contexts charges s) s e) := by
  constructor <;> intro h <;>
    exact {
      protectedFrontierCertified := h.protectedFrontierCertified
      protectedFrontierRetained := h.protectedFrontierRetained
      strictFrontierExpansion := h.strictFrontierExpansion
      generatorIsActive := h.generatorIsActive
      generatorBound := h.generatorBound
      proposalProduced := h.proposalProduced
      proposalBindsCandidate := h.proposalBindsCandidate
      packageHashIsActive := h.packageHashIsActive
      packageHashBound := h.packageHashBound
      goalDriftWithinBudget := h.goalDriftWithinBudget
      resourceWithinBudget := h.resourceWithinBudget
      informationNonRegression := h.informationNonRegression }

theorem accepted_iff_local (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence) :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) ↔
      Learned.LearnedAcceptedStep (Phase17Finite.learned (configurationAt fixed contexts charges s))
        s c (Phase17Finite.packet (configurationAt fixed contexts charges s) s e) := by
  constructor
  · intro h
    exact {
      baseObligations := (base_obligations_iff fixed contexts charges s c e).mp h.baseObligations
      learnedObligations := (learned_obligations_iff fixed contexts charges s c e).mp h.learnedObligations }
  · intro h
    exact {
      baseObligations := (base_obligations_iff fixed contexts charges s c e).mpr h.baseObligations
      learnedObligations := (learned_obligations_iff fixed contexts charges s c e).mpr h.learnedObligations }

/-- The actual immutable-root accepted-step type for the declared finite model,
    conditional on Q's
    independently checkable Facts for this source state. Provider validity is
    not assumed globally and no future accepted step is manufactured. -/
theorem accepted (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (facts : Phase17Finite.Facts (configurationAt fixed contexts charges s) s c e) :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) :=
  (accepted_iff_local fixed contexts charges s c e).mpr
    (Phase17Finite.accepted (configurationAt fixed contexts charges s) s c e facts)

theorem facts_require_parent (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (facts : Phase17Finite.Facts (configurationAt fixed contexts charges s) s c e) :
    (contexts s).parentPackage = s.packageHash := by
  rcases facts.trusted with ⟨_, _, _, _, _, _, _, _, parent, _⟩
  exact parent

theorem accepted_requires_parent (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (h : Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e)) :
    (contexts s).parentPackage = s.packageHash :=
  h.learnedObligations.generatorBound.2.1

theorem accepted_context_valid (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (h : Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e)) :
    Phase17Provenance.ContextValid (contexts s) :=
  h.learnedObligations.generatorBound.2.2

theorem accepted_source_charges (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (h : Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e)) :
    e.charges = c.update.charges ∧ e.charges = charges s ∧
      Phase17Resource.Fits fixed.policy e.charges :=
  h.baseObligations.resourceValid

theorem stale_parent_rejected (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (stale : (contexts s).parentPackage ≠ s.packageHash) :
    ¬ Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) := by
  intro h
  exact stale (accepted_requires_parent fixed contexts charges s c e h)

theorem facts_change_package (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (facts : Phase17Finite.Facts (configurationAt fixed contexts charges s) s c e) :
    c.next.packageHash ≠ s.packageHash := by
  rcases facts.updateValid with ⟨_, _, _, _, _, _, _, _, changed, _⟩
  simpa only [facts.typed, Phase17Finite.apply] using changed

/-- A successful first finite transition cannot reuse its exact old context as
    a generator-bound context for the successor. Fresh means newly parent-bound
    here; it does not mean challenge entropy or an authenticated physical event. -/
theorem successor_context_must_change (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (facts : Phase17Finite.Facts (configurationAt fixed contexts charges s) s c e)
    (nextParent : (contexts c.next).parentPackage = c.next.packageHash) :
    contexts c.next ≠ contexts s := by
  intro same
  have parent := facts_require_parent fixed contexts charges s c e facts
  have changed := facts_change_package fixed contexts charges s c e facts
  rw [same] at nextParent
  exact changed (nextParent.symm.trans parent)

theorem stale_successor_context_rejected (fixed : Phase17Finite.Configuration)
    (contexts : Contexts) (charges : Charges) (s : State) (first second : Candidate)
    (firstEvidence secondEvidence : Evidence)
    (facts : Phase17Finite.Facts (configurationAt fixed contexts charges s) s first firstEvidence)
    (stale : contexts first.next = contexts s) :
    ¬ Learned.LearnedAcceptedStep (learned fixed contexts charges) first.next second
      (packet fixed contexts charges first.next secondEvidence) := by
  intro h
  have parent := accepted_requires_parent fixed contexts charges first.next second secondEvidence h
  exact successor_context_must_change fixed contexts charges s first firstEvidence facts parent stale

theorem present_configuration_congruence (fixed : Phase17Finite.Configuration)
    (left right : Contexts) (leftCharges rightCharges : Charges) (s : State)
    (sameContext : left s = right s) (sameCharges : leftCharges s = rightCharges s) :
    configurationAt fixed left leftCharges s = configurationAt fixed right rightCharges s := by
  simp only [configurationAt, sameContext, sameCharges]

/-- Changing provider values at other states cannot alter this step's acceptance
    predicate. It can alter the ability to certify a later successor step. -/
theorem present_acceptance_congruence (fixed : Phase17Finite.Configuration)
    (left right : Contexts) (leftCharges rightCharges : Charges) (s : State)
    (c : Candidate) (e : Evidence)
    (sameContext : left s = right s) (sameCharges : leftCharges s = rightCharges s) :
    Learned.LearnedAcceptedStep (learned fixed left leftCharges) s c
        (packet fixed left leftCharges s e) ↔
      Learned.LearnedAcceptedStep (learned fixed right rightCharges) s c
        (packet fixed right rightCharges s e) := by
  rw [accepted_iff_local, accepted_iff_local,
    present_configuration_congruence fixed left right leftCharges rightCharges s sameContext sameCharges]

/-- Valid source context plus actual positive credits makes the unchanged AC
    selector available. This does not imply that any selected candidate passes. -/
theorem successor_controller_available (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (credits : Nat)
    (parent : (contexts s).parentPackage = s.packageHash)
    (valid : Phase17Provenance.ContextValid (contexts s)) (positive : 0 < credits) :
    ∃ i, Phase17Controller.decision (contexts s) (Phase17Controller.initial credits) =
        some (.evaluate i) ∧ i < 32 ∧
      (learned fixed contexts charges).generatorBound s (contexts s).generator := by
  have shape : Phase17Controller.ContextShape (contexts s) := ⟨valid.1, valid.2.2.1⟩
  obtain ⟨i, selected⟩ := Phase17Controller.credits_above_grammar_allowed
    (contexts s) shape credits positive
  have chosen := ((Phase17Controller.decision_evaluate_iff (contexts s)
    (Phase17Controller.initial credits) i).mp selected).2.2.2.2
  exact ⟨i, selected, Phase17Controller.choose_in_range (contexts s) shape _ i chosen,
    rfl, parent, valid⟩

/-- Two independently supplied linked finite facts produce two actual accepted
    steps under ONE kernel, preserve the protected view, retain the initial
    frontier, and add at least two frontier elements. Existence of either fact
    bundle, physical activation and campaign resource accounting remain outside
    this conditional theorem. -/
theorem two_step_continuation (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (first second : Candidate)
    (firstEvidence secondEvidence : Evidence)
    (firstFacts : Phase17Finite.Facts (configurationAt fixed contexts charges s) s first firstEvidence)
    (secondFacts : Phase17Finite.Facts (configurationAt fixed contexts charges first.next)
      first.next second secondEvidence) :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) s first
        (packet fixed contexts charges s firstEvidence) ∧
    Learned.LearnedAcceptedStep (learned fixed contexts charges) first.next second
        (packet fixed contexts charges first.next secondEvidence) ∧
    (learned fixed contexts charges).frontier s ⊆
        (learned fixed contexts charges).frontier second.next ∧
    ((learned fixed contexts charges).frontier s).card + 2 ≤
        ((learned fixed contexts charges).frontier second.next).card ∧
    Phase17Finite.protectedView second.next = Phase17Finite.protectedView s ∧
    contexts first.next ≠ contexts s := by
  have hfirst := accepted fixed contexts charges s first firstEvidence firstFacts
  have hsecond := accepted fixed contexts charges first.next second secondEvidence secondFacts
  have firstExpansion := hfirst.learnedObligations.strictFrontierExpansion
  have secondExpansion := hsecond.learnedObligations.strictFrontierExpansion
  refine ⟨hfirst, hsecond, fun t member => secondExpansion.1 (firstExpansion.1 member), ?_, ?_, ?_⟩
  · have one := firstExpansion.2
    have two := secondExpansion.2
    omega
  · rw [secondFacts.typed, Phase17Finite.protected_view_preserved,
      firstFacts.typed, Phase17Finite.protected_view_preserved]
  · exact successor_context_must_change fixed contexts charges s first firstEvidence firstFacts
      (facts_require_parent fixed contexts charges first.next second secondEvidence secondFacts)

end Phase17SuccessorContext
