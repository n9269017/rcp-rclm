import AuthenticatedAuthority
namespace Phase17AuthenticatedAuthorityControl
open Phase17AuthenticatedAuthority Phase17AuthenticatedAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (acceptReply commission channel { firstPending with history := firstPending.history.map (fun h => if h.cursor.serial = 0 then { h with cursor := { h.cursor with head := "forked" } } else h) } firstRequest firstReply = true)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17AuthenticatedAuthorityControl
