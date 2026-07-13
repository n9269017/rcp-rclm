import RcpRclmFormalCoreV2.RCLM.PaperIIAlignmentPremises
import RcpRclmFormalCoreV2.RCLM.ClassicalBinaryEngine

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace ClassicalBinary

open RCP
open RCP.ClassicalFinite

noncomputable def paperIINonLossyCandidate
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate) : Prop :=
  ProtectedNonLoss kernel state candidate ∧
    ConstructiveRecovery kernel state candidate

noncomputable def paperIIAlgebraicGate
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (_certificate : ClassicalCertificate) : Prop :=
  ProtectedNonLoss kernel state candidate ∧
    ConstructiveRecovery kernel state candidate

noncomputable def paperIIFullGate
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  (∀ index, kernel.residual state candidate certificate index ≤ 0) ∧
    kernel.trustValid state candidate certificate ∧
    kernel.resourceValid state candidate certificate ∧
    kernel.realityContained state candidate certificate

noncomputable def paperIIPredecessorAbilitiesPreserved
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (_certificate : ClassicalCertificate) : Prop :=
  kernel.progress state ≤ kernel.progress candidate.next

noncomputable def paperIIStrictAbilityExpansion
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (_certificate : ClassicalCertificate) : Prop :=
  kernel.progress state < kernel.progress candidate.next

def paperIIViabilityKernel (state : ClassicalState) : Prop :=
  kernel.admissible state ∧ kernel.protectedInvariant state

def paperIIProjectionRealized
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (_certificate : ClassicalCertificate) : Prop :=
  TypedSuccessor kernel state candidate

noncomputable def paperIIDirectSemantics :
    PaperIIDirectEngineSemantics architectureEngine where
  nonLossyCandidate := paperIINonLossyCandidate
  algebraicGate := paperIIAlgebraicGate
  fullGate := paperIIFullGate
  predecessorAbilitiesPreserved := paperIIPredecessorAbilitiesPreserved
  strictAbilityExpansion := paperIIStrictAbilityExpansion
  viabilityKernel := paperIIViabilityKernel
  projectionRealized := paperIIProjectionRealized
  nonLossyCandidate_of_obligations := by
    intro state candidate certificate obligations
    exact ⟨obligations.protectedNonLoss, obligations.constructiveRecovery⟩
  algebraicGate_of_obligations := by
    intro state candidate certificate obligations
    exact ⟨obligations.protectedNonLoss, obligations.constructiveRecovery⟩
  fullGate_of_obligations := by
    intro state candidate certificate obligations
    exact
      ⟨obligations.residualsNonpositive,
        obligations.trustValid,
        obligations.resourceValid,
        obligations.realityContained⟩
  predecessorAbilitiesPreserved_of_obligations := by
    intro state candidate certificate obligations
    exact obligations.progressNondecreasing
  strictAbilityExpansion_of_witness := by
    intro state candidate certificate strictWitness obligations
    exact obligations.strictProgressWhenWitness strictWitness
  viabilityKernel_of_domain := by
    intro state stateDomain
    have admissibleState : kernel.admissible state :=
      ⟨stateDomain.2, stateDomain.1⟩
    have invariantState : kernel.protectedInvariant state :=
      ⟨stateDomain.2, stateDomain.1⟩
    exact ⟨admissibleState, invariantState⟩
  projectionRealized_of_typedSuccessor := by
    intro state candidate certificate typedSuccessor
    exact typedSuccessor

def paperIIStrictImprovementStep :
    StrictArchitectureEngineStep architectureEngine initialState where
  step := improvementEngineStep
  strictWitness := by
    change ImprovementPacket
      BinaryState.initial
      RCP.ClassicalFinite.improvementCandidate
      BinaryCertificate.improvement
    exact ⟨rfl, rfl, rfl, rfl⟩

theorem improvement_paper_ii_direct_engine_aligned :
    ArchitectureSuccessorResult
        architectureEngine
        kernelRefinement
        binaryChecker
        preservationMonitors
        binaryPreservationMonitors
        initialArchitecturePredecessor
        paperIIStrictImprovementStep.step ∧
      PaperIIDirectEngineObligations
        paperIIDirectSemantics
        initialArchitecturePredecessor.state
        paperIIStrictImprovementStep.step.candidate
        paperIIStrictImprovementStep.step.certificate := by
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
    paperIIStrictImprovementStep

