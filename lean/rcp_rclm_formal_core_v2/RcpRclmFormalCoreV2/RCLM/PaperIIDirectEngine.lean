import RcpRclmFormalCoreV2.RCLM.ArchitectureEngine

namespace RcpRclmFormalCoreV2
namespace RCLM

structure PaperIIDirectEngineSemantics
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) where
  nonLossyCandidate : State → RCP.Candidate State Update → Prop
  algebraicGate : State → RCP.Candidate State Update → Certificate → Prop
  fullGate : State → RCP.Candidate State Update → Certificate → Prop
  predecessorAbilitiesPreserved :
    State → RCP.Candidate State Update → Certificate → Prop
  strictAbilityExpansion :
    State → RCP.Candidate State Update → Certificate → Prop
  viabilityKernel : State → Prop
  projectionRealized :
    State → RCP.Candidate State Update → Certificate → Prop
  nonLossyCandidate_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
        nonLossyCandidate state candidate
  algebraicGate_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
        algebraicGate state candidate certificate
  fullGate_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
        fullGate state candidate certificate
  predecessorAbilitiesPreserved_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
        predecessorAbilitiesPreserved state candidate certificate
  strictAbilityExpansion_of_witness :
    ∀ {state candidate certificate},
      kernel.strictWitness state candidate certificate →
      RCP.StepObligations kernel state candidate certificate →
        strictAbilityExpansion state candidate certificate
  viabilityKernel_of_domain :
    ∀ {state}, engine.domain state → viabilityKernel state
  projectionRealized_of_typedSuccessor :
    ∀ {state candidate certificate},
      RCP.TypedSuccessor kernel state candidate →
        projectionRealized state candidate certificate

structure StrictArchitectureEngineStep
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (state : State) where
  step : ArchitectureEngineStep engine state
  strictWitness :
    kernel.strictWitness state step.candidate step.certificate

def StrictArchitectureSuccessorAvailableAt
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (predecessor : ArchitecturePredecessor engine) : Prop :=
  Nonempty (StrictArchitectureEngineStep engine predecessor.state)

structure PaperIIDirectEngineObligations
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (semantics : PaperIIDirectEngineSemantics engine)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate : Certificate) : Prop where
  candidateNonLossy : semantics.nonLossyCandidate state candidate
  algebraicGate : semantics.algebraicGate state candidate certificate
  fullGate : semantics.fullGate state candidate certificate
  protectedNonLoss : RCP.ProtectedNonLoss kernel state candidate
  constructiveRecovery : RCP.ConstructiveRecovery kernel state candidate
  predecessorAbilitiesPreserved :
    semantics.predecessorAbilitiesPreserved state candidate certificate
  strictAbilityExpansion :
    semantics.strictAbilityExpansion state candidate certificate
  strictProgress : kernel.progress state < kernel.progress candidate.next
  successorViable : semantics.viabilityKernel candidate.next
  projectionRealized :
    semantics.projectionRealized state candidate certificate

theorem paper_ii_direct_engine_obligations
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (semantics : PaperIIDirectEngineSemantics engine)
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate : Certificate}
    (obligations : RCP.StepObligations kernel state candidate certificate)
    (successorDomain : engine.domain candidate.next)
    (strictWitness : kernel.strictWitness state candidate certificate) :
    PaperIIDirectEngineObligations
      semantics state candidate certificate := by
  have candidateNonLossy : semantics.nonLossyCandidate state candidate :=
    semantics.nonLossyCandidate_of_obligations obligations
  have algebraicGate : semantics.algebraicGate state candidate certificate :=
    semantics.algebraicGate_of_obligations obligations
  have fullGate : semantics.fullGate state candidate certificate :=
    semantics.fullGate_of_obligations obligations
  have predecessorAbilitiesPreserved :
      semantics.predecessorAbilitiesPreserved state candidate certificate :=
    semantics.predecessorAbilitiesPreserved_of_obligations obligations
  have strictAbilityExpansion :
      semantics.strictAbilityExpansion state candidate certificate :=
    semantics.strictAbilityExpansion_of_witness strictWitness obligations
  have strictProgress : kernel.progress state < kernel.progress candidate.next :=
    obligations.strictProgressWhenWitness strictWitness
  have successorViable : semantics.viabilityKernel candidate.next :=
    semantics.viabilityKernel_of_domain successorDomain
  have projectionRealized :
      semantics.projectionRealized state candidate certificate :=
    semantics.projectionRealized_of_typedSuccessor obligations.typedSuccessor
  exact
    { candidateNonLossy := candidateNonLossy
      algebraicGate := algebraicGate
      fullGate := fullGate
      protectedNonLoss := obligations.protectedNonLoss
      constructiveRecovery := obligations.constructiveRecovery
      predecessorAbilitiesPreserved := predecessorAbilitiesPreserved
      strictAbilityExpansion := strictAbilityExpansion
      strictProgress := strictProgress
      successorViable := successorViable
      projectionRealized := projectionRealized }

