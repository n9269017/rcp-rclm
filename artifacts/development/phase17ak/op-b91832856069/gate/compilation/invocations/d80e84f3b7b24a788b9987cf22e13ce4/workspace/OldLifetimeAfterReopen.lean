import DurableAuthority
namespace Phase17DurableAuthorityControl
open Phase17DurableAuthority Phase17DurableAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_4 (handle root0_3) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5 root0_5.witness.head root0_5.witness.journal image0_5 ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17DurableAuthorityControl
