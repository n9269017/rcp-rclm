import RcpRclmFormalCoreV2.RCP.Certificates

namespace RcpRclmFormalCoreV2
namespace RCP

/--
A trusted checker is a Boolean decision procedure paired with a proof that every
accepted packet satisfies the formal one-step obligations, provided the
predecessor is in the theorem domain and already satisfies the protected
invariant.
-/
structure TrustedChecker
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex) where
  check : State → Candidate State Update → Certificate → Bool
  sound : ∀ {state candidate certificate},
    K.admissible state →
    K.protectedInvariant state →
    check state candidate certificate = true →
    StepObligations K state candidate certificate

/-- The reserved one-step theorem name from the formal contract. -/
theorem accepted_step_sound
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    {state : State}
    {candidate : Candidate State Update}
    {certificate : Certificate}
    (stateAdmissible : K.admissible state)
    (stateInvariant : K.protectedInvariant state)
    (accepted : checker.check state candidate certificate = true) :
    StepObligations K state candidate certificate :=
  checker.sound stateAdmissible stateInvariant accepted

end RCP
end RcpRclmFormalCoreV2
