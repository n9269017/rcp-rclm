import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (canonicalTask fixed source1 (Phase17Provenance.rowAt context1 19).key (rowProgram domain1 19) = some 40)
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, choice1_0]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProducerDomainControl
