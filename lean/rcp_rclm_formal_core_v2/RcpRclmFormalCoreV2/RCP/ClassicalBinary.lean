import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.Monitors

namespace RcpRclmFormalCoreV2
namespace RCP
namespace ClassicalFinite

inductive BinaryState where
  | outside
  | initial
  | target
  deriving DecidableEq

inductive BinaryUpdate where
  | stay
  | improve
  deriving DecidableEq

inductive BinaryCertificate where
  | improvement
  | stability
  | malformed
  deriving DecidableEq

inductive BinaryResidualIndex where
  | typed
  | packet
  deriving DecidableEq

noncomputable def binaryGap : ℝ :=
  positiveKLDivergence uniformBinary biasedBinary

theorem binaryGap_pos : 0 < binaryGap :=
  uniformBinary_kl_biasedBinary_pos

noncomputable def binaryStateDistribution :
    BinaryState → PositiveDistribution 2
  | BinaryState.outside => uniformBinary
  | BinaryState.initial => uniformBinary
  | BinaryState.target => biasedBinary

noncomputable def binaryProgress (state : BinaryState) : ℝ :=
  binaryGap -
    positiveKLDivergence (binaryStateDistribution state) biasedBinary

theorem binaryProgress_initial :
    binaryProgress BinaryState.initial = 0 := by
  simp [binaryProgress, binaryGap, binaryStateDistribution]

theorem binaryProgress_target :
    binaryProgress BinaryState.target = binaryGap := by
  simp [binaryProgress, binaryStateDistribution,
    positiveKLDivergence_self]

theorem binaryProgress_initial_lt_target :
    binaryProgress BinaryState.initial <
      binaryProgress BinaryState.target := by
  rw [binaryProgress_initial, binaryProgress_target]
  exact binaryGap_pos

def binaryApply : BinaryState → BinaryUpdate → BinaryState
  | BinaryState.outside, BinaryUpdate.stay => BinaryState.outside
  | BinaryState.outside, BinaryUpdate.improve => BinaryState.outside
  | BinaryState.initial, BinaryUpdate.stay => BinaryState.initial
  | BinaryState.initial, BinaryUpdate.improve => BinaryState.target
  | BinaryState.target, BinaryUpdate.stay => BinaryState.target
  | BinaryState.target, BinaryUpdate.improve => BinaryState.target

def improvementCandidate : Candidate BinaryState BinaryUpdate where
  update := BinaryUpdate.improve
  next := BinaryState.target

def stabilityCandidate : Candidate BinaryState BinaryUpdate where
  update := BinaryUpdate.stay
  next := BinaryState.target

def invalidCandidate : Candidate BinaryState BinaryUpdate where
  update := BinaryUpdate.improve
  next := BinaryState.initial

def ImprovementPacket
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  state = BinaryState.initial ∧
    candidate.update = BinaryUpdate.improve ∧
    candidate.next = BinaryState.target ∧
    certificate = BinaryCertificate.improvement

def StabilityPacket
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  state = BinaryState.target ∧
    candidate.update = BinaryUpdate.stay ∧
    candidate.next = BinaryState.target ∧
    certificate = BinaryCertificate.stability

def binaryCheck
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Bool :=
  (decide (state = BinaryState.initial) &&
      decide (candidate.update = BinaryUpdate.improve) &&
      decide (candidate.next = BinaryState.target) &&
      decide (certificate = BinaryCertificate.improvement)) ||
    (decide (state = BinaryState.target) &&
      decide (candidate.update = BinaryUpdate.stay) &&
      decide (candidate.next = BinaryState.target) &&
      decide (certificate = BinaryCertificate.stability))

theorem binaryCheck_eq_true_iff
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) :
    binaryCheck state candidate certificate = true ↔
      ImprovementPacket state candidate certificate ∨
        StabilityPacket state candidate certificate := by
  simp [binaryCheck, ImprovementPacket, StabilityPacket,
    and_assoc]

theorem binaryCheck_rejects_invalidCandidate :
    binaryCheck
      BinaryState.initial
      invalidCandidate
      BinaryCertificate.improvement = false := by
  rfl

def binaryStateDistance (x y : BinaryState) : ℝ :=
  if x = y then 0 else 1

theorem binaryStateDistance_nonnegative (x y : BinaryState) :
    0 ≤ binaryStateDistance x y := by
  by_cases hxy : x = y
  · simp [binaryStateDistance, hxy]
  · simp [binaryStateDistance, hxy]

