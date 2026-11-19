import ServiceLifecycle
namespace Phase17ServiceLifecycleControl
open Phase17ServiceLifecycle Phase17ServiceLifecycleExamples
set_option maxRecDepth 65536
set_option maxHeartbeats 32000000
def wrongClaim : Bool := decide (execute { firstReserve with before := { firstReserve.before with current := { firstReserve.before.current with commission := "untrusted" } } } ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ServiceLifecycleControl
