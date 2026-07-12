import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCLM.ArchitectureTheorem
import RcpRclmFormalCoreV2.RCP.ClassicalBinary

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace ClassicalBinary

namespace Core := RCP.ClassicalFinite

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
    Core.BinaryState
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
    Core.BinaryUpdate
    ParameterUpdateRegister
    ArchitectureUpdateRegister
    MemoryUpdateRegister
    VerifierUpdateRegister
    SemanticUpdateRegister
    ToolUpdateRegister
    ResourceUpdateRegister

abbrev ClassicalCertificate :=
  CertificatePacket
    Core.BinaryCertificate
    SemanticEvidence
    TypeEvidence
    LedgerEvidence
    GoalTransportEvidence
    TrustEvidence
    ResourceEvidence
    RealityEvidence
    RecoveryEvidence
    ProgressEvidence


def canonicalState : Core.BinaryState → ClassicalState
  | Core.BinaryState.outside =>
      { core := Core.BinaryState.outside
        language := LanguageRegister.invalid
        worldReference := WorldReferenceRegister.absent
        humanReference := HumanReferenceRegister.absent
        definitiveness := DefinitivenessRegister.invalid
        ambiguity := AmbiguityRegister.uncontrolled
        memory := MemoryRegister.outside
        verifier := VerifierRegister.untrusted
        resources := { used := 2, limit := 1 }
        selfModel := SelfModelRegister.outside }
  | Core.BinaryState.initial =>
      { core := Core.BinaryState.initial
        language := LanguageRegister.symbolicBinary
        worldReference := WorldReferenceRegister.biasedTarget
        humanReference := HumanReferenceRegister.declaredBinaryTask
        definitiveness := DefinitivenessRegister.provisional
        ambiguity := AmbiguityRegister.bounded
        memory := MemoryRegister.initial
        verifier := VerifierRegister.trustedBinaryChecker
        resources := { used := 0, limit := 1 }
        selfModel := SelfModelRegister.initial }
  | Core.BinaryState.target =>
      { core := Core.BinaryState.target
        language := LanguageRegister.symbolicBinary
        worldReference := WorldReferenceRegister.biasedTarget
        humanReference := HumanReferenceRegister.declaredBinaryTask
        definitiveness := DefinitivenessRegister.certified
        ambiguity := AmbiguityRegister.resolved
        memory := MemoryRegister.target
        verifier := VerifierRegister.trustedBinaryChecker
        resources := { used := 1, limit := 1 }
        selfModel := SelfModelRegister.target }


def canonicalUpdate : Core.BinaryUpdate → ClassicalUpdate
  | Core.BinaryUpdate.stay =>
      { core := Core.BinaryUpdate.stay
        parameters := ParameterUpdateRegister.unchanged
        architecture := ArchitectureUpdateRegister.preserved
        memory := MemoryUpdateRegister.retained
        verifier := VerifierUpdateRegister.retained
        semantics := SemanticUpdateRegister.preserved
        tools := ToolUpdateRegister.none
        resources := ResourceUpdateRegister.bounded }
  | Core.BinaryUpdate.improve =>
      { core := Core.BinaryUpdate.improve
        parameters := ParameterUpdateRegister.targetAligned
        architecture := ArchitectureUpdateRegister.preserved
        memory := MemoryUpdateRegister.advanced
        verifier := VerifierUpdateRegister.retained
        semantics := SemanticUpdateRegister.targetAligned
        tools := ToolUpdateRegister.none
        resources := ResourceUpdateRegister.bounded }


