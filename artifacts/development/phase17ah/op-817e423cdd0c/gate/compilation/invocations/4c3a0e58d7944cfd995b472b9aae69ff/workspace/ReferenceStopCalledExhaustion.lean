import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (Phase17Controller.decision context4 state4_3.controller = some .searchExhausted)
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, terminal4]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProducerDomainControl
