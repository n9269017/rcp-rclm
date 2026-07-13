import Mathlib.Analysis.Matrix.PosDef
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.Monitors

open scoped BigOperators ComplexOrder

namespace RcpRclmFormalCoreV2
namespace RCP
namespace QuantumFinite

open ClassicalFinite

abbrev QuantumMatrix (n : Nat) := Matrix (Fin n) (Fin n) ℂ

structure DiagonalDensityMatrix (n : Nat) where
  distribution : Distribution n

@[ext] theorem DiagonalDensityMatrix.ext
    {n : Nat}
    {ρ σ : DiagonalDensityMatrix n}
    (distributionEq : ρ.distribution = σ.distribution) :
    ρ = σ := by
  cases ρ
  cases σ
  cases distributionEq
  rfl

def DiagonalDensityMatrix.matrix
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) : QuantumMatrix n :=
  Matrix.diagonal (fun i => (ρ.distribution.mass i : ℂ))

structure DensityMatrixEvidence
    {n : Nat}
    (matrix : QuantumMatrix n) : Prop where
  hermitian : matrix.IsHermitian
  positiveSemidefinite : matrix.PosSemidef
  traceOne : Matrix.trace matrix = 1

theorem DiagonalDensityMatrix.matrix_isHermitian
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) :
    ρ.matrix.IsHermitian := by
  apply Matrix.isHermitian_diagonal_of_self_adjoint
  apply funext
  intro i
  exact Complex.conj_ofReal (ρ.distribution.mass i)

theorem DiagonalDensityMatrix.matrix_posSemidef
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) :
    ρ.matrix.PosSemidef := by
  apply Matrix.PosSemidef.diagonal
  intro i
  exact (Complex.zero_le_real).2 (ρ.distribution.nonnegative i)

theorem DiagonalDensityMatrix.matrix_trace_one
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) :
    Matrix.trace ρ.matrix = 1 := by
  rw [DiagonalDensityMatrix.matrix, Matrix.trace_diagonal]
  rw [← Complex.ofReal_sum]
  rw [ρ.distribution.normalized]
  norm_num

theorem DiagonalDensityMatrix.densityEvidence
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) :
    DensityMatrixEvidence ρ.matrix := by
  exact
    { hermitian := ρ.matrix_isHermitian
      positiveSemidefinite := ρ.matrix_posSemidef
      traceOne := ρ.matrix_trace_one }

def SupportedBy
    {n : Nat}
    (ρ σ : DiagonalDensityMatrix n) : Prop :=
  ClassicalFinite.SupportedBy ρ.distribution σ.distribution

noncomputable def vonNeumannEntropy
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) : ℝ :=
  ClassicalFinite.shannonEntropy ρ.distribution

noncomputable def quantumRelativeEntropy
    {n : Nat}
    (ρ σ : DiagonalDensityMatrix n) : ℝ :=
  ClassicalFinite.klDivergence ρ.distribution σ.distribution

theorem quantumRelativeEntropy_nonnegative
    {n : Nat}
    (ρ σ : DiagonalDensityMatrix n)
    (support : SupportedBy ρ σ) :
    0 ≤ quantumRelativeEntropy ρ σ := by
  exact ClassicalFinite.klDivergence_nonnegative
    ρ.distribution σ.distribution support

theorem quantumRelativeEntropy_self
    {n : Nat}
    (ρ : DiagonalDensityMatrix n) :
    quantumRelativeEntropy ρ ρ = 0 := by
  exact ClassicalFinite.klDivergence_self ρ.distribution

structure PositiveDiagonalDensityMatrix (n : Nat) where
  density : DiagonalDensityMatrix n
  positive : ∀ i, 0 < density.distribution.mass i

def PositiveDiagonalDensityMatrix.ofPositiveDistribution
    {n : Nat}
    (p : PositiveDistribution n) :
    PositiveDiagonalDensityMatrix n where
  density := { distribution := p.distribution }
  positive := p.positive

theorem PositiveDiagonalDensityMatrix.supportedBy
    {n : Nat}
    (ρ σ : PositiveDiagonalDensityMatrix n) :
    SupportedBy ρ.density σ.density := by
  intro i _
  exact σ.positive i

noncomputable def positiveQuantumRelativeEntropy
    {n : Nat}
    (ρ σ : PositiveDiagonalDensityMatrix n) : ℝ :=
  quantumRelativeEntropy ρ.density σ.density

theorem positiveQuantumRelativeEntropy_nonnegative
    {n : Nat}
    (ρ σ : PositiveDiagonalDensityMatrix n) :
    0 ≤ positiveQuantumRelativeEntropy ρ σ := by
  exact quantumRelativeEntropy_nonnegative
    ρ.density σ.density (ρ.supportedBy σ)