def paperIIPacketConstructed
    (_state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  (candidate = improvementCandidate ∧
      certificate = improvementCertificate) ∨
    (candidate = stabilityCandidate ∧
      certificate = stabilityCertificate)

def paperIIGoalDistance
    (first second : WorldReferenceRegister) : ℝ :=
  if first = second then 0 else 1

theorem paperIIGoalDistance_nonnegative
    (first second : WorldReferenceRegister) :
    0 ≤ paperIIGoalDistance first second := by
  by_cases equalRegisters : first = second
  · simp [paperIIGoalDistance, equalRegisters]
  · simp [paperIIGoalDistance, equalRegisters]

theorem paperIIGoalDistance_self
    (goal : WorldReferenceRegister) :
    paperIIGoalDistance goal goal = 0 := by
  simp [paperIIGoalDistance]

theorem paperIIGoalDistance_triangle
    (first second third : WorldReferenceRegister) :
    paperIIGoalDistance first third ≤
      paperIIGoalDistance first second +
        paperIIGoalDistance second third := by
  cases first with
  | biasedTarget =>
      cases second with
      | biasedTarget =>
          cases third with
          | biasedTarget => simp [paperIIGoalDistance]
          | absent => simp [paperIIGoalDistance]
      | absent =>
          cases third with
          | biasedTarget => simp [paperIIGoalDistance]
          | absent => simp [paperIIGoalDistance]
  | absent =>
      cases second with
      | biasedTarget =>
          cases third with
          | biasedTarget => simp [paperIIGoalDistance]
          | absent => simp [paperIIGoalDistance]
      | absent =>
          cases third with
          | biasedTarget => simp [paperIIGoalDistance]
          | absent => simp [paperIIGoalDistance]

noncomputable def paperIISuccessorSemantics :
    PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierRegister)
      (UncertaintyEnvelope := RealityEvidence)
      (Goal := WorldReferenceRegister)
      architectureEngine where
  packetConstructed := paperIIPacketConstructed
  stateVerifierSchema := fun _ => .trustedBinaryChecker
  transportVerifierSchema := fun _ _ schema => schema
  verifierSchemaRefines := fun first second => first = second
  verifierSchemaReflexive := by
    intro schema
    rfl
  verifierSchemaTransitive := by
    intro first second third firstSecond secondThird
    exact Eq.trans firstSecond secondThird
  verifierSchemaTransportMonotone := by
    intro state candidate first second refinement
    exact refinement
  uncertaintyTransportValid := fun state candidate certificate =>
    kernel.realityContained state candidate certificate
  stateGoal := fun _ => .biasedTarget
  transportGoal := fun _ _ goal => goal
  goalDistance := paperIIGoalDistance
  goalDistance_nonnegative := paperIIGoalDistance_nonnegative
  goalDistance_self := paperIIGoalDistance_self
  goalDistance_triangle := paperIIGoalDistance_triangle
  goalTransportNonexpansive := by
    intro state candidate first second
    exact le_rfl
  goalDriftBudget := fun _ _ _ => 0
  goalDriftBudget_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  antiCircularTrust := fun state candidate certificate =>
    kernel.trustValid state candidate certificate
  proofBudgetValid := fun state candidate certificate =>
    kernel.resourceValid state candidate certificate
  successorPersistent := fun _ candidate _ =>
    kernel.admissible candidate.next ∧
      kernel.protectedInvariant candidate.next
  realityCertificate := fun state candidate certificate =>
    kernel.realityContained state candidate certificate
  tractabilityCertificate := fun state _ _ =>
    state.resources.used ≤ state.resources.limit
  soundnessFailureRisk := fun _ _ _ => 0
  soundnessFailureRisk_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  packetConstructed_of_engine := by
    intro state proposal certificate candidate constructed selected
    rcases constructed with constructed | constructed
    · rcases constructed with ⟨proposalEq, certificateEq⟩
      rcases selected with selected | selected
      · rcases selected with ⟨selectedProposalEq, candidateEq⟩
        exact Or.inl ⟨candidateEq, certificateEq⟩
      · rcases selected with ⟨selectedProposalEq, candidateEq⟩
        have contradiction : EngineProposal.improve = EngineProposal.stabilize :=
          Eq.trans proposalEq.symm selectedProposalEq
        cases contradiction
    · rcases constructed with ⟨proposalEq, certificateEq⟩
      rcases selected with selected | selected
      · rcases selected with ⟨selectedProposalEq, candidateEq⟩
        have contradiction : EngineProposal.stabilize = EngineProposal.improve :=
          Eq.trans proposalEq.symm selectedProposalEq
        cases contradiction
      · rcases selected with ⟨selectedProposalEq, candidateEq⟩
        exact Or.inr ⟨candidateEq, certificateEq⟩
  verifierSchema_step_of_obligations := by
    intro state candidate certificate obligations
    rfl
  uncertaintyTransportValid_of_obligations := by
    intro state candidate certificate obligations
    exact obligations.realityContained
  goalIdentity_of_obligations := by
    intro state candidate certificate obligations
    simp [paperIIGoalDistance]
  antiCircularTrust_of_obligations := by
    intro state candidate certificate obligations
    exact obligations.trustValid
  proofBudgetValid_of_obligations := by
    intro state candidate certificate obligations
    exact obligations.resourceValid
  successorPersistent_of_domain := by
    intro state candidate certificate successorDomain
    have successorAdmissible : kernel.admissible candidate.next :=
      ⟨successorDomain.2, successorDomain.1⟩
    have successorInvariant : kernel.protectedInvariant candidate.next :=
      ⟨successorDomain.2, successorDomain.1⟩
    exact ⟨successorAdmissible, successorInvariant⟩
  realityCertificate_of_obligations := by
    intro state candidate certificate obligations
    exact obligations.realityContained
  tractabilityCertificate_of_resource := by
    intro state proposal certificate candidate resource resourcePremise
    exact resourcePremise.1