def canonicalCertificate : Core.BinaryCertificate → ClassicalCertificate
  | Core.BinaryCertificate.improvement =>
      { core := Core.BinaryCertificate.improvement
        semantics := SemanticEvidence.coherent
        typing := TypeEvidence.typed
        ledger := LedgerEvidence.withinBudget
        goalTransport := GoalTransportEvidence.targetFixed
        trust := TrustEvidence.predecessorVerified
        resources := ResourceEvidence.bounded
        reality := RealityEvidence.contained
        recovery := RecoveryEvidence.exact
        progress := ProgressEvidence.strict }
  | Core.BinaryCertificate.stability =>
      { core := Core.BinaryCertificate.stability
        semantics := SemanticEvidence.coherent
        typing := TypeEvidence.typed
        ledger := LedgerEvidence.withinBudget
        goalTransport := GoalTransportEvidence.targetFixed
        trust := TrustEvidence.predecessorVerified
        resources := ResourceEvidence.bounded
        reality := RealityEvidence.contained
        recovery := RecoveryEvidence.exact
        progress := ProgressEvidence.stable }
  | Core.BinaryCertificate.malformed =>
      { core := Core.BinaryCertificate.malformed
        semantics := SemanticEvidence.rejected
        typing := TypeEvidence.rejected
        ledger := LedgerEvidence.rejected
        goalTransport := GoalTransportEvidence.rejected
        trust := TrustEvidence.rejected
        resources := ResourceEvidence.rejected
        reality := RealityEvidence.rejected
        recovery := RecoveryEvidence.rejected
        progress := ProgressEvidence.rejected }


def forgetCandidate
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate) :
    RCP.Candidate Core.BinaryState Core.BinaryUpdate where
  update := candidate.update.core
  next := candidate.next.core


def liftCandidate
    (candidate : RCP.Candidate Core.BinaryState Core.BinaryUpdate) :
    RCP.Candidate ClassicalState ClassicalUpdate where
  update := canonicalUpdate candidate.update
  next := canonicalState candidate.next


def apply (state : ClassicalState) (update : ClassicalUpdate) : ClassicalState :=
  canonicalState (Core.binaryApply state.core update.core)


def admissible (state : ClassicalState) : Prop :=
  state.core ≠ Core.BinaryState.outside ∧
    state = canonicalState state.core


def protectedInvariant (state : ClassicalState) : Prop :=
  state.core ≠ Core.BinaryState.outside ∧
    state = canonicalState state.core


noncomputable def protectedValue (state : ClassicalState) (_distinction : Unit) : ℝ :=
  Core.binaryProgress state.core


def stateDistance (x y : ClassicalState) : ℝ :=
  Core.binaryStateDistance x.core y.core


def recover
    (state : ClassicalState)
    (_candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (_endpoint : ClassicalState) : ClassicalState :=
  canonicalState state.core


noncomputable def progress (state : ClassicalState) : ℝ :=
  Core.binaryProgress state.core


def strictWitness
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  Core.binaryStrictWitness state.core (forgetCandidate candidate) certificate.core


def residual
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate)
    (index : Core.BinaryResidualIndex) : ℝ :=
  Core.binaryResidual state.core (forgetCandidate candidate) certificate.core index


def trustValid
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  Core.binaryTrustValid state.core (forgetCandidate candidate) certificate.core


def resourceValid
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  Core.binaryResourceValid state.core (forgetCandidate candidate) certificate.core


def realityContained
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  Core.binaryRealityContained state.core (forgetCandidate candidate) certificate.core


def initialState : ClassicalState := canonicalState Core.BinaryState.initial

def targetState : ClassicalState := canonicalState Core.BinaryState.target

def outsideState : ClassicalState := canonicalState Core.BinaryState.outside


def improvementUpdate : ClassicalUpdate := canonicalUpdate Core.BinaryUpdate.improve

def stabilityUpdate : ClassicalUpdate := canonicalUpdate Core.BinaryUpdate.stay


def improvementCertificate : ClassicalCertificate :=
  canonicalCertificate Core.BinaryCertificate.improvement


def stabilityCertificate : ClassicalCertificate :=
  canonicalCertificate Core.BinaryCertificate.stability


def malformedCertificate : ClassicalCertificate :=
  canonicalCertificate Core.BinaryCertificate.malformed


def improvementCandidate : RCP.Candidate ClassicalState ClassicalUpdate where
  update := improvementUpdate
  next := targetState


def stabilityCandidate : RCP.Candidate ClassicalState ClassicalUpdate where
  update := stabilityUpdate
  next := targetState


def invalidCandidate : RCP.Candidate ClassicalState ClassicalUpdate where
  update := improvementUpdate
  next := initialState


noncomputable def kernel :
    RCP.Kernel
      ClassicalState
      ClassicalUpdate
      ClassicalCertificate
      Unit
      Core.BinaryResidualIndex where
  apply := apply
  admissible := admissible
  protectedInvariant := protectedInvariant
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    refine ⟨initialState, (), targetState, (), ?_⟩
    change Core.binaryProgress Core.BinaryState.initial ≠
      Core.binaryProgress Core.BinaryState.target
    exact ne_of_lt Core.binaryProgress_initial_lt_target
  transportProtected := fun _state _candidate distinction => distinction
  lossBudget := fun _state _candidate => 0
  lossBudget_nonnegative := by
    intro state candidate
    exact le_rfl
  stateDistance := stateDistance
  stateDistance_nonnegative := by
    intro x y
    exact Core.binaryStateDistance_nonnegative x.core y.core
  recover := recover
  recoveryBudget := fun _state _candidate => 0
  recoveryBudget_nonnegative := by
    intro state candidate
    exact le_rfl
  progress := progress
  strictWitness := strictWitness
  residual := residual
  residual_nonconstant := by
    refine
      ⟨initialState,
        improvementCandidate,
        improvementCertificate,
        initialState,
        invalidCandidate,
        improvementCertificate,
        Core.BinaryResidualIndex.typed,
        ?_⟩
    norm_num [residual, forgetCandidate, Core.binaryResidual,
      Core.binaryApply, improvementCandidate, invalidCandidate,
      improvementUpdate, improvementCertificate, initialState,
      targetState, canonicalState, canonicalUpdate,
      canonicalCertificate]
  trustValid := trustValid
  resourceValid := resourceValid
  realityContained := realityContained
  realityContained_not_universal := by
    refine
      ⟨outsideState,
        ({ update := stabilityUpdate
           next := outsideState } :
          RCP.Candidate ClassicalState ClassicalUpdate),
        malformedCertificate,
        ?_⟩
    simp [realityContained, forgetCandidate,
      Core.binaryRealityContained, Core.binaryApply,
      outsideState, stabilityUpdate, malformedCertificate,
      canonicalState, canonicalUpdate, canonicalCertificate]


noncomputable def kernelRefinement :
    KernelRefinement kernel Core.binaryKernel where
  forgetState := fun state => state.core
  liftState := canonicalState
  forgetLiftState := by
    intro state
    cases state <;> rfl
  forgetUpdate := fun update => update.core
  liftUpdate := canonicalUpdate
  forgetLiftUpdate := by
    intro update
    cases update <;> rfl
  forgetCertificate := fun certificate => certificate.core
  liftCertificate := canonicalCertificate
  forgetLiftCertificate := by
    intro certificate
    cases certificate <;> rfl
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
    rfl
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
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  state = canonicalState state.core ∧
    candidate.update = canonicalUpdate candidate.update.core ∧
    candidate.next = canonicalState candidate.next.core ∧
    certificate = canonicalCertificate certificate.core


def PacketAccepted
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop :=
  Core.binaryCheck state.core (forgetCandidate candidate) certificate.core = true ∧
    ArchitectureEvidenceValid state candidate certificate


def check
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Bool :=
  Core.binaryCheck state.core (forgetCandidate candidate) certificate.core &&
    decide (state = canonicalState state.core) &&
    decide (candidate.update = canonicalUpdate candidate.update.core) &&
    decide (candidate.next = canonicalState candidate.next.core) &&
    decide (certificate = canonicalCertificate certificate.core)


theorem check_eq_true_iff
    (state : ClassicalState)
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) :
    check state candidate certificate = true ↔
      PacketAccepted state candidate certificate := by
  simp [check, PacketAccepted, ArchitectureEvidenceValid, and_assoc]


theorem architectureEvidence_of_check
    {state : ClassicalState}
    {candidate : RCP.Candidate ClassicalState ClassicalUpdate}
    {certificate : ClassicalCertificate}
    (accepted : check state candidate certificate = true) :
    ArchitectureEvidenceValid state candidate certificate := by
  exact (check_eq_true_iff state candidate certificate).1 accepted |>.2


