import AuthorityWitness
namespace Phase17AuthorityWitnessControl
open Phase17AuthorityWitness Phase17AuthorityWitnessExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 witness1_3 (.execute "owner" Phase17ControllerAuthorityExamples.completion0_0) ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17AuthorityWitnessControl
