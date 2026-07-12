import RcpRclmFormalCoreV2.RCP.Types

namespace RcpRclmFormalCoreV2
namespace RCP

/-- The declared progress functional does not decrease. -/
def ProgressNondecreasing
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex)
    (state : State)
    (candidate : Candidate State Update) : Prop :=
  K.progress state ≤ K.progress candidate.next

/-- A certified strict witness forces a strict increase of the same functional. -/
def StrictProgressWhenWitness
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex)
    (state : State)
    (candidate : Candidate State Update)
    (certificate : Certificate) : Prop :=
  K.strictWitness state candidate certificate →
    K.progress state < K.progress candidate.next

end RCP
end RcpRclmFormalCoreV2