theorem positiveQuantumRelativeEntropy_self
    {n : Nat}
    (ρ : PositiveDiagonalDensityMatrix n) :
    positiveQuantumRelativeEntropy ρ ρ = 0 := by
  exact quantumRelativeEntropy_self ρ.density

def swapDistribution (p : Distribution 2) : Distribution 2 where
  mass := Fin.cases (p.mass 1) (fun _ => p.mass 0)
  nonnegative := by
    intro i
    refine Fin.cases ?_ ?_ i
    · exact p.nonnegative 1
    · intro j
      exact p.nonnegative 0
  normalized := by
    have normalized := p.normalized
    rw [Fin.sum_univ_two] at normalized
    rw [Fin.sum_univ_two]
    change p.mass 1 + p.mass 0 = 1
    rw [add_comm]
    exact normalized

def swapDensity (ρ : DiagonalDensityMatrix 2) :
    DiagonalDensityMatrix 2 where
  distribution := swapDistribution ρ.distribution

theorem swapDensity_involutive
    (ρ : DiagonalDensityMatrix 2) :
    swapDensity (swapDensity ρ) = ρ := by
  apply DiagonalDensityMatrix.ext
  apply Distribution.ext
  funext i
  refine Fin.cases ?_ ?_ i
  · change ρ.distribution.mass 0 = ρ.distribution.mass 0
    rfl
  · intro j
    have jEq : j = 0 := by
      exact Fin.eq_zero j
    subst j
    change ρ.distribution.mass 1 = ρ.distribution.mass 1
    rfl

def swapIndex : Fin 2 ≃ Fin 2 :=
  Equiv.swap 0 1

def swapMatrixMap : QuantumMatrix 2 →ₗ[ℂ] QuantumMatrix 2 where
  toFun := fun matrix i j => matrix (swapIndex i) (swapIndex j)
  map_add' := by
    intro first second
    rfl
  map_smul' := by
    intro scalar matrix
    rfl

theorem swapMatrix_action
    (ρ : DiagonalDensityMatrix 2) :
    (swapDensity ρ).matrix = swapMatrixMap ρ.matrix := by
  ext i j
  refine Fin.cases ?_ ?_ i
  · refine Fin.cases ?_ ?_ j
    · rfl
    · intro k
      have kEq : k = 0 := by
        exact Fin.eq_zero k
      subst k
      rfl
  · intro h
    have hEq : h = 0 := by
      exact Fin.eq_zero h
    subst h
    refine Fin.cases ?_ ?_ j
    · rfl
    · intro k
      have kEq : k = 0 := by
        exact Fin.eq_zero k
      subst k
      rfl

structure FiniteDiagonalChannel (n : Nat) where
  apply : DiagonalDensityMatrix n → DiagonalDensityMatrix n
  matrixMap : QuantumMatrix n →ₗ[ℂ] QuantumMatrix n
  matrixAction : ∀ ρ, (apply ρ).matrix = matrixMap ρ.matrix
  tracePreserving : ∀ ρ,
    Matrix.trace (matrixMap ρ.matrix) = Matrix.trace ρ.matrix
  hermitianPreserving : ∀ ρ, (matrixMap ρ.matrix).IsHermitian
  positiveSemidefinitePreserving : ∀ ρ, (matrixMap ρ.matrix).PosSemidef

noncomputable def swapChannel : FiniteDiagonalChannel 2 where
  apply := swapDensity
  matrixMap := swapMatrixMap
  matrixAction := swapMatrix_action
  tracePreserving := by
    intro ρ
    rw [← swapMatrix_action ρ]
    rw [(swapDensity ρ).matrix_trace_one, ρ.matrix_trace_one]
  hermitianPreserving := by
    intro ρ
    rw [← swapMatrix_action ρ]
    exact (swapDensity ρ).matrix_isHermitian
  positiveSemidefinitePreserving := by
    intro ρ
    rw [← swapMatrix_action ρ]
    exact (swapDensity ρ).matrix_posSemidef

theorem swapChannel_vonNeumannEntropy_preserving
    (ρ : DiagonalDensityMatrix 2) :
    vonNeumannEntropy (swapChannel.apply ρ) =
      vonNeumannEntropy ρ := by
  unfold swapChannel
  unfold vonNeumannEntropy ClassicalFinite.shannonEntropy
  unfold swapDensity swapDistribution
  rw [Fin.sum_univ_two]
  rw [Fin.sum_univ_two]
  change
    -(ρ.distribution.mass 1 * Real.log (ρ.distribution.mass 1) +
        ρ.distribution.mass 0 * Real.log (ρ.distribution.mass 0)) =
      -(ρ.distribution.mass 0 * Real.log (ρ.distribution.mass 0) +
        ρ.distribution.mass 1 * Real.log (ρ.distribution.mass 1))
  ring

