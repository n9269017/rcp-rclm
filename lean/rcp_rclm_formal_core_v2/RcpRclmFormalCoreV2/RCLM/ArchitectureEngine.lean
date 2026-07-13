import RcpRclmFormalCoreV2.RCLM.ArchitectureTheorem
import RcpRclmFormalCoreV2.RCP.InfiniteHorizon

namespace RcpRclmFormalCoreV2
namespace RCLM

structure ArchitectureEngine
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    (kernel : RCP.Kernel State Update Certificate Protected ResidualIndex)
    (checker : RCP.TrustedChecker kernel) where
  domain : State → Prop
  witnessLibrary : Witness → Prop
  proposes : State → Witness → Proposal → Prop
  constructsCertificate : State → Proposal → Certificate → Prop
  selectsCandidate :
    State → Proposal → Certificate → RCP.Candidate State Update → Prop
  realizesSuccessor :
    State → RCP.Candidate State Update → State → Prop
  trustAnchorValid : State → TrustAnchor → Prop
  resourcePremise :
    State → Proposal → Certificate →
      RCP.Candidate State Update → ResourceRecord → Prop
  realizerTyped :
    ∀ {state witness proposal certificate candidate},
      domain state →
      witnessLibrary witness →
      proposes state witness proposal →
      constructsCertificate state proposal certificate →
      selectsCandidate state proposal certificate candidate →
      realizesSuccessor state candidate candidate.next →
      RCP.TypedSuccessor kernel state candidate
  trustAnchorSound :
    ∀ {state witness proposal certificate candidate anchor},
      domain state →
      witnessLibrary witness →
      proposes state witness proposal →
      constructsCertificate state proposal certificate →
      selectsCandidate state proposal certificate candidate →
      trustAnchorValid state anchor →
      kernel.trustValid state candidate certificate
  resourcePremiseSound :
    ∀ {state proposal certificate candidate resource},
      domain state →
      constructsCertificate state proposal certificate →
      selectsCandidate state proposal certificate candidate →
      resourcePremise state proposal certificate candidate resource →
      kernel.resourceValid state candidate certificate
  successorDomain :
    ∀ {state witness proposal certificate candidate anchor resource},
      domain state →
      kernel.admissible state →
      kernel.protectedInvariant state →
      witnessLibrary witness →
      proposes state witness proposal →
      constructsCertificate state proposal certificate →
      selectsCandidate state proposal certificate candidate →
      realizesSuccessor state candidate candidate.next →
      trustAnchorValid state anchor →
      resourcePremise state proposal certificate candidate resource →
      checker.check state candidate certificate = true →
      domain candidate.next
  trustAnchorPreserved :
    ∀ {state witness proposal certificate candidate anchor resource},
      domain state →
      kernel.admissible state →
      kernel.protectedInvariant state →
      witnessLibrary witness →
      proposes state witness proposal →
      constructsCertificate state proposal certificate →
      selectsCandidate state proposal certificate candidate →
      realizesSuccessor state candidate candidate.next →
      trustAnchorValid state anchor →
      resourcePremise state proposal certificate candidate resource →
      checker.check state candidate certificate = true →
      trustAnchorValid candidate.next anchor

structure ArchitecturePredecessor
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) where
  state : State
  trustAnchor : TrustAnchor
  domainValid : engine.domain state
  admissible : kernel.admissible state
  invariant : kernel.protectedInvariant state
  trustAnchorValid : engine.trustAnchorValid state trustAnchor

structure ArchitectureEngineStep
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
  witness : Witness
  proposal : Proposal
  certificate : Certificate
  candidate : RCP.Candidate State Update
  resource : ResourceRecord
  witnessCovered : engine.witnessLibrary witness
  proposalGenerated : engine.proposes state witness proposal
  certificateConstructed :
    engine.constructsCertificate state proposal certificate
  candidateSelected :
    engine.selectsCandidate state proposal certificate candidate
  successorRealized :
    engine.realizesSuccessor state candidate candidate.next
  resourceAuthorized :
    engine.resourcePremise state proposal certificate candidate resource
  checkerAccepted : checker.check state candidate certificate = true

