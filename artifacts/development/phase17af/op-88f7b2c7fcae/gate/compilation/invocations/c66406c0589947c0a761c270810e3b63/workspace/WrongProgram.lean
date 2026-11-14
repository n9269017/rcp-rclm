import SelectedSecondStep
namespace Phase17SecondStepControl
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongProgram : Program := { secondUpdate.program with a := 0 }
def wrongClaim : Bool := (fixed.catalog secondUpdate.task).check { proofs := Phase17Finite.selectedAfter.proofs, programs := Phase17Finite.selectedAfter.programs ++ [(secondUpdate.key, wrongProgram)] }
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17SecondStepControl
