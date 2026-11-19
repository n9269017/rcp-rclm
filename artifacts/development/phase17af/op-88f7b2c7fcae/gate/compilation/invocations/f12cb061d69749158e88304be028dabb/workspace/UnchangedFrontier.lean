import SelectedSecondStep
namespace Phase17SecondStepControl
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongAfter := { observedAfter with declared := Phase17Finite.selectedAfter.declared, namedFrontier := Phase17Finite.selectedAfter.namedFrontier }
def wrongClaim : Bool := decide ((Phase17Finite.frontier fixed Phase17Finite.selectedAfter).card < (Phase17Finite.frontier fixed wrongAfter).card)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17SecondStepControl
