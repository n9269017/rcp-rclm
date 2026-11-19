import DurableAuthority
namespace Phase17DurableAuthorityControl
open Phase17DurableAuthority Phase17DurableAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal ⟨image0_1.rootHead, image0_2.pair⟩ ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17DurableAuthorityControl
