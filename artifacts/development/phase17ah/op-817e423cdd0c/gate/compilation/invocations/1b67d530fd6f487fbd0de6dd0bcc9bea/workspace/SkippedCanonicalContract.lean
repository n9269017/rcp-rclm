import ProducerDomain
namespace Phase17ProducerDomainControl
open Phase17ProducerDomainExamples Phase17ProducerDomain Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (canonicalTask fixed source1 (Phase17Provenance.rowAt context1 0).key (rowProgram domain1 0) = some 57)
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, choice1_7]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ProducerDomainControl
