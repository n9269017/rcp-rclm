import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (truthfulReplay context1 evaluator1 (Phase17Controller.initial 32) [⟨19, true⟩] ≠ none)
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, truthfulReplay, Phase17Controller.initial, Phase17Controller.seen, List.map_nil, evaluation1_0, Bool.true_eq_false, if_false]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProducerDomainControl
