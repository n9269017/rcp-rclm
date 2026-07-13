import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCLM.ArchitectureTheorem
import RcpRclmFormalCoreV2.RCLM.ClassicalBinary
import RcpRclmFormalCoreV2.RCP.QuantumChannels

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace QuantumBinary

open RCP
open RCP.QuantumFinite
open ClassicalBinary

abbrev ArchitectureState :=
  State
    QuantumState
    LanguageRegister
    WorldReferenceRegister
    HumanReferenceRegister
    DefinitivenessRegister
    AmbiguityRegister
    MemoryRegister
    VerifierRegister
    ResourceRegister
    SelfModelRegister

abbrev ArchitectureUpdate :=
  Update
    QuantumUpdate
    ParameterUpdateRegister
    ArchitectureUpdateRegister
    MemoryUpdateRegister
    VerifierUpdateRegister
    SemanticUpdateRegister
    ToolUpdateRegister
    ResourceUpdateRegister

abbrev ArchitectureCertificate :=
  CertificatePacket
    QuantumCertificate
    SemanticEvidence
    TypeEvidence
    LedgerEvidence
    GoalTransportEvidence
    TrustEvidence
    ResourceEvidence
    RealityEvidence
    RecoveryEvidence
    ProgressEvidence

def canonicalState : QuantumState → ArchitectureState
  | .outside =>
      { core := .outside
        language := .invalid
        worldReference := .absent
        humanReference := .absent
        definitiveness := .invalid
        ambiguity := .uncontrolled
        memory := .outside
        verifier := .untrusted
        resources := { used := 2, limit := 1 }
        selfModel := .outside }
  | .source =>
      { core := .source
        language := .symbolicBinary
        worldReference := .biasedTarget
        humanReference := .declaredBinaryTask
        definitiveness := .provisional
        ambiguity := .bounded
        memory := .initial
        verifier := .trustedBinaryChecker
        resources := { used := 0, limit := 1 }
        selfModel := .initial }
  | .target =>
      { core := .target
        language := .symbolicBinary
        worldReference := .biasedTarget
        humanReference := .declaredBinaryTask
        definitiveness := .certified
        ambiguity := .resolved
        memory := .target
        verifier := .trustedBinaryChecker
        resources := { used := 1, limit := 1 }
        selfModel := .target }

def canonicalUpdate : QuantumUpdate → ArchitectureUpdate
  | .stay =>
      { core := .stay
        parameters := .unchanged
        architecture := .preserved
        memory := .retained
        verifier := .retained
        semantics := .preserved
        tools := .none
        resources := .bounded }
  | .swap =>
      { core := .swap
        parameters := .targetAligned
        architecture := .preserved
        memory := .advanced
        verifier := .retained
        semantics := .targetAligned
        tools := .none
        resources := .bounded }

def canonicalCertificate : QuantumCertificate → ArchitectureCertificate
  | .improvement =>
      { core := .improvement
        semantics := .coherent
        typing := .typed
        ledger := .withinBudget
        goalTransport := .targetFixed
        trust := .predecessorVerified
        resources := .bounded
        reality := .contained
        recovery := .exact
        progress := .strict }
  | .stability =>
      { core := .stability
        semantics := .coherent
        typing := .typed
        ledger := .withinBudget
        goalTransport := .targetFixed
        trust := .predecessorVerified
        resources := .bounded
        reality := .contained
        recovery := .exact
        progress := .stable }
  | .malformed =>
      { core := .malformed
        semantics := .rejected
        typing := .rejected
        ledger := .rejected
        goalTransport := .rejected
        trust := .rejected
        resources := .rejected
        reality := .rejected
        recovery := .rejected
        progress := .rejected }

@[simp] theorem canonicalState_core (state : QuantumState) :
    (canonicalState state).core = state := by
  cases state <;> rfl

@[simp] theorem canonicalUpdate_core (update : QuantumUpdate) :
    (canonicalUpdate update).core = update := by
  cases update <;> rfl

@[simp] theorem canonicalCertificate_core (certificate : QuantumCertificate) :
    (canonicalCertificate certificate).core = certificate := by
  cases certificate <;> rfl

