import Mathlib.Data.Finset.Basic
import RcpRclmFormalCoreV2.RCLM.PaperIIAlignmentPremises

namespace RcpRclmFormalCoreV2
namespace RCLM

structure PaperIIPacketBuilderOutput
    (State Update Certificate Proposal Witness ResourceRecord : Type*) where
  witness : Witness
  proposal : Proposal
  certificate : Certificate
  candidate : RCP.Candidate State Update
  resource : ResourceRecord

structure PaperIIBoundedSeedLibrary
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord Word : Type*}
    [DecidableEq Witness]
    [DecidableEq Word]
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) where
  seedDomain : State → Prop
  witnesses : State → Finset Witness
  grammar : State → Finset Word
  wordDepth : Word → Nat
  proofLength : Word → Nat
  maxWordDepth : Nat
  maxProofLength : Nat
  witnessOf : Word → Witness
  proposalOf : Word → Proposal
  certificateOf : Word → Certificate
  candidateOf : State → Word → RCP.Candidate State Update
  resourceOf : State → Word → ResourceRecord
  seedDomain_to_engineDomain :
    ∀ {state}, seedDomain state → engine.domain state
  grammarNonempty :
    ∀ {state}, seedDomain state → (grammar state).Nonempty
  wordWitnessMember :
    ∀ {state word}, word ∈ grammar state → witnessOf word ∈ witnesses state
  witnessMemberCovered :
    ∀ {state witness}, witness ∈ witnesses state → engine.witnessLibrary witness
  wordDepthBound :
    ∀ {state word}, word ∈ grammar state → wordDepth word ≤ maxWordDepth
  proofLengthBound :
    ∀ {state word}, word ∈ grammar state → proofLength word ≤ maxProofLength
  proposalGenerated :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      engine.proposes state (witnessOf word) (proposalOf word)
  certificateConstructed :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      engine.constructsCertificate state (proposalOf word) (certificateOf word)
  candidateSelected :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      engine.selectsCandidate
        state
        (proposalOf word)
        (certificateOf word)
        (candidateOf state word)
  successorRealized :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      engine.realizesSuccessor
        state
        (candidateOf state word)
        (candidateOf state word).next
  resourceAuthorized :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      engine.resourcePremise
        state
        (proposalOf word)
        (certificateOf word)
        (candidateOf state word)
        (resourceOf state word)
  checkerAccepted :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      checker.check
        state
        (candidateOf state word)
        (certificateOf word) = true
  successorSeedDomain :
    ∀ {state word},
      seedDomain state →
      word ∈ grammar state →
      seedDomain (candidateOf state word).next

namespace PaperIIBoundedSeedLibrary

def buildPacket
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
    (state : State)
    (word : Word) :
    PaperIIPacketBuilderOutput
      State Update Certificate Proposal Witness ResourceRecord where
  witness := library.witnessOf word
  proposal := library.proposalOf word
  certificate := library.certificateOf word
  candidate := library.candidateOf state word
  resource := library.resourceOf state word

end PaperIIBoundedSeedLibrary

structure PaperIIBoundedSeedPacket
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
    (state : State) where
  word : Word
  seedDomain : library.seedDomain state
  wordInGrammar : word ∈ library.grammar state

namespace PaperIIBoundedSeedPacket

def toEngineStep
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
    {library : PaperIIBoundedSeedLibrary (Word := Word) engine}
    {state : State}
    (packet : PaperIIBoundedSeedPacket library state) :
    ArchitectureEngineStep engine state where
  witness := library.witnessOf packet.word
  proposal := library.proposalOf packet.word
  certificate := library.certificateOf packet.word
  candidate := library.candidateOf state packet.word
  resource := library.resourceOf state packet.word
  witnessCovered :=
    library.witnessMemberCovered
      (library.wordWitnessMember packet.wordInGrammar)
  proposalGenerated :=
    library.proposalGenerated packet.seedDomain packet.wordInGrammar
  certificateConstructed :=
    library.certificateConstructed packet.seedDomain packet.wordInGrammar
  candidateSelected :=
    library.candidateSelected packet.seedDomain packet.wordInGrammar
  successorRealized :=
    library.successorRealized packet.seedDomain packet.wordInGrammar
  resourceAuthorized :=
    library.resourceAuthorized packet.seedDomain packet.wordInGrammar
  checkerAccepted :=
    library.checkerAccepted packet.seedDomain packet.wordInGrammar

end PaperIIBoundedSeedPacket

structure PaperIIBoundedSeedPredecessor
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
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine) where
  predecessor : ArchitecturePredecessor engine
  seedDomain : library.seedDomain predecessor.state

