import RcpRclmFormalCoreV2.RCLM.State
import RcpRclmFormalCoreV2.RCLM.Update
import RcpRclmFormalCoreV2.RCLM.CertificatePacket
import RcpRclmFormalCoreV2.RCLM.Refinement

namespace RcpRclmFormalCoreV2
namespace RCLM

variable
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState
        RclmUpdate
        RclmCertificate
        RclmProtected
        RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState
        CoreUpdate
        CoreCertificate
        CoreProtected
        CoreResidualIndex}


theorem rclm_step_obligations_refine_rcp
    (refinement : KernelRefinement rclmKernel coreKernel)
    {state : RclmState}
    {candidate : RCP.Candidate RclmState RclmUpdate}
    {certificate : RclmCertificate}
    (obligations :
      RCP.StepObligations rclmKernel state candidate certificate) :
    RCP.StepObligations
      coreKernel
      (refinement.forgetState state)
      (refinement.forgetCandidate candidate)
      (refinement.forgetCertificate certificate) :=
  refinement.stepObligationsPreserved obligations


theorem rclm_checker_refines_rcp
    (refinement : KernelRefinement rclmKernel coreKernel)
    (rclmChecker : RCP.TrustedChecker rclmKernel)
    {state : RclmState}
    {candidate : RCP.Candidate RclmState RclmUpdate}
    {certificate : RclmCertificate}
    (stateAdmissible : rclmKernel.admissible state)
    (stateInvariant : rclmKernel.protectedInvariant state)
    (accepted : rclmChecker.check state candidate certificate = true) :
    RCP.StepObligations
      coreKernel
      (refinement.forgetState state)
      (refinement.forgetCandidate candidate)
      (refinement.forgetCertificate certificate) := by
  have rclmObligations :
      RCP.StepObligations rclmKernel state candidate certificate :=
    rclmChecker.sound stateAdmissible stateInvariant accepted
  exact refinement.stepObligationsPreserved rclmObligations


theorem rclm_checker_acceptance_preserved
    (refinement : KernelRefinement rclmKernel coreKernel)
    (rclmChecker : RCP.TrustedChecker rclmKernel)
    (coreChecker : RCP.TrustedChecker coreKernel)
    (checkerRefinement :
      CheckerRefinement refinement rclmChecker coreChecker)
    {state : RclmState}
    {candidate : RCP.Candidate RclmState RclmUpdate}
    {certificate : RclmCertificate}
    (accepted : rclmChecker.check state candidate certificate = true) :
    coreChecker.check
      (refinement.forgetState state)
      (refinement.forgetCandidate candidate)
      (refinement.forgetCertificate certificate) = true :=
  checkerRefinement.acceptancePreserved state candidate certificate accepted


theorem rclm_checker_pair_refines_rcp
    (refinement : KernelRefinement rclmKernel coreKernel)
    (rclmChecker : RCP.TrustedChecker rclmKernel)
    (coreChecker : RCP.TrustedChecker coreKernel)
    (checkerRefinement :
      CheckerRefinement refinement rclmChecker coreChecker)
    {state : RclmState}
    {candidate : RCP.Candidate RclmState RclmUpdate}
    {certificate : RclmCertificate}
    (stateAdmissible : rclmKernel.admissible state)
    (stateInvariant : rclmKernel.protectedInvariant state)
    (accepted : rclmChecker.check state candidate certificate = true) :
    RCP.StepObligations
      coreKernel
      (refinement.forgetState state)
      (refinement.forgetCandidate candidate)
      (refinement.forgetCertificate certificate) := by
  have coreAdmissible :
      coreKernel.admissible (refinement.forgetState state) :=
    refinement.admissiblePreserved state stateAdmissible
  have coreInvariant :
      coreKernel.protectedInvariant (refinement.forgetState state) :=
    refinement.invariantPreserved state stateInvariant
  have coreAccepted :
      coreChecker.check
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (refinement.forgetCertificate certificate) = true :=
    checkerRefinement.acceptancePreserved
      state candidate certificate accepted
  exact coreChecker.sound coreAdmissible coreInvariant coreAccepted


