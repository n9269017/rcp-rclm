import RcpRclmFormalCoreV2.RCP.Types

namespace RcpRclmFormalCoreV2
namespace RCP

/--
The recovery map associated with the actual candidate update returns from the
claimed successor to within the declared recovery budget of the predecessor.
-/
def ConstructiveRecovery
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex)
    (state : State)
    (candidate : Candidate State Update) : Prop :=
  K.stateDistance
      (K.recover state candidate candidate.next)
      state ≤
    K.recoveryBudget state candidate

end RCP
end RcpRclmFormalCoreV2