theorem swapChannel_quantumRelativeEntropy_preserving
    (ρ σ : DiagonalDensityMatrix 2) :
    quantumRelativeEntropy (swapChannel.apply ρ) (swapChannel.apply σ) =
      quantumRelativeEntropy ρ σ := by
  unfold swapChannel
  unfold quantumRelativeEntropy ClassicalFinite.klDivergence
  unfold swapDensity swapDistribution
  rw [Fin.sum_univ_two]
  rw [Fin.sum_univ_two]
  change
    ρ.distribution.mass 1 *
          Real.log (ρ.distribution.mass 1 / σ.distribution.mass 1) +
        ρ.distribution.mass 0 *
          Real.log (ρ.distribution.mass 0 / σ.distribution.mass 0) =
      ρ.distribution.mass 0 *
          Real.log (ρ.distribution.mass 0 / σ.distribution.mass 0) +
        ρ.distribution.mass 1 *
          Real.log (ρ.distribution.mass 1 / σ.distribution.mass 1)
  ring

noncomputable def uniformDensity :
    PositiveDiagonalDensityMatrix 2 :=
  PositiveDiagonalDensityMatrix.ofPositiveDistribution uniformBinary

noncomputable def targetDensity :
    PositiveDiagonalDensityMatrix 2 :=
  PositiveDiagonalDensityMatrix.ofPositiveDistribution biasedBinary

noncomputable def sourceDistribution : PositiveDistribution 2 where
  distribution :=
    { mass := Fin.cases (1 / 4 : ℝ) (fun _ => 3 / 4)
      nonnegative := by
        intro i
        refine Fin.cases ?_ ?_ i
        · norm_num
        · intro j
          norm_num
      normalized := by
        rw [Fin.sum_univ_two]
        change (1 / 4 : ℝ) + 3 / 4 = 1
        norm_num }
  positive := by
    intro i
    refine Fin.cases ?_ ?_ i
    · norm_num
    · intro j
      norm_num

noncomputable def sourceDensity :
    PositiveDiagonalDensityMatrix 2 :=
  PositiveDiagonalDensityMatrix.ofPositiveDistribution sourceDistribution

theorem swapDensity_uniform :
    swapDensity uniformDensity.density = uniformDensity.density := by
  apply DiagonalDensityMatrix.ext
  apply Distribution.ext
  funext i
  refine Fin.cases ?_ ?_ i
  · change (1 / 2 : ℝ) = 1 / 2
    rfl
  · intro j
    have jEq : j = 0 := by
      exact Fin.eq_zero j
    subst j
    change (1 / 2 : ℝ) = 1 / 2
    rfl

theorem swapDensity_source_to_target :
    swapDensity sourceDensity.density = targetDensity.density := by
  apply DiagonalDensityMatrix.ext
  apply Distribution.ext
  funext i
  refine Fin.cases ?_ ?_ i
  · change (3 / 4 : ℝ) = 3 / 4
    rfl
  · intro j
    have jEq : j = 0 := by
      exact Fin.eq_zero j
    subst j
    change (1 / 4 : ℝ) = 1 / 4
    rfl

theorem swapDensity_target_to_source :
    swapDensity targetDensity.density = sourceDensity.density := by
  apply DiagonalDensityMatrix.ext
  apply Distribution.ext
  funext i
  refine Fin.cases ?_ ?_ i
  · change (1 / 4 : ℝ) = 1 / 4
    rfl
  · intro j
    have jEq : j = 0 := by
      exact Fin.eq_zero j
    subst j
    change (3 / 4 : ℝ) = 3 / 4
    rfl

theorem source_target_quantumRelativeEntropy :
    positiveQuantumRelativeEntropy sourceDensity targetDensity =
      (1 / 2 : ℝ) * Real.log 3 := by
  have hlogThird :
      Real.log (1 / 3 : ℝ) = -Real.log 3 := by
    rw [one_div, Real.log_inv]
  calc
    positiveQuantumRelativeEntropy sourceDensity targetDensity =
        (1 / 4 : ℝ) * Real.log (1 / 3) +
          (3 / 4 : ℝ) * Real.log 3 := by
      unfold positiveQuantumRelativeEntropy quantumRelativeEntropy
      unfold sourceDensity targetDensity
      unfold PositiveDiagonalDensityMatrix.ofPositiveDistribution
      unfold sourceDistribution biasedBinary ClassicalFinite.klDivergence
      rw [Fin.sum_univ_two]
      change
        (1 / 4 : ℝ) * Real.log ((1 / 4 : ℝ) / (3 / 4 : ℝ)) +
            (3 / 4 : ℝ) * Real.log ((3 / 4 : ℝ) / (1 / 4 : ℝ)) =
          (1 / 4 : ℝ) * Real.log (1 / 3) +
            (3 / 4 : ℝ) * Real.log 3
      norm_num
    _ = (1 / 2 : ℝ) * Real.log 3 := by
      rw [hlogThird]
      ring

theorem source_target_quantumRelativeEntropy_pos :
    0 < positiveQuantumRelativeEntropy sourceDensity targetDensity := by
  rw [source_target_quantumRelativeEntropy]
  exact mul_pos (by norm_num) (Real.log_pos (by norm_num))

theorem source_target_vonNeumannEntropy_equal :
    vonNeumannEntropy sourceDensity.density =
      vonNeumannEntropy targetDensity.density := by
  rw [← swapDensity_source_to_target]
  exact
    (swapChannel_vonNeumannEntropy_preserving sourceDensity.density).symm

inductive QuantumState where
  | outside
  | source
  | target
  deriving DecidableEq

inductive QuantumUpdate where
  | stay
  | swap
  deriving DecidableEq

inductive QuantumCertificate where
  | improvement
  | stability
  | malformed
  deriving DecidableEq

inductive QuantumResidualIndex where
  | typed
  | packet
  deriving DecidableEq

noncomputable def stateDensity :
    QuantumState → PositiveDiagonalDensityMatrix 2
  | QuantumState.outside => uniformDensity
  | QuantumState.source => sourceDensity
  | QuantumState.target => targetDensity

noncomputable def quantumGap : ℝ :=
  positiveQuantumRelativeEntropy sourceDensity targetDensity

theorem quantumGap_pos : 0 < quantumGap :=
  source_target_quantumRelativeEntropy_pos

noncomputable def quantumProgress (state : QuantumState) : ℝ :=
  quantumGap -
    positiveQuantumRelativeEntropy (stateDensity state) targetDensity

theorem quantumProgress_source :
    quantumProgress QuantumState.source = 0 := by
  simp [quantumProgress, quantumGap, stateDensity]

theorem quantumProgress_target :
    quantumProgress QuantumState.target = quantumGap := by
  simp [quantumProgress, stateDensity,
    positiveQuantumRelativeEntropy_self]

theorem quantumProgress_source_lt_target :
    quantumProgress QuantumState.source <
      quantumProgress QuantumState.target := by
  rw [quantumProgress_source, quantumProgress_target]
  exact quantumGap_pos

def quantumApply : QuantumState → QuantumUpdate → QuantumState
  | QuantumState.outside, QuantumUpdate.stay => QuantumState.outside
  | QuantumState.outside, QuantumUpdate.swap => QuantumState.outside
  | QuantumState.source, QuantumUpdate.stay => QuantumState.source
  | QuantumState.source, QuantumUpdate.swap => QuantumState.target
  | QuantumState.target, QuantumUpdate.stay => QuantumState.target
  | QuantumState.target, QuantumUpdate.swap => QuantumState.source

theorem quantumApply_density_swap
    (state : QuantumState) :
    (stateDensity (quantumApply state QuantumUpdate.swap)).density =
      swapDensity (stateDensity state).density := by
  cases state with
  | outside =>
      exact swapDensity_uniform.symm
  | source =>
      exact swapDensity_source_to_target.symm
  | target =>
      exact swapDensity_target_to_source.symm

def improvementCandidate : Candidate QuantumState QuantumUpdate where
  update := QuantumUpdate.swap
  next := QuantumState.target

def stabilityCandidate : Candidate QuantumState QuantumUpdate where
  update := QuantumUpdate.stay
  next := QuantumState.target

def invalidCandidate : Candidate QuantumState QuantumUpdate where
  update := QuantumUpdate.swap
  next := QuantumState.source

def ImprovementPacket
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : Prop :=
  state = QuantumState.source ∧
    candidate.update = QuantumUpdate.swap ∧
    candidate.next = QuantumState.target ∧
    certificate = QuantumCertificate.improvement

def StabilityPacket
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : Prop :=
  state = QuantumState.target ∧
    candidate.update = QuantumUpdate.stay ∧
    candidate.next = QuantumState.target ∧
    certificate = QuantumCertificate.stability

def quantumCheck
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : Bool :=
  (decide (state = QuantumState.source) &&
      decide (candidate.update = QuantumUpdate.swap) &&
      decide (candidate.next = QuantumState.target) &&
      decide (certificate = QuantumCertificate.improvement)) ||
    (decide (state = QuantumState.target) &&
      decide (candidate.update = QuantumUpdate.stay) &&
      decide (candidate.next = QuantumState.target) &&
      decide (certificate = QuantumCertificate.stability))

theorem quantumCheck_eq_true_iff
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) :
    quantumCheck state candidate certificate = true ↔
      ImprovementPacket state candidate certificate ∨
        StabilityPacket state candidate certificate := by
  simp [quantumCheck, ImprovementPacket, StabilityPacket, and_assoc]

theorem quantumCheck_rejects_invalidCandidate :
    quantumCheck
      QuantumState.source
      invalidCandidate
      QuantumCertificate.improvement = false := by
  rfl

def quantumStateDistance (x y : QuantumState) : ℝ :=
  if x = y then 0 else 1

theorem quantumStateDistance_nonnegative (x y : QuantumState) :
    0 ≤ quantumStateDistance x y := by
  by_cases hxy : x = y
  · simp [quantumStateDistance, hxy]
  · simp [quantumStateDistance, hxy]

theorem quantumStateDistance_self (state : QuantumState) :
    quantumStateDistance state state = 0 := by
  simp [quantumStateDistance]

theorem quantumStateDistance_triangle (x y z : QuantumState) :
    quantumStateDistance x z ≤
      quantumStateDistance x y + quantumStateDistance y z := by
  cases x <;> cases y <;> cases z <;>
    simp [quantumStateDistance]

def quantumRecover
    (_state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (endpoint : QuantumState) : QuantumState :=
  quantumApply endpoint candidate.update

theorem quantumRecover_improvement :
    quantumRecover
      QuantumState.source
      improvementCandidate
      QuantumState.target = QuantumState.source := by
  rfl

theorem quantumRecover_stability :
    quantumRecover
      QuantumState.target
      stabilityCandidate
      QuantumState.target = QuantumState.target := by
  rfl

def quantumResidual
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) :
    QuantumResidualIndex → ℝ
  | QuantumResidualIndex.typed =>
      if candidate.next = quantumApply state candidate.update then -1 else 1
  | QuantumResidualIndex.packet =>
      if quantumCheck state candidate certificate = true then -1 else 1

def quantumStrictWitness
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : Prop :=
  ImprovementPacket state candidate certificate

