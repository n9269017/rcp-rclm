import AuthenticatedAuthority
namespace Phase17AuthenticatedAuthorityControl
open Phase17AuthenticatedAuthority Phase17AuthenticatedAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (dispatch commission channel firstReply.before firstConsumed { firstRequest with root := "untrusted" } ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17AuthenticatedAuthorityControl
