import DurableCampaign
namespace Phase17DurableCampaignControl
open Phase17DurableCampaign Phase17DurableCampaignExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (commit provision1 provision1.binding interruptedFinal (cursor interruptedFinal) .backend (.launch interruptedGrant) "new-head" interruptedFinal.journal "new-image" ≠ none)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17DurableCampaignControl