theorem binaryStateDistance_self (state : BinaryState) :
    binaryStateDistance state state = 0 := by
  simp [binaryStateDistance]

theorem binaryStateDistance_triangle (x y z : BinaryState) :
    binaryStateDistance x z ≤
      binaryStateDistance x y + binaryStateDistance y z := by
  cases x <;> cases y <;> cases z <;>
    norm_num [binaryStateDistance]

def binaryResidual
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) :
    BinaryResidualIndex → ℝ
  | BinaryResidualIndex.typed =>
      if candidate.next = binaryApply state candidate.update then -1 else 1
  | BinaryResidualIndex.packet =>
      if binaryCheck state candidate certificate = true then -1 else 1

def binaryStrictWitness
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  ImprovementPacket state candidate certificate

def binaryTrustValid
    (state : BinaryState)
    (_candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  state ≠ BinaryState.outside ∧
    certificate ≠ BinaryCertificate.malformed

def binaryResourceValid
    (_state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  (certificate = BinaryCertificate.improvement →
      candidate.update = BinaryUpdate.improve) ∧
    (certificate = BinaryCertificate.stability →
      candidate.update = BinaryUpdate.stay) ∧
    certificate ≠ BinaryCertificate.malformed

def binaryRealityContained
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (_certificate : BinaryCertificate) : Prop :=
  candidate.next ≠ BinaryState.outside ∧
    candidate.next = binaryApply state candidate.update

noncomputable def binaryKernel :
    Kernel
      BinaryState
      BinaryUpdate
      BinaryCertificate
      Unit
      BinaryResidualIndex where
  apply := binaryApply
  admissible := fun state => state ≠ BinaryState.outside
  protectedInvariant := fun state => state ≠ BinaryState.outside
  protectedValue := fun state _ => binaryProgress state
  protectedValue_nonconstant := by
    refine
      ⟨BinaryState.initial, (), BinaryState.target, (), ?_⟩
    rw [binaryProgress_initial, binaryProgress_target]
    exact ne_of_lt binaryGap_pos
  transportProtected := fun _ _ distinction => distinction
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := fun _ _ => le_rfl
  stateDistance := binaryStateDistance
  stateDistance_nonnegative := fun x y =>
    binaryStateDistance_nonnegative x y
  recover := fun state _ _ => state
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := fun _ _ => le_rfl
  progress := binaryProgress
  strictWitness := binaryStrictWitness
  residual := binaryResidual
  residual_nonconstant := by
    have initial_ne_target :
        BinaryState.initial ≠ BinaryState.target := by
      decide
    refine
      ⟨BinaryState.initial,
        improvementCandidate,
        BinaryCertificate.improvement,
        BinaryState.initial,
        invalidCandidate,
        BinaryCertificate.improvement,
        BinaryResidualIndex.typed,
        ?_⟩
    norm_num [binaryResidual, binaryApply,
      improvementCandidate, invalidCandidate, initial_ne_target]
  trustValid := binaryTrustValid
  resourceValid := binaryResourceValid
  realityContained := binaryRealityContained
  realityContained_not_universal := by
    refine
      ⟨BinaryState.outside,
        ({ update := BinaryUpdate.stay
           next := BinaryState.outside } :
          Candidate BinaryState BinaryUpdate),
        BinaryCertificate.malformed,
        ?_⟩
    simp [binaryRealityContained]

noncomputable def binaryRecoveryCompositionLaws :
    RecoveryCompositionLaws binaryKernel where
  selfDistanceZero := by
    intro state
    exact binaryStateDistance_self state
  triangle := by
    intro x y z
    exact binaryStateDistance_triangle x y z
  recoverNonexpansive := by
    intro state candidate x y
    change binaryStateDistance state state ≤ binaryStateDistance x y
    rw [binaryStateDistance_self]
    exact binaryStateDistance_nonnegative x y

theorem initial_improvement_obligations :
    StepObligations
      binaryKernel
      BinaryState.initial
      improvementCandidate
      BinaryCertificate.improvement := by
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
  · rfl
  · intro index
    cases index with
    | typed =>
        norm_num [binaryKernel, binaryResidual,
          binaryApply, improvementCandidate]
    | packet =>
        norm_num [binaryKernel, binaryResidual, binaryCheck,
          improvementCandidate]
  · unfold ProtectedNonLoss
    intro distinction
    cases distinction
    change
      binaryProgress BinaryState.initial ≤
        binaryProgress BinaryState.target + 0
    rw [binaryProgress_initial, binaryProgress_target]
    simpa using binaryGap_pos.le
  · unfold ConstructiveRecovery
    simp [binaryKernel, binaryStateDistance]
  · simp [binaryKernel, improvementCandidate]
  · unfold ProgressNondecreasing
    change
      binaryProgress BinaryState.initial ≤
        binaryProgress BinaryState.target
    exact binaryProgress_initial_lt_target.le
  · unfold StrictProgressWhenWitness
    intro _strictWitness
    exact binaryProgress_initial_lt_target
  · simp [binaryKernel, binaryTrustValid]
  · simp [binaryKernel, binaryResourceValid, improvementCandidate]
  · simp [binaryKernel, binaryRealityContained,
      binaryApply, improvementCandidate]
  · simp [binaryKernel, improvementCandidate]

theorem target_stability_obligations :
    StepObligations
      binaryKernel
      BinaryState.target
      stabilityCandidate
      BinaryCertificate.stability := by
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
  · rfl
  · intro index
    cases index with
    | typed =>
        norm_num [binaryKernel, binaryResidual,
          binaryApply, stabilityCandidate]
    | packet =>
        norm_num [binaryKernel, binaryResidual, binaryCheck,
          stabilityCandidate]
  · unfold ProtectedNonLoss
    intro distinction
    cases distinction
    change
      binaryProgress BinaryState.target ≤
        binaryProgress BinaryState.target + 0
    simp
  · unfold ConstructiveRecovery
    simp [binaryKernel, binaryStateDistance]
  · simp [binaryKernel, stabilityCandidate]
  · unfold ProgressNondecreasing
    exact le_rfl
  · unfold StrictProgressWhenWitness
    intro strictWitness
    simp [binaryKernel, binaryStrictWitness,
      ImprovementPacket, stabilityCandidate] at strictWitness
  · simp [binaryKernel, binaryTrustValid]
  · simp [binaryKernel, binaryResourceValid, stabilityCandidate]
  · simp [binaryKernel, binaryRealityContained,
      binaryApply, stabilityCandidate]
  · simp [binaryKernel, stabilityCandidate]

noncomputable def binaryChecker : TrustedChecker binaryKernel where
  check := binaryCheck
  sound := by
    intro state candidate certificate
      _stateAdmissible _stateInvariant accepted
    have acceptedCases :
        ImprovementPacket state candidate certificate ∨
          StabilityPacket state candidate certificate :=
      (binaryCheck_eq_true_iff state candidate certificate).1 accepted
    rcases acceptedCases with improvement | stability
    · rcases improvement with
        ⟨stateEq, updateEq, nextEq, certificateEq⟩
      subst state
      subst certificate
      cases candidate with
      | mk update next =>
          dsimp at updateEq nextEq
          subst update
          subst next
          exact initial_improvement_obligations
    · rcases stability with
        ⟨stateEq, updateEq, nextEq, certificateEq⟩
      subst state
      subst certificate
      cases candidate with
      | mk update next =>
          dsimp at updateEq nextEq
          subst update
          subst next
          exact target_stability_obligations

theorem binary_checker_refines_kernel
    {state : BinaryState}
    {candidate : Candidate BinaryState BinaryUpdate}
    {certificate : BinaryCertificate}
    (stateAdmissible : binaryKernel.admissible state)
    (stateInvariant : binaryKernel.protectedInvariant state)
    (accepted : binaryChecker.check state candidate certificate = true) :
    StepObligations binaryKernel state candidate certificate := by
  exact accepted_step_sound
    binaryChecker stateAdmissible stateInvariant accepted

noncomputable def binaryLyapunovValue (state : BinaryState) : ℝ :=
  positiveKLDivergence (binaryStateDistribution state) biasedBinary

noncomputable def binaryMotionCharge
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate) : ℝ :=
  if binaryProgress state ≤ binaryProgress candidate.next then
    binaryProgress candidate.next - binaryProgress state
  else
    0

def binaryUnsupportedCollapse
    (_state : BinaryState)
    (_candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : ℝ :=
  if certificate = BinaryCertificate.malformed then 1 else 0

inductive BinaryRelevance where
  | targetFit
  | normalization
  deriving DecidableEq

def binaryRelevanceValue
    (state : BinaryState) : BinaryRelevance → ℝ
  | BinaryRelevance.targetFit => binaryProgress state
  | BinaryRelevance.normalization => 1

def binaryTransportRelevance
    (_state : BinaryState)
    (_candidate : Candidate BinaryState BinaryUpdate)
    (relevance : BinaryRelevance) : BinaryRelevance :=
  relevance

theorem binaryLyapunovValue_nonnegative (state : BinaryState) :
    0 ≤ binaryLyapunovValue state := by
  exact positiveKLDivergence_nonnegative
    (binaryStateDistribution state) biasedBinary

theorem binaryMotionCharge_nonnegative
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate) :
    0 ≤ binaryMotionCharge state candidate := by
  by_cases hProgress :
      binaryProgress state ≤ binaryProgress candidate.next
  · rw [binaryMotionCharge, if_pos hProgress]
    exact sub_nonneg.mpr hProgress
  · rw [binaryMotionCharge, if_neg hProgress]

theorem binaryLyapunov_motion_step
    {state : BinaryState}
    {candidate : Candidate BinaryState BinaryUpdate}
    {certificate : BinaryCertificate}
    (obligations :
      StepObligations binaryKernel state candidate certificate) :
    binaryLyapunovValue candidate.next +
        binaryMotionCharge state candidate ≤
      binaryLyapunovValue state := by
  have hProgress :
      binaryProgress state ≤ binaryProgress candidate.next := by
    exact obligations.progressNondecreasing
  rw [binaryMotionCharge, if_pos hProgress]
  calc
    binaryLyapunovValue candidate.next +
        (binaryProgress candidate.next - binaryProgress state) =
      binaryLyapunovValue state := by
        unfold binaryProgress binaryLyapunovValue
        ring
    _ ≤ binaryLyapunovValue state := le_rfl

theorem binaryUnsupportedCollapse_nonnegative
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) :
    0 ≤ binaryUnsupportedCollapse state candidate certificate := by
  by_cases hMalformed : certificate = BinaryCertificate.malformed
  · simp [binaryUnsupportedCollapse, hMalformed]
  · simp [binaryUnsupportedCollapse, hMalformed]

theorem binaryUnsupportedCollapse_step
    {state : BinaryState}
    {candidate : Candidate BinaryState BinaryUpdate}
    {certificate : BinaryCertificate}
    (obligations :
      StepObligations binaryKernel state candidate certificate) :
    binaryUnsupportedCollapse state candidate certificate ≤ 0 := by
  have trustEvidence :
      binaryTrustValid state candidate certificate := by
    exact obligations.trustValid
  have certificateNotMalformed :
      certificate ≠ BinaryCertificate.malformed :=
    trustEvidence.2
  simp [binaryUnsupportedCollapse, certificateNotMalformed]

theorem binaryRelevance_step
    {state : BinaryState}
    {candidate : Candidate BinaryState BinaryUpdate}
    {certificate : BinaryCertificate}
    (obligations :
      StepObligations binaryKernel state candidate certificate)
    (relevance : BinaryRelevance) :
    binaryRelevanceValue state relevance ≤
      binaryRelevanceValue candidate.next
        (binaryTransportRelevance state candidate relevance) := by
  cases relevance with
  | targetFit =>
      change binaryProgress state ≤ binaryProgress candidate.next
      exact obligations.progressNondecreasing
  | normalization =>
      exact le_rfl

noncomputable def binaryPreservationMonitors :
    PreservationMonitors binaryKernel (Relevance := BinaryRelevance) where
  lyapunovValue := binaryLyapunovValue
  motionCharge := fun state candidate _certificate =>
    binaryMotionCharge state candidate
  lyapunovError := fun _state _candidate _certificate => 0
  unsupportedCollapse := binaryUnsupportedCollapse
  ambiguityError := fun _state _candidate _certificate => 0
  relevanceValue := binaryRelevanceValue
  transportRelevance := binaryTransportRelevance
  relevanceError := fun _state _candidate _certificate => 0
  lyapunovValue_nonnegative := binaryLyapunovValue_nonnegative
  motionCharge_nonnegative := by
    intro state candidate certificate
    exact binaryMotionCharge_nonnegative state candidate
  lyapunovError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  unsupportedCollapse_nonnegative :=
    binaryUnsupportedCollapse_nonnegative
  ambiguityError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  relevanceError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  lyapunovStep := by
    intro state candidate certificate obligations
    change
      binaryLyapunovValue candidate.next +
          binaryMotionCharge state candidate ≤
        binaryLyapunovValue state + 0
    simpa using binaryLyapunov_motion_step obligations
  ambiguityStep := by
    intro state candidate certificate obligations
    change binaryUnsupportedCollapse state candidate certificate ≤ 0
    exact binaryUnsupportedCollapse_step obligations
  relevanceStep := by
    intro state candidate certificate obligations relevance
    change
      binaryRelevanceValue state relevance ≤
        binaryRelevanceValue candidate.next
            (binaryTransportRelevance state candidate relevance) + 0
    simpa using binaryRelevance_step obligations relevance

