import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring
import RcpRclmFormalCoreV2.RCP.RelativeEntropy

open scoped BigOperators

namespace RcpRclmFormalCoreV2
namespace RCP
namespace ClassicalFinite

structure Distribution (n : Nat) where
  mass : Fin n → ℝ
  nonnegative : ∀ i, 0 ≤ mass i
  normalized : (∑ i, mass i) = 1

@[ext] theorem Distribution.ext
    {n : Nat}
    {p q : Distribution n}
    (mass_eq : p.mass = q.mass) :
    p = q := by
  cases p
  cases q
  cases mass_eq
  rfl

def SupportedBy {n : Nat} (p q : Distribution n) : Prop :=
  ∀ i, 0 < p.mass i → 0 < q.mass i

noncomputable def shannonEntropy {n : Nat} (p : Distribution n) : ℝ :=
  -∑ i, p.mass i * Real.log (p.mass i)

noncomputable def klDivergence {n : Nat} (p q : Distribution n) : ℝ :=
  ∑ i, p.mass i * Real.log (p.mass i / q.mass i)

private theorem mass_sub_mass_le_klTerm
    {n : Nat}
    (p q : Distribution n)
    (support : SupportedBy p q)
    (i : Fin n) :
    p.mass i - q.mass i ≤
      p.mass i * Real.log (p.mass i / q.mass i) := by
  by_cases hpZero : p.mass i = 0
  · rw [hpZero]
    simp only [zero_div, Real.log_zero, zero_mul, zero_sub]
    exact neg_nonpos.mpr (q.nonnegative i)
  · have hpPositive : 0 < p.mass i :=
      lt_of_le_of_ne (p.nonnegative i) (Ne.symm hpZero)
    have hqPositive : 0 < q.mass i :=
      support i hpPositive
    have hratioPositive : 0 < q.mass i / p.mass i :=
      div_pos hqPositive hpPositive
    have hlogBound :
        Real.log (q.mass i / p.mass i) ≤
          q.mass i / p.mass i - 1 :=
      Real.log_le_sub_one_of_pos hratioPositive
    have hscaledBound :
        p.mass i * Real.log (q.mass i / p.mass i) ≤
          q.mass i - p.mass i := by
      calc
        p.mass i * Real.log (q.mass i / p.mass i) ≤
            p.mass i * (q.mass i / p.mass i - 1) :=
          mul_le_mul_of_nonneg_left hlogBound hpPositive.le
        _ = q.mass i - p.mass i := by
          field_simp [hpZero]
    have hlogReverse :
        Real.log (p.mass i / q.mass i) =
          -Real.log (q.mass i / p.mass i) := by
      rw [Real.log_div hpZero hqPositive.ne',
        Real.log_div hqPositive.ne' hpZero]
      ring
    calc
      p.mass i - q.mass i = -(q.mass i - p.mass i) := by
        ring
      _ ≤ -(p.mass i * Real.log (q.mass i / p.mass i)) :=
        neg_le_neg hscaledBound
      _ = p.mass i * Real.log (p.mass i / q.mass i) := by
        rw [hlogReverse]
        ring

theorem klDivergence_nonnegative
    {n : Nat}
    (p q : Distribution n)
    (support : SupportedBy p q) :
    0 ≤ klDivergence p q := by
  have hsum :
      (∑ i, (p.mass i - q.mass i)) ≤ klDivergence p q := by
    unfold klDivergence
    exact Finset.sum_le_sum fun i _ =>
      mass_sub_mass_le_klTerm p q support i
  have hsumZero :
      (∑ i, (p.mass i - q.mass i)) = 0 := by
    rw [Finset.sum_sub_distrib, p.normalized, q.normalized, sub_self]
  rw [hsumZero] at hsum
  exact hsum

theorem klDivergence_self
    {n : Nat}
    (p : Distribution n) :
    klDivergence p p = 0 := by
  simp [klDivergence]

structure PositiveDistribution (n : Nat) where
  distribution : Distribution n
  positive : ∀ i, 0 < distribution.mass i

theorem PositiveDistribution.supportedBy
    {n : Nat}
    (p q : PositiveDistribution n) :
    SupportedBy p.distribution q.distribution := by
  intro i _
  exact q.positive i

noncomputable def positiveKLDivergence
    {n : Nat}
    (p q : PositiveDistribution n) : ℝ :=
  klDivergence p.distribution q.distribution

theorem positiveKLDivergence_nonnegative
    {n : Nat}
    (p q : PositiveDistribution n) :
    0 ≤ positiveKLDivergence p q := by
  exact klDivergence_nonnegative
    p.distribution q.distribution (p.supportedBy q)

theorem positiveKLDivergence_self
    {n : Nat}
    (p : PositiveDistribution n) :
    positiveKLDivergence p p = 0 := by
  exact klDivergence_self p.distribution

noncomputable def uniformBinary : PositiveDistribution 2 where
  distribution :=
    { mass := Fin.cases (1 / 2 : ℝ) (fun _ => 1 / 2)
      nonnegative := by
        intro i
        refine Fin.cases ?_ ?_ i
        · norm_num
        · intro j
          norm_num
      normalized := by
        rw [Fin.sum_univ_two]
        change (1 / 2 : ℝ) + 1 / 2 = 1
        norm_num }
  positive := by
    intro i
    refine Fin.cases ?_ ?_ i
    · norm_num
    · intro j
      norm_num

noncomputable def biasedBinary : PositiveDistribution 2 where
  distribution :=
    { mass := Fin.cases (3 / 4 : ℝ) (fun _ => 1 / 4)
      nonnegative := by
        intro i
        refine Fin.cases ?_ ?_ i
        · norm_num
        · intro j
          norm_num
      normalized := by
        rw [Fin.sum_univ_two]
        change (3 / 4 : ℝ) + 1 / 4 = 1
        norm_num }
  positive := by
    intro i
    refine Fin.cases ?_ ?_ i
    · norm_num
    · intro j
      norm_num

theorem uniformBinary_kl_biasedBinary :
    positiveKLDivergence uniformBinary biasedBinary =
      (1 / 2 : ℝ) * Real.log (4 / 3) := by
  have hlogProduct :
      Real.log (2 / 3 : ℝ) + Real.log (2 : ℝ) =
        Real.log (4 / 3 : ℝ) := by
    rw [← Real.log_mul
      (by norm_num : (2 / 3 : ℝ) ≠ 0)
      (by norm_num : (2 : ℝ) ≠ 0)]
    norm_num
  calc
    positiveKLDivergence uniformBinary biasedBinary =
        (1 / 2 : ℝ) * Real.log (2 / 3) +
          (1 / 2 : ℝ) * Real.log 2 := by
      unfold positiveKLDivergence klDivergence
      rw [Fin.sum_univ_two]
      change
        (1 / 2 : ℝ) * Real.log ((1 / 2 : ℝ) / (3 / 4 : ℝ)) +
            (1 / 2 : ℝ) * Real.log ((1 / 2 : ℝ) / (1 / 4 : ℝ)) =
          (1 / 2 : ℝ) * Real.log (2 / 3) +
            (1 / 2 : ℝ) * Real.log 2
      norm_num
    _ = (1 / 2 : ℝ) *
        (Real.log (2 / 3) + Real.log 2) := by
      ring
    _ = (1 / 2 : ℝ) * Real.log (4 / 3) := by
      rw [hlogProduct]

theorem uniformBinary_kl_biasedBinary_pos :
    0 < positiveKLDivergence uniformBinary biasedBinary := by
  rw [uniformBinary_kl_biasedBinary]
  exact mul_pos (by norm_num) (Real.log_pos (by norm_num))

noncomputable def binaryKLDivergence :
    LawfulDivergence (PositiveDistribution 2) where
  value := positiveKLDivergence
  nonnegative := positiveKLDivergence_nonnegative
  self_zero := positiveKLDivergence_self
  nonconstant :=
    ⟨uniformBinary, biasedBinary,
      ne_of_gt uniformBinary_kl_biasedBinary_pos⟩

structure ZeroExtension (n : Nat) where
  distribution : Distribution (n + 1)
  headZero : distribution.mass 0 = 0

def extendByZero
    {n : Nat}
    (p : Distribution n) : ZeroExtension n where
  distribution :=
    { mass := Fin.cons 0 p.mass
      nonnegative := by
        intro i
        refine Fin.cases ?_ ?_ i
        · exact le_rfl
        · intro j
          exact p.nonnegative j
      normalized := by
        rw [Fin.sum_univ_succ]
        simp [p.normalized] }
  headZero := by
    rfl

def recoverZeroExtension
    {n : Nat}
    (extended : ZeroExtension n) : Distribution n where
  mass := fun i => extended.distribution.mass i.succ
  nonnegative := fun i => extended.distribution.nonnegative i.succ
  normalized := by
    have hnormalized :
        (∑ i, extended.distribution.mass i) = 1 :=
      extended.distribution.normalized
    rw [Fin.sum_univ_succ, extended.headZero, zero_add] at hnormalized
    exact hnormalized

theorem recover_extendByZero
    {n : Nat}
    (p : Distribution n) :
    recoverZeroExtension (extendByZero p) = p := by
  apply Distribution.ext
  funext i
  rfl

theorem supportedBy_extendByZero
    {n : Nat}
    (p q : Distribution n)
    (support : SupportedBy p q) :
    SupportedBy
      (extendByZero p).distribution
      (extendByZero q).distribution := by
  intro i
  refine Fin.cases ?_ ?_ i
  · intro hi
    simp [extendByZero] at hi
  · intro j hi
    have hp : 0 < p.mass j := by
      simpa [extendByZero] using hi
    have hq : 0 < q.mass j :=
      support j hp
    simpa [extendByZero] using hq

theorem shannonEntropy_extendByZero
    {n : Nat}
    (p : Distribution n) :
    shannonEntropy (extendByZero p).distribution =
      shannonEntropy p := by
  simp [shannonEntropy, extendByZero, Fin.sum_univ_succ]

theorem klDivergence_extendByZero
    {n : Nat}
    (p q : Distribution n) :
    klDivergence
        (extendByZero p).distribution
        (extendByZero q).distribution =
      klDivergence p q := by
  simp [klDivergence, extendByZero, Fin.sum_univ_succ]

theorem conservative_extension_recovery
    {n : Nat}
    (p q : Distribution n)
    (support : SupportedBy p q) :
    SupportedBy
        (extendByZero p).distribution
        (extendByZero q).distribution ∧
      shannonEntropy (extendByZero p).distribution = shannonEntropy p ∧
      klDivergence
          (extendByZero p).distribution
          (extendByZero q).distribution =
        klDivergence p q ∧
      recoverZeroExtension (extendByZero p) = p := by
  exact
    ⟨supportedBy_extendByZero p q support,
      shannonEntropy_extendByZero p,
      klDivergence_extendByZero p q,
      recover_extendByZero p⟩

end ClassicalFinite
end RCP
end RcpRclmFormalCoreV2