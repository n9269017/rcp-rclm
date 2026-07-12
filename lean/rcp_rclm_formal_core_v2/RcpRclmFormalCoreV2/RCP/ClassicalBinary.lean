import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.Trajectory

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

def binaryStateDistance (x y : BinaryState) : ℝ :=
  if x = y then 0 else 1

theorem binaryStateDistance_nonnegative (x y : BinaryState) :
    0 ≤ binaryStateDistance x y := by
  by_cases hxy : x = y
  · simp [binaryStateDistance, hxy]
  · simp [binaryStateDistance, hxy]

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
      improvementCandidate, invalidCandidate]
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
    exact binaryGap_pos.le
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
    exact le_rfl
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

end ClassicalFinite
end RCP
end RcpRclmFormalCoreV2
