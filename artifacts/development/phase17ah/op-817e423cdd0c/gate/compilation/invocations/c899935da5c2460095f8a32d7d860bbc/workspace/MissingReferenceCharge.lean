import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (authorizedReplay grant1 grant1 grant1.binding context1 evaluator1 2 state1_0 observations1 = some { state1_8 with spent := [] })
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, case_second_source]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProducerDomainControl
