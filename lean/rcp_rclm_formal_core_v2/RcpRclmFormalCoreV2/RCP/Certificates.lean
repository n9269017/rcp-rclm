import RcpRclmFormalCoreV2.RCP.ProtectedDistinctions
import RcpRclmFormalCoreV2.RCP.Recovery
import RcpRclmFormalCoreV2.RCP.Progress

namespace RcpRclmFormalCoreV2
namespace RCP

/--
The complete one-step obligations that a sound trusted checker must establish.
-/
structure StepObligations
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex)
    (state : State)
    (candidate : Candidate State Update)
    (certificate : Certificate) : Prop where
  typedSuccessor : TypedSuccessor K state candidate
  residualsNonpositive : ∀ index, K.residual state candidate certificate index ≤ 0
  protectedNonLoss : ProtectedNonLoss K state candidate
  constructiveRecovery : ConstructiveRecovery K state candidate
  invariantPreserved : K.protectedInvariant candidate.next
  progressNondecreasing : ProgressNondecreasing K state candidate
  strictProgressWhenWitness : StrictProgressWhenWitness K state candidate certificate
  trustValid : K.trustValid state candidate certificate
  resourceValid : K.resourceValid state candidate certificate
  realityContained : K.realityContained state candidate certificate
  successorAdmissible : K.admissible candidate.next

end RCP
end RcpRclmFormalCoreV2
