import ControllerAuthority
namespace Phase17ControllerAuthorityControl
open Phase17ProducerDomain Phase17ControllerAuthority Phase17ControllerAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def zeroPermit : Permit := { permit0_0 with initial := Phase17Controller.initial 0 }
def zeroPolicy : AuthorityPolicy := { policy0 with candidateCredits := 0, sources := [zeroPermit] }
def wrongClaim : Bool := decide (issue zeroPolicy zeroPolicy "head" "head" state0_0 zeroPermit ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ControllerAuthorityControl
