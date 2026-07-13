import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCLM.ArchitectureTheorem
import RcpRclmFormalCoreV2.RCP.ClassicalBinary

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace ClassicalBinary

open RCP
open RCP.ClassicalFinite

inductive LanguageRegister where
  | symbolicBinary
  | invalid
  deriving DecidableEq

inductive WorldReferenceRegister where
  | biasedTarget
  | absent
  deriving DecidableEq

inductive HumanReferenceRegister where
  | declaredBinaryTask
  | absent
  deriving DecidableEq

inductive DefinitivenessRegister where
  | provisional
  | certified
  | invalid
  deriving DecidableEq

inductive AmbiguityRegister where
  | bounded
  | resolved
  | uncontrolled
  deriving DecidableEq

inductive MemoryRegister where
  | outside
  | initial
  | target
  deriving DecidableEq

inductive VerifierRegister where
  | trustedBinaryChecker
  | untrusted
  deriving DecidableEq

structure ResourceRegister where
  used : Nat
  limit : Nat
  deriving DecidableEq

inductive SelfModelRegister where
  | outside
  | initial
  | target
  deriving DecidableEq

inductive ParameterUpdateRegister where
  | unchanged
  | targetAligned
  | invalid
  deriving DecidableEq

inductive ArchitectureUpdateRegister where
  | preserved
  | invalid
  deriving DecidableEq

inductive MemoryUpdateRegister where
  | retained
  | advanced
  | invalid
  deriving DecidableEq

inductive VerifierUpdateRegister where
  | retained
  | invalid
  deriving DecidableEq

inductive SemanticUpdateRegister where
  | preserved
  | targetAligned
  | invalid
  deriving DecidableEq

inductive ToolUpdateRegister where
  | none
  | invalid
  deriving DecidableEq

inductive ResourceUpdateRegister where
  | bounded
  | invalid
  deriving DecidableEq

inductive SemanticEvidence where
  | coherent
  | rejected
  deriving DecidableEq

inductive TypeEvidence where
  | typed
  | rejected
  deriving DecidableEq

inductive LedgerEvidence where
  | withinBudget
  | rejected
  deriving DecidableEq

inductive GoalTransportEvidence where
  | targetFixed
  | rejected
  deriving DecidableEq

inductive TrustEvidence where
  | predecessorVerified
  | rejected
  deriving DecidableEq

inductive ResourceEvidence where
  | bounded
  | rejected
  deriving DecidableEq

inductive RealityEvidence where
  | contained
  | rejected
  deriving DecidableEq

inductive RecoveryEvidence where
  | exact
  | rejected
  deriving DecidableEq

inductive ProgressEvidence where
  | strict
  | stable
  | rejected
  deriving DecidableEq

abbrev ClassicalState :=
  State
    BinaryState
    LanguageRegister
    WorldReferenceRegister
    HumanReferenceRegister
    DefinitivenessRegister
    AmbiguityRegister
    MemoryRegister
    VerifierRegister
    ResourceRegister
    SelfModelRegister

abbrev ClassicalUpdate :=
  Update
    BinaryUpdate
    ParameterUpdateRegister
    ArchitectureUpdateRegister
    MemoryUpdateRegister
    VerifierUpdateRegister
    SemanticUpdateRegister
    ToolUpdateRegister
    ResourceUpdateRegister

abbrev ClassicalCertificate :=
  CertificatePacket
    BinaryCertificate
    SemanticEvidence
    TypeEvidence
    LedgerEvidence
    GoalTransportEvidence
    TrustEvidence
    ResourceEvidence
    RealityEvidence
    RecoveryEvidence
    ProgressEvidence


