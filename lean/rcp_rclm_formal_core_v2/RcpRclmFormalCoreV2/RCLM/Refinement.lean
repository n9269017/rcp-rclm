import RcpRclmFormalCoreV2.RCP.Checker

namespace RcpRclmFormalCoreV2
namespace RCLM

/--
Contract for forgetting a substantive RCLM state/update/certificate packet to an
RCP theorem-kernel instance. Checker preservation is intentionally separated
from the structural maps and will be proved in the architecture theorem layer.
-/
structure Refinement
    {CoreState CoreUpdate CoreCertificate Protected ResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate : Type*}
    (coreKernel : RCP.Kernel CoreState CoreUpdate CoreCertificate Protected ResidualIndex) where
  forgetState : RclmState → CoreState
  forgetCandidate : RCP.Candidate RclmState RclmUpdate →
    RCP.Candidate CoreState CoreUpdate
  forgetCertificate : RclmCertificate → CoreCertificate

  rclmAdmissible : RclmState → Prop
  admissiblePreserved : ∀ state,
    rclmAdmissible state →
    coreKernel.admissible (forgetState state)

  candidateNextCompatible : ∀ candidate,
    (forgetCandidate candidate).next = forgetState candidate.next

  invariantTransport : RclmState → Prop
  invariantPreserved : ∀ state,
    invariantTransport state →
    coreKernel.protectedInvariant (forgetState state)

end RCLM
end RcpRclmFormalCoreV2