def quantumTrustValid
    (state : QuantumState)
    (_candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : Prop :=
  state ≠ QuantumState.outside ∧
    certificate ≠ QuantumCertificate.malformed

def quantumResourceValid
    (_state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : Prop :=
  (certificate = QuantumCertificate.improvement →
      candidate.update = QuantumUpdate.swap) ∧
    (certificate = QuantumCertificate.stability →
      candidate.update = QuantumUpdate.stay) ∧
    certificate ≠ QuantumCertificate.malformed

def quantumRealityContained
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (_certificate : QuantumCertificate) : Prop :=
  candidate.next ≠ QuantumState.outside ∧
    candidate.next = quantumApply state candidate.update

noncomputable def quantumKernel :
    Kernel
      QuantumState
      QuantumUpdate
      QuantumCertificate
      Unit
      QuantumResidualIndex where
  apply := quantumApply
  admissible := fun state => state ≠ QuantumState.outside
  protectedInvariant := fun state => state ≠ QuantumState.outside
  protectedValue := fun state _ => quantumProgress state
  protectedValue_nonconstant := by
    refine
      ⟨QuantumState.source, (), QuantumState.target, (), ?_⟩
    rw [quantumProgress_source, quantumProgress_target]
    exact ne_of_lt quantumGap_pos
  transportProtected := fun _ _ distinction => distinction
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := fun _ _ => le_rfl
  stateDistance := quantumStateDistance
  stateDistance_nonnegative := quantumStateDistance_nonnegative
  recover := quantumRecover
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := fun _ _ => le_rfl
  progress := quantumProgress
  strictWitness := quantumStrictWitness
  residual := quantumResidual
  residual_nonconstant := by
    have sourceNeTarget :
        QuantumState.source ≠ QuantumState.target := by
      decide
    refine
      ⟨QuantumState.source,
        improvementCandidate,
        QuantumCertificate.improvement,
        QuantumState.source,
        invalidCandidate,
        QuantumCertificate.improvement,
        QuantumResidualIndex.typed,
        ?_⟩
    norm_num [quantumResidual, quantumApply,
      improvementCandidate, invalidCandidate, sourceNeTarget]
  trustValid := quantumTrustValid
  resourceValid := quantumResourceValid
  realityContained := quantumRealityContained
  realityContained_not_universal := by
    refine
      ⟨QuantumState.outside,
        ({ update := QuantumUpdate.stay
           next := QuantumState.outside } :
          Candidate QuantumState QuantumUpdate),
        QuantumCertificate.malformed,
        ?_⟩
    simp [quantumRealityContained]

noncomputable def quantumRecoveryCompositionLaws :
    RecoveryCompositionLaws quantumKernel where
  selfDistanceZero := quantumStateDistance_self
  triangle := quantumStateDistance_triangle
  recoverNonexpansive := by
    intro state candidate x y
    cases candidate with
    | mk update next =>
        cases update <;> cases x <;> cases y <;>
          simp [quantumKernel, quantumRecover, quantumApply,
            quantumStateDistance]

theorem source_improvement_obligations :
    StepObligations
      quantumKernel
      QuantumState.source
      improvementCandidate
      QuantumCertificate.improvement := by
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
        norm_num [quantumKernel, quantumResidual,
          quantumApply, improvementCandidate]
    | packet =>
        norm_num [quantumKernel, quantumResidual,
          quantumCheck, improvementCandidate]
  · unfold ProtectedNonLoss
    intro distinction
    cases distinction
    change
      quantumProgress QuantumState.source ≤
        quantumProgress QuantumState.target + 0
    simpa using quantumProgress_source_lt_target.le
  · unfold ConstructiveRecovery
    simp [quantumKernel, quantumRecover, quantumStateDistance,
      quantumApply, improvementCandidate]
  · simp [quantumKernel, improvementCandidate]
  · unfold ProgressNondecreasing
    exact quantumProgress_source_lt_target.le
  · unfold StrictProgressWhenWitness
    intro _strictWitness
    exact quantumProgress_source_lt_target
  · simp [quantumKernel, quantumTrustValid]
  · simp [quantumKernel, quantumResourceValid, improvementCandidate]
  · simp [quantumKernel, quantumRealityContained,
      quantumApply, improvementCandidate]
  · simp [quantumKernel, improvementCandidate]

theorem target_stability_obligations :
    StepObligations
      quantumKernel
      QuantumState.target
      stabilityCandidate
      QuantumCertificate.stability := by
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
        norm_num [quantumKernel, quantumResidual,
          quantumApply, stabilityCandidate]
    | packet =>
        norm_num [quantumKernel, quantumResidual,
          quantumCheck, stabilityCandidate]
  · unfold ProtectedNonLoss
    intro distinction
    cases distinction
    change
      quantumProgress QuantumState.target ≤
        quantumProgress QuantumState.target + 0
    simp
  · unfold ConstructiveRecovery
    simp [quantumKernel, quantumRecover, quantumStateDistance,
      quantumApply, stabilityCandidate]
  · simp [quantumKernel, stabilityCandidate]
  · unfold ProgressNondecreasing
    exact le_rfl
  · unfold StrictProgressWhenWitness
    intro strictWitness
    simp [quantumKernel, quantumStrictWitness,
      ImprovementPacket, stabilityCandidate] at strictWitness
  · simp [quantumKernel, quantumTrustValid]
  · simp [quantumKernel, quantumResourceValid, stabilityCandidate]
  · simp [quantumKernel, quantumRealityContained,
      quantumApply, stabilityCandidate]
  · simp [quantumKernel, stabilityCandidate]

noncomputable def quantumChecker : TrustedChecker quantumKernel where
  check := quantumCheck
  sound := by
    intro state candidate certificate
      _stateAdmissible _stateInvariant accepted
    have acceptedCases :
        ImprovementPacket state candidate certificate ∨
          StabilityPacket state candidate certificate :=
      (quantumCheck_eq_true_iff state candidate certificate).1 accepted
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
          exact source_improvement_obligations
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

theorem quantum_checker_refines_kernel
    {state : QuantumState}
    {candidate : Candidate QuantumState QuantumUpdate}
    {certificate : QuantumCertificate}
    (stateAdmissible : quantumKernel.admissible state)
    (stateInvariant : quantumKernel.protectedInvariant state)
    (accepted : quantumChecker.check state candidate certificate = true) :
    StepObligations quantumKernel state candidate certificate := by
  exact accepted_step_sound
    quantumChecker stateAdmissible stateInvariant accepted

noncomputable def quantumLyapunovValue (state : QuantumState) : ℝ :=
  positiveQuantumRelativeEntropy (stateDensity state) targetDensity

noncomputable def quantumMotionCharge
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate) : ℝ :=
  if quantumProgress state ≤ quantumProgress candidate.next then
    quantumProgress candidate.next - quantumProgress state
  else
    0

def quantumUnsupportedCollapse
    (_state : QuantumState)
    (_candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) : ℝ :=
  if certificate = QuantumCertificate.malformed then 1 else 0

inductive QuantumRelevance where
  | targetFit
  | traceOne
  | entropyPreserved
  deriving DecidableEq

noncomputable def quantumRelevanceValue
    (state : QuantumState) : QuantumRelevance → ℝ
  | QuantumRelevance.targetFit => quantumProgress state
  | QuantumRelevance.traceOne => 1
  | QuantumRelevance.entropyPreserved =>
      vonNeumannEntropy (stateDensity state).density

def quantumTransportRelevance
    (_state : QuantumState)
    (_candidate : Candidate QuantumState QuantumUpdate)
    (relevance : QuantumRelevance) : QuantumRelevance :=
  relevance

theorem quantumLyapunovValue_nonnegative (state : QuantumState) :
    0 ≤ quantumLyapunovValue state := by
  exact positiveQuantumRelativeEntropy_nonnegative
    (stateDensity state) targetDensity

theorem quantumMotionCharge_nonnegative
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate) :
    0 ≤ quantumMotionCharge state candidate := by
  by_cases hProgress :
      quantumProgress state ≤ quantumProgress candidate.next
  · rw [quantumMotionCharge, if_pos hProgress]
    exact sub_nonneg.mpr hProgress
  · rw [quantumMotionCharge, if_neg hProgress]