def canonicalState : BinaryState → ClassicalState
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
  | .initial =>
      { core := .initial
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


def canonicalUpdate : BinaryUpdate → ClassicalUpdate
  | .stay =>
      { core := .stay
        parameters := .unchanged
        architecture := .preserved
        memory := .retained
        verifier := .retained
        semantics := .preserved
        tools := .none
        resources := .bounded }
  | .improve =>
      { core := .improve
        parameters := .targetAligned
        architecture := .preserved
        memory := .advanced
        verifier := .retained
        semantics := .targetAligned
        tools := .none
        resources := .bounded }


def canonicalCertificate : BinaryCertificate → ClassicalCertificate
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


@[simp] theorem canonicalState_core (state : BinaryState) :
    (canonicalState state).core = state := by
  cases state <;> rfl


@[simp] theorem canonicalUpdate_core (update : BinaryUpdate) :
    (canonicalUpdate update).core = update := by
  cases update <;> rfl


@[simp] theorem canonicalCertificate_core (certificate : BinaryCertificate) :
    (canonicalCertificate certificate).core = certificate := by
  cases certificate <;> rfl


def forgetCandidate
    (candidate : Candidate ClassicalState ClassicalUpdate) :
    Candidate BinaryState BinaryUpdate where
  update := candidate.update.core
  next := candidate.next.core


def liftCandidate
    (candidate : Candidate BinaryState BinaryUpdate) :
    Candidate ClassicalState ClassicalUpdate where
  update := canonicalUpdate candidate.update
  next := canonicalState candidate.next


@[simp] theorem forget_lift_candidate
    (candidate : Candidate BinaryState BinaryUpdate) :
    forgetCandidate (liftCandidate candidate) = candidate := by
  cases candidate
  simp [forgetCandidate, liftCandidate]


def apply (state : ClassicalState) (update : ClassicalUpdate) : ClassicalState :=
  canonicalState (binaryApply state.core update.core)


def admissible (state : ClassicalState) : Prop :=
  state.core ≠ .outside ∧ state = canonicalState state.core


def protectedInvariant (state : ClassicalState) : Prop :=
  state.core ≠ .outside ∧ state = canonicalState state.core


noncomputable def protectedValue
    (state : ClassicalState)
    (_distinction : Unit) : ℝ :=
  binaryProgress state.core


def stateDistance (x y : ClassicalState) : ℝ :=
  binaryStateDistance x.core y.core


def recover
    (state : ClassicalState)
    (_candidate : Candidate ClassicalState ClassicalUpdate)
    (_endpoint : ClassicalState) : ClassicalState :=
  canonicalState state.core


noncomputable def progress (state : ClassicalState) : ℝ :=
  binaryProgress state.core


def strictWitness
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  binaryStrictWitness state.core (forgetCandidate candidate) certificate.core


def residual
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate)
    (index : BinaryResidualIndex) : ℝ :=
  binaryResidual state.core (forgetCandidate candidate) certificate.core index


def trustValid
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  binaryTrustValid state.core (forgetCandidate candidate) certificate.core


def resourceValid
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  binaryResourceValid state.core (forgetCandidate candidate) certificate.core


def realityContained
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  binaryRealityContained state.core (forgetCandidate candidate) certificate.core


def initialState : ClassicalState := canonicalState .initial

def targetState : ClassicalState := canonicalState .target

def outsideState : ClassicalState := canonicalState .outside


def improvementUpdate : ClassicalUpdate := canonicalUpdate .improve

def stabilityUpdate : ClassicalUpdate := canonicalUpdate .stay


def improvementCertificate : ClassicalCertificate :=
  canonicalCertificate .improvement


def stabilityCertificate : ClassicalCertificate :=
  canonicalCertificate .stability


def malformedCertificate : ClassicalCertificate :=
  canonicalCertificate .malformed


def improvementCandidate : Candidate ClassicalState ClassicalUpdate where
  update := improvementUpdate
  next := targetState


def stabilityCandidate : Candidate ClassicalState ClassicalUpdate where
  update := stabilityUpdate
  next := targetState


def invalidCandidate : Candidate ClassicalState ClassicalUpdate where
  update := improvementUpdate
  next := initialState