def forgetCandidate
    (candidate : Candidate ArchitectureState ArchitectureUpdate) :
    Candidate QuantumState QuantumUpdate where
  update := candidate.update.core
  next := candidate.next.core

def liftCandidate
    (candidate : Candidate QuantumState QuantumUpdate) :
    Candidate ArchitectureState ArchitectureUpdate where
  update := canonicalUpdate candidate.update
  next := canonicalState candidate.next

@[simp] theorem forget_lift_candidate
    (candidate : Candidate QuantumState QuantumUpdate) :
    forgetCandidate (liftCandidate candidate) = candidate := by
  cases candidate
  simp [forgetCandidate, liftCandidate]

def apply
    (state : ArchitectureState)
    (update : ArchitectureUpdate) : ArchitectureState :=
  canonicalState (quantumApply state.core update.core)

def admissible (state : ArchitectureState) : Prop :=
  state.core ≠ .outside ∧ state = canonicalState state.core

def protectedInvariant (state : ArchitectureState) : Prop :=
  state.core ≠ .outside ∧ state = canonicalState state.core

noncomputable def protectedValue
    (state : ArchitectureState)
    (_distinction : Unit) : ℝ :=
  quantumProgress state.core

def stateDistance (x y : ArchitectureState) : ℝ :=
  quantumStateDistance x.core y.core

def recover
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (endpoint : ArchitectureState) : ArchitectureState :=
  canonicalState
    (quantumRecover state.core (forgetCandidate candidate) endpoint.core)

noncomputable def progress (state : ArchitectureState) : ℝ :=
  quantumProgress state.core

def strictWitness
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop :=
  quantumStrictWitness state.core (forgetCandidate candidate) certificate.core

def residual
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate)
    (index : QuantumResidualIndex) : ℝ :=
  quantumResidual state.core (forgetCandidate candidate) certificate.core index

def trustValid
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop :=
  quantumTrustValid state.core (forgetCandidate candidate) certificate.core

def resourceValid
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop :=
  quantumResourceValid state.core (forgetCandidate candidate) certificate.core

def realityContained
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop :=
  quantumRealityContained state.core (forgetCandidate candidate) certificate.core

def sourceState : ArchitectureState := canonicalState .source

def targetState : ArchitectureState := canonicalState .target

def outsideState : ArchitectureState := canonicalState .outside

def improvementUpdate : ArchitectureUpdate := canonicalUpdate .swap

def stabilityUpdate : ArchitectureUpdate := canonicalUpdate .stay

def improvementCertificate : ArchitectureCertificate :=
  canonicalCertificate .improvement

def stabilityCertificate : ArchitectureCertificate :=
  canonicalCertificate .stability

def malformedCertificate : ArchitectureCertificate :=
  canonicalCertificate .malformed

def improvementCandidate : Candidate ArchitectureState ArchitectureUpdate where
  update := improvementUpdate
  next := targetState

def stabilityCandidate : Candidate ArchitectureState ArchitectureUpdate where
  update := stabilityUpdate
  next := targetState

def invalidCandidate : Candidate ArchitectureState ArchitectureUpdate where
  update := improvementUpdate
  next := sourceState