def ArchitectureSuccessorAvailability
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) : Prop :=
  ∀ predecessor : ArchitecturePredecessor engine,
    Nonempty (ArchitectureEngineStep engine predecessor.state)

def nextArchitecturePredecessor
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (predecessor : ArchitecturePredecessor engine)
    (step : ArchitectureEngineStep engine predecessor.state) :
    ArchitecturePredecessor engine := by
  have obligations :
      RCP.StepObligations
        kernel predecessor.state step.candidate step.certificate :=
    checker.sound predecessor.admissible predecessor.invariant
      step.checkerAccepted
  refine
    { state := step.candidate.next
      trustAnchor := predecessor.trustAnchor
      domainValid := ?_
      admissible := obligations.successorAdmissible
      invariant := obligations.invariantPreserved
      trustAnchorValid := ?_ }
  · exact engine.successorDomain
      predecessor.domainValid
      predecessor.admissible
      predecessor.invariant
      step.witnessCovered
      step.proposalGenerated
      step.certificateConstructed
      step.candidateSelected
      step.successorRealized
      predecessor.trustAnchorValid
      step.resourceAuthorized
      step.checkerAccepted
  · exact engine.trustAnchorPreserved
      predecessor.domainValid
      predecessor.admissible
      predecessor.invariant
      step.witnessCovered
      step.proposalGenerated
      step.certificateConstructed
      step.candidateSelected
      step.successorRealized
      predecessor.trustAnchorValid
      step.resourceAuthorized
      step.checkerAccepted

structure ArchitectureSuccessorResult
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {Proposal Witness TrustAnchor ResourceRecord CoreRelevance RclmRelevance : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex}
    {rclmChecker : RCP.TrustedChecker rclmKernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      rclmKernel rclmChecker)
    (refinement : KernelRefinement rclmKernel coreKernel)
    (coreChecker : RCP.TrustedChecker coreKernel)
    (rclmMonitors :
      RCP.PreservationMonitors rclmKernel (Relevance := RclmRelevance))
    (coreMonitors :
      RCP.PreservationMonitors coreKernel (Relevance := CoreRelevance))
    (predecessor : ArchitecturePredecessor engine)
    (step : ArchitectureEngineStep engine predecessor.state) : Prop where
  engineTypedSuccessor :
    RCP.TypedSuccessor rclmKernel predecessor.state step.candidate
  rclmObligations :
    RCP.StepObligations
      rclmKernel predecessor.state step.candidate step.certificate
  coreCheckerAccepted :
    coreChecker.check
      (refinement.forgetState predecessor.state)
      (refinement.forgetCandidate step.candidate)
      (refinement.forgetCertificate step.certificate) = true
  coreObligations :
    RCP.StepObligations
      coreKernel
      (refinement.forgetState predecessor.state)
      (refinement.forgetCandidate step.candidate)
      (refinement.forgetCertificate step.certificate)
  coreRecoveryLaws : Nonempty (RCP.RecoveryCompositionLaws coreKernel)
  monitorRefinementEvidence :
    Nonempty (MonitorRefinement refinement rclmMonitors coreMonitors)
  successorDomain : engine.domain step.candidate.next
  successorAdmissible : rclmKernel.admissible step.candidate.next
  successorInvariant : rclmKernel.protectedInvariant step.candidate.next
  engineTrustValid :
    rclmKernel.trustValid predecessor.state step.candidate step.certificate
  engineResourceValid :
    rclmKernel.resourceValid predecessor.state step.candidate step.certificate
  trustAnchorPreserved :
    engine.trustAnchorValid step.candidate.next predecessor.trustAnchor