structure PaperIISeedSemanticIdentification
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
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
      PaperIIUncertaintyEnvelopeSemantics successorSemantics) where
  declaredVerifierSchema : State → VerifierSchema
  declaredTransportVerifierSchema :
    State → RCP.Candidate State Update → VerifierSchema → VerifierSchema
  declaredVerifierSchemaRefines : VerifierSchema → VerifierSchema → Prop
  declaredUncertaintyEnvelope : State → UncertaintyEnvelope
  declaredTransportUncertaintyEnvelope :
    State → RCP.Candidate State Update → UncertaintyEnvelope → UncertaintyEnvelope
  declaredUncertaintyEnvelopeRefines :
    UncertaintyEnvelope → UncertaintyEnvelope → Prop
  declaredGoal : State → Goal
  declaredTransportGoal : State → RCP.Candidate State Update → Goal → Goal
  declaredGoalDistance : Goal → Goal → ℝ
  declaredGoalDriftBudget :
    State → RCP.Candidate State Update → Certificate → ℝ
  verifierSchemaIdentified :
    ∀ state,
      declaredVerifierSchema state = successorSemantics.stateVerifierSchema state
  verifierTransportIdentified :
    ∀ state candidate schema,
      declaredTransportVerifierSchema state candidate schema =
        successorSemantics.transportVerifierSchema state candidate schema
  verifierRefinementIdentified :
    ∀ first second,
      declaredVerifierSchemaRefines first second =
        successorSemantics.verifierSchemaRefines first second
  uncertaintyEnvelopeIdentified :
    ∀ state,
      declaredUncertaintyEnvelope state = uncertaintySemantics.stateEnvelope state
  uncertaintyTransportIdentified :
    ∀ state candidate envelope,
      declaredTransportUncertaintyEnvelope state candidate envelope =
        uncertaintySemantics.transportEnvelope state candidate envelope
  uncertaintyRefinementIdentified :
    ∀ first second,
      declaredUncertaintyEnvelopeRefines first second =
        uncertaintySemantics.envelopeRefines first second
  goalIdentified :
    ∀ state, declaredGoal state = successorSemantics.stateGoal state
  goalTransportIdentified :
    ∀ state candidate goal,
      declaredTransportGoal state candidate goal =
        successorSemantics.transportGoal state candidate goal
  goalDistanceIdentified :
    ∀ first second,
      declaredGoalDistance first second = successorSemantics.goalDistance first second
  goalDriftBudgetIdentified :
    ∀ state candidate certificate,
      declaredGoalDriftBudget state candidate certificate =
        successorSemantics.goalDriftBudget state candidate certificate

structure PaperIIBoundedSeedSuccessorResult
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
    {successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine}
    {uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics}
    (identification :
      PaperIISeedSemanticIdentification successorSemantics uncertaintySemantics)
    (library : PaperIIBoundedSeedLibrary (Word := Word) engine)
    (predecessor : ArchitecturePredecessor engine)
    (packet : PaperIIBoundedSeedPacket library predecessor.state) : Prop where
  rclmObligations :
    RCP.StepObligations
      kernel
      predecessor.state
      packet.toEngineStep.candidate
      packet.toEngineStep.certificate
  successorVerification :
    PaperIISuccessorVerificationObligations
      successorSemantics
      predecessor.state
      packet.toEngineStep.candidate
      packet.toEngineStep.certificate
  successorSeedDomain : library.seedDomain packet.toEngineStep.candidate.next
  declaredVerifierSchemaPreserved :
    identification.declaredVerifierSchemaRefines
      (identification.declaredTransportVerifierSchema
        predecessor.state
        packet.toEngineStep.candidate
        (identification.declaredVerifierSchema predecessor.state))
      (identification.declaredVerifierSchema packet.toEngineStep.candidate.next)
  declaredUncertaintyEnvelopePreserved :
    identification.declaredUncertaintyEnvelopeRefines
      (identification.declaredTransportUncertaintyEnvelope
        predecessor.state
        packet.toEngineStep.candidate
        (identification.declaredUncertaintyEnvelope predecessor.state))
      (identification.declaredUncertaintyEnvelope packet.toEngineStep.candidate.next)
  declaredGoalIdentityBound :
    identification.declaredGoalDistance
        (identification.declaredGoal packet.toEngineStep.candidate.next)
        (identification.declaredTransportGoal
          predecessor.state
          packet.toEngineStep.candidate
          (identification.declaredGoal predecessor.state)) ≤
      identification.declaredGoalDriftBudget
        predecessor.state
        packet.toEngineStep.candidate
        packet.toEngineStep.certificate

theorem paper_ii_bounded_seed_packet_available
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
    {state : State}
    (seedDomain : library.seedDomain state) :
    Nonempty (PaperIIBoundedSeedPacket library state) := by
  rcases library.grammarNonempty seedDomain with ⟨word, wordInGrammar⟩
  exact
    ⟨{ word := word
       seedDomain := seedDomain
       wordInGrammar := wordInGrammar }⟩

