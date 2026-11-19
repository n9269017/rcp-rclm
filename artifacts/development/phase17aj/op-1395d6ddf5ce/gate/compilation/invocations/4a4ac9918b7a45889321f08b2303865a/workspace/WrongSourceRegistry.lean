import AuthorityWitness
namespace Phase17AuthorityWitnessControl
open Phase17AuthorityWitness Phase17AuthorityWitnessExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_1 (.reserve "owner" { Phase17ControllerAuthorityExamples.permit0_0 with checkpoint := "foreign-checkpoint" }) ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17AuthorityWitnessControl