noncomputable def checker : RCP.TrustedChecker kernel where
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
        RCP.StepObligations
          Core.binaryKernel
          state.core
          (forgetCandidate candidate)
          certificate.core :=
      Core.binaryChecker.sound
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
      unfold RCP.TypedSuccessor at coreTyped
      unfold RCP.TypedSuccessor
      calc
        candidate.next = canonicalState candidate.next.core := nextCanonical
        _ = canonicalState
              (Core.binaryApply state.core candidate.update.core) :=
          congrArg canonicalState coreTyped
        _ = kernel.apply state candidate.update := by
          rfl
    · intro index
      exact coreObligations.residualsNonpositive index
    · have coreNonLoss := coreObligations.protectedNonLoss
      unfold RCP.ProtectedNonLoss at coreNonLoss
      unfold RCP.ProtectedNonLoss
      intro distinction
      cases distinction
      simpa [kernel, protectedValue, forgetCandidate] using coreNonLoss ()
    · unfold RCP.ConstructiveRecovery
      simp [kernel, stateDistance, recover, Core.binaryStateDistance]
    · change candidate.next.core ≠ Core.BinaryState.outside ∧
        candidate.next = canonicalState candidate.next.core
      exact ⟨coreObligations.invariantPreserved, nextCanonical⟩
    · exact coreObligations.progressNondecreasing
    · exact coreObligations.strictProgressWhenWitness
    · exact coreObligations.trustValid
    · exact coreObligations.resourceValid
    · exact coreObligations.realityContained
    · change candidate.next.core ≠ Core.BinaryState.outside ∧
        candidate.next = canonicalState candidate.next.core
      exact ⟨coreObligations.successorAdmissible, nextCanonical⟩


noncomputable def checkerRefinement :
    CheckerRefinement kernelRefinement checker Core.binaryChecker where
  acceptancePreserved := by
    intro state candidate certificate accepted
    exact (check_eq_true_iff state candidate certificate).1 accepted |>.1


noncomputable def recoveryCompositionLaws :
    RCP.RecoveryCompositionLaws kernel where
  selfDistanceZero := by
    intro state
    exact Core.binaryStateDistance_self state.core
  triangle := by
    intro x y z
    exact Core.binaryStateDistance_triangle x.core y.core z.core
  recoverNonexpansive := by
    intro state candidate x y
    change Core.binaryStateDistance state.core state.core ≤
      Core.binaryStateDistance x.core y.core
    rw [Core.binaryStateDistance_self]
    exact Core.binaryStateDistance_nonnegative x.core y.core


noncomputable def preservationMonitors :
    RCP.PreservationMonitors kernel (Relevance := Core.BinaryRelevance) where
  lyapunovValue := fun state => Core.binaryLyapunovValue state.core
  motionCharge := fun state candidate certificate =>
    Core.binaryMotionCharge state.core (forgetCandidate candidate)
  lyapunovError := fun state candidate certificate => 0
  unsupportedCollapse := fun state candidate certificate =>
    Core.binaryUnsupportedCollapse
      state.core (forgetCandidate candidate) certificate.core
  ambiguityError := fun state candidate certificate => 0
  relevanceValue := fun state relevance =>
    Core.binaryRelevanceValue state.core relevance
  transportRelevance := fun state candidate relevance =>
    Core.binaryTransportRelevance state.core (forgetCandidate candidate) relevance
  relevanceError := fun state candidate certificate => 0
  lyapunovValue_nonnegative := by
    intro state
    exact Core.binaryLyapunovValue_nonnegative state.core
  motionCharge_nonnegative := by
    intro state candidate certificate
    exact Core.binaryMotionCharge_nonnegative state.core (forgetCandidate candidate)
  lyapunovError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  unsupportedCollapse_nonnegative := by
    intro state candidate certificate
    exact Core.binaryUnsupportedCollapse_nonnegative
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
    exact Core.binaryPreservationMonitors.lyapunovStep coreObligations
  ambiguityStep := by
    intro state candidate certificate obligations
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact Core.binaryPreservationMonitors.ambiguityStep coreObligations
  relevanceStep := by
    intro state candidate certificate obligations relevance
    have coreObligations := kernelRefinement.stepObligationsPreserved obligations
    exact Core.binaryPreservationMonitors.relevanceStep coreObligations relevance


noncomputable def monitorRefinement :
    MonitorRefinement
      kernelRefinement
      preservationMonitors
      Core.binaryPreservationMonitors where
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
    (candidate : RCP.Candidate ClassicalState ClassicalUpdate)
    (certificate : ClassicalCertificate) : Prop where
  architectureEvidence : ArchitectureEvidenceValid state candidate certificate
  rclmObligations : RCP.StepObligations kernel state candidate certificate
  coreObligations :
    RCP.StepObligations
      Core.binaryKernel
      state.core
      (forgetCandidate candidate)
      certificate.core


