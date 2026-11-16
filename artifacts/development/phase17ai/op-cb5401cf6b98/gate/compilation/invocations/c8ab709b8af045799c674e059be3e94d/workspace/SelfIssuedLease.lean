import ControllerAuthority
namespace Phase17ControllerAuthorityControl
open Phase17ProducerDomain Phase17ControllerAuthority Phase17ControllerAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (issue policy0 { policy0 with poolAttempts := 96 } "head" "head" state0_0 permit0_0 ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ControllerAuthorityControl
