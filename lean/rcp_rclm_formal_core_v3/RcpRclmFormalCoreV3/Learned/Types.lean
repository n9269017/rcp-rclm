import Mathlib.Data.Finset.Card
import RcpRclmFormalCoreV2.RCP

namespace RcpRclmFormalCoreV3
namespace Learned

/--
A learned package state keeps the complete successor-relevant package surface inside
one typed object.  The trusted checker and trust anchor are deliberately absent:
they remain external to the successor package.
-/
structure PackageState
    (BaseState ModelArchitecture ModelWeights Generator Planner TrainingPolicy
      RetrievalPolicy Memory Tokenizer VerificationPolicy ResourcePolicy SelfModel
      Task : Type*)
    [DecidableEq Task] where
  base : BaseState
  modelArchitecture : ModelArchitecture
  modelWeights : ModelWeights
  generator : Generator
  planner : Planner
  trainingPolicy : TrainingPolicy
  retrievalPolicy : RetrievalPolicy
  memory : Memory
  tokenizer : Tokenizer
  verificationPolicy : VerificationPolicy
  resourcePolicy : ResourcePolicy
  selfModel : SelfModel
  capabilityFrontier : Finset Task

/--
A typed learned-package update.  Every field is explicit so that a realizer can bind
an accepted successor to the exact changed component set.
-/
structure PackageUpdate
    (BaseUpdate WeightUpdate ArchitectureUpdate GeneratorUpdate PlannerUpdate
      TrainingPolicyUpdate RetrievalUpdate MemoryUpdate TokenizerUpdate
      SelfModelUpdate : Type*) where
  base : BaseUpdate
  weights : WeightUpdate
  architecture : ArchitectureUpdate
  generator : GeneratorUpdate
  planner : PlannerUpdate
  trainingPolicy : TrainingPolicyUpdate
  retrieval : RetrievalUpdate
  memory : MemoryUpdate
  tokenizer : TokenizerUpdate
  selfModel : SelfModelUpdate

/--
Gate D certificate packet.  The fields are untrusted data until the learned checker
validates their bindings to the predecessor, proposal, realized candidate, and
package hash.
-/
structure CertificatePacket
    (BaseCertificate Task Generator Proposal PackageHash : Type*)
    [DecidableEq Task] where
  base : BaseCertificate
  protectedFrontier : Finset Task
  generator : Generator
  proposal : Proposal
  generatorPackageHash : PackageHash
  deriving DecidableEq

end Learned
end RcpRclmFormalCoreV3
