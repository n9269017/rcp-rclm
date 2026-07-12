import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.Trajectory

namespace RcpRclmFormalCoreV2
namespace RCP
namespace ClassicalFinite

inductive BinaryState where
  | unsafe
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
  | .unsafe => uniformBinary
  | .initial => uniformBinary
  | .target => biasedBinary

noncomputable def binaryProgress (state : BinaryState) : ℝ :=
  binaryGap -
    positiveKLDivergence (binaryStateDistribution state) biasedBinary

theorem binaryProgress_initial :
    binaryProgress .initial = 0 := by
  simp [binaryProgress, binaryGap, binaryStateDistribution]

theorem binaryProgress_target :
    binaryProgress .target = binaryGap := by
  simp [binaryProgress, binaryStateDistribution,
    positiveKLDivergence_self]

theorem binaryProgress_initial_lt_target :
    binaryProgress .initial < binaryProgress .target := by
  rw [binaryProgress_initial, binaryProgress_target]
  exact binaryGap_pos

def binaryApply : BinaryState → BinaryUpdate → BinaryState
  | .unsafe, .stay => .unsafe
  | .unsafe, .improve => .unsafe
  | .initial, .stay => .initial
  | .initial, .improve => .target
  | .target, .stay => .target
  | .target, .improve => .target

def improvementCandidate : Candidate BinaryState BinaryUpdate where
  update := .improve
  next := .target

def stabilityCandidate : Candidate BinaryState BinaryUpdate where
  update := .stay
  next := .target

def invalidCandidate : Candidate BinaryState BinaryUpdate where
  update := .improve
  next := .initial

def ImprovementPacket
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  state = .initial ∧
    candidate.update = .improve ∧
    candidate.next = .target ∧
    certificate = .improvement

def StabilityPacket
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  state = .target ∧
    candidate.update = .stay ∧
    candidate.next = .target ∧
    certificate = .stability

def binaryCheck
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Bool :=
  decide (ImprovementPacket state candidate certificate) ||
    decide (StabilityPacket state candidate certificate)

theorem binaryCheck_eq_true_iff
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) :
    binaryCheck state candidate certificate = true ↔
      ImprovementPacket state candidate certificate ∨
        StabilityPacket state candidate certificate := by
  simp [binaryCheck]

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
  | .typed =>
      if candidate.next = binaryApply state candidate.update then -1 else 1
  | .packet =>
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
  state ≠ .unsafe ∧ certificate ≠ .malformed

def binaryResourceValid
    (_state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (certificate : BinaryCertificate) : Prop :=
  (certificate = .improvement → candidate.update = .improve) ∧
    (certificate = .stability → candidate.update = .stay) ∧
    certificate ≠ .malformed

def binaryRealityContained
    (state : BinaryState)
    (candidate : Candidate BinaryState BinaryUpdate)
    (_certificate : BinaryCertificate) : Prop :=
  candidate.next ≠ .unsafe ∧
    candidate.next = binaryApply state candidate.update

noncomputable def binaryKernel :
    Kernel
      BinaryState
      BinaryUpdate
      BinaryCertificate
      Unit
      BinaryResidualIndex where
  apply := binaryApply
  admissible := fun state => state ≠ .unsafe
  protectedInvariant := fun state => state ≠ .unsafe
  protectedValue := fun state _ => binaryProgress state
  protectedValue_nonconstant := by
    refine ⟨.initial, (), .target, (), ?_⟩
    rw [binaryProgress_initial, binaryProgress_target]
    exact ne_of_lt binaryGap_pos
  transportProtected := fun _ _ distinction => distinction
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := fun _ _ => le_rfl
  stateDistance := binaryStateDistance
  stateDistance_nonnegative := binaryStateDistance_nonnegative
  recover := fun state _ _ => state
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := fun _ _ => le_rfl
  progress := binaryProgress
  strictWitness := binaryStrictWitness
  residual := binaryResidual
  residual_nonconstant := by
    refine
      ⟨.initial, improvementCandidate, .improvement,
        .initial, invalidCandidate, .improvement, .typed, ?_⟩
    norm_num [binaryResidual, binaryApply,
      improvementCandidate, invalidCandidate]
  trustValid := binaryTrustValid
  resourceValid := binaryResourceValid
  realityContained := binaryRealityContained
  realityContained_not_universal := by
    refine
      ⟨.unsafe,
        { update := .stay, next := .unsafe },
        .malformed,
        ?_⟩
    simp [binaryRealityContained]

theorem initial_improvement_obligations :
    StepObligations
      binaryKernel
      .initial
      improvementCandidate
      .improvement := by
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
          ImprovementPacket, StabilityPacket, improvementCandidate]
  · unfold ProtectedNonLoss
    intro distinction
    cases distinction
    change binaryProgress .initial ≤ binaryProgress .target + 0
    rw [binaryProgress_initial, binaryProgress_target]
    exact binaryGap_pos.le
  · unfold ConstructiveRecovery
    simp [binaryKernel, binaryStateDistance]
  · simp [binaryKernel, improvementCandidate]
  · unfold ProgressNondecreasing
    change binaryProgress .initial ≤ binaryProgress .target
    exact binaryProgress_initial_lt_target.le
  · unfold StrictProgressWhenWitness
    intro _
    exact binaryProgress_initial_lt_target
  · simp [binaryKernel, binaryTrustValid]
  · simp [binaryKernel, binaryResourceValid, improvementCandidate]
  · simp [binaryKernel, binaryRealityContained,
      binaryApply, improvementCandidate]
  · simp [binaryKernel, improvementCandidate]

theorem target_stability_obligations :
    StepObligations
      binaryKernel
      .target
      stabilityCandidate
      .stability := by
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
          ImprovementPacket, StabilityPacket, stabilityCandidate]
  · unfold ProtectedNonLoss
    intro distinction
    cases distinction
    change binaryProgress .target ≤ binaryProgress .target + 0
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
    intro state candidate certificate _stateAdmissible _stateInvariant accepted
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
  | 0 => .initial
  | _ + 1 => .target

def binaryTrajectoryCandidate :
    Nat → Candidate BinaryState BinaryUpdate
  | 0 => improvementCandidate
  | _ + 1 => stabilityCandidate

def binaryTrajectoryCertificate : Nat → BinaryCertificate
  | 0 => .improvement
  | _ + 1 => .stability

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
  exact binaryProgress_initial_lt_target

end ClassicalFinite
end RCP
end RcpRclmFormalCoreV2
