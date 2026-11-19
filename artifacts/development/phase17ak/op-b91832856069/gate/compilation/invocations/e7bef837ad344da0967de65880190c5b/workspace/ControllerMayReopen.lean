import DurableAuthority
namespace Phase17DurableAuthorityControl
open Phase17DurableAuthority Phase17DurableAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_0 (handle root0_0) (cursor root0_0) .mutation Phase17AuthorityWitnessExamples.request0_1 root0_1.witness.head root0_1.witness.journal image0_1 ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17DurableAuthorityControl
