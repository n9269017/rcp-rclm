import RcpRclmFormalCoreV2.RCLM.PaperIIBoundedSeedLibrary
import RcpRclmFormalCoreV2.RCLM.ClassicalBinaryPaperII

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace ClassicalBinary

open RCP
open RCP.ClassicalFinite

inductive BoundedPacketWord where
  | improve
  | stabilize
  | rejected
  deriving DecidableEq

def boundedSeedDomain (state : ClassicalState) : Prop :=
  state = initialState ∨ state = targetState

def boundedSeedWitnesses (_state : ClassicalState) : Finset EngineWitness :=
  { .strictImprovement, .stableContinuation }

def boundedPacketGrammar (state : ClassicalState) : Finset BoundedPacketWord :=
  if state = initialState then { .improve } else { .stabilize }

def boundedWordDepth : BoundedPacketWord → Nat
  | .improve => 1
  | .stabilize => 1
  | .rejected => 0

def boundedProofLength : BoundedPacketWord → Nat
  | .improve => 1
  | .stabilize => 1
  | .rejected => 0

def boundedWitnessOf : BoundedPacketWord → EngineWitness
  | .improve => .strictImprovement
  | .stabilize => .stableContinuation
  | .rejected => .rejected

def boundedProposalOf : BoundedPacketWord → EngineProposal
  | .improve => .improve
  | .stabilize => .stabilize
  | .rejected => .rejected

def boundedCertificateOf : BoundedPacketWord → ClassicalCertificate
  | .improve => improvementCertificate
  | .stabilize => stabilityCertificate
  | .rejected => malformedCertificate

def boundedCandidateOf
    (_state : ClassicalState) : BoundedPacketWord →
    Candidate ClassicalState ClassicalUpdate
  | .improve => improvementCandidate
  | .stabilize => stabilityCandidate
  | .rejected => invalidCandidate

def boundedResourceOf
    (_state : ClassicalState) : BoundedPacketWord → EngineResourceRecord
  | .improve => improvementResource
  | .stabilize => stabilityResource
  | .rejected => stabilityResource

theorem targetState_ne_initialState : targetState ≠ initialState := by
  decide

theorem boundedPacketGrammar_cases
    {state : ClassicalState}
    {word : BoundedPacketWord}
    (seedDomain : boundedSeedDomain state)
    (wordInGrammar : word ∈ boundedPacketGrammar state) :
    (state = initialState ∧ word = .improve) ∨
      (state = targetState ∧ word = .stabilize) := by
  rcases seedDomain with stateEq | stateEq
  · subst state
    have wordEq : word = .improve := by
      simpa [boundedPacketGrammar] using wordInGrammar
    exact Or.inl ⟨rfl, wordEq⟩
  · subst state
    have wordEq : word = .stabilize := by
      simpa [boundedPacketGrammar, targetState_ne_initialState] using wordInGrammar
    exact Or.inr ⟨rfl, wordEq⟩