noncomputable def kernel :
    Kernel
      ArchitectureState
      ArchitectureUpdate
      ArchitectureCertificate
      Unit
      QuantumResidualIndex where
  apply := apply
  admissible := admissible
  protectedInvariant := protectedInvariant
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    refine ⟨sourceState, (), targetState, (), ?_⟩
    change quantumProgress .source ≠ quantumProgress .target
    exact ne_of_lt quantumProgress_source_lt_target
  transportProtected := fun _state _candidate distinction => distinction
  lossBudget := fun _state _candidate => 0
  lossBudget_nonnegative := by
    intro state candidate
    exact le_rfl
  stateDistance := stateDistance
  stateDistance_nonnegative := by
    intro x y
    exact quantumStateDistance_nonnegative x.core y.core
  recover := recover
  recoveryBudget := fun _state _candidate => 0
  recoveryBudget_nonnegative := by
    intro state candidate
    exact le_rfl
  progress := progress
  strictWitness := strictWitness
  residual := residual
  residual_nonconstant := by
    rcases quantumKernel.residual_nonconstant with
      ⟨state₁, candidate₁, certificate₁,
        state₂, candidate₂, certificate₂, index, different⟩
    refine
      ⟨canonicalState state₁,
        liftCandidate candidate₁,
        canonicalCertificate certificate₁,
        canonicalState state₂,
        liftCandidate candidate₂,
        canonicalCertificate certificate₂,
        index,
        ?_⟩
    simpa [residual, quantumKernel] using different
  trustValid := trustValid
  resourceValid := resourceValid
  realityContained := realityContained
  realityContained_not_universal := by
    rcases quantumKernel.realityContained_not_universal with
      ⟨state, candidate, certificate, rejected⟩
    refine
      ⟨canonicalState state,
        liftCandidate candidate,
        canonicalCertificate certificate,
        ?_⟩
    simpa [realityContained, quantumKernel] using rejected

noncomputable def kernelRefinement :
    KernelRefinement kernel quantumKernel where
  forgetState := fun state => state.core
  liftState := canonicalState
  forgetLiftState := canonicalState_core
  forgetUpdate := fun update => update.core
  liftUpdate := canonicalUpdate
  forgetLiftUpdate := canonicalUpdate_core
  forgetCertificate := fun certificate => certificate.core
  liftCertificate := canonicalCertificate
  forgetLiftCertificate := canonicalCertificate_core
  forgetProtected := fun distinction => distinction
  liftProtected := fun distinction => distinction
  forgetLiftProtected := by
    intro distinction
    cases distinction
    rfl
  forgetResidualIndex := fun index => index
  liftResidualIndex := fun index => index
  forgetLiftResidualIndex := by
    intro index
    rfl
  applyPreserved := by
    intro state update
    simpa [kernel, apply, quantumKernel] using
      canonicalState_core (quantumApply state.core update.core)
  admissiblePreserved := by
    intro state stateAdmissible
    exact stateAdmissible.1
  invariantPreserved := by
    intro state stateInvariant
    exact stateInvariant.1
  protectedValuePreserved := by
    intro state distinction
    rfl
  transportProtectedPreserved := by
    intro state candidate distinction
    rfl
  lossBudgetPreserved := by
    intro state candidate
    rfl
  stateDistancePreserved := by
    intro x y
    rfl
  recoverPreserved := by
    intro state candidate endpoint
    change
      (canonicalState
        (quantumRecover state.core (forgetCandidate candidate) endpoint.core)).core =
      quantumRecover
        state.core
        { update := candidate.update.core
          next := candidate.next.core }
        endpoint.core
    rw [canonicalState_core]
    rfl
  recoveryBudgetPreserved := by
    intro state candidate
    rfl
  progressPreserved := by
    intro state
    rfl
  strictWitnessPreserved := by
    intro state candidate certificate
    rfl
  residualPreserved := by
    intro state candidate certificate index
    rfl
  trustValidPreserved := by
    intro state candidate certificate
    rfl
  resourceValidPreserved := by
    intro state candidate certificate
    rfl
  realityContainedPreserved := by
    intro state candidate certificate
    rfl

def ArchitectureEvidenceValid
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop :=
  state = canonicalState state.core ∧
    candidate.update = canonicalUpdate candidate.update.core ∧
    candidate.next = canonicalState candidate.next.core ∧
    certificate = canonicalCertificate certificate.core

def PacketAccepted
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop :=
  quantumCheck state.core (forgetCandidate candidate) certificate.core = true ∧
    ArchitectureEvidenceValid state candidate certificate

def check
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Bool :=
  quantumCheck state.core (forgetCandidate candidate) certificate.core &&
    decide (state = canonicalState state.core) &&
    decide (candidate.update = canonicalUpdate candidate.update.core) &&
    decide (candidate.next = canonicalState candidate.next.core) &&
    decide (certificate = canonicalCertificate certificate.core)

