import DurableAuthority
namespace Phase17DurableAuthorityControl
open Phase17DurableAuthority Phase17DurableAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (Phase17AuthorityWitness.perform provision1.witness Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_3.witness (.execute "owner" Phase17ControllerAuthorityExamples.completion0_0) ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17DurableAuthorityControl