theorem quantumLyapunov_motion_step
    {state : QuantumState}
    {candidate : Candidate QuantumState QuantumUpdate}
    {certificate : QuantumCertificate}
    (obligations :
      StepObligations quantumKernel state candidate certificate) :
    quantumLyapunovValue candidate.next +
        quantumMotionCharge state candidate ≤
      quantumLyapunovValue state := by
  have hProgress :
      quantumProgress state ≤ quantumProgress candidate.next := by
    exact obligations.progressNondecreasing
  rw [quantumMotionCharge, if_pos hProgress]
  calc
    quantumLyapunovValue candidate.next +
        (quantumProgress candidate.next - quantumProgress state) =
      quantumLyapunovValue state := by
        unfold quantumProgress quantumLyapunovValue
        ring
    _ ≤ quantumLyapunovValue state := le_rfl

theorem quantumUnsupportedCollapse_nonnegative
    (state : QuantumState)
    (candidate : Candidate QuantumState QuantumUpdate)
    (certificate : QuantumCertificate) :
    0 ≤ quantumUnsupportedCollapse state candidate certificate := by
  by_cases hMalformed : certificate = QuantumCertificate.malformed
  · simp [quantumUnsupportedCollapse, hMalformed]
  · simp [quantumUnsupportedCollapse, hMalformed]

theorem quantumUnsupportedCollapse_step
    {state : QuantumState}
    {candidate : Candidate QuantumState QuantumUpdate}
    {certificate : QuantumCertificate}
    (obligations :
      StepObligations quantumKernel state candidate certificate) :
    quantumUnsupportedCollapse state candidate certificate ≤ 0 := by
  have trustEvidence :
      quantumTrustValid state candidate certificate := by
    exact obligations.trustValid
  have certificateNotMalformed :
      certificate ≠ QuantumCertificate.malformed :=
    trustEvidence.2
  simp [quantumUnsupportedCollapse, certificateNotMalformed]

theorem quantumRelevance_step
    {state : QuantumState}
    {candidate : Candidate QuantumState QuantumUpdate}
    {certificate : QuantumCertificate}
    (obligations :
      StepObligations quantumKernel state candidate certificate)
    (relevance : QuantumRelevance) :
    quantumRelevanceValue state relevance ≤
      quantumRelevanceValue candidate.next
        (quantumTransportRelevance state candidate relevance) := by
  cases relevance with
  | targetFit =>
      change quantumProgress state ≤ quantumProgress candidate.next
      exact obligations.progressNondecreasing
  | traceOne =>
      exact le_rfl
  | entropyPreserved =>
      have accepted :
          quantumCheck state candidate certificate = true := by
        by_contra notAccepted
        have checkFalse :
            quantumCheck state candidate certificate = false :=
          Bool.eq_false_of_not_eq_true notAccepted
        have residualBound :=
          obligations.residualsNonpositive QuantumResidualIndex.packet
        simp [quantumKernel, quantumResidual, checkFalse] at residualBound
      have acceptedPacket :
          ImprovementPacket state candidate certificate ∨
            StabilityPacket state candidate certificate :=
        (quantumCheck_eq_true_iff state candidate certificate).1 accepted
      rcases acceptedPacket with improvement | stability
      · rcases improvement with
          ⟨stateEq, updateEq, nextEq, certificateEq⟩
        subst state
        subst certificate
        cases candidate with
        | mk update next =>
            dsimp at updateEq nextEq
            subst update
            subst next
            change
              vonNeumannEntropy sourceDensity.density ≤
                vonNeumannEntropy targetDensity.density
            exact source_target_vonNeumannEntropy_equal.le
      · rcases stability with
          ⟨stateEq, updateEq, nextEq, certificateEq⟩
        subst state
        subst certificate
        cases candidate with
        | mk update next =>
            dsimp at updateEq nextEq
            subst update
            subst next
            exact le_rfl