noncomputable def kernel :
    Kernel
      ClassicalState
      ClassicalUpdate
      ClassicalCertificate
      Unit
      BinaryResidualIndex where
  apply := apply
  admissible := admissible
  protectedInvariant := protectedInvariant
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    refine ⟨initialState, (), targetState, (), ?_⟩
    change binaryProgress .initial ≠ binaryProgress .target
    exact ne_of_lt binaryProgress_initial_lt_target
  transportProtected := fun _state _candidate distinction => distinction
  lossBudget := fun _state _candidate => 0
  lossBudget_nonnegative := by
    intro state candidate
    exact le_rfl
  stateDistance := stateDistance
  stateDistance_nonnegative := by
    intro x y
    exact binaryStateDistance_nonnegative x.core y.core
  recover := recover
  recoveryBudget := fun _state _candidate => 0
  recoveryBudget_nonnegative := by
    intro state candidate
    exact le_rfl
  progress := progress
  strictWitness := strictWitness
  residual := residual
  residual_nonconstant := by
    rcases binaryKernel.residual_nonconstant with
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
    simpa [residual, binaryKernel] using different
  trustValid := trustValid
  resourceValid := resourceValid
  realityContained := realityContained
  realityContained_not_universal := by
    rcases binaryKernel.realityContained_not_universal with
      ⟨state, candidate, certificate, rejected⟩
    refine
      ⟨canonicalState state,
        liftCandidate candidate,
        canonicalCertificate certificate,
        ?_⟩
    simpa [realityContained, binaryKernel] using rejected


noncomputable def kernelRefinement :
    KernelRefinement kernel binaryKernel where
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
    simpa [kernel, apply, binaryKernel] using
      canonicalState_core (binaryApply state.core update.core)
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
    simpa [kernel, recover, binaryKernel] using
      canonicalState_core state.core
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
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  state = canonicalState state.core ∧
    candidate.update = canonicalUpdate candidate.update.core ∧
    candidate.next = canonicalState candidate.next.core ∧
    certificate = canonicalCertificate certificate.core


def PacketAccepted
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  binaryCheck state.core (forgetCandidate candidate) certificate.core = true ∧
    ArchitectureEvidenceValid state candidate certificate


def check
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Bool :=
  binaryCheck state.core (forgetCandidate candidate) certificate.core &&
    decide (state = canonicalState state.core) &&
    decide (candidate.update = canonicalUpdate candidate.update.core) &&
    decide (candidate.next = canonicalState candidate.next.core) &&
    decide (certificate = canonicalCertificate certificate.core)


theorem check_eq_true_iff
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) :
    check state candidate certificate = true ↔
      PacketAccepted state candidate certificate := by
  simp [check, PacketAccepted, ArchitectureEvidenceValid, and_assoc]


theorem architectureEvidence_of_check
    {state : ClassicalState}
    {candidate : Candidate ClassicalState ClassicalUpdate}
    {certificate : ClassicalCertificate}
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
          binaryKernel
          state.core
          (forgetCandidate candidate)
          certificate.core :=
      binaryChecker.sound
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
              (binaryApply state.core candidate.update.core) :=
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
      simpa [kernel, binaryKernel, protectedValue, forgetCandidate] using
        coreNonLoss ()
    · unfold ConstructiveRecovery
      simp [kernel, stateDistance, recover, binaryStateDistance]
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
    CheckerRefinement kernelRefinement checker binaryChecker where
  acceptancePreserved := by
    intro state candidate certificate accepted
    have packet : PacketAccepted state candidate certificate :=
      (check_eq_true_iff state candidate certificate).1 accepted
    exact packet.1


noncomputable def recoveryCompositionLaws :
    RecoveryCompositionLaws kernel where
  selfDistanceZero := by
    intro state
    exact binaryStateDistance_self state.core
  triangle := by
    intro x y z
    exact binaryStateDistance_triangle x.core y.core z.core
  recoverNonexpansive := by
    intro state candidate x y
    simpa [kernel, stateDistance, recover, binaryStateDistance_self] using
      binaryStateDistance_nonnegative x.core y.core