noncomputable def boundedSeedLibrary :
    PaperIIBoundedSeedLibrary
      (Word := BoundedPacketWord)
      architectureEngine where
  seedDomain := boundedSeedDomain
  witnesses := boundedSeedWitnesses
  grammar := boundedPacketGrammar
  wordDepth := boundedWordDepth
  proofLength := boundedProofLength
  maxWordDepth := 1
  maxProofLength := 1
  witnessOf := boundedWitnessOf
  proposalOf := boundedProposalOf
  certificateOf := boundedCertificateOf
  candidateOf := boundedCandidateOf
  resourceOf := boundedResourceOf
  seedDomain_to_engineDomain := by
    intro state seedDomain
    rcases seedDomain with stateEq | stateEq
    · subst state
      exact ⟨rfl, by decide⟩
    · subst state
      exact ⟨rfl, by decide⟩
  grammarNonempty := by
    intro state seedDomain
    rcases seedDomain with stateEq | stateEq
    · subst state
      exact ⟨.improve, by simp [boundedPacketGrammar]⟩
    · subst state
      exact
        ⟨.stabilize,
          by simp [boundedPacketGrammar, targetState_ne_initialState]⟩
  wordWitnessMember := by
    intro state word wordInGrammar
    cases word with
    | improve =>
        simp [boundedWitnessOf, boundedSeedWitnesses]
    | stabilize =>
        simp [boundedWitnessOf, boundedSeedWitnesses]
    | rejected =>
        by_cases stateEq : state = initialState
        · simp [boundedPacketGrammar, stateEq] at wordInGrammar
        · simp [boundedPacketGrammar, stateEq] at wordInGrammar
  witnessMemberCovered := by
    intro state witness witnessInLibrary
    cases witness with
    | strictImprovement =>
        exact True.intro
    | stableContinuation =>
        exact True.intro
    | rejected =>
        simp [boundedSeedWitnesses] at witnessInLibrary
  wordDepthBound := by
    intro state word wordInGrammar
    cases word <;> norm_num [boundedWordDepth]
  proofLengthBound := by
    intro state word wordInGrammar
    cases word <;> norm_num [boundedProofLength]
  proposalGenerated := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inl ⟨rfl, rfl, rfl⟩
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inr ⟨rfl, rfl, rfl⟩
  certificateConstructed := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inl ⟨rfl, rfl⟩
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inr ⟨rfl, rfl⟩
  candidateSelected := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inl ⟨rfl, rfl⟩
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inr ⟨rfl, rfl⟩
  successorRealized := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact ⟨rfl, rfl⟩
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact ⟨rfl, rfl⟩
  resourceAuthorized := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      change
        initialState.resources.used ≤ initialState.resources.limit ∧
          improvementResource.used ≤ improvementResource.limit
      norm_num [initialState, canonicalState, improvementResource]
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      change
        targetState.resources.used ≤ targetState.resources.limit ∧
          stabilityResource.used ≤ stabilityResource.limit
      norm_num [targetState, canonicalState, stabilityResource]
  checkerAccepted := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact improvement_check_accepts
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact stability_check_accepts
  successorSeedDomain := by
    intro state word seedDomain wordInGrammar
    rcases boundedPacketGrammar_cases seedDomain wordInGrammar with
      improvementCase | stabilityCase
    · rcases improvementCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inr rfl
    · rcases stabilityCase with ⟨stateEq, wordEq⟩
      subst state
      subst word
      exact Or.inr rfl

def boundedDeclaredVerifierSchema
    (_state : ClassicalState) : VerifierRegister :=
  .trustedBinaryChecker

def boundedDeclaredTransportVerifierSchema
    (_state : ClassicalState)
    (_candidate : Candidate ClassicalState ClassicalUpdate)
    (schema : VerifierRegister) : VerifierRegister :=
  schema

def boundedDeclaredVerifierSchemaRefines
    (first second : VerifierRegister) : Prop :=
  first = second

def boundedDeclaredUncertaintyEnvelope
    (_state : ClassicalState) : RealityEvidence :=
  .contained

def boundedDeclaredTransportUncertaintyEnvelope
    (_state : ClassicalState)
    (_candidate : Candidate ClassicalState ClassicalUpdate)
    (envelope : RealityEvidence) : RealityEvidence :=
  envelope

def boundedDeclaredUncertaintyEnvelopeRefines
    (first second : RealityEvidence) : Prop :=
  first = second

def boundedDeclaredGoal
    (_state : ClassicalState) : WorldReferenceRegister :=
  .biasedTarget

def boundedDeclaredTransportGoal
    (_state : ClassicalState)
    (_candidate : Candidate ClassicalState ClassicalUpdate)
    (goal : WorldReferenceRegister) : WorldReferenceRegister :=
  goal

def boundedDeclaredGoalDistance :
    WorldReferenceRegister → WorldReferenceRegister → ℝ :=
  paperIIGoalDistance

