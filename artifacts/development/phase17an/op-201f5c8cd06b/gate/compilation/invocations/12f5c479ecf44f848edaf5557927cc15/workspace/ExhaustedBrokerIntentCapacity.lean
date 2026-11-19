import ProtectedAuthority
namespace Phase17ProtectedAuthorityControl
open Phase17ProtectedAuthority Phase17ProtectedAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (dispatch commission runtime { firstState with consumed := List.replicate commission.maxIntents "used" } runIntent ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProtectedAuthorityControl
