import SelectedSecondStep
namespace Phase17SecondStepControl
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongProposal := { secondProposal with choices := [] }
def wrongClaim : Bool := (@decide (Phase17Provenance.CandidateMatches secondContext wrongProposal (Phase17Finite.candidateView secondCandidate)) (by unfold Phase17Provenance.CandidateMatches Phase17Provenance.Produced Phase17Provenance.ContextValid; infer_instance))
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17SecondStepControl