theorem rclm_architecture_successor_theorem
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
    (step : ArchitectureEngineStep engine predecessor.state) :
    ArchitectureSuccessorResult
      engine refinement coreChecker rclmMonitors coreMonitors predecessor step := by
  have engineTypedSuccessor :
      RCP.TypedSuccessor rclmKernel predecessor.state step.candidate :=
    engine.realizerTyped
      predecessor.domainValid
      step.witnessCovered
      step.proposalGenerated
      step.certificateConstructed
      step.candidateSelected
      step.successorRealized
  have rclmObligations :
      RCP.StepObligations
        rclmKernel predecessor.state step.candidate step.certificate :=
    rclmChecker.sound predecessor.admissible predecessor.invariant
      step.checkerAccepted
  have coreCheckerAccepted :
      coreChecker.check
        (refinement.forgetState predecessor.state)
        (refinement.forgetCandidate step.candidate)
        (refinement.forgetCertificate step.certificate) = true :=
    rclm_checker_acceptance_preserved
      refinement rclmChecker coreChecker checkerRefinement
      step.checkerAccepted
  have coreAdmissible :
      coreKernel.admissible (refinement.forgetState predecessor.state) :=
    refinement.admissiblePreserved predecessor.state predecessor.admissible
  have coreInvariant :
      coreKernel.protectedInvariant
        (refinement.forgetState predecessor.state) :=
    refinement.invariantPreserved predecessor.state predecessor.invariant
  have coreObligations :
      RCP.StepObligations
        coreKernel
        (refinement.forgetState predecessor.state)
        (refinement.forgetCandidate step.candidate)
        (refinement.forgetCertificate step.certificate) :=
    coreChecker.sound coreAdmissible coreInvariant coreCheckerAccepted
  have coreRecoveryLaws : RCP.RecoveryCompositionLaws coreKernel :=
    rclm_recovery_laws_refine_rcp refinement rclmRecoveryLaws
  have successorDomain : engine.domain step.candidate.next :=
    engine.successorDomain
      predecessor.domainValid
      predecessor.admissible
      predecessor.invariant
      step.witnessCovered
      step.proposalGenerated
      step.certificateConstructed
      step.candidateSelected
      step.successorRealized
      predecessor.trustAnchorValid
      step.resourceAuthorized
      step.checkerAccepted
  have engineTrustValid :
      rclmKernel.trustValid
        predecessor.state step.candidate step.certificate :=
    engine.trustAnchorSound
      predecessor.domainValid
      step.witnessCovered
      step.proposalGenerated
      step.certificateConstructed
      step.candidateSelected
      predecessor.trustAnchorValid
  have engineResourceValid :
      rclmKernel.resourceValid
        predecessor.state step.candidate step.certificate :=
    engine.resourcePremiseSound
      predecessor.domainValid
      step.certificateConstructed
      step.candidateSelected
      step.resourceAuthorized
  have trustAnchorPreserved :
      engine.trustAnchorValid
        step.candidate.next predecessor.trustAnchor :=
    engine.trustAnchorPreserved
      predecessor.domainValid
      predecessor.admissible
      predecessor.invariant
      step.witnessCovered
      step.proposalGenerated
      step.certificateConstructed
      step.candidateSelected
      step.successorRealized
      predecessor.trustAnchorValid
      step.resourceAuthorized
      step.checkerAccepted
  exact
    { engineTypedSuccessor := engineTypedSuccessor
      rclmObligations := rclmObligations
      coreCheckerAccepted := coreCheckerAccepted
      coreObligations := coreObligations
      coreRecoveryLaws := ⟨coreRecoveryLaws⟩
      monitorRefinementEvidence := ⟨monitorRefinement⟩
      successorDomain := successorDomain
      successorAdmissible := rclmObligations.successorAdmissible
      successorInvariant := rclmObligations.invariantPreserved
      engineTrustValid := engineTrustValid
      engineResourceValid := engineResourceValid
      trustAnchorPreserved := trustAnchorPreserved }

noncomputable def chooseArchitectureEngineStep
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (availability : ArchitectureSuccessorAvailability engine)
    (predecessor : ArchitecturePredecessor engine) :
    ArchitectureEngineStep engine predecessor.state :=
  Classical.choice (availability predecessor)

noncomputable def infiniteArchitecturePredecessor
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (availability : ArchitectureSuccessorAvailability engine)
    (initial : ArchitecturePredecessor engine) :
    Nat → ArchitecturePredecessor engine
  | 0 => initial
  | n + 1 =>
      nextArchitecturePredecessor engine
        (infiniteArchitecturePredecessor engine availability initial n)
        (chooseArchitectureEngineStep engine availability
          (infiniteArchitecturePredecessor engine availability initial n))

