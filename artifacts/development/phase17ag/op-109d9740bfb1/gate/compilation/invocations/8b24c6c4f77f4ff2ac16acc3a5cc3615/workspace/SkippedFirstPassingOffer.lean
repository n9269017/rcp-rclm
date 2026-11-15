import TruthfulSuccessorInterface
namespace Phase17SuccessorInterfaceControl
open Phase17SuccessorInterface Phase17TruthfulSuccessor Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (resultSummary 2 2 (search fixed contexts charges Phase17Finite.selectedAfter [selectedOffer, selectedOffer] 2) = (0, some 1, 2))
theorem actual_rejection : wrongClaim = false := by simp [wrongClaim, search, scan, selected_check, resultSummary]
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17SuccessorInterfaceControl
