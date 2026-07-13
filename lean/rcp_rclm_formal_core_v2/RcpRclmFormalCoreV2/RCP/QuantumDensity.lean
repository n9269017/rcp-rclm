import Mathlib.Analysis.Matrix.PosDef
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring
import RcpRclmFormalCoreV2.RCP.ClassicalFinite

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
  matrixAction : ∀ ρ : DiagonalDensityMatrix n,
    (apply ρ).matrix = matrixMap ρ.matrix
  tracePreserving : ∀ ρ : DiagonalDensityMatrix n,
    Matrix.trace (matrixMap ρ.matrix) = Matrix.trace ρ.matrix
  hermitianPreserving : ∀ ρ : DiagonalDensityMatrix n,
    (matrixMap ρ.matrix).IsHermitian
  positiveSemidefinitePreserving : ∀ ρ : DiagonalDensityMatrix n,
    (matrixMap ρ.matrix).PosSemidef

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

end QuantumFinite
end RCP
end RcpRclmFormalCoreV2
