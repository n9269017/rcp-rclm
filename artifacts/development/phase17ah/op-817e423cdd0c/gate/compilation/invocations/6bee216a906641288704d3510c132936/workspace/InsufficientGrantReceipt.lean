import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (authorizedStep grant4 grant4 grant4.binding context4 evaluator4 2 state4_3 ⟨27, false⟩ ≠ none)
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, resource_denial_no_receipt]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProducerDomainControl
