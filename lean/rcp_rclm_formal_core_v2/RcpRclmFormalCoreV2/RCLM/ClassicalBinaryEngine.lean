import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCLM.ArchitectureEngine
import RcpRclmFormalCoreV2.RCLM.ClassicalBinary

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace ClassicalBinary

open RCP
open RCP.ClassicalFinite

inductive EngineProposal where
  | improve
  | stabilize
  | rejected
  deriving DecidableEq

inductive EngineWitness where
  | strictImprovement
  | stableContinuation
  | rejected
  deriving DecidableEq

inductive EngineTrustAnchor where
  | root
  deriving DecidableEq

structure EngineResourceRecord where
  used : Nat
  limit : Nat
  deriving DecidableEq

def engineDomain (state : ClassicalState) : Prop :=
  state = canonicalState state.core ∧ state.core ≠ .outside

def engineWitnessLibrary : EngineWitness → Prop
  | .strictImprovement => True
  | .stableContinuation => True
  | .rejected => False

def engineProposes
    (state : ClassicalState)
    (witness : EngineWitness)
    (proposal : EngineProposal) : Prop :=
  (state = initialState ∧
      witness = .strictImprovement ∧
      proposal = .improve) ∨
    (state = targetState ∧
      witness = .stableContinuation ∧
      proposal = .stabilize)

def engineConstructsCertificate
    (_state : ClassicalState)
    (proposal : EngineProposal)
    (certificate : ClassicalCertificate) : Prop :=
  (proposal = .improve ∧ certificate = improvementCertificate) ∨
    (proposal = .stabilize ∧ certificate = stabilityCertificate)

def engineSelectsCandidate
    (_state : ClassicalState)
    (proposal : EngineProposal)
    (_certificate : ClassicalCertificate)
    (candidate : Candidate ClassicalState ClassicalUpdate) : Prop :=
  (proposal = .improve ∧ candidate = improvementCandidate) ∨
    (proposal = .stabilize ∧ candidate = stabilityCandidate)

def engineRealizesSuccessor
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (successor : ClassicalState) : Prop :=
  successor = apply state candidate.update ∧ candidate.next = successor

def engineTrustAnchorValid
    (state : ClassicalState)
    (anchor : EngineTrustAnchor) : Prop :=
  anchor = .root ∧ state.core ≠ .outside

def engineResourcePremise
    (state : ClassicalState)
    (_proposal : EngineProposal)
    (_certificate : ClassicalCertificate)
    (_candidate : Candidate ClassicalState ClassicalUpdate)
    (resource : EngineResourceRecord) : Prop :=
  state.resources.used ≤ state.resources.limit ∧
    resource.used ≤ resource.limit

def improvementResource : EngineResourceRecord where
  used := 1
  limit := 1

def stabilityResource : EngineResourceRecord where
  used := 0
  limit := 1

theorem stability_check_accepts :
    checker.check targetState stabilityCandidate stabilityCertificate = true := by
  rfl

theorem engine_relations_accept
    {state : ClassicalState}
    {witness : EngineWitness}
    {proposal : EngineProposal}
    {certificate : ClassicalCertificate}
    {candidate : Candidate ClassicalState ClassicalUpdate}
    (generated : engineProposes state witness proposal)
    (constructed :
      engineConstructsCertificate state proposal certificate)
    (selected :
      engineSelectsCandidate state proposal certificate candidate) :
    checker.check state candidate certificate = true := by
  rcases generated with generated | generated
  · rcases generated with ⟨stateEq, witnessEq, proposalEq⟩
    subst state
    subst witness
    subst proposal
    rcases constructed with constructed | constructed
    · rcases constructed with ⟨proposalEq, certificateEq⟩
      subst certificate
      rcases selected with selected | selected
      · rcases selected with ⟨proposalEq, candidateEq⟩
        subst candidate
        exact improvement_check_accepts
      · rcases selected with ⟨proposalContradiction, candidateEq⟩
        cases proposalContradiction
    · rcases constructed with ⟨proposalContradiction, certificateEq⟩
      cases proposalContradiction
  · rcases generated with ⟨stateEq, witnessEq, proposalEq⟩
    subst state
    subst witness
    subst proposal
    rcases constructed with constructed | constructed
    · rcases constructed with ⟨proposalContradiction, certificateEq⟩
      cases proposalContradiction
    · rcases constructed with ⟨proposalEq, certificateEq⟩
      subst certificate
      rcases selected with selected | selected
      · rcases selected with ⟨proposalContradiction, candidateEq⟩
        cases proposalContradiction
      · rcases selected with ⟨proposalEq, candidateEq⟩
        subst candidate
        exact stability_check_accepts

noncomputable def architectureEngine :
    ArchitectureEngine
      (Proposal := EngineProposal)
      (Witness := EngineWitness)
      (TrustAnchor := EngineTrustAnchor)
      (ResourceRecord := EngineResourceRecord)
      kernel checker where
  domain := engineDomain
  witnessLibrary := engineWitnessLibrary
  proposes := engineProposes
  constructsCertificate := engineConstructsCertificate
  selectsCandidate := engineSelectsCandidate
  realizesSuccessor := engineRealizesSuccessor
  trustAnchorValid := engineTrustAnchorValid
  resourcePremise := engineResourcePremise
  realizerTyped := by
    intro state witness proposal certificate candidate
      stateDomain witnessCovered generated constructed selected realized
    unfold TypedSuccessor
    exact realized.1
  trustAnchorSound := by
    intro state witness proposal certificate candidate anchor
      stateDomain witnessCovered generated constructed selected anchorValid
    have accepted : checker.check state candidate certificate = true :=
      engine_relations_accept generated constructed selected
    have stateAdmissible : kernel.admissible state :=
      ⟨stateDomain.2, stateDomain.1⟩
    have stateInvariant : kernel.protectedInvariant state :=
      ⟨stateDomain.2, stateDomain.1⟩
    have obligations := checker.sound stateAdmissible stateInvariant accepted
    exact obligations.trustValid
  resourcePremiseSound := by
    intro state proposal certificate candidate resource
      stateDomain constructed selected resourceAuthorized
    rcases constructed with constructed | constructed
    · rcases constructed with ⟨proposalEq, certificateEq⟩
      subst proposal
      subst certificate
      rcases selected with selected | selected
      · rcases selected with ⟨proposalEq, candidateEq⟩
        subst candidate
        simpa [kernel, resourceValid, forgetCandidate] using
          initial_improvement_obligations.resourceValid
      · rcases selected with ⟨proposalContradiction, candidateEq⟩
        cases proposalContradiction
    · rcases constructed with ⟨proposalEq, certificateEq⟩
      subst proposal
      subst certificate
      rcases selected with selected | selected
      · rcases selected with ⟨proposalContradiction, candidateEq⟩
        cases proposalContradiction
      · rcases selected with ⟨proposalEq, candidateEq⟩
        subst candidate
        simpa [kernel, resourceValid, forgetCandidate] using
          target_stability_obligations.resourceValid
  successorDomain := by
    intro state witness proposal certificate candidate anchor resource
      stateDomain stateAdmissible stateInvariant witnessCovered generated
      constructed selected realized anchorValid resourceAuthorized accepted
    have obligations := checker.sound stateAdmissible stateInvariant accepted
    exact
      ⟨obligations.successorAdmissible.2,
        obligations.successorAdmissible.1⟩
  trustAnchorPreserved := by
    intro state witness proposal certificate candidate anchor resource
      stateDomain stateAdmissible stateInvariant witnessCovered generated
      constructed selected realized anchorValid resourceAuthorized accepted
    have obligations := checker.sound stateAdmissible stateInvariant accepted
    exact
      ⟨anchorValid.1,
        obligations.successorAdmissible.1⟩

def initialArchitecturePredecessor :
    ArchitecturePredecessor architectureEngine where
  state := initialState
  trustAnchor := .root
  domainValid := by
    exact ⟨rfl, by decide⟩
  admissible := by
    exact ⟨by decide, rfl⟩
  invariant := by
    exact ⟨by decide, rfl⟩
  trustAnchorValid := by
    exact ⟨rfl, by decide⟩

def targetArchitecturePredecessor :
    ArchitecturePredecessor architectureEngine where
  state := targetState
  trustAnchor := .root
  domainValid := by
    exact ⟨rfl, by decide⟩
  admissible := by
    exact ⟨by decide, rfl⟩
  invariant := by
    exact ⟨by decide, rfl⟩
  trustAnchorValid := by
    exact ⟨rfl, by decide⟩

def improvementEngineStep :
    ArchitectureEngineStep architectureEngine initialState where
  witness := .strictImprovement
  proposal := .improve
  certificate := improvementCertificate
  candidate := improvementCandidate
  resource := improvementResource
  witnessCovered := True.intro
  proposalGenerated := Or.inl ⟨rfl, rfl, rfl⟩
  certificateConstructed := Or.inl ⟨rfl, rfl⟩
  candidateSelected := Or.inl ⟨rfl, rfl⟩
  successorRealized := by
    exact ⟨rfl, rfl⟩
  resourceAuthorized := by
    norm_num [engineResourcePremise, initialState, canonicalState,
      improvementResource]
  checkerAccepted := improvement_check_accepts