noncomputable def preservationMonitors :
    PreservationMonitors kernel (Relevance := BinaryRelevance) where
  lyapunovValue := fun state => binaryLyapunovValue state.core
  motionCharge := fun state candidate certificate =>
    binaryMotionCharge state.core (forgetCandidate candidate)
  lyapunovError := fun state candidate certificate => 0
  unsupportedCollapse := fun state candidate certificate =>
    binaryUnsupportedCollapse
      state.core (forgetCandidate candidate) certificate.core
  ambiguityError := fun state candidate certificate => 0
  relevanceValue := fun state relevance =>
    binaryRelevanceValue state.core relevance
  transportRelevance := fun state candidate relevance =>
    binaryTransportRelevance state.core (forgetCandidate candidate) relevance
  relevanceError := fun state candidate certificate => 0
  lyapunovValue_nonnegative := by
    intro state
    exact binaryLyapunovValue_nonnegative state.core
  motionCharge_nonnegative := by
    intro state candidate certificate
    exact binaryMotionCharge_nonnegative state.core (forgetCandidate candidate)
  lyapunovError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  unsupportedCollapse_nonnegative := by
    intro state candidate certificate
    exact binaryUnsupportedCollapse_nonnegative
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
    exact binaryPreservationMonitors.lyapunovStep coreObligations
  ambiguityStep := by
    intro state candidate certificate obligations
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact binaryPreservationMonitors.ambiguityStep coreObligations
  relevanceStep := by
    intro state candidate certificate obligations relevance
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact binaryPreservationMonitors.relevanceStep coreObligations relevance


noncomputable def monitorRefinement :
    MonitorRefinement
      kernelRefinement
      preservationMonitors
      binaryPreservationMonitors where
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


structure ArchitectureSuccessorObligations
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop where
  architectureEvidence : ArchitectureEvidenceValid state candidate certificate
  rclmObligations : StepObligations kernel state candidate certificate
  coreObligations :
    StepObligations
      binaryKernel
      state.core
      (forgetCandidate candidate)
      certificate.core


theorem accepted_architecture_successor
    {state : ClassicalState}
    {candidate : Candidate ClassicalState ClassicalUpdate}
    {certificate : ClassicalCertificate}
    (stateAdmissible : kernel.admissible state)
    (stateInvariant : kernel.protectedInvariant state)
    (accepted : checker.check state candidate certificate = true) :
    ArchitectureSuccessorObligations state candidate certificate := by
  have architectureEvidence :
      ArchitectureEvidenceValid state candidate certificate :=
    architectureEvidence_of_check accepted
  have rclmObligations :
      StepObligations kernel state candidate certificate :=
    checker.sound stateAdmissible stateInvariant accepted
  have coreObligations :
      StepObligations
        binaryKernel
        state.core
        (forgetCandidate candidate)
        certificate.core :=
    rclm_checker_refines_rcp
      kernelRefinement
      checker
      stateAdmissible
      stateInvariant
      accepted
  exact
    { architectureEvidence := architectureEvidence
      rclmObligations := rclmObligations
      coreObligations := coreObligations }


theorem improvement_check_accepts :
    checker.check initialState improvementCandidate improvementCertificate = true := by
  rfl


theorem improvement_refines_gate_b :
    StepObligations
      binaryKernel
      (kernelRefinement.forgetState initialState)
      (kernelRefinement.forgetCandidate improvementCandidate)
      (kernelRefinement.forgetCertificate improvementCertificate) := by
  have initialAdmissible : kernel.admissible initialState := by
    constructor
    · decide
    · rfl
  have initialInvariant : kernel.protectedInvariant initialState := by
    constructor
    · decide
    · rfl
  exact rclm_checker_refines_rcp
    kernelRefinement
    checker
    initialAdmissible
    initialInvariant
    improvement_check_accepts


theorem improvement_architecture_evidence :
    ArchitectureEvidenceValid
      initialState improvementCandidate improvementCertificate := by
  exact architectureEvidence_of_check improvement_check_accepts

end ClassicalBinary
end RCLM
end RcpRclmFormalCoreV2