theorem check_eq_true_iff
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) :
    check state candidate certificate = true ↔
      PacketAccepted state candidate certificate := by
  simp [check, PacketAccepted, ArchitectureEvidenceValid, and_assoc]

theorem architectureEvidence_of_check
    {state : ArchitectureState}
    {candidate : Candidate ArchitectureState ArchitectureUpdate}
    {certificate : ArchitectureCertificate}
    (accepted : check state candidate certificate = true) :
    ArchitectureEvidenceValid state candidate certificate := by
  have packet : PacketAccepted state candidate certificate :=
    (check_eq_true_iff state candidate certificate).1 accepted
  exact packet.2

noncomputable def checker : TrustedChecker kernel where
  check := check
  sound := by
    intro state candidate certificate
      stateAdmissible stateInvariant accepted
    have packet : PacketAccepted state candidate certificate :=
      (check_eq_true_iff state candidate certificate).1 accepted
    rcases packet with
      ⟨coreAccepted,
        stateCanonical,
        updateCanonical,
        nextCanonical,
        certificateCanonical⟩
    have coreObligations :
        StepObligations
          quantumKernel
          state.core
          (forgetCandidate candidate)
          certificate.core :=
      quantumChecker.sound
        stateAdmissible.1
        stateInvariant.1
        coreAccepted
    refine
      { typedSuccessor := ?_
        residualsNonpositive := ?_
        protectedNonLoss := ?_
        constructiveRecovery := ?_
        invariantPreserved := ?_
        progressNondecreasing := ?_
        strictProgressWhenWitness := ?_
        trustValid := ?_
        resourceValid := ?_
        realityContained := ?_
        successorAdmissible := ?_ }
    · have coreTyped := coreObligations.typedSuccessor
      unfold TypedSuccessor at coreTyped
      unfold TypedSuccessor
      calc
        candidate.next = canonicalState candidate.next.core := nextCanonical
        _ = canonicalState
              (quantumApply state.core candidate.update.core) :=
          congrArg canonicalState coreTyped
        _ = kernel.apply state candidate.update := by
          rfl
    · intro index
      exact coreObligations.residualsNonpositive index
    · have coreNonLoss := coreObligations.protectedNonLoss
      unfold ProtectedNonLoss at coreNonLoss
      unfold ProtectedNonLoss
      intro distinction
      cases distinction
      simpa [kernel, quantumKernel, protectedValue, forgetCandidate] using
        coreNonLoss ()
    · have coreRecovery := coreObligations.constructiveRecovery
      unfold ConstructiveRecovery at coreRecovery
      unfold ConstructiveRecovery
      simpa [kernel, stateDistance, recover, quantumKernel, forgetCandidate] using
        coreRecovery
    · change candidate.next.core ≠ .outside ∧
        candidate.next = canonicalState candidate.next.core
      exact ⟨coreObligations.invariantPreserved, nextCanonical⟩
    · exact coreObligations.progressNondecreasing
    · exact coreObligations.strictProgressWhenWitness
    · exact coreObligations.trustValid
    · exact coreObligations.resourceValid
    · exact coreObligations.realityContained
    · change candidate.next.core ≠ .outside ∧
        candidate.next = canonicalState candidate.next.core
      exact ⟨coreObligations.successorAdmissible, nextCanonical⟩

noncomputable def checkerRefinement :
    CheckerRefinement kernelRefinement checker quantumChecker where
  acceptancePreserved := by
    intro state candidate certificate accepted
    have packet : PacketAccepted state candidate certificate :=
      (check_eq_true_iff state candidate certificate).1 accepted
    exact packet.1

noncomputable def recoveryCompositionLaws :
    RecoveryCompositionLaws kernel where
  selfDistanceZero := by
    intro state
    exact quantumStateDistance_self state.core
  triangle := by
    intro x y z
    exact quantumStateDistance_triangle x.core y.core z.core
  recoverNonexpansive := by
    intro state candidate x y
    have coreBound := quantumRecoveryCompositionLaws.recoverNonexpansive
      state.core (forgetCandidate candidate) x.core y.core
    simpa [kernel, stateDistance, recover, quantumKernel] using coreBound