def boundedDeclaredGoalDriftBudget
    (_state : ClassicalState)
    (_candidate : Candidate ClassicalState ClassicalUpdate)
    (_certificate : ClassicalCertificate) : ℝ :=
  0

noncomputable def boundedSeedSemanticIdentification :
    PaperIISeedSemanticIdentification
      paperIISuccessorSemantics
      paperIIUncertaintySemantics where
  declaredVerifierSchema := boundedDeclaredVerifierSchema
  declaredTransportVerifierSchema := boundedDeclaredTransportVerifierSchema
  declaredVerifierSchemaRefines := boundedDeclaredVerifierSchemaRefines
  declaredUncertaintyEnvelope := boundedDeclaredUncertaintyEnvelope
  declaredTransportUncertaintyEnvelope :=
    boundedDeclaredTransportUncertaintyEnvelope
  declaredUncertaintyEnvelopeRefines :=
    boundedDeclaredUncertaintyEnvelopeRefines
  declaredGoal := boundedDeclaredGoal
  declaredTransportGoal := boundedDeclaredTransportGoal
  declaredGoalDistance := boundedDeclaredGoalDistance
  declaredGoalDriftBudget := boundedDeclaredGoalDriftBudget
  verifierSchemaIdentified := by
    intro state
    rfl
  verifierTransportIdentified := by
    intro state candidate schema
    rfl
  verifierRefinementIdentified := by
    intro first second
    rfl
  uncertaintyEnvelopeIdentified := by
    intro state
    rfl
  uncertaintyTransportIdentified := by
    intro state candidate envelope
    rfl
  uncertaintyRefinementIdentified := by
    intro first second
    rfl
  goalIdentified := by
    intro state
    rfl
  goalTransportIdentified := by
    intro state candidate goal
    rfl
  goalDistanceIdentified := by
    intro first second
    rfl
  goalDriftBudgetIdentified := by
    intro state candidate certificate
    rfl

def boundedPaperIIDomainSemantics :
    PaperIIDomainSemantics architectureEngine where
  directEngineDomain := engineDomain
  seedLibraryDomain := boundedSeedDomain
  successorVerificationDomain := engineDomain
  directEngineDomain_to_architectureDomain := by
    intro state stateDomain
    exact stateDomain
  seedLibraryDomain_to_directEngineDomain := by
    intro state seedDomain
    exact boundedSeedLibrary.seedDomain_to_engineDomain seedDomain
  seedLibraryDomain_to_successorVerificationDomain := by
    intro state seedDomain
    exact boundedSeedLibrary.seedDomain_to_engineDomain seedDomain
  architectureDomain_to_successorVerificationDomain := by
    intro state stateDomain
    exact stateDomain

def initialBoundedSeedPacket :
    PaperIIBoundedSeedPacket boundedSeedLibrary initialState where
  word := .improve
  seedDomain := Or.inl rfl
  wordInGrammar := by
    change BoundedPacketWord.improve ∈ boundedPacketGrammar initialState
    simp [boundedPacketGrammar]

def targetBoundedSeedPacket :
    PaperIIBoundedSeedPacket boundedSeedLibrary targetState where
  word := .stabilize
  seedDomain := Or.inr rfl
  wordInGrammar := by
    change BoundedPacketWord.stabilize ∈ boundedPacketGrammar targetState
    simp [boundedPacketGrammar, targetState_ne_initialState]

noncomputable def initialBoundedStrictStep :
    StrictArchitectureEngineStep architectureEngine initialState where
  step := initialBoundedSeedPacket.toEngineStep
  strictWitness := by
    change ImprovementPacket
      BinaryState.initial
      RCP.ClassicalFinite.improvementCandidate
      BinaryCertificate.improvement
    exact ⟨rfl, rfl, rfl, rfl⟩

