import RcpRclmFormalCoreV2.RCLM.PaperIIBoundedSeedLibrary

namespace RcpRclmFormalCoreV2
namespace RCLM

noncomputable def choosePaperIIBoundedSeedPacket
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (predecessor : PaperIIBoundedSeedPredecessor library) :
    PaperIIBoundedSeedPacket library predecessor.predecessor.state :=
  Classical.choice
    (paper_ii_bounded_seed_packet_available library predecessor.seedDomain)

def nextPaperIIBoundedSeedPredecessor
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (predecessor : PaperIIBoundedSeedPredecessor library)
    (packet :
      PaperIIBoundedSeedPacket library predecessor.predecessor.state) :
    PaperIIBoundedSeedPredecessor library where
  predecessor :=
    nextArchitecturePredecessor
      engine
      predecessor.predecessor
      packet.toEngineStep
  seedDomain := by
    change library.seedDomain packet.toEngineStep.candidate.next
    exact library.successorSeedDomain packet.seedDomain packet.wordInGrammar

noncomputable def infinitePaperIIBoundedSeedPredecessor
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library) :
    Nat → PaperIIBoundedSeedPredecessor library
  | 0 => initial
  | n + 1 =>
      let predecessor :=
        infinitePaperIIBoundedSeedPredecessor library initial n
      let packet := choosePaperIIBoundedSeedPacket library predecessor
      nextPaperIIBoundedSeedPredecessor library predecessor packet

noncomputable def infinitePaperIIBoundedSeedPacket
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library)
    (n : Nat) :
    PaperIIBoundedSeedPacket
      library
      (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor.state :=
  choosePaperIIBoundedSeedPacket
    library
    (infinitePaperIIBoundedSeedPredecessor library initial n)

noncomputable def infinitePaperIIBoundedSeedStep
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library)
    (n : Nat) :
    ArchitectureEngineStep
      engine
      (infinitePaperIIBoundedSeedPredecessor
        library initial n).predecessor.state :=
  (infinitePaperIIBoundedSeedPacket library initial n).toEngineStep

noncomputable def buildInfinitePaperIIBoundedSeedTrajectory
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library) :
    InfiniteArchitectureTrajectory engine where
  predecessor := fun n =>
    (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor
  step := fun n => infinitePaperIIBoundedSeedStep library initial n
  linked := by
    intro n
    rfl

theorem infinite_paper_ii_bounded_seed_domain
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library)
    (n : Nat) :
    library.seedDomain
      ((buildInfinitePaperIIBoundedSeedTrajectory
        library initial).predecessor n).state := by
  exact
    (infinitePaperIIBoundedSeedPredecessor library initial n).seedDomain

theorem infinite_paper_ii_bounded_seed_step_result
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (identification :
      PaperIISeedSemanticIdentification successorSemantics uncertaintySemantics)
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library)
    (n : Nat) :
    PaperIIBoundedSeedSuccessorResult
      identification
      library
      (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor
      (infinitePaperIIBoundedSeedPacket library initial n) := by
  exact paper_ii_bounded_seed_packet_builder_sound
    successorSemantics
    uncertaintySemantics
    identification
    library
    (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor
    (infinitePaperIIBoundedSeedPacket library initial n)

theorem conditional_infinite_paper_ii_bounded_seed_trajectory_exists
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (initial : PaperIIBoundedSeedPredecessor library) :
    ∃ trajectory : InfiniteArchitectureTrajectory engine,
      trajectory.predecessor 0 = initial.predecessor ∧
        ∀ n, library.seedDomain (trajectory.predecessor n).state := by
  let trajectory := buildInfinitePaperIIBoundedSeedTrajectory library initial
  refine ⟨trajectory, ?_, ?_⟩
  · rfl
  · intro n
    exact infinite_paper_ii_bounded_seed_domain library initial n

theorem infinite_paper_ii_bounded_seed_step_refines_architecture
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {Proposal Witness TrustAnchor ResourceRecord Word CoreRelevance RclmRelevance : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
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
    (successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (identification :
      PaperIISeedSemanticIdentification successorSemantics uncertaintySemantics)
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
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
    (initial : PaperIIBoundedSeedPredecessor library)
    (n : Nat) :
    ArchitectureSuccessorResult
        engine refinement coreChecker rclmMonitors coreMonitors
        (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor
        (infinitePaperIIBoundedSeedPacket library initial n).toEngineStep ∧
      PaperIIBoundedSeedSuccessorResult
        identification
        library
        (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor
        (infinitePaperIIBoundedSeedPacket library initial n) := by
  exact paper_ii_bounded_seed_packet_refines_architecture
    rclmChecker
    coreChecker
    engine
    successorSemantics
    uncertaintySemantics
    identification
    library
    refinement
    checkerRefinement
    rclmRecoveryLaws
    rclmMonitors
    coreMonitors
    monitorRefinement
    (infinitePaperIIBoundedSeedPredecessor library initial n).predecessor
    (infinitePaperIIBoundedSeedPacket library initial n)

end RCLM
end RcpRclmFormalCoreV2
