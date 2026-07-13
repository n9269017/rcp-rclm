import RcpRclmFormalCoreV2.RCLM.PaperIIBoundedSeedTrajectory
import RcpRclmFormalCoreV2.RCLM.ClassicalBinarySeedLibrary

namespace RcpRclmFormalCoreV2
namespace RCLM
namespace ClassicalBinary

def initialBoundedSeedPredecessor :
    PaperIIBoundedSeedPredecessor boundedSeedLibrary where
  predecessor := initialArchitecturePredecessor
  seedDomain := Or.inl rfl

noncomputable def classicalInfiniteBoundedSeedTrajectory :
    InfiniteArchitectureTrajectory architectureEngine :=
  buildInfinitePaperIIBoundedSeedTrajectory
    boundedSeedLibrary
    initialBoundedSeedPredecessor

theorem classical_infinite_bounded_seed_domain
    (n : Nat) :
    boundedSeedDomain
      (classicalInfiniteBoundedSeedTrajectory.predecessor n).state := by
  exact infinite_paper_ii_bounded_seed_domain
    boundedSeedLibrary
    initialBoundedSeedPredecessor
    n

theorem classical_infinite_bounded_seed_step_result
    (n : Nat) :
    PaperIIBoundedSeedSuccessorResult
      boundedSeedSemanticIdentification
      boundedSeedLibrary
      (infinitePaperIIBoundedSeedPredecessor
        boundedSeedLibrary initialBoundedSeedPredecessor n).predecessor
      (infinitePaperIIBoundedSeedPacket
        boundedSeedLibrary initialBoundedSeedPredecessor n) := by
  exact infinite_paper_ii_bounded_seed_step_result
    paperIISuccessorSemantics
    paperIIUncertaintySemantics
    boundedSeedSemanticIdentification
    boundedSeedLibrary
    initialBoundedSeedPredecessor
    n

theorem classical_infinite_bounded_seed_trajectory_exists :
    ∃ trajectory : InfiniteArchitectureTrajectory architectureEngine,
      trajectory.predecessor 0 = initialArchitecturePredecessor ∧
        ∀ n, boundedSeedDomain (trajectory.predecessor n).state := by
  exact conditional_infinite_paper_ii_bounded_seed_trajectory_exists
    boundedSeedLibrary
    initialBoundedSeedPredecessor

theorem classical_infinite_bounded_seed_step_refines_architecture
    (n : Nat) :
    ArchitectureSuccessorResult
        architectureEngine
        kernelRefinement
        RCP.ClassicalFinite.binaryChecker
        preservationMonitors
        binaryPreservationMonitors
        (infinitePaperIIBoundedSeedPredecessor
          boundedSeedLibrary initialBoundedSeedPredecessor n).predecessor
        (infinitePaperIIBoundedSeedPacket
          boundedSeedLibrary initialBoundedSeedPredecessor n).toEngineStep ∧
      PaperIIBoundedSeedSuccessorResult
        boundedSeedSemanticIdentification
        boundedSeedLibrary
        (infinitePaperIIBoundedSeedPredecessor
          boundedSeedLibrary initialBoundedSeedPredecessor n).predecessor
        (infinitePaperIIBoundedSeedPacket
          boundedSeedLibrary initialBoundedSeedPredecessor n) := by
  exact infinite_paper_ii_bounded_seed_step_refines_architecture
    checker
    RCP.ClassicalFinite.binaryChecker
    architectureEngine
    paperIISuccessorSemantics
    paperIIUncertaintySemantics
    boundedSeedSemanticIdentification
    boundedSeedLibrary
    kernelRefinement
    checkerRefinement
    recoveryCompositionLaws
    preservationMonitors
    binaryPreservationMonitors
    monitorRefinement
    initialBoundedSeedPredecessor
    n

end ClassicalBinary
end RCLM
end RcpRclmFormalCoreV2
