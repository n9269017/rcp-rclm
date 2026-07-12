import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Data.Fintype.BigOperators

open scoped BigOperators

namespace RcpRclmFormalCoreV2
namespace RCP
namespace ClassicalFinite

/-- A finite probability distribution with explicit normalization evidence. -/
structure Distribution (n : Nat) where
  mass : Fin n → ℝ
  nonnegative : ∀ i, 0 ≤ mass i
  normalized : (∑ i, mass i) = 1

/-- Support condition needed before claiming a finite KL theorem. -/
def SupportedBy {n : Nat} (p q : Distribution n) : Prop :=
  ∀ i, 0 < p.mass i → 0 < q.mass i

/-- Actual finite Shannon entropy expression; no placeholder constant is used. -/
noncomputable def shannonEntropy {n : Nat} (p : Distribution n) : ℝ :=
  -∑ i, p.mass i * Real.log (p.mass i)

/--
Actual finite KL expression. Gate B will prove its required laws only under the
explicit support conditions; this definition alone is not a completed KL theorem.
-/
noncomputable def klDivergence {n : Nat} (p q : Distribution n) : ℝ :=
  ∑ i, p.mass i * Real.log (p.mass i / q.mass i)

end ClassicalFinite
end RCP
end RcpRclmFormalCoreV2
