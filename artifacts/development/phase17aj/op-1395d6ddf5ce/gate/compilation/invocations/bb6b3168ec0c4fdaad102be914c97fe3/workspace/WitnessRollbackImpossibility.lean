import AuthorityWitness
namespace Phase17AuthorityWitnessControl
open Phase17AuthorityWitness Phase17AuthorityWitnessExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_1 request0_2 witness0_2.head witness0_2.journal = none)
theorem actual_rejection : wrongClaim = false := by
  simp only [wrongClaim, witness_rollback_is_outside_guarantee, decide_false]
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17AuthorityWitnessControl