def stabilityEngineStep :
    ArchitectureEngineStep architectureEngine targetState where
  witness := .stableContinuation
  proposal := .stabilize
  certificate := stabilityCertificate
  candidate := stabilityCandidate
  resource := stabilityResource
  witnessCovered := True.intro
  proposalGenerated := Or.inr ⟨rfl, rfl, rfl⟩
  certificateConstructed := Or.inr ⟨rfl, rfl⟩
  candidateSelected := Or.inr ⟨rfl, rfl⟩
  successorRealized := by
    exact ⟨rfl, rfl⟩
  resourceAuthorized := by
    norm_num [engineResourcePremise, targetState, canonicalState,
      stabilityResource]
  checkerAccepted := stability_check_accepts

theorem architectureSuccessorAvailability :
    ArchitectureSuccessorAvailability architectureEngine := by
  intro predecessor
  rcases predecessor.domainValid with ⟨stateCanonical, stateNotOutside⟩
  cases coreEq : predecessor.state.core with
  | outside =>
      exact False.elim (stateNotOutside coreEq)
  | initial =>
      have stateEq : predecessor.state = initialState := by
        calc
          predecessor.state = canonicalState predecessor.state.core :=
            stateCanonical
          _ = canonicalState .initial := by rw [coreEq]
          _ = initialState := rfl
      cases stateEq
      exact ⟨improvementEngineStep⟩
  | target =>
      have stateEq : predecessor.state = targetState := by
        calc
          predecessor.state = canonicalState predecessor.state.core :=
            stateCanonical
          _ = canonicalState .target := by rw [coreEq]
          _ = targetState := rfl
      cases stateEq
      exact ⟨stabilityEngineStep⟩

theorem improvement_direct_engine_successor :
    ArchitectureSuccessorResult
      architectureEngine
      kernelRefinement
      binaryChecker
      preservationMonitors
      binaryPreservationMonitors
      initialArchitecturePredecessor
      improvementEngineStep := by
  exact rclm_architecture_successor_theorem
    checker
    binaryChecker
    architectureEngine
    kernelRefinement
    checkerRefinement
    recoveryCompositionLaws
    preservationMonitors
    binaryPreservationMonitors
    monitorRefinement
    initialArchitecturePredecessor
    improvementEngineStep

noncomputable def classicalInfiniteArchitectureTrajectory :
    InfiniteArchitectureTrajectory architectureEngine :=
  buildInfiniteArchitectureTrajectory
    architectureEngine
    architectureSuccessorAvailability
    initialArchitecturePredecessor

theorem classical_infinite_architecture_trajectory_exists :
    ∃ trajectory : InfiniteArchitectureTrajectory architectureEngine,
      trajectory.predecessor 0 = initialArchitecturePredecessor := by
  exact conditional_infinite_architecture_trajectory_exists
    architectureEngine
    architectureSuccessorAvailability
    initialArchitecturePredecessor

theorem classical_infinite_architecture_step_result
    (n : Nat) :
    ArchitectureSuccessorResult
      architectureEngine
      kernelRefinement
      binaryChecker
      preservationMonitors
      binaryPreservationMonitors
      (classicalInfiniteArchitectureTrajectory.predecessor n)
      (classicalInfiniteArchitectureTrajectory.step n) := by
  exact infinite_architecture_step_result
    checker
    binaryChecker
    architectureEngine
    kernelRefinement
    checkerRefinement
    recoveryCompositionLaws
    preservationMonitors
    binaryPreservationMonitors
    monitorRefinement
    classicalInfiniteArchitectureTrajectory
    n

noncomputable def classicalInfiniteRclmAcceptedTrajectory :
    InfiniteAcceptedTrajectory checker :=
  InfiniteArchitectureTrajectory.toAcceptedTrajectory
    classicalInfiniteArchitectureTrajectory

noncomputable def classicalInfiniteCoreAcceptedTrajectory :
    InfiniteAcceptedTrajectory binaryChecker :=
  InfiniteArchitectureTrajectory.toCoreAcceptedTrajectory
    classicalInfiniteArchitectureTrajectory
    kernelRefinement
    checkerRefinement

end ClassicalBinary
end RCLM
end RcpRclmFormalCoreV2
