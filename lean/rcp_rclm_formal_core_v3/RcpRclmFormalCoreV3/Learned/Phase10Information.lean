import Mathlib
import RcpRclmFormalCoreV3.Learned.TransformerExtension

namespace RcpRclmFormalCoreV3
namespace Learned

/--
Selected finite token-distribution Shannon entropy written from externally certified
probability and logarithm values. Runtime intervals bind the concrete values used by
Phase 10; this formal surface records the diagonal semantic identification.
-/
noncomputable def selectedTokenShannonEntropy
    {Token : Type*}
    [Fintype Token]
    (probability logProbability : Token → ℚ) : ℚ := by
  classical
  exact -((Finset.univ : Finset Token).sum fun token =>
    probability token * logProbability token)

/--
For a diagonal token density, the selected von Neumann entropy is the entropy of its
finite spectrum.
-/
noncomputable def selectedTokenVonNeumannEntropy
    {Token : Type*}
    [Fintype Token]
    (probability logProbability : Token → ℚ) : ℚ :=
  selectedTokenShannonEntropy probability logProbability

/-- Exact selected diagonal identity between von Neumann and Shannon entropy. -/
theorem selected_token_von_neumann_eq_shannon
    {Token : Type*}
    [Fintype Token]
    (probability logProbability : Token → ℚ) :
    selectedTokenVonNeumannEntropy probability logProbability =
      selectedTokenShannonEntropy probability logProbability :=
  rfl

/-- Selected finite KL expression from certified probability and logarithm values. -/
noncomputable def selectedTokenKL
    {Token : Type*}
    [Fintype Token]
    (probability logProbability logTarget : Token → ℚ) : ℚ := by
  classical
  exact (Finset.univ : Finset Token).sum fun token =>
    probability token * (logProbability token - logTarget token)

/--
For commuting diagonal token densities, the selected quantum relative entropy is the
same finite spectral expression as KL divergence.
-/
noncomputable def selectedTokenDiagonalQRE
    {Token : Type*}
    [Fintype Token]
    (probability logProbability logTarget : Token → ℚ) : ℚ :=
  selectedTokenKL probability logProbability logTarget

/-- Exact selected diagonal identity between quantum relative entropy and KL. -/
theorem selected_token_diagonal_qre_eq_kl
    {Token : Type*}
    [Fintype Token]
    (probability logProbability logTarget : Token → ℚ) :
    selectedTokenDiagonalQRE probability logProbability logTarget =
      selectedTokenKL probability logProbability logTarget :=
  rfl

/-- The selected sparse transformer execution profile exposes one exact next-token map. -/
structure SparseTransitionSemantics (Token : Type*) where
  nextToken : Token → Token

/-- Agreement on a protected token set. -/
def SparseProtectedAgreement
    {Token : Type*}
    (predecessor candidate : SparseTransitionSemantics Token)
    (protectedTokens : Set Token) : Prop :=
  ∀ token, token ∈ protectedTokens →
    predecessor.nextToken token = candidate.nextToken token

/-- Protected transition agreement preserves the selected next-token result exactly. -/
theorem sparse_protected_transition_retained
    {Token : Type*}
    (predecessor candidate : SparseTransitionSemantics Token)
    (protectedTokens : Set Token)
    (agreement : SparseProtectedAgreement predecessor candidate protectedTokens)
    {token : Token}
    (member : token ∈ protectedTokens) :
    candidate.nextToken token = predecessor.nextToken token := by
  exact (agreement token member).symm

end Learned
end RcpRclmFormalCoreV3