noncomputable def preservationMonitors :
    PreservationMonitors kernel (Relevance := QuantumRelevance) where
  lyapunovValue := fun state => quantumLyapunovValue state.core
  motionCharge := fun state candidate certificate =>
    quantumMotionCharge state.core (forgetCandidate candidate)
  lyapunovError := fun state candidate certificate => 0
  unsupportedCollapse := fun state candidate certificate =>
    quantumUnsupportedCollapse
      state.core (forgetCandidate candidate) certificate.core
  ambiguityError := fun state candidate certificate => 0
  relevanceValue := fun state relevance =>
    quantumRelevanceValue state.core relevance
  transportRelevance := fun state candidate relevance =>
    quantumTransportRelevance state.core (forgetCandidate candidate) relevance
  relevanceError := fun state candidate certificate => 0
  lyapunovValue_nonnegative := by
    intro state
    exact quantumLyapunovValue_nonnegative state.core
  motionCharge_nonnegative := by
    intro state candidate certificate
    exact quantumMotionCharge_nonnegative state.core (forgetCandidate candidate)
  lyapunovError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  unsupportedCollapse_nonnegative := by
    intro state candidate certificate
    exact quantumUnsupportedCollapse_nonnegative
      state.core (forgetCandidate candidate) certificate.core
  ambiguityError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  relevanceError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  lyapunovStep := by
    intro state candidate certificate obligations
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact quantumPreservationMonitors.lyapunovStep coreObligations
  ambiguityStep := by
    intro state candidate certificate obligations
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact quantumPreservationMonitors.ambiguityStep coreObligations
  relevanceStep := by
    intro state candidate certificate obligations relevance
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact quantumPreservationMonitors.relevanceStep coreObligations relevance

noncomputable def monitorRefinement :
    MonitorRefinement
      kernelRefinement
      preservationMonitors
      quantumPreservationMonitors where
  forgetRelevance := fun relevance => relevance
  liftRelevance := fun relevance => relevance
  forgetLiftRelevance := by
    intro relevance
    rfl
  lyapunovValuePreserved := by
    intro state
    rfl
  motionChargePreserved := by
    intro state candidate certificate
    rfl
  lyapunovErrorPreserved := by
    intro state candidate certificate
    rfl
  unsupportedCollapsePreserved := by
    intro state candidate certificate
    rfl
  ambiguityErrorPreserved := by
    intro state candidate certificate
    rfl
  relevanceValuePreserved := by
    intro state relevance
    rfl
  transportRelevancePreserved := by
    intro state candidate relevance
    rfl
  relevanceErrorPreserved := by
    intro state candidate certificate
    rfl

noncomputable def densityOf
    (state : ArchitectureState) : PositiveDiagonalDensityMatrix 2 :=
  stateDensity state.core

noncomputable def forwardChannelOf
    (update : ArchitectureUpdate) : FiniteDiagonalChannel 2 :=
  selectedChannel update.core

noncomputable def recoveryChannelOf
    (update : ArchitectureUpdate) : FiniteDiagonalChannel 2 :=
  selectedRecoveryChannel update.core

noncomputable def entropyOf (state : ArchitectureState) : ℝ :=
  vonNeumannEntropy (densityOf state).density

noncomputable def relativeEntropyOf
    (state reference : ArchitectureState) : ℝ :=
  quantumRelativeEntropy (densityOf state).density (densityOf reference).density

