import Mathlib.Data.Real.Basic

namespace RcpRclmFormalCoreV2
namespace RCP

/--
A divergence interface used by concrete classical and quantum instantiations.
The abstract kernel does not identify this with KL or quantum relative entropy
until the corresponding laws are proved in Gate B or Gate C.
-/
structure LawfulDivergence (α : Type*) where
  value : α → α → ℝ
  nonnegative : ∀ x y, 0 ≤ value x y
  self_zero : ∀ x, value x x = 0
  nonconstant : ∃ x y, value x y ≠ 0

end RCP
end RcpRclmFormalCoreV2