theorem accepted_architecture_successor
    {state : ClassicalState}
    {candidate : RCP.Candidate ClassicalState ClassicalUpdate}
    {certificate : ClassicalCertificate}
    (stateAdmissible : kernel.admissible state)
    (stateInvariant : kernel.protectedInvariant state)
    (accepted : checker.check state candidate certificate = true) :
    ArchitectureSuccessorObligations state candidate certificate := by
  have architectureEvidence :
      ArchitectureEvidenceValid state candidate certificate :=
    architectureEvidence_of_check accepted
  have rclmObligations :
      RCP.StepObligations kernel state candidate certificate :=
    checker.sound stateAdmissible stateInvariant accepted
  have coreObligations :
      RCP.StepObligations
        Core.binaryKernel
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


def trajectoryState : Nat → ClassicalState
  | 0 => initialState
  | _ + 1 => targetState


def trajectoryCandidate :
    Nat → RCP.Candidate ClassicalState ClassicalUpdate
  | 0 => improvementCandidate
  | _ + 1 => stabilityCandidate


def trajectoryCertificate : Nat → ClassicalCertificate
  | 0 => improvementCertificate
  | _ + 1 => stabilityCertificate


noncomputable def workedTrajectory :
    RCP.FiniteAcceptedTrajectory checker 2 where
  state := trajectoryState
  candidate := trajectoryCandidate
  certificate := trajectoryCertificate
  initialAdmissible := by
    constructor
    · decide
    · rfl
  initialInvariant := by
    constructor
    · decide
    · rfl
  accepted := by
    intro t bound
    cases t with
    | zero =>
        rfl
    | succ t =>
        rfl
  linked := by
    intro t bound
    cases t with
    | zero =>
        rfl
    | succ t =>
        rfl


theorem workedTrajectory_first_step_strict :
    kernel.progress (workedTrajectory.state 0) <
      kernel.progress (workedTrajectory.state 1) := by
  change Core.binaryProgress Core.BinaryState.initial <
    Core.binaryProgress Core.BinaryState.target
  exact Core.binaryProgress_initial_lt_target


theorem workedTrajectory_endpoint_recovery :
    kernel.stateDistance
        (RCP.composedRecovery workedTrajectory 2
          (workedTrajectory.state 2))
        (workedTrajectory.state 0) ≤
      RCP.cumulativeRecoveryBudget workedTrajectory 2 := by
  exact RCP.finite_endpoint_recovery_bound
    checker
    recoveryCompositionLaws
    workedTrajectory
    2
    le_rfl


theorem workedTrajectory_lyapunov_motion_bound :
    preservationMonitors.lyapunovValue
          (workedTrajectory.state 2) +
        RCP.cumulativeMotionCharge
          preservationMonitors workedTrajectory 2 ≤
      preservationMonitors.lyapunovValue
          (workedTrajectory.state 0) +
        RCP.cumulativeLyapunovError
          preservationMonitors workedTrajectory 2 := by
  exact RCP.finite_lyapunov_motion_bound
    checker
    preservationMonitors
    workedTrajectory
    2
    le_rfl


theorem workedTrajectory_ambiguity_bound :
    RCP.cumulativeUnsupportedCollapse
        preservationMonitors workedTrajectory 2 ≤
      RCP.cumulativeAmbiguityError
        preservationMonitors workedTrajectory 2 := by
  exact RCP.finite_ambiguity_collapse_bound
    checker
    preservationMonitors
    workedTrajectory
    2
    le_rfl


theorem workedTrajectory_relevance_bound
    (relevance : Core.BinaryRelevance) :
    preservationMonitors.relevanceValue
        (workedTrajectory.state 0) relevance ≤
      preservationMonitors.relevanceValue
          (workedTrajectory.state 2)
          (RCP.transportedRelevance
            preservationMonitors workedTrajectory 2 relevance) +
        RCP.cumulativeRelevanceError
          preservationMonitors workedTrajectory 2 := by
  exact RCP.finite_self_model_relevance_bound
    checker
    preservationMonitors
    workedTrajectory
    2
    le_rfl
    relevance

end ClassicalBinary
end RCLM
end RcpRclmFormalCoreV2
