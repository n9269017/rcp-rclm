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

/--
The laws needed to compose one-step recovery maps into an endpoint rollback
bound.  They are kept separate from `Kernel` so that the basic checker theorem
does not silently assume metric or channel-like structure that an
instantiation has not supplied.

Only the laws used by the finite endpoint theorem are required:

* zero self-distance;
* a triangle inequality; and
* nonexpansiveness of every candidate-tied recovery map.

No symmetry or point-separation law is assumed because neither is needed for
the paper's telescoping rollback argument.
-/
structure RecoveryCompositionLaws
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex) : Prop where
  selfDistanceZero : ∀ state, K.stateDistance state state = 0
  triangle : ∀ x y z,
    K.stateDistance x z ≤ K.stateDistance x y + K.stateDistance y z
  recoverNonexpansive : ∀ state candidate x y,
    K.stateDistance
        (K.recover state candidate x)
        (K.recover state candidate y) ≤
      K.stateDistance x y

end RCP
end RcpRclmFormalCoreV2
