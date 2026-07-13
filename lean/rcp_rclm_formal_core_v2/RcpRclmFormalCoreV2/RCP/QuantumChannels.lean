import RcpRclmFormalCoreV2.RCP.QuantumKernel

namespace RcpRclmFormalCoreV2
namespace RCP
namespace QuantumFinite

def identityMatrixMap
    (n : Nat) : QuantumMatrix n →ₗ[ℂ] QuantumMatrix n :=
  LinearMap.id

noncomputable def identityChannel
    (n : Nat) : FiniteDiagonalChannel n where
  apply := fun ρ => ρ
  matrixMap := identityMatrixMap n
  matrixAction := by
    intro ρ
    rfl
  tracePreserving := by
    intro ρ
    rfl
  hermitianPreserving := by
    intro ρ
    exact ρ.matrix_isHermitian
  positiveSemidefinitePreserving := by
    intro ρ
    exact ρ.matrix_posSemidef

noncomputable def selectedChannel : QuantumUpdate → FiniteDiagonalChannel 2
  | QuantumUpdate.stay => identityChannel 2
  | QuantumUpdate.swap => swapChannel

noncomputable def selectedRecoveryChannel : QuantumUpdate → FiniteDiagonalChannel 2
  | QuantumUpdate.stay => identityChannel 2
  | QuantumUpdate.swap => swapChannel

theorem selectedChannel_state_action
    (state : QuantumState)
    (update : QuantumUpdate) :
    (selectedChannel update).apply (stateDensity state).density =
      (stateDensity (quantumApply state update)).density := by
  cases update with
  | stay =>
      cases state with
      | outside =>
          rfl
      | source =>
          rfl
      | target =>
          rfl
  | swap =>
      change
        swapDensity (stateDensity state).density =
          (stateDensity (quantumApply state QuantumUpdate.swap)).density
      exact (quantumApply_density_swap state).symm

theorem selectedChannel_recovery_exact
    (update : QuantumUpdate)
    (ρ : DiagonalDensityMatrix 2) :
    (selectedRecoveryChannel update).apply
        ((selectedChannel update).apply ρ) = ρ := by
  cases update with
  | stay =>
      rfl
  | swap =>
      exact swapDensity_involutive ρ

theorem selectedChannel_vonNeumannEntropy_preserving
    (update : QuantumUpdate)
    (ρ : DiagonalDensityMatrix 2) :
    vonNeumannEntropy ((selectedChannel update).apply ρ) =
      vonNeumannEntropy ρ := by
  cases update with
  | stay =>
      rfl
  | swap =>
      exact swapChannel_vonNeumannEntropy_preserving ρ

theorem selectedChannel_quantumRelativeEntropy_preserving
    (update : QuantumUpdate)
    (ρ σ : DiagonalDensityMatrix 2) :
    quantumRelativeEntropy
        ((selectedChannel update).apply ρ)
        ((selectedChannel update).apply σ) =
      quantumRelativeEntropy ρ σ := by
  cases update with
  | stay =>
      rfl
  | swap =>
      exact swapChannel_quantumRelativeEntropy_preserving ρ σ

theorem selectedChannel_densityEvidence
    (update : QuantumUpdate)
    (ρ : DiagonalDensityMatrix 2) :
    DensityMatrixEvidence ((selectedChannel update).apply ρ).matrix := by
  exact ((selectedChannel update).apply ρ).densityEvidence

end QuantumFinite
end RCP
end RcpRclmFormalCoreV2