theorem rclm_constructive_direct_nl_rsi_engine_aligned
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {Proposal Witness TrustAnchor ResourceRecord CoreRelevance RclmRelevance : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex}
    (rclmChecker : RCP.TrustedChecker rclmKernel)
    (coreChecker : RCP.TrustedChecker coreKernel)
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      rclmKernel rclmChecker)
    (semantics : PaperIIDirectEngineSemantics engine)
    (refinement : KernelRefinement rclmKernel coreKernel)
    (checkerRefinement :
      CheckerRefinement refinement rclmChecker coreChecker)
    (rclmRecoveryLaws : RCP.RecoveryCompositionLaws rclmKernel)
    (rclmMonitors :
      RCP.PreservationMonitors rclmKernel (Relevance := RclmRelevance))
    (coreMonitors :
      RCP.PreservationMonitors coreKernel (Relevance := CoreRelevance))
    (monitorRefinement :
      MonitorRefinement refinement rclmMonitors coreMonitors)
    (predecessor : ArchitecturePredecessor engine)
    (strictStep : StrictArchitectureEngineStep engine predecessor.state) :
    ArchitectureSuccessorResult
        engine refinement coreChecker rclmMonitors coreMonitors
        predecessor strictStep.step ∧
      PaperIIDirectEngineObligations
        semantics
        predecessor.state
        strictStep.step.candidate
        strictStep.step.certificate := by
  have architectureResult :
      ArchitectureSuccessorResult
        engine refinement coreChecker rclmMonitors coreMonitors
        predecessor strictStep.step :=
    rclm_architecture_successor_theorem
      rclmChecker coreChecker engine refinement checkerRefinement
      rclmRecoveryLaws rclmMonitors coreMonitors monitorRefinement
      predecessor strictStep.step
  have directObligations :
      PaperIIDirectEngineObligations
        semantics
        predecessor.state
        strictStep.step.candidate
        strictStep.step.certificate :=
    paper_ii_direct_engine_obligations
      semantics
      architectureResult.rclmObligations
      architectureResult.successorDomain
      strictStep.strictWitness
  exact ⟨architectureResult, directObligations⟩

theorem rclm_constructive_direct_nl_rsi_engine_exists
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {Proposal Witness TrustAnchor ResourceRecord CoreRelevance RclmRelevance : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex}
    (rclmChecker : RCP.TrustedChecker rclmKernel)
    (coreChecker : RCP.TrustedChecker coreKernel)
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      rclmKernel rclmChecker)
    (semantics : PaperIIDirectEngineSemantics engine)
    (refinement : KernelRefinement rclmKernel coreKernel)
    (checkerRefinement :
      CheckerRefinement refinement rclmChecker coreChecker)
    (rclmRecoveryLaws : RCP.RecoveryCompositionLaws rclmKernel)
    (rclmMonitors :
      RCP.PreservationMonitors rclmKernel (Relevance := RclmRelevance))
    (coreMonitors :
      RCP.PreservationMonitors coreKernel (Relevance := CoreRelevance))
    (monitorRefinement :
      MonitorRefinement refinement rclmMonitors coreMonitors)
    (predecessor : ArchitecturePredecessor engine)
    (available : StrictArchitectureSuccessorAvailableAt engine predecessor) :
    ∃ strictStep : StrictArchitectureEngineStep engine predecessor.state,
      ArchitectureSuccessorResult
          engine refinement coreChecker rclmMonitors coreMonitors
          predecessor strictStep.step ∧
        PaperIIDirectEngineObligations
          semantics
          predecessor.state
          strictStep.step.candidate
          strictStep.step.certificate := by
  rcases available with ⟨strictStep⟩
  have aligned :=
    rclm_constructive_direct_nl_rsi_engine_aligned
      rclmChecker coreChecker engine semantics refinement checkerRefinement
      rclmRecoveryLaws rclmMonitors coreMonitors monitorRefinement
      predecessor strictStep
  exact ⟨strictStep, aligned⟩

end RCLM
end RcpRclmFormalCoreV2
