import RcpRclmFormalCoreV2.RCLM.State
import RcpRclmFormalCoreV2.RCLM.Update
import RcpRclmFormalCoreV2.RCLM.CertificatePacket
import RcpRclmFormalCoreV2.RCLM.Refinement

namespace RcpRclmFormalCoreV2
namespace RCLM

/-!
Architecture theorem target.

The initial milestone fixes the typed state, update, certificate, and refinement
interfaces but does not yet claim `rclm_checker_refines_rcp` or
`rclm_architecture_successor_theorem`. Those theorems will be added only after
Gate A builds and the concrete Gate B refinement obligations are available.
-/

end RCLM
end RcpRclmFormalCoreV2