noncomputable def quantumPreservationMonitors :
    PreservationMonitors quantumKernel (Relevance := QuantumRelevance) where
  lyapunovValue := quantumLyapunovValue
  motionCharge := fun state candidate _certificate =>
    quantumMotionCharge state candidate
  lyapunovError := fun _state _candidate _certificate => 0
  unsupportedCollapse := quantumUnsupportedCollapse
  ambiguityError := fun _state _candidate _certificate => 0
  relevanceValue := quantumRelevanceValue
  transportRelevance := quantumTransportRelevance
  relevanceError := fun _state _candidate _certificate => 0
  lyapunovValue_nonnegative := quantumLyapunovValue_nonnegative
  motionCharge_nonnegative := by
    intro state candidate certificate
    exact quantumMotionCharge_nonnegative state candidate
  lyapunovError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  unsupportedCollapse_nonnegative := quantumUnsupportedCollapse_nonnegative
  ambiguityError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  relevanceError_nonnegative := by
    intro state candidate certificate
    exact le_rfl
  lyapunovStep := by
    intro state candidate certificate obligations
    simpa using quantumLyapunov_motion_step obligations
  ambiguityStep := by
    intro state candidate certificate obligations
    exact quantumUnsupportedCollapse_step obligations
  relevanceStep := by
    intro state candidate certificate obligations relevance
    simpa using quantumRelevance_step obligations relevance

def quantumTrajectoryState : Nat → QuantumState
  | 0 => QuantumState.source
  | _ + 1 => QuantumState.target

def quantumTrajectoryCandidate :
    Nat → Candidate QuantumState QuantumUpdate
  | 0 => improvementCandidate
  | _ + 1 => stabilityCandidate

def quantumTrajectoryCertificate : Nat → QuantumCertificate
  | 0 => QuantumCertificate.improvement
  | _ + 1 => QuantumCertificate.stability

noncomputable def quantumWorkedTrajectory :
    FiniteAcceptedTrajectory quantumChecker 2 where
  state := quantumTrajectoryState
  candidate := quantumTrajectoryCandidate
  certificate := quantumTrajectoryCertificate
  initialAdmissible := by
    simp [quantumKernel, quantumTrajectoryState]
  initialInvariant := by
    simp [quantumKernel, quantumTrajectoryState]
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

theorem quantumWorkedTrajectory_first_step_strict :
    quantumKernel.progress (quantumWorkedTrajectory.state 0) <
      quantumKernel.progress (quantumWorkedTrajectory.state 1) := by
  change
    quantumProgress QuantumState.source <
      quantumProgress QuantumState.target
  exact quantumProgress_source_lt_target

theorem quantumWorkedTrajectory_endpoint_recovery :
    quantumKernel.stateDistance
        (composedRecovery quantumWorkedTrajectory 2
          (quantumWorkedTrajectory.state 2))
        (quantumWorkedTrajectory.state 0) ≤
      cumulativeRecoveryBudget quantumWorkedTrajectory 2 := by
  exact finite_endpoint_recovery_bound
    quantumChecker
    quantumRecoveryCompositionLaws
    quantumWorkedTrajectory
    2
    le_rfl

theorem quantumWorkedTrajectory_lyapunov_motion_bound :
    quantumPreservationMonitors.lyapunovValue
          (quantumWorkedTrajectory.state 2) +
        cumulativeMotionCharge
          quantumPreservationMonitors quantumWorkedTrajectory 2 ≤
      quantumPreservationMonitors.lyapunovValue
          (quantumWorkedTrajectory.state 0) +
        cumulativeLyapunovError
          quantumPreservationMonitors quantumWorkedTrajectory 2 := by
  exact finite_lyapunov_motion_bound
    quantumChecker
    quantumPreservationMonitors
    quantumWorkedTrajectory
    2
    le_rfl

theorem quantumWorkedTrajectory_relevance_bound
    (relevance : QuantumRelevance) :
    quantumPreservationMonitors.relevanceValue
        (quantumWorkedTrajectory.state 0) relevance ≤
      quantumPreservationMonitors.relevanceValue
          (quantumWorkedTrajectory.state 2)
          (transportedRelevance
            quantumPreservationMonitors quantumWorkedTrajectory 2 relevance) +
        cumulativeRelevanceError
          quantumPreservationMonitors quantumWorkedTrajectory 2 := by
  exact finite_self_model_relevance_bound
    quantumChecker
    quantumPreservationMonitors
    quantumWorkedTrajectory
    2
    le_rfl
    relevance

end QuantumFinite
end RCP
end RcpRclmFormalCoreV2