structure QuantumArchitectureSuccessor
    (state : ArchitectureState)
    (candidate : Candidate ArchitectureState ArchitectureUpdate)
    (certificate : ArchitectureCertificate) : Prop where
  architectureEvidence : ArchitectureEvidenceValid state candidate certificate
  rclmObligations : StepObligations kernel state candidate certificate
  coreObligations :
    StepObligations
      quantumKernel
      state.core
      (forgetCandidate candidate)
      certificate.core
  successorDensityEvidence :
    DensityMatrixEvidence (densityOf candidate.next).density.matrix
  forwardChannelRealizes :
    (forwardChannelOf candidate.update).apply (densityOf state).density =
      (densityOf candidate.next).density
  recoveryChannelExact :
    (recoveryChannelOf candidate.update).apply
        ((forwardChannelOf candidate.update).apply (densityOf state).density) =
      (densityOf state).density
  entropyPreserved :
    entropyOf candidate.next = entropyOf state
  relativeEntropyPreserved : ∀ reference,
    quantumRelativeEntropy
        ((forwardChannelOf candidate.update).apply (densityOf state).density)
        ((forwardChannelOf candidate.update).apply (densityOf reference).density) =
      relativeEntropyOf state reference

theorem accepted_quantum_architecture_successor
    {state : ArchitectureState}
    {candidate : Candidate ArchitectureState ArchitectureUpdate}
    {certificate : ArchitectureCertificate}
    (stateAdmissible : kernel.admissible state)
    (stateInvariant : kernel.protectedInvariant state)
    (accepted : checker.check state candidate certificate = true) :
    QuantumArchitectureSuccessor state candidate certificate := by
  have architectureEvidence :
      ArchitectureEvidenceValid state candidate certificate :=
    architectureEvidence_of_check accepted
  have rclmObligations :
      StepObligations kernel state candidate certificate :=
    checker.sound stateAdmissible stateInvariant accepted
  have coreObligations :
      StepObligations
        quantumKernel
        state.core
        (forgetCandidate candidate)
        certificate.core :=
    kernelRefinement.stepObligationsPreserved rclmObligations
  have coreTyped :
      candidate.next.core = quantumApply state.core candidate.update.core := by
    exact coreObligations.typedSuccessor
  refine
    { architectureEvidence := architectureEvidence
      rclmObligations := rclmObligations
      coreObligations := coreObligations
      successorDensityEvidence := ?_
      forwardChannelRealizes := ?_
      recoveryChannelExact := ?_
      entropyPreserved := ?_
      relativeEntropyPreserved := ?_ }
  · exact (densityOf candidate.next).density.densityEvidence
  · calc
      (forwardChannelOf candidate.update).apply (densityOf state).density =
          (stateDensity
            (quantumApply state.core candidate.update.core)).density := by
        exact selectedChannel_state_action state.core candidate.update.core
      _ = (densityOf candidate.next).density := by
        exact congrArg (fun coreState => (stateDensity coreState).density) coreTyped.symm
  · exact selectedChannel_recovery_exact
      candidate.update.core (densityOf state).density
  · have channelEntropy := selectedChannel_vonNeumannEntropy_preserving
      candidate.update.core (densityOf state).density
    have forwardAction :
        (forwardChannelOf candidate.update).apply (densityOf state).density =
          (densityOf candidate.next).density := by
      calc
        (forwardChannelOf candidate.update).apply (densityOf state).density =
            (stateDensity
              (quantumApply state.core candidate.update.core)).density := by
          exact selectedChannel_state_action state.core candidate.update.core
        _ = (densityOf candidate.next).density := by
          exact congrArg (fun coreState => (stateDensity coreState).density) coreTyped.symm
    rw [forwardAction] at channelEntropy
    exact channelEntropy
  · intro reference
    exact selectedChannel_quantumRelativeEntropy_preserving
      candidate.update.core
      (densityOf state).density
      (densityOf reference).density

theorem improvement_quantum_architecture_successor :
    QuantumArchitectureSuccessor
      sourceState
      improvementCandidate
      improvementCertificate := by
  apply accepted_quantum_architecture_successor
  · simp [kernel, admissible, sourceState]
  · simp [kernel, protectedInvariant, sourceState]
  · rfl

theorem stability_quantum_architecture_successor :
    QuantumArchitectureSuccessor
      targetState
      stabilityCandidate
      stabilityCertificate := by
  apply accepted_quantum_architecture_successor
  · simp [kernel, admissible, targetState]
  · simp [kernel, protectedInvariant, targetState]
  · rfl

end QuantumBinary
end RCLM
end RcpRclmFormalCoreV2