theorem engineDomain_to_boundedSeedDomain
    {state : ClassicalState}
    (stateDomain : engineDomain state) :
    boundedSeedDomain state := by
  rcases stateDomain with ⟨stateCanonical, stateNotOutside⟩
  cases coreEq : state.core with
  | outside =>
      exact False.elim (stateNotOutside coreEq)
  | initial =>
      have stateEq : state = initialState := by
        calc
          state = canonicalState state.core := stateCanonical
          _ = canonicalState .initial := by rw [coreEq]
          _ = initialState := rfl
      exact Or.inl stateEq
  | target =>
      have stateEq : state = targetState := by
        calc
          state = canonicalState state.core := stateCanonical
          _ = canonicalState .target := by rw [coreEq]
          _ = targetState := rfl
      exact Or.inr stateEq

theorem boundedSeedPacketAvailableForArchitecture
    (predecessor : ArchitecturePredecessor architectureEngine) :
    Nonempty
      (PaperIIBoundedSeedPacket boundedSeedLibrary predecessor.state) := by
  have seedDomain : boundedSeedDomain predecessor.state :=
    engineDomain_to_boundedSeedDomain predecessor.domainValid
  exact paper_ii_bounded_seed_packet_available boundedSeedLibrary seedDomain

theorem initial_bounded_seed_packet_builder_refinement :
    ArchitectureSuccessorResult
        architectureEngine
        kernelRefinement
        binaryChecker
        preservationMonitors
        binaryPreservationMonitors
        initialArchitecturePredecessor
        initialBoundedSeedPacket.toEngineStep ∧
      PaperIIBoundedSeedSuccessorResult
        boundedSeedSemanticIdentification
        boundedSeedLibrary
        initialArchitecturePredecessor
        initialBoundedSeedPacket := by
  exact paper_ii_bounded_seed_packet_refines_architecture
    checker
    binaryChecker
    architectureEngine
    paperIISuccessorSemantics
    paperIIUncertaintySemantics
    boundedSeedSemanticIdentification
    boundedSeedLibrary
    kernelRefinement
    checkerRefinement
    recoveryCompositionLaws
    preservationMonitors
    binaryPreservationMonitors
    monitorRefinement
    initialArchitecturePredecessor
    initialBoundedSeedPacket

theorem initial_bounded_seed_direct_engine_refinement :
    ArchitectureSuccessorResult
        architectureEngine
        kernelRefinement
        binaryChecker
        preservationMonitors
        binaryPreservationMonitors
        initialArchitecturePredecessor
        initialBoundedStrictStep.step ∧
      PaperIIDirectEngineObligations
        paperIIDirectSemantics
        initialArchitecturePredecessor.state
        initialBoundedStrictStep.step.candidate
        initialBoundedStrictStep.step.certificate := by
  exact rclm_constructive_direct_nl_rsi_engine_aligned
    checker
    binaryChecker
    architectureEngine
    paperIIDirectSemantics
    kernelRefinement
    checkerRefinement
    recoveryCompositionLaws
    preservationMonitors
    binaryPreservationMonitors
    monitorRefinement
    initialArchitecturePredecessor
    initialBoundedStrictStep

theorem classical_bounded_seed_packet_builder_refinement
    (predecessor : ArchitecturePredecessor architectureEngine)
    (seedDomain : boundedSeedDomain predecessor.state) :
    ∃ packet : PaperIIBoundedSeedPacket boundedSeedLibrary predecessor.state,
      PaperIIBoundedSeedSuccessorResult
        boundedSeedSemanticIdentification
        boundedSeedLibrary
        predecessor
        packet := by
  rcases paper_ii_bounded_seed_packet_available
      boundedSeedLibrary seedDomain with ⟨packet⟩
  have result :
      PaperIIBoundedSeedSuccessorResult
        boundedSeedSemanticIdentification
        boundedSeedLibrary
        predecessor
        packet :=
    paper_ii_bounded_seed_packet_builder_sound
      paperIISuccessorSemantics
      paperIIUncertaintySemantics
      boundedSeedSemanticIdentification
      boundedSeedLibrary
      predecessor
      packet
  exact ⟨packet, result⟩

end ClassicalBinary
end RCLM
end RcpRclmFormalCoreV2
