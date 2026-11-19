import AuthenticatedAuthority
namespace Phase17AuthenticatedAuthorityControl
open Phase17AuthenticatedAuthority Phase17AuthenticatedAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (acceptReply commission channel firstPending firstRequest { firstReply with challenge := "untrusted" } = true)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17AuthenticatedAuthorityControl