theorem paper_ii_bounded_seed_packet_builder_sound
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
    (predecessor : ArchitecturePredecessor engine)
    (packet : PaperIIBoundedSeedPacket library predecessor.state) :
    PaperIIBoundedSeedSuccessorResult
      identification library predecessor packet := by
  have rclmObligations :
      RCP.StepObligations
        kernel
        predecessor.state
        packet.toEngineStep.candidate
        packet.toEngineStep.certificate :=
    checker.sound
      predecessor.admissible
      predecessor.invariant
      packet.toEngineStep.checkerAccepted
  have successorSeedDomain :
      library.seedDomain packet.toEngineStep.candidate.next :=
    library.successorSeedDomain packet.seedDomain packet.wordInGrammar
  have successorDomain : engine.domain packet.toEngineStep.candidate.next :=
    library.seedDomain_to_engineDomain successorSeedDomain
  have successorVerification :
      PaperIISuccessorVerificationObligations
        successorSemantics
        predecessor.state
        packet.toEngineStep.candidate
        packet.toEngineStep.certificate :=
    paper_ii_successor_verification_obligations
      successorSemantics
      packet.toEngineStep
      rclmObligations
      successorDomain
  have compiledUncertaintyEnvelopePreserved :
      uncertaintySemantics.envelopeRefines
        (uncertaintySemantics.transportEnvelope
          predecessor.state
          packet.toEngineStep.candidate
          (uncertaintySemantics.stateEnvelope predecessor.state))
        (uncertaintySemantics.stateEnvelope packet.toEngineStep.candidate.next) :=
    uncertaintySemantics.oneStepPersistence rclmObligations
  have declaredVerifierSchemaPreserved :
      identification.declaredVerifierSchemaRefines
        (identification.declaredTransportVerifierSchema
          predecessor.state
          packet.toEngineStep.candidate
          (identification.declaredVerifierSchema predecessor.state))
        (identification.declaredVerifierSchema packet.toEngineStep.candidate.next) := by
    rw [identification.verifierRefinementIdentified]
    rw [identification.verifierTransportIdentified]
    rw [identification.verifierSchemaIdentified]
    rw [identification.verifierSchemaIdentified]
    exact successorVerification.verifierSchemaPreserved
  have declaredUncertaintyEnvelopePreserved :
      identification.declaredUncertaintyEnvelopeRefines
        (identification.declaredTransportUncertaintyEnvelope
          predecessor.state
          packet.toEngineStep.candidate
          (identification.declaredUncertaintyEnvelope predecessor.state))
        (identification.declaredUncertaintyEnvelope packet.toEngineStep.candidate.next) := by
    rw [identification.uncertaintyRefinementIdentified]
    rw [identification.uncertaintyTransportIdentified]
    rw [identification.uncertaintyEnvelopeIdentified]
    rw [identification.uncertaintyEnvelopeIdentified]
    exact compiledUncertaintyEnvelopePreserved
  have declaredGoalIdentityBound :
      identification.declaredGoalDistance
          (identification.declaredGoal packet.toEngineStep.candidate.next)
          (identification.declaredTransportGoal
            predecessor.state
            packet.toEngineStep.candidate
            (identification.declaredGoal predecessor.state)) ≤
        identification.declaredGoalDriftBudget
          predecessor.state
          packet.toEngineStep.candidate
          packet.toEngineStep.certificate := by
    rw [identification.goalDistanceIdentified]
    rw [identification.goalIdentified]
    rw [identification.goalTransportIdentified]
    rw [identification.goalIdentified]
    rw [identification.goalDriftBudgetIdentified]
    exact successorVerification.goalIdentityBound
  exact
    { rclmObligations := rclmObligations
      successorVerification := successorVerification
      successorSeedDomain := successorSeedDomain
      declaredVerifierSchemaPreserved := declaredVerifierSchemaPreserved
      declaredUncertaintyEnvelopePreserved :=
        declaredUncertaintyEnvelopePreserved
      declaredGoalIdentityBound := declaredGoalIdentityBound }

theorem paper_ii_bounded_seed_packet_refines_architecture
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
    (predecessor : ArchitecturePredecessor engine)
    (packet : PaperIIBoundedSeedPacket library predecessor.state) :
    ArchitectureSuccessorResult
        engine refinement coreChecker rclmMonitors coreMonitors
        predecessor packet.toEngineStep ∧
      PaperIIBoundedSeedSuccessorResult
        identification library predecessor packet := by
  have architectureResult :
      ArchitectureSuccessorResult
        engine refinement coreChecker rclmMonitors coreMonitors
        predecessor packet.toEngineStep :=
    rclm_architecture_successor_theorem
      rclmChecker
      coreChecker
      engine
      refinement
      checkerRefinement
      rclmRecoveryLaws
      rclmMonitors
      coreMonitors
      monitorRefinement
      predecessor
      packet.toEngineStep
  have seedResult :
      PaperIIBoundedSeedSuccessorResult
        identification library predecessor packet :=
    paper_ii_bounded_seed_packet_builder_sound
      successorSemantics
      uncertaintySemantics
      identification
      library
      predecessor
      packet
  exact ⟨architectureResult, seedResult⟩

end RCLM
end RcpRclmFormalCoreV2
