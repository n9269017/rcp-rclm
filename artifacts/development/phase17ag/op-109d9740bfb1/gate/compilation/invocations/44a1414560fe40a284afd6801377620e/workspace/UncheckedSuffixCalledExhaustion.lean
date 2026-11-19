import TruthfulSuccessorInterface
namespace Phase17SuccessorInterfaceControl
open Phase17SuccessorInterface Phase17TruthfulSuccessor Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (resultSummary 2 1 result_budget_before_selected = (1, none, 1))
theorem actual_rejection : wrongClaim = false := by simp only [wrongClaim, case_budget_before_selected]; decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17SuccessorInterfaceControl