noncomputable def paperIIUncertaintySemantics :
    PaperIIUncertaintyEnvelopeSemantics paperIISuccessorSemantics where
  stateEnvelope := fun _ => .contained
  transportEnvelope := fun _ _ envelope => envelope
  envelopeRefines := fun first second => first = second
  envelopeReflexive := by
    intro envelope
    rfl
  envelopeTransitive := by
    intro first second third firstSecond secondThird
    exact Eq.trans firstSecond secondThird
  transportMonotone := by
    intro state candidate first second refinement
    exact refinement
  oneStepPersistence := by
    intro state candidate certificate obligations
    rfl

def paperIIDomainSemantics : PaperIIDomainSemantics architectureEngine where
  directEngineDomain := engineDomain
  seedLibraryDomain := engineDomain
  successorVerificationDomain := engineDomain
  directEngineDomain_to_architectureDomain := by
    intro state stateDomain
    exact stateDomain
  seedLibraryDomain_to_directEngineDomain := by
    intro state stateDomain
    exact stateDomain
  seedLibraryDomain_to_successorVerificationDomain := by
    intro state stateDomain
    exact stateDomain
  architectureDomain_to_successorVerificationDomain := by
    intro state stateDomain
    exact stateDomain

noncomputable def paperIIInfiniteBudgets :
    PaperIIInfiniteBudgetAssumptions
      paperIISuccessorSemantics
      classicalInfiniteArchitectureTrajectory where
  goalDrift := by
    change Summable fun _ : Nat => (0 : ℝ)
    exact summable_zero
  soundnessFailure := by
    change Summable fun _ : Nat => (0 : ℝ)
    exact summable_zero

theorem classical_paper_ii_aligned_infinite_result :
    PaperIIAlignedInfiniteResult
      paperIIDirectSemantics
      paperIISuccessorSemantics
      paperIIUncertaintySemantics
      paperIIDomainSemantics
      classicalInfiniteArchitectureTrajectory := by
  exact paper_ii_aligned_infinite_result
    paperIIDirectSemantics
    paperIISuccessorSemantics
    paperIIUncertaintySemantics
    paperIIDomainSemantics
    classicalInfiniteArchitectureTrajectory
    paperIIInfiniteBudgets

theorem classical_paper_ii_aligned_trajectory_exists :
    ∃ trajectory : InfiniteArchitectureTrajectory architectureEngine,
      trajectory.predecessor 0 = initialArchitecturePredecessor ∧
      paperIIDomainSemantics.seedLibraryDomain
        (trajectory.predecessor 0).state ∧
      PaperIIAlignedInfiniteResult
        paperIIDirectSemantics
        paperIISuccessorSemantics
        paperIIUncertaintySemantics
        paperIIDomainSemantics
        trajectory := by
  have initialSeedLibraryDomain :
      paperIIDomainSemantics.seedLibraryDomain
        initialArchitecturePredecessor.state := by
    exact ⟨rfl, by decide⟩
  exact conditional_infinite_paper_ii_aligned_trajectory_exists
    architectureEngine
    paperIIDirectSemantics
    paperIISuccessorSemantics
    paperIIUncertaintySemantics
    paperIIDomainSemantics
    architectureSuccessorAvailability
    initialArchitecturePredecessor
    initialSeedLibraryDomain
    paperIIInfiniteBudgets

end ClassicalBinary
end RCLM
end RcpRclmFormalCoreV2
