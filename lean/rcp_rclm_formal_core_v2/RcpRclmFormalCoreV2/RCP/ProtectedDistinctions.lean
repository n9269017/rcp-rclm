import RcpRclmFormalCoreV2.RCP.Types

namespace RcpRclmFormalCoreV2
namespace RCP

/--
Every protected distinction retains its declared value up to the explicit loss
budget after cross-time transport through the candidate update.
-/
def ProtectedNonLoss
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex)
    (state : State)
    (candidate : Candidate State Update) : Prop :=
  ∀ protected,
    K.protectedValue state protected ≤
      K.protectedValue candidate.next
        (K.transportProtected state candidate protected) +
      K.lossBudget state candidate

end RCP
end RcpRclmFormalCoreV2