noncomputable def infiniteArchitectureEngineStep
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (availability : ArchitectureSuccessorAvailability engine)
    (initial : ArchitecturePredecessor engine)
    (n : Nat) :
    ArchitectureEngineStep engine
      (infiniteArchitecturePredecessor engine availability initial n).state :=
  chooseArchitectureEngineStep engine availability
    (infiniteArchitecturePredecessor engine availability initial n)

structure InfiniteArchitectureTrajectory
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) where
  predecessor : Nat → ArchitecturePredecessor engine
  step : (n : Nat) → ArchitectureEngineStep engine (predecessor n).state
  linked : ∀ n, (predecessor (n + 1)).state = (step n).candidate.next

namespace InfiniteArchitectureTrajectory

noncomputable def toAcceptedTrajectory
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (trajectory : InfiniteArchitectureTrajectory engine) :
    RCP.InfiniteAcceptedTrajectory checker where
  state := fun n => (trajectory.predecessor n).state
  candidate := fun n => (trajectory.step n).candidate
  certificate := fun n => (trajectory.step n).certificate
  accepted := fun n => (trajectory.step n).checkerAccepted
  linked := trajectory.linked
  admissible := fun n => (trajectory.predecessor n).admissible
  invariant := fun n => (trajectory.predecessor n).invariant

noncomputable def toCoreAcceptedTrajectory
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {Proposal Witness TrustAnchor ResourceRecord : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex}
    {rclmChecker : RCP.TrustedChecker rclmKernel}
    {coreChecker : RCP.TrustedChecker coreKernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      rclmKernel rclmChecker}
    (trajectory : InfiniteArchitectureTrajectory engine)
    (refinement : KernelRefinement rclmKernel coreKernel)
    (checkerRefinement :
      CheckerRefinement refinement rclmChecker coreChecker) :
    RCP.InfiniteAcceptedTrajectory coreChecker where
  state := fun n => refinement.forgetState (trajectory.predecessor n).state
  candidate := fun n => refinement.forgetCandidate (trajectory.step n).candidate
  certificate := fun n =>
    refinement.forgetCertificate (trajectory.step n).certificate
  accepted := fun n =>
    checkerRefinement.acceptancePreserved
      (trajectory.predecessor n).state
      (trajectory.step n).candidate
      (trajectory.step n).certificate
      (trajectory.step n).checkerAccepted
  linked := by
    intro n
    have mapped := congrArg refinement.forgetState (trajectory.linked n)
    simpa [KernelRefinement.forgetCandidate] using mapped
  admissible := fun n =>
    refinement.admissiblePreserved
      (trajectory.predecessor n).state
      (trajectory.predecessor n).admissible
  invariant := fun n =>
    refinement.invariantPreserved
      (trajectory.predecessor n).state
      (trajectory.predecessor n).invariant

end InfiniteArchitectureTrajectory

noncomputable def buildInfiniteArchitectureTrajectory
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (availability : ArchitectureSuccessorAvailability engine)
    (initial : ArchitecturePredecessor engine) :
    InfiniteArchitectureTrajectory engine where
  predecessor := infiniteArchitecturePredecessor engine availability initial
  step := infiniteArchitectureEngineStep engine availability initial
  linked := by
    intro n
    rfl

theorem conditional_infinite_architecture_trajectory_exists
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (availability : ArchitectureSuccessorAvailability engine)
    (initial : ArchitecturePredecessor engine) :
    ∃ trajectory : InfiniteArchitectureTrajectory engine,
      trajectory.predecessor 0 = initial := by
  exact
    ⟨buildInfiniteArchitectureTrajectory engine availability initial, rfl⟩

theorem infinite_architecture_step_result
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
    (trajectory : InfiniteArchitectureTrajectory engine)
    (n : Nat) :
    ArchitectureSuccessorResult
      engine refinement coreChecker rclmMonitors coreMonitors
      (trajectory.predecessor n) (trajectory.step n) := by
  exact rclm_architecture_successor_theorem
    rclmChecker coreChecker engine refinement checkerRefinement
    rclmRecoveryLaws rclmMonitors coreMonitors monitorRefinement
    (trajectory.predecessor n) (trajectory.step n)

end RCLM
end RcpRclmFormalCoreV2