theorem rclm_recovery_laws_refine_rcp
    (refinement : KernelRefinement rclmKernel coreKernel)
    (laws : RCP.RecoveryCompositionLaws rclmKernel) :
    RCP.RecoveryCompositionLaws coreKernel :=
  refinement.recoveryCompositionLawsPreserved laws


theorem rclm_monitor_refinement_valid
    {CoreRelevance RclmRelevance : Type*}
    (refinement : KernelRefinement rclmKernel coreKernel)
    (rclmMonitors :
      RCP.PreservationMonitors rclmKernel (Relevance := RclmRelevance))
    (coreMonitors :
      RCP.PreservationMonitors coreKernel (Relevance := CoreRelevance))
    (monitorRefinement :
      MonitorRefinement refinement rclmMonitors coreMonitors) :
    (∀ relevance,
      monitorRefinement.forgetRelevance
          (monitorRefinement.liftRelevance relevance) = relevance) ∧
    (∀ state,
      rclmMonitors.lyapunovValue state =
        coreMonitors.lyapunovValue (refinement.forgetState state)) ∧
    (∀ state candidate certificate,
      rclmMonitors.motionCharge state candidate certificate =
        coreMonitors.motionCharge
          (refinement.forgetState state)
          (refinement.forgetCandidate candidate)
          (refinement.forgetCertificate certificate)) ∧
    (∀ state candidate certificate,
      rclmMonitors.lyapunovError state candidate certificate =
        coreMonitors.lyapunovError
          (refinement.forgetState state)
          (refinement.forgetCandidate candidate)
          (refinement.forgetCertificate certificate)) ∧
    (∀ state candidate certificate,
      rclmMonitors.unsupportedCollapse state candidate certificate =
        coreMonitors.unsupportedCollapse
          (refinement.forgetState state)
          (refinement.forgetCandidate candidate)
          (refinement.forgetCertificate certificate)) ∧
    (∀ state candidate certificate,
      rclmMonitors.ambiguityError state candidate certificate =
        coreMonitors.ambiguityError
          (refinement.forgetState state)
          (refinement.forgetCandidate candidate)
          (refinement.forgetCertificate certificate)) ∧
    (∀ state relevance,
      rclmMonitors.relevanceValue state relevance =
        coreMonitors.relevanceValue
          (refinement.forgetState state)
          (monitorRefinement.forgetRelevance relevance)) ∧
    (∀ state candidate relevance,
      monitorRefinement.forgetRelevance
          (rclmMonitors.transportRelevance state candidate relevance) =
        coreMonitors.transportRelevance
          (refinement.forgetState state)
          (refinement.forgetCandidate candidate)
          (monitorRefinement.forgetRelevance relevance)) ∧
    (∀ state candidate certificate,
      rclmMonitors.relevanceError state candidate certificate =
        coreMonitors.relevanceError
          (refinement.forgetState state)
          (refinement.forgetCandidate candidate)
          (refinement.forgetCertificate certificate)) := by
  refine ⟨monitorRefinement.forgetLiftRelevance, ?_⟩
  refine ⟨monitorRefinement.lyapunovValuePreserved, ?_⟩
  refine ⟨monitorRefinement.motionChargePreserved, ?_⟩
  refine ⟨monitorRefinement.lyapunovErrorPreserved, ?_⟩
  refine ⟨monitorRefinement.unsupportedCollapsePreserved, ?_⟩
  refine ⟨monitorRefinement.ambiguityErrorPreserved, ?_⟩
  refine ⟨monitorRefinement.relevanceValuePreserved, ?_⟩
  refine ⟨monitorRefinement.transportRelevancePreserved, ?_⟩
  exact monitorRefinement.relevanceErrorPreserved

end RCLM
end RcpRclmFormalCoreV2