def binaryTrajectoryState : Nat → BinaryState
  | 0 => BinaryState.initial
  | _ + 1 => BinaryState.target

def binaryTrajectoryCandidate :
    Nat → Candidate BinaryState BinaryUpdate
  | 0 => improvementCandidate
  | _ + 1 => stabilityCandidate

def binaryTrajectoryCertificate : Nat → BinaryCertificate
  | 0 => BinaryCertificate.improvement
  | _ + 1 => BinaryCertificate.stability

noncomputable def binaryWorkedTrajectory :
    FiniteAcceptedTrajectory binaryChecker 2 where
  state := binaryTrajectoryState
  candidate := binaryTrajectoryCandidate
  certificate := binaryTrajectoryCertificate
  initialAdmissible := by
    simp [binaryKernel, binaryTrajectoryState]
  initialInvariant := by
    simp [binaryKernel, binaryTrajectoryState]
  accepted := by
    intro t _bound
    cases t with
    | zero =>
        rfl
    | succ t =>
        rfl
  linked := by
    intro t _bound
    cases t with
    | zero =>
        rfl
    | succ t =>
        rfl

theorem binaryWorkedTrajectory_first_step_strict :
    binaryKernel.progress (binaryWorkedTrajectory.state 0) <
      binaryKernel.progress (binaryWorkedTrajectory.state 1) := by
  change
    binaryProgress BinaryState.initial <
      binaryProgress BinaryState.target
  exact binaryProgress_initial_lt_target

theorem binaryWorkedTrajectory_endpoint_recovery :
    binaryKernel.stateDistance
        (composedRecovery binaryWorkedTrajectory 2
          (binaryWorkedTrajectory.state 2))
        (binaryWorkedTrajectory.state 0) ≤
      cumulativeRecoveryBudget binaryWorkedTrajectory 2 := by
  exact finite_endpoint_recovery_bound
    binaryChecker
    binaryRecoveryCompositionLaws
    binaryWorkedTrajectory
    2
    le_rfl

theorem binaryWorkedTrajectory_lyapunov_motion_bound :
    binaryPreservationMonitors.lyapunovValue
          (binaryWorkedTrajectory.state 2) +
        cumulativeMotionCharge
          binaryPreservationMonitors binaryWorkedTrajectory 2 ≤
      binaryPreservationMonitors.lyapunovValue
          (binaryWorkedTrajectory.state 0) +
        cumulativeLyapunovError
          binaryPreservationMonitors binaryWorkedTrajectory 2 := by
  exact finite_lyapunov_motion_bound
    binaryChecker
    binaryPreservationMonitors
    binaryWorkedTrajectory
    2
    le_rfl

theorem binaryWorkedTrajectory_ambiguity_bound :
    cumulativeUnsupportedCollapse
        binaryPreservationMonitors binaryWorkedTrajectory 2 ≤
      cumulativeAmbiguityError
        binaryPreservationMonitors binaryWorkedTrajectory 2 := by
  exact finite_ambiguity_collapse_bound
    binaryChecker
    binaryPreservationMonitors
    binaryWorkedTrajectory
    2
    le_rfl

theorem binaryWorkedTrajectory_relevance_bound
    (relevance : BinaryRelevance) :
    binaryPreservationMonitors.relevanceValue
        (binaryWorkedTrajectory.state 0) relevance ≤
      binaryPreservationMonitors.relevanceValue
          (binaryWorkedTrajectory.state 2)
          (transportedRelevance
            binaryPreservationMonitors binaryWorkedTrajectory 2 relevance) +
        cumulativeRelevanceError
          binaryPreservationMonitors binaryWorkedTrajectory 2 := by
  exact finite_self_model_relevance_bound
    binaryChecker
    binaryPreservationMonitors
    binaryWorkedTrajectory
    2
    le_rfl
    relevance

end ClassicalFinite
end RCP
end RcpRclmFormalCoreV2